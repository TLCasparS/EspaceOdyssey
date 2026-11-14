/* Earth Twins of the Moon: static web app (no build step).
 * Reads three files and draws: ranked site list, 3D globe with heatmap, analog card.
 * To switch from fake to real data, change the paths in DATA below.
 */

const DATA = {
  scores: 'sample/scores.csv',       // later: '../outputs/scores.csv'   (Caspar)
  targets: 'sample/targets.json',    // later: '../outputs/targets.json' (Moon targets role)
  info: 'sample/site_info.json',     // Sofia's research notes per site
  isFake: true,                      // shows the "Fake data" badge
};

// Criteria in the agreed scores.csv order, with plain-language labels for the card.
const CRITERIA = [
  { key: 'SLOPE_BASE',  label: 'Flat base spot' },
  { key: 'STEEP_WALLS', label: 'Steep crater walls' },
  { key: 'RELIEF',      label: 'Height difference' },
  { key: 'ROUGHNESS',   label: 'Bumpy ground' },
  { key: 'BOWL_SHAPE',  label: 'Bowl shape' },
  { key: 'SUNNY_RIDGE', label: 'Sunny ridge' },
  { key: 'DARK_FLOOR',  label: 'Dark floor' },
  { key: 'BARE',        label: 'Bare ground' },
];

const COLORS = { earth: '#6CB4EE', moon: '#E8E3D3', newSite: '#F0C85D', known: '#A3ADBB' };

const state = { sites: [], targets: {}, info: {}, targetKey: null, selected: null, filter: 'all', globe: null };

/* ---------- Loading ---------- */

function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  const head = lines.shift().split(',').map(s => s.trim());
  return lines.filter(Boolean).map(line => {
    const cells = line.split(',');
    const row = {};
    head.forEach((h, i) => {
      const raw = (cells[i] ?? '').trim();
      // Agreed rule: an empty cell means "no data", never zero.
      row[h] = raw === '' ? null : (h === 'SITE' ? raw : Number(raw));
    });
    return row;
  });
}

async function loadAll() {
  const [csv, targets, info] = await Promise.all([
    fetch(DATA.scores).then(r => { if (!r.ok) throw new Error(DATA.scores); return r.text(); }),
    fetch(DATA.targets).then(r => { if (!r.ok) throw new Error(DATA.targets); return r.json(); }),
    fetch(DATA.info).then(r => (r.ok ? r.json() : {})).catch(() => ({})),
  ]);
  state.sites = parseCSV(csv).map(r => ({ ...r, name: r.SITE, lat: r.LAT, lng: r.LON }));
  state.targets = Object.fromEntries(Object.entries(targets).filter(([k]) => !k.startsWith('_')));
  state.info = info;
  state.targetKey = Object.keys(state.targets)[0];
}

/* ---------- Scoring ---------- */

// Similarity = 1 − mean absolute difference to the lunar target, over criteria with data.
function scoreSite(site, target) {
  const diffs = [];
  for (const c of CRITERIA) {
    const s = site[c.key], t = target[c.key];
    if (s == null || t == null) continue;
    diffs.push({ ...c, site: s, target: t, diff: Math.abs(s - t), signed: s - t });
  }
  const sim = diffs.length ? 1 - diffs.reduce((a, d) => a + d.diff, 0) / diffs.length : null;
  return { sim, diffs, coverage: diffs.length };
}

function ranked() {
  const target = state.targets[state.targetKey];
  return state.sites
    .map(s => ({ ...s, ...scoreSite(s, target), type: state.info[s.SITE]?.type ?? 'candidate' }))
    .sort((a, b) => (b.sim ?? -1) - (a.sim ?? -1))
    .map((s, i) => ({ ...s, rank: i + 1 }));
}

/* ---------- Helpers ---------- */

const esc = s => String(s ?? '').replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
const pct = v => (v == null ? '–' : Math.round(v * 100) + '%');
const fmtCoord = (lat, lng) => `${Math.abs(lat).toFixed(2)}°${lat >= 0 ? 'N' : 'S'}, ${Math.abs(lng).toFixed(2)}°${lng >= 0 ? 'E' : 'W'}`;
// Text still to research is written in [brackets]: show it highlighted.
const research = s => esc(s).replace(/\[([^\]]+)\]/g, '<span class="todo">[$1]</span>');

/* ---------- Site list ---------- */

function renderList() {
  const list = document.getElementById('siteList');
  const rows = ranked().filter(s => state.filter === 'all' || s.type === state.filter);
  list.innerHTML = rows.map(s => `
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
    </li>`).join('');
  list.querySelectorAll('.site-btn').forEach(b => b.addEventListener('click', () => select(b.dataset.site, true)));
}

/* ---------- Radar chart (SVG, no library) ---------- */

