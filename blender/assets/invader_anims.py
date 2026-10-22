"""The invader's clips (blender/assets/invader.py, stage 5).

A clip is a function t -> controls (invader_rig.rest_controls layout), built from:
  POSES     a small library of partial control dicts (arms down, guard, aim...), merged
            over the rest controls (`pose(...)`) and interpolated (`mix`) with eases;
  timeline  `seq(t, keys)` picks the two keys around t and mixes them (keys = [(time,
            controls, ease)]), so one-shots are lists of poses;
  gait      `gait(t, G)` the locomotion generator (feet planted while in contact: the
            in-place foot slides back at exactly stride / cycle), shared by Walk, Run,
            CrouchWalk, Drag and the upper-body layers of the armed variants.
Clip timings that the engine needs (fire, hit windows, the catch, the fall) are read from
the same constants (EVENTS), so they can't drift from the motion.

Directions (armature): +X the character's left, -Y its front, +Z up. Euler (x, y, z) in
degrees: +x bends forward (for a hanging limb: swings it back), +y leans toward +X, +z
turns toward +X (to the character's left).
"""
import copy
import math

import numpy as np
from mathutils import Matrix, Quaternion, Vector

import invader_rig as rig
from invader_rig import E


def mirror(e):
    """An euler for the left side -> the same motion on the right side."""
    return (e[0], -e[1], -e[2])


def ease(t, kind="io"):
    t = min(max(t, 0.0), 1.0)
    if kind == "lin":
        return t
    if kind == "in":
        return t * t
    if kind == "out":
        return 1 - (1 - t) * (1 - t)
    if kind == "snap":                    # fast out, settles
        return 1 - (1 - t) ** 3
    return t * t * (3 - 2 * t)


