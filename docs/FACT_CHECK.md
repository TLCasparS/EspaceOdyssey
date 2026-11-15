## Agent report: Task 2 Fact-check
Status: done (4 items left UNVERIFIED, reasons below)
What I did:
- Searched the repo for every claim in the task list plus everything marked "from memory", "unchecked" or "~"; added the slide-facing facts in `app/sample/site_info.json` (sizes, depths, ages, training history).
- Checked each against a named source (NASA, ESA, USGS, PGDA, Smithsonian GVP, IAU Gazetteer, Earth Impact Database, peer-reviewed papers; Wikipedia only where nothing better was found, and marked as such).
- 11 corrections suggested (table below), none applied: this branch changes only `docs/FACT_CHECK.md` and `docs/ai_usage/task2.md`.
Files changed / created: `docs/FACT_CHECK.md`, `docs/ai_usage/task2.md`
Tests: `python -m pytest -q tests` → 102 passed, 1 skipped, 1663 warnings in 44.26s (no code touched)
Open points / needs a human decision:
- Shackleton position on the card: we show the floor low point (89.625°S, 118.8°E); the IAU crater centre is 89.67°S, 129.78°E. Pick one and label it.
- Roter Kamm age: sources disagree (3.7 ± 0.3 Ma vs ~5 Ma).
- Haughton age: Earth Impact Database 39 Ma vs newer dating 31–32 Ma.
Unverified items (and why): Trou au Natron coordinates (no citable coordinate found), Al Wahbah age and floor mineral, PANGAEA participants beyond ESA, WorldCover weakest classes (validation report blocked), Haughton–Mars Project start year (1996 approval vs 1997), plus run-input bounding boxes (not slide facts; need a map check).
Data downloaded (size): none (web pages only)

# Fact check: numbers and names that may end up on a slide

Checked 14 Nov 2026 (night) by an AI research agent (Task 2, `docs/AGENTS_NIGHT_GUIDE.md`). Status:
**OK** = matches a named source (within the precision we state); **CORRECT TO …** = change suggested;
**UNVERIFIED** = no adequate source found (reason given). Nothing here has been applied to other files.

## Corrections to apply (summary)

| # | Where | Now says | Suggested |
|---|---|---|---|
| 1 | `docs/AGENTS_NIGHT_GUIDE.md:120` | Shackleton rim-to-floor 4073 m | **4077 m** (current `config/lunar_targets.json` c9 and criteria doc; 4073 m was the earlier ±25 km window) |
| 2 | `config/sites.csv:2`, `app/sample/site_info.json:6`, `docs/VALIDATION_config-v1.md:22`, criteria doc l.127 | Haughton "~20 km" / "~20–23 km" | **about 23 km** (Earth Impact Database; Wikipedia) |
| 3 | `config/missed_sites.yaml:22-24`, `docs/VALIDATION_config-v1.md:26` | Askja 65.0 N, 16.7 W, "unchecked" | **65.03 N, 16.75 W** (Öskjuvatn caldera, Smithsonian GVP) |
| 4 | `app/app.js:75`, `app/README.md:64` | Shackleton at 89.625°S, 118.8°E | label it **"floor low point"**, or use the IAU centre **89.67°S, 129.78°E** (they are ~2 km apart) |
| 5 | `app/sample/site_info.json:206` | Roter Kamm "4–5 million years old" | **about 4 million years (3.7 ± 0.3 Ma, Earth Impact Database)**; ESA says ~5 Ma: decide |
| 6 | `app/sample/site_info.json:226`, task list | Tenoumer filled by **sand** | **sediment** (ESA: 200–300 m of sediments; type not stated) |
| 7 | `app/sample/site_info.json:183` | Al Wahbah "white salt floor" | **"white crystalline floor"** (Wikipedia: sodium phosphate crystals, unsourced) |
| 8 | `app/sample/site_info.json:8` | Haughton–Mars Project "since 1997, … run by the Mars Institute" | **"approved 1996 (NASA Ames); run by the Mars Institute and SETI Institute, funded mainly by NASA"** |
| 9 | `app/sample/site_info.json:155` | El Elegante 1.6 km / 244 m | OK if the cited source says so; Wikipedia gives **1.5 km / 250 m**. Name the source on the card |
| 10 | `docs/VALIDATION_config-v1.md:26`, missed_sites | "Askja (Apollo training area)" | add **"July 1967"**: Askja is named for the 1967 trip, not 1965 |
| 11 | criteria doc l.41, `light.py` | lunar equator tilt 1.535° (NSSDC 6.68 − 5.145) | keep, but say **"≈ 1.54°"** on slides (standard value 1.543°); difference irrelevant |

