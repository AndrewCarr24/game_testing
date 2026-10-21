// Loose things (blender/lib/pickups.py): counts every pickup in the house, checks they rest in
// their room's batch (no extra draw calls), then plays: walks up to pickups in several rooms,
// takes them with E (identical ones stack), checks a stacked one waits for the one on it, and
// throws a book (thuds, lands, can be taken again) and a ceramic piece (shatters, a noise).
// Usage: GT_BASE=http://localhost:<port> node viewer/tools/pickups.mjs [out-dir]
import { chromium } from 'playwright-core';
import fs from 'fs';
import { url } from './level.mjs';
const out = process.argv[2] || 'build/pickups';
fs.mkdirSync(out, { recursive: true });
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 1100, height: 700 } });
const errors = [];
p.on('pageerror', (e) => { errors.push(e.message); console.log('pageerror:', e.message); });
let fails = 0;
const check = (label, ok, detail = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}  ${detail}`); if (!ok) fails++; };

await p.goto(url([0, 1.65, 17], [0, 1.5, 0]));
await p.waitForFunction(() => window.__loaded, null, { timeout: 90000 });
await p.mouse.click(550, 350); await p.waitForTimeout(500);

// ---------------------------------------------------------------- inventory of the house
const census = await p.evaluate(() => {
  const it = window.__interact, rooms = window.__level.rooms;
  const ps = it.items.filter((i) => i.def.type === 'pickup');
  const byItem = {}, byRoom = {};
  const v = window.__camera.position.clone();
  for (const i of ps) {
    byItem[i.def.item] = (byItem[i.def.item] ?? 0) + 1;
    i.node.getWorldPosition(v);
    const room = Object.entries(rooms).find(([, r]) => v.y >= r.floor - 0.2 && v.y < r.floor + (r.height || 4) &&
      v.x >= r.rect[0] && v.x <= r.rect[2] && v.z >= r.rect[1] && v.z <= r.rect[3])?.[0];
    byRoom[room ?? 'outside'] = (byRoom[room ?? 'outside'] ?? 0) + 1;
  }
  return { total: ps.length, batched: ps.filter((i) => i.batched).length, stacked: ps.filter((i) => i.load?.length).length,
           throwable: ps.filter((i) => i.def.throwable).length, byItem, byRoom, stats: document.getElementById('stats')?.textContent };
});
console.log(`pickups: ${census.total} (${census.batched} resting in a room batch, ${census.stacked} with something on them, ${census.throwable} throwable)`);
console.log('by item:', JSON.stringify(census.byItem));
console.log('by room:', JSON.stringify(census.byRoom));
console.log('stats:', census.stats);
check('the house has hundreds of pickups', census.total > 300, `${census.total}`);
check('resting pickups are drawn by their room batch', census.batched > census.total * 0.8, `${census.batched}/${census.total}`);
const tools = ['keycard', 'car_key', 'fuse', 'battery', 'flashlight', 'tablet', ...Object.keys(census.byItem).filter((id) => id.startsWith('key_'))];
const loose = census.total - tools.reduce((n, id) => n + (census.byItem[id] ?? 0), 0);
check('every loose thing is throwable (the tools are not)', census.throwable === loose, `${census.throwable}/${loose}`);
fs.writeFileSync(`${out}/census.json`, JSON.stringify(census, null, 1));

// ---------------------------------------------------------------- walk up and take
// walk up to a pickup: the first standing spot round it (0.55-0.95 m away, eye at standing
// height, not inside furniture) from which it is the thing the player focuses, looking at it
const goTo = (name) => p.evaluate((name) => {
  const it = window.__interact, pl = window.__player, cam = window.__camera;
  const item = it.items.find((i) => i.node.name === name);
  const box = window.__colliders[0].clone().setFromObject(item.node), c = box.getCenter(cam.position.clone());
  const floor = Object.values(window.__level.rooms).filter((r) => r.floor <= box.min.y + 0.05).reduce((a, r) => Math.max(a, r.floor), -1);
  const feet = c.clone(), dir = c.clone();
  for (const d of [0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 0.45]) for (let k = 0; k < 16; k++) {
    const a = (k / 16) * Math.PI * 2;
    feet.set(c.x + Math.cos(a) * d, floor + 0.31, c.z + Math.sin(a) * d);
    if (pl.overlapping(feet).length) continue;          // (a rug or a step under the feet is fine)
    feet.y = floor + 0.02;
    const eye = feet.clone(); eye.y += pl.eye;
    // (in a heap of lemons the one nearest the crosshair may be its neighbour: any of the kind will do)
    const got = it.nearest(eye, dir.subVectors(c, eye).normalize());
    if (got !== item && !(got && got.root === item.root && got.def.item === item.def.item)) continue;
    pl.pos.copy(feet); cam.position.copy(eye); cam.lookAt(c);
    return { item: item.def.item, name: got.node.name, eye: eye.toArray(), c: c.toArray() };
  }
  return { item: item.def.item, none: true };
}, name);
// every pickup can be reached: some free standing spot round it from which it (or one of its
// kind in the same placement, e.g. a heap of lemons) is what the player focuses
const reach = await p.evaluate(() => {
  const it = window.__interact, pl = window.__player, rooms = Object.values(window.__level.rooms);
  const bad = [];
  const box = window.__colliders[0].clone(), c = window.__camera.position.clone(), feet = c.clone(), dir = c.clone();
  for (const item of it.items) {
    if (item.def.type !== 'pickup' || item.host || item.taken) continue;
    box.setFromObject(item.node); box.getCenter(c);
    const floor = rooms.filter((r) => r.floor <= box.min.y + 0.05).reduce((a, r) => Math.max(a, r.floor), -1);
    let ok = false;
    // what's on it first: then it's reachable if they are (the top of a stack is tested itself)
    if (item.load?.length) continue;
    for (const d of [0.5, 0.7, 0.9, 1.1, 1.3, 1.5, 1.7, 1.9]) {
      for (let k = 0; k < 16 && !ok; k++) {
        const a = (k / 16) * Math.PI * 2;
        feet.set(c.x + Math.cos(a) * d, floor + 0.31, c.z + Math.sin(a) * d);
        if (pl.overlapping(feet).length) continue;
        feet.y = floor + pl.eye;
        const got = it.nearest(feet, dir.subVectors(c, feet).normalize());
        ok = got === item || (got && got.root === item.root && got.def.item === item.def.item);
      }
      if (ok) break;
    }
    if (!ok) bad.push(`${item.node.name}@${c.toArray().map((v) => v.toFixed(1)).join(',')}`);
  }
  return bad;
});
check('every pickup can be reached and focused from somewhere', reach.length === 0, `${reach.length} not: ${reach.slice(0, 20).join(', ')}`);

const S = () => p.evaluate(() => ({
  hint: document.getElementById('hint').textContent, toast: window.__toast(),
  inv: Object.fromEntries(window.__inventory.ids().map((id) => [id, window.__inventory.count(id)])),
}));
const take = async (name, shot) => {
  const at = await goTo(name);
  if (at.none) return { at, before: { hint: 'no spot to reach it from' }, after: { inv: {} }, taken: false, batched: true };
  await p.waitForTimeout(350);
  const before = await S();
  if (shot) await p.screenshot({ path: `${out}/${shot}_before.png` });
  await p.keyboard.press('KeyE'); await p.waitForTimeout(300);
  const after = await S();
  const st = await p.evaluate((name) => { const i = window.__interact.items.find((x) => x.node.name === name); return { taken: i.taken, batched: !!i.batched }; }, at.name);
  if (shot) await p.screenshot({ path: `${out}/${shot}_after.png` });
  return { at, before, after, ...st };
};

// a few kinds in several rooms (first match per pattern)
const pick = await p.evaluate(() => {
  const ps = window.__interact.items.filter((i) => i.def.type === 'pickup' && !i.load?.length && !i.host);
  const want = [['DecorAConsole', 'book'], ['DecorC_VignetteDesk', null], ['DiningWineSet', 'wine_bottle'], ['KitchenIsland', 'lemon'],
                ['DecorD_Nightstand', null], ['DecorBVignetteSideboard', 'ceramic_vase'], ['DecorC_VignetteGallery', null],
                ['DiningCenterpiece', 'candle'], ['DecorD_VignetteVanity', null], ['DecorBVignetteBread', 'bread']];
  return want.map(([prefix, item]) => ps.find((i) => i.node.name.startsWith(prefix) && (!item || i.def.item === item))?.node.name).filter(Boolean);
});
console.log('sampled:', pick.join(', '));
check('found pickups to sample in several rooms', pick.length >= 5, `${pick.length}`);
let n = 0;
for (const name of pick) {
  const r = await take(name, `take${n++}`);
  const got = (r.after.inv[r.at.item] ?? 0) > (r.before.inv?.[r.at.item] ?? 0);    // (that one, or its neighbour in a heap)
  check(`${name}: prompt, E takes it into the inventory`, r.before.hint.includes('Take') && got,
    `hint="${r.before.hint.slice(0, 60)}" taken=${r.taken} inv=${JSON.stringify(r.after.inv)}`);
}

// identical things stack: two books -> "Book x2"
const books = await p.evaluate(() => window.__interact.items.filter((i) => i.def.item === 'book' && !i.taken && !i.load?.length && !i.host)
  .slice(0, 2).map((i) => i.node.name));
const nb0 = (await S()).inv.book ?? 0;
for (const name of books) await take(name);
const inv = await p.evaluate(() => ({ count: window.__inventory.count('book'), label: window.__inventory.label('book'), rows: window.__inventory.ids().filter((x) => x === 'book').length }));
check('identical items stack in one inventory row', inv.rows === 1 && inv.count === nb0 + 2 && inv.label === `Book ×${nb0 + 2}`, JSON.stringify(inv));

// a stack: the book under another can't be taken until the top one is
const stack = await p.evaluate(() => {
  const low = window.__interact.items.find((i) => i.def.type === 'pickup' && !i.taken && i.load?.length === 1 && !i.load[0].load?.length && !i.load[0].taken);
  return low && { low: low.node.name, top: low.load[0].node.name, avail: window.__interact.available(low) };
});
if (stack) {
  check('a pickup with another resting on it is not available', stack.avail === false, JSON.stringify(stack));
  await take(stack.top);
  const avail = await p.evaluate((n) => window.__interact.available(window.__interact.items.find((i) => i.node.name === n)), stack.low);
  check('... and is once the one on it is taken', avail === true);
} else check('found a stack to test', false);

// throws: a book thuds, lands whole and can be taken again; a ceramic piece shatters
const noises = [];
await p.exposeFunction('__noiseSeen', (x) => noises.push(x));
await p.evaluate(() => window.__noise.on((e) => window.__noiseSeen({ loudness: e.loudness, source: e.source, item: e.item })));
await p.evaluate(() => { const i = window.__inventory; i.armed = 'book'; i.changed(); });
await p.evaluate(() => { const c = window.__camera; window.__player.pos.set(-20, 0, 0); c.position.set(-20, 1.6, 0); c.lookAt(-20, 0.5, -3); });
await p.waitForTimeout(200);
const before = await p.evaluate(() => window.__interact.items.length);
await p.keyboard.press('Enter'); await p.waitForTimeout(2500);
const landed = await p.evaluate((before) => ({ n: window.__interact.items.length - before, flying: window.__throwables.flying.length }), before);
check('a thrown book thuds (a noise) and lands as a pickup again', noises.some((x) => x.source === 'thud' && x.item === 'book') && landed.n === 1 && landed.flying === 0,
  `noises=${JSON.stringify(noises)} landed=${JSON.stringify(landed)}`);
await p.screenshot({ path: `${out}/book_landed.png` });
const shat = await p.evaluate(() => window.__inventory.ids().find((id) => window.__inventory.get(id).def.shatter));
if (shat) {
  await p.evaluate((id) => { const i = window.__inventory; i.armed = id; i.changed(); }, shat);
  await p.keyboard.press('Enter'); await p.waitForTimeout(1500);
  check(`a thrown ${shat} shatters with a noise`, noises.some((x) => x.source === 'shatter' && x.item === shat), JSON.stringify(noises));
  await p.screenshot({ path: `${out}/shatter.png` });
} else check('carrying something breakable to throw', false);
check('no page errors', errors.length === 0, errors.join(' | '));
await b.close();
console.log(fails ? `${fails} failed` : 'all passed');
process.exit(fails ? 1 : 0);
