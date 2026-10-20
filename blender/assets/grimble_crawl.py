"""The Grimble's indoor actions (grimble_rig.py's solver, same skeleton): it smashes the
glass and comes into the house on all fours, keeping its staff.

  Smash      one shot from the standing Idle at the glass: leaning on the staff, it winds up
             the free left arm and rakes its claws through the glass (MEASURED smashHit), then
             crouches: the knees fold, the torso pitches down, the left claw goes to the floor,
             the head comes low and forward, the robe pools; the right hand lowers the staff
             into the drag; it ends in the crawl rest pose
  Crawl      loop, in place: a low, predatory lateral-sequence crawl (hind L, fore L, hind R,
             fore R): belly low, shoulders and elbows high, the head forward and low; the
             right fist knuckle-walks gripping the staff, which drags behind along the right
             flank, its tip sliding on the floor
  CrawlFast  loop, in place: the chase, a lower trot (diagonal pairs)
  CrawlIdle  loop: on all fours, searching (the head lifts and dips, small turns, sniffs,
             pauses; a claw taps)
  Swipe      one shot from the crawl: wind-up (the left arm pulls back, the head lowers), a fast
             wide sweep of the left claw across the front, follow-through (MEASURED swipeHit)
  ReachUp    one shot from the crawl: rears up on its hind legs (to full size) and claws up and
             over a balustrade with the left hand; the right hand keeps the staff

Scale. The crawl family has to fit the house's openings (Crawl / CrawlFast / CrawlIdle under
3.3 m and within 3.0 m), but the head and hood are ~3.7 m wide at full size, so the creature
is a little smaller on all fours: `crawl_scale` (a uniform scale on the Root bone,
P["crawl_scale"]) is reached gradually inside Smash's crouch and held in the crawl family;
ReachUp unfolds to full size for its reach and folds back. Poses are designed at scale 1
("design metres") and the solver scales them; targets given in world metres (the glass, the
balustrade) are divided by the current scale.

The staff stays in the right hand throughout. Where the hand holds it lower down the shaft
than modelled (the drag), the Staff bone is posed directly ("staff_held").

All crawl-family clips start and end at (or within a few degrees of) the crawl rest pose, so
the engine's 0.4-0.5 s cross-fades blend cleanly.
"""
import math

import numpy as np
from mathutils import Matrix, Quaternion, Vector

from grimble_rig import _np, _v, euler_q, smooth

SMASH_T = 3.0
HIT_T = 1.0             # s into Smash: the left claw's wrist drives through the glass plane
CRAWL_T = 2.6           # s per Crawl cycle
CRAWL_S = 2.2           # design metres per Crawl cycle (x crawl_scale in the world)
FAST_T = 1.1
FAST_S = 2.9
CIDLE_T = 6.0
SWIPE_T = 1.7
SWIPE_HIT = 0.7         # s into Swipe: the claw crosses the front centre line
REACH_T = 3.0
REACH_HIT = 1.55        # s into ReachUp: the claws come over the balustrade top
GLASS_Y = -2.05         # world metres in front of the origin (Knock's contact plane)
REACH_UP = (5.6, 1.6)   # world (height, forward) of the left wrist at the ReachUp hit

# crawl rest pose (design metres, front -Y): belly low, the spine running forward and a little
# up to high shoulders, the neck dropping forward, the head out in front and low
HIPS_OFF = (0.0, 0.75, -1.1)
PITCH = dict(hips=-70.0, Spine1=-10.0, Spine2=-5.0, Spine3=0.0, Neck=18.0)
HEAD_PITCH = -8.0        # the head's absolute pitch in the crawl (+ = face tipped up)
HAND_L = (1.03, -1.6)                    # planted left wrist (x, y)
FIST_R = (-1.05, -1.85)                   # the right fist's grip on the staff (x, y)
FIST_Z = 0.36                            # ... the staff's axis height there
FOOT = {"L": (0.95, 0.85), "R": (-1.0, 0.9)}        # planted ankles (x, y)
POLE_ARM = {"L": (-0.25, 0.3, 1.0), "R": (0.0, 0.3, 1.0)}     # elbows high (inside the width)
POLE_KNEE = {"L": (0.55, -0.5, 1.0), "R": (-0.55, -0.5, 1.0)}     # knees up (inside the width)
SHRUG = 36.0            # deg: the shoulders hunched up (high shoulders; it also draws the arms in)
SLIDE = 0.5             # the right hand holds the staff this far up the shaft from its modelled grip
DRAG = (-0.07, 1.0)     # the staff's tip trails this way (xy) from the fist


