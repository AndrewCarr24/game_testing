"""Breakfast table: a 2.4 x 1.1 m walnut oval top on two Calacatta drum pedestals.
Long axis along X. Top surface 0.75 m. Origin is the floor centre."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitchen_lib as L  # noqa: E402

importlib.reload(L)
common, materials = L.common, L.materials

NAME = "KitchenTable"

P = dict(
    name=NAME,
    top=(2.4, 1.1, 0.045),
    height=0.75,
    pier_x=0.62,
    pier_r=0.2,
)


def build(**overrides):
    p = {**P, **overrides}
    b = L.Builder(p["name"])
    walnut = materials.walnut()
    marble = L.calacatta_mat()
    black = materials.black_metal()
    w, d, t = p["top"]
    h = p["height"]
    top = common.mesh_object(f"{b.n}_Top", common.rounded_slab_bmesh(w, d, t, d * 0.5 - 0.02, segments=14),
                             b.col, walnut, b.root)
    top.location = (0, 0, h - t / 2)
    common.add_bevel(top, 0.005)
    common.box_uv(top, tile=0.9)
    for sx in (-1, 1):
        r = p["pier_r"]
        prof = [(0.0, 0.0), (r * 1.05, 0.0), (r * 1.05, 0.02), (r * 0.8, 0.06), (r * 0.7, h - t - 0.1),
                (r * 0.9, h - t - 0.02), (r * 0.9, h - t), (0.0, h - t)]
        b.lathe(f"Pier{sx}", prof, marble, loc=(sx * p["pier_x"], 0, 0), segs=40, sharp=50, uv_tile=1.5)
    # slim black steel stretcher hidden in the shadow line under the top
    b.box("Stretcher", (2 * p["pier_x"], 0.05, 0.03), (0, 0, h - t - 0.015), black, bevel=0.002, tile=0)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
