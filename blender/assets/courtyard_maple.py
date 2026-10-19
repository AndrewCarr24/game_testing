"""Japanese maple (Acer palmatum) for the courtyard beds: a multi-stem small tree, five
smooth grey stems rising from one root crown in a vase shape, each forking into slender
branches that end in horizontal tiers of foliage (the layered, cloud-like habit of an old
garden maple), leaves turning crimson to copper. Leaf clumps are alpha-tested maple cards
from the shared courtyard atlas, laid mostly flat so the tiers read from below and above.

No planter: it is placed in a bed, its origin (the root crown) at the soil surface.
Collision: the stems below ~1.3 m are the Trunk mesh (a compact box); the branches above
(LimbsNoCollide) and the leaves (Canopy) have none, so no box hangs over the walkway at
head height. Units are metres."""
import importlib
import math
import os
import random
import sys

import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import courtyard_common as cc  # noqa: E402
import courtyard_olive_tree as olive  # noqa: E402

importlib.reload(cc)
importlib.reload(olive)
common = cc.common

NAME = "CourtyardMaple"

P = dict(
    name=NAME,
    seed=4,
    stems=5,
    height=3.3,
    spread=1.45,          # crown radius
    split_z=1.3,          # trunk mesh ends here
    clumps=16,
    back_y=0.5,           # the glass is this far behind the root crown (local +y): the tree is
                          # trained flat on that side, nothing grows past it
    cards=22,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rng = random.Random(p["seed"])
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    bark, leaf = cc.bark_mat(), cc.foliage_mat()
    # the olive's bark colour (one shared bark material, whichever tree builds last)
    bsdf = next(nd for nd in bark.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*olive.P["bark"], 1.0)
    bark.diffuse_color = (*olive.P["bark"], 1.0)

    trunk_bm, limb_bm = bmesh.new(), bmesh.new()
    sz = p["split_z"]
    H, R = p["height"], p["spread"]
    nodes = []
    a0 = rng.uniform(0, 2 * math.pi)
    for k in range(p["stems"]):
        a = a0 + k * 2 * math.pi / p["stems"] + rng.uniform(-0.3, 0.3)
        d = Vector((math.cos(a), math.sin(a), 0))
        if d.y > 0:                     # stems on the wall side rise steeper
            d.y *= 0.3
        lean = rng.uniform(0.45, 0.75)
        top = rng.uniform(0.62, 0.80) * H
        ctrl = [Vector((0, 0, 0)) + d * 0.04, d * 0.10 + Vector((0, 0, 0.35)),
                d * (0.25 + 0.2 * lean) + Vector((0, 0, 0.9)),
                d * (0.45 + 0.45 * lean) + Vector((rng.uniform(-0.1, 0.1), rng.uniform(-0.1, 0.1), 1.55)),
                d * (0.65 + 0.6 * lean) + Vector((0, 0, top))]
        pts = olive.spline(ctrl, per=3)
        r0 = rng.uniform(0.045, 0.06)
        rad = olive.taper(len(pts), r0, 0.016, 0.8)
        relief = olive.Bark(rng, lobes=2, lobe=0.05, twist=0.2, gnarl=0.03, burls=0, length=top)
        rings, tang = olive.rings_along(pts, rad, 7, relief)
        cut = next((i for i, q in enumerate(pts) if q.z >= sz), len(pts) - 1)
        olive.emit(trunk_bm, rings, 0, cut)
        olive.emit(limb_bm, rings, cut, len(rings) - 1, cap_tip=pts[-1] + tang[-1] * rad[-1])
        nodes += [(q, r) for q, r in zip(pts, rad) if q.z > 1.2]

    # tiers: clump centres on a few horizontal layers, wider low, narrower high
    tiers = [(0.50, 1.0), (0.66, 0.85), (0.82, 0.62), (0.96, 0.35)]
    centres = []
    tries = 0
    while len(centres) < p["clumps"] and tries < 5000:
        tries += 1
        tz, tr = tiers[rng.randrange(len(tiers))]
        az = rng.uniform(0, 2 * math.pi)
        rr = R * tr * rng.uniform(0.45, 1.0)
        q = Vector((rr * math.cos(az), rr * math.sin(az), H * tz + rng.uniform(-0.08, 0.08)))
        if q.y > p["back_y"] - 0.35:
            continue
        if all((q - c).length > 0.62 for c in centres):
            centres.append(q)
    centres.sort(key=lambda q: Vector((q.x, q.y)).length)

    def branch(start, end, r0, r1):
        dvec = end - start
        L = dvec.length
        side = dvec.normalized().cross(Vector((0, 0, 1)))
        side = side.normalized() if side.length > 1e-3 else Vector((1, 0, 0))
        mid = start + dvec * 0.5 + side * rng.uniform(-0.12, 0.12) * L + Vector((0, 0, 0.12 * L))
        pts = olive.spline([start, mid, end], per=3)
        rads = olive.taper(len(pts), r0, r1, 0.9)
        rings, tang = olive.rings_along(pts, rads, 4 if r0 > 0.014 else 3)
        olive.emit(limb_bm, rings, 0, len(rings) - 1, cap_tip=pts[-1] + tang[-1] * r1 * 1.5)
        return pts, rads

    clumps = []
    for c in centres:
        tip = c - Vector((0, 0, 0.05))
        best = min(nodes, key=lambda nr: (nr[0] - tip).length + 0.4 * max(0.0, nr[0].z - tip.z))
        q, r = best
        if (tip - q).length < 0.1:
            clumps.append(c)
            continue
        pts, rads = branch(q, tip, min(r * 0.7, 0.008 + 0.02 * (tip - q).length), 0.005)
        nodes += [(pt, rr) for pt, rr in zip(pts[1:-1], rads[1:-1])]
        clumps.append(c)

    for v in trunk_bm.verts:            # the root crown sits on the soil, nothing below it
        v.co.z = max(v.co.z, 0.0)
    common.mesh_object(f"{n}_Trunk", trunk_bm, col, bark, root)
    common.mesh_object(f"{n}_LimbsNoCollide", limb_bm, col, bark, root)

    # leaf tiers: flattened clumps of maple cards, laid near-horizontal, tips outward
    cb = bmesh.new()
    uvl = cb.loops.layers.uv.new("UVMap")
    normals = []
    for c in clumps:
        s = rng.uniform(0.85, 1.15)
        rx, rz = 0.48 * s, 0.17 * s
        out_c = Vector((c.x, c.y, 0))
        out_c = out_c.normalized() if out_c.length > 1e-3 else Vector((1, 0, 0))
        for _ in range(p["cards"]):
            while True:
                d = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
                if 0.1 < d.length <= 1.0:
                    break
            pos = c + Vector((d.x * rx, d.y * rx, d.z * rz))
            horiz = Vector((d.x, d.y, 0))
            horiz = (horiz.normalized() if horiz.length > 1e-3 else out_c) * 0.7 + out_c * 0.3
            up = (horiz.normalized() + Vector((0, 0, rng.uniform(0.05, 0.45)))).normalized()   # tip out, nearly flat
            right = up.cross(Vector((0, 0, 1)))
            right = right.normalized() if right.length > 1e-3 else Vector((1, 0, 0))
            right = (right + Vector((0, 0, rng.uniform(-0.25, 0.25)))).normalized()
            if right.cross(up).z < 0:
                right = -right                                   # front face looks up
            size = rng.uniform(0.40, 0.56)
            cc.add_card(cb, uvl, pos + up * size * 0.35, right * size * 0.5, up * size * 0.5, "maple",
                        flip=rng.random() < 0.5)
            vn = (Vector((0, 0, 1)) * 0.7 + (pos - c).normalized() * 0.3).normalized()
            normals.extend([vn] * 4)
    canopy = common.mesh_object(f"{n}_Canopy", cb, col, leaf, root, smooth=True)
    cc.set_vertex_normals(canopy.data, normals)

    # soft limit on the wall side: y -> b (1 - e^(-y/b)) never reaches b
    b = p["back_y"] - 0.05
    for o in root.children_recursive:
        if o.type == "MESH":
            for v in o.data.vertices:
                if v.co.y > 0:
                    v.co.y = b * (1 - math.exp(-v.co.y / b))
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
