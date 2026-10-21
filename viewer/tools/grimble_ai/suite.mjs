// Grimble AI suite: one page load (it breaks in at once), then the scenarios in scenarios.js run
// fast-forward (page.js: 6 substeps of 1/60 s per frame, seeded Math.random), each from a fresh
// placement with its memory wiped; metrics per scenario (sight through doors / glass, notice
// times, cheating, search after a loss, hearing, upstairs wait, prowl jams and room spread).
// Usage (from the project root): GT_BASE=http://localhost:8765 node viewer/tools/grimble_ai/suite.mjs <label> [names|all] [seed=1]
// Output: build/grimble_ai/<label>/<scenario>.json (log), photos from the player's eye, summary.txt
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
const HERE = path.dirname(new URL(import.meta.url).pathname);
const [label = 'x', names = 'all', seed = '1'] = process.argv.slice(2);
const out = `build/grimble_ai/${label}`;
fs.mkdirSync(out, { recursive: true });
const scSrc = fs.readFileSync(`${HERE}/scenarios.js`, 'utf8');
const pageSrc = fs.readFileSync(`${HERE}/page.js`, 'utf8');

fs.mkdirSync('build/locks', { recursive: true });
let slot = null;
while (slot === null) {
  for (let i = 0; i < 3 && slot === null; i++) { try { fs.mkdirSync(`build/locks/browser_${i}`); slot = i; } catch {} }
  if (slot === null) await new Promise((ok) => setTimeout(ok, 3000));
}
const release = () => { try { fs.rmdirSync(`build/locks/browser_${slot}`); } catch {} };
process.on('exit', release);
process.on('SIGINT', () => { release(); process.exit(1); });
process.on('uncaughtException', (e) => { console.error(e); release(); process.exit(1); });
process.on('unhandledRejection', (e) => { console.error(e); release(); process.exit(1); });

const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 960, height: 600 } });
p.on('pageerror', (e) => console.log('pageerror:', e.message));
p.on('console', (m) => { if (m.type() === 'error' || m.text().startsWith('[hunt]')) console.log('console:', m.text()); });
await p.addInitScript((seed) => {
  let a = seed >>> 0;
  Math.random = () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}, +seed * 7919 + 13);
await p.goto(`${process.env.GT_BASE || 'http://localhost:8765'}/viewer/index.html?level=mansion&gdelay=0&hunt=now&fx=0&pos=-18,1.65,3.5&look=-26,1.5,0${process.env.QS || ''}`);
await p.waitForFunction(() => window.__loaded && window.__grimble && window.__hunt, null, { timeout: 180000 });
await p.evaluate(`(${pageSrc})()`);
await p.waitForFunction(() => window.__grimble.state === 'inside' && window.__hunt.state !== 'smash' && window.__hunt.chain, null, { timeout: 120000, polling: 250 });
await p.evaluate(`window.__SC = ${scSrc}`);
const all = await p.evaluate(() => Object.keys(window.__SC));
const list = names === 'all' ? all : names.split(',');
const rooms = await p.evaluate(() => Object.fromEntries(Object.entries(window.__level.rooms).map(([k, r]) => [k, { rect: r.rect, floor: r.floor }])));
const roomOf = (x, z, y = 0) => { for (const [n, r] of Object.entries(rooms)) if (Math.abs(r.floor - (y > 3.5 ? 4.6 : 0)) < 0.5 && x >= r.rect[0] && x <= r.rect[2] && z >= r.rect[1] && z <= r.rect[3]) return n; return 'outside'; };
const D = (a, b, c, d) => Math.hypot(a - c, b - d);
const lines = [];
const say = (s) => { console.log(s); lines.push(s); };