def _scale(sv):
    return sv.crawl_scale


def _unit(v):
    v = np.asarray(v, float)
    return v / (np.linalg.norm(v) + 1e-12)


def hand_q(sv, s, F_t, N_t):
    """Rotation taking the rest hand's open-hand axes (F: wrist -> knuckles, N: palm) to
    the given directions."""
    F, N, _ = sv.open_axes[s]
    A = Matrix((_v(F), _v(N), _v(np.cross(F, N)))).transposed()
    F_t = _unit(F_t)
    N_t = np.asarray(N_t, float)
    N_t = _unit(N_t - (N_t @ F_t) * F_t)
    B = Matrix((_v(F_t), _v(N_t), _v(np.cross(F_t, N_t)))).transposed()
    return (B @ A.inverted()).to_quaternion()


def prepare(sv, scale):
    """Constants that depend on the mesh: the planted left hand's rotation and wrist height,
    the staff's axis / hook direction, the head's neutral lateral position."""
    sv.crawl_scale = scale
    q = hand_q(sv, "L", (0.3, -1.0, -0.12), (0, 0, -1.0))
    sv.plant_q = {"L": q}
    w0 = _np(sv.R["Hand.L"].translation)
    rel = (np.array(q.to_matrix()) @ (sv.hand_verts["L"] - w0).T).T
    near = np.linalg.norm(rel, axis=1) < 0.45            # the palm, not the gripping fingers
    sv.plant_z = {"L": float(-np.percentile(rel[near, 2], 3)) + 0.03}
    # the staff: rest axis tip -> grip, its length there, the hook's direction off the axis
    tip0, g0 = np.array(sv.lm["staff_tip"], float), np.array(sv.lm["grip_R"], float)
    sv.st_tip0, sv.st_g0 = tip0, g0
    sv.st_d0 = _unit(g0 - tip0)
    sv.st_L = float(np.linalg.norm(g0 - tip0))
    V = np.asarray(sv.staff_verts, float)
    along = (V - tip0) @ sv.st_d0
    top = V[along > along.max() - 0.6]
    off = top.mean(0) - (tip0 + sv.st_d0 * ((top.mean(0) - tip0) @ sv.st_d0))
    sv.st_u0 = _unit(off - (off @ sv.st_d0) * sv.st_d0)
    sv.st_r = 0.1
    # the head's neutral lateral position in the crawl (it is held there: width)
    sv.head_x = None
    PM = sv.solve(rest(sv))
    sv.head_x = float(PM["Head"].translation.x) / scale


def staff_pose(sv, G, slide, drag=DRAG, roll_k=1.0, dir3=None):
    """The staff held in the right hand at G (design m, the axis point in the fist), the hand
    `slide` further up the shaft than modelled. The tip rests on the floor along `drag` (xy)
    from the fist, or lies along dir3 (from the fist toward the tip) unless that would put it
    under the floor. roll_k: 0 keeps the rest roll, 1 turns the hook to curl upward.
    Returns (staff bone matrix, right hand matrix)."""
    G = np.asarray(G, float)
    L = sv.st_L + slide
    tip = None
    if dir3 is not None:
        tip = G + _unit(dir3) * L
        if tip[2] < sv.st_r:
            drag, tip = (dir3[0], dir3[1]), None
    if tip is None:
        b = _unit((drag[0], drag[1], 0.0))
        h = G[2] - sv.st_r
        dxy = math.sqrt(max(L * L - h * h, 1e-4))
        tip = np.array([G[0] + b[0] * dxy, G[1] + b[1] * dxy, sv.st_r])
    a = _unit(G - np.asarray(tip, float))
    d0, u0 = sv.st_d0, sv.st_u0
    up = np.array([0, 0, 1.0])
    ut = u0 * (1 - roll_k) + up * roll_k
    ut = ut - (ut @ a) * a
    if np.linalg.norm(ut) < 1e-6:
        ut = u0 - (u0 @ a) * a
    ut = _unit(ut)
    A = Matrix((_v(d0), _v(u0), _v(np.cross(d0, u0)))).transposed()
    B = Matrix((_v(a), _v(ut), _v(np.cross(a, ut)))).transposed()
    Rm = (B @ A.inverted()).to_4x4()
    p0 = sv.st_tip0 + d0 * L
    S = Matrix.Translation(_v(G)) @ Rm @ Matrix.Translation(_v(-p0))
    staff = S @ sv.R["Staff"]
    hand = S @ Matrix.Translation(_v(d0 * slide)) @ sv.R["Hand.R"]
    return staff, hand


