"""The Grimble's indoor actions (grimble_rig.py's solver, same skeleton): it smashes the
glass and comes into the house on all fours.

  Smash      one shot from the standing Idle at the glass: lets the staff fall, crouches,
             punches through the glass with both hands (BREAK_T), ends in the crawl rest pose
  Crawl      loop, in place: a slow, spidery lateral-sequence crawl (hind L, fore L, hind R,
             fore R), elbows high and wide, the head low, the robe dragging behind
  CrawlFast  loop, in place: the chase, a lower, longer-reaching trot
  CrawlIdle  loop: on all fours, searching (the head turns, sniffs, pauses)
  Swipe      one shot from the crawl: rears up a little and swipes the right arm forward and
             across (SWIPE_HIT)
  ReachUp    one shot from the crawl: rears up on its hind legs to full size and claws up and
             over a balustrade (REACH_HIT)

Scale. The crawl family has to fit the house's openings (everything under 2.9 m and within
2.6 m), but the head and hood alone are ~3.6 m wide and ~2.7 m tall at full size, so no pose
fits at scale 1: the creature folds down to `crawl_scale` (a uniform scale on the Root bone,
P["crawl_scale"]) during Smash and stays there in the crawl family; ReachUp unfolds to full
size for its reach and folds back. Poses are designed at scale 1 ("design metres") and the
solver scales them; targets given in world metres (the glass, the swipe's reach, the
balustrade) are divided by the current scale.

The staff: Smash drops it (it falls about its tip and lies on the ground beside the creature);
every crawl-family action holds the Staff bone in that same lying pose, unscaled. In the loops
the engine moves the creature, so it should detach the staff at the end of Smash (copy the
Grimble_Staff mesh's world matrix into a static prop, hide the skinned one); otherwise the
staff slides along beside it.

All crawl-family clips start and end at (or within a few degrees of) the crawl rest pose, so
the engine's 0.4-0.5 s cross-fades blend cleanly.
"""
import math

import numpy as np
from mathutils import Matrix, Quaternion, Vector

from grimble_rig import FPS, _np, _v, euler_q, smooth

SMASH_T = 2.5
BREAK_T = 1.2           # s into Smash when the fists go through the glass
CRAWL_T = 2.6           # s per Crawl cycle
CRAWL_S = 2.4           # design metres per Crawl cycle (x crawl_scale in the world)
FAST_T = 1.1
FAST_S = 3.2
CIDLE_T = 6.0
SWIPE_T = 1.6
SWIPE_HIT = 0.72        # s into Swipe when the claws cross the front centre line
REACH_T = 3.0
REACH_HIT = 1.55        # s into ReachUp when the claws come over the balustrade top
GLASS_Y = -2.05         # world metres in front of the origin (Knock's contact plane)
SWIPE_REACH = 2.5      # world metres in front of the origin at the hit
REACH_UP = (5.6, 1.6)   # world (height, forward) of the right wrist at the ReachUp hit (the claws
                        # lead it by ~0.5 m: measured claw numbers are in metadata())

# crawl rest pose (design metres, front -Y)
HIPS_OFF = (0.0, 0.8, -0.85)
# torso -92 deg (forward, a little down), the neck +22, the head back to +12 overall: the
# hood's back drape folds down behind the head, which keeps the hood top low
PITCH = dict(hips=-72.0, Spine1=-10.0, Spine2=-8.0, Spine3=-2.0, Neck=22.0, Head=82.0)
HAND = {"L": (1.0, -2.05), "R": (-1.05, -2.0)}     # planted wrists (x, y)
FOOT = {"L": (0.95, 0.9), "R": (-1.0, 0.95)}        # planted ankles (x, y)
POLE_ARM = {"L": (0.15, 0.9, 0.7), "R": (-0.15, 0.9, 0.7)}      # elbows up and back (not out: width)
HEAD_PITCH = 12.0       # the head's absolute pitch in the crawl (+ = face tipped up)
POLE_KNEE = {"L": (1.0, -0.7, 0.35), "R": (-1.0, -0.7, 0.35)}


def _scale(sv):
    return sv.crawl_scale


