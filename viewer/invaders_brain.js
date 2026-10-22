import * as THREE from 'three';
import { UPPER_Y } from './invaders_nav.js';

// One invader: senses, a state machine, and the body's motion along nav paths. The squad
// (viewer/invaders.js) owns what they share: intel with radio delay, rooms cleared, hiding spots
// checked, noise claims, the leader's orders, the path planner's queue and the LOD schedule.
//
// What an invader knows comes only from its senses and its squad (never the player's true
// position):
// - sight (the Grimble's model, human-sized): a ray from its eyes to the player's, stopped by
//   walls, shut doors, closed blinds, tall furniture and (for a crouched player) low furniture they
//   duck behind; glass doesn't stop a look. A focal cone (+-55 deg) and a slower peripheral one
//   (+-100 deg), and anyone within 1.6 m all round. A notice meter (`aware`) fills faster the
//   closer, brighter and faster-moving the player is; it falls out of sight. A hidden player
//   can't be seen, but if it saw them climb in it goes and opens that spot.
// - hearing: window.__noise events, muffled by each wall between (the squad works them out).
// - the squad: a shout reaches those in earshot at once; the radio gets to everyone else after
//   a delay (longer once the leader is dead).
//
// Roles: gun (holds sightlines, shoots after a reaction + aim delay with a spread that tightens
// while tracking, needs a clear line of fire, takes cover when shot at), bat / knife (sweep rooms,
// chase, swing), leader (a gunman who gives the orders), watcher (a gunman outside who covers a
// door or the windows of one side; going out that way gets you shot).
//
// States: arrive (walk in to the entry) -> enter -> sweep (room by room: points, hiding spots)
// | scene (the opening drives it: invaders_opening.js) | post (watcher) | hold (a sightline the leader gave it) | respond (intel: go there) | engage
// (gun: sees you) | chase (melee: sees you) | strike | pursue (to where you were) | search
// (rooms round the loss) | investigate (a noise) | check (a hiding spot) | breach (kicks in a
// locked door) | cover | stagger | flee | dead.

export const WEAPONS = {
  pistol: { kind: 'gun', range: 35, damage: 26, rate: 0.7, burst: 1, burstGap: 0.0, spread: 0.032, aim: [0.55, 0.9], sfx: 'gunshot' },
  rifle: { kind: 'gun', range: 50, damage: 30, rate: 0.14, burst: 3, burstGap: 0.95, spread: 0.028, aim: [0.7, 1.1], sfx: 'gunshot' },
  bat: { kind: 'melee', range: 1.75, arc: 110, damage: 35, windup: 0.42, recover: 0.55, cooldown: 1.1, sfx: 'bat_swing', hitSfx: 'bat_hit' },
  knife: { kind: 'melee', range: 1.3, arc: 70, damage: 45, windup: 0.28, recover: 0.4, cooldown: 0.9, sfx: 'knife_swing', hitSfx: 'knife_hit' },
};

export const ROLE_DEFAULTS = {
  gun: { weapon: 'rifle', walk: 1.5, jog: 3.2, run: 4.6 },
  leader: { weapon: 'pistol', walk: 1.5, jog: 3.2, run: 4.6 },
  watcher: { weapon: 'rifle', walk: 1.4, jog: 3.0, run: 4.4 },
  bat: { weapon: 'bat', walk: 1.6, jog: 3.6, run: 5.5 },
  knife: { weapon: 'knife', walk: 1.6, jog: 3.6, run: 5.8 },
};

export const SENSE = {
  sight: 42, sightOut: 60,        // m (watchers outdoors see further)
  fov: 0.96, peri: 1.75,          // rad: half the focal cone, half the peripheral cone
  close: 1.6,                     // m all round
  noticeAt10: 0.85,               // s to notice a lit, standing, walking player 10 m ahead
  forget: 0.25,                   // /s the meter falls out of sight
  eye: 1.62, crouchEye: 1.0,
  hearing: 34,                    // m for a loudness-1 noise in the open
  muffle: 0.55,                   // loudness kept through each wall
};

const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
const rand = (a, b) => a + Math.random() * (b - a);
const V3 = THREE.Vector3;
const _a = new V3(), _b = new V3(), _c = new V3();

let NEXT_ID = 1;

export class Invader {
  constructor(sq, { role = 'bat', pos, layer = 'ground', entry = null, post = null, weapon = null, name = null }) {
    this.sq = sq;
    this.id = NEXT_ID++;
    this.name = name ?? `inv${this.id}`;
    this.role = role;
    const R = ROLE_DEFAULTS[role] ?? ROLE_DEFAULTS.bat;
    this.speeds = { walk: R.walk, jog: R.jog, run: R.run, search: (R.walk + R.jog) / 2.2 };
    this.weaponName = weapon ?? R.weapon;
    this.weapon = WEAPONS[this.weaponName];
    this.gun = this.weapon.kind === 'gun';
    this.pos = pos.clone();
    this.layer = layer;
    this.yaw = 0; this.lookYaw = 0; this.pitch = 0;
    this.vel = new V3();
    this.moveSpeed = 0;              // what the body animates (m/s)
    this.crouch = 0;
    this.entry = entry; this.post = post;
    this.health = 100; this.maxHealth = 100; this.alive = true;
    this.team = 'invader';
    this.radius = 0.3; this.height = 1.8;
    this.time = 0;
    this.state = null; this.st = 0;  // state, time in it
    this.aware = 0; this.seenNow = false; this.seenAt = -1e9; this.visAt = -1e9;
    this.lastSeen = null;            // {pos (feet), t, vel, layer}
    this.know = null;                // {pos, t, src}: the latest it has (its own or the squad's)
    this.lead = null;                // a noise it's after
    this.glance = null;              // {yaw, until}: turn its head toward something
    this.hideSeen = null;            // the hiding spot it saw the player get into
    this.path = null; this.pathI = 0; this.goal = null; this.planning = false; this.planFail = 0;
    this.doorWait = null;
    this.anim = { aim: 0, swing: -1, stagger: 0, die: 0, kick: -1, phase: Math.random() * 6 };
    this.stats = { shots: 0, hits: 0, swings: 0, strikes: 0, sightings: 0, heard: 0, doors: 0, spots: 0, rooms: 0, plans: 0, fails: 0, jams: 0 };
    this.tier = 0; this.acc = 0; this.lastThink = 0;
    this.light = 1;
    this.set(this.role === 'watcher' ? 'post' : entry ? 'arrive' : 'sweep');
  }

