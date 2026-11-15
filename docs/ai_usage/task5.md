# AI use, night Task 5 (new lunar targets)

- Tool: Claude Code (Claude Opus 5.5), on Mateo's machine, in a separate git worktree on branch `agent/lunar-targets`.
- The AI wrote the two new scripts (`src/compute_polar_candidates.py`, `src/compute_mare_candidates.py`), ran them, and drafted `docs/NEW_TARGETS_REPORT.md`.
- The AI changed no existing pipeline code, frozen config or `config/lunar_targets.json`. The criteria come from the team's existing functions, imported unchanged.
- Region list from the NASA 2022 release. Region centres computed from PGDA product 78 file extents. No coordinates or numbers from memory.
- All computed targets are `verified: false`. A team member checks the previews and decides.
