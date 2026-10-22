// Crack test for the wilderness terrain (viewer/wild/terrain.js, CDLOD + geomorphing): terrain
// only, sky dome removed, background magenta; from many cameras 60-250 m above the ground looking
// down across several LOD rings, count magenta pixels (a seam shows the background through it).
// Must report 0. Also writes a wireframe picture of the LOD rings.
// Usage: node viewer/tools/wild_cracks.mjs [out_dir] [--world laurel_fork]   (takes a build/locks/browser_N slot)
// --world: a generated level; its terrain and backdrop ring are drawn (water, props, estate hidden;
// the ring has a hole over the square, so a seam inside it, or at the border, shows),
// cameras spread over +-560 m (its playable square).
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { ensureServer, BASE } from './server.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const argv = process.argv.slice(2);
const wi = argv.indexOf('--world');
const worldName = wi >= 0 ? argv.splice(wi, 2)[1] : null;
const out = argv[0] || path.join(root, worldName ? `build/wilderness/${worldName}/cracks` : 'build/wild_bench/cracks');
fs.mkdirSync(out, { recursive: true });
const locks = path.join(root, 'build/locks');
let slot = null;
while (!slot) {
  for (let i = 0; i < 3 && !slot; i++) { try { fs.mkdirSync(path.join(locks, `browser_${i}`)); slot = path.join(locks, `browser_${i}`); } catch {} }
  if (!slot) await new Promise((r) => setTimeout(r, 2000));
}
const release = () => { try { fs.rmdirSync(slot); } catch {} };
process.on('exit', release);
const stop = await ensureServer();
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
try {
  const p = await (await b.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1 })).newPage();
  p.on('pageerror', (e) => console.log('pageerror:', e.message));
  await p.goto(`${BASE}/viewer/wild_proto.html?t=3&q=3&trees=0&under=0&grass=0&hud=0&aa=0${worldName ? `&world=${worldName}` : ''}`);
  await p.waitForFunction(() => window.__loaded, null, { timeout: 120000 });
  const r = await p.evaluate((spread) => {
    const { renderer, scene, camera } = window.__three, w = window.__wild, gl = renderer.getContext();
    w.pause(true);
    scene.remove(scene.getObjectByName('Sky'));
    for (const n of ['Wild_Water', 'Wild_Estate', 'Wild_Authored']) { const o = scene.getObjectByName(n); if (o) o.visible = false; }
    if (w.props) w.props.group.visible = false;
    scene.background = null;
    renderer.setClearColor(0xff00ff, 1);
    const W = gl.drawingBufferWidth, H = gl.drawingBufferHeight, px = new Uint8Array(W * H * 4);
    const results = [];
    let seed = 1;
    const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    for (let k = 0; k < 120; k++) {
      // (kept well inside the world, so no view reaches its edge: what shows through is a seam)
      const x = (rnd() - 0.5) * spread, z = (rnd() - 0.5) * spread, a = rnd() * Math.PI * 2;
      const up = 15 + rnd() * 135, ground = w.world.heightAt(x, z);
      camera.position.set(x, ground + up, z);
      // the top of the view 20 deg below the horizon: every pixel should hit terrain
      const pitch = -(35 + 20) * Math.PI / 180;
      camera.lookAt(x + Math.cos(a) * Math.cos(pitch), ground + up + Math.sin(pitch), z + Math.sin(a) * Math.cos(pitch));
      camera.updateMatrixWorld();
      w.cull();
      renderer.render(scene, camera);
      gl.readPixels(0, 0, W, H, gl.RGBA, gl.UNSIGNED_BYTE, px);
      let holes = 0, first = null;
      for (let i = 0; i < px.length; i += 4) if (px[i] > 250 && px[i + 1] < 5 && px[i + 2] > 250) { holes++; if (!first) first = [(i / 4) % W, H - 1 - Math.floor(i / 4 / W)]; }
      results.push({ pos: camera.position.toArray().map((v) => +v.toFixed(0)), look: [+a.toFixed(3), +pitch.toFixed(3)], holes, first, patches: w.terrain.stats.patches, levels: w.terrain.stats.byLevel.join(' ') });
    }
    return { W, H, results };
  }, worldName ? 1120 : 600);
  const bad = r.results.filter((x) => x.holes);
  console.log(`${r.results.length} views ${r.W}x${r.H}: ${bad.length} with background showing through` +
    (bad.length ? '\n' + bad.map((x) => `  ${x.pos} holes ${x.holes} first at ${x.first} levels [${x.levels}]`).join('\n') : ''));
  console.log(`patches per view ${Math.min(...r.results.map((x) => x.patches))}..${Math.max(...r.results.map((x) => x.patches))}`);
  fs.writeFileSync(path.join(out, 'cracks.json'), JSON.stringify(r, null, 1));
  // wireframe picture of the LOD rings: from 250 m up, looking 25 deg down (no fog)
  const url = await p.evaluate(() => {
    const { renderer, scene, camera } = window.__three, w = window.__wild;
    renderer.setClearColor(0x9fb0c4, 1);
    w.uniforms.uFogDensity.value = 0;
    const g = w.world.heightAt(0, 300);
    camera.position.set(0, g + 250, 300);
    camera.lookAt(0, g + 250 - Math.tan(25 * Math.PI / 180) * 100, 200);
    camera.updateMatrixWorld();
    w.terrain.mesh.material.wireframe = true;
    w.cull(); renderer.render(scene, camera);
    return renderer.domElement.toDataURL('image/png');
  });
  fs.writeFileSync(path.join(out, 'terrain_wire.png'), Buffer.from(url.split(',')[1], 'base64'));
} finally { await b.close(); stop(); release(); }
