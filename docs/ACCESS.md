# Access: travel time to cities and nearest airport (criterion 26)

Status 15 Nov 2026, branch `material-access`. **Display only:** neither value enters the Moon score, and no
config, export or app file is changed by this branch. Sections 5 and 6 are proposals.

## 1. What it does
`src/pipeline/access.py` gives, for one lon/lat point:

| value | meaning | no data when |
|---|---|---|
| `ACCESS_HOURS` (**primary**) | travel time to the nearest city in hours, read from the pixel under the point | south of 60° S, north of 85° N, sea / no-data pixel |
| `AIRPORT_KM` | great-circle distance to the nearest **medium or large** airport, km | airport list empty |
| `AIRPORT_NAME`, `AIRPORT_TYPE` | name and OurAirports type (`medium_airport` / `large_airport`) of that airport | same |

- No data is empty / `None`, **never 0** (team rule of 14 Nov 2026). A real 0 h (pixel inside a city) stays 0.
- `TravelTimeRaster(path).hours(lon, lat)` reads one pixel (no interpolation, no averaging over the cell).
- `nearest_airport(lon, lat, load_airports(csv))` uses the haversine distance on a sphere (R = 6371.0088 km).
- `src/compute_access.py` runs both on every Polar low point (`out/night_polar/ranking.csv`, `low_lon/low_lat`)
  and every Mare base spot (`out/night_mare/ranking.csv`, `base_lon/base_lat`) and writes
  `data/access/access_hours.csv` (`run, cell, lon, lat, ACCESS_HOURS, AIRPORT_KM, AIRPORT_NAME, AIRPORT_TYPE, AIRPORT_IDENT`).
- Tests: `tests/test_access.py` (14 tests on a synthetic 0.5° raster and a 7-row airport list).

