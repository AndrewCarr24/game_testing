"""The invader's body as a signed distance field (blender/assets/invader.py, stage 1).

A clothed adult (~1.8 m, boots included) in an A-pose, as a smooth union of primitives
(round cones, ellipsoids, rounded boxes, tori) evaluated on a grid in numpy and meshed by
OpenVDB (bundled with Blender). The surface IS the clothing: work jacket, cargo trousers,
boots, a balaclava over the head; the gloved hands are their own finer grid (finger gaps
need ~1.5 mm cells), built in a hand frame and placed on the rest wrist.

Every primitive carries the bone it belongs to and a clothing zone, so the same field also
answers "which limb / which garment is this point on" for the skin weights
(invader_rig.py) and the texture painter (invader_paint.py).

Blender frame: metres, Z up, the character faces -Y, its left is +X. Joints are LANDMARKS.
"""
import math

import numpy as np

# ---------------------------------------------------------------- landmarks (rest pose)
# left side; the right side is mirrored in x
ARM_DROP = 50.0          # A-pose: the upper arm points this many degrees below horizontal
FORE_BEND = 12.0         # the forearm bends forward this much at the elbow (deg)

ZONES = ("jacket", "pants", "glove", "boot", "sole", "mask", "skin", "eye", "belt", "metal", "collar", "pocket")
ZI = {z: i for i, z in enumerate(ZONES)}


