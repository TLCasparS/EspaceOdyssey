# App changes for the real pipeline data (for Sofia)

14 Nov 2026 · from Caspar's pipeline side. Line numbers refer to `app/app.js` on branch `sofia/app`
(commit 3436bca). Nothing in the app has been changed; this is the list of what it needs.

## What changed in the data
`src/export_app.py` writes `outputs/` (see `outputs/README.md`):

- **`scores.csv`** is in your format (`SITE,LAT,LON` + your column names). The difference is the meaning:
  **each 0–1 value is already the similarity to the Moon** (1 = same as the Moon). Empty = no data.
- **`targets.json`** has no 0–1 target values any more. Per base type it lists each criterion with `counts`,
  `weight`, `score_method` and the **raw** Moon value + unit + source.
- **New files:**
  - `raw_values.csv`: raw Earth values, for the card.
  - `heatmap.json`: real scores.
  - `cells.json`: every searched cell with its status, to show the searched area.
- **`LAT/LON`** = the crater's low point, for the 3D view.

## Changes in `app.js`
1. **Data paths** (lines 6–11):
   - `scores: '../outputs/scores.csv'`, `targets: '../outputs/targets.json'`.
   - Add `raw: '../outputs/raw_values.csv'`, `heatmap: '../outputs/heatmap.json'`, `cells: '../outputs/cells.json'` and load them in `loadAll()` (lines 88–100).
   - Set `isFake: false`.
2. **CSV parser** (line 81): only `SITE` stays text, so `RUN`, `CELL` and `BASE_TYPE` become `NaN`. Treat those three as text too.
3. **New `targets.json` format** (lines 97, 104, 107):
   - `targets.polar.criteria` is a list of `{column, counts, weight, score_method, moon: {value, unit, source}, earth_unit}`. Build a lookup by `column`.
   - `similarityCriteria()` = criteria with `counts: true`, instead of `target()[c.key] != null`.
4. **Match = the score directly** (`closeness`, lines 108–114): drop `1 − |s − t|`. The filters compare the score with the threshold directly.
5. **Total score** (`scoreSite`, lines 117–126): use `SCORE_TOTAL` (weighted mean of the counted criteria, already computed) instead of 1 − mean difference.
6. **Ranking** (`ranked`, lines 139–144): sort by `SCORE_TOTAL` (or use `RANK`).
7. **Radar** (lines 261–271, polygon at line 298):
   - The Moon polygon = **1.0 on every axis** (Moon = perfect similarity); the site polygon = the scores.
   - Display-only axes (`score_method: display`) are best drawn greyed out.
   - Axes with `score_method: rank` have no similarity yet: label them "awaiting lunar value" instead of "no data".
8. **Card chips** (lines 312–314, 360, 365):
   - Sort by score: high = "closest to the Moon", low (e.g. < 0.5) = "what it lacks".
   - Chip text: **raw Earth vs raw Moon with unit**, from `raw_values.csv` and `targets.json` (`moon.value`, `earth_unit`), e.g. "Steep walls 23.9° vs 27.2°".
   - "too little / too much" = the sign of raw Earth − raw Moon.
9. **"No data yet"** (line 315): separate three cases. Empty with `score_method: rank` = no lunar value yet; `not computed` = no pipeline value yet (CRATER_SIZE, DRIVABLE); otherwise no data.
10. **Card header** (lines 327–328): `pct(SCORE_TOTAL)` as "similarity to the Moon", "rank `RANK` of N".
11. **Heatmap** (lines 388–412): replace `fakeHeatPoints()` with `heatmap.json` and remove the "Fake pattern" note. With few ranked cells the heatmap is sparse.
12. **Searched area:** optionally draw `cells.json` under the heatmap (for example faint outlines for `no_bowl` and `filtered`). It shows where we searched and found no bowl.
13. **Criteria texts** (lines 25–53):
    - RELIEF hint "height range within ~5 km" → "rim-to-floor depth" (the definition changed).
    - Mark RELIEF, SKY_VIEW and ASPECT as display only.
14. **Base types:** `targets.json` only has `polar` for now. `renderFilters()` already hides Lava tube and Mare when they have no target, so nothing to change there.

## Notes
- **Site names:** a known site from your `site_info.json` keeps its name when its point (from your `sample/scores.csv`) lies inside a cell, e.g. "Meteor Crater". Other cells are named `<run> <cell>`. Sites without a pipeline cell (Haughton, Atacama, …) are not in `outputs/scores.csv`.
- **Light criteria c1–c4** (SUNNY_RIDGE, DARK_FLOOR, LIGHT_NEAR_DARK, GRAZING_SUN) now have lunar values and similarity scores (since 14 Nov, Mateo's `lunar_light.py`).

## Card text for the light criteria (known limitation, accepted by the team)
For SUNNY_RIDGE, DARK_FLOOR and LIGHT_NEAR_DARK, `targets.json` has a `limitation` field. Please show a short version on the card, e.g. as a footnote under the light chips or radar:

> Light on the Moon is measured as the visible part of the Sun's disc (NASA PGDA illumination map); on Earth as the Sun's centre above the horizon. On flat ground at the pole both agree; on crater rims and floors they can differ a little.

Suggested short label for a tooltip: "Moon: Sun disc · Earth: Sun centre".