  get floorY() { return this.pos.y; }
  set(state, why = null) {
    if (state === this.state) return;
    this.prev = this.state;
    this.state = state; this.st = 0; this.why = why;
    this.sub = null;
    if (state !== 'engage' && state !== 'cover') { this.aimT = 0; this.burstLeft = 0; }
    if (state !== 'strike') this.strikeT = null;
    this.sq.log?.(this, state, why);
  }

  // ---------------------------------------------------------------- the combat target
  target() {
    if (this._target) return this._target;
    const me = this;
    this._target = {
      id: `invader:${this.id}`, kind: 'invader', team: 'invader', invader: this,
      position: () => me.pos, radius: this.radius, height: this.height,
      get health() { return me.health; }, set health(v) { me.health = v; },
      get maxHealth() { return me.maxHealth; },
      get alive() { return me.alive; },
      hit: (damage, info) => me.onHit(damage, info),
      // (for the weapons workstream: a stealth takedown is from behind by someone it doesn't know is there)
      unaware: () => me.aware < 0.5 && me.time - me.seenAt > 4 && !['engage', 'chase', 'strike', 'cover'].includes(me.state),
      facing: () => me.yaw,
    };
    return this._target;
  }

  onHit(damage, info = {}) {
    if (!this.alive) return;
    this.health -= damage;
    const from = info.from?.position?.() ?? info.from?.pos ?? null;
    this.stats.hitsTaken = (this.stats.hitsTaken ?? 0) + 1;
    this.lastHitAt = this.time;
    // (the body module plays the hit / fall the right way: blown forward from behind)
    const d = info.dir;
    this.hitFromBehind = !!d && d.x * Math.sin(this.yaw) + d.z * Math.cos(this.yaw) > 0.3;
    this.fellForward = this.hitFromBehind;
    if (this.health <= 0) { this.die(info); return; }
    // stagger, call out, and know where it came from
    this.anim.stagger = damage > 40 ? 0.9 : 0.5;
    this.staggerUntil = this.time + this.anim.stagger;
    window.__sfx?.play?.('invader_shout', this.pos);
    if (from) {
      const p = from.isVector3 ? from : new V3(from.x, from.y, from.z);
      this.sawAt(p, 'hit');
      this.sq.report(this, p, 'hit', true);
    }
    this.shotAt = this.time;
    this.aware = Math.max(this.aware, 0.85);
    if (from) this.glance = { yaw: Math.atan2(from.x - this.pos.x, from.z - this.pos.z), until: this.time + 2, p: from.clone?.() ?? null };
    // badly hurt: run (the leader holds on); else after whoever did it
    if (this.health < 30 && this.role !== 'leader') this.set('flee', 'hurt');
    else if (!['engage', 'chase', 'strike', 'cover', 'flee'].includes(this.state)) this.set('pursue', 'hit');
  }

  die(info) {
    this.alive = false;
    this.health = 0;
    this.set('dead', info?.weapon ?? 'hit');
    this.anim.die = 0.001;
    this.dieYaw = this.yaw + (Math.random() - 0.5) * 0.8;
    this.path = null;
    window.__sfx?.play?.('body_fall', this.pos);
    this.sq.onDeath(this, info);
  }

  // ---------------------------------------------------------------- senses
  eyePos(out = new V3()) { return out.set(this.pos.x, this.pos.y + (this.crouch > 0.5 ? SENSE.crouchEye : SENSE.eye), this.pos.z); }
  muzzle(out = new V3()) {
    const m = this.rig?.muzzle?.();
    if (m) return out.copy(m);
    const y = this.pos.y + (this.crouch > 0.5 ? 1.0 : 1.42);
    return out.set(this.pos.x + Math.sin(this.lookYaw) * 0.45 + Math.cos(this.lookYaw) * 0.12, y, this.pos.z + Math.cos(this.lookYaw) * 0.45 - Math.sin(this.lookYaw) * 0.12);
  }