def base(sv, bob=0.0, roll=0.0, yaw=0.0, lift=0.0, look=(0.0, 0.0, 0.0), hips=(0.0, 0.0, 0.0)):
    """The crawl body. bob (design m), roll / yaw (deg), lift: 0..1 rears the front up,
    look: the head's (pitch, roll, yaw) in degrees on top of HEAD_PITCH."""
    c = {}
    ho = np.array(HIPS_OFF) + np.array(hips)
    c["hips_off"] = (ho[0], ho[1], ho[2] + bob + 0.3 * lift)
    c["hips_rot"] = euler_q(PITCH["hips"] * (1 - 0.35 * lift), roll, yaw)
    c["Spine1"] = euler_q(PITCH["Spine1"] * (1 - lift), 0, -0.4 * yaw)
    c["Spine2"] = euler_q(PITCH["Spine2"] * (1 - lift), -0.3 * roll, -0.3 * yaw)
    c["Spine3"] = euler_q(PITCH["Spine3"], 0, -0.2 * yaw)
    c["Neck"] = euler_q(PITCH["Neck"] * (1 - 0.6 * lift), 0, 0)
    for s, sg in (("L", -1.0), ("R", 1.0)):
        c["pole_abs_" + s] = POLE_ARM[s]
        c["kpole_abs_" + s] = POLE_KNEE[s]
        c["Shoulder." + s] = euler_q(0, sg * SHRUG * (1 - lift), 0)
    c["open_L"] = 1.0
    c["open_R"] = 0.0
    c["root_scale"] = _scale(sv)
    # the head and hood are the widest part (any roll, turn or sway widens the creature): the
    # head is held square to the direction of travel and centred; only `look` turns it
    c["head_abs"] = euler_q(HEAD_PITCH + look[0], look[1], look[2])
    if getattr(sv, "head_x", None) is not None:
        c["head_x"] = sv.head_x
    return c


def hem(c, drag=0.0, sway=0.0, swing=(0.0, 0.0)):
    """The robe hangs from the low hips toward the floor wherever its bones' roots are (so the
    cloth is not stretched), pulled in a little (width) and trailing back (design m):
    per hem bone (pull in, trail back, tail height)."""
    # (each tail's target is reached along the bone's fixed length, so a target closer than the
    # bone overshoots: the lower bones aim well back, along the floor; the back panel stays
    # above the front one's end, so the skirt's mouth stays open instead of crossing itself)
    c["hem_drop"] = {
        "Hem.F1": (0.0, 1.1, 0.6), "Hem.F2": (0.0, 1.0, 0.18),           # under the belly, back along the floor
        # the back panel trails and lies down on the floor over the front one: the skirt's rear
        # opening is closed (no view up inside it)
        "Hem.B1": (0.0, 0.75 + 0.2 * drag, 0.75), "Hem.B2": (0.0, 1.0 + 0.4 * drag, 0.45),
        "Hem.L1": (0.15, 0.6 + swing[0] * 0.5, 0.4), "Hem.L2": (0.0, 1.0 + swing[0], 0.18),
        "Hem.R1": (0.2, 0.6 + swing[1] * 0.5, 0.4), "Hem.R2": (0.0, 1.0 + swing[1], 0.18),
    }
    return c


