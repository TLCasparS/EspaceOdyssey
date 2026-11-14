/* Earth Twins of the Moon: static web app (no build step).
 * Reads three files and draws: filter bar, ranked site list, 3D globe with heatmap, analog card.
 * To switch from fake to real data, change the paths in DATA below.
 */

const DATA = {
  scores: 'sample/scores.csv',       // later: '../outputs/scores.csv'   (Earth scoring)
  targets: 'sample/targets.json',    // later: '../outputs/targets.json' (Moon targets role)
  info: 'sample/site_info.json',     // Sofia's research notes per site
  isFake: true,                      // shows the "Fake data" badge
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
  { key: 'RELIEF',          group: 'terrain',  label: 'Relief',              hint: 'height range within ~5 km', bases: ANY },
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
const COLORS = { earth: '#6CB4EE', moon: '#E8E3D3', newSite: '#F0C85D', known: '#AAB3D6', red: '#D53C25' };

const state = {
  sites: [], targets: {}, info: {}, columns: new Set(),
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
      row[h] = raw === '' ? null : (h === 'SITE' ? raw : Number(raw));
    });
    return row;
  });
  return { head, rows };
}

async function loadAll() {
  const [csv, targets, info] = await Promise.all([
    fetch(DATA.scores).then(r => { if (!r.ok) throw new Error(DATA.scores); return r.text(); }),
    fetch(DATA.targets).then(r => { if (!r.ok) throw new Error(DATA.targets); return r.json(); }),
    fetch(DATA.info).then(r => (r.ok ? r.json() : {})).catch(() => ({})),
  ]);
  const { head, rows } = parseCSV(csv);
  state.columns = new Set(head);
  state.sites = rows.map(r => ({ ...r, lat: r.LAT, lng: r.LON }));
  state.targets = Object.fromEntries(Object.entries(targets).filter(([k]) => !k.startsWith('_')));
  state.info = info;
  if (!state.targets[state.base]) state.base = Object.keys(state.targets)[0];
}

/* ---------- Scoring ---------- */

const target = () => state.targets[state.base] ?? {};
const isPractical = c => c.group === 'practical';
// A criterion counts for similarity when it matters for this base, has a lunar value and is not practical.
const similarityCriteria = () => CRITERIA.filter(c => !isPractical(c) && c.bases.includes(state.base) && target()[c.key] != null);
const closeness = (site, c) => {
  const s = site[c.key];
  if (s == null) return null;
  if (isPractical(c)) return s;            // practical: higher is better, no lunar target
  const t = target()[c.key];
  return t == null ? null : 1 - Math.abs(s - t);
};

// Similarity = 1 − mean absolute difference to the lunar target, over criteria with data.
function scoreSite(site) {
  const diffs = [];
  for (const c of similarityCriteria()) {
    const s = site[c.key], t = target()[c.key];
    if (s == null) continue;
    diffs.push({ ...c, site: s, target: t, diff: Math.abs(s - t), signed: s - t });
  }
  const sim = diffs.length ? 1 - diffs.reduce((a, d) => a + d.diff, 0) / diffs.length : null;
  return { sim, diffs, coverage: diffs.length, possible: similarityCriteria().length };
}

const typeOf = site => state.info[site.SITE]?.type ?? 'candidate';

// Active filters: a site passes when it has data and matches at least the threshold on every selected criterion.
function passesFilters(site) {
  for (const key of state.active) {
    const v = closeness(site, byKey[key]);
    if (v == null || v < state.threshold) return false;
  }
  return true;
}

