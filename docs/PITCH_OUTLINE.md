## Agent report: Task 6 Pitch outline and jury FAQ
Status: done (open points below need the team)
What I did:
- Read the night guide, `CLAUDE.md`, the criteria doc, `docs/VALIDATION_config-v1.md`, `docs/NIGHT_RUN.md`,
  `docs/FACT_CHECK.md`, `docs/SUBMISSION_DRAFT.md` / `SUBMISSION_CHECKLIST.md`, `docs/NEW_TARGETS_REPORT.md`.
- Checked the night-run numbers given by the team against `outputs/night_export/` (export of 15 Nov, 02:43).
  They match: 264,896 Polar cells searched, 1,825 Polar places ranked, 500 Mare places, impact-list matches
  Meteor Crater, Roter Kamm, New Quebec/Pingualuit.
- Computed a few extra figures from the same export (method stated next to each number, table at the end).
- Wrote a **7-slide** outline (not 8–10 as the guide says: the Space Apps rule is max 7 slides incl. title,
  `docs/SUBMISSION_CHECKLIST.md` item 4.1) plus 3 backup slides for questions, a 30-second summary and the jury FAQ.
Files changed / created: `docs/PITCH_OUTLINE.md`, `docs/JURY_FAQ.md`, `docs/ai_usage/task6.md` (nothing committed)
Tests: not run (no code changed; a test run was stopped on request)
Open points / needs a human decision:
1. **Mine filter: not in the repo.** No file or commit on any branch mentions mines or open pits. Add the file /
   commit name and how many places it removed (`[TEAM: mine filter]` placeholders). All numbers below come from
   the 02:43 export, which is probably **before** the filter: re-check the top-20 lists after filtering.
2. **"Best light at high latitudes" is a tendency, not a rule.** Top 50 by light have median |latitude| 39.8°
   vs 30.1° for the top 50 by terrain. But the single best light place (27.81 N, 92.51 E) is a deep Himalayan
   bowl, and 4 of the 8 darkest floors are in the Himalaya/Tibet. Suggested wording: "light-like analogs sit
   further from the equator and in deep mountain bowls". Its 1,553 m spill depth could be a DEM artefact
   (a similar 775 m depression at 28.47 N, 84.01 E is already flagged UNVERIFIED in `docs/PIPELINE_polar_v1.md`).
3. **Meteor Crater score changed:** 0.462 (region run, validation doc) → 0.442 (night export, rank 45 of 1,825).
   Iceland cell 0.225 → 0.221. Reason not checked (probably a shifted world grid). Use the night-export numbers on
   slides and say "night run".
4. **Mare scores barely separate places** (median 0.971, 44 of 500 ≥ 0.99). Also a Mare cell on **Devon Island**
   (a Polar validation region) is in the Mare list (0.99, rank 41). Decide whether to show it.
5. Pitch length for the local pitch (Sun 15 Nov, 17:30) is not in the repo: `[TEAM]`.
Unverified items (and why): whether the top terrain cells are open-pit mines (needs imagery, not checked);
Atacama / Arizona attribution of top cells is from coordinates only (−28.3 / −70.8, 33.10 / −109.37,
34.58 / −113.21), no place-name lookup.
Data downloaded (size): none.

---

# Pitch outline: Earth Twins of the Moon

Source key: **[NX]** = `outputs/night_export/` (night run, `scores.csv`, `raw_values.csv`, `coverage.json`);
**[VAL]** = `docs/VALIDATION_config-v1.md`; **[CRIT]** = `docs/Moon Analog Criteria and Datasets.md`;
**[FC]** = `docs/FACT_CHECK.md`; **[TGT]** = `config/lunar_targets.json`; **[CL]** = `CLAUDE.md` decisions table.
Before using any external fact (crater sizes, training history), apply the corrections in [FC].

## 30-second summary
> Which places on Earth come closest to a lunar base site, and how close? We measured Shackleton crater at the
> lunar south pole from NASA's LOLA elevation and illumination data, then ran the *same code* over Earth: about
> 265,000 grid cells of 15 km, from open Copernicus and ESA data. 1,825 crater-like places were ranked against
> Shackleton, 500 flat plains against the lunar maria. From elevation data alone the method found real impact
> craters such as Meteor Crater, Roter Kamm and Pingualuit, and it was so good at closed bowls that it found
> open-pit mines too, so we filter them. The honest result: no place on Earth has the Moon's grazing Sun, and
> the places that look like Shackleton are not the places that are lit like it.

