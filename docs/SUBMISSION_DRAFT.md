# Submission draft (for the project page)

Draft by an AI agent (Task 1), for the team to edit. **Updated 15 Nov 2026 morning with the night-run numbers**
from `outputs/night_export/` (export of 15 Nov, 02:43), the same numbers as `docs/PITCH_OUTLINE.md` (which says
how each was computed). Lunar values from `config/lunar_targets.json`; validation from
`docs/VALIDATION_config-v1.md`. `[TEAM]` marks what only the team knows; `[TEAM: mine filter]` waits for the
open-pit-mine filter. Checklist and sources: `docs/SUBMISSION_CHECKLIST.md`. All fields must be in English.

---

## Project Name (options)
No NASA / Space Apps names or mission identifiers in the title (SI branding rule).

1. **Earth Twins of the Moon** (current name in the app; the team chose to keep it)
2. Moon Twins on Earth: ranking where to rehearse a lunar base
3. Lunar Analog Finder: measuring how Moon-like a place on Earth is
4. Shackleton's Twins: Earth craters ranked against the lunar south pole
5. One Ruler, Two Worlds: Earth analogs for lunar bases

Tagline (for the cover slide): *Which places on Earth come closest to a lunar base site, and how close?*

---

## High-Level Project Summary (~150 words)
We built a pipeline and a web app that rank places on Earth by how closely they match a planned lunar base site.
The reference is Shackleton crater at the lunar south pole: from NASA's LOLA elevation map we measure its bowl
shape, wall steepness and flat ground, and from NASA's illumination map its sunny rim and shadowed floor. The same
code then measures Earth (Copernicus DEM) on the same 60 m grid and turns each difference into a 0–100 % similarity.
In one night it searched about 265,000 grid cells of 15 km and ranked 1,825 crater-like places; from elevation
alone it found real impact craters such as Meteor Crater, Roter Kamm and Pingualuit. The app shows the results on
two linked globes, Earth and Moon, with a card per site that says what matches and where the analogy breaks down,
to help pick Earth field sites for testing equipment and operations.

---

## Link to Project Demo
`[TEAM]` public link to the 7-slide deck (PDF or Google Slides, no login). Test it in a private window.

## Link to Final Project
- Code and data: https://github.com/TLCasparS/EspaceOdyssey
- App (live, no login): https://tlcaspars.github.io/EspaceOdyssey/app/ (GitHub Pages from `main`; nobody merges
  to `main` after 23:59 CET)

---

## Detailed Project Description

### What it does
Earth Twins of the Moon answers one question: which places on Earth best stand in for a lunar base site, and by
how much? Instead of choosing analog sites by eye, it measures each candidate against a real lunar target with the
same definitions on both worlds, and it says where the comparison fails.

- **Two base types.** *Polar*: Shackleton crater, near the lunar south pole (sunny rim, permanently shadowed floor).
  *Mare*: a typical mare plain, summarised from 20 sample areas across four maria, shown at the Apollo 11 site.
- **A ranked list of Earth twins** with one similarity score each.
- **Two linked 3D globes.** Pick a base on the Moon globe and the Earth globe turns to its closest independent twin;
  a heatmap shows where the scored craters are, outlines show every region we searched, including the ones where
  nothing was found.
- **A card per site**: a radar chart (the Moon is the full outer ring), the closest criteria and what the site
  lacks, raw values side by side ("Steep walls 23.9° vs 27.2°"), ground values (drivable, bare ground, snow and ice,
  confirmed impact structure) and the facts no place on Earth can match.
- **A 3D close-up** of each site in real terrain and satellite imagery, with its values next to it.

### How it works
1. **Lunar target.** `src/compute_lunar_target.py` reads NASA's LOLA south-pole elevation map
   (LDEM_80S_20MPP_ADJ, 20 m) in a ±35 km window, resamples it to a 60 m grid and finds Shackleton's bowl from the
   data. Measured: rim-crest diameter 20.9 km, rim-to-floor depth about 4.1 km, inner walls 27.2°, depth/width
   0.197, base-pad slope 0.66°. Light values come from NASA PGDA's modelled illumination map (AVGVISIB, 60 m).
   The Mare target is the median of 20 lunar mare cells from SLDEM2015 (relief 154 m within 5 km, flattest pad
   0.24°, drivable ground 99.3 %, roughness 1.7 m), with tolerance = max(IQR, floor).
2. **Earth search.** Regions are split into ~15 km grid cells. ESA WorldCover removes trees, cropland, built-up
   areas (with a 2 km buffer), water and wetlands; the Copernicus DEM (GLO-30) is reprojected to the same 60 m metric grid. A cell needs a closed bowl
   at least 50 m deep, 1 km wide and not too elongated.
3. **Same ruler on both worlds.** The same functions compute every criterion on Earth and on the Moon: bowl shape,
   inner-wall slope, base-pad slope, roughness, and light (sunny ridge, dark floor, light next to dark) from a
   year-long Sun simulation over the Earth DEM vs the lunar illumination map.