def _n(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def landmarks():
    """Joint positions (Blender frame) of the rest pose. Keys ending in _L have an _R
    mirror (x negated)."""
    L = {}
    L["root"] = np.zeros(3)
    L["hips"] = np.array([0.0, 0.01, 0.95])          # pelvis centre (Hips bone head)
    L["spine"] = np.array([0.0, 0.005, 1.07])
    L["chest"] = np.array([0.0, 0.0, 1.24])
    L["neck"] = np.array([0.0, 0.012, 1.505])
    L["head"] = np.array([0.0, 0.006, 1.6])           # skull base (Head bone head)
    L["head_top"] = np.array([0.0, 0.0, 1.81])
    L["eye_L"] = np.array([0.032, -0.088, 1.685])
    # arm
    L["clav_L"] = np.array([0.025, -0.03, 1.45])        # Shoulder (clavicle) bone head
    S = np.array([0.18, 0.005, 1.43])
    d1 = np.array([math.cos(math.radians(ARM_DROP)), 0.0, -math.sin(math.radians(ARM_DROP))])
    E = S + 0.29 * d1
    b = math.radians(FORE_BEND)
    d2 = _n(d1 * math.cos(b) + np.array([0.0, -1.0, 0.0]) * math.sin(b))
    W = E + 0.255 * d2
    L["shoulder_L"], L["elbow_L"], L["wrist_L"] = S, E, W
    L["arm_dir_L"], L["fore_dir_L"] = d1, d2
    # leg
    L["hip_L"] = np.array([0.093, 0.0, 0.915])
    L["knee_L"] = np.array([0.103, -0.012, 0.505])
    L["ankle_L"] = np.array([0.11, 0.02, 0.095])
    L["ball_L"] = np.array([0.115, -0.125, 0.028])
    L["toe_L"] = np.array([0.118, -0.205, 0.028])
    L["heel_L"] = np.array([0.11, 0.07, 0.0])
    for k in list(L):
        if k.endswith("_L"):
            v = L[k].copy()
            v[0] = -v[0]
            L[k[:-2] + "_R"] = v
    return L


def hand_frame(L, side):
    """Rest frame of a hand (columns: across the knuckles toward the thumb side, along the
    fingers, the back of the hand), origin at the wrist."""
    s = 1.0 if side == "L" else -1.0
    F = _n(L["fore_dir_" + side])                    # along the fingers (continues the forearm)
    # relaxed A-pose: the thumbs point forward (-Y), the palms face the thighs
    t0 = np.array([0.0, -1.0, 0.0])
    thumb = _n(t0 - (t0 @ F) * F)
    back = _n(np.cross(thumb, F))
    if back[0] * s < 0:
        back = -back
    M = np.eye(4)
    M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = thumb, F, back, L["wrist_" + side]
    return M      # det -1 on the right hand (a mirror): flip the winding of meshes built in it


# hand-local landmarks (metres): x toward the thumb, y along the fingers, z the back of the
# hand. Fingers: base knuckle, middle joint, tip; the glove makes them ~2.2 cm thick.
HAND = dict(
    palm_len=0.1, palm_w=0.094, palm_th=0.036,
    fingers=dict(               # name: (x at the knuckle, length, splay deg, curl deg per joint)
        Index=(0.033, 0.09, 4.0, (12, 18, 12)),
        Middle=(0.011, 0.098, 0.0, (14, 20, 12)),
        Ring=(-0.012, 0.092, -4.0, (16, 22, 14)),
        Pinky=(-0.032, 0.074, -9.0, (18, 24, 14)),
    ),
    thumb_base=(0.032, 0.024, -0.012), thumb_dir=(0.75, 0.62, -0.25), thumb_len=(0.05, 0.035),
    finger_r=(0.0118, 0.0102),
)


def hand_joints():
    """Hand-local joint positions: dict finger -> [knuckle, middle, tip] (+ thumb: [cmc, mcp, tip])."""
    H = HAND
    out = {}
    for name, (x, ln, splay, curl) in H["fingers"].items():
        k = np.array([x, H["palm_len"] - (0.006 if name in ("Ring", "Pinky") else 0.0)
                      - (0.012 if name == "Pinky" else 0.0), 0.0])
        a = math.radians(splay)
        d = np.array([math.sin(a), math.cos(a), 0.0])
        pts = [k]
        segs = (ln * 0.5, ln * 0.5)
        ang = 0.0
        for j, sl in enumerate(segs):
            ang += math.radians(curl[j])
            dj = d * math.cos(ang) + np.array([0, 0, -1.0]) * math.sin(ang)
            pts.append(pts[-1] + dj * sl)
        out[name] = pts
    b = np.array(H["thumb_base"])
    td = _n(H["thumb_dir"])
    m = b + td * H["thumb_len"][0]
    td2 = _n(td + np.array([-0.15, 0.35, -0.25]))
    out["Thumb"] = [b, m, m + td2 * H["thumb_len"][1]]
    return out


# ---------------------------------------------------------------- primitives
# a primitive: dict(kind, ..., k=blend radius, op="u"|"s", bone=..., zone=...)

def rcone(a, b, ra, rb, k=0.02, **kw):
    return dict(kind="rcone", a=np.asarray(a, float), b=np.asarray(b, float), ra=ra, rb=rb, k=k, **kw)


def ell(c, r, k=0.02, rot=None, **kw):
    return dict(kind="ell", c=np.asarray(c, float), r=np.asarray(r, float),
                rot=np.eye(3) if rot is None else np.asarray(rot, float), k=k, **kw)


def rbox(c, half, rad, k=0.01, rot=None, **kw):
    return dict(kind="box", c=np.asarray(c, float), h=np.asarray(half, float), rad=rad,
                rot=np.eye(3) if rot is None else np.asarray(rot, float), k=k, **kw)


def ecyl(c, rx, ry, hz, rad, k=0.01, rot=None, **kw):
    """Capped elliptical cylinder along local z (radii rx, ry; half height hz), edges rounded by rad."""
    return dict(kind="ecyl", c=np.asarray(c, float), r2=np.array([rx, ry], float), hz=hz, rad=rad,
                rot=np.eye(3) if rot is None else np.asarray(rot, float), k=k, **kw)


def torus(c, R, r, k=0.01, rot=None, scale=(1, 1), **kw):
    """Torus around local z (after rot), ring radius R (scaled per local x/y), tube r."""
    return dict(kind="torus", c=np.asarray(c, float), R=R, r=r, sc=np.asarray(scale, float),
                rot=np.eye(3) if rot is None else np.asarray(rot, float), k=k, **kw)


def rot_x(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def basis_from(y):
    """A rotation whose local z is `y` (for tori around an axis)."""
    z = _n(y)
    x = _n(np.cross([0, 1, 0], z) if abs(z[1]) < 0.9 else np.cross([1, 0, 0], z))
    return np.stack([x, np.cross(z, x), z], 1)


def _sd(p, q):
    """Distance of points p (N, 3) to primitive q."""
    k = q["kind"]
    if k == "rcone":
        a, b, r1, r2 = q["a"], q["b"], q["ra"], q["rb"]
        ba = b - a
        l2 = ba @ ba
        rr = r1 - r2
        a2 = l2 - rr * rr
        il2 = 1.0 / l2
        pa = p - a
        y = pa @ ba
        z = y - l2
        xv = pa * l2 - y[:, None] * ba
        x2 = np.einsum("ij,ij->i", xv, xv)
        y2 = y * y * l2
        z2 = z * z * l2
        kk = np.sign(rr) * rr * rr * x2
        out = np.empty(len(p))
        m1 = np.sign(z) * a2 * z2 > kk
        m2 = (np.sign(y) * a2 * y2 < kk) & ~m1
        m3 = ~(m1 | m2)
        out[m1] = np.sqrt(x2[m1] + z2[m1]) * il2 - r2
        out[m2] = np.sqrt(x2[m2] + y2[m2]) * il2 - r1
        out[m3] = (np.sqrt(x2[m3] * a2 * il2) + y[m3] * rr) * il2 - r1
        return out
    if k == "ell":
        lp = (p - q["c"]) @ q["rot"]
        r = q["r"]
        k0 = np.linalg.norm(lp / r, axis=1)
        k1 = np.linalg.norm(lp / (r * r), axis=1)
        return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)
    if k == "box":
        lp = np.abs((p - q["c"]) @ q["rot"]) - (q["h"] - q["rad"])
        out = np.linalg.norm(np.maximum(lp, 0), axis=1) + np.minimum(lp.max(1), 0)
        return out - q["rad"]
    if k == "ecyl":
        lp = (p - q["c"]) @ q["rot"]
        r = q["r2"] - q["rad"]
        xy = lp[:, :2]
        k0 = np.linalg.norm(xy / r, axis=1)
        k1 = np.linalg.norm(xy / (r * r), axis=1)
        d2 = k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)
        w = np.stack([d2, np.abs(lp[:, 2]) - (q["hz"] - q["rad"])], 1)
        return np.minimum(w.max(1), 0) + np.linalg.norm(np.maximum(w, 0), axis=1) - q["rad"]
    if k == "torus":
        lp = (p - q["c"]) @ q["rot"]
        xy = lp[:, :2] / q["sc"]
        rad = np.linalg.norm(xy, axis=1)
        # approximate scaled ring distance (scale is mild)
        s = float(np.mean(q["sc"]))
        dq = np.stack([(rad - q["R"]) * s, lp[:, 2]], 1)
        return np.linalg.norm(dq, axis=1) - q["r"]
    raise ValueError(k)


