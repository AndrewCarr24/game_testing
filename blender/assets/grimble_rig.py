"""Skeleton, skin weights and animations for the Grimble (blender/assets/grimble.py).

Everything is generated from the model's own landmarks (eyes, hands on the staff, the
staff, the feet), so the rig follows the mesh if the model changes.

Pose solver: each frame, every bone's armature-space matrix is computed directly (FK
rotations about joints for the spine / hem, analytic two-bone IK for arms and legs,
the hands rigidly attached to the staff or placed by the action) and converted to the
bone's local basis, which is keyframed. No constraints, so the glTF gets exactly what
the solver computed. The staff bone is a child of Hand.R and never moves relative to
it: the right hand is placed wherever the staff has to be.

Actions (30 fps): Walk (loop, in place), Knock (one shot), Wave (loop), Idle (loop).
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

FPS = 30
FINGERS = ("Index", "Middle", "Ring", "Pinky", "Thumb")
# the open hand: per finger the spread (degrees toward the thumb side) and the curl at
# each of its three joints (degrees toward the palm)
OPEN = dict(Index=(16, (6, 14, 16)), Middle=(5, (6, 14, 16)), Ring=(-6, (8, 15, 17)),
            Pinky=(-17, (10, 16, 18)), Thumb=(0, (10, 12, 14)))

# walk
WALK_T = 2.8          # s per cycle (two steps)
WALK_S = 4.2          # m per cycle (the root has to move this far per cycle)
WALK_DUTY = 0.6       # fraction of the cycle each foot is planted
# knock
KNOCK_T = 3.5
KNOCK_D = 2.05        # contact plane: this far in front of the origin (Blender -Y)
KNOCK_TIMES = (1.25, 1.95, 2.65)
WAVE_T = 2.5
IDLE_T = 4.0


def log(*a):
    print("GRIMBLE", *a, flush=True)


def _v(x):
    return Vector([float(c) for c in x])


def _np(v):
    return np.array([v[0], v[1], v[2]], float)


def smooth(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def ik(a, t, l1, l2, pole):
    """Two-bone IK: joint position for a chain from a to t with lengths l1, l2,
    bending toward pole (a direction). Returns (joint, reached target)."""
    a, t, pole = (np.asarray(x, float) for x in (a, t, pole))
    d = t - a
    L = np.linalg.norm(d)
    u = d / max(L, 1e-9)
    Lc = min(max(L, abs(l1 - l2) + 1e-4), (l1 + l2) * 0.9995)
    x = (l1 * l1 - l2 * l2 + Lc * Lc) / (2 * Lc)
    h = math.sqrt(max(l1 * l1 - x * x, 0.0))
    pp = pole - (pole @ u) * u
    pp /= np.linalg.norm(pp) + 1e-12
    return a + u * x + pp * h, a + u * Lc


def frame(head, tail, up):
    """Bone matrix: Y along head->tail, Z toward `up` (Blender's align_roll), at head."""
    y = np.asarray(tail, float) - np.asarray(head, float)
    y /= np.linalg.norm(y)
    z = np.asarray(up, float) - (np.asarray(up, float) @ y) * y
    z /= np.linalg.norm(z)
    x = np.cross(y, z)
    m = Matrix.Identity(4)
    for r in range(3):
        m[r][0], m[r][1], m[r][2], m[r][3] = x[r], y[r], z[r], head[r]
    return m


def rot_about(M, pivot, q):
    p = _v(pivot)
    return Matrix.Translation(p) @ q.to_matrix().to_4x4() @ Matrix.Translation(-p) @ M


def euler_q(x=0.0, y=0.0, z=0.0):
    """Rotation from degrees about the armature's X (pitch: + tips the top back),
    Y (roll) and Z (yaw), applied in that order."""
    return (Quaternion((0, 0, 1), math.radians(z)) @ Quaternion((0, 1, 0), math.radians(y))
            @ Quaternion((1, 0, 0), -math.radians(x)))


# ---------------------------------------------------------------- skeleton

def skeleton(lm):
    """Bone list [(name, parent, head, tail, up)] in the model's final frame."""
    B = []

    def add(n, par, h, t, up=(0, -1, 0)):
        B.append((n, par, np.asarray(h, float), np.asarray(t, float), np.asarray(up, float)))

    add("Root", None, (0, 0, 0), (0, 0, 0.6))
    add("Hips", "Root", (-0.15, 0.15, 2.4), (-0.15, 0.12, 3.0))
    add("Spine1", "Hips", (-0.15, 0.12, 3.0), (-0.12, 0.05, 3.6))
    add("Spine2", "Spine1", (-0.12, 0.05, 3.6), (-0.05, -0.05, 4.15))
    add("Spine3", "Spine2", (-0.05, -0.05, 4.15), (0.1, -0.1, 4.55))
    add("Neck", "Spine3", (0.1, -0.1, 4.55), (0.25, -0.12, 4.9))
    hc = (lm["eye_L"] + lm["eye_R"]) / 2 + np.array([0, 0.6, 0])
    add("Head", "Neck", (0.25, -0.12, 4.9), (hc[0], hc[1], 6.7))
    arms = dict(L=dict(root=(0.2, -0.1, 4.45), sh=(0.95, 0.05, 4.6), pole=(1.0, 0.3, -0.6)),
                R=dict(root=(-0.1, -0.1, 4.45), sh=(-0.9, 0.0, 4.65), pole=(-0.8, 0.5, -1.0)))
    for s, a in arms.items():
        w = lm["wrist_" + s]
        e, _ = ik(a["sh"], w, 1.15, 1.15, a["pole"])
        add("Shoulder." + s, "Spine3", a["root"], a["sh"])
        add("UpperArm." + s, "Shoulder." + s, a["sh"], e, a["pole"])
        add("Forearm." + s, "UpperArm." + s, e, w, a["pole"])
        add("Hand." + s, "Forearm." + s, w, lm["pad_" + s], (0, 0, 1))
        for f in lm["fingers_" + s]:                 # 3 bones per finger, along its centre line
            for j in range(3):
                par = "Hand." + s if j == 0 else f"{f['name']}{j}.{s}"
                add(f"{f['name']}{j + 1}.{s}", par, f["J"][j], f["J"][j + 1], f["up"][j])
    add("Staff", "Hand.R", lm["staff_tip"], lm["grip_R"])
    for s, hip_x in (("L", 0.55), ("R", -0.6)):
        ank, toe = lm["ankle_" + s], lm["toe_" + s]
        hip = (hip_x, 0.12, 2.35)
        pole = (0.15 if s == "L" else -0.15, -1, 0)
        k, _ = ik(hip, ank, 1.2, 1.2, pole)
        add("Thigh." + s, "Hips", hip, k, pole)
        add("Shin." + s, "Thigh." + s, k, ank, pole)
        add("Foot." + s, "Shin." + s, ank, toe, (0, 0, 1))
    hems = dict(F=[(-0.15, -0.55, 2.3), (-0.15, -0.8, 1.15), (-0.15, -1.0, 0.05)],
                B=[(-0.15, 0.75, 2.3), (-0.1, 1.25, 1.15), (0.0, 1.8, 0.05)],
                L=[(0.75, 0.15, 2.3), (1.05, 0.2, 1.15), (1.35, 0.3, 0.05)],
                R=[(-1.05, 0.15, 2.3), (-1.3, 0.2, 1.15), (-1.5, 0.3, 0.05)])
    for n, pts in hems.items():
        add(f"Hem.{n}1", "Hips", pts[0], pts[1])
        add(f"Hem.{n}2", f"Hem.{n}1", pts[1], pts[2])
    return B, arms


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
        eb.head, eb.tail = _v(h), _v(t)
        eb.align_roll(_v(up))
        if par:
            eb.parent = arm_data.edit_bones[par]
        eb.use_connect = False
        eb.use_deform = True
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.select_set(False)
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    return arm


# ---------------------------------------------------------------- skinning

def _seg_dist(P, a, b):
    ab = b - a
    t = np.clip(((P - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)


def _weld(meshes):
    """Union vertex ids over meshes split from one surface (seams share positions)."""
    allv = np.concatenate([v for v, _ in meshes])
    key = np.round(allv * 1e4).astype(np.int64)
    _, uid, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    ids, off, edges = [], 0, []
    for v, t in meshes:
        m = inv[off:off + len(v)]
        ids.append(m)
        if len(t):
            tt = m[t]
            edges.append(np.concatenate([tt[:, [0, 1]], tt[:, [1, 2]], tt[:, [2, 0]]]))
        off += len(v)
    return allv[uid], ids, np.concatenate(edges)


def skin(arm, objs, bones, hand_info, lm):
    """Vertex groups + Armature modifiers. objs: dict part name -> object."""
    names = [b[0] for b in bones]
    bi = {n: i for i, n in enumerate(names)}
    seg = {b[0]: (b[2], b[3]) for b in bones}
    nb = len(names)

    def arrays(ob):
        me = ob.data
        v = np.zeros(len(me.vertices) * 3)
        me.vertices.foreach_get("co", v)
        me.calc_loop_triangles()
        t = np.zeros(len(me.loop_triangles) * 3, np.int64)
        me.loop_triangles.foreach_get("vertices", t)
        return v.reshape(-1, 3), t.reshape(-1, 3)

    body_v, body_t = arrays(objs["Body"])
    cloak_v, cloak_t = arrays(objs["Cloak"])
    U, (ib, ic), edges = _weld([(body_v, body_t), (cloak_v, cloak_t)])
    n = len(U)
    W = np.zeros((n, nb))
    # envelopes: weight = gain / (d + 0.1)^4, faded out beyond `cut` metres
    env = {"Hips": (1.0, 9), "Spine1": (1.0, 9), "Spine2": (1.0, 9), "Spine3": (1.0, 9), "Neck": (0.7, 9),
           "Head": (1.0, 2.5)}
    for s in "LR":
        env.update({f"Shoulder.{s}": (0.6, 0.9), f"UpperArm.{s}": (1.0, 0.85), f"Forearm.{s}": (1.0, 0.75),
                    f"Thigh.{s}": (0.3, 0.8), f"Shin.{s}": (0.3, 0.7), f"Foot.{s}": (0.6, 0.55)})
    for h in "FBLR":
        env.update({f"Hem.{h}1": (1.0, 9), f"Hem.{h}2": (1.0, 9)})
    D = {}
    for b, (g, cut) in env.items():
        a, t = seg[b]
        d = _seg_dist(U, a, t)
        D[b] = d
        fade = 1 - np.clip((d - 0.7 * cut) / (0.3 * cut), 0, 1) if cut < 9 else 1.0
        W[:, bi[b]] = g / (d + 0.1) ** 4 * fade
    W /= W.sum(1, keepdims=True) + 1e-12
    # the hood and the face are rigid with the head (except right by the sleeves)
    d_arm = np.min([D[f"{k}.{s}"] for k in ("UpperArm", "Forearm") for s in "LR"], axis=0)
    armness = 1 - np.clip((d_arm - 0.45) / 0.3, 0, 1)
    z = U[:, 2]
    head = np.clip((z - 4.9) / 0.5, 0, 1) * (1 - armness)
    face = np.zeros(n, bool)
    face[ib[body_v[:, 2] > 4.25]] = True
    head[face] = 1.0
    onehot = np.zeros(nb)
    onehot[bi["Head"]] = 1
    W = head[:, None] * onehot + (1 - head[:, None]) * W
    pinned = head > 0.98
    # the feet are rigid with their foot bones
    for s, sign in (("L", 1), ("R", -1)):
        fm = (body_v[:, 2] < 1.0) & (np.sign(body_v[:, 0] - 0.0) == sign)
        W[ib[fm]] = 0
        W[ib[fm], bi["Foot." + s]] = 1
        pinned[ib[fm]] = True
    # smooth over the welded surface (pinned rows stay)
    e = np.concatenate([edges, edges[:, ::-1]])
    deg = np.maximum(np.bincount(e[:, 0], minlength=n), 1)[:, None]
    for _ in range(8):
        acc = np.zeros_like(W)
        np.add.at(acc, e[:, 0], W[e[:, 1]])
        W = np.where(pinned[:, None], W, 0.5 * W + 0.5 * acc / deg)
    # top 4, normalised
    order = np.argsort(-W, axis=1)
    keep = np.zeros_like(W, bool)
    np.put_along_axis(keep, order[:, :4], True, axis=1)
    W = np.where(keep & (W > 0.01), W, 0)
    W /= W.sum(1, keepdims=True) + 1e-12

    def assign(ob, rows):
        # vertices left without weights (loose fan centres): rigid with the nearest bone
        zero = np.nonzero(rows.sum(1) < 1e-6)[0]
        if len(zero):
            co = np.array([ob.data.vertices[i].co[:] for i in zero])
            dist = np.stack([_seg_dist(co, a, t) for (a, t) in (seg[nm] for nm in names)], 1)
            rows = rows.copy()
            rows[zero, np.argmin(dist, 1)] = 1.0
        for nm in names:
            ob.vertex_groups.new(name=nm)
        q = np.round(rows * 200).astype(int)
        for j in range(nb):
            col = q[:, j]
            for val in np.unique(col[col > 0]):
                ob.vertex_groups[j].add(np.nonzero(col == val)[0].tolist(), val / 200.0, "REPLACE")
        m = ob.modifiers.new("Armature", "ARMATURE")
        m.object = arm
        ob.parent = arm

    assign(objs["Body"], W[ib])
    assign(objs["Cloak"], W[ic])

    def rigid(ob, groups):
        rows = np.zeros((len(ob.data.vertices), nb))
        for bone, idx in groups:
            rows[idx, bi[bone]] = 1
        assign(ob, rows)

    # hands: the palm / wrist on Hand.X; each finger along its length on its three bones,
    # blended over the knuckles; the claws rigid with the last bone
    nv = len(objs["Hands"].data.vertices)
    rows = np.zeros((nv, nb))
    for side, h in zip("RL", hand_info):         # the hands are listed upper (right) first
        a, b = h["verts"]
        rows[a:min(b, nv), bi["Hand." + side]] = 1
        for f in h["fingers"]:
            ids = [bi["Hand." + side]] + [bi[f"{f['name']}{j}.{side}"] for j in (1, 2, 3)]
            v0, v1 = f["tube"]
            k = np.arange(v0, v1)
            ring = np.minimum((k - v0) // f["sides"], len(f["ts"]) - 1)
            t = np.where(k - v0 >= len(f["ts"]) * f["sides"], 1.0, f["ts"][ring])
            wb = np.zeros((len(k), 4))
            J = f["joints"]
            wdt = 0.07
            for jj in range(3):                     # weight of segment jj+1 vs jj at joint J[jj]
                x = np.clip((t - (J[jj] - wdt)) / (2 * wdt), 0, 1)
                wb[:, jj + 1] = x
            w = np.zeros((len(k), 4))
            w[:, 0] = 1 - wb[:, 1]
            w[:, 1] = wb[:, 1] - wb[:, 2]
            w[:, 2] = wb[:, 2] - wb[:, 3]
            w[:, 3] = wb[:, 3]
            rows[k] = 0
            for jj in range(4):
                rows[k, ids[jj]] = w[:, jj]
            c0, c1 = f["claw"]
            rows[c0:c1] = 0
            rows[c0:c1, ids[3]] = 1
    assign(objs["Hands"], rows)
    rigid(objs["Staff"], [("Staff", np.arange(len(objs["Staff"].data.vertices)))])
    rigid(objs["Sockets"], [("Head", np.arange(len(objs["Sockets"].data.vertices)))])
    # eyes ride on the head bone, pivots unchanged
    for ob in objs["Eyes"]:
        mw = ob.matrix_world.copy()
        bone = arm.data.bones["Head"]
        ob.parent = arm
        ob.parent_type = "BONE"
        ob.parent_bone = "Head"
        ob.matrix_parent_inverse = (bone.matrix_local @ Matrix.Translation((0, bone.length, 0))).inverted()
        ob.matrix_basis = mw
    log(f"skinned: {n} surface vertices, {nb} bones; head-rigid {int(pinned.sum())}")


# ------------------------------------------------------------------ solver

class Solver:
    def __init__(self, arm, bones, arms, lm, hand_verts):
        self.arm = arm
        self.order = [b[0] for b in bones]
        self.parent = {b[0]: b[1] for b in bones}
        self.R = {n: arm.data.bones[n].matrix_local.copy() for n in self.order}
        self.rel = {n: (self.R[self.parent[n]].inverted() @ self.R[n]) if self.parent[n] else self.R[n]
                    for n in self.order}
        self.len = {n: arm.data.bones[n].length for n in self.order}
        self.arms = arms
        self.lm = lm
        self.hand_verts = hand_verts      # side -> (N, 3) rest vertices of the hand mesh
        # reference frames of the IK bones at rest (head -> tail, toward the rest pole):
        # a pose frame maps onto the bone's own matrix through these, whatever its roll
        self.Fr = {}
        self.up = {b[0]: b[4] for b in bones}
        for b in bones:
            if b[0].rstrip(".LR")[:-1] in FINGERS:
                bb = arm.data.bones[b[0]]
                self.Fr[b[0]] = frame(_np(bb.head_local), _np(bb.tail_local), b[4]).inverted() @ self.R[b[0]]
        for s in "LR":
            for b, pole in ((f"UpperArm.{s}", arms[s]["pole"]), (f"Forearm.{s}", arms[s]["pole"]),
                            (f"Thigh.{s}", (0.15 if s == "L" else -0.15, -1, 0)),
                            (f"Shin.{s}", (0.15 if s == "L" else -0.15, -1, 0))):
                bb = arm.data.bones[b]
                self.Fr[b] = frame(_np(bb.head_local), _np(bb.tail_local), pole).inverted() @ self.R[b]
        self.gap = 0.0
        self.gaps = {}

    def default(self, PM, n):
        par = self.parent[n]
        return PM[par] @ self.rel[n] if par else self.R[n].copy()

    def solve(self, c):
        """c: controls (see the actions). Returns pose matrices (armature space)."""
        PM = {}
        PM["Root"] = self.R["Root"].copy()
        M = self.default(PM, "Hips")
        M = Matrix.Translation(_v(c.get("hips_off", (0, 0, 0)))) @ rot_about(
            M, M.translation, c.get("hips_rot", Quaternion()))
        PM["Hips"] = M
        for b in ("Spine1", "Spine2", "Spine3", "Neck", "Head"):
            M = self.default(PM, b)
            PM[b] = rot_about(M, M.translation, c.get(b, Quaternion()))
        torso = (PM["Spine3"] @ self.R["Spine3"].inverted()).to_quaternion()
        for s in "LR":
            M = self.default(PM, "Shoulder." + s)
            PM["Shoulder." + s] = rot_about(M, M.translation, c.get("Shoulder." + s, Quaternion()))
            HM = c["hand_" + s]
            S = _np(self.default(PM, "UpperArm." + s).translation)
            pole = _np(torso @ _v(self.arms[s]["pole"]) + _v(c.get("pole_" + s, (0, 0, 0))))
            W = _np(HM.translation)
            ax = c.get("slide_" + s)
            if ax is not None:          # a hand on the staff may slide along it to stay in reach
                L = (self.len["UpperArm." + s] + self.len["Forearm." + s]) * 0.985
                d = W - S
                if np.linalg.norm(d) > L:
                    ax = np.asarray(ax, float)
                    bq, cq = d @ ax, d @ d - L * L
                    disc = bq * bq - cq
                    if disc >= 0:
                        r1, r2 = -bq - math.sqrt(disc), -bq + math.sqrt(disc)
                        a = r1 if abs(r1) < abs(r2) else r2
                        a = max(-0.6, min(0.6, a))
                        W = W + a * ax
                        HM = Matrix.Translation(_v(a * ax)) @ HM
            E, Wr = ik(S, W, self.len["UpperArm." + s], self.len["Forearm." + s], pole)
            g = float(np.linalg.norm(Wr - W))
            self.gaps["arm_" + s] = max(self.gaps.get("arm_" + s, 0), g)
            self.gap = max(self.gap, g)
            PM["UpperArm." + s] = frame(S, E, pole) @ self.Fr["UpperArm." + s]
            PM["Forearm." + s] = frame(E, Wr, pole) @ self.Fr["Forearm." + s]
            HMr = HM.copy()
            HMr.translation = _v(Wr)
            PM["Hand." + s] = HMr
        PM["Staff"] = PM["Hand.R"] @ self.rel["Staff"]
        for s in "LR":
            self._fingers(PM, s, c.get("open_" + s, 0.0), c.get("flutter_" + s, (0, 0, 0, 0, 0)))
        yaw = c.get("hips_rot", Quaternion())
        for s in "LR":
            hip = _np(self.default(PM, "Thigh." + s).translation)
            FM = c["foot_" + s]
            A = _np(FM.translation)
            pole = _np(yaw @ Vector((0.15 if s == "L" else -0.15, -1, 0)))
            K, Ar = ik(hip, A, self.len["Thigh." + s], self.len["Shin." + s], pole)
            g = float(np.linalg.norm(Ar - A))
            self.gaps["leg_" + s] = max(self.gaps.get("leg_" + s, 0), g)
            self.gap = max(self.gap, g)
            PM["Thigh." + s] = frame(hip, K, pole) @ self.Fr["Thigh." + s]
            PM["Shin." + s] = frame(K, Ar, pole) @ self.Fr["Shin." + s]
            FMr = FM.copy()
            FMr.translation = _v(Ar)
            PM["Foot." + s] = FMr
        for h in "FBLR":
            for k in (1, 2):
                b = f"Hem.{h}{k}"
                M = self.default(PM, b)
                d = c.get(b, (0, 0, 0))
                tail = M @ Vector((0, self.len[b], 0))
                q = (tail - M.translation).rotation_difference(tail + _v(d) - M.translation)
                PM[b] = rot_about(M, M.translation, q)
        return PM

    def _fingers(self, PM, s, o, flutter):
        """Finger chains: the modelled staff grip at o = 0; o = 1 is the open hand (fingers
        spread from the knuckles along the hand's forward axis, slightly curled toward the
        palm; the thumb out to the side)."""
        names = [[f"{f}{j}.{s}" for j in (1, 2, 3)] for f in FINGERS]
        if o <= 0:
            for chain in names:
                for b in chain:
                    PM[b] = self.default(PM, b)
            return
        F, N, Tp = self.open_axes[s]
        X = PM["Hand." + s] @ self.R["Hand." + s].inverted()     # the hand's motion from rest
        for fi, chain in enumerate(names):
            spread, curls = OPEN[FINGERS[fi]]
            a = math.radians(spread)
            if FINGERS[fi] == "Thumb":
                d = F * 0.45 + Tp * 0.9 + N * 0.3
            else:
                d = F * math.cos(a) + Tp * math.sin(a)
            d = _v(d).normalized()
            head = self.R[chain[0]].translation.copy()
            parent_open = PM["Hand." + s]
            parent_pose = PM["Hand." + s]
            for j, b in enumerate(chain):
                c = math.radians(curls[j] + flutter[fi] * (1 + j) / 3)
                d = (d * math.cos(c) + _v(N) * math.sin(c)).normalized()
                tail = head + d * self.len[b]
                Mo = X @ frame(_np(head), _np(tail), N) @ self.Fr[b]
                Bo = (parent_open @ self.rel[b]).inverted() @ Mo
                q = Quaternion().slerp(Bo.to_quaternion(), o)
                loc = Bo.translation * o
                PM[b] = parent_pose @ self.rel[b] @ (Matrix.Translation(loc) @ q.to_matrix().to_4x4())
                parent_open, parent_pose = Mo, PM[b]
                head = tail

    def basis(self, PM):
        out = {}
        for n in self.order:
            par = self.parent[n]
            B = (PM[par] @ self.rel[n]).inverted() @ PM[n] if par else self.R[n].inverted() @ PM[n]
            out[n] = B
        return out

    # helpers for actions
    def on_staff(self, side, S=None):
        """Hand matrix holding the staff (S: the staff's rigid transform)."""
        S = S or Matrix.Identity(4)
        return S @ self.R["Hand." + side]

    def hand_at(self, side, wrist, q):
        """The rest hand rotated by q about its wrist and moved so the wrist is at `wrist`."""
        R = self.R["Hand." + side]
        w0 = R.translation
        return Matrix.Translation(_v(wrist)) @ q.to_matrix().to_4x4() @ Matrix.Translation(-w0) @ R

    def foot_at(self, side, offset, pitch=0.0):
        R = self.R["Foot." + side]
        a = R.translation
        q = Quaternion((1, 0, 0), math.radians(pitch))
        return Matrix.Translation(a + _v(offset)) @ q.to_matrix().to_4x4() @ Matrix.Translation(-a) @ R


# ----------------------------------------------------------------- actions

def _rest_controls(sv):
    return dict(hand_L=sv.on_staff("L"), hand_R=sv.on_staff("R"),
                foot_L=sv.foot_at("L", (0, 0, 0)), foot_R=sv.foot_at("R", (0, 0, 0)))


def staff_transform(sv, tip, grip):
    """Rigid transform of the staff: its rest tip -> tip, rest grip -> grip (the length
    is kept: grip is moved along z to fit)."""
    tip0, g0 = _v(sv.lm["staff_tip"]), _v(sv.lm["grip_R"])
    L = (g0 - tip0).length
    tip, grip = _v(tip), _v(grip)
    dxy = (grip - tip).xy.length
    grip.z = tip.z + math.sqrt(max(L * L - dxy * dxy, 0.01))
    q = (tip0 - g0).rotation_difference(tip - grip)
    return Matrix.Translation(grip) @ q.to_matrix().to_4x4() @ Matrix.Translation(-g0)


def walk(sv, t):
    ph = (t / WALK_T) % 1.0
    v = WALK_S / WALK_T
    c = {}
    feet_y = {}
    for s, off in (("L", 0.0), ("R", 0.5)):
        u = (ph + off) % 1.0
        half = WALK_S * WALK_DUTY / 2
        if u < WALK_DUTY:
            y = -half + WALK_S * u
            z, pitch = 0.0, 0.0
        else:
            k = smooth(0, 1, (u - WALK_DUTY) / (1 - WALK_DUTY))
            y = half - 2 * half * k
            z = 0.42 * math.sin(math.pi * k)
            pitch = -14 * math.sin(math.pi * k)            # toes up through the swing
        feet_y[s] = y
        c["foot_" + s] = sv.foot_at(s, (0, y, z), pitch)
    # body: lowest at double support, sways over the stance foot, yaws with the stride
    bob = -0.07 - 0.07 * math.cos(4 * math.pi * (ph - 0.05))
    sway = 0.13 * math.cos(2 * math.pi * (ph - 0.3))
    c["hips_off"] = (sway, 0.0, bob)
    yaw = 5 * math.sin(2 * math.pi * (ph - 0.05))
    c["hips_rot"] = euler_q(0, 2.5 * math.cos(2 * math.pi * (ph - 0.3)), yaw)
    c["Spine1"] = euler_q(-3, 0, -0.5 * yaw)
    c["Spine2"] = euler_q(-2 + 1.0 * math.cos(4 * math.pi * ph), -1.5 * math.cos(2 * math.pi * (ph - 0.3)), -0.4 * yaw)
    c["Spine3"] = euler_q(-1, 0, 0)
    c["Neck"] = euler_q(1.5 * math.cos(4 * math.pi * (ph - 0.1)), 0, 0.2 * yaw)
    c["Head"] = euler_q(0, 1.5 * math.cos(2 * math.pi * (ph - 0.35)), 0)
    # the staff: planted (tip on the ground, sliding back with the ground) for half the
    # cycle, then swung forward; the right hand rides along
    tip0 = sv.lm["staff_tip"]
    g0 = sv.lm["grip_R"]
    ps = (ph - 0.45) % 1.0
    plant = 0.4
    reach = v * WALK_T * plant / 2
    if ps < plant:
        ty, tz = tip0[1] - reach + 2 * reach * (ps / plant), 0.0
    else:
        k = smooth(0, 1, (ps - plant) / (1 - plant))
        ty, tz = tip0[1] + reach - 2 * reach * k, 0.45 * math.sin(math.pi * k)
    tip = (tip0[0] + 0.5 * sway, ty, tz)
    grip = (g0[0] + 0.7 * sway, g0[1] + 0.12 * (ty - tip0[1]) - 0.05, g0[2] + bob)
    S = staff_transform(sv, tip, grip)
    c["hand_R"] = sv.on_staff("R", S)
    c["hand_L"] = sv.on_staff("L", S)
    c["slide_L"] = _np(S.to_3x3() @ _v(sv.lm["axis_L"]))
    c["staff"] = S
    # hem: pushed by the legs, swinging with a lag
    lag = (ph - 0.07) % 1.0
    fwd = min(feet_y["L"], feet_y["R"])
    back = max(feet_y["L"], feet_y["R"])
    c["Hem.F1"] = (0, 0.28 * min(fwd, 0) , 0.05 * min(fwd, 0) ** 2)
    c["Hem.F2"] = (0, 0.22 * min(fwd, 0) - 0.06 * math.sin(2 * math.pi * 2 * lag), 0)
    c["Hem.B1"] = (0, 0.2 * max(back, 0), 0)
    c["Hem.B2"] = (0, 0.15 * max(back, 0) + 0.08 * math.sin(2 * math.pi * 2 * lag), 0)
    for s in "LR":
        y = feet_y[s]
        c[f"Hem.{s}1"] = (0.0, 0.22 * y, 0)
        c[f"Hem.{s}2"] = (0.06 * math.sin(2 * math.pi * lag) * (1 if s == "L" else -1), 0.18 * y, 0)
    return c


def _knock_contact(sv, q):
    """Wrist offset so that the hand's front-most point (along -Y) touches the plane."""
    verts = sv.hand_verts["L"]
    w0 = _np(sv.R["Hand.L"].translation)
    rel = (np.array(q.to_matrix()) @ (verts - w0).T).T
    i = int(np.argmin(rel[:, 1]))
    return rel[i]                     # contact point relative to the wrist


KNOCK_WRIST = (0.95, None, 4.15)      # x, (y from the plane), z of the wrist while knocking


def knock(sv, t):
    c = _rest_controls(sv)
    q_k = sv.knock_q
    rel = sv.knock_rel
    wy_contact = -KNOCK_D - rel[1]
    ready = np.array([KNOCK_WRIST[0], wy_contact + 0.35, KNOCK_WRIST[2]])
    rest_w = _np(sv.R["Hand.L"].translation)
    t_out, t_back = 0.85, 2.85
    if t < t_out:                       # off the staff, up and forward
        k = smooth(0, 1, t / t_out)
        lift = np.array([0.15, 0.1, 0.35]) * math.sin(math.pi * k)
        w = rest_w + (ready - rest_w) * k + lift
        q = Quaternion().slerp(q_k, k)
    elif t < t_back:
        w = ready.copy()
        for tk in KNOCK_TIMES:            # three slow taps: a quick 0.2 s approach, a soft retract
            dt = t - tk
            if -0.22 < dt < 0:
                w[1] -= 0.35 * smooth(-0.22, 0, dt)
            elif 0 <= dt < 0.3:
                w[1] -= 0.35 * (1 - smooth(0, 0.3, dt))
        w[2] += 0.04 * math.sin(2 * math.pi * (t - t_out) / 0.7)
        q = q_k
    else:                               # back onto the staff
        k = smooth(0, 1, (t - t_back) / (KNOCK_T - t_back))
        lift = np.array([0.15, 0.1, 0.3]) * math.sin(math.pi * k)
        w = ready + (rest_w - ready) * k + lift
        q = q_k.slerp(Quaternion(), k)
    c["hand_L"] = sv.hand_at("L", w, q)
    env = smooth(0, 0.9, t) * (1 - smooth(2.8, KNOCK_T, t))
    c["Spine2"] = euler_q(-4 * env, -2 * env, 6 * env)
    c["Spine3"] = euler_q(-3 * env, 0, 4 * env)
    c["Head"] = euler_q(-4 * env, -6 * env, -4 * env)
    c["Shoulder.L"] = euler_q(0, -6 * env, 0)
    c["hips_off"] = (0.05 * env, -0.08 * env, -0.02 * env)
    c["pole_L"] = (0.6 * env, 0.4 * env, -0.3 * env)
    return c


WAVE_WRIST = (2.0, -0.7, 5.45)


def wave(sv, t):
    c = _rest_controls(sv)
    ph = (t / WAVE_T) % 1.0
    sw = math.sin(2 * math.pi * 2 * ph)                 # two waves per loop
    w = np.array(WAVE_WRIST) + np.array([0.22 * sw, 0.0, 0.05 * abs(sw)])
    c["hand_L"] = sv.hand_at("L", w, Quaternion((0, 1, 0), math.radians(18 * sw)) @ sv.wave_q)
    c["pole_L"] = (0.8, 0.6, -0.6)
    c["open_L"] = 1.0             # open for the whole clip (the engine's cross-fade does the opening)
    c["flutter_L"] = tuple(5 * math.sin(2 * math.pi * (4 * ph + 0.17 * k)) for k in range(5))
    c["Shoulder.L"] = euler_q(0, -10, 0)
    c["Spine2"] = euler_q(-2, -3, 3)
    c["Spine3"] = euler_q(-1, -2, 2)
    c["Head"] = euler_q(-3, -9 + 2 * math.sin(2 * math.pi * ph), 4 * math.sin(2 * math.pi * ph))
    c["hips_off"] = (0.04, 0, 0)
    return c


def idle(sv, t):
    c = _rest_controls(sv)
    ph = t / IDLE_T
    br = math.sin(2 * math.pi * ph)
    c["hips_off"] = (0.05 * math.sin(2 * math.pi * ph), 0, -0.015 * (1 - math.cos(4 * math.pi * ph)))
    c["hips_rot"] = euler_q(0, 1.0 * math.sin(2 * math.pi * ph), 0)
    c["Spine2"] = euler_q(1.4 * br, -0.8 * math.sin(2 * math.pi * ph), 0)
    c["Spine3"] = euler_q(1.0 * br, 0, 0)
    c["Neck"] = euler_q(-0.6 * br, 0, 0)
    c["Head"] = euler_q(1.5 * math.sin(2 * math.pi * ph + 0.6), -5 * math.sin(2 * math.pi * ph), 2.5 * math.sin(2 * math.pi * ph))
    for s in "LR":
        c[f"Hem.{s}2"] = (0.02 * math.sin(2 * math.pi * ph) * (1 if s == "L" else -1), 0, 0)
    return c


ACTIONS = (("Walk", walk, WALK_T), ("Knock", knock, KNOCK_T), ("Wave", wave, WAVE_T), ("Idle", idle, IDLE_T))


def bake_actions(sv, scene):
    arm = sv.arm
    scene.render.fps = FPS
    arm.animation_data_create()
    prefs = bpy.context.preferences.edit
    old = prefs.keyframe_new_interpolation_type
    prefs.keyframe_new_interpolation_type = "LINEAR"
    made = []
    for name, fn, T in ACTIONS:
        act = bpy.data.actions.get(name)
        if act is not None:
            bpy.data.actions.remove(act)
        act = bpy.data.actions.new(name)
        arm.animation_data.action = act
        nf = int(round(T * FPS))
        prev = {}
        sv.gap = 0.0
        sv.gaps = {}
        for f in range(nf + 1):
            t = (f % nf) / FPS if name != "Knock" else f / FPS
            PM = sv.solve(fn(sv, t))
            for bn, B in sv.basis(PM).items():
                pb = arm.pose.bones[bn]
                loc, q, _ = B.decompose()
                if bn in prev and prev[bn].dot(q) < 0:
                    q.negate()
                prev[bn] = q
                pb.location = loc
                pb.rotation_quaternion = q
                pb.keyframe_insert("location", frame=f, group=bn)
                pb.keyframe_insert("rotation_quaternion", frame=f, group=bn)
        log(f"action {name}: {nf} frames ({T:.2f} s), max IK gap {sv.gap * 100:.1f} cm "
            + " ".join(f"{k} {v * 100:.0f}" for k, v in sv.gaps.items() if v > 0.005))
        arm.animation_data.action = None
        track = arm.animation_data.nla_tracks.new()
        track.name = name
        strip = track.strips.new(name, 0, act)
        strip.name = name
        track.mute = True
        made.append(act)
    prefs.keyframe_new_interpolation_type = old
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
    return made


def prepare(sv):
    """Precompute action constants that depend on the mesh (knock contact, wave pose)."""
    # knock: the left fist turned (about the vertical) so its knuckles face forward
    kd = sv.lm["knuckle_L"]
    yaw = math.degrees(math.atan2(-1.0, 0.0) - math.atan2(kd[1], kd[0]))
    sv.knock_q = euler_q(0, 0, yaw)
    sv.knock_rel = _knock_contact(sv, sv.knock_q)
    # open-hand axes (rest space) per hand: F from the wrist toward the knuckles, N the palm
    # side (toward where the staff is), Tp across the fingers toward the thumb (up the staff)
    sv.open_axes = {}
    for s in "LR":
        F = sv.lm["pad_" + s] - sv.lm["wrist_" + s]
        F /= np.linalg.norm(F)
        N = -sv.lm["knuckle_" + s]
        N = N - (N @ F) * F
        N /= np.linalg.norm(N)
        Tp = np.cross(N, F)
        if Tp @ sv.lm["axis_" + s] < 0:
            Tp = -Tp
        sv.open_axes[s] = (F, N, Tp)
    # wave: the open left hand turned fingers-up, palm toward the viewer (-Y), tilted out a little
    F, N, _ = sv.open_axes["L"]
    A = Matrix((_v(F), _v(N), _v(np.cross(F, N)))).transposed()
    Bm = Matrix(((0, 0, 1), (0, -1, 0), tuple(np.cross((0, 0, 1), (0, -1, 0))))).transposed()
    sv.wave_q = euler_q(0, 12, 8) @ (Bm @ A.inverted()).to_quaternion()
    wy = -KNOCK_D - sv.knock_rel[1]
    contact = np.array([KNOCK_WRIST[0], wy, KNOCK_WRIST[2]]) + sv.knock_rel
    log(f"knock contact: {KNOCK_D:.2f} m in front of the origin, height {contact[2]:.2f} m, x {contact[0]:.2f}")
    return contact