def hand_q(sv, s, F_t, N_t):
    """Rotation taking the rest hand's open-hand axes (F: wrist -> knuckles, N: palm) to
    the given directions."""
    F, N, _ = sv.open_axes[s]
    A = Matrix((_v(F), _v(N), _v(np.cross(F, N)))).transposed()
    F_t = np.asarray(F_t, float)
    F_t /= np.linalg.norm(F_t)
    N_t = np.asarray(N_t, float)
    N_t = N_t - (N_t @ F_t) * F_t
    N_t /= np.linalg.norm(N_t)
    B = Matrix((_v(F_t), _v(N_t), _v(np.cross(F_t, N_t)))).transposed()
    return (B @ A.inverted()).to_quaternion()


def prepare(sv, scale):
    """Constants that depend on the mesh: the planted hands' rotation and wrist height,
    the dropped staff's lying matrix."""
    sv.crawl_scale = scale
    sv.plant_q, sv.plant_z = {}, {}
    for s, out in (("L", 1.0), ("R", -1.0)):
        q = hand_q(sv, s, (0.3 * out, -1.0, -0.12), (0, 0, -1.0))
        sv.plant_q[s] = q
        w0 = _np(sv.R["Hand." + s].translation)
        rel = (np.array(q.to_matrix()) @ (sv.hand_verts[s] - w0).T).T
        near = np.linalg.norm(rel, axis=1) < 0.45            # the palm, not the gripping fingers
        sv.plant_z[s] = float(-np.percentile(rel[near, 2], 3)) + 0.03
    # the staff, fallen about its tip toward the right and back, lying on the ground
    tip = _v(sv.lm["staff_tip"])
    R0 = sv.R["Staff"]
    d0 = (R0 @ Vector((0, 1, 0, 0))).xyz.normalized()       # the bone's axis (tip -> grip)
    d1 = Vector((-0.94, 0.34, 0.0)).normalized()
    q = d0.rotation_difference(d1)
    sv.staff_fall_q = q
    sv.staff_lying = Matrix.Translation(tip + Vector((0, 0, 0.13))) @ q.to_matrix().to_4x4() \
        @ Matrix.Translation(-tip) @ R0


def staff_at(sv, k):
    """The staff falling: k = 0 held (rest), 1 lying; gravity-like (slow start), with a
    small bounce at the end."""
    tip = _v(sv.lm["staff_tip"])
    R0 = sv.R["Staff"]
    a = min(max(k, 0.0), 1.0)
    q = Quaternion().slerp(sv.staff_fall_q, a)
    lift = 0.13 * a
    return Matrix.Translation(tip + Vector((0, 0, lift))) @ q.to_matrix().to_4x4() @ Matrix.Translation(-tip) @ R0


def _bounce(t, t0, t1):
    """0 -> 1 between t0 and t1 with a small bounce after landing."""
    if t <= t0:
        return 0.0
    if t < t1:
        return ((t - t0) / (t1 - t0)) ** 2
    dt = t - t1
    return 1.0 - 0.04 * math.exp(-dt / 0.12) * abs(math.sin(dt * 18))


def base(sv, bob=0.0, roll=0.0, yaw=0.0, lift=0.0, look=(0.0, 0.0, 0.0), hips=(0.0, 0.0, 0.0)):
    """The crawl body: hips back and down, the torso pitched forward to near horizontal,
    the neck and head pitched back up so the face looks forward low over the floor.
    bob (design m), roll / yaw (deg), lift: 0..1 rears the front up, look: head (x, y, z) deg."""
    c = {}
    ho = np.array(HIPS_OFF) + np.array(hips)
    c["hips_off"] = (ho[0], ho[1], ho[2] + bob + 0.25 * lift)
    c["hips_rot"] = euler_q(PITCH["hips"] * (1 - 0.35 * lift), roll, yaw)
    c["Spine1"] = euler_q(PITCH["Spine1"] * (1 - lift), 0, -0.4 * yaw)
    c["Spine2"] = euler_q(PITCH["Spine2"] * (1 - lift), -0.3 * roll, -0.3 * yaw)
    c["Spine3"] = euler_q(PITCH["Spine3"], 0, -0.2 * yaw)
    c["Neck"] = euler_q(PITCH["Neck"] * (1 - 0.3 * lift), 0, 0)
    # the head keeps its world pitch as the front rears up (lift)
    d_torso = -(0.35 * PITCH["hips"] + PITCH["Spine1"] + PITCH["Spine2"]) * lift
    # ... and stays square to the direction of travel (the chain's yaw / roll cancelled):
    # the head and hood are the widest part, so any turn widens the creature
    c["Head"] = euler_q(PITCH["Head"] - d_torso + 0.3 * PITCH["Neck"] * lift + look[0],
                        look[1] - 0.7 * roll, look[2] - 0.1 * yaw)
    for s in "LR":
        c["pole_abs_" + s] = POLE_ARM[s]
        c["kpole_abs_" + s] = POLE_KNEE[s]
        c["open_" + s] = 1.0
    c["staff_world"] = sv.staff_lying
    c["root_scale"] = _scale(sv)
    # the head and hood are the widest part (any roll or turn widens the creature): the head
    # is held square to the direction of travel, pitched back HEAD_PITCH, only `look` moves it
    c["head_abs"] = euler_q(HEAD_PITCH + look[0], look[1], look[2])
    return c


