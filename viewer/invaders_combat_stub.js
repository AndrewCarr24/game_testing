import * as THREE from 'three';

// A minimal window.__combat (prompts/wave2.md "Combat contract") for the invaders to code against
// until the weapons workstream's viewer/combat.js is merged. Installed only when nothing else
// has set window.__combat; thrown away at merge. It does just enough: targets, a hitscan shot
// (walls = window.__colliders, then targets as upright cylinders), a melee sweep, events, the
// player's health (regenerates out of combat) and a plain death screen with a restart button.

export function installCombatStub({ player, camera, colliders, harmless = false }) {
  const subs = new Map(), targets = new Set();
  const emit = (ev, e) => { for (const fn of subs.get(ev) ?? []) fn(e); };
  const ray = new THREE.Ray(), hit = new THREE.Vector3();
  const P = {
    id: 'player', kind: 'player', team: 'player', position: () => player.pos,
    radius: 0.3, get height() { return player.crouching ? 1.1 : 1.8; },
    health: 100, maxHealth: 100, alive: true, lastHit: -1e9,
    hit(damage, info = {}) {
      if (!this.alive || harmless || window.__bench || !(damage > 0)) return;
      this.health = Math.max(0, this.health - damage);
      this.lastHit = performance.now() / 1000;
      flash(Math.min(1, damage / 40));
      if (this.health <= 0) { this.alive = false; emit('playerDown', { target: this, ...info }); deathScreen(); }
    },
  };
  // a vertical cylinder (feet at p, radius r, height h) hit by the ray within maxD: distance or -1
  const cyl = (o, d, p, r, h, maxD) => {
    const ox = o.x - p.x, oz = o.z - p.z, a = d.x * d.x + d.z * d.z;
    if (a < 1e-9) return -1;
    const b = 2 * (ox * d.x + oz * d.z), c = ox * ox + oz * oz - r * r, disc = b * b - 4 * a * c;
    if (disc < 0) return -1;
    const t = (-b - Math.sqrt(disc)) / (2 * a);
    if (t < 0 || t > maxD) return -1;
    const y = o.y + d.y * t;
    return y >= p.y && y <= p.y + h ? t : -1;
  };
  const wallDist = (o, d, maxD) => {
    ray.set(o, d);
    let best = maxD;
    for (const c of colliders) {
      if (c.isEmpty() || c.rail || c.seeThrough || c.max.y < -50 || c.containsPoint(o)) continue;
      if (ray.intersectBox(c, hit)) { const t = hit.distanceTo(o); if (t < best) best = t; }
    }
    return best;
  };
  const C = {
    stub: true, player: P, targets,
    register(t) { targets.add(t); return t; },
    unregister(t) { targets.delete(t); },
    on(ev, fn) { if (!subs.has(ev)) subs.set(ev, new Set()); subs.get(ev).add(fn); return () => subs.get(ev).delete(fn); },
    emit,
    shoot({ from, origin, dir, spread = 0, range = 50, damage = 30, weapon = 'gun' }) {
      const d = dir.clone().normalize();
      if (spread) d.add(new THREE.Vector3().randomDirection().multiplyScalar(spread)).normalize();
      const wall = wallDist(origin, d, range);
      let best = null, bt = wall;
      for (const t of [P, ...targets]) {
        if (t === from || !t.alive || (from && t.team === from.team)) continue;
        if (t === P && player.hidden) continue;
        const td = cyl(origin, d, t.position(), t.radius ?? 0.3, t.height ?? 1.8, bt);
        if (td >= 0 && td < bt) { bt = td; best = t; }
      }
      const point = origin.clone().addScaledVector(d, bt);
      const res = { target: best, point, distance: bt, miss: !best };
      emit('shot', { from, origin, dir: d, point, target: best, weapon });
      if (best) { best.hit(damage, { from, dir: d, weapon, part: 'body' }); emit('hit', { target: best, from, damage, weapon }); if (!best.alive) emit('kill', { target: best, from, weapon }); }
      return res;
    },
    attack({ from, origin, dir, weapon = 'melee', range = 1.6, arc = 1.2, damage = 35, blocked = null }) {
      const hits = [];
      const f = new THREE.Vector3(dir.x, 0, dir.z).normalize();
      for (const t of [P, ...targets]) {
        if (t === from || !t.alive || (from && t.team === from.team)) continue;
        if (t === P && player.hidden) continue;
        const p = t.position(), dx = p.x - origin.x, dz = p.z - origin.z, dist = Math.hypot(dx, dz);
        if (dist > range + (t.radius ?? 0.3) || p.y > origin.y + 0.6 || p.y + (t.height ?? 1.8) < origin.y - 1.2) continue;
        const ang = Math.acos(Math.max(-1, Math.min(1, (dx * f.x + dz * f.z) / Math.max(dist, 1e-4))));
        if (dist > 0.5 && ang > arc * 0.6) continue;
        const aim = new THREE.Vector3(p.x, p.y + 1.1, p.z);
        if (blocked?.(aim)) continue;
        t.hit(damage, { from, dir: f, weapon, part: 'body' });
        hits.push({ target: t, point: aim });
        emit('hit', { target: t, from, damage, weapon });
        if (!t.alive) emit('kill', { target: t, from, weapon });
      }
      return hits;
    },
    update(dt) {
      // regenerates slowly out of combat (6 s since the last hit)
      if (P.alive && P.health < P.maxHealth && performance.now() / 1000 - P.lastHit > 6) P.health = Math.min(P.maxHealth, P.health + 4 * dt);
    },
  };
  // the HUD bits (made here, not in index.html: the stub goes away at merge)
  const red = document.createElement('div');
  red.style.cssText = 'position:absolute;inset:0;pointer-events:none;background:radial-gradient(ellipse at center, rgba(160,0,0,0) 45%, rgba(160,0,0,.75));opacity:0;transition:opacity .35s';
  document.body.appendChild(red);
  let fadeT = null;
  function flash(k) { red.style.transition = 'none'; red.style.opacity = String(0.35 + 0.65 * k); clearTimeout(fadeT); fadeT = setTimeout(() => { red.style.transition = 'opacity .8s'; red.style.opacity = String(Math.max(0, 1 - P.health / 100) * 0.5); }, 60); }
  function deathScreen() {
    const d = document.createElement('div');
    d.id = 'death';
    d.style.cssText = 'position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;background:rgba(0,0,0,0);transition:background 2s;color:#ddd;font:20px system-ui;z-index:20';
    d.innerHTML = '<div style="opacity:0;transition:opacity 2s 1s;letter-spacing:.3em">YOU DIED</div><button style="opacity:0;transition:opacity 1s 2s;font:15px system-ui;padding:8px 18px;border-radius:6px;border:1px solid #888;background:#222;color:#eee;cursor:pointer">Restart</button>';
    document.body.appendChild(d);
    document.exitPointerLock?.();
    requestAnimationFrame(() => { d.style.background = 'rgba(0,0,0,.92)'; for (const c of d.children) c.style.opacity = '1'; });
    d.querySelector('button').onclick = () => location.reload();
  }
  let last = performance.now();
  (function tick() { const now = performance.now(); C.update(Math.min(0.1, (now - last) / 1000)); last = now; requestAnimationFrame(tick); })();
  window.__combat = C;
  return C;
}
