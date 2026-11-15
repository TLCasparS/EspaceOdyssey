/* Moon Twins on Earth: static web app (no build step).
 * Reads the pipeline's files in ../outputs/ (written by src/export_app.py) and draws:
 * filter bar, ranked site list, 3D globe with heatmap, analog card, 3D terrain close-up.
 * Add ?sample to the URL to see the old fake sample data instead (for design work).
 */

const USE_SAMPLE = new URLSearchParams(location.search).has('sample');
// Scale test only (docs/APP_SCALE_TEST.md): ?data=outputs_fake/2000 reads that folder of FAKE data instead of
// ../outputs/. Without the parameter nothing changes.
const FAKE_DIR = (new URLSearchParams(location.search).get('data') ?? '').match(/^outputs_fake\/\d+$/)?.[0];
const OUT = FAKE_DIR ? `../${FAKE_DIR}/` : '../outputs/';
const DATA = USE_SAMPLE ? {
  scores: 'sample/scores.csv',       // fake 0–1 site values, compared with fake 0–1 targets
  targets: 'sample/targets.json',
  info: 'sample/site_info.json',
  isFake: true,                      // shows the "Fake data" badge
} : {
  scores: OUT + 'scores.csv',   // 0–1 values ARE the similarity to the Moon; SCORE_TOTAL, RANK
  targets: OUT + 'targets.json',// per base: criteria list with counts, weight, score_method, raw Moon value
  raw: OUT + 'raw_values.csv',  // raw Earth values, for "23.9° vs 27.2°" chips
  heatmap: OUT + 'heatmap.json',// [{lat, lng, weight}]
  cells: OUT + 'cells.json',    // every searched cell, with status (ranked / no_bowl / filtered)
  info: 'sample/site_info.json',     // Sofia's research notes per site (export_app.py reads it too)
  coords: 'sample/scores.csv',       // only SITE,LAT,LON: puts sites the pipeline hasn't scored yet on the map
  access: '../data/access/access_hours.csv', // Mateo's c26: travel time to a city + nearest airport (display only)
  // Positions of the extra lunar targets (targets.json → lunar_targets has their values but no positions)
  candidates: '../config/lunar_targets_candidates.json',
  isFake: false,
};

// The 29 criteria from "Moon Analog Criteria and Datasets", in five groups.
// key = scores.csv column. bases = which lunar base types the criterion matters for.
// Practical criteria are scored apart from similarity: they only filter.
const GROUPS = [
  { id: 'light', label: 'Light' },
  { id: 'terrain', label: 'Terrain' },
  { id: 'env', label: 'Environment' },
  { id: 'material', label: 'Material & subsurface', short: 'Material' },
  { id: 'practical', label: 'Practical' },
];
const ANY = ['polar', 'cave', 'mare'];
const CRITERIA = [
  { key: 'SUNNY_RIDGE',     group: 'light',    label: 'Sunny ridge',         hint: 'rim spots in sun most of the year', bases: ['polar'] },
  { key: 'DARK_FLOOR',      group: 'light',    label: 'Dark floor',          hint: 'floor the sun barely reaches', bases: ['polar'] },
  { key: 'LIGHT_NEAR_DARK', group: 'light',    label: 'Light next to dark',  hint: 'power and ice within driving reach', bases: ['polar'] },
  { key: 'GRAZING_SUN',     group: 'light',    label: 'Grazing sun',         hint: 'sun stays low on the horizon', bases: ['polar'] },
  { key: 'SKY_VIEW',        group: 'light',    label: 'Sky-view factor',     hint: 'little sky visible from the floor', bases: ['polar', 'cave'] },
  { key: 'CLEAR_SKIES',     group: 'light',    label: 'Clear skies',         hint: 'hard, direct light', bases: ANY },
  { key: 'BOWL_SHAPE',      group: 'terrain',  label: 'Bowl shape',          hint: 'closed, deep crater', bases: ['polar'] },
  { key: 'CRATER_SIZE',     group: 'terrain',  label: 'Crater size match',   hint: 'close to Shackleton’s size', bases: ['polar'] },
  { key: 'RELIEF',          group: 'terrain',  label: 'Relief',              hint: 'rim-to-floor depth', bases: ANY },
  { key: 'SLOPE_BASE',      group: 'terrain',  label: 'Flat base spot',      hint: 'flat enough to land and build', bases: ANY },
  { key: 'STEEP_WALLS',     group: 'terrain',  label: 'Steep walls',         hint: 'steep inner walls', bases: ['polar'] },
  { key: 'DRIVABLE',        group: 'terrain',  label: 'Drivable share',      hint: 'rover routes around the base', bases: ANY },
  { key: 'ROUGHNESS',       group: 'terrain',  label: 'Roughness',           hint: 'how bumpy the ground is', bases: ANY },
  { key: 'ASPECT',          group: 'terrain',  label: 'Pole-facing slopes',  hint: 'slopes that hold shadow', bases: ['polar'] },
  { key: 'COLD',            group: 'env',      label: 'Cold',                hint: 'very low ground temperature', bases: ['polar'] },
  { key: 'DAY_NIGHT_SWING', group: 'env',      label: 'Day–night swing',     hint: 'big temperature swing', bases: ['mare'] },
  { key: 'DRY',             group: 'env',      label: 'Dry',                 hint: 'no rain, no weathering', bases: ANY },
  { key: 'GROUND_ICE',      group: 'env',      label: 'Snow & ice',          hint: 'snow or ice cover on the crater floor', bases: ['polar'] },
  { key: 'BARE',            group: 'env',      label: 'Bare ground',         hint: 'no vegetation', bases: ANY },
  { key: 'FINE_SURFACE',    group: 'env',      label: 'Fine, loose surface', hint: 'dust and fine soil', bases: ANY },
  { key: 'NIGHT_DARK',      group: 'env',      label: 'Night darkness',      hint: 'no artificial light', bases: ANY },
  { key: 'HIGHLAND_ROCK',   group: 'material', label: 'Highland-type rock',  hint: 'anorthosite-like rock', bases: ['polar'] },
  { key: 'BASALT',          group: 'material', label: 'Basaltic ground',     hint: 'basalt or young lava', bases: ['cave', 'mare'] },
  { key: 'IMPACT_CRATER',   group: 'material', label: 'Real impact crater',  hint: 'confirmed impact structure', bases: ANY },
  { key: 'CAVE',            group: 'material', label: 'Cave or lava tube',   hint: 'known tubes or skylights', bases: ['cave'] },
  { key: 'ACCESS',          group: 'practical', label: 'Access',             hint: 'travel time to a city', bases: ANY },
  { key: 'DARK_WHEN_REACHABLE', group: 'practical', label: 'Dark when reachable', hint: 'shadow during the field season', bases: ['polar'] },
  { key: 'LINE_OF_SIGHT',   group: 'practical', label: 'Line of sight',      hint: 'open view for communication', bases: ANY },
  { key: 'STATION_NEARBY',  group: 'practical', label: 'Research station nearby', hint: 'existing logistics', bases: ANY },
];
const BASES = [
  { id: 'polar', label: 'Polar' },
  { id: 'cave', label: 'Lava tube' },
  { id: 'mare', label: 'Mare' },
];
// Where each base type sits on the Moon (from Mateo's lunar targets, config/lunar_targets.json). The Moon globe
// shows one marker per entry; a base can be picked once outputs/targets.json has its values. To add the
// lava-tube base later, add an entry with id 'cave' (candidate: Mare Tranquillitatis pit, 8.336°N, 33.222°E).
const MOON_BASES = [
  // lat/lng = Shackleton's low point (config/lunar_targets.json → polar.place.low_point_lat_lon)
  { id: 'polar', title: 'Polar base', name: 'Shackleton crater', place: 'lunar south pole', lat: -89.625, lng: 118.8,
    subtitle: '21 km wide, 4,077 m from rim crest to floor',
    why: 'Its rim is one of the sunniest places on the Moon (best spot lit 78% of the time: solar power), while its floor never sees the Sun (permanent shadow: water ice). Power and ice are about 7.5 km apart.',
    figure: '../figures/shackleton_target.png' },
  // Mare target: final values from Mateo (config/lunar_targets.json → mare, branch mare-moon, 14 Nov 2026).
  // Shown on the Moon card until Caspar's outputs/targets.json has the mare base; then those values are used.
  { id: 'mare', title: 'Mare surface base', name: 'Apollo 11 site', place: 'Mare Tranquillitatis', lat: 0.674, lng: 23.473,
    targetName: 'Apollo 11 site (20-cell median)',   // name in the list of lunar targets: the values are the 20-cell median
    subtitle: 'Typical lunar mare plain: median of 20 sample areas across 4 maria',
    why: 'Flat, smooth volcanic plains near the equator: easy to land and drive on, but with a huge day–night temperature swing.',
    target: [
      { label: 'Relief within 5 km', value: '154 m', note: 'gentle, but small craters are part of normal mare' },
      { label: 'Flattest landing pad', value: '0.24°', note: 'essentially flat' },
      { label: 'Drivable ground', value: '99.3%', note: 'of the area under 15° slope' },
      { label: 'Roughness', value: '1.7 m', note: 'smooth at the 60 m scale' },
    ],
    facts: [
      { label: 'Day–night swing', value: '≈ 290–300 K', note: '≈ 390 K at noon, ≈ 95 K before sunrise (LRO Diviner)' },
    ],
    detail: 'The Apollo 11 site itself (130 m relief, 0.32° pad, 99.9% drivable, 1.7 m roughness) sits within the range of the 20 sample areas: Apollo 11 really did land on “average” mare.',
    figure: '../figures/moon/mare_cells.png', figureLabel: 'See the map of the 20 sample areas' },
];
// Regions the pipeline's night run searches next, for both the Polar and the Mare track (config/night_regions.yaml
// on Caspar's night-run branch; bboxes approximate). Shown on the Earth for the Mare base until its scores exist.
const PLANNED_REGIONS = [
  { run: 'tibesti', label: 'Tibesti', country: 'Chad / Libya', bbox: [16.0, 19.5, 19.5, 22.0] },
  { run: 'harrat_saudi', label: 'Harrat lava fields', country: 'Saudi Arabia', bbox: [39.5, 22.0, 42.5, 24.5] },
  { run: 'altiplano_puna', label: 'Altiplano–Puna', country: 'Chile / Bolivia / Argentina', bbox: [-69.5, -24.5, -66.5, -21.5] },
  { run: 'namibia_south', label: 'Southern Namibia', country: 'Namibia', bbox: [16.0, -28.5, 18.5, -25.5] },
  { run: 'afar', label: 'Afar', country: 'Ethiopia / Eritrea', bbox: [40.0, 11.5, 42.5, 14.0] },
];
const fmtLatLng = (lat, lng) => `${Math.abs(lat)}°${lat < 0 ? 'S' : 'N'}, ${Math.abs(lng)}°${lng < 0 ? 'W' : 'E'}`;
const moonBase = id => MOON_BASES.find(b => b.id === id);
const byKey = Object.fromEntries(CRITERIA.map(c => [c.key, c]));
const COLORS = { earth: '#6CB4EE', moon: '#E8E3D3', newSite: '#F0C85D', known: '#A7BAC7', signal: '#3CC8B4' };

const state = {
  sites: [], targets: {}, info: {}, columns: new Set(),
  crit: {},              // per base: { KEY: { counts, weight, method, moon, unit, earthUnit } }, same shape for both data formats
  heat: null, cells: [], // pipeline heatmap points and searched cells
  base: 'polar', group: 'all', active: new Set(), threshold: 0.7,
  typeFilter: 'all', selected: null, globe: null, moon: null,
  knownOpen: false,      // the folded "Known analog sites" box under the ranking
  excludedOpen: false,   // the folded "Excluded after scoring" box (config-v1.1 post-run filters)
  view: 'globe', moonColours: false,   // 'globe' or 'terrain' (3D close-up of the selected site)
};

/* ---------- Loading ---------- */

// Access (criterion 26, display only, docs/ACCESS.md): travel time to the nearest city (Weiss et al. 2018) and
// straight-line distance to the nearest medium/large airport (OurAirports), one value per place.
// If the export already puts ACCESS_HOURS / AIRPORT_* into raw_values.csv, those win. Otherwise we join Mateo's
// file on RUN/CELL (night export: RUN "night_polar" = run "polar") or, for the first-run data, on the nearest
// Polar point within 1.5 km (same craters, low points within 0.5 km of each other).
const ACCESS_MATCH_KM = 1.5;
function kmBetween(lat1, lon1, lat2, lon2) {
  const r = Math.PI / 180, x = (lon2 - lon1) * r * Math.cos((lat1 + lat2) / 2 * r), y = (lat2 - lat1) * r;
  return 6371 * Math.hypot(x, y);
}
function attachAccess(rows) {
  const byCell = new Map(rows.map(a => [`night_${a.run}|${a.cell}`, a]));
  const polar = rows.filter(a => a.run === 'polar' && a.lat != null && a.lon != null);
  for (const s of state.sites) {
    let a = s.RUN ? byCell.get(`${s.RUN}|${s.CELL}`) : null;
    if (!a && !s.missed && !s.unscored && (s.BASE_TYPE ?? 'polar') === 'polar' && s.LAT != null) {
      let best = Infinity;
      for (const p of polar) {
        if (Math.abs(p.lat - s.LAT) > 0.05) continue;
        const d = kmBetween(s.LAT, s.LON, p.lat, p.lon);
        if (d < best) { best = d; a = p; }
      }
      if (best > ACCESS_MATCH_KM) a = null;
    }
    if (a) s.access = { ACCESS_HOURS: a.ACCESS_HOURS, AIRPORT_KM: a.AIRPORT_KM, AIRPORT_NAME: a.AIRPORT_NAME, AIRPORT_TYPE: a.AIRPORT_TYPE,
      STATION_NAME: a.STATION_NAME, STATION_KM: a.STATION_KM, STATION_TYPE: a.STATION_TYPE,
      ANALOG_STATION_NAME: a.ANALOG_STATION_NAME, ANALOG_STATION_KM: a.ANALOG_STATION_KM };
  }
}
function accessOf(s) {
  const raw = s.raw ?? {};
  return raw.ACCESS_HOURS != null || raw.AIRPORT_KM != null ? raw : (s.access ?? null);
}
function fmtTravel(h) {
  if (h == null) return null;
  if (h < 1) return `~${Math.max(5, Math.round(h * 60 / 5) * 5)} min`;
  if (h < 48) return `~${Math.round(h)} h`;
  return `~${Math.round(h / 24)} days`;
}
function accessHTML(s) {
  const a = accessOf(s);
  if (!a) return '';
  const t = fmtTravel(a.ACCESS_HOURS), km = a.AIRPORT_KM;
  if (t == null && km == null) return '';
  const kind = a.AIRPORT_TYPE === 'large_airport' ? 'large airport' : 'medium airport';
  return `<p class="impact-line access-line" title="Modelled travel time over land to the nearest city (a place with 1,500+ people per km² or 50,000+ inhabitants), roads of 2015 (Weiss et al. 2018, Malaria Atlas Project). Airport: straight-line distance, OurAirports; says nothing about flights.">
    <span>Access</span> ${t == null ? 'no travel-time data' : `<b>${t}</b> to the nearest city`}${km == null ? '' : ` · ${Math.round(km).toLocaleString('en')} km to ${esc(a.AIRPORT_NAME ?? 'an airport')} (${kind})`}</p>`;
}

// Nearest research station (Mateo's c29, docs/ACCESS.md R5). The list (INTERACT + our 6 planetary analog
// stations) is polar and alpine, so a station is shown only within STATION_MAX_KM: farther means "not in our list",
// not "no station". Straight-line km; display only.
const STATION_MAX_KM = 500;
const kmText = km => `${Math.round(km).toLocaleString('en')} km`;
function stationHTML(s) {
  const a = s.access;
  if (!a || a.STATION_KM == null) return '';
  const near = a.STATION_KM <= STATION_MAX_KM;
  const sameAnalog = a.ANALOG_STATION_NAME && a.ANALOG_STATION_NAME === a.STATION_NAME;
  const main = near
    ? `${esc(a.STATION_NAME)}, <b>${kmText(a.STATION_KM)}</b>${sameAnalog ? ' (planetary analog station)' : a.STATION_TYPE ? ` (${esc(a.STATION_TYPE)})` : ''}`
    : `none in our list within ${STATION_MAX_KM} km`;
  const analog = !sameAnalog && a.ANALOG_STATION_KM != null && a.ANALOG_STATION_KM <= STATION_MAX_KM
    ? `<br>Planetary analog station: ${esc(a.ANALOG_STATION_NAME)}, <b>${kmText(a.ANALOG_STATION_KM)}</b>` : '';
  return `<p class="impact-line station-line" title="Straight-line distance to the nearest station in the INTERACT list (Arctic and alpine research stations) and our list of 6 planetary analog stations (HMPRS, FMARS, MDRS, HI-SEAS, Biosphere 2, LunAres). The list covers polar and alpine regions: far away means 'not in this list', not 'no station'.">
    <span>Research station</span> ${main}${analog}</p>`;
}

