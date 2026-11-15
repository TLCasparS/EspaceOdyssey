# mare-v1.1: c30 small-crater density + fair Mare twins

Branch `mare-v1.1` (15 Nov 2026, Claude Code for Caspar). `mare-v1` stays the frozen reference.

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
