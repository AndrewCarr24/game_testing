"""Raised reflecting pool in honed limestone: coping all round, a still dark water
surface just below the rim, and a head wall at the north end with a bronze spout lip
and a thin sheet of falling water. Long axis along Y, head wall at +Y.

Origin: floor centre of the footprint. Units are metres."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import courtyard_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common
materials = cc.materials

NAME = "CourtyardPool"

P = dict(
    name=NAME,
    length=8.6,
    width=2.8,          # outer
    coping=0.30,
    height=0.42,        # rim height
    water_z=0.345,
    head_wall_t=0.50,
    head_wall_h=1.30,
    lip_z=1.02,         # spout lip height
    sheet_w=1.7,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    stone, water = cc.limestone_mat(), cc.water_mat()
    bronze = materials.bronze()
    glass = materials.glass("M_Courtyard_WaterSheet", tint=(0.80, 0.93, 0.95), alpha=0.42, roughness=0.05)

    L, W, c, H = p["length"], p["width"], p["coping"], p["height"]
    ht = p["head_wall_t"]
    # side copings (full length), south end coping
    for side, sx in (("W", -1), ("E", 1)):
        cc.rbox(f"{n}_Coping_{side}", (c, L, H), (sx * (W / 2 - c / 2), 0, H / 2), stone, col, root,
                bevel=0.012, uv_tile=2.0, seg=2)
    cc.rbox(f"{n}_Coping_S", (W - 2 * c + 0.002, c, H), (0, -L / 2 + c / 2, H / 2), stone, col, root,
            bevel=0.012, uv_tile=2.0, seg=2)
    # water: from the south coping to the head wall
    y0, y1 = -L / 2 + c, L / 2 - ht
    wz = p["water_z"]
    wat = cc.rbox(f"{n}_Water", (W - 2 * c, y1 - y0, 0.05), (0, (y0 + y1) / 2, wz - 0.025), water, col, root,
                  bevel=0, uv_tile=0)
    # inner basin floor (never seen, stops light leaking through the water slab)
    cc.rbox(f"{n}_Basin", (W - 2 * c + 0.002, y1 - y0 + 0.002, 0.05), (0, (y0 + y1) / 2, 0.025), stone, col, root,
            bevel=0, uv_tile=2.0)
    # head wall with a cap that overhangs slightly
    hh = p["head_wall_h"]
    cc.rbox(f"{n}_HeadWall", (W, ht, hh - 0.04), (0, L / 2 - ht / 2, (hh - 0.04) / 2), stone, col, root,
            bevel=0.012, uv_tile=2.0)
    cc.rbox(f"{n}_HeadCap", (W + 0.06, ht + 0.06, 0.05), (0, L / 2 - ht / 2 + 0.01, hh - 0.025), stone, col, root,
            bevel=0.01, uv_tile=2.0)
    # spout lip (bronze) and the falling sheet
    sw = p["sheet_w"]
    ly = L / 2 - ht
    cc.rbox(f"{n}_SpoutLip", (sw + 0.12, 0.10, 0.04), (0, ly - 0.03, p["lip_z"]), bronze, col, root, bevel=0.004, uv_tile=0.5)
    cc.rbox(f"{n}_SpoutSlot", (sw + 0.12, 0.012, 0.16), (0, ly + 0.003, p["lip_z"] + 0.06), bronze, col, root,
            bevel=0.002, uv_tile=0.5)
    sheet_h = p["lip_z"] - wz
    sheet = cc.rbox(f"{n}_Sheet", (sw, 0.012, sheet_h), (0, ly - 0.075, wz + sheet_h / 2), glass, col, root,
                    bevel=0, uv_tile=0)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