def _aabb(q):
    k = q["kind"]
    m = q["k"] + 0.004
    if k == "rcone":
        r = max(q["ra"], q["rb"])
        lo = np.minimum(q["a"], q["b"]) - r
        hi = np.maximum(q["a"], q["b"]) + r
    elif k == "ell":
        e = np.abs(q["rot"]) @ q["r"]
        lo, hi = q["c"] - e, q["c"] + e
    elif k == "ecyl":
        e = np.abs(q["rot"]) @ np.array([q["r2"][0], q["r2"][1], q["hz"]])
        lo, hi = q["c"] - e, q["c"] + e
    elif k == "box":
        e = np.abs(q["rot"]) @ q["h"]
        lo, hi = q["c"] - e, q["c"] + e
    else:
        e = np.abs(q["rot"]) @ np.array([q["R"] * q["sc"][0] + q["r"], q["R"] * q["sc"][1] + q["r"], q["r"]])
        lo, hi = q["c"] - e, q["c"] + e
    return lo - m, hi + m


def smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b + (a - b) * h - k * h * (1 - h)


def ssub(a, b, k):
    """a minus b (smooth)."""
    if k <= 0:
        return np.maximum(a, -b)
    h = np.clip(0.5 - 0.5 * (a + b) / k, 0, 1)
    return a + (-b - a) * h + k * h * (1 - h)


def eval_points(prims, p, details=()):
    """Field at points p (N, 3); also the per-primitive distances (N, nprims) for labels."""
    d = np.full(len(p), 1.0)
    per = np.full((len(p), len(prims)), 1.0, np.float32)
    for i, q in enumerate(prims):
        lo, hi = _aabb(q)
        m = np.all((p >= lo) & (p <= hi), axis=1)
        if not m.any():
            continue
        di = _sd(p[m], q)
        per[m, i] = di
        if q.get("op", "u") == "u":
            d[m] = smin(d[m], di, q["k"])
        else:
            d[m] = ssub(d[m], di, q["k"])
    for fn in details:
        d = d + fn(p)
    return d, per


