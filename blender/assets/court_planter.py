"""Large limestone planter for a multi-stem tree (or low planting): a pale limestone box on a
dark-metal recessed plinth with a broad rim and dark soil 7 cm below it. The soil surface is
`soil_top` above the ground: place the tree at that z.

Origin: floor centre. Units are metres.
"""
import importlib
import os
import sys

import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import court_common as cc  # noqa: E402

importlib.reload(cc)
common, outdoor = cc.common, cc.outdoor

NAME = "CourtPlanter"

P = dict(
    name=NAME,
    width=3.0,
    depth=3.0,
    height=0.95,
    plinth_h=0.08,
    plinth_inset=0.06,
    rim=0.14,
    soil_drop=0.07,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = cc.start(n)
    W, D, H, ph, pi, r = p["width"], p["depth"], p["height"], p["plinth_h"], p["plinth_inset"], p["rim"]
    sz = H - p["soil_drop"]
    hx, hy = W / 2, D / 2

    bm = bmesh.new()
    cc.box(bm, (-hx, -hy, ph), (hx, hy, H), bottom=True, top=False)
    # rim (four strips) and the inner walls down to the soil
    big = 6.0           # one quad per rim strip (they are only ~14 cm wide)
    cc.panel(bm, (-hx, -hy, H), (W, 0, 0), (0, r, 0), big)
    cc.panel(bm, (-hx, hy - r, H), (W, 0, 0), (0, r, 0), big)
    cc.panel(bm, (-hx, -hy + r, H), (r, 0, 0), (0, D - 2 * r, 0), big)
    cc.panel(bm, (hx - r, -hy + r, H), (r, 0, 0), (0, D - 2 * r, 0), big)
    ix, iy, dz = hx - r, hy - r, H - sz
    cc.panel(bm, (-ix, iy, sz), (0, 0, dz), (2 * ix, 0, 0), 6.0)
    cc.panel(bm, (-ix, -iy, sz), (2 * ix, 0, 0), (0, 0, dz), 6.0)       # south wall, inside (faces +y)
    cc.panel(bm, (-ix, -iy, sz), (0, 0, dz), (0, 2 * iy, 0), 6.0)       # west wall, inside (faces +x)
    cc.panel(bm, (ix, -iy, sz), (0, 2 * iy, 0), (0, 0, dz), 6.0)        # east wall, inside (faces -x)
    cc.finish(f"{n}_Body", bm, outdoor.stone(), col, root, uv_tile=2.0)

    bm = bmesh.new()
    cc.panel(bm, (-ix, -iy, sz), (2 * ix, 0, 0), (0, 2 * iy, 0), cell=4.0)
    cc.finish(f"{n}_Soil", bm, cc.outdoor.flat("M_Out_SoilDark", cc.SOIL_DARK), col, root)

    bm = bmesh.new()
    cc.box(bm, (-hx + pi, -hy + pi, 0), (hx - pi, hy - pi, ph + 0.01), cell=4.0, top=False)
    cc.finish(f"{n}_Plinth", bm, outdoor.dark_metal(), col, root)

    root["soil_top"] = sz
    parts = [o for o in root.children]
    return root, parts
