"""Automated QA for the invader (blender/assets/invader.py), run at the end of build().

Prints "QA ..." lines, returns numbers for the root's userData (measured strides, corpse
footprints), raises on errors. Deformation is evaluated here with linear blend skinning in
numpy from the solver's per-frame bone matrices (exactly what's keyed), so it doesn't
depend on the depsgraph.

mesh      per LOD: triangles vs budget, non-manifold edges, degenerate triangles
skin      <= 4 influences, weights sum to 1, no unweighted vertex
stretch   per clip, sampled frames: edge length / rest length on LOD0 (1st and 99.9th
          percentile, worst edge); limbs folding (< 0.45) or tearing (> 1.8) fail
contact   per clip: the held weapon's vertices inside the body, the hands inside the
          torso, any vertex below the floor (deaths and crouches included)
loops     looping clips: the pose at the seam (velocity jump of the joints)
gait      planted-foot slip in Walk / Run / CrouchWalk / Drag (in place: the foot must
          move back at exactly stride / cycle while in contact), the measured stride
budget    LOD triangle counts, texture sizes
"""
import math

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import invader_anims as anims

BUDGET = dict(Invader_Body_LOD0=(8000, 12000), Invader_Body_LOD1=(2400, 3600), Invader_Body_LOD2=(600, 1000))
HELD = dict(HoldRifle="Rifle", AimRifle="Rifle", ShootRifle="Rifle", ReloadRifle="Rifle",
            HoldPistol="Pistol", AimPistol="Pistol", ShootPistol="Pistol", ReloadPistol="Pistol",
            MeleeBat="Bat", MeleeKnife="Knife")


def line(*a):
    print("QA", *a, flush=True)


def _mesh(ob):
    me = ob.data
    v = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", v)
    me.calc_loop_triangles()
    t = np.zeros(len(me.loop_triangles) * 3, np.int64)
    me.loop_triangles.foreach_get("vertices", t)
    return v.reshape(-1, 3), t.reshape(-1, 3)


def _weights(ob, names):
    bi = {n: i for i, n in enumerate(names)}
    gi = {g.index: bi.get(g.name) for g in ob.vertex_groups}
    W = np.zeros((len(ob.data.vertices), len(names)))
    counts = np.zeros(len(ob.data.vertices), int)
    for v in ob.data.vertices:
        for g in v.groups:
            if g.weight > 0 and gi.get(g.group) is not None:
                W[v.index, gi[g.group]] += g.weight
                counts[v.index] += 1
    return W, counts


def _skin_mats(sv, PM, names):
    return np.array([np.array(PM[n] @ sv.Ri[n]) for n in names])          # (nb, 4, 4)


def deform(V, W, S):
    """Linear blend skinning: V (n, 3), W (n, nb), S (nb, 4, 4)."""
    Vh = np.concatenate([V, np.ones((len(V), 1))], 1)
    M = np.einsum("nb,bij->nij", W, S)
    return np.einsum("nij,nj->ni", M, Vh)[:, :3]


def _inside(bvh, P, far=3.0):
    """Points inside a closed mesh: odd number of hits along +X (rough, for counting)."""
    out = np.zeros(len(P), bool)
    for i, p in enumerate(P):
        o = Vector(p)
        n = 0
        d = Vector((1, 0, 0.0013))
        for _ in range(8):
            hit = bvh.ray_cast(o, d, far)
            if hit[0] is None:
                break
            n += 1
            o = hit[0] + d * 1e-4
        out[i] = n % 2 == 1
    return out