function ranked() {
  return state.sites
    .map(s => ({ ...s, ...scoreSite(s), type: typeOf(s) }))
    .sort((a, b) => (b.sim ?? -1) - (a.sim ?? -1))
    .map((s, i) => ({ ...s, rank: i + 1, passes: passesFilters(s) }));
}
const visibleSites = () => ranked().filter(s => s.passes);

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
      const noColumn = !state.columns.has(c.key);
      const notForBase = !c.bases.includes(state.base);
      const disabled = noColumn || notForBase;
      const tag = noColumn ? 'no data yet' : notForBase ? `not for ${baseLabel()}` : '';
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
  const total = state.sites.length, shown = visibleSites().length;
  document.getElementById('listHint').textContent = state.active.size
    ? `${shown} of ${total} sites pass the filters. Ranked by similarity to a ${baseLabel().toLowerCase()} base.`
    : `Ranked by similarity to a ${baseLabel().toLowerCase()} base, across all criteria with data.`;
  list.innerHTML = rows.length ? rows.map(s => `
    <li>
      <button type="button" class="site-btn" data-site="${esc(s.SITE)}" aria-current="${s.SITE === state.selected}">
        <span class="rank ${s.type === 'known' ? 'known' : 'new'}">${s.rank}</span>
        <span>
          <span class="site-name">${esc(s.SITE)}</span>
          <span class="site-meta">
            <span class="bar"><span style="width:${Math.round((s.sim ?? 0) * 100)}%"></span></span>
            <span class="pct">${pct(s.sim)}</span>
            <span>${s.type === 'known' ? 'Known' : 'New'}</span>
          </span>
        </span>
      </button>
    </li>`).join('') : '<li class="empty">No site passes these filters. Lower the minimum match or remove a filter.</li>';
  list.querySelectorAll('.site-btn').forEach(b => b.addEventListener('click', () => select(b.dataset.site, true)));
}

/* ---------- Radar chart (SVG, no library) ---------- */

// "All criteria": one axis per group (mean of its criteria). A group tab: one axis per criterion in it.
function radarAxes(site) {
  const crits = similarityCriteria();
  if (state.group === 'all' || state.group === 'practical') {
    return GROUPS.filter(g => g.id !== 'practical').map(g => {
      const cs = crits.filter(c => c.group === g.id && site[c.key] != null);
      const mean = arr => (arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null);
      return { label: g.short ?? g.label, site: mean(cs.map(c => site[c.key])), target: mean(cs.map(c => target()[c.key])) };
    }).filter(a => a.target != null || a.site != null);
  }
  return crits.filter(c => c.group === state.group).map(c => ({ label: c.label, site: site[c.key], target: target()[c.key] }));
}

function radarSVG(site) {
  const axes = radarAxes(site);
  if (axes.length < 3) {
    return `<p class="nodata">This group has fewer than three criteria for a ${esc(baseLabel().toLowerCase())} base, so there is no radar. See the chips below.</p>`;
  }
  const W = 470, H = 340, cx = W / 2, cy = H / 2 + 4, R = 112, n = axes.length;
  const ang = i => (-90 + (360 / n) * i) * Math.PI / 180;
  const pt = (i, v) => [cx + Math.cos(ang(i)) * R * v, cy + Math.sin(ang(i)) * R * v];
  const poly = vals => vals.map((v, i) => (v == null ? null : pt(i, v).map(x => x.toFixed(1)).join(','))).filter(Boolean).join(' ');
  const rings = [0.25, 0.5, 0.75, 1].map(f =>
    `<polygon points="${axes.map((_, i) => pt(i, f).join(',')).join(' ')}" fill="none" stroke="#283580" stroke-width="1"></polygon>`).join('');
  const lines = axes.map((a, i) => {
    const [x, y] = pt(i, 1);
    return `<line x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="#283580" ${a.site == null ? 'stroke-dasharray="3 4"' : ''}></line>`;
  }).join('');
  const labels = axes.map((a, i) => {
    const [x, y] = pt(i, 1.17);
    const cos = Math.cos(ang(i));
    const anchor = Math.abs(cos) < 0.2 ? 'middle' : cos > 0 ? 'start' : 'end';
    const note = a.site == null ? `<tspan x="${x.toFixed(1)}" dy="14" font-size="10.5">no data</tspan>` : '';
    return `<text x="${x.toFixed(1)}" y="${(y + 4).toFixed(1)}" text-anchor="${anchor}" font-size="12" font-family="Fira Sans, sans-serif" fill="${a.site == null ? '#8D96BD' : '#EEF1FA'}">${esc(a.label)}${note}</text>`;
  }).join('');
  const dots = axes.map((a, i) => (a.site == null ? '' : `<circle cx="${pt(i, a.site)[0].toFixed(1)}" cy="${pt(i, a.site)[1].toFixed(1)}" r="3.5" fill="${COLORS.earth}"></circle>`)).join('');
  return `<svg class="radar" viewBox="0 0 ${W} ${H}" role="img" aria-label="Radar chart: ${esc(site.SITE)} compared with the lunar target on ${n} axes">
    ${rings}${lines}
    <polygon points="${poly(axes.map(a => a.target))}" fill="rgba(232,227,211,0.06)" stroke="${COLORS.moon}" stroke-width="2" stroke-dasharray="6 4"></polygon>
    <polygon points="${poly(axes.map(a => a.site))}" fill="rgba(108,180,238,0.25)" stroke="${COLORS.earth}" stroke-width="2.5"></polygon>
    ${dots}${labels}
  </svg>`;
}

