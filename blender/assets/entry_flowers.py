"""Entry flower arrangement: a tall matte stoneware vase (open, rolled lip) with a loose,
sweeping spray of blossom branches: cupped five-petal flowers and buds in blush and white
on short spurs off tapering dark twigs. Sits on the round centre
table. Origin: centre of the underside of the vase. Units are metres.
"""
import importlib
import math
import os
import random
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import table_lamp  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "EntryFlowers"

P = dict(
    name=NAME,
    branches=11,
    seed=5,
    vase_h=0.36,
    vase_profile=[(0.075, 0.0), (0.085, 0.03), (0.105, 0.12), (0.100, 0.21), (0.062, 0.30), (0.052, 0.345), (0.058, 0.36)],
    spray=(0.5, 0.85),       # branch length range
)


def sphere(bm, c, r, segs=6, rings=4, jitter=0.0, rnd=None):
    ret = bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=r, matrix=Matrix.Translation(c))
    if jitter and rnd:
        for v in ret["verts"]:
            v.co += Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * (r * jitter)


def blossom(bm, c, r, normal, spin, cup=0.35):
    """One five-petal flower: a fan of 15 triangles round a sunken centre (each petal
    has two shoulder points and a notch between petals), cupped towards `normal`."""
    nrm = Vector(normal).normalized()
    t = nrm.orthogonal().normalized()
    b = nrm.cross(t)
    centre = bm.verts.new(c - nrm * r * 0.18)
    ring = []
    for k in range(5):
        a0 = spin + 2 * math.pi * k / 5
        for da, rr in ((-0.36, 0.95), (0.36, 0.95), (math.pi / 5, 0.60)):   # shoulders, then the notch
            a = a0 + da
            d = t * math.cos(a) + b * math.sin(a)
            ring.append(bm.verts.new(c + d * (r * rr) + nrm * (r * cup * rr * rr)))
    for k in range(len(ring)):
        bm.faces.new((centre, ring[k], ring[(k + 1) % len(ring)]))


def bud(bm, c, r):
    """Closed bud: an octahedron stretched a little along z (8 triangles)."""
    ret = bmesh.ops.create_uvsphere(bm, u_segments=4, v_segments=2, radius=r, matrix=Matrix.Translation(c))
    for v in ret["verts"]:
        v.co = c + Vector(((v.co - c).x, (v.co - c).y, (v.co - c).z * 1.3))


def twig(bm, pts, r0, r1, sides=4):
    """Continuous tapered twig along `pts`: rings shared between segments, no caps."""
    pts = [Vector(q) for q in pts]
    n = len(pts)
    rings = []
    ref = None
    for k, q in enumerate(pts):
        d = (pts[min(k + 1, n - 1)] - pts[max(k - 1, 0)]).normalized()
        if ref is None:
            ref = d.orthogonal().normalized()
        u = (ref - d * ref.dot(d)).normalized()
        w = d.cross(u)
        ref = u
        rr = r0 + (r1 - r0) * k / (n - 1)
        rings.append([bm.verts.new(q + (u * math.cos(2 * math.pi * s / sides) + w * math.sin(2 * math.pi * s / sides)) * rr)
                      for s in range(sides)])
    for k in range(n - 1):
        A, B = rings[k], rings[k + 1]
        for s in range(sides):
            bm.faces.new((A[s], A[(s + 1) % sides], B[(s + 1) % sides], B[s]))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    rnd_f = random.Random(p["seed"] + 100)     # flower orientation/details: separate stream (layout unchanged)

    ceramic = common.pbr_material("M_Entry_Stoneware", (0.60, 0.56, 0.50), roughness=0.62)
    twig_m = common.pbr_material("M_Entry_Twig", (0.045, 0.030, 0.020), roughness=0.8)
    blush = common.pbr_material("M_Entry_Blossom_Blush", (0.62, 0.36, 0.38), roughness=0.8)
    white = common.pbr_material("M_Entry_Blossom_White", (0.78, 0.74, 0.68), roughness=0.8)

    # ---- vase: matte stoneware with a real open neck (a rolled lip, dark inside) --------
    prof_pts = table_lamp.catmull(p["vase_profile"], per=3)
    top_r, top_z = p["vase_profile"][-1]
    pr = ([(0.0, 0.0)] + prof_pts +
          [(top_r - 0.004, top_z + 0.002), (top_r - 0.009, top_z - 0.002), (top_r - 0.011, top_z - 0.04),
           (0.0, top_z - 0.05)])
    vase = common.mesh_object(f"{n}_Vase", table_lamp.lathe(pr, 28, sharp=60), col, ceramic, root)

    # ---- branches ------------------------------------------------------------------------
    stems = bmesh.new()
    bl, wh = bmesh.new(), bmesh.new()
    top = p["vase_h"]
    for b in range(p["branches"]):
        th = 2 * math.pi * (b + rnd.uniform(-0.2, 0.2)) / p["branches"] + 0.4
        lean = math.radians(rnd.uniform(6, 40))
        L = rnd.uniform(*p["spray"])
        d_out = Vector((math.cos(th), math.sin(th), 0))
        base = Vector((rnd.uniform(-0.02, 0.02), rnd.uniform(-0.02, 0.02), top - 0.12))
        pts = []
        steps = 9
        for k in range(steps + 1):
            t = k / steps
            out = L * math.sin(lean) * t ** 1.5
            up = L * math.cos(lean) * t
            wob = 0.03 * math.sin(t * 5 + b)
            pts.append(base + d_out * out + Vector((-d_out.y, d_out.x, 0)) * wob + Vector((0, 0, up)))
        twig(stems, pts, 0.0065, 0.0065 * 0.45, sides=4)
        # blossom clusters on the upper two thirds, each on a short spur
        for k in range(3, steps + 1):
            c = pts[k]
            for _ in range(rnd.randint(1, 2) if k < steps else 3):
                off = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.3, 1))) * 0.045
                tgt = bl if rnd.random() < 0.5 else wh
                twig(stems, [c, c + off * 0.7], 0.0024, 0.0012, sides=3)
                for j in range(2):
                    o2 = off + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * 0.022
                    r = rnd.uniform(0.018, 0.034)
                    for _ in range(42):      # the old blob's vertex jitter: keeps the layout stream intact
                        rnd.uniform(-1, 1)
                    pos = c + o2 + o2.normalized() * r * 0.7     # flowers open at the spur's tip
                    face = (o2 - off * 0.3)
                    if face.length < 1e-6:
                        face = Vector((0, 0, 1))
                    face = (face.normalized() + Vector((0, 0, 0.6))).normalized()
                    if j == 1 and rnd_f.random() < 0.3:
                        bud(tgt, pos, r * 0.26)
                    else:
                        blossom(tgt, pos, r * 0.95, face, rnd_f.uniform(0, 2 * math.pi), cup=rnd_f.uniform(0.25, 0.5))
                        if rnd_f.random() < 0.5:
                            # a second, smaller flower tucked in beside it thickens the cluster
                            side = face.orthogonal().normalized()
                            blossom(tgt, pos + side * r * 0.7 - face * r * 0.25, r * 0.6,
                                    (face + side * 0.6).normalized(), rnd_f.uniform(0, 2 * math.pi), cup=0.4)
    common.mesh_object(f"{n}_Stems", stems, col, twig_m, root)
    common.mesh_object(f"{n}_BlossomBlush", bl, col, blush, root)
    common.mesh_object(f"{n}_BlossomWhite", wh, col, white, root)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
