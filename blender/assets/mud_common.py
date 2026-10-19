"""Mudroom kit shared by the locker walls (garage_lockers*.py) and the entry coat closet:
garments that hang like fabric (cloth-simulated headless, cached), modelled footwear, an
upholstered bench cushion, and Poly Haven (CC0) scans brought in decimated.

Garments: a garment-shaped closed volume (lofted body, sleeve tubes) is voxel-remeshed into
an even mesh, pinned where it hangs (a hook loop, a hanger's shoulders, a bag's handles),
then dropped under gravity for a few dozen frames in a scene of its own with the locker's
back panel / rail as colliders and self-collision on, and finally decimated to its
triangle budget. The result is cached in build/garment_cache/ keyed by its parameters, so
builds are fast and deterministic (and the asset's vertex-AO cache keeps hitting).

Every function returns plain mesh data (bmesh or object) in garment-local metres; the
assets place them.
"""
import hashlib
import importlib
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)

PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
CACHE = os.path.join(PROJECT, "build", "garment_cache")
VERSION = 5          # bump to invalidate every cached sim


# ------------------------------------------------------------------ geometry helpers

def ring(centre, w, d, n=16, power=3.0, axis_u=(1, 0, 0), axis_v=(0, 1, 0)):
    """Superellipse ring (rounded rectangle for power > 2) around `centre`."""
    c, au, av = Vector(centre), Vector(axis_u), Vector(axis_v)
    out = []
    for k in range(n):
        t = 2 * math.pi * k / n
        ct, st = math.cos(t), math.sin(t)
        x = w * math.copysign(abs(ct) ** (2 / power), ct)
        y = d * math.copysign(abs(st) ** (2 / power), st)
        out.append(c + au * x + av * y)
    return out


def loft(bm, rings, cap_start=True, cap_end=True):
    """Join rings (same vertex count) into a tube; optionally fan-cap the ends."""
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    n = len(rings[0])
    faces = []
    for a, b in zip(vs[:-1], vs[1:]):
        for k in range(n):
            faces.append(bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k])))
    for cap, ring_v, flip in ((cap_start, vs[0], True), (cap_end, vs[-1], False)):
        if cap:
            ctr = bm.verts.new(sum((v.co for v in ring_v), Vector()) / n)
            for k in range(n):
                f = (ring_v[k], ring_v[(k + 1) % n], ctr)
                faces.append(bm.faces.new(f[::-1] if not flip else f))
    return faces


def tube_along(bm, pts, radii, n=12, flat=1.0, up=(0, 1, 0), caps=(True, True)):
    """Loft round (or flattened, flat < 1 along `up`) rings along a polyline."""
    pts = [Vector(p) for p in pts]
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        u = Vector(up).cross(t).normalized()
        v = t.cross(u).normalized()
        rings.append(ring(p, radii[i], radii[i] * flat, n=n, power=2.0, axis_u=u, axis_v=v))
    return loft(bm, rings, *caps)


def rounded_box(size, r, cuts=4, crown=None):
    """Soft box (cushion, folded throw, bag body) without a subdivision modifier: a
    cushion_bmesh grid whose edge band is projected onto a radius-r rounding, so the edges
    read soft at a low triangle count. crown: as common.cushion_bmesh."""
    bm = common.cushion_bmesh(size, cuts=cuts, edge=r, crown=crown)
    h = [s_ / 2 for s_ in size]
    for v in bm.verts:
        p = v.co
        c = Vector([max(-(h[a] - r), min(h[a] - r, p[a])) for a in range(3)])
        n = p - c
        # only the edge band (two or more axes in the band) gets rounded; crowned faces keep their bulge
        band = sum(1 for a in range(3) if abs(p[a]) > h[a] - r + 1e-6)
        if band >= 2 and n.length > 1e-9:
            v.co = c + n.normalized() * r
    return bm


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ cloth simulation

def _dg(scene):
    """The (evaluated) depsgraph of a scene that is not the window's scene."""
    vl = scene.view_layers[0]
    with bpy.context.temp_override(scene=scene, view_layer=vl):
        dg = bpy.context.evaluated_depsgraph_get()
    return dg


def _key(tag, params):
    h = hashlib.sha1(json.dumps([VERSION, tag, params], sort_keys=True, default=str).encode())
    return h.hexdigest()[:16]


def _save_cache(path, me):
    import numpy as np
    extra = {}
    if me.uv_layers:
        uv = np.zeros(2 * len(me.loops), np.float32)
        me.uv_layers[0].data.foreach_get("uv", uv)
        extra["uv"] = uv
    co = np.zeros(3 * len(me.vertices), np.float32)
    me.vertices.foreach_get("co", co)
    counts = np.array([len(p.vertices) for p in me.polygons], np.int32)
    idx = np.zeros(int(counts.sum()), np.int32)
    me.polygons.foreach_get("vertices", idx)
    mats = np.zeros(len(me.polygons), np.int32)
    me.polygons.foreach_get("material_index", mats)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp.npz"
    np.savez_compressed(tmp, co=co, counts=counts, idx=idx, mats=mats, **extra)
    os.replace(tmp, path)


def _load_cache(path):
    import numpy as np
    d = np.load(path)
    co, counts, idx, mats = d["co"].reshape(-1, 3), d["counts"], d["idx"], d["mats"]
    bm = bmesh.new()
    verts = [bm.verts.new(tuple(map(float, c))) for c in co]
    k = 0
    for c, m in zip(counts, mats):
        f = bm.faces.new([verts[i] for i in idx[k:k + c]])
        f.material_index = int(m)
        k += c
    if "uv" in d:
        uv = d["uv"].reshape(-1, 2)
        lay = bm.loops.layers.uv.new("UVMap")
        k = 0
        for f in bm.faces:
            for lp in f.loops:
                lp[lay].uv = tuple(map(float, uv[k]))
                k += 1
    return bm


