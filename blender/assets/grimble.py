"""The Grimble: the villain. A cute-uncanny furry creature in a hooded black wool
cloak, leaning on a gnarled staff, 7.3 m tall. Static model (no rig yet).

Built every time from the AI sculpt concept/grimble/source/trellis2_gen2.glb
(TRELLIS.2, one fused 98k-face mesh, see its README):
 1. import, scale to P["height"], floor at z = 0 ("source frame"; every landmark
    in P is in this frame); the final model is shifted so the floor point between
    the feet (P["feet_mid"]) is the origin, front -Y.
 2. voxel remesh (watertight, drops the sculpt's degenerate / non-manifold faces),
    pre-decimate, then keep only faces that can be seen from outside (ray casts
    from every direction a player can look from; the sculpt is full of internal
    membranes); the source colour is sampled onto each face. Cached in
    build/grimble_cache/ (keyed on the source file and these parameters).
 3. classify faces: body (face, hands, feet: pale/brown fur and skin, gated by
    zone), staff (inside the rebuilt staff: removed), eye sockets (inside the new
    eyeballs: removed), cloak (the rest); decimate once with a vertex-group weight
    (face detail protected, cloak back cheapest), so body and cloak keep a shared,
    crack-free seam; clean the labels (majority vote, small islands) and split.
 4. body: UV unwrap (face one island, given extra texel density), bake the source
    colour (selected-to-active), the high-res normals and per-texel position /
    normal, then repaint in numpy (grimble_paint.py): fur, muzzle, nose, smile,
    eye rims, leathery hands, dark claws, plus a fur/wrinkle normal map.
    cloak: tileable coarse wool (base colour + normal) at world-scale UVs.
 5. eyes: real glossy eyeballs (Grimble_Eye_L / _R, origin at the eyeball centre,
    iris along local -Y = glTF +Z, custom property look = True).
 6. staff: rebuilt procedurally along the sculpt's staff line (gnarled, knotted,
    curled hook), planted in front of the right foot.
 7. baked ambient occlusion into the "AO" vertex colour (lib/vertex_ao.py).

Run inside Blender (blender/run.py) or headless via blender/tools/build_asset.py.
"""
import hashlib
import importlib
import json
import math
import os
import sys
import time

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, textures, vertex_ao  # noqa: E402
import grimble_hands  # noqa: E402
import grimble_paint  # noqa: E402
import grimble_rig  # noqa: E402
import grimble_rim  # noqa: E402

for _m in (common, textures, vertex_ao, grimble_hands, grimble_paint, grimble_rig, grimble_rim):
    importlib.reload(_m)

NAME = "Grimble"
# exporter options (build_asset.py): tangents, so three.js doesn't derive normal-map tangents
# from screen-space UV derivatives (a speck along every UV seam)
EXPORT = dict(export_tangents=True)
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
CACHE = os.path.join(PROJECT, "build", "grimble_cache")

P = dict(
    name=NAME,
    source="concept/grimble/source/trellis2_gen2.glb",
    height=7.3,                    # metres, top of the hood
    feet_mid=(-0.12, -0.29),       # source frame: floor point between the feet -> origin
    # base mesh
    voxel=0.012,                   # voxel remesh size (m)
    pre_ratio=0.12,                # decimation before the visibility cull
    vis_dirs=150,                  # visibility: directions on the sphere
    vis_spacing=0.02,              # visibility: ray spacing (m)
    vis_grow=3,                    # rings of faces kept around every face a ray hit
    vis_spacing2=0.03, vis_dirs2=120,   # the second cull, on the decimated mesh
    # budget: body + cloak triangles after the decimation
    tris_body=14000,
    tris_cloak=7000,
    hole_perimeter=8.0,            # the final hole pass closes holes / slits up to this perimeter (m)
    hood_core_res=(28, 14),
    # the hood's rolled, frayed front edge (grimble_rim.py)
    rim=True, rim_seed=11, rim_bins=72, rim_segments=84, rim_phi_max=145.0,
    rim_face_w=-0.1,               # body vertices this far in front of the head's centre count as the face
    rim_margin=0.04,               # the opening: the face's outline plus this (m)
    rim_wave=0.025,                # waviness of the line (m)
    rim_lift=0.02,                 # out from the hood surface (m)
    rim_radius=0.07,               # lip radius (m): an ~11 cm thick hem
    rim_thick_var=0.25,
    rim_cut=0.06,                  # cloak shards inside the opening (+ this) ...
    rim_depth=0.35,                # ... and less than this behind the face's edge are removed
    rim_cut_out=0.50,              # the hood's torn flaps this far outside the opening, in front of the rim, too
    rim_min_piece=400,             # cloak pieces left smaller than this (faces) after the cut go
    rim_fringe_step=1, rim_fringe_per=1, rim_fringe_len=0.09,        # the dark shell filling the hood behind the face (segments)
    cloak_back_smooth=0,           # Laplacian iterations softening the cloak's coarse back
    face_smooth=2,                 # Laplacian iterations on the face (closes hairline cracks)
    nose_crease=(0.45, -1.45, 5.62), nose_smooth=16, nose_smooth_r=0.6,   # ... and harder around the nose's sides
    # decimation steering (small weights: x(1 + 2000 w) collapse cost)
    protect=dict(face=0.004, hands=0.0006, feet=0.0, cloak_front=0.0008, cloak_back=0.0),
    # landmarks (source frame, metres). Eyes: (x, z) of the socket centre seen from the
    # front; +x is the creature's left.
    eye_l=(0.835, 5.675),
    eye_r=(0.055, 5.93),
    nose=(0.40, 5.48),
    face_centre=(0.30, -1.0, 5.6),
    face_radii=(1.45, 1.2, 1.35),
    feet=((-0.93, -0.09), (0.69, -0.48)),
    eye_diameter=0.44,             # fits the sculpt's sockets (~0.45 m across)
    eye_proud=0.38,                # fraction of the radius standing proud of the socket
    eye_segments=(28, 18),
    socket_scale=1.5, socket_back=1.25,   # the dark backing behind each eye (x R; hidden behind the eyeball)
    # staff centre line (source frame): traced from the sculpt (ground .. top of the
    # shaft), then the hook curling over toward +x and down
    staff_path=[
        (-0.085, -1.765, 0.0), (-0.097, -1.757, 0.475), (-0.140, -1.728, 0.920),
        (-0.199, -1.686, 1.396), (-0.320, -1.694, 1.864), (-0.386, -1.636, 2.337),
        (-0.474, -1.594, 2.808), (-0.62, -1.57, 3.27), (-0.80, -1.575, 3.70),
        (-0.93, -1.54, 4.18), (-1.06, -1.56, 4.65), (-1.222, -1.573, 5.124),
        (-1.370, -1.536, 5.586), (-1.573, -1.588, 6.012), (-1.79, -1.72, 6.40),
        (-1.78, -1.80, 6.66), (-1.64, -1.84, 6.81), (-1.46, -1.84, 6.84),
        (-1.33, -1.83, 6.72), (-1.33, -1.82, 6.56), (-1.41, -1.80, 6.47),
    ],
    staff_r=(0.098, 0.122),        # shaft radius at the bottom / top
    staff_hook_r=0.088,            # radius at the hook's tip
    staff_cut=0.15,                # sculpt faces this close to the staff line are removed
    grip_r=0.40,                   # faces this close to the staff line (in the hand zone) are hand
    staff_sides=10,
    staff_step=0.055,              # ring spacing along the staff (m)
    staff_seed=5,
    # hands (rebuilt on the grips; the sculpt's hands are removed)
    finger_r=0.050,                # finger radius (m): fat and knobbly, ~1/3 of the staff's width
    finger_gap=0.97,               # finger spacing along the shaft (x finger diameter): touching
    finger_wrap=200.0,             # degrees each finger curls round the shaft (index; the rest a bit less)
    finger_slant=0.35,             # how far (x spacing) each finger slants down the shaft as it wraps
    knuckle_angle=0.45,            # the knuckle row's angle, as a fraction of the front's from the wrist side
    thumb_wrap=40.0,
    claw_len=0.13,
    hand_tile=0.25,                # metres per hand skin texture tile
    hand_seed=3,
    tex_hand=1024,
    # face backing: a hole-free shell just behind the fur, textured from the face island
    backing_inset=0.04, backing_steps=(16, 48), backing_max_angle=75.0,
    # textures
    tex_body=2048, tex_cloak=1024, tex_staff=1024, tex_eye=512,
    cloak_tile=0.6,                # metres per cloak texture tile
    cloak_normal=0.35,             # cloak normal map strength (the weave; strong values glint at grazing light)
    cloak_specular=0.25,           # Specular IOR Level (KHR_materials_specular): black wool barely reflects
    body_specular=0.2,             # ... and fur
    lining_ao=0.3,                 # occlusion of the cloak's lining copies
    lining_dark=0.85,
    backing_ao=0.5,                # the face backing (seen through the face's creases) reads as fur in shadow               # how much the cloak's inward-facing side is darkened (baked into AO)
    staff_tile=0.7,
    face_texel_boost=1.25,         # face island scale relative to hands / feet before packing
    uv_smooth=40,                  # Laplacian iterations on the copy the body UVs are projected from
    ao=True,
    rig=True,                      # skeleton, skin weights and the actions (grimble_rig.py)
    force=False,                   # regenerate cached base mesh / textures
)

BODY, CLOAK, STAFF, EYE = 0, 1, 2, 3
EYE_AXES = {}          # socket axis per eye (set by _eye_spheres)


def log(*a):
    print("GRIMBLE", *a, flush=True)


# ----------------------------------------------------------------- utilities

def _hash(*items):
    h = hashlib.sha1()
    for it in items:
        if isinstance(it, np.ndarray):
            h.update(np.ascontiguousarray(it).tobytes())
        else:
            h.update(repr(it).encode())
    return h.hexdigest()[:16]


def _mesh_arrays(me):
    v = np.zeros(len(me.vertices) * 3, np.float64)
    me.vertices.foreach_get("co", v)
    me.calc_loop_triangles()
    t = np.zeros(len(me.loop_triangles) * 3, np.int64)
    me.loop_triangles.foreach_get("vertices", t)
    return v.reshape(-1, 3), t.reshape(-1, 3)


def _mesh_from_arrays(name, verts, tris):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts))
    me.vertices.foreach_set("co", np.asarray(verts, np.float32).ravel())
    n = len(tris)
    me.loops.add(n * 3)
    me.loops.foreach_set("vertex_index", np.asarray(tris, np.int32).ravel())
    me.polygons.add(n)
    me.polygons.foreach_set("loop_start", np.arange(0, 3 * n, 3, dtype=np.int32))
    me.update(calc_edges=True)
    me.validate()
    return me


def _object(name, me, col=None):
    ob = bpy.data.objects.new(name, me)
    (col or bpy.context.scene.collection).objects.link(ob)
    return ob


def _remove(ob):
    me = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    if me is not None and me.users == 0:
        bpy.data.meshes.remove(me)


