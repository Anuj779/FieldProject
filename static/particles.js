// Cursor-reactive crimson field, drawn behind content with no framework dependency.
(() => {
  const canvas = document.getElementById('particle-field');
  const ctx = canvas?.getContext('2d', {alpha: true});
  if (!ctx) return;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const fine = matchMedia('(pointer: fine)');
  let width = 0, height = 0, points = [], frame = 0, last = 0;
  const pointer = {x: -1000, y: -1000, tx: -1000, ty: -1000, active: false};
  function resize() {
    width = innerWidth; height = innerHeight;
    const ratio = Math.min(devicePixelRatio || 1, 1.5);
    canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    const spacing = fine.matches ? 44 : 70;
    points = [];
    for (let y = 12; y < height; y += spacing) {
      for (let x = 12; x < width; x += spacing) {
        points.push({x: x + (Math.random() - .5) * 16, y: y + (Math.random() - .5) * 16, ox: 0, oy: 0, vx: 0, vy: 0, phase: Math.random() * Math.PI * 2});
      }
    }
    draw(0, 1);
  }
  function draw(time, dt) {
    ctx.clearRect(0, 0, width, height);
    const moving = !reduced.matches;
    const follow = 1 - Math.exp(-dt * .13);
    pointer.x += (pointer.tx - pointer.x) * follow;
    pointer.y += (pointer.ty - pointer.y) * follow;
    for (const p of points) {
      const dx = p.x - pointer.x, dy = p.y - pointer.y;
      const distance = Math.hypot(dx, dy);
      const influence = moving && pointer.active ? Math.max(0, 1 - distance / 220) : 0;
      const angle = Math.atan2(dy, dx) + influence * .65;
      const force = influence * influence * 70;
      const steps = Math.max(1, Math.ceil(dt / .5)), step = dt / steps;
      for (let i = 0; i < steps; i++) {
        p.vx = (p.vx + (Math.cos(angle) * force - p.ox) * .018 * step) * Math.pow(.88, step);
        p.vy = (p.vy + (Math.sin(angle) * force - p.oy) * .018 * step) * Math.pow(.88, step);
        p.ox += p.vx * step; p.oy += p.vy * step;
      }
      const wave = moving ? Math.sin(time * .0005 + p.phase) : 0;
      const x = p.x + p.ox, y = p.y + p.oy + wave * 3;
      const length = 1.1 + influence * 6;
      ctx.strokeStyle = `rgba(${influence > .3 ? '255,100,120' : '239,35,60'},${.13 + influence * .65})`;
      ctx.lineWidth = 1.25 + influence;
      ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(x, y);
      ctx.lineTo(x + Math.cos(angle + wave * .2) * length, y + Math.sin(angle + wave * .2) * length);
      ctx.stroke();
    }
  }
  function tick(time) {
    if (document.hidden || reduced.matches || !fine.matches) { frame = 0; return; }
    const dt = Math.min((time - last) / 16.67 || 1, 2); last = time;
    draw(time, dt); frame = requestAnimationFrame(tick);
  }
  function sync() {
    cancelAnimationFrame(frame); frame = 0; last = 0;
    if (!document.hidden && !reduced.matches && fine.matches) frame = requestAnimationFrame(tick);
    else { pointer.active = false; points.forEach(p => { p.ox = p.oy = p.vx = p.vy = 0; }); draw(0, 1); }
  }
  addEventListener('pointermove', e => {
    if (e.pointerType === 'touch') return;
    if (!pointer.active) { pointer.x = e.clientX; pointer.y = e.clientY; }
    pointer.tx = e.clientX; pointer.ty = e.clientY; pointer.active = true;
  }, {passive: true});
  document.addEventListener('pointerleave', () => { pointer.active = false; });
  addEventListener('blur', () => { pointer.active = false; });
  addEventListener('resize', resize, {passive: true});
  document.addEventListener('visibilitychange', sync);
  reduced.addEventListener('change', sync); fine.addEventListener('change', () => { resize(); sync(); });
  addEventListener('pagehide', () => cancelAnimationFrame(frame));
  addEventListener('pageshow', sync);
  resize(); sync();
})();