def simulate(tag, params, make_shape, voxel, pin_fn, colliders=(), frames=48, tris=1200,
             cloth=None, mat_fn=None, solidify=0.0, open_fn=None, details_fn=None):
    """Cloth-drop a garment and return it as a bmesh (cached).

    make_shape() -> bmesh of the garment's closed volume (overlapping parts are fine);
    voxel: remesh voxel size (0 = use the shape's own topology, e.g. a scarf sheet);
    pin_fn(co) -> pin weight 0..1 at rest position co; colliders: list of (lo, hi) boxes;
    mat_fn(co, normal) -> material index for a face at rest; open_fn(co, normal) -> True for
    faces removed after the remesh (an open hem or cuff); tris: decimate target (cloth only);
    details_fn(bvh) -> bmesh of trim (pocket flaps, placket, quilting...) built on the smooth
    rest shape (bvh = BVH of it, e.g. for raycasts) and carried through the sim bound to the
    nearest rest triangle, so details fold with the fabric."""
    params = dict(params, voxel=voxel, frames=frames, tris=tris, cloth=cloth, colliders=list(colliders),
                  solidify=solidify)
    path = os.path.join(CACHE, f"{tag}_{_key(tag, params)}.npz")
    if os.path.exists(path):
        return _load_cache(path)

    scene = bpy.data.scenes.new("MudClothSim")
    scene.frame_start, scene.frame_end = 1, frames
    me = bpy.data.meshes.new("MudCloth")
    make_shape().to_mesh(me)
    ob = bpy.data.objects.new("MudCloth", me)
    scene.collection.objects.link(ob)
    temp = [ob]
    if voxel:
        rm = ob.modifiers.new("Remesh", "REMESH")
        rm.mode = "VOXEL"
        rm.voxel_size = voxel
        rm.adaptivity = 0.0
        dg = _dg(scene)
        new = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        ob.modifiers.clear()
        ob.data = new
        bpy.data.meshes.remove(me)
        me = new
    if open_fn:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if open_fn(f.calc_center_median(), f.normal)], context="FACES")
        bm.to_mesh(me)
        bm.free()
    # pins and materials from the rest shape
    vg = ob.vertex_groups.new(name="pin")
    for v in me.vertices:
        w = pin_fn(v.co)
        if w > 0:
            vg.add([v.index], min(1.0, w), "REPLACE")
    if mat_fn:
        for p in me.polygons:
            p.material_index = mat_fn(p.center, p.normal)
    binding = None
    if details_fn:
        binding = _bind_details(me, details_fn)
    for i, (lo, hi) in enumerate(colliders):
        cm = bpy.data.meshes.new(f"MudCollider{i}")
        bm = common.box_bmesh([hi[a] - lo[a] for a in range(3)])
        bm.to_mesh(cm)
        bm.free()
        co_ob = bpy.data.objects.new(f"MudCollider{i}", cm)
        co_ob.location = [(hi[a] + lo[a]) / 2 for a in range(3)]
        scene.collection.objects.link(co_ob)
        co_ob.modifiers.new("Collision", "COLLISION")
        co_ob.collision.thickness_outer = 0.004
        co_ob.collision.cloth_friction = 8.0
        temp.append(co_ob)
    cm = ob.modifiers.new("Cloth", "CLOTH")
    s = cm.settings
    c = {"mass": 0.3, "tension": 15.0, "shear": 5.0, "bending": 1.0, "air": 2.0, "quality": 7,
         "pressure": 0.0, "shrink": 0.0, **(cloth or {})}
    s.quality = c["quality"]
    s.mass = c["mass"]
    s.tension_stiffness = s.compression_stiffness = c["tension"]
    s.shear_stiffness = c["shear"]
    s.bending_stiffness = c["bending"]
    s.air_damping = c["air"]
    s.tension_damping = s.compression_damping = 5.0
    s.vertex_group_mass = "pin"
    s.pin_stiffness = 1.0
    if c["shrink"]:
        s.shrink_min = c["shrink"]
    if c["pressure"]:
        s.use_pressure = True
        s.uniform_pressure_force = c["pressure"]
    col = cm.collision_settings
    col.use_collision = bool(colliders)
    col.distance_min = 0.004
    col.use_self_collision = True
    col.self_distance_min = 0.003
    col.self_friction = 5.0
    cm.point_cache.frame_start, cm.point_cache.frame_end = 1, frames
    _dg(scene)
    for f in range(1, frames + 1):
        scene.frame_set(f)
    dg = _dg(scene)
    out = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    for o in temp:
        d = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if d is not None and d.users == 0:
            bpy.data.meshes.remove(d)
    bpy.data.scenes.remove(scene)

    # smooth a touch, add thickness if it is a sheet, decimate to budget
    bm = bmesh.new()
    bm.from_mesh(out)
    bpy.data.meshes.remove(out)
    deformed = [v.co.copy() for v in bm.verts]
    if solidify:
        bm = _solidify(bm, solidify)
    _decimate(bm, tris)
    if binding:
        _merge_into(bm, _apply_binding(binding, deformed))
    tmp = bpy.data.meshes.new("MudClothTmp")
    bm.to_mesh(tmp)
    _save_cache(path, tmp)
    bpy.data.meshes.remove(tmp)
    return bm


def _bind_details(me, details_fn):
    """Build the trim on the rest mesh and bind each of its vertices to the nearest rest
    triangle: (triangle vertex indices, barycentric weights, offset along the normal)."""
    from mathutils.bvhtree import BVHTree
    from mathutils.interpolate import poly_3d_calc
    rest = bmesh.new()
    rest.from_mesh(me)
    bmesh.ops.triangulate(rest, faces=rest.faces[:])
    rest.normal_update()
    rest.faces.ensure_lookup_table()
    bvh = BVHTree.FromBMesh(rest)
    det = details_fn(bvh)
    tris = [[v.index for v in f.verts] for f in rest.faces]
    rest_co = [v.co.copy() for v in rest.verts]
    binds = []
    for v in det.verts:
        loc, nor, fi, _ = bvh.find_nearest(v.co)
        ids = tris[fi]
        w = poly_3d_calc([rest_co[i] for i in ids], loc)
        binds.append((ids, w, (v.co - loc).dot(nor)))
    rest.free()
    me_det = bpy.data.meshes.new("MudDetail")
    det.to_mesh(me_det)
    det.free()
    return me_det, binds


def _apply_binding(binding, deformed):
    me_det, binds = binding
    bm = bmesh.new()
    bm.from_mesh(me_det)
    bpy.data.meshes.remove(me_det)
    bm.verts.ensure_lookup_table()
    for v, (ids, w, off) in zip(bm.verts, binds):
        a, b, c = (deformed[i] for i in ids)
        n = (b - a).cross(c - a)
        n = n.normalized() if n.length > 1e-12 else Vector((0, -1, 0))
        v.co = a * w[0] + b * w[1] + c * w[2] + n * off
    return bm


