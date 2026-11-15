/* "What we found": two pictures of the night run at the top of the page (Polar base, Shackleton).
 * 1. Funnel: from every grid cell searched to the ranked Earth twins. Numbers are computed here from
 *    outputs/coverage.json (cells per status) and outputs/scores.csv (EXCLUDED, RANK), never typed in.
 * 2. Terrain vs light: one dot per ranked Polar place (TERRAIN_SCORE, LIGHT_SCORE). Click a dot to open its card.
 * Plain SVG/HTML, no library. Uses app.js globals (state, OUT, DATA, select, setBase, renderList, nameOf, esc).
 * Hidden when the data has no TERRAIN_SCORE / LIGHT_SCORE (sample data, first-run export).
 */

const findings = { coverage: null, open: true };
const fmtN = n => Math.round(n).toLocaleString('en');
const pct0 = v => `${Math.round(v * 100)}%`;

// Ranked Polar places with both part-scores (excluded places have no RANK).
const polarRanked = () => state.sites.filter(s => s.BASE_TYPE === 'polar' && s.RANK != null && !s.EXCLUDED
  && s.TERRAIN_SCORE != null && s.LIGHT_SCORE != null);

/* ---------- Funnel ---------- */

function funnelSteps() {
  const cov = findings.coverage;
  if (!Array.isArray(cov)) return null;
  const t = {};
  let tiles = 0;
  cov.forEach(tile => {
    const p = tile.polar; if (!p) return;
    if (p.searched) tiles++;
    Object.entries(p).forEach(([k, v]) => { t[k] = (t[k] ?? 0) + v; });
  });
  if (!t.searched) return null;
  const polar = state.sites.filter(s => s.BASE_TYPE === 'polar' && s.SCORE_TOTAL != null);
  const ex = r => polar.filter(s => (s.EXCLUDED ?? '').includes(r)).length;
  const mines = ex('mine');
  const notDry = polar.filter(s => (s.EXCLUDED ?? '').includes('not a dry') && !(s.EXCLUDED ?? '').includes('mine')).length;
  const ranked = polar.filter(s => s.RANK != null && !s.EXCLUDED).length;
  const scored = polar.length;
  const land = (t.prefilter ?? 0) + (t.filtered ?? 0);
  const noBowl = (t.dropped ?? 0) + (t.no_bowl ?? 0);
  const other = (t.ice_floor ?? 0) + (t.duplicate ?? 0);
  // Remaining after each step; the steps add up to the cells searched (coverage.json).
  return [
    { left: t.searched, head: 'grid cells searched', text: `About 15 × 15 km each, in ${fmtN(tiles)} one-degree land tiles, deserts first, in one night.`, kind: 'start' },
    { left: t.searched - land, cut: land, head: 'ruled out by land cover', text: 'Mostly water, forest, fields or towns (ESA WorldCover).' },
    { left: t.searched - land - noBowl, cut: noBowl, head: 'no crater-like bowl', text: 'No closed bowl at least 50 m deep and 1 km wide (Copernicus elevation, 90 m then 30 m).' },
    { left: scored, cut: other, head: 'ice-filled or found twice', text: `Floor full of ice (${fmtN(t.ice_floor ?? 0)}) or the same bowl in two runs (${fmtN(t.duplicate ?? 0)}).`, small: true },
    { left: scored, head: 'crater-like places scored', text: 'Each one measured against Shackleton with the same code as the Moon.', kind: 'mid' },
    { left: scored - mines, cut: mines, head: 'open-pit mines', text: 'Inside a mapped mining area (Maus et al. 2022). Our bowl finder is good enough to find mines.', kind: 'mine' },
    { left: scored - mines - notDry, cut: notDry, head: 'not a dry bowl', text: 'Plants, ice or water in the bowl: not Moon-like ground.' },
    { left: ranked, head: 'Earth twins of Shackleton, ranked', text: 'The list, the globe and the cards below.', kind: 'end' },
  ];
}