def hem(c, drag=0.0, sway=0.0, swing=(0.0, 0.0)):
    """The robe hangs from the pitched hips to the floor and drags behind (design m)."""
    c["hem_tgt"] = {
        "Hem.F1": (-0.15, 1.0, 0.4), "Hem.F2": (-0.15, 2.2, 0.32),       # the front panel drags back under
        "Hem.B1": (-0.12 + sway * 0.3, 2.05 + 0.3 * drag, 0.9),
        "Hem.B2": (-0.1 + sway, 3.1 + 0.6 * drag, 0.35),
        # (the side panels' cloth sits in front of / outside their bones: aimed low, it would
        # swing through the floor)
        "Hem.L1": (1.0, 1.05 + swing[0] * 0.5, 0.95), "Hem.L2": (1.05, 1.6 + swing[0], 0.7),
        "Hem.R1": (-1.1, 1.05 + swing[1] * 0.5, 0.95), "Hem.R2": (-1.2, 1.6 + swing[1], 0.7),
    }
    return c


def place_hand(sv, s, xy, z=0.0, q=None):
    w = np.array([xy[0], xy[1], sv.plant_z[s] + z])
    return sv.hand_at(s, w, q if q is not None else sv.plant_q[s])


def place_foot(sv, s, xy, z=0.0, pitch=0.0):
    a = _np(sv.R["Foot." + s].translation)
    return sv.foot_at(s, (xy[0] - a[0], xy[1] - a[1], z), pitch)


def rest(sv):
    c = hem(base(sv))
    for s in "LR":
        c["hand_" + s] = place_hand(sv, s, HAND[s])
        c["foot_" + s] = place_foot(sv, s, FOOT[s])
    return c


def _gait(sv, t, T, S, duty, phases, lift_h, lift_f, reach=1.0):
    """Limb targets for an in-place gait: planted limbs move back at S / T (no sliding)."""
    c = {}
    feet = {}
    ph = (t / T) % 1.0
    L = S * duty
    for limb, off in phases.items():
        kind, s = limb.split(".")
        u = (ph + off) % 1.0
        if u < duty:
            dy = -L / 2 + L * (u / duty)
            z = 0.0
            k = None
        else:
            k = smooth(0, 1, (u - duty) / (1 - duty))
            dy = L / 2 - L * k
            z = math.sin(math.pi * k)
        if kind == "hand":
            x, y = HAND[s]
            y = y * reach
            # the hand comes up claws-first, fingers curled a little in the swing
            q = sv.plant_q[s] if k is None else euler_q(-25 * z, 0, 0) @ sv.plant_q[s]
            c["hand_" + s] = place_hand(sv, s, (x, y + dy), lift_h * z, q)
        else:
            x, y = FOOT[s]
            c["foot_" + s] = place_foot(sv, s, (x, y + dy), lift_f * z, -18 * z)
        feet[limb] = (dy, z)
    return c, feet, ph


def crawl(sv, t):
    phases = {"foot.L": 0.0, "hand.L": 0.25, "foot.R": 0.5, "hand.R": 0.75}      # lateral sequence
    lim, feet, ph = _gait(sv, t, CRAWL_T, CRAWL_S, 0.75, phases, 0.42, 0.32)
    w = 2 * math.pi * ph
    c = base(sv, bob=-0.05 + 0.05 * math.cos(2 * w), roll=2 * math.sin(w), yaw=3 * math.sin(w + 0.6),
             look=(2 * math.sin(2 * w), 0, 0))
    c = hem(c, drag=0.08 * math.sin(2 * w), sway=0.12 * math.sin(w - 0.8),
            swing=(feet["foot.L"][0] * 0.4, feet["foot.R"][0] * 0.4))
    c.update(lim)
    return c