## Key messages (one line each, with evidence)
1. **Same ruler for both worlds.** Earth and Moon are measured by the same functions on the same 60 m metric grid
   ([CL] 14 Nov; [CRIT] footnote 1). Score per criterion `exp(−((earth − moon)/tolerance)²)`, 1 = same as the Moon.
2. **It finds real craters from elevation alone.** The bowl detector knows nothing about impacts; afterwards
   3 ranked places match the confirmed-impact list: Meteor Crater, Roter Kamm, New Quebec/Pingualuit [NX,
   `IMPACT_CRATER = 1`]. The list has 88 structures and is incomplete (`outputs/night_export/README.md`).
3. **It finds every closed bowl, including mines** → mine filter `[TEAM: mine filter, file/commit, places removed]`.
4. **No place on Earth has the Moon's grazing Sun.** At Shackleton the Sun climbs at most 1.9° (1.5° at the pole);
   on Earth never less than 23.4° ([CRIT] c4). Lowest among our 1,825 places: 31.8° (81.6 N) [NX `GRAZING_SUN` raw].
   Consequence: Shackleton's floor is in shadow 100 % (target 1.0, [TGT]); the median Earth floor 16.5 % [NX raw
   `DARK_FLOOR`]; only 2 of 1,825 places reach ≥ 90 %.
5. **Terrain twins and light twins are different places.** Of the top 50 by terrain and the top 50 by light only
   5 are the same; rank correlation 0.06 over all 1,825 [NX, computed]. Best terrain: Atacama region and Arizona
   (`[TEAM: after mine filter]`); best light: further from the equator (median |lat| 39.8° vs 30.1°) and deep
   mountain bowls.
6. **Honest validation.** Settings frozen (tag `config-v1`) before validation; Haughton and Askja were missed, and
   we know why [VAL]. Tenoumer is missed for the same reason as Askja.

## Slides (7 for the submission; Space Apps limit incl. title)

### 1. Title
- "Earth Twins of the Moon", tagline: *Which places on Earth come closest to a lunar base site, and how close?*
- Team name EspaceOdyssey, challenge name, `[TEAM: full names]` (required on the slides, checklist 4.3).
- Visual: the two linked globes from the app (real screenshot, no AI images, checklist 5.3).

### 2. Problem
- Analog sites (Haughton, Meteor Crater, Iceland) are chosen by eye and poorly characterised (challenge brief, [CL]).
- Question: how Moon-like is a place, criterion by criterion, and where does the analogy break?
- Target: **Shackleton** rim + floor at the lunar south pole (Artemis region area, ~15 × 15 km cells,
  NASA 2022 release [FC]).

### 3. Method: one ruler, two worlds
- Moon: LOLA `LDEM_80S_20MPP_ADJ` (20 m → 60 m) + PGDA illumination map; crater found from the data.
  Shackleton measured: rim crest 20.9 km, rim-to-floor 4,077 m, wall 27.2° (scored ring), base pad 0.66° [TGT,
  CRIT]; agrees with Zuber et al. 2012 [FC].
- Earth: Copernicus DEM GLO-30 + ESA WorldCover, filters (water, trees, crops, towns + 2 km), bowl filter
  (closed, ≥ 50 m deep, ≥ 1 km wide, elongation ≤ 2), year-long Sun simulation for light [CL].
- 7 counting criteria: sunny ridge, dark floor, light next to dark, bowl shape, flat base, steep walls, roughness.
- Visual: funnel (slide 4 numbers) or the "same function → Earth / Moon" diagram.

### 4. The night run (scale)
- **264,896 cells of 15 km searched** in one night [NX `coverage.json`, 11,604 1° tiles of 19,433 land tiles:
  deserts first, not the whole planet, `docs/NIGHT_RUN.md`].
- Funnel [NX]: 11,932 out at the coarse land-cover prescreen → 202,422 no bowl at 90 m → 41,699 removed by land
  cover / water / towns → 6,909 no bowl at 30 m → 109 ice-filled floor → **1,825 ranked against Shackleton**.
- **500 Mare places** ranked against the median of 20 lunar mare cells (SLDEM2015) [NX; CL mare-v1].
- Impact craters recognised automatically: **Meteor Crater, Roter Kamm, Pingualuit** [NX].

