"""Parking bay inlaid in the floor: a glossy graphite display pad (3 mm proud) edged with
slim brushed-aluminium strips and corner ticks. Marks one bay; nothing stands in it.

Units are metres. The bay's long side runs along Y; origin at the bay centre on the floor.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import garage_cabinets as gk  # noqa: E402

importlib.reload(gk)
common = gk.common

NAME = "GarageBay"
P = dict(name=NAME, width=3.2, length=5.8, line=0.025, height=0.005, pad=0.003, tick=0.5)


def build(**overrides):
    p = {**P, **overrides}
    b = gk.Builder(p["name"])
    al = gk.aluminium()
    pad = gk.common.pbr_material("M_Garage_BayPad", (0.016, 0.017, 0.019), roughness=0.14, coat=0.5)
    W, L, t, h, k = p["width"], p["length"], p["line"], p["height"], p["tick"]
    b.box("Pad", (W - 0.08, L - 0.08, p["pad"]), (0, 0, p["pad"] / 2), pad, bevel=0, solid=False, tile=1.0)
    # the rectangle: long sides, and the short ends broken in the middle (corner brackets)
    for s, sx in (("L", -1), ("R", 1)):
        b.box(f"Side_{s}", (t, L, h), (sx * (W - t) / 2, 0, h / 2), al, bevel=0, seg=1, solid=False)
    for s, sy in (("N", 1), ("S", -1)):
        for q, sx in (("a", -1), ("b", 1)):
            b.box(f"End_{s}{q}", (k, t, h), (sx * (W / 2 - t - k / 2), sy * (L - t) / 2, h / 2), al, bevel=0, seg=1, solid=False)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