  perceive(dt, ctx) {
    const P = ctx.player, eye = ctx.eye, me = this.eyePos(_a);
    const outside = this.role === 'watcher' || !this.sq.world.nav.inHouse(this.pos.x, this.pos.z);
    const range = outside ? SENSE.sightOut : SENSE.sight;
    let vis = false, T = Infinity;
    const d = me.distanceTo(eye);
    if (!ctx.playerGone && !P.hidden && d <= range) {
      const flat = Math.hypot(eye.x - me.x, eye.z - me.z);
      const off = Math.abs(wrap(Math.atan2(eye.x - me.x, eye.z - me.z) - this.lookYaw));
      // (all round, close: unless they creep up crouched and slow; that's how a takedown happens)
      const vP = P.vel ? Math.hypot(P.vel.x, P.vel.z) : 0;
      const close = flat <= SENSE.close && Math.abs(eye.y - me.y) < 2.2 && !(P.crouching && vP < 1.5);
      const cone = off <= SENSE.fov ? 1 : off <= SENSE.peri ? 2 : 0;
      if ((cone || close) && this.sq.sightClear(me, eye, !!P.crouching)) {
        vis = true;
        const v = P.vel ? Math.hypot(P.vel.x, P.vel.z) : 1.5;
        T = SENSE.noticeAt10 * Math.max(0.15, flat / 10);
        T *= P.crouching ? 1.7 : 1;
        T *= v < 0.3 ? 1.4 : v > 5 ? 0.6 : 1;
        T /= ctx.lit;
        if (cone === 2) T *= 2.6;
        if (close) T = Math.min(T, 0.3);
        // it's expecting you: the squad has had contact lately, or a watcher sees someone outside
        if (this.sq.alert > 0.5 || this.time - this.seenAt < 12) T *= 0.45;
        if (this.role === 'watcher' && ctx.playerOutside) T *= 0.5;
      }
    }
    if (vis) this.aware = Math.min(1, this.aware + dt / T);
    else this.aware = Math.max(0, this.aware - SENSE.forget * dt);
    if (vis && this.aware >= 1) this.visAt = this.time;
    const seen = !P.hidden && !ctx.playerGone && this.aware > 0.9 && this.time - this.visAt < 0.3;
    if (seen && !this.seenNow) { this.stats.sightings++; window.__sfx?.play?.('invader_alert', this.pos); }
    this.seenNow = seen;
    if (seen) {
      const feet = P.pos;
      if (this.lastSeen && this.time - this.lastSeen.t < 0.4 && this.time > this.lastSeen.t) {
        const k = 1 / (this.time - this.lastSeen.t);
        this.trackV = (this.trackV ?? new V3()).lerp(_b.set((feet.x - this.lastSeen.pos.x) * k, 0, (feet.z - this.lastSeen.pos.z) * k), 0.3);
      } else this.trackV = new V3();
      this.sawAt(feet, 'sight');
      this.sq.report(this, feet, 'sight');
    } else if (vis && this.aware > 0.35) {
      this.glance = { yaw: Math.atan2(eye.x - me.x, eye.z - me.z), until: this.time + 1.2, p: eye.clone() };
    }
    // it saw them climb into a hiding spot: it knows which one
    if (P.hidden && !this._wasHidden && this.time - this.seenAt < 1.5 && P.hideSpot) {
      this.hideSeen = { spot: P.hideSpot, t: this.time };
      this.sq.report(this, P.pos, 'hide', true);
    }
    this._wasHidden = !!P.hidden;
  }

  // something tells it the player is at p (its eyes, a hit from there)
  sawAt(p, src) {
    this.seenAt = this.time;
    this.lastSeen = { pos: p.clone(), t: this.time, layer: this.sq.world.nav.layerAt(p.x, p.y, p.z).name };
    this.know = { pos: p.clone(), t: this.time, src, own: true };
  }

  // the squad passes on intel (after the shout / the radio's delay)
  told(info) {
    if (!this.alive) return;
    if (this.know && this.know.t >= info.t) return;
    this.know = { pos: info.pos.clone(), t: info.t, src: info.src, own: false, kind: info.kind };
    this.toldAt = this.time;
    this.sq.event?.('told', { id: this.id, src: info.src });
  }

  // a heard noise (the squad muffles it through walls first)
  hear(rec) {
    if (!this.alive) return;
    this.stats.heard++;
    const pri = (r) => r.loud / (1 + r.d / 15);
    if (!this.lead || this.time - this.lead.t > 15 || pri(rec) >= 0.6 * pri(this.lead)) { this.lead = { ...rec, t: this.time }; this.leadNew = true; }
    // a glance toward it whatever it's doing
    this.glance = { yaw: Math.atan2(rec.pos.x - this.pos.x, rec.pos.z - this.pos.z), until: this.time + 1.5, p: rec.pos.clone() };
  }

  // ---------------------------------------------------------------- the brain (LOD-scheduled)
  think(dt, ctx) {
    this.time += dt;
    this.st += dt;
    if (!this.alive) { this.anim.die = Math.min(1, this.anim.die + dt / 0.7); return; }
    if (this.staggerUntil > this.time) { this.stop(); return; }
    this.perceive(dt, ctx);
    if (ctx.playerGone) { if (!['post', 'sweep', 'idle'].includes(this.state)) { this.set('idle', 'player dead'); this.stop(); } return; }
    const st = this.state;
    // the opening (invaders_opening.js) drives it: its senses still run (above), the script decides
    if (st === 'scene') { if (this.sq.opening) this.sq.opening.think(this, dt, ctx); else this.set('sweep'); return; }
    if (st === 'flee') return this.flee(dt, ctx);
    if (st === 'strike') return this.strike(dt, ctx);
    if (st === 'breach') { if (this.seenNow) this.react(dt, ctx); else this.breach(dt, ctx); return; }
    if (this.seenNow) return this.react(dt, ctx);
    // a hiding spot it saw them get into
    if (this.hideSeen && !['check'].includes(st) && this.time - this.hideSeen.t < 60) {
      this.startCheck(this.hideSeen.spot, true); this.hideSeen = null; return;
    }
    // orders: the squad decides what intel means for it (respond / hold / search)
    if (this.order) { const o = this.order; this.order = null; this.obey(o); }
    // a fresh noise
    if (this.leadNew) {
      this.leadNew = false;
      if (this.role !== 'watcher' && !['engage', 'chase', 'pursue', 'check'].includes(st) && this.sq.claimNoise(this, this.lead)) {
        this.set('investigate', this.lead.source); this.sub = { lead: this.lead };
      }
    }
    switch (this.state) {
      case 'arrive': return this.arrive(dt, ctx);
      case 'post': return this.postStep(dt, ctx);
      case 'hold': return this.holdStep(dt, ctx);
      case 'respond': return this.respond(dt, ctx);
      case 'engage': case 'chase': case 'pursue': return this.pursue(dt, ctx);
      case 'cover': return this.cover(dt, ctx);
      case 'search': return this.search(dt, ctx);
      case 'investigate': return this.investigate(dt, ctx);
      case 'check': return this.check(dt, ctx);
      case 'idle': this.stop(); return this.scan(dt);
      default: return this.sweep(dt, ctx);
    }
  }

