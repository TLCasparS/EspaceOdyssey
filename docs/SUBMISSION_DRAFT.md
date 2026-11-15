# Submission draft (for the project page)

Task 1, **updated 15 Nov 2026 evening** with everything merged into `main` up to PR #41: new name, the filtered
ranking (mines and wet bowls removed), several lunar targets, access and research stations, rock at the site, the 3D
bowl ring, the Moon base to scale and the new app layout. Numbers are the same as the pitch (`pitch/SCRIPT.md`, which
lists the source of each number) and `outputs/` on `main`. All fields must be in English. Each section below is one
field of the project page, ready to paste. `[TEAM]` marks the few things only the team can fill in.

---

## Project Name
**Moon Twins on Earth**

Tagline: *Find the places on Earth that come closest to a lunar base site, and learn why.*

---

## High-Level Project Summary
Moon Twins on Earth is an open method and a web app that find the places on Earth that come closest to a planned
lunar base site, and show why. Today, Earth analog sites are mostly picked by eye. We measure them instead: the same
code reads NASA's lunar elevation and illumination data (Shackleton crater, two craters in Artemis III candidate
regions, and the lunar maria) and Earth's elevation data on the same 60 m grid, and turns every difference into a
0–100 % similarity. In one night it searched about 265,000 cells of 15 km and ranked 1,261 dry, crater-like places,
finding real impact craters from elevation alone. In the app, anyone can explore the ranking on two linked globes,
open a card per site (what matches, where the analogy breaks down, how to get there) and fly into the terrain. Our
main contribution is the method: it is repeatable, open, and built to scale to the rest of the planet and to new
lunar targets.

---

## Link to Project Demo
`[TEAM]` public link to the 7-slide deck (`pitch/Moon_Twins_on_Earth.pptx` exported to PDF or Google Slides, shared
without login). Test it in a private window.

## Link to Final Project
- App (live, no login): https://tlcaspars.github.io/EspaceOdyssey/app/
- Code, outputs and documentation: https://github.com/TLCasparS/EspaceOdyssey

---

## Detailed Project Description

### What it does
Moon Twins on Earth answers one question: which places on Earth best stand in for a lunar base site, and how close
are they? It measures each candidate against real lunar targets with the same definitions on both worlds, and it says
where the comparison fails.

- **Two base types.**
  - *Polar:* Shackleton crater at the lunar south pole (sunny rim, permanently shadowed floor), plus two small
    craters in Artemis III candidate regions (on the de Gerlache rim and in the Haworth region).
  - *Mare:* a typical mare plain (the median of 20 sample areas) plus four single maria, shown at the Apollo 11 site.
- **Closest lunar twin.** Every Earth place is scored against every lunar target of its base type, and the app says
  which lunar site it resembles most.
- **A ranked list and two linked 3D globes.** Pick a base on the Moon globe and the Earth globe turns to its closest
  twin. Each pin on Earth is a site you can open; a violet glow shows where many good craters cluster.
- **A card per site:**
  - a radar chart (the Moon is the full outer ring);
  - the criteria closest to the Moon and what the site lacks;
  - raw values side by side (for example "Steep walls 27.3° vs 27.2°");
  - **Access:** travel time to the nearest city, the nearest airport, the nearest research station within 500 km,
    and the nearest planetary analog station (such as the Mars Desert Research Station or HI-SEAS);
  - **On the ground:** land cover, confirmed impact crater, and the rock at the site from geological maps;
  - the facts no place on Earth can match.
- **A 3D close-up** of each site in real terrain and satellite imagery: the scored crater is outlined, with its floor
  and the base spot marked. A "Moon base to scale" view draws a lunar habitat and landing pad at true size on the
  ground, next to Shackleton's outline.
- **Honest misses.** Known analog sites the method did not find (Haughton, Askja, Tenoumer) have their own list,
  with the reason.

### Why it matters: learn, then discover
We built the app for people to **learn** what makes a good lunar base site and to **find new places on Earth**
themselves. A guide explains each step in plain words, and every score opens down to the measured value next to the
Moon value, so a student, a teacher or a field-campaign planner can see *why* a place ranks where it does. The
ranking also goes beyond the famous analog sites: our top places lie in the Tian Shan, the Pamirs, the Sahara, the
Danakil Desert and the Andes, and the app invites people to explore them, compare them and look for more.