function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  const head = lines.shift().split(',').map(s => s.trim());
  const rows = lines.filter(Boolean).map(line => {
    // Split on commas outside double quotes ("Svalbard Airport, Longyear" stays one cell).
    const cells = line.includes('"')
      ? (line.match(/("([^"]|"")*"|[^,]*)(,|$)/g) ?? []).map(c => c.replace(/,$/, '').replace(/^"|"$/g, '').replace(/""/g, '"'))
      : line.split(',');
    const row = {};
    head.forEach((h, i) => {
      const raw = (cells[i] ?? '').trim();
      // Agreed rule: an empty cell means "no data", never zero.
      row[h] = raw === '' ? null : (TEXT_COLUMNS.has(h) ? raw : Number(raw));
    });
    return row;
  });
  return { head, rows };
}
const TEXT_COLUMNS = new Set(['SITE', 'RUN', 'CELL', 'BASE_TYPE', 'IMPACT_NAME', 'IMPACT_SOURCE',
  'run', 'cell', 'AIRPORT_NAME', 'AIRPORT_TYPE', 'AIRPORT_IDENT',
  'ROLE', 'NAME', 'COUNTRY', 'MISSED_REASON',
  'EXCLUDED', 'EXCLUDED_DETAIL', 'BEST_TARGET',
  'ROCK_CLASS', 'ROCK_CLASS_NAME',     // night export text columns (EXCLUDED*: config-v1.1; ROCK_CLASS*: GLiM display)
  'ROCK_SITE', 'ROCK_SITE_LITH', 'ROCK_SITE_SOURCE', 'ROCK_SITE_SCALE',
  'STATION_NAME', 'STATION_TYPE', 'ANALOG_STATION_NAME']);   // nearest research / analog station (c29, display)   // Macrostrat map unit at the site (display)

// Rock type on Mare cards, display only (never in the score). Site level: the geological map unit under the base
// pad from Macrostrat (CC BY 4.0); how fine it is depends on the source map (ROCK_SITE_SCALE). Regional: GLiM 0.5° grid.
function rockHTML(s) {
  const raw = s.raw ?? {};
  if (s.BASE_TYPE !== 'mare') return '';
  const lith = raw.ROCK_SITE_LITH || raw.ROCK_SITE;
  const where = [raw.ROCK_SITE_SOURCE, raw.ROCK_SITE_SCALE ? `${raw.ROCK_SITE_SCALE}-scale map` : null].filter(Boolean).join(', ');
  const site = lith ? `<p class="impact-line rock-line" title="Geological map unit at the base pad${raw.ROCK_SITE ? `: ${esc(raw.ROCK_SITE)}` : ''}. Source: Macrostrat (macrostrat.org), CC BY 4.0. How fine the map is depends on the source map."><span>Rock at site</span> ${esc(lith)}${where ? ` (${esc(where)})` : ''}${raw.BASALT_SITE === 1 ? ' <span class="tag-basalt">Basalt at site</span>' : ''}</p>` : '';
  const region = raw.ROCK_CLASS_NAME ? `<p class="impact-line rock-line" title="Dominant rock class of the 0.5° grid cell (about 55 km), GLiM (Hartmann &amp; Moosdorf 2012), CC BY 3.0."><span>Rock, regional</span> ${esc(raw.ROCK_CLASS_NAME)}, regional (0.5° map)</p>` : '';
  return site + region;
}

const getText = url => fetch(url).then(r => { if (!r.ok) throw new Error(url); return r.text(); });
const getJSON = url => fetch(url).then(r => { if (!r.ok) throw new Error(url); return r.json(); });
const optional = (url, fallback) => (url ? getJSON(url).catch(() => fallback) : Promise.resolve(fallback));

async function loadAll() {
  const [csv, targets, info, rawCsv, heat, cells, coordsCsv, accessCsv, candidates] = await Promise.all([
    getText(DATA.scores),
    getJSON(DATA.targets),
    optional(DATA.info, {}),
    DATA.raw ? getText(DATA.raw).catch(() => '') : Promise.resolve(''),
    optional(DATA.heatmap, null),
    optional(DATA.cells, []),
    DATA.coords ? getText(DATA.coords).catch(() => '') : Promise.resolve(''),
    DATA.access ? getText(DATA.access).catch(() => '') : Promise.resolve(''),
    optional(DATA.candidates, null),
  ]);
  const { head, rows } = parseCSV(csv);
  const rawRows = rawCsv ? parseCSV(rawCsv).rows : [];
  const rawFor = r => rawRows.find(x => (r.RUN && x.RUN === r.RUN && x.CELL === r.CELL) || x.SITE === r.SITE) ?? {};
  state.columns = new Set(head);
  state.sites = rows.map(r => ({ ...r, lat: r.LAT, lng: r.LON, raw: rawFor(r) }));
  // Known analog sites the pipeline hasn't scored yet (it has only run on a few regions so far): kept as a
  // reference, in a small box under the ranking and as faint dots on the globe, with their research notes.
  // Team candidates without a score (the valleys) are left out. Only coordinates are read from the
  // sample file, never its fake values.
  if (coordsCsv) {
    const have = new Set(state.sites.map(x => x.SITE));
    parseCSV(coordsCsv).rows.filter(r => info[r.SITE]?.type === 'known' && !have.has(r.SITE) && r.LAT != null && r.LON != null)
      .forEach(r => state.sites.push({ SITE: r.SITE, LAT: r.LAT, LON: r.LON, lat: r.LAT, lng: r.LON, raw: {}, unscored: true }));
  }
  // Known craters our method searched but missed (type "missed", with lat/lng in site_info.json), e.g.
  // Tenoumer: shown on purpose, as an honest example of a limitation of the pipeline settings.
  if (!DATA.isFake) {
    // Night export: missed craters are rows of scores.csv with ROLE "missed" (and MISSED_REASON), without scores.
    state.sites.filter(x => x.ROLE === 'missed').forEach(x => { x.missed = true; x.unscored = true; });
    Object.entries(info).filter(([k, v]) => v?.type === 'missed' && v.lat != null && v.lng != null && !state.sites.some(x => x.SITE === k))
      .forEach(([k, v]) => state.sites.push({ SITE: k, LAT: v.lat, LON: v.lng, lat: v.lat, lng: v.lng, raw: {}, unscored: true, missed: true }));
  }
  if (accessCsv) attachAccess(parseCSV(accessCsv).rows);
  state.targets = Object.fromEntries(Object.entries(targets).filter(([k]) => !k.startsWith('_')));
  state.targetPos = targetPositions(candidates);
  // The night export names some cells differently (e.g. "Al Wahbah area r003c1511" instead of
  // "arid_al_wahbah r001c001"); site_info.json → _aliases maps the new name to the same notes.
  for (const [alias, key] of Object.entries(info?._aliases ?? {})) if (info[key] && !info[alias]) info[alias] = info[key];
  state.info = info;
  state.heat = Array.isArray(heat) ? heat : null;
  state.cells = Array.isArray(cells) ? cells : [];
  state.crit = Object.fromEntries(Object.entries(state.targets).map(([base, t]) => [base, criteriaMeta(t)]));
  if (!state.targets[state.base]) state.base = Object.keys(state.targets)[0];
}

// One shape for both formats. Pipeline: targets[base].criteria = [{column, counts, weight, score_method,
// moon: {value, unit, source}, earth_unit}]. Sample: targets[base] = {KEY: 0–1 target}, all counted.
function criteriaMeta(t) {
  if (Array.isArray(t.criteria)) {
    return Object.fromEntries(t.criteria.map(c => [c.column, {
      counts: !!c.counts, weight: c.weight ?? 0, method: c.score_method,
      moon: c.moon?.value ?? null, unit: c.moon?.unit ?? '', source: c.moon?.source ?? null, earthUnit: c.earth_unit ?? '',
      limitation: c.limitation ?? null,   // e.g. light: Sun disc on the Moon vs Sun centre on Earth
      fact: c.fact ?? null,               // e.g. Grazing sun: no Earth analog possible
      // 'more is better' (Drivable, Bare, Ground ice), 'fact' (Impact crater 1/0) or 'raw only' (Crater size):
      // NOT a similarity to the Moon, so never on the radar or in the Moon chips; shown in "On the ground".
      kind: c.display_kind ?? null,
    }]));
  }
  return Object.fromEntries(Object.entries(t).filter(([k, v]) => k !== 'label' && typeof v === 'number').map(([k, v]) => [k, {
    counts: true, weight: 1, method: 'target', moon: v, unit: '', source: null, earthUnit: '',
  }]));
}

/* ---------- Scoring ---------- */

const target = () => state.targets[state.base] ?? {};
const meta = key => state.crit[state.base]?.[key];
const isPractical = c => c.group === 'practical';
const isPipeline = () => !DATA.isFake;
// Criteria the Moon target knows for this base (counted, display-only, or still awaiting a lunar value).
const isGroundValue = key => !!meta(key)?.kind;   // display_kind set: not a similarity to the Moon
const baseCriteria = () => CRITERIA.filter(c => !isPractical(c) && c.bases.includes(state.base) && meta(c.key) && !isGroundValue(c.key));
// "On the ground": values about the place itself, not compared with the Moon.
const groundCriteria = () => CRITERIA.filter(c => c.bases.includes(state.base) && isGroundValue(c.key));
// Criteria that make up the total score.
const similarityCriteria = () => baseCriteria().filter(c => meta(c.key).counts);

// Similarity to the Moon, 0–1 (1 = same as the Moon). Pipeline: the value in scores.csv already is it.
// Sample: 1 − |site − target|. Practical criteria: their own score (higher = easier to use).
function sim(site, c) {
  const v = site[c.key];
  if (v == null) return null;
  if (isPractical(c) || isPipeline()) return v;
  const m = meta(c.key);
  return m?.moon == null ? null : 1 - Math.abs(v - m.moon);
}
// Raw Earth value (pipeline: raw_values.csv; sample: the 0–1 value itself).
const rawOf = (site, c) => (isPipeline() ? site.raw?.[c.key] ?? null : site[c.key]);
const hasData = key => state.sites.some(s => s[key] != null);

function scoreSite(site) {
  const details = baseCriteria().map(c => {
    const m = meta(c.key), s = sim(site, c), earth = rawOf(site, c);
    return { ...c, sim: s, earth, moon: m.moon, counts: m.counts, method: m.method,
      signed: earth != null && m.moon != null ? earth - m.moon : null };
  });
  const counted = details.filter(d => d.counts && d.sim != null);
  const wsum = counted.reduce((a, d) => a + (meta(d.key).weight || 1), 0);
  const own = counted.length ? counted.reduce((a, d) => a + d.sim * (meta(d.key).weight || 1), 0) / wsum : null;
  // Pipeline: SCORE_TOTAL is the weighted mean of the counted criteria, already computed.
  const total = isPipeline() && site.SCORE_TOTAL != null ? site.SCORE_TOTAL : own;
  return { sim: total, details, coverage: counted.length, possible: similarityCriteria().length };
}

const typeOf = site => (site.missed ? 'missed' : state.info[site.SITE]?.type ?? 'candidate');   // missed: night export ROLE or site_info
const nameOf = site => state.info[site.SITE ?? site]?.name ?? site.SITE ?? site;
// Tuning regions (CLAUDE.md, "do not count for validation"): used to check and set up the method, so a
// high rank there is partly built in. Screening regions (Al Wahbah, Roter Kamm, ...) are the fair results.
const TUNING_RUNS = new Set(['meteor_crater', 'pinacate', 'sf_volcanic']);
const isTuning = site => TUNING_RUNS.has(site.RUN) || site.ROLE === 'tuning';   // night export: ROLE column
const TUNING_NOTE = 'Tuning site: we used this region to check and set up our method, so its rank is partly built in and does not count as an independent result.';

// Active filters: a site passes when it has data and matches at least the threshold on every selected criterion.
function passesFilters(site) {
  for (const key of state.active) {
    const v = sim(site, byKey[key]);
    if (v == null || v < state.threshold) return false;
  }
  return true;
}

// The night export has Polar and Mare rows in one file (BASE_TYPE). Each base is ranked on its own: a Mare
// place is scored against the lunar mare, so it must never show up in the Polar ranking. Rows without
// BASE_TYPE (first-run data, known sites not scored yet, missed craters) show for every base.
const ofBase = s => s.BASE_TYPE == null || s.BASE_TYPE === state.base;
// config-v1.1 post-run filters (outputs/README.md): an EXCLUDED place (open-pit mine, bowl that is not dry) keeps
// its score (excludedSim) but is not ranked, not in the heatmap and not on the globe; it is listed in a folded
// box with its reason.
function ranked() {
  return state.sites.filter(ofBase)
    .map(s => {
      const sc = scoreSite(s);
      return s.EXCLUDED ? { ...s, ...sc, sim: null, excludedSim: sc.sim, type: typeOf(s) } : { ...s, ...sc, type: typeOf(s) };
    })
    .sort((a, b) => (b.sim ?? -1) - (a.sim ?? -1))
    .map((s, i) => ({ ...s, rank: s.sim == null ? null : i + 1, passes: passesFilters(s) }));
}
const visibleSites = () => ranked().filter(s => s.passes);
// Readable names for the pipeline's search regions (RUN in scores.csv / run in cells.json).
const REGION_COLORS = { found: '#3CC8B4', none: '#FF8A70' };
const RUN_LABELS = {
  svalbard_nordenskiold: 'Svalbard · Nordenskiöld Land', ellesmere_fosheim: 'Ellesmere Island · Fosheim Peninsula',
  greenland_peary_land: 'Greenland · Peary Land', greenland_kangerlussuaq: 'Greenland · Kangerlussuaq',
  arid_al_wahbah: 'Saudi Arabia · Al Wahbah', arid_tenoumer: 'Mauritania · Tenoumer', arid_roter_kamm: 'Namibia · Roter Kamm',
  meteor_crater: 'Arizona · Meteor Crater', pinacate: 'Mexico · El Pinacate',
};
const runLabel = r => RUN_LABELS[r] ?? r.replace(/_/g, ' ').replace(/^./, c => c.toUpperCase());
// Every searched region, from cells.json: centre, outline and what was found.
// Night (world-grid) runs are scattered over the whole Earth: one outline around them would wrap the globe, so
// they are left out here (their places show in the list, heatmap and globe; their cells in the 3D view).
function searchedRegions() {
  const by = {};
  state.cells.filter(c => !/^night_/.test(c.run ?? '')).forEach(c => {
    const r = by[c.run] ??= { run: c.run, label: runLabel(c.run), cells: 0, ranked: 0, bbox: [...c.bbox], status: {} };
    r.cells++; if (c.status === 'ranked') r.ranked++;
    r.status[c.status] = (r.status[c.status] ?? 0) + 1;
    r.bbox = [Math.min(r.bbox[0], c.bbox[0]), Math.min(r.bbox[1], c.bbox[1]), Math.max(r.bbox[2], c.bbox[2]), Math.max(r.bbox[3], c.bbox[3])];
  });
  return Object.values(by).map(r => ({ ...r, lat: (r.bbox[1] + r.bbox[3]) / 2, lng: (r.bbox[0] + r.bbox[2]) / 2 }));
}
const pipelineAreas = () => searchedRegions().map(r => r.label).join(', ') || 'none yet';
const scoredCount = () => state.sites.filter(s => ofBase(s) && !s.EXCLUDED && scoreSite(s).sim != null).length;

// "23.9° vs 27.2°": raw values with a short unit taken from earth_unit (e.g. "deg (inner wall slope)").
function fmtVal(v, unit) {
  if (v == null) return '–';
  const u = (unit || '').split(' (')[0].trim();
  if (u === 'deg') return `${v.toFixed(1)}°`;
  if (u === 'm') return `${Math.round(v)} m`;
  if (u === 'share' || u.startsWith('share of') || (u.includes('fraction') && !u.includes('/'))) return `${Math.round(v * 100)}%`;
  if (u.startsWith('lit fraction /')) return `${v.toFixed(2)}×`;     // sunlight relative to flat land
  if (u.startsWith('distance /')) return `${v.toFixed(2)} r`;         // in crater radii
  return Math.abs(v) >= 10 ? v.toFixed(0) : v.toFixed(2);
}

/* ---------- Helpers ---------- */

const esc = s => String(s ?? '').replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
const pct = v => (v == null ? '–' : Math.round(v * 100) + '%');
// Similarity score as shown. Mare scores sit at 97–99.6 %, so whole percents would show "100%" for many places:
// for Mare, one decimal, and never "100%" unless the score is exactly 1. Display only, the scores are unchanged.
const isMareSite = site => (site?.BASE_TYPE ?? state.base) === 'mare';
const scoreText = (v, site) => (v == null ? '–' : !isMareSite(site) ? pct(v)
  : v >= 1 ? '100%' : `${Math.min(99.9, Math.round(v * 1000) / 10).toFixed(1)}%`);
// Macrostrat: basalt / mafic volcanic rock in the map unit at the Mare base pad (1); 0 = other rock, empty = unknown.
const basaltAtSite = site => site?.raw?.BASALT_SITE === 1;
const fmtCoord = (lat, lng) => `${Math.abs(lat).toFixed(2)}°${lat >= 0 ? 'N' : 'S'}, ${Math.abs(lng).toFixed(2)}°${lng >= 0 ? 'E' : 'W'}`;
const research = s => esc(s).replace(/\[([^\]]+)\]/g, '<span class="todo">[$1]</span>');
// Source links under a research box; only http(s) links, opened in a new tab.
const sourcesHTML = list => {
  const ok = (list ?? []).filter(x => /^https?:\/\//.test(x?.url ?? ''));
  if (!ok.length) return '';
  return `<p class="sources-title">Sources</p><ul class="sources">${ok.map(x =>
    `<li><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.label || x.url)}</a></li>`).join('')}</ul>`;
};
// Numbered source list, so lines in "Opportunities & challenges" can point to [1], [2]...
const numberedSourcesHTML = list => {
  const items = (list ?? []).map((x, i) => ({ ...x, n: i + 1 })).filter(x => /^https?:\/\//.test(x?.url ?? ''));
  if (!items.length) return '';
  return `<p class="sources-title">Sources</p><ol class="sources">${items.map(x =>
    `<li value="${x.n}"><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.label || x.url)}</a></li>`).join('')}</ol>`;
};
// One line of the outlook box: text + its source numbers ("ours" = our own pipeline measurement).
const outlookLine = (item, sources) => {
  const text = String(item.text ?? '').replace(/^Our data:\s*/, '');
  const refs = [...(item.src ?? [])].sort((a, b) => (a === 'ours') - (b === 'ours') || a - b).map(r => {
    if (r === 'ours') return '<span class="ref-ours" title="Measured by our pipeline (config-v1), not from a publication">our data</span>';
    const s = sources?.[r - 1];
    return s && /^https?:\/\//.test(s.url ?? '') ? `<a class="ref" href="${esc(s.url)}" target="_blank" rel="noopener" title="${esc(s.label)}">[${r}]</a>` : '';
  }).join('');
  return `<li>${esc(text.charAt(0).toUpperCase() + text.slice(1))} ${refs}</li>`;
};
const outlookHTML = info => {
  const o = info.outlook;
  if (!o) return '';
  const list = (cls, title, items) => items?.length ? `<p class="outlook-title ${cls}">${title}</p><ul class="outlook ${cls}">${items.map(it => outlookLine(it, info.sources)).join('')}</ul>` : '';
  return list('opp', 'Opportunities', o.opportunities) + list('chal', 'Challenges', o.challenges);
};
const baseLabel = () => BASES.find(b => b.id === state.base)?.label ?? state.base;