  // ---- it sees the player
  react(dt, ctx) {
    const P = ctx.player, feet = P.pos;
    if (this.gun) {
      if (this.state !== 'engage' && this.state !== 'cover') this.set('engage', 'seen');
      return this.engage(dt, ctx);
    }
    // melee: run at them; strike when close
    if (this.state !== 'chase') this.set('chase', 'seen');
    const d = Math.hypot(feet.x - this.pos.x, feet.z - this.pos.z), dy = Math.abs(feet.y - this.pos.y);
    if (d <= this.weapon.range + 0.15 && dy < 1.2 && this.time > (this.nextStrike ?? 0) && !P.isDown) { this.startStrike(feet); return; }
    // close and in the open: straight at them; else along a path
    const L = this.sq.world.nav.layers.find((l) => l.name === this.layer);
    if (d < 6 && dy < 0.6 && this.sq.world.nav.clearWalk(L, this.pos.x, this.pos.z, feet.x, feet.z)) {
      this.path = null;
      this.steer(dt, feet.x, feet.z, this.speeds.run);
    } else this.goTo(feet, this.speeds.run, { moveTol: 0.8, every: 0.35 });
    this.lookAt(feet, dt);
  }

  // a gunman with the player in sight: stop, raise, aim (reaction + aim delay), fire while there's
  // a clear line of fire; a teammate in the way: step aside
  engage(dt, ctx) {
    const P = ctx.player, W = this.weapon, feet = P.pos;
    const aimP = _c.set(feet.x, feet.y + (P.crouching ? 0.7 : 1.15), feet.z);
    const d = this.pos.distanceTo(feet);
    this.lookAt(feet, dt, 8);
    // too far for the weapon: close in (jog)
    if (d > W.range * 0.92) { this.goTo(feet, this.speeds.jog, { moveTol: 2, every: 0.8 }); this.anim.aim = Math.max(0, this.anim.aim - dt * 2); return; }
    if (!this.noFire || this.noFire < 1.2) this.stop();
    this.anim.aim = Math.min(1, this.anim.aim + dt * 3);
    this.crouch = this.state === 'cover' && this.sub?.crouch ? 1 : 0;
    if (!this.aimT) { this.aimT = 0; this.aimNeed = rand(...W.aim) * (0.7 + 0.3 * Math.min(1, d / 15)) + rand(0.15, 0.35); }
    this.aimT += dt;
    if (this.aimT < this.aimNeed) return;
    // fire (bursts)
    this.fireT = (this.fireT ?? 0) - dt;
    if (this.fireT > 0) return;
    const m = this.muzzle(_a), lof = this.sq.lineOfFire(this, m, aimP);
    if (lof !== true) {
      // a teammate in the way: sidestep; glass or furniture between (it sees them through a
      // window): go round to them (the path takes it through a door), still watching
      this.noFire = (this.noFire ?? 0) + dt;
      // (a watcher keeps its post: it has reported them, the ones inside will come)
      if (lof === 'mate' || this.noFire < 1.2 || this.role === 'watcher') { if (lof === 'mate') this.sidestep(feet); this.fireT = 0.3; return; }
      this.goTo(feet, this.speeds.jog, { moveTol: 1.5, every: 1.0 });
      this.anim.aim = Math.max(0.3, this.anim.aim - dt * 2);
      return;
    }
    this.noFire = 0;
    const v = P.vel ? Math.hypot(P.vel.x, P.vel.z) : 0;
    // a snap shot first, steadier the longer it tracks (2 s); each shot of a burst kicks it off
    const track = Math.min(1, (this.aimT - this.aimNeed) / 2);
    let spread = W.spread * (1 + v / 4) * (1.7 - 0.9 * track);
    spread *= 1 + 0.5 * (W.burst - (this.burstLeft || W.burst));
    if (this.time - (this.shotAt ?? -1e9) < 1.5) spread *= 1.8;   // it's being shot at
    if (this.anim.stagger > 0 && this.staggerUntil > this.time - 0.5) spread *= 2;
    this.sq.fire(this, m, aimP, spread);
    this.stats.shots++;
    this.burstLeft = (this.burstLeft || W.burst) - 1;
    this.fireT = this.burstLeft > 0 ? W.rate : W.rate + W.burstGap * rand(0.8, 1.3);
    // under fire, between bursts: cover nearby
    if (this.burstLeft <= 0 && this.time - (this.shotAt ?? -1e9) < 4 && this.state !== 'cover' && ctx.tier === 0) {
      const c = this.sq.findCover(this, feet);
      if (c) { this.set('cover', 'shot at'); this.sub = { at: c.at, crouch: c.crouch, until: this.time + rand(4, 8) }; }
    }
  }

  cover(dt, ctx) {
    const S = this.sub;
    if (!S) { this.set('pursue'); return; }
    if (this.seenNow && this.pos.distanceTo(S.at) < 0.5) return this.engage(dt, ctx);
    const r = this.goTo(S.at, this.speeds.run, { moveTol: 0.3 });
    if (r === 'arrived') { this.crouch = S.crouch ? 1 : 0; this.lookAt(this.know?.pos, dt); if (this.time > S.until || !this.seenNow && this.st > 3) this.set('pursue', 'from cover'); }
    else if (r === 'nopath') this.set('pursue', 'no cover');
  }

  sidestep(feet) {
    const s = Math.random() < 0.5 ? 1 : -1, a = Math.atan2(feet.x - this.pos.x, feet.z - this.pos.z) + s * Math.PI / 2;
    this.goTo(_b.set(this.pos.x + Math.sin(a) * 1.2, this.pos.y, this.pos.z + Math.cos(a) * 1.2), this.speeds.jog, { moveTol: 0.3 });
  }

  startStrike(feet) {
    this.set('strike');
    this.strikeT = 0; this.strikeHit = false;
    this.strikeAt = feet.clone();
    this.anim.swing = 0;
    this.stop();
    this.stats.swings++;
    window.__sfx?.play?.(this.weapon.sfx, this.pos);
  }
  strike(dt, ctx) {
    const W = this.weapon;
    this.strikeT += dt;
    this.anim.swing = Math.min(1, this.strikeT / (W.windup + W.recover));
    if (this.seenNow) this.lookAt(ctx.player.pos, dt, 6);
    if (!this.strikeHit && this.strikeT >= W.windup) {
      this.strikeHit = true;
      const r = this.sq.melee(this, W);
      if (r) this.stats.strikes++;
    }
    if (this.strikeT >= W.windup + W.recover) {
      this.anim.swing = -1;
      this.nextStrike = this.time + W.cooldown * rand(0.8, 1.2) - W.recover;
      this.set(this.seenNow ? 'chase' : 'pursue');
    }
  }

