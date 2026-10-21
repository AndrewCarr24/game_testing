// Lights off (viewer/baked.js, bake.py --state off): for each room, walk up to its light switch,
// press E, and check that the room really goes dark (frame brightness from the player's eye, the
// room's lightLevel, the fixtures' glow), then that it comes back, and that power off darkens
// every room with an off state. Screenshots: <out>/<room>_on.png, _off.png, power_off.png.
// Usage: node viewer/tools/lights_off.mjs [out-dir] [room,room,...]
import fs from 'fs';
import { chromium } from 'playwright-core';
import { level, props, room as roomInfo, url } from './level.mjs';

const out = process.argv[2] || 'build/lights_off';
fs.mkdirSync(out, { recursive: true });
const only = process.argv[3] ? process.argv[3].split(',') : null;

// one browser at a time per slot machine-wide (build/locks/browser_N)
fs.mkdirSync('build/locks', { recursive: true });
let slot = null;
while (slot === null) {
  for (let i = 0; i < 3 && slot === null; i++) { try { fs.mkdirSync(`build/locks/browser_${i}`); slot = i; } catch {} }
  if (slot === null) await new Promise((ok) => setTimeout(ok, 3000));
}
const release = () => { try { fs.rmdirSync(`build/locks/browser_${slot}`); } catch {} };
process.on('exit', release);