def eval_grid(prims, lo, hi, h, details=()):
    """Field on a regular grid (block-wise per primitive: only its AABB is evaluated)."""
    lo = np.asarray(lo, float)
    n = np.ceil((np.asarray(hi) - lo) / h).astype(int) + 1
    d = np.full(tuple(n), 0.05, np.float32)
    ax = [lo[i] + h * np.arange(n[i]) for i in range(3)]
    for q in prims:
        qlo, qhi = _aabb(q)
        i0 = np.clip(np.floor((qlo - lo) / h).astype(int), 0, n - 1)
        i1 = np.clip(np.ceil((qhi - lo) / h).astype(int) + 1, 0, n)
        if np.any(i1 <= i0):
            continue
        X, Y, Z = np.meshgrid(ax[0][i0[0]:i1[0]], ax[1][i0[1]:i1[1]], ax[2][i0[2]:i1[2]], indexing="ij")
        pts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
        di = _sd(pts, q).reshape(X.shape).astype(np.float32)
        blk = d[i0[0]:i1[0], i0[1]:i1[1], i0[2]:i1[2]]
        if q.get("op", "u") == "u":
            blk[...] = smin(blk, di, q["k"])
        else:
            blk[...] = ssub(blk, di, q["k"])
    if details:
        # surface detail only near the surface (|d| < 1 cm)
        near = np.abs(d) < 0.012
        idx = np.nonzero(near)
        pts = np.stack([ax[0][idx[0]], ax[1][idx[1]], ax[2][idx[2]]], 1)
        add = np.zeros(len(pts))
        for fn in details:
            add += fn(pts)
        d[idx] += add.astype(np.float32)
    return d, lo


def mesh_grid(d, lo, h, iso=0.0, adaptivity=0.0):
    """OpenVDB isosurface -> (verts, quads) in world units."""
    import openvdb as vdb
    g = vdb.FloatGrid(0.05)
    g.copyFromArray(np.ascontiguousarray(d))
    pts, quads = g.convertToQuads(iso)
    verts = np.asarray(pts, float) * h + lo
    return verts, np.asarray(quads, np.int64)


# ---------------------------------------------------------------- noise (surface detail)

