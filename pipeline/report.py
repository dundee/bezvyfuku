# -*- coding: utf-8 -*-
"""
Mesicni XLSX report novych registraci osobnich vozidel (port rsv_report.py).

Vystup: XLSX se tremi listy - nove registrace podle pohonu, BEV registrace
podle tovarni znacky a dovezene ojetiny podle pohonu, vse s mezirocnim
srovnanim. Pocty se stejne jako v puvodnim skriptu berou ze snapshotu
nasledujiciho mesice, mezirocni srovnani z tehoz snapshotu.
"""

import re
import sys
from collections import Counter

from . import rules, snapshot

MESICE_CZ = [
    "leden", "unor", "brezen", "duben", "kveten", "cerven",
    "cervenec", "srpen", "zari", "rijen", "listopad", "prosinec",
]


# --------------------------------------------------------------------------
# Vyber a agregace
# --------------------------------------------------------------------------

def count(con, column, month, nove, bev_only=False):
    """Pocty z pohledu 'osobni' za mesic, seskupene podle 'palivo' nebo 'znacka'."""
    assert column in ("palivo", "znacka")
    sql = "SELECT %s, count(*) FROM osobni WHERE mesic = ? AND nove = ?" % column
    params = [month, nove]
    if bev_only:
        sql += " AND palivo_kod = ?"
        params.append(rules.PALIVO_BEV)
    return Counter(dict(con.execute(sql + " GROUP BY 1", params).fetchall()))


def build_table(cur, prev, with_shares):
    """Sloucena tabulka za oba roky, serazena sestupne podle aktualniho mesice."""
    cur_total, prev_total = sum(cur.values()), sum(prev.values())
    keys = sorted(set(cur) | set(prev), key=lambda k: (-cur.get(k, 0), k))
    table = []
    for k in keys:
        c, p = cur.get(k, 0), prev.get(k, 0)
        yoy = (c / p) if p else None
        if with_shares:
            table.append([
                k, c, (c / cur_total if cur_total else None),
                p, (p / prev_total if prev_total else None), yoy,
            ])
        else:
            table.append([k, c, p, yoy])
    return table, cur_total, prev_total


# --------------------------------------------------------------------------
# Zapis XLSX
# --------------------------------------------------------------------------

def month_label(month):
    year, mon = int(month[:4]), int(month[5:7])
    return "%s %d" % (MESICE_CZ[mon - 1], year)


def write_xlsx(path, month, prev_month, fuel_new, brands, fuel_used):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font

    year = int(month[:4])
    bold = Font(bold=True)

    def style_header(ws, ncols):
        for c in range(1, ncols + 1):
            cell = ws.cell(row=1, column=c)
            cell.font = bold
            cell.alignment = Alignment(horizontal="center")
        ws.freeze_panes = "A2"
        ws.column_dimensions["A"].width = 30
        for col in "BCDEF"[: ncols - 1]:
            ws.column_dimensions[col].width = 16

    def fuel_sheet(ws, data):
        table, cur_total, prev_total = data
        ws.append(["Palivo", "Vše", "Podíl", month_label(prev_month), "Podíl", "YoY"])
        for row in table:
            ws.append(row)
        ws.append([])
        ws.append([
            "celkem", cur_total, None, prev_total, None,
            (cur_total / prev_total) if prev_total else None,
        ])
        for r in range(2, ws.max_row + 1):
            ws.cell(row=r, column=3).number_format = "0.0%"
            ws.cell(row=r, column=5).number_format = "0.0%"
            ws.cell(row=r, column=6).number_format = "0.00"
        ws.cell(row=ws.max_row, column=1).font = bold
        style_header(ws, 6)

    wb = Workbook()

    ws = wb.active
    ws.title = "vse podle pohonu %s" % month_label(month)
    fuel_sheet(ws, fuel_new)

    ws = wb.create_sheet("znacky %s" % month_label(month))
    brand_table, brand_cur_total, brand_prev_total = brands
    ws.append([
        "Tovární značka",
        "počet registrací %d" % year,
        "počet registrací %d" % (year - 1),
        "YoY",
    ])
    for row in brand_table:
        ws.append(row)
    ws.append([])
    ws.append([
        "celkem", brand_cur_total, brand_prev_total,
        (brand_cur_total / brand_prev_total) if brand_prev_total else None,
    ])
    for r in range(2, ws.max_row + 1):
        ws.cell(row=r, column=4).number_format = "0.00"
    ws.cell(row=ws.max_row, column=1).font = bold
    style_header(ws, 4)

    fuel_sheet(wb.create_sheet("ojetiny podle pohonu %s" % month_label(month)),
               fuel_used)

    wb.save(path)


