# Submission draft (for the project page)

Task 1, **updated 15 Nov 2026 evening** (summary and detailed description: the team's final wording) with everything merged into `main` up to PR #41: new name, the filtered
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
Moon Twins on Earth is an open method and web app that finds the places on Earth closest to a planned lunar base
site, and shows why. Earth analog sites are usually picked by eye; we measure them. The same code reads NASA lunar
elevation and illumination data (Shackleton crater, two craters in Artemis III candidate regions, and the lunar maria)
and Earth elevation data on one 60 m grid, turning every difference into a 0–100 % similarity. In one night it
searched about 265,000 cells and ranked 1,261 dry, crater-like places, finding real impact craters from elevation
alone. In the app, anyone can explore the ranking on two linked globes, open a card for each site (what matches,
where the analogy breaks down, how to get there) and fly into the 3D terrain. It is made for people to learn what
makes a good base site and to discover new places beyond the famous analog sites. Our main contribution is the
method: repeatable, open, and built to scale to the whole planet and new lunar targets.

---

## Link to Project Demo
`[TEAM]` public link to the 7-slide deck (`pitch/Moon_Twins_on_Earth.pptx` exported to PDF or Google Slides, shared
without login). Test it in a private window.

## Link to Final Project
- App (live, no login): https://tlcaspars.github.io/EspaceOdyssey/app/
- Code, outputs and documentation: https://github.com/TLCasparS/EspaceOdyssey

---

## Detailed Project Description
Moon Twins on Earth is an open, reusable pipeline that measures how Moon-like a place on Earth is and ranks the best
Earth stand-ins ("twins") for candidate lunar base sites. Analog sites have mostly been chosen by eye. Our method can
be rerun and extended: for any lunar site, it finds the places on Earth that come closest, shows how close they are,
and says where the comparison breaks down. Our ranking and our web app are the first results built on it; we want the
pipeline itself to be the base that others build on.

### What it does and how it works

**The pipeline: one ruler for two worlds**
1. **Moon target.** The lunar site is measured from NASA data with the same code used for Earth. For Shackleton
   crater, the pipeline finds the bowl in NASA's 20 m LOLA south-pole elevation map: 20.9 km wide, about 4.1 km deep,
   inner walls 27.2°. NASA PGDA illumination maps give the sunlit rim and the permanently dark floor. SLDEM2015
   (LOLA + JAXA Kaguya) gives the mare plains.
2. **Earth search.** Any region, or the whole land surface, is split into cells of about 15 km, the size of an
   Artemis III landing region. ESA WorldCover removes forest, cropland, water, wetlands and towns (with a 2 km
   buffer). The Copernicus 30 m elevation model is reprojected to the same 60 m metric grid as the Moon. All data
   streams directly from AWS Open Data, with no manual downloads.
3. **Measure.** Each criterion is one function, applied the same way to Earth and Moon: bowl shape, steep walls, a
   flat landing pad, roughness, drivable ground, and light (sunny ridge, dark floor, light next to dark). On Earth,
   light comes from simulating a full year of Sun over the terrain. Raw values are stored.
4. **Score.** Each criterion becomes a similarity, `exp(−((Earth − Moon) / tolerance)²)`, where 1 means identical to
   the Moon; the total is a weighted mean. Because scoring is a separate step, a new lunar target is scored against
   every Earth place already measured, without recomputing the terrain.
5. **Filter.** Post-filters remove known false matches: open-pit mines (global mining polygons) and icy, wet or
   vegetated bowls. A filter never changes a score.
6. **Export.** Plain CSV and JSON files in a documented format, read by our app and by any other tool.

**Built to be reused**
- **New region:** one command with a bounding box (`run_pipeline.py --bbox W S E N`). The world search runs overnight
  on one laptop and picks up where it stopped.
- **New lunar site:** add its measured values to a config file; the next export scores every Earth place against it.
  That is how we added two smaller craters in Artemis III regions (de Gerlache rim, Haworth) and four individual maria
  next to Shackleton and the mare median.
- **New criterion:** add one function and a weight. Our criteria document lists 29 criteria; the app shows a
  criterion as soon as the export has data for it.
- **Settings** (thresholds, weights, tolerances) live in config files, not in the code. They are frozen with git tags
  and guarded by automated tests, so a change shows up as a new version instead of silently changing results.
- **Mars** is the natural next step: the Earth side stays as it is; a Mars target needs a reader for Mars elevation
  data and Mars-specific criteria.

**What we built on it in 48 hours**
- **The search:** about 265,000 cells (11,604 of 19,433 one-degree land tiles, deserts first); 1,825 crater-like
  places scored.
- **Real craters from elevation alone:** Meteor Crater, Roter Kamm and Pingualuit, which it was never told about.
- **Mines and ice:** it also found 111 open-pit mines, such as Chuquicamata and Escondida. After the mine and
  dry-bowl filters, 1,261 places are ranked.
- **Top results:** #1 is a bowl in the Tian Shan, China, 60 % similar to Shackleton, with walls as steep (27.3° vs
  27.2°). Meteor Crater, a known training site, ranks 10th (46 %).