def _solidify(bm, t):
    me = bpy.data.meshes.new("MudSolid")
    bm.to_mesh(me)
    bm.free()
    scene = bpy.data.scenes.new("MudSolidify")
    ob = bpy.data.objects.new("MudSolid", me)
    scene.collection.objects.link(ob)
    m = ob.modifiers.new("Solidify", "SOLIDIFY")
    m.thickness = t
    m.offset = 0.0
    m.use_even_offset = True
    new = bpy.data.meshes.new_from_object(ob.evaluated_get(_dg(scene)))
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me)
    bpy.data.scenes.remove(scene)
    out = bmesh.new()
    out.from_mesh(new)
    bpy.data.meshes.remove(new)
    return out


def _decimate(bm, tris):
    bm.faces.ensure_lookup_table()
    cur = sum(len(f.verts) - 2 for f in bm.faces)
    if cur <= tris:
        return
    me = bpy.data.meshes.new("MudDec")
    bm.to_mesh(me)
    scene = bpy.data.scenes.new("MudDecimate")
    ob = bpy.data.objects.new("MudDec", me)
    scene.collection.objects.link(ob)
    m = ob.modifiers.new("Decimate", "DECIMATE")
    m.decimate_type = "COLLAPSE"
    m.ratio = tris / cur
    m.use_collapse_triangulate = True
    new = bpy.data.meshes.new_from_object(ob.evaluated_get(_dg(scene)))
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me)
    bpy.data.scenes.remove(scene)
    bm.clear()
    bm.from_mesh(new)
    bpy.data.meshes.remove(new)


# ------------------------------------------------------------------ surface details

def surface_patch(bm, bvh, x0, x1, z0, z1, nu=3, nv=2, off=0.002, t=0.005, mat=0, y0=-1.0, bulge=0.0):
    """A thin panel (pocket flap, placket, patch) conforming to the simulated surface as
    seen from the front: grid points raycast along +Y onto the garment, lifted `off` off it,
    `t` thick (top + side walls; the hidden underside is left out). Returns False if any
    ray missed (a deep fold): the detail is skipped rather than left floating."""
    grid = []
    for j in range(nv + 1):
        row = []
        for i in range(nu + 1):
            x = x0 + (x1 - x0) * i / nu
            z = z1 + (z0 - z1) * j / nv
            loc, nor, _, _ = bvh.ray_cast(Vector((x, y0, z)), Vector((0, 1, 0)), 3.0)
            if loc is None or nor.length < 0.5:
                return False
            if nor.y > 0:
                nor = -nor
            b = bulge * math.sin(math.pi * i / nu) * math.sin(math.pi * j / nv) if nu > 1 and nv > 1 else 0.0
            row.append((loc + nor * off, nor, b))
        grid.append(row)
    lo = [[bm.verts.new(p) for p, n, b in row] for row in grid]
    hi = [[bm.verts.new(p + n * (t + b)) for p, n, b in row] for row in grid]
    faces = []
    for j in range(nv):
        for i in range(nu):
            faces.append(bm.faces.new((hi[j][i], hi[j + 1][i], hi[j + 1][i + 1], hi[j][i + 1])))
    ring_idx = [(0, i) for i in range(nu)] + [(j, nu) for j in range(nv)] + \
               [(nv, i) for i in range(nu, 0, -1)] + [(j, 0) for j in range(nv, 0, -1)]
    for k, (j, i) in enumerate(ring_idx):
        j2, i2 = ring_idx[(k + 1) % len(ring_idx)]
        faces.append(bm.faces.new((lo[j][i], lo[j2][i2], hi[j2][i2], hi[j][i])))
    for f in faces:
        f.material_index = mat
    return True


def _bvh(bm):
    from mathutils.bvhtree import BVHTree
    bm.normal_update()
    bm.faces.ensure_lookup_table()
    return BVHTree.FromBMesh(bm)


def _hit(bvh, x, z):
    loc, nor, _, _ = bvh.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)), 3.0)
    return loc


def hem_at(bvh, x, zlo, ztop):
    """Lowest z (1 cm steps) where the garment is hit from the front at x."""
    z = zlo
    while z < ztop:
        if _hit(bvh, x, z) is not None:
            return z
        z += 0.01
    return None


def sides_at(bvh, z, half=0.6):
    """Leftmost / rightmost x hit from the front at height z."""
    xs = [x / 100 for x in range(int(-half * 100), int(half * 100) + 1) if _hit(bvh, x / 100, z) is not None]
    return (xs[0], xs[-1]) if xs else None


def _merge_into(dst, src):
    """Append bmesh `src` to `dst` (keeping material indices) and free src."""
    me = bpy.data.meshes.new("MudMerge")
    src.to_mesh(me)
    src.free()
    dst.from_mesh(me)
    bpy.data.meshes.remove(me)


# ------------------------------------------------------------------ garments

HOOK_COLLIDERS = lambda wall: [((-0.7, wall, -1.3), (0.7, wall + 0.05, 0.3)),          # back panel
                                ((-0.7, wall - 0.035, -0.045), (0.7, wall, 0.045))]      # hook rail