def _catmull(points, step):
    """Centripetal-ish Catmull-Rom through points, resampled every `step` metres."""
    pts = [np.array(p, float) for p in points]
    pts = [2 * pts[0] - pts[1]] + pts + [2 * pts[-1] - pts[-2]]
    dense = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for t in np.linspace(0, 1, 24, endpoint=False):
            t2, t3 = t * t, t * t * t
            dense.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                                + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    dense.append(pts[-2])
    dense = np.array(dense)
    seg = np.linalg.norm(np.diff(dense, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    n = max(2, int(round(s[-1] / step)) + 1)
    si = np.linspace(0, s[-1], n)
    out = np.stack([np.interp(si, s, dense[:, k]) for k in range(3)], axis=1)
    return out, si


def _dist_polyline(pts, path):
    """Distance from each point to the polyline, and the arc length of the nearest point."""
    best = np.full(len(pts), np.inf)
    best_s = np.zeros(len(pts))
    s0 = 0.0
    for a, b in zip(path[:-1], path[1:]):
        ab = b - a
        L2 = ab @ ab
        t = np.clip(((pts - a) @ ab) / max(L2, 1e-12), 0, 1)
        d = np.linalg.norm(pts - (a + t[:, None] * ab), axis=1)
        m = d < best
        best[m] = d[m]
        best_s[m] = s0 + t[m] * math.sqrt(L2)
        s0 += math.sqrt(L2)
    return best, best_s


# ----------------------------------------------------------- source + base mesh

def _import_source(p):
    path = os.path.join(PROJECT, p["source"])
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    src = next(o for o in new if o.type == "MESH")
    for o in new:
        if o is not src:
            bpy.data.objects.remove(o, do_unlink=True)
    src.parent = None
    src.matrix_world = Matrix.Identity(4)
    me = src.data
    v, _ = _mesh_arrays(me)
    s = p["height"] / (v[:, 2].max() - v[:, 2].min())
    me.transform(Matrix.Translation((0, 0, -v[:, 2].min() * s)) @ Matrix.Scale(s, 4))
    src.name = NAME + "_Source"
    return src


def _back_visible(verts, tris, occluders=(), dirs=150, spacing=0.02):
    """Which triangles are seen from their back side by a viewer outside the model
    (orthographic ray grids from all directions above the ground, like _visible_faces).
    occluders: (verts, tris) of the other parts."""
    allv, allt, off = [verts], [tris], len(verts)
    for ev, et in occluders:
        allv.append(ev)
        allt.append(et + off)
        off += len(ev)
    av, at = np.concatenate(allv), np.concatenate(allt)
    tree = BVHTree.FromPolygons([tuple(x) for x in av], [tuple(t) for t in at], all_triangles=True)
    fn = np.cross(verts[tris[:, 1]] - verts[tris[:, 0]], verts[tris[:, 2]] - verts[tris[:, 0]])
    nreal = len(tris)
    lo, hi = verts.min(0), verts.max(0)
    cen = Vector(((lo + hi) / 2).tolist())
    R = float(np.linalg.norm(hi - lo) / 2) + 0.1
    k = int(R / spacing)
    back = np.zeros(nreal, bool)
    ga = math.pi * (3 - math.sqrt(5))
    rc = tree.ray_cast
    for i in range(dirs):
        z = 1 - 2 * (i + 0.5) / dirs
        r = math.sqrt(1 - z * z)
        dd = Vector((r * math.cos(ga * i), r * math.sin(ga * i), z))
        if dd.z < -0.97:
            continue
        ray = -dd
        a = dd.orthogonal().normalized()
        b = dd.cross(a).normalized()
        o0 = cen + dd * (R + 1)
        rn = np.array(ray)
        for ii in range(-k, k + 1):
            oi = o0 + a * (ii * spacing)
            for jj in range(-k, k + 1):
                hit = rc(oi + b * (jj * spacing), ray, 2 * R + 2)
                if hit[2] is None or hit[2] >= nreal:
                    continue
                if dd.z < 0 and hit[0].z + dd.z * 1.0 < 0.5:
                    continue
                if fn[hit[2]] @ rn > 0:
                    back[hit[2]] = True
    return back


def _add_lining(cloak, others, mat, p, cuffs=()):
    """The cloak is single-sided (three.js lit its back faces with a flipped normal: pale
    streaks, flecks and torn-looking light patches along the rims and inside the hood);
    where its back is really seen (the hood lining, the inside of the sleeves and of the
    front opening) a flipped copy 4 mm behind, in a dark lining material, takes its place.
    Copies keep the source vertices' skin weights. Cached by geometry."""
    me = cloak.data
    v, t = _mesh_arrays(me)
    key = _hash(np.round(v, 4), t, [np.round(o[0], 3).sum() for o in others], "lining5")
    cache = os.path.join(CACHE, "lining.npz")
    back = None
    if os.path.exists(cache) and not p["force"]:
        z = np.load(cache)
        if str(z["key"]) == key:
            back = z["back"]
    if back is None:
        back = _back_visible(v, t, others, dirs=150, spacing=0.02)
        back |= _back_visible_near(v, t, others, p["_head_centre"])
        np.savez_compressed(cache, key=np.array(key), back=back)
    log(f"lining: {back.sum()} of {len(t)} cloak faces are seen from behind")
    # two kinds: patches of the outer surface wound inside-out by the remesh / decimation
    # (normal toward the creature's core: seen from outside, they're really its front) are
    # flipped; the rest is the cloth's inner side (hood, sleeves, front opening) and gets
    # the dark lining copy
    fc_ = v[t].mean(1)
    fn_ = np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]])
    fn_ /= np.linalg.norm(fn_, axis=1, keepdims=True) + 1e-12
    head = p["_head_centre"]
    kk = np.clip((fc_[:, 2] - 4.6) / 0.8, 0, 1)[:, None]
    core = np.c_[np.full(len(fc_), -0.1 - p["_shift"][0]), np.full(len(fc_), 0.25 - p["_shift"][1]), fc_[:, 2]] * (1 - kk) + head * kk
    out_ = fc_ - core
    out_ /= np.linalg.norm(out_, axis=1, keepdims=True) + 1e-12
    # (no flipping: which side is "really" outside is ambiguous on the thin double shell)
    interior = back & ((fn_ * out_).sum(1) >= -0.2)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    faces = [bm.faces[i] for i in np.nonzero(back)[0]]
    is_int = {bm.faces[i] for i in np.nonzero(interior)[0]}
    dup = bmesh.ops.duplicate(bm, geom=faces)
    nf = [g for g in dup["geom"] if isinstance(g, bmesh.types.BMFace)]
    nverts = [g for g in dup["geom"] if isinstance(g, bmesh.types.BMVert)]
    fmap = dup["face_map"]
    bmesh.ops.reverse_faces(bm, faces=nf)
    bm.normal_update()
    ao = bm.verts.layers.float_color.get(vertex_ao.ATTR)
    dark = set()
    for src_f, new_f in fmap.items():
        near_face = (Vector(src_f.calc_center_median()) - Vector(p["_head_centre"].tolist())).length < 1.5 \
            if isinstance(src_f, bmesh.types.BMFace) else False
        if isinstance(src_f, bmesh.types.BMFace) and (src_f in is_int or near_face):
            dark |= set(new_f.verts)
    for x in nverts:
        x.co = x.co + x.normal * 0.004
        if ao is not None and x in dark:           # the inside of the hood / sleeves: in shadow
            c0 = x[ao]
            x[ao] = (min(c0[0], p["lining_ao"]),) * 3 + (1.0,)
    # the sleeve cuffs' caps (closing the sleeves where the sculpt's hands were) are the
    # inside of the sleeve: lining too (they caught the sun as a pale wedge)
    nc = 0
    for c in cuffs:
        cv = min(bm.verts, key=lambda x: (Vector(c.tolist()) - x.co).length)
        if (Vector(c.tolist()) - cv.co).length < 1e-3:
            for f in cv.link_faces:
                f.material_index = 1
                nc += 1
            if ao is not None:
                for f in cv.link_faces:
                    for x in f.verts:
                        x[ao] = (p["lining_ao"],) * 3 + (1.0,)
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = True
    me.materials.append(mat)
    log(f"lining: {len(nf)} back-facing cloak faces get a flipped copy ({len(is_int)} inside, darkened); "
        f"{nc} cuff cap faces")
    return len(nf)


def _back_visible_near(verts, tris, occluders, eyes_c):
    """Back-side visibility from close viewpoints (players at the glass, 2-8 m away, eye
    heights 1.7-8 m, all round): the far orthographic test misses the inside of the hood
    and the sleeves seen from near the creature. A face counts if a ray from a viewpoint
    to its centre hits it first, from behind."""
    allv, allt, off = [verts], [tris], len(verts)
    for ev, et in occluders:
        allv.append(ev)
        allt.append(et + off)
        off += len(ev)
    av, at = np.concatenate(allv), np.concatenate(allt)
    tree = BVHTree.FromPolygons([tuple(x) for x in av], [tuple(t) for t in at], all_triangles=True)
    fc = verts[tris].mean(1)
    fn = np.cross(verts[tris[:, 1]] - verts[tris[:, 0]], verts[tris[:, 2]] - verts[tris[:, 0]])
    back = np.zeros(len(tris), bool)
    rc = tree.ray_cast
    centre = np.array([eyes_c[0], eyes_c[1] + 0.5, 0.0])
    for rad in (1.5, 2.0, 2.6, 3.5, 5.0, 7.0):
        for hz in (1.7, 3.0, 4.5, 5.5, 6.5, 8.0):
            for k in range(32):
                a = 2 * math.pi * k / 32
                o = centre + np.array([rad * math.sin(a), -rad * math.cos(a), hz])
                d = fc - o
                L = np.linalg.norm(d, axis=1)
                d /= L[:, None]
                cand = np.nonzero((fn * d).sum(1) > 0)[0]     # faces turned away from this viewpoint
                ov = Vector(o.tolist())
                for i in cand:
                    h = rc(ov, Vector(d[i].tolist()), L[i] + 0.01)
                    j = h[2]
                    # whatever is hit first, if it's a cloak face turned away, its back shows
                    if j is not None and j < len(tris) and fn[j] @ d[i] > 0:
                        back[j] = True
    return back


def _eye_tris(eyes):
    """Eyeball spheres as triangles (occluders for the visibility cull)."""
    out_v, out_t = [], []
    for c, R in eyes.values():
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=R * 0.98)
        off = len(out_v)
        out_v += [tuple(np.array(v.co) + c) for v in bm.verts]
        bmesh.ops.triangulate(bm, faces=bm.faces)
        out_t += [tuple(off + v.index for v in f.verts) for f in bm.faces]
        bm.free()
    return np.array(out_v), np.array(out_t)


def _visible_faces(verts, tris, p, extra=()):
    """Faces a player can see: orthographic ray grids from directions all round,
    rejecting views from under the ground; then grown by a couple of rings.
    extra: (verts, tris) occluders that are not tested themselves (the eyeballs)."""
    allv, allt = [verts], [tris]
    off = len(verts)
    for ev, et in extra:
        allv.append(ev)
        allt.append(et + off)
        off += len(ev)
    av, at = np.concatenate(allv), np.concatenate(allt)
    tree = BVHTree.FromPolygons([tuple(x) for x in av], [tuple(t) for t in at], all_triangles=True)
    nreal = len(tris)
    lo, hi = verts.min(0), verts.max(0)
    cen = Vector(((lo + hi) / 2).tolist())
    R = float(np.linalg.norm(hi - lo) / 2) + 0.1
    sp = p["vis_spacing"]
    k = int(R / sp)
    vis = np.zeros(len(tris), bool)
    n = p["vis_dirs"]
    ga = math.pi * (3 - math.sqrt(5))
    rc = tree.ray_cast
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(1 - z * z)
        dd = Vector((r * math.cos(ga * i), r * math.sin(ga * i), z))   # model -> viewer
        if dd.z < -0.97:
            continue
        ray = -dd
        a = dd.orthogonal().normalized()
        b = dd.cross(a).normalized()
        o0 = cen + dd * (R + 1)
        for ii in range(-k, k + 1):
            oi = o0 + a * (ii * sp)
            for jj in range(-k, k + 1):
                hit = rc(oi + b * (jj * sp), ray, 2 * R + 2)
                if hit[2] is None:
                    continue
                # the viewer stands somewhere back along the ray: at 1 m it must be above 0.5 m
                if dd.z < 0 and hit[0].z + dd.z * 1.0 < 0.5:
                    continue
                if hit[2] < nreal:
                    vis[hit[2]] = True
    # grow by rings (vertex-adjacent faces)
    for _ in range(p["vis_grow"]):
        vv = np.zeros(len(verts), bool)
        vv[tris[vis].ravel()] = True
        vis = vis | vv[tris].any(1)
    return vis


def _sample_source_colour(src, points):
    """sRGB colour of the source texture at the surface point nearest each point."""
    me = src.data
    sv, st = _mesh_arrays(me)
    me.calc_loop_triangles()
    lt_loops = np.zeros(len(me.loop_triangles) * 3, np.int64)
    me.loop_triangles.foreach_get("loops", lt_loops)
    uv_all = np.zeros(len(me.loops) * 2)
    me.uv_layers[0].data.foreach_get("uv", uv_all)
    uv = uv_all.reshape(-1, 2)[lt_loops.reshape(-1, 3)]
    img = next(nd.image for m in me.materials for nd in m.node_tree.nodes
               if nd.type == "TEX_IMAGE" and nd.image and nd.image.colorspace_settings.name == "sRGB")
    w, h = img.size
    tex = np.zeros(w * h * 4, np.float32)
    img.pixels.foreach_get(tex)
    tex = tex.reshape(h, w, 4)[..., :3]
    tree = BVHTree.FromPolygons([tuple(x) for x in sv], [tuple(t) for t in st], all_triangles=True)
    idx = np.zeros(len(points), np.int64)
    P_ = np.zeros((len(points), 3))
    fn = tree.find_nearest
    for i, q in enumerate(points):
        loc, _, fi, _ = fn(Vector(q))
        idx[i] = fi
        P_[i] = loc
    a, b, c = sv[st[idx, 0]], sv[st[idx, 1]], sv[st[idx, 2]]
    v0, v1, v2 = b - a, c - a, P_ - a
    d00, d01, d11 = (v0 * v0).sum(1), (v0 * v1).sum(1), (v1 * v1).sum(1)
    d20, d21 = (v2 * v0).sum(1), (v2 * v1).sum(1)
    den = d00 * d11 - d01 * d01 + 1e-20
    w1 = (d11 * d20 - d01 * d21) / den
    w2 = (d00 * d21 - d01 * d20) / den
    w0 = 1 - w1 - w2
    U = uv[idx, 0] * w0[:, None] + uv[idx, 1] * w1[:, None] + uv[idx, 2] * w2[:, None]
    x = np.clip(U[:, 0] * w - 0.5, 0, w - 1).astype(int)
    y = np.clip(U[:, 1] * h - 0.5, 0, h - 1).astype(int)
    return tex[y, x]


