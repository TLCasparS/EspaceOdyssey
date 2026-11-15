# AI use: app features, night of 14–15 Nov 2026

Tool: Claude (Anthropic), working as a coding agent on Sofia's request, on branches `agent/app-features` and
`agent/hosting`.

What the AI did:
- Wrote the code for the three features (Opportunities & challenges box, Moon base to scale, astronaut guide)
  and the GitHub Pages hosting files.
- Searched the web for facts about the five scored sites and the base sizes, opened each source, and wrote the
  short lines in `app/sample/site_info.json` from them. Lines it could not tie to a source were left out.
- Wrote the guide's explanations from the team's criteria doc (`docs/Moon Analog Criteria and Datasets.md`).

What the AI did not do:
- No AI-generated images, video or audio. The astronaut and the base are simple drawings made in code.
- No AI runs inside the app: the guide's answers are pre-written text or numbers computed from our data.
- No scores or measurements were changed; all numbers marked "our data" come from the team's pipeline output.

Checked by: the agent opened every source link; the team should still read the lines before the pitch.
