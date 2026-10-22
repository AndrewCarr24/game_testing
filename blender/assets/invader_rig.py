"""Skeleton, skin weights and the pose solver of the invader (blender/assets/invader.py).

Skeleton: 34 deforming joints from the body's landmarks (invader_body.landmarks), plus
socket empties parented to bones (weapons, head attachments).

Weights: each vertex's limb comes from the body field's primitive labels (soft membership
over the nearest primitives); inside a limb the weight runs along the chain of joints
(smoothstep windows at each joint), then a few rounds of mesh smoothing, <= 4 influences.

Pose solver: a frame's controls (a plain dict, see `rest_controls`) -> every bone's
armature-space matrix: FK rotations about the rest joints (expressed in armature axes,
carried by the parent), two-bone IK for arms and legs (pole vectors), FK finger curls.
The matrices are converted to each bone's local basis and keyed. No constraints, so the
glTF gets exactly what the solver computed.

Axes (Blender, armature space): +X the character's left, -Y its front, +Z up.
Euler controls (degrees) E(x, y, z) = Rz @ Ry @ Rx about the armature axes:
  +x bends forward (the top tips toward the front), +y leans to the character's left,
  +z turns to the character's left.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

FPS = 30


def log(*a):
    print("INVADER", *a, flush=True)


def V(x):
    return Vector([float(c) for c in x])


def npv(v):
    return np.array([v[0], v[1], v[2]], float)


def E(x=0.0, y=0.0, z=0.0):
    """Rotation (Quaternion) from degrees about the armature X, Y, Z, applied in that order."""
    return (Quaternion((0, 0, 1), math.radians(z)) @ Quaternion((0, 1, 0), math.radians(y))
            @ Quaternion((1, 0, 0), math.radians(x)))


def frame(head, tail, up):
    """Bone matrix: Y along head->tail, Z toward `up` (Blender's align_roll), at head."""
    y = np.asarray(tail, float) - np.asarray(head, float)
    y /= np.linalg.norm(y)
    u = np.asarray(up, float)
    z = u - (u @ y) * y
    z /= np.linalg.norm(z)
    x = np.cross(y, z)
    m = Matrix.Identity(4)
    for r in range(3):
        m[r][0], m[r][1], m[r][2], m[r][3] = x[r], y[r], z[r], head[r]
    return m


def rot_about(M, pivot, q):
    p = V(pivot)
    return Matrix.Translation(p) @ q.to_matrix().to_4x4() @ Matrix.Translation(-p) @ M


def ik(a, t, l1, l2, pole):
    """Two-bone IK: the middle joint for a chain from a to t (lengths l1, l2) bending
    toward `pole` (a direction). Returns (joint, the end it reached, gap to the target)."""
    a, t, pole = (np.asarray(x, float) for x in (a, t, pole))
    d = t - a
    L = np.linalg.norm(d)
    u = d / max(L, 1e-9)
    Lc = min(max(L, abs(l1 - l2) + 1e-4), (l1 + l2) * 0.9999)
    x = (l1 * l1 - l2 * l2 + Lc * Lc) / (2 * Lc)
    h = math.sqrt(max(l1 * l1 - x * x, 0.0))
    pp = pole - (pole @ u) * u
    pp /= np.linalg.norm(pp) + 1e-12
    return a + u * x + pp * h, a + u * Lc, abs(L - Lc)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- skeleton

SIDES = ("L", "R")
FINGER_BONES = ("Thumb1", "Thumb2", "Index1", "Index2", "Fingers1", "Fingers2")


def skeleton(L, hand_frames, hand_joints):
    """[(name, parent, head, tail, up)] in the armature frame (= the model frame)."""
    B = []

    def add(n, par, h, t, up=(0, -1, 0)):
        B.append((n, par, np.asarray(h, float), np.asarray(t, float), np.asarray(up, float)))

    add("Root", None, (0, 0, 0), (0, 0.15, 0), (0, 0, 1))
    add("Hips", "Root", L["hips"], L["spine"])
    add("Spine", "Hips", L["spine"], L["chest"])
    add("Chest", "Spine", L["chest"], L["neck"])
    add("Neck", "Chest", L["neck"], L["head"])
    add("Head", "Neck", L["head"], L["head_top"])
    for s in SIDES:
        sg = 1 if s == "L" else -1
        add("Shoulder_" + s, "Chest", L["clav_" + s], L["shoulder_" + s], (0, 0, 1))
        # elbows point back (+Y) and a little out
        pole = np.array([0.15 * sg, 1.0, 0.0])
        add("UpperArm_" + s, "Shoulder_" + s, L["shoulder_" + s], L["elbow_" + s], pole)
        add("Forearm_" + s, "UpperArm_" + s, L["elbow_" + s], L["wrist_" + s], pole)
        M = hand_frames[s]
        hx, hy, hz = M[:3, 0], M[:3, 1], M[:3, 2]
        w = L["wrist_" + s]
        knuck = w + hy * 0.1
        add("Hand_" + s, "Forearm_" + s, w, knuck, hz)
        J = {k: [M[:3, :3] @ p + M[:3, 3] for p in v] for k, v in hand_joints.items()}
        add("Thumb1_" + s, "Hand_" + s, J["Thumb"][0], J["Thumb"][1], hz)
        add("Thumb2_" + s, "Thumb1_" + s, J["Thumb"][1], J["Thumb"][2], hz)
        add("Index1_" + s, "Hand_" + s, J["Index"][0], J["Index"][1], hz)
        add("Index2_" + s, "Index1_" + s, J["Index"][1], J["Index"][2], hz)
        add("Fingers1_" + s, "Hand_" + s, J["Middle"][0], J["Middle"][1], hz)
        add("Fingers2_" + s, "Fingers1_" + s, J["Middle"][1], J["Middle"][2], hz)
    for s in SIDES:
        add("Thigh_" + s, "Hips", L["hip_" + s], L["knee_" + s], (0, -1, 0))
        add("Shin_" + s, "Thigh_" + s, L["knee_" + s], L["ankle_" + s], (0, -1, 0))
        add("Foot_" + s, "Shin_" + s, L["ankle_" + s], L["ball_" + s], (0, 0, 1))
        add("Toe_" + s, "Foot_" + s, L["ball_" + s], L["toe_" + s], (0, 0, 1))
    return B


def build_armature(name, bones, col, root):
    arm_data = bpy.data.armatures.new(name)
    arm = bpy.data.objects.new(name, arm_data)
    col.objects.link(arm)
    arm.parent = root
    vl = bpy.context.view_layer
    for o in vl.objects.selected:
        o.select_set(False)
    vl.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for n, par, h, t, up in bones:
        eb = arm_data.edit_bones.new(n)
        eb.head, eb.tail = V(h), V(t)
        eb.align_roll(V(up))
        if par:
            eb.parent = arm_data.edit_bones[par]
        eb.use_connect = False
        eb.use_deform = n != "Root"
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.select_set(False)
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    return arm


def attach(ob, arm, bone_name):
    """Parent `ob` to a bone, keeping its world transform (the Grimble's eyes do the same)."""
    mw = ob.matrix_world.copy()
    bone = arm.data.bones[bone_name]
    ob.parent = arm
    ob.parent_type = "BONE"
    ob.parent_bone = bone_name
    ob.matrix_parent_inverse = (bone.matrix_local @ Matrix.Translation((0, bone.length, 0))).inverted()
    ob.matrix_basis = mw


# ---------------------------------------------------------------- weights

TORSO = (("Hips", None), ("Spine", 1.07), ("Chest", 1.24), ("Neck", 1.505), ("Head", 1.60))
TORSO_BLEND = {1.07: 0.07, 1.24: 0.08, 1.505: 0.03, 1.60: 0.035}


def _chain_param(P, pts):
    """Arc-length parameter of each point's closest point on the polyline pts."""
    best = np.full(len(P), np.inf)
    s_out = np.zeros(len(P))
    acc = 0.0
    for a, b in zip(pts[:-1], pts[1:]):
        ab = b - a
        ln = np.linalg.norm(ab)
        t = np.clip(((P - a) @ ab) / (ln * ln), -0.5 if acc == 0 else 0.0, 1.0)
        d = np.linalg.norm(P - (a + t[:, None] * ab), axis=1)
        m = d < best
        best[m] = d[m]
        s_out[m] = acc + t[m] * ln
        acc += ln
    return s_out


def _chain_weights(s, joints_s, blends):
    """Partition of unity over len(joints_s) + 1 bones along a chain: bone i covers the
    parameter range between joint i-1 and joint i, blended over +-blends[i] at joint i."""
    n = len(joints_s) + 1
    steps = [smoothstep(js - b, js + b, s) for js, b in zip(joints_s, blends)]
    W = np.zeros((len(s), n))
    prev = np.ones(len(s))
    for i in range(n):
        nxt = steps[i] if i < len(steps) else np.zeros(len(s))
        W[:, i] = prev - nxt
        prev = nxt
    return np.clip(W, 0, 1)


def weights(verts, faces, part, bone_names, L, body_labels, hand_labels, hand_frames, smooth_iter=6):
    """Weight matrix (nverts, nbones). part: per vertex 0 body, 1 left hand, 2 right hand.
    body_labels(P) / hand_labels(P_local, side) -> soft membership {bone: (N,) array}."""
    bi = {n: i for i, n in enumerate(bone_names)}
    W = np.zeros((len(verts), len(bone_names)))
    # body
    m = part == 0
    P = verts[m]
    lab = body_labels(P)
    region = {"torso": np.zeros(len(P)), "arm_L": np.zeros(len(P)), "arm_R": np.zeros(len(P)),
              "leg_L": np.zeros(len(P)), "leg_R": np.zeros(len(P)), "foot_L": np.zeros(len(P)),
              "foot_R": np.zeros(len(P))}
    for b, w in lab.items():
        side = b[-1]
        if b in ("Hips", "Spine", "Chest", "Neck", "Head"):
            region["torso"] += w
        elif b.split("_")[0] in ("Shoulder", "UpperArm", "Forearm", "Hand"):
            region["arm_" + side] += w
        elif b.split("_")[0] in ("Thigh", "Shin"):
            region["leg_" + side] += w
        else:
            region["foot_" + side] += w
    Wb = np.zeros((len(P), len(bone_names)))
    # torso along z
    z = P[:, 2]
    js = [j for _, j in TORSO[1:]]
    tw = _chain_weights(z, js, [TORSO_BLEND[j] for j in js])
    for i, (n, _) in enumerate(TORSO):
        Wb[:, bi[n]] += region["torso"] * tw[:, i]
    for s in "LR":
        pts = [L["clav_" + s], L["shoulder_" + s], L["elbow_" + s], L["wrist_" + s]]
        sp = _chain_param(P, pts)
        acc = np.cumsum([0] + [np.linalg.norm(b - a) for a, b in zip(pts[:-1], pts[1:])])
        aw = _chain_weights(sp, acc[1:], [0.05, 0.045, 0.03])
        for i, n in enumerate(("Shoulder", "UpperArm", "Forearm", "Hand")):
            Wb[:, bi[n + "_" + s]] += region["arm_" + s] * aw[:, i]
        pts = [L["hip_" + s], L["knee_" + s], L["ankle_" + s]]
        sp = _chain_param(P, pts)
        acc = np.cumsum([0] + [np.linalg.norm(b - a) for a, b in zip(pts[:-1], pts[1:])])
        lw = _chain_weights(sp, acc[1:], [0.06, 0.035])
        for i, n in enumerate(("Thigh", "Shin", "Foot")):
            Wb[:, bi[n + "_" + s]] += region["leg_" + s] * lw[:, i]
        # the boot below the ankle: foot, the toe cap beyond the ball
        by = L["ball_" + s][1]
        tw_ = smoothstep(by + 0.02, by - 0.025, P[:, 1])
        Wb[:, bi["Foot_" + s]] += region["foot_" + s] * (1 - tw_)
        Wb[:, bi["Toe_" + s]] += region["foot_" + s] * tw_
    W[m] = Wb
    # hands
    for pi, s in ((1, "L"), (2, "R")):
        m = part == pi
        if not m.any():
            continue
        M = hand_frames[s]
        loc = (verts[m] - M[:3, 3]) @ M[:3, :3]          # (inverse of an orthonormal frame)
        lab = hand_labels(loc, s)
        Wh = np.zeros((m.sum(), len(bone_names)))
        for b, w in lab.items():
            Wh[:, bi[b]] += w
        # the cuff behind the wrist blends into the forearm
        f = smoothstep(0.0, -0.035, loc[:, 1])
        Wh *= (1 - f)[:, None]
        Wh[:, bi["Forearm_" + s]] += f
        W[m] = Wh
    W /= np.maximum(W.sum(1, keepdims=True), 1e-9)
    # mesh smoothing (keeps islands apart: it only follows edges)
    if smooth_iter:
        e = np.concatenate([faces[:, [i, (i + 1) % faces.shape[1]]] for i in range(faces.shape[1])])
        e = np.concatenate([e, e[:, ::-1]])
        deg = np.bincount(e[:, 0], minlength=len(verts)).astype(float)
        for _ in range(smooth_iter):
            acc = np.zeros_like(W)
            np.add.at(acc, e[:, 0], W[e[:, 1]])
            W = 0.5 * W + 0.5 * acc / np.maximum(deg, 1)[:, None]
    # <= 4 influences
    idx = np.argsort(-W, axis=1)
    keep = np.zeros_like(W, bool)
    np.put_along_axis(keep, idx[:, :4], True, axis=1)
    W = np.where(keep & (W > 0.01), W, 0.0)
    W /= np.maximum(W.sum(1, keepdims=True), 1e-9)
    return W


def assign_weights(ob, W, bone_names):
    for g in list(ob.vertex_groups):
        ob.vertex_groups.remove(g)
    groups = [ob.vertex_groups.new(name=n) for n in bone_names]
    for j, g in enumerate(groups):
        nz = np.nonzero(W[:, j] > 0)[0]
        for v in nz:
            g.add([int(v)], float(W[v, j]), "REPLACE")


# ---------------------------------------------------------------- solver

def rest_controls():
    """Every control at rest. Arms/legs default to FK (all zero)."""
    return dict(
        hips=dict(pos=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0)),
        spine=(0.0, 0.0, 0.0), chest=(0.0, 0.0, 0.0), neck=(0.0, 0.0, 0.0), head=(0.0, 0.0, 0.0),
        arm_L=dict(shoulder=(0.0, 0.0, 0.0), upper=(0.0, 0.0, 0.0), fore=(0.0, 0.0, 0.0), hand=(0.0, 0.0, 0.0)),
        arm_R=dict(shoulder=(0.0, 0.0, 0.0), upper=(0.0, 0.0, 0.0), fore=(0.0, 0.0, 0.0), hand=(0.0, 0.0, 0.0)),
        leg_L=dict(thigh=(0.0, 0.0, 0.0), shin=(0.0, 0.0, 0.0), foot=(0.0, 0.0, 0.0), toe=0.0),
        leg_R=dict(thigh=(0.0, 0.0, 0.0), shin=(0.0, 0.0, 0.0), foot=(0.0, 0.0, 0.0), toe=0.0),
        fingers_L=dict(Thumb=0.0, Index=0.0, Fingers=0.0),
        fingers_R=dict(Thumb=0.0, Index=0.0, Fingers=0.0),
    )


