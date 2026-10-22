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
    if isinstance(a, (tuple, list)) or isinstance(b, (tuple, list)):
        if not isinstance(a, (tuple, list)):          # a finger curl given per joint in one pose only
            a = (a,) * len(b)
        if not isinstance(b, (tuple, list)):
            b = (b,) * len(a)
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
    k = G.get("swing_tan", 1.0)        # 1: leaves and lands at the stance speed (no pop at contact)
    dy = _hermite(yb, yf, m * k, m * k, s)
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


WALK = dict(cycle=34 / 30, stride=1.42, duty=0.62, lift=0.075, heel_strike=-14.0, toe_off=30.0, heel_off=0.55,
            bob=0.02, sway=0.022, hips_z=-0.05, lean=3.0, roll=3.0, yaw=6.0, lean_spine=1.0,
            arm_swing=16.0, elbow=10.0, elbow_swing=10.0, width=0.0)
RUN = dict(cycle=22 / 30, stride=3.3, duty=0.3, lift=0.24, swing_tan=0.85, heel_strike=-10.0, toe_off=38.0, heel_off=0.35,
           bob=0.04, bob_phase=0.6, sway=0.012, hips_z=-0.16, lean=9.0, roll=2.0, yaw=9.0, lean_spine=4.0,
           lean_chest=2.0, head=-8.0, arm_swing=40.0, arm_back=0.0, arm_in=-8.0, elbow=70.0, elbow_swing=20.0,
           fist=True, width=-0.01)
CROUCH_WALK = dict(cycle=1.4, stride=1.1, duty=0.68, lift=0.09, heel_strike=-10.0, toe_off=26.0, heel_off=0.5,
                   bob=0.015, sway=0.03, hips_z=-0.31, hips_y=0.06, lean=22.0, roll=2.0, yaw=5.0, lean_spine=10.0,
                   lean_chest=4.0, neck=-14.0, head=-12.0, arm_swing=10.0, arm_back=-20.0, elbow=35.0,
                   elbow_swing=8.0, width=0.03, crouch=True)
DRAG = dict(cycle=1.6, stride=0.8, duty=0.7, lift=0.06, heel_strike=6.0, toe_off=10.0, heel_off=0.6,
            bob=0.012, sway=0.02, hips_z=-0.16, hips_y=0.08, lean=24.0, roll=2.0, yaw=3.0, lean_spine=14.0,
            lean_chest=6.0, neck=-16.0, head=-10.0, width=0.04, dir=-1.0, crouch=True)

# times the engine acts on (s into the clip); the clips below are built from these
EV = dict(
    OpenDoor=dict(grab=0.42, push=0.78, T=1.6),
    Vault=dict(plant=0.36, clear=0.76, land=0.98, T=1.5, distance=1.6, height=0.75),
    Shout=dict(sound=0.3, T=1.5),
    Signal=dict(point=0.55, T=1.7),
    ShootRifle=dict(fire=0.0, T=0.2),
    ShootPistol=dict(fire=0.0, T=0.36),
    ReloadRifle=dict(magOut=0.55, magIn=1.45, done=2.2, T=2.4),
    ReloadPistol=dict(magOut=0.35, magIn=0.95, done=1.4, T=1.6),
    MeleeBat=dict(hit=(0.42, 0.56), T=1.25),
    MeleeKnife=dict(hit=(0.3, 0.42), T=0.95),
    HitFront=dict(T=0.65), HitBack=dict(T=0.65), Stagger=dict(T=1.5, distance=-0.55),
    DeathForward=dict(fall=0.95, T=2.0), DeathBack=dict(fall=0.9, T=2.0),
    Grab=dict(catch=0.46, T=1.1),
)


# ---------------------------------------------------------------- weapon holds

def wframe(origin, fwd, up):
    """A weapon's frame (armature space): -Y = fwd, +Z = up, at origin (its grip)."""
    f = np.asarray(fwd, float)
    f /= np.linalg.norm(f)
    u = np.asarray(up, float)
    u = u - (u @ f) * f
    u /= np.linalg.norm(u)
    y, z = -f, u
    x = np.cross(y, z)
    M = Matrix.Identity(4)
    for r in range(3):
        M[r][0], M[r][1], M[r][2], M[r][3] = x[r], y[r], z[r], origin[r]
    return M


def grip_frame(pos, up, fwd):
    """A hand's grip frame in weapon coordinates (like a socket: -Y fist forward, +Z up)."""
    return wframe(pos, fwd, up)


def held(sv, side, W, G=None, pole=None, space="arm"):
    """Arm IK controls placing a hand so its socket coincides with W (@ G)."""
    bone, S = sv.sockets["Socket_Hand_" + side]
    M = W @ (G if G is not None else Matrix.Identity(4)) @ S.inverted()
    sg = 1 if side == "L" else -1
    return dict(target=tuple(M.translation), rot=M.to_3x3(), space=space,
                pole=tuple(pole) if pole is not None else (0.6 * sg, 0.3, -1.0))


# left-hand grips in weapon coordinates
G_FORE = grip_frame((0.0, -0.29, 0.045), up=(0, -1, 0.0), fwd=(-1.0, 0.0, 0.55))          # under the handguard
G_MAG = grip_frame((0.0, -0.075, -0.05), up=(0, -0.3, -1), fwd=(-1.0, 0.0, 0.0))          # on the magazine
G_CUP = grip_frame((0.012, 0.0, -0.035), up=(0, -0.25, 1.0), fwd=(-0.7, -0.7, -0.2))      # support hand on a pistol
G_BAT = Matrix.Translation((0, 0, -0.075)) @ Matrix.Rotation(math.pi, 4, "Z")              # bottom hand on the bat

GRIP_R = dict(rifle=dict(Thumb=(30.0, 20.0), Index=(18.0, 30.0), Fingers=(72.0, 80.0)),
              pistol=dict(Thumb=(25.0, 15.0), Index=(14.0, 30.0), Fingers=(74.0, 82.0)),
              bat=dict(Thumb=(40.0, 35.0), Index=(70.0, 80.0), Fingers=(78.0, 85.0)),
              knife=dict(Thumb=(40.0, 35.0), Index=(72.0, 80.0), Fingers=(80.0, 88.0)))
GRIP_L = dict(fore=dict(Thumb=(25.0, 15.0), Index=(55.0, 60.0), Fingers=(62.0, 66.0)),
              cup=dict(Thumb=(15.0, 10.0), Index=(55.0, 55.0), Fingers=(60.0, 65.0)),
              bat=dict(Thumb=(40.0, 35.0), Index=(72.0, 80.0), Fingers=(78.0, 85.0)),
              fist=dict(Thumb=(35.0, 25.0), Index=(70.0, 80.0), Fingers=(78.0, 88.0)),
              open=dict(Thumb=4.0, Index=6.0, Fingers=8.0))


