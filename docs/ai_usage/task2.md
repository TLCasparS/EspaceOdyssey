# AI use, Task 2 (fact-check)

Sat 14 Nov 2026, night | Claude (claude.ai, research with web search) | Searched the repo for claims marked
"from memory", "unchecked" or "~" and for the claims listed in Task 2; checked each against web sources
(NASA, ESA, USGS, PGDA, Smithsonian GVP, IAU Gazetteer, Earth Impact Database, Zuber et al. 2012,
Wikipedia where nothing better was found) and wrote docs/FACT_CHECK.md with a source link and status per
claim. No other file was changed; suggested corrections are listed, not applied. Values were read from
the sources by the AI and are not yet re-read by a person: check the "CORRECT TO" rows against their
links before editing slides.

Tests on this branch: `python -m pytest -q tests` → 102 passed, 1 skipped, 1663 warnings in 44.26s (no code changed).