class Solver:
    """controls -> {bone: armature-space Matrix}. Arms: FK keys (shoulder/upper/fore/hand
    eulers) or IK keys (target: wrist position, rot: hand orientation as a Matrix 3x3 or
    euler on the rest hand, pole, space: "arm" | "chest"). Legs: FK (thigh/shin/foot) or
    IK (ankle: position, foot: euler about the ankle, toe: degrees, pole)."""

    def __init__(self, arm, bones, L):
        self.arm = arm
        self.order = [b[0] for b in bones]
        self.parent = {b[0]: b[1] for b in bones}
        self.R = {n: arm.data.bones[n].matrix_local.copy() for n in self.order}
        self.Ri = {n: m.inverted() for n, m in self.R.items()}
        self.rel = {n: (self.Ri[self.parent[n]] @ self.R[n]) if self.parent[n] else self.R[n]
                    for n in self.order}
        self.reli = {n: m.inverted() for n, m in self.rel.items()}
        self.head = {n: npv(self.R[n].translation) for n in self.order}
        self.len = {n: arm.data.bones[n].length for n in self.order}
        self.up = {b[0]: b[4] for b in bones}
        self.L = L
        self.gap = 0.0

    # armature-space rest positions carried by a bone's pose delta
    def delta(self, PM, bone):
        return PM[bone] @ self.Ri[bone]

    def fk(self, PM, bone, q):
        par = self.parent[bone]
        D = self.delta(PM, par) if par else Matrix.Identity(4)
        PM[bone] = D @ rot_about(self.R[bone], self.head[bone], q)

    def solve(self, c):
        PM = {}
        PM["Root"] = self.R["Root"]
        h = c["hips"]
        PM["Hips"] = Matrix.Translation(V(h["pos"])) @ rot_about(self.R["Hips"], self.head["Hips"], E(*h["rot"]))
        for b, k in (("Spine", "spine"), ("Chest", "chest"), ("Neck", "neck"), ("Head", "head")):
            self.fk(PM, b, E(*c[k]))
        for s in SIDES:
            self._arm(PM, s, c["arm_" + s])
            self._fingers(PM, s, c["fingers_" + s])
        for s in SIDES:
            self._leg(PM, s, c["leg_" + s])
        return PM

    def _arm(self, PM, s, a):
        self.fk(PM, "Shoulder_" + s, E(*a.get("shoulder", (0, 0, 0))))
        up_n, fo_n, ha_n = "UpperArm_" + s, "Forearm_" + s, "Hand_" + s
        if "target" not in a:
            self.fk(PM, up_n, E(*a.get("upper", (0, 0, 0))))
            self.fk(PM, fo_n, E(*a.get("fore", (0, 0, 0))))
            self.fk(PM, ha_n, E(*a.get("hand", (0, 0, 0))))
            return
        D = self.delta(PM, "Chest") if a.get("space", "arm") == "chest" else Matrix.Identity(4)
        Ds = self.delta(PM, "Shoulder_" + s)
        sh = npv(Ds @ V(self.head[up_n]))
        tgt = npv(D @ V(a["target"]))
        rot = a.get("rot", (0, 0, 0))
        if isinstance(rot, Matrix):
            Rh = D.to_3x3() @ rot
        else:
            Rh = D.to_3x3() @ E(*rot).to_matrix() @ self.R[ha_n].to_3x3()
        pole = npv(D.to_3x3() @ V(a.get("pole", self.up[up_n])))
        l1, l2 = self.len[up_n], self.len[fo_n]
        el, end, gap = ik(sh, tgt, l1, l2, pole)
        self.gap = max(self.gap, gap)
        PM[up_n] = frame(sh, el, pole)
        F = frame(el, end, pole)
        # forearm twist: half of the hand's roll about the forearm, relative to the rest
        y = npv(F.col[1])
        hz_rest = npv((self.Ri[fo_n] @ self.R[ha_n]).col[2])            # hand Z in the rest forearm frame
        hz_rest = hz_rest[[0, 2]]
        hz_pose = np.array(Rh.col[2])
        hz_pose = np.array([hz_pose @ npv(F.col[0]), hz_pose @ npv(F.col[2])])
        tw = math.atan2(hz_rest[0] * hz_pose[1] - hz_rest[1] * hz_pose[0], hz_rest @ hz_pose)
        q = Quaternion(V(y), -0.5 * tw)
        PM[fo_n] = Matrix.Translation(V(el)) @ (q.to_matrix() @ F.to_3x3()).to_4x4()
        PM[ha_n] = Matrix.Translation(V(end)) @ Rh.to_4x4()

    def _fingers(self, PM, s, f):
        for g, bones in (("Thumb", ("Thumb1", "Thumb2")), ("Index", ("Index1", "Index2")),
                         ("Fingers", ("Fingers1", "Fingers2"))):
            v = f.get(g, 0.0)
            curls = v if isinstance(v, (tuple, list)) else (v, v)
            for bn, cu in zip(bones, curls):
                n = bn + "_" + s
                par = self.parent[n]
                PM[n] = PM[par] @ self.rel[n] @ Quaternion((1, 0, 0), -math.radians(cu)).to_matrix().to_4x4()

    def _leg(self, PM, s, g):
        th, sh, ft, to = "Thigh_" + s, "Shin_" + s, "Foot_" + s, "Toe_" + s
        if "ankle" not in g:
            self.fk(PM, th, E(*g.get("thigh", (0, 0, 0))))
            self.fk(PM, sh, E(*g.get("shin", (0, 0, 0))))
            self.fk(PM, ft, E(*g.get("foot", (0, 0, 0))))
        else:
            Dh = self.delta(PM, "Hips")
            hip = npv(Dh @ V(self.head[th]))
            ank = np.asarray(g["ankle"], float)
            qf = E(*g.get("foot", (0, 0, 0)))
            pole = np.asarray(g.get("pole", (qf @ Vector((0, -1, 0)))), float)
            kn, end, gap = ik(hip, ank, self.len[th], self.len[sh], pole)
            self.gap = max(self.gap, gap)
            PM[th] = frame(hip, kn, pole)
            PM[sh] = frame(kn, end, pole)
            Rf = qf.to_matrix() @ self.R[ft].to_3x3()
            PM[ft] = Matrix.Translation(V(end)) @ Rf.to_4x4()
        D = self.delta(PM, ft)
        PM[to] = D @ rot_about(self.R[to], self.head[to], E(g.get("toe", 0.0), 0, 0))

    def basis(self, PM):
        out = {}
        for n in self.order:
            par = self.parent[n]
            if par:
                out[n] = self.reli[n] @ PM[par].inverted() @ PM[n]
            else:
                out[n] = self.Ri[n] @ PM[n]
        return out