def place_hand(sv, xy, z=0.0, q=None):
    w = np.array([xy[0], xy[1], sv.plant_z["L"] + z])
    return sv.hand_at("L", w, q if q is not None else sv.plant_q["L"])


def place_fist(sv, c, xy, z=0.0, slide=SLIDE, drag=DRAG):
    c["staff_held"], c["hand_R"] = staff_pose(sv, (xy[0], xy[1], FIST_Z + z), slide, drag)


def place_foot(sv, s, xy, z=0.0, pitch=0.0):
    a = _np(sv.R["Foot." + s].translation)
    return sv.foot_at(s, (xy[0] - a[0], xy[1] - a[1], z), pitch)


def rest(sv):
    c = hem(base(sv))
    c["hand_L"] = place_hand(sv, HAND_L)
    place_fist(sv, c, FIST_R)
    for s in "LR":
        c["foot_" + s] = place_foot(sv, s, FOOT[s])
    return c


def _gait(sv, c, t, T, S, duty, phases, lift_h, lift_f):
    """Limb targets for an in-place gait: planted limbs move back at S / T (no sliding)."""
    feet = {}
    ph = (t / T) % 1.0
    L = S * duty
    for limb, off in phases.items():
        u = (ph + off) % 1.0
        if u < duty:
            dy = -L / 2 + L * (u / duty)
            z, k = 0.0, None
        else:
            k = smooth(0, 1, (u - duty) / (1 - duty))
            dy = L / 2 - L * k
            z = math.sin(math.pi * k)
        if limb == "hand.L":
            q = sv.plant_q["L"] if k is None else euler_q(-25 * z, 0, 0) @ sv.plant_q["L"]
            c["hand_L"] = place_hand(sv, (HAND_L[0], HAND_L[1] + dy), lift_h * z, q)
        elif limb == "hand.R":
            place_fist(sv, c, (FIST_R[0], FIST_R[1] + dy), lift_h * 0.8 * z)
        else:
            s = limb[-1]
            x, y = FOOT[s]
            c["foot_" + s] = place_foot(sv, s, (x, y + dy), lift_f * z, -18 * z)
        feet[limb] = (dy, z)
    return feet, ph


def crawl(sv, t):
    ph = (t / CRAWL_T) % 1.0
    w = 2 * math.pi * ph
    c = base(sv, bob=-0.05 + 0.05 * math.cos(2 * w), roll=2 * math.sin(w), yaw=3 * math.sin(w + 0.6),
             look=(2 * math.sin(2 * w), 0, 0))
    phases = {"foot.L": 0.0, "hand.L": 0.25, "foot.R": 0.5, "hand.R": 0.75}      # lateral sequence
    feet, _ = _gait(sv, c, t, CRAWL_T, CRAWL_S, 0.75, phases, 0.42, 0.32)
    return hem(c, drag=0.08 * math.sin(2 * w), sway=0.12 * math.sin(w - 0.8),
               swing=(feet["foot.L"][0] * 0.4, feet["foot.R"][0] * 0.4))


def crawl_fast(sv, t):
    ph = (t / FAST_T) % 1.0
    w = 2 * math.pi * ph
    c = base(sv, bob=-0.12 + 0.09 * math.cos(2 * w - 0.6), roll=1.5 * math.sin(w), yaw=2 * math.sin(w + 0.4),
             look=(-4 + 3 * math.sin(2 * w), 0, 0), hips=(0, 0.1, 0))
    phases = {"foot.L": 0.0, "hand.R": 0.06, "foot.R": 0.5, "hand.L": 0.56}     # trot (diagonal pairs)
    feet, _ = _gait(sv, c, t, FAST_T, FAST_S, 0.55, phases, 0.38, 0.42)
    return hem(c, drag=0.35 + 0.15 * math.sin(2 * w + 1.0), sway=0.2 * math.sin(w - 1.0),
               swing=(feet["foot.L"][0] * 0.5, feet["foot.R"][0] * 0.5))


IDLE_YAW = 5.0          # deg: the head's searching turns (more would widen it past the limit)


