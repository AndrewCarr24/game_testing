"""Dead wood and rock for the wilderness kits: fallen logs (chestnut ghosts, root-wad blowdowns, a log
propped on a boulder), stumps, creek boulders. Called by trees.build_species for kinds log / stump /
rock; same file contract as the plants (Veg_<Id>_LOD0..2, COLOR_0 = AO, a zero _wind so one shader
fits all, veg.json entry) plus collision and climb hints.

Geometry is regenerated per LOD from the same parameters (sides, rings, subdivision). Moss is a
material, not a decal: faces that face the sky (n.z, plus noise) get the moss tile (the moss_01 scan
composed into a repeating mat), so caps have the moss's own texture and read at any distance.
AO: hemisphere rays against the LOD0 mesh (BVH) plus the ground plane; lib/vertex_ao.py skips faces
over 0.25 m2, which a 1 m-thick log's faces are.
"""
import math
import os
import random
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector, noise
from mathutils.bvhtree import BVHTree

import trees
from trees import MeshData, UP, node_name

N3 = "three.js frame: x, y up, z = -y_blender"


def _three(v):
    return [round(float(v[0]), 3), round(float(v[2]), 3), round(float(-v[1]), 3)]


# =============================================================================================
# materials
def _material(name, tex, nor=None, rough=0.9):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = trees._image(tex, "sRGB")
    nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    if nor:
        ni = nt.nodes.new("ShaderNodeTexImage")
        ni.image = trees._image(nor, "Non-Color")
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = 0.9
        nt.links.new(ni.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def materials(base_id, sp):
    """roles: bark (wood or bark), moss, soil (root wads), rock -> (mats dict, textures dict for veg.json)."""
    mats, tex = {}, {}
    for role in ("bark", "soil", "rock"):
        if sp.get(role):
            t = trees.prep_textures(base_id, {"bark": sp[role]})
            mats[role] = _material(f"M_Veg_{os.path.basename(t['bark'][0])[6:-4]}", t["bark"][0],
                                   t.get("bark_nor", (None,))[0], sp[role].get("rough", 0.9))
            tex[role] = t["bark"][0]
            if "bark_nor" in t:
                tex[role + "_nor"] = t["bark_nor"][0]
    if sp.get("moss", 0) > 0:
        tile = trees.leaf_atlas("br_ground")["tiles"]["moss_tile"]
        p = os.path.join(trees.PREP, tile["albedo"])
        pn = os.path.join(trees.PREP, tile["normal"])
        mats["moss"] = _material("M_Veg_Moss_Tile", p, pn, 0.85)
        tex["moss"], tex["moss_nor"] = p, pn
    return mats, tex


# =============================================================================================
# logs
def log_axis(P, rng):
    """Centre line samples (x along the log, z the centre height) and radius per sample."""
    L, r0 = P["length"], P["radius"]
    n = max(8, int(L / 0.25))
    xs = np.linspace(0, L, n + 1)
    ph = rng.uniform(0, 6.28)
    bend = P.get("bend", 0.25)
    out = []
    for x in xs:
        t = x / L
        r = r0 * (1 - P.get("taper", 0.35) * t) * (1 + 0.06 * math.sin(t * 9 + ph))
        y = bend * math.sin(math.pi * t + ph * 0.2) - bend * math.sin(ph * 0.2)
        z = r * (1 - P.get("sink", 0.12))
        if P.get("wad"):                       # the trunk rises into its root plate
            h0 = P["wad"]["lift"]
            xs_ = P["wad"].get("reach", 4.0)
            if x < xs_:
                z = max(z, r + h0 * (1 - x / xs_) ** 1.6)
        if P.get("prop"):                      # one end resting on a boulder
            px, ph_ = P["prop"]["x"], P["prop"]["height"]
            z = r * (1 - P.get("sink", 0.12)) + ph_ * min(1.0, x / px) ** 1.3 if x <= px else r + ph_
        out.append((float(x), float(y), float(z), float(r)))
    return out


def log_mesh(md, P, axis, sides, step, mats_i, rng, moss_k):
    """Tube along the axis with a lumpy, split cross-section, a jagged broken tip and a cut or broken base."""
    tile = P.get("tile") or P["bark"]["tile"]
    pts = axis[::step] + ([axis[-1]] if (len(axis) - 1) % step else [])
    rings = []
    urep = max(1, round(2 * math.pi * P["radius"] / tile[0]))
    seed = rng.uniform(0, 100)
    for k, (x, y, z, r) in enumerate(pts):
        if k < len(pts) - 1:
            d = Vector((pts[k + 1][0] - x, pts[k + 1][1] - y, pts[k + 1][2] - z)).normalized()
        else:
            d = Vector((x - pts[k - 1][0], y - pts[k - 1][1], z - pts[k - 1][2])).normalized()
        side = d.cross(UP).normalized()
        upv = side.cross(d).normalized()
        ring = []
        for j in range(sides + 1):
            a = 2 * math.pi * j / sides
            q = Vector((math.cos(a) * 1.3, math.sin(a) * 1.3, x * 0.7 + seed))
            lump = 1 + 0.09 * noise.noise(q) + 0.05 * math.sin(5 * a + seed)
            if P.get("split"):                 # long checks: grooves along the grain
                lump -= 0.08 * max(0.0, math.cos(7 * a + seed)) ** 8
            dirv = side * math.cos(a) + upv * math.sin(a)
            p = Vector((x, y, z)) + dirv * (r * lump)
            p.z = max(p.z, -0.05)
            ring.append((p, dirv, (urep * j / sides, x / tile[1])))
        rings.append(ring)
    vid = []
    for ring in rings:
        vid.append([md.vert(p, n, (0.0, 0.0, 0.0)) for p, n, _ in ring])
    for k in range(len(rings) - 1):
        for j in range(sides):
            a, b = rings[k][j], rings[k][j + 1]
            c, d = rings[k + 1][j + 1], rings[k + 1][j]
            nz = (a[1].z + c[1].z) / 2
            mid = (a[0] + c[0]) / 2
            m = _moss_w(mid, nz, moss_k, seed)
            mat = mats_i["moss"] if m and "moss" in mats_i else mats_i["bark"]
            uv = [a[2], b[2], c[2], d[2]]
            if mat == mats_i.get("moss"):
                uv = [(q[0].x / 0.25 + q[0].y / 0.25 * 0.3, q[0].y / 0.25) for q in (a, b, c, d)]
            md.face((vid[k][j], vid[k][j + 1], vid[k + 1][j + 1], vid[k + 1][j]), uv, mat)
    # broken tip: a splintered fan
    x, y, z, r = pts[-1]
    tip = rings[-1]
    d = (tip[0][0] - rings[-2][0][0]).normalized()
    cen = Vector((x, y, z)) + d * (r * 0.4)
    ci = md.vert(cen, d, (0, 0, 0))
    for j in range(sides):
        sp = tip[j][0] + d * (r * rng.uniform(0.0, 1.4) if P.get("broken_tip", True) else 0)
        si = md.vert(sp, d, (0, 0, 0))
        nxt = tip[j + 1][0]
        ni = md.vert(nxt, d, (0, 0, 0))
        md.face((vid[-1][j], si, ci), [(0, 0), (0.1, 0.2), (0.2, 0)], mats_i["bark"])
        md.face((si, vid[-1][j + 1], ci), [(0.1, 0.2), (0.2, 0), (0, 0)], mats_i["bark"])
    if not P.get("wad"):                       # cut / broken base cap
        x, y, z, r = pts[0]
        c0 = md.vert(Vector((x - r * 0.15, y, z)), Vector((-1, 0, 0)), (0, 0, 0))
        for j in range(sides):
            md.face((vid[0][j + 1], vid[0][j], c0), [(0, 0), (0.2, 0), (0.1, 0.2)], mats_i["bark"])


def _moss_w(p, nz, k, seed):
    if k <= 0:
        return False
    n = noise.noise(Vector((p.x * 0.8, p.y * 0.8, p.z * 0.8 + seed)))
    return nz + 0.35 * n > 1.05 - 0.6 * k


def root_wad(md, P, axis, segs, rings_n, mats_i, rng):
    """Uprooted root plate: a lumpy vertical disc of soil and roots at the base end, roots radiating."""
    W = P["wad"]
    x0, y0, z0, r0 = axis[0]
    R = W["radius"]
    c = Vector((x0 - 0.15, y0, max(z0, R * 0.92)))
    th = W.get("thick", 0.7)
    ph = rng.uniform(0, 10)
    front, back = [], []
    for i in range(rings_n + 1):
        rf = i / rings_n
        fr, bk = [], []
        for j in range(segs if i else 1):
            a = 2 * math.pi * j / segs
            wob = 1 + 0.32 * noise.noise(Vector((math.cos(a) * 1.6, math.sin(a) * 1.6, ph))) + 0.1 * math.sin(5 * a + ph)
            yy, zz = math.cos(a) * R * rf * wob, math.sin(a) * R * rf * wob
            bump = 0.35 * (1 - rf * rf) + 0.22 * noise.noise(Vector((yy * 1.5, zz * 1.5, ph + 3)))
            pf = Vector((c.x - th / 2 - bump, c.y + yy, max(-0.1, c.z + zz)))
            pb = Vector((c.x + th / 2 + bump * 0.6, c.y + yy, max(-0.1, c.z + zz)))
            fr.append(md.vert(pf, Vector((-1, yy * 0.3, zz * 0.3)).normalized(), (0, 0, 0)))
            bk.append(md.vert(pb, Vector((1, yy * 0.3, zz * 0.3)).normalized(), (0, 0, 0)))
        front.append(fr)
        back.append(bk)
    tile = 1.2

    def uv(v):
        q = md.co[v]
        return (q[1] / tile, q[2] / tile)
    for i in range(rings_n):
        for j in range(segs):
            j2 = (j + 1) % segs
            for ring, flip in ((front, False), (back, True)):
                if i == 0:
                    f = (ring[0][0], ring[1][j], ring[1][j2])
                else:
                    f = (ring[i][j], ring[i + 1][j], ring[i + 1][j2], ring[i][j2])
                f = tuple(reversed(f)) if flip else f
                md.face(f, [uv(v) for v in f], mats_i["soil"])
    for j in range(segs):                      # the rim
        j2 = (j + 1) % segs
        f = (front[-1][j], back[-1][j], back[-1][j2], front[-1][j2])
        md.face(f, [(j / segs * 4, 0), (j / segs * 4, 0.5), (j2 / segs * 4, 0.5), (j2 / segs * 4, 0)], mats_i["soil"])
    # roots: tapering tubes from the plate's face, curling down and out
    for k in range(W.get("roots", 10)):
        a = 2 * math.pi * (k + rng.uniform(-0.3, 0.3)) / W.get("roots", 10)
        start = c + Vector((-th / 2, math.cos(a) * R * rng.uniform(0.3, 0.8), math.sin(a) * R * rng.uniform(0.3, 0.8)))
        dirv = Vector((-rng.uniform(0.1, 0.4), math.cos(a), math.sin(a) - 0.5)).normalized()
        Lr = rng.uniform(0.35, 0.9) * R
        pts = [start]
        for q in range(4):
            dirv = (dirv + Vector((0, 0, -0.25))).normalized()
            pts.append(pts[-1] + dirv * (Lr / 4))
        b = trees.Branch(pts, 0)
        rr = rng.uniform(0.07, 0.16)
        b.rad = [rr * (1 - q / 4) ** 0.9 + 0.015 for q in range(5)]
        b.path0 = 0.0
        b.phase = 0.0
        trees.tube(md, b, W.get("root_sides", 5), 1, (0.8, 0.8), 1.0, mat=mats_i["soil"], cap=True)
    return c


def stubs(md, P, axis, rng, sides, mats_i):
    for k in range(P.get("stubs", 0)):
        i = rng.randrange(len(axis) // 5, len(axis) - 2)
        x, y, z, r = axis[i]
        a = rng.uniform(-0.6, math.pi + 0.6)
        d = Vector((rng.uniform(-0.3, 0.3), math.cos(a), math.sin(a))).normalized()
        base = Vector((x, y, z)) + d * (r * 0.7)
        L = rng.uniform(0.3, 1.1)
        b = trees.Branch([base, base + d * (L * 0.5), base + d * L], 0)
        rs = rng.uniform(0.05, 0.12) * P["radius"] / 0.6
        b.rad = [rs, rs * 0.75, rs * 0.4]
        b.path0, b.phase = 0.0, 0.0
        trees.tube(md, b, sides, 1, P["bark"]["tile"], 1.0, mat=mats_i["bark"], cap=True)


# =============================================================================================
# stumps
def stump_mesh(md, P, sides, rings, mats_i, rng, moss_k):
    H, r0 = P["height"], P["radius"]
    seed = rng.uniform(0, 100)
    tile = P.get("tile") or P["bark"]["tile"]
    urep = max(1, round(2 * math.pi * r0 / tile[0]))
    lobes = P.get("lobes", 5)
    rows = []
    top = []
    for i in range(rings + 1):
        t = i / rings
        z = -0.1 + (H + 0.1) * t
        row = []
        for j in range(sides + 1):
            a = 2 * math.pi * j / sides
            fl = 1 + P.get("flare", 0.6) * math.exp(-max(z, 0) / 0.35) * (0.55 + 0.45 * math.cos(lobes * a + seed))
            lump = 1 + 0.07 * noise.noise(Vector((math.cos(a) * 1.5, math.sin(a) * 1.5, z + seed)))
            rr = r0 * fl * lump * (1 - 0.1 * t)
            zz = z
            if i == rings:                     # broken: jagged splinters; sawn: flat, slightly tilted
                zz = H + (rng.uniform(-0.35, 0.25) * H * (0.5 + 0.5 * math.cos(3 * a + seed)) if P.get("broken")
                          else 0.05 * math.cos(a))
            p = Vector((math.cos(a) * rr, math.sin(a) * rr, zz))
            row.append((md.vert(p, Vector((math.cos(a), math.sin(a), 0.1)).normalized(), (0, 0, 0)),
                        (urep * j / sides, zz / tile[1]), p))
        rows.append(row)
    for i in range(rings):
        for j in range(sides):
            a, b, c, d = rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]
            mid = (a[2] + c[2]) / 2
            m = _moss_w(mid, 0.25 + 0.5 * math.exp(-max(mid.z, 0) / 0.25), moss_k * 0.8, seed)
            mat = mats_i["moss"] if m and "moss" in mats_i else mats_i["bark"]
            uv = [a[1], b[1], c[1], d[1]] if mat == mats_i["bark"] else [(q[2].x / 0.25, q[2].y / 0.25 + q[2].z / 0.25) for q in (a, b, c, d)]
            md.face((a[0], b[0], c[0], d[0]), uv, mat)
    # top: a cap (sawn face rings, or a pit of rotted wood for the broken one)
    cz = H - (0.25 * H if P.get("broken") else 0.0)
    ci = md.vert(Vector((0, 0, cz)), UP, (0, 0, 0))
    for j in range(sides):
        a, b = rows[-1][j], rows[-1][j + 1]
        mat = mats_i["moss"] if (moss_k > 0.5 and not P.get("broken") and "moss" in mats_i) else mats_i["bark"]
        md.face((a[0], b[0], ci), [(a[2].x / 0.4, a[2].y / 0.4), (b[2].x / 0.4, b[2].y / 0.4), (0, 0)], mat)


# =============================================================================================
# rocks
def rock_mesh(md, P, subdiv, mats_i, rng, moss_k, at=Vector((0, 0, 0)), dims=None):
    """Water-worn gneiss boulder: a noise-displaced, plane-cut icosphere, flat bottom, moss on top."""
    import bmesh
    sx, sy, sz = dims or P["dims"]
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    seed = rng.uniform(0, 100)
    planes = [(_rand_dir(rng), rng.uniform(0.55, 0.85)) for _ in range(P.get("facets", 5))]
    for v in bm.verts:
        p = v.co.copy()
        n = noise.noise(p * 1.3 + Vector((seed, 0, 0)))
        n2 = noise.noise(p * 3.1 + Vector((0, seed, 0)))
        p *= 1 + 0.16 * n + 0.05 * n2
        for pn, d in planes:                   # joint planes: flattened facets, rounded by the noise
            k = p.dot(pn) - d
            if k > 0:
                p -= pn * (k * 0.85)
        p = Vector((p.x * sx / 2, p.y * sy / 2, p.z * sz / 2))
        p.z = max(p.z + sz * 0.38, -0.08) if p.z < 0 else p.z + sz * 0.38
        v.co = p
    bm.normal_update()
    me = bpy.data.meshes.new("tmp_rock")
    bm.to_mesh(me)
    bm.free()
    me.calc_loop_triangles()
    tile = P.get("tile", 1.6)
    base = len(md.co)
    nrm = [v.normal.copy() for v in me.vertices]
    for v, n in zip(me.vertices, nrm):
        md.vert(v.co + at, n, (0, 0, 0))
    for poly in me.polygons:
        vs = list(poly.vertices)
        c = poly.center
        n = poly.normal
        mossy = _moss_w(c, n.z, moss_k, seed) and c.z > sz * 0.3
        if mossy and "moss" in mats_i:
            uv = [((me.vertices[i].co.x) / 0.25, (me.vertices[i].co.y) / 0.25) for i in vs]
            mat = mats_i["moss"]
        else:
            ax = int(np.argmax([abs(n.x), abs(n.y), abs(n.z)]))
            uv = []
            for i in vs:
                q = me.vertices[i].co
                u, w = [(q.y, q.z), (q.x, q.z), (q.x, q.y)][ax]
                uv.append((u / tile, w / tile))
            mat = mats_i["rock"]
        md.face(tuple(base + i for i in vs), uv, mat)
    bpy.data.meshes.remove(me)


def _rand_dir(rng):
    while True:
        v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.6, 1)))
        if 0.1 < v.length <= 1:
            return v.normalized()


