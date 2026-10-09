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
  const revealReport = section => {
    if (reduced.matches) return;
    section.querySelectorAll('.result-heading h1, .result-filename, .result-stats, .finding-content > *').forEach((node, index) => {
      running.get(node)?.cancel();
      const animation = node.animate([
        {opacity: 0, transform: 'translateY(20px)', filter: 'blur(4px)'},
        {opacity: 1, transform: 'translateY(0)', filter: 'blur(0)'}
      ], {duration: 700, delay: Math.min(index * 65, 850), easing: 'cubic-bezier(.16,1,.3,1)', fill: 'backwards'});
      running.set(node, animation);
      animation.onfinish = () => running.delete(node);
    });
  };
  window.ClauseMotion = {refresh, revealReport};
  const nav = document.querySelector('.nav');
  nav?.addEventListener('pointermove', event => {
    if (reduced.matches || event.pointerType === 'touch') return;
    const rect = nav.getBoundingClientRect();
    nav.style.setProperty('--nav-x', `${event.clientX - rect.left}px`);
    nav.style.setProperty('--nav-y', `${event.clientY - rect.top}px`);
  }, {passive: true});
  document.addEventListener('DOMContentLoaded', refresh);
  reduced.addEventListener('change', () => {
    if (reduced.matches) { running.forEach(animation => animation.finish()); running.clear(); }
  });
  window.addEventListener('pagehide', () => { running.forEach(animation => animation.cancel()); running.clear(); });
})();
