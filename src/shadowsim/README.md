# shadowsim: where on Earth is it as dark (and as bright) as the lunar south pole?

At the lunar south pole the Sun never rises more than ~1.5 deg. Crater floors like
Shackleton's stay in permanent shadow, while nearby ridges get sunlight most of the time.
Earth's axis is tilted 23.4 deg, so nowhere on Earth is *permanently* dark. We can still
measure how close a place gets: a floor that terrain keeps dark for a long time, next to
ridges that get almost all the sun possible at that latitude.

## How it works

1. **DEM**: Copernicus GLO-30 (30 m, free, streamed from AWS, no login). Each site is
   cropped to the analysis square (`--radius-km`) plus a horizon buffer (`--horizon-km`)
   and cached in `data/dem/`.
2. **Horizon**: for every cell and 72 directions, the steepest angle to the surrounding
   terrain (with Earth curvature and refraction).
3. **Sun**: Sun azimuth and elevation for every hour of one year (own implementation,
   checked against pvlib to within 0.05 deg).
4. **Year simulation**: a cell is lit when the Sun is above its horizon in that direction.
5. **Score**: one row per site in `data/results/shadow_scores.csv`, plus maps in
   `figures/shadow/`.

## Output columns

| column | meaning |
|---|---|
| `flat_lit_fraction` | share of the year with sun on flat land at this latitude |
| `flat_max_dark_days` | polar night without any terrain (0 below the Arctic Circle) |
| `darkest_terrain_shadow_p99` | darkest 1 % of cells: share of daylight hours blocked by terrain |
| `near_permanent_shadow_km2` | area where terrain blocks the sun >= 90 % of daylight hours |
| `max_extra_dark_days` | longest sunless stretch caused by terrain, beyond the flat-land value |
| `sunniest_lit_vs_flat_p99` | sunniest 1 % of cells compared with flat land (1.0 = as sunny as possible) |
| `max_continuous_sun_h` | longest uninterrupted period of sun anywhere in the area |
| `analog_score` | sqrt(darkest x sunniest): high when both extremes sit close together. **Placeholder, the team decides the final formula** (in `score.py`) |

## Run

```bash
conda env create -f environment.yml && conda activate spaceapps
python src/run_shadow_sites.py --demo           # synthetic 20 km crater at 75 N, ~10 s
python src/run_shadow_sites.py --only rjukan    # one real site (downloads ~2 tiles)
python src/run_shadow_sites.py                  # all sites in data/sites.csv
python -m pytest tests                          # sanity checks
```

Add candidates to `data/sites.csv`. The coordinates there are approximate
(`coords_checked = no`): check them on a map before you trust the results.

## Known limits

- The Sun is treated as a point (its centre). The real disc is 0.5 deg wide, so
  edges of shadows are slightly too sharp.
- Sun position uses the site centre for the whole square (fine for ~10 km).
- 30 m terrain cannot see small shadows (boulders, overhangs, gorge walls < 30 m apart).
  Narrow slot canyons will look sunnier than they are.
- Clouds are ignored: this is geometric (direct) sunlight only.
- The same code could run on the Moon with a LOLA DEM and lunar Sun positions, to
  compare Shackleton directly with the Earth sites.