### What is new: the method, and how it scales
- **One ruler for two worlds.** The same functions measure the Moon (NASA LOLA elevation and PGDA illumination) and
  Earth (Copernicus DEM) on the same 60 m grid: bowl shape, wall steepness, a flat pad for a base, roughness, and
  light (a year-long Sun simulation over each Earth crater, compared with the lunar illumination map). The analogy
  becomes a number that anyone can check, not an opinion.
- **A systematic search, not a list of known sites.** The planet is split into ~15 km cells (about the size of an
  Artemis III candidate region), filtered by land cover, and every closed bowl is measured. Filters run after scoring
  and never change a score: open-pit mines and wet, icy or vegetated bowls are flagged and left out of the ranking.
- **Built to scale.**
  - *More of Earth:* the night run covered 11,604 of 19,433 one-degree land tiles; the same command resumes for the
    rest.
  - *More lunar targets:* a new target is one set of lunar values. Every Earth place is re-scored against it without
    reading the terrain again; that is how the two Artemis III-region craters and the four maria were added.
  - *More criteria:* each criterion is its own function with its own tolerance; access, stations and rock type were
    added the same way, as context layers.
  - *Other worlds:* the same approach could take a Mars target from Mars elevation data (not done yet).
  - Open data and open code only, so anyone can rerun it, check it or extend it.

### How it works
1. **Lunar targets.** From NASA's LOLA south-pole elevation map (LDEM_80S_20MPP_ADJ, 20 m) we find Shackleton's bowl
   in the data: rim-crest diameter 20.9 km, rim-to-floor depth about 4.1 km, inner walls 27.2°, base-pad slope 0.66°.
   Light values come from NASA PGDA's illumination map (AVGVISIB, 60 m). The two Artemis III-region targets use the
   same code, centred with PGDA's high-resolution site maps. The Mare targets come from SLDEM2015.
2. **Earth search.** ~15 km grid cells. ESA WorldCover removes trees, cropland, built-up areas (with a 2 km buffer),
   water and wetlands; the Copernicus DEM (GLO-30) is reprojected to the same 60 m grid. A cell needs a closed bowl at
   least 50 m deep and 1 km wide.
3. **Score.** Each criterion becomes a similarity `exp(−((Earth − Moon) / tolerance)²)`; the total is their weighted
   mean. Criteria that can't be compared fairly are shown but not counted.
4. **Frozen before validation.** The scoring settings were frozen (git tags `config-v1`, `mare-v1`, guarded by tests)
   and our predictions were written down before the validation runs, so the results could not be tuned.
5. **Filters after scoring** (`config-v1.1`): mining polygons (Maus et al. 2022) and a dry-bowl test (WorldCover bare
   ground, snow and ice).
6. **Context layers** (shown in the card, never in a score): travel time, airports, research stations, rock type.
7. **Export and app.** `src/export_app.py` writes `outputs/`; the app is a static web page (HTML, JavaScript,
   globe.gl, MapLibre GL JS) with no build step, hosted on GitHub Pages.

### What we found
- **Scale.** About 265,000 cells of 15 km searched in one night (11,604 of 19,433 one-degree land tiles, deserts
  first). 1,825 crater-like places were scored. The bowl finder also found 111 open-pit mines (for example
  Chuquicamata). After removing mines and wet, icy or vegetated bowls, **1,261 places are ranked**.
- **Top twin:** a bowl in the Tian Shan mountains, China, 60 % similar. Its closest lunar twin is Shackleton itself,
  and its inner walls are as steep (27.3° vs 27.2°). Meteor Crater, a known training site we used for tuning, ranks
  10th (46 %).
- **It finds real craters from elevation alone.** The bowl finder knows nothing about impacts, yet ranked places
  include confirmed impact structures: Meteor Crater, Roter Kamm and Pingualuit.
- **Shape twins are not light twins.** No place scores high on both terrain and light.
- **Mare plains:** flat, Moon-like ground is common on Earth (the top 10 Mare places all score 99.4–99.6 %), but
  small craters and basalt are rare. 392 of 500 places have no small crater, while all 20 lunar sample areas have
  some; geological maps show basalt at none of the 500 sites (208 have no map unit). The app therefore shows Mare
  scores with one decimal and explains why they are so close.
- **Access:** 231 places have a research station within 500 km.

### Where the analogy breaks down
- **No grazing Sun on Earth.** At Shackleton the Sun climbs at most 1.9° above the horizon; on Earth it reaches at
  least 23.4°, even at the poles. Shackleton's floor is always in shadow, a typical Earth crater floor only 16.5 % of
  the time.
- Earth cannot reproduce the Moon's low gravity, vacuum or radiation, or the Mare's day–night temperature swing of
  about 290–300 K (LRO Diviner).