# ---------------------------------------------------------------- helpers for clips

def ankle_for_pivot(sv, side, pivot, rest_pivot, q):
    """Where the ankle must be for the foot (rotated by q about the ankle) to have its rest
    point `rest_pivot` (e.g. the ball or the heel) at `pivot`."""
    A = sv.L["ankle_" + side]
    off = q.to_matrix() @ V(np.asarray(rest_pivot, float) - A)
    return np.asarray(pivot, float) - npv(off)


def key_clip(sv, name, fn, T, loop=True, fps=FPS, extra_bones=()):
    """Solve fn(t) every frame and key it as action `name` (rotations on every bone, Hips
    location too), pushed to an NLA track so the exporter writes one animation per clip."""
    arm = sv.arm
    act = bpy.data.actions.get(name)
    if act is not None:
        bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name)
    arm.animation_data_create()
    arm.animation_data.action = act
    nf = max(int(round(T * fps)), 1)
    prev = {}
    sv.gap = 0.0
    frames = []
    for f in range(nf + 1):
        t = (f % nf) / fps if loop else min(f / fps, T)
        PM = sv.solve(fn(t))
        frames.append({k: v.copy() for k, v in PM.items()})
        for bn, B in sv.basis(PM).items():
            if bn == "Root":
                continue
            pb = arm.pose.bones[bn]
            loc, q, _ = B.decompose()
            if bn in prev and prev[bn].dot(q) < 0:
                q.negate()
            prev[bn] = q
            pb.rotation_quaternion = q
            pb.keyframe_insert("rotation_quaternion", frame=f, group=bn)
            if bn == "Hips" or loc.length > 1e-4:
                pb.location = loc
                pb.keyframe_insert("location", frame=f, group=bn)
    arm.animation_data.action = None
    track = arm.animation_data.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, 0, act)
    strip.name = name
    track.mute = True
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
    return act, frames
