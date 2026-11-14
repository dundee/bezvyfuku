# -*- coding: utf-8 -*-
"""
Data pro web: mesicni rady registraci do site/src/data/registrace.json.

Rady se pocitaji z tehoz pohledu 'osobni' jako XLSX report, takze soucet
za mesic na webu sedi s reportem. Kazda rada je seznam poctu zarovnany
na seznam 'mesice'. Soubor je v gitu a diff mezi mesici ukazuje, jak se
cisla zpetne meni s novym snapshotem.
"""

import json
import re
from pathlib import Path

from . import rules, snapshot

START = "2010-01"
OUT = snapshot.ROOT / "site" / "src" / "data" / "registrace.json"


def month_range(start, end):
    year, mon = int(start[:4]), int(start[5:7])
    months = []
    while "%04d-%02d" % (year, mon) <= end:
        months.append("%04d-%02d" % (year, mon))
        year, mon = (year + 1, 1) if mon == 12 else (year, mon + 1)
    return months


def series(con, column, months, nove, bev_only=False, keys=None):
    """{klic: [pocet za kazdy mesic]}, v poradi 'keys', jinak sestupne podle souctu.

    Druhou hodnotou je pocet vozidel, jejichz mesic neni platny RRRR-MM
    (vadne datum v registru), ty v radach nejsou.
    """
    assert column in ("skupina", "znacka")
    sql = ("SELECT %s, mesic, count(*) FROM osobni "
           "WHERE nove = ? AND mesic >= ? AND mesic <= ?" % column)
    params = [nove, months[0], months[-1]]
    if bev_only:
        sql += " AND palivo_kod = ?"
        params.append(rules.PALIVO_BEV)
    index = {m: i for i, m in enumerate(months)}
    out, invalid = {}, 0
    for key, mesic, n in con.execute(sql + " GROUP BY ALL", params).fetchall():
        i = index.get(mesic)
        if i is None:
            invalid += n
            continue
        out.setdefault(key, [0] * len(months))[i] += n
    if keys is not None:
        unexpected = set(out) - set(keys)
        assert not unexpected, "neocekavane klice: %s" % sorted(unexpected)
        return {k: out.get(k, [0] * len(months)) for k in keys}, invalid
    ordered = dict(sorted(out.items(), key=lambda kv: (-sum(kv[1]), kv[0])))
    return ordered, invalid


def build(con, snapshot_date):
    months = month_range(START, snapshot.last_month(snapshot_date))
    data = {
        "snapshot": snapshot_date,
        "posledniMesic": months[-1],
        "skupinaBev": rules.SKUPINA_BEV,
        "mesice": months,
        "pohon": {},
        "bevZnacky": {},
        "aliasy": rules.ZNACKA_ALIASES,
    }
    invalid = 0
    for typ, nove in (("nove", True), ("ojete", False)):
        data["pohon"][typ], n = series(con, "skupina", months, nove, keys=rules.PALIVO_SKUPINY)
        invalid += n
        data["bevZnacky"][typ], _ = series(con, "znacka", months, nove, bev_only=True)
    return data, invalid


def dumps(data):
    text = json.dumps(data, ensure_ascii=False, indent=1)
    # Seznamy na jeden radek, at ma kazda rada v diffu vlastni radek.
    return re.sub(r"\[\n\s+([^\[\]{}]*?)\n\s*\]",
                  lambda m: "[" + re.sub(r",\n\s+", ",", m.group(1)) + "]", text) + "\n"


def run(parquet, out=OUT):
    snapshot_date = snapshot.date_from_name(parquet)
    con = snapshot.connect(parquet)
    data, invalid = build(con, snapshot_date)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(dumps(data), encoding="utf-8")

    months = data["mesice"]
    print("Snapshot: %s" % parquet)
    print("Mesice  : %s .. %s (%d)" % (months[0], months[-1], len(months)))
    print("Rady    : %d skupin paliv, %d znacek BEV novych, %d ojetin"
          % (len(rules.PALIVO_SKUPINY), len(data["bevZnacky"]["nove"]),
             len(data["bevZnacky"]["ojete"])))
    if invalid:
        print("  POZOR: %d vozidel ma v obdobi neplatny mesic registrace, v radach nejsou"
              % invalid)
    print("Hotovo  : %s (%.0f kB)" % (out, out.stat().st_size / 1024))
    return out
