// Renders an SVG file to PNG at its own size in Chrome (for the design maps).
// Usage: node viewer/tools/svg_png.mjs in.svg out.png
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';

const [src, dst] = process.argv.slice(2);
const svg = fs.readFileSync(src, 'utf8');
const m = svg.match(/width="(\d+)" height="(\d+)"/);
const [w, h] = [+m[1], +m[2]];
const b = await chromium.launch({ channel: 'chrome' });
const page = await (await b.newContext({ viewport: { width: w, height: h } })).newPage();
await page.goto('file://' + path.resolve(src));
await page.screenshot({ path: dst, clip: { x: 0, y: 0, width: w, height: h } });
await b.close();
console.log('wrote', dst, w, 'x', h);
