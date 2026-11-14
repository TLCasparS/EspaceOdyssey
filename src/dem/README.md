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
python src/filter_cells.py --bbox 82 27 86 31 --name nepal_west
# optional population grid (GHS-POP, WGS84 version) and polar classes:
python src/filter_cells.py --bbox 82 27 86 31 --name nepal_west --pop data/GHS_POP_4326_30ss.tif
```
Cuts the area into 15 km cells. Masks blacklisted WorldCover classes (tree, crop, built-up, water,
wetland, mangrove), 2 km around built-up and 200 m around water/wetland; drops a cell if too little
of it is usable, if its largest usable patch is too small, if it is ocean, or (with `--pop`) if it is
populated. No slope filter. All thresholds are in `config/pipeline.yaml` (section `filter`).
Writes `out/<name>/cells.csv`, `cells.geojson` (open in QGIS / geojson.io), `usable_mask.tif` and `survivors.txt`
(one `analyze_bbox.py` command per kept cell).

## Polar pipeline, one command (filter -> terrain criteria -> ranking)
```bash
python src/run_pipeline.py --bbox 83 28 85 30 --name mustang_polar          # GLO-30, ~2 min
python src/run_pipeline.py --bbox 83 28 85 30 --name mustang_polar --res 90
```
Land-cover filter (above), then per surviving cell on a local-UTM 60 m grid the Polar terrain criteria
7, 9, 10, 11, 13, 14 (`src/pipeline/polar.py`), scored and weighted per `config/pipeline.yaml`.
Writes `out/<name>/ranking.csv`, `cells.geojson` (all cells, for the map), `radar.json` (0-1 score per
criterion per ranked cell, lunar target placeholders) and `run_info.json`. Rank-based scores are only
comparable within one run until lunar target values (LOLA) are filled in.

## Quick look — terrain summary for one bbox (from repo root)
```bash
python src/analyze_bbox.py --bbox 83.6 28.7 84.0 29.1 --name mustang
python src/analyze_bbox.py --bbox 83 28 85 30 --res 90 --name mustang_wide --no-tifs
```
Writes `out/<name>/summary.json` plus GeoTIFFs (elevation, slope_deg, roughness_m, relief_m, tri_m)
that open in QGIS.

## Site scores (metric grid, one row per named site)

`src/fetch_region.py` + `src/terrain.py` are a second way to get terrain metrics, used for
the named candidate sites in `config/sites.csv`:

| | `dem` package + `src/filter_cells.py`, `src/analyze_bbox.py` | `src/fetch_region.py` + `src/terrain.py` |
|---|---|---|
| Data | DEM (AWS), WorldCover (AWS) | DEM + WorldCover, Planetary Computer (AWS fallback) |
| Grid | native lon/lat, pixel size converted to metres | reprojected to UTM, square metric pixels |
| Metrics | slope, roughness (5x5), relief (1 km), TRI | slope, true-north aspect, relief (5 km), roughness (3x3), TRI |
| Output | `out/<name>/` (CSV, GeoJSON, JSON, GeoTIFFs) | one row per site in `data/results/scores.csv` |
| Run | `python src/filter_cells.py ...`, `python src/analyze_bbox.py ...` | `python src/run_terrain_sites.py --only <site>` |

Shared code: `fetch_region` uses `dem.fetch.tiles_for_bbox`, `dem.landcover.worldcover_tiles` and `dem.landcover.CLASSES`.
The metric-grid code lives in `dem/grid.py` (`to_metric_grid`) and `dem/terrain.py` (`compute_terrain`); `src/terrain.py` only re-exports them.

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
