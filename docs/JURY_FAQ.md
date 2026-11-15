# Jury FAQ: Earth Twins of the Moon

Short answers to hard questions, each with the file that backs it. Source key as in `docs/PITCH_OUTLINE.md`:
[NX] night export `outputs/night_export/`, [VAL] `docs/VALIDATION_config-v1.md`, [CRIT] criteria doc,
[FC] `docs/FACT_CHECK.md`, [TGT] `config/lunar_targets.json`, [CL] `CLAUDE.md`. `[TEAM]` = fill in.

## Method

**Why no machine learning?**
There is nothing to learn from: no labelled list of "good lunar analogs" exists, and the few known ones
(Haughton, Meteor Crater, Iceland) were picked by eye. A learned model would copy that choice. We measure
physical quantities with the same code on Earth and Moon, so every score can be traced to a value in metres,
degrees or hours of sunlight ([CL] decisions 14 Nov). It also let us freeze the method before validation.

**How is a place scored?**
Per criterion `score = exp(−((earth − moon) / tolerance)²)`, 1 = same as the Moon; total = weighted mean of the 7
counting criteria (sunny ridge, dark floor, light next to dark, bowl shape, flat base, steep walls, roughness).
Tolerances are a team choice in `config/pipeline.yaml` ([CL] 14 Nov). Size-dependent values (diameter, depth)
are shown but not scored, because Shackleton (20.9 km) is far bigger than Earth bowls: we compare shape, not size.

**Why 15 km cells and a 60 m grid?**
15 km ≈ an Artemis III candidate region ("approximately 15 by 15 km", NASA 2022, [FC]). 60 m is the common grid
for Earth (30 m DEM) and Moon (20 m LOLA), in a metric projection, because slope and roughness depend on
resolution ([CL]).

**How is Shackleton measured?**
`src/compute_lunar_target.py` reads LOLA `LDEM_80S_20MPP_ADJ` (±35 km, 20 m → 60 m) and finds the crater from
the data. Rim crest 20.9 km, rim-to-floor 4,077 m, scored wall ring 27.2°, base pad 0.66° [TGT, CRIT]. Zuber et
al. 2012 give 21 km and 4.1 ± 0.05 km [FC].

**Did you search the whole planet?**
No. 264,896 cells in 11,604 of 19,433 1° land tiles, deserts first, in one night with a time limit [NX, NIGHT_RUN].
The same command resumes for the rest.

**What does "recognised automatically" mean for the impact craters?**
The bowl detector only sees elevation. Afterwards each ranked place is matched against 88 confirmed impact
structures (Wikipedia list, incomplete). Three ranked places match: Meteor Crater, Roter Kamm, Pingualuit [NX].
The match is a label for display; it never changes the score.

**Why are mines in the results?**
An open-pit mine is a deep, closed, steep-walled bowl with a flat floor: exactly what the bowl filter asks for.
That shows the detector works, but a mine is not a useful analog site. We added a mine filter
`[TEAM: how it works, file/commit, places removed]`.

## Light

**How reliable are the light values?**
Earth: a year-long Sun simulation over the DEM (`src/pipeline/light.py`). Moon: NASA PGDA's modelled illumination
map (`AVGVISIB_85S_060M_201608`, Mazarico et al. 2011). Both share the flat-land reference (`flat_lit_fraction`)
and the rim zone (`light.rim_zone`). Known limitation, accepted 14 Nov: the Moon map counts the visible part of
the Sun's **disc**, Earth counts the Sun's **centre** above the horizon. Both give 0.5 on flat land; on terrain
they can differ where the Sun is partly hidden for long ([CRIT] footnote 2). The flat-land formula ignores
Earth's orbital eccentricity (up to ~2 % off at ±75°). The DEM is a surface model, so it includes buildings and
vegetation; the filters remove most of them.

**Why can no place on Earth match the grazing Sun?**
The Sun's highest elevation over a year depends only on latitude and axial tilt. On the Moon the tilt is ≈ 1.54°
(NSSDC, [FC]), so at Shackleton the Sun never rises above 1.9°. On Earth (tilt 23.4°) it is at least 23.4°, even
at the poles. Lowest in our ranked set: 31.8° at 81.6 N [NX]. That is why c4 is shown, not scored.
Effect: Shackleton's floor is in shadow 100 % of the time [TGT]; the median Earth floor 16.5 %, and only 2 of
1,825 places reach 90 % [NX].