class Lib:
    """Pose library, built once the solver (and so the landmarks) exist."""

    def __init__(self, sv):
        self.sv = sv
        L = sv.L
        self.L = L
        R = rig.rest_controls()
        self.rest = R
        armL = dict(shoulder=(0, -4, 0), upper=(4, 36, -4), fore=(-14, 0, 6), hand=(0, -6, 0))
        armR = dict(shoulder=mirror(armL["shoulder"]), upper=mirror(armL["upper"]),
                    fore=mirror(armL["fore"]), hand=mirror(armL["hand"]))
        fingers = dict(Thumb=4.0, Index=10.0, Fingers=14.0)
        self.arm_down = dict(L=armL, R=armR)
        self.stand = merge(R, dict(arm_L=armL, arm_R=armR, fingers_L=fingers, fingers_R=dict(fingers),
                                   hips=dict(pos=(0, 0, -0.012), rot=(0, 0, 0)),
                                   leg_L=self.planted("L"), leg_R=self.planted("R")))
        # a ready stance: feet apart, left foot ahead, knees soft
        self.ready_legs = dict(leg_L=self.planted("L", dx=0.04, dy=-0.12, yaw=8), leg_R=self.planted("R", dx=-0.04, dy=0.1, yaw=-20))
        self.ready = merge(self.stand, self.ready_legs, dict(hips=dict(pos=(0, 0.0, -0.05), rot=(4, 0, -10)),
                                                             spine=(3, 0, 4), chest=(2, 0, 4), neck=(-2, 0, 2)))
        # rifle frames (armature space; the stance turns the hips, the rifle points along -Y)
        self.W_aim_rifle = wframe((-0.105, -0.27, 1.36), (0.035, -1, 0.0), (0, 0, 1))
        self.W_low_rifle = wframe((-0.17, -0.15, 1.13), (0.5, -1, -0.6), (0.05, -0.3, 1))
        self.W_aim_pistol = wframe((-0.035, -0.47, 1.5), (0.0, -1, 0.02), (0, 0, 1))
        self.W_low_pistol = wframe((-0.07, -0.3, 1.08), (0.15, -1, -0.8), (0, -0.4, 1))

    def planted(self, s, dx=0.0, dy=0.0, yaw=0.0, lift=0.0, pitch=0.0, pole=None):
        """A leg in IK with the foot flat on the floor at its rest place (+ offsets)."""
        A = self.L["ankle_" + s]
        d = dict(ankle=(A[0] + dx, A[1] + dy, A[2] + lift), foot=(pitch, 0, yaw), toe=0.0)
        if pitch > 0:          # heel up: the ball stays on the floor, the toes flat
            ball = self.L["ball_" + s] - np.array([0, 0, 0.028])
            an = rig.ankle_for_pivot(self.sv, s, ball + np.array([dx, dy, lift]), ball, E(pitch, 0, yaw))
            d = dict(ankle=tuple(an), foot=(pitch, 0, yaw), toe=-pitch)
        if pole is not None:
            d["pole"] = pole
        return d

    # -- armed upper bodies (merged over a stance)
    def rifle(self, W, space="arm", lpole=None, rpole=None, left="fore"):
        sv = self.sv
        d = dict(arm_R=held(sv, "R", W, pole=rpole or (-0.5, 0.4, -1.0), space=space),
                 fingers_R=GRIP_R["rifle"])
        if left == "fore":
            d["arm_L"] = held(sv, "L", W, G_FORE, pole=lpole or (0.8, 0.2, -1.0), space=space)
            d["fingers_L"] = GRIP_L["fore"]
        return d

    def pistol(self, W, space="arm", two=True):
        sv = self.sv
        d = dict(arm_R=held(sv, "R", W, pole=(-0.5, 0.2, -1.0), space=space), fingers_R=GRIP_R["pistol"])
        if two:
            d["arm_L"] = held(sv, "L", W, G_CUP, pole=(0.6, 0.2, -1.0), space=space)
            d["fingers_L"] = GRIP_L["cup"]
        return d


def breathe(c, t, T, amp=1.0):
    w = 2 * math.pi * t / T
    return add(c, chest=(amp * 1.2 * math.sin(2 * w), 0, 0), head=(amp * 0.8 * math.sin(2 * w + 0.6), 0, 0),
               hips_pos=(0.004 * amp * math.sin(w), 0, 0.002 * amp * math.sin(2 * w)))


def hand_toward(sv, side, pos, palm, fingers, space="arm", pole=None):
    """IK controls for a hand at `pos` with the palm facing `palm` and fingers along `fingers`."""
    f = np.asarray(fingers, float)
    f /= np.linalg.norm(f)
    pn = np.asarray(palm, float)
    pn = pn - (pn @ f) * f
    pn /= np.linalg.norm(pn)
    back = -pn
    # hand bone frame: Y along the fingers, Z the back of the hand (see invader_rig.skeleton)
    z = back
    y = f
    x = np.cross(y, z)
    M = Matrix(((x[0], y[0], z[0]), (x[1], y[1], z[1]), (x[2], y[2], z[2])))
    sg = 1 if side == "L" else -1
    return dict(target=tuple(pos), rot=M, space=space, pole=tuple(pole) if pole is not None else (0.5 * sg, 0.6, -1.0))


# ---------------------------------------------------------------- clips

def clip_idle(sv, lib):
    T = 4.0

    def fn(t):
        w = 2 * math.pi * t / T
        c = breathe(lib.stand, t, T)
        return add(c, spine=(0, 0.6 * math.sin(w), 0), head=(0, 0, 3 * math.sin(w + 0.3)))
    return "Idle", fn, T, True


def clip_idle_alert(sv, lib):
    T = 5.0
    base = merge(lib.ready, dict(arm_L=dict(shoulder=(0, -2, 0), upper=(-12, 30, -6), fore=(-45, 0, 10), hand=(0, -6, 0)),
                                 arm_R=dict(shoulder=(0, 2, 0), upper=(-12, -30, 6), fore=(-45, 0, -10), hand=(0, 6, 0)),
                                 fingers_L=dict(Thumb=15.0, Index=30.0, Fingers=40.0),
                                 fingers_R=dict(Thumb=15.0, Index=30.0, Fingers=40.0)))
    keys = [(0.0, 0.0), (0.7, 35.0), (1.6, 35.0), (2.3, -10.0), (2.9, -40.0), (3.9, -40.0), (4.5, 0.0), (5.0, 0.0)]

    def fn(t):
        yaw = 0.0
        for (t0, a), (t1, b) in zip(keys[:-1], keys[1:]):
            if t0 <= t <= t1:
                yaw = a + (b - a) * ease((t - t0) / (t1 - t0))
                break
        c = breathe(base, t, T, 1.4)
        return add(c, chest=(0, 0, 0.3 * yaw), neck=(0, 0, 0.3 * yaw), head=(2.0 * math.sin(t * 2.1), 0, 0.4 * yaw))
    return "IdleAlert", fn, T, True


