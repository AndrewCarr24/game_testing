"""Island pendant: a spun bronze dome (0.46 m) with a glowing diffuser, on a thin
black cord to a ceiling canopy at 4.2 m. Origin is the centre of the underside (the dome rim, z = 0): place it at z = 1.95 m. The room
module puts a point light just under it. """
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitchen_lib as L  # noqa: E402

importlib.reload(L)
common, materials = L.common, L.materials

NAME = "KitchenPendant"

P = dict(
    name=NAME,
    rim_z=0.0,
    radius=0.23,
    height=0.21,
    ceiling=2.25,   # distance from the rim up to the ceiling when placed at z = 1.95
    emission=6.0,
)


def build(**overrides):
    p = {**P, **overrides}
    b = L.Builder(p["name"])
    bronze = materials.bronze()
    dark = materials.black_metal()
    glow = materials.emissive("M_Pendant_Glow", (1.0, 0.82, 0.58), p["emission"])
    z0, R, H = p["rim_z"], p["radius"], p["height"]
    w = 0.004
    outer = [(R, 0.0), (R - 0.004, 0.035), (R * 0.84, 0.095), (R * 0.58, 0.155), (R * 0.28, 0.195), (0.026, H)]
    outer = L.catmull([(R, 0.0), (R - 0.004, 0.03), (R * 0.85, 0.09), (R * 0.6, 0.15), (R * 0.3, 0.19), (0.03, H)], per=2)
    inner = [(r - w, max(z - w, 0.0)) for r, z in reversed(outer)]
    prof = outer + [(0.0, H)] if False else outer + inner
    b.lathe("Shade", prof, bronze, loc=(0, 0, z0), segs=32, sharp=50, uv_tile=0.3)
    # diffuser disc just inside the rim
    b.lathe("Glow", [(0.0, 0.012), (R - 0.012, 0.012), (R - 0.012, 0.016), (0.0, 0.016)], glow, loc=(0, 0, z0), segs=32,
            uv_tile=0)
    # top cap and cord to the ceiling canopy
    b.lathe("Cap", [(0.0, H - 0.01), (0.03, H - 0.01), (0.03, H + 0.015), (0.012, H + 0.03), (0.0, H + 0.03)], dark,
            loc=(0, 0, z0), segs=16, uv_tile=0)
    zt = z0 + H + 0.03
    b.tube("Cord_Piping", [(0, 0, zt), (0, 0, p["ceiling"] - 0.03)], 0.0035, dark, closed=False, res=3)
    b.lathe("Canopy_Piping", [(0, p["ceiling"] - 0.035), (0.055, p["ceiling"] - 0.035), (0.055, p["ceiling"]),
                              (0, p["ceiling"])], dark, segs=24, uv_tile=0)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