// Places nobody has researched yet (most of the night run's ~1,800 world cells): instead of "[to research]",
// short lines built only from our own measurements, each tagged "our data". No outside facts are invented;
// what our data cannot know (land owner, permits, natural crater or mine) is said as a challenge.
const pctR = v => `${Math.round(v * 100)}%`;
function travelText(h) { return h < 1 ? 'less than an hour' : h < 48 ? `about ${Math.round(h)} h` : `about ${Math.round(h / 24)} days`; }
function autoNotes(s, strengths, gaps) {
  const raw = s.raw ?? {}, mare = (s.BASE_TYPE ?? state.base) === 'mare';
  const lat = s.LAT ?? s.lat, ns = lat >= 0 ? 'N' : 'S';
  const breaks = [], opp = [], chal = [];
  const sunMax = raw.GRAZING_SUN ?? (lat == null ? null : Math.min(90, 90 - Math.abs(lat) + 23.44));
  if (!mare) {
    if (sunMax != null) breaks.push(`At ${Math.abs(lat).toFixed(0)}° ${ns} the Sun climbs to about ${Math.round(sunMax)}° at its highest; at Shackleton it never gets above 1.9°.`);
    if (raw.DARK_FLOOR != null) breaks.push(`The darkest part of its floor is in shadow ${pctR(raw.DARK_FLOOR)} of the time; Shackleton's floor never sees the Sun.`);
    const w = raw.CRATER_DIAMETER_EQUIV_M ?? raw.DIAMETER_EQUIV_M;
    if (w) breaks.push(`It is about ${(w / 1000).toFixed(1)} km wide; Shackleton is 20.9 km, about ${Math.round(20900 / w)} times wider.`);
  } else {
    breaks.push('Our Mare score compares only the shape of the ground. The Moon’s maria are dark basalt; rock type is not compared yet.');
  }
  // General fact, not a measurement: the card shows it without the "our data" tag.
  const general = 'Like every place on Earth: air, weather, full gravity and protection from radiation, none of which the Moon has.';
  const a = accessOf(s);
  if (strengths.length) opp.push({ text: `Closest to the Moon in: ${strengths.map(d => d.label.toLowerCase()).join(', ')}.`, src: ['ours'] });
  if (s.IMPACT_CRATER === 1) opp.push({ text: `A confirmed impact crater${raw.IMPACT_NAME ? ` (${raw.IMPACT_NAME})` : ''}, formed by an impact like Shackleton.`, src: ['ours'] });
  const drive = mare ? raw.DRIVABLE : s.DRIVABLE;
  if (drive != null && drive >= 0.8) opp.push({ text: `${pctR(drive)} of the ground ${mare ? 'within 5 km' : 'around the base spot'} is gentle enough to drive: room for rover tests.`, src: ['ours'] });
  if (!mare && s.BARE != null && s.BARE >= 0.8) opp.push({ text: `Bare ground on ${pctR(s.BARE)} of the floor and rim, with no trees or fields in the way.`, src: ['ours'] });
  if (a?.ACCESS_HOURS != null && a.ACCESS_HOURS <= 3) opp.push({ text: `${travelText(a.ACCESS_HOURS)[0].toUpperCase() + travelText(a.ACCESS_HOURS).slice(1)} from the nearest city by land (2015 roads): easy to reach for a field team.`, src: ['ours'] });
  if (gaps.length) chal.push({ text: `Furthest from the Moon in: ${gaps.map(d => d.label.toLowerCase()).join(', ')}.`, src: ['ours'] });
  if (!mare && s.GROUND_ICE != null && s.GROUND_ICE >= 0.2) chal.push({ text: `Snow or ice covers ${pctR(s.GROUND_ICE)} of the floor.`, src: ['ours'] });
  if (a?.ACCESS_HOURS != null && a.ACCESS_HOURS > 12) chal.push({ text: `Remote: ${travelText(a.ACCESS_HOURS)} from the nearest city by land (2015 roads).`, src: ['ours'] });
  chal.push({ text: `Not checked yet: who owns the land, whether visits need a permit${mare ? '' : ', and whether the bowl is natural (an open-pit mine looks the same in elevation data)'}.`, src: [] });
  return { breaks, general, outlook: { opportunities: opp, challenges: chal } };
}

/* ---------- Filter bar ---------- */

function renderFilters() {
  // Group tabs, with a count of active criteria per group
  const counts = {};
  state.active.forEach(k => { const g = byKey[k].group; counts[g] = (counts[g] ?? 0) + 1; });
  // Only criteria someone can actually use: meant for this base and with data. Groups left empty are hidden.
  const usable = c => c.bases.includes(state.base) && hasData(c.key);
  const groups = GROUPS.filter(g => CRITERIA.some(c => c.group === g.id && usable(c)));
  if (state.group !== 'all' && !groups.some(g => g.id === state.group)) state.group = 'all';
  document.getElementById('groupTabs').innerHTML =
    [{ id: 'all', label: 'All criteria' }, ...groups].map(g =>
      `<button type="button" class="tab" role="tab" data-group="${g.id}" aria-selected="${g.id === state.group}">${esc(g.label)}${counts[g.id] ? `<span class="count">${counts[g.id]}</span>` : ''}</button>`).join('');

  // Sub-row: the criteria of the chosen group
  const sub = document.getElementById('subRow');
  sub.hidden = state.group === 'all';
  if (!sub.hidden) {
    const g = GROUPS.find(x => x.id === state.group);
    document.getElementById('subHint').textContent = state.group === 'practical'
      ? 'Practical criteria do not change the similarity score. Pick one to hide sites that score below the minimum.'
      : 'Pick criteria to keep only sites close to the Moon on them.';
    document.getElementById('criterionChips').innerHTML = CRITERIA.filter(c => c.group === g.id && usable(c)).map(c => {
      const noData = !hasData(c.key);
      const notForBase = !c.bases.includes(state.base);
      const disabled = noData || notForBase;
      const m = meta(c.key);
      const tag = notForBase ? `not for ${baseLabel()}`
        : noData ? (m?.kind === 'raw only' ? 'size shown on the card' : m?.method === 'rank' ? 'awaiting lunar value' : m?.method === 'not computed' ? 'not computed yet' : 'no data yet')
        : m && !m.counts && !isPractical(c) ? 'not in score' : '';
      return `<button type="button" class="crit" data-key="${c.key}" aria-pressed="${state.active.has(c.key)}" ${disabled ? 'disabled' : ''} title="${esc(c.hint)}">${esc(c.label)}${tag ? ` <span class="tag">${esc(tag)}</span>` : ''}</button>`;
    }).join('');
  }

  // Active filter summary
  const activeRow = document.getElementById('activeRow');
  activeRow.hidden = state.active.size === 0;
  document.getElementById('activeChips').innerHTML = [...state.active].map(k =>
    `<button type="button" class="chip-x" data-remove="${k}" aria-label="Remove filter ${esc(byKey[k].label)}">${esc(byKey[k].label)} ✕</button>`).join('');
  document.getElementById('thresholdOut').textContent = Math.round(state.threshold * 100) + '%';
}

// Pick a lunar base type (on the Moon globe or its buttons): Earth sites are re-ranked against it.
// With Earth scores for that base, its closest Earth twin is selected and the Earth turns to it, while the top
// three pulse on the globe and in the list. Without scores yet (Mare tonight), the Earth shows where we search.
let twinTimer = null;
function setBase(id, fly) {
  state.moonInfo = id;
  state.moonTarget = null;   // back to today's target of that base
  const ready = !!state.targets[id];
  if (ready) {
    state.base = id;
    // Drop filters that do not apply to the new base type
    [...state.active].forEach(k => { if (!byKey[k].bases.includes(state.base)) state.active.delete(k); });
    const top = visibleSites().filter(x => x.sim != null);
    if (top.length) state.selected = bestTwin(top).SITE;
    state.twinFlash = top.slice(0, 3).map(x => x.SITE);
    if (state.globe && !DATA.isFake) {   // heatmap of the new base
      heatPoints = baseHeat();
      if (heatShown) state.globe.heatmapsData([{ points: heatPoints }]);
      setHeatNote();
    }
    clearTimeout(twinTimer);
    twinTimer = setTimeout(() => { state.twinFlash = []; renderList(); updateGlobe(false); }, 7000);
  }
  setEarthPaths();
  renderFilters();
  renderList();
  renderCard();
  if (!fly) updateGlobe(false);
  else if (ready && state.view === 'terrain') { updateGlobe(false); flyTerrainTo(currentSite()); }
  else if (ready) updateGlobe(true);
  else { updateGlobe(false); showPlanned(); }
  syncViewUI();
  updateMoon(fly);
}
// The best independent twin: tuning sites (Meteor Crater, Pinacate) rank high partly by design, so skip them.
const bestTwin = list => list.find(x => !isTuning(x)) ?? list[0];
const twinsOf = () => visibleSites().filter(x => x.sim != null).slice(0, 3);

function wireFilters() {
  document.getElementById('groupTabs').addEventListener('click', e => {
    const t = e.target.closest('[data-group]'); if (!t) return;
    state.group = t.dataset.group;
    renderFilters(); renderCard();
  });
  document.getElementById('criterionChips').addEventListener('click', e => {
    const c = e.target.closest('[data-key]'); if (!c || c.disabled) return;
    state.active.has(c.dataset.key) ? state.active.delete(c.dataset.key) : state.active.add(c.dataset.key);
    refresh();
  });
  document.getElementById('activeChips').addEventListener('click', e => {
    const c = e.target.closest('[data-remove]'); if (!c) return;
    state.active.delete(c.dataset.remove); refresh();
  });
  document.getElementById('clearFilters').addEventListener('click', () => { state.active.clear(); refresh(); });
  document.getElementById('threshold').addEventListener('input', e => { state.threshold = Number(e.target.value) / 100; refresh(); });
  document.querySelectorAll('.list-panel .seg button').forEach(b => b.addEventListener('click', () => {
    state.typeFilter = b.dataset.filter;
    document.querySelectorAll('.list-panel .seg button').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
    renderList();
  }));
}

/* ---------- Site list ---------- */

// Long rankings (night run: 1,825 places) show the best LIST_STEP first; "Show more" adds LIST_STEP more.
const LIST_STEP = 20;
function siteRowHTML(s) {
  return `
    <li>
      <button type="button" class="site-btn${state.twinFlash?.includes(s.SITE) ? ' is-twin' : ''}" data-site="${esc(s.SITE)}" aria-current="${s.SITE === state.selected}">
        <span class="rank ${s.type === 'known' ? 'known' : 'new'}">${s.rank ?? '–'}</span>
        <span>
          <span class="site-name">${esc(nameOf(s))}</span>
          <span class="site-meta">
            ${s.sim == null ? '<span class="not-scored">Not scored yet</span>' : `<span class="bar"><span style="width:${Math.round(s.sim * 100)}%"></span></span>
            <span class="pct">${scoreText(s.sim, s)}</span>`}
            <span>${s.type === 'known' ? 'Known' : 'New'}</span>
            ${isTuning(s) ? `<span class="tag-tuning" title="${esc(TUNING_NOTE)}">Tuning</span>` : ''}
            ${basaltAtSite(s) ? '<span class="tag-basalt" title="Macrostrat geological map: basalt or mafic volcanic rock at the base pad (display only, not in the score)">basalt at site</span>' : ''}
          </span>
        </span>
      </button>
    </li>`;
}
function renderList() {
  const list = document.getElementById('siteList');
  const ofType = s => state.typeFilter === 'all' || s.type === state.typeFilter;
  // Mare: optional "basalt at site only" (offered only when some place has BASALT_SITE = 1).
  const mareList = state.base === 'mare' && isPipeline();
  const hasBasalt = mareList && visibleSites().some(basaltAtSite);
  if (!hasBasalt) state.basaltOnly = false;
  const rows = visibleSites().filter(s => s.sim != null && ofType(s) && (!state.basaltOnly || basaltAtSite(s)));   // the ranking: scored sites only
  const reference = visibleSites().filter(s => s.sim == null && !s.missed && !s.EXCLUDED && ofType(s));   // known analogs, not scored yet
  const excluded = visibleSites().filter(s => s.EXCLUDED).sort((a, b) => (b.excludedSim ?? -1) - (a.excludedSim ?? -1));
  const missedSites = visibleSites().filter(s => s.missed);
  const total = scoredCount(), shown = visibleSites().filter(s => s.sim != null).length;
  document.getElementById('listHint').textContent = state.active.size
    ? `${shown} of ${total} sites pass the filters. Ranked by similarity to a ${baseLabel().toLowerCase()} base.`
    : `Ranked by similarity to ${moonBase(state.base) ? `${moonBase(state.base).name} (${baseLabel().toLowerCase()} base)` : `a ${baseLabel().toLowerCase()} base`} on the ${similarityCriteria().length} criteria that count.`;
  const mareNote = document.getElementById('mareNote');
  mareNote.hidden = !mareList;
  if (mareList) {
    mareNote.innerHTML = 'Flat, smooth mare-like terrain is common on Earth, so the top places differ only slightly. Rock at site (basalt) and crater texture tell them apart.'
      + (hasBasalt ? ` <label class="basalt-only"><input type="checkbox" id="basaltOnly" ${state.basaltOnly ? 'checked' : ''}> basalt at site only</label>` : '');
    mareNote.querySelector('#basaltOnly')?.addEventListener('change', e => { state.basaltOnly = e.target.checked; state.listLimit = LIST_STEP; renderList(); });
  }
  const pending = state.moonInfo && state.moonInfo !== state.base ? moonBase(state.moonInfo) : null;
  const note = document.getElementById('listNote');
  note.hidden = !pending;
  if (pending) note.innerHTML = `<b>${esc(pending.title)} twins: coming with tonight’s run.</b> We search ${PLANNED_REGIONS.length} volcanic regions for them (outlined on the Earth). The ranking below is still for the ${esc(baseLabel().toLowerCase())} base.`;
  const limit = Math.max(LIST_STEP, state.listLimit ?? LIST_STEP);
  const head = rows.slice(0, limit);
  // The selected site stays visible even when it ranks below the cut (e.g. picked from the guide).
  const sel = rows.slice(limit).find(s => s.SITE === state.selected);
  const more = rows.length - head.length;
  list.innerHTML = rows.length ? head.map(siteRowHTML).join('')
    + (sel ? `<li class="list-gap" aria-hidden="true">⋯</li>${siteRowHTML(sel)}` : '')
    + (more > 0 || limit > LIST_STEP ? `<li class="list-more">
        <span class="muted">Showing ${head.length.toLocaleString('en')} of ${rows.length.toLocaleString('en')}</span>
        ${more > 0 ? `<button type="button" class="region-btn" data-list="more">Show ${Math.min(LIST_STEP, more)} more</button>` : ''}
        ${more > LIST_STEP ? `<button type="button" class="region-btn" data-list="all">Show all</button>` : ''}
        ${limit > LIST_STEP ? `<button type="button" class="region-btn" data-list="less">Show fewer</button>` : ''}
      </li>` : '')
    : '<li class="empty">No site passes these filters. Lower the minimum match or remove a filter.</li>';
  list.querySelectorAll('[data-list]').forEach(b => b.addEventListener('click', () => {
    const k = b.dataset.list;
    state.listLimit = k === 'more' ? limit + LIST_STEP : k === 'all' ? rows.length : LIST_STEP;
    renderList();
    if (k === 'less') list.scrollIntoView({ block: 'start', behavior: reducedMotion ? 'auto' : 'smooth' });
  }));
  // Known analog sites the pipeline hasn't scored yet: a small, folded reference box.
  if (reference.length) {
    list.insertAdjacentHTML('beforeend', `<li class="regions known-ref">
      <details ${state.knownOpen || reference.some(s => s.SITE === state.selected) ? 'open' : ''}>
        <summary class="regions-title">Known analog sites <span class="muted">· not scored yet (${reference.length})</span></summary>
        <p class="regions-hint">Where analog work already happens. Our pipeline hasn't scored these; click one for its notes.</p>
        ${reference.map(s => `<button type="button" class="region-btn site-btn-ref${s.SITE === state.selected ? ' is-current' : ''}" data-site="${esc(s.SITE)}">${esc(nameOf(s))}${state.info[s.SITE]?.validation ? ` <span class="muted">· tested, ${esc(state.info[s.SITE].validation.result)}</span>` : ''}</button>`).join('')}
      </details>
    </li>`);
    list.querySelector('.known-ref details').addEventListener('toggle', e => { state.knownOpen = e.target.open; });
    list.querySelectorAll('.site-btn-ref').forEach(b => b.addEventListener('click', () => select(b.dataset.site, true)));
  }
  // Places taken out after scoring (config-v1.1): open-pit mines and bowls that are not dry. Folded, best first.
  if (excluded.length && state.typeFilter !== 'known') {
    const why = {};
    excluded.forEach(s => s.EXCLUDED.split(' + ').forEach(r => { why[r] = (why[r] ?? 0) + 1; }));
    const top = excluded.slice(0, 40);
    if (state.selected && !top.some(s => s.SITE === state.selected)) {
      const cur = excluded.find(s => s.SITE === state.selected); if (cur) top.push(cur);
    }
    list.insertAdjacentHTML('beforeend', `<li class="regions excluded-ref">
      <details ${state.excludedOpen || top.some(s => s.SITE === state.selected) ? 'open' : ''}>
        <summary class="regions-title">Excluded after scoring <span class="muted">· ${excluded.length} places</span></summary>
        <p class="regions-hint">Taken out of the ranking by our post-run filters (config-v1.1); their scores are unchanged.
          ${Object.entries(why).map(([r, n]) => `${esc(r.replace(/^excluded: /, ''))}: ${n}`).join(' · ')}.
          Best ${Math.min(40, excluded.length)} by score:</p>
        ${top.map(s => `<button type="button" class="region-btn site-btn-ref${s.SITE === state.selected ? ' is-current' : ''}" data-site="${esc(s.SITE)}">${esc(nameOf(s))} <span class="muted">· ${scoreText(s.excludedSim, s)} · ${esc(s.EXCLUDED.replace(/excluded: /g, ''))}</span></button>`).join('')}
      </details>
    </li>`);
    list.querySelector('.excluded-ref details').addEventListener('toggle', e => { state.excludedOpen = e.target.open; });
    list.querySelectorAll('.excluded-ref .site-btn-ref').forEach(b => b.addEventListener('click', () => select(b.dataset.site, true)));
  }
  // Regions the pipeline searched without finding a crater: also a result, worth showing.
  const empty = searchedRegions().filter(r => !r.ranked);
  if (empty.length && !state.active.size && state.typeFilter !== 'known') {
    list.insertAdjacentHTML('beforeend', `<li class="regions">
      <p class="regions-title">Searched, no crater found</p>
      <p class="regions-hint">No bowl at least 50 m deep and 1 km wide in these regions. Click one to see it on the globe.</p>
      ${empty.map(r => `<button type="button" class="region-btn" data-region="${esc(r.run)}" title="${r.cells} grid squares searched">${esc(r.label)}</button>`).join('')}
    </li>`);
    list.querySelectorAll('.region-btn[data-region]').forEach(b => b.addEventListener('click', () => showRegion(b.dataset.region)));
  }
  // A known crater our method missed (Tenoumer): its own block, shown even when every searched region found something.
  if (missedSites.length && !state.active.size && state.typeFilter !== 'known') {
    list.insertAdjacentHTML('beforeend', `<li class="regions">
      <p class="regions-title missed-title">${missedSites.length > 1 ? `Known places our method missed (${missedSites.length})` : 'A known crater our method missed'}</p>
      <p class="regions-hint">Real analog sites our search covered but did not find. Click ${missedSites.length > 1 ? 'one' : 'it'} to see why.</p>
      ${missedSites.map(s => `<button type="button" class="region-btn missed-btn site-btn-ref${s.SITE === state.selected ? ' is-current' : ''}" data-site="${esc(s.SITE)}">${esc(nameOf(s))}</button>`).join('')}
    </li>`);
    list.querySelectorAll('.missed-btn').forEach(b => b.addEventListener('click', () => select(b.dataset.site, true)));
  }
  list.querySelectorAll('.site-btn').forEach(b => b.addEventListener('click', () => select(b.dataset.site, true)));
}