def clip_walk(sv, lib):
    G = dict(WALK)
    return "Walk", (lambda t: gait(sv, lib, t, G)), G["cycle"], True


def clip_run(sv, lib):
    G = dict(RUN)
    return "Run", (lambda t: gait(sv, lib, t, G)), G["cycle"], True


def _crouch_pose(lib):
    L = lib.L
    return merge(lib.stand, dict(
        hips=dict(pos=(0.0, 0.07, -0.36), rot=(26, 0, -6)), spine=(10, 0, 2), chest=(4, 0, 2), neck=(-16, 0, 1),
        head=(-14, 0, 0),
        leg_L=lib.planted("L", dx=0.03, dy=-0.16, yaw=6), leg_R=lib.planted("R", dx=-0.05, dy=0.12, yaw=-14, pitch=30),
        arm_L=dict(shoulder=(0, -2, 0), upper=(-38, 24, -8), fore=(-42, 0, 10), hand=(0, -8, 0)),
        arm_R=dict(shoulder=(0, 2, 0), upper=(-30, -24, 8), fore=(-48, 0, -10), hand=(0, 8, 0)),
        fingers_L=dict(Thumb=12.0, Index=25.0, Fingers=35.0), fingers_R=dict(Thumb=12.0, Index=25.0, Fingers=35.0)))


def clip_crouch(sv, lib):
    T = 4.0
    base = _crouch_pose(lib)

    def fn(t):
        c = breathe(base, t, T, 1.2)
        return add(c, head=(0, 0, 8 * math.sin(2 * math.pi * t / T)))
    return "CrouchIdle", fn, T, True


def clip_crouch_walk(sv, lib):
    G = dict(CROUCH_WALK)
    up = _crouch_pose(lib)
    return "CrouchWalk", (lambda t: gait(sv, lib, t, G)), G["cycle"], True


def clip_search(sv, lib):
    """Sweep the room left to right, then turn and check behind over the right shoulder."""
    T = 6.0
    base = merge(lib.ready, dict(arm_L=dict(shoulder=(0, -2, 0), upper=(-10, 30, -6), fore=(-40, 0, 10)),
                                 arm_R=dict(shoulder=(0, 2, 0), upper=(-10, -30, 6), fore=(-40, 0, -10))))
    behind = merge(base, dict(leg_R=lib.planted("R", dx=-0.02, dy=0.14, yaw=-45),
                              hips=dict(pos=(0.0, 0.02, -0.06), rot=(2, 0, -35))))
    # (time, yaw of chest+head, lean, pose)
    K = [(0.0, 0, 0, base), (1.0, 40, 0, base), (2.0, 40, 6, base), (3.0, -30, 0, base),
         (3.7, -30, 0, base), (4.4, -60, -4, behind), (5.2, -60, -4, behind), (6.0, 0, 0, base)]

    def fn(t):
        for (t0, y0, l0, p0), (t1, y1, l1, p1) in zip(K[:-1], K[1:]):
            if t0 <= t <= t1:
                e = ease((t - t0) / (t1 - t0))
                c = mix(p0, p1, e)
                yaw = y0 + (y1 - y0) * e
                lean = l0 + (l1 - l0) * e
                break
        c = breathe(c, t, T, 1.3)
        return add(c, spine=(lean, 0, 0.25 * yaw), chest=(0, 0, 0.3 * yaw), neck=(0, 0, 0.2 * yaw),
                   head=(3 * math.sin(t * 1.7), 0, 0.35 * yaw))
    return "Search", fn, T, True


def clip_open_door(sv, lib):
    """Reach for a lever handle ~1.0 m high, 0.55 m ahead, press it, push the door."""
    ev = EV["OpenDoor"]
    T = ev["T"]
    st = lib.stand
    reach = merge(st, dict(arm_R=hand_toward(sv, "R", (-0.19, -0.4, 1.0), palm=(0.0, 0.0, -1.0), fingers=(0.2, -1, 0)),
                           spine=(10, 0, -6), chest=(5, 0, -4), head=(10, 0, -4),
                           hips=dict(pos=(0, -0.06, -0.03), rot=(2, 0, -6)),
                           fingers_R=dict(Thumb=10.0, Index=10.0, Fingers=12.0)))
    grab = merge(reach, dict(arm_R=hand_toward(sv, "R", (-0.19, -0.42, 0.98), palm=(0.0, 0.0, -1.0), fingers=(0.15, -1, -0.15)),
                             fingers_R=dict(Thumb=45.0, Index=70.0, Fingers=75.0)))
    press = merge(grab, dict(arm_R=hand_toward(sv, "R", (-0.19, -0.42, 0.94), palm=(0.0, 0.3, -1.0), fingers=(0.15, -1, -0.5))))
    push = merge(press, dict(arm_R=hand_toward(sv, "R", (-0.18, -0.62, 0.96), palm=(0.0, 0.3, -1.0), fingers=(0.15, -1, -0.4)),
                             spine=(10, 0, -6), chest=(6, 0, -4), hips=dict(pos=(0, -0.2, -0.05), rot=(4, 0, -6)),
                             leg_L=lib.planted("L", dy=-0.22, lift=0.0), leg_R=lib.planted("R", dy=0.05)))
    # the arm starts from FK (hanging): solve the hanging hand's world pose for a smooth reach
    keys = [(0.0, st, "io"), (0.3, reach, "io"), (ev["grab"], grab, "io"), (0.6, press, "io"),
            (ev["push"] + 0.25, push, "io"), (1.25, push, "io"), (T, st, "io")]
    hang = _fk_to_ik(sv, st, "R")
    keys[0] = (0.0, hang, "io")
    keys[-1] = (T, hang, "io")
    return "OpenDoor", (lambda t: seq(t, keys)), T, False


def _fk_to_ik(sv, c, side):
    """The same pose with one arm converted to IK (its solved hand pose), so it can blend
    with IK poses."""
    PM = sv.solve(c)
    H = PM["Hand_" + side]
    d = copy.deepcopy(c)
    sg = 1 if side == "L" else -1
    d["arm_" + side] = dict(shoulder=c["arm_" + side].get("shoulder", (0, 0, 0)), target=tuple(H.translation),
                            rot=H.to_3x3(), space="arm", pole=(0.3 * sg, 1.0, -0.2))
    return d