# =============================================================================================
# AO: hemisphere rays against LOD0 + ground
def ray_ao(objs, rays=24, dist=1.6, strength=0.75):
    me0 = objs[0].data
    co0 = [v.co.copy() for v in me0.vertices]
    bvh = BVHTree.FromPolygons(co0, [tuple(p.vertices) for p in me0.polygons])
    rr = random.Random(3)
    dirs = []
    for i in range(rays):                      # cosine-weighted hemisphere
        u, v = (i + 0.5) / rays, rr.random()
        r, a = math.sqrt(u), 2 * math.pi * v
        dirs.append(Vector((r * math.cos(a), r * math.sin(a), math.sqrt(max(0, 1 - u)))))
    for ob in objs:
        me = ob.data
        ao = np.zeros(len(me.vertices), np.float32)
        nr = me.attributes.get("bake_n")
        for vi, v in enumerate(me.vertices):
            n = Vector(nr.data[vi].vector) if nr else v.normal
            if n.length < 1e-6:
                n = UP
            rot = n.to_track_quat("Z", "Y").to_matrix()
            hit = 0.0
            o = v.co + n * 0.02
            for d in dirs:
                w = rot @ d
                if w.z < 0 and (o.z / -w.z) < dist:      # the ground
                    hit += 1
                    continue
                if bvh.ray_cast(o, w, dist)[0] is not None:
                    hit += 1
            ao[vi] = 1 - strength * hit / rays
        ao *= 1 - 0.3 * np.exp(-np.maximum(np.array([v.co.z for v in me.vertices]), 0) / 0.15)
        ao = np.round(np.clip(ao, 0.15, 1) * 16) / 16
        attr = me.color_attributes.get("AO") or me.color_attributes.new("AO", "FLOAT_COLOR", "POINT")
        attr.data.foreach_set("color", np.stack([ao, ao, ao, np.ones_like(ao)], 1).ravel())
        me.color_attributes.active_color = attr


