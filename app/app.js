/* Earth Twins of the Moon: static web app (no build step).
 * Reads the pipeline's files in ../outputs/ (written by src/export_app.py) and draws:
 * filter bar, ranked site list, 3D globe with heatmap, analog card, 3D terrain close-up.
 * Add ?sample to the URL to see the old fake sample data instead (for design work).
 */

const USE_SAMPLE = new URLSearchParams(location.search).has('sample');
const DATA = USE_SAMPLE ? {
  scores: 'sample/scores.csv',       // fake 0–1 site values, compared with fake 0–1 targets
  targets: 'sample/targets.json',
  info: 'sample/site_info.json',
  isFake: true,                      // shows the "Fake data" badge
} : {
  scores: '../outputs/scores.csv',   // 0–1 values ARE the similarity to the Moon; SCORE_TOTAL, RANK
  targets: '../outputs/targets.json',// per base: criteria list with counts, weight, score_method, raw Moon value
  raw: '../outputs/raw_values.csv',  // raw Earth values, for "23.9° vs 27.2°" chips
  heatmap: '../outputs/heatmap.json',// [{lat, lng, weight}]
  cells: '../outputs/cells.json',    // every searched cell, with status (ranked / no_bowl / filtered)
  info: 'sample/site_info.json',     // Sofia's research notes per site (export_app.py reads it too)
  coords: 'sample/scores.csv',       // only SITE,LAT,LON: puts sites the pipeline hasn't scored yet on the map
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
  { key: 'GROUND_ICE',      group: 'env',      label: 'Ice in the ground',   hint: 'permafrost or ice cover', bases: ['polar'] },
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
const byKey = Object.fromEntries(CRITERIA.map(c => [c.key, c]));
const COLORS = { earth: '#6CB4EE', moon: '#E8E3D3', newSite: '#F0C85D', known: '#A7BAC7', signal: '#3CC8B4' };

const state = {
  sites: [], targets: {}, info: {}, columns: new Set(),
  crit: {},              // per base: { KEY: { counts, weight, method, moon, unit, earthUnit } }, same shape for both data formats
  heat: null, cells: [], // pipeline heatmap points and searched cells
  base: 'polar', group: 'all', active: new Set(), threshold: 0.7,
  typeFilter: 'all', selected: null, globe: null,
  view: 'globe', moonColours: false,   // 'globe' or 'terrain' (3D close-up of the selected site)
};

/* ---------- Loading ---------- */

function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  const head = lines.shift().split(',').map(s => s.trim());
  const rows = lines.filter(Boolean).map(line => {
    const cells = line.split(',');
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
const TEXT_COLUMNS = new Set(['SITE', 'RUN', 'CELL', 'BASE_TYPE']);

const getText = url => fetch(url).then(r => { if (!r.ok) throw new Error(url); return r.text(); });
const getJSON = url => fetch(url).then(r => { if (!r.ok) throw new Error(url); return r.json(); });
const optional = (url, fallback) => (url ? getJSON(url).catch(() => fallback) : Promise.resolve(fallback));

async function loadAll() {
  const [csv, targets, info, rawCsv, heat, cells, coordsCsv] = await Promise.all([
    getText(DATA.scores),
    getJSON(DATA.targets),
    optional(DATA.info, {}),
    DATA.raw ? getText(DATA.raw).catch(() => '') : Promise.resolve(''),
    optional(DATA.heatmap, null),
    optional(DATA.cells, []),
    DATA.coords ? getText(DATA.coords).catch(() => '') : Promise.resolve(''),
  ]);
  const { head, rows } = parseCSV(csv);
  const rawRows = rawCsv ? parseCSV(rawCsv).rows : [];
  const rawFor = r => rawRows.find(x => (r.RUN && x.RUN === r.RUN && x.CELL === r.CELL) || x.SITE === r.SITE) ?? {};
  state.columns = new Set(head);
  state.sites = rows.map(r => ({ ...r, lat: r.LAT, lng: r.LON, raw: rawFor(r) }));
  // Sites in site_info.json that the pipeline hasn't scored yet (it has only run on a few areas so far):
  // kept on the map and in the list as "not scored yet", with their research notes. Only their
  // coordinates are read from the sample file, never its fake values.
  if (coordsCsv) {
    const have = new Set(state.sites.map(x => x.SITE));
    parseCSV(coordsCsv).rows.filter(r => info[r.SITE] && !have.has(r.SITE) && r.LAT != null && r.LON != null)
      .forEach(r => state.sites.push({ SITE: r.SITE, LAT: r.LAT, LON: r.LON, lat: r.LAT, lng: r.LON, raw: {}, unscored: true }));
  }
  state.targets = Object.fromEntries(Object.entries(targets).filter(([k]) => !k.startsWith('_')));
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
const baseCriteria = () => CRITERIA.filter(c => !isPractical(c) && c.bases.includes(state.base) && meta(c.key));
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

const typeOf = site => state.info[site.SITE]?.type ?? 'candidate';
const nameOf = site => state.info[site.SITE ?? site]?.name ?? site.SITE ?? site;

// Active filters: a site passes when it has data and matches at least the threshold on every selected criterion.
function passesFilters(site) {
  for (const key of state.active) {
    const v = sim(site, byKey[key]);
    if (v == null || v < state.threshold) return false;
  }
  return true;
}

function ranked() {
  return state.sites
    .map(s => ({ ...s, ...scoreSite(s), type: typeOf(s) }))
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
function searchedRegions() {
  const by = {};
  state.cells.forEach(c => {
    const r = by[c.run] ??= { run: c.run, label: runLabel(c.run), cells: 0, ranked: 0, bbox: [...c.bbox], status: {} };
    r.cells++; if (c.status === 'ranked') r.ranked++;
    r.status[c.status] = (r.status[c.status] ?? 0) + 1;
    r.bbox = [Math.min(r.bbox[0], c.bbox[0]), Math.min(r.bbox[1], c.bbox[1]), Math.max(r.bbox[2], c.bbox[2]), Math.max(r.bbox[3], c.bbox[3])];
  });
  return Object.values(by).map(r => ({ ...r, lat: (r.bbox[1] + r.bbox[3]) / 2, lng: (r.bbox[0] + r.bbox[2]) / 2 }));
}
const pipelineAreas = () => searchedRegions().map(r => r.label).join(', ') || 'none yet';
const scoredCount = () => state.sites.filter(s => scoreSite(s).sim != null).length;

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
const fmtCoord = (lat, lng) => `${Math.abs(lat).toFixed(2)}°${lat >= 0 ? 'N' : 'S'}, ${Math.abs(lng).toFixed(2)}°${lng >= 0 ? 'E' : 'W'}`;
const research = s => esc(s).replace(/\[([^\]]+)\]/g, '<span class="todo">[$1]</span>');
// Source links under a research box; only http(s) links, opened in a new tab.
const sourcesHTML = list => {
  const ok = (list ?? []).filter(x => /^https?:\/\//.test(x?.url ?? ''));
  if (!ok.length) return '';
  return `<p class="sources-title">Sources</p><ul class="sources">${ok.map(x =>
    `<li><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.label || x.url)}</a></li>`).join('')}</ul>`;
};
const baseLabel = () => BASES.find(b => b.id === state.base)?.label ?? state.base;

/* ---------- Filter bar ---------- */

function renderFilters() {
  // Base type
  document.getElementById('baseSeg').innerHTML = BASES.filter(b => state.targets[b.id]).map(b =>
    `<button type="button" data-base="${b.id}" aria-pressed="${b.id === state.base}">${esc(b.label)}</button>`).join('');

  // Group tabs, with a count of active criteria per group
  const counts = {};
  state.active.forEach(k => { const g = byKey[k].group; counts[g] = (counts[g] ?? 0) + 1; });
  document.getElementById('groupTabs').innerHTML =
    [{ id: 'all', label: 'All criteria' }, ...GROUPS].map(g =>
      `<button type="button" class="tab" role="tab" data-group="${g.id}" aria-selected="${g.id === state.group}">${esc(g.label)}${counts[g.id] ? `<span class="count">${counts[g.id]}</span>` : ''}</button>`).join('');

  // Sub-row: the criteria of the chosen group
  const sub = document.getElementById('subRow');
  sub.hidden = state.group === 'all';
  if (!sub.hidden) {
    const g = GROUPS.find(x => x.id === state.group);
    document.getElementById('subHint').textContent = state.group === 'practical'
      ? 'Practical criteria do not change the similarity score. Pick one to hide sites that score below the minimum.'
      : `Pick criteria to keep only sites close to the Moon on them. Greyed out: not used for a ${baseLabel().toLowerCase()} base, or no data yet.`;
    document.getElementById('criterionChips').innerHTML = CRITERIA.filter(c => c.group === g.id).map(c => {
      const noData = !hasData(c.key);
      const notForBase = !c.bases.includes(state.base);
      const disabled = noData || notForBase;
      const m = meta(c.key);
      const tag = notForBase ? `not for ${baseLabel()}`
        : noData ? (m?.method === 'rank' ? 'awaiting lunar value' : m?.method === 'not computed' ? 'not computed yet' : 'no data yet')
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

function wireFilters() {
  document.getElementById('baseSeg').addEventListener('click', e => {
    const b = e.target.closest('[data-base]'); if (!b) return;
    state.base = b.dataset.base;
    // Drop filters that do not apply to the new base type
    [...state.active].forEach(k => { if (!byKey[k].bases.includes(state.base)) state.active.delete(k); });
    refresh();
  });
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

function renderList() {
  const list = document.getElementById('siteList');
  const rows = visibleSites().filter(s => state.typeFilter === 'all' || s.type === state.typeFilter);
  const total = state.sites.length, shown = visibleSites().length, unscored = total - scoredCount();
  document.getElementById('listHint').textContent = state.active.size
    ? `${shown} of ${total} sites pass the filters. Ranked by similarity to a ${baseLabel().toLowerCase()} base.`
    : `Ranked by similarity to a ${baseLabel().toLowerCase()} base on the ${similarityCriteria().length} criteria that count.`
      + (unscored ? ` ${unscored} sites the pipeline hasn't scored yet are listed after them.` : '');
  list.innerHTML = rows.length ? rows.map(s => `
    <li>
      <button type="button" class="site-btn" data-site="${esc(s.SITE)}" aria-current="${s.SITE === state.selected}">
        <span class="rank ${s.type === 'known' ? 'known' : 'new'}">${s.rank ?? '–'}</span>
        <span>
          <span class="site-name">${esc(nameOf(s))}</span>
          <span class="site-meta">
            ${s.sim == null ? '<span class="not-scored">Not scored yet</span>' : `<span class="bar"><span style="width:${Math.round(s.sim * 100)}%"></span></span>
            <span class="pct">${pct(s.sim)}</span>`}
            <span>${s.type === 'known' ? 'Known' : 'New'}</span>
          </span>
        </span>
      </button>
    </li>`).join('') : '<li class="empty">No site passes these filters. Lower the minimum match or remove a filter.</li>';
  // Regions the pipeline searched without finding a crater: also a result, worth showing.
  const empty = searchedRegions().filter(r => !r.ranked);
  if (empty.length && !state.active.size && state.typeFilter !== 'known') {
    list.insertAdjacentHTML('beforeend', `<li class="regions">
      <p class="regions-title">Searched, no crater found</p>
      <p class="regions-hint">No bowl at least 50 m deep and 1 km wide in these regions. Click one to see it on the globe.</p>
      ${empty.map(r => `<button type="button" class="region-btn" data-region="${esc(r.run)}" title="${r.cells} grid squares searched">${esc(r.label)}</button>`).join('')}
    </li>`);
    list.querySelectorAll('.region-btn').forEach(b => b.addEventListener('click', () => showRegion(b.dataset.region)));
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
const chipTitle = d => `${d.hint} · ${pct(d.sim)} match${meta(d.key)?.limitation ? ' · Moon: Sun disc · Earth: Sun centre' : ''}`;
// Short version of targets.json "limitation" for the light criteria (text agreed with Caspar).
const LIGHT_NOTE = 'Light on the Moon is measured as the visible part of the Sun’s disc (NASA PGDA illumination map); on Earth as the Sun’s centre above the horizon. On flat ground at the pole both agree; on crater rims and floors they can differ a little.';
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
  // Chips: criteria with a value, closest to the Moon first. ≥ 50 % = close, below = what it lacks.
  const scored = s.details.filter(d => d.counts && d.sim != null).sort((a, b) => b.sim - a.sim);
  const shownOnly = s.details.filter(d => !d.counts && d.sim != null);
  const strengths = scored.filter(d => d.sim >= 0.5).slice(0, 3);
  const gaps = scored.filter(d => d.sim < 0.5).reverse().slice(0, 3);
  // Three kinds of "no value": no data yet, waiting for a lunar value, not computed yet.
  const missing = { nodata: [], rank: [], notcomputed: [] };
  s.details.filter(d => d.sim == null).forEach(d => {
    missing[d.method === 'rank' ? 'rank' : d.method === 'not computed' ? 'notcomputed' : 'nodata'].push(d.label);
  });
  const displayOnly = s.details.filter(d => !d.counts && d.sim != null).map(d => d.label);
  const hasLightLimit = s.details.some(d => d.sim != null && meta(d.key)?.limitation);
  // "No Earth analog possible" facts (Grazing sun), shortened for the card; full text in the tooltip.
  const facts = s.details.filter(d => meta(d.key)?.fact).map(d => ({ label: d.label, text: meta(d.key).fact,
    short: d.key === 'GRAZING_SUN' ? 'How high the Sun climbs depends only on latitude: at least 23.4° on Earth (at the poles), 1.9° at Shackleton.' : meta(d.key).fact }));
  const practical = CRITERIA.filter(c => isPractical(c) && c.bases.includes(state.base) && s[c.key] != null);
  const { axes, perGroup } = radarAxes(s);
  const groupName = state.group === 'all' || state.group === 'practical'
    ? (perGroup ? 'Average per group' : 'All criteria') : GROUPS.find(g => g.id === state.group).label;
  const moonName = (target().label ?? 'Lunar target').split(' (')[0];
  const missingNote = [
    missing.nodata.length && `No data yet: ${missing.nodata.join(', ')}.`,
    missing.rank.length && `Waiting for a lunar value: ${missing.rank.join(', ')}.`,
    missing.notcomputed.length && `Not computed yet: ${missing.notcomputed.join(', ')}.`,
  ].filter(Boolean);
  const raw = s.raw ?? {};
  const craterFacts = [
    raw.DIAMETER_EQUIV_M != null && `about ${(raw.DIAMETER_EQUIV_M / 1000).toFixed(1)} km wide`,
    raw.DEPTH_SPILL_M != null && `${Math.round(raw.DEPTH_SPILL_M)} m deep`,
  ].filter(Boolean);

  el.innerHTML = `
    <div class="card-top">
      <div class="card-title">
        <span class="badge ${s.type === 'known' ? 'badge-known' : 'badge-new'}">${s.type === 'known' ? 'Known analog' : 'New candidate'}</span>
        <h2 style="margin-top:8px">${esc(nameOf(s))}</h2>
        <p class="card-place">${esc(info.place ?? '')}${info.place ? ' · ' : ''}${fmtCoord(s.lat, s.lng)}${craterFacts.length ? ' · crater ' + esc(craterFacts.join(', ')) : ''}</p>
      </div>
      <div class="score">
        <strong>${pct(s.sim)}</strong>
        <span>${unscored ? 'not scored yet' : `similar to the Moon (${esc(baseLabel().toLowerCase())} base)<br>rank ${s.RANK ?? s.rank} of ${scoredCount()}`}</span>
      </div>
    </div>

    ${info.why ? `<p class="why">${research(info.why)}</p>` : ''}

    <div class="card-body">
    <div class="card-col card-col-a">
    ${unscored ? `<div class="radar-box">
      <h3>Not scored yet</h3>
      <p class="nodata">Our pipeline has only searched a few regions so far (${esc(pipelineAreas())}), so this site has no score or fingerprint yet. It stays on the map with our research notes; it gets a score once the pipeline runs on its area.</p>
    </div>` : `<div class="radar-box">
      <h3>Fingerprint · ${esc(groupName)}</h3>
      ${radarSVG(s, axes)}
      <div class="radar-legend">
        <span><span class="swatch" style="border-color:${COLORS.earth}"></span>${esc(nameOf(s))}</span>
        <span><span class="swatch" style="border-color:${COLORS.moon};border-top-style:dashed"></span>${esc(moonName)} = outer ring</span>
      </div>
      <p class="nodata">Each axis is how close the site is to the Moon: the centre is nothing alike, the outer ring is the same as the Moon.${displayOnly.length ? ` Hollow dots (${esc(displayOnly.join(', '))}) are shown but not counted in the score.` : ''}</p>
      ${missingNote.length ? `<p class="nodata">${esc(missingNote.join(' '))} Left out of the score, not counted as zero.</p>` : ''}
      ${hasLightLimit ? `<p class="nodata" title="${esc(meta('SUNNY_RIDGE')?.limitation ?? '')}"><b>Light:</b> ${esc(LIGHT_NOTE)}</p>` : ''}
    </div>`}

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
      <div class="chips">${strengths.length ? strengths.map(d => `<span class="chip good" title="${esc(chipTitle(d))}"><b>${esc(d.label)}</b> ${esc(vsText(d))}</span>`).join('') : '<span class="chip">Nothing above 50 % yet</span>'}</div>
    </div>

    <div>
      <h3>What it lacks</h3>
      <div class="chips">${gaps.length ? gaps.map(d => `<span class="chip gap" title="${esc(chipTitle(d))}"><b>${esc(d.label)}</b> ${d.signed == null ? '' : d.signed < 0 ? 'too little ' : 'too much '}(${esc(vsText(d))})</span>`).join('') : '<span class="chip">No big gaps</span>'}</div>
    </div>

    ${shownOnly.length ? `<div>
      <h3>Also compared, not in the score</h3>
      <div class="chips">${shownOnly.map(d => `<span class="chip" title="${esc(chipTitle(d))}"><b>${esc(d.label)}</b> ${esc(vsText(d))}</span>`).join('')}</div>
      ${facts.map(f => `<p class="nodata" title="${esc(f.text)}"><b>${esc(f.label)}: no place on Earth can match.</b> ${esc(f.short)}</p>`).join('')}
    </div>` : ''}
    ${isPipeline() ? '<p class="nodata">Earth value vs Moon value. Hover a chip for its match.</p>' : ''}`}

    <div class="note-box">
      <h3>Where the analogy breaks down</h3>
      <p>${info.breaks ? research(info.breaks) : '<span class="todo">[to research]</span>'}</p>
    </div>

    <div class="note-box">
      <h3>${isNew ? 'What we could test here' : 'How it has helped exploration'}</h3>
      <p>${info.helps ? research(info.helps) : `<span class="todo">${isNew ? '[to write once ranked: what we could test here]' : '[to research]'}</span>`}</p>
      ${sourcesHTML(info.sources)}
    </div>
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
function initGlobe() {
  const el = document.getElementById('globe');
  if (!hasWebGL() || typeof Globe !== 'function') { document.getElementById('globeError').hidden = false; return; }
  // Pipeline: one point per ranked crater, weight = SCORE_TOTAL. Sample: a fake pattern, for design only.
  const heat = DATA.isFake ? fakeHeatPoints() : (state.heat ?? []);
  heatPoints = heat;
  setHeatNote();
  const regions = searchedRegions();
  const regionNote = document.getElementById('regionNote');
  regionNote.hidden = !regions.length;
  regionNote.innerHTML = `Searched regions (${regions.length}): <i style="border-color:${REGION_COLORS.found}"></i>crater found <i style="border-color:${REGION_COLORS.none}"></i>nothing found`;

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
    .heatmapBaseAltitude(0.005 * labelScale)
    .heatmapTopAltitude(0.06 * labelScale)
    .labelLat('lat')
    .labelLng('lng')
    .labelText(d => labelTextOf(d))
    .labelSize(d => (d.SITE === state.selected ? 1.6 : 1.0) * labelScale)
    .labelDotRadius(d => (d.SITE === state.selected ? 0.7 : 0.45) * labelScale)
    .labelColor(d => (d.SITE === state.selected ? '#FFFFFF' : (typeOf(d) === 'known' ? COLORS.known : COLORS.newSite)))
    .labelAltitude(() => 0.07 * labelScale)
    .labelResolution(2)
    .onLabelClick(d => select(d.SITE, true))
    // Outlines of every region the pipeline searched (from cells.json).
    .pathsData(searchedRegions().map(r => {
      const [w, so, e, n] = r.bbox;
      return { ...r, points: [[so, w], [so, e], [n, e], [n, w], [so, w]] };
    }))
    .pathPoints('points')
    .pathPointLat(p => p[0])
    .pathPointLng(p => p[1])
    .pathColor(r => (r.ranked ? REGION_COLORS.found : REGION_COLORS.none))   // strong colours: they must show on ice too
    .pathStroke(4)
    .pathTransitionDuration(0)
    .pathLabel(r => `${esc(r.label)}: ${r.ranked ? `${r.ranked} crater${r.ranked > 1 ? 's' : ''} scored` : 'searched, no crater found'}`)
    .ringColor(() => t => `rgba(255,255,255,${1 - t})`)
    .ringMaxRadius(() => 4 * labelScale)
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
  g.pointOfView({ lat: 35, lng: 10, altitude: 2.3 });

  const fit = () => g.width(el.clientWidth).height(el.clientHeight);
  new ResizeObserver(fit).observe(el);
  fit();
  state.globe = g;
}

// Globe labels are sized in degrees on the globe, so zoomed in they grow huge and nearby craters
// (El Elegante and Pinacate NW are 25 km apart) pile up. Scale them with the camera height, and
// where labels would still overlap show only the best-ranked one, with "+1" for the hidden ones.
let labelScale = 1, labelHidden = new Map(), heatPoints = [], heatShown = true;
const HEAT_MIN_SCALE = 0.25;   // closer than this the blobs only cover the ground, so the heatmap hides
function setHeatNote() {
  document.getElementById('heatNote').textContent = !heatShown ? 'Zoom out to see the heatmap'
    : DATA.isFake ? 'Fake pattern, for design only'
    : heatPoints.length ? `${heatPoints.length} craters scored so far` : 'No heatmap data yet';
}   // SITE → '' (hidden) or ' +n' (leader of a group)
const labelTextOf = d => (labelHidden.has(d.SITE) ? (labelHidden.get(d.SITE) === '' ? '' : nameOf(d) + labelHidden.get(d.SITE)) : nameOf(d));

function declutterLabels(sites) {
  labelHidden = new Map();
  const order = [...sites].sort((a, b) => (b.SITE === state.selected) - (a.SITE === state.selected) || (a.rank ?? 1e9) - (b.rank ?? 1e9));
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
  g.heatmapBaseAltitude(0.005 * scale).heatmapTopAltitude(0.06 * scale);
  if (heatShown !== scale >= HEAT_MIN_SCALE) {
    heatShown = scale >= HEAT_MIN_SCALE;
    g.heatmapsData(heatShown ? [{ points: heatPoints }] : []);
    setHeatNote();
  }
  updateGlobe(false);
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
  const shown = visibleSites();
  const s = shown.find(x => x.SITE === state.selected);
  declutterLabels(shown);
  g.labelsData(shown.map(x => ({ ...x })));   // new objects so globe.gl redraws sizes and texts
  g.ringsData(s ? [{ lat: s.lat, lng: s.lng }] : []);
  if (s && fly) {
    pauseRotation(6000);
    g.pointOfView({ lat: s.lat, lng: s.lng, altitude: 1.4 }, 1200);
    setTimeout(onGlobeZoom, 1300);   // a programmed move doesn't fire the controls' 'change'
  }
}

/* ---------- 3D terrain: MapLibre GL with free tiles (no account, no key) ---------- */

const TERRAIN = {
  // Elevation: Terrain Tiles on AWS Open Data (Mapzen; SRTM, GMTED, ETOPO1 and others), Terrarium encoding.
  dem: 'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png',
  // Imagery: Sentinel-2 cloudless 2020 by EOX (modified Copernicus Sentinel data), about 10 m per pixel.
  img: 'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2020_3857/default/g/{z}/{y}/{x}.jpg',
  exaggeration: 1.5,   // heights x1.5 so relief reads on screen; said in the caption
  defaultZoom: 12,     // a site can set its own "zoom" in site_info.json
};
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
let terrainMap = null, terrainReady = false, orbitFrame = null, flyInTimer = null;
let flightTarget = null;                 // the fly-in in progress, so the orbit starts only if it arrives
const TILT = { pitch: 68, bearing: -25 }; // the tilted 3D view; the 2D/3D button returns to it

const currentSite = () => visibleSites().find(s => s.SITE === state.selected);

const CELL_COLORS = { ranked: '#3CC8B4', filtered: '#F2A35C', no_bowl: '#A7BAC7', ice_floor: '#9CCFF2' };
// Searched cells from cells.json as outlines (bbox = [W, S, E, N]).
function cellsGeoJSON() {
  return { type: 'FeatureCollection', features: state.cells.filter(c => Array.isArray(c.bbox)).map(c => {
    const [w, so, e, n] = c.bbox;
    return { type: 'Feature', properties: { status: c.status, reason: c.reason ?? '' },
      geometry: { type: 'LineString', coordinates: [[w, so], [e, so], [e, n], [w, n], [w, so]] } };
  }) };
}

function terrainStyle() {
  const dem = { type: 'raster-dem', tiles: [TERRAIN.dem], tileSize: 256, maxzoom: 15, encoding: 'terrarium' };
  return {
    version: 8,
    sources: {
      img: { type: 'raster', tiles: [TERRAIN.img], tileSize: 256, maxzoom: 15,
        attribution: 'Imagery: <a href="https://s2maps.eu" target="_blank" rel="noopener">Sentinel-2 cloudless</a> by EOX (contains modified Copernicus Sentinel data 2020)' },
      dem: { ...dem, attribution: 'Elevation: <a href="https://registry.opendata.aws/terrain-tiles/" target="_blank" rel="noopener">Terrain Tiles on AWS</a> (Mapzen)' },
      shade: dem,
      cells: { type: 'geojson', data: cellsGeoJSON() },
    },
    layers: [
      { id: 'space', type: 'background', paint: { 'background-color': '#030A12' } },
      { id: 'img', type: 'raster', source: 'img', paint: moonPaint() },
      { id: 'shade', type: 'hillshade', source: 'shade', paint: { 'hillshade-exaggeration': 0.3, 'hillshade-shadow-color': '#000000' } },
      // The grid cells the pipeline searched: teal = crater scored, orange = skipped (edge or sea), grey = no crater.
      // (Two layers: MapLibre can't change the dash pattern per feature.)
      { id: 'cells-other', type: 'line', source: 'cells', filter: ['!=', ['get', 'status'], 'ranked'], paint: {
        'line-color': ['match', ['get', 'status'], 'filtered', CELL_COLORS.filtered, 'ice_floor', CELL_COLORS.ice_floor, CELL_COLORS.no_bowl],
        'line-width': 1.2, 'line-opacity': 0.65, 'line-dasharray': [2, 2],
      } },
      { id: 'cells-ranked', type: 'line', source: 'cells', filter: ['==', ['get', 'status'], 'ranked'], paint: {
        'line-color': CELL_COLORS.ranked, 'line-width': 2.5, 'line-opacity': 0.95,
      } },
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
  const zoom = state.info[s.SITE]?.zoom ?? TERRAIN.defaultZoom;
  flightTarget = null;   // flyTo first stops any old move, which fires a 'moveend' that must not orbit
  settling = false;
  terrainMap.flyTo({ center: [s.lng, s.lat], zoom, ...TILT, duration: reducedMotion ? 0 : 4500, essential: true });
  flightTarget = s.SITE;
  flightGoal = { zoom, pitch: TILT.pitch };
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

function syncViewUI() {
  const inTerrain = state.view === 'terrain';
  const s = currentSite();
  // Hidden with visibility, not display:none, so the map keeps its size.
  document.getElementById('terrain').classList.toggle('is-off', !inTerrain);
  document.getElementById('terrain').setAttribute('aria-hidden', String(!inTerrain));
  document.getElementById('globeLegend').hidden = inTerrain;
  document.getElementById('moonBtn').hidden = !inTerrain;
  document.getElementById('moonBtn').setAttribute('aria-pressed', String(!!state.moonColours));
  const fly = document.getElementById('flyBtn');
  fly.textContent = inTerrain ? '← Back to globe' : 'Fly into 3D terrain';
  fly.disabled = !inTerrain && !s;
  const cap = document.getElementById('terrainCaption');
  cap.hidden = !inTerrain || !s;
  if (s) cap.innerHTML = `<b>${esc(nameOf(s))}</b><br>3D terrain, heights ×${TERRAIN.exaggeration}. Drag to look around, scroll to zoom.`
    + (state.cells.length ? `<br><span class="cell-key"><i style="border-color:${CELL_COLORS.ranked}"></i>scored crater <i style="border-color:${CELL_COLORS.filtered}"></i>skipped (edge or sea) <i style="border-color:${CELL_COLORS.no_bowl}"></i>no crater found${state.cells.some(c => c.status === 'ice_floor') ? ` <i style="border-color:${CELL_COLORS.ice_floor}"></i>ice-filled floor` : ''}</span>` : '');
}

function wireViewTools() {
  document.getElementById('flyBtn').addEventListener('click', () => (state.view === 'terrain' ? closeTerrain() : openTerrain()));
  document.getElementById('moonBtn').addEventListener('click', () => { state.moonColours = !state.moonColours; applyMoonColours(); syncViewUI(); });
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
  } catch (err) {
    document.getElementById('card').innerHTML = `<p class="hint">Could not load ${esc(err.message)}. Open the app through a web server (for example <code>python -m http.server</code> in the repo root), not by double-clicking the file.</p>`;
    return;
  }
  document.getElementById('dataBadge').hidden = !DATA.isFake;
  // Name only the data the app really shows. Planned sources: Copernicus DEM, ESA WorldCover, MODIS, LOLA, LROC, Diviner.
  document.getElementById('footNote').textContent = DATA.isFake
    ? 'Scores and heatmap are sample values, not results yet'
    : 'Scores from our pipeline: Earth terrain from Copernicus DEM GLO-30, Moon terrain from LOLA (LDEM 80°S, 20 m, Barker et al. 2023)';
  wireFilters();
  wireViewTools();
  initGlobe();
  state.selected = ranked()[0]?.SITE ?? null;
  refresh();
  // Load the 3D map quietly behind the globe, so the first fly-in doesn't wait for it.
  setTimeout(() => {
    const s = currentSite();
    if (!terrainMap && s && typeof maplibregl !== 'undefined' && hasWebGL()) createTerrainMap(s);
  }, 1500);
})();