/* ---------- Radar chart (SVG, no library) ---------- */

// Every axis is "similarity to the Moon", 0–1, so the Moon itself is the full outer ring.
// Axis status: ok (counts in the score), display (shown, weight 0), rank / notcomputed / nodata (no value).
function critAxis(site, c) {
  const m = meta(c.key), v = sim(site, c);
  const status = v != null ? (m.counts ? 'ok' : 'display')
    : m.method === 'rank' ? 'rank' : m.method === 'not computed' ? 'notcomputed' : 'nodata';
  return { label: c.label, value: v, status };
}
const AXIS_NOTE = { display: 'not in score', rank: 'awaiting lunar value', notcomputed: 'not computed yet', nodata: 'no data' };

// "All criteria": one axis per group (mean of its criteria) when at least three groups have data,
// otherwise one axis per criterion. A group tab: one axis per criterion in it.
function radarAxes(site) {
  const crits = baseCriteria();
  if (state.group === 'all' || state.group === 'practical') {
    const groups = GROUPS.filter(g => g.id !== 'practical').map(g => {
      const vals = crits.filter(c => c.group === g.id).map(c => sim(site, c)).filter(v => v != null);
      return { label: g.short ?? g.label, value: vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null, status: vals.length ? 'ok' : 'nodata', has: crits.some(c => c.group === g.id) };
    }).filter(a => a.has);
    if (groups.filter(a => a.value != null).length >= 3) return { axes: groups, perGroup: true };
    // Per criterion: only the ones with a value, so the chart stays readable; the rest are listed under it.
    const all = crits.map(c => critAxis(site, c)), withValue = all.filter(a => a.value != null);
    return { axes: withValue.length >= 3 ? withValue : all, perGroup: false };
  }
  return { axes: crits.filter(c => c.group === state.group).map(c => critAxis(site, c)), perGroup: false };
}

function radarSVG(site, axes) {
  if (axes.length < 3) {
    return `<p class="nodata">This group has fewer than three criteria for a ${esc(baseLabel().toLowerCase())} base, so there is no radar. See the chips.</p>`;
  }
  const W = 520, H = 380, cx = W / 2, cy = H / 2 + 4, R = 118, n = axes.length;
  const ang = i => (-90 + (360 / n) * i) * Math.PI / 180;
  const pt = (i, v) => [cx + Math.cos(ang(i)) * R * v, cy + Math.sin(ang(i)) * R * v];
  const xy = (i, v) => pt(i, v).map(x => x.toFixed(1)).join(',');
  const rings = [0.25, 0.5, 0.75].map(f =>
    `<polygon points="${axes.map((_, i) => xy(i, f)).join(' ')}" fill="none" stroke="#24465E" stroke-width="1"></polygon>`).join('');
  const lines = axes.map((a, i) => {
    const [x, y] = pt(i, 1);
    return `<line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="#24465E" ${a.value == null ? 'stroke-dasharray="3 4"' : ''}></line>`;
  }).join('');
  const labels = axes.map((a, i) => {
    const [x, y] = pt(i, 1.14);
    const cos = Math.cos(ang(i));
    const anchor = Math.abs(cos) < 0.2 ? 'middle' : cos > 0 ? 'start' : 'end';
    const off = a.status !== 'ok';
    const note = off ? `<tspan x="${x.toFixed(1)}" dy="13" font-size="10">${AXIS_NOTE[a.status]}</tspan>` : '';
    return `<text x="${x.toFixed(1)}" y="${(y + 4).toFixed(1)}" text-anchor="${anchor}" font-size="11.5" font-family="Fira Sans, sans-serif" fill="${off ? '#8AA2B2' : '#EEF3F6'}">${esc(a.label)}${note}</text>`;
  }).join('');
  // Earth polygon through the axes that have a value; display-only axes get a hollow dot.
  const withVal = axes.map((a, i) => [a, i]).filter(([a]) => a.value != null);
  const dots = withVal.map(([a, i]) => {
    const [x, y] = pt(i, a.value);
    return a.status === 'display'
      ? `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3.5" fill="#06121C" stroke="${COLORS.earth}" stroke-width="1.5"><title>${esc(a.label)}: ${pct(a.value)} (not in score)</title></circle>`
      : `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3.5" fill="${COLORS.earth}"><title>${esc(a.label)}: ${pct(a.value)}</title></circle>`;
  }).join('');
  const earth = withVal.length >= 2
    ? `<polygon points="${withVal.map(([a, i]) => xy(i, a.value)).join(' ')}" fill="rgba(108,180,238,0.22)" stroke="${COLORS.earth}" stroke-width="2.5" stroke-linejoin="round"></polygon>` : '';
  return `<svg class="radar" viewBox="0 0 ${W} ${H}" role="img" aria-label="Radar chart: ${esc(nameOf(site))} compared with the Moon on ${n} axes. The outer ring is the Moon.">
    ${rings}${lines}
    <polygon points="${axes.map((_, i) => xy(i, 1)).join(' ')}" fill="rgba(232,227,211,0.05)" stroke="${COLORS.moon}" stroke-width="2" stroke-dasharray="6 4"></polygon>
    ${earth}${dots}${labels}
  </svg>`;
}

/* ---------- Analog card ---------- */

// "Steep walls 23.9° vs 27.2°" (pipeline, raw values with units) or "0.62 vs 0.80" (sample).
// Card chips: hovering or focusing one shows its definition (defs.js) and this match line.
const chipAttrs = d => `data-def="${esc(d.key)}" data-match="${esc(`${pct(d.sim)} match with the Moon${meta(d.key)?.limitation ? ' · Moon: Sun disc · Earth: Sun centre' : ''}`)}" tabindex="0"`;
const vsText = d => {
  const unit = meta(d.key)?.earthUnit || meta(d.key)?.unit;
  return d.earth == null || d.moon == null ? pct(d.sim) : `${fmtVal(d.earth, unit)} vs ${fmtVal(d.moon, unit)}`;
};

function renderCard() {
  const el = document.getElementById('card');
  const s = ranked().find(r => r.SITE === state.selected);
  if (!s) { el.innerHTML = '<p class="hint">Pick a site from the list or the globe.</p>'; return; }
  const info = state.info[s.SITE] ?? {};
  const isNew = info.type !== 'known';
  const unscored = s.sim == null;
  const missed = s.type === 'missed';   // a known crater our method searched but did not find
  // Chips: criteria with a value, closest to the Moon first. ≥ 50 % = close, below = what it lacks.
  const scored = s.details.filter(d => d.counts && d.sim != null).sort((a, b) => b.sim - a.sim);
  const strengths = scored.filter(d => d.sim >= 0.5).slice(0, 3);
  const gaps = scored.filter(d => d.sim < 0.5).reverse().slice(0, 3);
  // Three kinds of "no value": no data yet, waiting for a lunar value, not computed yet.
  const missing = { nodata: [], rank: [], notcomputed: [] };
  s.details.filter(d => d.sim == null).forEach(d => {
    missing[d.method === 'rank' ? 'rank' : d.method === 'not computed' ? 'notcomputed' : 'nodata'].push(d.label);
  });
  const practical = CRITERIA.filter(c => isPractical(c) && c.bases.includes(state.base) && s[c.key] != null);
  const { axes, perGroup } = radarAxes(s);
  const groupName = state.group === 'all' || state.group === 'practical'
    ? (perGroup ? 'Average per group' : 'All criteria') : GROUPS.find(g => g.id === state.group).label;
  const moonName = (target().label ?? 'Lunar target').split(' (')[0];
  const twin = unscored || missed ? null : closestTwin(s);
  const missingNote = [
    missing.nodata.length && `No data yet: ${missing.nodata.join(', ')}.`,
    missing.rank.length && `Waiting for a lunar value: ${missing.rank.join(', ')}.`,
    missing.notcomputed.length && `Not computed yet: ${missing.notcomputed.join(', ')}.`,
  ].filter(Boolean);
  const raw = s.raw ?? {};
  // Not researched yet (no notes in site_info.json) but scored by the pipeline: lines from our data instead.
  const auto = isPipeline() && !unscored && !missed && !info.breaks && !info.outlook && !info.helps ? autoNotes(s, strengths, gaps) : null;
  const width = raw.CRATER_DIAMETER_EQUIV_M ?? raw.DIAMETER_EQUIV_M, depth = raw.CRATER_RIM_TO_FLOOR_M ?? raw.DEPTH_SPILL_M;
  const craterFacts = [
    width != null && `about ${(width / 1000).toFixed(1)} km wide`,
    depth != null && `${Math.round(depth)} m deep`,
  ].filter(Boolean);
  // On the ground: shares where more is better (bars), plus the impact-crater fact.
  const ground = groundCriteria().filter(c => meta(c.key).kind === 'more is better' && s[c.key] != null);
  const impact = s.IMPACT_CRATER == null ? null : s.IMPACT_CRATER === 1
    ? `Yes: <b>${esc(raw.IMPACT_NAME || 'confirmed impact structure')}</b>${raw.IMPACT_DIAMETER_KM ? `, ${raw.IMPACT_DIAMETER_KM} km` : ''}${/^https?:/.test(raw.IMPACT_SOURCE ?? '') ? ` (<a href="${esc(raw.IMPACT_SOURCE)}" target="_blank" rel="noopener">list</a>)` : ''}`
    : null;   // "not in the list" said little (the list is incomplete), so only a confirmed crater is shown

  el.innerHTML = `
    <div class="card-top">
      <div class="card-title">
        <span class="badge ${missed || s.EXCLUDED ? 'badge-missed' : s.type === 'known' ? 'badge-known' : 'badge-new'}">${s.EXCLUDED ? 'Excluded after scoring' : missed ? 'Missed by our method' : s.type === 'known' ? 'Known analog' : 'New candidate'}</span>
        <h2 style="margin-top:8px">${esc(nameOf(s))}</h2>
        <p class="card-place">${esc(info.place ?? s.COUNTRY ?? '')}${info.place || s.COUNTRY ? ' · ' : ''}${fmtCoord(s.lat, s.lng)}${craterFacts.length ? ' · crater ' + esc(craterFacts.join(', ')) : ''}</p>
        ${twin ? `<p class="card-twin" title="Score against each verified lunar target, same rule and weights; this target scores highest. The rank uses Shackleton.">Closest lunar twin: <b>${esc(twin.label)}</b> (${pct(twin.score)})</p>` : ''}
      </div>
      <div class="score">
        <strong>${scoreText(s.EXCLUDED ? s.excludedSim : s.sim, s)}</strong>
        <span>${s.EXCLUDED ? 'similar to the Moon, but<br>not ranked (config-v1.1)' : missed ? 'not found by our<br>pipeline (config-v1)' : info.validation ? `validation test:<br>${esc(info.validation.result)}` : unscored ? 'not scored yet' : `similar to the Moon (${esc(baseLabel().toLowerCase())} base)<br>rank ${s.RANK ?? s.rank} of ${scoredCount()}`}</span>
      </div>
    </div>

    ${s.EXCLUDED ? `<p class="tuning-note"><span class="tag-tuning">Excluded</span> Reason: ${esc(s.EXCLUDED.split(' + ').map(r => r.replace(/^excluded: /, '')).join(' and '))}${s.raw?.EXCLUDED_DETAIL ? ` (${esc(s.raw.EXCLUDED_DETAIL)})` : ''}. The shape matches, but ${/mine/.test(s.EXCLUDED) ? 'an open-pit mine is not a natural crater' : ''}${/mine/.test(s.EXCLUDED) && /dry/.test(s.EXCLUDED) ? ', and ' : ''}${/dry/.test(s.EXCLUDED) ? 'a bowl with plants, ice or water is no stand-in for a dry lunar crater' : ''}, so our post-run filter takes it out of the ranking. The score is unchanged.</p>` : ''}
    ${info.why ? `<p class="why">${research(info.why)}</p>` : ''}
    ${isTuning(s) ? `<p class="tuning-note"><span class="tag-tuning">Tuning site</span> We used this region to check and set up our method, so its high rank is partly built in. The fair test results are the screening regions, such as Al Wahbah and Roter Kamm.</p>` : ''}

    <div class="card-body">
    <div class="card-col card-col-a">
    ${missed ? `<div class="radar-box missed-box">
      <h3>Missed by our method</h3>
      <p>Our search covered this place but found no bowl here. We show it on purpose: a known site that our method misses is an honest example of its limits, and tells us what to fix next.</p>
      ${s.MISSED_REASON && info.breaks ? `<p><b>Pipeline note:</b> ${esc(s.MISSED_REASON)} <span class="ref-ours">our data</span></p>` : ''}
    </div>` : info.validation ? `<div class="radar-box missed-box">
      <h3>Validation test: ${esc(info.validation.result)}</h3>
      <p>${research(info.validation.text)}</p>
      ${sourcesHTML(info.validation.source ? [info.validation.source] : [])}
    </div>` : unscored ? `<div class="radar-box">
      <h3>Not scored yet</h3>
      <p class="nodata">Our pipeline has only searched a few regions so far (${esc(pipelineAreas())}), so this site has no score or fingerprint yet. It stays on the map with our research notes; it gets a score once the pipeline runs on its area.</p>
    </div>` : `<div class="radar-box">
      <h3>Fingerprint · ${esc(groupName)}</h3>
      ${radarSVG(s, axes)}
      <div class="radar-legend">
        <span><span class="swatch" style="border-color:${COLORS.earth}"></span>${esc(nameOf(s))}</span>
        <span><span class="swatch" style="border-color:${COLORS.moon};border-top-style:dashed"></span>${esc(moonName)} = outer ring</span>
      </div>
      ${missingNote.length ? `<p class="nodata">${esc(missingNote.join(' '))} Left out of the score, not counted as zero.</p>` : ''}
    </div>`}

    ${accessHTML(s) || stationHTML(s) ? `<div class="note-box prac-box access-box">
      ${accessHTML(s)}
      ${stationHTML(s)}
      <p class="nodata">A rough guide, not a trip plan: travel time from a model (roads of 2015); airport and station distances in a straight line. A listed station gives no right of use. Not part of the score.</p>
    </div>` : ''}

    ${ground.length || impact || rockHTML(s) ? `<details class="note-box prac-box fold-box">
      <summary><h3>On the ground</h3> <span class="fold-hint">${rockHTML(s) ? 'land cover, rock' : 'land cover'} · not in the score</span></summary>
      ${ground.length ? `<div class="prac">${ground.map(c => `
        <span title="${esc(meta(c.key).earthUnit)}">${esc(c.label)}</span>
        <span class="bar"><span style="width:${Math.round(s[c.key] * 100)}%"></span></span>
        <span class="pct">${Math.round(s[c.key] * 100)}%</span>`).join('')}
      </div>` : ''}
      ${impact ? `<p class="impact-line"><span>Impact crater</span> ${impact}</p>` : ''}
      ${rockHTML(s)}
      <p class="nodata">About the place itself, not compared with the Moon${ground.length ? ' (bars: more is better)' : ''}. Not part of the score.</p>
    </details>` : ''}

    ${practical.length ? `<div class="note-box prac-box">
      <h3>Practical</h3>
      <div class="prac">${practical.map(c => `
        <span title="${esc(c.hint)}">${esc(c.label)}</span>
        <span class="bar"><span style="width:${Math.round(s[c.key] * 100)}%"></span></span>
        <span class="pct">${Math.round(s[c.key] * 100)}</span>`).join('')}
      </div>
      <p class="nodata">Scored apart from similarity: these say how easy the site is to use, not how Moon-like it is.</p>
    </div>` : ''}
    </div>

    <div class="card-col card-col-b">
    ${unscored ? '' : `<div>
      <h3>Closest to the Moon on</h3>
      <div class="chips">${strengths.length ? strengths.map(d => `<span class="chip good" ${chipAttrs(d)}><b>${esc(d.label)}</b> ${esc(vsText(d))}</span>`).join('') : '<span class="chip">Nothing above 50 % yet</span>'}</div>
    </div>

    <div>
      <h3>What it lacks</h3>
      <div class="chips">${gaps.length ? gaps.map(d => `<span class="chip gap" ${chipAttrs(d)}><b>${esc(d.label)}</b> ${d.signed == null ? '' : d.signed < 0 ? 'too little ' : 'too much '}(${esc(vsText(d))})</span>`).join('') : '<span class="chip">No big gaps</span>'}</div>
    </div>

    `}

    <div class="note-box">
      <h3>${missed ? 'Why our method missed it' : 'Where the analogy breaks down'}</h3>
      ${info.breaks ? `<p>${research(info.breaks)}</p>` : missed && s.MISSED_REASON ? `<p>${esc(s.MISSED_REASON[0].toUpperCase() + s.MISSED_REASON.slice(1))}. <span class="ref-ours">our data</span></p>` : auto ? `<ul class="outlook">${auto.breaks.map(t => `<li>${esc(t)} <span class="ref-ours">our data</span></li>`).join('')}<li>${esc(auto.general)}</li></ul>` : '<p><span class="todo">[to research]</span></p>'}
    </div>

    ${info.outlook ? `${isNew || missed ? '' : `<div class="note-box">
      <h3>How it has helped exploration</h3>
      <p>${research(info.helps ?? '[to research]')}</p>
    </div>`}
    <div class="note-box outlook-box">
      <h3>Opportunities &amp; challenges</h3>
      ${outlookHTML(info)}
      ${numberedSourcesHTML(info.sources)}
    </div>` : auto ? `<div class="note-box outlook-box">
      <h3>Opportunities &amp; challenges</h3>
      ${outlookHTML({ outlook: auto.outlook, sources: [] })}
      <p class="nodata">Nobody on our team has researched this place yet: these lines come only from our pipeline’s measurements.</p>
    </div>` : missed && !info.helps ? '' : `<div class="note-box">
      <h3>${missed ? 'What we change next' : isNew ? 'What we could test here' : 'How it has helped exploration'}</h3>
      <p>${info.helps ? research(info.helps) : `<span class="todo">${isNew ? '[to write once ranked: what we could test here]' : '[to research]'}</span>`}</p>
      ${sourcesHTML(info.sources)}
    </div>`}
    </div>
    </div>`;
}

