"""The Grimble: the villain. A cute-uncanny furry creature in a hooded black wool
cloak, leaning on a gnarled staff, 7.3 m tall. Built every time by build() from the
AI sculpt concept/grimble/source/trellis2_gen2.glb, as a character pipeline:

STAGE 1  high-poly source: the sculpt is imported, scaled, voxel-remeshed and reduced to
         its visible shell (cached in build/grimble_cache/), and its faces are
         classified (fur/skin, cloak, the sculpt's staff, eye sockets). It is the detail
         source only; no game mesh is made from it directly.
STAGE 2  low-poly modelling (grimble_cloth.py): Body = head (the sculpt's face inside
         the opening traced from its fur patch, lids hugging the eyeballs) + feet;
         Cloak = hood, robe, sleeves as clean grids with real thickness at the rolled
         edges, a hood-rim fringe and a dark core inside the neck; Hands
         (grimble_hands.py), Staff, Eyes are procedural.
STAGE 3  UVs: the body: one Lambert-projected island per part (star-shaped, so no
         overlaps), packed with padding; the cloak: a unique atlas ("UVMap") from the
         grids' arc-length unwrap (seams at the robe's back centre, under the chin, under
         the sleeves), plus a world-scale "UVDetail" set for the tiling wool.
STAGE 4  bakes (Cycles, selected to active): the body's colour + detail normals from the
         sculpt's fur faces (then painted: grimble_paint.py); the cloak's fold normals
         from the sculpt's cloak (tangent space, MikkTSpace = three.js with exported
         tangents); vertex AO for every part.
STAGE 5  rig, skinning, actions (grimble_rig.py): 60 bones, <= 4 normalised influences.
STAGE 6  export (build_asset.py, EXPORT below: tangents on).
STAGE 7  QA (grimble_qa.py): geometry, contact, UVs, bakes, skin, budget, rig; fails the
         build on errors.

MATERIALS (glTF contract, for viewer/grimble.js)
  M_Grimble_Cloak       outside of the cloth. baseColorTexture T_Grimble_Cloak_DetailAlbedo
                        on TEXCOORD_1 (UVDetail, 1 unit = extras.detail.tile_m metres);
                        normalTexture T_Grimble_Cloak_Normal on TEXCOORD_0 (unique folds).
                        extras.detail = {normal: "T_Grimble_Cloak_DetailNormal", uv: 1,
                        tile_m: 0.6, scale: <normal scale>, blend: "udn"}: the engine
                        samples the detail normal on TEXCOORD_1 and combines it with the
                        unique normal (UDN: n = normalize(n1.xy + n2.xy * scale, n1.z)).
  M_Grimble_CloakLining inside of the cloth: detail albedo + detail normal, both TEXCOORD_1
                        (vertex colour AO darkens it).
  M_Grimble_CloakEdge   the rolled rims and the fringe: as the lining, in the light.
  COLOR_0 ("AO")        baked occlusion on every mesh: multiply into the base colour.
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
import grimble_crawl  # noqa: E402
import grimble_cloth  # noqa: E402
import grimble_qa  # noqa: E402

for _m in (common, textures, vertex_ao, grimble_hands, grimble_paint, grimble_rig, grimble_crawl, grimble_cloth,
           grimble_qa):
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
    # body (grimble_cloth.py): star-shaped head and feet fitted to the sculpt
    head_hidden_ao=0.2,            # occlusion of the head inside the hood (seen only through gaps)
    head_subdiv=5, head_inner=0.85, head_blend=3, head_spike=0.06,
    open_brim=0.08,                # a hood brim this far in front of the face still counts as the opening
    foot_subdiv=4, foot_z=0.2,
    # cloak: robe + hood grids projected onto the sculpt's cloak, then given thickness
    robe_rows=40, robe_cols=62, robe_z=(0.02, 6.5), robe_smooth=0, robe_tuck=0.07,
    hem_toe_h=0.26, hem_toe_w=0.32,      # the hem rises this much (m) over each foot, over this angle (rad)
    open_pct=97.0,                 # the face opening: this percentile of the fur patch's angle per direction
    robe_front_w=1.5, robe_chin=-0.55, robe_band=4, robe_top_band=6,  # in front the robe stops just above the chin's bottom
    hood_rows=22, hood_cols=60, hood_margin=0.08, hood_elev=-32.0, hood_th_max=3.13,
    hood_smooth=1, hood_clear=0.07, hood_lip=0.02, hood_lip_rows=5,
    hood_brim_rows=4, hood_brim=(0.28, 0.18),   # the cowl: rows forward of the opening (rad), its flare (m)
    core_subdiv=2, gorget_rows=12, gorget_cols=16, gorget_r=(0.3, 0.75), gorget_inset=0.08, core_z=4.5, core_back=0.25, core_rmax=2.5, core_inset=0.05,   # the dark core inside neck and chest
    fringe_seed=4, fringe_hood=60, fringe_arc=115.0, fringe_len=0.10,
    cloth_thick=0.09,              # solidify thickness at the rolled edges (m) ...
    cloth_thin=0.38,               # ... and this fraction of it elsewhere (~3.4 cm)
    sleeve_rows=26, sleeve_cols=14,          # full sleeves (shoulder .. cuff; rows clustered at the elbow)
    sleeve_prof=(0.36, 0.28, 0.25, 0.29),    # radius at the shoulder, elbow, wrist, cuff opening (m)
    sleeve_over=0.1,                         # the cuff reaches this far past the wrist
    sleeve_free=0.35,                        # ... and is free (not shrink-wrapped inside the robe) this far up
    sleeve_rmin=0.18,                        # the shrink-wrapped radius never goes below this
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
    toe_angles=(-26.0, 0.0, 26.0),  # the toes' directions round each foot's forward (deg, + = outward)
    toe_splay=10.0,                # each foot's toes turn outward this much (deg)
    toe_r=0.075, toe_out=0.2,      # toe radius; how far (m) the toes reach past the hem
    toe_claw_len=0.15,
    hand_tile=0.25,                # metres per hand skin texture tile
    hand_seed=3,
    tex_hand=1024,
    # textures
    tex_body=2048, tex_cloak=1024, tex_staff=1024, tex_eye=512,
    tex_cloak_unique=2048,         # the cloak's unique (baked) fold normal map
    uv_pad_px=8,                   # padding between UV islands (texels at the map's size)
    uv_cap_cos=0.55,               # body UVs: the cap within ~57 deg of each part's back point is its own island
    cloak_cage=0.25, cloak_ray=0.6,   # cloak bake: cage extrusion / max ray distance (m)
    cloak_fold_blur=2.0,           # cloak bake: softening of the scan's hard steps (px gaussian sigma)
    cloak_fold_z=0.45,             # cloak bake: normals flatter than this (z) blend toward flat
    cloak_tile=0.6,                # metres per cloak texture tile
    cloak_normal=0.35,             # cloak normal map strength (the weave; strong values glint at grazing light)
    cloak_specular=0.0,            # Specular IOR Level (KHR_materials_specular): black wool: none (three.js scales the grazing F90 by it too: even 0.1 lit the baked folds' edges as pale lines in low views)
    body_specular=0.2,             # ... and fur
    staff_tile=0.7,
    face_texel_boost=1.25,         # face island scale relative to hands / feet before packing
    ao=True,
    rig=True,                      # skeleton, skin weights and the actions (grimble_rig.py)
    crawl_scale=0.68,              # the crawl family's uniform scale (grimble_crawl.py): the galleries
                                   # are 3.2 m wide and the courtyard door 3.0 x 3.0 m; at full size the
                                   # hood alone is ~3.6 m wide (0.8 left it 3.0 m wide: no room to turn)
    qa=True, qa_strict=True,       # run grimble_qa at the end; fail the build on errors
    lining_ao=0.35,                # occlusion floor of the cloak's lining (it's in shadow)
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


def _uv_star(ob, parts, p):
    """Body UVs: per part (head, feet: star-shaped about their centres) a Lambert
    equal-area projection of the directions from the centre, which never folds, plus a
    second small island for the cap round the projection's singular back point (the back
    of the head inside the hood, the soles), so no triangle spans the singularity. The
    head's islands get extra texel density; then all are packed with padding."""
    me = ob.data
    if "UVMap" not in me.uv_layers:
        me.uv_layers.new(name="UVMap")
    v, t = _mesh_arrays(me)
    li = np.zeros(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", li)
    ls = np.zeros(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_start", ls)
    uv = np.zeros((len(me.loops), 2))
    for kind, v0, nv_, centre, frame in parts:
        if frame is not None:
            c, a, b, f = frame
        else:
            c, f = centre, np.array([0, 0, 1.0])
            a = np.array([1.0, 0, 0])
            b = np.cross(f, a)
        tids = np.nonzero((t[:, 0] >= v0) & (t[:, 0] < v0 + nv_))[0]
        dirs = v[t[tids]] - c
        dirs /= np.linalg.norm(dirs, axis=2, keepdims=True)
        cap = (dirs @ f).mean(1) < -p["uv_cap_cos"]
        for sel, axes in ((~cap, (a, b, f)), (cap, (a, -b, -f))):
            ti = tids[sel]
            if not len(ti):
                continue
            corners = (ls[ti][:, None] + np.arange(3)[None, :]).ravel()
            q = _lambert(v[li[corners]], c, *axes)
            P3 = v[li[corners]].reshape(-1, 3, 3)
            Q = q.reshape(-1, 3, 2)
            a3 = 0.5 * np.linalg.norm(np.cross(P3[:, 1] - P3[:, 0], P3[:, 2] - P3[:, 0]), axis=1).sum()
            e1, e2 = Q[:, 1] - Q[:, 0], Q[:, 2] - Q[:, 0]
            a2 = 0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]).sum()
            s_ = math.sqrt(a3 / max(a2, 1e-12)) * (p["face_texel_boost"] if kind == "head" else 1.0)
            uv[corners] = (q - q.min(0)) * s_
    me.uv_layers["UVMap"].data.foreach_set("uv", uv.ravel())
    _select_only(ob)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=False, margin_method="FRACTION", margin=p["uv_pad_px"] / p["tex_body"] * 2)
    bpy.ops.object.mode_set(mode="OBJECT")
    ob.select_set(False)
    uvs = np.zeros(len(me.loops) * 2)
    me.uv_layers["UVMap"].data.foreach_get("uv", uvs)
    me.uv_layers["UVMap"].data.foreach_set("uv", 0.5 + (uvs - 0.5) * 0.96)


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