/* ---------- Analog card ---------- */

function renderCard() {
  const el = document.getElementById('card');
  const s = ranked().find(r => r.SITE === state.selected);
  if (!s) { el.innerHTML = '<p class="hint">Pick a site from the list or the globe.</p>'; return; }
  const info = state.info[s.SITE] ?? {};
  const isNew = info.type === 'candidate';
  const byClosest = [...s.diffs].sort((a, b) => a.diff - b.diff);
  const strengths = byClosest.slice(0, 3);
  const gaps = byClosest.slice().reverse().filter(d => d.diff >= 0.15).slice(0, 3);
  const missing = similarityCriteria().filter(c => s[c.key] == null).map(c => c.label);
  const practical = CRITERIA.filter(c => isPractical(c) && c.bases.includes(state.base));
  const groupName = state.group === 'all' || state.group === 'practical' ? 'Average per group' : GROUPS.find(g => g.id === state.group).label;

  el.innerHTML = `
    <div class="card-top">
      <div class="card-title">
        <span class="badge ${s.type === 'known' ? 'badge-known' : 'badge-new'}">${s.type === 'known' ? 'Known analog' : 'New candidate'}</span>
        <h2 style="margin-top:8px">${esc(s.SITE)}</h2>
        <p class="card-place">${esc(info.place ?? '')}${info.place ? ' · ' : ''}${fmtCoord(s.lat, s.lng)}</p>
      </div>
      <div class="score">
        <strong>${pct(s.sim)}</strong>
        <span>similar to a ${esc(baseLabel().toLowerCase())} base<br>rank ${s.rank} of ${state.sites.length}</span>
      </div>
    </div>

    ${info.why ? `<p class="why">${research(info.why)}</p>` : ''}

    <div class="radar-box">
      <h3>Fingerprint · ${esc(groupName)}</h3>
      ${radarSVG(s)}
      <div class="radar-legend">
        <span><span class="swatch" style="border-color:${COLORS.earth}"></span>${esc(s.SITE)}</span>
        <span><span class="swatch" style="border-color:${COLORS.moon};border-top-style:dashed"></span>${esc(target().label ?? 'Lunar target')}</span>
      </div>
      ${missing.length ? `<p class="nodata">No data yet: ${missing.map(esc).join(', ')}. Left out of the score, not counted as zero.</p>` : ''}
    </div>

    <div>
      <h3>Closest to the Moon on</h3>
      <div class="chips">${strengths.map(d => `<span class="chip good"><b>${esc(d.label)}</b> ${d.site.toFixed(2)} vs ${d.target.toFixed(2)}</span>`).join('')}</div>
    </div>

    <div>
      <h3>What it lacks</h3>
      <div class="chips">${gaps.length ? gaps.map(d => `<span class="chip gap"><b>${esc(d.label)}</b> ${d.signed < 0 ? 'too little' : 'too much'} (${d.site.toFixed(2)} vs ${d.target.toFixed(2)})</span>`).join('') : '<span class="chip">No big gaps</span>'}</div>
    </div>

    <div class="note-box">
      <h3>Where the analogy breaks down</h3>
      <p>${info.breaks ? research(info.breaks) : '<span class="todo">[to research]</span>'}</p>
    </div>

    <div class="note-box">
      <h3>${isNew ? 'What we could test here' : 'How it has helped exploration'}</h3>
      <p>${info.helps ? research(info.helps) : `<span class="todo">${isNew ? '[to write once ranked: what we could test here]' : '[to research]'}</span>`}</p>
      ${sourcesHTML(info.sources)}
    </div>

    <div class="note-box">
      <h3>Practical</h3>
      <div class="prac">${practical.map(c => `
        <span title="${esc(c.hint)}">${esc(c.label)}</span>
        <span class="bar"><span style="width:${Math.round((s[c.key] ?? 0) * 100)}%"></span></span>
        <span class="pct">${s[c.key] == null ? '–' : Math.round(s[c.key] * 100)}</span>`).join('')}
      </div>
      <p class="nodata">Scored apart from similarity: these say how easy the site is to use, not how Moon-like it is.</p>
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
  const heat = fakeHeatPoints();
  document.getElementById('heatNote').textContent = DATA.isFake ? 'Fake pattern, for design only' : '';

  const g = Globe()(el)
    // NASA Blue Marble Next Generation, July 2004, topography + bathymetry (NASA Earth Observatory),
    // resized from 5400x2700 to 4096x2048. Relief shading is already in the image.
    .globeImageUrl('assets/blue-marble-2004-07-4096.jpg')
    .backgroundColor('#03051A')
    .atmosphereColor('#6CB4EE')
    .atmosphereAltitude(0.15)
    .heatmapsData([{ points: heat }])
    .heatmapPoints(d => d.points)
    .heatmapPointLat('lat')
    .heatmapPointLng('lng')
    .heatmapPointWeight('weight')
    .heatmapBandwidth(2.4)
    .heatmapColorSaturation(2.2)
    .heatmapBaseAltitude(0.005)
    .heatmapTopAltitude(0.06)
    .labelLat('lat')
    .labelLng('lng')
    .labelText('SITE')
    .labelSize(d => (d.SITE === state.selected ? 1.8 : 1.1))
    .labelDotRadius(d => (d.SITE === state.selected ? 0.8 : 0.5))
    .labelColor(d => (d.SITE === state.selected ? '#FFFFFF' : (typeOf(d) === 'known' ? COLORS.known : COLORS.newSite)))
    .labelAltitude(0.07)
    .labelResolution(2)
    .onLabelClick(d => select(d.SITE, true))
    .ringColor(() => t => `rgba(255,255,255,${1 - t})`)
    .ringMaxRadius(4)
    .ringPropagationSpeed(2)
    .ringRepeatPeriod(1200)
    .ringAltitude(0.07);

  // Always rotating; pauses briefly while someone drags or after flying to a site.
  const controls = g.controls();
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.35;
  controls.addEventListener('start', () => pauseRotation(0));
  controls.addEventListener('end', () => pauseRotation(4000));
  g.pointOfView({ lat: 35, lng: 10, altitude: 2.3 });

  const fit = () => g.width(el.clientWidth).height(el.clientHeight);
  new ResizeObserver(fit).observe(el);
  fit();
  state.globe = g;
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
  g.labelsData(shown);
  g.ringsData(s ? [{ lat: s.lat, lng: s.lng }] : []);
  if (s && fly) {
    pauseRotation(6000);
    g.pointOfView({ lat: s.lat, lng: s.lng, altitude: 1.4 }, 1200);
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

function terrainStyle() {
  const dem = { type: 'raster-dem', tiles: [TERRAIN.dem], tileSize: 256, maxzoom: 15, encoding: 'terrarium' };
  return {
    version: 8,
    sources: {
      img: { type: 'raster', tiles: [TERRAIN.img], tileSize: 256, maxzoom: 15,
        attribution: 'Imagery: <a href="https://s2maps.eu" target="_blank" rel="noopener">Sentinel-2 cloudless</a> by EOX (contains modified Copernicus Sentinel data 2020)' },
      dem: { ...dem, attribution: 'Elevation: <a href="https://registry.opendata.aws/terrain-tiles/" target="_blank" rel="noopener">Terrain Tiles on AWS</a> (Mapzen)' },
      shade: dem,
    },
    layers: [
      { id: 'space', type: 'background', paint: { 'background-color': '#03051A' } },
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
  const zoom = state.info[s.SITE]?.zoom ?? TERRAIN.defaultZoom;
  flightTarget = null;   // flyTo first stops any old move, which fires a 'moveend' that must not orbit
  terrainMap.flyTo({ center: [s.lng, s.lat], zoom, ...TILT, duration: reducedMotion ? 0 : 4500, essential: true });
  flightTarget = s.SITE;
  syncViewUI();
}

function onMoveEnd() {
  // Orbit only when a fly-in finished untouched: a drag, scroll or new flight clears flightTarget first.
  // (Don't compare zoom: with terrain, MapLibre adjusts it for the ground height, e.g. 14 → 13.5.)
  if (flightTarget) startOrbit();
  flightTarget = null;
  syncTiltButton();
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
  if (s) cap.innerHTML = `<b>${esc(s.SITE)}</b><br>3D terrain, heights ×${TERRAIN.exaggeration}. Drag to look around, scroll to zoom.`;
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
    : 'Scores from our pipeline: Copernicus DEM, ESA WorldCover, MODIS (Earth); LOLA, LROC, Diviner (Moon)';
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
