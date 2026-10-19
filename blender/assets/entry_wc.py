"""Wall-hung WC in glossy white ceramic: a rimless oval pan, a soft-close seat and lid, a
chamfered rear block that meets the wall, and a polished-bronze flush plate with two
buttons on the wall above it.

Origin: floor point under the centre of the pan. The wall is at +Y (0.30 m behind the
origin) and the lid faces -Y. Units are metres.
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import table_lamp  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "EntryWC"

P = dict(
    name=NAME,
    rx=0.18, ry=0.275,      # oval radii of the pan
    rim_z=0.40,
    wall_y=0.30,
    lid_t=0.030,
)


def oval(bm, k):
    bmesh.ops.scale(bm, vec=(1.0, k, 1.0), verts=bm.verts)
    return bm


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    ceramic = common.pbr_material("M_Entry_Ceramic", (0.80, 0.80, 0.78), roughness=0.10)
    bronze_p = common.pbr_material("M_Entry_Bronze_Polished", (0.50, 0.30, 0.14), roughness=0.2, metallic=1.0)
    black = materials.black_metal()

    rx, ry, rz = p["rx"], p["ry"], p["rim_z"]
    k = ry / rx
    # ---- pan: swept from the underside up the outside, over the rim and down inside -------
    outer = table_lamp.catmull([(0.045, 0.145), (0.10, 0.17), (0.155, 0.235), (rx, 0.31), (rx, rz - 0.015)], per=3)
    inner = table_lamp.catmull([(rx - 0.012, rz - 0.012), (rx - 0.035, 0.34), (rx - 0.08, 0.27), (0.07, 0.20),
                                (0.03, 0.18)], per=3)
    prof = [(0.0, 0.145)]
    for pt in outer + [(rx - 0.003, rz)] + inner + [(0.0, 0.178)]:
        if abs(pt[0] - prof[-1][0]) + abs(pt[1] - prof[-1][1]) > 1e-4:
            prof.append(pt)
    pan = table_lamp.lathe(prof, 40, sharp=55)
    oval(pan, k)
    common.mesh_object(f"{n}_Pan", pan, col, ceramic, root)

    # ---- rear block joining the pan to the wall ----------------------------------------------
    bx = rx * 2
    by0 = ry - 0.12
    blk = common.box_bmesh((bx * 0.92, p["wall_y"] - by0, 0.17))
    bmesh.ops.translate(blk, vec=(0, (p["wall_y"] + by0) / 2, 0.31), verts=blk.verts)
    rear = common.mesh_object(f"{n}_Rear", blk, col, ceramic, root, smooth=False)
    common.add_bevel(rear, 0.02, segments=3)

    # ---- seat ring and closed lid: a touch shorter than the pan at the back so the hinges sit
    # on the rim; eased seat edge, softly domed lid that overhangs the seat by a hair ---------------
    lt = p["lid_t"]
    sx_r = rx + 0.012
    sy_r = ry - 0.014
    syc = -0.022
    seat = table_lamp.lathe([(0.0, 0.0), (sx_r - 0.006, 0.0), (sx_r, 0.006), (sx_r, 0.016), (sx_r - 0.005, 0.021),
                             (0.0, 0.021)], 48, sharp=50)
    oval(seat, sy_r / sx_r)
    seat_ob = common.mesh_object(f"{n}_Seat", seat, col, ceramic, root)
    seat_ob.location = (0, syc, rz + 0.002)
    lr = sx_r + 0.003
    lid = table_lamp.lathe([(0.0, 0.0), (lr - 0.004, 0.0), (lr, 0.004), (lr, lt - 0.014), (lr - 0.010, lt - 0.005),
                            (lr * 0.55, lt - 0.001), (0.0, lt)], 48, sharp=50)
    oval(lid, (sy_r + 0.003) / lr)
    lid_ob = common.mesh_object(f"{n}_Lid", lid, col, ceramic, root)
    lid_ob.location = (0, syc, rz + 0.025)
    # hinges: two bronze bosses on the rear of the rim and the pivot bar into the seat
    hy = syc + sy_r + 0.014
    hinge = bmesh.new()
    for sx in (-1, 1):
        table_lamp.cylinder_between(hinge, (sx * 0.085, hy, rz - 0.002), (sx * 0.085, hy, rz + 0.030), 0.012, segs=14)
    table_lamp.cylinder_between(hinge, (-0.085, hy - 0.006, rz + 0.016), (0.085, hy - 0.006, rz + 0.016), 0.006, segs=10)
    common.mesh_object(f"{n}_Hinge", hinge, col, bronze_p, root)

    # ---- flush plate on the wall -------------------------------------------------------------------
    pw, ph = 0.24, 0.16
    plate = common.mesh_object(f"{n}_Plate", common.box_bmesh((pw, 0.010, ph)), col, bronze_p, root, smooth=False)
    plate.location = (0, p["wall_y"] - 0.005, 0.95)
    common.add_bevel(plate, 0.003, segments=2)
    for sx in (-1, 1):
        b = common.mesh_object(f"{n}_Button_{'L' if sx < 0 else 'R'}", common.box_bmesh((0.07, 0.006, 0.05)), col, black, root,
                               smooth=False)
        b.location = (sx * 0.055, p["wall_y"] - 0.013, 0.95)
        common.add_bevel(b, 0.002, segments=2)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