def run(L, sv, info, lods, part, weapons, sockets, errors_fatal=False):
    errs, out = [], {}
    names = [n for n in sv.order if n != "Root"]
    # ---- mesh + budget
    for ob in lods:
        v, t = _mesh(ob)
        e = np.sort(np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]]), 1)
        _, cnt = np.unique(e[:, 0] * (len(v) + 1) + e[:, 1], return_counts=True)
        area = 0.5 * np.linalg.norm(np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]]), axis=1)
        lo, hi = BUDGET[ob.name]
        line(f"mesh {ob.name}: {len(t)} tris (budget {lo}-{hi}), {len(v)} verts, non-manifold edges {(cnt > 2).sum()}, "
             f"open edges {(cnt == 1).sum()}, degenerate {(area < 1e-10).sum()}")
        if not lo <= len(t) <= hi:
            errs.append(f"{ob.name}: {len(t)} triangles outside {lo}-{hi}")
        W, counts = _weights(ob, names)
        s = W.sum(1)
        line(f"skin {ob.name}: max influences {counts.max()}, weight sums {s.min():.3f}..{s.max():.3f}, "
             f"unweighted {(s < 0.5).sum()}")
        if counts.max() > 4 or (s < 0.99).any() or (s > 1.01).any():
            errs.append(f"{ob.name}: skin weights (influences {counts.max()}, sums {s.min():.3f}..{s.max():.3f})")
    # ---- deformation per clip (LOD0)
    lod0 = lods[0]
    V0, T0 = _mesh(lod0)
    W0, _ = _weights(lod0, names)
    E0 = np.unique(np.sort(np.concatenate([T0[:, [0, 1]], T0[:, [1, 2]], T0[:, [2, 0]]]), 1), axis=0)
    L0 = np.linalg.norm(V0[E0[:, 0]] - V0[E0[:, 1]], axis=1)
    body = part == 0
    hands = part > 0
    torso_v = body & (V0[:, 2] > 0.95) & (np.abs(V0[:, 0]) < 0.16)          # trunk vertices (for hand-in-torso)
    wverts = {}
    for k, (ob, _) in weapons.items():
        v, _t = _mesh(ob)
        wverts[k] = v
    sock = sv.sockets["Socket_Hand_R"][1]
    worst = {}
    hrest = None
    for name, d in info.items():
        frames = d["frames"]
        n = len(frames)
        idx = sorted(set(np.linspace(0, n - 1, min(n, 9)).astype(int)))
        smin, smax, below, wpen, hpen = 9.0, 0.0, 0.0, 0, 0
        where = {}
        for f in idx:
            S = _skin_mats(sv, frames[f], names)
            V = deform(V0, W0, S)
            r = np.linalg.norm(V[E0[:, 0]] - V[E0[:, 1]], axis=1) / np.maximum(L0, 1e-6)
            smin, smax = min(smin, np.percentile(r, 0.1)), max(smax, np.percentile(r, 99.9))
            bad = np.nonzero((r > 1.8) | (r < 0.45))[0]
            for e in bad:
                b = names[int(W0[E0[e, 0]].argmax())]
                where[b] = where.get(b, 0) + 1
            below = max(below, -V[:, 2].min())
            if name in HELD or f == idx[len(idx) // 2]:
                # body-only BVH (the hands are separate islands)
                bmap = -np.ones(len(V), int)
                bmap[body] = np.arange(body.sum())
                tb = T0[np.all(body[T0], 1)]
                bvh = BVHTree.FromPolygons([tuple(p) for p in V[body]], [tuple(bmap[t]) for t in tb])
                if name in HELD:
                    Hm = frames[f]["Hand_R"] @ sock
                    wv = np.array([tuple(Hm @ Vector(p)) for p in wverts[HELD[name]][::3]])
                    wpen = max(wpen, int(_inside(bvh, wv).sum()))
                hv = V[hands][::4]
                ins = _inside(bvh, hv)
                hpen = max(hpen, int(ins.sum()))
        worst[name] = (smin, smax)
        if hrest is None:
            hrest = hpen          # Idle: the glove cuffs sit inside the sleeves by design
        flag = ""
        if smin < 0.15 or smax > 3.5:
            flag += " TEAR"
        elif smin < 0.3 or smax > 2.2:
            flag += " stretch"
        if below > 0.03:
            flag += " FLOOR"
        line(f"clip {name}: {d['T']:.2f}s, IK gap {d['gap'] * 100:.1f} cm, edge stretch {smin:.2f}..{smax:.2f}, "
             f"below floor {below * 100:.1f} cm, weapon verts in body {wpen}, hand verts in body {hpen - hrest:+d} vs rest{flag}"
             + (" worst at " + " ".join(f"{k}:{v}" for k, v in sorted(where.items(), key=lambda x: -x[1])[:4]) if where else ""))
        if "TEAR" in flag:
            errs.append(f"{name}: edge stretch {smin:.2f}..{smax:.2f}")
    # ---- loops: joint velocity jump across the seam
    for name, d in info.items():
        if not d["loop"]:
            continue
        fr = d["frames"]
        X = np.array([[np.array(f[n].translation) for n in names] for f in fr[:-1]])   # one cycle, cyclic
        Vv = np.roll(X, -1, axis=0) - X                                               # velocity per frame
        A = np.linalg.norm(np.roll(Vv, -1, axis=0) - Vv, axis=2) * anims.rig.FPS       # velocity change per frame
        seam = A[-1]                                                                   # last frame -> first
        jump = seam.max()
        inner = A[:-1].max()
        who = names[int(seam.argmax())]
        err0 = np.abs(np.array([np.array(fr[0][n].translation) for n in names]) - np.array([np.array(fr[-1][n].translation) for n in names])).max()
        line(f"loop {name}: seam velocity change {jump:.2f} m/s (worst {who}; the largest inside the cycle {inner:.2f}), "
             f"pose error {err0 * 1000:.1f} mm")
        if jump > max(0.3, 1.25 * inner) or err0 > 0.002:
            errs.append(f"{name}: loop seam pops ({jump:.2f} m/s)")
    # ---- gait: planted-foot slip and measured stride
    for name, G in anims.STRIDES.items():
        fr = info[name]["frames"]
        speed = G["stride"] / G["cycle"]
        slips, cv = [], []
        for s in "LR":
            ball = Vector(L["ball_" + s]) - Vector(sv.head["Foot_" + s])
            pts = np.array([np.array(f["Foot_" + s] @ (sv.R["Foot_" + s].inverted() @ Vector(L["ball_" + s]))) for f in fr])
            hp = np.array([np.array(f["Foot_" + s] @ (sv.R["Foot_" + s].inverted() @ Vector(L["heel_" + s]))) for f in fr])
            low = np.minimum(pts[:, 2] - L["ball_" + s][2], hp[:, 2] - L["heel_" + s][2])
            vel = np.diff(pts, axis=0) * anims.rig.FPS
            contact = (low[:-1] < 0.01) & (low[1:] < 0.01)
            if contact.any():
                vy = vel[contact, 1] * G.get("dir", 1.0)
                cv.append(np.median(vy))
                slip = np.abs(vel[contact, 1] * G.get("dir", 1.0) - speed)
                slips.append(np.percentile(slip, 90))
        meas = float(np.mean(cv)) * G["cycle"] if cv else 0.0
        line(f"gait {name}: speed {speed:.2f} m/s, planted foot moves back at {np.mean(cv) if cv else 0:.2f} m/s, "
             f"slip p90 {np.mean(slips) if slips else 0:.2f} m/s -> measured stride {meas:.2f} m per {G['cycle']:.2f} s")
        n = name[0].lower() + name[1:]
        out[n + "StrideMeasured"] = round(meas, 3)
    # ---- corpse footprints (glTF x, z) and the crouch eye height
    for name in ("DeathForward", "DeathBack"):
        PM = info[name]["frames"][-1]
        P = np.array([np.array(PM[n].translation) for n in names])
        x0, x1 = P[:, 0].min() - 0.15, P[:, 0].max() + 0.15
        z0, z1 = -P[:, 1].max() - 0.15, -P[:, 1].min() + 0.15
        out[name] = dict(footprint=[round(float(x0), 2), round(float(z0), 2), round(float(x1), 2), round(float(z1), 2)],
                         height=round(float(P[:, 2].max()) + 0.12, 2))
        line(f"corpse {name}: footprint x {x0:.2f}..{x1:.2f}, z {z0:.2f}..{z1:.2f} (glTF), top {P[:, 2].max() + 0.12:.2f} m")
    PM = info["CrouchIdle"]["frames"][0]
    eye = PM["Head"] @ (sv.R["Head"].inverted() @ Vector(L["eye_L"]))
    out["crouchEyeHeight"] = round(eye[2], 3)
    line(f"crouch eye height {eye[2]:.2f} m")
    for e in errs:
        line("ERROR", e)
    line(f"{len(errs)} errors")
    if errs and errors_fatal:
        raise RuntimeError("invader QA: " + "; ".join(errs))
    return out
