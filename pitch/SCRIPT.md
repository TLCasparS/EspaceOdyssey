# Moon Twins on Earth: 3-minute pitch script

Two speakers. **Speaker A = Caspar** (slides 1–4), **Speaker B = Sofi** (slides 5–7).
Spoken words: **344** in total (~125 words per minute → about **2:45**). Target: 2:50 at most.
The same text is in the speaker notes of `Moon_Twins_on_Earth.pptx`.

| Slide | Speaker | Words | Target |
|---|---|---|---|
| 1 Title | A (Caspar) | 29 | 0:14 |
| 2 The question | A (Caspar) | 48 | 0:23 |
| 3 Method | A (Caspar) | 65 | 0:31 |
| 4 The search | A (Caspar) | 52 | 0:25 |
| 5 Results | B (Sofi) | 46 | 0:22 |
| 6 What we learned | B (Sofi) | 60 | 0:29 |
| 7 Limits + try it | B (Sofi) | 44 | 0:21 |
| **Total** | | **344** | **2:45** |

---

### Slide 1: Title · Speaker A (Caspar) · 0:14
Hi, we are Team EspaceOdyssey. This is Earthrise, photographed by Apollo 8 from lunar orbit. Today we turn that view around: we look for the Moon's twins on Earth.

### Slide 2: The question · Speaker A (Caspar) · 0:23
Before astronauts build a base on the Moon, they rehearse on Earth. But today's analog sites were picked by eye, and nobody measured how Moon-like they really are. So we asked: where on Earth can we rehearse a Moon base? And we searched systematically, with open data only.

### Slide 3: Method · Speaker A (Caspar) · 0:31
On the Moon we measured Shackleton crater at the south pole and two craters in Artemis III landing regions, from NASA's LOLA elevation and PGDA light data. For mare plains we used SLDEM2015. On Earth we used the Copernicus elevation model and ESA WorldCover. Same code on both worlds, on the same 60-metre grid. Every criterion gets a score: one means identical to the Moon.

### Slide 4: The search · Speaker A (Caspar) · 0:25
In one night we searched about 265,000 cells of 15 kilometres, the size of an Artemis III landing region. 1,825 crater-like places were scored. Our bowl finder was so good it also found 111 open-pit mines, like Chuquicamata and Escondida. We filter them out. That leaves 1,261 ranked places. Sofi, the results.

> **HANDOVER → Sofi** (Caspar says "Sofi, the results." and steps back; Sofi clicks to slide 5.)

### Slide 5: Results · Speaker B (Sofi) · 0:22
Here is the map. Number one is a bowl in the Tian Shan mountains in China: 60 percent similar, and its closest lunar twin is Shackleton itself. Its walls are as steep as Shackleton's. Meteor Crater, a known training site we used for tuning, ranks tenth.

### Slide 6: What we learned · Speaker B (Sofi) · 0:29
Three lessons. One: places shaped like Shackleton are not lit like Shackleton. No place scores high on both. Two: Earth has no grazing Sun. Shackleton's floor is always in shadow; a typical Earth crater floor only 16.5 percent of the time. Three: for mare plains, flat ground is easy to find, but basalt and the Moon's small craters are rare.

### Slide 7: Limits + try it · Speaker B (Sofi) · 0:21
We also show what we miss. Haughton is too eroded. At Askja, the lake makes the caldera look too shallow. Lanzarote is mostly sea and villages. Every score is open in our app. Scan the code and find your own Moon twin. Thank you!

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
| Earthrise: NASA / Apollo 8, AS08-14-2383 | file from branch `app-hero` (`app/assets/earthrise-apollo8-as08-14-2383.jpg`) |

`[CHECK]` items: none on the slides. Team names are still the placeholder `[TEAM NAMES]` on slide 1.