def _base_mesh(p, src):
    """Remeshed, visibility-culled source with per-face source colour (cached)."""
    path = os.path.join(PROJECT, p["source"])
    st = os.stat(path)
    key = _hash(st.st_size, int(st.st_mtime), p["height"], p["voxel"], p["pre_ratio"],
                p["vis_dirs"], p["vis_spacing"], p["vis_grow"], "v2")
    cache = os.path.join(CACHE, "base.npz")
    if os.path.exists(cache) and not p["force"]:
        z = np.load(cache)
        if str(z["key"]) == key:
            return z["verts"], z["tris"], z["fcol"]
    t0 = time.time()
    tmp = _object("_grimble_remesh", src.data.copy())
    tmp.data.materials.clear()
    m = tmp.modifiers.new("Remesh", "REMESH")
    m.mode = "VOXEL"
    m.voxel_size = p["voxel"]
    m.adaptivity = 0.0
    d = tmp.modifiers.new("Decimate", "DECIMATE")
    d.ratio = p["pre_ratio"]
    d.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    _remove(tmp)
    verts, tris = _mesh_arrays(me)
    bpy.data.meshes.remove(me)
    log(f"remesh + decimate: {len(tris)} tris ({time.time() - t0:.1f}s)")
    vis = _visible_faces(verts, tris, p)
    tris = tris[vis]
    used = np.unique(tris)
    remap = -np.ones(len(verts), np.int64)
    remap[used] = np.arange(len(used))
    verts, tris = verts[used], remap[tris]
    log(f"visible: {len(tris)} tris ({time.time() - t0:.1f}s)")
    fcol = _sample_source_colour(src, verts[tris].mean(1))
    os.makedirs(CACHE, exist_ok=True)
    np.savez_compressed(cache, key=np.array(key), verts=verts.astype(np.float32),
                        tris=tris.astype(np.int32), fcol=fcol.astype(np.float32))
    log(f"base mesh cached ({time.time() - t0:.1f}s)")
    return verts.astype(np.float32), tris.astype(np.int32), fcol.astype(np.float32)


# ---------------------------------------------------------- landmarks / zones

def _staff_line(p):
    line, s = _catmull(p["staff_path"], 0.02)
    return line, s


def _eye_spheres(p, verts, tris):
    """Eyeball centre and radius per side, seated in the sculpt's sockets."""
    tree = BVHTree.FromPolygons([tuple(x) for x in verts], [tuple(t) for t in tris], all_triangles=True)
    R = p["eye_diameter"] / 2
    out = {}
    for side in ("L", "R"):
        x, z = p["eye_" + side.lower()]
        hits, nrms = [], []
        for dx in np.linspace(-0.12, 0.12, 5):
            for dz in np.linspace(-0.12, 0.12, 5):
                h = tree.ray_cast(Vector((x + dx, -8.0, z + dz)), Vector((0, 1, 0)), 20)
                if h[0] is not None:
                    hits.append(np.array(h[0]))
                    nrms.append(np.array(h[1]))
        hits, nrms = np.array(hits), np.array(nrms)
        centre_hit = hits[len(hits) // 2] if len(hits) else np.array([x, -1.2, z])
        # front of the socket: the frontmost (min y) of the central hits
        front = hits[np.argmin(hits[:, 1])] if len(hits) else centre_hit
        n = nrms.mean(0)
        n /= np.linalg.norm(n)
        # seat the ball along a blend of the socket normal and straight ahead
        axis = n + np.array([0, -1.0, 0])
        axis /= np.linalg.norm(axis)
        surf = np.array([x, front[1], z])
        c = surf - axis * R * (1 - p["eye_proud"])
        out[side] = (c, R)
        EYE_AXES[side] = axis
    return out


def _zones(p, cen):
    fc = np.array(p["face_centre"])
    fr = np.array(p["face_radii"])
    face = (((cen - fc) / fr) ** 2).sum(1) < 1.0
    face &= cen[:, 1] < -0.25
    feet = np.zeros(len(cen), bool)
    for fx, fy in p["feet"]:
        feet |= (np.hypot(cen[:, 0] - fx, cen[:, 1] - fy) < 0.62) & (cen[:, 2] < 0.62)
    line, _ = _staff_line(p)
    ds, ss = _dist_polyline(cen, line)
    hands = (ds < 0.6) & (cen[:, 2] > 3.0) & (cen[:, 2] < 5.6)
    return face, hands, feet, ds


def _classify(p, verts, tris, fcol, eyes):
    cen = verts[tris].mean(1)
    lum = fcol @ np.array([0.2126, 0.7152, 0.0722])
    face, hands, feet, ds = _zones(p, cen)
    hands &= (cen[:, 2] > 3.25) & (cen[:, 2] < 5.3)
    lab = np.full(len(tris), CLOAK, np.int8)
    # inside the face's inner ellipse everything is body (dark sockets, nostrils, the
    # smile line); toward the hood only pale faces are (the hood's lining is dark)
    fc, fr = np.array(p["face_centre"]), np.array(p["face_radii"])
    inner = (((cen - fc) / (fr * 0.62)) ** 2).sum(1) < 1.0
    # the hands wrap the staff: everything that close to it (and not the staff) is hand
    grip = hands & (ds < p["grip_r"])
    body = (face & ((lum > 0.13) | inner)) | (hands & (lum > 0.115)) | grip | (feet & (lum > 0.11))
    lab[body] = BODY
    lab[ds < p["staff_cut"]] = STAFF
    for c, R in eyes.values():
        lab[np.linalg.norm(cen - c, axis=1) < R - 0.01] = EYE
    return lab, (face, hands, feet)


def _face_adjacency(tris):
    """Pairs of faces sharing an edge."""
    e = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    e.sort(1)
    f = np.tile(np.arange(len(tris)), 3)
    key = e[:, 0].astype(np.int64) * (int(tris.max()) + 1) + e[:, 1]
    order = np.argsort(key, kind="stable")
    ks, fs = key[order], f[order]
    same = ks[1:] == ks[:-1]
    return np.stack([fs[:-1][same], fs[1:][same]], 1)


def _components(n, pairs):
    """Connected-component label per item from adjacency pairs (pointer jumping)."""
    L = np.arange(n)
    if len(pairs) == 0:
        return L
    a, b = pairs[:, 0], pairs[:, 1]
    while True:
        la, lb = L[a], L[b]
        m = np.minimum(la, lb)
        changed = (la != lb).any()
        np.minimum.at(L, la, m)
        np.minimum.at(L, lb, m)
        while True:
            L2 = L[L]
            if (L2 == L).all():
                break
            L = L2
        if not changed:
            return L


def _clean_labels(lab, tris, rounds=3, min_island=60):
    pairs = _face_adjacency(tris)
    n = len(tris)
    for _ in range(rounds):
        # majority vote over the 3 edge neighbours + self (body vs cloak only)
        isb = (lab == BODY).astype(np.int32)
        votes = isb.copy()
        cnt = np.ones(n, np.int32)
        np.add.at(votes, pairs[:, 0], isb[pairs[:, 1]])
        np.add.at(votes, pairs[:, 1], isb[pairs[:, 0]])
        np.add.at(cnt, pairs[:, 0], 1)
        np.add.at(cnt, pairs[:, 1], 1)
        flip = lab != STAFF
        lab = np.where(flip & (votes * 2 > cnt), BODY, np.where(flip & (votes * 2 < cnt), CLOAK, lab)).astype(np.int8)
    for _ in range(2):
        same = lab[pairs[:, 0]] == lab[pairs[:, 1]]
        comp = _components(n, pairs[same])
        sizes = np.bincount(comp, minlength=n)
        small = sizes[comp] < min_island
        lab = np.where(small & (lab == BODY), CLOAK, np.where(small & (lab == CLOAK), BODY, lab)).astype(np.int8)
    return lab


# --------------------------------------------------------------- decimation

def _collapse(verts, tris, vweight, ratio):
    """Collapse decimation; vweight (0..1) protects vertices (1 = kept as long as
    anything unprotected is left to collapse)."""
    me = _mesh_from_arrays("_grimble_dec", verts, tris)
    ob = _object("_grimble_dec", me)
    vg = ob.vertex_groups.new(name="protect")
    q = np.round(vweight * 2000).astype(int)
    for val in np.unique(q):
        vg.add(np.nonzero(q == val)[0].tolist(), val / 2000.0, "REPLACE")
    d = ob.modifiers.new("Decimate", "DECIMATE")
    d.ratio = min(1.0, ratio)
    d.use_collapse_triangulate = True
    d.vertex_group = "protect"
    d.invert_vertex_group = True
    d.vertex_group_factor = 1000.0
    dg = bpy.context.evaluated_depsgraph_get()
    nm = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    _remove(ob)
    nv, nt = _mesh_arrays(nm)
    bpy.data.meshes.remove(nm)
    return nv, nt


def _transfer(verts, tris, values, nv, nt):
    """Per-face values onto a new mesh: nearest old face to each new face centre."""
    tree = BVHTree.FromPolygons([tuple(x) for x in verts], [tuple(t) for t in tris], all_triangles=True)
    fnn = tree.find_nearest
    idx = np.array([fnn(Vector(c))[2] for c in nv[nt].mean(1)])
    return [v[idx] for v in values]


def _vertex_max(nverts, tris, w):
    vw = np.zeros(nverts)
    for k in range(3):
        np.maximum.at(vw, tris[:, k], w)
    return vw


def _decimate(p, verts, tris, lab, zones):
    """Two collapse passes on the joined body + cloak so their seam stays shared
    (no cracks): 1) the cloak (and the seam) down to its budget, body locked;
    2) the body down to its budget, cloak and seam locked. Within a pass, small
    weights steer where triangles go (the face keeps most; the cloak's back
    least). Returns verts, tris and labels."""
    pr = p["protect"]
    face, hands, feet = zones
    zone = np.where(face, 1, np.where(hands, 2, np.where(feet, 3, 0))).astype(np.int8)

    def normals(v, t):
        fn = np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]])
        return fn / (np.linalg.norm(fn, axis=1, keepdims=True) + 1e-12)

    # pass 1: cloak
    fn = normals(verts, tris)
    is_body = lab == BODY
    w = np.where(fn[:, 1] > 0.2, pr["cloak_back"], pr["cloak_front"])
    vw = _vertex_max(len(verts), tris, np.where(is_body, 0.0, w))
    cloak_v = _vertex_max(len(verts), tris, (~is_body).astype(float)) > 0
    body_v = _vertex_max(len(verts), tris, is_body.astype(float)) > 0
    vw[body_v & ~cloak_v] = 1.0                        # body interior locked
    ratio = (is_body.sum() + p["tris_cloak"]) / len(tris)
    v1, t1 = _collapse(verts, tris, vw, ratio)
    lab1, zone1 = _transfer(verts, tris, (lab, zone), v1, t1)
    # pass 2: body
    is_body = lab1 == BODY
    w = np.select([zone1 == 1, zone1 == 2, zone1 == 3], [pr["face"], pr["hands"], pr["feet"]], 0.0)
    vw = _vertex_max(len(v1), t1, np.where(is_body, w, 0.0))
    cloak_v = _vertex_max(len(v1), t1, (~is_body).astype(float)) > 0
    vw[cloak_v] = 1.0                                  # cloak and seam locked
    ratio = ((~is_body).sum() + p["tris_body"]) / len(t1)
    v2, t2 = _collapse(v1, t1, vw, ratio)
    (lab2,) = _transfer(v1, t1, (lab1,), v2, t2)
    return v2, t2, lab2


# ------------------------------------------------------------------ parts

def _part_object(name, verts, tris, mask, col, root):
    t = tris[mask]
    used = np.unique(t)
    remap = -np.ones(len(verts), np.int64)
    remap[used] = np.arange(len(used))
    me = _mesh_from_arrays(name, verts[used], remap[t])
    for poly in me.polygons:
        poly.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    ob.parent = root
    return ob


def _fill_holes(verts, tris, lab, eyes, max_sides=48, zip_dist=0.02, caps=()):
    """Close small holes and slits (creases the visibility culls missed, sculpt
    holes): first zip cracks (weld boundary vertices a couple of cm apart), then
    walk every open boundary cycle (directed, so bow-tie vertices are fine) and fan
    each one of up to max_sides edges to its centroid; the eye sockets (up to 400
    edges) are capped too, behind the eyeballs, so there's no see-through gap where
    the lid is wider than the eyeball. New faces take the label of the face they border."""
    bm = bmesh.new()
    vs = [bm.verts.new(tuple(x)) for x in verts]
    for k, t in enumerate(tris):
        try:
            f = bm.faces.new((vs[t[0]], vs[t[1]], vs[t[2]]))
            f.material_index = int(lab[k])
        except ValueError:
            pass
    bverts = list({v for e in bm.edges if e.is_boundary for v in e.verts})
    near_eye = [v for v in bverts if any(np.linalg.norm(np.array(v.co) - ec) < 0.6 for ec, _ in eyes.values())]
    bmesh.ops.remove_doubles(bm, verts=near_eye, dist=zip_dist * 1.75)   # cracks around the eyes and nose
    bverts = list({v for e in bm.edges if e.is_boundary for v in e.verts})
    bmesh.ops.remove_doubles(bm, verts=bverts, dist=zip_dist)
    for f in [f for f in bm.faces if f.calc_area() < 1e-9]:
        bm.faces.remove(f)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.verts.index_update()
    nv = np.array([v.co[:] for v in bm.verts])
    nt = np.array([[v.index for v in f.verts] for f in bm.faces], np.int64)
    nl = np.array([f.material_index for f in bm.faces], np.int8)
    bm.free()
    nv, nt, nl, nh = _fan_fill(nv, nt, nl, eyes, max_sides, caps)
    log(f"filled {nh} holes")
    return nv, nt, nl


FAN_CENTRES = []      # centres of the fans made by the last _fan_fill call


