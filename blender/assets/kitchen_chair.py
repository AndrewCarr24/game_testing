"""Breakfast-table chair: walnut round legs with raked back posts, an oat linen
seat cushion and a curved linen back pad. Seat height 0.46 m. Faces -Y."""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitchen_lib as L  # noqa: E402

importlib.reload(L)
common, materials = L.common, L.materials

NAME = "KitchenChair"

P = dict(
    name=NAME,
    half_w=0.215,        # leg centre lines
    front_y=-0.20,
    back_y=0.21,
    seat_z=0.45,
    back_top=0.83,
    leg_r=0.0165,
    rake=0.07,
)


def build(**overrides):
    p = {**P, **overrides}
    b = L.Builder(p["name"])
    walnut = materials.walnut()
    fabric = L.cream_fabric()

    hw, yf, yb, sz = p["half_w"], p["front_y"], p["back_y"], p["seat_z"]
    r = p["leg_r"]
    for sx in (-1, 1):
        x = sx * hw
        b.tube(f"LegF{sx}", [(x, yf, 0.001), (x, yf, sz - 0.02)], r, walnut, closed=False, res=2)
        pts = [(x, yb + 0.015, 0.001), (x, yb, sz * 0.5), (x, yb, sz), (x, yb + p["rake"], p["back_top"])]
        pts = common.fillet_polyline(pts, 0.12, segments=6, closed=False)
        b.tube(f"LegB{sx}", pts, r, walnut, closed=False, res=2)
    rail_h = 0.05
    for name, size, c in (("RailF", (2 * hw, 0.03, rail_h), (0, yf, sz - 0.045)),
                          ("RailB", (2 * hw, 0.03, rail_h), (0, yb, sz - 0.045)),
                          ("RailL", (0.03, yb - yf, rail_h), (-hw, (yf + yb) / 2, sz - 0.045)),
                          ("RailR", (0.03, yb - yf, rail_h), (hw, (yf + yb) / 2, sz - 0.045))):
        b.box(name, size, c, walnut, bevel=0.003, seg=1, tile=0.5)
    cw, cd, ch = 2 * hw + 0.04, yb - yf + 0.05, 0.075
    bm = common.cushion_bmesh((cw, cd, ch), cuts=3, edge=0.02, crown={"+z": 0.012})
    seat = common.mesh_object(f"{b.n}_Seat", bm, b.col, fabric, b.root)
    seat.location = (0, (yf + yb) / 2, sz - 0.02 + ch / 2)
    common.add_subsurf(seat, 1, 1)
    common.box_uv(seat, tile=0.25)
    ang = math.atan2(p["rake"], p["back_top"] - sz)
    bz0, bz1 = 0.58, p["back_top"] - 0.02
    zc = (bz0 + bz1) / 2
    yc = yb + p["rake"] * (zc - sz) / (p["back_top"] - sz)
    bm = common.cushion_bmesh((2 * hw - 0.03, 0.05, bz1 - bz0), cuts=3, edge=0.015, crown={"-y": 0.01, "+y": 0.006})
    pad = common.mesh_object(f"{b.n}_Back", bm, b.col, fabric, b.root)
    pad.location = (0, yc, zc)
    pad.rotation_euler = (-ang, 0, 0)
    common.add_subsurf(pad, 1, 1)
    common.box_uv(pad, tile=0.25)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
