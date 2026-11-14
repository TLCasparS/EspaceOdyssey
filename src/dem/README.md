# dem — Copernicus DEM + terrain metrics

Reads Copernicus DEM GLO-30 / GLO-90 directly from the public AWS buckets (no account needed)
and computes slope, roughness, local relief and TRI, which can be compared with lunar DEMs (LOLA).

## Two ways to get terrain metrics

| | `dem` package (this folder) | `src/fetch_region.py` + `src/terrain.py` |
|---|---|---|
| Data | DEM only, AWS | DEM + ESA WorldCover 2021, Planetary Computer (AWS fallback) |
| Grid | native lon/lat, pixel size converted to metres | reprojected to UTM, square metric pixels |
| Metrics | slope, roughness (5x5), relief (1 km), TRI | slope, true-north aspect, relief (5 km), roughness (3x3), TRI |
| Output | `out/<name>/summary.json` + GeoTIFFs for QGIS | one row per site in `data/results/scores.csv` |
| Run | `python scripts/analyze_bbox.py --bbox ...` | `python src/run_terrain_sites.py --only <site>` |

Shared code: `fetch_region` uses `dem.fetch.tiles_for_bbox` for the AWS tiles, and
`terrain.compute_terrain` uses `dem.terrain.tri`.

## Setup
```bash
pip install -r requirements.txt          # or: conda env create -f environment.yml
```

## Command line (from repo root)
```bash
python scripts/analyze_bbox.py --bbox 83.6 28.7 84.0 29.1 --name mustang
python scripts/analyze_bbox.py --bbox 83 28 85 30 --res 90 --name mustang_wide --no-tifs
```
Writes `out/<name>/summary.json` plus GeoTIFFs (elevation, slope_deg, roughness_m, relief_m, tri_m)
that open in QGIS.

## In Python
The package lives in `src/`, so put that folder on the path first:
```python
import sys; sys.path.insert(0, "src")
from dem import read_bbox, pixel_size_m, summarize

elev, profile = read_bbox(83.6, 28.7, 84.0, 29.1, res=30)   # west, south, east, north
dx, dy = pixel_size_m(profile["transform"], center_lat=28.9)
summary, layers = summarize(elev, dx, dy)
print(summary["slope_deg"]["median"], summary["frac_slope_lt_5deg"])
```

## Notes
- `res=90` is ~9x less data: use it to screen large regions, then 30 m to zoom in.
- Elevation is a surface model (includes vegetation/buildings), heights above EGM2008 geoid.
- Ocean tiles and a few countries' tiles don't exist; they come back as NaN with a warning.
- `out/` is in `.gitignore`.