/* ---------- Globe ---------- */

function hasWebGL() {
  try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')); } catch { return false; }
}

// FAKE heatmap: blobs around dry, polar, volcanic and deep-valley regions, only to design the layer.
// Replace with a grid of real suitability scores (lat, lng, weight) from the pipeline.
function fakeHeatPoints() {
  let seed = 7;
  const rand = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const gauss = () => Math.sqrt(-2 * Math.log(rand() + 1e-9)) * Math.cos(2 * Math.PI * rand());
  const blobs = [
    [75.4, -89.7, 1.0, 2.0], [78.5, 16, 0.8, 1.5], [60, 8.5, 0.6, 1.5], [46.2, 8.2, 0.5, 1.0],
    [65, -16, 0.6, 1.5], [28.8, 83.8, 0.9, 1.5], [32, 85, 0.7, 3.0], [-23.8, -69, 0.8, 1.5],
    [-77.6, 162, 1.0, 2.0], [-20, -67.5, 0.6, 1.5], [24, 12, 0.4, 4.0], [35, -111, 0.6, 1.5],
    [43.4, -113.5, 0.6, 1.2], [41.7, -121.5, 0.5, 1.0], [29.1, -13.6, 0.6, 0.6],
  ];
  const pts = [];
  for (const [lat, lng, w, spread] of blobs) {
    for (let i = 0; i < 60; i++) pts.push({ lat: lat + gauss() * spread * 0.6, lng: lng + gauss() * spread, weight: w * (0.4 + 0.6 * rand()) });
  }
  return pts;
}

let resumeTimer = null;
// Hit-area columns catch the mouse but are never drawn. globe.gl hides a fully transparent shape (and then the
// mouse can't find it), so they get a tiny alpha, and before each frame their materials are told to write
// neither colour nor depth: no faint discs, no holes in the heatmap behind them.
const HIT_COLOR = 'rgba(0,0,0,0.01)';
function ghostHitAreas(globe) {
  const scene = globe.scene(), before = scene.onBeforeRender;
  let layer = null;
  scene.onBeforeRender = (...args) => {
    before?.apply(scene, args);
    if (!layer) scene.traverse(o => { if (!layer && o.__globeObjType === 'point') layer = o.parent; });
    layer?.children.forEach(o => {
      const m = o.material;
      if (m && (m.colorWrite || m.depthWrite)) { m.colorWrite = false; m.depthWrite = false; }
    });
  };
}
// Hit-area radius: about HIT_PX on screen at the current zoom, but at most half the way to the nearest other
// marker, so the closest dot always wins; never smaller than the dot itself.
const HIT_PX = 12;
function degPerPx(g) {   // at the centre of the view
  const pv = g.pointOfView(), lat = Math.max(-80, Math.min(80, pv.lat));
  const a = g.getScreenCoords(lat, pv.lng, 0), b = g.getScreenCoords(lat + 1, pv.lng, 0);
  const px = a && b ? Math.hypot(b.x - a.x, b.y - a.y) : 0;
  return px ? 1 / px : null;
}
const arcDeg = (a, b) => {
  const r = Math.PI / 180;
  const c = Math.sin(a.lat * r) * Math.sin(b.lat * r) + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.cos((a.lng - b.lng) * r);
  return Math.acos(Math.min(1, Math.max(-1, c))) / r;
};
function setHitRadii(g, items, dotDeg, maxDeg) {
  const want = Math.min(maxDeg, (degPerPx(g) ?? 0.3) * HIT_PX);
  items.forEach(a => {
    const near = items.reduce((m, b) => (b === a ? m : Math.min(m, arcDeg(a, b))), Infinity);
    a.hitR = Math.max(dotDeg(a), Math.min(want, near / 2));
  });
  return items;
}
// Heatmap colour, t = 0 (few, weak craters) to 1 (many strong ones): see-through violet to pale lilac.
const HEAT_STOPS = [[70, 50, 160], [130, 80, 220], [190, 120, 255], [235, 190, 255]];
function heatColor(t) {
  t = Math.max(0, Math.min(1, t));
  const x = t * (HEAT_STOPS.length - 1), i = Math.min(HEAT_STOPS.length - 2, Math.floor(x)), f = x - i;
  const c = HEAT_STOPS[i].map((v, k) => Math.round(v + (HEAT_STOPS[i + 1][k] - v) * f));
  return `rgba(${c},${(0.8 * Math.sqrt(t)).toFixed(3)})`;
}
// A small circle (radius in degrees) around a site, drawn as a polygon: the pin under the dot.
function pinOf(site, r) {
  const ring = [];
  for (let i = 0; i <= 24; i++) {
    const a = (i / 24) * 2 * Math.PI;
    ring.push([site.lng + (r * Math.sin(a)) / Math.max(0.2, Math.cos((site.lat * Math.PI) / 180)), site.lat + r * Math.cos(a)]);
  }
  return { ...site, selected: site.SITE === state.selected, geometry: { type: 'Polygon', coordinates: [ring] } };
}
// The globe's label font has plain English letters only ("Ovacık" showed as "Ovac?k"): drop accents for the
// globe labels. The list and the cards keep the real spelling.
const PLAIN = { ı: 'i', İ: 'I', ł: 'l', Ł: 'L', ø: 'o', Ø: 'O', ß: 'ss', đ: 'd', Đ: 'D', æ: 'ae', Æ: 'AE', œ: 'oe', Œ: 'OE', 'ʻ': "'", 'ʼ': "'", '’': "'", '‘': "'", '–': '-', '—': '-' };
const plainText = t => String(t ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^\x00-\x7F]/g, ch => PLAIN[ch] ?? '');

function initGlobe() {
  const el = document.getElementById('globe');
  if (!hasWebGL() || typeof Globe !== 'function') { document.getElementById('globeError').hidden = false; return; }
  // Pipeline: one point per ranked crater, weight = SCORE_TOTAL. Sample: a fake pattern, for design only.
  const heat = DATA.isFake ? fakeHeatPoints() : baseHeat();
  heatPoints = heat;
  setHeatNote();
  // Legend line only for the dashed Mare boxes (shown while a base without results is picked).
  document.getElementById('regionNote').innerHTML = `<i style="border-color:${COLORS.moon};border-top-style:dashed"></i>searched tonight (Mare)`;

  const g = Globe()(el)
    // NASA Blue Marble Next Generation, July 2004, topography + bathymetry (NASA Earth Observatory),
    // resized from 5400x2700 to 4096x2048. Relief shading is already in the image.
    .globeImageUrl('assets/blue-marble-2004-07-4096.jpg')
    .backgroundColor('#030A12')
    .atmosphereColor('#6CB4EE')
    .atmosphereAltitude(0.15)
    .heatmapsData([{ points: heat }])
    .heatmapPoints(d => d.points)
    .heatmapPointLat('lat')
    .heatmapPointLng('lng')
    .heatmapPointWeight('weight')
    .heatmapBandwidth(DATA.isFake ? 2.4 : 0.9)   // real data: one point per crater, so smaller blobs
    .heatmapColorSaturation(2.2)
    // A soft violet haze, flat on the ground: it shows where good craters cluster without looking like buttons.
    .heatmapColorFn(() => heatColor)
    .heatmapBaseAltitude(0.005 * labelScale)
    .heatmapTopAltitude(0.005 * labelScale)
    .labelLat('lat')
    .labelLng('lng')
    .labelText(d => plainText(labelTextOf(d)))
    .labelSize(d => (d.SITE === state.selected ? 1.6 : 1.0) * labelScale)
    .labelDotRadius(d => (d.SITE === state.selected ? 0.7 : d.sim == null ? 0.3 : 0.45) * labelScale)
    // Scored sites stand out; known analogs not scored yet are faint grey dots without a name.
    .labelColor(d => (d.SITE === state.selected ? '#FFFFFF' : d.missed ? REGION_COLORS.none : d.sim == null ? 'rgba(167,186,199,0.55)'
      : (typeOf(d) === 'known' ? COLORS.known : COLORS.newSite)))
    .labelAltitude(() => 0.07 * labelScale)
    .labelResolution(2)
    .onLabelClick(d => select(d.SITE, true))
    // Invisible hit areas: a wider column under each label, so a dot is easy to hover and click (team comment).
    .pointLat('lat')
    .pointLng('lng')
    // Just under the labels, so a click right on a name still hits the label; ~4× the dot's radius around it.
    .pointAltitude(() => 0.065 * labelScale)
    .pointRadius('hitR')
    .pointColor(() => HIT_COLOR)
    .pointResolution(10)
    .pointsMerge(false)
    .pointsTransitionDuration(0)
    .pointLabel(d => `${esc(nameOf(d))}${d.sim == null ? '' : ` · ${scoreText(d.sim, d)} like the Moon`}`)
    .onPointClick(d => { el.style.cursor = ''; select(d.SITE, true); })
    .onPointHover(d => { el.style.cursor = d ? 'pointer' : ''; })
    // Pins: a dark disc with a white rim under every dot you can click, so sites stand apart from the haze.
    .polygonGeoJsonGeometry('geometry')
    .polygonAltitude(() => 0.068 * labelScale)
    .polygonCapColor(d => (d.selected ? 'rgba(3,10,18,0.75)' : 'rgba(3,10,18,0.6)'))
    .polygonSideColor(() => 'rgba(0,0,0,0)')
    .polygonStrokeColor(d => (d.selected ? '#FFFFFF' : 'rgba(255,255,255,0.85)'))
    .polygonsTransitionDuration(0)
    .polygonLabel(d => `${esc(nameOf(d))}${d.sim == null ? '' : ` · ${scoreText(d.sim, d)} like the Moon`}`)
    .onPolygonClick(d => { el.style.cursor = ''; select(d.SITE, true); })
    .onPolygonHover(d => { el.style.cursor = d ? 'pointer' : ''; })
    // Outlines of every region the pipeline searched (from cells.json); dashed Moon-cream: searched next (Mare).
    .pathPoints('points')
    .pathPointLat(p => p[0])
    .pathPointLng(p => p[1])
    .pathColor(r => (r.planned ? COLORS.moon : r.ranked ? REGION_COLORS.found : REGION_COLORS.none))   // strong colours: they must show on ice too
    .pathStroke(4)
    .pathDashLength(r => (r.planned ? 0.06 : 1))
    .pathDashGap(r => (r.planned ? 0.03 : 0))
    .pathDashAnimateTime(r => (r.planned ? 4000 : 0))
    .pathTransitionDuration(0)
    .pathLabel(r => (r.planned ? `${esc(r.label)} (${esc(r.country)}): searched tonight for Mare twins`
      : `${esc(r.label)}: ${r.ranked ? `${r.ranked} crater${r.ranked > 1 ? 's' : ''} scored` : 'searched, no crater found'}`))
    .ringColor(r => t => (r.planned ? `rgba(232,227,211,${1 - t})` : r.twin ? `rgba(60,200,180,${1 - t})` : `rgba(255,255,255,${1 - t})`))
    .ringMaxRadius(r => (r.planned ? 7 : 4) * labelScale)
    .ringPropagationSpeed(2)
    .ringRepeatPeriod(1200)
    .ringAltitude(() => 0.07 * labelScale);

  // Always rotating; pauses briefly while someone drags or after flying to a site.
  const controls = g.controls();
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.35;
  controls.addEventListener('start', () => pauseRotation(0));
  controls.addEventListener('end', () => pauseRotation(4000));
  controls.addEventListener('change', onGlobeZoom);
  g.pointOfView({ lat: 35, lng: 10, altitude: innerWidth > 1180 ? 2.0 : 2.3 });   // wide screens: the Earth is the stage
  ghostHitAreas(g);
  state.globe = g;
  setEarthPaths();

  const fit = () => g.width(el.clientWidth).height(el.clientHeight);
  new ResizeObserver(fit).observe(el);
  fit();
}

// Globe labels are sized in degrees on the globe, so zoomed in they grow huge and nearby craters
// (El Elegante and Pinacate NW are 25 km apart) pile up. Scale them with the camera height, and
// where labels would still overlap show only the best-ranked one, with "+1" for the hidden ones.
let labelScale = 1, labelHidden = new Map(), heatPoints = [], heatShown = true;
// Heatmap points of the selected base only (night export: each point has "base").
const baseHeat = () => (state.heat ?? []).filter(p => p.base == null || p.base === state.base);
// With hundreds of places the globe would be covered in names: only the best LABEL_LIMIT (of the places that
// pass the filters), known sites and the selected one get a name and dot; the heatmap shows the rest.
const LABEL_LIMIT = 30;
const HEAT_MIN_SCALE = 0.25;   // closer than this the blobs only cover the ground, so the heatmap hides
function setHeatNote() {
  document.getElementById('heatNote').textContent = !heatShown ? 'Zoom out to see the heatmap'
    : DATA.isFake ? 'Fake pattern, for design only'
    : heatPoints.length ? `${heatPoints.length.toLocaleString('en')} ${state.base === 'mare' ? 'places' : 'craters'} scored so far${heatPoints.length > LABEL_LIMIT ? ` · best ${LABEL_LIMIT} named` : ''}` : 'No heatmap data yet';
}   // SITE → '' (hidden) or ' +n' (leader of a group)
const labelTextOf = d => (d.sim == null && d.SITE !== state.selected ? '' : labelHidden.has(d.SITE) ? (labelHidden.get(d.SITE) === '' ? '' : nameOf(d) + labelHidden.get(d.SITE)) : nameOf(d));

