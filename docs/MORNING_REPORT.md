# Morning report, Sun 15 Nov 2026 (unattended session, ~07:40–09:30)

Branch `main` only. No new night run: everything comes from the stored raw records
(`%LOCALAPPDATA%\espaceodyssey_night\raw`). config-v1 and mare-v1 scoring untouched (freeze tests pass).

## What was done
1. **Rescore from raw**: `night_run.py --score --tracks A,B2`. The new `out/night_polar` and `out/night_mare`
   are byte-identical to the stored ones (ranking.csv, radar.json, cells.geojson compared), so the stored results are
   reproducible. Backup of the old folders: `%LOCALAPPDATA%\espaceodyssey_data\backup_out_20261115`.
2. **config-v1.1 post-run filters** (`config/post_filters.yaml`, `src/post_filters.py`, decision row in `CLAUDE.md`):
   - *excluded: mine*: the place's low point lies inside a mining polygon of **Maus et al. (2022), Global-scale mining
     polygons v2**, PANGAEA, https://doi.org/10.1594/PANGAEA.942325 (44,929 polygons, CC BY-SA 4.0, 24.7 MB).
   - *excluded: not a dry bowl (vegetation/ice/water)*: BARE_SHARE < 0.3 or ICE_FLOOR_SHARE > 0.2 or ICE_RIM_SHARE > 0.2.
     An empty share (no data) is not tested.
   - An excluded place keeps SCORE_TOTAL and raw values, gets `EXCLUDED` (+ `EXCLUDED_DETAIL`, `MINE_DIST_KM` in
     raw_values.csv), has no RANK, no heatmap point; its cell has status `excluded` in cells.json.
3. **Export into `outputs/`** (replaces the 14 Nov five-site export): night_polar + night_mare + meteor_crater + pinacate.
   - Offline names (`src/place_names.py`): NAME like "54 km SW of Bardaï" from GeoNames cities1000 (CC BY 4.0),
     COUNTRY per place from Natural Earth admin-0 polygons (public domain), Natural Earth region names for remote places.
     Known sites and impact structures keep their names.
   - `config/site_anchors.csv` keeps the app cards (site_info.json) for Al Wahbah, Roter Kamm and both Pinacate craters.
   - Same bowl in two runs (Meteor Crater, 2 × Pinacate): exported once, the region run's row is kept (3 night rows dropped).
   - cells.json only within 16 km of a ranked/kept place (own cell + neighbours): 2.2 MB instead of 12 MB.
   - Command (also in `docs/NIGHT_RUN.md` and `outputs/README.md`):
     `python src/export_app.py out/night_polar out/night_mare out/meteor_crater out/pinacate --post-filters config/post_filters.yaml --place-names %LOCALAPPDATA%/espaceodyssey_data --anchors config/site_anchors.csv --dedupe-km 1 --cells-near-km 16`
4. **App fixes needed for the night export** (`app/app.js`, `app/index.html`). Without them the export does not display
   correctly:
   - The app ranked all rows together, so Mare rows (~0.99) would have topped the Polar list. Now it shows only rows of
     the selected base type, with a heatmap per base type.
   - `NAME` / `EXCLUDED` were parsed as numbers (NaN). They are now text columns.
   - Excluded places: not ranked, not on the globe, listed in a folded "Excluded after scoring" box (best 40), card with
     badge and reason.
   - The night runs are no longer drawn as one region outline around the whole globe.
   - Empty favicon, so the browser logs no 404.
5. **Self-check**: `pytest` 134 passed, 1 skipped (after `git pull --rebase` onto the GLiM merge). App served with
   `python -m http.server`, loaded in headless Chrome over DevTools: **no console errors, no exceptions, no failed
   requests** (only three.js deprecation warnings from the globe library). Checked: Polar list 1,261 rows, Mare switch
   500 rows, excluded card, 3D terrain view (5,820 cells), guide panel. New top 10: no place flagged as mine.