def hook_jacket(length=0.74, width=0.25, depth=0.035, sleeve=0.58, collar=0.07, hood=False, wall=0.08,
                tris=1300, stiff=1.0, pockets="bellows", placket=True, splay=0.55, quilt=0.0, voxel=0.022,
                mass=0.35):
    """A jacket / coat / gilet hung by its collar loop from a hook at the origin (hook tip),
    front -Y, the locker's back panel at y = +wall (the hook rail just in front of it).
    sleeve = 0 makes a gilet (open armholes); quilt = baffle spacing (channel quilting);
    pockets: "bellows" (field jacket), "flap" (coat), None.
    Material indices: 0 shell, 1 collar (corduroy / contrast), 2 trim."""
    params = dict(length=length, width=width, depth=depth, sleeve=sleeve, collar=collar, hood=hood,
                  wall=wall, stiff=stiff, splay=splay, pockets=pockets, placket=placket, quilt=quilt,
                  voxel=voxel, mass=mass)
    top = 0.03                   # collar top, just above the hook tip
    yc = -depth * 0.2            # body centre: the back of the neck sits on the hook
    hem = top - length
    sleeve_dirs = {sx: Vector((sx * math.sin(splay), 0, -math.cos(splay))) for sx in (-1, 1)}
    sh_pts = {sx: Vector((sx * (width - 0.035), yc, top - 0.15)) for sx in (-1, 1)}

    def shape():
        bm = bmesh.new()
        rings = []
        nz = 6 if not quilt else max(6, int((length - 0.24) / quilt * 2))
        zs = [top, top - 0.05, top - 0.11, top - 0.17, top - 0.24]
        zs += [top - 0.24 - (length - 0.24) * k / nz for k in range(1, nz + 1)]
        for z in zs:
            dz = top - z
            w = 0.07 + (width - 0.07) * smoothstep(0.0, 0.20, dz) + 0.01 * smoothstep(0.3, length, dz)
            if not sleeve:       # gilet: cut-in armholes
                w -= 0.03 * smoothstep(0.08, 0.16, dz) * (1 - smoothstep(0.26, 0.34, dz))
            d = depth * (0.9 + 0.3 * smoothstep(0.1, 0.4, dz))
            rings.append(ring((0, yc, z), w, d, n=20, power=3.0))
        loft(bm, rings)
        if sleeve:
            for sx in (-1, 1):
                pts = [sh_pts[sx] + sleeve_dirs[sx] * (sleeve * k / 5) for k in range(6)]
                tube_along(bm, pts, [0.056 - 0.013 * k / 5 for k in range(6)], n=12, flat=0.8, up=(0, 1, 0))
        if hood:
            tube_along(bm, [(0, yc + depth * 0.6, top - 0.02), (0, yc + depth * 1.4, top - 0.14),
                            (0, yc + depth * 1.3, top - 0.24)], [0.09, 0.1, 0.07], n=12, flat=0.5, up=(1, 0, 0))
        return bm

    def opened(c, n):
        if c.z < hem + 0.012 and n.z < -0.6:
            return True
        if sleeve:
            for sx in (-1, 1):
                a = (c - sh_pts[sx]).dot(sleeve_dirs[sx])
                if a > sleeve - 0.012 and n.dot(sleeve_dirs[sx]) > 0.6:
                    return True
        return False

    def pin(co):
        d = (co - Vector((0, yc + depth * 0.9, top - 0.015))).length
        return 1.0 if d < 0.03 else 0.0

    def mat(c, n):
        return 1 if (collar and c.z > top - collar) else 0

    def details(bvh):
        det = bmesh.new()
        if placket:      # storm flap / button stand down the centre front
            surface_patch(det, bvh, -0.024, 0.024, hem + 0.008, top - collar - 0.02, nu=2, nv=16, t=0.003)
        if quilt:        # channel quilting: one puffed panel per baffle, each side of the zip
            z = top - collar - 0.015
            while z - quilt > hem + 0.01:
                sides = sides_at(bvh, z - quilt / 2, half=width + 0.05)
                for sx in (-1, 1):
                    if not sides:
                        continue
                    edge = min(abs(sides[0]), abs(sides[1])) - 0.012
                    xa, xb = sorted((sx * 0.026, sx * edge))
                    surface_patch(det, bvh, xa, xb, z - quilt + 0.001, z - 0.001, nu=4, nv=2, off=0.0005, t=0.0015,
                                  bulge=0.011)
                z -= quilt
        for sx in (-1, 1):
            xc = sx * width * 0.52
            z0 = hem + 0.05
            if pockets == "bellows":     # field-jacket bellows pockets with flaps
                surface_patch(det, bvh, xc - 0.08, xc + 0.08, z0, z0 + 0.15, nu=5, nv=4, t=0.003, bulge=0.005)
                surface_patch(det, bvh, xc - 0.086, xc + 0.086, z0 + 0.125, z0 + 0.18, nu=5, nv=2, off=0.006, t=0.004)
            elif pockets == "flap":      # tailored coat: flap only
                surface_patch(det, bvh, xc - 0.075, xc + 0.075, z0 + 0.14, z0 + 0.19, nu=5, nv=1, off=0.002, t=0.004)
        return det

    return simulate("hook_jacket", params, shape, voxel, pin, HOOK_COLLIDERS(wall), frames=50, tris=tris,
                    cloth={"bending": 2.0 * stiff, "mass": mass}, mat_fn=mat, open_fn=opened,
                    details_fn=details if (placket or pockets or quilt) else None)


def hanger_coat(length=1.0, width=0.24, depth=0.032, sleeve=0.6, collar=0.06, tris=900, stiff=0.8,
                pockets="flap", seed=0):
    """A coat on a hanger: shoulders carried by the hanger bar (pinned along it), the hook
    of the hanger at the origin, front -Y, shoulders along X. (Hung edge-on in the closet:
    rotate it a quarter turn.) Material indices as hook_jacket."""
    params = dict(length=length, width=width, depth=depth, sleeve=sleeve, collar=collar, stiff=stiff,
                  pockets=pockets, seed=seed)
    top = -0.13                 # collar top below the hanger hook
    hem = top - length
    splay = 0.42 + 0.05 * seed
    sleeve_dirs = {sx: Vector((sx * math.sin(splay), 0, -math.cos(splay))) for sx in (-1, 1)}
    sh_pts = {sx: Vector((sx * (width - 0.035), 0, top - 0.09)) for sx in (-1, 1)}

    def shape():
        bm = bmesh.new()
        rings = []
        zs = [top, top - 0.03, top - 0.07, top - 0.12, top - 0.2]
        zs += [top - 0.2 - (length - 0.2) * k / 7 for k in range(1, 8)]
        for z in zs:
            dz = top - z
            w = 0.08 + (width - 0.08) * smoothstep(0.0, 0.10, dz) + 0.02 * smoothstep(0.3, length, dz)
            d = depth * (0.8 + 0.4 * smoothstep(0.05, 0.3, dz))
            rings.append(ring((0, 0, z), w, d, n=20, power=3.0))
        loft(bm, rings)
        for sx in (-1, 1):
            pts = [sh_pts[sx] + sleeve_dirs[sx] * (sleeve * k / 5) for k in range(6)]
            tube_along(bm, pts, [0.055 - 0.013 * k / 5 for k in range(6)], n=12, flat=0.8, up=(0, 1, 0))
        return bm

    def opened(c, n):
        if c.z < hem + 0.012 and n.z < -0.6:
            return True
        for sx in (-1, 1):
            a = (c - sh_pts[sx]).dot(sleeve_dirs[sx])
            if a > sleeve - 0.012 and n.dot(sleeve_dirs[sx]) > 0.6:
                return True
        return False

    def pin(co):
        # the hanger: a bar sloping from the neck down to each shoulder point, inside the coat
        x = abs(co.x)
        if x > width - 0.02:
            return 0.0
        bar_z = top - 0.01 - 0.07 * (x / width)
        return 1.0 if co.z > bar_z - 0.012 else 0.0

    def mat(c, n):
        return 1 if (collar and c.z > top - collar) else 0

    def details(bvh):
        det = bmesh.new()
        surface_patch(det, bvh, -0.022, 0.022, hem + 0.01, top - collar - 0.01, nu=2, nv=14, t=0.003)
        if pockets:
            for sx in (-1, 1):
                xc = sx * width * 0.55
                surface_patch(det, bvh, xc - 0.07, xc + 0.07, hem + 0.3, hem + 0.345, nu=4, nv=1, off=0.002, t=0.004)
        return det

    return simulate("hanger_coat", params, shape, 0.024, pin, (), frames=40, tris=tris,
                    cloth={"bending": 1.5 * stiff, "mass": 0.4}, mat_fn=mat, open_fn=opened, details_fn=details)


