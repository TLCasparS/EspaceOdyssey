# Moon Analog Criteria and Datasets

Nov 13, 2026 · @Caspar

## Goal and scope

We rank places on Earth by how well they stand in for lunar base locations in general, using 29 measurable criteria from open data. The Moon offers three kinds of base site, and each needs a different Earth analog:

- **Polar base** (south pole rims such as Shackleton): near-constant sun on the rim, permanent shadow and ice on the floor.
- **Lava-tube base** (pits such as Marius Hills or Mare Tranquillitatis): shelter underground from radiation, impacts and temperature swings.
- **Mare surface base** (flat basalt plains at low latitude): easy landing and driving, but a huge day–night temperature swing.

Mars, Gorafe and Kali Gandaki are parked for now.

Every criterion gives a 0–1 score per place, and each base type weights the criteria differently. Thirteen of the 29 come from one elevation model plus our shadow simulation. The lunar values come from LRO products and serve as the target profile on each site's radar chart.

## Hard filters

Filters remove land that can never work, before any scoring. Thresholds are our proposals; keep them in one config file.

| Filter | Proposed rule | Dataset |
| --- | --- | --- |
| Water | drop "Permanent water bodies" | ESA WorldCover 10 m |
| Vegetation | drop "Tree cover", "Mangroves", "Cropland", "Herbaceous wetland" | ESA WorldCover 10 m |
| Cities | drop "Built-up" plus a 2 km buffer | ESA WorldCover 10 m |
| Population | drop cells above \~10 people/km² | GHS-POP, 100 m |
| Steep base spot | drop cells steeper than \~15° at the base spot only | Copernicus DEM GLO-30 |

Keep the slope filter local to the base spot. The walls around it must stay in the data, because they create the shadow.

## Scored criteria

The "Base type" column says which lunar base a criterion matters for; "Any" applies to all three. Lunar reference values marked \~ are from memory and need a check before the pitch.