4. **Score.** Each criterion becomes a similarity `exp(−((Earth − Moon) / tolerance)²)`; the total is their
   weighted mean. Criteria that can't be compared fairly are shown but not counted (e.g. sky-view, relief, the
   Sun's height).
5. **Frozen and tested.** The scoring settings were frozen (git tags `config-v1`, `mare-v1`, guarded by tests)
   before validation, so the validation regions could not be tuned.
6. **Export and app.** `src/export_app.py` writes `outputs/` (scores, raw values, lunar targets, heatmap, searched
   cells); the app is a static web page (HTML, JavaScript, globe.gl, MapLibre GL JS), no build step.

### What we found (night run, 14–15 Nov)
- **Scale.** 264,896 grid cells of 15 km searched in one night: 11,604 of the 19,433 1° land tiles, deserts first,
  not yet the whole planet. Funnel: 11,932 out at the coarse land-cover prescreen, 202,422 with no bowl at 90 m,
  41,699 removed by land cover / water / towns, 6,909 with no bowl at 30 m, 109 with an ice-filled floor, leaving
  **1,825 places ranked against Shackleton** `[TEAM: mine filter: how many remain]`.
- **It finds real craters from elevation alone.** The bowl detector knows nothing about impacts; afterwards three
  ranked places match the list of confirmed impact structures: Meteor Crater, Roter Kamm and New Quebec /
  Pingualuit (the list has 88 structures and is incomplete).
- **It also finds open-pit mines**, because they are perfect closed bowls; we filter them `[TEAM: mine filter]`.
- **Known craters for scale:** Meteor Crater 44 % (rank 45; a tuning site, so not an independent result), the best
  Pinacate maar 40 %, Al Wahbah 27 %, Roter Kamm 24 %, Pingualuit 20 %. Top overall: `[TEAM: after mine filter]`.
- **Terrain twins and light twins are different places.** Of the 50 best places by terrain and the 50 best by light,
  only 5 are the same (rank correlation 0.06 over all 1,825). The best light twins lie further from the equator and
  in deep mountain bowls.
- **Mare:** 500 flat places were measured against the lunar mare target, and half of them score 97 % or more:
  flat, Moon-like ground is common on Earth, so terrain alone does not separate places. Rock type (basalt) has to
  come in before a Mare ranking means much.
- **Where the analogy breaks down.** No place on Earth has the Moon's grazing Sun: at Shackleton the Sun climbs at
  most 1.9° above the horizon, on Earth never less than 23.4° (lowest among our 1,825 places: 31.8°, at 81.6° N).
  So Shackleton's floor is always in shadow, while a typical Earth crater floor is in shadow 16.5 % of the time
  and only 2 of the 1,825 places reach 90 %. Earth also cannot reproduce the Moon's low gravity, vacuum or
  radiation, or the Mare's day–night temperature swing of about 290–300 K (LRO Diviner).
  Light is measured as the visible part of the Sun's disc on the Moon and as the Sun's centre on Earth; both agree
  on flat ground but can differ a little on rims and floors.
- **Honest validation** (`docs/VALIDATION_config-v1.md`, predictions written before the runs):
  Haughton crater (Devon Island) was not found: it is too eroded to form a closed bowl in the DEM. In Iceland,
  976 cells gave one weak match (22.5 %); Askja's caldera lake was missed because its depth is measured from the
  water surface (48 m, below our 50 m minimum). Tenoumer crater (Mauritania) was missed for the same reason (44 m).
  The app shows these misses on purpose.

### Benefits
- A repeatable, open way to compare Earth sites with a lunar target, criterion by criterion, instead of by eye.
- It shows both sides: what matches and what doesn't, so a team can choose a site for the property they want to
  test (bowl shape, steep walls, flat landing pad, rough ground).
- Everything uses open data and open code; anyone can rerun it on new regions.

### What we hope to achieve
Run the search over the rest of Earth (the night run covered 11,604 of 19,433 1° land tiles), add more lunar
targets (10 Artemis-region polar candidates and 4 per-mare targets are computed and waiting for review; scoring
against several targets is built), add rock type for the Mare base and lava tubes, and give analog-campaign and rover teams a short list of field sites that match
their landing site best, with the limits stated.

### Tools
Python (NumPy, SciPy, rasterio, pyproj, GeoPandas, pandas, PyYAML, pystac-client, Planetary Computer client,
Matplotlib, Plotly, pytest); JavaScript, HTML and CSS with globe.gl 2.32.0 and MapLibre GL JS 4.7.1; data read
directly from AWS Open Data and NASA PGDA; Git and GitHub. `[TEAM]` hardware: personal laptops.

---

## Use of Super Intelligence (SI)
Not shown to the judges, but the same text belongs in the project (README / app footer).

