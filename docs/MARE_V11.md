# Mare display additions: c30 small-crater density + fair Mare twins

Branch `mare-v1.1` (15 Nov 2026, Claude Code for Caspar).

**Team decision (15 Nov 2026): there is no mare-v1.1.** The mare-v1 score is unchanged (`SCORE_TOTAL`, `RANK`).
Display additions: (1) c30 small-crater density, weight 0, display only, never scored; (2) common-tolerance Mare twins
(changes `BEST_TARGET` / `SCORE_<mare target>` only). Code names with "v11" (`mare_v11:` config section,
`pipeline/mare_v11.py`, `--mare-v11`, this file's name) are historical: they mean these display additions, not a new
scoring version. The prediction and run sections below keep their original wording ("mare-v1.1") as written at the time.

**Validation outcome (Lanzarote): 0 of 16 cells kept by the frozen filter.** The threshold-0 run is a diagnostic only.

**Known limitation:** the Copernicus DEM stores the sea as flat 0 m, not as no data. In coastal Mare cells whose 5 km
zone reaches the sea, c13 roughness (median) can become 0 (seen in 2 Lanzarote diagnostic cells), and c9 / c12 are
also affected. Not fixed in mare-v1 (frozen); a fix (mask WorldCover water in the Mare zone) would mean mare-v2.

## Lanzarote prediction (written BEFORE the run, committed separately)

Lanzarote is the held-out Mare **validation** site. Nothing was tuned there, and no Lanzarote result had been looked
at when this was written.

- Run: `python src/run_pipeline.py --base mare --mare-v11 --bbox -13.95 28.82 -13.40 29.25 --name lanzarote_mare_v11`
  (bbox from memory, not checked against a map; it covers the island, with sea around it).
- Comparison set ("comparable places"): the 500 places of the night run's B2 Mare shortlist (`out/mare_v11/places.csv`),
  scored with the same config. Their mare-v1 scores: 10th percentile 0.901, median 0.971, max 0.996.
- **Prediction:**
  1. Few cells survive the filter (sea, the 2 km built-up buffer around Arrecife and the resorts): 1 to 4 kept cells.
  2. Lanzarote does **not** rank high: its best cell scores **0.6 to 0.9** (mare-v1 and mare-v1.1, same with c30
     weight 0), i.e. below the B2 10th percentile, about the bottom 10 % if it were inserted into the 500.
     Reason: a young volcanic island with cinder cones (Timanfaya) and rough lava fields: c9 relief within 5 km well
     above the lunar 154 m, c13 roughness above the lunar 1.69 m, c12 drivable share lower than the Moon's 0.99.
  3. c30 > 0 in at least one cell (volcanic craters on cones count as closed depressions), possibly inside the lunar
     range 0.09 to 0.42 per km2. That would be volcanic craters, not impact craters: display only.
  4. BEST_TARGET (common tolerance): one of the higher-relief targets (20-cell median, Crisium or Tranquillitatis).
- What would count as "ranks high": best cell at or above the B2 median (0.971).

## Lanzarote result (after the run)

`python src/run_pipeline.py --base mare --mare-v11 --bbox -13.95 28.82 -13.40 29.25 --name lanzarote_mare_v11`

**Validation answer: Lanzarote does not rank high. It does not rank at all.** The frozen hard filter keeps
**0 of 16** cells: no cell reaches `min_usable` 0.5. The best cell (r001c001, 70 % bare, probably Timanfaya) has 32 %
usable land. The rest is lost to sea and to the 2 km buffer around the island's scattered villages and resorts.

Diagnostic only, NOT the validation result: the same code with `filter.min_usable` set to 0 in memory (config file
unchanged), output in `out/lanzarote_mare_v11_diag_min_usable0/`:

| cell | usable | score (v1.1 = v1) | would rank in B2 (of 501) | c9 m | c10 deg | c12 | c13 m | c30 /km2 | BEST_TARGET |
|---|---|---|---|---|---|---|---|---|---|
| r001c000 | 0.08 | 0.651 | 487 | 366 | 0.53 | 0.967 | 1.94 | 0 | Crisium (0.830) |
| r001c002 | 0.03 | 0.575 | 490 | 422 | 0.57 | 0.964 | 2.06 | 0.013 | Crisium (0.730) |
| r002c002 | 0.04 | 0.500 | 497 | 277 | 0.73 | 0.990 | 0.00 ⚠ | 0.013 | Crisium (0.602) |
| r001c001 | 0.32 | 0.347 | 499 | 429 | 0.35 | 0.887 | 2.69 | 0.025 | Crisium (0.519) |
| r000c001 | 0.05 | 0.017 | 501 | 547 | 4.28 | 0.884 | 0.00 ⚠ | 0 | Serenitatis (0.050) |

Prediction against result:
1. "1 to 4 kept cells": **wrong**, 0 kept. The filter excludes the island before any scoring.
2. "Best cell 0.6 to 0.9, bottom ~10 %": **right** in the diagnostic (best 0.651, rank 487 of 501, bottom 3 %).
   The reason matches the prediction: relief 277–547 m against the lunar 154 m.
3. "c30 > 0 in at least one cell, possibly in the lunar range": **half right**. c30 > 0 in 3 cells, but at most
   0.025 per km2, far below the lunar minimum of 0.089.
4. "BEST_TARGET a higher-relief target": **right**. Crisium (c9 286 m) in 4 of 5 cells.

⚠ Known limitation (see top): c13 = 0.00 in two coastal cells. Their 5 km zone reaches the sea, which the Copernicus DEM
stores as flat 0 m, not as no data, so the median roughness becomes 0. This affects only coastal Mare cells.
Candidate fix for mare-v2: mask WorldCover water in the Mare zone.

What this says about the method: Lanzarote is a basalt (composition) analog. Our Mare criteria are terrain only,
and the filter wants 15 km cells of open, unbuilt land, so an inhabited volcanic island cannot qualify. That
result is honest, not a failure of the code, but it should be said in the pitch: our Mare analogs are big, flat,
empty plains, not volcanic ones.

## 1. c30 small-crater density

**Definition** (`pipeline.mare.small_crater_density`, one function for Earth AND Moon): count closed depressions
≥ 10 m deep (filled depth), ≥ 300 m wide (equivalent diameter of the filled area) and with elongation ≤ 2 whose low
point lies within 5 km of the base spot, then divide by the data-covered area of the 5 km disc (per km2). It runs on
the 60 m grid and reuses the Polar `find_depressions`, with these limits instead of the bowl limits. The window is
cut to 5 + 1.5 km around the base spot, so Earth and Moon see the same geometry. If less than half of the disc has
data, the result is None (no data, never 0). Parameters are in `config/pipeline.yaml` → `mare_v11.c30`.
Known behaviour: the priority-flood fill merges a pit inside a larger closed depression into that one depression.

**Earth:** the 500 B2 places, from the stored crops (`%LOCALAPPDATA%\espaceodyssey_night\crops\B2`), with the base
spot from the stored base_lon/base_lat. Check per place: the base-pad slope recomputed on the crop must match the
stored c10. All 500 crops are present and pass, so no place has missing c30. Script: `src/mare_v11_rescore.py`;
output `out/mare_v11/` (git-ignored).

**Moon:** the 20 cells of the frozen mare target, using the SLDEM2015 512 ppd tiles (MIT archive, Mateo's source) and
the same `compute_mare_target.load_cell_grid` resampling. Script: `src/compute_mare_c30.py`.
Result: **median 0.236 per km2, IQR 0.121, range 0.089–0.420** (7 to 33 pits per 5 km zone). It is stored as
`lunar_targets.json → mare.criteria.c30_small_craters` with `verified: false` and
**"computed by Claude Code, to be checked by Mateo"**. Per-mare medians are in the candidates file (Tranquillitatis
0.306, Serenitatis 0.216, Imbrium 0.229, Crisium 0.127).
⚠ Reproduction check: on this machine `mare_cell` gives values slightly different from the frozen per-cell values
(c10 up to 0.03°, c9 a few m). serenitatis_04 is the exception: c9 is 188 m instead of 126 m, so the base spot moved.
The code is unchanged since Mateo's run and the source is the same, so the cause is probably GDAL / library
versions in the reprojection (not verified). The differences are stored per cell (`repro_diff`). For Mateo: please
rerun `python src/compute_mare_c30.py` on your Mac and compare.

**Earth vs Moon:**

| c30 per km2 | Earth (500 B2 places) | Moon (20 cells) |
|---|---|---|
| exactly 0 | 392 | 0 |
| 0–0.05 | 62 | 0 |
| 0.05–0.10 | 27 | 1 |
| 0.10–0.15 | 10 | 4 |
| 0.15–0.20 | 7 | 3 |
| 0.20–0.25 | 1 | 4 |
| 0.25–0.30 | 1 | 4 |
| 0.30–0.45 | 0 | 4 |

The distributions **overlap, but only in their tails**: 28 Earth places reach the lunar minimum (0.089), 9 reach the
lunar Q1 (0.146) and 1 reaches the lunar median. The high Earth values come from sand seas, judged by location
(Namib Sand Sea, Grand Erg Oriental, Nafud, Gran Desierto, Kumtag, Badain Jaran, Registan, Taklamakan; from
geography, not checked against a dune map). On Earth, c30 mostly measures **interdune hollows, not impact craters**.

## 2. Fair Mare twins (common tolerance)

With mare-v1, each Mare target is scored with its own tolerance, max(IQR, floor). The 20-cell target spans four maria,
so its c9 tolerance is 163 m. A single mare has 42 m (Imbrium) to 116 m (Crisium). A forgiving target gives higher
scores to everyone, so BEST_TARGET mostly picked the **widest** target, not the **closest** one: 401 of 500 went to
the 20-cell median. The display addition (`mare_v11.common_tolerance: true`, `pipeline.mare_v11.v11_targets`) scores every
Mare target with the 20-cell median's tolerance per criterion. BEST_TARGET then compares closeness to the lunar
values only. The per-mare IQRs come from only 5 cells each, so they are rough anyway.
SCORE_TOTAL does not change: it is always scored against the 20-cell target with its own tolerance.

## 3. c30 weight and tolerance (decided 15 Nov 2026: display only)

**Decision: c30 display only (`mare_v11.c30_weight: 0`)**, tolerance = max(IQR 0.121, floor 0.0127). The floor is
1 pit per 5 km zone, the counting resolution. Why weight 0:
- 78 % of the Earth shortlist has c30 = 0 and scores exp(−(0.236/0.121)²) ≈ 0.02 on it. Counting c30 would push
  almost every total down by ~0.2 and mostly separate places by sand-sea hollows.
- What-if at weight 1.0 (equal to the other four): the whole top 20 becomes sand-sea places that ranked 26 to 444
  under mare-v1, and Crisium (the mare with the fewest pits) wins 160 BEST_TARGETs. c30 would decide the twin.
- If the team still wants c30 counted, first find a way to tell craters from dune hollows (e.g. exclude WorldCover
  sand / dune areas, or require a raised rim).

**Mare top 20, before (mare-v1) and after (with the display additions, c30 weight 0).** The ranks are identical for
all 500 places, because with weight 0 c30 never enters the score. The table also shows the what-if at weight 1.0.
The recomputed mare-v1 scores match the stored night-run scores (max difference 0.0001, rounding).

| # | place | lat | lon | score v1 = v1.1 | c30 | what-if w=1: score (rank) | BEST v1 | BEST v1.1 |
|---|---|---|---|---|---|---|---|---|
| 1 | b077_r003c1261 | 24.064 | 6.156 | 0.9961 | 0 | 0.801 (33) | 20 cells | 20 cells |
| 2 | b094_r003c1513 | 42.443 | 96.480 | 0.9956 | 0 | 0.801 (34) | 20 cells | 20 cells |
| 3 | b079_r000c1422 | 25.759 | 32.852 | 0.9953 | 0 | 0.801 (35) | 20 cells | 20 cells |
| 4 | b094_r003c1554 | 42.435 | 103.972 | 0.9948 | 0 | 0.800 (36) | 20 cells | 20 cells |
| 5 | b086_r006c1129 | 34.186 | 3.976 | 0.9945 | 0 | 0.800 (37) | 20 cells | 20 cells |
| 6 | b124_r003c155 | 75.012 | -98.674 | 0.9944 | 0 | 0.800 (38) | 20 cells | 20 cells |
| 7 | b082_r003c1384 | 29.479 | 34.280 | 0.9943 | 0 | 0.800 (39) | 20 cells | 20 cells |
| 8 | b094_r002c1525 | 42.337 | 98.173 | 0.9940 | 0 | 0.800 (41) | 20 cells | 20 cells |
| 9 | b083_r007c1581 | 31.156 | 68.776 | 0.9939 | 0 | 0.800 (43) | 20 cells | 20 cells |
| 10 | b035_r007c1349 | -21.006 | 14.744 | 0.9938 | 0 | 0.800 (44) | 20 cells | 20 cells |
| 11 | b080_r005c1586 | 27.622 | 61.136 | 0.9936 | 0 | 0.799 (45) | 20 cells | 20 cells |
| 12 | b083_r002c1491 | 30.438 | 52.984 | 0.9933 | 0 | 0.799 (46) | 20 cells | 20 cells |
| 13 | b093_r000c1550 | 41.054 | 96.834 | 0.9931 | 0 | 0.799 (47) | 20 cells | 20 cells |
| 14 | b083_r001c1375 | 30.225 | 34.623 | 0.9930 | 0 | 0.799 (48) | 20 cells | 20 cells |
| 15 | b096_r003c1527 | 44.657 | 109.384 | 0.9925 | 0 | 0.799 (52) | 20 cells | 20 cells |
| 16 | b093_r004c1593 | 41.575 | 106.947 | 0.9924 | 0 | 0.799 (51) | 20 cells | 20 cells |
| 17 | b094_r001c1496 | 42.165 | 92.326 | 0.9924 | 0 | 0.798 (53) | 20 cells | 20 cells |
| 18 | b084_r005c1362 | 31.939 | 36.300 | 0.9923 | 0 | 0.798 (55) | 20 cells | 20 cells |
| 19 | b094_r002c1577 | 42.340 | 107.685 | 0.9923 | 0 | 0.798 (56) | 20 cells | 20 cells |
| 20 | b076_r001c1337 | 22.672 | 15.315 | 0.9922 | 0 | 0.798 (54) | 20 cells | 20 cells |

What-if top 5 at weight 1.0: Namib Sand Sea (−25.83, 15.70; mare-v1 rank 292), Gran Desierto (31.93, −114.25; 294),
Nafud (29.24, 39.35; 296), Grand Erg Oriental (31.16, 8.07; 370), Kumtag (40.11, 92.62; 402). The full list is in
`out/mare_v11/places.csv` (`rank_v11_w`).

**BEST_TARGET counts (500 B2 places):**

| target | before (mare-v1, own tolerances) | after (common tolerance, c30 w=0) | what-if c30 w=1.0 |
|---|---|---|---|
| 20-cell median | 401 | 280 | 184 |
| Imbrium | 37 | 110 | 108 |
| Tranquillitatis | 29 | 56 | 0 |
| Serenitatis | 20 | 41 | 48 |
| Crisium | 13 | 13 | 160 |

## 5. Scope note

**c30 re-ranks the 500-place shortlist that mare-v1 chose (night run B1 → B2); it is not a new global search.** A place
that mare-v1's coarse B1 pass did not select was never given a c30 value. With the proposed weight 0, nothing is
re-ranked: c30 is a display value next to the mare-v1 score.

## Files

- `src/pipeline/mare.py`: `small_crater_density` (c30), `C30`
- `src/pipeline/mare_v11.py`: `v11_criteria`, `v11_targets` (common tolerance)
- `src/compute_mare_c30.py`: lunar c30 (20 cells + per mare) → `config/lunar_targets.json`, `config/lunar_targets_candidates.json`
- `src/mare_v11_rescore.py`: Earth c30 on the B2 crops, before/after scores → `out/mare_v11/`
- `src/pipeline/run_mare.py`, `src/run_pipeline.py`: `--base mare --mare-v11`
- `config/pipeline.yaml` → `mare_v11:` (the frozen `mare:` section is unchanged)
- `tests/test_mare_c30.py` (synthetic plains with and without pits, size/shape/distance limits, no data, common
  tolerance); `tests/test_mare_freeze.py` still guards the four mare-v1 criteria exactly
- `outputs/` on main: **not changed**. The mare-v1 export is unaffected: `build_targets` gives identical targets
  with the new candidates file.
