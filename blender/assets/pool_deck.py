"""Raised limestone pool deck with a 25 x 6 m lap pool. Origin: the zone's centre at lawn
level (z = 0 is the lawn), so it is placed at (0, 0) with no rotation. +x east, +y north
(toward the infinity edge), the house is to the south (-y).

The lawn can't be cut, so the pool is built up: the deck top sits 0.45 m above the lawn,
the pale coping rim is 2 cm above it and the opaque water plane 6 cm below the coping.
North long side: an infinity edge. The water runs to a knife-edge lip, drops down a dark
weir face into a catch trough a step lower, and an outer trough wall (below the water
level, so the vanishing edge reads from the house) retains the lawn. West end: a sun
shelf (a bright, shallow turquoise plane; the in-water loungers stand on it).
Broad steps on the south side (centred) and at the east end; the west end is a flank.
Everything big is cut into cells of 1 m or less for the vertex-baked lighting."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pool_common as pc  # noqa: E402

importlib.reload(pc)
common = pc.common
lunge = pc.lunge

NAME = "PoolDeck"

P = dict(
    name=NAME,
    deck=(-15.0, -10.0, 14.6, None),     # x0, y0, x1, (y1 follows the trough)
    h=0.45,                              # deck above the lawn
    pool=(-13.5, -3.6, 11.5, 2.4),       # water: x0, y0, x1, y1 (north = infinity edge)
    cope_w=0.40,
    cope_top=0.47,
    water_z=0.41,
    lip_w=0.07,
    trough_w=0.40,
    trough_wall_w=0.40,
    trough_water_z=0.19,
    trough_wall_h=0.28,
    shelf_len=3.4,
    shelf_floor=0.31,
    south_steps=(-4.5, 4.5),             # x range of the broad south steps
    east_steps=(-8.5, -3.5),             # y range of the east steps
    step_rise=0.15,
    step_go=0.5,
    cell=1.0,
)


def build(**overrides):
    p = {**P, **overrides}
    b = pc.Builder(p["name"])
    stone, cope, weir, water, shelf = pc.stone(), pc.coping(), pc.weir(), pc.outdoor.water(), pc.shelf_water()
    cell, H = p["cell"], p["h"]
    px0, py0, px1, py1 = p["pool"]
    cw, ct = p["cope_w"], p["cope_top"]
    wz = p["water_z"]
    lip_w, tw, tww = p["lip_w"], p["trough_w"], p["trough_wall_w"]
    x0, y0, x1, _ = p["deck"]
    y1 = py1 + lip_w + tw + tww                       # north edge of the deck / trough wall
    twz, twh = p["trough_water_z"], p["trough_wall_h"]
    ex0, ex1 = px0 - cw, px1 + cw                     # outer extent of the coping
    sy = py0 - cw                                     # south edge of the coping
    s0, s1 = p["south_steps"]
    e0, e1 = p["east_steps"]
    rise, go = p["step_rise"], p["step_go"]

    # ---- paving: three rectangles around the pool block (south band, west and east strips)
    b.hquad(stone, x0, y0, x1, sy, H, step=cell, tile=2.0)
    b.hquad(stone, x0, sy, ex0, y1, H, step=cell, tile=2.0)
    b.hquad(stone, ex1, sy, x1, y1, H, step=cell, tile=2.0)

    # ---- the deck's outer edge faces (steps lower the first 0.30 m where they run)
    low = H - rise
    # south edge (faces -y)
    b.vwall(stone, (x0, y0), (s0, y0), 0, H, (0, -1), cell, 2.0)
    b.vwall(stone, (s1, y0), (x1, y0), 0, H, (0, -1), cell, 2.0)
    b.vwall(stone, (s0, y0), (s1, y0), low, H, (0, -1), cell, 2.0)
    # west edge (faces -x), full height
    b.vwall(stone, (x0, y1), (x0, y0), 0, H, (-1, 0), cell, 2.0)
    # east edge (faces +x)
    b.vwall(stone, (x1, y0), (x1, e0), 0, H, (1, 0), cell, 2.0)
    b.vwall(stone, (x1, e1), (x1, y1), 0, H, (1, 0), cell, 2.0)
    b.vwall(stone, (x1, e0), (x1, e1), low, H, (1, 0), cell, 2.0)
    # north edge strips beside the pool block (faces +y)
    b.vwall(stone, (x0, y1), (ex0, y1), 0, H, (0, 1), cell, 2.0)
    b.vwall(stone, (ex1, y1), (x1, y1), 0, H, (0, 1), cell, 2.0)

    # ---- steps: two treads of `rise`, each `go` deep, on the south side and the east end
    for k in range(2):
        top = H - rise * (k + 1)
        d0, d1 = go * k, go * (k + 1)
        b.box(stone, (s0, y0 - d1, 0), (s1, y0 - d0, top), tile=2.0, step=cell, skip=("-z", "+y"))
        b.box(stone, (x1 + d0, e0, 0), (x1 + d1, e1, top), tile=2.0, step=cell, skip=("-z", "-x"))

    # ---- low LED step lights in the upper south riser (they glow in the bake)
    lamp = pc.outdoor.lamp("Warm")
    nl = 5
    for k in range(nl):
        lx = lunge(s0 + 0.9, s1 - 0.9, k / (nl - 1))
        b.box(lamp, (lx - 0.11, y0 - 0.012, H - 0.09), (lx + 0.11, y0, H - 0.06), skip=("-z", "+y"))

    # ---- coping ring (flat pale limestone, 2 cm proud of the paving)
    b.box(cope, (ex0, sy, 0.36), (ex1, py0, ct), step=cell, skip=("-z",))
    for sx, lo_x, hi_x, hid in (("w", ex0, px0, "+x"), ("e", px1, ex1, "-x")):
        # block from the south coping to the trough end; its inner face is the pool wall
        # and, past the lip, the end of the trough
        b.box(cope, (lo_x, py0, 0), (hi_x, y1, ct), step=cell, skip=("-z", "-y"))

    # ---- water
    sl = p["shelf_len"]
    sx = px0 + sl
    b.hquad(shelf, px0, py0, sx - 0.04, py1, wz - 0.01, step=None)
    b.hquad(water, sx + 0.04, py0, px1, py1, wz, step=None)
    # nosing between the shelf and the deep water
    b.box(cope, (sx - 0.04, py0, wz - 0.02), (sx + 0.04, py1, wz + 0.012), step=cell, skip=("-z", "-x", "+x", "-y", "+y"))
    # shelf edge faces of the nosing (the 2 cm step into the deep water)
    b.vwall(cope, (sx + 0.04, py0), (sx + 0.04, py1), wz - 0.02, wz + 0.012, (1, 0), cell)

    # ---- infinity edge: knife-edge lip, weir face, catch trough, outer wall
    ly = py1 + lip_w
    b.hquad(cope, px0, py1, px1, ly, wz + 0.005, step=cell)                     # lip top
    b.vwall(weir, (px0, ly), (px1, ly), twz, wz + 0.005, (0, 1), cell)          # weir face
    b.hquad(water, px0, ly, px1, ly + tw, twz, step=None)                       # trough water
    wy0 = ly + tw
    b.box(stone, (px0, wy0, 0), (px1, y1, twh), tile=2.0, step=cell, skip=("-z", "-x", "+x"))
    # inner (south) face of the outer wall only shows above the trough water
    # (box above emitted it from z=0; it is hidden below twz)

    parts = [o for o in b.finish()[1]]
    return b.root, parts


if __name__ == "__main__":
    root, parts = build()
    pc.report(root, parts)
