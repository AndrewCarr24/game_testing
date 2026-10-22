// Lists the requests that fail while viewer/wild.html loads a world (debug helper).
// Usage: node blender/town/diner/tools/failed_requests.mjs "<query string>"
import { chromium } from 'playwright-core';
const BASE = process.env.GT_BASE || 'http://localhost:8765';
const qs = process.argv[2] || '?world=laurel_town&hud=0';
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const page = await (await b.newContext({ viewport: { width: 800, height: 450 } })).newPage();
page.on('requestfailed', (r) => console.log('FAILED', r.url(), r.failure()?.errorText));
page.on('response', (r) => { if (r.status() >= 400) console.log('HTTP', r.status(), r.url()); });
page.on('pageerror', (e) => console.log('pageerror', e.message));
await page.goto(`${BASE}/viewer/wild.html${qs}`);
await page.waitForFunction(() => window.__loaded || document.getElementById('hud')?.textContent.startsWith('error'), null, { timeout: 120000 }).catch(() => {});
console.log('hud:', await page.evaluate(() => document.getElementById('hud')?.textContent.slice(0, 200)));
await b.close();
