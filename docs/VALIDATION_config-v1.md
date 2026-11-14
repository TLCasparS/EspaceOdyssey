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

## Results (14 Nov 2026, after the runs; config-v1 unchanged)
Runs: 9.2 min in total (Haughton 21 s; Iceland parts 50–130 s each); no errors.

### Cells per region
| Run | Searched | Filtered | No bowl | Ice floor | Ranked |
|---|---|---|---|---|---|
| devon_haughton | 20 | 7 | 13 | 0 | **0** |
| iceland_nw | 156 | 107 | 49 | 0 | 0 |
| iceland_ne | 156 | 94 | 62 | 0 | 0 |
| iceland_cw | 162 | 81 | 81 | 0 | 0 |
| iceland_ce | 162 | 36 | 125 | 1 | 0 |
| iceland_sw | 170 | 130 | 39 | 0 | **1** |
| iceland_se | 170 | 118 | 49 | 3 | 0 |
| **Iceland total** | 976 | 566 | 405 | 4 | **1** |

### Prediction 1, Haughton: not found. Outcome as predicted; the reason was different
- The two cells nearest the `sites.csv` point (7.2 and 9.6 km) pass the land-cover filter but have **no
  closed depression at all** that meets the size limits.
- Diagnosis (`src/diagnose_bowls.py`, per-cell windows): **0 closed depressions ≥ 20 m deep** in the whole
  box.
- Extra check with the **whole 65 × 67 km box in one window** (to rule out the window limit): **0 closed
  depressions ≥ 10 m**. Relief within 12 km of the point is only 34–368 m.
- **Conclusion:** the window-size limit was *not* what stopped Haughton. The terrain has no closed bowl that
  the DEM can see, which fits strong erosion. The window limit for craters > ~20 km is still real (see the
  criteria doc) but did not decide this case. Unchecked: whether the `sites.csv` point is exactly on the crater.

### Prediction 2, Askja: no cell within 15 km ranked. Outcome as predicted; the mechanism was different
- The three cells within 15 km (4.5, 10.7, 14.4 km) pass the land-cover filter (usable 92–99 %, water
  1–5 %): **the water filter was not what stopped Askja.**
- With the whole area in one window there is one large depression 5.6 km from the point: 13.2 km², **48 m
  spill depth**, 4.1 km equivalent width, elongation 1.26. 85 % of it is perfectly flat at its lowest level:
  the DEM's flattened lake surface (probably the caldera lake, unchecked). The depth is measured from the
  **water surface**, not the lake bottom, and is **below the 50 m minimum**.
- Side finding: the per-cell diagnosis does not list this depression although its own window sees it
  (47.6 m). Likely because on a flat lake the "low point" is an arbitrary lake pixel and can fall into a
  neighbouring cell (not confirmed). The pipeline's `find_depressions` has the same behaviour. Not changed
  (config-v1).
- Score comparison with Meteor Crater: not possible, nothing was ranked near Askja.

### Prediction 3: no Iceland cell outscores Meteor Crater on c7 / c11. Holds (but on 1 cell)
Only **one** Iceland cell was ranked at all: iceland_sw r006c016, low point 64.101 N, 19.427 W (164 km from
Askja; what it is was not checked).

| | Iceland r006c016 | Meteor Crater |
|---|---|---|
| Total score vs Moon | 0.225 | 0.462 |
| c7 depth/width | 0.037 [0.00] | 0.130 [0.17] |
| c11 inner walls | 5.7° [0.00] | 23.9° [0.65] |
| c1 / c2 / c3 | 1.13 [0.31] / 0.43 [0.28] / 2.09 [0.00] | 1.03 [0.17] / 0.28 [0.12] / 0.75 [1.00] |
| depth / width | 64.6 m / 1.73 km | 146.5 m / 1.13 km |

Links: [low point](https://earth.google.com/web/@64.10097,-19.42690,2410a,0d,35y,0h,0t,0r) ·
[base pad](https://earth.google.com/web/@64.10880,-19.40429,2462a,0d,35y,0h,0t,0r)

### Honest summary
config-v1 finds **no analog in either validation region**: Haughton is not seen as a bowl at all (eroded), and
Iceland gives one shallow, wide bowl with score 0.225. Two limits of the method show up:
1. It only sees **closed** bowls in the DEM. Eroded craters and lakes count by their spill depth from the
   water surface.
2. The **50 m spill-depth minimum** removes caldera lakes (Askja 48 m) and filled craters (Tenoumer 44 m).

Both are documented; neither was changed (config-v1 frozen). Candidates for config-v2: window limit for large
craters, flat-lake low point, spill depth vs rim-crest depth for the bowl filter.