async function shoot(name, view) {
  const v = await p.evaluate((view) => {
    const g = window.__grimble, h = window.__hunt, pl = window.__player;
    const hb = g.root.getObjectByName('Head'); const hv = hb.getWorldPosition(g.root.position.clone());
    if (view === 'eye') return { pos: [pl.pos.x, pl.pos.y + pl.eye, pl.pos.z], at: [hv.x, hv.y - 0.6, hv.z] };
    const c = h.chain, by = h.bodyYaw;
    let bx = c.b.x - Math.sin(by) * 3, bz = c.b.y - Math.cos(by) * 3;
    const k = h.nav.nearest(bx, bz, 6); if (k >= 0) { const cc = h.nav.centre(k); bx = cc.x; bz = cc.y; }
    return { pos: [bx, 3.9, bz], at: [c.hd.x + Math.sin(c.hf) * 2, 0.6, c.hd.y + Math.cos(c.hf) * 2] };
  }, view);
  await p.evaluate((v) => { window.__S.photo = v; }, v);
  await p.waitForTimeout(350);
  await p.screenshot({ path: `${out}/${name}.png` });
}

for (const name of list) {
  const t0 = Date.now();
  await p.evaluate((n) => window.__S.run(window.__SC[n]), name);
  for (;;) {
    await p.waitForTimeout(200);
    const st = await p.evaluate(() => ({ done: window.__S.done, want: window.__S.want, paused: window.__S.paused }));
    if (st.paused && st.want) {
      await shoot(`${name}_${st.want.name}`, st.want.view || 'eye');
      if (st.want.view !== 'eye') await shoot(`${name}_${st.want.name}_eye`, 'eye');
      await p.evaluate(() => { window.__S.want = null; window.__S.resume(); });
    }
    if (st.done) break;
    if (Date.now() - t0 > 600000) { console.log('timeout'); break; }
  }
  await shoot(`${name}_end_eye`, 'eye');
  const { log, events } = await p.evaluate(() => ({ log: window.__S.log, events: window.__S.events }));
  fs.writeFileSync(`${out}/${name}.json`, JSON.stringify({ log, events }));
  say(`== ${name} (${((Date.now() - t0) / 1000).toFixed(0)} s wall) ${metrics(name, log, events)}`);
}
fs.writeFileSync(`${out}/summary.txt`, lines.join('\n') + '\n');
await Promise.race([b.close(), new Promise((ok) => setTimeout(ok, 5000))]);
process.exit(0);

