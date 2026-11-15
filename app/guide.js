/* Astronaut guide: a scripted helper (no AI, no server). Three parts:
 *   Tour  – five steps through the page: globe → list → card → Moon → honest limits.
 *   Words – "What does this mean?" for each criterion of the selected lunar base, written from our criteria doc
 *           (docs/Moon Analog Criteria and Datasets.md), plus the Moon value from outputs/targets.json.
 *   Ask   – ready-made questions; answers are fixed text or computed from the loaded data (never invented).
 * Loaded after app.js and uses its globals (state, ranked, meta, select, ...). Delete this file and its <script>
 * tag to remove the guide; nothing else depends on it. The astronaut is a simple drawing made in code. */

const GUIDE_WORDS = {
  SUNNY_RIDGE: 'How much sun the best spot on the rim gets over a year, compared with flat open land. Shackleton’s rim has spots in sunlight most of the time: good for solar power.',
  DARK_FLOOR: 'How much of the crater floor stays in shadow. Shackleton’s floor never sees the Sun, so it can trap water ice.',
  LIGHT_NEAR_DARK: 'How far the darkest floor spot is from the sunniest rim spot, in crater radii. Close together means power and ice within driving reach.',
  GRAZING_SUN: 'How high the Sun climbs over the year. At Shackleton it stays within about 2° of the horizon; on Earth it reaches at least 23.4°, even at the poles. No place on Earth can match, so it is shown but not scored.',
  SKY_VIEW: 'How much open sky the crater floor can see. Less sky means deeper, longer shadow.',
  CLEAR_SKIES: 'How often the sky is free of clouds: hard, direct light like on the airless Moon.',
  BOWL_SHAPE: 'Is it a closed, deep bowl? Measured as depth divided by width.',
  CRATER_SIZE: 'Width and depth compared with Shackleton (20.9 km wide). Earth craters in our results are far smaller, so this is shown, not scored.',
  RELIEF: 'Height from the rim down to the floor. It depends on the crater’s size, so it is shown but not scored.',
  SLOPE_BASE: 'Slope of the flattest spot about 200 m wide just outside the bowl: where a crew could land and build.',
  STEEP_WALLS: 'Average slope of the crater’s inner walls. Steep walls are what keep the floor in shadow.',
  DRIVABLE: 'Share of the ground within about 5 km gentle enough for a rover to drive on.',
  ROUGHNESS: 'How bumpy the ground is around the crater. Rough ground is harder to drive and land on.',
  ASPECT: 'Share of steep slopes facing the pole, which hold shadow. Shown only: Shackleton sits almost on the pole, so “towards the pole” points a different way for each part of its wall.',
  COLD: 'How cold the ground gets. Shadowed lunar floors are colder than anywhere on Earth.',
  DAY_NIGHT_SWING: 'Difference between day and night ground temperature. On the lunar mare it is roughly 290–300 K.',
  DRY: 'How little rain falls: the Moon has no liquid water and no weathering by rain.',
  GROUND_ICE: 'Share of the crater floor covered by snow or ice (from ESA WorldCover).',
  BARE: 'Share of the ground with no plants, like the Moon.',
  FINE_SURFACE: 'How much fine, loose soil there is, like the Moon’s dusty regolith.',
  NIGHT_DARK: 'How dark the night is, with no artificial light.',
  HIGHLAND_ROCK: 'Rock similar to the pale highland rock (anorthosite) of the lunar poles.',
  BASALT: 'Dark volcanic rock (basalt), like the lunar maria.',
  IMPACT_CRATER: 'Is it a confirmed impact crater, made like the Moon’s craters? Many bowls on Earth are volcanic instead.',
  CAVE: 'Known lava tubes or skylights, like the pits seen on the Moon.',
};
const GUIDE_TERMS = [
  ['Similarity %', 'How close a site is to the lunar base, from 0 to 100%. It is the weighted average of the criteria that count; 100% would be identical to the Moon on every one.'],
  ['Fingerprint (radar)', 'One axis per criterion. The outer ring is the Moon; the closer the site’s shape gets to it, the more Moon-like it is on that axis.'],
  ['Tuning site', 'A region we used to check and set up our method (Meteor Crater, El Pinacate). Its high rank is partly built in, so it does not count as an independent result.'],
  ['Maar', 'A volcanic crater made by steam explosions when magma meets groundwater. It can look like an impact crater but formed differently.'],
  ['Spill depth', 'How deep a bowl is up to the lowest point of its rim, where water would overflow. Our search needs at least 50 m.'],
  ['Our data', 'A value measured by our own pipeline from elevation data, not taken from a publication.'],
];

