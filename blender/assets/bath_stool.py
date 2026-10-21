"""Spa stool: a sculpted honed-stone drum with a soft waist and a dark marble top, with
a stack of folded oat linen towels and a brass-lidded candle jar on it (the jar is a throwable pickup).

Origin: floor centre. Rotationally symmetric; the front faces -Y.
"""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials, pickups  # noqa: E402
import bath_common as bc  # noqa: E402
import bath_vanity as bv  # noqa: E402  (soft_extrude, round_outline)

importlib.reload(common)
importlib.reload(pickups)
importlib.reload(bc)
importlib.reload(bv)

NAME = "BathStool"

P = dict(name=NAME, radius=0.21, height=0.46, segs=32, towels=3)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    stone, dark, brass = bc.stone(), bc.marble_dark(), bc.brass()
    oat = materials.fabric("M_Fabric_Oat", (0.42, 0.37, 0.30))
    glass = bc.ceramic()

    r, h, segs = p["radius"], p["height"], p["segs"]
    top_t = 0.03
    prof = bc.catmull([(0.0, 0.0), (r * 0.80, 0.0), (r * 0.92, 0.02), (r * 0.88, 0.12), (r * 0.82, 0.22),
                       (r * 0.90, 0.33), (r, h - top_t - 0.03), (r, h - top_t), (0.0, h - top_t)], per=3)
    dedup = []
    for pt in prof:
        if not dedup or abs(pt[0] - dedup[-1][0]) + abs(pt[1] - dedup[-1][1]) > 1e-6:
            dedup.append(pt)
    dedup = [(a, max(b, 0.0)) for a, b in dedup]
    dedup[0] = (0.0, 0.0)
    dedup[-1] = (0.0, h - top_t)
    body = common.mesh_object(f"{n}_Body", bc.lathe(dedup, segs), col, stone, root)
    bc.cylindrical_uv(body, tile=1.0)
    top = common.mesh_object(f"{n}_Top", bc.lathe([(0.0, h - top_t), (r + 0.002, h - top_t), (r + 0.002, h),
                                                    (r - 0.004, h + 0.0015), (0.0, h + 0.0015)], segs), col, dark, root)
    bc.cylindrical_uv(top, tile=1.0)

    # folded towels: the fold rounds the front edge, the hems sit square-ish at the back,
    # the cut ends are eased; each one a touch smaller and nudged so the stack looks placed
    z = h + 0.0015
    for i in range(p["towels"]):
        th = 0.045 - 0.004 * i
        L, dep = 0.30 - 0.01 * i, 0.20
        x0 = -0.07 + 0.012 * (i % 2)
        y0 = -0.02 - dep / 2
        out = bv.round_outline(y0, y0 + dep, z, z + th, th * 0.5, 0.008, segs=4)
        # a soft sag across the top (the stack above presses it) - lower the top middle points
        out = [(y, zz - (0.003 if zz > z + th * 0.9 and y0 + 0.03 < y < y0 + dep - 0.03 else 0.0)) for y, zz in out]
        tw = common.mesh_object(f"{n}_Towel_{i}", bv.soft_extrude(out, x0 - L / 2, x0 + L / 2, ease=0.010, inset=0.006),
                                col, oat, root)
        common.box_uv(tw, tile=0.25)
        z += th - 0.002
    # candle jar beside them
    jar = bc.lathe([(0.0, 0.0), (0.040, 0.0), (0.042, 0.004), (0.042, 0.075), (0.040, 0.078), (0.0, 0.078)], 28)
    j = common.mesh_object(f"{n}_Jar", jar, col, glass, root)
    j.location = (0.125, 0.06, h + 0.0015)
    lid = bc.lathe([(0.0, 0.0), (0.043, 0.0), (0.043, 0.012), (0.0, 0.012)], 28)
    l = common.mesh_object(f"{n}_Lid", lid, col, brass, root)
    l.location = (0.125, 0.06, h + 0.0015 + 0.078)
    # the candle jar is a throwable pickup (lib/pickups.py); the towels stay
    pickups.adopt(f"{n}_CandleJar", col, root, "candle", [j, l], (0.125, 0.06, h + 0.0015))
    bc.merge(root, bc.children(root, "_Towel_"), f"{n}_Towels")
    return root, bc.parts_of(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
