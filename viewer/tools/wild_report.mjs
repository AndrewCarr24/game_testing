// Markdown tables from wild_bench.mjs runs (build/wild_bench/<label>/stats-<profile>.json), for
// design/wilderness/_tech/runtime.md. Usage: node viewer/tools/wild_report.mjs label1 label2 ...
// (no labels: every run found). Headline metric: render ms = frames each synced by a 1-pixel
// readback, mean over 4 quarter turns (max = worst direction); GPU = timer query p50.
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const dir = path.join(root, 'build/wild_bench');
const labels = process.argv.slice(2).length ? process.argv.slice(2) : fs.readdirSync(dir);
const runs = [];
for (const l of labels) for (const p of ['gpu', 'soft']) {
  const f = path.join(dir, l, `stats-${p}.json`);
  if (fs.existsSync(f)) runs.push(JSON.parse(fs.readFileSync(f, 'utf8')));
}
const k = (n) => (n == null ? '-' : n >= 1e6 ? (n / 1e6).toFixed(2) + 'M' : n >= 1000 ? Math.round(n / 1000) + 'k' : String(n));
const sum = (o) => Object.values(o || {}).reduce((a, b) => a + b, 0);

console.log('| run | profile | q | MSAA | view | render ms mean (worst dir) | GPU p50 ms | draw calls | triangles max | trees drawn near / mid / far | grass blades |');
console.log('|---|---|---|---|---|---|---|---|---|---|---|');
for (const s of runs) for (const [v, r] of Object.entries(s.views)) {
  const t = r.stats?.trees;
  let tiers = '-';
  if (t) {
    const trees = ['broadleaf', 'conifer', 'pine'].filter((n) => t[n]);
    const cols = Math.max(...trees.map((n) => t[n].length));
    tiers = [...Array(cols).keys()].map((i) => trees.reduce((a, n) => a + (t[n][i] || 0), 0)).join(' / ');
  }
  console.log(`| ${s.label}${s.qs ? ` \`${s.qs}\`` : ''} | ${s.profile} | ${s.quality} | ${s.msaa ? 'on' : 'off'} | ${v} | ${r.finishMs?.mean ?? '-'} (${r.finishMs?.max ?? '-'}) | ${r.all.gpuMs?.p50 ?? '-'} | ${r.all.calls.max} | ${k(r.all.tris.max)} | ${tiers} | ${k(r.stats?.grass?.blades)} |`);
}
console.log('\n| run | profile | load s | world gen ms | download MB | GPU textures MB | JS heap MB | trees | undergrowth | walk: frame p95 ms, feet above ground (m) |');
console.log('|---|---|---|---|---|---|---|---|---|---|');
for (const s of runs) {
  const c = s.counts;
  const w = s.walk ? `${s.walk.frameMs.p95}, ${s.walk.feetAboveGround.min}..${s.walk.feetAboveGround.max} over ${s.walk.distanceM} m` : '-';
  console.log(`| ${s.label}${s.qs ? ` \`${s.qs}\`` : ''} | ${s.profile} | ${s.load.seconds} | ${s.timings.world} | ${s.downloadMB} | ${s.textureMB} | ${s.heapMB ?? '-'} | ${k(c.broadleaf + c.conifer + c.pine)} | ${k(c.fern + c.tuft)} | ${w} |`);
}
const sh = runs.find((s) => s.shipping)?.shipping;
if (sh) console.log(`\nShipping estimate of the generated data: heights 16-bit + gzip ${sh.heightsMB} MB, splat WebP ${sh.splatWebpMB} MB, light WebP ${sh.lightWebpRgbMB} MB, ${k(sh.instances)} instances quantised + gzip ${sh.instancesMB} MB.`);
const tb = runs.find((s) => s.views?.forest?.stats?.trisBy);
if (tb) {
  console.log(`\nTriangles by system (${tb.label}, ${tb.profile}):\n`);
  console.log('| view | triangles by mesh (instances x triangles each) |');
  console.log('|---|---|');
  for (const [v, r] of Object.entries(tb.views)) console.log(`| ${v} | ${Object.entries(r.stats.trisBy).sort((a, b) => b[1] - a[1]).map(([n, t]) => `${n} ${k(t)}`).join(', ')} (total ${k(sum(r.stats.trisBy))}) |`);
}