def clip_vault(sv, lib):
    """Over a low obstacle (EV height, its front edge 0.45 m ahead, 0.4 m deep): plant the
    left hand, swing the legs over to the right, land. Authored in world space while the
    root moves forward along ROOT_CURVE; the clip is that minus the root (in place)."""
    ev = EV["Vault"]
    T, D, Hh = ev["T"], ev["distance"], ev["height"]
    L = lib.L

    def root(t):                       # forward distance travelled by time t (s): slower over the top
        s = t / T
        return D * (0.5 - 0.5 * math.cos(math.pi * s)) * 0.85 + D * 0.15 * s

    edge = -0.45                      # obstacle front edge (world y; forward is -Y)
    top = edge - 0.25
    st = lib.stand
    # world-space key poses: hips offset, legs, arms
    def P(hx, hy, hz, rot, lL, lR, aL, aR, sp=(0, 0, 0), ch=(0, 0, 0), hd=(0, 0, 0)):
        return dict(h=(hx, hy, hz), rot=rot, lL=lL, lR=lR, aL=aL, aR=aR, sp=sp, ch=ch, hd=hd)
    A = {s: L["ankle_" + s] for s in "LR"}

    def foot(s, x, y, z, pitch=0.0, yaw=0.0):
        return dict(ankle=(A[s][0] + x, y, A[s][2] + z), foot=(pitch, 0, yaw), toe=0.0)
    # keys: hips offset (world), hips rot, feet (world ankle offsets / heights), arm kinds, spine / chest / head
    K = [
        (0.0, P(0, 0, -0.02, (2, 0, 0), foot("L", 0, A["L"][1], 0), foot("R", 0, A["R"][1], 0), "hang", "hang")),
        (0.2, P(0, -0.22, -0.08, (14, 0, 0), foot("L", 0, -0.2, 0, -10), foot("R", 0, 0.05, 0.06, 30), "reach", "back",
                sp=(10, 0, 0))),
        (ev["plant"], P(0.02, -0.34, 0.0, (30, 0, 10), foot("L", 0, -0.3, 0.02, 20), foot("R", 0, -0.12, 0.2, 20),
                        "plant", "up", sp=(22, 8, 0), ch=(8, 6, 0))),
        (0.55, P(-0.06, -0.52, 0.14, (34, -6, 25), foot("L", -0.12, -0.5, Hh + 0.05, 10), foot("R", -0.2, -0.6, Hh + 0.1, 0),
                 "plant", "up", sp=(24, 16, 10), ch=(10, 10, 6))),
        (0.64, P(-0.1, -0.78, 0.18, (16, -4, 22), foot("L", -0.2, -0.78, Hh + 0.02, 0), foot("R", -0.26, -0.9, Hh + 0.06, -6),
                 "lift", "up", sp=(10, 12, 8), ch=(3, 8, 5))),
        (ev["clear"], P(-0.1, -0.95, 0.1, (10, 0, 18), foot("L", -0.2, -1.02, Hh * 0.6, -10), foot("R", -0.25, -1.1, Hh * 0.7, -10),
                        "lift", "up", sp=(6, 8, 6), ch=(2, 5, 4))),
        (ev["land"], P(-0.05, -1.3, -0.12, (10, 0, 8), foot("L", -0.05, -1.25, 0.08, 10), foot("R", -0.06, -1.42, 0, -6),
                       "free", "free", sp=(10, 2, 2))),
        (1.2, P(0, -1.52, -0.06, (6, 0, 0), foot("L", 0, -1.45, 0, 0), foot("R", 0, -1.62, 0, 0), "free", "free", sp=(4, 0, 0))),
        (T, P(0, -D, -0.012, (0, 0, 0), foot("L", 0, A["L"][1] - D, 0), foot("R", 0, A["R"][1] - D, 0), "hang", "hang")),
    ]
    hang = {s: _fk_to_ik(sv, lib.stand, s)["arm_" + s] for s in "LR"}

    def arm(side, kind, t, hw, r):
        """IK arm for a kind; hw = the hips' world position, r = the root's travel (in place: + r)."""
        sg = 1 if side == "L" else -1
        if kind == "hang":
            return copy.deepcopy(hang[side])
        if kind == "plant":                   # the left hand on the obstacle top (world)
            pos = np.array([0.06, top, Hh + 0.035])
            return hand_toward(sv, side, (pos[0], pos[1] + r, pos[2]), palm=(0, 0, -1), fingers=(0.4 * sg, -1, 0),
                               pole=(0.8 * sg, 1.0, 0.0))
        off = dict(reach=(0.16, -0.42, 0.3), back=(-0.28, 0.15, 0.25), up=(-0.34, -0.22, 0.42), lift=(0.28, -0.25, 0.4),
                   free=(0.3, -0.22, 0.3))[kind]
        pos = hw + np.array([off[0] * (sg if kind in ("free",) else 1), off[1], off[2]])
        return hand_toward(sv, side, (pos[0], pos[1] + r, pos[2]), palm=(-sg * 0.3, 0, -1), fingers=(0.3 * sg, -1, 0.2),
                           pole=(0.8 * sg, 0.8, -0.3))

    def fn(t):
        for (t0, a), (t1, b) in zip(K[:-1], K[1:]):
            if t0 <= t <= t1:
                e = ease((t - t0) / (t1 - t0))
                break
        else:
            a = b = K[-1][1]
            e = 0.0
        r = root(t)
        c = copy.deepcopy(lib.stand)
        h = tuple(x + (y - x) * e for x, y in zip(a["h"], b["h"]))
        c["hips"] = dict(pos=(h[0], h[1] + r, h[2]), rot=tuple(x + (y - x) * e for x, y in zip(a["rot"], b["rot"])))
        for k, kk in (("spine", "sp"), ("chest", "ch"), ("head", "hd")):
            c[k] = tuple(x + (y - x) * e for x, y in zip(a[kk], b[kk]))
        for s, kk in (("L", "lL"), ("R", "lR")):
            fa, fb = a[kk], b[kk]
            an = tuple(x + (y - x) * e for x, y in zip(fa["ankle"], fb["ankle"]))
            c["leg_" + s] = dict(ankle=(an[0], an[1] + r, an[2]), foot=tuple(x + (y - x) * e for x, y in zip(fa["foot"], fb["foot"])),
                                 toe=0.0, pole=(0.2 if s == "L" else -0.2, -1.0, 0.0))
        for s, kk in (("L", "aL"), ("R", "aR")):
            ka, kb = a[kk], b[kk]
            hw = L["hips"] + np.array(h)
            c["arm_" + s] = mix(arm(s, ka, t, hw, r), arm(s, kb, t, hw, r), e)
        c["fingers_L"] = dict(Thumb=10.0, Index=15.0, Fingers=20.0)
        return c
    vault_root_curve[:] = [(round(i * T / 15, 3), round(root(i * T / 15), 3)) for i in range(16)]
    return "Vault", fn, T, False


vault_root_curve = []