def crawl_fast(sv, t):
    phases = {"foot.L": 0.0, "hand.R": 0.06, "foot.R": 0.5, "hand.L": 0.56}     # trot (diagonal pairs)
    lim, feet, ph = _gait(sv, t, FAST_T, FAST_S, 0.55, phases, 0.38, 0.42)
    w = 2 * math.pi * ph
    c = base(sv, bob=-0.12 + 0.09 * math.cos(2 * w - 0.6), roll=2.5 * math.sin(w), yaw=3 * math.sin(w + 0.4),
             look=(-4 + 3 * math.sin(2 * w), 0, 0), hips=(0, 0.1, 0))
    c = hem(c, drag=0.35 + 0.15 * math.sin(2 * w + 1.0), sway=0.2 * math.sin(w - 1.0),
            swing=(feet["foot.L"][0] * 0.5, feet["foot.R"][0] * 0.5))
    c.update(lim)
    return c


def crawl_idle(sv, t):
    """6 s: looks left, sniffs, looks right, pauses, back; weight shifts; a hand flexes."""
    ph = t / CIDLE_T
    key = [(0.0, 0.0, 0.0), (0.12, 30.0, -6.0), (0.3, 32.0, -4.0), (0.42, -5.0, 6.0), (0.5, -34.0, -8.0),
           (0.7, -30.0, -4.0), (0.82, 0.0, 4.0), (1.0, 0.0, 0.0)]
    for (t0, y0, p0), (t1, y1, p1) in zip(key, key[1:]):
        if t0 <= ph <= t1:
            k = smooth(t0, t1, ph)
            yaw, pit = y0 + (y1 - y0) * k, p0 + (p1 - p0) * k
            break
    sniff = 0.0
    for t_s in (0.24, 0.62):                        # quick sniffs (small nods)
        dt = ph - t_s
        if 0 <= dt < 0.06:
            sniff = 3.5 * math.sin(2 * math.pi * dt / 0.02) * (1 - dt / 0.06)
    w = 2 * math.pi * ph
    br = math.sin(2 * w)
    c = base(sv, bob=-0.05 + 0.025 * br, roll=2.5 * math.sin(w), yaw=0.15 * yaw,
             look=(pit + sniff, -0.12 * yaw, yaw))
    c = hem(c, drag=0.03 * br)
    for s in "LR":
        c["hand_" + s] = place_hand(sv, s, HAND[s])
        c["foot_" + s] = place_foot(sv, s, FOOT[s])
    # the left hand lifts its claws and taps once
    k = smooth(0.84, 0.88, ph) * (1 - smooth(0.92, 0.97, ph))
    if k > 0:
        c["hand_L"] = place_hand(sv, "L", HAND["L"], 0.18 * k, euler_q(28 * k, 0, 0) @ sv.plant_q["L"])
    return c


def swipe(sv, t):
    """Rears up a little, the right arm winds out to the side and sweeps forward and across."""
    s_ = _scale(sv)
    up = smooth(0.0, 0.45, t) * (1 - smooth(1.15, SWIPE_T, t))
    lunge = smooth(0.25, SWIPE_HIT, t) * (1 - smooth(SWIPE_HIT + 0.2, SWIPE_T, t))
    c = base(sv, lift=0.35 * up, hips=(0, -0.25 * up - 0.55 * lunge, 0.15 * up), look=(-8 * up, 0, -6 * up),
             yaw=-8 * up)
    c = hem(c, drag=0.1 * up)
    c["hand_L"] = place_hand(sv, "L", (HAND["L"][0], HAND["L"][1] + 0.3 * up))
    for s in "LR":
        c["foot_" + s] = place_foot(sv, s, FOOT[s])
    # the right hand's path (world metres, then / scale): wind-up out right, the sweep across
    # the front at SWIPE_REACH, through to the left, back to the floor
    reach = SWIPE_REACH / s_
    P = [(0.0, (HAND["R"][0], HAND["R"][1], 0.0)),
         (0.38, (-2.3, -1.6, 2.1)),
         (SWIPE_HIT - 0.12, (-1.4, -reach + 0.35, 1.75)),
         (SWIPE_HIT, (0.0, -reach, 1.55)),
         (SWIPE_HIT + 0.12, (1.2, -reach + 0.45, 1.3)),
         (1.1, (0.9, -1.8, 1.0)),
         (SWIPE_T, (HAND["R"][0], HAND["R"][1], 0.0))]
    w, k = _path(P, t)
    q_sw = hand_q(sv, "R", (0.55, -1.0, 0.1), (0.95, 0.2, -0.3))      # claws leading, palm across
    if t < P[1][0]:
        q = sv.plant_q["R"].slerp(q_sw, smooth(0, P[1][0], t))
    elif t > P[5][0]:
        q = q_sw.slerp(sv.plant_q["R"], smooth(P[5][0], SWIPE_T, t))
    else:
        q = q_sw
    c["hand_R"] = sv.hand_at("R", np.array([w[0], w[1], w[2] + sv.plant_z["R"]]), q)
    c["pole_abs_R"] = (-1.0, 0.6, 0.5)
    return c


