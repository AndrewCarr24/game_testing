// Scenarios for build/gt/suite.mjs (evaluated in the page). World glTF (x, z); +z south.
// G: [x, z, yaw] of the spine's base, yaw = atan2(dx, dz) (W -PI/2, E PI/2, N PI, S 0).
// P: player feet [x, z, y]. saw: it has just seen the player (chasing). idle: hold it s seconds.
// steps: {go: [[x, z], ...], mode: run|walk|crouch}, {wait}, {until(h, pl, S), timeout}, {tp}, {door: [x, z, open]},
//        {noise: [x, z, loud]}, {crouch}, {hidden}, {look}, {fn(h, pl, S)}, {photo: {name, view: eye|high}}
(() => {
  const W = -Math.PI / 2, E = Math.PI / 2, N = Math.PI, S0 = 0;
  const DEN = [-19.75, 10.5], MUD = [13.5, -3.5];
  return {
    // ---- losing the player round corners (search)
    corner_stop: { G: [2, 8.75, W], P: [-6, 8.75], saw: true, secs: 40, steps: [
      { go: [[-11.75, 8.5], [-12.7, 5.0]], mode: 'run', label: 'tucked' }, { look: [-11.75, 1.5, 9] }, { wait: 40 }] },
    hide_room: { G: [4, 8.75, W], P: [-5, 8.75], saw: true, secs: 50, steps: [
      { go: [[-11.75, 8.75], [-11.75, 3.5], [-16, 3.5], [-16.5, 9.2]], mode: 'run', label: 'hid' }, { look: [-14, 1.5, 4] }, { wait: 50 }] },
    kitchen_corner: { G: [-9, -8.75, E], P: [-2, -8.75], saw: true, secs: 40, steps: [
      { go: [[0, -8.75], [0, -13], [4, -11.4], [7.2, -11.3]], mode: 'run', label: 'tucked' }, { look: [0, 1.5, -11] }, { wait: 40 }] },
    entry_corner: { G: [-6, 8.75, E], P: [1, 8.75], saw: true, secs: 40, steps: [
      { go: [[4.75, 8.75], [4.75, 12.5], [2, 11.6], [-7.3, 11.6]], mode: 'run', label: 'tucked' }, { look: [4.75, 1.5, 11] }, { wait: 40 }] },
    dining_tuck: { G: [10, 8.75, W], P: [-5, 8.75], saw: true, secs: 55, steps: [
      { go: [[-11.75, 8.75], [-11.75, 3.5], [-17, 3.5], [-20, -8], [-20, -11.8], [-25.2, -11.2]], mode: 'run', label: 'tucked' }, { look: [-20, 1.5, -11] }, { wait: 55 }] },
    // seen in gallery_e, into the mudroom (a side room it can't enter), door shut, off the doorway line
    mudroom: { G: [-11.75, 8.75, E], P: [-3, 8.75], saw: true, secs: 200, steps: [
      { go: [[11.75, 8.75], [11.75, -3.5]], mode: 'run', timeout: 20 }, { door: [...MUD, true] }, { tp: [15.2, -3.5] }, { door: [...MUD, false] },
      { go: [[19, -8]], mode: 'walk', label: 'hidden' }, { look: [12, 1.5, -3.5] }, { wait: 30 }, { photo: { name: 'mud_30s', view: 'high' } }, { wait: 200 }] },
    // ---- cheating
    // seen in the entry, then hops round the cloakroom (door shut, never in line with the gap)
    lurk_cheat: { G: [-4, 14, E], P: [6, 14], saw: true, secs: 16, steps: [
      { wait: 0.4 }, { tp: [11, 12] }, { look: [6, 1.5, 14] }, { wait: 2.5, label: 'in cloak' }, { tp: [12.5, 16] }, { wait: 1.2 }, { tp: [10, 11] }, { wait: 1.2 },
      { tp: [12.5, 16] }, { wait: 1.2 }, { tp: [10, 11] }, { wait: 8 }] },
    // the player close behind it in gallery_e, then away round the SE corner and west
    behind_run: { G: [11.75, 1, N], P: [11.75, 6.2], saw: true, secs: 30, steps: [
      { wait: 2 }, { go: [[11.75, 8.75], [-4, 8.75], [-11.75, 8.75], [-11.75, -2]], mode: 'run', label: 'away' }, { look: [-11.75, 1.5, 8.75] }, { wait: 30 }] },
    // ---- sight
    door_shut: { G: [-19.75, 3, S0], P: [-19.75, 12.5], idle: 30, secs: 5, steps: [{ look: [-19.75, 1.5, 3] }, { wait: 5 }] },
    door_open: { G: [-19.75, 3, S0], P: [-19.75, 12.5], idle: 30, secs: 5, doors: [[-19.75, 10.5, true]], steps: [{ look: [-19.75, 1.5, 3] }, { wait: 5 }] },
    den_swipe: { G: [-20, -6, S0], P: [-18.3, 8], saw: true, secs: 18, steps: [
      { go: [[-18.6, 9.6], [-19.75, 9.9]], mode: 'run' }, { door: [...DEN, true] }, { tp: [-19.75, 10.95] }, { door: [...DEN, false] }, { label: 'in den', wait: 0 }, { look: [-19.75, 1.5, 0] }, { wait: 16 }] },
    glass_court: { G: [-5, 9.2, N], P: [-5, 1.5], idle: 30, secs: 5, steps: [{ look: [-5, 1.5, 9] }, { wait: 5 }] },
    behind_far: { G: [-20, -6, N], P: [-20, 6], idle: 30, secs: 5, steps: [{ wait: 5 }] },
    behind_close: { G: [-20, -6, N], P: [-20, -0.2], idle: 30, secs: 5, steps: [{ wait: 5 }] },
    notice_far: { G: [-20, -8, S0], P: [-20, 8], idle: 30, secs: 6, steps: [{ wait: 6 }] },
    notice_crouch: { G: [-20, -8, S0], P: [-20, 8], idle: 30, secs: 6, steps: [{ crouch: true }, { wait: 6 }] },
    notice_near: { G: [-20, -6, S0], P: [-20, 2], idle: 30, secs: 4, steps: [{ wait: 4 }] },
    crouch_island: { G: [-0.5, -11.2, N], P: [-0.5, -15.8], idle: 60, secs: 5, steps: [{ crouch: true }, { look: [-0.5, 1, -11] }, { wait: 5 }] },
    hidden_plain: { G: [-20, -8, S0], P: [-20, 0], idle: 30, secs: 5, steps: [{ hidden: true }, { wait: 5 }] },
    // ---- hearing
    // A (kitchen) then, 3 s later while it's on the way, B (the SW gallery corner)
    two_noises: { G: [-20, 0, N], P: [-24.5, 18], idle: 30, secs: 35, steps: [
      { wait: 1 }, { noise: [-5.5, -15, 1] }, { wait: 3 }, { noise: [-11.75, 8.75, 1] }, { wait: 35 }] },
    lure_chase: { G: [-20, -6, S0], P: [-18.3, 8], saw: true, secs: 40, steps: [
      { go: [[-18.6, 9.6], [-19.75, 9.9]], mode: 'run' }, { door: [...DEN, true] }, { tp: [-19.75, 11.6] }, { door: [...DEN, false] },
      { go: [[-24.5, 12], [-24.5, 18]], mode: 'walk', label: 'hidden' }, { wait: 2 }, { noise: [-8, -15, 1] }, { wait: 40 }] },
    footsteps: { G: [-22, 7, N], P: [-24.5, 12], idle: 60, secs: 22, steps: [
      { go: [[-14.5, 12], [-24.5, 12], [-14.5, 12], [-24.5, 12]], mode: 'run', timeout: 20, label: 'ran' }, { wait: 1 }] },
    muffled: { G: [-20, 0, N], P: [-24.5, 18], idle: 40, secs: 12, steps: [{ wait: 1 }, { noise: [20, -15, 1] }, { wait: 12 }] },
    loud_rush: { G: [-20, 0, N], P: [-24.5, 18], idle: 40, secs: 20, steps: [{ wait: 1 }, { noise: [-11.75, -8.75, 1] }, { wait: 20 }] },
    // a noise inside the mudroom (unreachable): it should wait at the doorway facing in
    side_noise: { G: [11.75, 7, N], P: [19, -8], idle: 40, secs: 30, steps: [{ wait: 1 }, { noise: [17, -4, 1] }, { wait: 30 }] },
    // ---- upstairs: at the great room's upper rail, knocked down, then 2 m back from it
    upper: { G: [-18, 1, E], P: [-12.9, 1, 4.6], saw: true, secs: 75, steps: [
      { look: [-18, 2, 1] }, { until: (h, pl) => pl.isDown, timeout: 25, label: 'down' }, { until: (h, pl) => !pl.isDown, timeout: 10 },
      { tp: [-10.9, 1, 4.6], label: 'back from rail' }, { look: [-12, 5.5, 1] }, { wait: 75 }] },
    // ---- prowl: the player hidden in the mudroom the whole time
    prowl: { G: [-20, 0, E], P: [19, -8], secs: 300, photoUnstick: 4, steps: [{ wait: 300 }] },
  };
})()
