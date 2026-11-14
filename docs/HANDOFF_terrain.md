# Handoff: DEM, filtering and terrain scoring (from claude.ai chat, 14 Nov 2026)

Context for Claude Code. Read together with `docs/Moon_Analog_Criteria_and_Datasets.md` (the team's plan: 29 criteria, 3 base types). That document is the source of truth; this file records what was built and decided in the chat.

## Project in one paragraph
NASA Space Apps 2026, challenge "Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars". We rank places on Earth by how well they stand in for lunar base sites. Focus: Moon only (Mars, Gorafe, Kali Gandaki parked). Pipeline: **hard filters → per-cell criteria scored 0–1 → weighted presets per base type (Polar, Mare, Cave) → ranking + radar chart vs. a lunar target profile.**

## Code that exists (written in the chat)
Package lives in `src/dem/`. The two scripts were first placed in `scripts/`; the repo rule is code in `src/`, so they can move to `src/` (they find `src/dem` either way).

| File | What it does |
|---|---|
| `src/dem/fetch.py` | `tile_url`, `tiles_for_bbox`, `read_bbox(west, south, east, north, res=30\|90)` reads Copernicus DEM GLO-30/90 straight from AWS (`copernicus-dem-30m` / `-90m`, unsigned), merges tiles, NaN for missing/ocean tiles. `save_tif`. |
| `src/dem/terrain.py` | `pixel_size_m`, `slope_deg` (Horn), `roughness` (std in window), `local_relief` (max−min), `tri`, `summarize` (stats + share of slope <5°, <10°, >30°). Works on the **degree grid** with an approximate metre conversion. |
| `src/dem/landcover.py` | ESA WorldCover 2021 v200 from AWS (`esa-worldcover`, 3×3° tiles named by SW corner), `read_landcover(bbox, res_m=100)` reads COG overviews (downsampled, fast). Class table in `CLASSES`. |
| `scripts/analyze_bbox.py` | One bbox → `out/<name>/summary.json` + GeoTIFFs (elevation, slope, roughness, relief, TRI). `--name` is only the output folder label; the place comes from `--bbox WEST SOUTH EAST NORTH`. |
| `scripts/filter_cells.py` | Large bbox → grid of ~15 km cells (Artemis III region size) → drops cells by land cover, water, ocean, built-up, optional population (`--pop` GHS-POP raster in EPSG:4326). Writes `cells.csv`, `cells.geojson`, `survivors.txt`. |

Tested offline with synthetic data (slope on a known plane, tile merge, missing tiles, all filters). The live AWS reads were **not** tested from the chat sandbox. One live run on the user's machine worked:
`analyze_bbox.py --bbox 83.6 28.7 84.0 29.1` (Kali Gandaki) → median slope 28.75°, only 3.7 % of area <5°, median 1 km relief 511 m → too steep as a base-site analog.

The repo also has `src/fetch_region.py`, `src/run_terrain_sites.py`, `src/run_shadow_sites.py`, `src/terrain.py` and `src/shadowsim/` written elsewhere. **Not yet reconciled with `src/dem/`** — check for duplication before adding more.

## Known gaps vs. the criteria document (to fix)
1. **Filter rules differ.** `filter_cells.py` currently *whitelists* WorldCover class 60 (bare). The plan *blacklists*: drop water (80), tree cover (10), mangroves (95), cropland (40), herbaceous wetland (90), built-up (50) **plus a 2 km buffer**; population > ~10 people/km² (GHS-POP). Keep shrub/grass/snow/moss (needed for polar analogs like Devon Island). Thresholds belong in **one config file**.
2. **Slope filter only at the base spot** (drop if base spot > ~15°). Never mask steep pixels: walls create the shadow.
3. **Grid/projection.** Plan says: reproject to local UTM (metric) and resample Earth and Moon to a **common 60 m grid** before slope/roughness. `terrain.py` currently does neither.
4. **No scoring framework yet.**

## Agreed next step: terrain scoring v1 (Polar)
Make the DEM-only Polar terrain criteria work end to end, on the 60 m UTM grid, per surviving cell:

| # | Criterion | Measure | Good is |
|---|---|---|---|
| 7 | Bowl shape | closed depression (fill − DEM), depth/width ratio | deep, closed |
| 9 | Relief | max − min within ~5 km | high (polar) |
| 10 | Flat base spot | slope at candidate base spot (~200 m pad) | low |
| 11 | Steep walls | mean slope of walls around the low point | high (~30° on Shackleton) |
| 13 | Roughness | elevation std in moving window | close to lunar target |
| 14 | Aspect | share of steep terrain facing the nearer pole | high |

Rows 10 and 11 must stay separate (one combined slope score cancels out).

Design:
- one function per criterion → score 0–1 per cell, or `None` for no data (show as "no data", never 0)
- presets of weights per base type in config; weights adjustable for the jury demo
- output: ranked table + per-site values for the radar chart
- later: plug in `shadowsim` outputs for light criteria 1–5, then Mare (16 day–night swing via MODIS LST, 23 basalt via GLiM)

Lunar target values come from LOLA 5 m site DEMs (Shackleton rim etc.) and SLDEM2015, resampled to the same 60 m grid — see the criteria document's Moon datasets table.

## Practical notes
- Windows machine; run scripts from the repo root.
- `out/` and `data/` should be in `.gitignore`.
- Bbox coordinates: bboxfinder.com gives WEST SOUTH EAST NORTH directly; west/south are negative.