function radarSVG(diffsByKey, site, target) {
  const W = 460, H = 330, cx = W / 2, cy = H / 2 + 4, R = 112, n = CRITERIA.length;
  const ang = i => (-90 + (360 / n) * i) * Math.PI / 180;
  const pt = (i, v) => [cx + Math.cos(ang(i)) * R * v, cy + Math.sin(ang(i)) * R * v];
  const poly = vals => vals.map((v, i) => (v == null ? null : pt(i, v).map(x => x.toFixed(1)).join(','))).filter(Boolean).join(' ');

  const rings = [0.25, 0.5, 0.75, 1].map(f =>
    `<polygon points="${CRITERIA.map((_, i) => pt(i, f).join(',')).join(' ')}" fill="none" stroke="#2A3342" stroke-width="1"></polygon>`).join('');
  const axes = CRITERIA.map((c, i) => {
    const [x, y] = pt(i, 1);
    const missing = site[c.key] == null;
    return `<line x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="#2A3342" ${missing ? 'stroke-dasharray="3 4"' : ''}></line>`;
  }).join('');
  const labels = CRITERIA.map((c, i) => {
    const [x, y] = pt(i, 1.17);
    const cos = Math.cos(ang(i));
    const anchor = Math.abs(cos) < 0.2 ? 'middle' : cos > 0 ? 'start' : 'end';
    const missing = site[c.key] == null;
    const note = missing ? `<tspan x="${x.toFixed(1)}" dy="14" font-size="10.5">no data</tspan>` : '';
    return `<text x="${x.toFixed(1)}" y="${(y + 4).toFixed(1)}" text-anchor="${anchor}" font-size="11.5" fill="${missing ? '#8B95A3' : '#E6EAF0'}">${esc(c.label)}${note}</text>`;
  }).join('');
  const sitePts = CRITERIA.map(c => site[c.key]);
  const tgtPts = CRITERIA.map(c => target[c.key]);
  const dots = sitePts.map((v, i) => (v == null ? '' : `<circle cx="${pt(i, v)[0].toFixed(1)}" cy="${pt(i, v)[1].toFixed(1)}" r="3.5" fill="${COLORS.earth}"></circle>`)).join('');

  return `<svg class="radar" viewBox="0 0 ${W} ${H}" role="img" aria-label="Radar chart: ${esc(site.SITE)} compared with the lunar target on ${n} criteria">
    ${rings}${axes}
    <polygon points="${poly(tgtPts)}" fill="rgba(232,227,211,0.06)" stroke="${COLORS.moon}" stroke-width="2" stroke-dasharray="6 4"></polygon>
    <polygon points="${poly(sitePts)}" fill="rgba(108,180,238,0.25)" stroke="${COLORS.earth}" stroke-width="2.5"></polygon>
    ${dots}${labels}
  </svg>`;
}

/* ---------- Analog card ---------- */

function renderCard() {
  const el = document.getElementById('card');
  const s = ranked().find(r => r.SITE === state.selected);
  if (!s) { el.innerHTML = '<p class="hint">Pick a site from the list or the globe.</p>'; return; }
  const target = state.targets[state.targetKey];
  const info = state.info[s.SITE] ?? {};
  const byClosest = [...s.diffs].sort((a, b) => a.diff - b.diff);
  const strengths = byClosest.slice(0, 3);
  const gaps = byClosest.slice().reverse().filter(d => d.diff >= 0.15).slice(0, 3);
  const missing = CRITERIA.filter(c => s[c.key] == null).map(c => c.label);

  el.innerHTML = `
    <div class="card-top">
      <div class="card-title">
        <span class="badge ${s.type === 'known' ? 'badge-known' : 'badge-new'}">${s.type === 'known' ? 'Known analog' : 'New candidate'}</span>
        <h2 style="margin-top:8px">${esc(s.SITE)}</h2>
        <p class="card-place">${esc(info.place ?? '')}${info.place ? ' · ' : ''}${fmtCoord(s.lat, s.lng)}</p>
      </div>
      <div class="score">
        <strong>${pct(s.sim)}</strong>
        <span>similar · rank ${s.rank} of ${state.sites.length}</span>
      </div>
    </div>

    ${info.why ? `<p class="why">${research(info.why)}</p>` : ''}

    <div class="radar-box">
      <h3>Terrain and light fingerprint</h3>
      ${radarSVG(s.diffs, s, target)}
      <div class="radar-legend">
        <span><span class="swatch" style="border-color:${COLORS.earth}"></span>${esc(s.SITE)}</span>
        <span><span class="swatch" style="border-color:${COLORS.moon};border-top-style:dashed"></span>${esc(target.label ?? 'Lunar target')}</span>
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
      <h3>How it helps exploration</h3>
      <p>${info.helps ? research(info.helps) : '<span class="todo">[to research]</span>'}</p>
    </div>`;
}

/* ---------- Globe ---------- */

function hasWebGL() {
  try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')); } catch { return false; }
}