  // lost sight (or told where they are): there, then on their heading a moment, then search
  pursue(dt, ctx) {
    const K = this.know;
    this.anim.aim = Math.max(0, this.anim.aim - dt * 1.5);
    this.crouch = 0;
    if (this.role === 'watcher') { this.set('post', 'lost them'); return; }
    if (!K) { this.set('sweep', 'nothing known'); return; }
    if (this.state !== 'pursue') { this.set('pursue'); }
    const S = this.sub ??= { target: K.pos.clone(), t0: this.time, v: (this.trackV ?? new V3()).clone(), phase: 'go' };
    if (K.pos.distanceTo(S.target) > 1.5) { S.target.copy(K.pos); S.t0 = this.time; S.phase = 'go'; }
    const speed = this.gun ? this.speeds.jog : this.speeds.run;
    if (S.phase === 'go') {
      const r = this.goTo(S.target, speed, { moveTol: 1.0, breach: this.sq.breachOK(this, S.target) });
      if (r === 'arrived' || this.time - S.t0 > 25 || r === 'nopath') {
        if (r === 'nopath' && this.planFail < 3 && this.time - S.t0 < 3) return;
        if (S.v.length() > 1 && this.time - K.t < 4) {
          S.phase = 'push'; S.t1 = this.time;
          S.push = _b.copy(this.pos).addScaledVector(S.v.clone().normalize(), Math.min(8, S.v.length() * 2)).clone();
        } else this.startSearch(S.target);
      }
      this.lookAlong(dt);
      return;
    }
    const r = this.goTo(S.push, speed, { moveTol: 1.0 });
    if (r !== 'moving' || this.time - S.t1 > 3) this.startSearch(S.target);
    this.lookAlong(dt);
  }

  // ---- arrival: from where it spawned to its entry, through it, then to work
  arrive(dt, ctx) {
    const E = this.entry;
    if (!E) { this.set('sweep'); return; }
    if (!this.sub) this.sub = { phase: 'approach' };
    const S = this.sub;
    if (S.phase === 'approach') {
      const r = this.goTo(E.outside, this.speeds.jog, { moveTol: 0.6 });
      this.lookAlong(dt);
      if (r === 'arrived') S.phase = E.smash && !this.sq.glassBroken ? 'smash' : 'in';
      else if (r === 'nopath' && this.planFail > 4) this.set('sweep', 'no way in');
      return;
    }
    if (S.phase === 'smash') {
      // the great room's glass: a few blows, then it's open
      this.stop();
      this.lookAt(E.inside, dt, 4);
      S.t = (S.t ?? 0) + dt;
      if (this.anim.swing < 0 && S.t > 0.3) { this.anim.swing = 0; S.sw = 0; window.__sfx?.play?.('bat_swing', this.pos); }
      if (this.anim.swing >= 0) { S.sw += dt; this.anim.swing = Math.min(1, S.sw / 0.9); if (S.sw >= 0.9) { this.anim.swing = -1; S.n = (S.n ?? 0) + 1; window.__noise?.emit({ position: E.inside.clone(), loudness: 1.2, source: 'glass_blow', team: 'invader' }); } }
      if ((S.n ?? 0) >= 2 || this.sq.glassBroken) { this.sq.breakGlass(); S.phase = 'in'; }
      return;
    }
    // its door is locked (to them: the outer doors while the opening ran): kick it in
    if (E.door?.locked?.()) {
      const at = _b.set(E.centre.x + E.normal.x * 0.85, this.pos.y, E.centre.y + E.normal.y * 0.85);
      const r = this.goTo(at, this.speeds.walk, { moveTol: 0.35 });
      if (r === 'arrived' || (r === 'nopath' && this.planFail > 2)) this.startBreach(E.door);
      else this.lookAlong(dt);
      return;
    }
    const r = this.goTo(E.inside, this.speeds.jog, { moveTol: 0.6 });
    this.lookAlong(dt);
    // (in: after the player if it knows where they were lately, else a room to sweep)
    if (r === 'arrived' || (r === 'nopath' && this.planFail > 4)) { this.inside = true; this.set(this.task ?? (this.know && this.time - this.know.t < 30 ? 'respond' : 'sweep'), 'in'); this.sq.arrived(this); }
  }

  // ---- watcher: at its post, facing what it covers, looking round a little
  postStep(dt, ctx) {
    const Pt = this.post;
    if (!Pt) { this.set('sweep'); return; }
    if (this.know && this.time - this.know.t < 6 && this.sq.inHouseP(this.know.pos) === false && this.know.pos.distanceTo(this.pos) < 30) {
      // someone outside, reported near: go and look (a short way from its post)
      const r = this.goTo(this.know.pos, this.speeds.jog, { moveTol: 1.5 });
      this.lookAlong(dt);
      if (r === 'arrived') this.know = null;
      return;
    }
    const r = this.goTo(Pt.at, this.speeds.jog, { moveTol: 0.6 });
    if (r === 'arrived') { this.stop(); this.scan(dt, Pt.yaw, Pt.amp ?? 0.5, 7); }
    else this.lookAlong(dt);
  }

  // ---- hold: a gunman the leader posted on a sightline (a doorway, the stair)
  holdStep(dt, ctx) {
    const H = this.sub ?? this.holdAt;
    if (!H) { this.set('sweep'); return; }
    this.sub = H;
    const r = this.goTo(H.at, this.speeds.jog, { moveTol: 0.5 });
    if (r === 'arrived') { this.stop(); this.scan(dt, H.yaw, 0.35, 6); if (this.time > H.until) this.set('sweep', 'hold over'); }
    else if (r === 'nopath' && this.planFail > 3) this.set('sweep', 'no hold');
    else this.lookAlong(dt);
  }