def _uv_node(mat, image_node, layer):
    nt = mat.node_tree
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = layer
    uvn.location = (image_node.location.x - 250, image_node.location.y)
    nt.links.new(uvn.outputs["UV"], image_node.inputs["Vector"])


def _chain_weights(ob, curve, arc, stops):
    """Skin weights by arc position along a centre line: stops [(bone, fraction of the
    length)], blended smoothly between neighbours. Stored as "_w_<bone>" groups (read by
    grimble_rig.skin())."""
    co = np.zeros(len(ob.data.vertices) * 3)
    ob.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    s = np.array([arc[np.argmin(np.linalg.norm(curve - q, axis=1))] for q in co]) / arc[-1]
    xs = [f for _, f in stops]
    W = np.zeros((len(co), len(stops)))
    for k in range(len(stops)):
        e = np.zeros(len(stops))
        e[k] = 1
        W[:, k] = np.interp(s, xs, e)
    for k, (bone, _) in enumerate(stops):
        g = ob.vertex_groups.new(name="_w_" + bone)
        q = np.round(W[:, k] * 200).astype(int)
        for val in np.unique(q[q > 0]):
            g.add(np.nonzero(q == val)[0].tolist(), val / 200.0, "REPLACE")


def _sleeve_weights(ob, sinfo, side):
    """Skin weights for a sleeve, by each vertex's arc position along the arm: the shoulder end
    blends into the shoulder / spine, the elbow blends upper arm -> forearm over ~0.45 m (no
    hard segment), the forearm and the cuff ride the forearm. Stored as "_w_<bone>" vertex
    groups; grimble_rig.skin() reads (and removes) them."""
    co = np.zeros(len(ob.data.vertices) * 3)
    ob.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    curve, arc = sinfo["curve"], sinfo["arc"]
    s = np.array([arc[np.argmin(np.linalg.norm(curve - q, axis=1))] for q in co])

    def sm(a, b, x):
        t = np.clip((x - a) / (b - a), 0, 1)
        return t * t * (3 - 2 * t)
    k_sh = 1 - sm(sinfo["s_sh"] - 0.05, sinfo["s_sh"] + 0.5, s)
    # the elbow: upper arm -> the half-rotation helper (rigid with it at the joint) -> forearm;
    # linear blending of two bones a right angle apart pinched and folded the inside of the elbow
    se = sinfo["s_el"]
    up_ = 1 - sm(se - 0.4, se, s)
    fo_ = sm(se, se + 0.4, s)
    arm_ = 1 - 0.8 * k_sh
    w = {"Spine3": 0.35 * k_sh, "Shoulder." + side: 0.45 * k_sh,
         "UpperArm." + side: arm_ * up_, "Elbow." + side: arm_ * (1 - up_ - fo_), "Forearm." + side: arm_ * fo_}
    tot = sum(w.values())
    for bone, ww in w.items():
        g = ob.vertex_groups.new(name="_w_" + bone)
        q = np.round(ww / tot * 200).astype(int)
        for val in np.unique(q[q > 0]):
            g.add(np.nonzero(q == val)[0].tolist(), val / 200.0, "REPLACE")


