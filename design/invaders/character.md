# The invader: character asset contract

Status: **built** (2026-10-22). A placeholder look the user will workshop later (like the Grimble);
the contract below (names, sockets, userData, clip timings) is what the engine codes against and
stays stable when the look changes. Owner: the invader-character workstream. Engine side (AI,
spawning, combat): the invader-behaviour workstream.

A ~1.8 m adult in dark work clothes (work jacket with zip and chest pockets, cargo trousers, boots,
gloves) with a balaclava (eye opening: skin and eyes painted); variants: 3 outfits x head
attachments (hard white mask, cap, hood, combinations) x 4 weapons.

## Files
- Generator (rebuild: `Blender -b --factory-startup --python blender/tools/build_asset.py -- invader`,
  ~20 s; caches in `build/invader_cache/`):
  `blender/assets/invader.py` (pipeline, `P`), `invader_body.py` (the body as a signed distance
  field, meshed by OpenVDB), `invader_rig.py` (skeleton, weights, pose solver), `invader_anims.py`
  (pose library, gait generator, clips, EV timings), `invader_gear.py` (weapons, head
  attachments, palette atlas), `invader_paint.py` (bakes + outfit textures), `invader_qa.py`
  (checks, run by every build), `invader_crowd.py` (bone animation texture).
- Output: `assets/models/invader.gltf` + `.bin`, `assets/models/textures/T_Invader_*.webp`,
  `assets/models/invader_anim.bin` + `.json` (crowd path).
- Engine helpers (import these, don't duplicate): `viewer/invader_asset.js` (`InvaderAsset`,
  `Invader`: load, spawn, outfit/head/weapon/LOD, play with cross-fades and upper-body layering,
  `placeInvaders` test hook), `viewer/invader_crowd.js` (`InvaderCrowd`: instanced GPU-skinned crowd).
- Viewer: `viewer/invader_view.html` (every clip, outfit, head, weapon, LOD, upper-body layer,
  skeleton, socket axes, scrolling floor at the clip's speed; `?crowd=50`, `?crowd=compare`,
  `?skinned=50`; `?clip=Walk&t=0.3&view=side&weapon=Rifle&head=cap&outfit=Navy&lod=1`).
- Tests: `viewer/tools/invader_check.mjs` (this contract in three.js + the house hook),
  `invader_sheet.mjs` (contact sheets: `"Walk@f0,f0.5:side;AimRifle@1:three::weapon=Rifle"`),
  `invader_perf.mjs` (crowd vs SkinnedMesh cost).
- House: `viewer/index.html?level=mansion&invaders=x,z,rotDeg,Clip[,Weapon,Outfit,head];...`
  (marked `[invader-character]` hook; e.g. `invaders=-2.2,12.6,15,AimRifle,Rifle,Navy,cap;2.4,12.2,-25,Search,,Olive,hood`).

## Frame
glTF metres, Y up, origin on the floor between the feet, faces **+Z** (Blender -Y): to walk along
(dx, dz) set `root.rotation.y = atan2(dx, dz)` (same as the Grimble).

## Nodes
- `Invader` (the root node; its `userData` holds the numbers below; the scene node wraps it).
  `InvaderAsset` reads it as `asset.meta`.
- `Invader_Armature` with the skeleton.
- Skinned bodies on one skeleton: `Invader_Body_LOD0` (10,010 tris), `Invader_Body_LOD1` (3,000),
  `Invader_Body_LOD2` (800). Show exactly one (`Invader.setLod`; suggested switch at
  `userData.lodDistance` = [12, 30] m).
