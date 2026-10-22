"""The player's first-person right arm (the view model, viewer/weapons_viewmodel.js): a bare hand
gripping the chef's knife (blender/assets/kitchen_knife.py) in a hammer grip, the wrist, the
forearm, and the pushed-up sleeve of a charcoal knit sweater with a ribbed cuff.

Seen 30-60 cm from the eye, so it is modelled for that:
STAGE 1  a signed distance field (the toolkit of invader_body.py: round cones, ellipsoids,
         smooth unions) of the hand closed round the knife's handle (four fingers in three
         phalanges each wrapping the handle, the thumb over the index and middle fingers, the
         metacarpals, thenar and hypothenar pads, knuckles, nails), the wrist and forearm
         (elliptical tapered tube, the ulna's knob), the sleeve (soft folds, a ribbed cuff),
         minus the handle itself (the flesh presses flat on it). Meshed by OpenVDB at 0.8 mm.
         Cached in build/viewmodel_cache/.
STAGE 2  the game mesh: the field mesh decimated (~7k triangles), smart UVs, one 1024 atlas.
STAGE 3  bakes (Cycles): tangent normals from the field mesh, ambient occlusion (with the
         handle as an occluder); numpy paint from each texel's position and zone: skin tones
         (warmer knuckles and fingertips, a paler palm, pink nails, faint veins, freckles),
         occlusion tinted red (light that scatters through skin), pores in the normal map;
         heathered knit for the sleeve. Base colour, ORM (occlusion, roughness, metal), normal.
STAGE 4  a rig of three bones (Forearm -> Twist -> Hand) so the slash can bend and roll the
         wrist; weights blend across the wrist and along the forearm (the twist).

Frame (the grip frame, so the engine needs no re-basing): the knife's handle axis is +Z (the
blade toward +Z), the back of the hand faces +X, the edge (the front of the fist) +Y, the
forearm leaves toward -Y (and down the handle, -Z). After the glTF exporter's Y-up
conversion this is the view model's grip frame G (handle +Y, back +X, wrist +Z). The empty
`ViewmodelArm_Socket` (parented to the Hand bone) is where the weapon's `_Grip` goes, with
its frame: the engine puts the picked-up weapon there. Not a placed prop: the origin is the
handle's centre, not the floor (build_asset's grounding WARN doesn't apply).

A preview knife (the kitchen_knife asset, not exported) sits in the socket so build_asset's
sheet shows the grip.
"""
import hashlib
import importlib
import inspect
import math
import os
import sys
import time

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common  # noqa: E402
import invader_body as sdf  # noqa: E402   (the SDF toolkit: primitives, smooth unions, OpenVDB meshing)
import invader_paint as paint  # noqa: E402   (Cycles bake helpers)

for _m in (common, sdf, paint):
    importlib.reload(_m)

NAME = "ViewmodelArm"
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
CACHE = os.path.join(PROJECT, "build", "viewmodel_cache")
EXPORT = dict(export_tangents=True)

P = dict(
    name=NAME,
    h=0.0008,             # field grid cell (m)
    tris=7200,            # game mesh triangles
    tex=1024,
    ao_samples=96,
    stage="full",         # "hires": the field mesh only (shaping)
    preview_knife=True,
    # the knife's handle (kitchen_knife.py): half extents across (X: thickness, Y: height)
    handle=(0.0185 / 2 * 1.04, 0.0245 / 2 * 1.04, 0.122 / 2),
    skin=(0.745, 0.605, 0.54),        # sRGB base skin
    sleeve=(0.30, 0.31, 0.33),        # heather charcoal knit
)


def _n(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _rot(deg, axis=(0, 0, 1)):
    """3x3 rotation by deg about axis."""
    a = math.radians(deg)
    x, y, z = _n(axis)
    c, s, C = math.cos(a), math.sin(a), 1 - math.cos(a)
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
                     [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])


# ---------------------------------------------------------------- the skeleton of the grip
# Metacarpal direction (wrist -> knuckles): forward (+Y) and up the handle (+Z): the handle lies
# obliquely across the palm, so the blade leans ~110 deg from the forearm.
A_M = _n((0.0, 0.944, 0.33))
U_M = _n(np.cross((1.0, 0, 0), A_M))          # across the knuckles (radial, toward the thumb = +Z)
FORE = -A_M                                   # wrist -> elbow
WRIST = np.array([0.0165, -0.060, -0.002])      # the wrist joint (radiocarpal) centre

