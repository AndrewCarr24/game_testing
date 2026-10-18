"""Two-tier dumbbell rack: a graphite frame with angled saddle shelves, ten pairs of
hex rubber dumbbells (5-30 kg: heads grow with weight, chrome handles) and a
small oak top rail. Front faces -Y (the dumbbells are taken from the front);
2.0 m wide, 0.55 deep, 0.95 high. Origin is the floor centre."""
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

NAME = "GuestDumbbellRack"

P = dict(name=NAME, width=2.0, depth=0.56, height=0.88, pairs=5)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    gr, rub, steel, oak = guest_mats.graphite(), guest_mats.rubber(), guest_mats.materials.steel(), guest_mats.oak()
    own = (col, root, n)
    A = guest_mats.add
    W, D, H = p["width"], p["depth"], p["height"]
    # frame: end frames (two uprights + rails) and long rails
    for sx in (-1, 1):
        x = sx * (W / 2 - 0.04)
        A(own, f"Leg_F{sx}", common.box_bmesh((0.06, 0.06, H)), gr, (x, -D / 2 + 0.06, H / 2), 0.006)
        A(own, f"Leg_B{sx}", common.box_bmesh((0.06, 0.06, H - 0.0)), gr, (x, D / 2 - 0.06, H / 2), 0.006)
        A(own, f"Foot{sx}", common.box_bmesh((0.06, D, 0.04)), gr, (x, 0, 0.02), 0.005)
    # shelves at 0.25 and 0.57 (z of the saddle's lowest line)
    shelf_z = (0.27, 0.62)
    bm_fr = bmesh.new()
    for z in shelf_z:
        for yy in (-D / 2 + 0.06, D / 2 - 0.06):
            bmesh.ops.create_cube(bm_fr, size=1.0, matrix=Matrix.Translation((0, yy, z - 0.035)) @ Matrix.Diagonal((W - 0.04, 0.05, 0.05, 1.0)))
        # tilted shelf plate
        bmesh.ops.create_cube(bm_fr, size=1.0, matrix=Matrix.Translation((0, 0, z - 0.04)) @ Matrix.Diagonal((W - 0.06, D - 0.14, 0.016, 1.0)))
    A(own, "Shelves", bm_fr, gr, (0, 0, 0), 0)
    A(own, "TopRail", common.box_bmesh((W + 0.02, 0.07, 0.03)), oak, (0, D / 2 - 0.06, H + 0.015), 0.004)
    # dumbbells
    seg = 6
    n_pairs = p["pairs"]
    pitch = (W - 0.18) / (n_pairs * 2)
    heads_bm, handles_bm = bmesh.new(), bmesh.new()
    for tier, z in enumerate(shelf_z):
        for i in range(n_pairs * 2):
            x = -W / 2 + 0.11 + pitch * (i + 0.5)
            wt = i // 2 / (n_pairs - 1)      # 0..1 across the rack
            hr = 0.040 + 0.025 * wt + (0.008 if tier else 0)
            hl = 0.075 + 0.05 * wt
            # along y: dumbbell lies with its handle along Y
            hlen = 0.16
            for sy in (-1, 1):
                bmesh.ops.create_cone(heads_bm, cap_ends=True, cap_tris=False, segments=seg, radius1=hr, radius2=hr, depth=hl,
                                      matrix=Matrix.Translation((x, sy * (hlen / 2 + hl / 2), z + hr - 0.02)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
            bmesh.ops.create_cone(handles_bm, cap_ends=True, cap_tris=False, segments=8, radius1=0.0145, radius2=0.0145, depth=hlen + 0.02,
                                  matrix=Matrix.Translation((x, 0, z + hr - 0.02)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    A(own, "Heads", heads_bm, rub, (0, 0, 0), 0)
    A(own, "Handles", handles_bm, steel, (0, 0, 0), 0)
    parts = guest_mats.consolidate(root, max_dim=0.35)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
