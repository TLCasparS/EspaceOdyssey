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

Set at the top of `app.js` (`DATA`):

| File | Who writes it | Now |
|---|---|---|
| `scores.csv` | Earth scoring (Caspar) | `sample/scores.csv`, fake values |
| `targets.json` | Moon targets role | `sample/targets.json`, fake values |
| `site_info.json` | Sofia (research notes per site) | `sample/site_info.json`, draft text |

`scores.csv` follows the team format: `SITE,LAT,LON` and one 0–1 column per criterion.
An empty cell means "no data": the app leaves it out of the score and says so on the card.

The app knows all 29 criteria from "Moon Analog Criteria and Datasets" (list `CRITERIA` in
`app.js`, five groups: Light, Terrain, Environment, Material & subsurface, Practical). The
original eight columns keep their names; the other 21 column names are a **proposal** to agree
with the scoring roles (for example `GRAZING_SUN`, `COLD`, `BASALT`, `CAVE`, `ACCESS`). A
criterion whose column is missing from `scores.csv` simply shows as "no data yet" in the filters.

`targets.json` has one entry per base type (`polar`, `cave`, `mare`) and lists only the
criteria that matter for that base. Practical criteria have no lunar value: they never change
the similarity score, they only filter.

## Filters

- **Base type** switches the lunar target (Polar, Lava tube, Mare).
- **Filter by** opens a group; pick criteria to keep only sites that match the Moon on them
  by at least the minimum match (default 70 %). Practical criteria filter on their own score.

To switch to real data, point `DATA.scores` and `DATA.targets` at `../outputs/...` and set
`isFake: false`.

The heatmap is a fake pattern for now (`fakeHeatPoints()` in `app.js`). It should be
replaced by a grid of real suitability scores (lat, lng, weight) from the pipeline.

## AI use

The hackathon asks teams to say where and how AI was used. For this app:

- **Code:** `index.html`, `style.css` and `app.js` were written with help from an AI assistant
  (Claude, by Anthropic). Commits it helped with carry a `Co-Authored-By: Claude` line.
- **Data:** `sample/scores.csv` and `sample/targets.json` are fake values made by a script, only to
  design the app. The heatmap is a fake pattern for the same reason. The app shows a "Fake data" badge.
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