def _remove_fins(verts, tris, keep_mask=None):
    """Edges shared by 3+ triangles (fins the remesh and the fills leave): keep the two
    largest faces on each, drop the rest, so every hole's rim becomes a closed loop.
    Returns the boolean mask of triangles to keep."""
    keep = np.ones(len(tris), bool) if keep_mask is None else keep_mask.copy()
    area = 0.5 * np.linalg.norm(np.cross(verts[tris[:, 1]] - verts[tris[:, 0]],
                                         verts[tris[:, 2]] - verts[tris[:, 0]]), axis=1)
    for _ in range(3):
        idx = np.nonzero(keep)[0]
        e = np.sort(np.concatenate([tris[idx][:, [0, 1]], tris[idx][:, [1, 2]], tris[idx][:, [2, 0]]]), 1)
        f = np.tile(idx, 3)
        key = e[:, 0] * (len(verts) + 1) + e[:, 1]
        u, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
        bad = np.nonzero(cnt > 2)[0]
        if not len(bad):
            break
        for b in bad:
            fs = f[inv == b]
            for fi in fs[np.argsort(-area[fs])][2:]:
                keep[fi] = False
    return keep


def _fan_fill(nv, nt, nl, eyes, max_sides=48, caps=(), max_perim=None, keep=None, keep_frac=0.0):
    """Fan every open boundary cycle of up to max_sides edges (600 at the eye sockets
    and the given caps) to its centroid; walking directed half-edges, so bow-tie
    vertices are fine. New faces take the label of the face they border."""
    # open edges (used by one triangle), walked as an undirected graph: a neighbouring
    # triangle with flipped winding would break a directed walk. Each fan triangle takes
    # the winding opposite to its rim edge in the triangle it borders.
    he = np.concatenate([nt[:, [0, 1]], nt[:, [1, 2]], nt[:, [2, 0]]])
    owner = np.tile(np.arange(len(nt)), 3)
    und = np.sort(he, 1)
    ukey = und[:, 0] * (len(nv) + 1) + und[:, 1]
    _, inv, cnt = np.unique(ukey, return_inverse=True, return_counts=True)
    open_ = np.nonzero(cnt[inv] == 1)[0]
    adj, edir = {}, {}
    for k in open_:
        a_, b_ = int(he[k, 0]), int(he[k, 1])
        adj.setdefault(a_, []).append(b_)
        adj.setdefault(b_, []).append(a_)
        edir[(a_, b_)] = int(owner[k])                # the owner triangle has a_ -> b_
    used = set()
    new_v, new_t, new_l = [], [], []
    for start in list(adj.keys()):
        for first in list(adj[start]):
            if (min(start, first), max(start, first)) in used:
                continue
            cyc, prev, cur = [start], start, first
            used.add((min(start, first), max(start, first)))
            ok = False
            while len(cyc) <= 600:
                if cur == start:
                    ok = True
                    break
                cyc.append(cur)
                nxt_ = [x for x in adj[cur] if (min(cur, x), max(cur, x)) not in used]
                if not nxt_:
                    break
                nx = nxt_[0]
                used.add((min(cur, nx), max(cur, nx)))
                prev, cur = cur, nx
            if not ok or len(cyc) < 3:
                continue
            c = nv[cyc].mean(0)
            socket = any(np.linalg.norm(c - ec) < R * 1.6 for ec, R in eyes.values())
            socket |= any(np.linalg.norm(c - cc) < cr for cc, cr in caps)
            if len(cyc) > (600 if socket else max_sides):
                continue
            if keep is not None and keep[cyc].mean() > keep_frac:   # mostly a seam with another part
                continue
            if max_perim is not None and not socket:
                per = np.linalg.norm(np.diff(nv[cyc + cyc[:1]], axis=0), axis=1).sum()
                if per > max_perim:
                    continue
            ci = len(nv) + len(new_v)
            new_v.append(c)
            for i in range(len(cyc)):
                a_, b_ = cyc[i], cyc[(i + 1) % len(cyc)]
                if (a_, b_) in edir:                       # owner has a_ -> b_: the fan goes b_ -> a_
                    new_t.append((b_, a_, ci))
                    new_l.append(nl[edir[(a_, b_)]])
                else:
                    new_t.append((a_, b_, ci))
                    new_l.append(nl[edir.get((b_, a_), 0)])
    FAN_CENTRES[:] = [np.array(x) for x in new_v]
    if new_v:
        nv = np.concatenate([nv, np.array(new_v)])
        nt = np.concatenate([nt, np.array(new_t, np.int64)])
        nl = np.concatenate([nl, np.array(new_l, np.int8)])
    return nv, nt, nl, len(new_v)



def _fill_enclosed(tris, lab):
    """Cloak islands enclosed by body (dark patches inside the face: sockets,
    crevices, the sculpt's shading) become body; the main cloak and loose cloth
    pieces (not bordered by body) stay cloak."""
    pairs = _face_adjacency(tris)
    isc = lab == CLOAK
    same = isc[pairs[:, 0]] & isc[pairs[:, 1]]
    comp = _components(len(tris), pairs[same])
    sizes = np.bincount(comp, minlength=len(tris))
    main = np.argmax(np.where(isc, sizes[comp], 0))
    main = comp[main]
    # per cloak component: edges to body vs. all its edges to other faces
    mixed = isc[pairs[:, 0]] != isc[pairs[:, 1]]
    cpair = np.where(isc[pairs[:, 0]], comp[pairs[:, 0]], comp[pairs[:, 1]])
    to_body = np.bincount(cpair[mixed & (np.where(isc[pairs[:, 0]], lab[pairs[:, 1]], lab[pairs[:, 0]]) == BODY)],
                          minlength=len(tris))
    # open boundary edges of each component (edges used by one face) count against
    e = np.sort(np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]]), 1)
    key = e[:, 0] * (int(tris.max()) + 1) + e[:, 1]
    u, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
    open_f = np.tile(np.arange(len(tris)), 3)[cnt[inv] == 1]
    opened = np.bincount(comp[open_f[isc[open_f]]], minlength=len(tris))
    flip = isc & (comp != main) & (to_body[comp] > 2 * opened[comp])
    out = lab.copy()
    out[flip] = BODY
    return out


def _keep_body_parts(p, verts, tris, lab):
    """Body = the face, the two hands and the two feet (the largest body components
    in each zone); stray pale patches (dust on the hood lining, the hem) become cloak."""
    idx = np.nonzero(lab == BODY)[0]
    bt = tris[idx]
    comp = _components(len(bt), _face_adjacency(bt))
    face, hands, feet, _ = _zones(p, verts[bt].mean(1))
    keep = np.zeros(len(bt), bool)
    for zone, count in ((face, 1), (hands, 2), (feet, 2)):
        ids, sizes = np.unique(comp[zone], return_counts=True)
        for ci in ids[np.argsort(-sizes)][:count]:
            keep |= comp == ci
    out = lab.copy()
    out[idx[~keep]] = CLOAK
    return out


def _extract_hands(p, verts, tris, lab):
    """Find the sculpt's two hands (body components gripping the staff), describe
    each grip (arc length on the staff, span, wrist point in the sleeve) and remove
    their faces; the rebuilt hands replace them."""
    idx = np.nonzero(lab == BODY)[0]
    bt = tris[idx]
    comp = _components(len(bt), _face_adjacency(bt))
    cen = verts[bt].mean(1)
    line, sl = _staff_line(p)
    ds, ss = _dist_polyline(cen, line)
    in_hand = (ds < 0.6) & (cen[:, 2] > 3.0) & (cen[:, 2] < 5.6)
    ids, sizes = np.unique(comp[in_hand], return_counts=True)
    cloak_v = np.zeros(len(verts), bool)
    cloak_v[tris[lab == CLOAK].ravel()] = True
    hands, drop = [], np.zeros(len(tris), bool)
    for ci in ids[np.argsort(-sizes)][:2]:
        m = comp == ci
        hv = np.unique(bt[m])
        seam = hv[cloak_v[hv]]
        near = m & (ds < 0.35)
        s_c = float(np.median(ss[near])) if near.any() else float(np.median(ss[m]))
        wrist = verts[seam].mean(0) if len(seam) else verts[hv].mean(0)
        hands.append(dict(s=s_c, wrist=wrist))
        drop[idx[m]] = True
    hands.sort(key=lambda h: -h["s"])
    log("hands: " + ", ".join(f"grip s={h['s']:.2f} wrist {np.round(h['wrist'], 2)}" for h in hands))
    return hands, drop


def _face_frame(eyes):
    """The face projection's frame: centre inside the head, axes a (eye line),
    b (up), f (forward)."""
    cl, cr = eyes["L"][0], eyes["R"][0]
    a = (cl - cr) / np.linalg.norm(cl - cr)
    f = np.array([0, -1.0, 0]) - a * (-a[1])
    f /= np.linalg.norm(f)
    b = np.cross(f, a)
    return (cl + cr) / 2 - f * 0.75 - b * 0.35, a, b, f


def _drop_inward_faces(body, eyes, p):
    """The sculpt's folded skin in the face (slivers facing back into the head beside
    the nose and on the cheeks) reads as dark cracks: delete it; the face backing
    behind shows fur there instead."""
    me = body.data
    c, a, b, f = _face_frame(eyes)
    fc, fr = np.array(p["face_centre"]), np.array(p["face_radii"])
    bm = bmesh.new()
    bm.from_mesh(me)
    kill = []
    for fa in bm.faces:
        q = np.array(fa.calc_center_median())
        if (((q - fc) / (fr * 0.8)) ** 2).sum() > 1.0 or q[1] > -0.6:
            continue
        if any(np.linalg.norm(q - ec) < R * 1.3 for ec, R in eyes.values()):
            continue
        d = q - c
        d /= np.linalg.norm(d)
        if np.array(fa.normal) @ d < -0.05:
            kill.append(fa)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(me)
    bm.free()
    return len(kill)


def _smooth_parts(ob, zone_fn, iters=6, lam=0.5):
    """Tidy the sculpt's lumpy hands: Laplacian smoothing of the hands' interior
    vertices (their seam with the sleeves stays put, so nothing cracks)."""
    me = ob.data
    v, t = _mesh_arrays(me)
    sel = zone_fn(v)
    q = _smoothed(v, t, iters, lam)
    v = np.where(sel[:, None], q, v)
    me.vertices.foreach_set("co", v.astype(np.float32).ravel())
    me.update()


def _remove_floaters(verts, tris, keep_min=40):
    pairs = _face_adjacency(tris)
    comp = _components(len(tris), pairs)
    sizes = np.bincount(comp, minlength=len(tris))
    return sizes[comp] >= keep_min


def _select_only(ob):
    vl = bpy.context.view_layer
    for o in vl.objects.selected:
        o.select_set(False)
    vl.objects.active = ob
    ob.select_set(True)


def _lambert(v, centre, a, b, f):
    """Lambert azimuthal equal-area projection of the directions from `centre`,
    centred on axis f (a, b span the image plane)."""
    d = v - centre
    d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-12
    x, y, z = d @ a, d @ b, d @ f
    k = np.sqrt(2 / np.maximum(1 + z, 1e-4))
    return np.stack([k * x, k * y], 1)


