# AI use: submission check, imagery licence, draft numbers, video script (15 Nov 2026 morning)

Tool: Claude (Anthropic), as a coding agent on Sofia's request, branch `agent/submission-final`.

What the AI did:
- Checked EOX's licence pages and tile service: switched the 3D imagery to the 2016 layer (CC BY 4.0).
- Added `_aliases` in `app/sample/site_info.json` (plus a 3-line lookup in `app.js`) so the site notes still show
  when the app reads the night export; reworded three "our data" lines that the night run made untrue.
- Copied the night-run numbers from `docs/PITCH_OUTLINE.md` into `docs/SUBMISSION_DRAFT.md`, added a status list
  to `docs/SUBMISSION_CHECKLIST.md`, wrote `docs/DEMO_VIDEO_SCRIPT.md`.

What it did not do: no scores changed, no new numbers invented, no images, video or audio made.
Checked: app loads with first-run and night data (local browser), no console errors; the team should read the
texts before using them.