const guide = { open: false, tab: 'tour', step: 0, answer: null };
const GUIDE_TOUR = [
  { sel: '.globe-wrap', title: '1 · The Earth',
    text: 'This globe shows where our search found Moon-like places: warmer heatmap colours are better matches, and the outlines are the regions we searched. Drag to turn it; click a dot to open that site.' },
  { sel: '.list-panel', title: '2 · The Earth twins',
    text: 'The ranking: every crater our pipeline scored, ordered by how similar it is to the lunar base you picked. “Tuning” marks the regions we used to set up our method.' },
  { sel: '.card-panel', title: '3 · The site card',
    text: 'Everything about the selected site: its fingerprint against the Moon, what is closest and what it lacks, where the analogy breaks, and its opportunities and challenges, each with a source.' },
  { sel: '.moon-wrap', title: '4 · The Moon',
    text: 'Pick the lunar base you want to rehearse. Shackleton crater at the south pole is measured from NASA’s LOLA elevation data with the same code we run on Earth.' },
  { sel: () => document.querySelector('.missed-btn')?.parentElement ?? document.querySelector('.card-panel'), title: '5 · Honest limits',
    text: 'No place on Earth is a perfect twin: here the Sun always climbs higher than at the lunar pole, and Earth has air, weather and full gravity. We also show a real crater our method missed, and why.' },
];

const ASTRONAUT_SVG = `<svg viewBox="0 0 64 64" aria-hidden="true" focusable="false">
  <circle cx="32" cy="34" r="26" fill="#12293B"/>
  <path d="M14 60c0-12 8-19 18-19s18 7 18 19z" fill="#E8E3D3"/>
  <rect x="25" y="46" width="14" height="8" rx="2" fill="#A7BAC7"/>
  <circle cx="32" cy="28" r="15" fill="#E8E3D3"/>
  <rect x="21" y="20" width="22" height="15" rx="7.5" fill="#134257"/>
  <path d="M25 24c3-2 8-2 11 0" stroke="#7FDCCD" stroke-width="2" fill="none" stroke-linecap="round"/>
  <circle cx="47" cy="28" r="2.5" fill="#3CC8B4"/>
</svg>`;

/* ---------- Answers, computed from the loaded data ---------- */

const scoredSites = () => ranked().filter(s => s.sim != null);
const showBtn = s => `<button type="button" class="guide-link" data-guide-site="${esc(s.SITE)}">Show ${esc(nameOf(s))}</button>`;
const pctOf = v => `${Math.round(v * 100)}%`;

