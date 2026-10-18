"""Walnut slat wall: vertical walnut battens over a black felt panel, with a warm LED
line top and bottom. A warm feature wall for the garage's side walls.

Units are metres. The front faces -Y (back at +Y against the wall), the origin is
the floor centre.
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

NAME = "GarageSlatwall"
P = dict(name=NAME, width=6.4, depth=0.09, z0=0.12, z1=3.5, slat_w=0.035, pitch=0.07, slat_depth=0.05)


def build(**overrides):
    p = {**P, **overrides}
    b = gk.Builder(p["name"])
    grd = gk.graphite_dark()
    walnut = materials.walnut()
    glow = materials.emissive("M_Garage_SlatGlow", (1.0, 0.78, 0.5), 1.6)
    W, D, z0, z1 = p["width"], p["depth"], p["z0"], p["z1"]
    yb = D / 2
    b.lo_hi("Plinth", (-W / 2, yb - D + 0.02, 0), (W / 2, yb, z0), grd, bevel=0, solid=True)
    b.lo_hi("Back", (-W / 2, yb - 0.02, z0), (W / 2, yb, z1), grd, bevel=0, solid=True)
    n = int(W / p["pitch"])
    x_start = -(n - 1) * p["pitch"] / 2
    for i in range(n):
        b.box(f"Slat{i}", (p["slat_w"], p["slat_depth"], z1 - z0 - 0.12), (x_start + i * p["pitch"], yb - 0.02 - p["slat_depth"] / 2, (z0 + z1) / 2), walnut,
              bevel=0, tile=0.5, solid=True)
    b.lo_hi("LED_Top", (-W / 2 + 0.05, yb - 0.075, z1 - 0.1), (W / 2 - 0.05, yb - 0.02, z1 - 0.09), glow, bevel=0, solid=False)
    b.lo_hi("LED_Bottom", (-W / 2 + 0.05, yb - 0.075, z0 + 0.01), (W / 2 - 0.05, yb - 0.02, z0 + 0.02), glow, bevel=0, solid=False)
    b.lo_hi("Cap", (-W / 2, yb - D + 0.02, z1), (W / 2, yb, z1 + 0.04), grd, bevel=0, solid=True)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
