"""Walk-in shower, clad in dark book-matched marble: back and right wall panels, a
raised dark marble tray with a brass drain, a floating stone bench, a stone ledge,
a brass rain head on a wall arm, a thermostatic valve with a dial and a handheld
shower on a slide rail, and glass (a long fixed panel on the left and a
short return at the front, in slim brass channels with a stabiliser bar) leaving a wide
walk-in opening at the front.

Origin: centre of the footprint on the floor. The back wall is at +Y, the right wall
at +X; the open walk-in front faces -Y. For a corner shower in the south-east corner
of a room (back wall = east wall), rotate -90.
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

NAME = "BathShower"

P = dict(
    name=NAME,
    size=(2.2, 1.9),        # footprint width (x), depth (y)
    wall_t=0.05,            # marble cladding thickness
    wall_h=3.8,             # cladding height (room height)
    glass_h=2.45,
    glass_t=0.010,
    front_return=0.62,      # the fixed glass return at the front-left corner
    tray_t=0.014,
    bench=(0.95, 0.42, 0.45),   # x length, depth, seat height
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    dark, brass, stone = bc.marble_dark(), bc.brass(), bc.stone()
    glass = materials.glass("M_Bath_ShowerGlass", tint=(0.8, 0.9, 0.9), alpha=0.24, roughness=0.02)

    W, D = p["size"]
    t, wh = p["wall_t"], p["wall_h"]
    xr, yb = W / 2, D / 2                         # right wall and back wall planes
    xl, yf = -W / 2, -D / 2

    # ---- cladding panels (book-matched pair on the back wall) -----------------
    for sgn, tag in ((-1, "A"), (1, "B")):
        pw = W / 2 - (t if sgn > 0 else 0.0)
        cx = sgn * W / 4 - (t / 2 if sgn > 0 else 0)
        ob = bc.box(col, root, f"{n}_BackPanel_{tag}", (pw, t, wh), (cx, yb - t / 2, wh / 2), dark, bevel=0.0,
                    uv_tile=2.4)
        if sgn > 0:                                # mirror the veins: the book-match
            for d in ob.data.uv_layers["UVMap"].data:
                d.uv = (-d.uv[0], d.uv[1])
    bc.box(col, root, f"{n}_RightPanel", (t, D - t, wh), (xr - t / 2, -t / 2, wh / 2), dark, bevel=0.0, uv_tile=2.4)

    # ---- tray, drain
    tw, td = W - 0.0, D - 0.0
    bc.box(col, root, f"{n}_Tray", (tw - 2 * t + 0.02, td - t, p["tray_t"]), (-0.0 + 0.0, -t / 2 + 0.0, p["tray_t"] / 2),
           dark, bevel=0.0, uv_tile=2.4)
    zt = p["tray_t"]
    bc.box(col, root, f"{n}_Drain", (0.16, 0.16, 0.004), (-0.25, -0.12, zt + 0.0015), brass, bevel=0.0015)
    for k in range(-2, 3):
        bc.box(col, root, f"{n}_DrainSlot_{k}", (0.012, 0.13, 0.0014), (-0.25 + k * 0.028, -0.12, zt + 0.0042),
               materials.black_metal(), bevel=0.0)

    # ---- bench (floating stone slab) + ledge
    bl, bd, bh = p["bench"]
    bx = xr - t - bl / 2
    by = yb - t - bd / 2
    bc.box(col, root, f"{n}_Bench", (bl, bd, 0.07), (bx, by, bh - 0.035), stone, bevel=0.004, uv_tile=1.0)
    bc.box(col, root, f"{n}_BenchBase", (bl - 0.1, bd - 0.1, bh - 0.07 - zt), (bx, by, (bh - 0.07 + zt) / 2),
           stone, bevel=0.002, uv_tile=1.0)
    bc.box(col, root, f"{n}_PipingLedge", (0.92, 0.12, 0.03), (-0.45, yb - t - 0.06, 1.12), stone, bevel=0.003, uv_tile=1.0)
    for sx in (-0.82, -0.08):
        bc.box(col, root, f"{n}_LedgeBracket", (0.02, 0.06, 0.015), (sx, yb - t - 0.03, 1.095), brass, bevel=0.0)

    # ---- fittings: valve, rail with handheld, rain head arm
    yv = yb - t
    vx = -0.45
    plate = bc.lathe([(0.0, 0.0), (0.075, 0.0), (0.075, 0.008), (0.0, 0.008)], 40)
    pl = common.mesh_object(f"{n}_ValvePlate", plate, col, brass, root)
    pl.rotation_euler = (math.radians(90), 0, 0)
    pl.location = (vx, yv - 0.0, 1.30)
    dial = bc.lathe([(0.0, 0.0), (0.030, 0.0), (0.033, 0.004), (0.033, 0.022), (0.0, 0.022)], 32)
    d = common.mesh_object(f"{n}_ValveDial", dial, col, brass, root)
    d.rotation_euler = (math.radians(90), 0, 0)
    d.location = (vx, yv - 0.008, 1.30)
    # slide rail + handheld
    rail = bmesh.new()
    rx = -0.05
    bc.cylinder_between(rail, (rx, yv - 0.025, 0.95), (rx, yv - 0.025, 1.95), 0.011, 12)
    for z in (0.95, 1.95):
        bc.cylinder_between(rail, (rx, yv, z), (rx, yv - 0.025, z), 0.016, 12)
    common.mesh_object(f"{n}_Rail", rail, col, brass, root)
    hh = bmesh.new()
    bc.cylinder_between(hh, (rx, yv - 0.056, 1.32), (rx, yv - 0.056, 1.50), 0.0135, 14)      # handle
    bc.cylinder_between(hh, (rx, yv - 0.056, 1.50), (rx, yv - 0.060, 1.58), 0.021, 16)       # head
    bc.cylinder_between(hh, (rx, yv - 0.040, 1.32), (rx, yv - 0.056, 1.32), 0.016, 12)       # slider
    common.mesh_object(f"{n}_Handheld", hh, col, brass, root)
    # rain head: arm out of the back wall, a flat disc with a rim
    ax = -0.45
    az = 2.42
    arm = bmesh.new()
    bc.cylinder_between(arm, (ax, yv, az), (ax, yv - 0.46, az), 0.014, 12)
    bc.cylinder_between(arm, (ax, yv - 0.46, az), (ax, yv - 0.46, az - 0.05), 0.012, 12)
    common.mesh_object(f"{n}_RainArm", arm, col, brass, root)
    head = bc.lathe([(0.0, 0.0), (0.150, 0.0), (0.154, 0.004), (0.154, 0.012), (0.145, 0.016), (0.0, 0.016)], 56)
    h = common.mesh_object(f"{n}_RainHead", head, col, brass, root)
    h.location = (ax, yv - 0.46, az - 0.066)
    face = bc.lathe([(0.0, -0.0004), (0.139, -0.0004), (0.139, 0.0), (0.0, 0.0)], 56)
    fc = common.mesh_object(f"{n}_RainFace", face, col, materials.black_metal(), root)
    fc.location = (ax, yv - 0.46, az - 0.066)

    # ---- glass: long fixed panel on the left, short return at the front-left
    gh, gt = p["glass_h"], p["glass_t"]
    gx = xl + gt / 2 + 0.002
    gl = D - t
    glass_l = bc.box(col, root, f"{n}_Glass_Side", (gt, gl, gh), (gx, -t / 2 + 0.0, gh / 2 + 0.01), glass, bevel=0.0, smooth=False)
    fr = p["front_return"]
    glass_f = bc.box(col, root, f"{n}_Glass_Front", (fr, gt, gh), (xl + fr / 2, yf + gt / 2 + 0.002, gh / 2 + 0.01), glass,
                     bevel=0.0, smooth=False)
    # brass channels: along the floor under both panels, up the wall edge and up the corner joint
    ch = 0.022
    bc.box(col, root, f"{n}_Channel_Side", (ch, gl, 0.02), (gx, -t / 2, 0.01), brass, bevel=0.002)
    bc.box(col, root, f"{n}_Channel_Front", (fr, ch, 0.02), (xl + fr / 2, yf + gt / 2 + 0.002, 0.01), brass, bevel=0.002)
    bc.box(col, root, f"{n}_Channel_Wall", (ch, 0.02, gh + 0.01), (gx, yb - t - 0.01, (gh + 0.01) / 2), brass, bevel=0.002)
    bc.box(col, root, f"{n}_Channel_Corner", (ch, ch, gh + 0.01), (gx, yf + ch / 2, (gh + 0.01) / 2), brass, bevel=0.002)
    bc.box(col, root, f"{n}_Channel_FrontEnd", (ch, ch, gh + 0.01), (xl + fr - ch / 2, yf + ch / 2, (gh + 0.01) / 2), brass, bevel=0.002)
    # stabiliser bar: from the back wall across the glass top
    bar = bmesh.new()
    bc.cylinder_between(bar, (gx, yb - t, gh - 0.1), (gx, yf + 0.02, gh - 0.1), 0.010, 12)
    common.mesh_object(f"{n}_Stabiliser", bar, col, brass, root)
    bc.merge(root, bc.children(root, "_BackPanel_"), f"{n}_BackPanel")
    bc.merge(root, bc.by_material(root, brass), f"{n}_PipingBrass")
    bc.merge(root, bc.by_material(root, materials.black_metal()), f"{n}_PipingBlack")
    return root, bc.parts_of(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