### 5. What we found
- **No grazing Sun on Earth** (message 4): the one criterion no place can match; shown, not scored.
- **Terrain ≠ light** (message 5): scatter plot of TERRAIN_SCORE vs LIGHT_SCORE for 1,825 places; it is a cloud
  (rank correlation 0.06). Two map pins: best terrain twin, best light twin `[TEAM: pick after mine filter]`.
- **Mines**: the detector finds open pits as perfect closed bowls → mine filter `[TEAM: before/after count]`.
- Known craters for scale (night run [NX]): Meteor Crater 0.44 (rank 45, tuning site, not independent),
  Al Wahbah 0.27, Roter Kamm 0.24, Pingualuit 0.20. Top overall 0.69 `[TEAM: after mine filter]`.

### 6. Honest limits and validation
- Frozen before validation (`config-v1`, test-guarded) [CL].
- **Haughton (Devon Island): missed.** Not the window limit: even one 65 × 67 km window has no closed depression
  ≥ 10 m; the crater is too eroded for the DEM to see a bowl [VAL].
- **Askja (Iceland): missed.** Not the water filter: the caldera lake is a flat surface in the DEM, so depth is
  measured from the water, 48 m < 50 m minimum [VAL].
- **Tenoumer (Mauritania): missed**, 44 m spill depth, floor filled with sediment [CRIT; FC #6].
- Other limits: bowls < 1 km not resolved at 60 m; craters > ~20 km don't close in the Earth window; Sun disc
  (Moon) vs Sun centre (Earth) [CRIT].
- The app shows the misses on purpose (`ROLE = missed`).

### 7. Next steps + links
- config-v2: larger window for big craters, lake low point, rim-crest depth, open-bowl mode for cirques [VAL, CRIT].
- More lunar targets: 10 Artemis-region Polar candidates + 4 per-mare targets computed, waiting for review
  (`verified: false`, `docs/NEW_TARGETS_REPORT.md`); multi-target scoring is built (`docs/MULTI_TARGET.md`).
- Lava tubes (Cave base type), remaining tiles of the world.
- App link, repo link, AI-use line `[TEAM]`.

## Backup slides (only for questions, not in the submitted deck)
- **B1 Criteria table** with Shackleton values, tolerances and weights ([TGT], `config/pipeline.yaml`).
- **B2 Validation table** (cells per region, predictions written before the runs) [VAL].
- **B3 Light limitation**: Sun disc vs Sun centre, Earth Sun elevation formula `90° − max(0, |lat| − 23.4°)`.

## Numbers used here and how they were obtained
All from `outputs/night_export/` with pandas on 15 Nov 2026 unless stated.

| Number | How |
|---|---|
| 264,896 searched; funnel counts | sum of `polar` counts over all tiles in `coverage.json`; statuses from `cell_status()` in `src/export_app.py` ("dropped" = A1 skip: no bowl at 90 m, `src/pipeline/a1.py`) |
| 11,604 tiles | `outputs/night_export/README.md`; 19,433 land tiles from `docs/NIGHT_RUN.md` |
| 1,825 Polar, 500 Mare | rows with `BASE_TYPE` polar / mare and a score in `scores.csv` (plus 3 missed sites, 2 tuning rows extra) |
| Impact matches | `IMPACT_CRATER == 1`: Meteor Crater, Roter Kamm, New Quebec/Pingualuit |
| Meteor 0.442 rank 45; Al Wahbah 0.273; Roter Kamm 0.241; Pingualuit 0.198; top 0.695 | `SCORE_TOTAL`, `RANK` in `scores.csv` |
| Overlap 5 of top 50; Spearman 0.06 | `nlargest(50)` on `TERRAIN_SCORE` and `LIGHT_SCORE`; Spearman over all 1,825 ranked |
| Median |lat| 30.1° (terrain top 50) vs 39.8° (light top 50) | median of `abs(LAT)` |
| Floor shadow median 0.165; 2 places ≥ 0.9 | `DARK_FLOOR` in `raw_values.csv` (Moon target 1.0, [TGT]) |
| Lowest max Sun elevation 31.8° at 81.6 N | `GRAZING_SUN` in `raw_values.csv` |
| Mare median 0.971, 44 ≥ 0.99 | `SCORE_TOTAL` of Mare rows |