function declutterLabels(sites) {
  labelHidden = new Map();
  const order = sites.filter(s => s.sim != null || s.SITE === state.selected)   // unnamed dots don't count
    .sort((a, b) => (b.SITE === state.selected) - (a.SITE === state.selected) || (a.rank ?? 1e9) - (b.rank ?? 1e9));
  const kept = [];
  const minGap = 3 * labelScale;     // degrees; about three label heights
  for (const s of order) {
    const near = kept.find(k => {
      const dLat = k.lat - s.lat, dLng = (k.lng - s.lng) * Math.cos(s.lat * Math.PI / 180);
      return Math.hypot(dLat, dLng) < minGap;
    });
    if (!near) { kept.push(s); continue; }
    labelHidden.set(s.SITE, '');
    near.extra = (near.extra ?? 0) + 1;
  }
  kept.forEach(k => { if (k.extra) labelHidden.set(k.SITE, ` +${k.extra}`); delete k.extra; });
}

function onGlobeZoom() {
  const g = state.globe; if (!g) return;
  // Shrinks a bit slower than the camera height, so zoomed-in labels stay readable.
  const scale = Math.min(1.2, Math.max(0.03, (g.pointOfView().altitude / 2.3) ** 0.75));
  if (Math.abs(scale - labelScale) / labelScale < 0.15) return;   // redraw only on a real zoom change
  labelScale = scale;
  // Heatmap and labels float above the globe; zoomed in, bring them down so they sit on the ground.
  g.heatmapBaseAltitude(0.005 * scale).heatmapTopAltitude(0.005 * scale);
  if (heatShown !== scale >= HEAT_MIN_SCALE) {
    heatShown = scale >= HEAT_MIN_SCALE;
    g.heatmapsData(heatShown ? [{ points: heatPoints }] : []);
    setHeatNote();
  }
  updateGlobe(false);
}

const boxPath = (r, extra) => { const [w, so, e, n] = r.bbox; return { ...r, ...extra, points: [[so, w], [so, e], [n, e], [n, w], [so, w]] }; };
function setEarthPaths() {
  const g = state.globe; if (!g) return;
  const planned = state.moonInfo && !state.targets[state.moonInfo];
  // The searched-region outlines were removed (too busy); only the planned Mare boxes are drawn.
  g.pathsData(planned ? PLANNED_REGIONS.map(r => boxPath(r, { planned: true })) : []);
  document.getElementById('regionNote').hidden = !planned;
}
// Turn the Earth to the regions searched next (Mare), or to one of them.
function showPlanned(run) {
  const g = state.globe; if (!g) return;
  if (state.view === 'terrain') closeTerrain();
  pauseRotation(9000);
  const r = PLANNED_REGIONS.find(x => x.run === run);
  g.pointOfView(r ? { lat: (r.bbox[1] + r.bbox[3]) / 2, lng: (r.bbox[0] + r.bbox[2]) / 2, altitude: 0.9 } : { lat: 2, lng: 0, altitude: 2.6 }, 1500);
  setTimeout(onGlobeZoom, 1600);
}

// Fly the globe to a searched region (leaving the 3D view if it is open).
function showRegion(run) {
  const r = searchedRegions().find(x => x.run === run); const g = state.globe;
  if (!r || !g) return;
  if (state.view === 'terrain') closeTerrain();
  pauseRotation(8000);
  g.pointOfView({ lat: r.lat, lng: r.lng, altitude: 0.25 }, 1500);
  setTimeout(onGlobeZoom, 1600);
}

function pauseRotation(ms) {
  const g = state.globe; if (!g) return;
  g.controls().autoRotate = false;
  clearTimeout(resumeTimer);
  if (ms > 0) resumeTimer = setTimeout(() => { g.controls().autoRotate = true; }, ms);
}

function updateGlobe(fly) {
  const g = state.globe;
  if (!g) return;
  const shown = visibleSites().filter(x => !x.EXCLUDED || x.SITE === state.selected);   // excluded: only when picked
  const s = shown.find(x => x.SITE === state.selected);
  const named = new Set(shown.filter(x => x.sim != null).slice(0, LABEL_LIMIT).map(x => x.SITE));
  const onGlobe = shown.filter(x => x.sim == null || named.has(x.SITE) || typeOf(x) === 'known' || x.SITE === state.selected
    || state.twinFlash?.includes(x.SITE));
  declutterLabels(onGlobe);
  g.labelsData(onGlobe.map(x => ({ ...x })));   // new objects so globe.gl redraws sizes and texts
  g.pointsData(setHitRadii(g, onGlobe.map(x => ({ ...x })), d => (d.SITE === state.selected ? 0.7 : 0.45) * labelScale, 4));   // invisible hit areas
  g.polygonsData(onGlobe.map(x => pinOf(x, (x.SITE === state.selected ? 0.7 : x.sim == null ? 0.3 : 0.45) * labelScale * 1.9)));
  g.ringsData([...(s ? [{ lat: s.lat, lng: s.lng }] : []),
    ...shown.filter(x => state.twinFlash?.includes(x.SITE) && x.SITE !== state.selected).map(x => ({ lat: x.lat, lng: x.lng, twin: true })),
    ...(state.moonInfo && !state.targets[state.moonInfo] ? PLANNED_REGIONS.map(r => ({ lat: (r.bbox[1] + r.bbox[3]) / 2, lng: (r.bbox[0] + r.bbox[2]) / 2, planned: true })) : [])]);
  if (s && fly) {
    pauseRotation(6000);
    g.pointOfView({ lat: s.lat, lng: s.lng, altitude: 1.4 }, 1200);
    setTimeout(onGlobeZoom, 1300);   // a programmed move doesn't fire the controls' 'change'
  }
}

/* ---------- Moon globe: pick the lunar base the Earth sites are compared with ---------- */

// Several lunar targets per base (docs/MULTI_TARGET.md): targets[base].lunar_targets holds each verified target's
// values; scores.csv has SCORE_<TARGET>, BEST_TARGET, BEST_SCORE. Positions come from the candidates file:
// Polar = the crater's low point (the bowl the values describe), Mare = centre of the target's sample areas.
const lng180 = l => (l > 180 ? l - 360 : l);
function targetPositions(cand) {
  const pos = {};
  for (const t of cand?.targets ?? []) {
    const p = t.place?.low_point_lat_lon ?? t.region_centre_lat_lon, cells = t.cells_lat_lon;
    if (Array.isArray(p)) {
      pos[t.name] = { lat: p[0], lng: lng180(p[1]), where: t.place?.low_point_lat_lon ? 'marker on the crater floor' : 'marker at the region centre', preview: t.preview };
    } else if (Array.isArray(cells) && cells.length) {
      const n = cells.length;
      pos[t.name] = { lat: cells.reduce((a, c) => a + c[0], 0) / n, lng: lng180(cells.reduce((a, c) => a + c[1], 0) / n),
        where: `marker at the centre of its ${n} sample areas`, n, preview: t.preview };
    }
  }
  return pos;
}
// "Polar · small crater on the de Gerlache rim (Artemis III region, …)" → "small crater on the de Gerlache rim"
const shortTargetLabel = t => String(t.label ?? t.name).replace(/^(Polar|Mare)\s*·\s*/, '').split(' (')[0];
// Verified targets of a base, today's (built-in) target first. Empty when the export has only one target.
function lunarTargets(baseId) {
  const b = moonBase(baseId), list = state.targets[baseId]?.lunar_targets;
  if (!b || !Array.isArray(list)) return [];
  return list.filter(t => t.verified === true).map(t => {
    const pos = t.builtin ? { lat: b.lat, lng: b.lng } : (state.targetPos?.[t.name] ?? {});
    return { base: baseId, name: t.name, column: t.column, builtin: !!t.builtin, criteria: t.criteria ?? {},
      label: t.builtin ? (b.targetName ?? b.name) : shortTargetLabel(t), lat: pos.lat ?? null, lng: pos.lng ?? null,
      where: pos.where ?? null, n: pos.n ?? null, preview: pos.preview ?? null };
  }).sort((a, z) => z.builtin - a.builtin);
}
const moonTargetOf = baseId => {
  const ts = lunarTargets(baseId);
  return ts.find(t => t.name === state.moonTarget) ?? ts.find(t => t.builtin) ?? null;
};
// Pick one lunar target (marker or button): its values show in the Moon panel. Ranking stays on SCORE_TOTAL.
function pickTarget(baseId, name) {
  if (baseId !== state.moonInfo) setBase(baseId, true);
  state.moonTarget = name;
  updateMoon(true);   // Mare: turn to that mare; Polar: stay at 78°S, turn to the target's longitude so its name reads upright
}
// Earth card, Polar only: the target with the highest score (Mare tolerances differ per target, so not comparable).
function closestTwin(s) {
  if (state.base !== 'polar' || (s.BASE_TYPE ?? 'polar') !== 'polar' || s.BEST_TARGET == null || s.BEST_SCORE == null) return null;
  const t = lunarTargets('polar').find(x => x.name === s.BEST_TARGET);
  return { label: t?.label ?? s.BEST_TARGET, score: s.BEST_SCORE };
}

const moonReady = id => !!state.targets[id];
function initMoon() {
  const el = document.getElementById('moonGlobe');
  if (!hasWebGL() || typeof Globe !== 'function') return;
  const m = Globe()(el)
    // NASA SVS CGI Moon Kit colour map (LRO camera, LROC WAC mosaic by ASU), 4096x2048, converted to JPEG.
    .globeImageUrl('assets/lroc-moon-color-4096.jpg')
    .backgroundColor('#030A12')
    .showAtmosphere(false)
    .labelLat('lat')
    .labelLng('lng')
    // Several targets of one base: only the picked one has its name written (the others on hover). The polar
    // targets lie within 3.5° of the pole, so their dots and text are smaller.
    .labelText(b => (b.target && !b.sel ? '' : plainText(b.name)))
    .labelSize(b => (b.crowded ? 2.2 : b.target ? 3 : b.sel ? 4.2 : 3.4))
    .labelDotRadius(b => (b.crowded ? (b.sel ? 0.9 : 0.7) : b.sel ? 1.6 : 1.2))
    .labelColor(b => (b.sel ? '#FFFFFF' : moonReady(b.id) ? COLORS.signal : 'rgba(167,186,199,0.75)'))
    .labelAltitude(0.01)
    .labelResolution(3)
    .labelLabel(b => `${esc(b.title)} · ${esc(b.name)}${moonReady(b.id) ? '' : ' (Earth twins coming)'}`)
    .onLabelClick(b => (b.target ? pickTarget(b.id, b.target) : setBase(b.id, true)))
    // Invisible hit areas, wider than the dots (team comment); same hover text and click as the labels.
    .pointLat('lat')
    .pointLng('lng')
    .pointAltitude(0.012)
    .pointRadius('hitR')
    .pointColor(() => HIT_COLOR)
    .pointResolution(12)
    .pointsMerge(false)
    .pointsTransitionDuration(0)
    .pointLabel(b => `${esc(b.title)} · ${esc(b.name)}${moonReady(b.id) ? '' : ' (Earth twins coming)'}`)
    .onPointClick(b => (b.target ? pickTarget(b.id, b.target) : setBase(b.id, true)))
    .onPointHover(b => { el.style.cursor = b ? 'pointer' : ''; })
    .ringColor(() => t => `rgba(255,255,255,${1 - t})`)
    .ringMaxRadius(d => d.r ?? 6)
    .ringPropagationSpeed(3)
    .ringRepeatPeriod(1400);
  const c = m.controls();
  c.autoRotate = true;
  c.autoRotateSpeed = 0.5;
  c.addEventListener('start', () => { c.autoRotate = false; clearTimeout(moonResume); });
  c.addEventListener('end', () => { clearTimeout(moonResume); moonResume = setTimeout(() => { c.autoRotate = true; }, 4000); });
  const fit = () => m.width(el.clientWidth).height(el.clientHeight);
  new ResizeObserver(fit).observe(el);
  fit();
  ghostHitAreas(m);
  state.moon = m;
  document.getElementById('moonBases').addEventListener('click', e => {
    const b = e.target.closest('[data-moon]'); if (b) setBase(b.dataset.moon, true);
  });
  document.getElementById('moonInfo').addEventListener('click', e => {
    const t = e.target.closest('[data-twin]'); if (t) return select(t.dataset.twin, true);
    const lt = e.target.closest('[data-target]'); if (lt) return pickTarget(state.moonInfo, lt.dataset.target);
    const r = e.target.closest('[data-planned]'); if (r) showPlanned(r.dataset.planned);
  });
  updateMoon(true);
}
let moonResume = null;
const baseLabelOf = id => BASES.find(b => b.id === id)?.label ?? id;

// Markers, ring and camera. The open base shows one marker per lunar target, the other base one marker.
// Polar: the camera looks from 78°S (at the picked target's longitude), so the pole sits near the middle and stays
// in view while the Moon turns.
function updateMoon(fly) {
  const m = state.moon;
  const b = moonBase(state.moonInfo);
  const sel = b ? moonTargetOf(b.id) : null;
  renderMoonButtons();
  if (!m) return;
  const markers = MOON_BASES.flatMap(x => {
    const ts = x.id === state.moonInfo ? lunarTargets(x.id).filter(t => t.lat != null) : [];
    if (!ts.length) return [{ ...x, sel: x.id === state.moonInfo }];
    return ts.map(t => ({ ...x, name: t.label, target: t.name, lat: t.lat, lng: t.lng, sel: t.name === sel?.name, crowded: x.id === 'polar' }));
  });
  m.labelsData(markers);
  m.pointsData(setHitRadii(m, markers.map(x => ({ ...x })), b => (b.crowded ? (b.sel ? 0.9 : 0.7) : b.sel ? 1.6 : 1.2), 6));
  const at = markers.find(x => x.sel);
  m.ringsData(at ? [{ lat: at.lat, lng: at.lng, r: at.crowded ? 3 : 6 }] : []);
  if (b && fly) {
    m.controls().autoRotate = false;
    clearTimeout(moonResume);
    moonResume = setTimeout(() => { m.controls().autoRotate = true; }, 5000);
    const p = at ?? b;
    m.pointOfView(b.id === 'polar' ? { lat: -78, lng: p.lng, altitude: 1.25 }
      : { lat: Math.max(-70, Math.min(70, p.lat)), lng: p.lng, altitude: 1.25 }, 1200);
  }
}

function renderMoonButtons() {
  document.getElementById('moonBases').innerHTML = MOON_BASES.map(b => `<button type="button" class="moon-btn" data-moon="${b.id}"
      aria-pressed="${b.id === state.moonInfo}"${moonReady(b.id) ? '' : ' data-soon'}>
      <b>${esc(baseLabelOf(b.id))}</b> ${esc(b.name)}${moonReady(b.id) ? '' : ' <span class="soon">Earth twins coming</span>'}</button>`).join('');
  renderMoonInfo();
}

// The lunar target in a few lines: why it is a base site, its counted values, and the facts no Earth place can match.
function renderMoonInfo() {
  const el = document.getElementById('moonInfo');
  const b = moonBase(state.moonInfo);
  if (!b) { el.innerHTML = '<p class="hint">Click a base on the Moon to find its Earth twins.</p>'; return; }
  const crit = state.crit[b.id];
  const row = (label, value, note, fact) => `<li class="${fact ? 'is-fact' : note ? 'has-note' : ''}"><span>${esc(label)}</span><b>${esc(value)}</b>${note ? `<em>${esc(note)}</em>` : ''}</li>`;
  const targets = lunarTargets(b.id), sel = moonTargetOf(b.id);
  const picker = targets.length > 1 ? `<p class="moon-sub">Lunar targets (${targets.length}): Earth places are scored against each</p>
    <div class="moon-twins moon-targets">${targets.map(t => `<button type="button" class="moon-twin" data-target="${esc(t.name)}" aria-pressed="${t.name === sel?.name}"><span>${esc(t.label)}</span>${t.builtin ? '<i>ranking uses this one</i>' : ''}</button>`).join('')}</div>` : '';
  if (sel && !sel.builtin) { el.innerHTML = picker + moonTargetHTML(b, sel, crit, row); return; }
  const val = c => fmtVal(crit[c.key].moon, crit[c.key].earthUnit || crit[c.key].unit);
  // Target values: from outputs/targets.json once the pipeline exports this base, else the team's values above.
  const rows = crit ? CRITERIA.filter(c => crit[c.key]?.counts && crit[c.key].moon != null && !crit[c.key].kind).map(c => row(c.label, val(c))).join('')
    : (b.target ?? []).map(t => row(t.label, t.value, t.note)).join('');
  const shownFacts = new Set();
  const facts = [
    ...(crit ? CRITERIA.filter(c => crit[c.key]?.fact && crit[c.key].moon != null).map(c => (shownFacts.add(c.label), row(c.label, val(c), 'no Earth analog possible', true))) : []),
    ...(b.facts ?? []).filter(f => !shownFacts.has(f.label)).map(f => row(f.label, f.value, `${f.note}. No Earth analog possible.`, true)),
  ].join('');
  el.innerHTML = picker + `
    <p class="moon-title"><b>${esc(b.title)}</b> · ${esc(b.name)} (${esc(b.place)}), ${esc(fmtLatLng(b.lat, b.lng))}</p>
    ${b.subtitle ? `<p class="moon-facts">${esc(b.subtitle)}</p>` : ''}
    <p class="moon-why">${esc(b.why)}</p>
    ${rows || facts ? `<details class="moon-fold"><summary>${crit ? `Show ${esc(b.name)}’s values` : 'What a lunar mare base site looks like'}</summary>${crit ? '<p class="moon-fold-hint">What Earth sites are compared with</p>' : ''}<ul class="moon-vals">${rows}${facts}</ul></details>` : ''}
    ${b.detail ? `<p class="moon-detail">${esc(b.detail)}</p>` : ''}
    ${crit && b.id === state.base ? `<p class="moon-sub">Closest Earth twins</p><div class="moon-twins">${twinsOf().map(t => `<button type="button" class="moon-twin" data-twin="${esc(t.SITE)}"><span class="rank ${t.type === 'known' ? 'known' : 'new'}">${t.rank}</span><span>${esc(nameOf(t))}</span><b>${scoreText(t.sim, t)}</b>${isTuning(t) ? '<i>tuning</i>' : t.SITE === bestTwin(twinsOf())?.SITE ? '<i class="best">best independent</i>' : ''}</button>`).join('')}</div>` : ''}
    ${crit ? '' : `<p class="moon-soon">Earth twins for this base come with tonight’s pipeline run. Where we search:</p><div class="moon-twins">${PLANNED_REGIONS.map(r => `<button type="button" class="moon-twin" data-planned="${r.run}"><span>${esc(r.label)}</span><i>${esc(r.country)}</i></button>`).join('')}</div>`}
    <a class="moon-fig" href="${esc(b.figure)}" target="_blank" rel="noopener" hidden>${esc(b.figureLabel ?? 'See the target figure')}</a>`;
  // Show the figure link only if the figure is in the repo (the mare map arrives with Mateo's branch).
  const link = el.querySelector('.moon-fig');
  if (b.figure) fetch(b.figure, { method: 'HEAD' }).then(r => { if (r.ok && state.moonInfo === b.id) link.hidden = false; }).catch(() => {});
}

