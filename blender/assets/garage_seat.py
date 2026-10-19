"""Window seat for the mudroom: a long oak plinth bench with a linen seat cushion,
a low sage-green back bolster and scatter cushions, with cream drawers below.
Sits under a window; the back is the +Y side.

Units are metres. The front faces -Y, the origin is the floor centre.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import garage_cabinets as gk  # noqa: E402

importlib.reload(gk)
common, materials = gk.common, gk.materials
from mathutils import Vector  # noqa: E402

NAME = "GarageSeat"
P = dict(name=NAME, width=4.2, depth=0.55, base_h=0.4)


def build(**overrides):
    p = {**P, **overrides}
    b = gk.Builder(p["name"])
    grd = gk.graphite_dark()
    cream, oak = gk.cream(), gk.oak_light()
    bronze = materials.bronze()
    oat = gk.linen("M_Fabric_Oat", (0.42, 0.37, 0.30))
    ink = gk.linen("M_Fabric_Sage", (0.16, 0.22, 0.16))
    clay = gk.linen("M_Fabric_Clay", (0.30, 0.12, 0.07))

    W, D, bh = p["width"], p["depth"], p["base_h"]
    yf, yb = -D / 2, D / 2
    g = 0.003
    ph = 0.07
    b.lo_hi("Plinth", (-W / 2 + 0.03, yf + 0.05, 0), (W / 2 - 0.03, yb - 0.02, ph), grd, bevel=0)
    b.lo_hi("Carcass", (-W / 2, yf + 0.025, ph), (W / 2, yb, bh - 0.03), grd, bevel=0)
    n = 4
    w = W / n
    for i in range(n):
        xa = -W / 2 + i * w
        b.lo_hi(f"Drawer{i}", (xa + g, yf, ph + g), (xa + w - g, yf + 0.025, bh - 0.03 - g), cream, bevel=0.002)
        b.box(f"Drawer{i}_Pull", (0.3, 0.016, 0.014), (xa + w / 2, yf - 0.008, bh - 0.08), bronze, bevel=0.0015, seg=1)
    b.lo_hi("Top", (-W / 2 - 0.01, yf - 0.01, bh - 0.03), (W / 2 + 0.01, yb, bh), oak, bevel=0.004)
    for i in range(2):   # two long seat cushions
        xa = -W / 2 + 0.04 + i * (W - 0.08) / 2
        # piped, softly crowned seat cushion (the two meet with a soft gap in the middle)
        x0c, x1c = xa + 0.01, xa + (W - 0.08) / 2 - 0.01
        size = (x1c - x0c, yb - 0.06 - (yf + 0.03), 0.08)
        loc = ((x0c + x1c) / 2, (yf + 0.03 + yb - 0.06) / 2, bh + 0.04)
        e = 0.024
        cush = b._add(f"Cushion{i}", common.cushion_bmesh(size, cuts=3, edge=e,
                                                          crown={"+z": 0.012, "+x": 0.004, "-x": 0.004, "-y": 0.006}),
                      oat, loc, 0.25, 0, 2, smooth=True)
        common.add_subsurf(cush)
        top_loop = common.piping_loop(size, "z", e / 6, e * 0.9)[0]
        b.tube(f"Cushion{i}_Piping", [tuple(Vector(q) + Vector(loc)) for q in top_loop], 0.004, oat, closed=True, res=1)
    # bolster along the back and scatter cushions
    b.lo_hi("Bolster", (-W / 2 + 0.05, yb - 0.1, bh + 0.08), (W / 2 - 0.05, yb - 0.02, bh + 0.3), ink, bevel=0.035, seg=3, tile=0.25)
    for i, (x, col, tilt) in enumerate(((-1.5, clay, 0.1), (-1.15, oat, -0.1), (1.0, clay, -0.12), (1.4, ink, 0.12))):
        ob = b.lo_hi(f"Pillow{i}", (x - 0.2, yb - 0.2, bh + 0.08), (x + 0.2, yb - 0.1, bh + 0.44), col, bevel=0.04, seg=3, tile=0.25)
        ob.rotation_euler = (-0.12, 0, tilt)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