# fingers: height on the handle (z), MCP knuckle (x, y), phalanx lengths, radii (base, tip),
# flexion at MCP / PIP / DIP (deg, about +Z: curling toward the palm)
FINGERS = dict(
    Index=dict(z=0.044, mcp=(0.0235, 0.0228), L=(0.043, 0.025, 0.0195), r=(0.0096, 0.0079), flex=(92, 92, 38), cmc=0.0165),
    Middle=dict(z=0.0238, mcp=(0.0240, 0.0232), L=(0.047, 0.028, 0.0205), r=(0.0099, 0.0081), flex=(91, 94, 40), cmc=0.0045),
    Ring=dict(z=0.0040, mcp=(0.0235, 0.0226), L=(0.044, 0.027, 0.0200), r=(0.0093, 0.0076), flex=(91, 95, 42), cmc=-0.0068),
    Little=dict(z=-0.0148, mcp=(0.0220, 0.0212), L=(0.036, 0.0205, 0.0180), r=(0.0081, 0.0067), flex=(90, 96, 44), cmc=-0.0172),
)
# thumb: CMC (base), MCP, IP, tip; radii
THUMB = dict(cmc=(0.016, -0.050, 0.024), mcp=(-0.0035, -0.0205, 0.0565), ip=(-0.0335, -0.0065, 0.0515),
             tip=(-0.0352, 0.0150, 0.0338), r=(0.0128, 0.0104, 0.0094, 0.0078))


def finger_joints(f):
    """[MCP, PIP, DIP, tip] of a finger (world), and the unit direction of each phalanx."""
    z = f["z"]
    p = [np.array([f["mcp"][0], f["mcp"][1], z])]
    d = np.array([0.0, 1.0, 0.0])
    dirs = []
    for L, fl in zip(f["L"], f["flex"]):
        d = _rot(fl) @ d
        dirs.append(d.copy())
        p.append(p[-1] + d * L)
    return p, dirs


def cmc_point(f):
    return WRIST + 0.018 * A_M + f["cmc"] * U_M + np.array([0.0015, 0, 0])


# ---------------------------------------------------------------- field primitives
def etube(a, b, ru, rv, u, k=0.01, ribs=None, noise=None, **kw):
    """Elliptical tube from a to b: radii ru(h), rv(h) (h = 0..1 along) across directions u and
    v = axis x u; ribs = (count, amplitude, h0, h1) knit ribs round it between h0 and h1."""
    return dict(kind="etube", a=np.asarray(a, float), b=np.asarray(b, float), ru=ru, rv=rv,
                u=_n(u), k=k, ribs=ribs, noise=noise, **kw)


def _etube_sd(p, q):
    a, b = q["a"], q["b"]
    ab = b - a
    L = np.linalg.norm(ab)
    ax = ab / L
    u = q["u"] - (q["u"] @ ax) * ax
    u /= np.linalg.norm(u)
    v = np.cross(ax, u)
    pa = p - a
    t = pa @ ax
    h = np.clip(t / L, 0, 1)
    qu, qv = pa @ u, pa @ v
    ru, rv = q["ru"](h), q["rv"](h)
    if q.get("ribs"):
        n, amp, h0, h1 = q["ribs"]
        th = np.arctan2(qv, qu)
        w = np.clip((h - h0) / 0.01, 0, 1) * np.clip((h1 - h) / 0.01, 0, 1)
        bump = amp * w * np.cos(n * th)
        ru, rv = ru + bump, rv + bump
    k0 = np.sqrt((qu / ru) ** 2 + (qv / rv) ** 2)
    k1 = np.sqrt((qu / ru ** 2) ** 2 + (qv / rv ** 2) ** 2)
    d = k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)
    over = np.maximum(-t, 0) + np.maximum(t - L, 0)
    d = np.where(over > 0, np.sqrt(np.maximum(d, 0) ** 2 + over ** 2), d)
    if q.get("noise"):
        amp, scale, seed = q["noise"]
        d = d + amp * sdf.vnoise(p, scale, seed)
    return d


def _aabb(q):
    if q["kind"] == "etube":
        r = max(float(q["ru"](np.array([0.0, 0.5, 1.0])).max()), float(q["rv"](np.array([0.0, 0.5, 1.0])).max())) + 0.006
        lo = np.minimum(q["a"], q["b"]) - r
        hi = np.maximum(q["a"], q["b"]) + r
        return lo - q["k"], hi + q["k"]
    return sdf._aabb(q)


def _sd(p, q):
    return _etube_sd(p, q) if q["kind"] == "etube" else sdf._sd(p, q)


