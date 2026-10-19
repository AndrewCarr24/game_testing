"""Slim ceramic table lamp: a glazed gourd body on a bronze foot, a bronze neck and socket,
and a glowing thin-walled linen drum shade with rolled bronze rims, a three-arm spider
and a finial. Cheap lathe geometry (about 1,000 triangles). Origin: centre of the underside;
0.58 m tall. Units are metres.
"""
import importlib
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import living_side_table  # noqa: E402
from lib import common, materials  # noqa: E402

importlib.reload(living_side_table)
lathe = living_side_table.lathe

NAME = "LivingTableLamp"
P = dict(name=NAME, segs=24, glow=1.6)


def _merge(bm, other):
    vm = {v: bm.verts.new(v.co) for v in other.verts}
    for f in other.faces:
        nf = bm.faces.new([vm[v] for v in f.verts])
        nf.smooth = f.smooth
    other.free()


def _rod(bm, a, b, r, sides=4):
    """A thin straight square-section rod from a to b (smooth shaded), appended to bm."""
    d = (b - a).normalized()
    u = d.orthogonal().normalized()
    w = d.cross(u)
    rings = [[bm.verts.new(p + r * (math.cos(2 * math.pi * k / sides) * u + math.sin(2 * math.pi * k / sides) * w))
              for k in range(sides)] for p in (a, b)]
    for k in range(sides):
        q = (k + 1) % sides
        f = bm.faces.new((rings[0][k], rings[0][q], rings[1][q], rings[1][k]))
        f.smooth = True


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    ceramic = common.pbr_material("M_Ceramic_Glaze", (0.55, 0.52, 0.46), roughness=0.18)
    bronze = materials.bronze()
    glow = materials.emissive("M_Living_LampGlow", (1.0, 0.78, 0.50), p["glow"])
    seg = p["segs"]
    body = [(0, 0.012), (0.045, 0.012), (0.064, 0.028), (0.080, 0.058), (0.089, 0.098), (0.087, 0.138),
            (0.075, 0.178), (0.052, 0.222), (0.031, 0.258), (0.020, 0.29), (0.018, 0.32), (0, 0.32)]
    b = common.mesh_object(f"{n}_Body", lathe(body, seg), col, ceramic, root)
    foot = common.mesh_object(f"{n}_Foot", lathe([(0, 0), (0.05, 0), (0.05, 0.012), (0, 0.012)], seg), col, bronze, root)
    # neck, then a bronze socket cup inside the shade
    stem = common.mesh_object(f"{n}_Neck", lathe([(0.012, 0.32), (0.012, 0.40), (0.018, 0.405), (0.018, 0.45),
                                                  (0.0, 0.45)], 12, closed=False), col, bronze, root)
    # drum shade: a thin linen wall (4 mm) with a slight taper, rolled bronze rims top
    # and bottom, held by a three-arm spider to a finial
    r0, r1, z0, z1 = 0.165, 0.150, 0.36, 0.58
    wt = 0.004
    shade = common.mesh_object(f"{n}_Shade", lathe([(r0, z0), (r1, z1), (r1 - wt, z1), (r0 - wt, z0)], seg, closed=True),
                               col, glow, root)
    rims = lathe([(r0 + 0.002, z0 - 0.002), (r0 + 0.002, z0 + 0.008), (r0 - wt - 0.002, z0 + 0.008),
                  (r0 - wt - 0.002, z0 - 0.002)], seg)
    top_rim = lathe([(r1 + 0.002, z1 - 0.008), (r1 + 0.002, z1 + 0.002), (r1 - wt - 0.002, z1 + 0.002),
                     (r1 - wt - 0.002, z1 - 0.008)], seg)
    _merge(rims, top_rim)
    zs = z1 - 0.004
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.5
        _rod(rims, Vector((0, 0, zs + 0.012)), Vector(((r1 - wt) * math.cos(a), (r1 - wt) * math.sin(a), zs)), 0.0028)
    _rod(rims, Vector((0, 0, 0.45)), Vector((0, 0, zs + 0.012)), 0.004)
    _merge(rims, lathe([(0.0, zs + 0.006), (0.009, zs + 0.010), (0.010, zs + 0.014), (0.005, zs + 0.019),
                        (0.0, zs + 0.021)], 10))
    fit = common.mesh_object(f"{n}_Fitting", rims, col, bronze, root)
    for ob in (b, foot, stem, shade, fit):
        common.box_uv(ob, 0.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
