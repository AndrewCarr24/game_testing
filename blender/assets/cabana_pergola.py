"""Pergola over the outdoor dining and kitchen: dark metal posts and two deep primary beams
carrying close teak slats. 11 x 7.6 m, 2.9 m to the underside of the beams, slats run across
(Y). The back (north, +Y) post row has only the two end posts. Origin: floor centre."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cabana_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common

NAME = "CabanaPergola"

P = dict(name=NAME, length=11.0, depth=7.0, post_h=2.88, pitch=0.42, slat_w=0.07, slat_h=0.17, beam_h=0.34)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = cc.start(n)
    m = cc.M()
    box, quad = cc.box, cc.quad
    L, D, PH = p["length"], p["depth"], p["post_h"]
    bh = p["beam_h"]
    px = L / 2 - 0.5
    rows = {-1: (-px, -px / 3, px / 3, px), 1: (-px, px)}
    for sy, xs in rows.items():
        y = sy * (D / 2 - 0.25)
        for i, x in enumerate(xs):
            box(f"{n}_Post{sy}_{i}", (x - 0.07, y - 0.07, 0.0), (x + 0.07, y + 0.07, PH), m["dark"], col, root, drop=("-z", "+z"))
        box(f"{n}_Beam{sy}", (-L / 2, y - 0.07, PH), (L / 2, y + 0.07, PH + bh), m["dark"], col, root, drop=("+z",))
        # recessed warm light under each beam
        yy = y + (0.075 if sy < 0 else -0.075)
        quad(f"{n}_Light{sy}", [(-L / 2 + 0.3, yy, PH + 0.04), (L / 2 - 0.3, yy, PH + 0.04), (L / 2 - 0.3, yy, PH + 0.10),
                                (-L / 2 + 0.3, yy, PH + 0.10)][::(1 if sy < 0 else -1)], m["lamp"], col, root)
    ns = int(L / p["pitch"])
    x0 = -(ns - 1) * p["pitch"] / 2
    for i in range(ns):
        x = x0 + i * p["pitch"]
        box(f"{n}_Slat{i}", (x - p["slat_w"] / 2, -D / 2 - 0.35, PH + bh), (x + p["slat_w"] / 2, D / 2 + 0.35, PH + bh + p["slat_h"]),
            m["teak"], col, root, drop=("-x", "+x") if False else ())
    return cc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