def clip_shout(sv, lib):
    ev = EV["Shout"]
    T = ev["T"]
    st = lib.stand
    yell = merge(lib.ready, dict(spine=(-4, 0, 0), chest=(-8, 0, 0), neck=(10, 0, 0), head=(-14, 0, 0),
                                 hips=dict(pos=(0, 0.02, -0.04), rot=(-2, 0, -6)),
                                 arm_L=dict(shoulder=(0, 0, 10), upper=(-30, 10, -10), fore=(-60, 0, 20), hand=(0, 0, 0)),
                                 arm_R=dict(shoulder=(0, 0, -10), upper=(-30, -10, 10), fore=(-60, 0, -20), hand=(0, 0, 0)),
                                 fingers_L=GRIP_L["fist"], fingers_R=GRIP_L["fist"]))
    keys = [(0.0, st, "io"), (0.22, yell, "out"), (ev["sound"] + 0.05, add(yell, chest=(-3, 0, 0), head=(-6, 0, 0)), "io"),
            (0.9, yell, "io"), (T, st, "io")]
    return "Shout", (lambda t: seq(t, keys)), T, False


def clip_signal(sv, lib):
    """Point forward with the left arm, then wave 'over here' twice."""
    ev = EV["Signal"]
    T = ev["T"]
    st = lib.stand
    point = merge(st, dict(arm_L=dict(shoulder=(0, 0, 6), upper=(-80, -30, 10), fore=(-5, 0, 0), hand=(0, 0, 0)),
                           fingers_L=dict(Thumb=30.0, Index=0.0, Fingers=85.0), chest=(0, 0, 8), head=(0, 0, -6)))
    wave_a = merge(st, dict(arm_L=dict(shoulder=(0, 0, 12), upper=(-100, -20, 30), fore=(-70, 0, 20), hand=(0, 0, 0)),
                            fingers_L=GRIP_L["open"], chest=(0, 0, 10), head=(0, 0, 18)))
    wave_b = merge(wave_a, dict(arm_L=dict(shoulder=(0, 0, 12), upper=(-100, -20, 30), fore=(-105, 0, 20), hand=(0, 0, 0))))
    keys = [(0.0, st, "io"), (0.35, point, "out"), (ev["point"] + 0.15, point, "io"), (0.95, wave_a, "io"),
            (1.12, wave_b, "io"), (1.3, wave_a, "io"), (1.45, wave_b, "io"), (T, st, "io")]
    return "Signal", (lambda t: seq(t, keys)), T, False


def _armed(lib, W, kind, stance=None, space="arm", **kw):
    base = stance if stance is not None else lib.ready
    if kind == "rifle":
        return merge(base, lib.rifle(W, space=space, **kw))
    return merge(base, lib.pistol(W, space=space, **kw))


AIM_RIFLE_SPINE = dict(spine=(6, 0, 10), chest=(4, -2, 8), neck=(8, -4, 2), head=(10, -10, -6))
AIM_PISTOL_SPINE = dict(spine=(4, 0, 6), chest=(2, 0, 4), neck=(4, 0, 0), head=(4, -4, -2))
HOLD_SPINE = dict(spine=(3, 0, -6), chest=(2, 0, -6), neck=(-2, 0, 6), head=(0, 0, 4))


def clip_hold_rifle(sv, lib):
    T = 3.0
    base = _armed(lib, lib.W_low_rifle, "rifle", stance=merge(lib.ready, HOLD_SPINE))

    def fn(t):
        return breathe(base, t, T, 1.0)
    return "HoldRifle", fn, T, True


def clip_hold_pistol(sv, lib):
    T = 3.0
    base = _armed(lib, lib.W_low_pistol, "pistol", stance=merge(lib.ready, HOLD_SPINE))
    return "HoldPistol", (lambda t: breathe(base, t, T, 1.0)), T, True


def _aim(lib, kind, dW=None, extra=None):
    W = lib.W_aim_rifle if kind == "rifle" else lib.W_aim_pistol
    if dW is not None:
        W = dW @ W if False else _apply(W, dW)
    st = merge(lib.ready, AIM_RIFLE_SPINE if kind == "rifle" else AIM_PISTOL_SPINE, extra or {})
    return _armed(lib, W, kind, stance=st)


def _apply(W, d):
    """Recoil: d = (back m, rise deg) applied in the weapon's frame, about the butt / grip."""
    back, rise = d
    M = W.copy()
    fwd = -Vector(M.col[1][:3])
    rot = Matrix.Rotation(math.radians(rise), 4, Vector(M.col[0][:3]))
    p = M.translation.copy()
    R = rot @ M
    R.translation = p - fwd * back
    return R


def clip_aim_rifle(sv, lib):
    T = 3.0

    def fn(t):
        w = 2 * math.pi * t / T
        c = _aim(lib, "rifle", (0.0, 0.25 * math.sin(w * 2)))
        return add(c, chest=(0.4 * math.sin(2 * w), 0, 0))
    return "AimRifle", fn, T, True


def clip_aim_pistol(sv, lib):
    T = 3.0

    def fn(t):
        w = 2 * math.pi * t / T
        return _aim(lib, "pistol", (0.0, 0.3 * math.sin(w * 2)))
    return "AimPistol", fn, T, True


def clip_shoot(kind):
    def mk(sv, lib):
        name = "ShootRifle" if kind == "rifle" else "ShootPistol"
        T = EV[name]["T"]
        kick, rise = (0.035, 3.5) if kind == "rifle" else (0.03, 11.0)

        def fn(t):
            s = t / T
            k = (1 - math.exp(-s * 25)) * math.exp(-s * 6) * 1.3 if s > 0 else 0.0
            k = min(k, 1.0)
            c = _aim(lib, kind, (kick * k, rise * k))
            return add(c, chest=(-1.5 * k, 0, 0), head=(-1.0 * k, 0, 0))
        return name, fn, T, False
    return mk


def clip_reload_rifle(sv, lib):
    ev = EV["ReloadRifle"]
    T = ev["T"]
    st = merge(lib.ready, HOLD_SPINE)
    W0 = wframe((-0.12, -0.3, 1.18), (0.3, -1, -0.35), (0.25, 0.0, 1))   # tilted, magazine well toward the left hand
    hold = _armed(lib, W0, "rifle", stance=st)
    on_mag = merge(hold, dict(arm_L=held(sv, "L", W0, G_MAG, pole=(0.8, 0.2, -1.0)), fingers_L=GRIP_L["fist"]))
    W_dn = wframe((-0.12, -0.3, 1.18), (0.3, -1, -0.35), (0.25, 0.0, 1))
    pouch = merge(hold, dict(arm_L=hand_toward(sv, "L", (0.16, -0.12, 1.0), palm=(-1, 0, 0), fingers=(0, -0.2, -1)),
                             fingers_L=GRIP_L["fist"], chest=(6, 0, 12)))
    insert = merge(on_mag, dict(chest=(4, 0, 8)))
    slap = merge(on_mag, dict(arm_L=held(sv, "L", W0, Matrix.Translation((0, 0, -0.05)) @ G_MAG, pole=(0.8, 0.2, -1.0)),
                              fingers_L=GRIP_L["open"]))
    charge = merge(hold, dict(arm_L=hand_toward(sv, "L", tuple(W0 @ Vector((0.03, 0.09, 0.11))), palm=(-1, 0, 0), fingers=(0, -1, 0.3)),
                              fingers_L=dict(Thumb=40.0, Index=65.0, Fingers=70.0)))
    charged = merge(charge, dict(arm_L=hand_toward(sv, "L", tuple(W0 @ Vector((0.03, 0.17, 0.11))), palm=(-1, 0, 0), fingers=(0, -1, 0.3))))
    back = _armed(lib, lib.W_low_rifle, "rifle", stance=st)
    # the left arm: from the foregrip (IK) through the free hand poses (IK as well)
    keys = [(0.0, back, "io"), (0.3, hold, "io"), (ev["magOut"], on_mag, "io"), (0.85, pouch, "io"), (1.15, pouch, "io"),
            (ev["magIn"], insert, "io"), (1.62, slap, "snap"), (1.85, charge, "io"), (2.0, charged, "snap"),
            (T, back, "io")]
    return "ReloadRifle", (lambda t: seq(t, keys)), T, False