def tote(w=0.36, h=0.34, d=0.075, drop=0.17, wall=0.08, tris=700, seed=0):
    """Canvas boat tote hung by both handles over a hook at the origin, front -Y.
    Returns (bag bmesh: open top, material 0 canvas, 1 trim (bottom panel and top band);
    handle bmesh: material 0)."""
    params = dict(w=w, h=h, d=d, drop=drop, wall=wall, seed=seed)
    top = -drop
    yc = 0.005

    def shape():
        bm = bmesh.new()
        rings = []
        for k in range(7):
            z = top - h * k / 6
            f = k / 6
            ww = w / 2 * (1.0 - 0.04 * f)
            dd = d / 2 * (0.5 + 0.5 * math.sin(math.pi * min(1.0, 0.25 + f)))     # fuller at the bottom
            rings.append(ring((0, yc, z), ww, dd, n=24, power=4.0))
        loft(bm, rings)
        return bm

    def opened(c, n):
        return c.z > top - 0.01 and n.z > 0.6

    attach = [(sx * 0.075, yc + sy * d * 0.25) for sx in (-1, 1) for sy in (-1, 1)]

    def pin(co):
        if co.z < top - 0.03:
            return 0.0
        return 1.0 if any(math.hypot(co.x - ax, co.y - ay) < 0.035 for ax, ay in attach) else 0.0

    def details(bvh):          # boat-tote trim: a bottom panel and a top band, sewn on the front
        det = bmesh.new()
        for z0, z1, nv in ((top - h + 0.006, top - h * 0.72, 3), (top - 0.052, top - 0.02, 1)):
            sd = sides_at(bvh, z0, half=w) or (-w * 0.4, w * 0.4)
            x = min(-sd[0], sd[1]) - 0.008
            surface_patch(det, bvh, -x, x, z0, z1, nu=8, nv=nv, t=0.0025, mat=1)
        return det

    bag = simulate("tote", params, shape, 0.018, pin, HOOK_COLLIDERS(wall), frames=45, tris=tris,
                   cloth={"bending": 1.2, "mass": 0.3, "tension": 20.0}, open_fn=opened, details_fn=details)
    hb = bmesh.new()
    for sy in (-1, 1):            # front and back handles, both over the hook
        y0 = yc + sy * d * 0.38
        pts = [(-0.075, y0, top - 0.02), (-0.06, y0 * 0.5, top * 0.45), (-0.02, -0.004, -0.004), (0.0, -0.008, 0.008),
               (0.02, -0.004, -0.004), (0.06, y0 * 0.5, top * 0.45), (0.075, y0, top - 0.02)]
        tube_along(hb, pts, [0.011] * len(pts), n=6, flat=0.28, up=(0, 1, 0))
    return bag, hb


def scarf(width=0.22, front=0.66, back=0.46, wall=0.08, tris=700, t=0.008, seed=0):
    """A wool scarf folded over a hook at the origin, both ends hanging (front one longer).
    A sheet simulated then given thickness. Material 0 wool."""
    params = dict(width=width, front=front, back=back, wall=wall, t=t, seed=seed)
    step = 0.025

    def shape():
        bm = bmesh.new()
        # path: down the back (toward the wall), over the hook, down the front
        path = []
        n_b = int(back / step)
        for k in range(n_b, 0, -1):
            path.append(Vector((0.0, 0.035, 0.012 - k * step)))
        for k in range(5):        # over the hook top
            a = math.pi * k / 4
            path.append(Vector((0.0, 0.035 * math.cos(a) * 0.5 + 0.0, 0.012 + 0.012 * math.sin(a))))
        n_f = int(front / step)
        for k in range(1, n_f + 1):
            path.append(Vector((0.0, -0.022, 0.012 - k * step)))
        nx = max(2, round(width / step))
        rows = []
        for k, p in enumerate(path):
            row = []
            for i in range(nx + 1):
                u = i / nx - 0.5
                g = 0.55 + 0.45 * min(1.0, abs(p.z - 0.012) / 0.12)     # gathered at the hook
                wave = 0.012 * math.sin(7.0 * p.z + 2.0 * u + seed) * (u * 2)
                row.append(bm.verts.new(p + Vector((width * u * g, wave, 0))))
            rows.append(row)
        for r0, r1 in zip(rows[:-1], rows[1:]):
            for i in range(nx):
                bm.faces.new((r0[i], r0[i + 1], r1[i + 1], r1[i]))
        return bm

    def pin(co):
        return 1.0 if co.z > 0.016 and abs(co.x) < width * 0.22 else 0.0

    return simulate("scarf", params, shape, 0.0, pin, HOOK_COLLIDERS(wall), frames=50, tris=tris,
                    cloth={"bending": 0.08, "mass": 0.25, "tension": 8.0, "shear": 2.0}, solidify=t)


def felt_hat(brim=0.165, crown_r=0.092, crown_h=0.115, seg=18):
    """Felt fedora: brim and pinched crown as one lathe, grosgrain band. Origin at the
    centre of the brim plane, crown up +Z. Material 0 felt, 1 band."""
    bm = bmesh.new()
    prof = [(brim, 0.012, 0), (brim - 0.012, 0.004, 0), (crown_r + 0.035, -0.002, 0), (crown_r + 0.004, 0.0, 0),
            (crown_r, 0.004, 1), (crown_r - 0.002, 0.028, 1), (crown_r - 0.006, 0.034, 0),
            (crown_r - 0.012, crown_h * 0.75, 0), (crown_r - 0.03, crown_h, 0), (crown_r * 0.45, crown_h * 0.96, 0),
            (0.0, crown_h * 0.86, 0)]
    rings = []
    for r, z, m in prof:
        ring_v = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            pinch = 1.0 - 0.12 * max(0.0, math.cos(a)) ** 2 * smoothstep(crown_h * 0.6, crown_h, z) if r < crown_r + 0.01 else 1.0
            sy = 1.12 if r < crown_r + 0.01 else 1.06      # oval head shape
            ring_v.append(bm.verts.new((r * math.cos(a) * pinch, r * math.sin(a) * sy, z)))
        rings.append((ring_v, m))
    for (r0, m0), (r1, m1) in zip(rings[:-1], rings[1:]):
        for k in range(seg):
            f = bm.faces.new((r0[k], r0[(k + 1) % seg], r1[(k + 1) % seg], r1[k]))
            f.material_index = 1 if (m0 and m1) else 0
    # underside of the brim (so it reads from below / the side)
    return bm