def crawl_idle(sv, t):
    """6 s: lifts its head and looks left, sniffs low, looks right, pauses, back; weight
    shifts; the left claw lifts and taps."""
    ph = t / CIDLE_T
    key = [(0.0, 0.0, 0.0), (0.12, 1.0, 2.0), (0.3, 1.0, -9.0), (0.42, 0.0, -4.0), (0.5, -1.0, 2.0),
           (0.7, -1.0, -8.0), (0.82, 0.0, 3.0), (1.0, 0.0, 0.0)]
    for (t0, y0, p0), (t1, y1, p1) in zip(key, key[1:]):
        if t0 <= ph <= t1:
            k = smooth(t0, t1, ph)
            yaw, pit = (y0 + (y1 - y0) * k) * IDLE_YAW, p0 + (p1 - p0) * k
            break
    sniff = 0.0
    for t_s in (0.24, 0.62):                        # quick sniffs (small nods, low)
        dt = ph - t_s
        if 0 <= dt < 0.06:
            sniff = 3.5 * math.sin(2 * math.pi * dt / 0.02) * (1 - dt / 0.06)
    w = 2 * math.pi * ph
    br = math.sin(2 * w)
    c = base(sv, bob=-0.05 + 0.025 * br, roll=2.0 * math.sin(w), look=(pit + sniff, 0.0, yaw))
    c = hem(c, drag=0.03 * br)
    c["hand_L"] = place_hand(sv, HAND_L)
    place_fist(sv, c, FIST_R)
    for s in "LR":
        c["foot_" + s] = place_foot(sv, s, FOOT[s])
    k = smooth(0.84, 0.88, ph) * (1 - smooth(0.92, 0.97, ph))
    if k > 0:                                       # the left claw lifts and taps once
        c["hand_L"] = place_hand(sv, HAND_L, 0.18 * k, euler_q(28 * k, 0, 0) @ sv.plant_q["L"])
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


def swipe(sv, t):
    """Wind-up (weight back and right, the head lowers, the left arm pulls back and out), a
    fast wide sweep of the left claw across the front at chest height, the follow-through out
    to the right, back down."""
    wind = smooth(0.0, 0.5, t) * (1 - smooth(0.62, 0.8, t))
    lunge = smooth(0.45, SWIPE_HIT, t) * (1 - smooth(1.0, SWIPE_T, t))
    up = smooth(0.1, 0.5, t) * (1 - smooth(1.15, SWIPE_T, t))
    duck = smooth(0.3, 0.6, t) * (1 - smooth(0.95, 1.4, t))      # the head drops and turns away
    c = base(sv, lift=0.08 * up, hips=(0, 0.25 * wind - 0.4 * lunge, 0.0),
             roll=-5 * wind + 4 * lunge, yaw=10 * wind - 12 * lunge,
             look=(-14 * duck, 0, -16 * duck))
    c = hem(c, drag=0.1 * up)
    place_fist(sv, c, FIST_R)
    for s in "LR":
        c["foot_" + s] = place_foot(sv, s, FOOT[s])
    # the left wrist (design m): planted -> pulled back and out -> the sweep -> through -> down
    hl = (HAND_L[0], HAND_L[1], 0.0)
    P = [(0.0, hl),
         (0.5, (2.0, -0.9, 2.2)),                    # wound up: out, back, high
         (0.6, (2.15, -2.3, 1.9)),
         (SWIPE_HIT, (0.2, -3.75, 1.6)),             # across the front
         (0.8, (-1.5, -3.2, 1.45)),
         (0.95, (-1.9, -2.2, 1.3)),                  # follow-through, out to the right
         (1.25, (0.2, -2.3, 0.8)),
         (SWIPE_T, hl)]
    w, _ = _path(P, t)
    q_sw = hand_q(sv, "L", (-0.6, -1.0, 0.05), (-0.95, 0.15, -0.3))     # claws leading, palm across
    if t < 0.5:
        q = sv.plant_q["L"].slerp(q_sw, smooth(0.0, 0.5, t))
    elif t > 1.0:
        q = q_sw.slerp(sv.plant_q["L"], smooth(1.0, SWIPE_T, t))
    else:
        q = q_sw
    c["hand_L"] = sv.hand_at("L", np.array([w[0], w[1], w[2] + sv.plant_z["L"] * (1 - up)]), q)
    c["pole_abs_L"] = tuple(np.array(POLE_ARM["L"]) * (1 - wind) + np.array((1.0, 0.7, 0.4)) * wind)
    c.pop("head_x", None)
    return c


