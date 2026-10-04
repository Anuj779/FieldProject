// Native scroll reveals: no scroll listeners or additional animation dependencies.
(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const watched = new WeakSet();
  const running = new Map();
  const selector = '.hero-copy > *, .hero-art, .use-strip, .section-title, .steps article, .faq > div:first-child, .faq-list details, .auth-intro > *, .auth-panel, .workspace-header, .upload-panel, .upload-aside, .result-heading, .result-stats, .finding, footer';
  const observer = new IntersectionObserver(entries => {
    entries.forEach(({target, isIntersecting}) => {
      if (!isIntersecting || reduced.matches || target.getBoundingClientRect().height === 0) return;
      running.get(target)?.cancel();
      const side = target.matches('.hero-art, .auth-panel, .upload-aside, .faq-list details') ? 1 : -1;
      const distance = innerWidth < 768 ? 22 : 65;
      const order = [...target.parentElement.children].indexOf(target) % 4;
      const animation = target.animate([
        {opacity: 0, transform: `translate3d(${side * distance}px, 32px, 0) scale(.97)`},
        {opacity: 1, transform: 'translate3d(0, 0, 0) scale(1)'}
      ], {duration: 850, delay: order * 65, easing: 'cubic-bezier(.16,1,.3,1)', fill: 'backwards'});
      running.set(target, animation);
      animation.onfinish = () => running.delete(target);
    });
  }, {threshold: .12, rootMargin: '0px 0px -25px 0px'});

  const refresh = () => document.querySelectorAll(selector).forEach(node => {
    if (!watched.has(node)) { watched.add(node); observer.observe(node); }
  });
  window.ClauseMotion = {refresh};
  document.addEventListener('DOMContentLoaded', refresh);
  reduced.addEventListener('change', () => {
    if (reduced.matches) { running.forEach(animation => animation.finish()); running.clear(); }
  });
  window.addEventListener('pagehide', () => { running.forEach(animation => animation.cancel()); running.clear(); });
})();