// One extra lunar target (not today's): same values table, from targets.json → lunar_targets[].criteria
// (keyed by criterion id, mapped to the scores.csv column through targets[base].criteria).
function moonTargetHTML(b, t, crit, row) {
  const colOf = Object.fromEntries((state.targets[b.id]?.criteria ?? []).map(c => [c.column, c.criterion]));
  const rows = crit ? CRITERIA.filter(c => crit[c.key]?.counts && !crit[c.key].kind && t.criteria[colOf[c.key]]?.value != null)
    .map(c => row(c.label, fmtVal(t.criteria[colOf[c.key]].value, crit[c.key].earthUnit || crit[c.key].unit))).join('') : '';
  const why = b.id === 'polar'
    ? 'A small crater inside an Artemis III candidate landing region (NASA lists of 2022 and 2024), found by our bowl detector with the same code as on Earth. It is not the feature the region was picked for (sunlit ridges and peaks).'
    : `${t.n ?? 'Some'} of the 20 mare sample areas, the ones in this mare (SLDEM2015, same cells as the 20-cell median). With so few areas the spread, and so the tolerance, is a rough estimate.`;
  const twins = b.id === state.base && t.column ? visibleSites().filter(x => x.sim != null && x[t.column] != null)
    .sort((x, z) => z[t.column] - x[t.column]).slice(0, 3) : [];
  const where = t.lat != null ? `, ${fmtLatLng(+t.lat.toFixed(2), +t.lng.toFixed(2))}${t.where ? ` (${t.where})` : ''}` : '';
  const html = `
    <p class="moon-title"><b>${esc(b.title)}</b> · ${esc(t.label)}${esc(where)}</p>
    <p class="moon-why">${esc(why)}</p>
    ${rows ? `<details class="moon-fold"><summary>Show ${esc(t.label)}’s values</summary><p class="moon-fold-hint">What Earth sites are compared with</p><ul class="moon-vals">${rows}</ul></details>` : ''}
    ${twins.length ? `<p class="moon-sub">Closest Earth twins to this target</p><div class="moon-twins">${twins.map((x, i) => `<button type="button" class="moon-twin" data-twin="${esc(x.SITE)}"><span class="rank ${x.type === 'known' ? 'known' : 'new'}">${i + 1}</span><span>${esc(nameOf(x))}</span><b>${scoreText(x[t.column], x)}</b></button>`).join('')}</div>
      <p class="nodata">The ranking and the main score use ${esc(lunarTargets(b.id).find(x => x.builtin)?.label ?? 'today’s target')}.</p>` : ''}
    ${t.preview ? `<a class="moon-fig" href="../${esc(t.preview)}" target="_blank" rel="noopener" hidden>See the target preview figure</a>` : ''}`;
  if (t.preview) setTimeout(() => {
    const link = document.querySelector('#moonInfo .moon-fig');
    fetch(`../${t.preview}`, { method: 'HEAD' }).then(r => { if (r.ok && link && state.moonTarget === t.name) link.hidden = false; }).catch(() => {});
  });
  return html;
}

/* ---------- 3D terrain: MapLibre GL with free tiles (no account, no key) ---------- */

const TERRAIN = {
  // Elevation: Terrain Tiles on AWS Open Data (Mapzen; SRTM, GMTED, ETOPO1 and others), Terrarium encoding.
  dem: 'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png',
  // Imagery: Sentinel-2 cloudless 2016 by EOX (modified Copernicus Sentinel data), about 10 m per pixel.
  // The 2016 layer is CC BY 4.0; the 2018–2025 layers are CC BY-NC-SA 4.0 (non-commercial), which does not fit
  // the challenge rule that third-party materials be free without restriction or open source.
  img: 'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/{z}/{y}/{x}.jpg',
  exaggeration: 1.5,   // heights x1.5 so relief reads on screen; said in the caption
  defaultZoom: 12,     // a site can set its own "zoom" in site_info.json
};
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
let terrainMap = null, terrainReady = false, orbitFrame = null, flyInTimer = null;
let flightTarget = null;                 // the fly-in in progress, so the orbit starts only if it arrives
const TILT = { pitch: 68, bearing: -25 }; // the tilted 3D view; the 2D/3D button returns to it

const currentSite = () => visibleSites().find(s => s.SITE === state.selected);

// (The searched-cell outlines in the 3D view were removed: they added noise without a clear purpose.)
function terrainStyle() {
  const dem = { type: 'raster-dem', tiles: [TERRAIN.dem], tileSize: 256, maxzoom: 15, encoding: 'terrarium' };
  return {
    version: 8,
    sources: {
      img: { type: 'raster', tiles: [TERRAIN.img], tileSize: 256, maxzoom: 15,
        attribution: 'Imagery: <a href="https://s2maps.eu" target="_blank" rel="noopener">Sentinel-2 cloudless</a> by EOX IT Services GmbH (contains modified Copernicus Sentinel data 2016), <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener">CC BY 4.0</a>' },
      dem: { ...dem, attribution: 'Elevation: <a href="https://registry.opendata.aws/terrain-tiles/" target="_blank" rel="noopener">Terrain Tiles on AWS</a> (Mapzen)' },
      shade: dem,
    },
    layers: [
      { id: 'space', type: 'background', paint: { 'background-color': '#030A12' } },
      { id: 'img', type: 'raster', source: 'img', paint: moonPaint() },
      { id: 'shade', type: 'hillshade', source: 'shade', paint: { 'hillshade-exaggeration': 0.3, 'hillshade-shadow-color': '#000000' } },
    ],
    terrain: { source: 'dem', exaggeration: TERRAIN.exaggeration },
  };
}

function stopOrbit() { cancelAnimationFrame(orbitFrame); orbitFrame = null; }
function startOrbit() {
  stopOrbit();
  if (reducedMotion || state.view !== 'terrain' || !terrainReady) return;
  const step = () => {
    if (state.view !== 'terrain') return stopOrbit();
    terrainMap.setBearing(terrainMap.getBearing() + 0.04);
    orbitFrame = requestAnimationFrame(step);
  };
  orbitFrame = requestAnimationFrame(step);
}

// The camera only moves once the map has loaded and while it is on screen. A flight before
// 'load' stalls the map, and a move inside a hidden box turns MapLibre's camera into NaN (black map).
function flyTerrainTo(s) {
  if (!terrainMap || !terrainReady || !s || state.view !== 'terrain') return;
  stopOrbit();
  drawBowlLayer(s);
  if (state.showBase) { drawBaseLayer(s); flyToBase(s); return syncViewUI(); }
  // Polar: the low point, zoomed so the bowl ring fills about half the view. Mare: the base spot, a ~5 km view.
  const bowl = bowlOf(s);
  const center = bowl?.floor ?? bowl?.base ?? [s.lng, s.lat];
  const zoom = bowlZoom(bowl, center[1]) ?? state.info[s.SITE]?.zoom ?? TERRAIN.defaultZoom;
  flightTarget = null;   // flyTo first stops any old move, which fires a 'moveend' that must not orbit
  settling = false;
  // A bowl is seen from a bit higher (less tilt), so the ridges in front hide less of its ring.
  const pitch = bowl?.diameter ? BOWL_PITCH : TILT.pitch;
  terrainMap.flyTo({ center, zoom, ...TILT, pitch, duration: reducedMotion ? 0 : 4500, essential: true });
  flightTarget = s.SITE;
  flightGoal = { zoom, pitch };
  syncViewUI();
}

function onMoveEnd() {
  // A fly-in keeps the ground height of where it started (e.g. Meteor Crater, 1.7 km up), so it aims at
  // a point in the air above a lower site and the crater ends up at the bottom edge. Once there (the
  // elevation tiles are loaded by then), switch to the real ground height and glide to the centre.
  if (flightTarget && !settling && landedOff()) return settleOnGround();
  settling = false;
  // Orbit only when a fly-in finished untouched: a drag, scroll or new flight clears flightTarget first.
  // (Don't compare zoom: with terrain, MapLibre adjusts it for the ground height, e.g. 14 → 13.5.)
  if (flightTarget) startOrbit();
  flightTarget = null;
  syncTiltButton();
}

let settling = false, flightGoal = null;
// After a fly-in: is the camera's ground height off, or did MapLibre change tilt or zoom to stay above ground?
function landedOff() {
  try {
    const tr = terrainMap.transform, ground = terrainMap.terrain?.getElevationForLngLatZoom(tr.center, tr.tileZoom);
    if (!Number.isFinite(ground) || !flightGoal) return false;
    return Math.abs(ground - tr.elevation) > 50 || Math.abs(tr.pitch - flightGoal.pitch) > 1 || Math.abs(tr.zoom - flightGoal.zoom) > 0.05;
  } catch { return false; }
}
function settleOnGround() {
  // Glide camera height, tilt and zoom to where the fly-in meant to land; the centre stays on the site.
  const tr = terrainMap.transform, keep = flightTarget;
  const from = { e: tr.elevation, z: tr.zoom, p: tr.pitch };
  const to = { e: terrainMap.terrain.getElevationForLngLatZoom(tr.center, tr.tileZoom), z: flightGoal.zoom, p: flightGoal.pitch };
  const t0 = performance.now(), dur = reducedMotion ? 0 : 1200;
  settling = true;
  const step = now => {
    if (flightTarget !== keep || state.view !== 'terrain') { settling = false; return; }  // viewer took over
    const k = dur ? Math.min(1, (now - t0) / dur) : 1, f = k * k * (3 - 2 * k), mix = key => from[key] + (to[key] - from[key]) * f;
    tr.elevation = mix('e'); tr.zoom = mix('z'); tr.pitch = mix('p');
    terrainMap.triggerRepaint();
    // Last frame: a real (no-op) jump so MapLibre redraws everything and fires 'moveend', which starts the orbit.
    if (k < 1) requestAnimationFrame(step); else terrainMap.jumpTo({ zoom: to.z, pitch: to.p });
  };
  requestAnimationFrame(step);
}

function viewerTookOver() { flightTarget = null; stopOrbit(); }

function cameraBroken() {
  try {
    const c = terrainMap.getCenter();
    return ![c.lng, c.lat, terrainMap.getZoom(), terrainMap.getPitch()].every(Number.isFinite);
  } catch { return true; }
}

// 2D/3D toggle next to + and −: look straight down, then tilt back to the 3D view.
const isTilted = () => terrainMap.getPitch() > 5;
function toggleTilt() {
  if (!terrainReady) return;
  viewerTookOver();
  terrainMap.easeTo(isTilted() ? { pitch: 0, bearing: 0, duration: 900 } : { ...TILT, duration: 900 });
}
function syncTiltButton() {
  const b = document.querySelector('#terrain .tilt-btn');
  if (!b || !terrainMap) return;
  const tilted = isTilted();
  b.textContent = tilted ? '2D' : '3D';
  b.title = tilted ? 'Look straight down (2D)' : 'Tilt back to the 3D view';
  b.setAttribute('aria-label', b.title);
}
class TiltControl {
  onAdd() {
    this.el = document.createElement('div');
    this.el.className = 'maplibregl-ctrl maplibregl-ctrl-group';
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'tilt-btn';
    b.addEventListener('click', toggleTilt);
    this.el.append(b);
    return this.el;
  }
  onRemove() { this.el.remove(); }
}

function createTerrainMap(s) {
  terrainReady = false;
  terrainMap = new maplibregl.Map({
    container: 'terrain', style: terrainStyle(), center: [s.lng, s.lat], zoom: 4, pitch: 0,
    maxPitch: 80, attributionControl: false,
  });
  terrainMap.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
  terrainMap.addControl(new TiltControl(), 'top-right');
  terrainMap.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');
  syncTiltButton();
  ['mousedown', 'touchstart', 'wheel'].forEach(ev => terrainMap.on(ev, viewerTookOver));
  terrainMap.on('moveend', onMoveEnd);
  terrainMap.on('pitchend', syncTiltButton);
  terrainMap.on('zoomend', syncBaseLabels);
  terrainMap.once('load', () => {
    terrainReady = true;
    // Start the credits folded into the ⓘ button so they don't cover the caption.
    document.querySelectorAll('#terrain .maplibregl-ctrl-attrib').forEach(d => {
      d.classList.remove('maplibregl-compact-show'); d.removeAttribute('open');
    });
    applyMoonColours();              // in case it was switched while loading
    flyTerrainTo(currentSite());     // the site selected now, even if it changed while loading
  });
}

function openTerrain() {
  const s = currentSite();
  if (!s || typeof maplibregl === 'undefined' || !hasWebGL()) return;
  clearTimeout(flyInTimer);
  state.view = 'terrain';
  syncViewUI();                      // show the box first, so the map has a real size
  pauseRotation(0);
  state.globe?.pauseAnimation();     // the globe is covered; stop drawing it so the 3D map gets the GPU
  if (terrainMap && cameraBroken()) { terrainMap.remove(); terrainMap = null; }   // self-repair
  if (!terrainMap) return createTerrainMap(s);
  terrainMap.resize();
  flyTerrainTo(s);
}

function closeTerrain() {
  clearTimeout(flyInTimer);
  viewerTookOver();
  terrainMap?.stop();                // end any flight before the box is hidden
  clearBowlLayer();                  // ring and markers belong to the place shown in 3D
  state.view = 'globe';
  syncViewUI();
  state.globe?.resumeAnimation();
  pauseRotation(3000);
}

// Grey, high-contrast imagery so Earth terrain reads like the Moon.
const moonPaint = () => ({ 'raster-saturation': state.moonColours ? -1 : 0, 'raster-contrast': state.moonColours ? 0.25 : 0 });
// With 3D terrain, MapLibre caches the imagery draped on the ground, so setPaintProperty only
// recolours tiles that load later. Re-adding the layer redraws all of it at once.
function applyMoonColours() {
  if (!terrainReady) return;
  const layer = terrainMap.getStyle()?.layers.find(l => l.id === 'img');
  if (!layer) return;
  terrainMap.removeLayer('img');
  terrainMap.addLayer({ ...layer, paint: moonPaint() }, 'shade');
}

/* ---------- The bowl we scored (3D view) ----------
   Polar: a teal ring the size of the scored bowl (CRATER_DIAMETER_EQUIV_M, else DIAMETER_EQUIV_M, from
   raw_values.csv) centred on its low point (LAT/LON), plus dots at the crater floor and the base spot
   (BASE_LAT/BASE_LON). Mare: the base spot only. Pipeline places only; drawn by code from outputs/. */
const BOWL_COLOR = '#3CC8B4';
const BOWL_PITCH = 50;   // degrees; the usual 3D tilt (TILT) is 68
let bowlMarkers = [], bowlShown = null;
const numOrNull = v => (v == null || v === '' || !Number.isFinite(+v) ? null : +v);

// The point `dist` metres from (lng, lat) on bearing `brg` (radians), on a sphere (great circle).
function destPoint(lng, lat, dist, brg) {
  const R = 6371008.8, d = dist / R, r = Math.PI / 180, p1 = lat * r, l1 = lng * r;
  const p2 = Math.asin(Math.sin(p1) * Math.cos(d) + Math.cos(p1) * Math.sin(d) * Math.cos(brg));
  const l2 = l1 + Math.atan2(Math.sin(brg) * Math.sin(d) * Math.cos(p1), Math.cos(d) - Math.sin(p1) * Math.sin(p2));
  return [l2 / r, p2 / r];
}

function bowlOf(s) {
  if (!s || !isPipeline() || s.unscored || s.missed) return null;
  const raw = s.raw ?? {}, mare = s.BASE_TYPE === 'mare';
  const lat = numOrNull(s.LAT), lng = numOrNull(s.LON), blat = numOrNull(raw.BASE_LAT), blng = numOrNull(raw.BASE_LON);
  const floor = !mare && lat != null && lng != null ? [lng, lat] : null;
  const base = blat != null && blng != null ? [blng, blat] : null;
  const d = numOrNull(raw.CRATER_DIAMETER_EQUIV_M) ?? numOrNull(raw.DIAMETER_EQUIV_M);
  const diameter = floor && d > 0 ? d : null;
  return floor || base ? { mare, floor, base, diameter } : null;
}