def reach_up(sv, t):
    """Unfolds to full size up on its hind legs, the left claw up and over a balustrade
    (REACH_UP, world), hangs there a moment, drops back to the crawl. The right hand keeps the
    staff (it comes up to the chest, the tip dragging on the floor behind)."""
    s0 = _scale(sv)
    up = smooth(0.15, 1.15, t) * (1 - smooth(2.15, REACH_T, t))
    sc = s0 + (1 - s0) * up
    c = base(sv, lift=up, hips=(0, -0.55 * up, 0.8 * up), look=(14 * up, 0, 0))
    c["root_scale"] = sc
    c.pop("head_abs")
    c.pop("head_x", None)
    # upright: the hips back over the feet, the spine nearly straight and leaning forward
    c["hips_rot"] = euler_q(PITCH["hips"] * (1 - up) - 12 * up, 0, 0)
    for b, a in (("Spine1", -4), ("Spine2", -4), ("Spine3", -2)):
        c[b] = euler_q(PITCH[b] * (1 - up) + a * up, 0, 0)
    c["Neck"] = euler_q(PITCH["Neck"] * (1 - up) + 6 * up, 0, 0)
    # the head: crawl pitch (absolute) -> upright, through the chain
    tor = PITCH["hips"] + PITCH["Spine1"] + PITCH["Spine2"] + PITCH["Spine3"] + PITCH["Neck"]
    c["Head"] = euler_q((HEAD_PITCH - tor) * (1 - up) + 10 * up, 0, 0)
    c = hem(c)
    c["hem_tgt"] = dict(REST_HEM)                     # the robe falls back around the legs
    c["hem_mix"] = 1 - up
    for s in "LR":
        c["foot_" + s] = place_foot(sv, s, (FOOT[s][0] * (1 - 0.15 * up), FOOT[s][1] - 0.35 * up))
        c["kpole_abs_" + s] = (POLE_KNEE[s][0], -1.0, 0.1 * (1 - up))
    # the right fist with the staff: up to the chest (world), the tip dragging behind
    g_up = np.array([-1.0, -1.1, 3.4])
    g0 = np.array([FIST_R[0] * s0, FIST_R[1] * s0, FIST_Z * s0])
    g = (g0 + (g_up - g0) * up) / sc
    c["staff_held"], c["hand_R"] = staff_pose(sv, g, SLIDE)
    c["pole_abs_R"] = tuple(np.array(POLE_ARM["R"]) * (1 - up) + np.array((-1.0, 0.6, -0.4)) * up)
    # the left claw: world target -> design (/ the current scale)
    hz, hy = REACH_UP
    over = np.array([0.45, -(hy + 0.35), hz - 0.55])            # over the top and down the far side
    top = np.array([0.45, -hy, hz])
    pts = [(0.0, (HAND_L[0] * sc, HAND_L[1] * sc, 0.0)), (0.75, (1.2, -1.2, 4.4)),
           (REACH_HIT - 0.25, (0.55, -hy + 0.4, hz + 0.25)), (REACH_HIT, tuple(top)),
           (REACH_HIT + 0.35, tuple(over)), (2.2, tuple(over + np.array([0.1, 0.1, -0.1]))),
           (REACH_T, (HAND_L[0] * s0, HAND_L[1] * s0, 0.0))]
    wv, _ = _path(pts, t)
    wd = wv / sc
    q_up = hand_q(sv, "L", (0.15, -0.55, 1.0), (0, -0.6, -0.8))
    k = smooth(0.1, 0.8, t) * (1 - smooth(2.2, REACH_T - 0.1, t))
    c["hand_L"] = sv.hand_at("L", np.array([wd[0], wd[1], wd[2] + sv.plant_z["L"] * (1 - k)]),
                             sv.plant_q["L"].slerp(q_up, k))
    c["pole_abs_L"] = tuple(np.array(POLE_ARM["L"]) * (1 - up) + np.array((1.0, 0.5, -0.6)) * up)
    return c