# =============================================================================================
def build(sp_name, base_id, v, sp0, seed, preview=True):
    t0 = time.time()
    sp = trees.variant_params(sp0, v, random.Random(seed + 1))
    if sp.get("variant_size"):
        sp["dims"] = sp["variant_size"][(v - 1) % len(sp["variant_size"])]
    if sp.get("variant_over"):
        sp.update(sp["variant_over"][(v - 1) % len(sp["variant_over"])])
    seed = seed + 101 * (v - 1) + sp.get("seed_off", 0)
    col = bpy.data.collections.new(node_name(sp_name))
    bpy.context.scene.collection.children.link(col)
    mats, tex = materials(base_id, sp)
    roles = [r for r in ("bark", "soil", "rock", "moss") if r in mats]
    mi = {r: i for i, r in enumerate(roles)}
    root_ob = bpy.data.objects.new(node_name(sp_name), None)
    col.objects.link(root_ob)
    objs, lod_info = [], []
    climb, collider = {}, None
    for li, lod in enumerate(sp["lods"]):
        rng = random.Random(seed)              # the same shape in every LOD
        md = MeshData()
        k = sp["kind"]
        if k == "log":
            axis = log_axis(sp, rng)
            log_mesh(md, sp, axis, lod["sides"], lod["step"], mi, rng, sp.get("moss", 0))
            if lod.get("stubs", True):
                stubs(md, sp, axis, rng, max(3, lod["sides"] // 3), mi)
            if sp.get("wad"):
                wc = root_wad(md, sp, axis, lod["wad_segs"], lod["wad_rings"], mi, rng)
            if sp.get("prop"):
                pr = sp["prop"]
                ax = axis[min(len(axis) - 1, int(pr["x"] / sp["length"] * (len(axis) - 1)))]
                rock_mesh(md, dict(facets=4, tile=1.6), lod["subdiv"], mi, random.Random(seed + 9), sp.get("moss", 0),
                          at=Vector((ax[0], ax[1] - 0.1, -0.02)), dims=pr["boulder"])
            if li == 0:
                collider, climb = log_hints(sp, axis, wc if sp.get("wad") else None)
        elif k == "stump":
            stump_mesh(md, sp, lod["sides"], lod["rings"], mi, rng, sp.get("moss", 0))
            if li == 0:
                collider = dict(type="cylinder", radius=round(sp["radius"] * 1.05, 2), height=round(sp["height"], 2))
                climb = dict(top_height=round(sp["height"], 2), jump_onto=sp["height"] <= 0.9)
        elif k == "rock":
            rock_mesh(md, sp, lod["subdiv"], mi, rng, sp.get("moss", 0))
            if li == 0:
                dx, dy, dz = sp["dims"]
                collider = dict(type="ellipsoid", center=[0.0, round(dz * 0.4, 2), 0.0],
                                radii=[round(dx / 2 * 0.95, 2), round(dz * 0.55, 2), round(dy / 2 * 0.95, 2)])
                climb = dict(top_height=round(dz * 0.88, 2), jump_onto=dz * 0.88 <= 0.9)
        ob = trees.to_object(f"{node_name(sp_name)}_LOD{li}", md, mats, roles, col)
        ob.parent = root_ob
        objs.append(ob)
        by = {r: sum(len(f) - 2 for f, m in zip(md.faces, md.mat) if m == i) for i, r in enumerate(roles)}
        lod_info.append(dict(name=ob.name, tris=md.tris(), verts=len(md.co), draw_calls=sum(1 for r in roles if by.get(r)),
                             **{f"{r}_tris": by[r] for r in roles}))
    ray_ao(objs, strength=sp.get("ao_strength", 0.7))
    path, (size, size_tex), doc = trees.export(sp_name, root_ob)
    info = dict(title=sp["title"], gltf=os.path.basename(path), bytes_geometry=size, bytes_textures=size_tex,
                lods=lod_info, lod_dist=sp["lod_dist"], cards=0, seed=seed,
                height_m=round(max(v_.co.z for v_ in objs[0].data.vertices), 2),
                textures={r: [os.path.basename(p), bpy.data.images[os.path.splitext(os.path.basename(p))[0]].size[0]]
                          for r, p in tex.items()})
    for k_ in ("kind", "group", "latin", "community", "reference", "notes"):
        if k_ in sp0:
            info[k_] = sp0[k_]
    info.update(species=base_id, variant=v, variants=sp0.get("variants", 1), collider=collider, climb=climb,
                sources=sorted({sp[r]["src"] for r in ("bark", "soil", "rock") if sp.get(r)} |
                               ({"moss_01"} if "moss" in mats else set())))
    print(f"VEG {sp_name}: " + "  ".join(f"LOD{i} {l['tris']} tris" for i, l in enumerate(lod_info)) + f"  {size / 1024:.0f} KB")
    if preview:
        os.makedirs(trees.PREVIEWS, exist_ok=True)
        trees.preview_sheet(sp_name, objs, os.path.join(trees.PREVIEWS, f"{sp_name}.png"))
        info["preview"] = f"previews/{sp_name}.png"
    info["build_s"] = round(time.time() - t0, 1)
    return info


def log_hints(sp, axis, wad_c):
    """Collision capsules along the log (three.js frame) and how to get over it."""
    caps = []
    step = max(1, len(axis) // 6)
    for i in range(0, len(axis) - step, step):
        a, b = axis[i], axis[min(i + step, len(axis) - 1)]
        caps.append(dict(a=_three((a[0], a[1], a[2])), b=_three((b[0], b[1], b[2])), r=round(min(a[3], b[3]), 2)))
    col = dict(type="capsules", capsules=caps)
    tops = [z + r for _, _, z, r in axis]
    climb = dict(top_height=round(max(tops), 2), top_min=round(min(tops), 2))
    # where the top is low enough for the existing ~1 m jump: three.js x ranges along the log
    runs, cur = [], None
    for (x, _, z, r) in axis:
        ok = z + r <= 0.95
        if ok and cur is None:
            cur = [x, x]
        elif ok:
            cur[1] = x
        elif cur is not None:
            runs.append(cur)
            cur = None
    if cur is not None:
        runs.append(cur)
    climb["jump_over"] = [[round(a, 2), round(b, 2)] for a, b in runs if b - a >= 0.5]
    unders = [(x, z - r) for x, _, z, r in axis if z - r >= 0.85]
    if unders and unders[-1][0] - unders[0][0] >= 0.5:
        climb["crawl_under"] = dict(x0=round(unders[0][0], 2), x1=round(unders[-1][0], 2),
                                    clearance=round(max(u[1] for u in unders), 2),
                                    note="three.js x range along the log where the underside clears 0.85 m")
    if sp.get("prop"):                         # the log itself is the ramp up to its high end
        ramp = [_three((x, y, z + r * 0.95)) for x, y, z, r in axis[::max(1, len(axis) // 8)]]
        climb["ramps"] = [ramp]
        climb["note"] = "walk up the log from x=0 (on the ground) to the propped end; level.ramps format"
    if wad_c is not None:
        R = sp["wad"]["radius"]
        col["root_wad"] = dict(type="box", min=[round(wad_c.x - 0.8, 2), 0.0, round(-(wad_c.y + R), 2)],
                               max=[round(wad_c.x + 0.5, 2), round(wad_c.z + R, 2), round(-(wad_c.y - R), 2)])
    return col, climb
