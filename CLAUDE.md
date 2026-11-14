# Project brief

## Challenge
NASA Space Apps Challenge 2026: "Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars".
Page: https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/
(TODO: paste the official summary and objectives from that page.)

## Our question, in one sentence
DRAFT, not yet agreed: Which places on Earth best stand in for lunar base sites (polar rim, lava tube, mare plain), ranked by measurable similarity from open Earth and Moon data?

## Target and candidate sites
- Scope: Moon only. Mars, Gorafe and Kali Gandaki are parked.
- Base types: Polar, Lava tube (Cave), Mare surface. Version 1 starts with **Polar**, terrain criteria first.
- Lunar target for Polar: Shackleton rim area (LOLA 5 m site DEMs + LROC WAC illumination map). Targets for Mare/Cave: to be decided (e.g. Mare Tranquillitatis pit).
- Earth candidates: not chosen by hand. They come out of the pipeline (filter → score → rank).
- Test run done: Kali Gandaki (bbox 83.6 28.7 84.0 29.1) → median slope 28.75°, only 3.7 % of the area under 5° → too steep for a base site.
- **Meteor Crater** (bbox -111.2 34.85 -110.85 35.15, `out/meteor_crater/`) is a **sanity/tuning site** with a known bowl. It is used to check and tune the pipeline and does **not** count for the later validation.
- **Tuning regions, like Meteor Crater (do not count for validation):** Pinacate volcanic field, Sonora (bbox -113.8 31.6 -113.2 32.1, `out/pinacate/`) and San Francisco Volcanic Field, Arizona (bbox -112.3 35.0 -111.2 35.8, `out/sf_volcanic/`, approximate extent from memory). Used on 14 Nov 2026 for the c5 / c7 / c2 correlation check.
- **Validation regions, keep untouched:** Iceland and Devon Island. Do not run, tune or look at results there until the method and weights are frozen.
- **Mustang** (bbox 83 28 85 30, `out/mustang_polar/`) stays as the example of a region without good analogs (deep valleys, almost no closed bowls).

## Data we use
Full list and caveats: `docs/Moon_Analog_Criteria_and_Datasets.md`.

| Dataset | Source | Where the files live |
|---|---|---|
| Copernicus DEM GLO-30 / GLO-90 | AWS `copernicus-dem-30m` / `copernicus-dem-90m`, no account | read live from S3 by `src/dem/fetch.py`; outputs in `out/` |
| ESA WorldCover 2021 v200 | AWS `esa-worldcover`, no account | read live from S3 by `src/dem/landcover.py` |
| GHS-POP (WGS84, 30 arcsec) | JRC GHSL download page | `data/` (optional, not downloaded yet) |
| LOLA 5 m site DEMs, LROC WAC illumination, SLDEM2015 | NASA PGDA / LROC, no login | `data/moon/` (not downloaded yet) |
| MODIS LST, GLiM, Earth Impact Database | see criteria document | later |

`data/` and `out/` are git-ignored.

## Decisions made
| Date | Decision | Why |
|---|---|---|
| 13 Nov 2026 | Moon only; Mars and own candidate sites parked | two days, keep scope small |
| 13 Nov 2026 | 29 criteria, 3 base types, each criterion scored 0–1, weighted presets per base type | see criteria document |
| 13 Nov 2026 | Hard filters before scoring; slope filter only at the base spot, never on the walls | walls create the shadow |
| 14 Nov 2026 | Grid cells of ~15 km | size of an Artemis III candidate region |
| 14 Nov 2026 | Version 1 = Polar, terrain criteria 7, 9, 10, 11, 13, 14 first | all come from the DEM we already load |
| 14 Nov 2026 | Compare Earth and Moon on one common metric grid (60 m, local UTM) | slope and roughness depend on resolution and projection |
| 14 Nov 2026 | Missing data shows as "no data", never 0 | some datasets don't cover the poles |
| 14 Nov 2026 | Polar lunar target = Shackleton, computed by `src/compute_lunar_target.py` from LOLA `LDEM_80S_20MPP_ADJ` (20 m → 60 m) with the same code as the Earth cells | same definitions on both sides; crater found from the data |
| 14 Nov 2026 | Similarity rule: score = exp(−((earth − moon) / tolerance)²), tolerance per criterion in `pipeline.yaml` (team choice); criteria without a verified lunar value keep rank scoring | scores comparable across runs; no spread from the run's cells |
| 14 Nov 2026 | Compare by shape, not size: c7 depth/width, c10 base slope, c11 inner-wall slope, c13 roughness are scored; c9 rim-to-floor depth is display only (weight 0) | Shackleton (≈21 km) is far bigger than Earth bowls |
| 14 Nov 2026 | Zones relative to the bowl (r = equivalent radius of the filled depression): c11 ring 0.5–1.0 × r; c13 over bowl + 1.3 × r; c10 pad outside the bowl, centre ≤ 1 km from its edge | fixed km windows missed Shackleton's walls and rim |
| 14 Nov 2026 | c14 aspect display only (weight 0) | at Shackleton "toward the pole" is no fixed direction; shadow comes from light criteria 1–5 |
| 14 Nov 2026 | Bowl filter: require a closed depression ≥ 50 m deep, ≥ 1 km wide, elongation (longest axis / equivalent diameter) ≤ 2 | bowl-less cells and valleys outranked real bowls (Mustang run) |
| 14 Nov 2026 | Keep the 1 km minimum bowl width for all regions | resolution limit: < ~17 px at 60 m, walls smoothed |
| 14 Nov 2026 | Light criteria interface (Earth `light.py`, Moon `lunar_light.py` by Mateo): c1 rim max lit / flat-land lit, c2 p99 floor shadow, c3 dark→sunny distance / r, c4 max Sun elevation; "lit" = Sun centre above the horizon; shared `flat_lit_fraction` | same definitions on both sides |
| 14 Nov 2026 | Total score = "score (vs Moon)": weighted mean of target-scored criteria with weight > 0 only. Rank-scored criteria are shown as raw value + rank score and as a separate "rank score (within run)", never in the total, until a lunar target exists | rank scores depend on the run (1 cell → 0.5) and distorted the total |
| 14 Nov 2026 | c5 sky-view factor display only (weight 0) | duplicates c7 for simple bowls and overlaps c2 (r −0.91 each over 6 bowl cells); c2 has the lunar comparison |

## Who does what
- Caspar: data pipeline (DEM, filters, terrain scoring)
- Sofi: design and presentation of the results
- (TODO: third team member: area)

## Rules for AI help
- Never invent numbers or sources. Say when you are unsure.
- Keep code in src/, data in data/.
- Small changes, one task at a time.
- Read `docs/Moon_Analog_Criteria_and_Datasets.md` (team plan, source of truth) and `docs/HANDOFF_terrain.md` (what is built, known gaps, next step) before working on the pipeline.
- Lunar reference values marked ~ in the criteria document are unverified; check them before using them.
