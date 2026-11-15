# AI use: final export (15 Nov 2026, evening)

Tool: Claude (Anthropic) in Claude Code, working on `main` on request.

What the AI did:
- `src/pipeline/multi_target.py`: completeness rule. A score against a lunar target is only given when every
  counting criterion has both a lunar and an Earth value; otherwise no data, never best target ("missing values
  must never score better than real ones", team request). Tests updated / added in `tests/test_multi_target.py`.
- `src/export_app.py`: `--glim` option, GLiM rock class display columns in `raw_values.csv`
  (`ROCK_CLASS`, `ROCK_CLASS_NAME`, `BASALT_SHARE_5KM`, `GLIM_COVERED_SHARE`, `BASALT_REGION`), using the merged
  `src/pipeline/material.py` unchanged; parameters in `config/display.yaml` → `material` (outside the freeze).
  Tests in `tests/test_export_material.py`.
- Re-ran the export with this morning's command plus `--glim`; checked that every pre-existing column of
  `scores.csv` and `raw_values.csv` is byte-identical, that the built-in target re-scored from raw values equals
  `SCORE_TOTAL` on every row, and ran pytest + a headless Chrome check of the app.
- `app/app.js`: only `ROCK_CLASS` / `ROCK_CLASS_NAME` added to the text columns (else parsed as NaN).
- Docs: `docs/MULTI_TARGET.md` (rule + real-data counts), `docs/NIGHT_RUN.md` (command), `CLAUDE.md` decision row.

Not done by the AI: choosing or verifying lunar targets (team, `docs/NEW_TARGETS_REPORT.md`), the basalt threshold
and coverage values (taken from `docs/MATERIAL_REPORT.md`), any change to config-v1 / mare-v1 scoring.
No numbers were invented; all counts come from the export run.
