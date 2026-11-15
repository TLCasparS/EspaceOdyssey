# Material: GLiM rock classes (criteria 22, 23)

Status 15 Nov 2026, branch `material-glim`. **Display and proposal only:** no score, config or export uses this yet.

## What it does
`src/pipeline/material.py` returns, for each lon/lat point:

| field | meaning |
|---|---|
| `rock_class` | first-level GLiM code of the polygon under the point; empty = no data |
| `share_<code>` | area share of each class within 5 km, relative to the **covered** part of the disc |
| `covered_share` | part of the 5 km disc that has GLiM data (0–1) |

- Sea, and GLiM's own class `nd` ("no data"), are **left out**, never counted as 0 (team rule of 14 Nov 2026). If none of the disc is covered, all shares are empty.
- Areas are measured in a local azimuthal equidistant projection centred on each point, so the disc is a true 5 km circle at every latitude, the poles included.
- Three-level GLiM codes (e.g. `vbpy`) are cut to the first level (`vb`).
- Loaders (the same algorithm runs on all of them):
  - `GridSource`: the PANGAEA 0.5° grid (used now). Each grid cell becomes a square polygon carrying its dominant class.
  - `PolygonFileSource`: the full GLiM polygons (FileGDB/GPKG/SHP). It reads one 2° tile at a time with a bbox filter, so only the area around the points is loaded. A projected layer is handled: the bbox is transformed into the layer's CRS.
  - `FrameSource`: any GeoDataFrame (used by the tests).

Scripts:
- `src/compute_rock_classes.py` → `data/material/rock_classes.csv`. Polar uses the bowl low point; Mare uses the base spot. It reads `out/night_*/ranking.csv` only.
- `src/mare_basalt_whatif.py` → a what-if table for the proposed c23 (see `docs/MATERIAL_REPORT.md`).
- Tests: `tests/test_material.py` (12 tests on synthetic polygons, a projected GPKG and a small ASCII grid).

## First-level classes (Hartmann & Moosdorf 2012)
su unconsolidated sediments · ss siliciclastic sedimentary · sm mixed sedimentary · sc carbonate sedimentary ·
py pyroclastics · ev evaporites · mt metamorphics · pa acid plutonic · pi intermediate plutonic · pb basic plutonic ·
va acid volcanic · vi intermediate volcanic · **vb basic volcanic (basalt)** · ig ice and glaciers · wb water bodies · nd no data

## Data actually used
| | |
|---|---|
| Dataset | Hartmann & Moosdorf (2012): Global Lithological Map Database v1.0 (gridded to 0.5°), PANGAEA, doi:10.1594/PANGAEA.788537 |
| Licence | CC-BY 3.0 (stated on the PANGAEA page) |
| File | `hartmann-moosdorf_2012.zip`, 38,670 bytes → `glim_wgs84_0point5deg.txt.asc` (ESRI ASCII, 720 × 360, 0.5°, NODATA −9999) + `Classnames.txt` (`Value_` → `xx` code) |
| Stored at | `%LOCALAPPDATA%\espaceodyssey_data\glim_pangaea_0p5deg\` (outside OneDrive and the repo) |
| Cite | Hartmann, J., Moosdorf, N. (2012), G3 13, Q12004, doi:10.1029/2012GC004370 |

## Limits (read before using the numbers)
1. **The 0.5° grid is NOT a 5 km measurement.** Each cell (~55 km × 55 km at the equator) has one dominant class. So "share within 5 km" is really the overlap of the disc with neighbouring 55 km cells. Most points get 1.0 for one class; only points near a cell edge get a mix. Small basalt fields (a few km, typical cinder-cone fields) disappear completely unless they dominate their cell.
2. **Coastal land counts as sea.** In the grid, a coastal cell can be NODATA, so land points on coasts and islands get "no data" or only a thin covered sliver. Examples from the night run: the Namibian and Atacama coasts, Canadian Arctic islands, and Kīlauea summit (polar #659). The what-if uses c23 = no data when less than 50 % of the disc is covered.
3. **Original GLiM scale:** average 1:3,750,000. It was compiled from 92 regional maps of very different scale and age (Hartmann & Moosdorf 2012). The polygons would be sharper than the grid but are still coarse at the 5 km level.
4. **Quaternary cover is inconsistent.** Some source maps show unconsolidated sediments (`su`) over the bedrock and others don't, so `su` versus bedrock classes partly reflects the source map, not the ground. This matters for Mare: young lava flows can be mapped as `vb`, `py` or (under thin cover) `su` depending on the country.
5. **No anorthosite.** GLiM has no anorthosite class. Anorthosite is a plutonic rock that falls inside `pi`/`pb` with other rocks at the first level. Criterion 22 (highland-type rock) **cannot** be scored from GLiM. Polar shows the rock class for display only.
6. **Points:** Polar uses the low point of the bowl and Mare the base spot. A 15 km cell can contain other rocks than the 5 km disc around that point.

## Full polygons (not downloaded, see report)
The full vector data, `LiMW_GIS 2015.gdb.zip`, is reachable via Dropbox (linked from the CSDMS and CCGM pages; link alive on 15 Nov 2026, 1,138,691,332 bytes). **It has no licence statement.** CCGM's only digital-map licence is paid, for research use only, with no redistribution, and the CC-BY of the PANGAEA grid does not obviously cover it. So it was not downloaded. To use it once the team clears the licence:

```
python src/compute_rock_classes.py --gdb "<path>\LiMW_GIS 2015.gdb" --layer <layer> --field xx
```

The layer name and the class field are **not verified**. The code assumes a field with first-level (or three-level) codes, default `xx`, as in the grid's `Classnames.txt`. Check with `pyogrio.list_layers(path)` and `pyogrio.read_info(path, layer)`.
