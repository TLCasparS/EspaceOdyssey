# Moon Twins on Earth: 3-minute pitch script (with live demo)

Team **EspaceOdyssey**: Caspar Schlageter, Sofi Sosa, Mateo Pozo.
Two speakers: **Speaker A = Caspar** (slides 1–4), **Speaker B = Sofi** (live demo + slides 5–7).
Spoken words: **304** (click cues in [brackets] not counted). At ~125 words per minute that is about
**2:26** of speech; the demo clicks and pauses fill the rest. Target: **2:50 at most**.
The same text is in the speaker notes of `Moon_Twins_on_Earth.pptx`.

| Slide | Speaker | Words | Target |
|---|---|---|---|
| 1 Title | A  | 29 | 0:12 |
| 2 The question | A  | 29 | 0:16 |
| 3 Method | A  | 54 | 0:25 |
| 4 The search | A  | 45 | 0:22 |
| 5 LIVE DEMO | B  | 64 | 0:50 |
| 6 What we learned | B  | 51 | 0:25 |
| 7 Limits + explore | B  | 32 | 0:14 |
| **Total** | | **304** | **2:44** |

## Before the pitch (demo setup)
- Open https://tlcaspars.github.io/EspaceOdyssey/app/ in a browser tab **before** you start, scroll past the
  Earthrise screen to the globe, and check the globe has loaded (it needs WebGL and the internet).
- Keep the slides in one window and the browser in another; switch with Alt+Tab.
- **If the demo fails:** stay on slide 5 and say the same words over the screenshot. It shows the same view.

---

### Slide 1: Title · Speaker A (Caspar) · 0:12
Hi, we are Caspar, Sofi and Mateo, team EspaceOdyssey. This is Earthrise, seen from Apollo 8. We turn the view around and look for the Moon's twins on Earth.

### Slide 2: The question · Speaker A (Caspar) · 0:16
Astronauts rehearse Moon missions on Earth. But today's analog sites were picked by eye, and nobody measured how Moon-like they are. So we searched systematically, with open data only.

### Slide 3: Method · Speaker A (Caspar) · 0:25
On the Moon: Shackleton crater at the south pole and two craters in Artemis III regions, from NASA's LOLA and PGDA data, plus mare plains from SLDEM2015. On Earth: the Copernicus elevation model and ESA WorldCover. Same code, same 60-metre grid. Every criterion scores from zero to one: one means identical to the Moon.

### Slide 4: The search · Speaker A (Caspar) · 0:22
In one night we searched about 265,000 cells, each the size of an Artemis III landing region. 1,825 crater-like places were scored. The finder was so good it found 111 open-pit mines, like Chuquicamata. We filtered them out: 1,261 places remain. Sofi will show you.

> **HANDOVER → Sofi.** Caspar says "Sofi will show you." Sofi clicks to slide 5 and switches to the browser.

