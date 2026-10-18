"""Guest armchair: a deep, low sage lounge chair with soft rolled arms, a loose seat
cushion, a linen lumbar cushion and four tapered pale-oak legs with brass caps.
Faces -Y; origin is the floor centre."""
import importlib
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestArmchair"

P = dict(name=NAME, width=0.84, depth=0.88, leg_h=0.16, seat_h=0.42, arm_h=0.62, back_h=0.92)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    oak, brass = guest_mats.oak(), guest_mats.brass()
    sage, linen = guest_mats.sage_light(), guest_mats.linen()
    own = (col, root, n)
    A = guest_mats.add
    W, D, LH, SH, AH, BH = p["width"], p["depth"], p["leg_h"], p["seat_h"], p["arm_h"], p["back_h"]
    parts = []

    # legs: splayed slightly outwards
    for fx, fy, nm in ((-1, -1, "FL"), (1, -1, "FR"), (-1, 1, "BL"), (1, 1, "BR")):
        lg = A(own, f"Leg_{nm}", guest_mats.taper_bmesh(0.05, 0.03, LH), oak,
               (fx * (W / 2 - 0.09), fy * (D / 2 - 0.10), LH / 2), 0.002)
        A(own, f"Cap_{nm}", guest_mats.cyl_bmesh(0.017, 0.012, seg=12), brass,
          (fx * (W / 2 - 0.09 + 0.012 * fx), fy * (D / 2 - 0.10 + 0.012 * fy), 0.006), 0, bucket=parts)
    # base box (sits on the legs), and the plinth rail visible between legs
    base = common.mesh_object(f"{n}_Base", common.cushion_bmesh((W, D, SH - LH - 0.12), cuts=4, edge=0.05,
                              crown={"-y": 0.01, "+x": 0.01, "-x": 0.01}), col, sage, root)
    base.location = (0, 0, LH + (SH - LH - 0.12) / 2)
    common.add_subsurf(base)
    common.box_uv(base, 0.25)
    # arms: rounded bolsters
    aw = 0.17
    for s, sx in (("L", -1), ("R", 1)):
        arm = common.mesh_object(f"{n}_Arm_{s}", common.cushion_bmesh((aw, D - 0.02, AH - (SH - 0.14)), cuts=4, edge=0.06,
                                 crown={"+z": 0.02, "-y": 0.012, "+x": 0.01, "-x": 0.01}), col, sage, root)
        arm.location = (sx * (W / 2 - aw / 2), 0, (AH + SH - 0.14) / 2)
        common.add_subsurf(arm)
        common.box_uv(arm, 0.25)
    # back: a thick reclined cushion block
    bt = 0.20
    back = common.mesh_object(f"{n}_Back", common.cushion_bmesh((W - 0.02, bt, BH - SH + 0.14), cuts=4, edge=0.06,
                              crown={"-y": 0.03, "+z": 0.012, "+y": 0.01}), col, sage, root)
    t = math.radians(-12)
    back.rotation_euler = (t, 0, 0)
    bh = BH - SH + 0.14
    back.location = (0, D / 2 - bt / 2 - 0.02 + math.sin(math.radians(12)) * bh / 2 * 0.9, SH - 0.14 + bh / 2 * math.cos(t))
    common.add_subsurf(back)
    common.box_uv(back, 0.25)
    # loose seat cushion
    sw = W - 2 * aw + 0.02
    sd = D - bt - 0.08
    seat = common.mesh_object(f"{n}_Seat", common.cushion_bmesh((sw, sd, 0.14), cuts=4, edge=0.05,
                              crown={"+z": 0.03, "-y": 0.01}), col, sage, root)
    seat.location = (0, -D / 2 + sd / 2 + 0.03, SH - 0.07)
    common.add_subsurf(seat)
    common.box_uv(seat, 0.25)
    # linen lumbar cushion leaning against the back
    cu = common.mesh_object(f"{n}_Cushion", common.cushion_bmesh((0.36, 0.11, 0.34), cuts=4, edge=0.04,
                            crown={"-y": 0.02, "+z": 0.01}), col, linen, root)
    cu.rotation_euler = (math.radians(-22), 0, math.radians(7))
    cu.location = (0.13, D / 2 - bt - 0.06, SH + 0.17)
    common.add_subsurf(cu)
    common.box_uv(cu, 0.25)
    parts = guest_mats.consolidate(root, max_dim=0.35)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
