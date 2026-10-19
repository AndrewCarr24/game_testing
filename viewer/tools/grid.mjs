// Contact sheet of screenshots, labelled. Usage: node grid.mjs out.png columns img1.png img2.png ...
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
const [out, cols, ...imgs] = process.argv.slice(2);
const html = `<body style="margin:0;background:#111;display:grid;grid-template-columns:repeat(${cols},1fr);gap:4px">` +
  imgs.map((f) => `<div style="position:relative"><img src="file://${path.resolve(f)}" style="width:100%;display:block"><span style="position:absolute;left:6px;top:4px;color:#fff;font:14px sans-serif;text-shadow:0 0 3px #000">${f.split('/').slice(-3).join('/')}</span></div>`).join('') + '</body>';
const tmp = path.resolve(out) + '.html';
fs.writeFileSync(tmp, html);
const b = await chromium.launch({ channel: 'chrome' });
const p = await b.newPage({ viewport: { width: 1600, height: 400 } });
await p.goto('file://' + tmp); await p.waitForTimeout(800);
await p.screenshot({ path: out, fullPage: true });
await b.close();
fs.unlinkSync(tmp);
