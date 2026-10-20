// Screenshots of the Grimble frozen in a pose, from several angles, in the real engine.
// Usage: node viewer/tools/grimble_pose.mjs <out-dir> <action> <time-s> [distance=4.5] [height=1.6]
// It stands on the great room floor at (-20, 0, 0) facing +x; 8 cameras ring it.
import { chromium } from 'playwright-core';
import fs from 'fs';
const [out, action = 'Crawl', time = '0.5', dist = '4.5', h = '1.6'] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 900, height: 600 } });
p.on('pageerror', (e) => console.log('pageerror:', e.message));
await p.goto('http://localhost:8765/viewer/index.html?level=mansion&gdelay=0&hunt=0&pos=-15,1.65,0&look=-20,1,0');
await p.waitForFunction(() => window.__loaded && window.__grimble, null, { timeout: 90000 });
const info = await p.evaluate(([action, time]) => {
  const g = window.__grimble;
  g.update = () => {};                               // freeze its brain
  // furniture out of the way (the shell stays)
  const cu = window.__culler; cu.update = () => false;
  for (const r of cu.rooms) for (const o of r.objects) o.visible = false;
  for (const s of cu.shared || []) s.obj.visible = false;
  g.root.visible = true;
  g.root.position.set(-20, 0, 0);
  g.root.rotation.y = Math.PI / 2;
  g.blob.position.set(-20, 0.02, 0); g.blob.visible = true;
  g.mixer.stopAllAction();
  const a = g.actions[action];
  a.reset(); a.play(); a.paused = false;
  g.mixer.setTime(+time);
  a.paused = true;
  g.root.updateMatrixWorld(true);
  return Object.keys(g.actions).join(',');
}, [action, time]);
const D = +dist, H = +h;
for (let i = 0; i < 8; i++) {
  const ang = (i / 8) * Math.PI * 2;
  await p.evaluate(([x, y, z]) => {
    const c = window.__camera;
    window.__bench = { frameStart() {}, drive() { c.position.set(x, y, z); c.lookAt(-20, 1.3, 0); }, renderStart() {}, frameEnd() {} };
  }, [-20 + Math.cos(ang) * D, H, Math.sin(ang) * D]);
  await p.waitForTimeout(500);
  await p.screenshot({ path: `${out}/${action}_${time}_${i}.png` });
}
console.log('actions:', info);
await b.close();