> Yes. We used an SI assistant, Claude (Anthropic), mainly through Claude Code, as a coding and writing helper.
> **Code:** it helped write parts of the pipeline (for example the light simulation, DEM fetching and terrain
> modules, the lunar target and Mare scripts, the export) and the web app (`index.html`, `style.css`, `app.js`).
> Team members reviewed and tested this code; commits it helped with carry a `Co-Authored-By: Claude` line, and
> `AI_USAGE.md` lists each use with how it was checked. **Text:** it drafted documentation, the site notes in the
> app (checked against the linked sources) and a first draft of this submission text. **Data:** all scores come
> from our pipeline run on the open datasets listed below; the optional `?sample` view of the app uses fake values
> made by a script and is labelled "Fake data". **Images, video, audio:** none are SI-generated; the globes, terrain
> and imagery are real NASA, ESA/EOX and AWS data. The idea, the criteria and the decisions are the team's
> `[TEAM: confirm, and add any other SI tools you used]`. The app states this in its footer and in an
> `ai-assistance` meta tag.

---

## NASA Data
- **LOLA south-pole elevation, LDEM_80S_20MPP_ADJ** (Barker et al. 2023), NASA PGDA product 90:
  https://pgda.gsfc.nasa.gov/products/90. Defines the Polar target (Shackleton's shape, walls, base pad).
- **Lunar south-pole illumination, AVGVISIB_85S_060M_201608** (Mazarico et al. 2011), NASA PGDA product 69:
  https://pgda.gsfc.nasa.gov/products/69. Lunar side of the light criteria.
- **SLDEM2015** (LOLA + JAXA SELENE/Kaguya Terrain Camera; Barker et al. 2016), NASA PGDA product 54:
  https://pgda.gsfc.nasa.gov/products/54. Mare target from 20 sample areas.
- **LRO Diviner** surface temperatures (Williams et al. 2017, Icarus, doi:10.1016/j.icarus.2016.08.012): the Mare
  day–night swing fact.
- **Apollo landing-site coordinates** (Wagner et al. 2017, Icarus 283, 92–103): position of the Mare marker.
- **NASA Moon Fact Sheet** (NSSDC): lunar equator tilt for the Sun's maximum height. `[check link]`
- **Blue Marble Next Generation**, July 2004 (NASA Earth Observatory): Earth globe image,
  https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/
- **CGI Moon Kit** (NASA Scientific Visualization Studio, from LRO LROC WAC data): Moon globe image,
  https://svs.gsfc.nasa.gov/4720

## Space Agency Partner Data and Other References
**Space agency partner data**
- **Copernicus DEM GLO-30 / GLO-90** (ESA, Copernicus programme), read from AWS Open Data:
  https://registry.opendata.aws/copernicus-dem/
- **ESA WorldCover 2021 v200** (10 m land cover, CC BY 4.0): https://worldcover2021.esa.int and
  https://registry.opendata.aws/esa-worldcover-vito/
- **JAXA SELENE (Kaguya) Terrain Camera**, inside SLDEM2015 (above).

**Other data**
- Wikipedia, "List of impact craters on Earth" (confirmed impact structures, display only):
  https://en.wikipedia.org/wiki/List_of_impact_craters_on_Earth (text CC BY-SA 4.0)
- Terrain Tiles on AWS (Mapzen; SRTM, GMTED, ETOPO1 and others), 3D view elevation:
  https://registry.opendata.aws/terrain-tiles/ (licence/attribution: `[check]`)
- Sentinel-2 cloudless 2016 by EOX IT Services GmbH (contains modified Copernicus Sentinel data 2016), 3D view
  imagery: https://s2maps.eu, CC BY 4.0 (we use the 2016 layer because EOX's 2018–2025 layers are non-commercial)
- Travel time to cities (card "Access" line, display only): Weiss, D.J. et al. (2018), Nature 553, 333–336,
  doi:10.1038/nature25181; data from the Malaria Atlas Project (CC BY; `docs/ACCESS.md`)
- Nearest airport (card "Access" line): OurAirports `airports.csv`, https://ourairports.com/data/ (public domain
  according to third-party pages; `[TEAM: open ourairports.com/data once and confirm]`, see `docs/ACCESS.md`)
- Site notes: sources linked per site in `app/sample/site_info.json`.

**Software**
- globe.gl 2.32.0 (`[check licence]`), MapLibre GL JS 4.7.1 (`[check licence]`), loaded from unpkg.
- Python: NumPy, SciPy, rasterio, pyproj, GeoPandas, pandas, PyYAML, pystac-client, planetary-computer,
  Matplotlib, Plotly, pytest.
- Our code: https://github.com/TLCasparS/EspaceOdyssey (licence: `[TEAM]`, see checklist open point 3).

**Methods and references**
- Team criteria document: `docs/Moon Analog Criteria and Datasets.md` (29 criteria, data sources and caveats).
- Validation report: `docs/VALIDATION_config-v1.md`.

---

## Slide notes (7-slide limit)
The deck skeleton already has exactly 7 slides; keep it at 7. Before submitting:
- Team slide: full names `[TEAM]`, Mateo's role `[TEAM]`.
- App slide: one real screenshot (globe + card, or a crater in 3D).
- Results slide: night-run numbers above (same as `docs/PITCH_OUTLINE.md`); keep the "Honest limits" card.
- Last slide: hosted app link and repo link; the AI-use line.
- No logos, no photos of people, no AI-generated images.
