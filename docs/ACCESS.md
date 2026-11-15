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

---

# Research stations nearby (criterion 29)

Status 15 Nov 2026. **Display only:** never in the Moon score, never in `scores.csv`. No config, export or app
file is changed. Sections R5 and R6 are proposals for the app (Sofi).

## R1. What it does
| file | job |
|---|---|
| `src/build_stations.py` (`--fetch` downloads first) | builds `data/stations/stations.csv` from INTERACT + the hand-made analog list |
| `data/stations/analog_stations_manual.csv` | hand-made planetary analog list, one source link per row |
| `src/pipeline/stations.py` | `load_stations()`, `nearest_station(lon, lat, stations, analog_only=False)`: great-circle (same haversine and R = 6371.0088 km as the airport code) |
| `src/compute_stations.py` | adds the station columns to `data/access/access_hours.csv` in place; `compute_access.py` calls it at the end when `stations.csv` exists, so rerunning access keeps them |
| `tests/test_stations.py` | 6 tests (synthetic stations, build from tiny sources, no-data rules, personal fields not copied) |

`stations.csv` (102 rows, 16 kB) columns: `name, operator, lat, lon, type, season, analog, source, dataset, status,
year_established`. `analog` = `yes` only for the hand-made list.

New columns in `access_hours.csv` (point = Polar low point / Mare base spot, as for c26):

| column | meaning |
|---|---|
| `STATION_NAME`, `STATION_KM`, `STATION_TYPE` | nearest station of any kind in `stations.csv`, straight-line km, its type (INTERACT: `research station`; analog list: `field camp` / `habitat`) |
| `ANALOG_STATION_NAME`, `ANALOG_STATION_KM` | nearest station with `analog = yes` |

Empty = no data, never 0. All 2,325 places have values (every place has a valid point).

