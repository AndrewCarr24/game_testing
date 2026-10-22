// Photos of the stand-in invaders: a line-up of the roles and poses (idle, walking, aiming, the
// bat's swing, a knife, a crouch, a dead one) in the courtyard, and a squad in the great room seen
// from the player's eye. The brains are paused (each holds its pose) so the shots repeat.
// Usage: GT_BASE=http://localhost:8827 node viewer/tools/invaders_shots.mjs [out=build/invaders/shots]
import fs from 'fs';
import { withPage } from './invaders_lib.mjs';

const [out = 'build/invaders/shots'] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
await withPage('&grimble=0&waves=0&invaders=on&god=1', async (p) => {
  await p.waitForFunction(() => window.__invaders, null, { timeout: 60000 });
  await p.evaluate(() => {
    document.querySelectorAll('#hud,#stats,#hint').forEach((e) => (e.style.display = 'none'));
    const I = window.__invaders, V = window.__player.pos.constructor;
    I.clear();
    window.__player.update = () => {};
    const poses = [
      ['leader', 'idle'], ['gun', 'aim'], ['gun', 'walk'], ['watcher', 'aim'], ['bat', 'idle'], ['bat', 'swing'], ['bat', 'run'], ['knife', 'swing'], ['knife', 'crouch'], ['gun', 'dead'],
    ];
    poses.forEach(([role, pose], i) => {
      const a = I.spawn(role, { at: new V(-8 + i * 1.75, 0, 3.5), inside: true, yaw: Math.PI });
      a.think = function (dt) {
        this.time += dt;
        this.lookYaw = this.yaw = Math.PI + (pose === 'aim' ? 0.25 : 0);
        this.moveSpeed = pose === 'walk' ? 1.6 : pose === 'run' ? 5 : 0;
        this.anim.aim = pose === 'aim' ? 1 : 0;
        this.anim.swing = pose === 'swing' ? 0.5 : -1;
        this.crouch = pose === 'crouch' ? 1 : 0;
        if (pose === 'dead' && this.alive) { this.alive = false; this.anim.die = 1; this.dieYaw = this.yaw; }
      };
      a.move = () => {};
    });
    // a squad in the great room, from the gallery
    const sq = [['gun', -18, 2, 0.5], ['bat', -20, -1, 1.2], ['knife', -16.5, -3, 2.0], ['gun', -22, 4, 1.0]];
    for (const [role, x, z, yaw] of sq) {
      const a = I.spawn(role, { at: new V(x, 0, z), inside: true, yaw: yaw + Math.PI / 2 });
      a.think = function (dt) { this.time += dt; this.anim.aim = this.gun ? 0.6 : 0; this.moveSpeed = role === 'bat' ? 1.5 : 0; };
      a.move = () => {};
    }
  });
  const views = {
    lineup: [[0, 1.5, -1.5], [0, 1.0, 3.5]],
    lineup_close: [[-3.5, 1.4, 0.6], [-3.5, 1.0, 3.5]],
    lineup_side: [[-12, 1.6, 0.5], [-2, 0.9, 3.5]],
    great_room: [[-11.8, 1.65, 0], [-19, 1.2, 1]],
  };
  for (const [name, [pos, at]] of Object.entries(views)) {
    await p.evaluate(([pos, at]) => { const c = window.__camera; c.position.set(...pos); c.lookAt(...at); }, [pos, at]);
    await p.waitForTimeout(700);
    await p.screenshot({ path: `${out}/${name}.png` });
  }
});
