# -*- coding: utf-8 -*-
"""
Snapshoty RSV: prevod mesicniho CSV na Parquet a pohledy nad nim.

CSV (~17 GB) se prevede jednou na Parquet (~2.4 GB) a vsechny dalsi kroky
uz ctou jen Parquet. Hodnoty zustavaji jako text presne podle CSV, vyklad
(populace, nove/ojete, nazvy paliv, aliasy znacek) dela az pohled 'osobni'.
"""

import re
import sys
import time
from pathlib import Path

import duckdb

from . import rules

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / "data" / "snapshots"
TMP_DIR = ROOT / "data" / "tmp"

# Znaky, ktere odstrani Python str.strip(). Puvodni skript cistil znacku
# pres strip(), SQL trim() proto musi odstranovat presne totez.
WHITESPACE = "".join(c for c in map(chr, range(sys.maxunicode + 1)) if c.isspace())


def sql_str(value):
    return "'%s'" % str(value).replace("'", "''")


def sql_strip(expr):
    return "trim(%s, %s)" % (expr, sql_str(WHITESPACE))


def ident(name):
    return '"%s"' % name.replace('"', '""')


def duckdb_connect():
    # Kdyz DuckDB dojde pamet, odklada na disk, jinak do .tmp v aktualnim adresari.
    return duckdb.connect(config={"temp_directory": str(TMP_DIR)})


# --------------------------------------------------------------------------
# Prevod CSV -> Parquet
# --------------------------------------------------------------------------

def date_from_name(path):
    """Datum snapshotu ze jmena souboru: ..._20261101.csv -> 2026-11-01."""
    m = re.search(r"(\d{4})-?(\d{2})-?(\d{2})", Path(path).name)
    if not m:
        raise SystemExit("Ze jmena souboru nejde urcit datum snapshotu: %s" % path)
    return "%s-%s-%s" % m.groups()


def read_csv_sql(csv_path):
    return (
        "read_csv(%s, header = true, all_varchar = true, delim = ',', "
        "quote = '\"', escape = '\"', store_rejects = true)" % sql_str(csv_path)
    )


def ingest(source, snapshot_date=None):
    """Prevede CSV snapshot na data/snapshots/RRRR-MM-DD.parquet.

    source je cesta k CSV, nebo '-' pro cteni ze stdin. Pak jde vypis
    stahovat rovnou do DuckDB bez 17 GB na disku, datum je ale treba zadat.
    """
    if source == "-":
        if not snapshot_date:
            raise SystemExit("Pri cteni ze stdin zadej datum snapshotu: --date RRRR-MM-DD")
        csv_path = "/dev/stdin"
        print("Soubor : stdin")
    else:
        csv_path = Path(source)
        if not csv_path.exists():
            raise SystemExit("Soubor neexistuje: %s" % csv_path)
        snapshot_date = snapshot_date or date_from_name(csv_path)
        print("Soubor : %s (%.1f GB)" % (csv_path, csv_path.stat().st_size / 1024 ** 3))
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", snapshot_date):
        raise SystemExit("Datum snapshotu musi byt ve tvaru RRRR-MM-DD, dostal jsem %r"
                         % snapshot_date)
    out = SNAPSHOT_DIR / ("%s.parquet" % snapshot_date)
    tmp = out.with_name(out.name + ".tmp")
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    # Stdin jde precist jen jednou, hlavicka se proto kontroluje az na Parquetu.
    con = duckdb_connect()
    t0 = time.time()
    con.execute("SET preserve_insertion_order = false")
    con.execute("COPY (SELECT * FROM %s) TO %s (FORMAT parquet, COMPRESSION zstd)"
                % (read_csv_sql(csv_path), sql_str(tmp)))
    columns = [r[0] for r in con.execute(
        "DESCRIBE SELECT * FROM read_parquet(%s)" % sql_str(tmp)).fetchall()]
    missing = [c for c in rules.REQUIRED_COLUMNS if c not in columns]
    if missing:
        tmp.unlink()
        raise SystemExit("V hlavicce chybi sloupce: %s" % ", ".join(missing))
    rejects = con.execute("SELECT count(*) FROM reject_errors").fetchone()[0]
    rows = con.execute("SELECT count(*) FROM read_parquet(%s)" % sql_str(tmp)).fetchone()[0]
    tmp.replace(out)

    print("Parquet: %s (%.1f GB), %.0f s, %s radku"
          % (out, out.stat().st_size / 1024 ** 3, time.time() - t0, fmt_int(rows)))
    if rejects:
        print("  POZOR: %d radku se nepodarilo zparsovat, prvni z nich:" % rejects)
        for line, err in con.execute(
                "SELECT line, error_message FROM reject_errors ORDER BY line LIMIT 5").fetchall():
            print("    radek %s: %s" % (line, err))
    return out


