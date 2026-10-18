"""Floor-to-ceiling wine racking for the cellar: a black plinth and smoked-oak storage
cabinet with an oak worktop, a grid of individual bottle cells (cheap low-poly bottles:
mostly bottom-out, some neck-out with bronze foil), and a fluted smoked-oak crown that
runs up to the ceiling. `bays` bays of `bay_w` metres side by side.

Units are metres. The front faces -Y (the back goes against a wall), origin at the floor
centre of the whole run; the run is centred on x = 0. Height = `height` (the ceiling).
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "DiningWineRack"

P = dict(
    name=NAME,
    bays=4,
    bay_w=1.0,
    depth=0.40,            # racking depth
    height=4.2,            # floor to ceiling
    plinth_h=0.08,
    cabinet_top=0.90,      # worktop underside
    top_t=0.035,
    cabinet_depth=0.48,
    rack_top=2.60,
    cols=8,                # bottle cells per bay
    rows=12,
    divider=0.010,
    bottle_r=0.042,
    bottle_len=0.08,
    neck_out=0.06,         # share of cells showing a neck-out bottle
    empty=0.07,            # share of cells left empty
    seed=3,
)


# ------------------------------------------------------------------- bottles

def _rand(i, j, k):
    return (math.sin(i * 12.9898 + j * 78.233 + k * 37.719) * 43758.5453) % 1.0


def bottle_bottom_out(bm, x, y_front, z, r, length, segs=6):
    """Open octagonal tube + front cap, axis along +Y, front end at y_front."""
    m = Matrix.Translation((x, y_front + length / 2, z)) @ Matrix.Rotation(math.pi / 2, 4, "X")
    bmesh.ops.create_cone(bm, cap_ends=False, segments=segs, radius1=r, radius2=r, depth=length, matrix=m)
    cap = Matrix.Translation((x, y_front, z)) @ Matrix.Rotation(math.pi / 2, 4, "X")
    bmesh.ops.create_circle(bm, cap_ends=True, cap_tris=False, segments=segs, radius=r, matrix=cap)


def bottle_neck_out(bm, foil, x, y_front, z, r, segs=6):
    """Neck facing the viewer: a short shoulder and neck with a foil capsule."""
    body = 0.09
    m = Matrix.Translation((x, y_front + 0.085 + body / 2, z)) @ Matrix.Rotation(math.pi / 2, 4, "X")
    bmesh.ops.create_cone(bm, cap_ends=False, segments=segs, radius1=r, radius2=r, depth=body, matrix=m)
    # shoulder (cone, wide end back) and neck
    m = Matrix.Translation((x, y_front + 0.085 + 0.0, z)) @ Matrix.Rotation(-math.pi / 2, 4, "X")
    bmesh.ops.create_cone(bm, cap_ends=False, segments=segs, radius1=r, radius2=0.0125, depth=0.04, matrix=m)
    m = Matrix.Translation((x, y_front + 0.04, z)) @ Matrix.Rotation(-math.pi / 2, 4, "X")
    bmesh.ops.create_cone(bm, cap_ends=False, segments=6, radius1=0.0125, radius2=0.0125, depth=0.05, matrix=m)
    # foil capsule
    m = Matrix.Translation((x, y_front + 0.012, z)) @ Matrix.Rotation(-math.pi / 2, 4, "X")
    bmesh.ops.create_cone(foil, cap_ends=True, cap_tris=False, segments=6, radius1=0.0145, radius2=0.0145,
                          depth=0.04, matrix=m)


# --------------------------------------------------------------------- build

def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    oak = materials.smoked_oak()
    dark = materials.black_metal()
    bronze = materials.bronze()
    glass_g = common.pbr_material("M_Bottle_Green", (0.022, 0.060, 0.028), roughness=0.15)
    glass_k = common.pbr_material("M_Bottle_Black", (0.020, 0.018, 0.022), roughness=0.15)
    backing = common.pbr_material("M_Rack_Backing", (0.010, 0.0075, 0.006), roughness=0.9)

    nb, bw = p["bays"], p["bay_w"]
    W = nb * bw
    D = p["depth"]
    y_back = D / 2          # back plane of the run (against the wall)
    y_front = -D / 2

    # --- plinth, cabinet and worktop
    plinth = common.mesh_object(f"{n}_Plinth", common.box_bmesh((W - 0.06, p["cabinet_depth"] - 0.07, p["plinth_h"])),
                                col, dark, root)
    cd = p["cabinet_depth"]
    plinth.location = (0, y_back - cd / 2 + 0.0, p["plinth_h"] / 2)
    ch = p["cabinet_top"] - p["plinth_h"]
    carcass = common.mesh_object(f"{n}_Cabinet", common.box_bmesh((W - 0.01, cd - 0.03, ch)), col, oak, root)
    carcass.location = (0, y_back - (cd - 0.03) / 2, p["plinth_h"] + ch / 2)
    common.add_bevel(carcass, 0.004, 2)
    common.box_uv(carcass, 0.5)
    wt = common.mesh_object(f"{n}_Worktop", common.box_bmesh((W, cd + 0.02, p["top_t"])), col, oak, root)
    wt.location = (0, y_back - (cd + 0.02) / 2 + 0.0, p["cabinet_top"] + p["top_t"] / 2)
    common.add_bevel(wt, 0.004, 2)
    common.box_uv(wt, 0.5)

    # doors with slim bronze pulls
    door_b, pull_b = bmesh.new(), bmesh.new()
    gap = 0.004
    dw = bw / 2 - gap * 1.5
    dh = ch - 0.03
    for i in range(nb * 2):
        cx = -W / 2 + gap + dw / 2 + i * (dw + gap) + (i // 2) * (bw - 2 * dw - 3 * gap) * 0 + 0.0
        cx = -W / 2 + (i + 0.5) * (W / (nb * 2))
        bmesh.ops.create_cube(door_b, size=1.0, matrix=Matrix.Translation((cx, y_back - cd + 0.006, p["plinth_h"] + 0.01 + dh / 2)) @
                              Matrix.Diagonal((W / (nb * 2) - 0.006, 0.02, dh, 1)))
        px = cx + (0.07 if i % 2 == 0 else -0.07) * 0 + (W / (nb * 2) / 2 - 0.045) * (1 if i % 2 == 0 else -1)
        bmesh.ops.create_cone(pull_b, cap_ends=True, cap_tris=False, segments=6, radius1=0.006, radius2=0.006,
                              depth=0.36, matrix=Matrix.Translation((px, y_back - cd - 0.018, p["plinth_h"] + 0.01 + dh * 0.62)))
    doors = common.mesh_object(f"{n}_Doors", door_b, col, oak, root, smooth=False)
    pulls = common.mesh_object(f"{n}_Pulls", pull_b, col, bronze, root)
    common.box_uv(doors, 0.5)
    common.box_uv(pulls, 0.5)

    # --- racking frame: vertical and horizontal dividers (flat boards, no bevels)
    z0 = p["cabinet_top"] + p["top_t"] + 0.01
    rows, cols = p["rows"], p["cols"]
    cell_h = (p["rack_top"] - z0) / rows
    cell_w = bw / cols
    t = p["divider"]
    rd = D - 0.02            # full depth (bay boundaries and the top/bottom boards)
    sd = 0.19                # shallow dividers between cells (bottles are seen at the front)
    frame = bmesh.new()
    for i in range(nb * cols + 1):
        x = -W / 2 + i * cell_w
        full = (i % cols == 0)
        d_ = rd if full else sd
        bmesh.ops.create_cube(frame, size=1.0, matrix=Matrix.Translation((x, y_back - rd + d_ / 2 if full else y_front + 0.01 + d_ / 2, (z0 + p["rack_top"]) / 2)) @
                              Matrix.Diagonal((t * (2.2 if full else 1.0), d_, p["rack_top"] - z0, 1)))
    for j in range(rows + 1):
        z = z0 + j * cell_h
        edge = j in (0, rows)
        d_ = rd if edge else sd
        bmesh.ops.create_cube(frame, size=1.0, matrix=Matrix.Translation((0, y_back - rd + d_ / 2 if edge else y_front + 0.01 + d_ / 2, z)) @
                              Matrix.Diagonal((W, d_, t * (2.0 if edge else 1.0), 1)))
    fr = common.mesh_object(f"{n}_Frame", frame, col, oak, root, smooth=False)
    common.box_uv(fr, 0.5)
    back = common.mesh_object(f"{n}_Backing", common.box_bmesh((W, 0.012, p["rack_top"] - z0)), col, backing, root)
    back.location = (0, y_back - 0.006, (z0 + p["rack_top"]) / 2)
    common.box_uv(back, 1.0)

    # --- bottles
    bg, bk, foil = bmesh.new(), bmesh.new(), bmesh.new()
    r = p["bottle_r"]
    yf = y_front + 0.03
    for i in range(nb * cols):
        for j in range(rows):
            u = _rand(i, j, p["seed"])
            if u < p["empty"]:
                continue
            x = -W / 2 + (i + 0.5) * cell_w
            z = z0 + (j + 0.5) * cell_h
            target = bg if _rand(i, j, p["seed"] + 5) < 0.62 else bk
            if _rand(i, j, p["seed"] + 9) < p["neck_out"]:
                bottle_neck_out(target, foil, x, yf, z, r)
            else:
                bottle_bottom_out(target, x, yf + 0.05 * _rand(i, j, 2), z, r, p["bottle_len"])
    for bm_, nm, mat in ((bg, "BottlesGreen", glass_g), (bk, "BottlesBlack", glass_k), (foil, "Foil", bronze)):
        ob = common.mesh_object(f"{n}_{nm}", bm_, col, mat, root)
        common.box_uv(ob, 0.5)

    # --- fluted crown up to the ceiling, with a bronze reveal under it
    zc0, zc1 = p["rack_top"] + 0.03, p["height"]
    crown_back = common.mesh_object(f"{n}_Crown", common.box_bmesh((W, 0.05, zc1 - zc0)), col, backing, root)
    crown_back.location = (0, y_back - 0.025, (zc0 + zc1) / 2)
    common.box_uv(crown_back, 1.0)
    rib = bmesh.new()
    pitch = 0.09
    k = int(W / pitch)
    for i in range(k):
        x = -W / 2 + (i + 0.5) * W / k
        bmesh.ops.create_cube(rib, size=1.0, matrix=Matrix.Translation((x, y_back - 0.05 - 0.02, (zc0 + zc1) / 2)) @
                              Matrix.Diagonal((0.048, 0.04, zc1 - zc0 - 0.02, 1)))
    ribs = common.mesh_object(f"{n}_CrownRibs", rib, col, oak, root, smooth=False)
    common.box_uv(ribs, 0.5)
    reveal = common.mesh_object(f"{n}_Reveal", common.box_bmesh((W, 0.06, 0.02)), col, bronze, root)
    reveal.location = (0, y_back - 0.04, p["rack_top"] + 0.015)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
