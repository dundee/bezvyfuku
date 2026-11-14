# -*- coding: utf-8 -*-
"""
Pipeline pro bezvyfuku.cz.

Pouziti:
    uv run python -m pipeline ingest RSV_vypis_vozidel_20261101.csv
    curl -sSf <url> | uv run python -m pipeline ingest - --date 2026-11-01
    uv run python -m pipeline report [--snapshot 2026-11-01] [--month 2026-10] [-o out.xlsx]
    uv run python -m pipeline export [--snapshot 2026-11-01]
"""

import argparse

from . import export, report, snapshot


def main():
    ap = argparse.ArgumentParser(
        prog="python -m pipeline",
        description="Data pro bezvyfuku.cz z otevrenych dat RSV.",
    )
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ingest", help="prevest CSV snapshot na Parquet v data/snapshots")
    p.add_argument("csv_path", help="RSV_vypis_vozidel_RRRRMMDD.csv, nebo - pro stdin")
    p.add_argument("--date", help="datum snapshotu RRRR-MM-DD (vychozi: ze jmena souboru)")

    snap_help = "RRRR-MM-DD nebo cesta k Parquetu (vychozi: posledni snapshot)"
    p = sub.add_parser("report", help="mesicni XLSX report")
    p.add_argument("--snapshot", help=snap_help)
    p.add_argument("--month", help="cilovy mesic RRRR-MM (vychozi: posledni cely mesic)")
    p.add_argument("-o", "--output", help="cesta k vystupnimu XLSX")

    p = sub.add_parser("export", help="data pro web do site/src/data")
    p.add_argument("--snapshot", help=snap_help)

    args = ap.parse_args()
    if args.command == "ingest":
        snapshot.ingest(args.csv_path, args.date)
    elif args.command == "report":
        report.run(snapshot.find(args.snapshot), args.month, args.output)
    elif args.command == "export":
        export.run(snapshot.find(args.snapshot))


if __name__ == "__main__":
    main()