def _hash3(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def vnoise(p, scale, seed=0):
    """Smooth value noise in [-1, 1] at points p (N, 3), feature size 1/scale m."""
    q = p * scale
    i = np.floor(q).astype(np.int64)
    f = q - i
    f = f * f * (3 - 2 * f)
    out = np.zeros(len(p))
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out += w * _hash3(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out * 2 - 1


# ---------------------------------------------------------------- the body

def body_prims(L, p):
    """Primitives of the clothed body (both sides), hands excluded."""
    Q = []

    def add(q, bone, zone):
        q["bone"], q["zone"] = bone, zone
        Q.append(q)

    # --- torso (jacket over the chest and hips; trousers below the hem)
    add(ell((0, 0.012, 0.92), (0.168, 0.118, 0.13), k=0.03), "Hips", "pants")           # pelvis
    for s in (1, -1):
        add(ell((0.072 * s, 0.062, 0.865), (0.088, 0.072, 0.105), k=0.03), "Hips", "pants")  # seat
    # a boxy work jacket: stacked rounded elliptical cylinders
    add(ecyl((0, 0.008, 1.06), 0.158, 0.114, 0.12, 0.05, k=0.05), "Spine", "jacket")       # abdomen
    add(ecyl((0, 0.0, 1.27), 0.172, 0.122, 0.13, 0.07, k=0.05), "Chest", "jacket")         # ribcage
    add(ell((0, 0.012, 1.40), (0.168, 0.1, 0.085), k=0.04), "Chest", "jacket")            # upper chest / back
    add(ell((0, -0.045, 1.33), (0.12, 0.06, 0.07), k=0.04), "Chest", "jacket")            # chest
    add(ell((0, 0.055, 1.33), (0.15, 0.06, 0.12), k=0.04), "Chest", "jacket")             # shoulder blades
    # the jacket's lower body, slightly proud of the trousers, ending at the hem
    zc = (p["hem_z"] + 1.02) / 2
    add(ecyl((0, 0.016, zc), 0.168, 0.126, (1.02 - p["hem_z"]) / 2, 0.012, k=0.03), "Hips", "jacket")
    # trapezius, shoulders
    for s, sd in ((1, "L"), (-1, "R")):
        add(rcone((0.03 * s, 0.025, 1.49), L["shoulder_" + sd] + np.array([0, 0.012, 0.035]), 0.058, 0.052, k=0.04),
            "Chest", "jacket")
        add(ell(L["shoulder_" + sd] + np.array([0.012 * s, 0.0, 0.0]), (0.068, 0.07, 0.072), k=0.035),
            "UpperArm_" + sd, "jacket")                                                   # deltoid
    # neck + collar
    add(rcone(L["neck"] + np.array([0, 0.012, -0.04]), L["head"] + np.array([0, 0, 0.01]), 0.064, 0.058, k=0.03),
        "Neck", "mask")
    # stand-up collar: a ring around the neck base, lower in front
    add(torus((0, 0.01, 1.518), 0.071, 0.019, k=0.015, rot=rot_x(-18), scale=(1.1, 1.0)), "Chest", "collar")
    add(torus((0, 0.012, 1.545), 0.068, 0.012, k=0.012, rot=rot_x(-22), scale=(1.08, 1.0)), "Chest", "collar")
    # --- head (under a balaclava)
    add(ell((0, 0.012, 1.71), (0.079, 0.099, 0.103), k=0.02), "Head", "mask")           # cranium
    add(ell((0, -0.036, 1.632), (0.062, 0.062, 0.064), k=0.03), "Head", "mask")         # face / jaw
    add(ell((0, -0.076, 1.588), (0.03, 0.026, 0.024), k=0.02), "Head", "mask")          # chin
    add(ell((0, -0.08, 1.705), (0.06, 0.022, 0.018), k=0.018), "Head", "mask")          # brow
    for s in (1, -1):
        add(ell((0.046 * s, -0.07, 1.655), (0.025, 0.02, 0.02), k=0.02), "Head", "mask")  # cheekbones
        add(ell((0.079 * s, 0.002, 1.668), (0.012, 0.026, 0.032), k=0.012), "Head", "mask")  # ears
    add(rcone((0, -0.091, 1.68), (0, -0.104, 1.647), 0.011, 0.014, k=0.012), "Head", "mask")   # nose
    for s in (1, -1):                                                                     # eye sockets
        add(ell((0.032 * s, -0.098, 1.684), (0.019, 0.012, 0.0105), k=0.008, op="s"), "Head", "eye")
    # --- arms (jacket sleeves)
    for s, sd in ((1, "L"), (-1, "R")):
        S, E, W = L["shoulder_" + sd], L["elbow_" + sd], L["wrist_" + sd]
        add(rcone(S + np.array([0, 0.0, -0.01]), E, 0.064, 0.051, k=0.03), "UpperArm_" + sd, "jacket")
        add(ell(S + (E - S) * 0.45 + np.array([0, 0.012, 0]), (0.054, 0.056, 0.075), k=0.03,
                rot=basis_from(E - S)), "UpperArm_" + sd, "jacket")                      # biceps/triceps bulk
        cuff = E + (W - E) * 0.86
        add(rcone(E, cuff, 0.051, 0.045, k=0.02), "Forearm_" + sd, "jacket")
        add(ell(E + (W - E) * 0.3, (0.046, 0.05, 0.075), k=0.025, rot=basis_from(W - E)), "Forearm_" + sd, "jacket")
        add(torus(cuff, 0.042, 0.007, k=0.006, rot=basis_from(W - E)), "Forearm_" + sd, "jacket")   # cuff band
    # --- legs (cargo trousers + boots)
    for s, sd in ((1, "L"), (-1, "R")):
        H, K, A = L["hip_" + sd], L["knee_" + sd], L["ankle_" + sd]
        add(rcone(H + np.array([0.012 * s, 0.0, 0.0]), K, 0.096, 0.062, k=0.045), "Thigh_" + sd, "pants")
        add(ell(H + (K - H) * 0.35 + np.array([0.012 * s, 0.0, 0]), (0.078, 0.084, 0.14), k=0.03), "Thigh_" + sd, "pants")
        add(ell(K + np.array([0, -0.022, 0.005]), (0.05, 0.035, 0.05), k=0.03), "Shin_" + sd, "pants")    # kneecap
        boot_top = np.array([A[0], A[1] - 0.004, p["boot_z"]])
        add(rcone(K, boot_top + np.array([0, 0, 0.04]), 0.06, 0.054, k=0.03), "Shin_" + sd, "pants")
        add(ell(K + (A - K) * 0.32 + np.array([0, 0.03, 0]), (0.056, 0.058, 0.1), k=0.03), "Shin_" + sd, "pants")  # calf
        # cargo pocket on the outer thigh
        pc = H + (K - H) * 0.52 + np.array([0.082 * s, -0.006, 0])
        add(rbox(pc, (0.012, 0.055, 0.075), 0.01, k=0.012, rot=rot_y(-4 * s)), "Thigh_" + sd, "pocket")
        # trouser hem bunching over the boot
        add(torus(boot_top + np.array([0, 0, 0.03]), 0.052, 0.012, k=0.015), "Shin_" + sd, "pants")
        # boot: shaft, foot, toe cap, sole, heel
        add(rcone(boot_top, A + np.array([0, 0.004, -0.01]), 0.056, 0.052, k=0.02), "Foot_" + sd, "boot")
        add(rbox((A[0], -0.055, 0.07), (0.05, 0.11, 0.045), 0.04, k=0.03), "Foot_" + sd, "boot")
        add(ell((A[0] + 0.004 * s, -0.17, 0.055), (0.052, 0.055, 0.042), k=0.02), "Toe_" + sd, "boot")
        add(rbox((A[0] + 0.002 * s, -0.068, 0.016), (0.055, 0.148, 0.016), 0.012, k=0.008), "Foot_" + sd, "sole")
        add(rbox((A[0], 0.035, 0.022), (0.05, 0.05, 0.022), 0.012, k=0.006), "Foot_" + sd, "sole")
    # belt (a band proud of the trousers at the waist, under the jacket hem it hides mostly)
    return Q


def details(p):
    """Surface detail added near the surface on the fine grid: fabric folds."""
    def fn(pts):
        z = pts[:, 2]
        out = 0.0006 * vnoise(pts, 45, 1) + 0.0004 * vnoise(pts, 140, 2)
        # soft creases at the waist, the knees and over the boots (noisy, not rings)
        band = np.exp(-((z - 1.0) / 0.06) ** 2) * 0.0009 * np.sin(z * 260 + 6 * vnoise(pts, 18, 3))
        knee = np.exp(-((z - 0.5) / 0.05) ** 2) * 0.0008 * np.sin(z * 300 + 6 * vnoise(pts, 20, 4))
        ank = np.exp(-((z - p["boot_z"] - 0.03) / 0.03) ** 2) * 0.001 * np.sin(z * 380 + 5 * vnoise(pts, 25, 5))
        return out + band + knee + ank
    return [fn]


def hand_prims(p, side):
    """Glove primitives in the hand frame (see hand_frame)."""
    H = HAND
    J = hand_joints()
    Q = []
    s = 1.0  # built for the left hand; the right is mirrored by its frame

    def add(q, bone, zone="glove"):
        q["bone"], q["zone"] = bone, zone
        Q.append(q)

    sd = side
    # palm: a flattened rounded box from the wrist to the knuckles
    add(rbox((0.0, H["palm_len"] * 0.52, 0.0), (H["palm_w"] / 2, H["palm_len"] / 2, H["palm_th"] / 2), 0.014, k=0.01),
        "Hand_" + sd)
    add(ell((0.024, 0.035, -0.008), (0.022, 0.03, 0.016), k=0.012), "Hand_" + sd)   # thumb pad
    # glove cuff (goes inside the jacket sleeve)
    add(rcone((0, -0.055, 0.0), (0, 0.012, 0.0), 0.041, 0.04, k=0.015), "Hand_" + sd)
    add(torus((0, -0.03, 0.0), 0.04, 0.006, k=0.006, rot=rot_x(90)), "Hand_" + sd)
    r0, r1 = H["finger_r"]
    for name in ("Index", "Middle", "Ring", "Pinky"):
        a, b, c = J[name]
        bone = "Index" if name == "Index" else "Fingers"
        rr = 1.0 if name != "Pinky" else 0.88
        add(rcone(a + np.array([0, -0.012, 0]), b, r0 * rr, r0 * 0.95 * rr, k=0.004), bone + "1_" + sd)
        add(rcone(b, c, r0 * 0.95 * rr, r1 * rr, k=0.003), bone + "2_" + sd)
    a, b, c = J["Thumb"]
    add(rcone(a, b, 0.0148, 0.0128, k=0.008), "Thumb1_" + sd)
    add(rcone(b, c, 0.0128, 0.011, k=0.004), "Thumb2_" + sd)
    return Q


def hand_details(pts):
    return 0.0004 * vnoise(pts, 220, 7)