def _smoothed(v, tris, iters, lam=0.6):
    """Laplacian-smoothed copy of the vertex positions (open boundaries pinned)."""
    e = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    key = np.sort(e, 1)
    k = key[:, 0] * (len(v) + 1) + key[:, 1]
    u, cnt = np.unique(k, return_counts=True)
    bnd_e = u[cnt == 1]
    pinned = np.zeros(len(v), bool)
    pinned[(bnd_e // (len(v) + 1)).astype(np.int64)] = True
    pinned[(bnd_e % (len(v) + 1)).astype(np.int64)] = True
    e = np.concatenate([e, e[:, ::-1]])
    deg = np.maximum(np.bincount(e[:, 0], minlength=len(v)), 1)[:, None]
    q = v.copy()
    for _ in range(iters):
        acc = np.zeros_like(q)
        np.add.at(acc, e[:, 0], q[e[:, 1]])
        q = np.where(pinned[:, None], q, q + lam * (acc / deg - q))
    return q


def _uv_body(ob, face_mask, p, eyes):
    """One island per body part. The sculpt's skin is full of tiny voxel tunnels
    (the face has genus ~30), so a disc unwrap fails and smart project shatters it;
    instead each part gets a Lambert equal-area projection of the directions from a
    point inside it: the face from inside the head along its forward axis (so the
    texture reads like the face), each hand / foot from its centroid along its mean
    normal. The face island is scaled for extra texel density, then all are packed."""
    me = ob.data
    if "UVMap" not in me.uv_layers:
        me.uv_layers.new(name="UVMap")
    v, t = _mesh_arrays(me)
    comp = _components(len(t), _face_adjacency(t))
    li = np.zeros(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", li)
    ls = np.zeros(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_start", ls)
    uv = np.zeros((len(me.loops), 2))
    fn = np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]])
    area = 0.5 * np.linalg.norm(fn, axis=1)
    cl, cr = eyes["L"][0], eyes["R"][0]
    folded = np.zeros(len(t), bool)
    face_info = None
    for ci in np.unique(comp):
        m = comp == ci
        is_face = face_mask[m].mean() > 0.5
        if is_face:
            centre, a, b, f = _face_frame(eyes)
        else:
            f = fn[m].sum(0)
            f /= np.linalg.norm(f)
            a = np.cross(f, [0, 0, 1.0]) if abs(f[2]) < 0.9 else np.cross(f, [1.0, 0, 0])
            a /= np.linalg.norm(a)
            b = np.cross(f, a)
            centre = (v[t[m]].reshape(-1, 3) * np.repeat(area[m], 3)[:, None]).sum(0) / (3 * area[m].sum())
        tri_ids = np.nonzero(m)[0]
        corners = (ls[tri_ids][:, None] + np.arange(3)[None, :]).ravel()
        cv = np.unique(t[m])
        remap = -np.ones(len(v), np.int64)
        remap[cv] = np.arange(len(cv))
        vs_ = _smoothed(v[cv], remap[t[m]], p["uv_smooth"])
        hand = (not is_face) and 3.0 < centre[2] < 5.6
        qv = _lambert(vs_, centre, a, b, f)
        q = qv[remap[li[corners]]].reshape(-1, 3, 2)
        # folded triangles (hidden inner layers of the voxel shell, socket walls) would
        # overwrite visible texels in the bakes: collapse each to its own centroid, so it
        # takes the colour of the surface in front of it and bakes nothing
        e1, e2 = q[:, 1] - q[:, 0], q[:, 2] - q[:, 0]
        sa = e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]
        bad = sa * np.sign(sa.sum()) <= 0
        # inner layers: triangles behind another surface of the same part along their
        # projection ray (they'd share texels with the visible surface)
        ctr = v[t[m]].mean(1)
        tree = BVHTree.FromPolygons([tuple(x) for x in v[cv]], [tuple(x) for x in remap[t[m]]], all_triangles=True)
        for k, cpt in enumerate(ctr):
            if bad[k]:
                continue
            dvec = cpt - centre
            dvec /= np.linalg.norm(dvec)
            hit = tree.ray_cast(Vector((cpt + dvec * 0.004).tolist()), Vector(dvec.tolist()), 3.0)
            if hit[2] is not None:
                bad[k] = True
        folded[tri_ids[bad]] = True
        log(f"  uv part ({'face' if is_face else 'hand' if hand else 'foot'}, {m.sum()} tris): "
            f"{bad.sum()} folded / hidden")
        q = q.reshape(-1, 2)
        # density: uv area per 3D area -> 1 (then the face gets its boost)
        e1, e2 = q.reshape(-1, 3, 2)[:, 1] - q.reshape(-1, 3, 2)[:, 0], q.reshape(-1, 3, 2)[:, 2] - q.reshape(-1, 3, 2)[:, 0]
        a2 = 0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]).sum()
        scale = math.sqrt(area[m].sum() / max(a2, 1e-12)) * (p["face_texel_boost"] if is_face else 1.0)
        qmin = q.min(0)
        q = (q - qmin) * scale
        uv[corners] = q
        if is_face and (face_info is None or m.sum() > face_info["n"]):
            face_info = dict(n=int(m.sum()), centre=centre, a=a, b=b, f=f, qmin=qmin, scale=scale,
                             corners=corners, pre=q.copy(), good=~np.repeat(bad, 3))
    me.uv_layers["UVMap"].data.foreach_set("uv", uv.ravel())
    pre = uv.copy()
    _select_only(ob)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")
    ob.select_set(False)
    # keep every island 2% away from the atlas border: the sampler repeats, so texels at
    # the very edge were filtered with the opposite edge (pale flecks at the hood rim)
    uvs = np.zeros(len(me.loops) * 2)
    me.uv_layers["UVMap"].data.foreach_get("uv", uvs)
    me.uv_layers["UVMap"].data.foreach_set("uv", (0.5 + (uvs - 0.5) * 0.96))
    # folded triangles (hidden inner layers of the voxel shell, socket walls) would
    # overwrite visible texels in the bakes: after packing, each is shrunk into its
    # nearest unfolded neighbour's texels, so it takes that colour and bakes nothing
    uv = np.zeros(len(me.loops) * 2)
    me.uv_layers["UVMap"].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    # the packing's affine per part: maps every corner's projected UV into the packed atlas
    # (used afterwards to give the folded triangles continuous UVs again)
    corner_part = np.zeros(len(me.loops), np.int64)
    corner_part[(ls[:, None] + np.arange(3)[None, :]).ravel()] = np.repeat(comp, 3)
    good_c = np.zeros(len(me.loops), bool)
    good_c[(ls[~folded][:, None] + np.arange(3)[None, :]).ravel()] = True
    natural = uv.copy()
    for ci in np.unique(comp):
        sel = corner_part == ci
        g = sel & good_c
        if g.sum() < 3:
            continue
        Mp = np.linalg.lstsq(np.c_[pre[g], np.ones(g.sum())], uv[g], rcond=None)[0]
        natural[sel] = np.c_[pre[sel], np.ones(sel.sum())] @ Mp
    fold_c = (ls[folded][:, None] + np.arange(3)[None, :]).ravel()
    if face_info is not None:   # the packing's transform of the face island (for the backing)
        g = face_info["good"]
        X = np.c_[face_info["pre"][g], np.ones(g.sum())]
        face_info["M"] = np.linalg.lstsq(X, uv[face_info["corners"][g]], rcond=None)[0]
    # each collapsed triangle takes the texels of its nearest unfolded neighbour along
    # the surface (a breadth-first walk over shared edges: a 3D-nearest pick can jump
    # across a socket to a dark-painted lid)
    src_face = np.where(folded, -1, np.arange(len(t)))
    pairs = _face_adjacency(t)
    for _ in range(60):
        miss = src_face < 0
        if not miss.any():
            break
        for x, y in ((0, 1), (1, 0)):
            m_ = miss[pairs[:, x]] & (src_face[pairs[:, y]] >= 0)
            src_face[pairs[m_, x]] = src_face[pairs[m_, y]]
    def _sarea(q):
        return (q[1, 0] - q[0, 0]) * (q[2, 1] - q[0, 1]) - (q[1, 1] - q[0, 1]) * (q[2, 0] - q[0, 0])
    good_sign = np.sign(sum(_sarea(uv[ls[k] + np.arange(3)]) for k in np.nonzero(~folded)[0][:2000]))
    for ti in np.nonzero(folded)[0]:
        gi = src_face[ti]
        if gi < 0:
            continue
        c = ls[ti] + np.arange(3)
        # a shrunken copy of the neighbour's UV triangle (not a point: a zero-area UV
        # triangle has no tangent frame, and normal mapping shades it black), wound like
        # the rest of the island (a mirrored tangent frame shades dark too)
        nuv = uv[ls[gi] + np.arange(3)]
        q = nuv.mean(0) + (nuv - nuv.mean(0)) * 0.3
        if np.sign(_sarea(q)) != good_sign:
            q = q[[0, 2, 1]]
        uv[c] = q
    me.uv_layers["UVMap"].data.foreach_set("uv", uv.ravel())
    log(f"body uv: {len(np.unique(comp))} parts, {folded.sum()} folded / hidden triangles collapsed")
    face_info["restore"] = (fold_c, natural[fold_c])
    return face_info


