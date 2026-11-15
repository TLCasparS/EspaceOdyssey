## Agent report: Task 3 Scoring against several lunar targets ("closest lunar twin")
Status: done (code, tests, docs; not run on real night-run data: none is in the repo)
What I did:
- New module `src/pipeline/multi_target.py`: builds today's target + candidate targets per base type and scores
  stored raw values against each with the existing `pipeline.scoring.score_direct` / `total_score` (unchanged).
  Also a small CLI for `ranking.csv` files and night-run raw records (`raw/<track>/*.jsonl`).
- `src/export_app.py`: new options `--candidates` and `--include-unverified`. If a candidate target is in use,
  `scores.csv` gets `SCORE_<TARGET>`, `BEST_TARGET`, `BEST_SCORE` (and `MULTI_TARGET_PREVIEW`) appended after the
  existing columns, and `targets.json` gets `targets[base].lunar_targets` and `_multi_target`.
- Regression: with only today's targets (no candidates file, or only unverified candidates) every output file is
  byte-identical to before (test + manual diff against `main`'s `export_app.py`).
- Read format = the file Task 5 already pushed on `agent/lunar-targets` (`config/lunar_targets_candidates.json`);
  tested against it locally (not committed here; that file belongs to Task 5).
Files changed / created: `src/pipeline/multi_target.py` (new), `src/export_app.py`, `tests/test_multi_target.py` (new),
`docs/MULTI_TARGET.md` (new), `docs/ai_usage/task3.md` (new)
Tests: `python -m pytest -q` → 114 passed, 2 skipped (before: 102 passed, 1 skipped; the new skip is
`test_task5_file_format_loads`, which runs once Task 5's file is merged; it passed locally with that file copied in)
Open points / needs a human decision:
1. **Place per cell.** `export_app.py` reads `ranking.csv`, which holds ONE place per cell, chosen as the best match
   to Shackleton. Another target might prefer a different bowl in the same cell. The CLI with `--raw` re-picks the
   best place per target from the night run's raw records (`PLACE_<TARGET>` = candidate index). Decide whether
   the app export should also use the raw records (needs a change in `night_run.py`, not mine).
2. **Targets with fewer criteria.** A target scores over the counting criteria it has usable values for (weights
   renormalised, as today). Task 5's `polar_dm1` / `polar_dm2` have no c1–c3, so they are scored on terrain only and
   can win `BEST_TARGET` against targets scored on more criteria. Option: require the same criteria set before a
   target may be "best". I didn't add a rule without a team decision.
3. **Names of today's targets:** I named them `shackleton` (Polar) and `mare_20cells` (Mare). Columns
   `SCORE_SHACKLETON`, `SCORE_MARE_20CELLS`. Rename in `BUILTIN` in `multi_target.py` if you prefer other names.
4. **Night run:** `night_run.py --score` is unchanged (not mine). After `--score`, run
   `python src/pipeline/multi_target.py --raw <work>/raw/A --base polar -o out/multi_target_polar.csv` or export
   as usual (columns appear automatically once a candidate is verified).
5. CLI vs export: the CLI re-scores with the CURRENT config (like `night_run --score`) and prints a note if today's
   target then differs from the stored score; `export_app.py` uses the config the run was scored with (`radar.json`),
   so `SCORE_SHACKLETON` = `SCORE_TOTAL` there (it warns if not).
Unverified items (and why): none of my own numbers. The example values below come from synthetic test runs and
Task 5's unverified targets (preview); they are not results.
Data downloaded (size): none

---

# Several lunar targets per base type ("closest lunar twin")

Raw values are target-independent, so each Earth place can be scored against any number of lunar targets
without new DEM reads. Per place we report the score against each target and the best-matching one.

## Rules
- **Same scoring rule:** per criterion `exp(-((earth - moon) / tolerance)^2)`, total = weighted mean of the counting
  criteria (weight > 0) that have a score. Same code (`pipeline.scoring`), same rounding (4 decimals) as today.
- **Same weights per base type** as today (from config / the run's `radar.json`).
- **Tolerance:** the target's own if it has one; Mare: `max(own, mare.tolerance_floor)` (the rule `config.load_config`
  already applies to today's Mare target). Otherwise Polar uses `config/pipeline.yaml` polar tolerances.
  A Mare criterion without its own tolerance is not scored.
- **Verification:** real scoring uses a candidate only if the target has `verified: true`, and within it only
  criteria with `verified: true`. `--include-unverified` = preview: every non-skipped target and every criterion
  with a value; outputs are marked (`MULTI_TARGET_PREVIEW = 1`, `targets._multi_target.preview = true`, README).
- Missing value = no data (left out, weights renormalised), never 0. `skipped: true` targets are ignored.
- `config/lunar_targets.json` is unchanged and still the only source of today's targets.

## Candidate file format (`config/lunar_targets_candidates.json`, written by Task 5)
```json
{
  "_readme": "...",
  "targets": [
    {
      "name": "polar_site01",                // unique; column = SCORE_ + upper-case name (non-alphanumerics -> _)
      "label": "Polar · Connecting Ridge",    // optional, shown in targets.json
      "base_type": "polar",                   // polar | mare
      "verified": false,                      // target level: must be true for real scoring
      "skipped": false,                       // true = no criteria (skip_reason), ignored
      "criteria": {
        "c7_bowl":   {"value": 0.0508, "verified": false, "source": "...", "date": "2026-11-14"},
        "c9_relief": {"value": 152.0,  "verified": false, "source": "...", "tolerance": 40.0}
      }
    }
  ]
}
```
Criterion ids and units are those of `config/lunar_targets.json`. Other fields (region, preview, git_commit, …) are
allowed and ignored by the scoring. Names `total` (→ `SCORE_TOTAL`) and duplicate columns are refused.

## How to add a target
1. Compute its raw values with the same code as the Earth side (Task 5 scripts) and add an entry as above,
   `verified: false`.
2. Preview: `python src/export_app.py out/<run> ... --include-unverified --out outputs_preview/`.
3. A person checks the values / preview image, then sets `verified: true` on the target and on each accepted criterion.
4. Export as usual: `python src/export_app.py out/<run> ...`. The new columns appear by themselves.

## Outputs
`outputs/scores.csv`: the existing columns are unchanged and stay in place. Appended, only if a candidate target is in use:

| Column | Meaning |
|---|---|
| `SCORE_<TARGET>` | score vs Moon against that target, one per target (today's target first; equals `SCORE_TOTAL`). Empty for rows of another base type / no data |
| `BEST_TARGET` | `name` of the target with the highest score among the row's base type (ties: today's target first) |
| `BEST_SCORE` | that score |
| `MULTI_TARGET_PREVIEW` | `1` on every row, only in a preview (`--include-unverified`) |

`outputs/targets.json`: `targets[base].lunar_targets = [{name, column, label, base_type, builtin, verified, preview,
source, criteria: {criterion: {value, tolerance, weight}}}]` (counting criteria only) and
`_multi_target = {preview, note}` (underscore: the app skips it when it lists base types).

CLI output (`multi_target.py`): `run,id,base_type,lat,lon,score,SCORE_<...>,PLACE_<...>,BEST_TARGET,BEST_SCORE,PREVIEW`.

## Example (synthetic runs, Task 5 targets UNVERIFIED → preview, not results)
Three fake places (`tests/test_multi_target.py` fake config, `_place` values), exported with Task 5's
`config/lunar_targets_candidates.json` (branch `agent/lunar-targets`, all `verified: false`) and `--include-unverified`.
Selected columns of `scores.csv` (16 targets in total):
```
SITE,SCORE_TOTAL,SCORE_SHACKLETON,SCORE_POLAR_SITE01,SCORE_POLAR_HAWORTH,SCORE_POLAR_LM7,BEST_TARGET,BEST_SCORE,MULTI_TARGET_PREVIEW
runa r001c001,0.9735,0.9735,0.3311,0.3295,0.7575,shackleton,0.9735,1
runb r000c000,0.3493,0.3493,0.3872,0.4553,0.6529,polar_lm7,0.6529,1
runa r001c002,0.3276,0.3276,0.9729,0.9906,0.3364,polar_haworth,0.9906,1
```

## App changes Sofia would need (not made: `app/` is not mine)
1. `app/app.js:138` `TEXT_COLUMNS`: add `BEST_TARGET` (else `Number("polar_site01")` = NaN). `NAME`, `COUNTRY`,
   `ROLE`, `MISSED_REASON` are also text but not in that set today, so the app turns them into NaN. That's an
   existing issue, worth fixing at the same time.
2. Feature-detect: `state.columns.has('BEST_TARGET')`. The columns exist only once a candidate target is verified.
3. Site card: "Closest lunar twin: <label of BEST_TARGET> (<BEST_SCORE>)". Labels from
   `targets[base].lunar_targets` (match `name`); optionally a small table of all `SCORE_<TARGET>` (`column` field).
4. Ranking: optional selector "rank by target" = sort by the chosen `SCORE_<TARGET>` instead of `SCORE_TOTAL`.
5. Preview: if `targets._multi_target.preview` is true (or `MULTI_TARGET_PREVIEW` = 1), show a "preview: unverified
   targets" banner.
6. Moon globe (optional, later): one marker per target needs its position. Task 5's file has
   `region_centre_lat_lon` (Polar), but the export does not pass it on yet.