def _path(P, t):
    """Catmull-Rom through timed points [(t, xyz)]."""
    ts = [p[0] for p in P]
    i = max(0, min(len(P) - 2, int(np.searchsorted(ts, t, side="right")) - 1))
    t0, t1 = ts[i], ts[i + 1]
    u = min(max((t - t0) / max(t1 - t0, 1e-6), 0.0), 1.0)
    p = [np.array(P[max(0, min(len(P) - 1, j))][1], float) for j in (i - 1, i, i + 1, i + 2)]
    a = 2 * p[1]
    b = p[2] - p[0]
    c = 2 * p[0] - 5 * p[1] + 4 * p[2] - p[3]
    d = -p[0] + 3 * p[1] - 3 * p[2] + p[3]
    return 0.5 * (a + b * u + c * u * u + d * u * u * u), u


def reach_up(sv, t):
    """Unfolds to full size up on its hind legs, claws up and over a balustrade (REACH_UP),
    hangs there a moment, drops back to the crawl."""
    s0 = _scale(sv)
    up = smooth(0.15, 1.15, t) * (1 - smooth(2.15, REACH_T, t))
    sc = s0 + (1 - s0) * up
    c = base(sv, lift=up, hips=(0, -0.55 * up, 0.75 * up), look=(18 * up, 0, 0))
    c["root_scale"] = sc
    c.pop("head_abs")
    # upright: the hips back over the feet, the spine nearly straight and leaning forward
    c["hips_rot"] = euler_q(PITCH["hips"] * (1 - up) - 12 * up, 0, 0)
    for b, a in (("Spine1", -4), ("Spine2", -4), ("Spine3", -2)):
        c[b] = euler_q(PITCH[b] * (1 - up) + a * up, 0, 0)
    c["Neck"] = euler_q(PITCH["Neck"] * (1 - up) + 6 * up, 0, 0)
    c["Head"] = euler_q(PITCH["Head"] * (1 - up) + 10 * up, 0, 0)
    c = hem(c, drag=0.0)
    c["hem_tgt"] = _blend_hem(c["hem_tgt"], up)      # the robe falls back around the legs
    for s in "LR":
        c["foot_" + s] = place_foot(sv, s, (FOOT[s][0] * (1 - 0.15 * up), FOOT[s][1] - 0.35 * up))
        c["kpole_abs_" + s] = (POLE_KNEE[s][0], -1.0, 0.1 * (1 - up))
    # the claws: world target -> design (/ the current scale)
    hz, hy = REACH_UP
    over = np.array([0.0, -(hy + 0.35), hz - 0.55])            # over the top and down the far side
    top = np.array([0.0, -hy, hz])
    P = {"R": [(0.0, None), (0.75, (-1.2, -1.3, 4.6)), (REACH_HIT - 0.25, (-0.45, -hy + 0.4, hz + 0.25)),
               (REACH_HIT, (-0.35, top[1], top[2])), (REACH_HIT + 0.35, (-0.35, over[1], over[2])),
               (2.2, (-0.5, over[1] + 0.1, over[2] - 0.1)), (REACH_T, None)],
         "L": [(0.0, None), (0.85, (1.2, -1.2, 4.4)), (REACH_HIT - 0.15, (0.55, -hy + 0.35, hz + 0.1)),
               (REACH_HIT + 0.1, (0.45, top[1], top[2] - 0.05)), (REACH_HIT + 0.45, (0.45, over[1], over[2] - 0.05)),
               (2.2, (0.6, over[1] + 0.1, over[2] - 0.15)), (REACH_T, None)]}
    for s in "LR":
        pts = []
        for tt, p in P[s]:
            if p is None:                                         # planted (design -> world)
                p = (HAND[s][0] * sc, HAND[s][1] * sc, 0.0)
            pts.append((tt, p))
        wv, _ = _path(pts, t)
        wd = wv / sc
        q_up = hand_q(sv, s, (0.15 if s == "L" else -0.15, -0.55, 1.0), (0, -0.6, -0.8))
        k = smooth(0.1, 0.8, t) * (1 - smooth(2.2, REACH_T - 0.1, t))
        q = sv.plant_q[s].slerp(q_up, k)
        c["hand_" + s] = sv.hand_at(s, np.array([wd[0], wd[1], wd[2] + sv.plant_z[s] * (1 - k)]), q)
        c["pole_abs_" + s] = tuple(np.array(POLE_ARM[s]) * (1 - up) + np.array(((1 if s == "L" else -1) * 1.0, 0.5, -0.6)) * up)
    return c


