# Moon Twins on Earth: 3-minute pitch script (with live demo)

Team **EspaceOdyssey**: Caspar Schlageter, Sofi Sosa, Mateo Pozo.
Two speakers: **Speaker A = Caspar** (slides 1–4), **Speaker B = Sofi** (live demo + slides 5–7).
Spoken words: **327** (click cues in [brackets] not counted). At ~125 words per minute that is about
**2:37** of speech; the demo clicks and the 3D flight fill the rest. Target: **2:50 at most**.
The same text is in the speaker notes of `Moon_Twins_on_Earth.pptx`.

| Slide | Speaker | Words | Target |
|---|---|---|---|
| 1 Title | A | 29 | 0:12 |
| 2 The question | A | 29 | 0:16 |
| 3 Method | A | 54 | 0:25 |
| 4 The search | A | 54 | 0:26 |
| 5 LIVE DEMO | B | 76 | 0:50 |
| 6 What we learned | B | 53 | 0:25 |
| 7 Limits + explore | B | 32 | 0:14 |
| **Total** | | **327** | **2:48** |

## Wording rules (apply in the Q&A too)
- Product name: **Moon Twins on Earth**, everywhere.
- Say **"crater-like places (closed depressions)"**, never "1,261 craters". No top-10 list.
- Impact craters: say **"it flags known impact craters, incl. Pingualuit in the world search"**. Do not say it
  "found Meteor Crater on its own" (Meteor Crater is a tuning site).
- No basalt numbers.

## Before the pitch (demo setup)
- Open https://tlcaspars.github.io/EspaceOdyssey/app/ in a browser tab **before** you start, scroll past the
  Earthrise screen to the globe, and check the globe has loaded (it needs WebGL and the internet).
- Keep the slides in one window and the browser in another; switch with Alt+Tab.
- **If the demo fails:** stay on slide 5, click the video (`pitch/img/demo.mp4`, 27 s, embedded) and say the same
  words. The video shows the same click path, recorded from the live app. The PDF shows only its first frame.

---

### Slide 1: Title · Speaker A (Caspar) · 0:12
Hi, we are Caspar, Sofi and Mateo, team EspaceOdyssey. This is Earthrise, seen from Apollo 8. We turn the view around and look for the Moon's twins on Earth.

### Slide 2: The question · Speaker A (Caspar) · 0:16
Astronauts rehearse Moon missions on Earth. But today's analog sites were picked by eye, and nobody measured how Moon-like they are. So we searched systematically, with open data only.

### Slide 3: Method · Speaker A (Caspar) · 0:25
On the Moon: Shackleton crater at the south pole and two craters in Artemis III regions, from NASA's LOLA and PGDA data, plus mare plains from SLDEM2015. On Earth: the Copernicus elevation model and ESA WorldCover. Same code, same 60-metre grid. Every criterion scores from zero to one: one means identical to the Moon.

### Slide 4: The search · Speaker A (Caspar) · 0:26
In one night we searched about 265,000 cells, each the size of an Artemis III landing region. 1,825 crater-like places, closed depressions, were scored. It even found 111 open-pit mines; we filtered them out, and 1,261 places remain. It also flags known impact craters, including Pingualuit in the world search. Sofi will show you.

> **HANDOVER → Sofi.** Caspar says "Sofi will show you." Sofi clicks to slide 5 and switches to the browser.

### Slide 5: LIVE DEMO · Speaker B (Sofi) · 0:50

**Exact click path** (app already open on the globe, Polar view, "All criteria"):
1. In the **Earth twins** list on the left, click **"54 km SW of Bardaï"** (Tibesti, Chad).
2. The app flies into the **3D terrain** by itself. Wait until the **teal ring** (= the bowl we scored) and the
   "crater floor" / "base spot" dots appear. Optional: drag to look around.
3. **Scroll down** to the datasheet: point at the **radar** (Fingerprint · All criteria) and at the line
   **"Closest lunar twin: Shackleton crater (48%)"** under the title; then at **"What it lacks"** (all light criteria).
4. Scroll back up, Alt+Tab back to the slides.

This is our app, live. Every dot is a crater-like place, a closed depression we ranked. [Click '54 km SW of Bardaï' in the Earth twins list] Let's fly to the Tibesti mountains in Chad. [Wait until the 3D terrain and the teal ring appear] Here it is in 3D. The teal ring is the bowl we scored. [Scroll down to the datasheet] Its datasheet. The radar compares every criterion with Shackleton, the outer ring. Steep walls and the flat base spot match well. Its closest lunar twin is Shackleton, at 48 percent. And it says honestly what it lacks: the light. [Scroll back up, then back to the slides]

### Slide 6: What we learned · Speaker B (Sofi) · 0:25
Shape twins are not light twins: no place scores high on both. And Earth has no grazing Sun: Shackleton's floor is always in shadow, a typical Earth crater floor only 16.5 percent of the time. For mare plains, flat ground is common, but only 1 of 500 places reaches the Moon's small-crater density.