def clip_reload_pistol(sv, lib):
    ev = EV["ReloadPistol"]
    T = ev["T"]
    st = merge(lib.ready, HOLD_SPINE)
    W0 = wframe((-0.06, -0.3, 1.2), (0.25, -1, 0.1), (-0.5, 0, 1))
    hold = _armed(lib, W0, "pistol", stance=st, two=False)
    hold = merge(hold, dict(arm_L=hand_toward(sv, "L", (0.0, -0.3, 1.1), palm=(-1, 0, 0.3), fingers=(-0.3, -1, 0))))
    pouch = merge(hold, dict(arm_L=hand_toward(sv, "L", (0.16, -0.08, 0.98), palm=(-1, 0, 0), fingers=(0, -0.2, -1)),
                             fingers_L=GRIP_L["fist"]))
    insert = merge(hold, dict(arm_L=hand_toward(sv, "L", tuple(W0 @ Vector((0.0, 0.01, -0.07))), palm=(0, 0, 1), fingers=(-0.6, -0.6, 0)),
                              fingers_L=GRIP_L["fist"]))
    back = _armed(lib, lib.W_low_pistol, "pistol", stance=st)
    keys = [(0.0, back, "io"), (0.25, hold, "io"), (ev["magOut"] + 0.15, pouch, "io"), (0.7, pouch, "io"),
            (ev["magIn"], insert, "io"), (1.15, insert, "io"), (T, back, "io")]
    return "ReloadPistol", (lambda t: seq(t, keys)), T, False


def _bat_pose(lib, grip, axis, spine, hips_yaw, legs=None, lean=0.0):
    sv = lib.sv
    up = np.asarray(axis, float)
    fwd = np.cross(up, (0, 0, 1)) if abs(up[2]) < 0.95 else np.array([0, -1.0, 0])
    W = wframe(grip, fwd, up)
    c = merge(lib.ready, legs or {}, dict(hips=dict(pos=(0, 0.0, -0.06), rot=(4 + lean, 0, hips_yaw)),
                                          spine=spine, chest=(2, 0, spine[2] * 0.8)))
    c = merge(c, dict(arm_R=held(sv, "R", W, pole=(-0.8, 0.5, -0.6)), fingers_R=GRIP_R["bat"],
                      arm_L=held(sv, "L", W, G_BAT, pole=(0.8, 0.3, -0.8)), fingers_L=GRIP_L["bat"]))
    return c


def clip_melee_bat(sv, lib):
    ev = EV["MeleeBat"]
    T = ev["T"]
    h0, h1 = ev["hit"]
    ready = _bat_pose(lib, (-0.14, -0.2, 1.25), (-0.1, 0.35, 1.0), (3, 0, 4), -6)
    wind = _bat_pose(lib, (-0.24, 0.0, 1.42), (0.15, 0.85, 0.5), (0, -4, -28), -24)
    contact = _bat_pose(lib, (-0.02, -0.36, 1.12), (0.3, -0.95, 0.05), (8, 0, 8), 10,
                        legs=dict(leg_L=lib.planted("L", dx=0.06, dy=-0.25, yaw=20)), lean=6)
    follow = _bat_pose(lib, (0.22, -0.2, 1.18), (0.9, 0.35, 0.25), (6, 4, 42), 34,
                       legs=dict(leg_L=lib.planted("L", dx=0.06, dy=-0.25, yaw=30)), lean=4)
    keys = [(0.0, ready, "io"), (0.3, wind, "io"), (h0, contact, "in"), (h1 + 0.08, follow, "out"),
            (0.85, follow, "io"), (T, ready, "io")]
    return "MeleeBat", (lambda t: seq(t, keys)), T, False


def clip_melee_knife(sv, lib):
    ev = EV["MeleeKnife"]
    T = ev["T"]
    h0, h1 = ev["hit"]
    knife_fingers = GRIP_R["knife"]
    guard_L = dict(shoulder=(0, -2, 0), upper=(-30, 20, -10), fore=(-75, 0, 15), hand=(0, 0, 0))
    base = merge(lib.ready, dict(fingers_R=knife_fingers, arm_L=guard_L, fingers_L=GRIP_L["fist"]))
    W_ready = wframe((-0.16, -0.3, 1.1), (0, 0, -1), (0.1, -1.0, 0.25))
    W_back = wframe((-0.22, -0.05, 1.2), (0, 0, -1), (0.0, -1.0, 0.2))
    W_stab = wframe((-0.05, -0.68, 1.3), (0, 0, -1), (0.08, -1.0, 0.05))
    pr = (-0.6, 0.5, -0.8)
    ready = merge(base, dict(arm_R=held(sv, "R", W_ready, pole=pr)))
    back = merge(base, dict(arm_R=held(sv, "R", W_back, pole=pr), chest=(0, 0, -16), spine=(0, 0, -8),
                            hips=dict(pos=(0, 0.03, -0.06), rot=(2, 0, -14))))
    stab = merge(base, dict(arm_R=held(sv, "R", W_stab, pole=pr), chest=(6, 0, 14), spine=(8, 0, 8),
                            hips=dict(pos=(0, -0.1, -0.08), rot=(8, 0, 8)),
                            leg_L=lib.planted("L", dx=0.04, dy=-0.25, yaw=10)))
    keys = [(0.0, ready, "io"), (0.2, back, "io"), (h0, stab, "snap"), (h1, stab, "io"), (0.7, ready, "io"), (T, ready, "io")]
    return "MeleeKnife", (lambda t: seq(t, keys)), T, False


