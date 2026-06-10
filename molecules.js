(function () {
  const COUNT  = 16;
  const W_MOL  = 230;   // element width px
  const RADIUS = 56;    // collision radius px
  const COLOR  = 'rgba(35,15,120,0.08)';

  const SVG = `<svg viewBox="0 0 200 130" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
    <!-- Benzene ring -->
    <polygon points="68,48 87,59 87,81 68,92 49,81 49,59"/>
    <!-- Benzene double bonds: top-right, bottom-right, left edges (inner parallel, offset toward center 68,70) -->
    <line x1="68" y1="52" x2="84" y2="61" stroke-width="1.8"/>
    <line x1="84" y1="79" x2="68" y2="88" stroke-width="1.8"/>
    <line x1="52" y1="79" x2="52" y2="61" stroke-width="1.8"/>
    <!-- Pyrrole ring -->
    <polygon points="87,59 108,52 121,70 108,88 87,81"/>
    <!-- Pyrrole C2=C3 double bond (inner parallel, offset toward ring center 102,70) -->
    <line x1="107" y1="55" x2="117" y2="70" stroke-width="1.8"/>
    <!-- N-H bond stub and label -->
    <line x1="108" y1="88" x2="110" y2="101"/>
    <text x="110" y="112" font-size="9" text-anchor="middle" fill="currentColor" stroke="none" font-family="ui-monospace,monospace">H</text>
    <text x="115" y="90" font-size="9" text-anchor="start" fill="currentColor" stroke="none" font-family="ui-monospace,monospace">N</text>
    <!-- 5-OH substituent -->
    <line x1="49" y1="81" x2="31" y2="81"/>
    <text x="21" y="85" font-size="9" text-anchor="middle" fill="currentColor" stroke="none" font-family="ui-monospace,monospace">HO</text>
    <!-- Ethylamine side chain: C3 → CH2 → CH2 → NH2 -->
    <line x1="108" y1="52" x2="128" y2="38"/>
    <line x1="128" y1="38" x2="150" y2="44"/>
    <line x1="150" y1="44" x2="168" y2="30"/>
    <text x="170" y="29" font-size="9" text-anchor="start" fill="currentColor" stroke="none" font-family="ui-monospace,monospace">NH2</text>
  </svg>`;

  const layer = document.createElement('div');
  layer.className = 'mol-layer';
  layer.setAttribute('aria-hidden', 'true');
  document.body.prepend(layer);

  const particles = [];

  for (let i = 0; i < COUNT; i++) {
    const el = document.createElement('div');
    el.style.cssText = `position:absolute;left:0;top:0;width:${W_MOL}px;color:${COLOR};pointer-events:none;will-change:transform;`;
    el.innerHTML = SVG;
    layer.appendChild(el);

    const speed = 10 + Math.random() * 16;
    const dir   = Math.random() * Math.PI * 2;

    particles.push({
      el,
      x:  RADIUS + Math.random() * (window.innerWidth  - RADIUS * 2),
      y:  RADIUS + Math.random() * (window.innerHeight - RADIUS * 2),
      vx: Math.cos(dir) * speed,
      vy: Math.sin(dir) * speed,
      angle: Math.random() * 360,
      va: (Math.random() - 0.5) * 24,
    });
  }

  const MAX_SPEED = 100;
  const MAX_SPIN  = 50;
  let last = null;

  function tick(ts) {
    if (!last) { last = ts; requestAnimationFrame(tick); return; }
    const dt = Math.min((ts - last) / 1000, 0.05);
    last = ts;

    const VW = window.innerWidth;
    const VH = window.innerHeight;

    // Integrate
    for (const p of particles) {
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.angle += p.va * dt;

      // Wall bounce
      if (p.x < RADIUS)       { p.x = RADIUS;       p.vx =  Math.abs(p.vx); }
      if (p.x > VW - RADIUS)  { p.x = VW - RADIUS;  p.vx = -Math.abs(p.vx); }
      if (p.y < RADIUS)       { p.y = RADIUS;        p.vy =  Math.abs(p.vy); }
      if (p.y > VH - RADIUS)  { p.y = VH - RADIUS;  p.vy = -Math.abs(p.vy); }
    }

    // Elastic collisions (equal mass)
    const minD = RADIUS * 2;
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const a = particles[i], b = particles[j];
        const dx = b.x - a.x, dy = b.y - a.y;
        const d2 = dx * dx + dy * dy;
        if (d2 >= minD * minD || d2 === 0) continue;

        const d  = Math.sqrt(d2);
        const nx = dx / d, ny = dy / d;

        // Push apart
        const push = (minD - d) * 0.5;
        a.x -= nx * push; a.y -= ny * push;
        b.x += nx * push; b.y += ny * push;

        // Exchange velocity along normal
        const rel = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny;
        if (rel < 0) {
          a.vx += rel * nx; a.vy += rel * ny;
          b.vx -= rel * nx; b.vy -= rel * ny;
          // Spin kick on impact
          a.va = Math.max(-MAX_SPIN, Math.min(MAX_SPIN, a.va - rel * 0.25));
          b.va = Math.max(-MAX_SPIN, Math.min(MAX_SPIN, b.va + rel * 0.25));
        }
      }
    }

    // Render + speed clamp
    for (const p of particles) {
      const spd = Math.sqrt(p.vx * p.vx + p.vy * p.vy);
      if (spd > MAX_SPEED) { p.vx = p.vx / spd * MAX_SPEED; p.vy = p.vy / spd * MAX_SPEED; }
      p.el.style.transform = `translate(${p.x - W_MOL / 2}px,${p.y - W_MOL / 2}px) rotate(${p.angle}deg)`;
    }

    requestAnimationFrame(tick);
  }

  requestAnimationFrame(tick);
}());
