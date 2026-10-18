"""Motor court fountain: a raised round limestone basin 8 m across with still water just
below its broad coping, and in the middle a limestone plinth carrying a tall twisted bronze
monolith (a rectangular section that tapers and turns 100 degrees as it rises).

Origin: the basin's centre on the ground. z = 0 is the lawn (the paving round it is 5 cm up).
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

NAME = "CourtFountain"

P = dict(
    name=NAME,
    radius=4.0,             # outer radius of the basin wall
    coping_w=0.55,          # flat limestone coping on top of the wall
    wall_h=0.62,            # top of the coping above the lawn
    water_z=0.545,          # still water, 7.5 cm below the coping
    plinth_r=1.5,
    plinth_h=0.95,
    # bronze blades: (x, y, start angle deg, height above the plinth, half section at base,
    # half section at top, twist deg, rings)
    blades=[(0.0, 0.0, 20.0, 6.4, (0.80, 0.25), (0.46, 0.11), 160.0, 16),
            (0.78, -0.42, -40.0, 3.4, (0.50, 0.17), (0.28, 0.08), -120.0, 7),
            (-0.72, 0.52, 70.0, 2.2, (0.42, 0.15), (0.24, 0.07), 110.0, 6)],
    seg=40,
)


def section(hw, hd, ch):
    """Rectangle with chamfered corners, counter-clockwise (8 points)."""
    return [(hw - ch, -hd), (hw, -hd + ch), (hw, hd - ch), (hw - ch, hd),
            (-hw + ch, hd), (-hw, hd - ch), (-hw, -hd + ch), (-hw + ch, -hd)]


def blade(bm, cx, cy, rot, z0, h, base, top, twist, N):
    """Tapering rectangular column that turns `twist` degrees as it rises."""
    rings = []
    for k in range(N + 1):
        t = k / N
        e = t * t * (3 - 2 * t) * 0.35 + t * 0.65
        hw = base[0] + (top[0] - base[0]) * e
        hd = base[1] + (top[1] - base[1]) * e
        ang = math.radians(rot + twist * t)
        ca, sa = math.cos(ang), math.sin(ang)
        ring = []
        for (x, y) in section(hw, hd, min(hw, hd) * 0.5):
            ring.append(bm.verts.new((cx + x * ca - y * sa, cy + x * sa + y * ca, z0 + h * t)))
        rings.append(ring)
    m = len(rings[0])
    for k in range(N):
        a, b = rings[k], rings[k + 1]
        for i in range(m):
            j = (i + 1) % m
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(rings[-1])


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = cc.start(n)
    R, cw, H, wz = p["radius"], p["coping_w"], p["wall_h"], p["water_z"]
    seg = p["seg"]
    c = (0.0, 0.0)

    # ---------------- basin: outer wall, coping, inner wall above the water (limestone)
    bm = bmesh.new()
    cc.wall(bm, c, R, 0.0, H, seg=seg, rows=1)
    cc.polar_patch(bm, c, [R - cw, R], H, seg=seg)
    cc.wall(bm, c, R - cw, wz - 0.03, H, seg=seg, outward=False)
    # plinth
    pr, ph = p["plinth_r"], p["plinth_h"]
    cc.wall(bm, c, pr, wz - 0.03, ph, seg=24)
    fan = [bm.verts.new((pr * math.cos(2 * math.pi * i / 24), pr * math.sin(2 * math.pi * i / 24), ph))
           for i in range(24)]
    bm.faces.new(fan)
    cc.finish(f"{n}_Basin", bm, outdoor.stone(), col, root, uv_tile=2.0)

    # ---------------- water: annulus between the plinth and the inner wall
    bm = bmesh.new()
    inner = R - cw
    steps = 2
    radii = [pr + (inner - pr) * k / steps for k in range(steps + 1)]
    cc.polar_patch(bm, c, radii, wz, seg=seg)
    cc.finish(f"{n}_Water", bm, outdoor.water(), col, root)

    # ---------------- bronze blades: a tall twisted one with two shorter companions
    bm = bmesh.new()
    for (cx, cy, rot, h, base, top, twist, rings) in p["blades"]:
        blade(bm, cx, cy, rot, ph, h, base, top, twist, rings)
    cc.finish(f"{n}_Monolith", bm, outdoor.bronze(), col, root, smooth=True)

    parts = [o for o in root.children]
    return root, parts