# --------------------------------------------------------------------------
# Kontroly
# --------------------------------------------------------------------------

def previous_year(month):
    return "%04d-%s" % (int(month[:4]) - 1, month[5:7])


# Zapis, ktery vypada spis na prestavbare nebo karosarnu nez na znacku
# (napr. 'EDWARD DAVIES COMMERCIALS LTD' u prestaveneho Fordu Tourneo).
# Takove radky stoji za rucni kontrolu, jestli nepatri pod nekterou znacku.
FIRMA_RE = re.compile(
    r"(?<![&\w])(LTD|LIMITED|GMBH|S\.?R\.?O\.?|A\.?S\.?|INC|N\.?V\.?|B\.?V\.?"
    r"|COMMERCIALS|COMPANY|HOLDING|GROUP)(?![&\w])"
)


def suspicious_brands(counts):
    return {
        name: n for name, n in counts.items()
        if FIRMA_RE.search(name.upper()) or len(name.split()) >= 3 or "," in name
    }


def report_unmapped_fuels(con, month, out=sys.stdout):
    fuels = con.execute(
        "SELECT palivo_kod, count(*) FROM osobni WHERE mesic = ? "
        "AND palivo_kod NOT IN (SELECT kod FROM palivo_labels) GROUP BY 1 ORDER BY 1",
        [month],
    ).fetchall()
    if fuels:
        print("  paliva mimo mapu (prosla syrove): %s"
              % ", ".join("%s (%d)" % (k, v) for k, v in fuels), file=out)


# --------------------------------------------------------------------------
# Beh
# --------------------------------------------------------------------------

def run(parquet, month=None, output=None):
    snapshot_date = snapshot.date_from_name(parquet)
    month = month or snapshot.last_month(snapshot_date)
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        raise SystemExit("Mesic musi byt ve tvaru RRRR-MM, dostal jsem %r" % month)
    prev_month = previous_year(month)
    output = output or "report_%s.xlsx" % month

    print("Snapshot: %s" % parquet)
    print("Mesic   : %s, meziroc. srovnani %s" % (month, prev_month))

    con = snapshot.connect(parquet)
    fuel_new = build_table(count(con, "palivo", month, True),
                           count(con, "palivo", prev_month, True), with_shares=True)
    fuel_used = build_table(count(con, "palivo", month, False),
                            count(con, "palivo", prev_month, False), with_shares=True)
    bev_counts = count(con, "znacka", month, True, bev_only=True)
    brands = build_table(bev_counts, count(con, "znacka", prev_month, True, bev_only=True),
                         with_shares=False)
    bev_used = sum(count(con, "znacka", month, False, bev_only=True).values())
    bev_used_prev = sum(count(con, "znacka", prev_month, False, bev_only=True).values())

    if not fuel_new[1]:
        raise SystemExit(
            "Za %s nejsou zadne nove registrace. Je mesic uz ve snapshotu?" % month
        )

    print()
    print("%-18s %10s %10s" % ("", month, prev_month))
    print("%-18s %10d %10d" % ("nove", fuel_new[1], fuel_new[2]))
    print("%-18s %10d %10d" % ("  z toho BEV", brands[1], brands[2]))
    print("%-18s %10d %10d" % ("dovoz ojetin", fuel_used[1], fuel_used[2]))
    print("%-18s %10d %10d" % ("  z toho BEV", bev_used, bev_used_prev))

    # Kontrola, ze se v agregaci nic neztratilo.
    total_new, total_used = con.execute(
        "SELECT count(*) FILTER (WHERE nove), count(*) FILTER (WHERE NOT nove) "
        "FROM osobni WHERE mesic = ?", [month]).fetchone()
    assert fuel_new[1] == total_new, "soucet po palivech nesedi na pocet novych"
    assert fuel_used[1] == total_used, "soucet po palivech nesedi na pocet ojetin"

    print("\nKontroly:")
    print("  soucet po palivech sedi na pocet radku")
    report_unmapped_fuels(con, month)
    odd = suspicious_brands(bev_counts)
    if odd:
        print("  znacky, ktere vypadaji na prestavbare - zvaz alias: %s"
              % ", ".join("%s (%d)" % (k, v) for k, v in sorted(odd.items())))

    write_xlsx(output, month, prev_month, fuel_new, brands, fuel_used)
    print("\nHotovo: %s" % output)
    return output
