/* Moon Twins on Earth: definitions on the card chips.
 * Hover (or tab to) a chip such as "Steep walls" and a small box says what the word means; it goes away when
 * the mouse leaves. Only the card's chips have it (team request). Text follows docs/"Moon Analog Criteria and
 * Datasets.md" ("What we measure on Earth"), in plain words. Loaded after app.js (uses byKey and esc).
 */

const CRITERION_DEFS = {
  SUNNY_RIDGE: 'How much of the year the sunniest spot on the crater rim is in sunlight. On the Moon, sunny rims are where solar panels would stand.',
  DARK_FLOOR: 'How rarely the Sun reaches the crater floor. Shackleton’s floor is in permanent shadow, where ice can last.',
  LIGHT_NEAR_DARK: 'How close the sunniest rim spot is to the darkest floor spot, compared with the crater’s size: power and ice within driving reach.',
  GRAZING_SUN: 'How high the Sun climbs over the year. At the lunar south pole it stays just above the horizon; on Earth it always climbs much higher.',
  SKY_VIEW: 'How much open sky you see from the crater floor. Less sky means deeper, darker shadow.',
  CLEAR_SKIES: 'Share of the year without clouds. The Moon has no air, so its light is hard and direct.',
  BOWL_SHAPE: 'Whether the place is a closed, deep bowl: its depth compared with its width.',
  CRATER_SIZE: 'How close the crater’s width and depth are to Shackleton’s.',
  RELIEF: 'Rim-to-floor depth: how far the rim stands above the lowest point of the floor.',
  SLOPE_BASE: 'How flat the flattest spot of about 200 m is, just outside the bowl on its rim. A base needs flat ground to land and build.',
  STEEP_WALLS: 'How steep the crater’s inner walls are (mean slope, in degrees). Steep walls keep the floor in shadow, as at Shackleton.',
  DRIVABLE: 'Share of the ground around the base gentle enough for a rover to drive on.',
  ROUGHNESS: 'How bumpy the ground is: how much the height changes between neighbouring 60 m cells, over the bowl and its rim.',
  ASPECT: 'Share of the steep slopes that face the nearer pole. These slopes stay in shadow longest.',
  COLD: 'How cold the ground gets over the year, from satellite surface temperatures.',
  DAY_NIGHT_SWING: 'Difference between day and night ground temperature. On the Moon it swings by hundreds of degrees.',
  DRY: 'How little rain falls in a year. No water means no weathering, as on the Moon.',
  GROUND_ICE: 'Snow or ice cover on the crater floor.',
  BARE: 'Share of bare ground, with no plants.',
  FINE_SURFACE: 'Share of sand and silt in the topsoil, like the Moon’s fine, loose dust.',
  NIGHT_DARK: 'How dark the night is, with no artificial light nearby.',
  HIGHLAND_ROCK: 'Rock like the pale anorthosite of the lunar highlands, where Shackleton lies.',
  BASALT: 'Basalt or young lava: the dark volcanic rock of the lunar seas (maria).',
  IMPACT_CRATER: 'Whether the place is a confirmed crater made by a meteorite impact, like the Moon’s craters.',
  CAVE: 'Known lava tubes or skylights: possible shelters for a base.',
  ACCESS: 'Travel time from the place to the nearest city.',
  DARK_WHEN_REACHABLE: 'Whether the floor is in shadow during the months a field team can get there.',
  LINE_OF_SIGHT: 'How open the view is from the place, for radio contact.',
  STATION_NEARBY: 'Distance to the nearest research station that could support a team.',
};

(function initChipDefs() {
  const card = document.getElementById('card');
  if (!card) return;
  const tip = document.createElement('div');
  tip.className = 'def-tip';
  tip.id = 'defTip';
  tip.setAttribute('role', 'tooltip');
  tip.hidden = true;
  document.body.appendChild(tip);
  let current = null;

  function show(chip) {
    const key = chip.dataset.def;
    const text = CRITERION_DEFS[key];
    if (!text) return hide();
    const label = byKey[key]?.label ?? key;
    tip.innerHTML = `<b>${esc(label)}</b><span>${esc(text)}</span>${chip.dataset.match ? `<small>${esc(chip.dataset.match)}</small>` : ''}`;
    tip.hidden = false;
    current = chip;
    chip.setAttribute('aria-describedby', 'defTip');
    // Below the chip, or above it when there is no room; never past the window's edges.
    const r = chip.getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight, gap = 8;
    const left = Math.max(gap, Math.min(r.left + r.width / 2 - w / 2, innerWidth - w - gap));
    const top = r.bottom + gap + h <= innerHeight - gap ? r.bottom + gap : Math.max(gap, r.top - gap - h);
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
  }
  function hide() {
    tip.hidden = true;
    current?.removeAttribute('aria-describedby');
    current = null;
  }

  card.addEventListener('mouseover', e => {
    const chip = e.target.closest('[data-def]');
    if (chip && chip !== current) show(chip);
    else if (!chip && current) hide();
  });
  card.addEventListener('mouseleave', hide);
  card.addEventListener('focusin', e => { const chip = e.target.closest('[data-def]'); if (chip) show(chip); });
  card.addEventListener('focusout', hide);
  card.addEventListener('click', e => { if (!e.target.closest('[data-def]')) hide(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') hide(); });
  window.addEventListener('scroll', hide, true);   // the box is fixed, so it would drift off its chip
  window.addEventListener('resize', hide);
  // A new card replaces the chips: drop a box left from the old one.
  new MutationObserver(() => { if (current && !current.isConnected) hide(); }).observe(card, { childList: true });
})();
