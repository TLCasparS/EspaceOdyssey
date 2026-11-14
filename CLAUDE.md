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
