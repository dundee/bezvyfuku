# -*- coding: utf-8 -*-
"""
Port musi dat stejna cisla jako puvodni rsv_report.py a web stejne soucty
jako report.

Referencni XLSX v golden/ jsou vystupy puvodniho skriptu. Testy nad daty
se preskoci, kdyz prislusny snapshot neni v data/snapshots (stahnout
a prevest pres 'python -m pipeline ingest').
"""

import json
from pathlib import Path

import duckdb
import openpyxl
import pytest

from pipeline import export, report, rules, snapshot

GOLDEN = Path(__file__).parent / "golden"

# (snapshot, mesic reportu)
CASES = [
    ("2026-08-01", "2026-07"),
    ("2026-09-01", "2026-08"),
    ("2026-10-01", "2026-09"),
    ("2026-11-01", "2026-10"),
]


def read_sheets(path):
    wb = openpyxl.load_workbook(path, read_only=True)
    return {ws.title: [list(r) for r in ws.iter_rows(values_only=True)]
            for ws in wb.worksheets}


# report_2026-10.xlsx byl po vygenerovani upraven rucne: hlavicka listu
# s palivy je 'Registrací' misto 'Vše' a chybi radky s malymi pocty
# (BA + BA, E 95, Nafta + Bionafta, ...). Soucty 'celkem' je ale porad
# zahrnuji. U nej se porovnava jen to, co v nem zustalo, a soucty.
EDITED = {"2026-10"}


def golden(month):
    sheets = read_sheets(GOLDEN / ("report_%s.xlsx" % month))
    if month in EDITED:
        for rows in sheets.values():
            if rows[0][1] == "Registrací":
                rows[0][1] = "Vše"
    return sheets


def assert_same_report(mine, ref, edited):
    assert list(mine) == list(ref)
    for title, rows in ref.items():
        if not edited:
            assert mine[title] == rows, title
            continue
        *table, _blank, total = rows
        assert mine[title][:len(table)] == table, title
        assert mine[title][-1] == total, title


def snapshot_or_skip(date):
    path = snapshot.SNAPSHOT_DIR / ("%s.parquet" % date)
    if not path.exists():
        pytest.skip("chybi snapshot %s" % date)
    return path


@pytest.mark.parametrize("date,month", CASES)
def test_report_matches_original(tmp_path, date, month):
    parquet = snapshot_or_skip(date)
    out = report.run(parquet, month, tmp_path / "report.xlsx")
    assert_same_report(read_sheets(out), golden(month), month in EDITED)


@pytest.mark.parametrize("date,month", CASES)
def test_export_totals_match_report(date, month):
    parquet = snapshot_or_skip(date)
    data, _ = export.build(snapshot.connect(parquet), date)
    assert json.loads(export.dumps(data)) == data

    i = data["mesice"].index(month)

    def totals(rady):
        return [sum(s[i] for s in rady.values()), sum(s[i - 12] for s in rady.values())]

    fuel_new, brands, fuel_used = golden(month).values()
    assert totals(data["pohon"]["nove"]) == [fuel_new[-1][1], fuel_new[-1][3]]
    assert totals(data["pohon"]["ojete"]) == [fuel_used[-1][1], fuel_used[-1][3]]
    assert totals(data["bevZnacky"]["nove"]) == [brands[-1][1], brands[-1][2]]
    assert totals(data["bevModely"]["nove"]) == [brands[-1][1], brands[-1][2]]
    bev = data["pohon"]["nove"][rules.SKUPINA_BEV]
    assert [bev[i], bev[i - 12]] == [brands[-1][1], brands[-1][2]]
    bev_ojete = data["pohon"]["ojete"][rules.SKUPINA_BEV]
    assert totals(data["bevModely"]["ojete"]) == [bev_ojete[i], bev_ojete[i - 12]]


@pytest.mark.parametrize("kod,skupina", [
    ("EL", "Elektro (BEV)"),
    ("EL.", "Ostatní"),
    ("BA + EL", "Hybrid"),
    ("EL + NM", "Hybrid"),
    ("BA 95 B+LPG+EL", "Hybrid"),
    ("BA", "Benzín"),
    ("BA ", "Benzín"),
    ("BA 95 B", "Benzín"),
    ("BA + E 85", "Benzín"),
    ("BENZIN", "Benzín"),
    ("NM", "Nafta"),
    ("NM I NM BIO 48", "Nafta"),
    ("BIO NM", "Nafta"),
    ("BA + LPG", "LPG"),
    ("BA95B+LPG", "LPG"),
    ("ba95b+lpg", "LPG"),
    ("PB+BA", "LPG"),
    ("BA + CNG", "CNG"),
    ("CNG+BA", "CNG"),
    ("NG", "CNG"),
    ("LNG", "CNG"),
    ("VODÍK", "Ostatní"),
    (".", "Ostatní"),
    ("", "Ostatní"),
    ("DIESEL", "Ostatní"),
])
def test_skupina_paliva(kod, skupina):
    assert rules.skupina_paliva(kod) == skupina


def test_strip_matches_python():
    con = duckdb.connect()
    for s in [" ŠKODA ", "\u00a0TESLA\u3000", "\tBYD\n", "\x1cMG\x85", "  ", "KIA"]:
        got = con.execute("SELECT " + snapshot.sql_strip("?"), [s]).fetchone()[0]
        assert got == s.strip()


def test_month_range():
    assert export.month_range("2025-11", "2026-02") == [
        "2025-11", "2025-12", "2026-01", "2026-02"]
