# Polar pipeline v1: what it does (14 Nov 2026)

One command, from the repo root:

```powershell
.venv\Scripts\python.exe src\run_pipeline.py --bbox 83 28 85 30 --name mustang_polar   # GLO-30, ~2 min
```

`bbox → 15 km cells → land-cover filter → terrain criteria per surviving cell (60 m local-UTM grid) → 0–1 scores → weighted score → ranking`

Thresholds and weights: `config/pipeline.yaml`. Lunar reference values: `config/lunar_targets.json` (all TODO from LOLA).

## Stage 1: hard filters (`src/pipeline/filters.py`)
- Drop WorldCover classes tree (10), cropland (40), built-up (50), water (80), wetland (90), mangroves (95). Keep shrub, grass, bare, snow/ice, moss.
- Mask 2 km around built-up and 200 m around water/wetland.
- Cell dropped if: usable share < 0.5, largest connected usable patch < 2 km², edge cell < half size, ocean/no data, or population > 10/km² (only with `--pop`).
- **No slope filter here**: steep walls are what we look for.

## Stage 2: Polar terrain criteria (`src/pipeline/polar.py`)
All on a 60 m grid, cell read with a 3.5 km buffer. The low point = deepest closed depression in the cell, else its lowest pixel.

| # | Criterion | Raw value | Score (0–1) |
|---|---|---|---|
| 7 | Bowl shape | closed depression depth / equivalent diameter (priority-flood fill) | rank in run, higher = better |
| 9 | Relief | max − min in 5 km square at the low point (m) | rank in run, higher = better |
| 10 | Flat base spot | mean slope of the flattest usable ~200 m pad (°); **> 15° → cell dropped** (only slope filter) | linear: 0° → 1, 15° → 0 |
| 11 | Steep walls | mean slope in 500–3000 m ring around the low point (°) | rank in run, higher = better |
| 13 | Roughness | median std of elevation in 3×3 px (m) | None until a lunar target exists |
| 14 | Pole-facing slopes | share of slopes > 20° facing the nearer pole (±45°) | the share itself |

- 10 and 11 are separate; steep pixels are never masked.
- Missing data = None ("no data"), never 0. The weighted score uses only the criteria that have a score.
- Rank scores are only comparable within one run, until lunar targets are filled in.

## Outputs (`out/<name>/`)
`ranking.csv` (ranked cells, raw + score per criterion), `cells.geojson` (all cells with reasons, for the map), `radar.json` (scores per criterion + lunar target profile), `run_info.json` (bbox, sources, config).

## Known limits
- Many small "closed depressions" in steep terrain; some deep ones (e.g. 775 m at 84.011 E 28.471 N) exist in the Copernicus DEM itself, real or artifact is unchecked.
- The flattest pad can be anywhere in the cell, not necessarily next to the walls, so criterion 10 rarely drops a cell in mountains.
- Roughness (13) includes slope (std of a tilted plane is not 0).
- Light criteria 1–5 (`src/shadowsim`) and temperature are not wired in yet.

## Tests
`.venv\Scripts\python.exe -m pytest -q tests`: synthetic bowl, planes, ridge, 60 m grid on Earth and Moon projections, filters, scoring.