const GUIDE_QUESTIONS = [
  { q: 'Which site is the closest twin?', a: () => {
    const all = scoredSites();
    if (!all.length) return '<p>No site has a score yet.</p>';
    const fair = all.filter(s => !isTuning(s));
    const top = all[0], best = fair[0];
    let html = `<p>For the ${esc(baseLabel().toLowerCase())} base, the highest score is <b>${esc(nameOf(top))}</b> (${pctOf(top.sim)}).</p>`;
    if (best && best.SITE !== top.SITE) html += `<p>But ${esc(nameOf(top))} is a tuning site. The best independent result is <b>${esc(nameOf(best))}</b> (${pctOf(best.sim)}, rank ${best.rank} of ${all.length}).</p>`;
    return html + `<p>${showBtn(best ?? top)}</p>`;
  } },
  { q: 'Which site is best for testing rovers?', a: () => {
    const all = scoredSites().filter(s => s.DRIVABLE != null);
    if (!all.length) return '<p>No site has a drivable-ground value yet.</p>';
    const drive = [...all].sort((a, b) => b.DRIVABLE - a.DRIVABLE)[0];
    const rough = all.filter(s => s.raw?.ROUGHNESS != null).sort((a, b) => a.raw.ROUGHNESS - b.raw.ROUGHNESS)[0];
    let html = `<p>Most drivable ground within about 5 km: <b>${esc(nameOf(drive))}</b> (${(Math.round(drive.DRIVABLE * 1000) / 10)}%).`;
    if (rough) html += ` Smoothest ground around the crater: <b>${esc(nameOf(rough))}</b> (roughness ${Math.round(rough.raw.ROUGHNESS)} m, Shackleton ${fmtVal(meta('ROUGHNESS')?.moon, 'm')}).`;
    html += '</p><p class="guide-note">Our data only sees slopes and bumps in elevation maps. It does not know about rocks, loose sand or permits: check “Opportunities &amp; challenges” on the card.</p>';
    return html + `<p>${showBtn(drive)}${rough && rough.SITE !== drive.SITE ? ' ' + showBtn(rough) : ''}</p>`;
  } },
  { q: 'Which site is easiest to reach?', a: () => {
    // Access (c26, docs/ACCESS.md): modelled travel time to the nearest city + nearest airport. Display only.
    // Only places of the selected base (the night export mixes Polar and Mare rows).
    const sameBase = s => s.BASE_TYPE == null || s.BASE_TYPE === state.base;
    const scored = scoredSites().filter(sameBase);
    const hasH = s => accessOf(s)?.ACCESS_HOURS != null;
    const all = scored.filter(hasH);
    if (!all.length) return '<p>No site has travel-time data yet.</p>';
    const hrs = s => accessOf(s).ACCESS_HOURS;
    const byHours = list => [...list].sort((a, b) => hrs(a) - hrs(b))[0];
    const line = s => {
      const a = accessOf(s);
      return `<b>${esc(nameOf(s))}</b> (${pctOf(s.sim)} similar): ${fmtTravel(a.ACCESS_HOURS)} to the nearest city` +
        (a.AIRPORT_KM != null ? `, ${Math.round(a.AIRPORT_KM).toLocaleString('en')} km to ${esc(a.AIRPORT_NAME ?? 'an airport')}` : '');
    };
    const TOP = 10, many = scored.length > TOP;
    // With many places the quickest one overall is often a weak twin, so lead with the best ten.
    const topQuick = many ? byHours(scored.slice(0, TOP).filter(hasH)) : null;
    const quickest = byHours(all);
    const air = all.filter(s => accessOf(s).AIRPORT_KM != null).sort((a, b) => accessOf(a).AIRPORT_KM - accessOf(b).AIRPORT_KM)[0];
    let html = '';
    if (topQuick) html += `<p>Among the ${TOP} closest twins, the easiest to reach is ${line(topQuick)}.</p>`;
    if (!topQuick || topQuick.SITE !== quickest.SITE)
      html += `<p>${many ? `Of all ${all.length.toLocaleString('en')} places, the quickest` : 'Quickest'} to reach: ${line(quickest)}.</p>`;
    if (air && air.SITE !== quickest.SITE && air.SITE !== topQuick?.SITE) html += `<p>Closest to an airport: ${line(air)}.</p>`;
    const btns = [topQuick, quickest, air].filter((s, i, arr) => s && arr.findIndex(x => x?.SITE === s.SITE) === i);
    return html + `<p class="guide-note">Travel time is a model over roads of 2015 to the nearest city (Weiss et al. 2018); the airport is a straight-line distance and says nothing about flights. It also ignores permits and land owners: see “Opportunities &amp; challenges” on the card.</p>
      <p>${btns.map(showBtn).join(' ')}</p>`;
  } },
  { q: 'Why is no Earth place a perfect match?', a: () => {
    const all = scoredSites();
    const widest = all.filter(s => s.raw?.CRATER_DIAMETER_EQUIV_M != null).sort((a, b) => b.raw.CRATER_DIAMETER_EQUIV_M - a.raw.CRATER_DIAMETER_EQUIV_M)[0];
    return `<ul class="guide-list">
      <li><b>Light:</b> at Shackleton the Sun stays within about 2° of the horizon; anywhere on Earth it climbs to at least 23.4°. So no Earth crater gets the Moon’s long, low light.</li>
      ${widest ? `<li><b>Size:</b> the widest crater in our results, ${esc(nameOf(widest))}, is about ${(widest.raw.CRATER_DIAMETER_EQUIV_M / 1000).toFixed(1)} km across; Shackleton is 20.9 km.</li>` : ''}
      <li><b>The planet itself:</b> Earth has air, weather and full gravity, and shields us from radiation. No place on Earth can reproduce the lunar vacuum, low gravity or radiation.</li>
    </ul><p class="guide-note">That is why every card has a “Where the analogy breaks down” box.</p>`;
  } },
  { q: 'How is the score made?', a: () => {
    const n = similarityCriteria().length;
    return `<p>For the ${esc(baseLabel().toLowerCase())} base, ${n} criteria count. For each one, our pipeline measures the Earth site and the Moon with the same code and turns the difference into a 0–100% similarity. The score is their weighted average.</p>
      <p class="guide-note">Some criteria are shown but not scored, for example when no place on Earth can match (Grazing sun) or when the value depends on size (Relief).</p>`;
  } },
  { q: 'What is a tuning site?', a: () => `<p>${esc(TUNING_NOTE)}</p>` },
  { q: 'Did the method miss any real crater?', a: () => {
    const missed = state.sites.filter(s => state.info[s.SITE]?.type === 'missed');
    if (!missed.length) return '<p>No missed crater is listed in this data.</p>';
    return missed.map(s => `<p><b>${esc(nameOf(s))}:</b> ${research(state.info[s.SITE].breaks ?? '')}</p><p>${showBtn(s)}</p>`).join('');
  } },
  { q: 'What can I do in the 3D view?', a: () => `<p>Pick a site and press <b>Fly into 3D terrain</b>. Drag to look around, use <b>2D</b> to look straight down, and <b>Moon colours</b> to see the ground in grey like the Moon.</p>
      <p><b>Moon base to scale</b> draws a habitat and a landing pad at their real sizes, and Shackleton’s rim around the crater: you can see how small an Earth crater is next to it.</p>` },
];