function renderFunnel() {
  const el = document.getElementById('funnel');
  const steps = funnelSteps();
  if (!steps) { el.hidden = true; return; }
  el.hidden = false;
  const max = Math.log10(steps[0].left);
  // Bar width on a log scale: 265,000 and 1,261 both stay visible.
  const w = n => `${Math.max(2, (Math.log10(Math.max(1, n)) / max) * 100).toFixed(1)}%`;
  el.innerHTML = `<figcaption><h3>From ${fmtN(steps[0].left)} cells to ${fmtN(steps.at(-1).left)} twins</h3>
      <p class="find-sub">Polar base · how the search narrowed down</p></figcaption>
    <ol class="funnel">${steps.filter(s => !s.small || s.cut).map(s => s.cut != null ? `
      <li class="fn-cut${s.kind === 'mine' ? ' is-mine' : ''}${s.small ? ' is-small' : ''}">
        ${s.kind === 'mine' ? `<button type="button" class="fn-link" data-funnel="mines" title="Show the excluded places in the list">` : '<span>'}
          <b>− ${fmtN(s.cut)}</b> ${esc(s.head)}${s.kind === 'mine' ? ' <span aria-hidden="true">→</span>' : ''}
        ${s.kind === 'mine' ? '</button>' : '</span>'}
        <span class="fn-text">${esc(s.text)}</span>
      </li>` : `
      <li class="fn-stage fn-${s.kind}">
        <span class="fn-bar"><span style="width:${w(s.left)}"></span></span>
        <span class="fn-num">${fmtN(s.left)}</span>
        <span class="fn-head">${esc(s.head)}</span>
        <span class="fn-text">${esc(s.text)}</span>
      </li>`).join('')}
    </ol>
    <p class="find-note">Bars use a log scale. Counts from <code>coverage.json</code> and <code>scores.csv</code>.</p>`;
  el.querySelector('[data-funnel="mines"]')?.addEventListener('click', showExcluded);
}

// The mines row opens the folded "Excluded after scoring" box in the list: a demo moment.
function showExcluded() {
  if (state.base !== 'polar' && typeof setBase === 'function') setBase('polar', false);
  state.excludedOpen = true;
  renderList();
  const box = document.querySelector('.excluded-ref');
  if (!box) return;
  box.querySelector('details').open = true;
  // The list scrolls inside its own panel: an instant jump reaches both the panel and the page
  // (a smooth scroll stops at the outer one).
  box.scrollIntoView({ block: 'start' });
  document.querySelector('.list-panel')?.scrollIntoView({ block: 'start' });
}

/* ---------- Terrain vs light scatter ---------- */

