"""Round reading side table: a walnut top with a slim bronze pedestal and a weighted
disc foot. Origin: floor centre. 0.52 m across, 0.56 m high."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import library_kit as kit  # noqa: E402
from library_kit import Mesh, common, materials  # noqa: E402

importlib.reload(kit)

NAME = "LibrarySideTable"

P = dict(name=NAME, radius=0.26, height=0.56, top_t=0.035)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    walnut, bronze = materials.walnut(), materials.bronze()
    r, H, t = p["radius"], p["height"], p["top_t"]
    wood, brz = Mesh(0.5), Mesh(0.5)
    wood.lathe([(0, H - t), (r - 0.012, H - t), (r, H - t + 0.008), (r, H - 0.008), (r - 0.012, H), (0, H)], segs=40)
    brz.lathe([(0, 0.0), (0.17, 0.0), (0.17, 0.016), (0.15, 0.024), (0.03, 0.03), (0.021, 0.06), (0.021, H - t - 0.02),
               (0.05, H - t - 0.012), (0.12, H - t), (0, H - t)], segs=28)
    wood.to_object(f"{n}_Top", col, walnut, root, smooth=True)
    brz.to_object(f"{n}_Base", col, bronze, root, smooth=True)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