// FAKE heatmap: blobs around dry, polar and deep-valley regions, only to design the layer.
// Replace with a grid of real suitability scores (lat, lng, weight) from the pipeline.
function fakeHeatPoints() {
  let seed = 7;
  const rand = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const gauss = () => Math.sqrt(-2 * Math.log(rand() + 1e-9)) * Math.cos(2 * Math.PI * rand());
  const blobs = [
    [75.4, -89.7, 1.0, 2.0], [78.5, 16, 0.8, 1.5], [60, 8.5, 0.6, 1.5], [46.2, 8.2, 0.5, 1.0],
    [65, -16, 0.6, 1.5], [28.8, 83.8, 0.9, 1.5], [32, 85, 0.7, 3.0], [-23.8, -69, 0.8, 1.5],
    [-77.6, 162, 1.0, 2.0], [37.4, -3, 0.5, 1.0], [-20, -67.5, 0.6, 1.5], [24, 12, 0.4, 4.0],
  ];
  const pts = [];
  for (const [lat, lng, w, spread] of blobs) {
    for (let i = 0; i < 60; i++) pts.push({ lat: lat + gauss() * spread * 0.6, lng: lng + gauss() * spread, weight: w * (0.4 + 0.6 * rand()) });
  }
  return pts;
}

function initGlobe() {
  const el = document.getElementById('globe');
  if (!hasWebGL() || typeof Globe !== 'function') { document.getElementById('globeError').hidden = false; return; }
  const heat = fakeHeatPoints();
  document.getElementById('heatNote').textContent = DATA.isFake ? 'Fake pattern, for design only' : '';

  const g = Globe()(el)
    .globeImageUrl('https://unpkg.com/three-globe@2.31.0/example/img/earth-blue-marble.jpg')
    .bumpImageUrl('https://unpkg.com/three-globe@2.31.0/example/img/earth-topology.png')
    .backgroundColor('#05070B')
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
    .labelsData(state.sites)
    .labelLat('lat')
    .labelLng('lng')
    .labelText('SITE')
    .labelSize(d => (d.SITE === state.selected ? 1.8 : 1.1))
    .labelDotRadius(d => (d.SITE === state.selected ? 0.8 : 0.5))
    .labelColor(d => (d.SITE === state.selected ? '#FFFFFF' : (state.info[d.SITE]?.type === 'known' ? COLORS.known : COLORS.newSite)))
    .labelAltitude(0.07)
    .labelResolution(2)
    .onLabelClick(d => select(d.SITE, true))
    .ringsData([])
    .ringColor(() => t => `rgba(255,255,255,${1 - t})`)
    .ringMaxRadius(4)
    .ringPropagationSpeed(2)
    .ringRepeatPeriod(1200)
    .ringAltitude(0.07);

  g.controls().autoRotate = true;
  g.controls().autoRotateSpeed = 0.35;
  g.pointOfView({ lat: 35, lng: 10, altitude: 2.3 });

  const fit = () => g.width(el.clientWidth).height(el.clientHeight);
  new ResizeObserver(fit).observe(el);
  fit();

  document.getElementById('heatToggle').addEventListener('change', e => g.heatmapsData(e.target.checked ? [{ points: heat }] : []));
  document.getElementById('spinToggle').addEventListener('change', e => { g.controls().autoRotate = e.target.checked; });
  state.globe = g;
}

function updateGlobe(fly) {
  const g = state.globe;
  if (!g) return;
  const s = state.sites.find(x => x.SITE === state.selected);
  g.labelsData([...state.sites]); // re-evaluate label styles
  g.ringsData(s ? [{ lat: s.lat, lng: s.lng }] : []);
  if (s && fly) {
    g.controls().autoRotate = false;
    document.getElementById('spinToggle').checked = false;
    g.pointOfView({ lat: s.lat, lng: s.lng, altitude: 1.4 }, 1200);
  }
}

/* ---------- Wiring ---------- */

function select(site, fly) {
  state.selected = site;
  renderList();
  renderCard();
  updateGlobe(fly);
}

function initControls() {
  const sel = document.getElementById('targetSelect');
  sel.innerHTML = Object.entries(state.targets).map(([k, t]) => `<option value="${esc(k)}">${esc(t.label ?? k)}</option>`).join('');
  sel.addEventListener('change', () => { state.targetKey = sel.value; renderList(); renderCard(); });
  document.querySelectorAll('.seg button').forEach(b => b.addEventListener('click', () => {
    state.filter = b.dataset.filter;
    document.querySelectorAll('.seg button').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
    renderList();
  }));
  document.getElementById('dataBadge').hidden = !DATA.isFake;
  document.getElementById('footNote').textContent = DATA.isFake ? 'Showing sample files with fake values' : 'Showing pipeline outputs';
}

(async function main() {
  try {
    await loadAll();
  } catch (err) {
    document.getElementById('card').innerHTML = `<p class="hint">Could not load ${esc(err.message)}. Open the app through a web server (for example <code>python -m http.server</code> in the repo root), not by double-clicking the file.</p>`;
    return;
  }
  initControls();
  state.selected = ranked()[0]?.SITE ?? null;
  renderList();
  renderCard();
  initGlobe();
  updateGlobe(false);
})();
