"""Water closet: a wall-hung ceramic WC with a soft-close seat and lid, a dark-marble-clad
service wall behind it with a brass flush plate, a floating stone ledge and a brass
paper-roll holder, and a free-standing book-matched marble privacy partition in front.

Origin: the WC's centre on the floor, at the service wall. The back (the wall) is at
+Y, the WC faces -Y; the partition runs across X at y = -partition_gap. To fit a corner
against the west wall, rotate 90 (the WC then faces east).
"""
import importlib
import math
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import bath_common as bc  # noqa: E402

importlib.reload(common)
importlib.reload(bc)

NAME = "BathToilet"

P = dict(
    name=NAME,
    segs=48,
    pan_len=0.56, pan_w=0.37,
    rim_z=0.40,
    service_depth=0.14,          # the clad service wall stands this far off the real wall
    service_w=1.25,
    service_h=1.25,
    partition_gap=1.55,          # from the wall to the partition's inner face
    partition_len=2.1,           # along X, centred on the WC axis offset (see partition_off)
    partition_off=0.08,          # partition centre relative to the WC axis along X (the screen returns into the south wall)
    partition_h=2.7,
    partition_t=0.08,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    ceramic, brass, marble, stone = bc.ceramic(), bc.brass(), bc.marble_wall(), bc.stone()
    black = materials.black_metal()
    segs = p["segs"]

    sd = p["service_depth"]
    # origin on the floor at the *front* of the service wall; the real wall is at +y = sd
    L, Wd, zr = p["pan_len"], p["pan_w"], p["rim_z"]
    A, B = Wd / 2, L / 2
    cy = -B + 0.0                              # the pan runs from y = 0 (against the service wall) to -L

    # ---- pan: lofted rings from a narrow underside up to the rim
    def ring(z, a, b, yc, expo=2.4):
        pts = bc.superellipse(a, b, expo, segs)
        return (z, [(x, y + yc) for x, y in pts])
    rings = [("pole", 0, cy + 0.02, 0.17),
             ring(0.172, 0.09, 0.14, cy + 0.04), ring(0.20, 0.135, 0.21, cy + 0.02),
             ring(0.25, 0.168, 0.255, cy + 0.0), ring(0.32, 0.182, 0.275, cy), ring(0.375, A, B, cy),
             ring(zr - 0.012, A + 0.003, B + 0.003, cy), ring(zr, A - 0.004, B - 0.004, cy)]
    rings.append(("pole", 0, cy, zr))           # closed rim deck (the hinge area behind the seat shows)
    common.mesh_object(f"{n}_Pan", bc.loft(rings, segs), col, ceramic, root)

    # seat ring and closed lid, ending short of the wall so the hinges sit on the rear deck.
    # The lid overhangs the seat slightly and has a soft domed top; a hairline shows between them.
    back_gap = 0.045
    sa, sb = A + 0.004, B + 0.004 - back_gap / 2
    syc = cy - back_gap / 2 - 0.004

    def ring_xy(a, b, z):
        return (z, [(x, y + syc) for x, y in bc.superellipse(a, b, 2.4, segs)])

    seat_z0 = zr + 0.003
    seat = [ring_xy(sa - 0.006, sb - 0.006, seat_z0), ring_xy(sa, sb, seat_z0 + 0.005), ring_xy(sa, sb, seat_z0 + 0.016),
            ring_xy(sa - 0.005, sb - 0.005, seat_z0 + 0.021), ("pole", 0, syc, seat_z0 + 0.021)]
    seat_bm = bc.loft(seat, segs)
    common.mesh_object(f"{n}_Seat", seat_bm, col, ceramic, root)
    lz = seat_z0 + 0.023
    lid = [ring_xy(sa - 0.002, sb - 0.002, lz), ring_xy(sa + 0.002, sb + 0.002, lz + 0.004),
           ring_xy(sa + 0.002, sb + 0.002, lz + 0.011), ring_xy(sa - 0.008, sb - 0.008, lz + 0.019),
           ring_xy(sa * 0.6, sb * 0.6, lz + 0.026), ("pole", 0, syc, lz + 0.028)]
    common.mesh_object(f"{n}_Lid", bc.loft(lid, segs), col, ceramic, root)
    # hinge: two brass bosses on the rear deck and the pivot bar through the seat's back
    hb = bmesh.new()
    hy = -back_gap / 2 + 0.002
    for sx in (-1, 1):
        bc.cylinder_between(hb, (sx * 0.085, hy, zr), (sx * 0.085, hy, zr + 0.026), 0.013, 14)
        bc.cylinder_between(hb, (sx * 0.085, hy, zr + 0.026), (sx * 0.085, hy, zr + 0.029), 0.010, 14)
    bc.cylinder_between(hb, (-0.085, hy - 0.004, zr + 0.017), (0.085, hy - 0.004, zr + 0.017), 0.0065, 10)
    common.mesh_object(f"{n}_Hinge", hb, col, brass, root)

    # wall bracket block under the pan
    bc.box(col, root, f"{n}_Block", (0.26, 0.10, 0.22), (0, -0.05, 0.30), ceramic, bevel=0.01)

    # ---- service wall (marble, in front of the real wall), flush plate, ledge, roll holder
    sw, sh = p["service_w"], p["service_h"]
    bc.box(col, root, f"{n}_ServiceWall", (sw, sd, sh), (0, sd / 2, sh / 2), bc.marble_dark(), bevel=0.0, uv_tile=2.4)
    bc.box(col, root, f"{n}_PipingLedge", (sw + 0.04, sd + 0.07, 0.05), (0, sd / 2 - 0.035, sh + 0.025), stone, bevel=0.004, uv_tile=1.0)
    bc.box(col, root, f"{n}_FlushPlate", (0.24, 0.012, 0.16), (0, -0.006, 0.95), brass, bevel=0.003)
    for sx in (-1, 1):
        btn = bc.lathe([(0.0, 0.0), (0.028, 0.0), (0.030, 0.003), (0.030, 0.008), (0.0, 0.008)], 24)
        b = common.mesh_object(f"{n}_FlushButton", btn.copy(), col, ceramic, root)
        b.rotation_euler = (math.radians(90), 0, 0)
        b.location = (sx * 0.055, -0.012, 0.95)
    # paper roll holder on the right of the pan
    hx, hz = 0.32, 0.62
    rh = bmesh.new()
    bc.cylinder_between(rh, (hx, 0.0, hz), (hx, -0.06, hz), 0.006, 10)
    bc.cylinder_between(rh, (hx - 0.035, -0.07, hz), (hx + 0.035, -0.07, hz), 0.006, 10)
    common.mesh_object(f"{n}_RollHolder", rh, col, brass, root)
    roll = bmesh.new()
    bc.cylinder_between(roll, (hx - 0.05, -0.07, hz), (hx + 0.05, -0.07, hz), 0.026, 24)
    common.box_uv(common.mesh_object(f"{n}_PipingRoll", roll, col,
                                     materials.fabric("M_Fabric_Linen_Ivory", (0.55, 0.52, 0.46)), root), tile=0.25)

    # ---- privacy partition (book-matched marble slab, floating 3 cm above the floor)
    pg, pl, ph, pt = p["partition_gap"], p["partition_len"], p["partition_h"], p["partition_t"]
    bc.box(col, root, f"{n}_Partition", (pl, pt, ph - 0.03), (p["partition_off"], -pg - pt / 2, 0.03 + (ph - 0.03) / 2),
                  marble, bevel=0.0, uv_tile=2.4)
    # brass shadow-gap strip along the base so it seems to hover
    bc.box(col, root, f"{n}_PartitionFoot", (pl - 0.1, pt - 0.03, 0.03), (p["partition_off"], -pg - pt / 2, 0.015),
           black, bevel=0.0)
    bc.merge(root, bc.by_material(root, ceramic), f"{n}_Ceramic")
    bc.merge(root, bc.by_material(root, brass), f"{n}_PipingBrass")
    bc.merge(root, bc.by_material(root, black), f"{n}_PipingFoot")
    return root, bc.parts_of(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