## Moon

| Claim | Where in the repo | Checked value | Source | Status |
|---|---|---|---|---|
| Shackleton diameter ~21 km | criteria doc l.126, `config/sites.csv:2` | 21 km (mean rim diameter); IAU: 20.92 km | [Zuber et al. 2012, Table 1](https://ntrs.nasa.gov/api/citations/20120013758/downloads/20120013758.pdf); [IAU Gazetteer, Shackleton](https://planetarynames.wr.usgs.gov/Feature/5450) | OK |
| Our rim crest diameter 20.9 km | criteria doc l.46, `lunar_targets.json` place | 20.92 km (IAU) | IAU Gazetteer (above) | OK (matches to 0.02 km) |
| Shackleton depth ~4 km | task list; criteria doc l.46–47 (4077 m) | 4.1 ± 0.05 km rim to floor; depth/diameter 0.195 ± 0.025 | [Zuber et al. 2012](https://ntrs.nasa.gov/api/citations/20120013758/downloads/20120013758.pdf), Table 1 | OK |
| Our rim-crest-to-floor 4073 m | `docs/AGENTS_NIGHT_GUIDE.md:120` | repo value is now **4077 m**; both within Zuber's 4.1 ± 0.05 km | `config/lunar_targets.json` c9; [Zuber et al. 2012](https://ntrs.nasa.gov/api/citations/20120013758/downloads/20120013758.pdf) | CORRECT TO 4077 m (internal consistency) |
| Our bowl depth/width 0.197 | `lunar_targets.json` c7 | 0.195 ± 0.025 | [Zuber et al. 2012](https://ntrs.nasa.gov/api/citations/20120013758/downloads/20120013758.pdf) | OK |
| Inner wall ~30° | `docs/HANDOFF_terrain.md:38` | average ≈ 30° (table text partly illegible in the scan), maximum 35° | [Zuber et al. 2012](https://ntrs.nasa.gov/api/citations/20120013758/downloads/20120013758.pdf), Table 1 | OK (re-read the original table before quoting "30°") |
| Our inner wall 27.2° (c11) / 29.0° (whole wall) | criteria doc l.49, app chips "27.2°" | c11 = ring 0.5–1.0 × r around the low point; 29.0° = all inner-wall pixels; both below Zuber's ≈30° average | `lunar_targets.json` (c11, place.inner_wall_mean_slope_deg) | OK, but **say which one** on a slide: 27.2° is the scored c11 |
| Shackleton position | `app/app.js:75`, `app/README.md:64` | IAU centre 89.67°S, 129.78°E (Zuber rim centre 89.655°S, 129.174°E); ours = floor low point 89.625°S, 118.8°E | [IAU Gazetteer](https://planetarynames.wr.usgs.gov/Feature/5450); [Zuber et al. 2012](https://ntrs.nasa.gov/api/citations/20120013758/downloads/20120013758.pdf) | CORRECT TO label (see #4) |
| Lunar equator tilt 1.535° (6.68° − 5.145°) | criteria doc l.41, `src/pipeline/light.py` | NSSDC: obliquity to orbit 6.68°, orbit inclination 5.145° → 1.535°; commonly quoted 1.543° | [NSSDC Moon Fact Sheet](https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html) (updated 11 Jan 2024); [Wikipedia, Orbit of the Moon](https://en.wikipedia.org/wiki/Moon_orbit) | OK (see #11) |
| Max Sun elevation at the pole ~1.5° | criteria doc l.41, `app/app.js:571` | = the tilt, 1.54°; 1.91° at Shackleton's low point (89.625°S) by the repo's formula | [NSSDC Moon Fact Sheet](https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html) (tilt); `light.max_sun_elevation_deg` | OK |
| Diviner: equator ~387–397 K at noon, ~95 K before sunrise | `src/pipeline/mare.py` FACT_C16, `lunar_targets.json` mare c16, `app/app.js:91` | same | [Diviner team, Level 4 products post](https://diviner.ucla.edu/single-post/2018/04/20/new-diviner-level-4-data-products), links Williams et al. 2017, Icarus, [doi:10.1016/j.icarus.2016.08.012](https://doi.org/10.1016/j.icarus.2016.08.012) | OK |
| Mare Tranquillitatis pit: opening 88–100 m, ~105 m deep; 8.3355°N, 33.222°E | criteria doc l.118, `app/app.js:73` | inner diameter 88–100 m, funnel 140–146 m, depth 105 m, 8.3355 / 33.222 | [LROC Pits Atlas, pit 3](https://lroc.im-ldi.com/pits/3) | OK |
| Apollo 11 site 0.67416°N, 23.47314°E | `config/mare_cells.json`, app | lunar module 0.67416°N, 23.47314°E | [NSSDC Apollo landing site coordinates](https://nssdc.gsfc.nasa.gov/planetary/lunar/lunar_sites.html) (Wagner et al. 2017) | OK |
| SLDEM2015 vertical accuracy 3–4 m | criteria doc l.107, `config/pipeline.yaml:130` | typical vertical accuracy 3–4 m | [PGDA product 54](https://pgda.gsfc.nasa.gov/products/54) (Barker et al., Icarus 273, 346–355) | OK |

## Artemis III

| Claim | Where | Checked value | Source | Status |
|---|---|---|---|---|
| 13 candidate regions (2022) | task list | 13 regions, announced 19 Aug 2022 | [NASA release, Aug 2022](https://www.nasa.gov/news-release/nasa-identifies-candidate-regions-for-landing-next-americans-on-Moon/) | OK |
| 9 regions in the 2024 update | task list | 9 regions, 28 Oct 2024 (Peak near Cabeus B, Haworth, Malapert Massif, Mons Mouton Plateau, Mons Mouton, Nobile Rim 1 & 2, de Gerlache Rim 2, Slater Plain) | [NASA release, Oct 2024](https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/) | OK |
| Region size ~15 × 15 km (our 15 km cells) | `config/pipeline.yaml:9`, `CLAUDE.md:60`, `docs/HANDOFF_terrain.md:17` | "approximately 15 by 15 km" per region | [NASA release, Aug 2022](https://www.nasa.gov/news-release/nasa-identifies-candidate-regions-for-landing-next-americans-on-Moon/) | OK (the 2024 release gives no size) |

## Earth sites

| Claim | Where | Checked value | Source | Status |
|---|---|---|---|---|
| Meteor Crater ~35.03 N, 111.02 W, ~1.2 km | `CLAUDE.md:25`, `site_info.json:54` | 35.028 N, 111.023 W; 1.18–1.19 km; ~170 m deep | [Earth Impact Database list (NASA ARES)](https://ares.jsc.nasa.gov/engagement/activities/resources/crater-comparisons/earth-impact-database.pdf); [Wikipedia](https://en.wikipedia.org/wiki/Meteor_Crater) | OK |
| Al Wahbah ~22.90 N, 41.14 E | `config/regions.yaml:13`, `site_info.json:183` | 22.906 N, 41.138 E; ~2 km wide, 250 m deep; maar | [Wikipedia, Al Wahbah crater](https://en.wikipedia.org/wiki/Al_Wahbah_crater) (cites Grainger 1996, Geology Today for the maar origin) | OK (position, size, maar) |
| Al Wahbah age ~1.1 Ma; "salt" floor | `site_info.json:183` | age not found in a citable source; floor: sodium phosphate crystals (unsourced) | [Wikipedia, Al Wahbah crater](https://en.wikipedia.org/wiki/Al_Wahbah_crater) | UNVERIFIED (age); CORRECT wording (#7) |
| Roter Kamm ~27.77 S, 16.29 E; 2.5 km | `config/regions.yaml:15`, `site_info.json:206` | 27.8 S, 16.3 E; 2.5 km; ~130 m deep; ≥100 m sand on the floor | Earth Impact Database list; [ESA image page](https://www.esa.int/ESA_Multimedia/Images/2020/06/Roter_Kamm_impact_crater) | OK |
| Roter Kamm age 4–5 Ma | `site_info.json:206` | 3.7 ± 0.3 Ma (EID); "approximately 5 million years" (ESA) | [Earth Impact Database list](https://ares.jsc.nasa.gov/engagement/activities/resources/crater-comparisons/earth-impact-database.pdf); [ESA, Roter Kamm](https://www.esa.int/ESA_Multimedia/Images/2020/06/Roter_Kamm_impact_crater) | CORRECT TO (#5) |
| Tenoumer ~22.92 N, 10.41 W, ~1.9 km, ~110 m deep | `config/missed_sites.yaml:4-8`, `site_info.json:226` | 22.918 N, 10.408 W; 1.9 km; rims ~110 m above the floor; original depth 300–400 m | [Wikipedia](https://en.wikipedia.org/wiki/Tenoumer_crater); [ESA image page](https://www.esa.int/ESA_Multimedia/Images/2022/06/Tenoumer_Crater_Mauritania); EID list | OK |
| Tenoumer "sand-filled" | task list, `site_info.json:226` | floor covered by 200–300 m of **sediments** (type not given) | [ESA, Tenoumer](https://www.esa.int/ESA_Multimedia/Images/2022/06/Tenoumer_Crater_Mauritania) | CORRECT TO sediment (#6) |
| Trou au Natron ~20.95 N, 16.53 E | `docs/NIGHT_RUN.md:51` | no citable coordinate found. Consistent with sources: caldera ~6–8 km, up to 1,000 m deep, south-east of Toussidé (21.04 N, 16.47 E) | [Wikipedia, Trou au Natron](https://en.wikipedia.org/wiki/Trou_au_Natron); [Wikipedia, Toussidé](https://en.wikipedia.org/wiki/Toussid%C3%A9) | UNVERIFIED (position plausible, not confirmed) |
| El Elegante (Pinacate) ~31.85 N, 113.40 W | `site_info.json:155`, app labels | 31.847 N, 113.391 W; ~1.5 km, ~250 m deep; maar, ~32,000 years (all uncited on Wikipedia) | [Wikipedia (Kiwix mirror), El Elegante](https://kaweah.freedombox.rocks/kiwix/wikipedia_en_all_maxi_2023-10/El_Elegante_Crater) | OK (position); size see #9 |
| "Pinacate NW, probably MacDougal crater" | `site_info.json:174` | not checked | — | UNVERIFIED (not in the task list; needs a map check) |
| Haughton ~75.38 N, 89.67 W | `config/sites.csv:2`, `missed_sites.yaml:12-16` | 75°23′N, 89°40′W (= 75.383, 89.667) | [Wikipedia, Haughton impact crater](https://en.wikipedia.org/wiki/Haughton_impact_crater); EID list (75.4 N, 89.7 W) | OK |
| Haughton ~20–23 km | `config/sites.csv:2`, `site_info.json:6`, `VALIDATION_config-v1.md:22` | about 23 km | [Earth Impact Database list](https://ares.jsc.nasa.gov/engagement/activities/resources/crater-comparisons/earth-impact-database.pdf); [Wikipedia, Haughton impact crater](https://en.wikipedia.org/wiki/Haughton_impact_crater) | CORRECT TO ~23 km (#2) |
| Haughton age (if used) | not in the repo | 39 Ma (EID) vs 31–32 Ma (Erickson et al. 2021, GCA 304) | [Earth Impact Database list](https://ares.jsc.nasa.gov/engagement/activities/resources/crater-comparisons/earth-impact-database.pdf); [Wikipedia, Haughton impact crater](https://en.wikipedia.org/wiki/Haughton_impact_crater) | note: use "~31 Ma" with the newer dating if needed |
| Askja ~65.0 N, 16.7 W, with a lake | `missed_sites.yaml:20-24`, `VALIDATION_config-v1.md:26,66` | Öskjuvatn caldera 65°02′N, 16°45′W (65.033 N, 16.75 W); the lake is Öskjuvatn | [Smithsonian GVP, Askja](https://volcano.si.edu/volcano.cfm?vn=373060) | CORRECT TO 65.03 N, 16.75 W (#3) |

## Training history (analog use)

| Claim | Where | Checked value | Source | Status |
|---|---|---|---|---|
| Apollo geology training in Iceland | `VALIDATION_config-v1.md:26` | 12–16 Jul 1965 and 2–8 Jul 1967; Askja visited in **1967** | [USGS OF 2005-1190 table (NASA ALSJ)](https://www.nasa.gov/wp-content/uploads/static/history/alsj/of2005-1190_table1.pdf); [Exploration Museum](https://www.explorationmuseum.com/astronaut-training/) | OK (Askja: 1967, see #10) |
| … at Meteor Crater, "from 1963" | `site_info.json:54-56` | first trip 16–18 Jan 1963, later 1965, 1967, 1969, 1971 | [USGS OF 2005-1190 table](https://www.nasa.gov/wp-content/uploads/static/history/alsj/of2005-1190_table1.pdf) | OK ("taught by Gene Shoemaker" not checked) |
| … at the Nördlinger Ries | task list | 11–13 Aug 1970, Apollo 14 crew | [USGS OF 2005-1190 table](https://www.nasa.gov/wp-content/uploads/static/history/alsj/of2005-1190_table1.pdf) | OK |
| … at Sudbury | task list | Jul 1971 (Apollo 16), 24–25 May 1972 (Apollo 17) | [USGS OF 2005-1190 table](https://www.nasa.gov/wp-content/uploads/static/history/alsj/of2005-1190_table1.pdf) | OK |
| … at Pinacate | task list | Nov 1965, Nov–Dec 1966, Mar 1967, Feb 1970 (Apollo 14) | [USGS OF 2005-1190 table](https://www.nasa.gov/wp-content/uploads/static/history/alsj/of2005-1190_table1.pdf) | OK |
| Craters of the Moon, Apollo 14 crew, 22 Aug 1969 | `site_info.json:78` | 22–23 Aug 1969, Apollo 14 crew | [USGS OF 2005-1190 table](https://www.nasa.gov/wp-content/uploads/static/history/alsj/of2005-1190_table1.pdf) | OK |
| ESA astronaut training on Lanzarote | `site_info.json:106` | PANGAEA has a Lanzarote session (volcanic terrains); astronaut crew trained there in 2016 | [ESA, What is PANGAEA](https://www.esa.int/Science_Exploration/Human_and_Robotic_Exploration/CAVES_and_Pangaea/What_is_PANGAEA); [ESA image, 2017](https://www.esa.int/ESA_Multimedia/Images/2017/11/Pangaea_training_in_Lanzarote) | OK (Lanzarote training). The card's "astronauts from ESA, NASA and …": UNVERIFIED (sources checked name ESA astronauts only) |
| Haughton–Mars Project "since 1997, NASA-supported, Mars Institute" | `site_info.json:8` | approved 1996 by NRC/NASA Ames; run by SETI Institute and Mars Institute; funded primarily by NASA | [Wikipedia, Haughton–Mars Project](https://en.wikipedia.org/wiki/Haughton%E2%80%93Mars_Project) | CORRECT TO (#8); "1997" UNVERIFIED |

## Earth datasets

| Claim | Where | Checked value | Source | Status |
|---|---|---|---|---|
| Copernicus DEM vertical accuracy | task list (no number in the repo yet) | absolute < 4 m (90 % linear error); relative < 2 m for slopes ≤ 20 %, < 4 m above | [Copernicus Data Space, COP-DEM](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM) | OK (use "< 4 m, LE90") |
| WorldCover 2021 overall accuracy 76.7 % | criteria doc l.85 | 76.7 % | [ESA WorldCover 2021](https://worldcover2021.esa.int) | OK |
| WorldCover weak classes: shrub, wetland, moss/lichen | criteria doc l.85 | validation report not reachable (bot protection) | — | UNVERIFIED |

## Marked "from memory" in the repo, out of scope for slides

These are run inputs or internal notes, not slide facts; checking them needs map work, not a source.

| Item | Where | Status |
|---|---|---|
| Region bounding boxes "from memory" | `CLAUDE.md:26-27`, `config/night_regions.yaml:3` | UNVERIFIED (need a map check; a wrong box only changes what is searched) |
| 775 m depression at 84.011 E 28.471 N, real or DEM artifact | `docs/PIPELINE_polar_v1.md:39` | UNVERIFIED (needs imagery) |
| Tenoumer position "matched from memory" | criteria doc l.150 | now OK: matches `missed_sites.yaml` ([Wikipedia, Tenoumer crater](https://en.wikipedia.org/wiki/Tenoumer_crater); [Earth Impact Database list](https://ares.jsc.nasa.gov/engagement/activities/resources/crater-comparisons/earth-impact-database.pdf)) |
| Askja "flattened lake surface (probably the caldera lake)" | `VALIDATION_config-v1.md:66` | OK: the caldera lake is Öskjuvatn ([Smithsonian GVP, Askja](https://volcano.si.edu/volcano.cfm?vn=373060)) |

Test run on this branch: see `docs/ai_usage/task2.md`.
