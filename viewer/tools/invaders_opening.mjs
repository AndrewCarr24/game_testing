// The opening's scripted runs (viewer/invaders_opening.js; scenarios in
// invaders_opening_scenarios.js: arrival, ring_heard, answer, glass, hide, heard, outside), fast-
// forward through the invader suite's page harness (invaders_suite.mjs with SC set). Results, logs
// and photos in build/invaders/<label>/ (summary.txt).
// Usage: GT_BASE=http://localhost:8832 node viewer/tools/invaders_opening.mjs <label> [names|all] [seed=1]
import { spawnSync } from 'child_process';
import path from 'path';

const HERE = path.dirname(new URL(import.meta.url).pathname);
const r = spawnSync(process.execPath, [`${HERE}/invaders_suite.mjs`, ...process.argv.slice(2)], { stdio: 'inherit', env: { ...process.env, SC: 'invaders_opening_scenarios.js' } });
process.exit(r.status ?? 1);
