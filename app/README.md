# App: Earth Twins of the Moon

A static web page (HTML + JavaScript, no build step): ranked site list, 3D globe with a
suitability heatmap, and an analog card with a radar chart for each site.

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

How the scores are read:

- The values in `scores.csv` already are the similarity to the Moon (1 = same as the Moon). So on the
  radar the Moon is the full outer ring, and the site's shape shows how close it gets on each axis.
- The headline % is `SCORE_TOTAL`, the weighted mean of the criteria that count (`counts: true` in
  `targets.json`). Criteria with weight 0 (Sky-view, Relief, Pole-facing slopes) are shown as hollow
  dots and "Also compared, not in the score".
- Light criteria (Sunny ridge, Dark floor, Light next to dark) carry a `limitation` in `targets.json`: the
  card shows a short footnote (Moon = Sun disc, Earth = Sun centre). Grazing sun carries a `fact`: no place
  on Earth can match it, so it is shown but never counted.
- An empty cell means "no value", never zero. The card says which of three reasons: no data yet,
  waiting for a lunar value (the light criteria), or not computed yet.
- Sites are keyed by `SITE`. A crater that matches a known site keeps that name (e.g. Meteor Crater);
  others are named `<run> <cell>` (e.g. `pinacate r001c002`) and get a display `name` in `site_info.json`
  (e.g. "El Elegante crater").

The app knows all 29 criteria from "Moon Analog Criteria and Datasets" (list `CRITERIA` in `app.js`,
five groups: Light, Terrain, Environment, Material & subsurface, Practical). A criterion with no data
shows as greyed out in the filters. Only the `polar` base type has pipeline data so far.

## Filters

- **Base type** switches the lunar target (only Polar with real data; Lava tube and Mare in `?sample`).
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
- Radar chart: plain SVG in `app.js`, no library.
- 3D terrain close-up: MapLibre GL JS 4.7.1 (open source), loaded from unpkg. No account or key.
  - Elevation: [Terrain Tiles on AWS](https://registry.opendata.aws/terrain-tiles/) (Mapzen; SRTM, GMTED,
    ETOPO1 and others), shown with heights ×1.5.
  - Imagery: [Sentinel-2 cloudless 2020](https://s2maps.eu) by EOX (modified Copernicus Sentinel data),
    CC BY-NC-SA 4.0, fine for a non-commercial hackathon.
  - Clicking a site (list or globe) spins the globe to it, then flies into 3D terrain and orbits slowly.
    "Moon colours" turns the imagery grey. Esc or "Back to globe" returns. How close it flies in is
    the `zoom` value per site in `site_info.json`.