def clip_hit(front):
    def mk(sv, lib):
        name = "HitFront" if front else "HitBack"
        T = EV[name]["T"]
        st = lib.ready
        sgn = 1 if front else -1           # a hit from the front throws the upper body back
        hit = merge(st, dict(spine=(-10 * sgn, 0, 4), chest=(-10 * sgn, 0, 6), neck=(-6 * sgn, 0, 0), head=(-16 * sgn, 0, 8),
                             hips=dict(pos=(0, 0.06 * sgn, -0.08), rot=(-4 * sgn, 0, 4)),
                             arm_L=dict(shoulder=(0, 0, 0), upper=(-30 if front else 25, 45, 0), fore=(-50, 0, 0)),
                             arm_R=dict(shoulder=(0, 0, 0), upper=(-20 if front else 30, -45, 0), fore=(-40, 0, 0)),
                             fingers_L=GRIP_L["open"], fingers_R=GRIP_L["open"]))
        keys = [(0.0, st, "io"), (0.09, hit, "snap"), (0.22, hit, "io"), (T, st, "io")]
        return name, (lambda t: seq(t, keys)), T, False
    return mk


def clip_stagger(sv, lib):
    """Knocked back: two stumbling steps backward (the engine moves the root EV distance), arms out."""
    ev = EV["Stagger"]
    T, D = ev["T"], ev["distance"]
    L = lib.L
    A = {s: L["ankle_" + s] for s in "LR"}

    def root(t):
        return D * ease(min(t / 1.0, 1.0), "out")

    def fn(t):
        r = root(t)                         # negative: moving backward (+Y world)
        c = copy.deepcopy(lib.ready)
        # step 1: right foot back at 0.15-0.4, step 2: left foot back at 0.45-0.75
        def step(s, t0, t1, y_from, y_to):
            if t < t0:
                y = y_from
                z = 0.0
            elif t > t1:
                y = y_to
                z = 0.0
            else:
                e = (t - t0) / (t1 - t0)
                y = y_from + (y_to - y_from) * ease(e)
                z = 0.07 * math.sin(math.pi * e)
            return dict(ankle=(A[s][0] + (0.04 if s == "L" else -0.04), y - r, A[s][2] + z), foot=(0, 0, 0), toe=0.0)
        c["leg_R"] = step("R", 0.12, 0.38, A["R"][1] + 0.1, A["R"][1] + 0.1 - D * 0.55 * 1.0 * -1 + 0.0)
        c["leg_L"] = step("L", 0.42, 0.75, A["L"][1] - 0.12, A["L"][1] - D * 1.0 * -1 - 0.12)
        k = math.exp(-t * 2.2) * math.sin(min(t / 0.12, 1.0) * math.pi / 2)
        c["hips"] = dict(pos=(0.02 * math.sin(t * 9), 0.05 * k, -0.06 - 0.08 * k), rot=(-12 * k, 4 * math.sin(t * 7), 0))
        c["spine"] = (-10 * k, 0, 0)
        c["chest"] = (-8 * k, -4 * math.sin(t * 6), 0)
        c["head"] = (-14 * k + 6 * (1 - k), 0, 0)
        c["arm_L"] = dict(shoulder=(0, 0, 0), upper=(-40 * k, 30 + 40 * k, 0), fore=(-30, 0, 0))
        c["arm_R"] = dict(shoulder=(0, 0, 0), upper=(-30 * k, -30 - 40 * k, 0), fore=(-30, 0, 0))
        c["fingers_L"] = c["fingers_R"] = GRIP_L["open"]
        if t > 1.0:
            e = ease((t - 1.0) / (T - 1.0))
            c = mix(c, _ready_at(lib, A, -D), e)
        return c
    stagger_root_curve[:] = [(round(i * T / 15, 3), round(root(i * T / 15), 3)) for i in range(16)]
    return "Stagger", fn, T, False


stagger_root_curve = []


def _ready_at(lib, A, d):
    """The ready pose, with the feet where the stagger left them (in place: the root caught up)."""
    return copy.deepcopy(lib.ready)


def clip_death(forward):
    def mk(sv, lib):
        name = "DeathForward" if forward else "DeathBack"
        ev = EV[name]
        T = ev["T"]
        st = lib.ready
        s = 1 if forward else -1
        # buckle: knees go, torso folds
        if forward:
            buckle = merge(st, dict(hips=dict(pos=(0, -0.05, -0.38), rot=(30, 0, 6)), spine=(16, 0, 0), chest=(10, 0, 0),
                                    neck=(10, 0, 0), head=(16, 0, 0),
                                    leg_L=dict(thigh=(-70, 0, 0), shin=(100, 0, 0), foot=(-30, 0, 0)),
                                    leg_R=dict(thigh=(-60, 0, 0), shin=(90, 0, 0), foot=(-30, 0, 0)),
                                    arm_L=dict(upper=(-20, 30, 0), fore=(-30, 0, 0)), arm_R=dict(upper=(-25, -30, 0), fore=(-30, 0, 0))))
            # face down, the body along -Y; hips at ~0.12 m, rotated 90 deg forward
            down = merge(st, dict(hips=dict(pos=(0.03, -0.62, -0.78), rot=(84, 0, 8)), spine=(4, 0, 0), chest=(4, 0, 0),
                                  neck=(-30, 0, 0), head=(-20, 0, 40),
                                  leg_L=dict(thigh=(-2, 6, 0), shin=(20, 0, 0), foot=(40, 0, 0)),
                                  leg_R=dict(thigh=(4, -4, 0), shin=(14, 0, 0), foot=(40, 0, 0)),
                                  arm_L=dict(shoulder=(0, 0, 0), upper=(-150, 20, 0), fore=(-20, 0, 0), hand=(0, 0, 0)),
                                  arm_R=dict(shoulder=(0, 0, 0), upper=(-10, -40, 0), fore=(-10, 0, 0), hand=(0, 0, 0)),
                                  fingers_L=GRIP_L["open"], fingers_R=GRIP_L["open"]))
        else:
            buckle = merge(st, dict(hips=dict(pos=(0, 0.08, -0.32), rot=(-14, 0, -6)), spine=(-10, 0, 0), chest=(-8, 0, 0),
                                    head=(-20, 0, 0),
                                    leg_L=dict(thigh=(-60, 0, 0), shin=(70, 0, 0), foot=(-10, 0, 0)),
                                    leg_R=dict(thigh=(-40, 0, 0), shin=(50, 0, 0), foot=(-10, 0, 0)),
                                    arm_L=dict(upper=(-40, 40, 0), fore=(-30, 0, 0)), arm_R=dict(upper=(-50, -40, 0), fore=(-40, 0, 0))))
            down = merge(st, dict(hips=dict(pos=(0.0, 0.66, -0.8), rot=(-86, 0, -6)), spine=(-2, 0, 0), chest=(-2, 0, 0),
                                  neck=(4, 0, 0), head=(6, 0, -35),
                                  leg_L=dict(thigh=(-14, 8, 0), shin=(24, 0, 0), foot=(-20, 0, 0)),
                                  leg_R=dict(thigh=(-4, -6, 0), shin=(8, 0, 0), foot=(-20, 0, 0)),
                                  arm_L=dict(shoulder=(0, 0, 0), upper=(-20, 70, 0), fore=(-30, 0, 0)),
                                  arm_R=dict(shoulder=(0, 0, 0), upper=(-100, -60, 0), fore=(-20, 0, 0)),
                                  fingers_L=GRIP_L["open"], fingers_R=GRIP_L["open"]))
        st_fk = _legs_fk(sv, st)
        keys = [(0.0, st_fk, "io"), (0.45, buckle, "in"), (ev["fall"], down, "in"), (ev["fall"] + 0.15, add(down, hips_pos=(0, 0, 0.025)), "out"),
                (ev["fall"] + 0.35, down, "in"), (T, down, "io")]
        return name, (lambda t: seq(t, keys)), T, False
    return mk