- **What the method misses, shown on purpose:** Haughton crater (too eroded to form a closed bowl in the elevation
  data), Askja (its lake makes the caldera only 48 m deep, under our 50 m minimum), Tenoumer (44 m), and Lanzarote
  (all 16 cells removed: sea, villages and resorts).
- NASA Earth data plays a small part: Earth terrain and land cover come from ESA/Copernicus, while NASA data defines
  the lunar side.

### Benefits
- A repeatable, open way to compare Earth sites with a lunar target, criterion by criterion, instead of by eye.
- It shows both sides, what matches and what doesn't, so a team can choose a site for the property it wants to test
  (steep walls, a flat landing pad, rough ground, deep shadow) and see how easy it is to reach.
- A learning tool: anyone can explore the Moon and Earth side by side in a browser, without installing anything.
- New candidate places beyond the well-known analog sites, each with its measured evidence.

### What we hope to achieve
Search the rest of Earth; add more lunar targets (more Artemis III regions, lava tubes, then Mars); bring rock type
into the Mare score once site-level maps cover enough places; and give analog-campaign, rover and education teams a
short list of field sites for their lunar site, with the limits stated. We would also like people to send back what
they find on the ground, so the ranking can be checked against reality.

### Tools
- **Python:** NumPy, SciPy, rasterio, pyproj, GeoPandas, pandas, PyYAML, pystac-client, Planetary Computer client,
  Matplotlib, Plotly, pytest.
- **Web:** JavaScript, HTML and CSS with globe.gl 2.32.0 and MapLibre GL JS 4.7.1.
- **Data access:** AWS Open Data, NASA PGDA, PANGAEA, the Macrostrat API.
- **Other:** Git, GitHub and GitHub Pages. Hardware: `[TEAM]` (for example: personal laptops).

---

## Use of Super Intelligence (SI)
> Yes. We used an SI assistant, Claude (Anthropic), mainly through Claude Code, as a coding and writing helper.
> **Code:** it helped write parts of the pipeline (for example the light simulation, terrain and DEM modules, the
> lunar target and Mare scripts, the filters and the export) and the web app. Team members reviewed and tested this
> code; commits it helped with carry a `Co-Authored-By: Claude` line, and `AI_USAGE.md` lists each use with how it
> was checked. **Text:** it drafted documentation, the site notes in the app (checked against the linked sources)
> and first drafts of the pitch and of this submission. **Data:** all scores come from our pipeline run on the open
> datasets listed below. **Images, video, audio:** none are SI-generated; the globes, terrain and imagery are real
> NASA, ESA/EOX and AWS data, and the opening photo is NASA's Earthrise. The idea, the criteria and the decisions are
> the team's. The app states this in its footer.
> `[TEAM: confirm, and add any other SI tools you used]`

---

## NASA Data
- **LOLA south-pole elevation, LDEM_80S_20MPP_ADJ** (Barker et al. 2023), NASA PGDA product 90:
  https://pgda.gsfc.nasa.gov/products/90. Defines the Polar targets (shape, walls, base pad).
- **Lunar south-pole illumination, AVGVISIB_85S_060M_201608** (Mazarico et al. 2011), NASA PGDA product 69:
  https://pgda.gsfc.nasa.gov/products/69. Lunar side of the light criteria.
- **High-resolution LOLA topography for lunar south pole sites** (M. K. Barker), NASA PGDA product 78:
  https://pgda.gsfc.nasa.gov/products/78. Centres of the Artemis III candidate regions.
- **Artemis III candidate landing regions**, NASA release 22-089, 19 Aug 2022:
  https://www.nasa.gov/news-release/nasa-identifies-candidate-regions-for-landing-next-americans-on-moon/
- **SLDEM2015** (LOLA + JAXA SELENE/Kaguya Terrain Camera; Barker et al. 2016), NASA PGDA product 54:
  https://pgda.gsfc.nasa.gov/products/54. Mare targets.
- **LRO Diviner** surface temperatures (Williams et al. 2017, Icarus, doi:10.1016/j.icarus.2016.08.012): the Mare
  day–night swing.
- **Apollo landing-site coordinates** (Wagner et al. 2017, Icarus 283, 92–103): position of the Mare marker.
- **Lunar surface habitat size** (Burke, Howard & Kessler 2022, "Internal layout of a lunar surface habitat", NASA):
  https://ntrs.nasa.gov/citations/20220013669. Habitat in the "Moon base to scale" view.