## Filter counts (Polar, 1,825 places after the 3 duplicates are dropped)
| | places |
|---|---|
| excluded: mine | 111 |
| excluded: not a dry bowl | 476 |
| both reasons | 23 |
| **excluded in total** | **564** |
| **ranked after the filters** | **1,261** |

68 of the old top 100 are excluded. Mare: no filter applied (not asked); 0 of the 500 Mare places lie in a mining polygon.

## Old top 25 (night export 02:43): what the filters did
Mine names: the mining polygons carry no names. "OSM" = named features within 1.5 km in OpenStreetMap (Overpass API, queried
this morning); "suspected" = the name you remembered.

| old rank | place (new NAME) | result | mine name (source) |
|---|---|---|---|
| 1 | 16 km N of Balqash, Kazakhstan | **mine** (29.3 km² polygon) | Kounrad, OSM "Қоңырат карьері" (Kounrad quarry): confirmed |
| 2 | Patagonia (73 km W of El Chaltén), Chile | not dry (bare 0.16, ice floor 0.30, ice rim 0.41) | |
| 3 | Ellesmere Island, Canada | not dry (ice rim 0.24) | |
| 4 | Patagonia (102 km NW of El Chaltén), Chile | not dry (bare 0.06, ice floor 0.29) | |
| 5 | Tian Shan (118 km SW of Xinyuan), China | kept → **new #1** | |
| 6 | 34 km SW of Vallenar, Chile | **mine** | OSM "Mina El Algarrobo" (not on your list) |
| 7 | 31 km N of Vallenar, Chile | **mine** | OSM "Mina Los Colorados" (not on your list) |
| 8 | 9 km NW of Clifton, USA | **mine** | Morenci, OSM "Morenci Open Pit": confirmed |
| 9 | 15 km E of Torata, Peru | **mine** (40.9 km² polygon) | Cuajone suspected; position fits, but OSM has no named feature within 1.5 km: not confirmed by name |
| 10 | Patagonia (60 km W of Puerto Natales), Chile | not dry (ice rim 0.31) | |
| 11 | near Bagdad, USA | **mine** | Bagdad, OSM "Bagdad Open Pit Mine": confirmed |
| 12 | 80 km SW of Yabēlo, Ethiopia | not dry (bare 0.02) | |
| 13 | 47 km SE of Battle Mountain, USA | **mine** | Nevada gold, OSM "Cortez Open Pit Mine": confirmed |
| 14 | Wellington Island, Chile | not dry (bare 0.17, ice rim 0.38) | |
| 15 | 11 km SW of Rŭshon (Afghanistan per Natural Earth; the town is across the border in Tajikistan) | kept → new #2 | |
| 16 | Atacama Desert (151 km SE of Antofagasta), Chile | **mine** (231.7 km² polygon) | Escondida, OSM "Mina Escondida" (+ Zaldívar): confirmed |
| 17 | 47 km NW of Wanaka, New Zealand | not dry (ice rim 0.57) | |
| 18 | Libyan Desert (80 km E of Kuraymah), Sudan | kept → new #3 | |
| 19 | 17 km N of Ovacık, Turkey | kept → new #4 | |
| 20 | 19 km N of Calama, Chile | **mine** | Chuquicamata, OSM "Mina Chuquicamata": confirmed |
| 21 | Danakil Desert (63 km S of Edd), Eritrea | kept → new #5 | |
| 22 | 20 km NE of Mēga, Ethiopia | not dry (bare 0.00) | |
| 23 | 12 km NW of Carlin, USA | **mine** (42.5 km² polygon) | Nevada gold suspected; OSM has one unnamed mine feature: not confirmed by name |
| 24 | Tibetan Plateau (96 km SE of Huatugou), China | kept → new #6 | |
| 25 | 23 km SE of Gawanē, Ethiopia | not dry (bare 0.00) | |

