// Evaluate an expression in the loaded house (with ?invaders=0 unless the query says otherwise)
// and print the JSON result. For looking things up while writing scenarios.
// Usage: GT_BASE=... node viewer/tools/invaders_eval.mjs "<async js expression>" [qs]
import { withPage } from './invaders_lib.mjs';
const [expr, qs = '&grimble=0&fx=0&invaders=0'] = process.argv.slice(2);
const r = await withPage(qs, (p) => p.evaluate(`(async () => (${expr}))()`));
console.log(JSON.stringify(r, null, 1));