## 2. Data actually used
### Travel time to cities
| | |
|---|---|
| Dataset | Weiss et al. (2018), "A global map of travel time to cities to assess inequalities in accessibility in 2015", Nature 553, 333–336, doi:10.1038/nature25181 |
| Host | Malaria Atlas Project, layer `Accessibility:201501_Global_Travel_Time_to_Cities` on `data.malariaatlas.org` (GeoServer). No login. Earth Engine was not used. |
| Download | `https://data.malariaatlas.org/geoserver/ows?service=CSW&version=2.0.1&request=DirectDownload&ResourceId=Accessibility:201501_Global_Travel_Time_to_Cities` |
| File | `201501_Global_Travel_Time_to_Cities_2015.zip`, 350,278,270 bytes → `201501_Global_Travel_Time_to_Cities_2015.tif`, 354,754,098 bytes, sha256 `55c95c60…b1fc34` |
| Grid (read from the file) | EPSG:4326, 43,200 × 17,400 px, 30 arcsec (~1 km at the equator), lon −180…180, **lat −60…85**, int32, **minutes**, no data −9999 |
| Licence | Attribution licence. MAP open access policy (malariaatlas.org/open-access-policy, read 15 Nov 2026): maps are "available to all users under the Creative Commons Attribution 3.0 Unported License". The Google Earth Engine catalogue page for the same dataset says "Creative Commons Attribution 4.0 International". The two pages name different CC BY versions; both allow use with citation. |
| Cite | Weiss, D.J. et al. (2018), Nature 553, 333–336, doi:10.1038/nature25181; data: Malaria Atlas Project |
| Stored at | `~/espaceodyssey_data/access_weiss2018/` (Windows: `%LOCALAPPDATA%\espaceodyssey_data\access_weiss2018\`), outside the repo |

"City" (as described on the Earth Engine catalogue page): a contiguous area with ≥ 1,500 inhabitants per km², or
mostly built-up land with a population centre of ≥ 50,000 inhabitants.

### Airports
| | |
|---|---|
| Dataset | OurAirports `airports.csv` (updated daily by the project) |
| Download | `https://davidmegginson.github.io/ourairports-data/airports.csv` (linked from the README of github.com/davidmegginson/ourairports-data) |
| File | 12,761,365 bytes, 86,368 rows, last-modified 15 Nov 2026, sha256 `aa5d3eba…f7d05d` |
| Used | rows with `type` = `medium_airport` or `large_airport` and valid coordinates: **5,282** airports |
| Licence | **Not verified first-hand.** `ourairports.com/data/` could not be opened on 15 Nov 2026 (expired TLS certificate). Third-party pages quote OurAirports as "All data is released to the Public Domain, and comes with no guarantee of accuracy or fitness for use." Please open the page once and confirm before the submission lists it. |
| Stored at | `~/espaceodyssey_data/ourairports/airports.csv`, outside the repo |

## 3. Result of the run (15 Nov 2026)
2,325 places (1,825 Polar, 500 Mare). All have a travel time (no place lies south of 60° S; latitudes run
from −52.1° to 82.0°). No place has exactly 0 h.

| | Polar (1,825) | Mare (500) |
|---|---|---|
| `ACCESS_HOURS` min / median / 90th percentile / max | 0.10 / 9.03 / 34.26 / 191.58 | 0.27 / 11.16 / 97.23 / 145.95 |
| `AIRPORT_KM` min / median / 90th percentile / max | 1.7 / 140.0 / 235.7 / 3,318.9 | 17.6 / 147.0 / 346.4 / 609.8 |
| nearest airport is medium / large | 1,349 / 476 | 376 / 124 |

Places within a travel time (both runs together, of 2,325): ≤ 1 h 53 · ≤ 3 h 333 · ≤ 6 h 801 · ≤ 12 h 1,330 ·
≤ 24 h 1,837 · ≤ 48 h 2,119.

The join with the night export was checked: `outputs/night_export/raw_values.csv` has 2,328 rows; 2,325 match on
(`RUN`, `CELL`) with identical coordinates. The 3 rows without `RUN` (missed known sites) get no data.

## 4. Limits (read before using the numbers)
1. **Roads and cities of 2015.** Roads built or closed since then are not in the map.
2. **~1 km pixels, one pixel per place.** The value is for the pixel under the low point / base spot, not the
   15 km cell. A crater floor without a track can be hours from a road pixel next to it.
3. **No Antarctica, nothing north of 85° N.** The raster covers 60° S to 85° N only. Outside it the value is
   no data, not 0. No night-run place is affected, but McMurdo-type sites would be.
4. **Sea and large lakes are no data.** Checked in the file: mid-Atlantic, Caspian Sea and Lake Superior are −9999.
5. **It is a model, not a timetable.** Travel time is the cheapest path over a friction surface (roads, rail,
   rivers, land cover, slope) with surface transport only. It ignores flights, seasons, permits, borders in
   practice, and whether a vehicle can really leave the road. Very large values (the maximum here is 192 h at
   80.4° N, 60.2° W in the high Arctic; Greenland's ice sheet reads ~277 h) mean "far from everything", not a plannable trip.
   Islands get a value through modelled water travel (e.g. the Kerguelen cell: 187 h).
6. **"City" is a density threshold**, so a small town with an airport and a hospital may not count, and the
   nearest "city" can be far from the nearest useful settlement.
7. **Airports: distance in a straight line, not a route.** The type comes from OurAirports volunteers and says
   nothing about scheduled flights or public access. Example from the run: Alert (military, Ellesmere) and
   Pituffik Space Base are "medium_airport". The largest distance (3,319 km, Kerguelen cell → Tôlanaro,
   Madagascar) shows that for remote islands the value is only "no airport nearby".
8. **Not a similarity to the Moon.** Short travel time is a practical plus, nothing else.

## 5. Proposal for the export (`src/export_app.py`, owned by another session: not changed here)
Read `data/access/access_hours.csv` and join on `RUN` = `night_` + `run`, `CELL` = `cell`.

- **`raw_values.csv`:** add `ACCESS_HOURS`, `AIRPORT_KM`, `AIRPORT_NAME`, `AIRPORT_TYPE`. Empty when there is no
  row or no value.
- **`targets.json`**, both base types, one entry per value, same shape as the other display columns:

  ```json
  {"column": "ACCESS_HOURS", "criterion": "c26_access", "counts": false, "weight": 0,
   "score_method": "display", "display_kind": "raw only", "in_scores_csv": false,
   "earth_unit": "hours (travel time to the nearest city, 2015, Weiss et al. 2018)", "moon": null,
   "note": "Display only. Practical value, not a similarity to the Moon."}
  ```
  and the same for `AIRPORT_KM` with `"earth_unit": "km (straight line to the nearest medium or large airport, OurAirports)"`.
- **Not in `scores.csv`.** Every number there is read by the app as a 0–1 value (the Practical box draws
  `value × 100 %` as a bar), so hours would be drawn wrongly. If the team later wants a 0–1 "Access" bar, that
  needs a team-chosen scale (which travel time counts as 1, which as 0); none is proposed here.
- Sources for the `outputs/README.md` table: the two "Cite" lines of section 2.

## 6. Proposal for the app (`app/`, not changed here)
All line numbers refer to `app/app.js` on `main` (commit 0be1738).

1. **Parser** (line 142): add `'AIRPORT_NAME', 'AIRPORT_TYPE'` to `TEXT_COLUMNS`.
2. **Card line** in `renderCard()`, next to the impact line (line 668), from `s.raw`:

   ```js
   const h = raw.ACCESS_HOURS, km = raw.AIRPORT_KM;
   const fmtH = h == null ? null : h < 1 ? `~${Math.round(h * 60)} min` : h < 48 ? `~${Math.round(h)} h` : `~${Math.round(h / 24)} days`;
   const access = fmtH == null && km == null ? null :
     `${fmtH == null ? 'no travel-time data' : `<b>${fmtH}</b> to nearest city`}` +
     (km == null ? '' : ` · ${Math.round(km)} km to ${esc(raw.AIRPORT_NAME)} (${raw.AIRPORT_TYPE === 'large_airport' ? 'large' : 'medium'} airport)`);
   // in the template:
   ${access ? `<p class="impact-line"><span>Access</span> ${access}</p>` : ''}
   ```
   Example from the data: "Access **~31 min** to nearest city · 11 km to Balkhash Airport (medium airport)".
   Tooltip / footnote: "Modelled surface travel time, roads of 2015 (Weiss et al. 2018). Airport distance is a
   straight line."
3. **Optional filter "max travel time".** A slider in the filter bar, off by default:

   ```html
   <label class="threshold">Max. travel time
     <input type="range" id="maxHours" min="0" max="6" step="1" value="6"> <output id="maxHoursOut">any</output></label>
   ```
   ```js
   const HOUR_STEPS = [1, 3, 6, 12, 24, 48, Infinity];           // slider positions
   // state: maxHours: Infinity
   // passesFilters(): add at the top
   if (state.maxHours !== Infinity) {
     const h = site.raw?.ACCESS_HOURS;
     if (h == null || h > state.maxHours) return false;         // no data never passes a limit
   }
   ```
   Sites kept at each step (of 2,325): 53 · 333 · 801 · 1,330 · 1,837 · 2,119 · all. The filter only hides
   sites; ranks and scores stay the same.
4. The existing practical criterion `ACCESS` (line 65) expects a 0–1 column. Keep it for the sample data; with
   pipeline data it stays "no data" until the team picks a scale (section 5).

## 7. Reproduce
```
mkdir -p ~/espaceodyssey_data/access_weiss2018 ~/espaceodyssey_data/ourairports
curl -o ~/espaceodyssey_data/access_weiss2018/tt.zip "<download URL of section 2>"   # 350 MB
unzip ~/espaceodyssey_data/access_weiss2018/tt.zip -d ~/espaceodyssey_data/access_weiss2018
curl -o ~/espaceodyssey_data/ourairports/airports.csv https://davidmegginson.github.io/ourairports-data/airports.csv
python src/compute_access.py          # or --raster <tif> --airports <csv>
python -m pytest tests/test_access.py
```
`airports.csv` changes daily, so `AIRPORT_*` can differ slightly on a later download.