const SC = { w: 540, h: 400, l: 66, r: 20, t: 20, b: 60, hi: 0.6 };   // hi = "high on both" corner
function renderScatter() {
  const el = document.getElementById('scatter');
  const pts = polarRanked();
  if (!pts.length) { el.hidden = true; return; }
  el.hidden = false;
  const x = v => SC.l + v * (SC.w - SC.l - SC.r);
  const y = v => SC.h - SC.b - v * (SC.h - SC.t - SC.b);
  const both = pts.filter(s => s.TERRAIN_SCORE >= SC.hi && s.LIGHT_SCORE >= SC.hi).length;
  // Shallow bowls: bowl shape and wall steepness both ~0 % like the Moon, so only the flat spot matches.
  const shallowPts = pts.filter(s => s.BOWL_SHAPE != null && s.STEEP_WALLS != null && s.BOWL_SHAPE < 0.05 && s.STEEP_WALLS < 0.05);
  const shallowX = shallowPts.length ? shallowPts.reduce((a, s) => a + s.TERRAIN_SCORE, 0) / shallowPts.length : null;
  const top = [...pts].sort((a, b) => a.RANK - b.RANK).slice(0, 5);
  const meteor = pts.find(s => /meteor/i.test(s.SITE) || /meteor/i.test(s.NAME ?? ''));
  const marked = new Map(top.map(s => [s.SITE, String(s.RANK)]));
  if (meteor && !marked.has(meteor.SITE)) marked.set(meteor.SITE, 'M');
  const ticks = [0, 0.25, 0.5, 0.75, 1];
  const dot = s => {
    const m = marked.get(s.SITE);
    return `<circle class="sc-dot${m ? ' is-marked' : ''}${s.SITE === state.selected ? ' is-selected' : ''}" cx="${x(s.TERRAIN_SCORE).toFixed(1)}" cy="${y(s.LIGHT_SCORE).toFixed(1)}" r="${m ? 10 : 4}" data-site="${esc(s.SITE)}" tabindex="${m ? 0 : -1}">
      <title>${esc(nameOf(s))}: terrain ${pct0(s.TERRAIN_SCORE)}, light ${pct0(s.LIGHT_SCORE)}, rank ${s.RANK}</title></circle>`;
  };
  const caption = both === 0 ? 'No place on Earth scores high on both.' : `Only ${fmtN(both)} of ${fmtN(pts.length)} places score ${pct0(SC.hi)} or more on both.`;
  el.innerHTML = `<figcaption><h3>Terrain twins are not light twins</h3>
      <p class="find-sub">${fmtN(pts.length)} ranked Polar places · click a dot to open its card</p></figcaption>
    <svg viewBox="0 0 ${SC.w} ${SC.h}" class="scatter" role="img" aria-label="Scatter plot of terrain match against light match. ${esc(caption)}">
      <rect class="sc-corner" x="${x(SC.hi)}" y="${y(1)}" width="${x(1) - x(SC.hi)}" height="${y(SC.hi) - y(1)}"/>
      <text class="sc-corner-label" x="${(x(SC.hi) + x(1)) / 2}" y="${y(SC.hi) - 40}" text-anchor="middle">Good on both</text>
      <text class="sc-corner-label strong" x="${(x(SC.hi) + x(1)) / 2}" y="${y(SC.hi) - 14}" text-anchor="middle">${both === 0 ? 'empty' : `${fmtN(both)} place${both > 1 ? 's' : ''}`}</text>
      ${ticks.map(t => `<line class="sc-grid" x1="${x(t)}" x2="${x(t)}" y1="${y(0)}" y2="${y(1)}"/><line class="sc-grid" x1="${x(0)}" x2="${x(1)}" y1="${y(t)}" y2="${y(t)}"/>
        <text class="sc-tick" x="${x(t)}" y="${y(0) + 22}" text-anchor="middle">${pct0(t)}</text>
        <text class="sc-tick" x="${x(0) - 10}" y="${y(t) + 5}" text-anchor="end">${pct0(t)}</text>`).join('')}
      <text class="sc-axis" x="${(x(0) + x(1)) / 2}" y="${SC.h - 10}" text-anchor="middle">Terrain match (bowl, walls, flat spot, roughness) →</text>
      <text class="sc-axis" transform="translate(18 ${(y(0) + y(1)) / 2}) rotate(-90)" text-anchor="middle">Light match (sunny rim, dark floor) →</text>
      ${shallowPts.length > pts.length / 4 ? `<text class="sc-note" x="${x(shallowX) + 12}" y="${y(0.9)}">${fmtN(shallowPts.length)} shallow bowls:</text>
        <text class="sc-note" x="${x(shallowX) + 12}" y="${y(0.9) + 20}">only the flat spot matches</text>
        <line class="sc-note-line" x1="${x(shallowX) + 8}" y1="${y(0.9) - 5}" x2="${x(shallowX)}" y2="${y(0.72)}"/>` : ''}
      <g>${pts.filter(s => !marked.has(s.SITE)).map(dot).join('')}</g>
      <g>${pts.filter(s => marked.has(s.SITE)).map(dot).join('')}</g>
      ${[...marked].map(([site, m]) => { const s = pts.find(p => p.SITE === site);
        return `<text class="sc-mark" x="${x(s.TERRAIN_SCORE)}" y="${y(s.LIGHT_SCORE) + 5}" text-anchor="middle" pointer-events="none">${m}</text>`; }).join('')}
      <g class="sc-moon"><circle cx="${x(1)}" cy="${y(1)}" r="9"/><text x="${x(1) - 14}" y="${y(1) + 5}" text-anchor="end">Shackleton</text></g>
    </svg>
    <p class="sc-caption">${esc(caption)}</p>
    <p class="find-note">“High” = ${pct0(SC.hi)} or more on both parts of the score. Shackleton itself is 100% on both.${shallowPts.length ? ` ${fmtN(shallowPts.length)} places are shallow bowls whose shape and walls are far from Shackleton’s, so only their flat base spot matches.` : ''}</p>
    <ol class="sc-legend">${[...marked].map(([site, m]) => { const s = pts.find(p => p.SITE === site);
      return `<li><button type="button" data-site="${esc(site)}"><span class="sc-key">${m}</span>${esc(nameOf(s))} <span class="muted">· terrain ${pct0(s.TERRAIN_SCORE)}, light ${pct0(s.LIGHT_SCORE)}${m === 'M' ? `, rank ${s.RANK}` : ''}</span></button></li>`; }).join('')}</ol>`;
  el.querySelectorAll('[data-site]').forEach(n => {
    n.addEventListener('click', () => openFromFindings(n.dataset.site));
    n.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openFromFindings(n.dataset.site); } });
  });
}

function openFromFindings(site) {
  if (state.base !== 'polar' && typeof setBase === 'function') setBase('polar', false);
  select(site, false);
  renderScatter();   // highlight the chosen dot
  document.querySelector('.card-panel')?.scrollIntoView({ block: 'start', behavior: reducedMotion ? 'auto' : 'smooth' });
}

/* ---------- Start ---------- */

async function initFindings() {
  const sec = document.getElementById('findings');
  if (!sec || DATA.isFake || !polarRanked().length) return;   // nothing to show with sample / first-run data
  findings.coverage = await fetch(OUT + 'coverage.json').then(r => (r.ok ? r.json() : null)).catch(() => null);
  sec.hidden = false;
  const det = sec.querySelector('details');
  try { if (localStorage.getItem('eo-findings-open') === '0') det.open = false; } catch { /* storage blocked: stay open */ }
  det.addEventListener('toggle', () => { try { localStorage.setItem('eo-findings-open', det.open ? '1' : '0'); } catch { /* ignore */ } });
  renderFunnel();
  renderScatter();
}

(function startFindings(tries = 0) {
  if (typeof state !== 'undefined' && state.sites?.length && document.getElementById('card')?.children.length) return initFindings();
  if (tries < 120) setTimeout(() => startFindings(tries + 1), 250);
})();