def _cloak_materials(p):
    """The three cloak materials (see MATERIALS in the module docstring)."""
    alb, dnrm = grimble_paint.cloak_textures(p["tex_cloak"], force=p["force"])
    unique = os.path.join(textures.TEX_DIR, "T_Grimble_Cloak_Normal.png")
    if not os.path.exists(unique):          # a flat placeholder until the bake writes it
        n = p["tex_cloak_unique"]
        textures._save("T_Grimble_Cloak_Normal", np.tile([0.5, 0.5, 1.0], (n, n, 1)), non_color=True)
    out = []
    # (the rims' UVs are stretched across the cloth's thickness by Solidify: no normal map
    #  there, its tangents would be meaningless and light it as bright streaks)
    for name, rough, spec, normal, nuv in (("M_Grimble_Cloak", 0.95, p["cloak_specular"], unique, "UVMap"),
                                           ("M_Grimble_CloakLining", 1.0, 0.1, dnrm, "UVDetail"),
                                           ("M_Grimble_CloakEdge", 1.0, 0.1, None, "UVDetail")):
        m = _material(name, (0.03, 0.028, 0.026), rough, alb, normal,
                      1.0 if nuv == "UVMap" else p["cloak_normal"], specular=spec)
        m.use_backface_culling = True
        tex_nodes = [nd for nd in m.node_tree.nodes if nd.type == "TEX_IMAGE"]
        for nd in tex_nodes:
            if nd.image and "Detail" in nd.image.name:
                _uv_node(m, nd, "UVDetail")
            elif nd.image:
                _uv_node(m, nd, nuv)
        if name == "M_Grimble_Cloak":
            # the engine adds the tiling detail normal over the unique fold normal
            m["detail"] = dict(normal="T_Grimble_Cloak_DetailNormal", uv=1, tile_m=p["cloak_tile"],
                               scale=p["cloak_normal"], blend="udn")
        out.append(m)
    return out


