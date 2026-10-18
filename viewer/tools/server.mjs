// Makes sure the project is being served on :8765 (the viewer and tests load from there);
// starts `python3 -m http.server` for the duration of the script if nothing is listening.
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
export const BASE = 'http://localhost:8765';

const up = () => fetch(`${BASE}/viewer/index.html`, { method: 'HEAD' }).then((r) => r.ok, () => false);

export async function ensureServer() {
  if (await up()) return () => {};
  const child = spawn('python3', ['-m', 'http.server', '8765'], { cwd: root, stdio: 'ignore' });
  for (let i = 0; i < 50 && !(await up()); i++) await new Promise((r) => setTimeout(r, 100));
  return () => child.kill();
}