function metrics(name, L, E) {
  const ev = (lab) => E.find((e) => e.label === lab)?.t;
  const knock = L.filter((l, i) => l.down && !L[i - 1]?.down);
  const states = {}; for (const l of L) states[l.st + (l.sub ? '/' + l.sub : '')] = +((states[l.st + (l.sub ? '/' + l.sub : '')] || 0) + 0.1).toFixed(1);
  const firstSeen = L.find((l) => l.seen)?.t;
  const st = `states ${JSON.stringify(states)}`;
  const m = [];
  // generic: sight losses and refinds after the player stopped running
  const tStop = ev('tucked') ?? ev('hid') ?? ev('hidden') ?? ev('away');
  if (tStop !== undefined) {
    // last sighting before/after tStop
    const lossI = (() => { for (let i = L.length - 1; i >= 0; i--) if (L[i].t <= tStop + 0.05 && L[i].seen) return i; return 0; })();
    const loss = L[lossI];
    const refound = L.find((l) => l.t > tStop + 0.5 && l.seen);
    m.push(`lost at ${loss?.t} (ls ${JSON.stringify(loss?.ls)}), refound ${refound ? `after ${(refound.t - tStop).toFixed(1)} s` : 'never'}; knockdowns after hiding ${knock.filter((k) => k.t > tStop).length}`);
    // where it went after losing them: time within 8 m of the loss point in the next 60 / 180 s
    if (loss?.ls) {
      const [lx, lz] = loss.ls;
      let n60 = 0, n180 = 0, left = false, ret = null, giveUp = null;
      for (const l of L) {
        if (l.t < loss.t) continue;
        const d = D(l.x, l.z, lx, lz);
        if (d < 8) { if (l.t < loss.t + 60) n60 += 0.1; if (l.t < loss.t + 180) n180 += 0.1; }
        if (d > 15) left = true;
        if (left && ret == null && d < 5) ret = l.t - loss.t;
        if (giveUp == null && l.st === 'prowl') giveUp = l.t - loss.t;
      }
      m.push(`near loss point (8 m): ${n60.toFixed(0)} s of 60, ${n180.toFixed(0)} s of 180; returned after leaving: ${ret == null ? 'never' : ret.toFixed(0) + ' s'}; prowl after ${giveUp == null ? '-' : giveUp.toFixed(1) + ' s'}`);
    }
    // cheats: unseen + idle facing within 20 deg of the hidden player; lastSeen changes while unseen
    const un = L.filter((l) => l.t > tStop && !l.seen);
    const idle = un.filter((l) => l.anim === 'CrawlIdle');
    const face = idle.filter((l) => Math.abs(l.brg) < 0.35).length;
    let lsMoves = 0; for (let i = 1; i < L.length; i++) if (L[i].t > tStop && !L[i].seen && L[i].ls && L[i - 1].ls && D(...L[i].ls, ...L[i - 1].ls) > 0.3) lsMoves++;
    m.push(`unseen ${(un.length / 10).toFixed(1)} s, idle ${(idle.length / 10).toFixed(1)} s facing the hidden player ${idle.length ? Math.round(100 * face / idle.length) : 0}%; lastSeen moved while unseen ${lsMoves}x`);
  }
  if (name === 'lurk_cheat') {
    const t = ev('in cloak');
    const un = L.filter((l) => l.t > t && !l.seen && l.anim === 'CrawlIdle');
    const face = un.filter((l) => Math.abs(l.brg) < 0.35).length;
    m.push(`idle unseen ${(un.length / 10).toFixed(1)} s, facing the hidden player ${un.length ? Math.round(100 * face / un.length) : 0}%`);
  }
  if (/^(door_|glass|behind_far|behind_close|notice|crouch_island|hidden_plain)/.test(name)) m.push(`first noticed ${firstSeen === undefined ? 'never' : 't=' + firstSeen}`);
  if (name === 'den_swipe') m.push(`knockdowns with the player in the den ${knock.filter((k) => k.pz > 10.6).length}; first noticed in den ${L.find((l) => l.t > ev('in den') + 0.3 && l.seen)?.t ?? 'never'}`);
  const near = (x, z, r = 4) => L.find((l) => D(l.x, l.z, x, z) < r)?.t;
  if (name === 'two_noises') m.push(`reached A (-5.5,-15) ${near(-5.5, -15) ?? 'never'}, B (-11.75,8.75) ${near(-11.75, 8.75) ?? 'never'}`);
  if (name === 'lure_chase') { const tn = E.find((e) => /^noise/.test(e.label))?.t; m.push(`noise at ${tn}; reached it (4 m) ${near(-8, -15) ? (near(-8, -15) - tn).toFixed(1) + ' s later' : 'never'}; closest ${Math.min(...L.map((l) => D(l.x, l.z, -8, -15))).toFixed(1)} m`); }
  if (name === 'footsteps') { const moved = L.find((l) => ['chase', 'search', 'investigate'].includes(l.st) || (l.st === 'prowl' && l.anim !== 'CrawlIdle')); m.push(`reacted ${moved ? 't=' + moved.t + ' ' + moved.st : 'never'}; closest to player ${Math.min(...L.map((l) => D(l.x, l.z, l.px, l.pz))).toFixed(1)} m`); }
  if (name === 'muffled') { const moved = L.find((l) => l.t > 1.1 && (['chase', 'search', 'investigate'].includes(l.st) || (l.st === 'prowl' && l.anim !== 'CrawlIdle'))); m.push(`reacted ${moved ? 't=' + moved.t + ' ' + moved.st : 'never'}`); }
  if (name === 'loud_rush') { const t = near(-11.75, -8.75, 3); const moved = L.find((l) => l.t > 1.05 && l.anim !== 'CrawlIdle'); m.push(`started ${moved?.t ?? '-'} (${moved?.anim}), reached ${t ?? 'never'} (dist ${D(-20, 0, -11.75, -8.75).toFixed(1)} m straight); after: ${JSON.stringify(states)}`); }
  if (name === 'side_noise') { const atDoor = L.filter((l) => D(l.x, l.z, 12, -3.5) < 3.5); const facing = atDoor.filter((l) => Math.abs(Math.atan2(Math.sin(l.hf - Math.PI / 2), Math.cos(l.hf - Math.PI / 2))) < 0.6).length; m.push(`at the mudroom door ${(atDoor.length / 10).toFixed(1)} s (facing in ${(facing / 10).toFixed(1)} s); first there ${atDoor[0]?.t ?? 'never'}`); }
  if (name === 'upper') {
    const tb = ev('back from rail');
    if (tb !== undefined) {
      const after = L.filter((l) => l.t >= tb);
      const at = after[0];
      const nearRail = after.filter((l) => D(l.x, l.z, at.x, at.z) < 4);
      let leave = after.find((l) => D(l.x, l.z, at.x, at.z) > 6);
      const foot = after.find((l) => D(l.x, l.z, -6.3, 11.85) < 5);
      m.push(`knocked down at ${ev('down')}; after stepping back: within 4 m of where it stood ${(nearRail.length / 10).toFixed(0)} s, left after ${leave ? (leave.t - tb).toFixed(1) + ' s' : 'never'}; at the stair foot ${foot ? (foot.t - tb).toFixed(0) + ' s after' : 'never'}`);
    } else m.push('no knockdown');
  }
  if (name === 'prowl' || name === 'mudroom') {
    // futile: crawl anim, < 0.5 m progress over 3 s
    let fut = 0; const futAt = [];
    for (let i = 30; i < L.length; i++) if (/^Crawl(Fast)?$/.test(L[i].anim) && !['swipe', 'reachUp'].includes(L[i].st) && D(L[i].x, L[i].z, L[i - 30].x, L[i - 30].z) < 0.5) { fut += 0.1; if (!futAt.length || L[i].t - futAt[futAt.length - 1][1] > 1) futAt.push([L[i].t, L[i].t, L[i].x, L[i].z]); else futAt[futAt.length - 1][1] = L[i].t; }
    // rocking: crawl anim, within a 1.5 m circle for 10 s
    let rock = 0; for (let i = 100; i < L.length; i++) { const seg = L.slice(i - 100, i); if (seg.every((l) => /^Crawl/.test(l.anim) && l.anim !== 'CrawlIdle' || true) && seg.filter((l) => l.anim !== 'CrawlIdle').length > 80 && Math.max(...seg.map((l) => D(l.x, l.z, L[i].x, L[i].z))) < 1.5) rock += 0.1; }
    const snaps = L.filter((l) => Math.abs(l.dYaw) > 0.5).length, snaps2 = L.filter((l) => Math.abs(l.dYaw) > 0.8).length;
    let flick = 0; let lastSw = -1e9, lastA = null; for (const l of L) { if (lastA && l.anim !== lastA) { if (l.t - lastSw < 0.45) flick++; lastSw = l.t; } lastA = l.anim; }
    const dwell = {}; for (const l of L) { const r = roomOf(l.x, l.z); dwell[r] = (dwell[r] || 0) + 0.1; }
    const goals = []; for (const l of L) if (l.goal && (!goals.length || D(...goals[goals.length - 1], ...l.goal) > 1)) goals.push(l.goal);
    const gr = {}; for (const g2 of goals) { const r = roomOf(...g2); gr[r] = (gr[r] || 0) + 1; }
    const sp = []; for (let i = 10; i < L.length; i += 10) if (L[i].anim !== 'CrawlIdle') sp.push(D(L[i].x, L[i].z, L[i - 10].x, L[i - 10].z));
    const last = L[L.length - 1];
    m.push(`unsticks ${last.unst}, plan fails ${last.fails}, futile ${fut.toFixed(1)} s ${futAt.filter((f) => f[1] - f[0] > 0.5).slice(0, 6).map((f) => `[${f[0].toFixed(0)}-${f[1].toFixed(0)} (${f[2]},${f[3]})]`).join(' ')}, rocking ${rock.toFixed(0)} s, yaw snaps >29deg/0.1s ${snaps} (>46deg ${snaps2}), anim flicker ${flick}`);
    m.push(`dwell ${Object.entries(dwell).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k} ${v.toFixed(0)}`).join(', ')}`);
    m.push(`goal rooms ${JSON.stringify(gr)}; speed when moving ${sp.length ? (sp.reduce((a, v) => a + v, 0) / sp.length).toFixed(2) : '-'} m/s (spread ${sp.length ? Math.min(...sp).toFixed(2) + '-' + Math.max(...sp).toFixed(2) : '-'})`);
  }
  return `${m.join(' | ')}\n   ${st}`;
}