def umbrella(length=0.86, seg=8):
    """Furled umbrella hanging by its crook handle from a hook at the origin.
    Material 0 canopy, 1 handle (wood/leather), 2 metal (ferrule, tip, runner)."""
    bm = bmesh.new()
    # crook: a J over the hook, opening toward the wall
    crook = [(0.0, 0.028, -0.06), (0.0, 0.03, -0.01), (0.0, 0.018, 0.016), (0.0, -0.004, 0.022),
             (0.0, -0.022, 0.008), (0.0, -0.026, -0.03), (0.0, -0.026, -0.13)]
    tube_along(bm, crook, [0.0125] * len(crook), n=8)
    handle_faces = set(bm.faces)
    zc = -0.13
    # metal collar
    rings = [ring((0, -0.026, zc), 0.011, 0.011, n=8, power=2), ring((0, -0.026, zc - 0.03), 0.009, 0.009, n=8, power=2)]
    collar = loft(bm, rings)
    # furled canopy: fluted, fat in the middle, tapering to the tip
    rings = []
    zs = [zc - 0.03, zc - 0.06, zc - 0.2, zc - 0.38, zc - 0.55, zc - length + 0.1]
    rs = [0.012, 0.03, 0.036, 0.032, 0.022, 0.008]
    for z, r in zip(zs, rs):
        pts = []
        for k in range(seg * 2):
            a = math.pi * k / seg + 0.3 * (z - zc)
            rr = r * (1.0 if k % 2 == 0 else 0.72)
            pts.append(Vector((rr * math.cos(a), -0.026 + rr * math.sin(a), z)))
        rings.append(pts)
    canopy = loft(bm, rings)
    # tie strap round the middle
    rings = [ring((0, -0.026, zc - 0.29), 0.037, 0.037, n=12, power=2), ring((0, -0.026, zc - 0.32), 0.036, 0.036, n=12, power=2)]
    strap = loft(bm, rings)
    tip = loft(bm, [ring((0, -0.026, zc - length + 0.1), 0.006, 0.006, n=6, power=2),
                    ring((0, -0.026, zc - length + 0.02), 0.003, 0.003, n=6, power=2)])
    for f in canopy + strap:
        f.material_index = 0
    for f in collar + tip:
        f.material_index = 2
    for f in handle_faces:
        f.material_index = 1
    return bm


def dog_lead(drop=0.42, wall=0.08):
    """Leather dog lead hung by its hand loop: two strands falling from the hook, the clip
    end swinging lower. Material 0 leather, 1 brass."""
    bm = bmesh.new()
    loop = [(-0.03, 0.01, -drop * 0.55), (-0.02, 0.0, -0.05), (0.0, -0.006, 0.014), (0.02, 0.0, -0.05),
            (0.035, 0.012, -drop * 0.5), (0.03, 0.02, -drop * 0.92), (0.0, 0.022, -drop), (-0.03, 0.015, -drop * 0.9),
            (-0.03, 0.01, -drop * 0.55)]
    loop = common.fillet_polyline(loop, 0.03, segments=3, closed=False)
    tube_along(bm, loop, [0.008] * len(loop), n=4, flat=0.25, up=(0, 1, 0), caps=(False, False))
    tail = [(0.035, 0.012, -drop * 0.5), (0.05, 0.02, -drop * 0.8), (0.055, 0.03, -drop * 1.15)]
    tube_along(bm, tail, [0.008] * 3, n=4, flat=0.25, up=(0, 1, 0))
    clip = loft(bm, [ring((0.055, 0.03, -drop * 1.15), 0.008, 0.005, n=8, power=2),
                     ring((0.056, 0.031, -drop * 1.15 - 0.06), 0.006, 0.004, n=8, power=2)])
    for f in clip:
        f.material_index = 1
    return bm


def leather_bag(w=0.3, h=0.23, d=0.11, strap=0.34):
    """Structured leather bag hanging by a long strap from a hook at the origin, front -Y.
    Material 0 leather, 1 brass."""
    bm = rounded_box((w, d, h), 0.025, cuts=4, crown={"-y": 0.012, "+y": 0.006, "+z": 0.004})
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0.015, -strap - h / 2))
    # flap over the front
    flap = common.cushion_bmesh((w * 0.98, 0.012, h * 0.55), cuts=2, edge=0.006)
    for v in flap.verts:
        v.co.y -= 0.004 * (1 - (v.co.x / (w / 2)) ** 2)
    bmesh.ops.translate(flap, verts=flap.verts, vec=(0, 0.015 - d / 2 - 0.012, -strap - h * 0.25))
    _merge_into(bm, flap)
    # strap: from both ends up over the hook
    for sx in (-1, 1):
        pts = [(sx * (w / 2 - 0.01), 0.015, -strap - 0.01), (sx * w * 0.38, 0.012, -strap * 0.6),
               (sx * 0.06, 0.0, -0.06), (sx * 0.012, -0.006, 0.012)]
        pts = common.fillet_polyline(pts, 0.05, segments=3, closed=False)
        tube_along(bm, pts, [0.012] * len(pts), n=4, flat=0.25, up=(0, 1, 0))
    bk = loft(bm, [ring((0, 0.015 - d / 2 - 0.02, -strap - h * 0.48), 0.014, 0.004, n=8, power=4),
                   ring((0, 0.015 - d / 2 - 0.024, -strap - h * 0.48), 0.014, 0.004, n=8, power=4)])
    for f in bk:
        f.material_index = 1
    return bm


# ------------------------------------------------------------------ footwear

