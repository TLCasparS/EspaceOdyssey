# outputs/ for the app

Written by `src/export_app.py` from 4 runs: night_polar, night_mare, meteor_crater, pinacate.
Base types: polar (1825 rows), mare (500 rows); plus 3 missed known sites.

| File | What it is |
|---|---|
| `scores.csv` | one row per ranked (Polar) / kept (Mare) cell + missed known sites: `SITE,LAT,LON`, one 0–1 column per criterion, display columns, then `RUN,CELL,BASE_TYPE,SCORE_TOTAL,RANK,NAME,COUNTRY,ROLE,TERRAIN_SCORE,LIGHT_SCORE,MISSED_REASON` |
| `raw_values.csv` | same rows, raw Earth values (units in `targets.json` → `earth_unit`), impact match, base pad |
| `targets.json` | per base type: each column's meaning, `counts`, `weight`, `score_method`, raw Moon value + unit + source |
| `heatmap.json` | `[{lat, lng, weight, base}]` per scored cell (cell centre), weight = `SCORE_TOTAL` |
| `cells.json` | cells within 16 km of a ranked/kept place (6320): `bbox`, `status`, `reason` |
| `coverage.json` | every searched cell counted per 1° tile and base type (11604 tiles): searched / filtered / prefilter / no_bowl / ice_floor / dropped / ranked (Polar) or kept (Mare) |
| `regions.json` | regions in this export: title, bbox, **role** (tuning / validation / screening), country, cell counts |

## Columns
- **0–1 criterion columns** = similarity to the Moon (1 = same). Empty = no data / no similarity yet. The meaning
  depends on `BASE_TYPE`: read it through `targets[BASE_TYPE]` (DRIVABLE is a display share for Polar and a scored
  similarity for Mare).
- **`SCORE_TOTAL`** = score vs Moon (counted criteria only); **`RANK`** = rank within the same `BASE_TYPE`.
- **`TERRAIN_SCORE` / `LIGHT_SCORE`** = the same weighted mean over the counted terrain / light criteria only.
- **`NAME`** = known site (site_info) or confirmed impact structure, else the nearest place (see Place names below). **`COUNTRY`** =
  per place, Natural Earth polygon (see Place names below).
- **`ROLE`** = tuning / validation / screening (from the region), or **missed** for known sites the pipeline does
  not rank; `MISSED_REASON` says why (Tenoumer crater, Haughton crater, Askja caldera).
- **`LAT`/`LON`** = Polar: the crater's low point; Mare: the base pad.
- **`EXCLUDED`** = config-v1.1 post-run filter reason(s); empty = not excluded (see below).
- Mare scores: similarity to the frozen mare-v1 lunar target (`targets.json` → mare).

Re-create: `python src/export_app.py out/night_polar out/night_mare out/meteor_crater out/pinacate --post-filters config/post_filters.yaml --place-names <data dir> --anchors config/site_anchors.csv --glim <data dir> --dedupe-km 1 --cells-near-km 16`

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

## Several lunar targets ("closest lunar twin")
Columns after `MISSED_REASON`: `SCORE_SHACKLETON`, `SCORE_MARE_20CELLS`, `SCORE_POLAR_SL2`, `SCORE_POLAR_HAWORTH`, `SCORE_MARE_TRANQUILLITATIS`, `SCORE_MARE_SERENITATIS`, `SCORE_MARE_IMBRIUM`, `SCORE_MARE_CRISIUM`, `BEST_TARGET`, `BEST_SCORE`. `SCORE_<TARGET>` = score vs Moon against that
target (same rule, weights and tolerances as `SCORE_TOTAL`; today's target equals `SCORE_TOTAL`); `BEST_TARGET` /
`BEST_SCORE` = best-matching target of the row's base type. Targets: `targets[BASE_TYPE].lunar_targets`
(see docs/MULTI_TARGET.md). Targets used: shackleton, mare_20cells, polar_sl2, polar_haworth, mare_tranquillitatis, mare_serenitatis, mare_imbrium, mare_crisium.
**Missing values never score better than real ones:** a `SCORE_<TARGET>` is only given when every counting
criterion has both a lunar and an Earth value; otherwise it is empty and that target cannot be `BEST_TARGET`.
`RANK` stays the rank of `SCORE_TOTAL`. The place per cell is the bowl chosen against today's target (one place per
cell in `ranking.csv`); another target might prefer a different bowl in the same cell.

