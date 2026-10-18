"""Upholstered dining chair: oat linen seat cushion and a curved, wrap-around back
shell with a welted edge, on four slim tapered bronze legs (the rear pair sweeps up
behind the back) with a smoked-oak seat rail.

Units are metres. Faces -Y, origin at the floor centre. Seat height 0.46 m.
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "DiningChair"

P = dict(
    name=NAME,
    fabric_name="M_Fabric_Oat",
    fabric=(0.42, 0.37, 0.30),
    seat_w=0.50,            # seat cushion width
    seat_d=0.50,            # seat cushion depth
    seat_top=0.465,         # seat cushion top
    seat_t=0.085,           # cushion thickness
    rail_t=0.035,           # oak rail under the cushion
    leg_top_r=0.0125,
    leg_bot_r=0.0085,
    back_w=0.48,
    back_h=0.40,
    back_t=0.075,
    back_z0=0.52,           # bottom of the back shell
    back_tilt_deg=9.0,
    wrap=0.05,              # how far the back's sides curl forward
    arms=False,
)


def cone_between(bm, a, b, r1, r2, segs=10):
    a, b = Vector(a), Vector(b)
    d = b - a
    rot = d.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
    m = Matrix.Translation((a + b) / 2) @ rot
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                          radius1=r1, radius2=r2, depth=d.length, matrix=m)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    fabric = materials.fabric(p["fabric_name"], p["fabric"])
    bronze = materials.bronze()
    oak = materials.smoked_oak()

    st = p["seat_top"]
    sw, sd, sh = p["seat_w"], p["seat_d"], p["seat_t"]
    seat_y = -0.01                       # seat cushion centre in y
    cushion_z0 = st - sh
    rail_z0 = cushion_z0 - p["rail_t"]

    # --- seat cushion (soft crown, welted look from the bevelled edge)
    seat = common.mesh_object(
        f"{n}_Seat",
        common.cushion_bmesh((sw, sd, sh), cuts=2, edge=0.022,
                             crown={"+z": 0.018, "-y": 0.006, "+x": 0.004, "-x": 0.004}),
        col, fabric, root)
    seat.location = (0, seat_y, cushion_z0 + sh / 2)
    common.add_subsurf(seat, 1, 1)

    # --- oak seat rail, slightly inset under the cushion
    rail = common.mesh_object(
        f"{n}_Rail", common.box_bmesh((sw - 0.06, sd - 0.06, p["rail_t"] + 0.004)),
        col, oak, root)
    rail.location = (0, seat_y, rail_z0 + (p["rail_t"] + 0.004) / 2)
    common.add_bevel(rail, 0.004, 2)

    # --- legs: front pair straight and tapered; rear pair a sabre curve from the floor,
    #     past the seat rail and up behind the back shell (tube ends sink into it)
    lx = sw / 2 - 0.045
    yf = seat_y - sd / 2 + 0.05
    yb = seat_y + sd / 2 - 0.06
    top_z = rail_z0 + 0.01
    tilt = math.radians(p["back_tilt_deg"])
    bw, bh, bt = p["back_w"], p["back_h"], p["back_t"]
    bm = bmesh.new()
    for sx in (-1, 1):
        cone_between(bm, (sx * (lx + 0.01), yf - 0.012, 0.0), (sx * lx, yf, top_z),
                     p["leg_bot_r"], p["leg_top_r"])
    common.mesh_object(f"{n}_LegsFront", bm, col, bronze, root)

    zt = p["back_z0"] + bh * 0.80
    slope = math.tan(tilt)
    back_zc = p["back_z0"] + bh / 2
    # rear leg centre line y at height z above the seat (follows the back's lean)
    def leg_y(z):
        return yb + 0.045 + (z - rail_z0) * slope
    for sx in (-1, 1):
        x = sx * (lx - 0.012)
        pts = [(x * 1.02, yb + 0.085, 0.0095), (x * 1.0, yb + 0.012, 0.30),
               (x, leg_y(rail_z0 + 0.06), rail_z0 + 0.06), (x, leg_y(p["back_z0"]), p["back_z0"]),
               (x * 0.99, leg_y(zt), zt)]
        pts = common.fillet_polyline(pts, 0.12, segments=6, closed=False)
        common.tube_object(f"{n}_LegRear_{'L' if sx < 0 else 'R'}", pts, p["leg_top_r"] * 0.95,
                           col, bronze, root, closed=False, profile_res=2)

    # --- the back shell: a cushion box bent round the sitter and tilted back
    bmb = common.cushion_bmesh((bw, bt, bh), cuts=3, edge=0.02,
                               crown={"-y": 0.016, "+y": 0.004, "+z": 0.006})
    for v in bmb.verts:
        u = v.co.x / (bw / 2)
        zr = (v.co.z + bh / 2) / bh       # 0 bottom .. 1 top
        v.co.y -= p["wrap"] * u * u * (0.35 + 0.65 * zr)       # sides curl forward
        v.co.x *= 1.0 - 0.07 * (1 - zr)                        # slightly narrower at the base
    rot = Matrix.Rotation(-tilt, 4, "X")
    bmesh.ops.transform(bmb, matrix=rot, verts=bmb.verts)
    back = common.mesh_object(f"{n}_Back", bmb, col, fabric, root)
    # the rear face (centre height) rests on the leg lines
    back.location = (0, leg_y(back_zc) - 0.01 - bt / 2 * math.cos(tilt) + 0.012, back_zc)
    common.add_subsurf(back, 1, 1)

    for ob in (seat, back):
        common.box_uv(ob, tile=0.25)
    common.box_uv(rail, tile=0.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    for o in parts:
        if not o.data.uv_layers:
            common.box_uv(o, tile=0.5)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
