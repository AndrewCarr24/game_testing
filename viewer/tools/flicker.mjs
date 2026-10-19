// Flicker test: from far away, nudge the camera by 1 mm (no visible change) and count the
// pixels that flip; z-fighting (art vs wall, rugs vs floor...) shows up as flipped pixels.
// Usage: node viewer/tools/flicker.mjs [near]   (near overrides the camera's near plane)
import { chromium } from 'playwright-core';
import fs from 'fs';
import { url } from './level.mjs';
const near = process.argv[2] && process.argv[2] !== '-' ? +process.argv[2] : null;
const hide = process.argv[3] ? new RegExp(process.argv[3]) : null;   // hide meshes whose name matches (diagnosis)
const VIEWS = [   // eye, look (glTF): long views with pictures on the walls
  { name: 'gallery_s, art 20 m away', pos: [12, 1.65, 8.8], look: [-8, 1.6, 10.3] },
  { name: 'great room, art across', pos: [-14.5, 1.65, -9], look: [-25.5, 2.5, 9] },
  { name: 'ugallery_n, art down the gallery', pos: [-12, 6.25, -8.8], look: [12, 6.2, -10.3] },
];
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
await p.goto(url(VIEWS[0].pos, VIEWS[0].look));
await p.waitForFunction(() => window.__loaded, null, { timeout: 90000 });
let total = 0;
for (const v of VIEWS) {
  const r = await p.evaluate(async ({ v, near, hide: hs }) => {
    const hide = hs ? new RegExp(hs) : null;
    const { renderer, scene, camera } = window.__three;
    const pl = window.__player;
    if (near) { camera.near = near; camera.updateProjectionMatrix(); }
    if (hide) scene.traverse((o) => { if (o.isMesh && (hide.test(o.name) || hide.test(o.material.name))) o.visible = false; });
    const gl = renderer.getContext();
    const w = gl.drawingBufferWidth, h = gl.drawingBufferHeight;
    const shot = (dx) => new Promise((ok) => {
      window.__bench = { frameStart() {}, renderStart() {}, frameEnd() {},
        drive() { camera.position.set(v.pos[0] + dx, v.pos[1], v.pos[2]); camera.lookAt(v.look[0] + dx, v.look[1], v.look[2]);
                  pl.pos.set(v.pos[0] + dx, v.pos[1] - pl.eye, v.pos[2]); pl.vel.set(0, 0, 0); } };
      let n = 0;
      const wait = () => { if (++n < 6) return requestAnimationFrame(wait);
        const px = new Uint8Array(w * h * 4); gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, px); ok(px); };
      requestAnimationFrame(wait);
    });
    let flips = 0;
    const heat = new Uint8Array(w * h);
    let prev = await shot(0);
    const base = prev;
    for (let k = 1; k <= 4; k++) {
      const cur = await shot(k * 0.001);
      for (let i = 0; i < cur.length; i += 4) {
        const d = Math.abs(cur[i] - prev[i]) + Math.abs(cur[i + 1] - prev[i + 1]) + Math.abs(cur[i + 2] - prev[i + 2]);
        if (d > 60) { flips++; heat[i / 4] = 255; }
      }
      prev = cur;
    }
    window.__bench = null;
    // heatmap: flipping pixels red over the dimmed view (rows flipped: GL is bottom-up)
    const c = new OffscreenCanvas(w, h), g = c.getContext('2d'), img = g.createImageData(w, h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const i = (y * w + x), o = ((h - 1 - y) * w + x) * 4, a = i * 4;
      const grey = (base[a] + base[a + 1] + base[a + 2]) / 9;
      img.data[o] = heat[i] ? 255 : grey; img.data[o + 1] = heat[i] ? 0 : grey; img.data[o + 2] = heat[i] ? 0 : grey; img.data[o + 3] = 255;
    }
    g.putImageData(img, 0, 0);
    const blob = await c.convertToBlob({ type: 'image/png' });
    const buf = new Uint8Array(await blob.arrayBuffer());
    let bin = ''; for (let i = 0; i < buf.length; i += 0x8000) bin += String.fromCharCode(...buf.subarray(i, i + 0x8000));
    return { flips: Math.round(flips / 4), of: w * h, png: btoa(bin) };
  }, { v, near, hide: hide && hide.source });
  console.log(`${v.name}: ${r.flips} pixels flip per 1 mm step (of ${r.of})`);
  fs.mkdirSync('build/flicker', { recursive: true });
  fs.writeFileSync(`build/flicker/${v.name.split(',')[0]}.png`, Buffer.from(r.png, 'base64'));
  total += r.flips;
}
console.log(`total ${total}`);
await b.close();