const bake = JSON.parse(fs.readFileSync(new URL('../../assets/levels/mansion_bake.json', import.meta.url)));
const rooms = Object.keys(bake.rooms).filter((r) => bake.rooms[r].off && (!only || only.includes(r)));
let fails = 0;
const check = (label, ok, detail = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}  ${detail}`); if (!ok) fails++; };

const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
try {
  const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
  p.on('pageerror', (e) => console.log('pageerror:', e.message));
  p.on('console', (m) => { if (m.type() === 'error' || /baked\.js/.test(m.text())) console.log('console:', m.text()); });
  p.on('response', (r) => { if (r.status() >= 400) console.log('http', r.status(), r.url()); });
  // mean sRGB brightness (0..255) of a screenshot, measured in the page
  const brightness = (png) => p.evaluate(async (b64) => {
    const img = new Image(); img.src = 'data:image/png;base64,' + b64; await img.decode();
    const c = new OffscreenCanvas(img.width, img.height).getContext('2d'); c.drawImage(img, 0, 0);
    const d = c.getImageData(0, 0, img.width, img.height).data; let s = 0;
    for (let i = 0; i < d.length; i += 4) s += 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];
    return s / (d.length / 4);
  }, png.toString('base64'));
  const shot = async (name) => { await p.evaluate(() => { const h = document.getElementById('hud'); if (h) h.style.visibility = 'hidden'; });
    const png = await p.screenshot({ path: `${out}/${name}.png` });
    await p.evaluate(() => { const h = document.getElementById('hud'); if (h) h.style.visibility = ''; });
    return brightness(png); };
  const teleport = (pos, look) => p.evaluate(([pos, look]) => {
    window.__player.pos.set(pos[0], pos[1] - 1.65, pos[2]); window.__player.vel.set(0, 0, 0);
    window.__player.syncCamera(); window.__camera.lookAt(...look);
  }, [pos, look]);

  // a view of the room from just inside its switch, looking across it
  const views = {};
  for (const r of rooms) {
    const sig = bake.rooms[r].off.signal;
    const sw = props('ix_switch').find((s) => s.room === r && s.signal === sig);
    const R = roomInfo(r);
    const eyeY = R.floor + 1.65;
    if (sw) {
      const a = (sw.rotationY * Math.PI) / 180;
      const n = [-Math.sin(a), Math.cos(a)];               // out of the wall, into the room (assets face -Y = glTF +z)
      const inward = ((R.cx - sw.position[0]) * n[0] + (R.cz - sw.position[2]) * n[1]) > 0 ? n : [-n[0], -n[1]];
      views[r] = { sw, at: [sw.position[0] + inward[0] * 0.7, eyeY, sw.position[2] + inward[1] * 0.7], look: sw.position,
                   view: [sw.position[0] + inward[0] * 0.9, eyeY, sw.position[2] + inward[1] * 0.9],
                   viewLook: [R.cx, R.floor + 1.2, R.cz] };
    } else {
      views[r] = { sw: null, view: [R.cx, eyeY, R.cz], viewLook: [R.x1, R.floor + 1.2, R.cz] };
    }
  }
  const first = views[rooms[0]];
  await p.goto(url(first.view, first.viewLook) + '&grimble=0&q=2' + (process.env.QS || ''));
  await p.waitForFunction(() => window.__loaded && window.__lighting, null, { timeout: 120000 });
  await p.mouse.click(640, 360); await p.waitForTimeout(500);

  const result = {};
  for (const r of rooms) {
    const v = views[r], sig = bake.rooms[r].off.signal;
    await teleport(v.view, v.viewLook); await p.waitForTimeout(1200);
    const on = await shot(`${r}_on`);
    const lvOn = await p.evaluate((r) => window.__lighting.lightLevel(r), r);
    if (v.sw) {
      await teleport(v.at, v.look); await p.waitForTimeout(500);
      await p.keyboard.press('KeyE'); await p.waitForTimeout(300);
    } else {
      await p.evaluate((s) => window.__signals.set(s, false), sig);
    }
    const sigVal = await p.evaluate((s) => window.__signals.get(s), sig);
    await teleport(v.view, v.viewLook); await p.waitForTimeout(1200);
    const off = await shot(`${r}_off`);
    const lvOff = await p.evaluate((r) => window.__lighting.lightLevel(r), r);
    const envT = await p.evaluate((r) => window.__lighting.rooms[r].lit.envT, r);
    check(`${r}: the switch turns ${sig} off`, sigVal === false, `signal=${sigVal}`);
    check(`${r}: its reflections are re-filtered dark`, Math.abs(envT - 1) < 1e-3, `envT=${envT}`);
    check(`${r}: the room goes dark`, off < on * 0.8 && lvOff < 0.8, `frame ${on.toFixed(1)} -> ${off.toFixed(1)}, lightLevel ${lvOn.toFixed(2)} -> ${lvOff.toFixed(2)}`);
    // back on
    if (v.sw) { await teleport(v.at, v.look); await p.waitForTimeout(400); await p.keyboard.press('KeyE'); }
    else await p.evaluate((s) => window.__signals.set(s, true), sig);
    await teleport(v.view, v.viewLook); await p.waitForTimeout(1200);
    const again = await shot(`${r}_again`);
    check(`${r}: and comes back`, Math.abs(again - on) < Math.max(2, on * 0.04), `frame ${again.toFixed(1)} (lit ${on.toFixed(1)})`);
    result[r] = { on: +on.toFixed(1), off: +off.toFixed(1), lightLevelOff: +lvOff.toFixed(3) };
  }
  // power off: every room with an off state dark
  await p.evaluate(() => window.__signals.set('power', false)); await p.waitForTimeout(1500);
  const v = views[rooms[0]];
  await teleport(v.view, v.viewLook); await p.waitForTimeout(600);
  await shot('power_off');
  const dark = await p.evaluate((rs) => rs.filter((r) => !window.__lighting.isDark(r)), rooms);
  check('power off darkens every room with an off state', dark.length === 0, dark.join(','));
  await p.evaluate(() => window.__signals.set('power', true)); await p.waitForTimeout(1500);
  const lit = await p.evaluate((rs) => rs.filter((r) => window.__lighting.lightLevel(r) < 0.999), rooms);
  check('power back on lights them again', lit.length === 0, lit.join(','));
  fs.writeFileSync(`${out}/result.json`, JSON.stringify(result, null, 2));
} finally {
  await b.close();
  release();
}
console.log(fails ? `${fails} FAILED` : 'all passed', '->', out);
process.exit(fails ? 1 : 0);