/* ---------- Rendering ---------- */

function guideBodyHTML() {
  if (guide.tab === 'tour') {
    const st = GUIDE_TOUR[guide.step];
    return `<p class="guide-step">${esc(st.title)}</p><p>${esc(st.text)}</p>
      <div class="guide-nav">
        <button type="button" class="guide-btn" data-guide-nav="-1" ${guide.step === 0 ? 'disabled' : ''}>Back</button>
        <span class="guide-dots" aria-hidden="true">${GUIDE_TOUR.map((_, i) => `<i class="${i === guide.step ? 'on' : ''}"></i>`).join('')}</span>
        ${guide.step < GUIDE_TOUR.length - 1
          ? '<button type="button" class="guide-btn primary" data-guide-nav="1">Next</button>'
          : '<button type="button" class="guide-btn primary" data-guide-tab="ask">Ask me</button>'}
      </div>`;
  }
  if (guide.tab === 'words') {
    const crit = [...baseCriteria(), ...groundCriteria()].filter(c => GUIDE_WORDS[c.key]);
    const item = (title, text, extra = '') => `<details class="guide-word"><summary>${esc(title)}</summary><p>${esc(text)}</p>${extra}</details>`;
    return `<p class="guide-note">Criteria for the ${esc(baseLabel().toLowerCase())} base, then a few words from the app.</p>
      ${crit.map(c => {
        const m = meta(c.key);
        const moon = m?.moon != null && !m.kind ? `<p class="guide-note">Moon (${esc(moonBase(state.base)?.name ?? 'target')}): ${esc(fmtVal(m.moon, m.earthUnit))} · ${m.counts ? 'counts in the score' : 'shown, not scored'}</p>` : '';
        return item(c.label, GUIDE_WORDS[c.key], moon);
      }).join('')}
      ${GUIDE_TERMS.map(([t, d]) => item(t, d)).join('')}`;
  }
  const qa = guide.answer != null ? GUIDE_QUESTIONS[guide.answer] : null;
  return qa ? `<p class="guide-step">${esc(qa.q)}</p>${qa.a()}
      <p><button type="button" class="guide-btn" data-guide-back>Other questions</button></p>`
    : `<ul class="guide-qs">${GUIDE_QUESTIONS.map((x, i) => `<li><button type="button" class="guide-q" data-guide-q="${i}">${esc(x.q)}</button></li>`).join('')}</ul>`;
}

