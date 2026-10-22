# The invader: character asset contract

Status: **DRAFT, being built** (names below are the contract; numbers marked ~ are measured and
filled in by the build). Owner: the invader-character workstream. Engine side (AI, spawning,
crowds): the invader-behaviour workstream codes against this file.

A placeholder the user will workshop later (like the Grimble): a clean, believable ~1.8 m adult in
dark work clothes, gloves, boots and a full-face covering.

## Files
- `blender/assets/invader.py` (+ `invader_body.py` mesh, `invader_rig.py` skeleton/skin/solver,
  `invader_anims.py` clips, `invader_gear.py` weapons + attachments, `invader_paint.py` textures,
  `invader_qa.py` checks, `invader_crowd.py` bone-animation texture).
  Build: `Blender -b --factory-startup --python blender/tools/build_asset.py -- invader`
- `assets/models/invader.gltf` (+ `.bin`, textures in `assets/models/textures/T_Invader_*.webp`)
- `assets/models/invader_anim.bin` + `invader_anim.json`: the crowd path (bone animation texture)
- `viewer/invader_view.html`: every clip, outfit, attachment, weapon, LOD; crowd demo

## Frame
glTF metres, Y up, origin on the floor between the feet, faces **+Z** (Blender -Y). Same as the
Grimble: `root.rotation.y = atan2(dx, dz)` turns it to walk along (dx, dz).

## Nodes
- `Invader` (scene root node): `userData` = the numbers below.
- `Invader_Armature` with the skeleton (joint names use `_`, never `.`: three.js strips dots).
- Skinned meshes, all on the same skeleton: `Invader_Body_LOD0` (~10k tris), `Invader_Body_LOD1`
  (~3k), `Invader_Body_LOD2` (~800). Show exactly one.
- Head attachments, children of `Socket_Head` (rigid on the Head bone): `Invader_Mask` (plain hard
  face mask over the balaclava), `Invader_Cap` (ball cap), `Invader_Hood` (hood up). Any
  combination (cap and hood exclude each other); none = bare balaclava.
- Weapons, children of `Socket_Hand_R`: `Invader_Rifle`, `Invader_Pistol`, `Invader_Bat`,
  `Invader_Knife` (all hidden by default except none; the engine shows one). Child markers:
  `Invader_Rifle_Muzzle`, `Invader_Pistol_Muzzle` (tracer / flash origin, +Z = shot direction),
  `Invader_Bat_Tip`, `Invader_Knife_Tip` (melee sweep end; the grip is the socket origin).
- Other sockets (empty nodes): `Socket_Hand_L` (child of Hand_L), `Socket_Back` (child of Chest:
  a slung rifle), `Socket_Hip_R` (child of Hips: holstered pistol). Socket frame: +Z = forward
  (muzzle / blade tip direction), +Y = up (top of the weapon); a weapon's origin is its grip.

## Skeleton (34 joints)
Root, Hips, Spine, Chest, Neck, Head;
Shoulder_L/R, UpperArm_L/R, Forearm_L/R, Hand_L/R;
Thumb1_L/R, Thumb2_L/R, Index1_L/R, Index2_L/R, Fingers1_L/R, Fingers2_L/R (middle+ring+pinky);
Thigh_L/R, Shin_L/R, Foot_L/R, Toe_L/R.
Root never moves (clips are in place); Hips carry the body's bob/sway/drop.
`userData.upperBody`: the joints of the upper-body layer (Spine and everything above it), for
layering e.g. `AimRifle` (upper) over `Walk` (lower): filter clip tracks by joint name.

## Clips (30 fps, in place)
Loops: `Idle`, `IdleAlert` (looking around), `Walk`, `Run`, `CrouchIdle`, `CrouchWalk`, `Search`
(sweep + check behind), `HoldRifle` (low ready), `HoldPistol`, `AimRifle`, `AimPistol`, `Drag`
(walking backward, dragging the caught player).
One-shots (clampWhenFinished): `OpenDoor`, `Vault` (low obstacle), `Shout`, `Signal`,
`ShootRifle`, `ShootPistol` (one recoil, starts and ends in the aim pose: repeat for bursts),
`ReloadRifle`, `ReloadPistol`, `MeleeBat`, `MeleeKnife`, `HitFront`, `HitBack`, `Stagger`,
`DeathForward`, `DeathBack`, `Grab` (lunge and catch).

## Root userData (numbers the engine needs)
- `height`, `eyeHeight`, `crouchEyeHeight`, `radius`
- strides: `walkStride` / `walkCycle` (m and s per two-step cycle; speed = stride / cycle),
  `runStride` / `runCycle`, `crouchWalkStride` / `crouchWalkCycle`, `dragStride` / `dragCycle`
  (backward); play the clip with timeScale = actualSpeed / (stride / cycle) to keep feet planted.
- `events`: per one-shot clip the times (s) the engine acts on: `ShootRifle.fire`,
  `ShootPistol.fire`, `MeleeBat.hit` [start, end], `MeleeKnife.hit` [start, end],
  `Grab.catch`, `OpenDoor.push`, `DeathForward.fall` / `DeathBack.fall` (body_fall sound),
  `ReloadRifle.done`, `ReloadPistol.done`, `Vault.distance` (m the body travels forward;
  move the root this far over the clip), `Vault.height` (obstacle height it clears).
- `lods`: [{mesh, tris, distance}] suggested switch distances.
- `outfits`: [{name, map}] body base-colour textures (`T_Invader_Body_<Name>.webp`): swap
  `Invader_Body_LOD*.material.map` (one material per outfit, shared by every invader wearing it).
- `attachments`, `weapons`, `sockets`: the node names above.

## Budgets
LOD0 ~8-12k tris, LOD1 ~3k, LOD2 ~800; 2 materials (`M_Invader_Body`, `M_Invader_Gear`);
textures: body 1k set (base colour per outfit, normal, ORM) + gear 1k set.

## Crowds (50 on screen)
See "Crowd path" (filled in when built): a bone animation texture (every clip's joint matrices
per frame) for GPU-skinned `InstancedMesh` drawing of LOD1/LOD2.
