# EspaceOdyssey

**Moon Twins on Earth**: a map of the places on Earth that look most like candidate Moon-base sites,
measured with the same code on Earth and Moon elevation data.

- Live app: https://tlcaspars.github.io/EspaceOdyssey/app/ (GitHub Pages, served from `main`)
- Run it on your laptop: see [`app/README.md`](app/README.md)
- Hosting notes: [`docs/HOSTING.md`](docs/HOSTING.md)

## Licence

**Code:** Apache License 2.0, see [`LICENSE`](LICENSE). Copyright 2026 Caspar Schlageter, Sofi Sosa, Mateo Pozo
(team EspaceOdyssey).

**Data:** the files in `outputs/` and `data/` are derived from third-party datasets, which keep their own licences:

| Dataset | Licence |
|---|---|
| NASA LOLA / PGDA products (LDEM_80S_20MPP_ADJ, AVGVISIB, SLDEM2015), NASA images | NASA data, public domain (no copyright) |
| Copernicus DEM GLO-30 / GLO-90 (ESA, Copernicus programme) | free use with attribution |
| ESA WorldCover 2021 v200 | CC BY 4.0 |
| Maus et al. (2022), Global-scale mining polygons v2 (PANGAEA) | CC BY-SA 4.0 |
| GeoNames cities1000 | CC BY 4.0 |
| Natural Earth | public domain |
| Macrostrat | CC BY 4.0 |
| GLiM, 0.5° grid (Hartmann & Moosdorf 2012, PANGAEA) | CC BY 3.0 |
| Travel time to cities (Weiss et al. 2018, Malaria Atlas Project) | CC BY |
| OurAirports | public domain |
| Wikipedia, "List of impact craters on Earth" | CC BY-SA 4.0 |
| Sentinel-2 cloudless 2016 by EOX (3D view imagery) | CC BY 4.0 |
| INTERACT GIS station list (interact-gis.org, accessed 15 Nov 2026) | no licence stated; cited as source |

Because the mine filter uses CC BY-SA data, the files in `outputs/` are shared under **CC BY-SA 4.0**.
Full source list with links: `docs/SUBMISSION_DRAFT.md` (NASA Data and References sections).

**Libraries loaded by the app:** globe.gl (MIT), MapLibre GL JS (BSD-3-Clause).