def _small_part(name, v, t, col, mats, mat_index):
    """A small mesh part of the cloak (fringe, core): both UV layers (no unique texels:
    material 1 / 2 use only the tiling detail), one material for all faces."""
    me = _mesh_from_arrays(name, v, t)
    for layer in ("UVMap", "UVDetail"):
        uv = me.uv_layers.new(name=layer)
    li = np.zeros(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", li)
    me.uv_layers["UVMap"].data.foreach_set("uv", np.zeros(len(me.loops) * 2, np.float32))
    me.uv_layers["UVDetail"].data.foreach_set("uv", (v[li][:, :2] / 0.6).astype(np.float32).ravel())
    for m in mats:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", np.full(len(me.polygons), mat_index, np.int32))
    for poly in me.polygons:
        poly.use_smooth = True
    return _object(name, me, col)


def _bake_cloak_normal(cloak, hp, p, flat_rects=()):
    """Cycles selected-to-active: the sculpt's cloak (high-poly) -> the cloak's outside
    (material 0, unique UVMap) as a tangent-space normal map (MikkTSpace, as three.js uses
    with exported tangents). Cached by geometry. Returns stats (ray misses, skew)."""
    me = cloak.data
    v, t = _mesh_arrays(me)
    uv = np.zeros(len(me.loops) * 2)
    me.uv_layers["UVMap"].data.foreach_get("uv", uv)
    key = _hash(np.round(v, 4), np.round(uv, 5), len(hp.data.polygons), p["cloak_cage"], p["cloak_ray"],
                p["tex_cloak_unique"], np.round(np.array(flat_rects), 4), "bake3",
                p["cloak_fold_blur"], p["cloak_fold_z"])
    stats_file = os.path.join(CACHE, "cloak_bake.json")
    path = os.path.join(textures.TEX_DIR, "T_Grimble_Cloak_Normal.png")
    if os.path.exists(stats_file) and os.path.exists(path) and not p["force"]:
        st = json.load(open(stats_file))
        if st.get("key") == key:
            return st
    t0 = time.time()
    # the outside faces only (the lining / rims share overlapping UVs)
    tmp = _object("_grimble_bake_lp", me.copy())
    bm = bmesh.new()
    bm.from_mesh(tmp.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != 0], context="FACES")
    bm.to_mesh(tmp.data)
    bm.free()
    tmp.data.uv_layers.active = tmp.data.uv_layers["UVMap"]
    tmp.data.uv_layers["UVMap"].active_render = True
    scene = bpy.context.scene
    _cycles(scene, 4)
    n = p["tex_cloak_unique"]
    img = _bake_image("_bake_cloak_n", n)
    _bake(tmp, img, "target", sources=[hp], bake_type="NORMAL", normal_space="TANGENT",
          extrusion=p["cloak_cage"], ray=p["cloak_ray"], margin=16)
    nrm = _pixels(img)
    bpy.data.images.remove(img)
    # QA: ray misses (sampled from the outside faces along their normals) and skew
    hv_, ht_ = _mesh_arrays(hp.data)
    tree = BVHTree.FromPolygons([tuple(x) for x in hv_], [tuple(x) for x in ht_], all_triangles=True)
    lv, lt = _mesh_arrays(tmp.data)
    rng = np.random.default_rng(1)
    pick = rng.choice(len(lt), size=min(3000, len(lt)), replace=False)
    miss = 0
    for i in pick:
        a, b, c = lv[lt[i]]
        nn = np.cross(b - a, c - a)
        nn /= np.linalg.norm(nn) + 1e-12
        cpt = (a + b + c) / 3
        h = tree.ray_cast(Vector((cpt + nn * p["cloak_cage"]).tolist()), Vector((-nn).tolist()),
                          p["cloak_cage"] + p["cloak_ray"])
        if h[0] is None:
            miss += 1
    nv = nrm * 2 - 1
    nv /= np.linalg.norm(nv, axis=-1, keepdims=True) + 1e-9
    skew_raw = float((nv[..., 2] < 0.35).mean())
    # the scan's overlapping layers leave hard steps (lit as pale lines): soften them a
    # little (gaussian, cloak_fold_blur px), then tame the remaining near-grazing normals
    sig = p["cloak_fold_blur"]
    if sig > 0:
        rad_ = int(math.ceil(sig * 2.5))
        wk = np.exp(-0.5 * (np.arange(-rad_, rad_ + 1) / sig) ** 2)
        wk /= wk.sum()
        for ax in (0, 1):
            nv = sum(w_ * np.roll(nv, o_, axis=ax) for o_, w_ in zip(range(-rad_, rad_ + 1), wk))
        nv /= np.linalg.norm(nv, axis=-1, keepdims=True) + 1e-9
    z0 = p["cloak_fold_z"]
    k = np.clip((nv[..., 2] - z0) / 0.35, 0, 1)[..., None]
    nv = nv * k + np.array([0.0, 0.0, 1.0]) * (1 - k)
    nv /= np.linalg.norm(nv, axis=-1, keepdims=True) + 1e-9
    # pieces the sculpt has no cloth for (the hood's lip hugging the face, the procedural
    # sleeve cuffs): their bake found the wrong surface -> flat normals, feathered
    H, W_ = nv.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W_]
    uu, vv = (xx + 0.5) / W_, 1 - (yy + 0.5) / H
    flat = np.zeros((H, W_))
    fe = 12.0 / n
    for u0, u1, v0, v1 in flat_rects:
        du = np.maximum(np.maximum(u0 - uu, uu - u1), 0)
        dv = np.maximum(np.maximum(v0 - vv, vv - v1), 0)
        flat = np.maximum(flat, np.clip(1 - np.hypot(du, dv) / fe, 0, 1))
    nv = nv * (1 - flat[..., None]) + np.array([0.0, 0.0, 1.0]) * flat[..., None]
    nv /= np.linalg.norm(nv, axis=-1, keepdims=True) + 1e-9
    nrm = nv * 0.5 + 0.5
    skew = float((nv[..., 2] < 0.35).mean())
    _remove(tmp)
    textures._save("T_Grimble_Cloak_Normal", np.clip(nrm, 0, 1), non_color=True)
    img2 = bpy.data.images.get("T_Grimble_Cloak_Normal.png")
    for im in bpy.data.images:
        if im.filepath and os.path.basename(im.filepath) == "T_Grimble_Cloak_Normal.png":
            im.reload()
    st = dict(key=key, ray_miss_pct=100.0 * miss / len(pick), skew_pct=100.0 * skew, skew_raw_pct=100.0 * skew_raw,
              res=n,
              seconds=round(time.time() - t0, 1))
    json.dump(st, open(stats_file, "w"))
    log(f"cloak normal bake: {n}px, ray misses {st['ray_miss_pct']:.1f}%, skewed texels {st['skew_pct']:.1f}% "
        f"({st['seconds']}s)")
    return st


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