| base | BEST_TARGET | places (excluded included) |
|---|---|---|
| mare | mare_20cells | 401 |
| mare | mare_crisium | 13 |
| mare | mare_imbrium | 37 |
| mare | mare_serenitatis | 20 |
| mare | mare_tranquillitatis | 29 |
| polar | polar_haworth | 805 |
| polar | polar_sl2 | 957 |
| polar | shackleton | 63 |

## Rock class (GLiM, display only; never in a score)
`raw_values.csv` columns `ROCK_CLASS`, `ROCK_CLASS_NAME`, `BASALT_SHARE_5KM`, `GLIM_COVERED_SHARE`, `BASALT_REGION`, at the Polar low point / Mare base pad (`LAT`/`LON`).
- `ROCK_CLASS` = first-level GLiM code of the grid cell under the point (`vb` = basic volcanic = basalt; names in
  `ROCK_CLASS_NAME` and `targets.json` -> `_material.classes`); empty = no data (sea or GLiM "nd").
- `BASALT_SHARE_5KM` = share of `vb` within 5 km, relative to the part of the disc that has GLiM data;
  `GLIM_COVERED_SHARE` = that part (0-1). `BASALT_REGION` = 1 if `BASALT_SHARE_5KM` >= 0.5, else 0.
  Both are **empty (no data)** when less than 50% of the disc has GLiM data: coastal grid
  cells can be sea, so coast and island places show no data, never 0.
- **Caveat:** source = Hartmann & Moosdorf (2012) GLiM v1.0 gridded to 0.5 deg, PANGAEA doi:10.1594/PANGAEA.788537 (CC-BY 3.0); cite doi:10.1029/2012GC004370. One dominant class per 0.5 deg cell (~55 km), so this is a "basalt region
  yes/no" flag, not a 5 km measurement; small lava fields vanish. GLiM has no anorthosite class (c22 cannot be
  scored). Details: docs/MATERIAL.md.

| base | BASALT_REGION | places |
|---|---|---|
| mare | 0 | 476 |
| mare | 1 | 9 |
| mare | no data | 15 |
| polar | 0 | 1645 |
| polar | 1 | 167 |
| polar | no data | 16 |

## config-v1.1: post-run filters (Polar only; config-v1 scoring unchanged)
Rules in `config/post_filters.yaml`, code `src/post_filters.py`. An excluded place keeps `SCORE_TOTAL` and its raw
values, gets **`EXCLUDED`** = reason(s) (`raw_values.csv` → `EXCLUDED_DETAIL`), has **no `RANK`** and **no heatmap point**;
its cell has status `excluded` in `cells.json`. Remaining places keep their scores; only their ranks move up.
- **`excluded: mine`**: low point inside a mining polygon of Maus et al. (2022), Global-scale mining polygons v2,
  PANGAEA https://doi.org/10.1594/PANGAEA.942325 (CC BY-SA 4.0). 44929 polygons.
- **`excluded: not a dry bowl (vegetation/ice/water)`**: `BARE_SHARE` < 0.3 or `ICE_FLOOR_SHARE` > 0.2 or `ICE_RIM_SHARE` > 0.2
  (WorldCover 2021 shares from config-v1; an empty share = no data = not tested).

| Polar places in this export | count |
|---|---|
| before the filters | 1825 |
| excluded: mine | 111 |
| excluded: not a dry bowl (vegetation/ice/water) | 476 |
| both reasons | 23 |
| excluded in total | 564 |
| ranked after the filters | 1261 |

Not excluded but within 1 km of a mining polygon (`MINE_DIST_KM`, for a manual look): 1 (ranks 390).

## Place names (offline)
`NAME` (when no known site or impact structure matches) = nearest populated place from GeoNames `cities1000`
(CC BY 4.0, https://www.geonames.org), "34 km SW of Balkhash"; among places within 1.5 × the nearest distance the
most populous is used. Beyond 60 km the Natural Earth geographic region is added, beyond 400 km only the region is
shown. `COUNTRY` = Natural Earth 1:10m Admin 0 polygon containing the point (public domain; de-facto borders as
Natural Earth draws them). Computed per place by `src/place_names.py`; no web lookup.

## Same bowl in two runs (3 rows dropped, `--dedupe-km 1`)
The region run's row is kept (tuning sites keep the values their docs quote); the night (world-grid) row is dropped,
its cell has status `duplicate` in `cells.json`. Scores differ slightly because the 60 m grid is laid on a different cell.

| dropped (run cell, score) | kept (run cell, score) |
|---|---|
| night_polar b087_r004c419, 0.4424 | meteor_crater r001c001, 0.462 |
| night_polar b084_r005c419, 0.4025 | pinacate r001c002, 0.4043 |
| night_polar b084_r006c417, 0.1784 | pinacate r002c001, 0.1783 |