REST_HEM = {"Hem.F1": (-0.15, -0.8, 1.15), "Hem.F2": (-0.15, -1.0, 0.05),
            "Hem.B1": (-0.1, 1.25, 1.15), "Hem.B2": (0.0, 1.8, 0.05),
            "Hem.L1": (1.05, 0.2, 1.15), "Hem.L2": (1.35, 0.3, 0.05),
            "Hem.R1": (-1.3, 0.2, 1.15), "Hem.R2": (-1.5, 0.3, 0.05)}


def _blend_hem(tgt, k):
    """Toward the standing drape (the hem bones' rest tails) by k."""
    return {b: tuple(np.array(tgt[b]) * (1 - k) + np.array(REST_HEM[b]) * k) for b in tgt}


def smash(sv, t, idle_c):
    """From the standing Idle (idle_c: its controls at t = 0). 0-0.35 the left hand lets go of
    the staff, 0.35-0.85 wind-up (the left arm draws back and up, the knees give, the torso
    turns), HIT_T the claw rakes through the glass, then the crouch (1.25-2.7): the knees fold
    first, the torso pitches down, the head comes low and forward, the left claw goes to the
    floor, the right hand lowers the staff into the drag, the robe pools; the scale eases to
    crawl_scale inside that motion; 2.7-3.0 settles into the crawl rest pose."""
    s0 = _scale(sv)
    sc = 1 + (s0 - 1) * smooth(1.3, 2.85, t)
    cr = rest(sv)
    c = dict(idle_c)
    for k_ in ("slide_L", "slide_R"):
        c.pop(k_, None)
    # body curves
    knees = 0.25 * smooth(0.35, 0.85, t) + 0.75 * smooth(1.25, 2.1, t)     # hips down (knees fold)
    torso = 0.22 * smooth(0.6, 1.0, t) + 0.78 * smooth(1.45, 2.5, t)       # torso pitches down
    neck = smooth(1.7, 2.65, t)                                             # head low and forward
    turn = smooth(0.35, 0.8, t) * (1 - smooth(0.85, 1.3, t))               # the wind-up twist
    strike = math.exp(-((t - HIT_T) / 0.22) ** 2)
    ho = np.array(idle_c.get("hips_off", (0, 0, 0)))
    hc = np.array(cr["hips_off"])
    hip = ho.copy()
    hip[2] = ho[2] + (hc[2] - ho[2]) * knees
    hip[1] = ho[1] + (hc[1] - ho[1]) * smooth(1.3, 2.4, t) - 0.3 * strike
    c["hips_off"] = tuple(hip)
    for b in ("hips_rot", "Spine1", "Spine2", "Spine3"):
        q = idle_c.get(b, Quaternion()).slerp(cr[b], torso)
        if b == "Spine2":
            q = euler_q(0, 0, 14 * turn - 10 * strike) @ q
        c[b] = q
    c["Neck"] = idle_c.get("Neck", Quaternion()).slerp(cr["Neck"], neck)
    c["Head"] = Quaternion()
    look = -8 * smooth(0.3, 0.9, t) * (1 - smooth(1.2, 1.8, t))          # the head dips into the strike
    c["head_abs"] = euler_q(look, 0, 0).slerp(cr["head_abs"], neck)
    c["root_scale"] = sc
    # the robe: the standing drape -> pooling as the hips come down -> the crawl's drag
    pool = smooth(1.25, 2.1, t)
    tgt = dict(REST_HEM)
    for b in ("Hem.L2", "Hem.R2", "Hem.F2", "Hem.B2"):       # the hem spreads a little on the floor
        x, y, z = tgt[b]
        spread = 0.25 * pool
        tgt[b] = (x * (1 + spread), y * (1 + spread), z)
    c["hem_tgt"] = tgt
    c["hem_drop"] = cr["hem_drop"]
    c["hem_mix"] = smooth(1.6, 2.8, t)
    # legs: from the rest stance to the crawl's (the feet step back and out as it crouches)
    for s in "LR":
        a = _np(sv.R["Foot." + s].translation)
        f0 = np.array([a[0], a[1]])
        f1 = np.array(FOOT[s])
        k = smooth(1.35 + (0.3 if s == "R" else 0.0), 1.85 + (0.3 if s == "R" else 0.0), t)
        xy = f0 + (f1 - f0) * k
        c["foot_" + s] = place_foot(sv, s, xy, 0.25 * math.sin(math.pi * k), -10 * math.sin(math.pi * k))
        fold = max(knees, torso)
        c["kpole_abs_" + s] = tuple(np.array((0.15 if s == "L" else -0.15, -1, 0)) * (1 - fold)
                                    + np.array(POLE_KNEE[s]) * fold)
        c["pole_abs_" + s] = tuple(np.array(sv.arms[s]["pole"]) * (1 - torso) + np.array(POLE_ARM[s]) * torso)
    # the left claw (world metres; the first point is the rest grip on the staff): off the staff,
    # wound up back and high, raked through the glass at HIT_T, down through it, then onto the
    # floor in the crawl's place
    gy = GLASS_Y
    rest_w = _np(sv.R["Hand.L"].translation)
    hl = np.array([HAND_L[0] * s0, HAND_L[1] * s0, 0.0])
    P = [(0.0, tuple(rest_w)),
         (0.3, tuple(rest_w + np.array([0.2, 0.25, 0.15]))),
         (0.82, (1.55, 0.25, 4.6)),                       # wound up: back, out, high
         (HIT_T - 0.1, (1.05, gy + 1.0, 3.5)),
         (HIT_T, (0.8, gy + 0.4, 3.0)),
         (HIT_T + 0.17, (0.75, gy - 0.05, 2.15)),        # through the glass, raking down
         (1.45, (0.9, gy + 0.3, 1.4)),
         (2.2, (hl[0] + 0.1, hl[1] - 0.1, 0.55)),
         (2.65, tuple(hl)), (SMASH_T, tuple(hl))]
    wv, _ = _path(P, t)
    wd = wv / sc
    q_p = hand_q(sv, "L", (0.1, -1.0, -0.35), (0, 0.35, -1.0))         # claws forward and down, palm down
    if t < 0.82:
        q = Quaternion().slerp(q_p, smooth(0.15, 0.82, t))
    elif t < 1.9:
        q = q_p
    else:
        q = q_p.slerp(sv.plant_q["L"], smooth(1.9, 2.65, t))
    z_plant = sv.plant_z["L"] * smooth(2.1, 2.65, t)
    c["hand_L"] = sv.hand_at("L", np.array([wd[0], wd[1], wd[2] + z_plant]), q)
    c["open_L"] = smooth(0.15, 0.6, t)
    c["open_R"] = 0.0
    # the right hand keeps the staff: planted as it is through the strike (leaning on it a
    # little), then lowered: the fist comes down to the crawl's place, the hand sliding up the
    # shaft, the tip sliding back and out along the floor
    low = smooth(1.3, 2.6, t)
    if low <= 0:
        c["hand_R"] = sv.on_staff("R")
        c.pop("staff_held", None)
    else:
        g0 = np.array(sv.st_g0)
        g1 = np.array([FIST_R[0], FIST_R[1], FIST_Z]) * s0
        g_world = g0 + (g1 - g0) * low
        # the staff's direction from the fist: as modelled (down, the tip a little left of the
        # grip) -> straight down -> out to the right -> trailing behind (the tip on the floor)
        d_rest = _unit(sv.st_tip0 - g0)
        d_side = _unit((-0.35, 0.6, -0.72))
        d_drag = _unit((DRAG[0], DRAG[1], -0.05))
        k1, k2 = smooth(0.0, 0.4, low), smooth(0.25, 0.9, low)
        d = _unit(d_rest * (1 - k1) + d_side * k1)
        d = _unit(d * (1 - k2) + d_drag * k2)
        c["staff_held"], c["hand_R"] = staff_pose(sv, g_world / sc, SLIDE * low, roll_k=low, dir3=d)
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
MEASURED = dict(smashHit=0.93, swipeHit=0.70, swipeReach=3.6, reachHit=1.55, reachUpHeight=6.4, reachUpReach=2.2)


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
