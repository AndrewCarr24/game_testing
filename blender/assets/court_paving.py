"""Motor court paving: a pale gravel field framed by limestone banding. Everything is in
zone-local metres with the court's centre at the origin, so the asset is placed at (0, 0).

  field          x -21..21, y -10.5..10.5 (north edge = the house terrace edge, y -25 in the world)
  border         1.0 m limestone band round the west, east and south sides, with the 8 m drive
                 mouth in the south band (centre x 11.75 = the garage door's centre line)
  entry path     6 m wide, from the terrace to the fountain plaza, ends in the plaza's arc
  plaza          limestone annulus round the fountain basin (fountain centre at `fx`, 0)
  outer ring     a 0.6 m limestone ring concentric with the fountain, tangent to the south band,
                 broken where the entry path crosses it
  north band     1.0 m limestone along the terrace edge (the ring is tangent to it and the south band)
  garage apron   limestone in front of the garage door, with a dark linear drain at its edge
  lane edging    0.5 m limestone strips along both sides of the drive lane to the apron
Gravel (z 0.04) is 2 cm below the stone (z 0.06) so the banding reads as set slabs in a gravel
bed. Gravel cells hidden under stone are left out. Grids of <= 1.5 m cells for baked lighting.
"""
import importlib
import math
import os
import sys

import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import court_common as cc  # noqa: E402

importlib.reload(cc)
common, outdoor = cc.common, cc.outdoor

NAME = "CourtPaving"

P = dict(
    name=NAME,
    half_w=21.0,            # field half width (x)
    half_d=10.5,            # field half depth (y)
    border=1.0,
    fx=-8.0, fy=0.0,        # fountain centre (zone-local)
    plaza_r=6.3,
    basin_r=4.0,
    ring_r=(8.9, 9.5),
    path_half=3.0,
    drive=(7.75, 15.75),    # mouth in the south band
    apron=(7.0, 16.5),      # x range of the garage apron
    apron_depth=5.0,
    edging=0.5,
    z_gravel=0.04,
    z_stone=0.06,   # level with the house terrace (6 cm above the lawn)
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = cc.start(n)
    W, D, B = p["half_w"], p["half_d"], p["border"]
    fx, fy = p["fx"], p["fy"]
    zs, zg = p["z_stone"], p["z_gravel"]
    d0, d1 = p["drive"]
    a0, a1 = p["apron"]
    ay = D - p["apron_depth"]
    E = p["edging"]
    pr, ph = p["plaza_r"], p["path_half"]

    # ---------------- limestone
    bm = bmesh.new()
    # borders: west, east (full depth), south (two pieces round the drive mouth)
    cc.box(bm, (-W, -D, 0), (-W + B, D, zs), sides="wes")
    cc.box(bm, (W - B, -D, 0), (W, D, zs), sides="wes")
    cc.box(bm, (-W + B, -D, 0), (d0, -D + B, zs), sides="sne")
    cc.box(bm, (d1, -D, 0), (W - B, -D + B, zs), sides="snw")
    # north band along the terrace edge (the entry path and the apron run through it)
    cc.box(bm, (-W + B, D - B, 0), (fx - ph, D, zs), sides="s")
    cc.box(bm, (fx + ph, D - B, 0), (a0, D, zs), sides="s")
    cc.box(bm, (a1, D - B, 0), (W - B, D, zs), sides="s")
    # drive lane edging, from the south band to the apron
    cc.box(bm, (d0, -D + B, 0), (d0 + E, ay, zs), sides="we")
    cc.box(bm, (d1 - E, -D + B, 0), (d1, ay, zs), sides="we")
    # garage apron
    cc.box(bm, (a0, ay, 0), (a1, D, zs), sides="sew")
    # plaza round the fountain
    cc.polar_patch(bm, (fx, fy), [p["basin_r"] - 0.1, (p["basin_r"] + pr) / 2, pr], zs, seg=40)
    # outer ring, broken where the path crosses it (vertical cut at the path's edges)
    r0, r1 = p["ring_r"]

    def span(r):
        d = math.asin(min(1.0, ph / r))
        return (math.pi / 2 + d, math.pi / 2 + 2 * math.pi - d)

    cc.polar_patch(bm, (fx, fy), [r0, r1], zs, seg=56, theta=span)
    # entry path: columns at x, the lower end follows the plaza's circle
    cols = max(2, round(2 * ph / 1.5))
    top = D
    ylow = lambda x: fy + math.sqrt(pr * pr - (x - fx) ** 2)
    rows = math.ceil((top - ylow(fx - ph)) / 1.5 - 1e-6)
    grid = []
    for i in range(cols + 1):
        x = fx - ph + 2 * ph * i / cols
        y0 = ylow(x)
        grid.append([bm.verts.new((x, y0 + (top - y0) * j / rows, zs)) for j in range(rows + 1)])
    for i in range(cols):
        for j in range(rows):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    cc.finish(f"{n}_Limestone", bm, outdoor.stone(), col, root, uv_tile=2.0)

    # ---------------- gravel field: grid, minus cells wholly under stone
    def covered(x, y):
        if math.hypot(x - fx, y - fy) < pr + 0.02:
            return True
        if abs(x - fx) < ph and y > fy:
            return True
        if a0 <= x <= a1 and y >= ay:
            return True
        if y >= D - B:
            return True
        return False

    nx = round(2 * (W - B) / 1.5)
    ny = round((D - B - (-D + B)) / 1.5)
    xs = [-W + B + 2 * (W - B) * i / nx for i in range(nx + 1)]
    ys = [-D + B + (D - B - (-D + B)) * j / ny for j in range(ny + 1)]
    # the drive mouth (south band opening) is gravel too
    ys_mouth = [-D, -D + B]
    nm = max(1, round((d1 - d0) / 1.5))
    xs_mouth = [d0 + (d1 - d0) * i / nm for i in range(nm + 1)]
    bm = bmesh.new()
    vid = {}

    def vert(x, y):
        key = (round(x, 4), round(y, 4))
        if key not in vid:
            vid[key] = bm.verts.new((x, y, zg))
        return vid[key]

    def cell(xa, xb, ya, yb):
        pts = [(xa, ya), (xb, ya), (xb, yb), (xa, yb), ((xa + xb) / 2, (ya + yb) / 2)]
        if all(covered(*q) for q in pts):
            return
        bm.faces.new((vert(xa, ya), vert(xb, ya), vert(xb, yb), vert(xa, yb)))

    for i in range(nx):
        for j in range(ny):
            cell(xs[i], xs[i + 1], ys[j], ys[j + 1])
    for i in range(nm):
        cell(xs_mouth[i], xs_mouth[i + 1], ys_mouth[0], ys_mouth[1])
    cc.finish(f"{n}_Gravel", bm, outdoor.gravel(), col, root, uv_tile=2.0)

    # ---------------- drains (dark metal slots)
    bm = bmesh.new()
    cc.box(bm, (a0, ay - 0.2, zs), (a1, ay, 0.068), cell=1.2, sides="")
    cc.finish(f"{n}_Drain", bm, outdoor.dark_metal(), col, root)

    parts = [o for o in root.children]
    return root, parts
