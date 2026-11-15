# Demo video script (2 minutes + a 30-second cut)

Written by an AI agent on 15 Nov 2026 morning, for the team to edit and record. Every number is from
`docs/PITCH_OUTLINE.md` (night export of 15 Nov, 02:43) or `config/lunar_targets.json`; nothing new.

**Read this first: the length rule.** If the *submission's* "Link to Project Demo" is a video, it must be
**30 seconds or less** ("a 30-second or less video presentation"; "Projects that exceed these limits will not be
eligible for Global Judging", Project Submission Guide, see `docs/SUBMISSION_CHECKLIST.md` 3.3 and 4.1). So:
- the **2-minute version** is for the local pitch, the repo README or the "Link to Final Project" page;
- the **30-second cut** (bottom) is the one to use if the team submits a video instead of the 7 slides.

**Recording rules** (checklist 5.3–5.6): a team member's own voice (no AI voice, no AI images or video); no NASA
logos; no people under 18; no music unless it is clearly free to use (safest: none); English, or English subtitles.
Screen-record the live app: https://tlcaspars.github.io/EspaceOdyssey/app/ on a laptop, full screen, ~1440 px wide.

Pace: about 140 words a minute. The voice-over below is ~280 words.

---

## 2-minute version

| Time | On screen (what to click) | Voice-over |
|---|---|---|
| 0:00–0:12 | App opens. Moon globe turning; point at the **Shackleton** label. | "Astronauts are going back to the Moon, to its south pole, near Shackleton crater. Before they go, they rehearse on Earth. But which places on Earth are really most like Shackleton, and how close are they?" |
| 0:12–0:32 | Click the **Moon** card for the polar base: Shackleton's values. | "We measured Shackleton from NASA's LOLA elevation map and NASA's illumination map: a bowl almost 21 kilometres wide, walls of 27 degrees, flat ground for a base, a sunny rim and a floor in permanent shadow. Then we ran the *same code* over Earth, on the same 60-metre grid, with open Copernicus elevation and ESA land-cover data." |
| 0:32–0:52 | Earth globe: zoom out to the heatmap and the searched area. Slow spin. | "In one night it searched about 265,000 grid cells of 15 kilometres and ranked 1,825 crater-like places against Shackleton. It knows nothing about impacts, yet it found real impact craters: Meteor Crater, Roter Kamm and Pingualuit. It also found open-pit mines, because they are perfect bowls, so we filter them out." |
| 0:52–1:15 | Click **Meteor Crater** in the list. Card: radar chart, then scroll to **Opportunities & challenges**. | "Every place gets a card. The Moon is the outer ring, so you see at once what matches and what is missing: walls of 23 degrees against Shackleton's 27. Below, opportunities and challenges, each with its source: who owns the land, what has been tested there, how to get in." |
| 1:15–1:35 | **Fly into 3D terrain** → **Moon base to scale** → **Compare with Shackleton**. | "Fly into the real terrain and place a lunar base at true size: a 6.5-metre habitat and a landing pad from published studies. Then zoom out: Shackleton's rim is more than fifteen times wider than Meteor Crater." |
| 1:35–1:52 | Card section on what no place can match; then a missed site (e.g. **Haughton**) in the list. | "And it says where the analogy breaks. At Shackleton the Sun never climbs above 1.9 degrees; on Earth never below 23. So Shackleton's floor is always dark, and a typical Earth crater floor only 16 percent of the time. Our method also missed Haughton and Askja, and the app shows why." |
| 1:52–2:00 | Click **Guide** (astronaut); end on the app with the link as text. | "A guide explains every number. Earth Twins of the Moon: open data, open code, one ruler for two worlds." |

On-screen text at the end (typed, not spoken): `tlcaspars.github.io/EspaceOdyssey/app` · team EspaceOdyssey ·
`[TEAM: names]` · "AI assistant used for code and text; no AI images, video or voice."

### Before recording
- Check each number on screen matches the voice-over: if the app still shows the first-run data (Meteor 46 %) and not
  the night run (44 %, rank 45; walls 23.5° instead of 23.9°), either wait for the night data in the app or say only
  "about 45 percent" and "about 24 degrees".
- `[TEAM: mine filter]`: if the mine filter changes the 1,825, say the new number.
- "More than fifteen times wider": Shackleton rim 20.9 km (`config/lunar_targets.json`) vs Meteor Crater about
  1.1–1.2 km (our 1,127 m equivalent diameter; ~1.2 km in `docs/FACT_CHECK.md`) = 17–19×.
- Do one dry run with the narration read aloud and a stopwatch; cut words, not pace.

---

## 30-second cut (if the submission demo is a video)

~70 words. Same clicks, faster: Moon globe → Earth heatmap → Meteor Crater card → 3D with base → link.

> "Which places on Earth are most like the Moon's south pole? We measured Shackleton crater with NASA's LOLA data,
> then ran the same code over Earth: 265,000 grid cells in one night, 1,825 crater-like places ranked. It found real
> impact craters from elevation alone. Every place gets a card with what matches, what is missing, and where the
> analogy breaks: no place on Earth has the Moon's grazing Sun. Earth Twins of the Moon."

Time it: it must end before 0:30, including the title and link frames.
