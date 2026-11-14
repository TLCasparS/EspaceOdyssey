# outputs/ for the app

Written by `src/export_app.py` from: meteor_crater, pinacate. Base type: polar.
Re-create with `python src/export_app.py out/meteor_crater out/pinacate` (site names need
`--sites-info` / `--sites-coords`, default `app/sample/site_info.json` and `app/sample/scores.csv` from Sofia's app).
Known sites matched this time: Meteor Crater.

| File | What it is |
|---|---|
| `scores.csv` | one row per ranked cell: `SITE,LAT,LON`, one 0–1 column per criterion, then `RUN,CELL,BASE_TYPE,SCORE_TOTAL,RANK` |
| `raw_values.csv` | same rows, raw Earth values (units in `targets.json` → `earth_unit`) plus depth, diameter, base pad, dark days |
| `targets.json` | per base type: each criterion's column, `counts`, `weight`, `score_method`, raw Moon value + unit + source |
| `heatmap.json` | `[{lat, lng, weight}]`, one point per ranked cell at the **cell centre**, weight = `SCORE_TOTAL` |
| `cells.json` | every searched cell of these runs (25): centre, `bbox` [W,S,E,N], `status` (ranked / no_bowl / filtered / dropped) + `reason`, for drawing the searched area |

**Why bowl-less cells are not in the heatmap with weight 0:** a weighted heatmap adds up the weights, so a
point with weight 0 adds nothing and would be invisible. To show where we searched and found nothing, draw
`cells.json` (e.g. faint outlines for `no_bowl` / `filtered`) under the heatmap instead.
Status counts here: ranked 3, no_bowl 17, filtered 5, dropped 0.

## How to read the numbers
- **A 0–1 value in `scores.csv` is already the similarity to the Moon**: exp(−((Earth − Moon) / tolerance)²),
  1 = same as the Moon. Do not compare it with a target again.
- **Empty = no data** or no similarity yet. Never 0.
- **`SCORE_TOTAL`** = score vs Moon: weighted mean of the criteria with `counts: true` only
  (SUNNY_RIDGE, DARK_FLOOR, LIGHT_NEAR_DARK, BOWL_SHAPE, SLOPE_BASE, STEEP_WALLS, ROUGHNESS). Comparable across runs. **`RANK`** = rank of `SCORE_TOTAL` over all rows in this file.
- **`LAT`/`LON`** = the crater's low point (centre of the bowl), for the 3D view. The base pad is in `raw_values.csv`.
- **`SITE`** = a known site from `site_info.json` when its (approximate) point lies inside the cell, else `<run> <cell>`.

## Which criteria count
- **Counted (target, weight > 0):** SUNNY_RIDGE, DARK_FLOOR, LIGHT_NEAR_DARK, BOWL_SHAPE, SLOPE_BASE, STEEP_WALLS, ROUGHNESS
- **Display only (similarity shown, weight 0):** GRAZING_SUN, SKY_VIEW, RELIEF, ASPECT
- **Rank-scored, no lunar value yet** (empty in `scores.csv`, raw value in `raw_values.csv`):
  none (every scored criterion has a lunar value).
- **Not computed by the pipeline yet:** CRATER_SIZE, DRIVABLE
- Only the polar base type exists so far; `cave` and `mare` have no targets yet.

## No Earth analog possible: GRAZING_SUN
No Earth analog possible: the Sun's highest elevation is purely a matter of latitude. On Earth it is at least 23.4 deg (at the poles, from the axial tilt); at Shackleton it is 1.9 deg (1.5 deg at the lunar pole). Shown for information, weight 0. (`targets.json` → `fact`.)

## Known limitation: Sun disc vs Sun centre (SUNNY_RIDGE, DARK_FLOOR, LIGHT_NEAR_DARK)
Known limitation: on the Moon 'lit' is the visible fraction of the solar DISC (PGDA AVGVISIB, extended Sun); on Earth it is the Sun's CENTRE above the horizon (point Sun). Both give 0.5 on flat land at the pole; on terrain they can differ where the Sun stays partly hidden for long stretches (disc fraction > 0 while the centre is already below the horizon). The same text is in `targets.json` (`limitation`) for these three criteria.