  // ---- respond: intel says the player is (was) at a place: go (melee fast, guns jog)
  respond(dt, ctx) {
    const K = this.know;
    if (!K) { this.set('sweep'); return; }
    this.sub ??= { t0: this.time };
    const r = this.goTo(K.pos, this.gun ? this.speeds.jog : this.speeds.run, { moveTol: 1.2, breach: this.sq.breachOK(this, K.pos) });
    this.lookAlong(dt);
    if (r === 'arrived' || this.time - this.sub.t0 > 40 || (r === 'nopath' && this.planFail > 3)) this.startSearch(K.pos);
  }

  // ---- search round a loss: the rooms nearest it, point by point, their hiding spots
  startSearch(at) {
    this.set('search');
    this.sub = { centre: at.clone(), plan: this.sq.searchPlan(this, at), i: 0, phase: 'go', t: this.time };
  }
  search(dt, ctx) {
    const S = this.sub;
    if (!S || S.i >= S.plan.length) { this.sq.searched(this, S?.centre); this.set('sweep', 'search done'); return; }
    if (this.glance && this.time < this.glance.until) { this.stop(); this.turnLook(this.glance.yaw, dt, 5); return; }
    const pt = S.plan[S.i];
    if (pt.spot) { this.startCheck(pt.spot, false, () => { S.i++; this.set('search'); this.sub = S; }); return; }
    if (S.phase === 'go') {
      const r = this.goTo(pt.at, this.speeds.search, { moveTol: 0.6 });
      this.lookAlong(dt);
      if (r === 'arrived' || r === 'nopath' && this.planFail > 2 || this.time - S.t > 20) { S.phase = 'look'; S.until = this.time + (pt.dwell ?? rand(1.2, 2.5)); this.scanBase = this.lookYaw; }
      return;
    }
    this.stop();
    this.scan(dt, this.scanBase, 1.1, 3.5);
    if (this.time >= S.until) { if (pt.room) this.sq.roomCleared(pt.room, this); S.i++; S.phase = 'go'; S.t = this.time; }
  }

  // ---- sweep: the room the squad gives it, point by point, checking hiding spots
  sweep(dt, ctx) {
    if (!this.inside && this.role !== 'watcher' && this.entry) { this.set('arrive'); return; }
    let S = this.sub;
    if (!S || S.i >= S.plan.length) {
      if (S?.room) { this.sq.roomCleared(S.room, this); this.stats.rooms++; }
      const room = this.sq.nextRoom(this);
      if (!room) { this.stop(); this.scan(dt); return; }
      S = this.sub = { room, plan: this.sq.roomPlan(this, room), i: 0, phase: 'go', t: this.time };
    }
    if (this.glance && this.time < this.glance.until) { this.stop(); this.turnLook(this.glance.yaw, dt, 5); return; }
    const pt = S.plan[S.i];
    if (!pt) { S.i++; return; }
    if (pt.spot) { this.startCheck(pt.spot, false, () => { S.i++; this.set('sweep'); this.sub = S; }); return; }
    if (S.phase === 'go') {
      const speed = this.sq.alert > 0.5 ? this.speeds.search : this.speeds.walk;
      const r = this.goTo(pt.at, speed, { moveTol: 0.6 });
      this.lookAlong(dt);
      if (r === 'arrived' || (r === 'nopath' && this.planFail > 2) || this.time - S.t > 30) { S.phase = 'look'; S.until = this.time + (pt.dwell ?? rand(0.8, 2.2)); this.scanBase = this.lookYaw; }
      return;
    }
    this.stop();
    this.scan(dt, this.scanBase, 1.0, 4);
    if (this.time >= S.until) { S.i++; S.phase = 'go'; S.t = this.time; }
  }

  // ---- a noise: go and look (fast if loud), a look round, a spot or two near it
  investigate(dt, ctx) {
    const S = this.sub, L = S?.lead;
    if (!L) { this.set('sweep'); return; }
    if (!S.phase) { S.phase = 'go'; S.t0 = this.time; }
    if (S.phase === 'go') {
      const fast = L.loud >= 1.2 || L.d < 10;
      const r = this.goTo(L.pos, fast ? this.speeds.jog : this.speeds.search, { moveTol: 1.2, breach: false });
      this.lookAlong(dt, L.pos);
      if (r === 'arrived' || this.time - S.t0 > 35 || (r === 'nopath' && this.planFail > 2)) { S.phase = 'look'; S.until = this.time + rand(2.5, 4.5); this.scanBase = Math.atan2(L.pos.x - this.pos.x, L.pos.z - this.pos.z); }
      return;
    }
    this.stop();
    this.scan(dt, this.scanBase, 1.3, 3.5);
    if (this.time >= S.until) {
      this.sq.releaseNoise(this, L);
      // a short search round it (a spot or two)
      this.startSearch(L.pos);
      this.sub.plan = this.sub.plan.slice(0, 3);
    }
  }

  // ---- a hiding spot: to its mouth, open it; the player inside is dragged out
  startCheck(spot, sure, then = null) {
    const back = this.state === 'check' ? this.checkThen : null;
    this.set('check', sure ? 'saw them hide' : 'spot');
    this.sub = { spot, sure, phase: 'go', t: this.time };
    this.checkThen = then ?? back;
  }
  check(dt, ctx) {
    const S = this.sub, sp = S?.spot;
    if (!sp) { this.set('sweep'); return; }
    if (S.phase === 'go') {
      const r = this.goTo(sp.exit, S.sure ? this.speeds.run : this.speeds.search, { moveTol: 0.5 });
      this.lookAlong(dt, sp.eye);
      if (r === 'arrived' || (r === 'nopath' && this.planFail > 2) || this.time - S.t > 25) { S.phase = 'open'; S.t1 = this.time; this.stop(); }
      return;
    }
    this.stop();
    this.lookAt(sp.eye, dt, 6);
    if (this.time - S.t1 < 0.6) return;
    if (S.phase === 'open') {
      S.phase = 'done';
      this.stats.spots++;
      this.sq.spotChecked(sp, this);
      const P = ctx.player;
      if (P.hideSpot && P.hideSpot.node === sp.node) {
        // found: out they come
        window.__sfx?.play?.('invader_alert', this.pos);
        this.sq.dragOut(this, sp);
        this.aware = 1; this.visAt = this.time + 0.1; this.sawAt(P.pos, 'found');
        this.sq.report(this, P.pos, 'found', true);
        this.set(this.gun ? 'engage' : 'chase', 'found');
        return;
      }
      window.__sfx?.play?.('cabinet_open', sp.exit);
    }
    if (this.time - S.t1 > 1.4) { const f = this.checkThen; this.checkThen = null; if (f) f(); else this.set('sweep'); }
  }