def _mix(a, b, t):
    if isinstance(a, dict):
        out = {}
        for k in set(a) | set(b):
            if k in a and k in b:
                out[k] = _mix(a[k], b[k], t)
            else:
                out[k] = copy.deepcopy(a.get(k, b.get(k)))
        return out
    if isinstance(a, Matrix):
        qa, qb = a.to_quaternion(), b.to_quaternion()
        return qa.slerp(qb, t).to_matrix()
    if isinstance(a, (tuple, list)):
        return tuple(_mix(x, y, t) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a + (b - a) * t
    return a if t < 0.5 else b


def mix(a, b, t):
    """Interpolate two full control dicts (matching modes: an arm in IK in one and FK in
    the other snaps at t = 0.5; avoid it)."""
    return _mix(a, b, t)


def merge(base, *over):
    out = copy.deepcopy(base)
    for o in over:
        for k, v in o.items():
            if isinstance(v, dict) and isinstance(out.get(k), dict) and not _is_mode_change(out[k], v):
                out[k] = merge(out[k], v)
            else:
                out[k] = copy.deepcopy(v)
    return out


def _is_mode_change(a, b):
    return ("target" in a) != ("target" in b) or ("ankle" in a) != ("ankle" in b)


def add(c, **deltas):
    """Add euler offsets to the spine/head controls (procedural layers)."""
    c = copy.deepcopy(c)
    for k, d in deltas.items():
        if k == "hips_pos":
            c["hips"]["pos"] = tuple(x + y for x, y in zip(c["hips"]["pos"], d))
        elif k == "hips_rot":
            c["hips"]["rot"] = tuple(x + y for x, y in zip(c["hips"]["rot"], d))
        else:
            c[k] = tuple(x + y for x, y in zip(c[k], d))
    return c


def seq(t, keys):
    """keys: [(time, controls, ease)]; the ease of a key shapes the segment arriving at it."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, a, _), (t1, b, e) in zip(keys[:-1], keys[1:]):
        if t <= t1:
            return mix(a, b, ease((t - t0) / max(t1 - t0, 1e-6), e))
    return keys[-1][1]


# ---------------------------------------------------------------- poses

class Lib:
    """Pose library, built once the solver (and so the landmarks) exist."""

    def __init__(self, sv):
        self.sv = sv
        L = sv.L
        self.L = L
        R = rig.rest_controls()
        self.rest = R
        # arms hanging by the sides (A-pose -> relaxed), elbows soft, fingers relaxed
        armL = dict(shoulder=(0, -4, 0), upper=(4, 36, -4), fore=(-14, 0, 6), hand=(0, -6, 0))
        armR = dict(shoulder=mirror(armL["shoulder"]), upper=mirror(armL["upper"]),
                    fore=mirror(armL["fore"]), hand=mirror(armL["hand"]))
        fingers = dict(Thumb=4.0, Index=10.0, Fingers=14.0)
        self.stand = merge(R, dict(arm_L=armL, arm_R=armR, fingers_L=fingers, fingers_R=dict(fingers),
                                   hips=dict(pos=(0, 0, -0.012), rot=(0, 0, 0)),
                                   leg_L=self.planted("L"), leg_R=self.planted("R")))

    def planted(self, s, dx=0.0, dy=0.0, yaw=0.0, lift=0.0, pitch=0.0):
        """A leg in IK with the foot flat on the floor at its rest place (+ offsets)."""
        A = self.L["ankle_" + s]
        return dict(ankle=(A[0] + dx, A[1] + dy, A[2] + lift), foot=(pitch, 0, yaw), toe=0.0)


# ---------------------------------------------------------------- gait

def _hermite(p0, p1, m0, m1, s):
    s2, s3 = s * s, s * s * s
    return (2 * s3 - 3 * s2 + 1) * p0 + (s3 - 2 * s2 + s) * m0 + (-2 * s3 + 3 * s2) * p1 + (s3 - s2) * m1


def foot_track(u, G):
    """Foot displacement (dy, dz) and pitch (deg, + = heel up) at phase u (0 = heel strike)."""
    S, beta, h = G["stride"], G["duty"], G["lift"]
    yf, yb = -beta * S / 2, beta * S / 2            # front (contact) .. back (toe off); front is -Y
    if u < beta:
        s = u / beta
        dy = yf + (yb - yf) * s
        dz = 0.0
        p_hs, p_to = G["heel_strike"], G["toe_off"]
        if s < 0.18:
            pitch = p_hs * (1 - rig.smoothstep(0.0, 0.18, s))
        elif s > G["heel_off"]:
            pitch = p_to * rig.smoothstep(G["heel_off"], 1.0, s) ** 1.5
        else:
            pitch = 0.0
        return dy, dz, pitch, True
    s = (u - beta) / (1 - beta)
    m = (yb - yf) / beta * (1 - beta)                # the stance's speed, in swing-phase units
    dy = _hermite(yb, yf, m * 0.35, m * 0.35, s)
    dz = h * math.sin(math.pi * min(s * 1.08, 1.0)) ** 1.2 * (1.0 - 0.5 * s)
    pitch = G["toe_off"] * (1 - rig.smoothstep(0.0, 0.45, s)) + G["heel_strike"] * rig.smoothstep(0.55, 1.0, s) - 6 * math.sin(math.pi * s)
    return dy, dz, pitch, False


def gait_legs(sv, t, G, base):
    """Leg IK controls for a gait at time t (cycle G['cycle'], left heel strike at t = 0)."""
    L = sv.L
    ph = (t / G["cycle"]) % 1.0
    c = copy.deepcopy(base)
    contacts = {}
    for s, off in (("L", 0.0), ("R", 0.5)):
        u = (ph + off) % 1.0
        dy, dz, pitch, contact = foot_track(u, G)
        dy *= G.get("dir", 1.0)
        q = E(pitch, 0, 0)
        heel = L["heel_" + s] + np.array([0, -0.0, 0.0])
        ball = L["ball_" + s] + np.array([0, 0, -0.028])
        sg = 1 if s == "L" else -1
        width = G.get("width", 0.0) * sg
        if pitch < 0:
            pv_rest = heel
        else:
            pv_rest = ball
        pv = pv_rest + np.array([width, dy, dz + G.get("foot_z", 0.0)])
        A = rig.ankle_for_pivot(sv, s, pv, pv_rest, q)
        c["leg_" + s] = dict(ankle=tuple(A), foot=(pitch, 0, 0), toe=-max(0.0, pitch) * (1.0 if contact else 0.4),
                             pole=(0, -1, -0.15 if G.get("crouch") else 0.0))
        contacts[s] = contact
    return c, ph


def gait(sv, lib, t, G, upper=None):
    """Full-body locomotion: legs from the generator, the hips bob and sway, the arms swing
    (unless `upper` gives the arms/spine, e.g. holding a rifle)."""
    c, ph = gait_legs(sv, t, G, upper if upper is not None else lib.stand)
    w = 2 * math.pi * ph
    bob = G["bob"] * (0.5 + 0.5 * math.cos(2 * w - G.get("bob_phase", 0.0)))   # lowest at contact
    c["hips"] = dict(pos=(G["sway"] * math.sin(w), G.get("hips_y", 0.0), G["hips_z"] - bob),
                     rot=(G["lean"], G["roll"] * math.sin(w), -G["yaw"] * math.cos(w)))
    c["spine"] = (G["lean_spine"], -0.5 * G["roll"] * math.sin(w), 0.5 * G["yaw"] * math.cos(w))
    c["chest"] = (G.get("lean_chest", 0.0), 0.0, 0.6 * G["yaw"] * math.cos(w))
    c["neck"] = (G.get("neck", 0.0), 0.0, -0.3 * G["yaw"] * math.cos(w))
    c["head"] = (G.get("head", 0.0) + 1.5 * math.sin(2 * w), 0.0, 0.0)
    if upper is None:
        a = G["arm_swing"]
        for s, sg in (("L", -1.0), ("R", 1.0)):
            # the right arm swings forward with the left leg (at ph 0)
            fwd = sg * math.cos(w)
            arm = copy.deepcopy(lib.stand["arm_" + s])
            ux, uy, uz = arm["upper"]
            arm["upper"] = (ux - a * fwd + G.get("arm_back", 0.0), uy + G.get("arm_in", 0.0) * (1 if s == "L" else -1), uz)
            fx, fy, fz = arm["fore"]
            arm["fore"] = (fx - G["elbow"] - G["elbow_swing"] * max(fwd, 0.0), fy, fz)
            c["arm_" + s] = arm
            if G.get("fist"):
                c["fingers_" + s] = dict(Thumb=25.0, Index=55.0, Fingers=65.0)
    return c


WALK = dict(cycle=1.12, stride=1.44, duty=0.62, lift=0.075, heel_strike=-16.0, toe_off=32.0, heel_off=0.55,
            bob=0.022, sway=0.022, hips_z=-0.022, lean=3.0, roll=3.0, yaw=6.0, lean_spine=1.0,
            arm_swing=16.0, elbow=10.0, elbow_swing=10.0, width=0.0)


# ---------------------------------------------------------------- clips

def clip_idle(sv, lib):
    T = 4.0

    def fn(t):
        w = 2 * math.pi * t / T
        c = add(lib.stand, chest=(1.2 * math.sin(2 * w), 0, 0), spine=(0, 0.6 * math.sin(w), 0),
                head=(1.5 * math.sin(w + 1), 0, 3 * math.sin(w * 0.5 + 0.3)),
                hips_pos=(0.006 * math.sin(w), 0, 0.002 * math.sin(2 * w)))
        return c
    return "Idle", fn, T, True


def clip_walk(sv, lib):
    G = dict(WALK)
    return "Walk", (lambda t: gait(sv, lib, t, G)), G["cycle"], True


CLIPS = (clip_idle, clip_walk)
STRIDES = dict(Walk=WALK)


def bake_all(sv):
    lib = Lib(sv)
    made, info = [], {}
    for mk in CLIPS:
        name, fn, T, loop = mk(sv, lib)
        act, frames = rig.key_clip(sv, name, fn, T, loop=loop)
        info[name] = dict(T=T, loop=loop, frames=frames, gap=sv.gap)
        rig.log(f"clip {name}: {T:.2f} s {'loop' if loop else 'once'}, IK gap {sv.gap * 100:.1f} cm")
        made.append(act)
    return made, info


def metadata():
    md = {}
    for k, G in STRIDES.items():
        n = k[0].lower() + k[1:]
        md[n + "Stride"] = round(G["stride"], 3)
        md[n + "Cycle"] = round(G["cycle"], 3)
        md[n + "Speed"] = round(G["stride"] / G["cycle"], 3)
    return md