def _blend_hem(tgt, k):
    """Toward the standing drape (the hem bones' rest tails) as it rears up."""
    rest = {"Hem.F1": (-0.15, -0.8, 1.15), "Hem.F2": (-0.15, -1.0, 0.05),
            "Hem.B1": (-0.1, 1.25, 1.15), "Hem.B2": (0.0, 1.8, 0.05),
            "Hem.L1": (1.05, 0.2, 1.15), "Hem.L2": (1.35, 0.3, 0.05),
            "Hem.R1": (-1.3, 0.2, 1.15), "Hem.R2": (-1.5, 0.3, 0.05)}
    return {b: tuple(np.array(tgt[b]) * (1 - k) + np.array(rest[b]) * k) for b in tgt}


def smash(sv, t, idle_c):
    """From the standing Idle (idle_c: its controls at t = 0): lets the staff fall, crouches
    (folding down to crawl_scale), punches both fists through the glass at BREAK_T, and drops
    into the crawl rest pose."""
    s0 = _scale(sv)
    c = dict(idle_c)
    # a partial crouch into the punch, the rest of the fold (and most of the shrink) after it
    fold = 0.3 * smooth(0.3, 1.0, t) + 0.7 * smooth(BREAK_T + 0.1, 2.15, t)   # 0 standing -> 1 crawl
    sc = 1 + (s0 - 1) * (0.2 * smooth(0.4, 1.1, t) + 0.8 * smooth(BREAK_T + 0.1, 2.15, t))
    cr = rest(sv)
    # body: blend standing -> crawl rest by `fold`, with a forward lunge into the strike
    lunge = math.exp(-((t - BREAK_T) / 0.3) ** 2)
    for k in ("hips_off",):
        a, b = np.array(idle_c.get(k, (0, 0, 0))), np.array(cr[k])
        c[k] = tuple(a + (b - a) * fold + np.array([0, -0.35, 0.15]) * lunge)
    for k in ("hips_rot", "Spine1", "Spine2", "Spine3", "Neck", "Head"):
        a, b = idle_c.get(k, Quaternion()), cr[k]
        q = a.slerp(b, fold)
        if k in ("Spine2", "Spine3"):          # the torso straightens into the punch
            q = euler_q(12 * lunge, 0, 0) @ q
        c[k] = q
    c["root_scale"] = sc
    c["staff_world"] = staff_at(sv, _bounce(t, 0.15, 0.9))       # lets go: it falls, lands, bounces
    # hem: the standing drape -> the crawl's
    c["hem_tgt"] = _blend_hem(cr["hem_tgt"], 1 - fold)
    # legs: from the rest stance to the crawl's (feet shuffle back as it crouches)
    for s in "LR":
        a = _np(sv.R["Foot." + s].translation)
        f0 = np.array([a[0], a[1]])
        f1 = np.array(FOOT[s])
        k = smooth(0.4 + (0.25 if s == "R" else 0.0), 1.3 + (0.25 if s == "R" else 0.0), t)
        xy = f0 + (f1 - f0) * k
        c["foot_" + s] = place_foot(sv, s, xy, 0.3 * math.sin(math.pi * k), -12 * math.sin(math.pi * k))
        c["kpole_abs_" + s] = tuple(np.array((0.15 if s == "L" else -0.15, -1, 0)) * (1 - fold)
                                    + np.array(POLE_KNEE[s]) * fold)
        c["pole_abs_" + s] = tuple(np.array(sv.arms[s]["pole"]) * (1 - fold) + np.array(POLE_ARM[s]) * fold)
        c["open_" + s] = smooth(0.15, 0.55, t)
    # fists: off the staff, drawn back (wind-up), punched through the glass plane at
    # BREAK_T (world height 1.5-3.0 m), carried through, then down onto the floor
    gy = GLASS_Y
    for s, side in (("L", 1.0), ("R", -1.0)):
        rest_w = _np(sv.R["Hand." + s].translation)
        P = [(0.0, tuple(rest_w)),
             (0.25, tuple(rest_w + np.array([0.15 * side, 0.25, 0.1]))),
             (0.75, (0.95 * side, -0.6, 3.6)),
             # the wrists: the claws lead them by ~0.5 m, so the tips meet the glass at BREAK_T
             (BREAK_T - 0.15, (0.75 * side, gy + 1.05, 2.95 - (0.5 if s == "R" else 0.0))),
             (BREAK_T, (0.7 * side, gy + 0.45, 2.65 - (0.6 if s == "R" else 0.0))),
             (BREAK_T + 0.2, (0.85 * side, gy - 0.1, 2.05 - (0.4 if s == "R" else 0.0))),
             (1.85, (HAND[s][0] * s0, HAND[s][1] * s0, 0.6)),
             (SMASH_T, (HAND[s][0] * s0, HAND[s][1] * s0, 0.0))]
        # points are in world metres except the first two (the standing pose, scale 1)
        wv, _ = _path(P, t)
        wd = wv / sc
        q_p = hand_q(sv, s, (0.15 * side, -1.0, 0.25), (0, 0.15, -1.0))     # claws first, palm down
        if t < 0.75:
            q = Quaternion().slerp(q_p, smooth(0.15, 0.75, t))
        elif t < 1.85:
            q = q_p
        else:
            q = q_p.slerp(sv.plant_q[s], smooth(1.85, SMASH_T, t))
        z_plant = sv.plant_z[s] * smooth(1.85, SMASH_T, t)
        c["hand_" + s] = sv.hand_at(s, np.array([wd[0], wd[1], wd[2] + z_plant]), q)
        c.pop("slide_" + s, None)
    return c