| # | Criterion | Base type | Lunar reference | What we measure on Earth | Earth data | Priority |
| --- | --- | --- | --- | --- | --- | --- |
|  | **Light** |  |  |  |  |  |
| 1 | Sunny ridge | Polar | best rim spots sunlit most of the year | share of the year in direct sun vs. flat land at the same latitude | DEM + shadow sim | Core |
| 2 | Dark floor | Polar | permanently shadowed floor | share of daylight blocked by terrain; longest run of days without sun | DEM + shadow sim | Core |
| 3 | Light next to dark | Polar | power and ice within driving reach | distance from darkest cell to sunniest cell | DEM + shadow sim | Core |
| 4 | Grazing sun | Polar | sun stays within \~1.5° of the horizon | mean and max sun elevation over the year | latitude only | Core |
| 5 | Sky-view factor | Polar, Cave | no atmosphere, so shadow is truly dark | share of sky visible from the floor (low is good) | DEM | Core |
| 6 | Clear skies | Any | hard, direct light | annual cloud-free share | MODIS clear-sky coverage | Secondary |
|  | **Terrain** |  |  |  |  |  |
| 7 | Bowl shape | Polar | closed, deep crater | closed depression; depth to width ratio | DEM | Core |
| 8 | Crater size match | Polar | Shackleton rim crest 20.9 km wide, rim to floor 4073 m (LOLA LDEM\_80S\_20MPP\_ADJ, resampled to 60 m, measured 14 Nov 2026)¹ | diameter and depth vs. target crater | DEM | Secondary |
| 9 | Rim-to-floor depth | Any | Shackleton 4073 m (LOLA, 14 Nov 2026)¹; low relief on mare | rim-to-floor depth of the bowl: median rim crest elevation minus the floor low point (changed 14 Nov 2026 from "max minus min within \~5 km", which did not reach Shackleton's rim and was scale-dependent). Size-dependent, so display only (weight 0) | DEM | Core |
| 10 | Flat base spot | Any | landing and building | slope at the candidate cell (low is good) | DEM | Core |
| 11 | Steep walls | Polar | Shackleton inner wall mean slope 29.0° (LOLA LDEM\_80S\_20MPP\_ADJ at 60 m, measured 14 Nov 2026)¹ | mean slope of walls around the low point (high is good) | DEM | Core |
| 12 | Drivable share | Any | rover routes around the base | share of cells within \~5 km under 15–20° | DEM | Secondary |
| 13 | Roughness | Any | traverse difficulty | spread of elevation in a moving window | DEM | Core |
| 14 | Aspect | Polar | pole-facing slopes hold shadow | share of steep terrain facing the nearer pole | DEM | Core |
|  | **Environment** |  |  |  |  |  |
| 15 | Cold | Polar | shadowed floors at 25–70 K | annual minimum and mean land surface temperature | MODIS LST | Secondary |
| 16 | Day–night swing | Mare | near 400 K at noon, under 100 K at night at the equator | daytime minus night-time land surface temperature | MODIS LST | Core |
| 17 | Dry | Any | no liquid water, no weathering by rain | mean annual precipitation | CHIRPS or ERA5 | Secondary |
| 18 | Ice in the ground | Polar | water ice in cold traps | permafrost probability; snow and ice cover | permafrost map; WorldCover | Secondary |
| 19 | Bare ground | Any | no vegetation | bare class share; NDVI near zero | WorldCover; Sentinel-2 | Core |
| 20 | Fine, loose surface | Any | fine abrasive regolith and dust | sand and silt share of topsoil | SoilGrids | Stretch |
| 21 | Night darkness | Any | no artificial light | night-light brightness | VIIRS Black Marble | Stretch |
|  | **Material and subsurface** |  |  |  |  |  |
| 22 | Highland-type rock | Polar | anorthosite | rock type; brightness as rough proxy | geological maps, by hand | Stretch |
| 23 | Basaltic volcanic ground | Mare, Cave | mare basalt | basalt or young lava share of the area | global lithology map | Core |
| 24 | Real impact crater | Any | the Moon's surface is shaped by impacts | site is a confirmed impact structure | Earth Impact Database | Core |
| 25 | Cave or lava tube | Cave | pits with overhangs lead to possible tubes | known lava tubes or skylights at the site | cave and volcanic-field lists, by hand | Core |
|  | **Practical (scored apart from similarity)** |  |  |  |  |  |
| 26 | Access | Any | crews must reach the site | travel time to nearest city | MAP travel-time map | Secondary |
| 27 | Dark when reachable | Polar | Haughton's gap: no shadow in field season | overlap of dark period and accessible months | shadow sim + snow cover | Secondary |
| 28 | Line of sight | Any | direct-to-Earth communication | viewshed from the site | DEM | Stretch |
| 29 | Research station nearby | Any | existing logistics | distance to nearest station | station lists | Stretch |

¹ Measured by `src/compute_lunar_target.py` from [LDEM\_80S\_20MPP\_ADJ.TIF](https://pgda.gsfc.nasa.gov/products/90) (LOLA, Barker et al. 2023), a ±25 km window around the pole, bilinear to the common 60 m grid. Crater found from the data (largest closed depression near the pole). Rim crest = highest point per 1° azimuth within 1.3 × the bowl's equivalent radius; diameter = 2 × median crest distance from the floor low point; depth = median crest elevation minus the low point (−2869 m). Inner wall = bowl pixels between the floor (< 10°, ~5.2 km across) and the rim crest. Full values in `config/lunar_targets.json`. The pipeline's criterion 11 ring (0.5–1.0 × equivalent radius) gives 27.1° for the same crater.

Rows 10 and 11 must stay separate: low slope is good at the base spot and high slope is good on the walls, so one combined slope score cancels out.

## Earth datasets

Three datasets cover 19 of the 29 criteria and all sit on public cloud storage with no login: Copernicus DEM, ESA WorldCover and MODIS land surface temperature (the last via Earth Engine or Earthdata). Rows marked \* were not checked today and come from memory.

| Dataset | Feeds criteria | Resolution and coverage | Access | Caveat |
| --- | --- | --- | --- | --- |
| [Copernicus DEM GLO-30](https://registry.opendata.aws/copernicus-dem/) | 1–5, 7–14, 28 | 30 m, global including polar regions | AWS bucket `copernicus-dem-30m`, no account needed, cloud-optimized GeoTIFF | A surface model: it includes buildings and vegetation. Tiles for a few countries are not public. Heights use the EGM2008 geoid |
| [ESA WorldCover 2021 v200](https://worldcover2021.esa.int) | filters, 18, 19 | 10 m, global, 11 classes | AWS bucket `esa-worldcover`, CC-BY 4.0 | 76.7 % overall accuracy; shrub, wetland and moss/lichen classes are the weak ones |
| [MODIS LST, MOD11A1 / MYD11A1 v6.1](https://www.earthdata.nasa.gov/data/catalog/lpcloud-myd11a1-061) | 6, 15, 16 | 1 km, daily, day and night, global | Google Earth Engine `MODIS/061/MOD11A1`, or Earthdata login | Clear-sky pixels only. 1 km cannot resolve one shadowed crater floor, so use it for regional climate. The product also carries clear-sky coverage layers for criterion 6 |
| GHS-POP | population filter | 100 m, global | JRC download | Epoch must match the land-cover year roughly |
| [Earth Impact Database](https://en.wikipedia.org/wiki/Earth_Impact_Database) | 24, 8 | 190 confirmed structures with coordinates and diameter | no bulk download; the Wikipedia list tables are the quick route | Many structures are buried or eroded flat. Cross-check each with the DEM for real bowl relief |
| [MAP travel time to cities](https://developers.google.com/earth-engine/datasets/catalog/projects_malariaatlasproject_assets_accessibility_accessibility_to_cities_2015_v1_0) | 26 | \~1 km, 60°S to 85°N, year 2015 | Earth Engine or malariaatlas.org | No Antarctica. Roads are from 2015 |
| [Permafrost map, Obu et al. 2019](https://www.permafrost.org/?p=1530) | 18 | 1 km, Northern Hemisphere, 2000–2016 | data archive linked from the paper | Northern Hemisphere only. Gives permafrost probability and ground temperature |
| Sentinel-2 or HLS \* | 19 | 10–30 m, global | Copernicus Data Space; Earth Engine | Only needed if the WorldCover bare class is too coarse a signal |
| CHIRPS or ERA5 precipitation \* | 17 | \~5 km (CHIRPS, 50°S–50°N) or \~30 km (ERA5, global) | Earth Engine | CHIRPS stops at 50° latitude, so polar candidates need ERA5 |
| Global lithology map (GLiM) \* | 22, 23 | polygon map, global | PANGAEA download | Coarse; good for "basalt yes/no", not for anorthosite |
| SoilGrids \* | 20 | 250 m, global | ISRIC web services | Modelled, weak in deserts and polar areas |
| VIIRS Black Marble \* | 21 | 500 m, global | Earthdata; Earth Engine | Use an annual composite |
| Lava tube and cave lists \* | 25 | point lists per volcanic field | literature, by hand | No global raster exists. Start from basalt fields (criterion 23) and check candidates by hand |
| Sentinel-1 SAR | 13 (optional) | 10 m, global | Copernicus Data Space | Roughness at centimetre scale; pairs with lunar radar. Skip unless time allows |

From the challenge's resource list, RADARSAT, JAXA G-Portal and the ESA Open Science Catalog add little for these criteria.

## Moon datasets

The Moon side gives the target profile each Earth site is compared with, and every product below is a free download with no login. SLDEM2015 covers mare and lava-tube targets; the LOLA polar products cover the pole.

| Dataset | Base type | Gives us | Resolution and coverage | Caveat |
| --- | --- | --- | --- | --- |
| [SLDEM2015](https://pgda.gsfc.nasa.gov/products/54) | Mare, Cave | elevation for slope, roughness and relief | \~60 m at the equator, latitudes 60°S to 60°N, vertical accuracy 3–4 m | Stops at ±60°. FLOAT IMG and JPEG2000 files, tiled or global |
| [SLDEM2015 slope and azimuth](https://pgda.gsfc.nasa.gov/products/67) | Any | ready-made slope and aspect maps | pole to pole, 64 to 512 pixels per degree | Slope depends on the baseline: compare at one resolution only |
| [LOLA 5 m mosaic, 87–90°S](https://pgda.gsfc.nasa.gov/products/81) | Polar | elevation, slope and count maps of the south pole | 5 m GeoTIFF, south polar stereographic | Most 5 m pixels are interpolated between laser tracks, so do not measure roughness at 5 m |
| [LOLA 5 m site DEMs](https://pgda.gsfc.nasa.gov/products/78) | Polar | per-site elevation, slope and error maps (Shackleton rim, connecting ridge, de Gerlache rim and others) | 5 m GeoTIFF per site | Small areas; good for the 3D side-by-side view |
| [LROC WAC illumination map, south](https://data.lroc.im-ldi.com/lroc/view_rdr/WAC_POLE_ILL_TWI_SOUTH) | Polar | measured share of time each pixel is lit: the target for criteria 1 and 2 | 100 m, 88–90°S, 3,807 images over one lunar year | Noise and scattered light leave small non-zero values inside permanent shadow |
| [LROC WAC south pole movie](https://data.lroc.im-ldi.com/lroc/view_rdr/WAC_POLE_MOVIE_SOUTH) | Polar | frames for the shadow animation | 100 m, 80–90°S, 8,170 images | Large download; take a subset |
| [LROC PSR shapefile](https://data.lroc.im-ldi.com/lroc/view_rdr/NAC_POLE_PSR_SOUTH) | Polar | outlines of permanently shadowed regions | PSRs larger than 5 km², 80°S to the pole | Outlines are modelled from LOLA, not imaged |
| [Diviner polar products](https://ode.rsl.wustl.edu/moon/pagehelp/Content/Missions_Instruments/LRO/DIVINER/PRP.htm) | Polar | annual average and maximum temperature, depth to stable ice | 240 m polar grids | Text tables (.TAB) that need gridding first |
| Diviner global temperature maps \* | Mare | day and night temperatures for criterion 16 | global gridded maps | Not checked today; find the product name on the Diviner PDS page |
| [LROC lunar pit locations](https://data.lroc.im-ldi.com/lroc/view_rdr/SHAPEFILE_LUNAR_PIT_LOCATIONS) | Cave | shapefile of pits with diameters and depths | point list, global | Most pits sit in impact melt, not lava tubes; filter to mare pits |

Reference numbers for the cave target: the [Mare Tranquillitatis pit](https://lroc.im-ldi.com/pits/3) has an inner opening 88–100 m wide and is about 105 m deep.

## Minimal data stack and traps

For a first working ranking, five downloads are enough; start them tonight because the lunar files are large.

1. Copernicus DEM GLO-30 tiles for the search regions (AWS).
2. ESA WorldCover tiles for the same regions (AWS).
3. MODIS land surface temperature, day and night, as a multi-year mean (Earth Engine export).
4. One lunar target per base type we keep: the LOLA Shackleton rim DEM plus the WAC illumination map for Polar; an SLDEM2015 tile around a mare pit for Mare and Cave.
5. The impact-structure list and the lunar pit shapefile (small tables).

Traps we found while checking the data:

- **Resolution mismatch.** Earth is 30 m, the lunar pole 5 m, the lunar mare \~60 m. Resample both sides to one grid (60 m is the safe choice) before computing slope or roughness.
- **Projection.** Copernicus tiles are in degrees and pixels narrow toward the poles. Reproject to a metric grid (local UTM) before any slope calculation.
- **Surface model.** Copernicus includes trees and buildings. The filters remove most of this, so filter first.
- **Temperature scale.** MODIS at 1 km describes the region, not one shadowed hollow. Score "cold" as climate and let the shadow simulation carry the local effect.
- **Coverage gaps.** Travel time stops at 60°S, the permafrost map is Northern Hemisphere only, and CHIRPS stops at 50° latitude. Polar candidates lose some criteria; show them as "no data", not zero.
- **Caves have no global map.** Criterion 25 is a hand check on shortlisted basalt fields.

## Open decisions

- [ ] Which base types do we score in two days: all three, or Polar plus one other?
- [ ] Which lunar target per base type (for example Shackleton rim, Mare Tranquillitatis pit, one flat mare site)?
- [ ] Search area: whole world at \~1 km for screening, or a few regions at 30 m?
- [ ] Common grid for Earth–Moon comparison: 60 m?
- [ ] Default weights per base type (the presets), and which criteria ship in version 1.
- [ ] Who owns what: data and filters, shadow simulation, app and design, pitch.

## Sources

Dataset figures come from the pages below, read as search summaries on 13 Nov 2026; open each one before quoting numbers in the pitch.

- [Space Apps challenge page](https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/)
- [Copernicus DEM on AWS](https://registry.opendata.aws/copernicus-dem/) and [Copernicus DEM description](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM)
- [ESA WorldCover 2021](https://worldcover2021.esa.int) and [WorldCover on AWS](https://registry.opendata.aws/esa-worldcover-vito/index.html)
- [MODIS MYD11A1 v6.1](https://www.earthdata.nasa.gov/data/catalog/lpcloud-myd11a1-061)
- [Earth Impact Database (Wikipedia summary)](https://en.wikipedia.org/wiki/Earth_Impact_Database)
- [MAP accessibility to cities 2015](https://developers.google.com/earth-engine/datasets/catalog/projects_malariaatlasproject_assets_accessibility_accessibility_to_cities_2015_v1_0)
- [Obu et al. 2019 permafrost map](https://www.permafrost.org/?p=1530)
- [SLDEM2015](https://pgda.gsfc.nasa.gov/products/54) and [slope and azimuth maps](https://pgda.gsfc.nasa.gov/products/67)
- [LOLA south pole 5 m mosaic](https://pgda.gsfc.nasa.gov/products/81), [site DEMs](https://pgda.gsfc.nasa.gov/products/78) and [README](https://core2.gsfc.nasa.gov/PGDA/LOLA_5mpp/README)
- [LROC WAC illumination map](https://data.lroc.im-ldi.com/lroc/view_rdr/WAC_POLE_ILL_TWI_SOUTH), [south pole movie](https://data.lroc.im-ldi.com/lroc/view_rdr/WAC_POLE_MOVIE_SOUTH), [PSR mosaic and shapefile](https://data.lroc.im-ldi.com/lroc/view_rdr/NAC_POLE_PSR_SOUTH), [PSR temperatures](https://www.lroc.im-ldi.com/images/979)
- [Diviner polar resource product](https://ode.rsl.wustl.edu/moon/pagehelp/Content/Missions_Instruments/LRO/DIVINER/PRP.htm) and [lunar temperature overview](https://meetingorganizer.copernicus.org/EPSC2013/EPSC2013-386-1.pdf)
- [LROC lunar pit shapefile](https://data.lroc.im-ldi.com/lroc/view_rdr/SHAPEFILE_LUNAR_PIT_LOCATIONS) and [Mare Tranquillitatis pit](https://lroc.im-ldi.com/pits/3)