### Slide 5: LIVE DEMO · Speaker B (Sofi) · 0:50
This is our app, live. Every dot on the globe is a ranked crater. [Click #1 in the list] Number one: a bowl in the Tian Shan mountains in China. 60 percent similar, and its closest lunar twin is Shackleton itself. Its walls are as steep as Shackleton's. [Scroll the card to 'What it lacks'] The card also says honestly where the analogy breaks. [Click Meteor Crater, #10] Meteor Crater, a known training site we used for tuning, ranks tenth. [Back to the slides]

### Slide 6: What we learned · Speaker B (Sofi) · 0:25
Three lessons. Shape twins are not light twins: no place scores high on both. Earth has no grazing Sun: Shackleton's floor is always in shadow, a typical Earth crater floor only 16.5 percent of the time. And for mare plains, flat ground is common, but basalt and small craters are rare.

### Slide 7: Limits + explore it yourself · Speaker B (Sofi) · 0:14
We also show what we miss: Haughton is eroded, Askja's lake hides its depth, Lanzarote is mostly sea and villages. Scan the code and explore it on your own phone. Thank you!

Leave slide 7 (the QR code) on screen during the questions.

---

## Five likely jury questions (one-line answers, from `docs/JURY_FAQ.md`)

1. **Why no machine learning?** No labelled list of good lunar analogs exists, so a model would only copy the hand-picked ones; we measure physical values with the same code on both worlds, so every score traces back to metres, degrees or hours of sunlight.
2. **Did you search the whole planet?** No: about 265,000 cells in 11,604 of 19,433 one-degree land tiles, deserts first, in one night; the same command resumes for the rest.
3. **Why did validation miss Haughton and Askja?** We froze all settings before testing: Haughton is too eroded to form a closed bowl in the elevation data, and Askja's lake makes the caldera only 48 m deep, under our 50 m minimum. That shows exactly what the method cannot see.
4. **Then why trust the ranking?** From elevation alone it found real impact craters it was never told about (Meteor Crater, Roter Kamm, Pingualuit) and even mines, and every score opens in the app down to the raw value next to the Moon value.
5. **Why can no place on Earth match the light?** The Sun's highest elevation depends only on latitude and axial tilt: at Shackleton it never rises above 1.9°, on Earth it reaches at least 23.4°, even at the poles.

---

## Sources for every number (no number added beyond these)

| Number | Source |
|---|---|
| ~265,000 cells searched; 11,604 of 19,433 tiles | `docs/PITCH_OUTLINE.md`, `docs/JURY_FAQ.md` (264,896); the app's funnel shows 264,921, so we say "about 265,000" |
| 15 km cells ≈ Artemis III candidate region | `docs/FACT_CHECK.md` (NASA, Aug 2022) |
| 1,825 scored; 111 mines; 1,261 ranked; Chuquicamata, Escondida | `docs/MORNING_REPORT.md`, `outputs/README.md` |
| Tian Shan #1, 60 % (0.6028), closest lunar twin Shackleton; walls 27.3° vs 27.2° | `outputs/scores.csv` (`RANK`, `SCORE_TOTAL`, `BEST_TARGET`); app card |
| Meteor Crater #10, 46 % (0.462), tuning site | `docs/MORNING_REPORT.md`, `outputs/scores.csv` |
| Two Artemis III-region craters (de Gerlache rim, Haworth) | `docs/MULTI_TARGET.md` |
| 20 mare cells, SLDEM2015 | `docs/MULTI_TARGET.md`, `docs/MARE_V11.md` |
| No place high on both terrain and light | app scatter (1,261 ranked places); `docs/JURY_FAQ.md` |
| Shackleton floor always in shadow; typical Earth floor 16.5 % | `docs/JURY_FAQ.md` (median over the 1,825 night-run places, before the mine filter) |
| Mare: flat ground common | `docs/MORNING_REPORT.md` (top 10 Mare all 0.994–0.996) |
| Small craters rare: 392 of 500 Earth places have none; all 20 lunar cells have some | `docs/MARE_V11.md` |
| Basalt rare: 0 of 500 basalt at the site | `docs/MACROSTRAT_REPORT.md` (coverage is partial: 208 places have no map unit) |
| Haughton eroded; Askja 48 m < 50 m | `docs/VALIDATION_config-v1.md`, `outputs/scores.csv` `MISSED_REASON` |
| Lanzarote: 0 of 16 cells pass the filter (sea, 2 km buffer around villages and resorts) | `docs/MARE_V11.md` |
| 1.9° at Shackleton, ≥ 23.4° on Earth | `docs/JURY_FAQ.md`, `docs/FACT_CHECK.md` |

## Images
- Earthrise: NASA / Apollo 8 (AS08-14-2383), file from the app (`app/assets/`).
- Globes on slide 3: rendered by `pitch/render_globes.py` from the app's textures, NASA Blue Marble Next Generation
  and NASA SVS CGI Moon Kit (LRO). Gold dot = Tian Shan (#1), teal dot = Shackleton.
- Funnel, scatter and demo backup: screenshots of the app (new layout, 15 Nov 2026), headless Chrome, 1920×1080.
- QR code (slide 7) → https://tlcaspars.github.io/EspaceOdyssey/app/
