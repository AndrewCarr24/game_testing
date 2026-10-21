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
import ix_common  # noqa: E402  (hiding spot, prompts/interactivity.md)

importlib.reload(ix_common)

NAME = "KitchenTable"

P = dict(
    name=NAME,
    top=(2.4, 1.1, 0.045),
    height=0.75,
    pier_x=0.62,
    pier_r=0.2,
    hide=True,                # a hiding spot under the table (out between two chairs)
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
    uv = top.data.uv_layers["UVMap"]          # the walnut grain runs along v: turn it down the length
    for d_ in uv.data:
        pass  # the walnut scan is rotated so its grain runs along u (polyhaven_textures ROTATE): no swap
    for sx in (-1, 1):
        r = p["pier_r"]
        # turned marble pier: a plinth ring, a soft cove into the waisted shaft, a flared
        # capital under the top (floor and top contact faces aren't modelled)
        prof = [(r * 1.05, 0.0), (r * 1.05, 0.016), (r * 1.0, 0.022), (r * 0.86, 0.045), (r * 0.8, 0.07),
                (r * 0.72, 0.3), (r * 0.74, h - t - 0.16), (r * 0.82, h - t - 0.06), (r * 0.9, h - t - 0.02),
                (r * 0.9, h - t)]
        pier = b.lathe(f"Pier{sx}", prof, marble, loc=(sx * p["pier_x"], 0, 0), segs=28, sharp=50, uv_tile=0,
                       closed=False)
        L.cylindrical_uv(pier, 1.5)
    # slim black steel stretcher hidden in the shadow line under the top
    b.box("Stretcher", (2 * p["pier_x"], 0.05, 0.03), (0, 0, h - t - 0.015), black, bevel=0.002, tile=0)
    if p["hide"]:
        # hiding spot (open cover): under the top beside a pier, looking out between the chairs
        # (the kitchen's are 0.7 m apart: gaps at x = +-0.35)
        y_out = -d / 2 - 0.8
        ix_common.hide_spot(b.root, b.col, b.n, (0.28, -0.24, 0.5), [(0.33, y_out, 0.0), (-0.33, y_out, 0.0)],
                            "Hide under the table", "Crawl out", cover="open", pitch=-2)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