def _face_backing(body, info, eyes, p):
    """A hole-free shell a few cm behind the face's fur (star-shaped about the face
    projection's centre, so it can't have cracks), textured from the face island at
    the same projected direction: the sculpt's hairline cracks and creases show fur
    in shadow instead of the hood's dark inside. Appended to the body mesh."""
    me = body.data
    v, t = _mesh_arrays(me)
    allv, allt = [v], [t]
    off = len(v)
    ev, et = _eye_tris(eyes)
    tree = BVHTree.FromPolygons([tuple(x) for x in np.concatenate([v, ev])],
                                [tuple(x) for x in np.concatenate([t, et + off])], all_triangles=True)
    c, a, b, f = info["centre"], info["a"], info["b"], info["f"]
    nr, na = p["backing_steps"]
    amax = math.radians(p["backing_max_angle"])
    al = np.linspace(0, amax, nr + 1)[1:]
    az = np.linspace(0, 2 * math.pi, na, endpoint=False)
    dist = np.full((nr, na), np.nan)
    dirs = np.zeros((nr, na, 3))
    for i, A_ in enumerate(al):
        for j, Z in enumerate(az):
            d = math.cos(A_) * f + math.sin(A_) * (math.cos(Z) * a + math.sin(Z) * b)
            dirs[i, j] = d
            h = tree.ray_cast(Vector(c.tolist()), Vector(d.tolist()), 3.0)
            if h[0] is not None:
                dist[i, j] = h[3]
    cen_d = tree.ray_cast(Vector(c.tolist()), Vector(f.tolist()), 3.0)[3] or np.nanmin(dist)
    # stay behind the surface between rays too: min over each 3x3 neighbourhood, minus the inset
    filled = np.where(np.isnan(dist), np.inf, dist)
    pad = np.concatenate([filled[:, -1:], filled, filled[:, :1]], 1)
    pad = np.concatenate([np.full((1, na + 2), cen_d), pad, pad[-1:]], 0)
    mn = np.min([pad[1 + di:1 + di + nr, 1 + dj:1 + dj + na] for di in (-1, 0, 1) for dj in (-1, 0, 1)], axis=0)
    r = mn - p["backing_inset"]
    ok = np.isfinite(r) & ~np.isnan(dist)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    M = info["M"]

    def uv_of(pt):
        q = _lambert(pt[None], c, a, b, f)[0]
        q = (q - info["qmin"]) * info["scale"]
        return np.r_[q, 1] @ M

    apex = bm.verts.new(tuple(c + f * (cen_d - p["backing_inset"])))
    grid = [[bm.verts.new(tuple(c + dirs[i, j] * r[i, j])) if ok[i, j] else None for j in range(na)] for i in range(nr)]
    faces = []
    for j in range(na):
        j2 = (j + 1) % na
        if grid[0][j] and grid[0][j2]:
            faces.append((apex, grid[0][j], grid[0][j2]))
    for i in range(nr - 1):
        for j in range(na):
            j2 = (j + 1) % na
            q = [grid[i][j], grid[i + 1][j], grid[i + 1][j2], grid[i][j2]]
            if all(q):
                faces.append((q[0], q[1], q[2]))
                faces.append((q[0], q[2], q[3]))
    for fv in faces:
        fa = bm.faces.new(fv)
        fa.smooth = True
        for l in fa.loops:
            l[uvl].uv = tuple(uv_of(np.array(l.vert.co)))
    bm.normal_update()
    # the shell faces the viewer (outward from the centre)
    for fa in bm.faces:
        if fa.normal.dot(Vector((np.array(fa.calc_center_median()) - c).tolist())) < 0:
            fa.normal_flip()
    loose = [x for x in bm.verts if not x.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    # append to the body
    tmp = bpy.data.meshes.new("_backing")
    bm.to_mesh(tmp)
    bm.free()
    bb = bmesh.new()
    bb.from_mesh(me)
    bb.from_mesh(tmp)
    bb.to_mesh(me)
    bb.free()
    bpy.data.meshes.remove(tmp)
    for poly in me.polygons:
        poly.use_smooth = True
    return int(len(faces))


def _uv_wrap(ob, tile, eyes):
    """Continuous world-scale UVs for the cloak: u = angle round a vertical axis (the
    body's, blending into the head's toward the hood) x the local radius, v = height
    minus half the radial distance (so horizontal shoulders and the hood's top still
    get texture). One seam, down the back. (Smart project cut the noisy drape into
    thousands of islands: 40% of its edges were UV seams, and three.js, which builds
    normal-map tangents from screen-space UV derivatives when the glTF has none, draws
    a bright speck along every seam.)"""
    me = ob.data
    if "UVMap" not in me.uv_layers:
        me.uv_layers.new(name="UVMap")
    v, _ = _mesh_arrays(me)
    head = (eyes["L"][0] + eyes["R"][0]) / 2 + np.array([0, 0.6, 0])
    body = np.array([-0.1, 0.25])
    k = np.clip((v[:, 2] - 4.4) / 1.0, 0, 1)[:, None]
    axis = body * (1 - k) + head[:2] * k
    d = v[:, :2] - axis
    rho = np.linalg.norm(d, axis=1)
    th = np.arctan2(d[:, 0], -d[:, 1])        # 0 at the front (-Y), +-pi at the back
    # the local circumference scale: median radius per height band (smoothed)
    zb = np.clip((v[:, 2] / 0.5).astype(int), 0, 20)
    med = np.array([np.median(rho[zb == b]) if (zb == b).any() else 1.0 for b in range(21)])
    med = np.convolve(np.pad(med, 1, mode="edge"), np.ones(3) / 3, mode="valid")
    R = np.maximum(med[zb], 0.4)
    # a whole number of tiles round: the back seam matches (one constant circumference;
    # the weave runs a little finer on the hood, coarser at the hem)
    n_round = max(1, round(2 * math.pi * float(np.median(rho)) / tile))
    li = np.zeros(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", li)
    uv = np.zeros((len(me.loops), 2))
    for poly in me.polygons:
        ls = list(poly.loop_indices)
        t = th[li[ls]]
        if t.max() - t.min() > math.pi:       # straddles the back seam: unwrap
            t = np.where(t < 0, t + 2 * math.pi, t)
        vi = li[ls]
        uv[ls, 0] = t / (2 * math.pi) * n_round
        uv[ls, 1] = (v[vi, 2] - 0.5 * rho[vi]) / tile
    me.uv_layers["UVMap"].data.foreach_set("uv", uv.ravel())


def _darken_lining(ob, eyes, amount, cuffs=()):
    """Multiply the 'AO' colour of vertices whose normal faces the creature's core (a
    vertical axis through the body, blending into the head's centre toward the hood)."""
    me = ob.data
    attr = me.color_attributes.get(vertex_ao.ATTR)
    if attr is None:
        return 0
    v = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", v)
    v = v.reshape(-1, 3)
    nrm = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("normal", nrm)
    nrm = nrm.reshape(-1, 3)
    head = (eyes["L"][0] + eyes["R"][0]) / 2 + np.array([0, 0.6, 0])
    k = np.clip((v[:, 2] - 4.6) / 0.8, 0, 1)[:, None]
    core = np.c_[np.full(len(v), -0.1), np.full(len(v), 0.25), v[:, 2]] * (1 - k) + head * k
    d = core - v
    d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9
    inward = (nrm * d).sum(1)
    f = 1 - amount * np.clip((inward - 0.0) / 0.4, 0, 1)
    # the cloth's rims and fold creases: the remeshed cloth is a thin closed shell, so every
    # edge is a 2 cm tube whose normals sweep round and catch the sun -> darken by curvature
    e = np.zeros(len(me.edges) * 2, np.int64)
    me.edges.foreach_get("vertices", e)
    e = e.reshape(-1, 2)
    bend = 1 - (nrm[e[:, 0]] * nrm[e[:, 1]]).sum(1)
    curv = np.zeros(len(v))
    np.maximum.at(curv, e[:, 0], bend)
    np.maximum.at(curv, e[:, 1], bend)
    lo, hi = np.percentile(curv, 85), np.percentile(curv, 97)
    f *= 1 - 0.6 * np.clip((curv - lo) / max(hi - lo, 1e-6), 0, 1)
    # the sleeve cuffs' caps (where the sculpt's hands were): the inside of the sleeve
    for c in cuffs:
        f *= 1 - 0.7 * np.clip(1 - np.linalg.norm(v - c, axis=1) / 0.45, 0, 1)
    # blur over the surface so the rims get a soft dark band, not light-and-dark patches
    ee = np.concatenate([e, e[:, ::-1]])
    deg = np.maximum(np.bincount(ee[:, 0], minlength=len(v)), 1)
    for _ in range(4):
        acc = np.zeros(len(v))
        np.add.at(acc, ee[:, 0], f[ee[:, 1]])
        f = 0.5 * f + 0.5 * acc / deg
    ao = np.zeros(len(attr.data) * 4, np.float32)
    attr.data.foreach_get("color", ao)
    ao = ao.reshape(-1, 4)
    ao[:, :3] *= f[:, None]
    attr.data.foreach_set("color", ao.ravel())
    log(f"lining / rims darkened: {(f < 0.9).sum()} of {len(f)} cloak vertices")
    return int((f < 0.9).sum())


def _uv_world(ob, tile):
    """Smart-project UVs rescaled so 1 UV unit = `tile` metres (for tiling textures)."""
    me = ob.data
    if "UVMap" not in me.uv_layers:
        me.uv_layers.new(name="UVMap")
    _select_only(ob)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.001, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    ob.select_set(False)
    v, _ = _mesh_arrays(me)
    uv = np.zeros(len(me.loops) * 2)
    me.uv_layers["UVMap"].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    li = np.zeros(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", li)
    a3 = a2 = 0.0
    for poly in me.polygons:
        ls = list(poly.loop_indices)
        p3 = v[li[ls]]
        p2 = uv[ls]
        for k in range(1, len(ls) - 1):
            a3 += 0.5 * np.linalg.norm(np.cross(p3[k] - p3[0], p3[k + 1] - p3[0]))
            e1, e2 = p2[k] - p2[0], p2[k + 1] - p2[0]
            a2 += 0.5 * abs(e1[0] * e2[1] - e1[1] * e2[0])
    scale = math.sqrt(a3 / max(a2, 1e-12)) / tile
    me.uv_layers["UVMap"].data.foreach_set("uv", (uv * scale).ravel())


# ------------------------------------------------------------------ baking

def _cycles(scene, samples):
    scene.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        scene.cycles.device = "GPU"
    except (TypeError, KeyError, AttributeError):
        pass
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False


def _bake_image(name, size, float_buffer=True):
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)
    return bpy.data.images.new(name, size, size, alpha=False, float_buffer=float_buffer)


def _pixels(img):
    w, h = img.size
    a = np.zeros(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(h, w, 4)[::-1, :, :3].copy()      # row 0 = top (v = 1)


def _bake_material(name, kind, img):
    """Temporary bake material: kind 'target' (just the image node), 'position',
    'normal' (emission of the geometry's position / smooth normal)."""
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    nt = m.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    if kind in ("position", "normal"):
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        em = nt.nodes.new("ShaderNodeEmission")
        nt.links.new(geo.outputs["Position" if kind == "position" else "Normal"], em.inputs["Color"])
        nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.nodes.active = tex
    return m


def _bake(target, img, kind, sources=(), bake_type="EMIT", margin=24, extrusion=0.06, ray=0.25, **kw):
    me = target.data
    saved = list(me.materials)
    me.materials.clear()
    me.materials.append(_bake_material("_bake_" + kind, kind, img))
    vl = bpy.context.view_layer
    for o in vl.objects.selected:
        o.select_set(False)
    for s in sources:
        s.select_set(True)
    target.select_set(True)
    vl.objects.active = target
    bpy.ops.object.bake(type=bake_type, use_selected_to_active=bool(sources), cage_extrusion=extrusion,
                        max_ray_distance=ray, margin=margin, margin_type="EXTEND", use_clear=True,
                        target="IMAGE_TEXTURES", **kw)
    m = me.materials[0]
    me.materials.clear()
    for s in saved:
        me.materials.append(s)
    bpy.data.materials.remove(m)
    for o in vl.objects.selected:
        o.select_set(False)


def _body_bakes(p, body, src, hires):
    """Source colour, high-res tangent normals, position, smooth normal (all in UV space)."""
    n = p["tex_body"]
    scene = bpy.context.scene
    _cycles(scene, 4)
    out = {}
    t0 = time.time()
    img = _bake_image("_bake_albedo", n)
    _bake(body, img, "target", sources=[src], bake_type="DIFFUSE", pass_filter={"COLOR"},
          extrusion=0.08, ray=0.3)
    out["albedo"] = _pixels(img)          # linear
    bpy.data.images.remove(img)
    img = _bake_image("_bake_nrm_t", n)
    _bake(body, img, "target", sources=[hires], bake_type="NORMAL", normal_space="TANGENT",
          extrusion=0.05, ray=0.15)
    out["tnormal"] = _pixels(img)
    bpy.data.images.remove(img)
    _cycles(scene, 1)
    img = _bake_image("_bake_pos", n)
    _bake(body, img, "position")
    out["pos"] = _pixels(img)
    bpy.data.images.remove(img)
    img = _bake_image("_bake_nrm", n)
    _bake(body, img, "normal")
    out["nrm"] = _pixels(img)
    bpy.data.images.remove(img)
    # coverage (inside the islands, no margin) for debugging / padding
    img = _bake_image("_bake_cov", n)
    _bake(body, img, "normal", margin=0)
    cov = _pixels(img)
    out["cov"] = (np.abs(cov).sum(2) > 1e-6)
    bpy.data.images.remove(img)
    log(f"body bakes {time.time() - t0:.1f}s")
    return out


# ------------------------------------------------------------------- eyes

def _eye_object(name, centre, R, p, col, root, mat):
    seg, rings = p["eye_segments"]
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=R)
    # pole along -Y (gaze): rotate +Z to -Y
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "X"))
    # cornea: a gentle bulge over the front 40 degrees
    for v in bm.verts:
        d = v.co.normalized()
        ang = math.acos(max(-1, min(1, -d.y)))
        if ang < math.radians(42):
            v.co = d * (R * (1 + 0.07 * math.cos(ang / math.radians(42) * math.pi / 2) ** 2))
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for l in f.loops:
            co = l.vert.co
            l[uvl].uv = (0.5 + co.x / (2.2 * R), 0.5 + co.z / (2.2 * R))
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    ob.parent = root
    ob.location = Vector(centre.tolist())
    ob["look"] = True
    return ob


def _append_rim(sockets, rim):
    """Add the hood rim to the sockets mesh (rigid with the head; material 0 = the
    cloak's weave). Returns (first vertex, vertex count, inner mask)."""
    rv, rt, ruv, rinner, rmat = rim
    me = sockets.data
    v0 = len(me.vertices)
    bm = bmesh.new()
    bm.from_mesh(me)
    uvl = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    vs = [bm.verts.new(tuple(x)) for x in rv]
    for t, mi in zip(rt, rmat):
        try:
            f = bm.faces.new([vs[i] for i in t])
        except ValueError:
            continue
        f.material_index = int(mi)
        f.smooth = True
        for l, i in zip(f.loops, t):
            l[uvl].uv = tuple(ruv[i])
    bm.to_mesh(me)
    bm.free()
    return v0, len(rv), rinner


def _hood_core(sockets, body, cloak, eyes, mat, p):
    """A dark star-shaped shell filling the hood behind the face (from inside the head,
    every direction to just short of the nearest fur / cloth): the gaps between the hood's
    torn rim and the face showed the sky as pale flecks; now they show the hood's dark
    inside. Rigid with the head (it's part of the sockets mesh)."""
    allv, allt, off = [], [], 0
    for ob in (body, cloak):
        v, t = _mesh_arrays(ob.data)
        allv.append(v)
        allt.append(t + off)
        off += len(v)
    tree = BVHTree.FromPolygons([tuple(x) for x in np.concatenate(allv)],
                                [tuple(x) for x in np.concatenate(allt)], all_triangles=True)
    c = (eyes["L"][0] + eyes["R"][0]) / 2 + np.array([0, 0.75, -0.25])
    nu, nv_ = p["hood_core_res"]
    rings = []
    for i in range(1, nv_):
        th = math.pi * i / nv_
        row = []
        for j in range(nu):
            ph = 2 * math.pi * j / nu
            d = Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)))
            h = tree.ray_cast(Vector(c.tolist()), d, 3.0)
            r = min(h[3] if h[0] is not None else 1.2, 1.2)
            row.append(r)
        rings.append(row)
    R = np.array(rings)
    # stay behind the surface between rays: min over neighbours, then inset
    Rm = np.minimum.reduce([np.roll(np.pad(R, ((1, 1), (0, 0)), mode="edge"), (di, dj), (0, 1))[1:-1]
                            for di in (-1, 0, 1) for dj in (-1, 0, 1)])
    Rm = Rm * 0.9 - 0.03
    bm = bmesh.new()
    vs = []
    for i in range(nv_ - 1):
        th = math.pi * (i + 1) / nv_
        vs.append([bm.verts.new(tuple(c + Rm[i, j] * np.array([math.sin(th) * math.cos(2 * math.pi * j / nu),
                                                                math.sin(th) * math.sin(2 * math.pi * j / nu),
                                                                math.cos(th)]))) for j in range(nu)])
    top = bm.verts.new(tuple(c + np.array([0, 0, Rm[0].min()])))
    bot = bm.verts.new(tuple(c - np.array([0, 0, Rm[-1].min()])))
    for j in range(nu):
        j2 = (j + 1) % nu
        bm.faces.new((top, vs[0][j], vs[0][j2]))
        bm.faces.new((bot, vs[-1][j2], vs[-1][j]))
        for i in range(nv_ - 2):
            bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j2], vs[i][j2]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        f.material_index = 1
        f.smooth = True
    tmp = bpy.data.meshes.new("_core")
    bm.to_mesh(tmp)
    n = len(bm.faces)
    bm.free()
    b2 = bmesh.new()
    b2.from_mesh(sockets.data)
    b2.from_mesh(tmp)
    b2.to_mesh(sockets.data)
    b2.free()
    bpy.data.meshes.remove(tmp)
    sockets.data.materials.append(mat)
    return n


def _socket_object(name, eyes, p, col, root, mat):
    """A dark backing behind each eyeball (a sphere of 1.5 R, centred 1.25 radii
    behind the eye), several cm behind the lids everywhere: where the sculpt's lid
    rim is wider than the eyeball, you see deep socket shadow, not through the head."""
    bm = bmesh.new()
    for side, (c, R) in eyes.items():
        ax = EYE_AXES.get(side, np.array([0, -1.0, 0]))
        tmp = bmesh.new()
        bmesh.ops.create_uvsphere(tmp, u_segments=16, v_segments=10, radius=R * p["socket_scale"])
        for v in tmp.verts:
            v.co = Vector((np.array(v.co) + c - ax * R * p["socket_back"]).tolist())
        me = bpy.data.meshes.new("_tmp")
        tmp.to_mesh(me)
        tmp.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    ob.parent = root
    common.box_uv(ob, p["cloak_tile"])
    return ob


# ------------------------------------------------------------------- staff

