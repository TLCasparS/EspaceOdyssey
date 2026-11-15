# outputs/ for the app

Written by `src/export_app.py` from 2 runs: night_polar, night_mare.
Base types: polar (1825 rows), mare (500 rows); plus 3 missed known sites.

| File | What it is |
|---|---|
| `scores.csv` | one row per ranked (Polar) / kept (Mare) cell + missed known sites: `SITE,LAT,LON`, one 0–1 column per criterion, display columns, then `RUN,CELL,BASE_TYPE,SCORE_TOTAL,RANK,NAME,COUNTRY,ROLE,TERRAIN_SCORE,LIGHT_SCORE,MISSED_REASON` |
| `raw_values.csv` | same rows, raw Earth values (units in `targets.json` → `earth_unit`), impact match, base pad |
| `targets.json` | per base type: each column's meaning, `counts`, `weight`, `score_method`, raw Moon value + unit + source |
| `heatmap.json` | `[{lat, lng, weight, base}]` per scored cell (cell centre), weight = `SCORE_TOTAL` |
| `cells.json` | cells within 50 km of a ranked/kept place (33909): `bbox`, `status`, `reason` |
| `coverage.json` | every searched cell counted per 1° tile and base type (11604 tiles): searched / filtered / prefilter / no_bowl / ice_floor / dropped / ranked (Polar) or kept (Mare) |
| `regions.json` | regions in this export: title, bbox, **role** (tuning / validation / screening), country, cell counts |

## Columns
- **0–1 criterion columns** = similarity to the Moon (1 = same). Empty = no data / no similarity yet. The meaning
  depends on `BASE_TYPE`: read it through `targets[BASE_TYPE]` (DRIVABLE is a display share for Polar and a scored
  similarity for Mare).
- **`SCORE_TOTAL`** = score vs Moon (counted criteria only); **`RANK`** = rank within the same `BASE_TYPE`.
- **`TERRAIN_SCORE` / `LIGHT_SCORE`** = the same weighted mean over the counted terrain / light criteria only.
- **`NAME`** = known site (site_info) or confirmed impact structure, else `<region title> <cell>`. **`COUNTRY`** =
  region level (approximate, from the region registry, no per-cell lookup).
- **`ROLE`** = tuning / validation / screening (from the region), or **missed** for known sites the pipeline does
  not rank; `MISSED_REASON` says why (Tenoumer crater, Haughton crater, Askja caldera).
- **`LAT`/`LON`** = Polar: the crater's low point; Mare: the base pad.
- Mare scores stay **empty** until the lunar Mare targets (Mateo) are verified; raw values are already there.

## Display-only columns (Polar, weight 0, never in SCORE_TOTAL)
- **DRIVABLE** (more is better): share of pixels flatter than display.drivable_slope_deg within display.drivable_radius_km of the base pad
- **BARE** (more is better): share of WorldCover bare/sparse (class 60) in floor + rim zone
- **GROUND_ICE** (more is better): share of WorldCover snow & ice in the floor zone
- **IMPACT_CRATER** (fact): 1 = low point lies within max(0.6 x diameter, 1 km) of a confirmed impact structure in data/impact/impact_structures.csv (Wikipedia list, incomplete), 0 = not in that list
- **CRATER_SIZE** (raw only): size-dependent: diameter and depth in raw_values.csv (CRATER_DIAMETER_EQUIV_M, CRATER_RIM_TO_FLOOR_M); no 0-1 value
- Impact list: 88 confirmed structures (incomplete; "0" = not in this list).

## No Earth analog possible: GRAZING_SUN (Polar)
No Earth analog possible: the Sun's highest elevation is purely a matter of latitude. On Earth it is at least 23.4 deg (at the poles, from the axial tilt); at Shackleton it is 1.9 deg (1.5 deg at the lunar pole). Shown for information, weight 0.

## Known limitation: Sun disc vs Sun centre (SUNNY_RIDGE, DARK_FLOOR, LIGHT_NEAR_DARK)
Known limitation: on the Moon 'lit' is the visible fraction of the solar DISC (PGDA AVGVISIB, extended Sun); on Earth it is the Sun's CENTRE above the horizon (point Sun). Both give 0.5 on flat land at the pole; on terrain they can differ where the Sun stays partly hidden for long stretches (disc fraction > 0 while the centre is already below the horizon).
