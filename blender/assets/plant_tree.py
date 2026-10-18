"""Tree generator for the estate's planting (wrapped by plant_tree_round / _olive /
_cypress / _multistem / _fruit). `build(kind=..., seed=...)` makes a trunk, limbs and a
crown of overlapping lumpy foliage masses (flatter undersides, gaps between tiers so the
limbs show), all low-poly: outdoors everything is merged and lit per vertex (baked).

Origin: trunk base on the ground, z up, units metres. Materials: outdoor.foliage() for the
green crowns, flat colours for olive / birch (silver-green, light green), flat bark.
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plant_common as pc  # noqa: E402

importlib.reload(pc)
common, outdoor = pc.common, pc.outdoor

NAME = "PlantTree"
P = dict(name=NAME, kind="round", seed=3)

# crown colours (linear RGB)
OLIVE_LEAF = (0.088, 0.108, 0.062)       # silver-green
BIRCH_LEAF = (0.062, 0.128, 0.026)       # fresh light green
BIRCH_BARK = (0.46, 0.44, 0.39)          # pale papery trunk
APPLE_RED = (0.30, 0.025, 0.02)
OLIVE_BARK = (0.11, 0.095, 0.08)         # grey-brown, lighter than the shared bark


def v3(x, y, z):
    return Vector((x, y, z))


def polar(r, a, z):
    return v3(r * math.cos(a), r * math.sin(a), z)


def limb_to(bm, start, end, r0, r1, rng, sides=5, bend=0.25, mid=2, **kw):
    """Gently bowed limb from start to end."""
    start, end = Vector(start), Vector(end)
    d = end - start
    side = Vector((-d.y, d.x, 0))
    side = side.normalized() * d.length * bend * rng.uniform(-1, 1) if side.length > 1e-4 else Vector()
    ctrl = [start, start.lerp(end, 0.5) + side + v3(0, 0, d.length * 0.05), end]
    pts = pc.spline(ctrl, per=mid)
    pc.sweep(bm, pts, pc.taper(len(pts), r0, r1), sides=sides, rng=rng, noise=0.06)
    return pts


# ------------------------------------------------------------------ kinds
def tree_round(p, rng, bk, crown):
    """Broad deciduous crown, 12 m: tiers of leaf clusters on a short trunk."""
    trunk = pc.spline([v3(0, 0, 0), v3(0.12, -0.08, 1.4), v3(0.0, 0.1, 2.8), v3(0.05, 0.0, 4.0)], per=1)
    pc.sweep(bk, trunk, pc.taper(len(trunk), 0.42, 0.26, flare=0.25, flare_len=0.1), sides=7,
             lobe=0.12, lobes=3, twist=0.4, noise=0.05, rng=rng, tip=False)
    top = v3(0.05, 0.0, 4.0)
    a0 = rng.uniform(0, 6.28)
    # tier 1: three low lateral masses (4.8-7.6 m) with gaps between them, limbs visible below
    for i in range(3):
        a = a0 + i * 2.094 + rng.uniform(-0.25, 0.25)
        c = polar(rng.uniform(3.4, 3.9), a, rng.uniform(5.4, 6.1))
        limb_to(bk, top, c - v3(0, 0, 1.0) - polar(1.5, a, 0), 0.2, 0.08, rng, sides=5, mid=1)
        pc.cluster(crown, c, (rng.uniform(3.0, 3.3), rng.uniform(3.0, 3.3), rng.uniform(1.9, 2.2)), rng,
                   sats=2, sat_size=(0.3, 0.42), lump=0.2)
    # tier 2: one bigger mass over the gaps (7.4-10.5 m) and the crest
    a = a0 + 1.0
    c = polar(rng.uniform(1.4, 2.0), a, 8.4)
    limb_to(bk, top, v3(c.x * 0.6, c.y * 0.6, 5.8), 0.17, 0.07, rng, sides=5, mid=1)
    pc.cluster(crown, c, (3.3, 3.3, 2.3), rng, sats=3, sat_size=(0.3, 0.4), lump=0.2)
    pc.cluster(crown, polar(1.0, a + 3.14, 10.2), (2.5, 2.5, 1.7), rng, sats=1, sat_size=(0.3, 0.4), lump=0.18)


def tree_olive(p, rng, bk, crown):
    """Gnarled multi-trunk olive, 5 m, silver-green crown: thick fluted stems forking low."""
    a0 = rng.uniform(0, 6.28)
    ends = []
    for i in range(3):
        a = a0 + i * 2.09 + rng.uniform(-0.3, 0.3)
        lean = rng.uniform(0.9, 1.2)
        pts = pc.spline([v3(rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05), 0),
                         polar(0.14 * lean, a, 0.55),
                         polar(0.5 * lean, a + 0.6, 1.2),
                         polar(0.85 * lean, a + 0.2, 1.9),
                         polar(1.15 * lean, a, 2.5)], per=1)
        rad = pc.taper(len(pts), 0.27, 0.10, flare=0.12, flare_len=0.12)
        pc.sweep(bk, pts, rad, sides=6, lobe=0.3, lobes=3, twist=0.9 + i, noise=0.12, rng=rng, tip=False)
        ends.append((a, pts[-1]))
    for i, (a, e) in enumerate(ends):
        c = polar(rng.uniform(1.0, 1.35), a + rng.uniform(-0.25, 0.25), rng.uniform(3.2, 3.6))
        pc.cluster(crown, c, (rng.uniform(1.4, 1.6), rng.uniform(1.4, 1.6), rng.uniform(0.95, 1.1)), rng,
                   sats=3, sat_size=(0.3, 0.42), lump=0.22, subdiv=1)
    pc.cluster(crown, polar(rng.uniform(0.2, 0.5), a0 + 3.1, rng.uniform(3.95, 4.15)), (1.35, 1.3, 0.9), rng,
               sats=3, sat_size=(0.3, 0.42), lump=0.2, subdiv=1)


def tree_cypress(p, rng, bk, crown):
    """Italian cypress, 10 m, slim flame: one lumpy spindle (1.5 m wide, widest low), a stub of trunk."""
    sides = 8
    H, R = 10.0, 0.74
    ts = [0.0, 0.09, 0.2, 0.33, 0.47, 0.61, 0.74, 0.86, 0.95, 1.0]
    noise = pc.Lump(rng, 1.0)

    def prof(t):
        if t < 0.3:
            return R * (0.5 + 0.5 * math.sin(t / 0.3 * math.pi / 2))
        return R * max(0.0, 1.0 - (t - 0.3) / 0.7) ** 0.8

    vs = []
    for i, t in enumerate(ts):
        z = 0.3 + (H - 0.3) * t
        base = prof(t)
        ring = []
        if base <= 0:
            vs.append([crown.verts.new((0, 0, z))])
            continue
        for k in range(sides):
            th = 2 * math.pi * k / sides + i * 0.45
            f = 1 + 0.16 * noise(math.cos(th) * 2, math.sin(th) * 2, z * 0.8) + 0.07 * rng.uniform(-1, 1)
            ring.append(crown.verts.new((base * f * math.cos(th), base * f * math.sin(th), z)))
        vs.append(ring)
    for i in range(len(ts) - 1):
        a, b = vs[i], vs[i + 1]
        for k in range(sides):
            j = (k + 1) % sides
            if len(b) == 1:
                f = crown.faces.new((a[k], a[j], b[0]))
            else:
                f = crown.faces.new((a[k], a[j], b[j], b[k]))
            f.smooth = True
    cv = crown.verts.new((0, 0, 0.3))
    for k in range(sides):
        f = crown.faces.new((vs[0][(k + 1) % sides], vs[0][k], cv))
        f.smooth = True
    pts = pc.spline([v3(0, 0, 0), v3(0, 0, 0.3), v3(0, 0, 0.6)], per=1)
    pc.sweep(bk, pts, [0.16, 0.13, 0.1], sides=6, tip=False)


def tree_multistem(p, rng, bk, crown):
    """Multi-stem birch-like tree, 7 m: pale slender stems, one airy light-green crown."""
    a0 = rng.uniform(0, 6.28)
    n_stems = 3
    for i in range(n_stems):
        a = a0 + i * 6.283 / n_stems + rng.uniform(-0.4, 0.4)
        lean = rng.uniform(0.7, 1.0)
        h = rng.uniform(3.7, 4.4)
        pts = pc.spline([v3(rng.uniform(-0.08, 0.08), rng.uniform(-0.08, 0.08), 0),
                         polar(0.2 * lean, a, h * 0.25),
                         polar(0.55 * lean, a + 0.2, h * 0.55),
                         polar(0.95 * lean, a, h * 0.85),
                         polar(1.2 * lean, a, h)], per=1)
        pc.sweep(bk, pts, pc.taper(len(pts), 0.115, 0.04, flare=0.04, flare_len=0.1), sides=5, noise=0.05,
                 rng=rng, tip=True)
        c = pts[-1] + v3(rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), rng.uniform(0.4, 0.8))
        pc.cluster(crown, c, (rng.uniform(1.5, 1.75), rng.uniform(1.5, 1.75), rng.uniform(1.5, 1.8)), rng,
                   sats=3, sat_size=(0.3, 0.42), lump=0.22, subdiv=1, flat_bottom=0.75)
    pc.cluster(crown, v3(0.1, 0, 5.4), (1.6, 1.55, 1.5), rng, sats=3, lump=0.2, subdiv=1, flat_bottom=0.8)
    pc.cluster(crown, polar(1.0, a0 + 0.9, 3.1), (0.95, 0.95, 0.85), rng, sats=1, lump=0.22, subdiv=1,
               flat_bottom=0.8)


def tree_fruit(p, rng, bk, crown, fruit):
    """Small apple tree, 4 m: short trunk, spreading crown, a few red apples."""
    trunk = pc.spline([v3(0, 0, 0), v3(0.05, 0.02, 0.5), v3(-0.03, 0.04, 1.0), v3(0, 0, 1.35)], per=1)
    pc.sweep(bk, trunk, pc.taper(len(trunk), 0.17, 0.12, flare=0.1, flare_len=0.1), sides=7, lobe=0.1,
             lobes=3, twist=0.3, noise=0.05, rng=rng, tip=False)
    a0 = rng.uniform(0, 6.28)
    blobs = []
    for i in range(4):
        a = a0 + i * math.pi / 2 + rng.uniform(-0.3, 0.3)
        c = polar(rng.uniform(1.2, 1.5), a, rng.uniform(2.3, 2.7))
        limb_to(bk, v3(0, 0, 1.3), c - polar(0.5, a, 0.5), 0.09, 0.04, rng, sides=5, bend=0.2, mid=1)
        blobs.append((c, (rng.uniform(1.15, 1.35), rng.uniform(1.15, 1.35), rng.uniform(0.8, 0.95))))
    blobs.append((v3(rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), 3.1), (1.35, 1.3, 0.9)))
    for c, r in blobs:
        pc.cluster(crown, c, r, rng, sats=3, sat_size=(0.3, 0.42), lump=0.2, subdiv=1)
    for i in range(7):
        c, r = blobs[i % len(blobs)]
        a = rng.uniform(0, 6.28)
        pos = c + v3(math.cos(a) * r[0] * 0.78, math.sin(a) * r[1] * 0.78, -r[2] * rng.uniform(0.25, 0.55))
        g = bmesh.ops.create_icosphere(fruit, subdivisions=1, radius=0.085)
        bmesh.ops.translate(fruit, vec=pos, verts=g["verts"])


# ------------------------------------------------------------------ build
def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rng = pc.rng_for(p["seed"])
    col, root = pc.new_asset(n)
    kind = p["kind"]
    bark_bm, crown_bm, fruit_bm = bmesh.new(), bmesh.new(), bmesh.new()
    if kind == "round":
        tree_round(p, rng, bark_bm, crown_bm)
    elif kind == "olive":
        tree_olive(p, rng, bark_bm, crown_bm)
    elif kind == "cypress":
        tree_cypress(p, rng, bark_bm, crown_bm)
    elif kind == "multistem":
        tree_multistem(p, rng, bark_bm, crown_bm)
    elif kind == "fruit":
        tree_fruit(p, rng, bark_bm, crown_bm, fruit_bm)
    else:
        raise ValueError(kind)

    bark = {"olive": outdoor.flat("M_Out_OliveBark", OLIVE_BARK),
            "multistem": outdoor.flat("M_Out_BirchBark", BIRCH_BARK)}.get(kind, outdoor.bark())
    leaf = {"olive": lambda: outdoor.flat("M_Out_OliveLeaf", OLIVE_LEAF),
            "multistem": lambda: outdoor.flat("M_Out_BirchLeaf", BIRCH_LEAF)}.get(kind, outdoor.foliage)()
    for v in bark_bm.verts:
        v.co.z = max(v.co.z, 0.0)
    if bark_bm.verts:
        common.mesh_object(f"{n}_Trunk", bark_bm, col, bark, root)
    else:
        bark_bm.free()
    cr = common.mesh_object(f"{n}_Crown", crown_bm, col, leaf, root)
    if kind not in ("olive", "multistem"):
        common.box_uv(cr, tile=1.5)
    if fruit_bm.verts:
        for f in fruit_bm.faces:
            f.smooth = True
        common.mesh_object(f"{n}_Fruit", fruit_bm, col, outdoor.flat("M_Out_Apple", APPLE_RED), root)
    else:
        fruit_bm.free()
    return root, pc.parts_of(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
