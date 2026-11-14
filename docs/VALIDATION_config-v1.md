# Validation on config-v1

Config: git tag `config-v1` (commit 9be7be9), guarded by `tests/test_config_freeze.py`. Nothing was tuned on
these regions. This file is committed **before** the runs; results are added below afterwards.

## Regions
| Run | Bbox (W S E N) | Cells |
|---|---|---|
| devon_haughton | -90.6 75.1 -88.7 75.7 | 20 |
| iceland_nw | -24.6 65.5 -19.0 66.6 | 156 |
| iceland_ne | -19.0 65.5 -13.4 66.6 | 156 |
| iceland_cw | -24.6 64.4 -19.0 65.5 | 162 |
| iceland_ce | -19.0 64.4 -13.4 65.5 | 162 |
| iceland_sw | -24.6 63.2 -19.0 64.4 | 170 |
| iceland_se | -19.0 63.2 -13.4 64.4 | 170 |

The Haughton box is centred on `config/sites.csv` (75.383 N, 89.667 W, `coords_checked = no`). Iceland is
split into 6 runs for memory reasons; together they cover the whole island.

## Predictions (written before the runs)
1. **Haughton crater (Devon Island).** Probably **fails the bowl filter.**
   - **Size:** Haughton is ~20–23 km across (from memory and `sites.csv`, unchecked), larger than one 15 km
     cell. The Earth DEM window per cell is the cell + 2 × 5.5 km buffer (~26 km), so the crater may not close
     inside it: the fill spills at the window edge, and the depression comes out too shallow or is not found.
   - **Erosion:** Haughton is heavily eroded and may no longer be a closed bowl.
2. **Askja (Iceland, Apollo training area, approx. 65.0 N, 16.7 W, unchecked).** The caldera lake is masked by
   the water filter (WorldCover water class + 200 m buffer), so the floor may not count as a usable bowl
   (base pad and usable-area rules).
   - **Success criterion:** does any cell within ~15 km of Askja get ranked, and how does its score compare
     with Meteor Crater (config-v1 score 0.462)?
3. **General.** No Iceland cell outscores Meteor Crater on c7 (bowl, Meteor 0.130 depth/width, score 0.17) and
   c11 (inner walls, Meteor 23.9°, score 0.65). Reason: Iceland's bowls are mostly volcanic and open. Report if
   this is wrong.

## Results
(added after the runs)