- Head attachments, skinned (rigid on Head; the hood's lower edge follows Neck/Chest):
  `Invader_Mask` (~700 tris), `Invader_Cap` (~420), `Invader_Hood` (~900). Any combination
  (cap + hood intersect: don't combine those two); none = bare balaclava.
- Weapons, children of `Socket_Hand_R` with identity local transforms: `Invader_Rifle`,
  `Invader_Pistol`, `Invader_Bat`, `Invader_Knife` (all exported visible: show one, hide the rest;
  `Invader.setWeapon`). Markers: `Invader_Rifle_Muzzle`, `Invader_Pistol_Muzzle` (tracer / muzzle
  flash origin; local **+Z = shot direction**, verified: in AimRifle / AimPistol the muzzle's +Z is
  the character's forward, at ~1.5 m), `Invader_Bat_Tip`, `Invader_Knife_Tip` (melee sweep end;
  the sweep runs from the socket to the tip).
- Sockets (empty nodes): `Socket_Hand_R` (on Hand_R, the fist's grip point), `Socket_Hand_L`
  (on Hand_L), `Socket_Head` (on Head), `Socket_Back` (on Chest, upper back), `Socket_Hip_R` (on
  Hips, right hip). Socket frame: **+Z = forward** (muzzle direction), **+Y = up** (top of a gun);
  a held thing's origin is its grip. Guns: barrel along +Z, grip down -Y. Bat and knife: the shaft
  / blade runs along **+Y** (out of the thumb side of the fist), the knife's edge faces +Z.
  To holster or sling: reparent the weapon node to `Socket_Hip_R` / `Socket_Back` with an identity
  local transform (the pistol hangs muzzle-down; the rifle diagonally, muzzle down-left).

## Skeleton (34 joints; names use `_`, never `.`, which three.js strips)
Root, Hips, Spine, Chest, Neck, Head;
Shoulder_L/R, UpperArm_L/R, Forearm_L/R, Hand_L/R;
Thumb1_L/R, Thumb2_L/R, Index1_L/R, Index2_L/R, Fingers1_L/R, Fingers2_L/R (middle + ring + pinky);
Thigh_L/R, Shin_L/R, Foot_L/R, Toe_L/R.
Root never moves (clips are in place). Only Hips has translation tracks (bob, drop, falls); every
other joint is rotation only. Weights: <= 4 influences, normalised, broad blends across the hip
crease and the shoulder (linear blend skinning).
`userData.upperBody`: Spine and everything above it. Layering, e.g. walking while aiming:
`inv.play('Walk'); inv.play('AimRifle', { upper: true })` (`InvaderAsset.layeredClip` takes the
lower body's tracks from one clip and the upper body's from the other; Hips stays with the lower).

## Clips (30 fps, in place; durations in s)
| clip | dur | loop | notes |
|---|---|---|---|
| Idle | 4.0 | loop | relaxed breathing, weight shift |
| IdleAlert | 5.0 | loop | ready stance, scans left / right |
| Walk | 1.133 | loop | 1.25 m/s |
| Run | 0.733 | loop | 4.5 m/s, fists |
| CrouchIdle | 4.0 | loop | eyes at `crouchEyeHeight` 1.19 m |
| CrouchWalk | 1.4 | loop | 0.79 m/s |
| Search | 6.0 | loop | sweeps the room, then turns to check behind (right shoulder) |
| HoldRifle | 3.0 | loop | low ready, both hands on the rifle |
| HoldPistol | 3.0 | loop | low ready, two hands |
| AimRifle | 3.0 | loop | shouldered, cheek on the stock |
| AimPistol | 3.0 | loop | two-handed, arms out |
| Drag | 1.6 | loop | walking backward bent over, fists low in front (0.5 m/s backward) |
| OpenDoor | 1.6 | once | right hand to a lever ~1.0 m high, 0.4 m ahead; presses; pushes |
| Vault | 1.5 | once | over a 0.75 m obstacle 0.45 m ahead: left hand plants on top, legs tuck over |
| Shout | 1.5 | once | yells, fists out |
| Signal | 1.7 | once | points forward, then waves "over here" (left arm) |
| ShootRifle | 0.2 | once | one shot of recoil from / back to AimRifle (repeat for bursts) |
| ShootPistol | 0.367 | once | one shot from / back to AimPistol |
| ReloadRifle | 2.4 | once | mag out, to the pouch, in, slap, charging handle |
| ReloadPistol | 1.6 | once | |
| MeleeBat | 1.267 | once | two-handed swing right to left at chest height |
| MeleeKnife | 0.933 | once | forward stab at chest height |
| HitFront | 0.667 | once | hit from the front: thrown back, recovers |
| HitBack | 0.667 | once | hit from behind: thrown forward |
| Stagger | 1.5 | once | stumbles two steps back |
| DeathForward | 2.0 | once | buckles, falls on the face (clamp the last frame) |
| DeathBack | 2.0 | once | falls on the back |
| Grab | 1.1 | once | lunges, both hands catch at ~1.1 m, pulls in |

One-shots: `LoopOnce` + `clampWhenFinished` (`Invader.play` does it for these names).

## Root userData
- `height` 1.81, `eyeHeight` 1.685, `crouchEyeHeight` 1.19, `radius` 0.3 (m).
- Locomotion (in place): `walkStride` 1.42 / `walkCycle` 1.133 / `walkSpeed` 1.25; `runStride` 3.3 /
  `runCycle` 0.733 / `runSpeed` 4.5; `crouchWalkStride` 1.1 / `crouchWalkCycle` 1.4 /
  `crouchWalkSpeed` 0.79; `dragStride` 0.8 / `dragCycle` 1.6 / `dragSpeed` 0.5 (backward).
  Stride = metres per two-step cycle. Keep feet planted: `action.timeScale = speed / (stride / cycle)`.
  `*StrideMeasured` = what the QA measured from the planted foot (walk 1.40, run 3.16, crouch walk
  1.07, drag 0.80; the run's foot lands slightly fast, so 3.16 is the slip-free value at 4.3 m/s).
- `events` (s into the clip), all from the same constants the clips are built from:
  `OpenDoor {grab 0.42, push 0.78}`; `Vault {plant 0.36, clear 0.76, land 0.98, distance 1.6,
  height 0.75, rootCurve}`; `Shout {sound 0.3}`; `Signal {point 0.55}`; `ShootRifle {fire 0}`;
  `ShootPistol {fire 0}`; `ReloadRifle {magOut 0.55, magIn 1.45, done 2.2}`;
  `ReloadPistol {magOut 0.35, magIn 0.95, done 1.4}`; `MeleeBat {hit [0.42, 0.56]}`;
  `MeleeKnife {hit [0.30, 0.42]}`; `Stagger {distance -0.55, rootCurve}`;
  `DeathForward {fall 0.95, footprint, height}`; `DeathBack {fall 0.9, footprint, height}`;
  `Grab {catch 0.46}`; each also has `duration`.
- **Root motion for Vault and Stagger**: the clips are in place; the engine moves the root forward
  (+Z local, glTF) by `rootCurve` = [[t, metres], ...] (Vault: 1.6 m forward, eased; Stagger:
  0.55 m backward, negative). Don't also move it by speed (no double move).
- Corpses: `events.DeathForward.footprint` / `DeathBack.footprint` = [x0, z0, x1, z1] (glTF,
  root-local, unrotated) of the body lying at the end of the clip (forward: z -0.52..1.46, ahead of
  the root; back: z -1.46..0.35, behind it); `height` = its top (0.37 / 0.72 m). Use it for the
  corpse's collider, sight lines and the "body found" check.
- `lods` [{mesh, tris}], `lodDistance` [12, 30].
- `outfits` [{name, map}]: Charcoal (default, in the glTF), Navy, Olive; maps
  `textures/T_Invader_Body_<Name>.webp`. Swap the LOD meshes' material (`Invader.setOutfit`; one
  material per outfit, shared by every invader wearing it, so batching stays possible).
- `attachments`, `weapons`, `sockets`, `upperBody`: the node names above.

## Materials, textures, budgets
- `M_Invader_Body`: base colour (1024, per outfit), normal (1024, baked from the high-res field
  mesh, tangents exported), ORM (1024: R = AO, G = roughness, B = metallic; also multiplied into the
  base colour, since direct light gets no AO in three.js).
- `M_Invader_Gear` (weapons + attachments): a 256 palette atlas (colour + ORM), nearest filtering.
- LOD0 10,010 / LOD1 3,000 / LOD2 800 tris; attachments 420-900, weapons 40-200 each.
- Download (raw / gzip): invader.gltf 221 KB / 18 KB, invader.bin 598 KB / 454 KB (geometry is
  Draco; the 28 clips' rotation keys are most of it), textures ~300 KB (5 x 1024 + 2 tiny),
  crowd texture 711 KB / 357 KB (only needed for crowds). `optimize_textures.py` keeps
  `T_Invader_*` at full size (marked hook).
- Lighting: the viewer and the house hook use the scene environment + sun. In the house the
  invader should get the room's probe like the props (`baked.js` SH + env) or it reads dark and
  flat against the baked rooms; that's the behaviour workstream's call (it knows which room the
  invader is in).

## Crowds (20-50 on screen)
Two paths, both measured with `viewer/tools/invader_perf.mjs` (M4 Pro, 1600x900):
1. **SkinnedMesh per invader** (`asset.spawn()`, a mixer each): 50 invaders = ~103 draw calls,
   0.11 ms/frame CPU for the 50 mixers; fine for the first waves (6, 20), and the only path with
   cross-fades and upper-body layering. Use distance LODs.
2. **Instanced crowd** (`InvaderCrowd`, `?crowd=50`): 50 invaders with mixed clips, outfits,
   weapons and headgear in **10 draw calls** (one per outfit body batch and per weapon /
   attachment kind), no CPU animation cost. three.js 0.160 has no skinned instancing, so
   `invader_crowd.js` patches the asset's own MeshStandardMaterial (onBeforeCompile): each vertex
   fetches its 4 joints' matrices for 2 frames from the bone animation texture and lerps; weapons
   are rigid on an extra row (the right-hand socket). Verified against the SkinnedMesh side by side
   (`?crowd=compare&clip=AimRifle&t=0.4&weapon=Rifle&head=cap`). Per instance: position, rotation,
   clip, start time, speed (`crowd.set(id, {clip, time, speed, position, rotationY})`); no blending
   between clips (switch at a pose that matches, or swap the far ones only).
   Data: `invader_anim.json` {fps 15, width 102 texels (3 per joint, 33 joints + 1 socket row),
   height 872 frames, joints (texture order), extra, clips {name: {start, frames, duration, loop}}};
   `invader_anim.bin` float16 RGBA. Matrices are skinning matrices in the glTF model frame.
Recommendation: SkinnedMesh for the invaders near the player / in combat (LOD0-1 within ~15 m,
up to ~10-15 at once), the instanced crowd at LOD1/LOD2 for the rest (a wave of 50 outside, the
lawn); hand an invader from one path to the other at a clip boundary.

## QA (runs in every build; `QA ...` lines)
Mesh (manifold, degenerate), skin (<= 4 influences, sums = 1, no unweighted vertex), per-clip edge
stretch on LOD0 (fails on tears: < 0.15 or > 3.5x; the knees in the deep crouch and the armpits
with raised arms reach ~2-3x, visually fine), held weapon / hand vertices inside the body, below-floor
vertices (falls are clamped to the floor), loop seams (a velocity jump at the seam no larger than
inside the cycle), planted-foot slip and the measured strides, corpse footprints.
Known limits: the bat swing passes the bat through the body / arms for a few
frames; the vault reads best against a real obstacle (its hand plant is 7 cm short at the end of
the plant); cap + hood intersect.