def shoe(kind="trainer", length=0.285, width=0.102, side=1):
    """A modelled shoe, origin under the sole centre, toe toward -Y. side = 1 right, -1 left.
    kind: "trainer" (cupsole, laces, padded collar) or "loafer" (thin sole + heel, low vamp,
    penny strap). Material indices: 0 upper, 1 sole, 2 lining/insole, 3 laces / strap."""
    bm = bmesh.new()
    trainer = kind == "trainer"
    nt = 12
    ts = [0.5 - 0.5 * math.cos(math.pi * k / nt) for k in range(nt + 1)]      # denser at toe and heel

    def half_w(t):          # 0 toe .. 1 heel
        base = 0.86 + 0.14 * math.exp(-((t - 0.3) / 0.18) ** 2) - 0.12 * math.exp(-((t - 0.62) / 0.12) ** 2)
        t = min(max(t, 0.0), 1.0)
        toe = math.sin(0.5 * math.pi * min(1.0, t / 0.2)) ** 0.5
        heel = math.sin(0.5 * math.pi * min(1.0, (1 - t) / 0.12)) ** 0.5
        return width / 2 * base * toe * heel

    def ypos(t):
        return -length / 2 + length * t

    def sole_z(t):          # sole bottom: toe spring
        return 0.014 * (1 - smoothstep(0.0, 0.22, t)) ** 2 if trainer else 0.008 * (1 - smoothstep(0, 0.2, t)) ** 2

    sole_t = (lambda t: 0.024 + 0.004 * t) if trainer else (lambda t: 0.009 if t < 0.72 else 0.026)

    def xoff(t):            # medial curve
        return side * 0.006 * math.sin(math.pi * t) - side * 0.004

    # sole: outline loop, side walls + top (bottom unseen)
    loop_t = ts[1:-1]
    outline = [(t, +1) for t in loop_t] + [(1.0, 0)] + [(t, -1) for t in reversed(loop_t)] + [(0.0, 0)]

    def opt(t, s, grow=0.0):
        return Vector((xoff(t) + s * (half_w(t) + grow), ypos(t), 0))

    bot = [bm.verts.new(opt(t, s, 0.0) + Vector((0, 0, sole_z(t)))) for t, s in outline]
    mid = [bm.verts.new(opt(t, s, 0.005 if trainer else 0.003) + Vector((0, 0, sole_z(t) + sole_t(t) * 0.45)))
           for t, s in outline]
    topv = [bm.verts.new(opt(t, s, 0.003) + Vector((0, 0, sole_z(t) + sole_t(t)))) for t, s in outline]
    n = len(outline)
    sole_faces = [bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k])) for a, b in ((bot, mid), (mid, topv))
                  for k in range(n)]
    for f in sole_faces:
        f.material_index = 1
    ins = bm.faces.new([bm.verts.new(opt(t, s, -0.012) + Vector((0, 0, sole_z(t) + sole_t(t) + 0.001)))
                        for t, s in outline if 0.25 < t < 0.97][::-1])
    ins.material_index = 2
    ins.normal_update()
    if ins.normal.z < 0:
        ins.normal_flip()

    # upper: arches across the foot from one sole edge to the other
    def height(t):
        cap = math.sin(0.5 * math.pi * min(1.0, t / 0.16)) ** 0.6       # rounded toe cap
        if trainer:
            return cap * (0.036 + 0.05 * smoothstep(0.05, 0.5, t)) + 0.01 * smoothstep(0.75, 1.0, t)
        return cap * (0.03 + 0.03 * smoothstep(0.05, 0.5, t)) + 0.006 * smoothstep(0.8, 1.0, t)

    collar_t = 0.6 if trainer else 0.52
    nu = 8
    grid = []
    for t in ts:
        row = []
        for i in range(nu + 1):
            u = i / nu
            if t == 0:          # toe: the arches close to the toe tip
                row.append(bm.verts.new((xoff(0.0), ypos(0.0) + 0.003, sole_z(0.0) + sole_t(0.0) + 0.004)))
                continue
            hw = half_w(t) * 0.97 if t < 1 else 0.0           # heel: a closed back seam
            x = xoff(t) - hw * math.cos(math.pi * u)
            arch = math.sin(math.pi * u) ** 0.55
            if t > collar_t:    # behind the opening the back stays at rim height (a small tab on a trainer)
                arch = min(arch, math.sin(0.2 * math.pi) ** 0.55 + (0.07 if trainer else 0.0) * smoothstep(0.9, 1.0, t))
            z = sole_z(t) + sole_t(t) + height(t) * arch
            row.append(bm.verts.new((x, ypos(t) - (0.003 if t == 1 else 0.0), z)))
        grid.append(row)
    for j in range(nt):
        for i in range(nu):
            t_mid = (ts[j] + ts[j + 1]) / 2
            u_mid = (i + 0.5) / nu
            if t_mid > collar_t and t_mid < 0.97 and 0.2 < u_mid < 0.8:
                continue                                        # the foot opening
            quad = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
            uniq = list(dict.fromkeys(quad))
            if len(uniq) < 3:
                continue
            f = bm.faces.new(uniq)
            f.material_index = 0
    # opening rim: a padded collar (trainer) / binding (loafer)
    rim = []
    j0 = next(j for j in range(nt) if (ts[j] + ts[j + 1]) / 2 > collar_t)
    for j in range(j0, nt):
        rim.append(grid[j][2].co.copy())
    for j in range(nt - 1, j0 - 1, -1):
        rim.append(grid[j][nu - 2].co.copy())
    rim.append(rim[0])
    f0 = len(bm.faces)
    tube_along(bm, rim, [0.008 if trainer else 0.004] * len(rim), n=4, caps=(False, False))
    bm.faces.ensure_lookup_table()
    for f in bm.faces[f0:]:
        f.material_index = 0
    if trainer:   # laces across the instep (tongue under them is the arch itself)
        for k in range(4):
            t = 0.35 + 0.065 * k
            z = sole_z(t) + sole_t(t) + height(t) + 0.003
            hw = half_w(t) * 0.42
            pts = [(xoff(t) - hw, ypos(t), z - 0.008), (xoff(t), ypos(t) + 0.003, z + 0.002), (xoff(t) + hw, ypos(t), z - 0.008)]
            f1 = len(bm.faces)
            tube_along(bm, pts, [0.0028] * 3, n=3, flat=0.6, up=(0, 0, 1), caps=(False, False))
            bm.faces.ensure_lookup_table()
            for f in bm.faces[f1:]:
                f.material_index = 3
    else:         # penny strap across the vamp
        t = collar_t - 0.06
        z = sole_z(t) + sole_t(t) + height(t)
        hw = half_w(t) * 0.98
        pts = [(xoff(t) - hw, ypos(t), z - 0.03), (xoff(t) - hw * 0.6, ypos(t), z - 0.004), (xoff(t), ypos(t), z + 0.003),
               (xoff(t) + hw * 0.6, ypos(t), z - 0.004), (xoff(t) + hw, ypos(t), z - 0.03)]
        f1 = len(bm.faces)
        tube_along(bm, pts, [0.009] * 5, n=4, flat=0.3, up=(0, 0, 1))
        bm.faces.ensure_lookup_table()
        for f in bm.faces[f1:]:
            f.material_index = 3
    bmesh.ops.recalc_face_normals(bm, faces=[f for f in bm.faces if f.material_index in (0,)])
    return bm