def _staff_object(p, col, root, mat, grips=()):
    rng = np.random.default_rng(p["staff_seed"])
    line, s = _catmull(p["staff_path"], p["staff_step"])
    L = s[-1]
    # where the hook starts (the shaft's top): last control point of the traced shaft
    shaft_top = np.array(p["staff_path"][14])
    s_hook = s[np.argmin(np.linalg.norm(line - shaft_top, axis=1))]
    # parallel-transport frames
    T = np.gradient(line, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    N = np.zeros_like(T)
    ref = np.array([1.0, 0, 0])
    N[0] = np.cross(T[0], np.cross(ref, T[0]))
    N[0] /= np.linalg.norm(N[0])
    for i in range(1, len(T)):
        v = N[i - 1] - (N[i - 1] @ T[i]) * T[i]
        N[i] = v / np.linalg.norm(v)
    B = np.cross(T, N)
    sides = p["staff_sides"]
    th = np.linspace(0, 2 * math.pi, sides, endpoint=False)
    r0, r1 = p["staff_r"]
    # radius along the length: taper, low-frequency gnarl, knots
    base = np.where(s < s_hook, r0 + (r1 - r0) * (s / s_hook),
                    r1 + (p["staff_hook_r"] - r1) * np.clip((s - s_hook) / (L - s_hook), 0, 1))
    gn = np.zeros(len(s))
    for k, amp in ((0.9, 0.10), (2.3, 0.06), (5.1, 0.035)):
        ph = rng.uniform(0, 2 * math.pi)
        gn += amp * np.sin(2 * math.pi * k * s / 2.0 + ph)
    knots = [(rng.uniform(0.6, s_hook - 0.2), rng.uniform(0, 2 * math.pi), rng.uniform(0.025, 0.045),
              rng.uniform(0.07, 0.13)) for _ in range(9)]
    knots = [k for k in knots if all(abs(k[0] - g) > 0.45 for g in grips)]    # the hands hold smooth wood
    knots.append((L - 0.06, 0.0, 0.0, 0.1))
    rings = []
    for i in range(len(s)):
        r = base[i] * (1 + gn[i])
        # twisted ridges (bark fibres spiralling up the shaft)
        ridge = 0.06 * np.sin(5 * th + 3.0 * s[i]) + 0.03 * np.sin(9 * th - 5.0 * s[i] + 1.3)
        rad = r * (1 + ridge)
        for ks, kt, ka, kw in knots:
            dth = np.angle(np.exp(1j * (th - kt)))
            rad = rad + ka * np.exp(-((s[i] - ks) / kw) ** 2 - (dth / 0.9) ** 2)
        # the carved knob at the hook's tip
        tip = np.clip((s[i] - (L - 0.28)) / 0.28, 0, 1)
        rad = rad * (1 + 0.45 * math.sin(math.pi * min(1.0, tip * 1.15)) ** 1.5)
        # round the very end over
        if i == len(s) - 1:
            rad = rad * 0.35
        if i == 0:
            rad = rad * 0.92
        ring = line[i] + np.outer(np.cos(th) * rad, N[i]) + np.outer(np.sin(th) * rad, B[i])
        rings.append(ring)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    vs = [[bm.verts.new(tuple(q)) for q in ring] for ring in rings]
    tile = p["staff_tile"]
    for i in range(len(rings) - 1):
        for j in range(sides):
            j2 = (j + 1) % sides
            f = bm.faces.new((vs[i][j], vs[i][j2], vs[i + 1][j2], vs[i + 1][j]))
            u0, u1 = j / sides, (j + 1) / sides
            v0, v1 = s[i] / tile, s[i + 1] / tile
            for l, uv in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
                l[uvl].uv = uv
    # caps: the foot (flat on the ground) and the hook's tip
    for ring_i, flip in ((0, True), (len(rings) - 1, False)):
        c = bm.verts.new(tuple(rings[ring_i].mean(0)))
        for j in range(sides):
            j2 = (j + 1) % sides
            a, b = vs[ring_i][j], vs[ring_i][j2]
            f = bm.faces.new((c, b, a) if flip else (c, a, b))
            for l in f.loops:
                dv = Vector(l.vert.co) - Vector(c.co)
                ang = math.atan2(dv.y, dv.x)
                l[uvl].uv = (0.5 + 0.08 * math.cos(ang), 0.5 + 0.08 * math.sin(ang))
    # foot sits on the ground
    zmin = min(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co.z -= zmin
    bm.normal_update()
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(NAME + "_Staff")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(NAME + "_Staff", me)
    col.objects.link(ob)
    ob.parent = root
    return ob


# ------------------------------------------------------------------ materials

def _material(name, color, roughness, base=None, normal=None, normal_strength=1.0, specular=None):
    m = common.pbr_material(name, color, roughness=roughness)
    if specular is not None:      # Principled "Specular IOR Level" -> glTF KHR_materials_specular
        bsdf = next(nd for nd in m.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Specular IOR Level"].default_value = specular
    if base:
        common.set_base_color_map(m, textures.load(base))
    if normal:
        common.set_normal_map(m, textures.load(normal, non_color=True), normal_strength)
    return m


# --------------------------------------------------------------------- rig

def _rig(n, col, root, objs, hand_info, shift):
    """Skeleton from the model's landmarks, skin weights, the four actions."""
    t0 = time.time()
    sh = np.array(shift)
    bpy.context.view_layer.update()
    lm = {}
    for ob in objs["Eyes"]:
        lm["eye_" + ob.name[-1]] = np.array(ob.matrix_world.translation)
    for side, h in zip("RL", hand_info):
        lm["wrist_" + side] = h["wrist"] + sh
        lm["pad_" + side] = h["pad"] + sh
        lm["grip_" + side] = h["grip"] + sh
        lm["knuckle_" + side] = h["knuckle_dir"]
        lm["axis_" + side] = h["axis"]
        fl = []
        for f in h["fingers"]:
            interp = lambda t, arr: np.array([np.interp(t, f["ts"], arr[:, i]) for i in range(3)])
            J = [interp(t, f["pts"]) + sh for t in f["joints"]]
            ups = [interp((f["joints"][j] + f["joints"][j + 1]) / 2, f["inward"]) for j in range(3)]
            fl.append(dict(name=f["name"], J=J, up=ups))
        lm["fingers_" + side] = fl
    sv_ = np.zeros(len(objs["Staff"].data.vertices) * 3)
    objs["Staff"].data.vertices.foreach_get("co", sv_)
    sv_ = sv_.reshape(-1, 3)
    lm["staff_tip"] = sv_[sv_[:, 2] < 0.08].mean(0) * np.array([1, 1, 0])
    bv = np.zeros(len(objs["Body"].data.vertices) * 3)
    objs["Body"].data.vertices.foreach_get("co", bv)
    bv = bv.reshape(-1, 3)
    for side, sign in (("L", 1), ("R", -1)):
        f = bv[(bv[:, 2] < 1.0) & (np.sign(bv[:, 0]) == sign)]
        x = f[:, 0].mean()
        lm["ankle_" + side] = np.array([x, 0.65 * f[:, 1].max() + 0.35 * f[:, 1].mean(), 0.35])
        lm["toe_" + side] = np.array([x, f[:, 1].min() + 0.15, 0.1])
    bones, arms = grimble_rig.skeleton(lm)
    arm = grimble_rig.build_armature(n + "_Armature", bones, col, root)
    hv = {}
    hco = np.zeros(len(objs["Hands"].data.vertices) * 3)
    objs["Hands"].data.vertices.foreach_get("co", hco)
    hco = hco.reshape(-1, 3)
    for side, h in zip("RL", hand_info):
        a, b = h["verts"]
        hv[side] = hco[a:b]
    grimble_rig.skin(arm, objs, bones, hand_info, lm)
    sv = grimble_rig.Solver(arm, bones, arms, lm, hv)
    # the solver must reproduce the rest pose exactly
    PM = sv.solve(grimble_rig._rest_controls(sv))
    err = max(max(abs(B[i][j] - (1 if i == j else 0)) for i in range(4) for j in range(4))
              for B in sv.basis(PM).values())
    log(f"rig: {len(bones)} bones, rest-pose check {err:.2e}")
    for bn, B in sv.basis(PM).items():
        e = max(abs(B[i][j] - (1 if i == j else 0)) for i in range(4) for j in range(4))
        if e > 1e-3:
            log(f"  rest mismatch {bn}: {e:.3f}")
    grimble_rig.prepare(sv)
    grimble_rig.bake_actions(sv, bpy.context.scene)
    log(f"rig + actions {time.time() - t0:.1f}s")
    return arm


# ------------------------------------------------------------------- build

def build(**overrides):
    with np.errstate(all="ignore"):     # Accelerate's matmul raises spurious FP warnings
        return _build({**P, **overrides})


def _build(p):
    t0 = time.time()
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    os.makedirs(CACHE, exist_ok=True)

    src = _import_source(p)
    verts, tris, fcol = _base_mesh(p, src)
    log(f"base {len(tris)} tris")
    eyes = _eye_spheres(p, verts, tris)
    lab, zones = _classify(p, verts, tris, fcol, eyes)
    # high-res reference (for the normal bake): the base mesh minus staff and sockets
    keep = (lab == BODY) | (lab == CLOAK)
    hires = _object("_grimble_hires", _mesh_from_arrays("_grimble_hires", verts, tris[keep]))
    vv, tt, ll = verts, tris[keep], lab[keep]
    zones = tuple(z[keep] for z in zones)
    dv, dt, dl = _decimate(p, vv, tt, ll, zones)
    # second cull on the final mesh: drops the inner layers the first pass kept;
    # then close the small holes either pass left (faces in deep creases no ray hit)
    vis = _visible_faces(dv, dt, dict(p, vis_spacing=p["vis_spacing2"], vis_dirs=p["vis_dirs2"], vis_grow=1),
                         extra=[_eye_tris(eyes)])
    log(f"final cull: {(~vis).sum()} hidden faces removed")
    dt, dl = dt[vis], dl[vis]
    dv, dt, dl = _fill_holes(dv, dt, dl, eyes)
    floating = ~_remove_floaters(dv, dt)
    # loose leftovers of the sculpt's staff (the new staff replaces it)
    comp = _components(len(dt), _face_adjacency(dt))
    sizes = np.bincount(comp)
    line, _ = _staff_line(p)
    ds, _ = _dist_polyline(dv[dt].mean(1), line)
    near = np.bincount(comp, weights=(ds < 0.35).astype(float)) / np.maximum(sizes, 1)
    floating |= (sizes[comp] < sizes.max()) & (near[comp] > 0.5)
    dv, dt, dl = dv, dt[~floating], dl[~floating]
    dl = _clean_labels(dl, dt)
    dl = _fill_enclosed(dt, dl)
    dl = _keep_body_parts(p, dv, dt, dl)
    # hood lining glimpsed through gaps right behind the fur: paint it as fur
    fc, fr = np.array(p["face_centre"]), np.array(p["face_radii"])
    cen = dv[dt].mean(1)
    behind = (((cen - fc) / (fr * 0.6)) ** 2).sum(1) < 1.0
    dl[behind & (dl == CLOAK) & (cen[:, 1] < -0.6)] = BODY
    # the sculpt's hands go (rebuilt below); cap the sleeve cuffs they leave open
    hands, drop = _extract_hands(p, dv, dt, dl)
    dt, dl = dt[~drop], dl[~drop]
    dv, dt, dl = _fill_holes(dv, dt, dl, eyes, caps=[(h["wrist"], 0.7) for h in hands])
    cuffs = [c for c in FAN_CENTRES if min(np.linalg.norm(c - h["wrist"]) for h in hands) < 0.7]
    keep = _remove_floaters(dv, dt)
    dt, dl = dt[keep], dl[keep]
    # last hole pass on the joined surface (body + cloak, so their seam isn't a hole):
    # every compact hole or slit left by the culls, the hand extraction and the cleanups
    # (the sky showed through them as pale flecks); the rims are long and stay open
    dv, dt, dl, nh = _fan_fill(dv, dt, dl, eyes, max_sides=120, max_perim=p["hole_perimeter"])
    log(f"final hole pass: {nh} holes closed")
    log(f"decimated {len(dt)} tris: body {(dl == BODY).sum()} cloak {(dl == CLOAK).sum()}")

    # the body / cloak seam (edges between a body face and a cloak face)
    pairs = _face_adjacency(dt)
    mixed = pairs[dl[pairs[:, 0]] != dl[pairs[:, 1]]]
    seam_pts = dv[np.intersect1d(dt[mixed[:, 0]], dt[mixed[:, 1]])]
    body = _part_object(n + "_Body", dv, dt, dl == BODY, col, root)
    cloak = _part_object(n + "_Cloak", dv, dt, dl == CLOAK, col, root)
    # the face: a light pass closes the sculpt's hairline cracks and evens the decimation
    _smooth_parts(body, lambda v: (v[:, 2] > 4.4) & ~((v[:, 0] < -0.6) & (v[:, 1] < -1.2)), p["face_smooth"], 0.35)
    # the sculpt's deep cracks down the sides of the nose: iron them out (eye rims stay)
    nose_c = np.array(p["nose_crease"])
    _smooth_parts(body, lambda v: (np.linalg.norm(v - nose_c, axis=1) < p["nose_smooth_r"])
                  & np.all([np.linalg.norm(v - c, axis=1) > R * 1.15 for c, R in eyes.values()], axis=0),
                  p["nose_smooth"], 0.5)
    log(f"face folds removed: {_drop_inward_faces(body, eyes, p)}")
    # close the body's own small holes (the sculpt's, and where folds went); the eye
    # rims and the long seam with the cloak stay open
    bv, bt = _mesh_arrays(body.data)
    nv2, nt2, _, nh = _fan_fill(bv, bt, np.zeros(len(bt), np.int8), {}, max_sides=120)
    old = body.data
    body.data = _mesh_from_arrays(n + "_Body", nv2, nt2)
    bpy.data.meshes.remove(old)
    for poly in body.data.polygons:
        poly.use_smooth = True
    log(f"body holes filled: {nh}")
    body.data.set_sharp_from_angle(angle=math.radians(85))   # the cloak is cloth: smooth everywhere
    # the cloak's back: the cheapest part of the decimation; a light smoothing softens its
    # facets (open edges stay put)
    if p["cloak_back_smooth"]:
        _smooth_parts(cloak, lambda v: v[:, 1] > 0.5, p["cloak_back_smooth"], 0.5)
    # the cloak's own holes and slits (the joined pass can't see them where a hole's corner
    # touches another loop): close every compact one that doesn't touch the face seam
    cv_, ct_ = _mesh_arrays(cloak.data)
    ct_ = ct_[_remove_fins(cv_, ct_)]
    bkey = set(map(tuple, np.round(_mesh_arrays(body.data)[0] * 1e4).astype(np.int64)))
    seam_v = np.array([tuple(x) in bkey for x in np.round(cv_ * 1e4).astype(np.int64)])
    cv2, ct2, _, nh = _fan_fill(cv_, ct_, np.zeros(len(ct_), np.int8), eyes, max_sides=200,
                                max_perim=p["hole_perimeter"], keep=seam_v, keep_frac=0.6)
    old = cloak.data
    cloak.data = _mesh_from_arrays(n + "_Cloak", cv2, ct2)
    bpy.data.meshes.remove(old)
    for poly in cloak.data.polygons:
        poly.use_smooth = True
    log(f"cloak holes closed: {nh}")
    # the hood's front edge: the scan's torn shards around the face go; a rolled, frayed
    # wool hem is swept along the face opening instead (grimble_rim.py)
    rim = None
    if p["rim"]:
        band, rv, rt, ruv, rinner, nfr, rmat = grimble_rim.build(body, cloak, _face_frame(eyes), p,
                                                           np.random.default_rng(p["rim_seed"]))
        cv_, ct_ = _mesh_arrays(cloak.data)
        ct_ = ct_[~band]
        # the cut leaves torn slivers hanging by a corner: drop small pieces and faces
        # joined to the rest only through a vertex
        comp = _components(len(ct_), _face_adjacency(ct_))
        sizes = np.bincount(comp)
        ct_ = ct_[sizes[comp] >= p["rim_min_piece"]]
        used = np.unique(ct_)
        remap = -np.ones(len(cv_), np.int64)
        remap[used] = np.arange(len(used))
        old = cloak.data
        cloak.data = _mesh_from_arrays(n + "_Cloak", cv_[used], remap[ct_])
        bpy.data.meshes.remove(old)
        for poly in cloak.data.polygons:
            poly.use_smooth = True
        rim = (rv, rt, ruv, rinner, rmat)
        log(f"hood rim: {band.sum()} shard faces removed; rim {len(rt)} tris ({nfr} fringe strands)")

    # --- body UVs + textures
    bc = np.array([pl.center for pl in body.data.polygons])
    fz, _, _, _ = _zones(p, bc)
    face_info = _uv_body(body, fz, p, eyes)
    geo_key = _hash(np.round(_mesh_arrays(body.data)[0], 4),
                    np.array([d.uv[:] for d in body.data.uv_layers["UVMap"].data]).round(5), p["tex_body"])
    names = grimble_paint.body_names()
    paint_key = _hash(geo_key, grimble_paint.version(), {k: p[k] for k in ("eye_l", "eye_r", "nose", "feet")})
    key_file = os.path.join(CACHE, "body_textures.json")
    have = all(os.path.exists(os.path.join(textures.TEX_DIR, nm + ".png")) for nm in names)
    stored = json.load(open(key_file)) if os.path.exists(key_file) else {}
    if p["force"] or not have or stored.get("key") != paint_key:
        bake_file = os.path.join(CACHE, "body_bakes.npz")
        bakes = None
        if os.path.exists(bake_file) and not p["force"]:
            z = np.load(bake_file)
            if str(z["key"]) == geo_key:
                bakes = {k: z[k] for k in ("albedo", "tnormal", "pos", "nrm", "cov")}
        if bakes is None:
            bakes = _body_bakes(p, body, src, hires)
            np.savez_compressed(bake_file, key=np.array(geo_key), **{k: (v.astype(np.float16) if v.dtype != bool else v)
                                                          for k, v in bakes.items()})
        bakes = {k: v.astype(np.float32) if v.dtype != bool else v for k, v in bakes.items()}
        grimble_paint.paint_body(bakes, p, eyes, seam_pts)
        json.dump({"key": paint_key}, open(key_file, "w"))
    _remove(hires)
    _remove(src)
    # the folded triangles were collapsed into their neighbours' texels for the bakes; for
    # the final mesh they get their continuous projected UVs back (they sample the texels of
    # the surface in front of them): fewer UV seams, which three.js's derivative tangents
    # turned into glints (the toes, the creases by the nose)
    ci_, uv_ = face_info["restore"]
    data = np.zeros(len(body.data.loops) * 2)
    body.data.uv_layers["UVMap"].data.foreach_get("uv", data)
    data = data.reshape(-1, 2)
    data[ci_] = uv_
    body.data.uv_layers["UVMap"].data.foreach_set("uv", data.ravel())

    n_body_v = len(body.data.vertices)
    nb = _face_backing(body, face_info, eyes, p)
    log(f"face backing: {nb} tris")
    body_mat = _material("M_Grimble_Body", (0.4, 0.3, 0.22), 0.72,
                         os.path.join(textures.TEX_DIR, names[0] + ".png"),
                         os.path.join(textures.TEX_DIR, names[1] + ".png"), 1.0, specular=p["body_specular"])
    body_mat.roughness = 0.85
    next(nd for nd in body_mat.node_tree.nodes if nd.type == "BSDF_PRINCIPLED").inputs["Roughness"].default_value = 0.85
    body_mat.use_backface_culling = True        # single-sided: its folds' back faces read as pale streaks
    body.data.materials.append(body_mat)

    # --- cloak
    _uv_wrap(cloak, p["cloak_tile"], eyes)
    cb, cn = grimble_paint.cloak_textures(p["tex_cloak"], force=p["force"])
    cloak_mat = _material("M_Grimble_Cloak", (0.03, 0.028, 0.026), 0.95, cb, cn, p["cloak_normal"],
                          specular=p["cloak_specular"])
    cloak_mat.use_backface_culling = True       # single-sided; the seen back side gets a lining (_add_lining)
    cloak.data.materials.append(cloak_mat)
    lining_mat = _material("M_Grimble_CloakLining", (0.008, 0.007, 0.006), 1.0, specular=0.1)
    lining_mat.use_backface_culling = True

    # --- eyes
    eb = grimble_paint.eye_texture(p["tex_eye"], force=p["force"])
    eye_mat = _material("M_Grimble_Eye", (0.05, 0.02, 0.01), 0.035, eb)
    eye_objs = [_eye_object(f"{n}_Eye_{side}", c, R, p, col, root, eye_mat) for side, (c, R) in eyes.items()]
    sockets = _socket_object(n + "_Sockets", eyes, p, col, root, cloak_mat)
    log(f"hood core: {_hood_core(sockets, body, cloak, eyes, lining_mat, p)} tris")
    rim_range = None
    if rim is not None:
        rim_range = _append_rim(sockets, rim)

    # --- staff
    sb, sn = grimble_paint.staff_textures(p["tex_staff"], force=p["force"])
    staff_mat = _material("M_Grimble_Staff", (0.2, 0.12, 0.07), 0.72, sb, sn, 1.0, specular=0.3)
    staff = _staff_object(p, col, root, staff_mat, grips=[h["s"] for h in hands])
    # --- hands, built on the staff's real surface
    hb, hn = grimble_paint.hand_textures(p["tex_hand"], force=p["force"])
    hand_mat = _material("M_Grimble_Hand", (0.2, 0.11, 0.06), 0.62, hb, hn, 1.0)
    claw_mat = _material("M_Grimble_Claw", (0.012, 0.009, 0.008), 0.6, specular=0.3)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    stree = BVHTree.FromObject(staff, bpy.context.evaluated_depsgraph_get())
    line, sl = _catmull(p["staff_path"], p["staff_step"])
    hand_info = grimble_hands.build_hands(bm, uvl, hands, line, sl, stree, p)
    for f in bm.faces:
        f.smooth = True
    hme = bpy.data.meshes.new(n + "_Hands")
    bm.to_mesh(hme)
    bm.free()
    hme.materials.append(hand_mat)
    hme.materials.append(claw_mat)
    hands_ob = bpy.data.objects.new(n + "_Hands", hme)
    col.objects.link(hands_ob)
    hands_ob.parent = root

    # --- origin between the feet
    fx, fy = p["feet_mid"]
    shift = Matrix.Translation((-fx, -fy, 0))
    for ob in (body, cloak, staff, sockets, hands_ob):
        ob.data.transform(shift)
    for ob in (body, cloak):      # the voxel surface overshoots the floor by up to a voxel or two
        v = np.zeros(len(ob.data.vertices) * 3)
        ob.data.vertices.foreach_get("co", v)
        v = v.reshape(-1, 3)
        v[:, 2] = np.maximum(v[:, 2], 0.0)
        ob.data.vertices.foreach_set("co", v.ravel())
    for ob in eye_objs:
        ob.location = ob.location + Vector((-fx, -fy, 0))
    parts = [body, cloak, staff, sockets, hands_ob] + eye_objs
    for ob in parts:
        ob.data.update()

    if p["ao"]:
        vertex_ao.bake(root, distance=1.2, samples=32, strength=0.7, max_face_area=0.25)
        # the face backing sits deep in the hood: keep it at the occlusion of fur in shadow
        attr = body.data.color_attributes.get(vertex_ao.ATTR)
        if attr is not None:
            ao = np.zeros(len(attr.data) * 4, np.float32)
            attr.data.foreach_get("color", ao)
            ao = ao.reshape(-1, 4)
            ao[n_body_v:, :3] = p["backing_ao"]
            attr.data.foreach_set("color", ao.ravel())
        # the cloak's inner side (the hood lining, the walls of the front opening) faces
        # into the creature: in the engine nothing shadows it, so the low sun lit it as
        # bright slivers along the rims. Bake it dark into the occlusion.
        _darken_lining(cloak, eyes, p["lining_dark"], [c + np.array([-fx, -fy, 0]) for c in cuffs])
        # the staff and the hands move against the cloak: occlusion baked at rest would ride
        # along (dark blotches near the staff's foot, dark fingers in the open wave)
        for ob, lo_ in ((staff, 1.0), (hands_ob, 0.75)):
            attr = ob.data.color_attributes.get(vertex_ao.ATTR)
            if attr is not None:
                ao = np.zeros(len(attr.data) * 4, np.float32)
                attr.data.foreach_get("color", ao)
                ao = ao.reshape(-1, 4)
                ao[:, :3] = np.maximum(ao[:, :3], lo_)
                attr.data.foreach_set("color", ao.ravel())
        # the rim's inner side (toward the face) is in the hood's shadow
        if rim_range is not None:
            attr = sockets.data.color_attributes.get(vertex_ao.ATTR)
            if attr is not None:
                ao = np.zeros(len(attr.data) * 4, np.float32)
                attr.data.foreach_get("color", ao)
                ao = ao.reshape(-1, 4)
                v0, nv_, inner = rim_range
                seg = ao[v0:v0 + nv_]
                seg[inner, :3] = np.minimum(seg[inner, :3], p["lining_ao"] + 0.15)
                seg[~inner, :3] = np.maximum(seg[~inner, :3], 0.75)
                ao[v0:v0 + nv_] = seg
                attr.data.foreach_set("color", ao.ravel())
        # the eyeballs turn: occlusion baked in the rest pose would swing into view
        for ob in eye_objs:
            attr = ob.data.color_attributes.get(vertex_ao.ATTR)
            if attr is not None:
                attr.data.foreach_set("color", np.ones(len(attr.data) * 4, np.float32))
    if p["rig"]:
        _rig(n, col, root, dict(Body=body, Cloak=cloak, Staff=staff, Sockets=sockets, Hands=hands_ob,
                                Eyes=eye_objs), hand_info, Vector((-fx, -fy, 0)))
    others = [_mesh_arrays(o.data) for o in (body, staff, sockets, hands_ob)]
    for o in eye_objs:
        ev, et = _mesh_arrays(o.data)
        others.append((ev + np.array(o.matrix_world.translation), et))
    p["_head_centre"] = (eyes["L"][0] + eyes["R"][0]) / 2 + np.array([-fx, -fy + 0.6, 0])
    p["_shift"] = (fx, fy)
    _add_lining(cloak, others, lining_mat, p, [c + np.array([-fx, -fy, 0]) for c in cuffs])
    log(f"done in {time.time() - t0:.1f}s; tris body {len(body.data.polygons)} cloak {len(cloak.data.polygons)}"
        f" staff {sum(len(pl.vertices) - 2 for pl in staff.data.polygons)}"
        f" hands {sum(len(pl.vertices) - 2 for pl in hands_ob.data.polygons)}"
        f" eyes {sum(len(pl.vertices) - 2 for o in eye_objs for pl in o.data.polygons)}")
    return root, parts


if __name__ == "__main__":
    build()
