"""Reading floor lamp: a bronze disc foot, slim pole and a glowing linen drum shade
(point light at z = 1.42). Origin: floor centre. 0.38 m across, 1.6 m high."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import library_kit as kit  # noqa: E402
from library_kit import Mesh, common, materials  # noqa: E402

importlib.reload(kit)

NAME = "LibraryFloorLamp"

P = dict(name=NAME, height=1.6, shade_r=0.19, shade_h=0.28)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    bronze = materials.bronze()
    glow = materials.emissive("M_LampShade_Warm", (1.0, 0.78, 0.52), 1.5)
    H, R, sh = p["height"], p["shade_r"], p["shade_h"]
    zs = H - sh
    brz = Mesh(0.5)
    brz.lathe([(0, 0.0), (0.15, 0.0), (0.15, 0.012), (0.135, 0.02), (0.02, 0.026), (0.011, 0.05), (0.011, zs + 0.02),
               (0.0, zs + 0.02)], segs=28)
    # spokes under the shade, a finial on top
    for i in range(3):
        import math
        a = i * 2 * math.pi / 3
        brz.box((0.5 * R * math.cos(a), 0.5 * R * math.sin(a), zs + 0.01), (R, 0.006, 0.006), rot=(a, "z"))
    brz.lathe([(0, 0.0), (0.012, 0.0), (0.012, 0.02), (0.0, 0.03)], segs=10, centre=(0, 0, H - 0.0))
    # rims
    for z in (zs, H - 0.006):
        brz.lathe([(R - 0.004, 0.0), (R + 0.002, 0.0), (R + 0.002, 0.006), (R - 0.004, 0.006)], segs=40, centre=(0, 0, z))
    brz.to_object(f"{n}_Bronze", col, bronze, root, smooth=True)
    shade = Mesh(0.5)
    shade.lathe([(R - 0.004, zs), (R, zs), (R, H), (R - 0.004, H), (R - 0.004, zs)], segs=40)
    shade.to_object(f"{n}_Shade", col, glow, root, smooth=True)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
