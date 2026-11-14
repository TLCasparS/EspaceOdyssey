# Night agents guide (14 → 15 Nov 2026)

You are one of several AI agents working overnight for team **EspaceOdyssey** (NASA Space Apps 2026,
challenge "Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars").
Read this whole file before you start. Then do **only your own task** (section "Tasks").
A person checks your work in the morning. Make that check fast and safe.

---

## 1. Project in 60 seconds

We rank places on Earth by how closely they resemble lunar base sites, using open data.

- **Pipeline:** hard filters (land cover, water, towns) → candidate places on a common 60 m metric grid →
  criteria (raw values) → score per criterion = closeness to a lunar target → weighted total.
- **Score per criterion:** `score = exp(-((earth - moon) / tolerance)^2)`. 1 = same as the Moon.
- **Base types:**
  - **Polar** (frozen as tag `config-v1`): closed bowls ("craters") compared with **Shackleton**.
    Counting criteria: c1 sunny ridge, c2 dark floor, c3 light next to dark, c7 bowl shape,
    c10 flat base, c11 steep walls, c13 roughness. Display only (weight 0): c4, c5, c8, c9, c12, c14, c18, c19, c24.
  - **Mare** (frozen as tag `mare-v1`): flat plains compared with a median over 20 lunar mare cells
    (Mateo). Counting: c9 relief, c10 flat base, c12 drivable share, c13 roughness. Display: c16, c23.
- **Moon side:** LOLA 20 m DEM + PGDA illumination (Polar), SLDEM2015 (Mare). Values in
  `config/lunar_targets.json`; only entries with `verified: true` are used.
