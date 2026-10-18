"""Outdoor dining table for ten: a 3.8 m teak top on two dark metal slab legs, four teak-framed
chairs with sand cushions on each long side and one at each end, a linen runner and three
bronze vessels. Long axis along X, origin: floor centre."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cabana_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common

NAME = "CabanaDining"

P = dict(name=NAME, length=3.8, width=1.1, height=0.76)


def chair(n, tag, col, parent, m, loc, rot):
    g = cc.group(f"{n}_Chair{tag}", col, parent, loc, rot)       # chair faces -y in its own frame
    box = cc.box
    s = 0.235
    for lx in (-1, 1):
        for ly, top in ((-1, 0.43), (1, 0.88)):
            box(f"{n}_Leg{tag}{lx}{ly}", (lx * s - 0.02, ly * s - 0.02, 0.0), (lx * s + 0.02, ly * s + 0.02, top), m["teak"], col, g,
                drop=("-z", "+z" if top < 0.5 else ""))
    box(f"{n}_Seat{tag}", (-s - 0.02, -s - 0.02, 0.43), (s + 0.02, s + 0.02, 0.47), m["teak"], col, g, drop=("-z",))
    box(f"{n}_Cushion{tag}", (-0.205, -0.205, 0.47), (0.205, 0.205, 0.52), m["sand"], col, g, drop=("-z",))
    box(f"{n}_Back{tag}", (-s - 0.02, s - 0.02, 0.60), (s + 0.02, s + 0.02, 0.88), m["teak"], col, g, drop=("-z", "+z"))
    return g


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = cc.start(n)
    m = cc.M()
    box, cyl = cc.box, cc.cyl
    L, W, H = p["length"], p["width"], p["height"]
    box(f"{n}_Top", (-L / 2, -W / 2, H - 0.05), (L / 2, W / 2, H), m["teak"], col, root, step=1.3, drop=("-z",))
    for sx in (-1, 1):
        box(f"{n}_Leg{sx}", (sx * (L / 2 - 0.55) - 0.04, -W / 2 + 0.2, 0.0), (sx * (L / 2 - 0.55) + 0.04, W / 2 - 0.2, H - 0.05),
            m["dark"], col, root, drop=("-z", "+z"))
    box(f"{n}_Runner", (-1.3, -0.17, H), (1.3, 0.17, H + 0.006), m["cream"], col, root, drop=("-z",))
    for i, (x, hgt, r) in enumerate(((-0.8, 0.30, 0.07), (0.0, 0.20, 0.10), (0.8, 0.26, 0.06))):
        cyl(f"{n}_Vessel{i}", (x, 0.0), r, H + 0.006, H + 0.006 + hgt, m["bronze"], col, root, seg=6, caps=(False, True), r1=r * 0.7)
    k = 0
    for i in range(4):
        x = -1.35 + i * 0.9
        chair(n, f"S{i}", col, root, m, (x, -W / 2 - 0.22, 0.0), 180)     # south side faces +y toward the table
        chair(n, f"N{i}", col, root, m, (x, W / 2 + 0.22, 0.0), 0)
    chair(n, "W", col, root, m, (-L / 2 - 0.22, 0.0, 0.0), -90)
    chair(n, "E", col, root, m, (L / 2 + 0.22, 0.0, 0.0), 90)
    return cc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