def _rig(n, col, root, objs, hand_info, shift, toe_info=(), crawl_scale=0.68):
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
    lm["toes"] = list(toe_info)
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
    sv.staff_verts = sv_ - 0.0            # the staff's rest vertices (the crawl drags it)
    grimble_crawl.prepare(sv, crawl_scale)
    grimble_rig.bake_actions(sv, bpy.context.scene, extra=grimble_crawl.actions(sv))
    grimble_rig.LAST_SOLVER = sv            # for probes / QA
    # numbers the engine needs (glTF extras on the root node and the scene)
    for k, v in grimble_crawl.metadata(sv).items():
        root[k] = v
        bpy.context.scene[k] = v
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
    # ================= STAGE 1: high-poly / low-poly split ==========================
    # The sculpt (remeshed, visible shell, classified) is the HIGH-POLY source only:
    #   hp_body  = its fur / skin faces (face, feet) -> body bakes (colour, normal)
    #   hp_cloak = its cloak faces                   -> cloak bake (fold normal map)
    cen = verts[tris].mean(1)
    sline, _ = _staff_line(p)
    d_staff, _ = _dist_polyline(cen, sline)
    hand_zone = (d_staff < 0.55) & (cen[:, 2] < 5.35)                       # the sculpt's upper hand
    face_t = tris[(lab == BODY) & (cen[:, 2] > 4.2) & ~hand_zone]
    cloak_t = tris[lab == CLOAK]
    hires = _object("_grimble_hp_body", _mesh_from_arrays("_grimble_hp_body", verts, tris[lab == BODY]))
    hp_cloak = _object("_grimble_hp_cloak", _mesh_from_arrays("_grimble_hp_cloak", verts, cloak_t))
    face_tree = grimble_cloth._tree(verts, face_t)
    cloak_tree = grimble_cloth._tree(verts, cloak_t)
    hands, _ = _extract_hands(p, verts, tris, lab)
    frame = _face_frame(eyes)
    c_head = frame[0]
    c_, a_, b_, f_ = frame

    # ================= STAGE 2: low-poly modelling ===================================
    # -- the face opening: the outline of the sculpt's fur patch (what the committed
    #    version showed), per angle round the face's axis
    psis_h = np.linspace(-math.pi, math.pi, p["hood_cols"], endpoint=False)
    dface = verts[face_t].mean(1) - c_
    dface /= np.linalg.norm(dface, axis=1, keepdims=True)
    ps_f, th_f = grimble_cloth._psi_th(frame, dface)
    open_th = np.full(len(psis_h), np.nan)
    half = math.pi / len(psis_h) * 1.5
    for j, ps in enumerate(psis_h):
        m = np.abs(np.angle(np.exp(1j * (ps_f - ps)))) < half
        if m.sum() > 5:
            open_th[j] = np.percentile(th_f[m], p["open_pct"])
    ok_ = ~np.isnan(open_th)
    open_th = np.interp(np.arange(len(psis_h)), np.nonzero(ok_)[0], open_th[ok_], period=len(psis_h))
    for _ in range(2):
        open_th = np.convolve(np.r_[open_th[-3:], open_th, open_th[:3]], np.ones(7) / 7, mode="valid")

    def open_fn(psi):
        return np.interp(psi, psis_h, open_th, period=2 * math.pi)

    # -- body: head (face from the sculpt, lids hugging the eyeballs) and feet
    hv, ht, hface = grimble_cloth.head(face_tree, frame, open_fn, p,
                                       eyes=[(c0, R0) for c0, R0 in eyes.values()])
    head_tree = grimble_cloth._tree(hv, ht)

    def head_r(dirs):
        r = grimble_cloth._outermost(head_tree, c_head, dirs, 2.6)
        return np.where(np.isnan(r), 0.5, r)
    parts_v, parts_t, parts_info = [hv], [ht], [("head", 0, len(hv), c_head, frame)]
    off = len(hv)
    feet_t = tris[(lab == BODY) & (cen[:, 2] < 1.0)]
    foot_centres = []
    for fx_, fy_ in p["feet"]:
        fc_ = np.array([fx_, fy_, p["foot_z"]])
        near = feet_t[np.linalg.norm(verts[feet_t].mean(1)[:, :2] - fc_[:2], axis=1) < 0.9]
        fv, ft = grimble_cloth.foot(grimble_cloth._tree(verts, near), fc_, p)
        parts_v.append(fv)
        parts_t.append(ft + off)
        parts_info.append(("foot", off, len(fv), fc_, None))
        foot_centres.append(fc_)
        off += len(fv)
    bv_all = np.concatenate(parts_v)
    bt_all = np.concatenate(parts_t)
    body = _part_object(n + "_Body", bv_all, bt_all, np.ones(len(bt_all), bool), col, root)

    # -- cloak pieces (grids): hood, robe (hem band + single-layer middle + collar band),
    #    sleeves; then fringe and the dark core
    hvz, hW, hD = grimble_cloth.hood(cloak_tree, head_r, frame, psis_h, open_th, p)
    seam_pts = hvz[0]
    th_open_row = np.arccos(np.clip(hD[0] @ f_, -1, 1))

    def hood_cover(pts):
        d = pts - c_
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        elev = np.degrees(np.arcsin(np.clip(d[:, 2], -1, 1)))
        th = np.arccos(np.clip(d @ f_, -1, 1))
        ps = np.arctan2(d @ a_, d @ b_)
        tho = np.interp(ps, psis_h, th_open_row, period=2 * math.pi)
        return np.clip((elev - (p["hood_elev"] - 6)) / 12, 0, 1) * np.clip((th - tho) / 0.15, 0, 1)
    cv_all = verts[cloak_t].reshape(-1, 3)
    axis_pts = []
    for z in np.linspace(0.0, 5.2, 27):
        m = np.abs(cv_all[:, 2] - z) < 0.2
        if m.sum() > 20:
            axis_pts.append([np.median(cv_all[m, 0]), np.median(cv_all[m, 1]), z])
    axis_pts = np.array(axis_pts)
    for k in range(2):
        axis_pts[:, k] = np.convolve(np.pad(axis_pts[:, k], 2, mode="edge"), np.ones(5) / 5, mode="valid")
    fv_ = hv[hface]
    z_chin = float(np.percentile(fv_[:, 2], 3))
    fcen = fv_.mean(0)
    ax46 = np.array([np.interp(4.6, axis_pts[:, 2], axis_pts[:, k]) for k in range(2)])
    th_face = math.atan2(fcen[0] - ax46[0], -(fcen[1] - ax46[1]))
    ax02 = np.array([np.interp(0.2, axis_pts[:, 2], axis_pts[:, k]) for k in range(2)])
    th_feet = [math.atan2(fc_[0] - ax02[0], -(fc_[1] - ax02[1])) for fc_ in foot_centres]

    def robe_top(th):
        w = np.exp(-(np.angle(np.exp(1j * (th - th_face))) / p["robe_front_w"]) ** 2)
        return p["robe_z"][1] - (p["robe_z"][1] - (z_chin + p["robe_chin"])) * w

    def robe_bottom(th):          # the hem rises over the toes, so the claws show
        w = np.max([np.exp(-(np.angle(np.exp(1j * (th - tf))) / p["hem_toe_w"]) ** 2) for tf in th_feet], axis=0)
        return p["robe_z"][0] + p["hem_toe_h"] * w
    rv, rW = grimble_cloth.robe(cloak_tree, p, hood_cover, axis_pts, robe_top, robe_bottom)

    def robe_axis(q):
        return np.array([np.interp(q[2], axis_pts[:, 2], axis_pts[:, 0]),
                         np.interp(q[2], axis_pts[:, 2], axis_pts[:, 1]), q[2]])

    def staff_grip_point(h_):
        sl_line, sl_s = _staff_line(p)
        return sl_line[np.argmin(np.abs(sl_s - h_["s"]))]
    # full sleeves round the arms as the skeleton will build them (the hands are listed
    # upper = right first; the rig works in the shifted frame: origin between the feet)
    mid = np.array([p["feet_mid"][0], p["feet_mid"][1], 0.0])
    sleeve_g = []
    for side, h_ in zip("RL", hands):
        sh_, el_, wr_ = (x + mid for x in grimble_rig.arm_chain(side, np.asarray(h_["wrist"], float) - mid))
        sv_, sW, sref, sinfo = grimble_cloth.sleeve_arm(sh_, el_, wr_, robe_axis(sh_), cloak_tree, p)
        sleeve_g.append((sv_, sW, sref, sinfo, side))

    # ================= STAGE 3: UV layout ============================================
    # UVMap: one unique atlas for the cloak's outside (each grid unwrapped by arc length:
    # no overlaps, seams at the robe's back centre, under the chin inside the collar,
    # under each sleeve), packed at one texel density with padding. UVDetail: world scale.
    metric = {"robe": grimble_cloth.metric_uv(rv), "hood": grimble_cloth.metric_uv(hvz)}
    for k_, (sv_, *_) in enumerate(sleeve_g):
        metric[f"sleeve{k_}"] = grimble_cloth.metric_uv(sv_)
    atlas, cloak_density = grimble_cloth.pack_atlas(metric, p["tex_cloak_unique"], p["uv_pad_px"])
    tile = p["cloak_tile"]

    def uvsets(key, rows=slice(None)):
        Ua, Va = atlas[key]
        Um, Vm = metric[key]
        return [("UVMap", Ua[rows], Va[rows]), ("UVDetail", Um[rows] / tile, Vm[rows] / tile)]
    log(f"cloak UV atlas: {cloak_density:.0f} px/m at {p['tex_cloak_unique']}")

    # -- materials (the glTF contract: see MATERIALS in the module docstring)
    mats = _cloak_materials(p)
    lining_mat = mats[1]
    hood_ob = grimble_cloth.grid_object(n + "_Hood", hvz, uvsets("hood"), hW, lambda q: c_head, col, mats, p)
    # the robe: one solid grid (outside, lining, rims; thick at the hem and the collar), so
    # wherever the crouch shows its inside it is the dark lining, never a hole
    rw_ = rW.copy()
    rw_[-1], rw_[-2] = np.maximum(rw_[-1], 1.0), np.maximum(rw_[-2], 0.5)
    robe_ob = grimble_cloth.grid_object(n + "_Robe", rv, uvsets("robe"), rw_, robe_axis, col, mats, p)
    sleeves = []
    for k_, (sv_, sW, sref, sinfo, side) in enumerate(sleeve_g):
        ob_ = grimble_cloth.grid_object(n + f"_Sleeve{k_}", sv_, uvsets(f"sleeve{k_}"), sW,
                                        lambda q, sref=sref: sref(q), col, mats, p)
        _sleeve_weights(ob_, sinfo, side)
        sleeves.append(ob_)
    # fringe off the hood's rim (round the top and sides): edge material
    frng = np.random.default_rng(p["fringe_seed"])
    keep_rim = np.abs(psis_h) < math.radians(p["fringe_arc"])
    rim = hvz[0][keep_rim]
    rim_out = (hvz[0] - hvz[2])[keep_rim]
    rim_out /= np.linalg.norm(rim_out, axis=1, keepdims=True) + 1e-9
    fv1, ft1 = grimble_cloth.fringe(rim, rim_out, np.array([0, 0, -1.0]), p["fringe_hood"], p["fringe_len"], frng)
    fringe_ob = _small_part(n + "_Fringe", fv1, ft1, col, mats, 2)
    # the gorget: a dark tube along the neck chain (chest -> neck -> into the head), rigid
    # in turn with Spine3, Neck and Head; wherever the collar and the hood's base part in a
    # pose it shows instead of a gap (it replaces the old star-shaped core, whose blended
    # weights tore into shards under the chin)
    trees_ = [grimble_cloth._tree(*_mesh_arrays(ob.data)) for ob in (robe_ob, hood_ob)]
    trees_.append(head_tree)
    ctrl = [np.array(q) + mid for q in grimble_rig.NECK_CHAIN]
    gv, gref, gcurve, garc = grimble_cloth.gorget(ctrl, trees_, p)
    gm = grimble_cloth.metric_uv(gv)
    core_ob = grimble_cloth.grid_object(n + "_Core", gv, [("UVMap", gm[0] * 0.0, gm[1] * 0.0),
                                                           ("UVDetail", gm[0] / tile, gm[1] / tile)],
                                        np.zeros(gv.shape[:2]), gref, col, mats, p, solid=False)
    core_ob.data.polygons.foreach_set("material_index", np.full(len(core_ob.data.polygons), 1, np.int32))
    _chain_weights(core_ob, gcurve, garc, [("Spine3", 0.0), ("Neck", 0.42), ("Head", 0.8)])
    # one cloak object
    vl = bpy.context.view_layer
    for o in vl.objects.selected:
        o.select_set(False)
    for ob in [robe_ob, hood_ob, fringe_ob, core_ob] + sleeves:
        ob.select_set(True)
    vl.objects.active = robe_ob
    bpy.ops.object.join()
    cloak = robe_ob
    cloak.name = n + "_Cloak"
    cloak.data.name = n + "_Cloak"
    cloak.select_set(False)
    cme = cloak.data
    cme.uv_layers.active_index = 0
    for poly in cme.polygons:
        poly.use_smooth = True
    cloak.parent = root
    log(f"body: head {len(ht)} + feet {len(bt_all) - len(ht)} tris; cloak {len(cme.polygons)} tris "
        f"(robe {p['robe_rows']}x{p['robe_cols']}, hood {p['hood_rows']}x{p['hood_cols']})")

    # ================= STAGE 4: bakes ================================================
    # cloak: the sculpt's folds -> a unique tangent-space normal map (outside only)
    flat_rects = []
    Ua, Va = atlas["hood"]
    kl = p["hood_lip_rows"] + 2 + p["hood_brim_rows"]          # the lip and the brim: no sculpt cloth there
    flat_rects.append((Ua[:kl].min(), Ua[:kl].max(), Va[:kl].min(), Va[:kl].max()))
    for k_ in range(len(sleeve_g)):
        Ua, Va = atlas[f"sleeve{k_}"]
        flat_rects.append((Ua.min(), Ua.max(), Va.min(), Va.max()))
    bake_stats = _bake_cloak_normal(cloak, hp_cloak, p, flat_rects)
    _remove(hp_cloak)

    # --- body UVs + textures
    _uv_star(body, parts_info, p)
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
    body_mat = _material("M_Grimble_Body", (0.4, 0.3, 0.22), 0.85,
                         os.path.join(textures.TEX_DIR, names[0] + ".png"),
                         os.path.join(textures.TEX_DIR, names[1] + ".png"), 1.0, specular=p["body_specular"])
    body_mat.use_backface_culling = True
    body.data.materials.append(body_mat)

    # --- eyes
    eb = grimble_paint.eye_texture(p["tex_eye"], force=p["force"])
    eye_mat = _material("M_Grimble_Eye", (0.05, 0.02, 0.01), 0.035, eb)
    eye_objs = [_eye_object(f"{n}_Eye_{side}", c, R, p, col, root, eye_mat) for side, (c, R) in eyes.items()]
    sockets = _socket_object(n + "_Sockets", eyes, p, col, root, lining_mat)

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
    # --- toes (in the hands' mesh: same skin and claw materials), out from under the hem
    fmx, fmy = p["feet_mid"]
    toe_info = grimble_hands.build_toes(bm, uvl, [(fc_, "L" if fc_[0] - fmx > 0 else "R") for fc_ in foot_centres],
                                        rv[0], p)
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
    for ob in (body, cloak):      # nothing below the floor
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
        # the head outside the face opening is inside the hood: in its shadow
        attr = body.data.color_attributes.get(vertex_ao.ATTR)
        if attr is not None:
            ao = np.zeros(len(attr.data) * 4, np.float32)
            attr.data.foreach_get("color", ao)
            ao = ao.reshape(-1, 4)
            hm = np.zeros(len(ao), bool)
            hm[:len(hface)] = ~hface
            ao[hm, :3] = np.minimum(ao[hm, :3], p["head_hidden_ao"])
            attr.data.foreach_set("color", ao.ravel())
        # the cloak's lining (inside the hood, the sleeves, the hem's underside): in shadow
        attr = cloak.data.color_attributes.get(vertex_ao.ATTR)
        if attr is not None:
            ao = np.zeros(len(attr.data) * 4, np.float32)
            attr.data.foreach_get("color", ao)
            ao = ao.reshape(-1, 4)
            mi = np.zeros(len(cloak.data.polygons), np.int64)
            cloak.data.polygons.foreach_get("material_index", mi)
            lv = np.zeros(len(ao), bool)
            for poly in cloak.data.polygons:
                if mi[poly.index] == 1:
                    lv[list(poly.vertices)] = True
            ao[lv, :3] = np.minimum(ao[lv, :3], p["lining_ao"])
            attr.data.foreach_set("color", ao.ravel())
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
        # the eyeballs turn: occlusion baked in the rest pose would swing into view
        for ob in eye_objs:
            attr = ob.data.color_attributes.get(vertex_ao.ATTR)
            if attr is not None:
                attr.data.foreach_set("color", np.ones(len(attr.data) * 4, np.float32))
    if p["rig"]:
        _rig(n, col, root, dict(Body=body, Cloak=cloak, Staff=staff, Sockets=sockets, Hands=hands_ob,
                                Eyes=eye_objs), hand_info, Vector((-fx, -fy, 0)), toe_info, p["crawl_scale"])
        # the crawl body's footprint (from the deformed crawl loops) for the engine's wall push-out
        motion = grimble_qa.motion_checks(root, parts)
        mx = np.max([motion[nm]["foot_max"] for nm in grimble_qa.CRAWL_LOOPS if nm in motion], axis=0)
        for k, v in zip(("bodyFront", "bodyBack", "bodyHalfWidth"), mx):
            root[k] = round(float(v) + 0.01, 2)
            bpy.context.scene[k] = root[k]
    else:
        motion = None
    # ================= STAGE 7: QA ===================================================
    if p["qa"]:
        errs = grimble_qa.run(root, parts, dict(tex_body=p["tex_body"], tex_cloak_unique=p["tex_cloak_unique"],
                                                bake=bake_stats, motion=motion))
        if errs and p["qa_strict"]:
            raise RuntimeError(f"Grimble QA failed: {len(errs)} errors (see QA ERROR lines)")
    log(f"done in {time.time() - t0:.1f}s; tris body {len(body.data.polygons)} cloak {len(cloak.data.polygons)}"
        f" staff {sum(len(pl.vertices) - 2 for pl in staff.data.polygons)}"
        f" hands {sum(len(pl.vertices) - 2 for pl in hands_ob.data.polygons)}"
        f" eyes {sum(len(pl.vertices) - 2 for o in eye_objs for pl in o.data.polygons)}")
    return root, parts


if __name__ == "__main__":
    build()
