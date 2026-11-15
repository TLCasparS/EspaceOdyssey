/* Moon Twins on Earth: opening screen.
 * A full-screen Earthrise photo (Apollo 8, NASA) with the title. Scrolling down fades the photo and the title
 * out while the app (globes, list, cards) comes up underneath. Reduced motion: it fades without moving.
 */
(function initHero() {
  const hero = document.getElementById('hero');
  if (!hero) return;
  const bg = hero.querySelector('.hero-bg');
  const text = hero.querySelector('.hero-text');
  const credit = hero.querySelector('.hero-credit');
  const go = hero.querySelector('.hero-go');
  const still = matchMedia('(prefers-reduced-motion: reduce)');
  let queued = false;

  function paint() {
    queued = false;
    const h = hero.offsetHeight || innerHeight;
    const p = Math.min(1, Math.max(0, scrollY / (h * 0.85)));   // 0 at the top, 1 once the hero is mostly gone
    bg.style.opacity = String(1 - p);
    text.style.opacity = String(Math.max(0, 1 - p * 1.8));
    credit.style.opacity = go.style.opacity = String(Math.max(0, 1 - p * 3));
    if (still.matches) { bg.style.transform = ''; text.style.transform = ''; return; }
    bg.style.transform = `scale(${1 + 0.08 * p})`;
    text.style.transform = `translateY(${-60 * p}px)`;
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
