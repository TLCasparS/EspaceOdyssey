# App: Moon Twins on Earth

A static web page (HTML + JavaScript, no build step). Layout: the ranked list of Earth twins on the left,
the Earth globe with a suitability heatmap in the middle, the Moon globe to pick the lunar base on the
right, and under the two globes an analog card with a radar chart for each site.

## Run it on your laptop

From the repo root:

```bash
python -m http.server 8000
```

Then open http://localhost:8000/app/ . Double-clicking `index.html` does not work, because
the browser blocks reading the data files from disk.

## Data it reads

Set at the top of `app.js` (`DATA`). By default the app reads the pipeline's export in `../outputs/`
(written by `src/export_app.py`). Add `?sample` to the URL (http://localhost:8000/app/?sample) to see
the old fake sample data instead, useful for design work.

| File | Who writes it | What the app does with it |
|---|---|---|
| `outputs/scores.csv` | pipeline (Caspar) | one row per scored crater: 0–1 similarity to the Moon per criterion, `SCORE_TOTAL`, `RANK` |
| `outputs/raw_values.csv` | pipeline | raw Earth values for the chips, e.g. "Steep walls 23.9° vs 27.2°", and crater width/depth |
| `outputs/targets.json` | pipeline | per base type: which criteria count, their weight, and the raw Moon value with its unit |
| `outputs/heatmap.json` | pipeline | globe heatmap points `{lat, lng, weight}` |
| `outputs/cells.json` | pipeline | every searched grid cell: outlines in the 3D view (teal = scored, orange = skipped at an edge or the sea, grey = no crater, light blue = ice-filled floor); grouped per region into outlines on the globe (teal = crater found, coral = nothing found) and the "Searched, no crater found" list |
| `sample/scores.csv` | Sofia | in normal mode only its `SITE,LAT,LON`, for the **known analog sites** the pipeline hasn't scored yet: they show as faint grey dots on the globe and in a folded "Known analog sites · not scored yet" box under the ranking, with their notes. Its fake values are never shown, and unscored team candidates (the valleys) are left out |
| `sample/site_info.json` | Sofia | names, research notes, sources and 3D zoom per site; `export_app.py` reads it too, to name known sites |
| `site_info.json` → `type: "missed"` | Sofia + Caspar | a known crater our search covered but did not find (Tenoumer: spill depth 44 m < 50 m minimum in config-v1). Needs `lat`/`lng` in its entry; shown with a "Missed by our method" card, a coral dot on the globe and a line under "Searched, no crater found" |

How the scores are read:

- The values in `scores.csv` already are the similarity to the Moon (1 = same as the Moon). So on the
  radar the Moon is the full outer ring, and the site's shape shows how close it gets on each axis.
- The headline % is `SCORE_TOTAL`, the weighted mean of the criteria that count (`counts: true` in
  `targets.json`). Criteria with weight 0 (Sky-view, Relief, Pole-facing slopes) are shown as hollow
  dots and "Also compared, not in the score".
- Light criteria (Sunny ridge, Dark floor, Light next to dark) carry a `limitation` in `targets.json`: the
  card shows a short footnote (Moon = Sun disc, Earth = Sun centre). Grazing sun carries a `fact`: no place
  on Earth can match it, so it is shown but never counted.
- Columns with a `display_kind` in `targets.json` are **not** a similarity to the Moon: Drivable, Bare ground,
  Snow & ice ("more is better" shares) and Impact crater (1/0, name from `raw_values.csv`). They sit in the
  card's "On the ground" box, never on the radar. Crater size is raw only: the card header shows width and
  rim-to-floor depth (`CRATER_DIAMETER_EQUIV_M`, `CRATER_RIM_TO_FLOOR_M`).
- Validation results (frozen config-v1, `docs/VALIDATION_config-v1.md`) go into `site_info.json` as a
  `validation` entry, e.g. Haughton: "not found" (eroded, no closed bowl).
- An empty cell means "no value", never zero. The card says which of three reasons: no data yet,
  waiting for a lunar value (the light criteria), or not computed yet.
- Sites are keyed by `SITE`. A crater that matches a known site keeps that name (e.g. Meteor Crater);
  others are named `<run> <cell>` (e.g. `pinacate r001c002`) and get a display `name` in `site_info.json`
  (e.g. "El Elegante crater").

The app knows all 29 criteria from "Moon Analog Criteria and Datasets" (list `CRITERIA` in `app.js`,
five groups: Light, Terrain, Environment, Material & subsurface, Practical). A criterion with no data
shows as greyed out in the filters. Only the `polar` base type has pipeline data so far.

## Moon globe

- Shows one marker per lunar base (list `MOON_BASES` in `app.js`, positions from `config/lunar_targets.json`
  and Mateo's notes): Polar = Shackleton crater (89.625°S, 118.8°E), Mare = Apollo 11 site (0.674°N, 23.473°E;
  "typical lunar mare plain").
- Clicking a marker (or its button under the Moon) picks that base type: the Earth list, heatmap and cards are
  re-ranked against it. This is the only base-type selector (the old "Base type" buttons are gone).
- Picking a base links the two globes: its best independent Earth twin (the highest-ranked site that is not a
  tuning site, e.g. Al Wahbah) is selected and the Earth turns to it, the top
  three pulse on the globe and in the list for a few seconds, and the Moon card lists them ("Closest Earth
  twins", each one clickable).
- A base without Earth scores yet (Mare until the night run): the Earth shows the regions searched next
  (`PLANNED_REGIONS` in `app.js`, from Caspar's `config/night_regions.yaml`) as dashed cream outlines with
  rings, the list says the Mare twins are coming and that its ranking is still Polar, and the Moon card lists
  those regions (click one to turn the Earth to it).
- A base can be picked once `outputs/targets.json` has its values; until then it says "Earth twins coming".
- Mare: the Moon card already shows Mateo's final target (median of 20 sample areas in 4 maria: relief 154 m,
  landing pad 0.24°, drivable 99.3%, roughness 1.7 m), the day–night swing fact (≈ 290–300 K, LRO Diviner,
  no Earth analog) and the Apollo 11 site's own values, kept in `MOON_BASES`. Once Caspar's export has the mare
  base, the values come from `outputs/targets.json` instead.
- The figure link shows only when the figure is in the repo (`figures/moon/mare_cells.png` comes with
  Mateo's `mare-moon` branch).
- Under the Moon: why it is a base site, its target values, and the facts no Earth place can match
  (e.g. Grazing sun 1.9°).
- Lava tube: add an entry with id `cave` to `MOON_BASES` when its data exists (candidate: Mare Tranquillitatis
  pit, 8.336°N, 33.222°E).

## Filters

- **Filter by** opens a group; pick criteria to keep only sites that match the Moon on them
  by at least the minimum match (default 70 %). Practical criteria filter on their own score.

## AI use

The hackathon asks teams to say where and how AI was used. For this app:

- **Code:** `index.html`, `style.css` and `app.js` were written with help from an AI assistant
  (Claude, by Anthropic). Commits it helped with carry a `Co-Authored-By: Claude` line.
- **Data:** the scores come from the team's pipeline (`outputs/`). Only the optional `?sample` view uses
  fake values made by a script (`sample/scores.csv`, `sample/targets.json`, a fake heatmap pattern), only
  to design the app; it shows a "Fake data" badge.
- **Text:** the notes in `sample/site_info.json` were drafted with AI help. Facts about known sites
  link to their sources; `[brackets]` mark text still to research or check.
- **Images and video:** none are AI-generated. The globe uses NASA's Blue Marble, and the 3D view uses
  real elevation (AWS Terrain Tiles) and satellite imagery (Sentinel-2 cloudless by EOX).
- The same note is shown in the app's footer and in an `ai-assistance` meta tag in `index.html`.

## Branding

The app uses no NASA or Space Apps logos or design elements (hackathon rule). The header shows the
team name, EspaceOdyssey. NASA imagery (Blue Marble) is used as data, with credit.

## Libraries

- globe.gl 2.32.0 (3D globe and heatmap), loaded from unpkg.
- Earth image: NASA Blue Marble Next Generation, July 2004, topography + bathymetry
  (NASA Earth Observatory, public domain), resized to 4096×2048 in
  `assets/blue-marble-2004-07-4096.jpg`. Source:
  https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/
- Moon image: CGI Moon Kit colour map, 2019 version, 4096×2048 (`lroc_color_poles_4k.tif`), by NASA's
  Scientific Visualization Studio from LRO camera data (LROC WAC mosaic, Arizona State University),
  converted to JPEG in `assets/lroc-moon-color-4096.jpg`. Source: https://svs.gsfc.nasa.gov/4720
- Radar chart: plain SVG in `app.js`, no library.
- 3D terrain close-up: MapLibre GL JS 4.7.1 (open source), loaded from unpkg. No account or key.
  - Elevation: [Terrain Tiles on AWS](https://registry.opendata.aws/terrain-tiles/) (Mapzen; SRTM, GMTED,
    ETOPO1 and others), shown with heights ×1.5.
  - Imagery: [Sentinel-2 cloudless 2016](https://s2maps.eu) by EOX IT Services GmbH (contains modified
    Copernicus Sentinel data 2016), CC BY 4.0. We use the 2016 layer on purpose: EOX's 2018–2025 layers are
    CC BY-NC-SA 4.0 (non-commercial), and the challenge asks for third-party materials that are free without
    restriction or open source.
  - Clicking a site (list or globe) spins the globe to it, then flies into 3D terrain and orbits slowly.
    A values panel (top right) shows that site's numbers, Earth vs Moon with a match bar, grouped into
    Light, Shape and On the ground (only the criteria that count; display-only ones stay on the card); open on desktop, folded behind a "Values" button on phones.
    "Moon colours" turns the imagery grey. Esc or "Back to globe" returns. How close it flies in is
    the `zoom` value per site in `site_info.json`.