**Why don't terrain twins and light twins coincide?**
Shape is decided by geology, darkness by latitude and depth. Places that look like Shackleton (mostly arid, low
latitude: Atacama region, Arizona) get a high Sun; places with dark floors are further from the equator or in
deep mountain bowls. Only 5 of the top 50 by terrain are in the top 50 by light; rank correlation 0.06 over 1,825
places [NX]. So a team should pick a site by what it wants to test: shape and driving, or shadow and power.
Caveat: some of the darkest floors are very deep Himalayan depressions that may be DEM artefacts (unchecked).

## Validation

**Why did validation "fail"?**
Because it was a real test. We froze all settings (tag `config-v1`, guarded by tests) and wrote predictions before
running Devon Island and Iceland [VAL]:
- **Haughton**: not found. We expected the 26 km window to cut it off; the real reason is that it has no closed
  bowl in the DEM at all, not even ≥ 10 m in one 65 × 67 km window. It is heavily eroded.
- **Askja**: not found. Not the water filter: the caldera lake is a flat surface in the DEM, so depth is measured
  from the water (48 m), below the 50 m minimum.
- Iceland overall: 976 cells, one weak match (0.225).
This tells us exactly what the method cannot see: eroded craters and lake- or sediment-filled bowls. Tenoumer
(44 m spill depth) is missed for the same reason. Fixes are listed for config-v2; we did not tune them in.

**Then why trust the ranking?**
It recovers known structures it was never told about (three impact craters, mines), and every score can be opened
down to the raw value next to the Moon value in the app. It ranks *shape and light similarity*, not "fame" as an
analog site, so famous eroded sites can legitimately rank low.

**Why does Meteor Crater score only 0.44 (rank 45)?**
It is small (1.1 km), so at 60 m its walls are smoothed: 23.9° measured, a lower bound ([CRIT], small-crater
limit). It is also a tuning site, so it does not count as an independent result. Its score was 0.462 in the
region run and 0.442 in the night run; the difference is not checked (probably a shifted grid).

**What about the Mare base type?**
500 flat places scored against the median of 20 lunar mare cells (SLDEM2015, Mateo, tag `mare-v1`). Flat plains
are common, so Mare scores are high and close together (median 0.97) [NX]: the Mare ranking separates places only
weakly. Its validation site (Lanzarote) is kept untouched until the method is frozen for good.

## What is unverified

- **Mine filter details** `[TEAM]`, and whether specific top cells are mines (needs imagery).
- **New lunar targets**: 10 Polar (Artemis regions) and 4 Mare candidates are all `verified: false`; several Artemis
  regions are ridges without a bowl and don't fit the Polar definition (`docs/NEW_TARGETS_REPORT.md`).
- **Region boxes** for screening and tuning regions were chosen from memory ([CL], [FC]).
- **Deep mountain depressions** (e.g. 28.47 N, 84.01 E): real or DEM artefact, not checked (`docs/PIPELINE_polar_v1.md`).
- **Facts to correct before slides**: Haughton ~23 km (not 20), Askja 65.03 N 16.75 W, Shackleton position label,
  Roter Kamm age, Tenoumer "sediment" not "sand" ([FC], 11 corrections).
- Region-level country names are approximate (no per-cell lookup).

## Reproduce

All data is open and needs no login (Copernicus DEM and ESA WorldCover on AWS; LOLA, PGDA, SLDEM2015 from NASA PGDA).
From the repo root (Windows, see `docs/NIGHT_RUN.md`):

```powershell
.venv\Scripts\python.exe src\stage0_world.py --workers 8
.venv\Scripts\python.exe src\night_run.py --world --tracks A,B1 --max-hours 9 --workers 7
.venv\Scripts\python.exe src\night_run.py --b2
.venv\Scripts\python.exe src\night_run.py --score
.venv\Scripts\python.exe src\export_app.py out\night_polar out\night_mare out\meteor_crater out\pinacate
```

- Lunar target: `src/compute_lunar_target.py` (Polar), `src/compute_mare_target.py` (Mare).
- Every raw record carries provenance (git commit, config check, DEM source and resolution, UTC time) [NIGHT_RUN].
- Freezes: `tests/test_config_freeze.py`, `tests/test_mare_freeze.py`. Test suite: `python -m pytest -q tests`
  (102 passed, 1 skipped in the Task 2 and Task 5 reports, before PRs 20–23; `[TEAM: re-run]`).
- Download size: ~2–4 GB per hour of night run [NIGHT_RUN].

## AI use
We used Claude (Anthropic) as a coding and writing helper; team members reviewed and tested the code, and
`AI_USAGE.md` lists each use. No AI runs in the app and no images are AI-generated (`docs/SUBMISSION_DRAFT.md`).