  // ---- a locked door between it and the player: kick it in (loud), then through
  startBreach(door) {
    this.set('breach', door.name);
    this.sub = { door, n: 0, t: 0 };
  }
  breach(dt, ctx) {
    const S = this.sub, D = S?.door;
    if (!D || !D.locked()) { this.set(this.prev && this.prev !== 'breach' ? this.prev : 'pursue'); return; }
    this.stop();
    this.lookAt(_b.set(D.centre.x, this.pos.y + 1, D.centre.y), dt, 6);
    S.t += dt;
    if (S.t >= 1.15) {
      S.t = 0; S.n++;
      this.anim.kick = 0;
      window.__noise?.emit({ position: new V3(D.centre.x, this.pos.y + 1, D.centre.y), loudness: 1.4, source: 'door_kick', team: 'invader' });
      window.__sfx?.play?.('door_kick', new V3(D.centre.x, this.pos.y + 1, D.centre.y));
      if (S.n >= 4) { this.sq.breakDoor(D); this.stats.breaches = (this.stats.breaches ?? 0) + 1; }
    }
    if (this.anim.kick >= 0) { this.anim.kick += dt / 0.6; if (this.anim.kick >= 1) this.anim.kick = -1; }
  }

  // ---- hurt: away from the player, out of the house, then it waits there
  flee(dt, ctx) {
    this.anim.aim = 0;
    this.sub ??= { to: this.sq.fleeTarget(this, ctx.player.pos), t0: this.time };
    const r = this.goTo(this.sub.to, this.speeds.run * 0.9, { moveTol: 1.5 });
    this.lookAlong(dt);
    if (r !== 'moving' && this.time - this.sub.t0 > 2) { this.stop(); this.scan(dt); if (this.seenNow && this.gun) this.engage(dt, ctx); }
  }

  // orders from the leader (or the squad when there's none): {kind: 'respond'|'hold'|'search', ...}
  obey(o) {
    if (['engage', 'chase', 'strike', 'flee', 'breach', 'check', 'cover'].includes(this.state) || !this.alive) return;
    if (!this.inside && this.role !== 'watcher' && this.entry && this.state === 'arrive') { this.task = o.kind === 'hold' ? 'hold' : null; if (o.kind === 'hold') this.holdAt = o; return; }
    if (o.kind === 'respond') { this.set('respond', o.why); }
    else if (o.kind === 'hold') { this.set('hold', o.why); this.sub = o; }
    else if (o.kind === 'search') this.startSearch(o.at);
  }

  // ---------------------------------------------------------------- movement
  stop() { this.path = null; this.moveSpeed = 0; this.vel.set(0, 0, 0); }

  // keep a route to `target` and follow it: 'moving' | 'arrived' | 'nopath' | 'planning'
  goTo(target, speed, { moveTol = 0.6, every = 0.8, breach = false } = {}) {
    const g = this.goal, dg = g ? Math.hypot(g.x - target.x, g.z - target.z) + Math.abs(g.y - target.y) * 0.5 : Infinity;
    if (Math.hypot(target.x - this.pos.x, target.z - this.pos.z) < moveTol && Math.abs(target.y - this.pos.y) < 1.5) { this.path = null; this.moveSpeed = 0; this.goal = target.clone(); this.arrivedAt = this.time; return 'arrived'; }
    // (a target off the nav, in furniture: the end of its route there is as close as it gets)
    if (!this.path && this.doneGoal && this.doneGoal.distanceTo(target) < Math.max(0.5, moveTol)) { this.moveSpeed = 0; return this.donePartial ? 'nopath' : 'arrived'; }
    if (!this.planning && (dg > 2.5 || breach !== !!this.planBreach || (dg > moveTol && this.time - (this.planAt ?? -1e9) > every) || (!this.path && this.time - (this.planAt ?? -1e9) > 0.5))) {
      this.goal = target.clone();
      this.planBreach = breach;
      this.doneGoal = null;
      this.sq.requestPath(this, target, { breach });
    }
    this.wantSpeed = speed;
    if (this.planning && !this.path) return 'planning';
    if (!this.path) return this.planFail > 0 ? 'nopath' : 'planning';
    return 'moving';
  }

  // the planner's answer
  gotPath(path, failed) {
    this.planning = false;
    this.planAt = this.time;
    if (!path) { this.planFail++; this.stats.fails++; this.path = null; return; }
    // (a route to the nearest place it can get to, not the goal itself: it counts as no way there once walked)
    this.planFail = 0;
    this.stats.plans++;
    this.path = path; this.pathI = path.length > 1 ? 1 : 0;
    this.doneGoal = null;
    this.progress = null;
  }

