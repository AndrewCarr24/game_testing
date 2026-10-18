// Visual check: screenshots from fixed camera positions (bench_route.mjs views: one per
// room plus hero-prop close-ups), HUD hidden, into build/bench/<label>/shots/<view>.png.
// Compare two labels with compare.mjs.
//
// Usage: node viewer/tools/shots.mjs [label] [view ...]
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { views } from './bench_route.mjs';
import { ensureServer, BASE } from './server.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const [label = 'latest', ...only] = process.argv.slice(2);
const dir = path.join(root, 'build/bench', label, 'shots');
fs.mkdirSync(dir, { recursive: true });
const list = views().filter((v) => !only.length || only.includes(v.name));

const stop = await ensureServer();
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const page = await b.newPage({ viewport: { width: 1600, height: 900 } });
page.on('pageerror', (e) => console.log('pageerror:', e.message));
await page.goto(`${BASE}/viewer/index.html?level=mansion`);
await page.waitForFunction(() => window.__loaded, null, { timeout: 120000 });
await page.addStyleTag({ content: 'body > *:not(canvas) { display: none !important; }' });
const frames = (n) => page.evaluate((n) => new Promise((ok) => {
  const step = () => (n-- > 0 ? requestAnimationFrame(step) : ok());
  step();
}), n);
for (const v of list) {
  await page.evaluate(({ pos, look }) => {
    const { camera, renderer } = window.__three;
    const pl = window.__player;
    const no = () => {};
    window.__bench = { frameStart: no, renderStart: no, frameEnd: no, drive() {
      camera.position.set(...pos); camera.lookAt(...look);
      pl.pos.set(pos[0], pos[1] - pl.eye, pos[2]); pl.vel.set(0, 0, 0);
    } };
    renderer.shadowMap.needsUpdate = true;
  }, v);
  await frames(8);                                    // culling settles on the new position
  await page.evaluate(() => { window.__three.renderer.shadowMap.needsUpdate = true; });
  await frames(4);
  await page.locator('canvas').screenshot({ path: path.join(dir, `${v.name}.png`) });
}
console.log(`${list.length} shots -> ${path.relative(root, dir)}`);
await b.close();
stop();
