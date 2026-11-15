/* Moon Twins on Earth: opening screen.
 * A full-screen Earthrise photo (Apollo 8, NASA) with the title. The screen stays pinned while you scroll the first
 * part: the photo fades into the app's background colour while the title glides down to just above the app. Then
 * both scroll on together and the app (globes, list, cards) comes up. Reduced motion: fade only, nothing moves.
 */
(function initHero() {
  const hero = document.getElementById('hero');
  if (!hero) return;
  const stage = hero.querySelector('.hero-stage');
  const bg = hero.querySelector('.hero-bg');
  const text = hero.querySelector('.hero-text');
  const go = hero.querySelector('.hero-go');
  const credit = hero.querySelector('.hero-credit');
  const still = matchMedia('(prefers-reduced-motion: reduce)');
  let queued = false;
  const ease = t => t * t * (3 - 2 * t);   // smooth start and stop

  function paint() {
    queued = false;
    const pinned = Math.max(1, hero.offsetHeight - stage.offsetHeight);   // scroll distance while the stage is pinned
    const p = Math.min(1, Math.max(0, scrollY / pinned));                 // 0 at the top, 1 when the pin ends
    bg.style.opacity = String(1 - p);
    go.style.opacity = credit.style.opacity = String(Math.max(0, 1 - p * 3));
    go.style.pointerEvents = p > 0.3 ? 'none' : '';
    if (still.matches) { bg.style.transform = text.style.transform = ''; return; }
    bg.style.transform = `scale(${1 + 0.06 * p})`;
    // The title glides down as the photo fades, so it ends just above the app's header: no empty gap.
    const room = stage.offsetHeight - text.offsetTop - text.offsetHeight - 48;
    text.style.transform = `translateY(${Math.max(0, room) * ease(p)}px)`;
  }
  const onScroll = () => { if (!queued) { queued = true; requestAnimationFrame(paint); } };
  addEventListener('scroll', onScroll, { passive: true });
  addEventListener('resize', onScroll);
  paint();

  // "Explore the map": glide down to the app (instant with reduced motion).
  go.addEventListener('click', e => {
    const app = document.getElementById('app');
    if (!app) return;
    e.preventDefault();
    app.scrollIntoView({ behavior: still.matches ? 'auto' : 'smooth', block: 'start' });
  });
})();
