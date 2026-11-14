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

To switch to real data, point `DATA.scores` and `DATA.targets` at `../outputs/...` and set
`isFake: false`.

The heatmap is a fake pattern for now (`fakeHeatPoints()` in `app.js`). It should be
replaced by a grid of real suitability scores (lat, lng, weight) from the pipeline.

## Libraries

- globe.gl 2.32.0 (3D globe and heatmap), loaded from unpkg.
- Earth texture from the three-globe example images (NASA Blue Marble).
- Radar chart: plain SVG in `app.js`, no library.