## R2. Sources
### INTERACT stations
| | |
|---|---|
| Where | `https://interact-gis.org/api/StationList/`: the public JSON the page interact-gis.org/Home/Stations loads (no login), read 15 Nov 2026, 117 stations, sha256 `30366d4f…939579` |
| Kept | name, `OperatingCountry` (as `operator`: a country, not an organisation), lat/lon (0–360° longitudes converted to ±180°), `OperatingPeriod` (as `season`, free text; "year-round" spellings unified to `Year-Round`), `OpeningYear` |
| Dropped | 21 rows the site hides (`Hidden: true`; all Russian stations). **Contact names, e-mails and phone numbers in the JSON are not copied.** 96 rows kept, 11 of them in Antarctica |
| Type | `StationType` 0 = `research station` (94 rows). The meaning of type 2 is not documented in the JSON; 2 rows (M'Clintock Channel Polar Research Cabins, Station Hintereis) are labelled `INTERACT type 2` |
| Licence | **Not stated.** No licence for the station list was found; the Copyright page says SLU owns the intellectual property of INTERACT GIS. We copy only facts (name, position, operating period). Cite as "INTERACT GIS station list, interact-gis.org, accessed 15 Nov 2026"; ask INTERACT if the team wants certainty. |

### Hand-made planetary analog list (6 rows)
| station | lat, lon | source of the position |
|---|---|---|
| Haughton-Mars Project Research Station (HMPRS), Devon Island | 75.43333, −89.86667 | marsinstitute.no/hmp: "75° 26' N, 89° 52' W" (arc-minute, ~1 km) |
| Flashline Mars Arctic Research Station (FMARS), Devon Island | 75.43132, −89.82339 | Wikipedia article (geo tag) |
| Mars Desert Research Station (MDRS), Utah | 38.40646, −110.79190 | Wikipedia article (geo tag) |
| HI-SEAS, Mauna Loa, Hawaii | 19.60238, −155.48719 | Wikipedia article (geo tag) |
| Biosphere 2 (SAM habitat), Arizona | 32.57878, −110.85059 | Wikipedia article of Biosphere 2 (SAM is on that site; its own position not checked) |
| LunAres, Piła, Poland | 53.17484, 16.72632 | Wikipedia article (geo tag); indoor habitat, no field terrain |

`season` is empty (no data) for all six: no source was checked for it. Indoor-only habitats in buildings (HERA,
CHAPEA, ESA LUNA) are left out. Concordia (ESA uses it as a space analog) is in the list as an INTERACT station
with `analog = no`; changing that is a team choice.

### Not used: COMNAP Antarctic Facilities (team decision 15 Nov 2026)
PGC GitHub release v3.5.0 (114 facilities) was tried and dropped:
1. Licence: "Data may be freely used for educational and non-commercial purposes only" (cite COMNAP 2024). The
   Space Apps terms want third-party material free without restriction or open source; non-commercial is neither.
2. No gain: with COMNAP in the list it was the nearest station for 592 places, but never closer than 1,267 km
   (median 3,907 km). With the 500 km card cut-off (R5) it would never have shown. Dropping it left the number of
   places with a station ≤ 500 km unchanged (231).

## R3. Result (15 Nov 2026, 2,325 places)
| | Polar (1,825) | Mare (500) |
|---|---|---|
| `STATION_KM` min / median / 90th pct / max | 20.4 / 1,983 / 4,515 / 7,372 | 19.5 / 1,401 / 3,558 / 6,354 |
| places with a station ≤ 100 / 250 / 500 km | 15 / 52 / 143 | 7 / 46 / 88 |
| `ANALOG_STATION_KM` min / median / max | 20.4 / 5,149 / 12,419 | 19.5 / 4,593 / 9,600 |
| places with an analog station ≤ 100 / 250 / 500 km | 6 / 14 / 33 | 5 / 20 / 37 |

Nearest station comes from INTERACT for 1,739 Polar / 465 Mare places, from the analog list for 86 / 35.
Closest analog pairs: a Mare cell on Devon Island 19.5 km from HMPRS; a Polar cell in Arizona 20.4 km from
Biosphere 2; a Polar cell on Hawaii 30.8 km from HI-SEAS. Analog stations ≤ 250 km: HMPRS 14 places, Biosphere 2
12, MDRS 7, HI-SEAS 1.

Note: Devon Island is a validation region. The station columns are display values; they change no score and
no tuning, so they do not touch the validation.

## R4. Limits (read before using the numbers)
1. **The list is polar and alpine.** INTERACT is mostly Arctic, boreal and alpine (21 of 96 rows south of 50° N,
   11 of them in Antarctica). Deserts, the tropics and most mid-latitudes have no station in our list.
   **A large `STATION_KM` means "no station in this list", not "no station there".** Example: a Patagonian place
   gets an Antarctic base 1,718 km away (Bulgarian Antarctic Base St. Kliment Ohridski).
2. **Straight line, not a route.** Same as the airport distance: says nothing about access or permits.
3. **Listing ≠ right of use.** Each station has its own access rules.
4. **Hand list is small and chosen by us** (6 rows), so `ANALOG_STATION_KM` is a "how far from known analog
   work" hint for a few regions only. Values over ~500 km carry no meaning.
5. **INTERACT is the live site**; rows were last updated between Feb 2018 and Nov 2026.
6. **Not a similarity to the Moon.**

## R5. Proposal: card text (`app/app.js`, owned by Sofi: not changed here)
Parser: add `'STATION_NAME', 'STATION_TYPE', 'ANALOG_STATION_NAME'` to `TEXT_COLUMNS` (else they read as NaN), and
copy the five columns into `s.access` in `attachAccess()` (line 158). Show a station only within **500 km**
(proposed cut-off, team choice; R4.1/R4.4):

```js
const STATION_MAX_KM = 500;
function stationHTML(s) {
  const a = accessOf(s);
  if (!a || a.STATION_KM == null) return '';
  const near = a.STATION_KM <= STATION_MAX_KM
    ? `${esc(a.STATION_NAME)}, <b>${Math.round(a.STATION_KM).toLocaleString('en')} km</b> (${esc(a.STATION_TYPE)})`
    : `none listed within ${STATION_MAX_KM} km`;
  const ana = a.ANALOG_STATION_KM != null && a.ANALOG_STATION_KM <= STATION_MAX_KM
    ? ` · analog station: ${esc(a.ANALOG_STATION_NAME)}, ${Math.round(a.ANALOG_STATION_KM)} km` : '';
  return `<p class="impact-line station-line" title="Straight-line distance to the nearest station in the INTERACT list (Arctic and alpine research stations) and our list of 6 planetary analog stations. The list covers polar and alpine regions only: far away means 'not in this list'. A listed station gives no right of use."><span>Research station</span> ${near}${ana}</p>`;
}
```
Examples from the data:
- "Research station **Czech Arctic Research Station of Josef Svoboda, 158 km** (research station)" (Svalbard Polar cell).
- "Research station **Haughton-Mars Project Research Station (HMPRS), 20 km** (field camp) · analog station: Haughton-Mars Project Research Station (HMPRS), 20 km" (Devon Island Mare cell).
- "Research station none listed within 500 km" (most places: 2,094 of 2,325).

Footer of the Practical box: "Stations: INTERACT GIS station list; own list of analog stations."

## R6. Proposal: globe layer "Research stations"
- Data: `../data/stations/stations.csv` (102 rows, 16 kB), loaded once like `access_hours.csv`.
- Toggle in the layer controls, **off by default**. `globe.gl` `htmlElementsData` (the app already uses
  `labelsData` and `pointsData`; HTML elements keep the icons separate from the site hit areas):

```js
const STATION_ICON = { analog: '🚀', other: '🔬' };   // or small inline SVGs in the app style
const stationKind = r => (r.analog === 'yes' ? 'analog' : 'other');
function showStations(on) {
  state.globe.htmlElementsData(on ? DATA.stations : [])
    .htmlLat(r => r.lat).htmlLng(r => r.lon).htmlAltitude(0.005)
    .htmlElement(r => {
      const el = document.createElement('div');
      el.className = `station-icon station-${stationKind(r)}`;
      el.textContent = STATION_ICON[stationKind(r)];
      el.title = `${r.name} (${r.type}${r.season ? ', ' + r.season : ''})${r.operator ? ' · ' + r.operator : ''}`;
      return el;
    });
}
```
- Analog stations (6) drawn larger and always labelled; INTERACT icons small, labels on hover.
- Legend line: "Research stations (INTERACT GIS; own analog list)".
- Line from the selected site to its nearest station when ≤ 500 km (`arcsData`, one arc), optional.

## R7. Reproduce
```
python src/build_stations.py --fetch        # INTERACT JSON -> ~/espaceodyssey_data/stations/
python src/compute_stations.py              # adds the 5 columns to data/access/access_hours.csv
python -m pytest tests/test_stations.py
```
