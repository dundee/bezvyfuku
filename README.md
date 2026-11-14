# bezvyfuku.cz

Elektromobily v registracích aut: web s interaktivními grafy z otevřených dat
[Registru silničních vozidel](https://download.dataovozidlech.cz/).

## Jak to funguje

Ministerstvo dopravy každý měsíc zveřejňuje úplný výpis registru jako CSV (~17 GB).
Aktuální výpis je vždy na <https://download.dataovozidlech.cz/vypiszregistru/vypisvozidel>,
nový vychází 12. dne v měsíci.

1. `pipeline ingest` převede CSV na Parquet (~2,3 GB, ~15 s) do `data/snapshots/`.
2. `pipeline report` vytvoří měsíční XLSX report (stejný jako dřív `rsv_report.py`).
3. `pipeline export` spočítá měsíční řady pro web do `site/src/data/registrace.json` (~100 kB).
4. `site/` je statický web (Astro + ECharts), `npm run build` ho sestaví do `site/dist/`.

Pravidla výběru (populace, nová/ojetá, paliva, aliasy značek) jsou na jednom místě
v `pipeline/rules.py`. Report i web z nich počítají, takže čísla sedí.

`registrace.json` je v gitu: diff mezi měsíci ukazuje, jak se čísla zpětně mění
s novým výpisem.

## Požadavky

- [uv](https://docs.astral.sh/uv/), Python 3.14 a závislosti si stáhne sám
- Node.js 26 (viz `.tool-versions`)

## Každý měsíc

```sh
uv run python -m pipeline ingest RSV_vypis_vozidel_20261201.csv
uv run python -m pipeline report    # report_2026-11.xlsx
uv run python -m pipeline export
cd site && npm run build
```

`report` i `export` berou poslední snapshot, jiný jde vybrat přes `--snapshot 2026-11-01`.

## Vývoj

```sh
uv sync
uv run pytest

cd site
npm install
npx astro dev --background    # http://localhost:4321, zastavit: npx astro dev stop
npm run check
```

`tests/golden/` obsahuje reporty z původního `rsv_report.py`. Testy hlídají, že port
dává stejná čísla a že součty na webu sedí s reportem. Testy nad daty se přeskočí,
když v `data/snapshots/` chybí příslušný výpis.