# --------------------------------------------------------------------------
# Prace se snapshotem
# --------------------------------------------------------------------------

def find(snapshot=None):
    """Parquet snapshotu: posledni, podle data RRRR-MM-DD, nebo primo cesta."""
    if snapshot is None:
        files = sorted(SNAPSHOT_DIR.glob("*.parquet"))
        if not files:
            raise SystemExit("V %s neni zadny snapshot, spust nejdriv: ingest <csv>"
                             % SNAPSHOT_DIR)
        return files[-1]
    path = Path(snapshot)
    if path.suffix != ".parquet":
        path = SNAPSHOT_DIR / ("%s.parquet" % snapshot)
    if not path.exists():
        raise SystemExit("Snapshot neexistuje: %s" % path)
    return path


def last_month(snapshot_date):
    """Posledni cely mesic ve snapshotu (snapshot z 1. 11. -> rijen)."""
    year, mon = int(snapshot_date[:4]), int(snapshot_date[5:7])
    year, mon = (year - 1, 12) if mon == 1 else (year, mon - 1)
    return "%04d-%02d" % (year, mon)


# Pohled 'osobni' = populace reportu, jeden radek na vozidlo.
#   mesic  - mesic 1. registrace v CR (RRRR-MM)
#   nove   - 'Datum 1. registrace' se rovna 'Datum 1. registrace v CR'.
#            Kdyz je prvni registrace starsi, vozidlo uz bylo registrovane
#            v zahranici, tedy jde o dovoz ojetiny.
#   palivo - nazev z PALIVO_LABELS, neznamy kod projde syrovy
#   skupina - siroka skupina paliva pro grafy (rules.skupina_paliva)
#   znacka - po strip() a ZNACKA_ALIASES
# Prazdne hodnoty se berou jako '', stejne jako je cetl csv modul.
OSOBNI_SQL = """
CREATE VIEW osobni AS
WITH v AS (
    SELECT
        coalesce({reg}, '') AS datum_reg,
        coalesce({reg_cz}, '') AS datum_reg_cz,
        coalesce({palivo}, '') AS palivo_kod,
        {znacka_zapis} AS znacka_zapis
    FROM vozidla
    WHERE {druh} = {druh_value}
)
SELECT
    substr(datum_reg_cz, 1, 7) AS mesic,
    datum_reg = datum_reg_cz AS nove,
    palivo_kod,
    coalesce(p.nazev, palivo_kod) AS palivo,
    s.skupina,
    coalesce(z.znacka, znacka_zapis) AS znacka
FROM v
LEFT JOIN palivo_labels p ON p.kod = v.palivo_kod
LEFT JOIN palivo_skupiny s ON s.kod = v.palivo_kod
LEFT JOIN znacka_aliases z ON z.zapis = v.znacka_zapis
"""


def connect(parquet):
    """DuckDB spojeni s pohledy 'vozidla' (cely snapshot) a 'osobni'."""
    con = duckdb_connect()
    con.execute("CREATE TABLE palivo_labels (kod VARCHAR, nazev VARCHAR)")
    con.executemany("INSERT INTO palivo_labels VALUES (?, ?)",
                    list(rules.PALIVO_LABELS.items()))
    con.execute("CREATE TABLE znacka_aliases (zapis VARCHAR, znacka VARCHAR)")
    con.executemany("INSERT INTO znacka_aliases VALUES (?, ?)",
                    list(rules.ZNACKA_ALIASES.items()))
    con.execute("CREATE VIEW vozidla AS SELECT * FROM read_parquet(%s)" % sql_str(parquet))
    kody = [r[0] for r in con.execute(
        "SELECT DISTINCT coalesce(%s, '') FROM vozidla" % ident(rules.COL_PALIVO)).fetchall()]
    con.execute("CREATE TABLE palivo_skupiny (kod VARCHAR, skupina VARCHAR)")
    con.execute("INSERT INTO palivo_skupiny SELECT unnest(?), unnest(?)",
                [kody, [rules.skupina_paliva(k) for k in kody]])
    con.execute(OSOBNI_SQL.format(
        reg=ident(rules.COL_REG),
        reg_cz=ident(rules.COL_REG_CZ),
        palivo=ident(rules.COL_PALIVO),
        znacka_zapis=sql_strip("coalesce(%s, '')" % ident(rules.COL_ZNACKA)),
        druh=ident(rules.COL_DRUH),
        druh_value=sql_str(rules.DRUH_VOZIDLA),
    ))
    return con


def fmt_int(n):
    return f"{n:,}".replace(",", " ")
