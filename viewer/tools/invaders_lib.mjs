// Shared by the invader tests: take a browser slot (build/locks/browser_0..2), open a page of the
// house, run fn(page), close and release (also on errors). GT_BASE picks the server.
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
export const BASE = process.env.GT_BASE || 'http://localhost:8765';

export async function withPage(qs, fn, { w = 960, h = 600, seed = null, wait = () => window.__loaded } = {}) {
  const locks = path.join(root, 'build/locks');
  fs.mkdirSync(locks, { recursive: true });
  let slot = null;
  while (slot === null) {
    for (let i = 0; i < 3 && slot === null; i++) { try { fs.mkdirSync(`${locks}/browser_${i}`); slot = i; } catch {} }
    if (slot === null) await new Promise((ok) => setTimeout(ok, 3000));
  }
  const release = () => { try { fs.rmdirSync(`${locks}/browser_${slot}`); } catch {} };
  process.on('exit', release);
  process.on('SIGINT', () => { release(); process.exit(1); });
  let b;
  try {
    b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
    const p = await b.newPage({ viewport: { width: w, height: h } });
    p.on('pageerror', (e) => console.log('pageerror:', e.message));
    p.on('console', (m) => { if (m.type() === 'error' || m.text().startsWith('[inv]')) console.log('console:', m.text()); });
    if (seed != null) {
      await p.addInitScript((seed) => {
        let a = seed >>> 0;
        Math.random = () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
      }, seed * 7919 + 13);
    }
    await p.goto(`${BASE}/viewer/index.html?level=mansion${qs}`);
    await p.waitForFunction(wait, null, { timeout: 180000, polling: 250 });
    return await fn(p);
  } finally { await b?.close(); release(); }
}
