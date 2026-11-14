# dem — Copernicus DEM, WorldCover land cover + terrain metrics

Reads Copernicus DEM GLO-30 / GLO-90 and ESA WorldCover 2021 directly from the public AWS
buckets (no account needed) and computes slope, roughness, local relief and TRI, which can be
compared with lunar DEMs (LOLA).

## Setup
```bash
pip install -r requirements.txt          # or: conda env create -f environment.yml
```

## Step 1 — filter a large area (land cover + population)
```bash
python scripts/filter_cells.py --bbox 82 27 86 31 --name nepal_west
# optional population grid (GHS-POP, WGS84 version) and polar classes:
python scripts/filter_cells.py --bbox 82 27 86 31 --name nepal_west --pop data/GHS_POP_4326_30ss.tif --keep-classes 60 70 100
```
Cuts the area into 15 km cells and drops cells with too little bare ground (ESA WorldCover class 60),
built-up area, water/wetland, ocean, or (with `--pop`) more than 5 people/km2. All thresholds are flags
(`--min-usable`, `--max-built`, `--max-water`, `--max-pop`, `--cell-km`).
Writes `out/<name>/cells.csv`, `cells.geojson` (open in QGIS / geojson.io) and `survivors.txt`
(one `analyze_bbox.py` command per kept cell).

## Step 2 — terrain analysis per cell (from repo root)
```bash
python scripts/analyze_bbox.py --bbox 83.6 28.7 84.0 29.1 --name mustang
python scripts/analyze_bbox.py --bbox 83 28 85 30 --res 90 --name mustang_wide --no-tifs
```
Writes `out/<name>/summary.json` plus GeoTIFFs (elevation, slope_deg, roughness_m, relief_m, tri_m)
that open in QGIS.

## Site scores (metric grid, one row per named site)

`src/fetch_region.py` + `src/terrain.py` are a second way to get terrain metrics, used for
the named candidate sites in `data/sites.csv`:

| | `dem` package + `scripts/` | `src/fetch_region.py` + `src/terrain.py` |
|---|---|---|
| Data | DEM (AWS), WorldCover (AWS) | DEM + WorldCover, Planetary Computer (AWS fallback) |
| Grid | native lon/lat, pixel size converted to metres | reprojected to UTM, square metric pixels |
| Metrics | slope, roughness (5x5), relief (1 km), TRI | slope, true-north aspect, relief (5 km), roughness (3x3), TRI |
| Output | `out/<name>/` (CSV, GeoJSON, JSON, GeoTIFFs) | one row per site in `data/results/scores.csv` |
| Run | `python scripts/filter_cells.py ...`, `python scripts/analyze_bbox.py ...` | `python src/run_terrain_sites.py --only <site>` |

Shared code: `fetch_region` uses `dem.fetch.tiles_for_bbox` and `dem.landcover.worldcover_tiles`
for the AWS tiles, and `terrain.compute_terrain` uses `dem.terrain.tri`.

## In Python
The package lives in `src/`, so put that folder on the path first:
```python
import sys; sys.path.insert(0, "src")
from dem import read_bbox, read_landcover, pixel_size_m, summarize

elev, profile = read_bbox(83.6, 28.7, 84.0, 29.1, res=30)   # west, south, east, north
dx, dy = pixel_size_m(profile["transform"], center_lat=28.9)
summary, layers = summarize(elev, dx, dy)
print(summary["slope_deg"]["median"], summary["frac_slope_lt_5deg"])

classes, transform = read_landcover(83.6, 28.7, 84.0, 29.1, res_m=100)  # WorldCover codes
```

## Notes
- `res=90` is ~9x less data: use it to screen large regions, then 30 m to zoom in.
- Elevation is a surface model (includes vegetation/buildings), heights above EGM2008 geoid.
- Ocean tiles and a few countries' tiles don't exist; they come back as NaN (DEM) or class 0
  (WorldCover) with a warning. Network errors are retried and then raised, never treated as ocean.
- `out/` is in `.gitignore`.