  // every frame: along the path (doors opened on the way), pushed out of walls and each other
  move(dt, ctx) {
    if (!this.alive) { this.moveSpeed = 0; return; }
    if (this.staggerUntil > this.time) { this.moveSpeed = 0; return; }
    const P = this.path;
    if (!P) { if (!this.steering) this.moveSpeed *= Math.max(0, 1 - dt * 8); this.settle(dt); return; }
    let w = P[this.pathI];
    // a door on the way: open it first (wait while it swings); a locked one: kick it in, or round
    if (w.door && !w.door.isOpen()) {
      const D = w.door, dd = Math.hypot(D.centre.x - this.pos.x, D.centre.y - this.pos.z);
      if (dd < 1.35) {
        this.moveSpeed = 0;
        this.yawTo(Math.atan2(D.centre.x - this.pos.x, D.centre.y - this.pos.z), dt, 6);
        if (D.locked()) {
          if (this.sq.breachOK(this, this.goal)) { this.startBreach(D); return; }
          this.path = null; this.sq.requestPath(this, this.goal, {}); return;
        }
        if (!D.opening()) { D.open(); this.stats.doors++; this.sq.doorOpened(D, this); }
        this.doorWait = (this.doorWait ?? 0) + dt;
        if (this.doorWait < 1.2) return;          // (the leaf's collider is off while it swings)
      }
    } else this.doorWait = 0;
    // arrived at this waypoint: on to the next (its layer)
    const dx = w.x - this.pos.x, dz = w.z - this.pos.z, d = Math.hypot(dx, dz);
    if (d < 0.35 || (this.pathI < P.length - 1 && d < 0.6 && !w.door)) {
      this.layer = w.layer;
      this.pathI++;
      if (this.pathI >= P.length) { this.path = null; this.moveSpeed = 0; this.arrivedAt = this.time; this.doneGoal = this.goal?.clone() ?? null; this.donePartial = !!P.partial; return; }
      w = P[this.pathI];
    }
    const speed = this.wantSpeed ?? this.speeds.walk;
    this.steer(dt, w.x, w.z, speed, w.layer);
    // no progress for 2.5 s: a jam; replan (a teammate in a doorway, a door that swung shut)
    const rem = Math.hypot(w.x - this.pos.x, w.z - this.pos.z) + (P.length - this.pathI) * 1.0;
    if (!this.progress || rem < this.progress.best - 0.5) this.progress = { best: rem, t: this.time };
    else if (this.time - this.progress.t > 2.5) {
      this.stats.jams++;
      this.progress = null;
      this.path = null;
      this.sq.requestPath(this, this.goal ?? w, { jam: true });
    }
  }

  // walk toward (x, z) at speed, turning as it goes
  steer(dt, x, z, speed, layer = null) {
    const dx = x - this.pos.x, dz = z - this.pos.z, d = Math.hypot(dx, dz);
    if (d < 1e-4) return;
    const want = Math.atan2(dx, dz);
    const off = this.yawTo(want, dt, 7);
    const k = off > 1.6 ? 0.15 : Math.max(0.35, Math.cos(off));
    const s = Math.min(speed * k, d / Math.max(dt, 1e-3));
    this.moveSpeed += (s - this.moveSpeed) * Math.min(1, dt * 6);
    const step = this.moveSpeed * dt;
    this.vel.set(Math.sin(this.yaw) * this.moveSpeed, 0, Math.cos(this.yaw) * this.moveSpeed);
    this.pos.x += Math.sin(this.yaw) * step;
    this.pos.z += Math.cos(this.yaw) * step;
    if (layer && layer !== this.layer && d < 0.8) this.layer = layer;
    this.settle(dt);
  }

  // the floor under it (the stair's ramp), out of walls and furniture
  settle(dt) {
    const nav = this.sq.world.nav;
    if (this.layer === 'stair' && !nav.onRamp(this.pos.x, this.pos.z, 0.3)) this.layer = this.pos.x > (nav.ramp.x[0] + nav.ramp.x[1]) / 2 ? 'upper' : 'ground';
    const L = this.layer === 'stair' ? nav.layers[2] : this.layer === 'upper' ? nav.layers[1] : nav.layers[0];
    const y = nav.floorY(L, this.pos.x, this.pos.z);
    this.pos.y += (y - this.pos.y) * Math.min(1, dt * 12);
    if (Math.abs(y - this.pos.y) > 1.5) this.pos.y = y;
    this.sq.pushOut(this);
  }

  // turn the body toward a heading (returns how far off it still is); the head follows
  yawTo(want, dt, rate = 6) {
    const d = wrap(want - this.yaw), s = Math.sign(d) * Math.min(Math.abs(d), rate * dt);
    this.yaw = wrap(this.yaw + s);
    if (!this.glance || this.time > this.glance.until) this.lookYaw = wrap(this.lookYaw + Math.sign(wrap(this.yaw - this.lookYaw)) * Math.min(Math.abs(wrap(this.yaw - this.lookYaw)), 8 * dt));
    return Math.abs(d) - Math.abs(s);
  }
  turnLook(want, dt, rate = 5) {
    const d = wrap(want - this.lookYaw);
    this.lookYaw = wrap(this.lookYaw + Math.sign(d) * Math.min(Math.abs(d), rate * dt));
    // the body follows the head past ~50 degrees
    if (Math.abs(wrap(this.lookYaw - this.yaw)) > 0.9) this.yaw = wrap(this.yaw + Math.sign(wrap(this.lookYaw - this.yaw)) * Math.min(Math.abs(wrap(this.lookYaw - this.yaw)) - 0.9, 4 * dt));
  }
  lookAt(p, dt, rate = 5) {
    if (!p) return;
    const want = Math.atan2(p.x - this.pos.x, p.z - this.pos.z);
    this.turnLook(want, dt, rate);
    if (!this.path) this.yawTo(want, dt, rate * 0.8);
  }
  // looking where it's going, glancing at things heard / half seen, and at `p` when close
  lookAlong(dt, p = null) {
    if (this.glance && this.time < this.glance.until) { this.turnLook(this.glance.yaw, dt, 6); return; }
    if (p && Math.hypot(p.x - this.pos.x, p.z - this.pos.z) < 8) { this.turnLook(Math.atan2(p.x - this.pos.x, p.z - this.pos.z), dt, 4); return; }
    const sweep = Math.sin(this.time * 0.9 + this.id) * 0.45;
    this.turnLook(this.yaw + sweep, dt, 3);
  }
  scan(dt, base = this.scanBase ?? this.yaw, amp = 0.9, period = 5) {
    this.scanBase = base;
    if (this.glance && this.time < this.glance.until) { this.turnLook(this.glance.yaw, dt, 6); return; }
    this.turnLook(base + amp * Math.sin((2 * Math.PI * this.time) / period + this.id), dt, 2.2);
  }
}

export { UPPER_Y };