def smash_fn(sv):
    from grimble_rig import idle
    c0 = idle(sv, 0.0)
    return lambda sv_, t: smash(sv_, t, c0)


def actions(sv):
    """(name, fn, seconds, opts) for grimble_rig.bake_actions."""
    return (("Smash", smash_fn(sv), SMASH_T, dict(oneshot=True)),
            ("Crawl", crawl, CRAWL_T, {}),
            ("CrawlFast", crawl_fast, FAST_T, {}),
            ("CrawlIdle", crawl_idle, CIDLE_T, {}),
            ("Swipe", swipe, SWIPE_T, dict(oneshot=True)),
            ("ReachUp", reach_up, REACH_T, dict(oneshot=True)))


# measured off the deformed claws (grimble_qa.motion_checks re-measures them on every build and
# fails if they drift): Smash's claw tips cross the glass plane; Swipe's cross the front centre
# line (reach = distance in front of the origin); ReachUp's come over the top
MEASURED = dict(smashHit=1.10, swipeHit=0.70, swipeReach=3.0, reachHit=1.55, reachUpHeight=6.3, reachUpReach=2.2)


def metadata(sv):
    """Numbers the engine needs (world metres / seconds), custom properties on the root
    (glTF extras -> userData; viewer/grimble_hunt.js reads them)."""
    s = _scale(sv)
    m = dict(crawlScale=round(s, 4),
             crawlStride=round(CRAWL_S * s, 3), crawlCycle=CRAWL_T,
             fastStride=round(FAST_S * s, 3), fastCycle=FAST_T,
             glassY=-GLASS_Y)
    m.update(MEASURED)
    return m