- **Shape twins are not light twins:** no place ranks high on both.
- **Earth has no grazing Sun:** at Shackleton the Sun never rises above 1.9°; on Earth it reaches at least 23.4°.
- **Mare:** flat ground like the Moon's is common on Earth, but small craters and basalt are rare.
- **A live web app with two linked 3D globes.** Pick a base on the Moon and the Earth turns to its best twins. Each
  site has a card with a radar chart, Earth and Moon values side by side, what matches and what is missing, ground
  conditions, access (nearest city, airport and research station) and a 3D close-up with the crater outlined and a
  lunar base drawn to scale.

### Benefits
- Choosing an analog site becomes a measured comparison, criterion by criterion, that anyone can check and rerun.
  Every score traces back to a raw value next to the Moon value.
- Teams can pick a field site for what they want to test (steep-wall traverses, landing pads, rough terrain, shadowed
  floors), see how to reach it, and see clearly what Earth cannot rehearse.
- It looks beyond the well-known sites: apart from Meteor Crater, our top 10 are remote bowls in Central Asia,
  Turkey, the Sahara, the Danakil and the Andes.

### Intended impact
- Give analog-campaign, rover and instrument teams a ranked shortlist of field sites for each lunar site, with the
  limits stated.
- Help people learn what makes a good lunar base site and discover new places on Earth themselves: the app explains
  every step in plain words and runs in any browser, for students, teachers and the public.
- Be a shared, open base: others can plug in new Artemis candidate sites as they are announced, new criteria, or new
  planets.

### How it is creative
- The lunar target is measured, not looked up: from NASA data, with the same code and on the same grid as every Earth
  cell, so the comparison is fair by construction.
- Every Earth place gets a "closest lunar twin" among several real lunar sites.
- Sunlight is a measured criterion: simulated over Earth craters and compared with the lunar pole's illumination.
- We show failures on purpose: known sites the method missed are listed, with the reason.

### Factors we considered
- **Scale:** Shackleton is 21 km wide and most Earth bowls are far smaller, so we compare shape, not size.
- **Resolution:** slope and roughness depend on grid size, so both worlds use one 60 m metric grid.
- **Honest validation:** we froze the settings before testing on held-out sites. We missed Haughton (too eroded),
  Askja (its lake leaves the caldera only 48 m deep, under our 50 m minimum), Tenoumer (44 m) and Lanzarote (sea and
  villages fail the filter). The app shows these misses.
- **Missing data** shows as "no data", never as zero; in our export every ranked place has a value for every counted
  criterion.
- **Known limits:** lunar light maps measure the Sun's disc, our Earth simulation its centre. Earth cannot reproduce
  low gravity, vacuum, radiation or the mare's day–night temperature swing.
- **No machine learning:** no labelled list of good analogs exists, and physical measurements keep every score
  traceable.
- **Open licences only,** so anyone can reuse the whole stack.

### Tools, languages, hardware and software
- **Python:** NumPy, SciPy, rasterio, pyproj, GeoPandas, pandas, PyYAML, pystac-client, Matplotlib, Plotly, pytest.
- **Web:** JavaScript, HTML and CSS with globe.gl and MapLibre GL JS; hosted on GitHub Pages.
- **Data access:** read directly from AWS Open Data, NASA PGDA, PANGAEA and the Macrostrat API. Git and GitHub.
- **Hardware:** our own laptops.
- **Claude Code** as a coding assistant (details in the SI field).

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
- Our code: https://github.com/TLCasparS/EspaceOdyssey (Apache License 2.0; data licences listed in the README)

**Methods and references**
- Team criteria document: `docs/Moon Analog Criteria and Datasets.md` (29 criteria, data sources and caveats).
- Validation: `docs/VALIDATION_config-v1.md`; filters: `config/post_filters.yaml`; several lunar targets:
  `docs/MULTI_TARGET.md`; access and stations: `docs/ACCESS.md`.

---

## Before pasting (team)
- **Demo link:** public deck link, tested in a private window.
- **Images:** 1–3 app screenshots for the page (for example `pitch/img/app_map_tianshan.png`, `pitch/img/app_card.png`).
- **OurAirports licence:** `docs/ACCESS.md` could not open ourairports.com/data first-hand; open it once and confirm.
- **At submission:** the two tick boxes (Terms; original work with all resources listed in References), the
  China-review question and the SI confirmation are answered by the team.