function renderGuide() {
  const panel = document.getElementById('guidePanel');
  panel.hidden = !guide.open;
  document.getElementById('guideBtn').setAttribute('aria-expanded', String(guide.open));
  document.querySelectorAll('.guide-spot').forEach(el => el.classList.remove('guide-spot'));
  if (!guide.open) return;
  panel.querySelectorAll('[data-guide-tab]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.guideTab === guide.tab)));
  document.getElementById('guideBody').innerHTML = guideBodyHTML();
  if (guide.tab === 'tour') {
    const st = GUIDE_TOUR[guide.step];
    const el = typeof st.sel === 'function' ? st.sel() : document.querySelector(st.sel);
    if (el) { el.classList.add('guide-spot'); el.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'center' }); }
  }
}

function initGuide() {
  const wrap = document.createElement('div');
  wrap.className = 'guide';
  wrap.innerHTML = `
    <div id="guidePanel" class="guide-panel" role="dialog" aria-label="Astronaut guide" hidden>
      <div class="guide-head">
        <span class="guide-face">${ASTRONAUT_SVG}</span>
        <div><b>Your field guide</b><span>Pre-written answers, no AI</span></div>
        <button type="button" class="guide-close" data-guide-close aria-label="Close the guide">×</button>
      </div>
      <div class="guide-tabs" role="group" aria-label="Guide sections">
        <button type="button" data-guide-tab="tour">Tour</button>
        <button type="button" data-guide-tab="words">What does it mean?</button>
        <button type="button" data-guide-tab="ask">Ask</button>
      </div>
      <div id="guideBody" class="guide-body"></div>
    </div>
    <button type="button" id="guideBtn" class="guide-btn-float" aria-expanded="false" aria-controls="guidePanel">
      <span class="guide-face">${ASTRONAUT_SVG}</span><span class="guide-btn-text">Guide</span>
    </button>`;
  document.body.append(wrap);

  // First visit: a gentle pulse on the button (remembered in this browser only; works without storage too).
  let seen = false;
  try { seen = localStorage.getItem('eo-guide-seen') === '1'; } catch {}
  if (!seen) document.getElementById('guideBtn').classList.add('is-new');

  wrap.addEventListener('click', e => {
    const t = e.target.closest('button');
    if (!t) return;
    if (t.id === 'guideBtn') {
      guide.open = !guide.open;
      t.classList.remove('is-new');
      try { localStorage.setItem('eo-guide-seen', '1'); } catch {}
    } else if (t.dataset.guideClose != null) guide.open = false;
    else if (t.dataset.guideTab) { guide.tab = t.dataset.guideTab; guide.answer = null; }
    else if (t.dataset.guideNav) guide.step = Math.max(0, Math.min(GUIDE_TOUR.length - 1, guide.step + Number(t.dataset.guideNav)));
    else if (t.dataset.guideQ) guide.answer = Number(t.dataset.guideQ);
    else if (t.dataset.guideBack != null) guide.answer = null;
    else if (t.dataset.guideSite) {
      select(t.dataset.guideSite, false);
      document.querySelector('.card-panel')?.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' });
      return;
    } else return;
    renderGuide();
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && guide.open) { guide.open = false; renderGuide(); } });
}

// Wait until app.js has loaded the data (the card shows a site), then add the guide.
(function startGuide(tries = 0) {
  if (typeof state !== 'undefined' && state.sites?.length && document.getElementById('card')?.children.length) return initGuide();
  if (tries < 120) setTimeout(() => startGuide(tries + 1), 250);
})();
