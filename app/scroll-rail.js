/* Moon Twins on Earth: page scroll rail.
 * The globes, the Moon and the 3D view catch the mouse wheel (it zooms them), so on a big screen it can be hard to
 * scroll the page. This small bar sits at the right edge, above everything else:
 *  - wheel over it: the page scrolls (the bar never zooms anything);
 *  - drag it up or down: the page follows, like a scrollbar;
 *  - click a dash: jump to that part of the page (the long, bright dash is where you are).
 * It is its own element, so it never changes how the globes, list or cards behave. Loaded last.
 */
(function initScrollRail() {
  const SECTIONS = [
    { sel: '#hero', label: 'Start' },
    { sel: '#app', label: 'Map' },
    { sel: '.card-panel', label: 'Site card' },
    { sel: '#findings', label: 'What we found' },
    { sel: '.footer', label: 'Sources' },
  ].map(s => ({ ...s, el: document.querySelector(s.sel) })).filter(s => s.el);
  if (SECTIONS.length < 2) return;

  const still = matchMedia('(prefers-reduced-motion: reduce)');
  const rail = document.createElement('nav');
  rail.className = 'scroll-rail';
  rail.setAttribute('aria-label', 'Page sections');
  rail.innerHTML = SECTIONS.map((s, i) =>
    `<button type="button" class="rail-dash" data-rail="${i}" aria-label="Go to: ${s.label}"><span class="rail-label">${s.label}</span></button>`
  ).join('');
  document.body.appendChild(rail);
  const dashes = [...rail.querySelectorAll('.rail-dash')];

  // Where you are: the last visible part whose top has passed 40% of the window.
  let queued = false;
  function paint() {
    queued = false;
    const line = innerHeight * 0.4;
    let active = 0;
    SECTIONS.forEach((s, i) => {
      const off = s.el.hidden || s.el.getClientRects().length === 0;
      dashes[i].hidden = off;
      if (!off && s.el.getBoundingClientRect().top <= line) active = i;
    });
    // At the very bottom the last part is "here", even when it is too short to reach the line.
    if (innerHeight + scrollY >= document.documentElement.scrollHeight - 2) {
      for (let i = SECTIONS.length - 1; i >= 0; i--) if (!dashes[i].hidden) { active = i; break; }
    }
    dashes.forEach((d, i) => {
      d.classList.toggle('is-here', i === active);
      if (i === active) d.setAttribute('aria-current', 'location'); else d.removeAttribute('aria-current');
    });
  }
  const queue = () => { if (!queued) { queued = true; requestAnimationFrame(paint); } };
  addEventListener('scroll', queue, { passive: true });
  addEventListener('resize', queue);
  // Parts of the page appear later (cards, findings): keep the dashes in step.
  new MutationObserver(queue).observe(document.body, { subtree: true, attributes: true, attributeFilter: ['hidden'] });
  paint();

  // Wheel over the bar: always the page. (Done by hand so nothing under the bar can take it.)
  rail.addEventListener('wheel', e => {
    e.preventDefault();
    const unit = e.deltaMode === 1 ? 40 : e.deltaMode === 2 ? innerHeight : 1;
    scrollBy({ top: e.deltaY * unit, behavior: 'auto' });
  }, { passive: false });

  // Drag: the page moves like a scrollbar (the whole page fits in the window's height).
  let drag = null;
  rail.addEventListener('pointerdown', e => {
    if (e.button !== 0) return;
    drag = { y: e.clientY, top: scrollY, moved: false, id: e.pointerId };
  });
  rail.addEventListener('pointermove', e => {
    if (!drag || e.pointerId !== drag.id) return;
    const dy = e.clientY - drag.y;
    if (!drag.moved && Math.abs(dy) < 4) return;
    if (!drag.moved) { drag.moved = true; rail.setPointerCapture(e.pointerId); rail.classList.add('is-dragging'); }
    const ratio = document.documentElement.scrollHeight / innerHeight;
    scrollTo({ top: drag.top + dy * ratio, behavior: 'auto' });
  });
  const endDrag = e => {
    if (!drag || e.pointerId !== drag.id) return;
    if (drag.moved) { rail.classList.remove('is-dragging'); rail.dataset.justDragged = '1'; setTimeout(() => delete rail.dataset.justDragged, 0); }
    drag = null;
  };
  rail.addEventListener('pointerup', endDrag);
  rail.addEventListener('pointercancel', endDrag);

  // Click a dash: go to that part.
  rail.addEventListener('click', e => {
    const dash = e.target.closest('.rail-dash');
    if (!dash || rail.dataset.justDragged) return;
    const s = SECTIONS[+dash.dataset.rail];
    const behavior = still.matches ? 'auto' : 'smooth';
    if (s.sel === '#hero') scrollTo({ top: 0, behavior });
    else s.el.scrollIntoView({ behavior, block: 'start' });
  });
})();