- **Night run (running on Caspar's laptop tonight):** `src/night_run.py --world` stores **raw values**
  per candidate. Scoring is a separate, re-runnable step (`--score`). New lunar targets can be scored
  against the stored raw values without recomputing.
- **App:** `app/` (Sofia), static web page reading `outputs/` (written by `src/export_app.py`).

Key documents (read the ones your task needs):

| File | What |
|---|---|
| `CLAUDE.md` | project brief, decisions with dates, region roles (tuning / screening / validation) |
| `docs/Moon Analog Criteria and Datasets.md` | the team plan: 29 criteria, datasets, lunar values (file name has spaces) |
| `docs/VALIDATION_config-v1.md` | validation result (Haughton, Askja not found, and why) |
| `docs/NIGHT_RUN.md` | how the night run works, morning steps |
| `docs/APP_CHANGES_for_Sofia.md`, `outputs/README.md` | export format the app reads |
| `config/pipeline.yaml`, `config/lunar_targets.json` | thresholds, weights, tolerances, lunar targets |

---

## 2. Rules for every agent (non-negotiable)

1. **Never merge into `main`, never push to `main`, never force-push.** Work on your own branch
   `agent/<task-name>` and open a pull request, or write files only, as your task says.
2. **Do not change frozen settings:** nothing in `config/pipeline.yaml` sections covered by
   `config-v1` (Polar) or `mare-v1` (Mare), and no edits to `config/lunar_targets.json`.
   The freeze tests (`tests/test_config_freeze.py`, `tests/test_mare_freeze.py`) must keep passing.
3. **Do not change existing criterion functions** (`src/pipeline/polar.py`, `mare.py`, `light.py`,
   `lunar_light.py`, `scoring.py` behaviour for existing targets). Add new code next to them.
4. **No invented numbers or sources.** Every number you write comes from data you computed (say how)
   or from a source you name (link). If unsure, write `UNVERIFIED` and why.
5. **Coordinates and names from memory are not facts.** Find places from data or a citable source.
6. **Lunar values you compute stay `verified: false`.** A person flips them after checking.
7. **Don't touch Caspar's laptop work directory** (`%LOCALAPPDATA%\espaceodyssey_night`) or the repo
   folder the night run started from. If you run on Caspar's laptop at all, use a separate clone.
8. **Small and reviewable:** one task, one branch, small commits with clear messages.
9. **End with a report** (template in section 4). If you couldn't finish, the report says what's left.
10. **Hackathon rule on AI use:** write a short note on how AI was used in your task to your own file
    `docs/ai_usage/task<N>.md` (NOT to `AI_USAGE.md`: several branches editing one file cause merge
    conflicts; the team combines the notes in the morning).
11. **Write only the files your task owns** (table in section 2a). If you think another file needs a
    change, describe it in your report instead of making it.

Stop and write it in your report instead of guessing if: a requirement is ambiguous, a source
contradicts our documents, a test fails that isn't yours, or a step needs a login or a large download.

### 2a. File ownership (so parallel agents never overwrite each other)

Every agent works on its own branch and writes only its own files. Two branches changing the same file
is what causes conflicts, so each file below has exactly one owner tonight.

| Task | Branch | May create / change | Must not touch |
|---|---|---|---|
| 1 | `agent/submission` | `docs/SUBMISSION_CHECKLIST.md`, `docs/SUBMISSION_DRAFT.md`, `docs/ai_usage/task1.md` | everything else |
| 2 | `agent/fact-check` | `docs/FACT_CHECK.md`, `docs/ai_usage/task2.md` | everything else (list corrections, don't apply them) |
| 3 | `agent/multi-target` | new scoring module (e.g. `src/pipeline/multi_target.py`), `src/export_app.py`, new tests, `docs/MULTI_TARGET.md`, `docs/ai_usage/task3.md` | `config/lunar_targets.json`, `config/pipeline.yaml`, existing criterion functions |
| 4 | `agent/app-scale` | `scripts/make_fake_outputs.py`, `outputs_fake/`, `docs/APP_SCALE_TEST.md`, `docs/ai_usage/task4.md` | `app/app.js` (Sofia decides), `outputs/` |
| 5 | `agent/lunar-targets` | `config/lunar_targets_candidates.json`, `figures/moon/targets/`, `docs/NEW_TARGETS_REPORT.md`, new helper scripts, `docs/ai_usage/task5.md` | `config/lunar_targets.json`, existing criterion functions |
| 6 | `agent/pitch` | `docs/PITCH_OUTLINE.md`, `docs/JURY_FAQ.md`, `docs/ai_usage/task6.md` | everything else |
| nobody | — | — | `CLAUDE.md`, `AI_USAGE.md`, `config/pipeline.yaml`, `config/lunar_targets.json`, `requirements.txt`, `environment.yml`, existing files in `src/pipeline/`, `app/` |

Tasks 3 and 5 connect only through the **format** of `config/lunar_targets_candidates.json` (defined in
Task 3). Task 5 writes that file; Task 3 reads the format and tests with its own fake data. They never
edit the same file. Chat agents (Tasks 1, 2, 6) have no repo access: they deliver their files to a person,
who commits them on the task's branch.

---

## 3. Tasks

Each task: goal, where to run, inputs, steps, outputs, done when. Start prompt at the end of each.

### Task 1: Challenge requirements and submission draft
**Goal:** make sure nothing required for the submission is missing, and draft the texts.
**Where:** any chat or research agent (no code, no laptop).
**Inputs:** challenge page
https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/,
the general Space Apps 2026 rules and judging criteria (find them on spaceappschallenge.org),
`CLAUDE.md`, the criteria doc, `docs/VALIDATION_config-v1.md`, `app/README.md`.
**Steps:**
1. List every deliverable and rule (project page fields, video/demo length, data/AI disclosure,
   use of NASA data, branding rules, deadlines with time zone). Quote the source line for each.
2. Mark each item: done / partly / missing, based on the repo.
3. Map our work to the challenge objectives and judging criteria.
4. Draft: project title options, a 1-paragraph summary, the full project description, a data
   sources list (with links), an AI-use statement consistent with `AI_USAGE.md` and the app footer.
**Outputs:** `docs/SUBMISSION_CHECKLIST.md`, `docs/SUBMISSION_DRAFT.md` (branch `agent/submission`, PR).
**Done when:** every requirement has a source link and a status; drafts make no claim that isn't in
the repo (e.g. don't say "searched the whole planet" unless the night run report says so).

> Start prompt: "Read docs/AGENTS_NIGHT_GUIDE.md and do Task 1 only. Follow section 2 rules."

### Task 2: Fact-check everything marked "from memory"
**Goal:** every number and name that may end up on a slide is checked against a source.
**Where:** research agent with web access.
**Claims to check (add any others you find marked "from memory", "unchecked" or "~" in the repo):**
- Shackleton: diameter (~21 km), depth (~4 km), inner wall slope (~30°); our LOLA values: rim crest
  diameter 20.9 km, rim-crest-to-floor 4073 m, inner wall 27.2°.
- Moon equator tilt to the ecliptic: 1.535° (derived 6.68° − 5.145°); max Sun elevation at the pole ~1.5°.
- Diviner: equator ~387–397 K at noon, ~95 K before sunrise (Williams et al. 2017).
- Earth craters (position, diameter, depth): Meteor Crater (~35.03 N, 111.02 W, ~1.2 km);
  Al Wahbah (~22.90 N, 41.14 E); Roter Kamm (~27.77 S, 16.29 E); Tenoumer (~22.92 N, 10.41 W,
  ~1.9 km, ~110 m deep, sand-filled); Trou au Natron (~20.95 N, 16.53 E); El Elegante, Pinacate
  (~31.85 N, 113.40 W); Haughton (~75.38 N, 89.67 W, ~20–23 km).
- Askja caldera position (~65.0 N, 16.7 W) and its lake; Apollo geology training in Iceland,
  at Meteor Crater, Nördlinger Ries, Sudbury, Pinacate; ESA training on Lanzarote.
- Artemis III: number of candidate regions (13 in 2022, 9 in the 2024 update), region size ~15 × 15 km.
- Mare Tranquillitatis pit: ~88–100 m opening, ~105 m deep.
- Copernicus DEM vertical accuracy; SLDEM2015 vertical accuracy 3–4 m; WorldCover overall accuracy 76.7 %.
**Outputs:** `docs/FACT_CHECK.md`: table with claim | where it appears in the repo | checked value |
source link | status (OK / CORRECT TO … / UNVERIFIED). Branch `agent/fact-check`, PR. **Do not edit
other files**; list suggested corrections instead.
**Done when:** every claim has a status and a source, or `UNVERIFIED` with the reason.

> Start prompt: "Read docs/AGENTS_NIGHT_GUIDE.md and do Task 2 only. Follow section 2 rules."

### Task 3: Scoring against several lunar targets ("closest lunar twin")
**Goal:** score stored raw values against **several** lunar targets per base type and report, per
Earth place, the score against each target and the best-matching target.
**Where:** cloud coding session on the GitHub repo (branch from `main`; if `main` has no
`src/night_run.py` yet, branch from `night-run`). No data downloads needed.
**Design constraints:**
- Raw values are target-independent. Scoring must read only stored raw values (the night run's raw
  records and `out/<run>/ranking.csv`) and targets; no DEM reads.
- Keep `config/lunar_targets.json` as is and backward compatible. Read additional targets from a
  new optional file `config/lunar_targets_candidates.json` (written tonight by Task 5) with the same
  per-criterion shape, plus `name`, `base_type`, `verified`. Use only `verified: true` targets for
  real scoring; allow an explicit `--include-unverified` flag for previews, and mark outputs as preview.
- Same scoring rule, same weights and tolerances per base type as today (from config), unless a
  target carries its own tolerance (Mare targets do: `tolerance = max(IQR, floor)`).
- Output columns: `SCORE_<TARGET>` per target, `BEST_TARGET`, `BEST_SCORE`. Extend `export_app.py`
  so `outputs/scores.csv` gets these columns and `outputs/targets.json` lists all targets (keep the
  existing columns so the app keeps working).
- Tests with synthetic raw values and two fake targets (one verified, one not).
**Outputs:** code + tests on branch `agent/multi-target`, PR; a short `docs/MULTI_TARGET.md`
(format, how to add a target, example output). List the app changes Sofia would need.
**Done when:** all existing tests + new tests pass; with only today's targets the outputs are identical
to before (regression check).

> Start prompt: "Read docs/AGENTS_NIGHT_GUIDE.md and do Task 3 only. Follow section 2 rules."

### Task 4: App stress test at night-run scale
**Goal:** find out whether Sofia's app stays usable with tonight's data volume, before real data arrives.
**Where:** cloud coding session on the GitHub repo (branch from `main`). No downloads.
**Steps:**
1. Write `scripts/make_fake_outputs.py` that generates fake export files in the current format
   (`docs/APP_CHANGES_for_Sofia.md`, `outputs/README.md`): e.g. 200, 2,000 and 10,000 scored places,
   20,000 coverage tiles, cells near places only. Clearly fake (names like `FAKE_0001`), written to
   `outputs_fake/`, never to `outputs/`.
2. Point the app at them (query parameter or a copy of `app/` reading `outputs_fake/`; don't change
   Sofia's default behaviour) and measure: load time, file sizes, globe/label count, list rendering,
   memory. Use a headless browser if available; otherwise analyse the code paths and file sizes.
3. Write concrete, prioritised fixes for Sofia (e.g. labels only for top N, points instead of labels,
   coverage as one layer, lazy loading), with the line numbers in `app/app.js`.
**Outputs:** `docs/APP_SCALE_TEST.md`, the generator script; branch `agent/app-scale`, PR.
**Do not** modify `app/app.js` itself unless a fix is tiny, isolated and behind a flag; Sofia decides.
**Done when:** the report gives numbers per size and a clear "breaks at about N places" statement.

> Start prompt: "Read docs/AGENTS_NIGHT_GUIDE.md and do Task 4 only. Follow section 2 rules."

### Task 5: New lunar targets (Mateo's machine)
**Goal:** more lunar targets so each Earth place gets a "closest lunar twin" tomorrow.
**Where:** Mateo's computer (needs lunar data downloads). Separate clone. Not on Caspar's laptop.
**Steps:**
1. **Polar:** one target per Artemis candidate region near the south pole (e.g. Connecting ridge
   = LOLA Site01, Peak near Shackleton = Site07, de Gerlache rim, Malapert, Nobile rim). Region
   coordinates from a citable source (record it). Same method as Shackleton: LOLA
   `LDEM_80S_20MPP_ADJ.TIF` window ±35 km → 60 m, criteria via the existing functions; light c1–c4
   from PGDA `AVGVISIB_85S_060M_201608` and `LPSR_85S_060M_201608`. Find the bowl or rim from the
   data; save a preview PNG per target (floor, walls, rim, base pad).
2. **Mare:** split the existing 20-cell target into one target per mare (Tranquillitatis,
   Serenitatis, Imbrium, Crisium): median + IQR per criterion, `tolerance = max(IQR, floor)`.
3. Note where a region doesn't fit the Polar definition (e.g. a ridge without a closed bowl): report
   it, don't force it.
**Outputs:** `config/lunar_targets_candidates.json` (format as in Task 3: `name`, `base_type`,
per-criterion `value`, `tolerance` if any, `source`, `date`, `git_commit`, `verified: false`),
previews in `figures/moon/targets/`, report `docs/NEW_TARGETS_REPORT.md`. Branch
`agent/lunar-targets`, PR (or leave committed locally if push sign-in fails).
**Done when:** each target has values, a preview and a source, or a clear reason why it was skipped.

> Start prompt: "Read docs/AGENTS_NIGHT_GUIDE.md and do Task 5 only. Follow section 2 rules."

### Task 6 (optional): Pitch outline and jury FAQ
**Goal:** a pitch storyline and answers to hard questions, from what the repo actually shows.
**Where:** any chat agent.
**Content:** storyline (problem → method → Shackleton target → what we found → limits → next steps);
key messages: the method finds real craters from elevation data alone; no place on Earth has the
Moon's grazing sun; light-like and crater-like analogs don't coincide; honest validation (Haughton,
Askja missed, and why); Tenoumer as a known limitation. Slide outline (8–10 slides), a 30-second
summary, and a jury FAQ (why no machine learning, how reliable the light values are, why validation
"failed", what's unverified, how to reproduce).
**Outputs:** `docs/PITCH_OUTLINE.md`, `docs/JURY_FAQ.md`; branch `agent/pitch`, PR.
**Done when:** every claim points to a repo file or a source; nothing about the night run's results is
invented (leave `[from night run]` placeholders).

> Start prompt: "Read docs/AGENTS_NIGHT_GUIDE.md and do Task 6 only. Follow section 2 rules."

---

## 4. Report template (end of every task)

Put this at the top of your main output file and in the PR description:

```
## Agent report: Task <n> <name>
Status: done / partly done / blocked
What I did (3–6 bullets):
Files changed / created:
Tests: <command> → <result>
Open points / needs a human decision:
Unverified items (and why):
Data downloaded (size):
```

---

## 5. Morning review (for the team)

0. Merge order (each PR touches only its own files, so order barely matters): fact-check and
   submission/pitch docs first, then `agent/lunar-targets`, then `agent/multi-target`, then
   `agent/app-scale`. Combine `docs/ai_usage/task*.md` into `AI_USAGE.md` in one commit at the end.
1. Read each report (top of file / PR description). Target: 10 minutes per agent.
2. Task 2 first: apply fact-check corrections to slides and docs.
3. Task 5: check previews and plausibility, then set `verified: true` per target you accept.
4. Task 3: merge, then re-score the night run against all verified targets.
5. Task 4: Sofia picks the fixes she wants.
6. Tasks 1 and 6: edit the drafts into the final submission and pitch.