def _legs_fk(sv, c):
    """Legs of an IK pose as FK eulers (so a pose can blend into FK falls). Approximate: the
    rest legs with the hips' drop taken by the knees is close enough for the first frames."""
    d = copy.deepcopy(c)
    for s in "LR":
        d["leg_" + s] = dict(thigh=(-8, 0, 0), shin=(14, 0, 0), foot=(-6, 0, 0))
    d["hips"] = dict(pos=(0, 0, -0.03), rot=c["hips"]["rot"])
    return d


def clip_grab(sv, lib):
    ev = EV["Grab"]
    T = ev["T"]
    st = lib.ready
    reach = merge(st, dict(
        arm_L=hand_toward(sv, "L", (0.14, -0.62, 1.1), palm=(-1, 0, 0), fingers=(0, -1, 0)),
        arm_R=hand_toward(sv, "R", (-0.14, -0.62, 1.1), palm=(1, 0, 0), fingers=(0, -1, 0)),
        fingers_L=GRIP_L["open"], fingers_R=GRIP_L["open"], spine=(16, 0, 0), chest=(8, 0, 0), head=(-10, 0, 0),
        hips=dict(pos=(0, -0.12, -0.12), rot=(10, 0, 0)), leg_L=lib.planted("L", dx=0.02, dy=-0.32, yaw=6)))
    caught = merge(reach, dict(
        arm_L=hand_toward(sv, "L", (0.09, -0.6, 1.12), palm=(-1, 0.3, 0), fingers=(0, -1, -0.3)),
        arm_R=hand_toward(sv, "R", (-0.09, -0.6, 1.12), palm=(1, 0.3, 0), fingers=(0, -1, -0.3)),
        fingers_L=GRIP_L["fist"], fingers_R=GRIP_L["fist"]))
    pull = merge(caught, dict(
        arm_L=hand_toward(sv, "L", (0.1, -0.38, 1.12), palm=(-1, 0.3, 0), fingers=(0, -1, -0.3)),
        arm_R=hand_toward(sv, "R", (-0.1, -0.38, 1.12), palm=(1, 0.3, 0), fingers=(0, -1, -0.3)),
        spine=(4, 0, 0), chest=(-2, 0, 0), hips=dict(pos=(0, 0.02, -0.1), rot=(0, 0, 0))))
    start = merge(st, dict(arm_L=hand_toward(sv, "L", (0.2, -0.2, 1.0), palm=(-1, 0, 0), fingers=(0, -1, 0)),
                           arm_R=hand_toward(sv, "R", (-0.2, -0.2, 1.0), palm=(1, 0, 0), fingers=(0, -1, 0))))
    keys = [(0.0, start, "io"), (0.35, reach, "out"), (ev["catch"], caught, "io"), (0.75, pull, "io"), (T, pull, "io")]
    return "Grab", (lambda t: seq(t, keys)), T, False


def clip_drag(sv, lib):
    """Walking backward, bent over, both fists low in front (holding the caught player)."""
    G = dict(DRAG)
    hold = merge(lib.stand, dict(
        arm_L=hand_toward(sv, "L", (0.1, -0.5, 0.72), palm=(-1, 0.3, 0), fingers=(0, -1, -0.6)),
        arm_R=hand_toward(sv, "R", (-0.1, -0.5, 0.72), palm=(1, 0.3, 0), fingers=(0, -1, -0.6)),
        fingers_L=GRIP_L["fist"], fingers_R=GRIP_L["fist"]))
    return "Drag", (lambda t: gait(sv, lib, t, G, upper=hold)), G["cycle"], True


CLIPS = (clip_idle, clip_idle_alert, clip_walk, clip_run, clip_crouch, clip_crouch_walk, clip_search, clip_open_door,
         clip_vault, clip_shout, clip_signal, clip_hold_rifle, clip_hold_pistol, clip_aim_rifle, clip_aim_pistol,
         clip_shoot("rifle"), clip_shoot("pistol"), clip_reload_rifle, clip_reload_pistol, clip_melee_bat,
         clip_melee_knife, clip_hit(True), clip_hit(False), clip_stagger, clip_death(True), clip_death(False),
         clip_grab, clip_drag)
STRIDES = dict(Walk=WALK, Run=RUN, CrouchWalk=CROUCH_WALK, Drag=DRAG)

# joints of the upper-body layer (Spine and everything above it)
UPPER_BODY = ("Spine", "Chest", "Neck", "Head") + tuple(
    f"{b}_{s}" for s in "LR" for b in ("Shoulder", "UpperArm", "Forearm", "Hand", "Thumb1", "Thumb2", "Index1",
                                       "Index2", "Fingers1", "Fingers2"))


def bake_all(sv, only=None):
    lib = Lib(sv)
    made, info = [], {}
    for mk in CLIPS:
        name, fn, T, loop = mk(sv, lib)
        if only and name not in only:
            continue
        act, frames = rig.key_clip(sv, name, fn, T, loop=loop, floor=name.startswith("Death"))
        info[name] = dict(T=T, loop=loop, frames=frames, gap=sv.gap)
        rig.log(f"clip {name}: {T:.2f} s {'loop' if loop else 'once'}, IK gap {sv.gap * 100:.1f} cm "
                + " ".join(f"{k} {v * 100:.0f}" for k, v in sv.gaps.items() if v > 0.01))
        made.append(act)
    return made, info


def metadata(sv=None):
    md = {}
    for k, G in STRIDES.items():
        n = k[0].lower() + k[1:]
        md[n + "Stride"] = round(G["stride"], 3)
        md[n + "Cycle"] = round(G["cycle"], 3)
        md[n + "Speed"] = round(G["stride"] / G["cycle"], 3)
    ev = {}
    for k, v in EV.items():
        ev[k] = {kk: (list(vv) if isinstance(vv, tuple) else vv) for kk, vv in v.items() if kk != "T"}
        ev[k]["duration"] = v["T"]
    # forward (glTF +Z) displacement the engine applies over Vault / Stagger: [[t, metres], ...]
    ev["Vault"]["rootCurve"] = [list(x) for x in vault_root_curve]
    ev["Stagger"]["rootCurve"] = [list(x) for x in stagger_root_curve]
    md["events"] = ev
    md["eyeHeight"] = 1.685
    return md