// Zoom at which `metres` span the shorter side of the 3D view (MapLibre: the world is 512 × 2^zoom px wide).
function bowlZoom(bowl, lat) {
  const span = bowl?.diameter ? bowl.diameter * 2 : bowl?.mare ? 5000 : null;   // ring ≈ half the view; Mare ≈ 5 km
  const box = document.getElementById('terrain');
  const px = Math.min(box?.clientWidth || 800, box?.clientHeight || 600);
  if (!span || !px) return null;
  const z = Math.log2((40075016.686 * Math.cos(lat * Math.PI / 180) * px) / (512 * span));
  return Number.isFinite(z) ? Math.max(9, Math.min(16.5, z)) : null;
}

function bowlMarker(lngLat, text) {
  const el = document.createElement('div');
  el.className = 'bowl-pin';
  el.innerHTML = `<i></i><span>${esc(text)}</span>`;
  // Stays visible when a ridge stands between the camera and the point (MapLibre fades covered markers).
  return new maplibregl.Marker({ element: el, anchor: 'left', offset: [-6, 0], opacityWhenCovered: '0.9' }).setLngLat(lngLat).addTo(terrainMap);
}

function clearBowlLayer() {
  bowlMarkers.forEach(m => m.remove());
  bowlMarkers = [];
  bowlShown = null;
  if (!terrainMap) return;
  ['bowl-halo', 'bowl-ring'].forEach(id => terrainMap.getLayer(id) && terrainMap.removeLayer(id));
  if (terrainMap.getSource('bowl')) terrainMap.removeSource('bowl');
}

function drawBowlLayer(s) {
  clearBowlLayer();
  if (!terrainReady || state.view !== 'terrain') return;
  const bowl = bowlOf(s);
  if (!bowl) return;
  if (bowl.diameter) {
    // 64 points on the ground, as a polygon; its outline is draped over the terrain.
    const ring = Array.from({ length: 65 }, (_, i) => destPoint(...bowl.floor, bowl.diameter / 2, ((i % 64) / 64) * 2 * Math.PI));
    terrainMap.addSource('bowl', { type: 'geojson', data: { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [ring] } } });
    terrainMap.addLayer({ id: 'bowl-halo', type: 'line', source: 'bowl', paint: { 'line-color': '#030A12', 'line-width': 7, 'line-opacity': 0.6, 'line-blur': 1 } });
    terrainMap.addLayer({ id: 'bowl-ring', type: 'line', source: 'bowl', paint: { 'line-color': BOWL_COLOR, 'line-width': 3 } });
  }
  // With "Moon base to scale" on, the habitat label already marks the base spot: no dots then.
  if (!state.showBase) {
    if (bowl.floor) bowlMarkers.push(bowlMarker(bowl.floor, 'crater floor'));
    if (bowl.base) bowlMarkers.push(bowlMarker(bowl.base, 'base spot'));
  }
  bowlShown = { ring: !!bowl.diameter };
}

/* ---------- Moon base drawn to scale (3D view) ---------- */

// Sizes come from published sources; WHERE each piece sits is our own illustration, not a site plan.
// Drawn by code (no images, nothing AI-generated).
const BASE_SCALE = {
  habitatD: 6.5,       // m, NASA reference Surface Habitat, inflatable part, outer diameter (Burke, Howard & Kessler 2022)
  padInnerR: 12,       // m, landing pad inner zone (engine plume heat and pressure), Metzger & Autry 2022
  padOuterR: 27,       // m, landing pad outer zone (stops the plume eroding soil), Metzger & Autry 2022
  spacing: 200,        // m, habitat to pad centre: illustrative only, said in the caption
  shackletonD: 20900,  // m, Shackleton rim crest width, our LOLA measurement (config/lunar_targets.json)
  sources: {
    habitat: { label: 'Burke, Howard & Kessler (2022), Internal layout of a lunar surface habitat, NASA', url: 'https://ntrs.nasa.gov/citations/20220013669' },
    pad: { label: 'Metzger & Autry (2022), The cost of lunar landing pads', url: 'https://arxiv.org/abs/2205.00378' },
  },
};
const BASE_COLORS = { habitat: '#E8E3D3', pad: '#F0C85D', blast: '#F0A35D', shackleton: '#E8E3D3', path: '#7FDCCD' };
let baseMarkers = [];

// A circle as a polygon ring, r in metres (flat-Earth offset: fine at these sizes).
function circleRing(lng, lat, r, n = 96) {
  const kx = 111320 * Math.cos(lat * Math.PI / 180), ky = 110540;
  return Array.from({ length: n + 1 }, (_, i) => {
    const t = (i / n) * 2 * Math.PI;
    return [lng + (r * Math.cos(t)) / kx, lat + (r * Math.sin(t)) / ky];
  });
}
const offsetLngLat = (lng, lat, dx, dy) => [lng + dx / (111320 * Math.cos(lat * Math.PI / 180)), lat + dy / 110540];

// Habitat on the flat base spot our pipeline picked (BASE_LAT/BASE_LON), else the site point.
function basePlan(s) {
  const lat = Number(s.raw?.BASE_LAT ?? s.lat), lng = Number(s.raw?.BASE_LON ?? s.lng);
  const hab = [lng, lat], pad = offsetLngLat(lng, lat, BASE_SCALE.spacing, 0);
  const poly = (ring, kind) => ({ type: 'Feature', properties: { kind }, geometry: { type: 'Polygon', coordinates: [ring] } });
  const line = (coords, kind) => ({ type: 'Feature', properties: { kind }, geometry: { type: 'LineString', coordinates: coords } });
  return {
    hab, pad, shackletonLabel: offsetLngLat(s.lng, s.lat, 0, BASE_SCALE.shackletonD / 2),
    geojson: { type: 'FeatureCollection', features: [
      line(circleRing(s.lng, s.lat, BASE_SCALE.shackletonD / 2, 256), 'shackleton'),
      poly(circleRing(...pad, BASE_SCALE.padOuterR), 'blast'),
      poly(circleRing(...pad, BASE_SCALE.padInnerR), 'pad'),
      line([hab, pad], 'path'),
      poly(circleRing(...hab, BASE_SCALE.habitatD / 2, 48), 'habitat'),
    ] },
  };
}

function baseMarker(lngLat, text, cls) {
  const el = document.createElement('div');
  el.className = `base-label ${cls}`;
  el.textContent = text;
  return new maplibregl.Marker({ element: el, anchor: 'bottom', offset: [0, -6] }).setLngLat(lngLat).addTo(terrainMap);
}

function clearBaseLayer() {
  baseMarkers.forEach(m => m.remove());
  baseMarkers = [];
  if (!terrainMap) return;
  ['base-fill', 'base-edge', 'base-line', 'base-shackleton-casing', 'base-shackleton'].forEach(id => terrainMap.getLayer(id) && terrainMap.removeLayer(id));
  if (terrainMap.getSource('base')) terrainMap.removeSource('base');
}

function drawBaseLayer(s) {
  clearBaseLayer();
  if (!state.showBase || !terrainReady || !s) return;
  const plan = basePlan(s);
  terrainMap.addSource('base', { type: 'geojson', data: plan.geojson });
  terrainMap.addLayer({ id: 'base-fill', type: 'fill', source: 'base', filter: ['==', ['geometry-type'], 'Polygon'], paint: {
    'fill-color': ['match', ['get', 'kind'], 'habitat', BASE_COLORS.habitat, 'pad', BASE_COLORS.pad, BASE_COLORS.blast],
    'fill-opacity': ['match', ['get', 'kind'], 'habitat', 0.95, 'pad', 0.75, 0.3],
    'fill-outline-color': '#04201C',
  } });
  terrainMap.addLayer({ id: 'base-edge', type: 'line', source: 'base', filter: ['==', ['geometry-type'], 'Polygon'], paint: {
    'line-color': ['match', ['get', 'kind'], 'habitat', '#FFFFFF', 'pad', BASE_COLORS.pad, BASE_COLORS.blast], 'line-width': 1.5,
  } });
  terrainMap.addLayer({ id: 'base-line', type: 'line', source: 'base', filter: ['==', ['get', 'kind'], 'path'], paint: {
    'line-color': BASE_COLORS.path, 'line-width': 2, 'line-dasharray': [1.5, 1.5],
  } });
  // Shackleton's rim: white dashes on a dark band, so the ring shows on pale sand as well as on dark rock.
  terrainMap.addLayer({ id: 'base-shackleton-casing', type: 'line', source: 'base', filter: ['==', ['get', 'kind'], 'shackleton'], paint: {
    'line-color': '#030A12', 'line-width': 7, 'line-opacity': 0.55, 'line-blur': 1,
  } });
  terrainMap.addLayer({ id: 'base-shackleton', type: 'line', source: 'base', filter: ['==', ['get', 'kind'], 'shackleton'], paint: {
    'line-color': '#FFFFFF', 'line-width': 3.5, 'line-opacity': 1, 'line-dasharray': [3, 2],
  } });
  baseMarkers = [
    baseMarker(plan.hab, `Habitat ${BASE_SCALE.habitatD} m`, 'is-hab'),
    baseMarker(plan.pad, `Landing pad ${BASE_SCALE.padInnerR * 2} m · blast zone ${BASE_SCALE.padOuterR * 2} m`, 'is-pad'),
    baseMarker(plan.shackletonLabel, `Shackleton's rim, same scale (${(BASE_SCALE.shackletonD / 1000).toFixed(1)} km)`, 'is-shack'),
  ];
  syncBaseLabels();
}
// Zoomed out, the habitat and pad labels would sit on top of each other: show one "Base" label instead.
function syncBaseLabels() {
  if (baseMarkers.length < 3 || !terrainMap) return;
  const far = terrainMap.getZoom() < 14;
  const [hab, pad] = baseMarkers.map(m => m.getElement());
  hab.hidden = far;
  pad.textContent = far ? 'Moon base (habitat + landing pad)' : `Landing pad ${BASE_SCALE.padInnerR * 2} m · blast zone ${BASE_SCALE.padOuterR * 2} m`;
}

// Fly so both the habitat and the pad fit, tilted; zooming out shows Shackleton's rim around the crater.
// Same landing as a site fly-in (flightTarget/flightGoal), so onMoveEnd puts the camera on the real ground
// height afterwards; otherwise the base sits at the wrong height and its labels float off screen.
function flyCamera(center, zoom, pitch, bearing) {
  stopOrbit();
  flightTarget = null;
  settling = false;
  terrainMap.flyTo({ center, zoom, pitch, bearing, duration: reducedMotion ? 0 : 3500, essential: true });
  flightTarget = state.selected;
  flightGoal = { zoom, pitch };
}
function flyToBase(s) {
  if (!terrainReady || !s) return;
  const plan = basePlan(s);
  flyCamera([(plan.hab[0] + plan.pad[0]) / 2, (plan.hab[1] + plan.pad[1]) / 2], 16.4, 60, -20);
}
function flyToShackleton(s) {
  if (!terrainReady || !s) return;
  flyCamera([s.lng, s.lat], 10.4, 40, 0);
}

function toggleBase() {
  state.showBase = !state.showBase;
  const s = currentSite();
  drawBowlLayer(s);                  // ring stays; its dots step aside for the habitat label
  drawBaseLayer(s);
  if (state.showBase) flyToBase(s); else flyTerrainTo(s);
  syncViewUI();
}

function baseCaptionHTML() {
  const src = x => `<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.label)}</a>`;
  const sw = (c, round) => `<i class="base-sw${round ? ' is-round' : ''}" style="background:${c}"></i>`;
  return `<span class="base-key">${sw(BASE_COLORS.habitat, true)}habitat ${BASE_SCALE.habitatD} m wide ${sw(BASE_COLORS.pad, true)}landing pad ${BASE_SCALE.padInnerR * 2} m
    ${sw(BASE_COLORS.blast, true)}blast zone ${BASE_SCALE.padOuterR * 2} m <i class="base-sw is-ring"></i>Shackleton's rim ${(BASE_SCALE.shackletonD / 1000).toFixed(1)} km</span>
    <span class="base-more"><br>Drawn to scale by code. Sizes: habitat ${src(BASE_SCALE.sources.habitat)}; pad ${src(BASE_SCALE.sources.pad)}; Shackleton: our LOLA measurement.
    The layout (${BASE_SCALE.spacing} m apart, on the flat spot our pipeline picked) is only an illustration.</span>
    <span class="base-less"><br>Drawn to scale; sizes from NASA and published studies (sources on a wider screen). Layout is illustrative.</span>
    <br><button type="button" class="base-jump" data-base-jump="base">Close-up of the base</button>
    <button type="button" class="base-jump" data-base-jump="shackleton">Compare with Shackleton</button>`;
}

function syncViewUI() {
  const inTerrain = state.view === 'terrain';
  const s = currentSite();
  // Hidden with visibility, not display:none, so the map keeps its size.
  document.getElementById('terrain').classList.toggle('is-off', !inTerrain);
  document.getElementById('terrain').setAttribute('aria-hidden', String(!inTerrain));
  document.getElementById('globeLegend').hidden = inTerrain;
  document.getElementById('moonBtn').hidden = !inTerrain;
  document.getElementById('moonBtn').setAttribute('aria-pressed', String(!!state.moonColours));
  document.getElementById('baseBtn').hidden = !inTerrain || !s;
  document.getElementById('baseBtn').setAttribute('aria-pressed', String(!!state.showBase));
  const fly = document.getElementById('flyBtn');
  fly.textContent = inTerrain ? '← Back to globe' : 'Fly into 3D terrain';
  fly.disabled = !inTerrain && !s;
  const cap = document.getElementById('terrainCaption');
  cap.hidden = !inTerrain || !s;
  if (s) cap.innerHTML = `<b>${esc(nameOf(s))}</b><span class="cap-help${state.showBase ? ' is-base' : ''}"><br>3D terrain, heights ×${TERRAIN.exaggeration}. Drag to look around, scroll to zoom.</span>`
    + (state.showBase ? `<br>${baseCaptionHTML()}` : '')
    + (inTerrain && !state.showBase && bowlShown ? `<br><span class="bowl-key">${bowlShown.ring ? '<i class="bowl-sw-ring"></i>ring = the bowl we scored · ' : ''}<i class="bowl-sw-dot"></i>${bowlShown.ring ? 'dots = crater floor and base spot' : 'dot = base spot'}</span>` : '');
}

function wireViewTools() {
  document.getElementById('flyBtn').addEventListener('click', () => (state.view === 'terrain' ? closeTerrain() : openTerrain()));
  document.getElementById('moonBtn').addEventListener('click', () => { state.moonColours = !state.moonColours; applyMoonColours(); syncViewUI(); });
  document.getElementById('baseBtn').addEventListener('click', toggleBase);
  document.getElementById('terrainCaption').addEventListener('click', e => {
    const b = e.target.closest('[data-base-jump]');
    if (!b) return;
    (b.dataset.baseJump === 'shackleton' ? flyToShackleton : flyToBase)(currentSite());
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && state.view === 'terrain') closeTerrain(); });
}

/* ---------- Wiring ---------- */

// fly = the viewer clicked a site: spin the globe to it, then dive into 3D terrain.
function select(site, fly) {
  state.selected = site;
  renderList();
  renderCard();
  updateGlobe(fly && state.view === 'globe');
  if (!fly) return syncViewUI();
  if (state.view === 'terrain') return flyTerrainTo(currentSite());
  clearTimeout(flyInTimer);
  flyInTimer = setTimeout(openTerrain, reducedMotion ? 0 : 1300);
}

// Re-render everything after a filter or base change; keep the selection if it still passes.
function refresh() {
  const before = state.selected;
  const shown = visibleSites();
  if (!shown.some(s => s.SITE === state.selected)) state.selected = shown[0]?.SITE ?? null;
  renderFilters();
  renderList();
  renderCard();
  updateGlobe(false);
  if (state.view === 'terrain') {
    if (!state.selected) closeTerrain();
    else if (state.selected !== before) flyTerrainTo(currentSite());
  }
  syncViewUI();
}

(async function main() {
  try {
    await loadAll();
    if (FAKE_DIR) performance.mark('scale:data-loaded');   // scale test timing only
  } catch (err) {
    document.getElementById('card').innerHTML = `<p class="hint">Could not load ${esc(err.message)}. Open the app through a web server (for example <code>python -m http.server</code> in the repo root), not by double-clicking the file.</p>`;
    return;
  }
  document.getElementById('dataBadge').hidden = !DATA.isFake && !FAKE_DIR;   // fake scale-test data shows the badge too
  // Name only the data the app really shows. Planned sources: Copernicus DEM, ESA WorldCover, MODIS, LOLA, LROC, Diviner.
  document.getElementById('footNote').textContent = DATA.isFake
    ? 'Scores and heatmap are sample values, not results yet'
    : 'Scores from our pipeline: Earth terrain from Copernicus DEM GLO-30, Moon terrain from LOLA (LDEM 80°S, 20 m, Barker et al. 2023). Rock at site: Macrostrat, CC BY 4.0. Stations: INTERACT GIS station list (interact-gis.org, accessed 15 Nov 2026); own list of analog stations';
  wireFilters();
  wireViewTools();
  initGlobe();
  state.moonInfo = state.base;
  initMoon();
  renderMoonButtons();
  state.selected = bestTwin(ranked().filter(x => x.sim != null))?.SITE ?? ranked()[0]?.SITE ?? null;
  refresh();
  if (FAKE_DIR) performance.mark('scale:first-render');
  // Load the 3D map quietly behind the globe, so the first fly-in doesn't wait for it.
  setTimeout(() => {
    const s = currentSite();
    if (!terrainMap && s && typeof maplibregl !== 'undefined' && hasWebGL()) createTerrainMap(s);
  }, 1500);
})();