def smooth01(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def field_tree(p):
    """The arm as groups of primitives: [(group name, op, k, [prims])], combined in order:
    'u' = smooth union with what came before (k), 's' = smooth subtraction, 'min' = union."""
    hx, hy, hz = p["handle"]
    rc, el, rb = sdf.rcone, sdf.ell, sdf.rbox
    G = []
    # -- the palm: carpals, four metacarpals with their flesh, the knuckles, the pads
    palm = []
    palm.append(el(WRIST + 0.012 * A_M + np.array([0.0005, 0, 0]), (0.0150, 0.017, 0.0265), k=0.010,
                   rot=np.stack([[1.0, 0, 0], A_M, U_M], 1)))                         # carpals / heel
    for name, f in FINGERS.items():
        j, _ = finger_joints(f)
        c = cmc_point(f)
        rr = f["r"][0]
        palm.append(rc(c, j[0] - 0.002 * A_M, 0.0118, rr * 1.18, k=0.009))           # metacarpal + flesh
        palm.append(el(j[0] + np.array([0.0055, 0.0005, 0]), (0.0085, 0.0088, rr * 0.95), k=0.004))   # knuckle head
    # the palm's pads: thenar (the thumb's muscle, behind the handle near the top) and
    # hypothenar (the heel under the little finger), cupping the handle's back
    palm.append(el((0.0045, -0.0330, 0.0300), (0.0150, 0.0215, 0.0185), k=0.010, rot=sdf.rot_x(-28)))
    palm.append(el((0.0105, -0.0345, -0.0165), (0.0135, 0.0220, 0.0170), k=0.010, rot=sdf.rot_x(-20)))
    # the palm's body over the metacarpals: a flattened ellipsoid (the back of the hand is flat)
    palm.append(el(WRIST + 0.052 * A_M + np.array([0.0225, 0, 0]) + 0.002 * U_M, (0.0098, 0.044, 0.034), k=0.016,
                   rot=np.stack([[1.0, 0, 0], A_M, U_M], 1)))
    G.append(("palm", "u", 0.0, palm))
    # -- the thumb: metacarpal (inside the thenar), proximal, distal
    T = {k: np.array(v) for k, v in THUMB.items() if k != "r"}
    tr = THUMB["r"]
    thumb = [rc(T["cmc"], T["mcp"], tr[0], tr[1], k=0.006),
             rc(T["mcp"], T["ip"], tr[1], tr[2], k=0.004),
             rc(T["ip"], T["tip"], tr[2], tr[3], k=0.003)]
    G.append(("thumb", "u", 0.0055, thumb))
    # -- the four fingers, each a chain (smooth inside), side by side (hard creases between)
    chains = []
    for name, f in FINGERS.items():
        j, dirs = finger_joints(f)
        r0, r1 = f["r"]
        rs = [r0, r0 * 0.96, r0 * 0.9, r1]
        chains.append([rc(j[0], j[1], rs[0], rs[1], k=0.0),
                       rc(j[1], j[2], rs[1] * 0.98, rs[2], k=0.0025),
                       rc(j[2], j[3], rs[2] * 0.97, rs[3], k=0.0020)])
    G.append(("fingers", "u", 0.0045, chains))
    # -- nails: thin plates on the backs of the distal phalanges
    nails = []
    for name, f in FINGERS.items():
        j, dirs = finger_joints(f)
        d3 = dirs[2]
        out = np.cross((0, 0, 1.0), d3)           # perpendicular in the wrap plane, away from the palm side
        mid = (j[2] + j[3]) / 2 + d3 * 0.0025
        if out @ (mid - np.array([0, 0, mid[2]])) < 0:
            out = -out
        rr = f["r"][1]
        nails.append(el(mid + out * (rr * 1.0 - 0.0010), (0.0016, rr * 0.80, rr * 0.72), k=0.0012,
                        rot=np.stack([out, d3, np.cross(out, d3)], 1)))
    dt = _n(T["tip"] - T["ip"])
    tout = _n(np.cross(dt, (1.0, 0, 0)))          # the thumb's back faces away from the fingers (-X-ish)
    if tout[0] > 0:
        tout = -tout
    tout = _n(np.array([-1.0, 0, 0.35]) - (np.array([-1.0, 0, 0.35]) @ dt) * dt)
    nails.append(el((T["ip"] + T["tip"]) / 2 + dt * 0.003 + tout * (tr[3] - 0.0008), (0.0016, 0.0085, 0.0075), k=0.0012,
                    rot=np.stack([tout, dt, np.cross(tout, dt)], 1)))
    G.append(("nails", "u", 0.0010, nails))
    # -- the wrist and forearm: an elliptical tube (wide across the knuckles' direction),
    # the muscle belly swelling toward the elbow; the ulna's knob on the little-finger side
    elbow = WRIST + 0.30 * FORE
    fore = etube(WRIST + 0.006 * A_M, elbow,
                 ru=lambda h: 0.0270 + 0.0145 * smooth01(h / 0.72) - 0.0025 * np.exp(-((h - 0.05) / 0.04) ** 2),
                 rv=lambda h: 0.0178 + 0.0175 * smooth01(h / 0.78), u=U_M, k=0.010)
    G.append(("forearm", "u", 0.012, [fore,
                                      el(WRIST + 0.012 * FORE + np.array([0.0105, 0, 0]) - 0.0215 * U_M, (0.0062, 0.0075, 0.0065), k=0.006)]))
    # -- the handle: the flesh presses flat on it (subtracted)
    G.append(("handle", "s", 0.0022, [sdf.ecyl((0, 0, 0), hx, hy, hz, 0.004, k=0.0)]))
    # -- the sleeve: pushed up to ~7 cm past the wrist, soft folds; the ribbed cuff at its end
    s0 = WRIST + 0.072 * FORE
    s1 = WRIST + 0.30 * FORE
    fr = lambda h: 0.0270 + 0.0145 * smooth01((0.24 + h * 0.76) / 0.72)   # the forearm's radius under it
    fv = lambda h: 0.0178 + 0.0175 * smooth01((0.24 + h * 0.76) / 0.78)
    cuff = etube(s0, s0 + 0.055 * FORE, ru=lambda h: fr(h * 0.24) + 0.0042 + 0.0012 * smooth01(h / 0.3),
                 rv=lambda h: fv(h * 0.24) + 0.0042 + 0.0012 * smooth01(h / 0.3), u=U_M, k=0.0,
                 ribs=(44, 0.00075, 0.02, 0.98))
    body = etube(s0 + 0.045 * FORE, s1 + 0.02 * FORE, ru=lambda h: fr(0.2 + h * 0.8) + 0.0075, rv=lambda h: fv(0.2 + h * 0.8) + 0.0068,
                 u=U_M, k=0.0, noise=(0.0016, 55.0, 7))
    G.append(("sleeve", "min", 0.0, [cuff, body]))
    return G


def evaluate(p, pts, tree=None, groups=False):
    """The field at points pts (N, 3); with groups=True also each group's own field (labels)."""
    tree = tree or field_tree(p)
    d = np.full(len(pts), 1.0)
    per = {}
    for name, op, k, prims in tree:
        # a group: primitives smooth-unioned in turn, or chains of them (each chain smooth
        # inside, the chains side by side: a plain union, so fingers keep their creases)
        g = np.full(len(pts), 1.0)
        for chain in (prims if isinstance(prims[0], list) else [prims]):
            c = np.full(len(pts), 1.0)
            for q in chain:
                lo, hi = _aabb(q)
                m = np.all((pts >= lo) & (pts <= hi), axis=1)
                if not m.any():
                    continue
                di = _sd(pts[m], q)
                c[m] = sdf.smin(c[m], di, q["k"])
            g = np.minimum(g, c)
        if groups:
            per[name] = g.copy()
        if op == "u":
            d = sdf.smin(d, g, k)
        elif op == "s":
            d = sdf.ssub(d, g, k)
        else:
            d = np.minimum(d, g)
    return (d, per) if groups else d


def bounds():
    lo = np.array([-0.052, -0.36, -0.13])
    hi = np.array([0.072, 0.045, 0.075])
    return lo, hi


def log(*a):
    print("VIEWMODEL", *a, flush=True)


def _key(p, *extra):
    h = hashlib.sha1()
    src = inspect.getsource(sys.modules[__name__])
    # the field's source only (everything above `evaluate`'s callers), plus the parameters it reads
    h.update(src[:src.index("def bounds():")].encode())
    h.update(inspect.getsource(sdf._sd).encode())
    h.update(repr((p["h"], p["handle"]) + extra).encode())
    return h.hexdigest()[:16]


def hires(p):
    """(verts, quads) of the field mesh (cached)."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"hires_{_key(p)}.npz")
    if os.path.exists(path):
        try:
            z = np.load(path)
            return z["v"], z["f"]
        except Exception:
            pass
    t0 = time.time()
    h = p["h"]
    lo, hi = bounds()
    n = np.ceil((hi - lo) / h).astype(int) + 1
    ax = [lo[i] + h * np.arange(n[i]) for i in range(3)]
    d = np.empty(tuple(n), np.float32)
    tree = field_tree(p)
    # slab by slab along x (memory)
    Y, Z = np.meshgrid(ax[1], ax[2], indexing="ij")
    for i, x in enumerate(ax[0]):
        pts = np.stack([np.full(Y.size, x), Y.ravel(), Z.ravel()], 1)
        d[i] = evaluate(p, pts, tree).reshape(Y.shape)
    v, f = sdf.mesh_grid(np.clip(d, -0.05, 0.05), lo, h)
    log(f"field {d.shape} -> {len(v)} verts, {len(f)} quads ({time.time() - t0:.1f}s)")
    np.savez(path, v=v, f=f)
    return v, f


def _mesh(name, verts, faces, col, parent=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(x) for x in verts], [], [tuple(x) for x in faces])
    me.validate()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    if parent is not None:
        ob.parent = parent
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # (recalc_face_normals turns the decimated arm inside out: settle it by the signed volume)
    bm.faces.ensure_lookup_table()
    vol = sum(f.verts[0].co.dot(f.verts[i].co.cross(f.verts[i + 1].co)) for f in bm.faces for i in range(1, len(f.verts) - 1))
    if vol < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = True
    return ob


def _select_only(ob):
    vl = bpy.context.view_layer
    for o in vl.objects:
        if o.select_get():
            o.select_set(False)
    vl.objects.active = ob
    ob.select_set(True)


def preview_knife(col, socket):
    """The kitchen knife in the socket (preview only: its own collection, not under the root)."""
    import kitchen_knife
    importlib.reload(kitchen_knife)
    kroot, parts = kitchen_knife.build()
    grip = next(o for o in kroot.children if o.name.endswith("_Grip"))
    bpy.context.view_layer.update()
    # knife local: X to the tip, -Y the edge, Z thickness -> grip frame: Z, +Y, X
    R = Matrix(((0, 0, 1, 0), (0, -1, 0, 0), (1, 0, 0, 0), (0, 0, 0, 1)))
    kroot.matrix_world = socket.matrix_world @ R @ grip.matrix_world.inverted() @ kroot.matrix_world
    return kroot


# ---------------------------------------------------------------- stage 2: the game mesh
def lowpoly(p, v, f, col):
    """The field mesh decimated to ~p['tris'] triangles: the hand keeps more of them than the
    forearm and sleeve (a vertex group steers the collapse). Cached (vertices, faces)."""
    path = os.path.join(CACHE, f"low_{_key(p, p['tris'], 'low2')}.npz")
    if os.path.exists(path):
        try:
            z = np.load(path)
            return z["v"], z["f"]
        except Exception:
            pass
    ob = _mesh("_dec", v, f, col)
    s = (v - WRIST) @ FORE                      # along the arm: < 0 = the hand
    g = ob.vertex_groups.new(name="dense")
    w = np.clip(0.35 + 0.65 * smooth01((s + 0.005) / 0.05), 0, 1)
    for i, wi in enumerate(w):
        g.add([i], float(wi), "REPLACE")
    _select_only(ob)
    ob.data.calc_loop_triangles()
    m = ob.modifiers.new("dec", "DECIMATE")
    m.ratio = p["tris"] / len(ob.data.loop_triangles)
    m.vertex_group = "dense"
    m.vertex_group_factor = 1.0
    m.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier="dec")
    me = ob.data
    vo = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", vo)
    vo = vo.reshape(-1, 3)
    fo = np.array([tuple(pl.vertices) for pl in me.polygons if len(pl.vertices) == 3], np.int64)
    quads = [tuple(pl.vertices) for pl in me.polygons if len(pl.vertices) == 4]
    if quads:
        q = np.array(quads, np.int64)
        fo = np.concatenate([fo, q[:, [0, 1, 2]], q[:, [0, 2, 3]]])
    ob.select_set(False)
    bpy.context.view_layer.objects.active = None
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    bpy.context.view_layer.update()
    hand = ((vo - WRIST) @ FORE < 0).mean()
    log(f"lowpoly: {len(fo)} triangles ({hand * 100:.0f}% of the vertices in the hand)")
    np.savez(path, v=vo, f=fo)
    return vo, fo


# ---------------------------------------------------------------- stage 3: textures
def srgb_to_lin(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def _blur(a, r):
    """Box-blur a 2D array (r pixels, twice: ~gaussian), wrapping (the atlas has margins)."""
    for _ in range(2):
        for ax in (0, 1):
            c = np.cumsum(np.pad(a, [(r + 1, r) if i == ax else (0, 0) for i in range(a.ndim)], mode="wrap"), axis=ax)
            hi = np.take(c, np.arange(2 * r + 1, c.shape[ax]), axis=ax)
            lo = np.take(c, np.arange(0, c.shape[ax] - 2 * r - 1), axis=ax)
            a = (hi - lo) / (2 * r + 1)
    return a


def paint_maps(p, pos, nlow, ao, tan_n, size):
    """Base colour (sRGB), ORM and the tangent normal map, from each texel's position, low-poly
    normal (object space), occlusion and the baked tangent normal."""
    H, W = pos.shape[:2]
    P = pos.reshape(-1, 3).astype(np.float64)
    N = nlow.reshape(-1, 3) * 2 - 1
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-9
    _, per = evaluate(p, P, groups=True)
    names = ["palm", "thumb", "fingers", "nails", "forearm", "sleeve"]
    D = np.stack([per[k] for k in names], 1)
    zone = np.argmin(D, 1)
    nail = (per["nails"] < 0.0007) & (per["nails"] < per["fingers"] + 0.0006)
    sleeve = zone == 5
    rng = np.random.default_rng(5)
    # ---- skin
    base = srgb_to_lin(p["skin"])
    col = np.tile(base, (len(P), 1))
    # the palm side (toward the handle / facing -X on the palm and thumb) is paler and pinker
    rad = P[:, :2] / (np.linalg.norm(P[:, :2], axis=1, keepdims=True) + 1e-9)
    inward = np.clip(-(N[:, 0] * rad[:, 0] + N[:, 1] * rad[:, 1]), 0, 1)
    palmar = np.where(zone == 2, inward, np.clip(-N[:, 0] * 1.4, 0, 1))
    palmar = np.where(zone == 4, np.clip(-N[:, 0], 0, 1) * 0.6, palmar)
    col *= (1 + palmar[:, None] * np.array([0.10, 0.05, 0.04]))
    col *= (1 - (1 - palmar[:, None]) * np.array([0.04, 0.07, 0.08]))              # the back: a little tanned
    # knuckles (MCP, PIP, DIP) and fingertips: blood close under thin skin -> redder
    warm = np.zeros(len(P))
    tips = np.zeros(len(P))
    for f in FINGERS.values():
        j, _ = finger_joints(f)
        for k, pt in enumerate(j[:3]):
            c = pt + (np.array([0.012, 0, 0]) if k == 0 else np.array([0, 0, 0]))
            r = 0.011 if k == 0 else 0.0085
            warm = np.maximum(warm, np.exp(-(np.linalg.norm(P - c, axis=1) / r) ** 2) * (1 - palmar))
        tips = np.maximum(tips, np.exp(-(np.linalg.norm(P - j[3], axis=1) / 0.010) ** 2))
    T = {k: np.array(v) for k, v in THUMB.items() if k != "r"}
    tips = np.maximum(tips, np.exp(-(np.linalg.norm(P - T["tip"], axis=1) / 0.011) ** 2))
    warm = np.maximum(warm, np.exp(-(np.linalg.norm(P - T["ip"], axis=1) / 0.009) ** 2) * 0.7)
    col *= (1 + warm[:, None] * np.array([0.05, -0.15, -0.15]))
    col *= (1 + tips[:, None] * np.array([0.04, -0.09, -0.07]))
    # knuckle wrinkles: lines across the back of each bent joint (PIP, DIP, the thumb's IP),
    # ~1.5 mm apart round the joint's outer corner, fading away from its middle
    wr = np.zeros(len(P))
    joints = []
    for f in FINGERS.values():
        j, dirs = finger_joints(f)
        rr = f["r"][0]
        joints.append((j[1], dirs[0], dirs[1], rr, 1.0))
        joints.append((j[2], dirs[1], dirs[2], rr * 0.9, 0.7))
    td_in, td_out = _n(T["ip"] - T["mcp"]), _n(T["tip"] - T["ip"])
    joints.append((T["ip"], td_in, td_out, THUMB["r"][2], 1.0))
    for J, din, dout, rr, w in joints:
        axis = np.cross(din, dout)
        if np.linalg.norm(axis) < 1e-6:
            continue
        axis = axis / np.linalg.norm(axis)
        corner = _n(din - dout)                       # the joint's outer corner (the back of the finger)
        q = P - J
        qa = q @ axis
        qp = q - qa[:, None] * axis
        rad = np.linalg.norm(qp, axis=1) + 1e-9
        cosang = np.clip((qp @ corner) / rad, -1, 1)
        side = np.sign(qp @ np.cross(axis, corner))
        arc = np.arccos(cosang) * side * rad           # m along the skin from the corner's middle
        near = (np.abs(qa) < rr * 0.95) & (rad > rr * 0.6) & (rad < rr * 1.6) & (cosang > 0.2)
        ph = arc / 0.0015
        lines = np.exp(-((ph - np.round(ph)) * 0.0015 / 0.00034) ** 2 / 2)
        fade = np.exp(-(arc / 0.0042) ** 2) * np.clip(1 - (np.abs(qa) / (rr * 0.95)) ** 4, 0, 1)
        wr = np.maximum(wr, np.where(near, lines * fade * w, 0))
    col *= (1 - wr[:, None] * np.array([0.10, 0.14, 0.14]))
    # mottling (large, faint) and freckles (small, sparse) on the back of the hand and the forearm
    mott = sdf.vnoise(P, 45.0, 3) * 0.5 + sdf.vnoise(P, 140.0, 4) * 0.5
    col *= (1 + mott[:, None] * np.array([0.05, 0.075, 0.075]))
    frk = np.clip((sdf.vnoise(P, 420.0, 9) - 0.62) * 4, 0, 1) * (1 - palmar) * 0.18
    col *= (1 - frk[:, None] * np.array([0.25, 0.4, 0.5]))
    # faint veins: thin winding lines on the back of the hand and up the inner wrist
    vline = np.abs(sdf.vnoise(P * np.array([1.0, 0.25, 1.0]), 60.0, 11))
    vein = np.clip(1 - vline / 0.035, 0, 1) * np.clip(((P - WRIST) @ FORE + 0.06) / 0.04, 0, 1) * \
        np.clip(1 - ((P - WRIST) @ FORE) / 0.08, 0, 1) * (1 - palmar * 0.5) * (zone != 2)
    col = col * (1 - vein[:, None] * 0.10) + vein[:, None] * np.array([0.0, 0.004, 0.012])
    # nails: pinker, lighter, a whiter free edge
    nl = srgb_to_lin((0.84, 0.665, 0.61))
    col = np.where(nail[:, None], nl * (1 + 0.04 * sdf.vnoise(P, 900.0, 2)[:, None]), col)
    # occlusion tinted red: light in the creases has gone through skin
    aoc = ao.reshape(-1)
    tint = np.array([1.0, 0.78, 0.72])
    col *= tint + (1 - tint) * np.clip(aoc, 0, 1)[:, None] ** 0.6
    rough = 0.56 + 0.06 * palmar - 0.05 * tips + 0.04 * warm + 0.04 * sdf.vnoise(P, 300.0, 6)
    rough = np.where(nail, 0.30, rough) + wr * 0.08
    # ---- the sleeve: heathered charcoal knit (light and dark fibres), the cuff a shade darker
    sb = srgb_to_lin(p["sleeve"])
    fib = rng.random(len(P))
    heather = 0.55 * sdf.vnoise(P, 700.0, 21) + 0.45 * (fib - 0.5) * 2
    sc = sb * (1 + 0.22 * heather[:, None])
    cuffz = ((P - WRIST) @ FORE) < 0.072 + 0.05
    sc = np.where(cuffz[:, None], sc * 0.9, sc)
    sc *= np.clip(aoc, 0, 1)[:, None] ** 0.35
    col = np.where(sleeve[:, None], sc, col)
    rough = np.where(sleeve, 0.93, rough)
    alb = lin_to_srgb(col).reshape(H, W, 3)
    orm = np.stack([np.clip(aoc, 0, 1), np.clip(rough, 0.05, 1), np.zeros(len(P))], 1).reshape(H, W, 3)
    # ---- detail in the normal map: pores in the skin, a fine knit in the sleeve (isotropic bumps
    # in texture space: every island has the same texel density, so they're the same size everywhere)
    hgt = rng.random((H, W))
    pores = hgt - _blur(hgt, 1)
    knit = _blur(rng.random((H, W)), 1)
    knit = knit - _blur(knit, 3)
    sl = sleeve.reshape(H, W)
    h = np.where(sl, knit * 0.9, -np.abs(pores) * 0.28 + _blur(pores, 2) * 0.22 - _blur(wr.reshape(H, W), 1) * 0.9)
    gy, gx = np.gradient(h)
    n = tan_n * 2 - 1
    n[..., 0] -= gx
    n[..., 1] += gy            # (rows are top-down, v up)
    n /= np.linalg.norm(n, axis=2, keepdims=True) + 1e-9
    nrm = n * 0.5 + 0.5
    stats = {k: float((zone == i).mean()) for i, k in enumerate(names)}
    stats["nail"] = float(nail.mean())
    return alb.astype(np.float32), orm.astype(np.float32), nrm.astype(np.float32), stats


def textures(p, low, col):
    """UVs on the game mesh, the bakes, the paint (cached by the mesh and the painter's source)."""
    paint.uv_unwrap(low, p["tex"])
    me = low.data
    vco = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", vco)
    uv = np.zeros(len(me.loops) * 2)
    me.uv_layers[0].data.foreach_get("uv", uv)
    src = inspect.getsource(paint_maps) + _key(p)
    key = hashlib.sha1(src.encode() + np.round(vco, 5).tobytes() + np.round(uv, 5).tobytes()
                       + repr((p["tex"], p["ao_samples"], p["skin"], p["sleeve"])).encode()).hexdigest()[:16]
    path = os.path.join(CACHE, f"tex_{key}.npz")
    if os.path.exists(path):
        try:
            z = np.load(path)
            return z["alb"], z["orm"], z["nrm"]
        except Exception:
            pass
    t0 = time.time()
    size = p["tex"]
    scene = bpy.context.scene
    paint.cycles(scene, 1)
    pos_img = paint.image("_bake_pos", size)
    paint.bake(low, pos_img, "position", margin=12)
    nlo_img = paint.image("_bake_nlow", size, non_color=True)
    paint.bake(low, nlo_img, "nlow", bake_type="NORMAL", margin=12, normal_space="OBJECT")
    v, f = hires(p)
    hi = _mesh("_hi", v, f, col)
    nrm_img = paint.image("_bake_nrm", size, non_color=True)
    scene.cycles.samples = 4
    paint.bake(low, nrm_img, "target", sources=[hi], bake_type="NORMAL", margin=12, extrusion=0.004, ray=0.012,
               normal_space="TANGENT")
    hme = hi.data
    bpy.data.objects.remove(hi)
    bpy.data.meshes.remove(hme)
    # the handle as an occluder (the flesh round it darkens)
    hx, hy, hz = p["handle"]
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=1.0, radius2=1.0, depth=2 * hz)
    for vv in bm.verts:
        vv.co.x *= hx
        vv.co.y *= hy
    occ = common.mesh_object("_handle_occluder", bm, col)
    scene.cycles.samples = p["ao_samples"]
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    ao_img = paint.image("_bake_ao", size)
    paint.bake(low, ao_img, "target", bake_type="AO", margin=12)
    ome = occ.data
    bpy.data.objects.remove(occ)
    bpy.data.meshes.remove(ome)
    pos = paint.pixels(pos_img)
    nlow = paint.pixels(nlo_img)
    tan_n = paint.pixels(nrm_img)
    ao = paint.pixels(ao_img)[..., 0]
    for im in (pos_img, nlo_img, nrm_img, ao_img):
        bpy.data.images.remove(im)
    alb, orm, nrm, stats = paint_maps(p, pos, nlow, ao, tan_n, size)
    np.savez(path, alb=alb, orm=orm, nrm=nrm)
    log(f"textures baked + painted in {time.time() - t0:.1f}s; zones " +
        " ".join(f"{k} {v * 100:.1f}%" for k, v in stats.items()))
    return alb, orm, nrm


def _image(name, arr, non_color):
    im = bpy.data.images.get(name)
    if im is not None:
        bpy.data.images.remove(im)
    im = bpy.data.images.new(name, arr.shape[1], arr.shape[0], alpha=False, float_buffer=False)
    if non_color:
        im.colorspace_settings.name = "Non-Color"
    paint.set_pixels(im, arr)
    im.pack()
    return im


def material(n, alb, orm, nrm):
    name = f"M_{n}"
    m = bpy.data.materials.get(name)
    if m is not None:
        bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    nt = m.node_tree
    bsdf = next(nd for nd in nt.nodes if nd.type == "BSDF_PRINCIPLED")
    t_a = nt.nodes.new("ShaderNodeTexImage")
    t_a.image = _image(f"T_{n}_BaseColor", alb, False)
    nt.links.new(t_a.outputs["Color"], bsdf.inputs["Base Color"])
    t_o = nt.nodes.new("ShaderNodeTexImage")
    t_o.image = _image(f"T_{n}_ORM", orm, True)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(t_o.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    t_n = nt.nodes.new("ShaderNodeTexImage")
    t_n.image = _image(f"T_{n}_Normal", nrm, True)
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(t_n.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    # (skin) a touch of subsurface in Blender's own renders; the engine fakes it (viewmodel shader)
    try:
        bsdf.inputs["Subsurface Weight"].default_value = 0.15
        bsdf.inputs["Subsurface Radius"].default_value = (0.004, 0.0015, 0.0008)
    except KeyError:
        pass
    return m


# ---------------------------------------------------------------- stage 4: the rig
ELBOW = WRIST + 0.30 * FORE
BONES = (("Forearm", ELBOW, WRIST + 0.15 * FORE, None),
         ("Twist", WRIST + 0.15 * FORE, WRIST, "Forearm"),
         ("Hand", WRIST, WRIST + 0.085 * A_M, "Twist"))


def weights(v):
    """Per vertex (Forearm, Twist, Hand): the hand bends at the wrist (a 3 cm blend), the
    forearm's roll is shared out along it (the Twist bone)."""
    s = (v - WRIST) @ FORE
    hand = 1 - smooth01((s + 0.010) / 0.032)
    twist = (1 - hand) * (1 - smooth01((s - 0.03) / 0.17))
    fore = 1 - hand - twist
    return np.stack([fore, twist, hand], 1)


def rig(n, col, root, mesh):
    ad = bpy.data.armatures.new(f"{n}_Rig")
    arm = bpy.data.objects.new(f"{n}_Armature", ad)
    col.objects.link(arm)
    arm.parent = root
    _select_only(arm)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for name, head, tail, parent in BONES:
        b = ad.edit_bones.new(name)
        b.head, b.tail = Vector(head), Vector(tail)
        b.align_roll(Vector((1.0, 0, 0)))          # each bone's Z toward the back of the hand
        if parent:
            b.parent = eb[parent]
            b.use_connect = True
        eb[name] = b
    bpy.ops.object.mode_set(mode="OBJECT")
    mesh.parent = arm
    mod = mesh.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    me = mesh.data
    v = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", v)
    W = weights(v.reshape(-1, 3))
    for i, (name, *_r) in enumerate(BONES):
        g = mesh.vertex_groups.new(name=name)
        for vi in np.nonzero(W[:, i] > 0.002)[0]:
            g.add([int(vi)], float(W[vi, i]), "REPLACE")
    return arm


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    v, f = hires(p)
    if p["stage"] == "hires":
        ob = _mesh(f"{n}_Hires", v, f, col, root)
        sock = common.empty(f"{n}_Socket", col)
        sock.parent = root
        if p["preview_knife"]:
            preview_knife(col, sock)
        return root, [ob]
    lv, lf = lowpoly(p, v, f, col)
    low = _mesh(f"{n}_Mesh", lv, lf, col)
    alb, orm, nrm = textures(p, low, col)
    low.data.materials.append(material(n, alb, orm, nrm))
    arm = rig(n, col, root, low)
    # the weapon's socket: on the Hand bone, at the handle's centre in the grip frame
    sock = common.empty(f"{n}_Socket", col)
    sock.empty_display_size = 0.03
    sock.parent = arm
    sock.parent_type = "BONE"
    sock.parent_bone = "Hand"
    bpy.context.view_layer.update()
    sock.matrix_world = Matrix.Identity(4)
    # for the engine (glTF extras -> userData.viewmodel): the joints and axes in the grip frame
    root["viewmodel"] = {
        "wrist": common.to_gltf(WRIST), "elbow": common.to_gltf(ELBOW),
        "forearm": common.to_gltf(FORE),                 # wrist -> elbow
        "flex": common.to_gltf(U_M),                     # the wrist bends (palm-ward +) about this
        "deviation": common.to_gltf((1.0, 0, 0)),        # side to side (toward the thumb +)
        "twist": common.to_gltf(A_M),                    # the forearm rolls about this
    }
    bpy.context.view_layer.update()
    if p["preview_knife"]:
        preview_knife(col, sock)
    return root, [low]


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes")