- **Blue Marble Next Generation**, July 2004 (NASA Earth Observatory): Earth globe image,
  https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/
- **CGI Moon Kit** (NASA Scientific Visualization Studio, from LRO LROC WAC data): Moon globe image,
  https://svs.gsfc.nasa.gov/4720
- **Earthrise, Apollo 8** (NASA, AS08-14-2383): opening photo of the app,
  https://images.nasa.gov/details/as08-14-2383

## Space Agency Partner Data and Other References
**Space agency partner data**
- **Copernicus DEM GLO-30 / GLO-90** (ESA, Copernicus programme), via AWS Open Data:
  https://registry.opendata.aws/copernicus-dem/
- **ESA WorldCover 2021 v200** (10 m land cover, CC BY 4.0): https://worldcover2021.esa.int and
  https://registry.opendata.aws/esa-worldcover-vito/
- **JAXA SELENE (Kaguya) Terrain Camera**, inside SLDEM2015 (above).

**Other data**
- **Global-scale mining polygons v2** (Maus et al. 2022, PANGAEA, CC BY-SA 4.0), mine filter:
  https://doi.org/10.1594/PANGAEA.942325; paper: Scientific Data 9, 433 (2022).
- **Macrostrat** geological map units (rock at the site, CC BY 4.0): https://macrostrat.org
- **GLiM, Global Lithological Map** (Hartmann & Moosdorf 2012, 0.5° grid, CC BY 3.0), regional rock class:
  https://doi.org/10.1594/PANGAEA.788537; paper: doi:10.1029/2012GC004370.
- **Travel time to cities** (Weiss et al. 2018, Nature 553, 333–336, doi:10.1038/nature25181; Malaria Atlas
  Project, CC BY): https://malariaatlas.org
- **OurAirports** airport list: https://ourairports.com/data/
- **INTERACT GIS station list**, interact-gis.org, accessed 15 Nov 2026: research stations.
- **Planetary analog stations** (Haughton-Mars Project, FMARS, MDRS, HI-SEAS, Biosphere 2, LunAres): positions from
  marsinstitute.no and Wikipedia.
- **GeoNames** `cities1000` (CC BY 4.0), place names: https://www.geonames.org
- **Natural Earth** 1:10m Admin 0 (public domain), countries: https://www.naturalearthdata.com
- **OpenStreetMap** (Overpass API, ODbL), to check the names of filtered mines: https://www.openstreetmap.org
- Wikipedia, "List of impact craters on Earth" (confirmed impact structures, CC BY-SA 4.0):
  https://en.wikipedia.org/wiki/List_of_impact_craters_on_Earth
- **Landing pad size** (Metzger & Autry 2022, "The cost of lunar landing pads"): https://arxiv.org/abs/2205.00378
- **Terrain Tiles on AWS** (Mapzen; SRTM, GMTED, ETOPO1 and others), 3D view elevation:
  https://registry.opendata.aws/terrain-tiles/
- **Sentinel-2 cloudless 2016** by EOX IT Services GmbH (contains modified Copernicus Sentinel data 2016, CC BY 4.0),
  3D view imagery: https://s2maps.eu
- Site notes: sources linked per site in `app/sample/site_info.json`.

**Software**
- globe.gl 2.32.0 and MapLibre GL JS 4.7.1, loaded from unpkg.
- Python: NumPy, SciPy, rasterio, pyproj, GeoPandas, pandas, PyYAML, pystac-client, planetary-computer, Matplotlib,
  Plotly, pytest.
- Our code: https://github.com/TLCasparS/EspaceOdyssey

**Methods and references**
- Team criteria document: `docs/Moon Analog Criteria and Datasets.md` (29 criteria, data sources and caveats).
- Validation: `docs/VALIDATION_config-v1.md`; filters: `config/post_filters.yaml`; several lunar targets:
  `docs/MULTI_TARGET.md`; access and stations: `docs/ACCESS.md`.

---

## Before pasting (team)
- **Demo link:** public deck link, tested in a private window.
- **Images:** 1–3 app screenshots for the page (for example `pitch/img/app_map_tianshan.png`, `pitch/img/app_card.png`).
- **OurAirports licence:** `docs/ACCESS.md` could not open ourairports.com/data first-hand; open it once and confirm.
- **Licence for our code:** there is no `LICENSE` file yet. Without one, NASA distributes our code under Apache 2.0.
- **At submission:** the two tick boxes (Terms; original work with all resources listed in References), the
  China-review question and the SI confirmation are answered by the team.