# ------------------------------------------------------------------ soft furnishings

def bench_cushion(w, d, h=0.06, welt=0.0065):
    """Upholstered bench cushion: crowned top, boxed sides, a welt round the top edge.
    Origin at the centre of its underside. Material 0 cover, 1 welt."""
    rr = 0.018
    bm = rounded_box((w, d, h), rr, cuts=3, crown={"+z": 0.012, "-y": 0.006, "+y": 0.003, "+x": 0.003, "-x": 0.003})
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, h / 2))
    r = 0.03
    i = rr * 0.29
    zt = h - rr * 0.29
    corners = [(-w / 2 + i, -d / 2 + i, zt), (w / 2 - i, -d / 2 + i, zt), (w / 2 - i, d / 2 - i, zt), (-w / 2 + i, d / 2 - i, zt)]
    pts = common.fillet_polyline(corners, r, segments=3, closed=True)
    pts.append(pts[0])
    f0 = len(bm.faces)
    tube_along(bm, pts, [welt] * len(pts), n=4, caps=(False, False))
    bm.faces.ensure_lookup_table()
    for f in bm.faces[f0:]:
        f.material_index = 1
    return bm


def folded_throw(w=0.42, d=0.28, layer=0.036, layers=2):
    """A wool throw folded in a soft stack, the fold edge toward -Y. Origin at the base centre."""
    bm = bmesh.new()
    for k in range(layers):
        lb = rounded_box((w - 0.006 * k, d - 0.01 * (k % 2), layer), layer * 0.48, cuts=2,
                         crown={"+z": 0.003, "-y": 0.004, "+x": 0.002})
        bmesh.ops.translate(lb, verts=lb.verts, vec=(0.003 * (k % 2), 0.004 * k, layer / 2 + k * (layer - 0.002)))
        _merge_into(bm, lb)
    return bm


# ------------------------------------------------------------------ Poly Haven scans

SCANS = os.path.join(PROJECT, "build", "polyhaven", "models")


def scan_texture(ph_id, mapname, ours):
    """Copy a scan's 1k map into assets/textures as `ours` (once); returns the path."""
    import shutil
    dst = os.path.join(textures.TEX_DIR, ours + ".jpg")
    if not os.path.exists(dst):
        src = os.path.join(SCANS, ph_id, "textures", f"{ph_id}_{mapname}_1k.jpg")
        shutil.copyfile(src, dst + ".tmp")
        os.replace(dst + ".tmp", dst)
    return dst


def scan_material(name, ph_id, prefix, roughness, fallback=(0.3, 0.3, 0.3), normal=1.0, maps=("diff", "nor_gl")):
    """Principled material from a scan's base colour + normal (the ARM map is dropped:
    flat roughness), textures saved as <prefix>_BaseColor / _Normal. Without the scan (and
    without the copies in assets/textures) it is a flat `fallback` colour instead."""
    m = common.pbr_material(name, (1, 1, 1), roughness=roughness)
    if not any(n.type == "TEX_IMAGE" for n in m.node_tree.nodes):
        try:
            base = scan_texture(ph_id, maps[0], prefix + "_BaseColor")
            nor = scan_texture(ph_id, maps[1], prefix + "_Normal")
        except OSError as e:
            print(f"mud_common: scan textures for {ph_id} unavailable ({e}); flat colour")
            return common.pbr_material(name, fallback, roughness=roughness)
        common.set_base_color_map(m, textures.load(base))
        common.set_normal_map(m, textures.load(nor, non_color=True), normal)
    return m


def scan_mesh(ph_id, objects, tris, scale=1.0, rotate_z=0.0):
    """Import a Poly Haven model (fetched once into build/polyhaven), keep `objects`, join,
    centre it on its footprint with the bottom at z = 0, scale, decimate to `tris` (UVs kept).
    Cached in build/garment_cache/. Returns a bmesh with a "UVMap" layer, or None if the
    model can't be had (no network on first build): callers fall back to modelled pieces."""
    params = dict(ph_id=ph_id, objects=list(objects), tris=tris, scale=scale, rotate_z=rotate_z)
    path = os.path.join(CACHE, f"scan_{ph_id}_{_key('scan', params)}.npz")
    if os.path.exists(path):
        return _load_cache(path)
    gltf = os.path.join(SCANS, ph_id, f"{ph_id}_1k.gltf")
    if not os.path.exists(gltf):
        try:
            sys.path.insert(0, os.path.join(PROJECT, "blender", "tools"))
            import polyhaven_models
            gltf = polyhaven_models.fetch_model(ph_id)
        except Exception as e:  # offline: fall back
            print(f"mud_common: Poly Haven model {ph_id} unavailable ({e})")
            return None
    scene = bpy.data.scenes.new("MudScan")
    before_obs, before_mats, before_imgs = set(bpy.data.objects), set(bpy.data.materials), set(bpy.data.images)
    before_meshes = set(bpy.data.meshes)
    with bpy.context.temp_override(scene=scene, view_layer=scene.view_layers[0]):
        bpy.ops.import_scene.gltf(filepath=gltf)
    new = [o for o in bpy.data.objects if o not in before_obs]
    bm = bmesh.new()
    for o in new:
        if o.type == "MESH" and o.name in objects:
            me = o.data.copy()
            me.transform(o.matrix_world)
            me.materials.clear()
            bm.from_mesh(me)
            bpy.data.meshes.remove(me)
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    for m in [m for m in bpy.data.meshes if m not in before_meshes and m.users == 0]:
        bpy.data.meshes.remove(m)
    for m in [m for m in bpy.data.materials if m not in before_mats]:
        bpy.data.materials.remove(m)
    for i in [i for i in bpy.data.images if i not in before_imgs]:
        bpy.data.images.remove(i)
    bpy.data.scenes.remove(scene)
    for f in bm.faces:
        f.material_index = 0
    xs, ys, zs = ([v.co[a] for v in bm.verts] for a in range(3))
    off = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)))
    mat = Matrix.Rotation(rotate_z, 4, "Z") @ Matrix.Scale(scale, 4) @ Matrix.Translation(-off)
    bmesh.ops.transform(bm, matrix=mat, verts=bm.verts)
    _decimate(bm, tris)
    tmp = bpy.data.meshes.new("MudScanTmp")
    bm.to_mesh(tmp)
    _save_cache(path, tmp)
    bpy.data.meshes.remove(tmp)
    return bm
