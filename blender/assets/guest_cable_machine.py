"""Functional trainer (dual adjustable pulley): two weight-stack towers joined by a
top crossbar, graphite frame with oak panels, steel guide rods, plate stacks (one
mesh) with a brass selector pin, pulleys, cables with handles hanging from the
carriages and a pull-up bar. The user stands at -Y (front), the machine's back at
+Y. 1.45 m wide, 0.80 deep, 2.2 m tall. Origin is the floor centre."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestCableMachine"

P = dict(name=NAME, width=1.45, depth=0.80, height=2.2, plates=14)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    gr, rub, steel = guest_mats.graphite(), guest_mats.rubber(), guest_mats.materials.steel()
    oak, brass = guest_mats.oak(), guest_mats.brass()
    own = (col, root, n)
    A = guest_mats.add
    W, D, H = p["width"], p["depth"], p["height"]
    tw = 0.40                       # tower width (x)
    tx = W / 2 - tw / 2
    ty = D / 2 - 0.16               # tower depth centre (towers sit at the back)
    # base: two long skids and a front crossbar
    for sx in (-1, 1):
        A(own, f"Skid{sx}", common.box_bmesh((0.08, D, 0.06)), gr, (sx * (tx + 0.165), 0, 0.03), 0.008)
    A(own, "BaseBar", common.box_bmesh((W - 0.08, 0.08, 0.06)), gr, (0, -D / 2 + 0.04, 0.03), 0.008)
    # rubber standing plate between the skids
    A(own, "Platform", common.box_bmesh((W - 0.30, D - 0.10, 0.014)), rub, (0, 0.03, 0.007), 0.003)
    # tower uprights (front and rear posts)
    for sx in (-1, 1):
        for sy, nm in ((-1, "F"), (1, "B")):
            for dx, nd in ((-1, "i"), (1, "o")):
                A(own, f"Post_{nm}{nd}{sx}", common.box_bmesh((0.07, 0.07, H)), gr, (sx * tx + dx * 0.165, ty + sy * 0.12, H / 2), 0.008)
    # top crossbar
    A(own, "TopBar", common.box_bmesh((W, 0.10, 0.09)), gr, (0, ty, H - 0.045), 0.01)
    # oak side panels on the outer faces of the towers
    for sx in (-1, 1):
        A(own, f"Panel{sx}", common.box_bmesh((0.018, 0.31, H - 0.3)), oak, (sx * (tx + tw / 2 + 0.009), ty, (H - 0.3) / 2 + 0.12), 0.004)
    # rear panel (closes the back)
    A(own, "BackPlate", common.box_bmesh((W - 2 * 0.05, 0.02, 0.9)), gr, (0, ty + 0.16, 1.45), 0.004)
    # weight stacks: slabs in one mesh per tower pair
    plates = p["plates"]
    ph = 0.047
    stack = bmesh.new()
    for sx in (-1, 1):
        for k in range(plates):
            bmesh.ops.create_cube(stack, size=1.0, matrix=Matrix.Translation((sx * tx, ty, 0.18 + k * (ph + 0.004) + ph / 2))
                                  @ Matrix.Diagonal((0.24, 0.17, ph, 1.0)))
    # every plate gets a 4 mm chamfer (the stack reads as separate cast plates, not a block)
    bmesh.ops.bevel(stack, geom=stack.edges[:], offset=0.004, segments=1, affect="EDGES")
    # top plate with the lift rod's collar
    for sx in (-1, 1):
        zt = 0.18 + plates * (ph + 0.004)
        bmesh.ops.create_cube(stack, size=1.0, matrix=Matrix.Translation((sx * tx, ty, zt + 0.015))
                              @ Matrix.Diagonal((0.26, 0.18, 0.03, 1.0)))
        bmesh.ops.create_cone(stack, cap_ends=True, cap_tris=False, segments=10, radius1=0.022, radius2=0.022,
                              depth=0.05, matrix=Matrix.Translation((sx * tx, ty, zt + 0.055)))
    A(own, "Stack", stack, gr, (0, 0, 0), 0)
    # guide rods
    rods = bmesh.new()
    for sx in (-1, 1):
        for dx in (-0.09, 0.09):
            bmesh.ops.create_cone(rods, cap_ends=True, cap_tris=False, segments=8, radius1=0.008, radius2=0.008,
                                  depth=H - 0.2, matrix=Matrix.Translation((sx * tx + dx, ty - 0.05, H / 2)))
    A(own, "Rods", rods, steel, (0, 0, 0), 0)
    # selector pins
    for sx in (-1, 1):
        A(own, f"Pin{sx}", guest_mats.cyl_bmesh(0.006, 0.12, seg=8, axis="y"), brass, (sx * tx, ty - 0.14, 0.18 + 5 * (ph + 0.004) + ph / 2), 0)
    # carriages on a slider at 1.3 m and 0.4 m (steel pulleys on brackets)
    # inner faces of the towers: slider rails
    for sx in (-1, 1):
        A(own, f"Slider{sx}", common.box_bmesh((0.03, 0.03, H - 0.55)), steel, (sx * (tx - tw / 2 + 0.03), ty - 0.14, H / 2 + 0.05), 0.004)
        for z, nm in ((1.25, "Hi"), (0.35, "Lo")):
            A(own, f"Carriage_{nm}{sx}", common.box_bmesh((0.08, 0.06, 0.10)), gr, (sx * (tx - tw / 2 + 0.04), ty - 0.17, z), 0.006)
            A(own, f"Pulley_{nm}{sx}", guest_mats.cyl_bmesh(0.05, 0.02, seg=20, axis="x"), steel, (sx * (tx - tw / 2 - 0.0), ty - 0.23, z), 0.0)
        # cables: from the top pulley down to a carriage, then a handle hanging out front
        pts = [(sx * (tx - tw / 2 + 0.04), ty - 0.23, 1.30), (sx * (tx - tw / 2 + 0.04), ty - 0.23, H - 0.12)]
        c = common.tube_object(f"{n}_CableUp{sx}", pts, 0.0035, col, steel, root, closed=False, profile_res=1)
        c2 = common.tube_object(f"{n}_CableHang{sx}", [(sx * (tx - tw / 2 + 0.04), ty - 0.26, 1.25), (sx * (tx - tw / 2 - 0.04), -D / 2 + 0.22, 0.95)],
                                0.0035, col, steel, root, closed=False, profile_res=1)
        # handle: a small D-grip
        hz = 0.95
        A(own, f"Handle{sx}", guest_mats.cyl_bmesh(0.012, 0.13, seg=10, axis="x"), rub, (sx * (tx - tw / 2 - 0.04), -D / 2 + 0.22, hz - 0.03), 0)
        A(own, f"Strap{sx}", common.box_bmesh((0.012, 0.01, 0.06)), gr, (sx * (tx - tw / 2 - 0.04) - 0.0, -D / 2 + 0.22, hz + 0.0), 0.002)
    # pull-up bar across the top front
    A(own, "PullBar", guest_mats.cyl_bmesh(0.016, W - 0.5, seg=14, axis="x"), steel, (0, -D / 2 + 0.25, H - 0.15), 0)
    for sx in (-1, 1):
        A(own, f"PullArm{sx}", common.box_bmesh((0.04, D / 2 + 0.05 - 0.0, 0.04)), gr, (sx * (W / 2 - 0.25), -D / 2 + 0.25 + (D / 2 - 0.25 - 0.04) * 0, H - 0.15), 0.004)
    # centre screen / readout panel
    A(own, "Screen", common.box_bmesh((0.34, 0.012, 0.2)), guest_mats.screen(), (0, ty - 0.06, 1.55), 0, tile=0.25)
    parts = guest_mats.consolidate(root, max_dim=0.45)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