So 10 of the top 25 are mines (all 7 you suspected are hit, plus El Algarrobo and Los Colorados), 9 are not dry bowls,
6 stay. Just below the top 25, #26 (Great Basin, 72 km N of Tonopah, Nevada), #27 (6 km SW of Tierra Amarilla, Chile)
and #30 (5 km SW of Mammoth, Arizona; also not dry) are mine hits too. I did not check their mine names.

## New top 15 Polar (config-v1.1)
Google Earth links open on the low point. TERRAIN / LIGHT = the two part scores. "bowl" = equivalent diameter / spill depth.

| # | place | country | score | terrain | light | bowl | bare | link |
|---|---|---|---|---|---|---|---|---|
| 1 | Tian Shan (118 km SW of Xinyuan) | China | 0.603 | 0.676 | 0.505 | 2.9 km / 92 m | 0.38 | [42.57203, 82.3905](https://earth.google.com/web/@42.57203,82.3905,0a,6000d,35y,0h,45t,0r) |
| 2 | 11 km SW of Rŭshon | Afghanistan | 0.542 | 0.794 | 0.206 | 1.5 km / 221 m | 0.58 | [37.87297, 71.46668](https://earth.google.com/web/@37.87297,71.46668,0a,6000d,35y,0h,45t,0r) |
| 3 | Libyan Desert (80 km E of Kuraymah) | Sudan | 0.526 | 0.806 | 0.153 | 1.0 km / 269 m | 1.00 | [18.40855, 32.59257](https://earth.google.com/web/@18.40855,32.59257,0a,6000d,35y,0h,45t,0r) |
| 4 | 17 km N of Ovacık | Turkey | 0.506 | 0.685 | 0.266 | 1.1 km / 133 m | 0.86 | [39.50009, 39.14865](https://earth.google.com/web/@39.50009,39.14865,0a,6000d,35y,0h,45t,0r) |
| 5 | Danakil Desert (63 km S of Edd) | Eritrea | 0.501 | 0.775 | 0.135 | 1.1 km / 179 m | 0.85 | [13.36733, 41.69556](https://earth.google.com/web/@13.36733,41.69556,0a,6000d,35y,0h,45t,0r) |
| 6 | Tibetan Plateau (96 km SE of Huatugou) | China | 0.493 | 0.615 | 0.330 | 1.1 km / 92 m | 0.92 | [37.51138, 91.41632](https://earth.google.com/web/@37.51138,91.41632,0a,6000d,35y,0h,45t,0r) |
| 7 | 54 km SW of Bardaï (Tibesti) | Chad | 0.480 | 0.711 | 0.172 | 1.4 km / 349 m | 1.00 | [21.02585, 16.61421](https://earth.google.com/web/@21.02585,16.61421,0a,6000d,35y,0h,45t,0r) |
| 8 | 49 km SW of Wuqia | China | 0.480 | 0.649 | 0.254 | 2.5 km / 199 m | 0.79 | [39.47356, 74.7809](https://earth.google.com/web/@39.47356,74.7809,0a,6000d,35y,0h,45t,0r) |
| 9 | 30 km SW of Chongos Alto | Peru | 0.467 | 0.679 | 0.184 | 1.0 km / 82 m | 0.31 | [-12.43626, -75.53765](https://earth.google.com/web/@-12.43626,-75.53765,0a,6000d,35y,0h,45t,0r) |
| 10 | Meteor Crater (tuning site) | USA | 0.462 | 0.486 | 0.430 | 1.1 km / 146 m | 0.53 | [35.02724, -111.02202](https://earth.google.com/web/@35.02724,-111.02202,0a,6000d,35y,0h,45t,0r) |
| 11 | 39 km NE of Khuzdar | Pakistan | 0.459 | 0.418 | 0.513 | 2.0 km / 139 m | 1.00 | [27.98151, 66.95306](https://earth.google.com/web/@27.98151,66.95306,0a,6000d,35y,0h,45t,0r) |
| 12 | 48 km SE of Khuzdar | Pakistan | 0.457 | 0.581 | 0.292 | 2.6 km / 86 m | 0.83 | [27.47937, 66.92793](https://earth.google.com/web/@27.47937,66.92793,0a,6000d,35y,0h,45t,0r) |
| 13 | Altiplano (83 km SE of San Pedro de Atacama) | Chile | 0.429 | 0.251 | 0.666 | 8.7 km / 125 m | 0.98 | [-23.49878, -67.69708](https://earth.google.com/web/@-23.49878,-67.69708,0a,6000d,35y,0h,45t,0r) |
| 14 | Himalayas (63 km NW of Seppa) | India | 0.426 | 0.377 | 0.492 | 1.4 km / 655 m | 0.39 | [27.79554, 92.62913](https://earth.google.com/web/@27.79554,92.62913,0a,6000d,35y,0h,45t,0r) |
| 15 | 52 km SE of Camargo | Bolivia | 0.420 | 0.370 | 0.487 | 1.0 km / 173 m | 0.33 | [-21.03516, -64.94364](https://earth.google.com/web/@-21.03516,-64.94364,0a,6000d,35y,0h,45t,0r) |

OSM cross-check of the new top 25 (quarry / mine / mineshaft / landfill / `resource` tags within 2 km): **nothing for 24 of 25.** The one hit is Meteor Crater (#10): a single OSM `man_made=mineshaft`
(presumably the historic Barringer exploration shaft). It is not in the Maus polygons, so it is not excluded; it's a known
tuning site anyway. OSM is incomplete, so "no tag" does not prove "no mine".

## New top 10 Mare (mare-v1, no filter)
| # | place | country | score | link |
|---|---|---|---|---|
| 1 | Ahag (156 km NE of Tamanghasset) | Algeria | 0.9961 | [24.06448, 6.15605](https://earth.google.com/web/@24.06448,6.15605,0a,6000d,35y,0h,45t,0r) |
| 2 | Gobi Desert (247 km E of Hami) | China | 0.9956 | [42.44285, 96.4795](https://earth.google.com/web/@42.44285,96.4795,0a,6000d,35y,0h,45t,0r) |
| 3 | 22 km E of Luxor | Egypt | 0.9953 | [25.75945, 32.85181](https://earth.google.com/web/@25.75945,32.85181,0a,6000d,35y,0h,45t,0r) |
| 4 | Mongolian Plateau (132 km S of Dalandzadgad) | Mongolia | 0.9948 | [42.43539, 103.97241](https://earth.google.com/web/@42.43539,103.97241,0a,6000d,35y,0h,45t,0r) |
| 5 | 44 km E of Messaad | Algeria | 0.9945 | [34.18606, 3.9763](https://earth.google.com/web/@34.18606,3.9763,0a,6000d,35y,0h,45t,0r) |
| 6 | Bathurst Island | Canada | 0.9944 | [75.01226, -98.67431](https://earth.google.com/web/@75.01226,-98.67431,0a,6000d,35y,0h,45t,0r) |
| 7 | 71 km W of Aqaba | Egypt | 0.9943 | [29.47912, 34.27989](https://earth.google.com/web/@29.47912,34.27989,0a,6000d,35y,0h,45t,0r) |
| 8 | Gobi Desert (290 km N of Jiuquan) | China | 0.9940 | [42.33664, 98.17262](https://earth.google.com/web/@42.33664,98.17262,0a,6000d,35y,0h,45t,0r) |
| 9 | 67 km W of Zhob | Pakistan | 0.9939 | [31.15638, 68.77623](https://earth.google.com/web/@31.15638,68.77623,0a,6000d,35y,0h,45t,0r) |
| 10 | 27 km NW of Uis | Namibia | 0.9938 | [-21.0055, 14.74398](https://earth.google.com/web/@-21.0055,14.74398,0a,6000d,35y,0h,45t,0r) |

"Ahag" is Natural Earth's own (abbreviated) label for that region, presumably the Ahaggar; I did not rename it.

## Meteor Crater 0.442 (night) vs 0.462 (VALIDATION_config-v1.md)
Confirmed: cell/grid alignment. It is the same bowl (low points 20 m apart) in a different cell (world grid
`b087_r004c419` vs region cell `r001c001`), so the 60 m UTM grid is laid differently. The −0.020 comes mostly from c11
inner walls (23.9° → 23.5°, −0.011 on the total) and c3 light near dark (0.754 → 0.674, −0.006). The export keeps the
region run's 0.462 (dedupe, see below).

## Skipped, and why
- **No second mining dataset** (e.g. Tang & Werner 2023, or OSM `landuse=quarry` as a filter). Maus v2 hit all 7 suspected
  mines; OSM was used only as a cross-check, not as a filter.
- **Overpass/OSM** was only used for the cross-check above (coordinates only, no personal data).
- **No coverage drawing in the app**: coverage.json is exported but the app still doesn't read it (as before). The night
  runs' searched area shows only as cells in the 3D view.
- **The new top places were not checked in imagery.** Use the Google Earth links.
- Downloads (all open licence, no login, far below 3 GB), in `%LOCALAPPDATA%\espaceodyssey_data`: Maus v2 gpkg 24.7 MB,
  Natural Earth admin-0 4.9 MB + geography regions 2.0 MB, GeoNames cities1000 11.1 MB. No pip installs needed.
- Not touched: `docs/PITCH_OUTLINE.md`, `docs/JURY_FAQ.md`, `docs/ai_usage/task6.md`, the GLiM worktree and the merged
  GLiM files, config-v1 / mare-v1 scoring.

## Please decide
1. **Second-best bowl in an excluded cell.** The filter works per exported place, i.e. the cell's best place. If that
   place is a mine, the cell drops out even when it has another, natural bowl (raw records keep all candidates). Option:
   filter candidates inside `night_run.py --score` before picking the best. Not done: bigger change, and it changes
   which place represents a cell.
2. **Duplicates**: Meteor Crater and the two Pinacate craters come from their region runs (Meteor 0.462, rank 10), not
   from the night grid (0.442). Fine for you, or should the night row win (one grid for all)?
3. **`outputs/night_export/`** (the uncleaned 02:43 export, 7 tracked files + an untracked 12 MB cells.json) is still
   in the repo. The app doesn't read it. Delete it?
4. **Near a mine**: new #9 (Peru, 30 km SW of Chongos Alto) is 1.65 km from a mining polygon, outside the 1 km info
   radius. Only one ranked place is within 1 km (rank 390). Have a look at #9.
5. **Licence**: Maus v2 is CC BY-SA 4.0 (ShareAlike). The exported `EXCLUDED` flags are derived from it; attribution is in
   `outputs/README.md` and `config/post_filters.yaml`. Please check this is OK for the submission's licence.
6. **Mare scores barely separate**: the top 10 Mare are all 0.994–0.996 (many flat bare plains match the mare-v1
   target almost perfectly). Not changed (mare-v1 frozen), but worth one sentence in the pitch.
7. **Top Polar places are mostly mountain bowls** (Tian Shan, Pamir, Tibet, Himalaya), some with bare share just
   above 0.3 (#9 0.31, #14 0.39, #15 0.33). Cirques or seasonal lakes may remain; a quick visual check of the top 15
   would help before the pitch.
8. Al Wahbah now ranks 484 (0.273, night grid) and Roter Kamm 619 (0.241); their app cards still work (anchors).

## Git
Commits on `main` (explicit paths): post-filters + names + tests; app fixes; new outputs; docs (this report,
CLAUDE.md decision row, NIGHT_RUN.md command, ai_usage note). Rebased onto the GLiM merge (`git pull --rebase origin
main`), tests re-run (green). **Not pushed:** `git push origin main` hung with no output (most likely at the GitHub
sign-in) and was stopped after 90 s. The commits are local on `main`. To publish, run `git push origin main` yourself
(GitHub Pages then republishes from `main` within a few minutes).
