"""Gatehouse just inside the gate: a small white-render pavilion, flat roof on a thin
cantilevered slab with a dark steel coping, a glazed front (fixed lights either side of a
centred door) and a ribbon window in its left side, on a low limestone plinth with a stoop.
A desk, a stool and a ceiling light inside. Units are metres.
The front (glazing, stoop) faces -Y. Origin: the centre of the plan on the ground.
"""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gate_common as gc  # noqa: E402

importlib.reload(gc)
common, outdoor = gc.common, gc.outdoor

NAME = "GateHouse"

P = dict(
    name=NAME,
    width=3.6,          # x (the glazed front)
    depth=3.4,          # y
    wall=0.22,
    plinth_h=0.14,
    plinth_over=0.10,
    stoop=0.70,
    wall_top=2.72,
    slab_h=0.18,
    front_over=0.50,    # roof cantilever over the stoop
    over=0.15,
    coping=(0.08, 0.06),
)


def up_rect(bm, x0, y0, x1, y1, z, step=gc.STEP):
    gc.grid_face(bm, gc.V(x0, y0, z), gc.V(1, 0, 0), gc.V(0, 1, 0), x1 - x0, y1 - y0, step)


def down_rect(bm, x0, y0, x1, y1, z, step=gc.STEP):
    gc.grid_face(bm, gc.V(x0, y1, z), gc.V(1, 0, 0), gc.V(0, -1, 0), x1 - x0, y1 - y0, step)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    parts = gc.Parts(n, col, root)
    V, X, Y, Z = gc.V, gc.V(1, 0, 0), gc.V(0, 1, 0), gc.V(0, 0, 1)
    white = parts.bm("Walls", outdoor.render_white())
    stone = parts.bm("Stone", outdoor.stone(), 2.0)
    metal = parts.bm("Metal", outdoor.dark_metal())
    bronze = parts.bm("Bronze", outdoor.bronze())
    roofm = parts.bm("Roof", outdoor.flat("M_Out_Roof_Membrane", (0.20, 0.20, 0.205)))
    glass = parts.bm("Glass", outdoor.glass())
    lamp = parts.bm("Lamp", outdoor.lamp())
    wood = parts.bm("Desk", outdoor.teak(), 0.5)

    W, D, t = p["width"], p["depth"], p["wall"]
    hx, hy = W / 2, D / 2
    zb, zt, ph = p["plinth_h"], p["wall_top"], p["plinth_h"]
    Hw = zt - zb
    po, st = p["plinth_over"], p["stoop"]

    # plinth: sides, and its top only outside the walls (stoop, margins) and inside (floor)
    gc.box(stone, V(-hx - po, -hy - st, 0), V(hx + po, hy + po, ph), sides="nsew", top=False)
    up_rect(stone, -hx - po, -hy - st, hx + po, -hy, ph)                      # stoop
    up_rect(stone, -hx - po, -hy, -hx, hy + po, ph)                           # west margin
    up_rect(stone, hx, -hy, hx + po, hy + po, ph)                             # east margin
    up_rect(stone, -hx, hy, hx, hy + po, ph)                                  # back margin
    up_rect(stone, -hx + t, -hy + t, hx - t, hy - t, ph)                      # floor

    # --- walls: (origin, u, outward normal, length, openings in outer coords)
    door_w = 1.0
    front_open = [(W / 2 - 1.5, W / 2 + 1.5, 0.0, 2.32)]                      # u from x = -1.5 .. 1.5
    side_open = [(0.65, 2.65, 0.95, 2.10)]
    walls = [
        ("front", V(-hx, -hy, zb), X, -Y, W, front_open),
        ("west", V(-hx, hy, zb), -Y, -X, D, side_open),
        ("east", V(hx, -hy, zb), Y, X, D, []),
        ("back", V(hx, hy, zb), -X, Y, W, []),
    ]
    for name, o, u, nrm, L, ops in walls:
        wall_face_args = (white, o, u, Z, nrm, L, Hw, ops)
        gc.wall_face(*wall_face_args)
        # inner face: reversed direction, inset by the wall thickness
        io = o + u * (L - t) - nrm * t
        iops = [(L - t - a1, L - t - a0, b0, b1) for a0, a1, b0, b1 in ops]
        gc.wall_face(white, io, -u, Z, -nrm, L - 2 * t, Hw, iops)
        gc.reveals(white, o, u, Z, nrm, t, ops)

    # --- glazing, frames (front)
    fx0, fx1, fz1 = -1.5, 1.5, zb + 2.32
    mid = -t / 2                                                  # glass plane, mid reveal
    fy = -hy + t / 2
    fb = 0.055                                                    # frame bar section
    def bar(x0, x1, z0, z1, dy=0.04, mat=metal):
        gc.box(mat, V(x0, fy - dy, z0), V(x1, fy + dy, z1), step=4.0, top=True, bottom=True)
    bar(fx0, fx1, zb, zb + 0.06)                                  # sill
    bar(fx0, fx1, fz1 - 0.06, fz1)                                # head
    bar(fx0, fx0 + fb, zb, fz1)                                   # jambs
    bar(fx1 - fb, fx1, zb, fz1)
    for xm in (-door_w / 2, door_w / 2):                          # door stiles
        bar(xm - fb / 2, xm + fb / 2, zb, fz1)
    bar(fx0, fx1, zb + 2.08, zb + 2.08 + 0.05)                    # transom
    for (xa, xb) in ((fx0 + fb, -door_w / 2 - fb / 2), (-door_w / 2 + fb / 2, door_w / 2 - fb / 2),
                     (door_w / 2 + fb / 2, fx1 - fb)):
        for fz in ((zb + 0.06, zb + 2.08), (zb + 2.13, fz1 - 0.06)):
            for d, nz in ((0.0, -1), (0.0, 1)):
                pts = [V(xa, fy, fz[0]), V(xb, fy, fz[0]), V(xb, fy, fz[1]), V(xa, fy, fz[1])]
                gc.quad(glass, *(pts if nz < 0 else pts[::-1]))
    # door pull (bronze) and a kick plate
    gc.box(bronze, V(door_w / 2 - 0.12, -hy - 0.01, zb + 0.9), V(door_w / 2 - 0.09, fy, zb + 1.5),
           step=4.0, top=True, bottom=True)
    # ribbon window in the west wall: frame + glass
    a0, a1, b0, b1 = side_open[0]
    wy0, wy1 = hy - a1, hy - a0                                   # u runs along -y from +hy
    wz0, wz1 = zb + b0, zb + b1
    wx = -hx + t / 2
    def wbar(y0, y1, z0, z1):
        gc.box(metal, V(wx - 0.04, y0, z0), V(wx + 0.04, y1, z1), step=4.0, top=True, bottom=True)
    wbar(wy0, wy1, wz0, wz0 + 0.05)
    wbar(wy0, wy1, wz1 - 0.05, wz1)
    wbar(wy0, wy0 + 0.05, wz0, wz1)
    wbar(wy1 - 0.05, wy1, wz0, wz1)
    wbar((wy0 + wy1) / 2 - 0.025, (wy0 + wy1) / 2 + 0.025, wz0, wz1)
    for (ya, yb) in ((wy0 + 0.05, (wy0 + wy1) / 2 - 0.025), ((wy0 + wy1) / 2 + 0.025, wy1 - 0.05)):
        pts = [V(wx, ya, wz0 + 0.05), V(wx, yb, wz0 + 0.05), V(wx, yb, wz1 - 0.05), V(wx, ya, wz1 - 0.05)]
        gc.quad(glass, *pts)
        gc.quad(glass, *pts[::-1])

    # --- roof: cantilevered slab, soffit strips, coping, membrane
    o = p["over"]
    fo = p["front_over"]
    sx0, sx1, sy0, sy1 = -hx - o, hx + o, -hy - fo, hy + o
    z0s, z1s = zt, zt + p["slab_h"]
    gc.box(white, V(sx0, sy0, z0s), V(sx1, sy1, z1s), sides="nsew", top=False, bottom=False)
    down_rect(white, sx0, sy0, sx1, -hy, z0s)                      # front soffit
    down_rect(white, sx0, -hy, -hx, sy1, z0s)
    down_rect(white, hx, -hy, sx1, sy1, z0s)
    down_rect(white, -hx, hy, hx, sy1, z0s)
    down_rect(white, -hx + t, -hy + t, hx - t, hy - t, z0s)        # interior ceiling
    cw, ch = p["coping"]
    cz = z1s
    for (x0, y0, x1, y1) in ((sx0, sy0, sx1, sy0 + cw), (sx0, sy1 - cw, sx1, sy1),
                             (sx0, sy0 + cw, sx0 + cw, sy1 - cw), (sx1 - cw, sy0 + cw, sx1, sy1 - cw)):
        gc.box(metal, V(x0, y0, cz), V(x1, y1, cz + ch), step=4.0, top=True, bottom=False)
    up_rect(roofm, sx0 + cw, sy0 + cw, sx1 - cw, sy1 - cw, cz + 0.004)
    # soffit downlights over the stoop
    for lx in (-0.9, 0.9):
        gc.box(lamp, V(lx - 0.09, -hy - 0.28, z0s - 0.012), V(lx + 0.09, -hy - 0.10, z0s), step=4.0,
               top=False, bottom=True, sides="")
    # inside: ceiling light, desk, stool
    gc.box(lamp, V(-0.6, -0.25, z0s - 0.012), V(0.6, 0.25, z0s), step=4.0, top=False, bottom=True, sides="")
    dx0, dx1, dy0, dy1 = -1.1, 1.1, hy - t - 0.62, hy - t - 0.02
    gc.box(metal, V(dx0, dy0, zb), V(dx1, dy1, zb + 0.74), step=4.0, top=False)
    gc.box(wood, V(dx0 - 0.04, dy0 - 0.06, zb + 0.74), V(dx1 + 0.04, dy1, zb + 0.78), step=4.0, top=True, bottom=False)
    gc.cylinder(metal, (0.0, 0.25), 0.19, zb, zb + 0.62, sides=10)
    return root, parts.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