### Slide 7: Limits + explore it yourself · Speaker B (Sofi) · 0:14
We also show what we miss: Haughton is eroded, Askja's lake hides its depth, Lanzarote is mostly sea and villages. Scan the code and explore it on your own phone. Thank you!

Leave slide 7 (the QR code) on screen during the questions.

---

## Q&A prep: likely jury questions (one-line answers, from `docs/JURY_FAQ.md`)

1. **Why are famous analogs like Haughton and Askja not in your results?** We froze all settings before testing them (tag `config-v1`) and wrote our predictions down first. Haughton (Devon Island, ~23 km) is so eroded that the elevation data shows no closed bowl at all, not even 10 m deep in a 65 × 67 km window. At Askja (Iceland) the caldera lake is a flat water surface in the elevation model, so the depth is measured from the water: 48 m, under our 50 m minimum. That tells us exactly what the method cannot see: eroded craters and bowls filled by a lake or sediment; the fixes are listed for the next version, not tuned in.
2. **Why no machine learning?** No labelled list of good lunar analogs exists, so a model would only copy the hand-picked ones; we measure physical values with the same code on both worlds, so every score traces back to metres, degrees or hours of sunlight.
3. **Did you search the whole planet?** No: about 265,000 cells in 11,604 of 19,433 one-degree land tiles, deserts first, in one night; the same command resumes for the rest.
4. **Then why trust the ranking?** It flags known impact craters, incl. Pingualuit in the world search, its bowl finder also picked up open-pit mines (which we filter out), and every score opens in the app down to the raw value next to the Moon value.
5. **Why can no place on Earth match the light?** The Sun's highest elevation depends only on latitude and axial tilt: at Shackleton it never rises above 1.9°, on Earth it reaches at least 23.4°, even at the poles.

---

## Sources for every number (no number added beyond these)

| Number | Source |
|---|---|
| ~265,000 cells searched; 11,604 of 19,433 tiles | `docs/PITCH_OUTLINE.md`, `docs/JURY_FAQ.md` (264,896); the app's funnel shows 264,921, so we say "about 265,000" |
| 15 km cells ≈ Artemis III candidate region | `docs/FACT_CHECK.md` (NASA, Aug 2022) |
| 1,825 crater-like places scored; 111 mines; 1,261 ranked; Chuquicamata, Escondida | `docs/MORNING_REPORT.md`, `outputs/README.md` |
| Known impact craters flagged, incl. Pingualuit in the world search | `outputs/scores.csv` `IMPACT_CRATER` = 1 (Pingualuit, `night_polar`; later excluded as "not a dry bowl"); list of 88 structures, `outputs/README.md` |
| Demo place: 54 km SW of Bardaï (Tibesti, Chad), 48 %, closest lunar twin Shackleton; steep walls 27.4° vs 27.2°, flat base spot 1.1° vs 0.7° | `outputs/scores.csv` (`SCORE_TOTAL` 0.4803, `BEST_TARGET` shackleton); app datasheet |
| Two Artemis III-region craters (de Gerlache rim, Haworth) | `docs/MULTI_TARGET.md` |
| 20 mare cells, SLDEM2015 | `docs/MULTI_TARGET.md`, `docs/MARE_V11.md` |
| No place high on both terrain and light | app scatter (1,261 ranked places); `docs/JURY_FAQ.md` |
| Shackleton floor always in shadow; typical Earth floor 16.5 % | `docs/JURY_FAQ.md` (median over the 1,825 night-run places, before the mine filter) |
| Mare: flat ground common | `docs/MORNING_REPORT.md` (top 10 Mare all 0.994–0.996) |
| 1 of 500 Earth Mare places reaches the Moon's small-crater density | `docs/MARE_V11.md` (c30: 1 place reaches the median of the 20 lunar cells) |
| Haughton eroded (no closed depression ≥ 10 m, 65 × 67 km window); Askja 48 m < 50 m | `docs/VALIDATION_config-v1.md`, `outputs/scores.csv` `MISSED_REASON` |
| Lanzarote: 0 of 16 cells pass the filter (sea, 2 km buffer around villages and resorts) | `docs/MARE_V11.md` |
| 1.9° at Shackleton, ≥ 23.4° on Earth | `docs/JURY_FAQ.md`, `docs/FACT_CHECK.md` |

## Images and video
- Earthrise: NASA / Apollo 8 (AS08-14-2383), file from the app (`app/assets/`).
- Globes on slide 3: rendered by `pitch/render_globes.py` from the app's textures, NASA Blue Marble Next Generation
  and NASA SVS CGI Moon Kit (LRO). Gold dot = the demo place (Tibesti), teal dot = Shackleton.
- `pitch/img/demo.mp4`: screencast of the live app (headless Chrome, 1920×1080), the click path above. The slow
  software-rendered 3D flight is sped up; it starts after the click, so the globe legend is not shown.
- Funnel and scatter: screenshots of the app (15 Nov 2026).
- QR code (slide 7) → https://tlcaspars.github.io/EspaceOdyssey/app/
