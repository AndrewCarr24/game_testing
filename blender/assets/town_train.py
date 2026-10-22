"""The heritage excursion train, parked at the depot: a road-switcher diesel locomotive (green
and cream, a long hood and a short hood either side of the cab, a walkway with handrails,
two trucks) and two streamlined-era coaches (green with a cream window band, vestibule ends,
lit windows), coupled on 1.435 m track; ~1.5k triangles per vehicle.

Origin: the railhead centre at the middle of the set (z = 0 = top of rail); the set runs
along Y (the locomotive at -Y).
"""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import town_common as tc  # noqa: E402

importlib.reload(tc.tt)
importlib.reload(tc)
V = tc.V

NAME = "TownTrain"
P = dict(name=NAME, module="town_train", loco=17.0, coach=20.0, gap=0.9, width=3.1)


def truck(kit, y, w=3.1):
    kit.p("Trucks", "metal_dark").box((-1.25, y - 1.4, 0.35), (1.25, y + 1.4, 0.85))
    for dy in (-0.9, 0.9):
        for sx in (-1, 1):
            a, b = V(sx * 0.72, y + dy, 0.46), V(sx * 0.86, y + dy, 0.46)
            kit.p("Wheels", "metal_dark").tube(a - V(sx * 0.07, 0, 0), b, 0.46, sides=8)


def loco(kit, y0, y1, w):
    hw = w / 2
    G, Cr = "trim_green", "paint_white"
    kit.p("Frame", "metal_dark").box((-hw, y0, 1.1), (hw, y1, 1.45))
    kit.p("Walkway", "metal_galv").box((-hw, y0, 1.45), (hw, y1, 1.5), skip="b")
    cab0, cab1 = y0 + 4.0, y0 + 7.0
    kit.p("ShortHood", G).box((-1.0, y0 + 0.8, 1.5), (1.0, cab0, 3.3), skip="b")
    kit.p("Cab", G).box((-hw + 0.1, cab0, 1.5), (hw - 0.1, cab1, 4.2), skip="b")
    kit.p("Cab", Cr).box((-hw + 0.08, cab0, 2.6), (hw - 0.08, cab1, 2.8), skip="bt")
    for sx in (-1, 1):
        kit.p("CabGlass", "glass_dark").face([(sx * (hw - 0.09), cab0 + 0.4, 2.9), (sx * (hw - 0.09), cab1 - 0.4, 2.9),
                                              (sx * (hw - 0.09), cab1 - 0.4, 3.8), (sx * (hw - 0.09), cab0 + 0.4, 3.8)][:: sx],
                                             toward=(sx, 0, 0))
    for y, d in ((cab0, -1), (cab1, 1)):
        for sx in (-0.55, 0.55):
            kit.p("CabGlass", "glass_dark").face([(sx - 0.4, y + d * 0.005, 2.9), (sx + 0.4, y + d * 0.005, 2.9), (sx + 0.4, y + d * 0.005, 3.8),
                                                  (sx - 0.4, y + d * 0.005, 3.8)], toward=(0, d, 0))
    kit.p("LongHood", G).box((-1.0, cab1, 1.5), (1.0, y1 - 0.8, 3.6), skip="b")
    kit.p("LongHood", Cr).box((-1.01, cab1, 2.4), (1.01, y1 - 0.8, 2.6), skip="bt")
    for k in range(6):
        y = cab1 + 0.8 + k * 1.3
        kit.p("Louvres", "metal_dark").box((-1.02, y, 2.7), (1.02, y + 0.9, 3.3), skip="bt")
    kit.p("Stack", "metal_dark").cyl((0, y1 - 3.0), 0.2, 3.6, 3.9, sides=6)
    kit.p("Headlight", "headlight").face([(-0.2, y0 + 0.795, 2.9), (0.2, y0 + 0.795, 2.9), (0.2, y0 + 0.795, 3.2), (-0.2, y0 + 0.795, 3.2)],
                                         toward=(0, -1, 0))
    for sx in (-1, 1):
        kit.p("Handrails", "paint_yellow").tube(V(sx * (hw - 0.05), y0 + 0.3, 2.4), V(sx * (hw - 0.05), y1 - 0.3, 2.4), 0.025, 4)
        for y in (y0 + 0.3, y0 + 3.0, cab1 + 3.0, y1 - 0.3):
            kit.p("Handrails", "paint_yellow").tube(V(sx * (hw - 0.05), y, 1.5), V(sx * (hw - 0.05), y, 2.4), 0.02, 4)
    for y in (y0 + 0.3, y1 - 0.3):
        kit.p("Pilots", "paint_yellow").box((-hw, y - 0.2, 0.6), (hw, y + 0.2, 1.1))
    kit.p("Tank", "metal_dark").box((-1.2, y0 + 6.0, 0.6), (1.2, y0 + 10.5, 1.1))
    truck(kit, y0 + 3.0, w)
    truck(kit, y1 - 3.0, w)
    kit.collide((-hw, y0, 0.0), (hw, y1, 4.2))


def coach(kit, y0, y1, w, lit=True):
    hw = w / 2
    kit.p("Body", "trim_green").box((-hw, y0 + 0.4, 1.1), (hw, y1 - 0.4, 3.9), skip="t")
    kit.p("Band", "paint_white").box((-hw - 0.005, y0 + 0.4, 2.1), (hw + 0.005, y1 - 0.4, 3.0), skip="bt")
    R = kit.p("Roof", "metal_galv")
    prof = [(-hw, 3.9), (-hw + 0.4, 4.2), (-0.6, 4.38), (0.6, 4.38), (hw - 0.4, 4.2), (hw, 3.9)]
    for (xa, za), (xb, zb) in zip(prof, prof[1:]):
        R.face([(xa, y0 + 0.4, za), (xb, y0 + 0.4, zb), (xb, y1 - 0.4, zb), (xa, y1 - 0.4, za)], toward=(xa + xb, 0, 1))
    for y, d in ((y0 + 0.4, -1), (y1 - 0.4, 1)):
        R.face([(x, y, z) for x, z in prof][:: (1 if d < 0 else -1)] + [], toward=(0, d, 0)) if False else None
        kit.p("Ends", "trim_green").face([(-hw, y, 3.9)] + [(x, y, z) for x, z in prof[1:-1]] + [(hw, y, 3.9)], toward=(0, d, 0))
        kit.p("Vestibule", "rubber").box((-0.9, y - 0.25 if d < 0 else y, 1.2), (0.9, y if d < 0 else y + 0.25, 3.8))
    n = 10
    for sx in (-1, 1):
        for k in range(n):
            ya = y0 + 2.0 + k * (y1 - y0 - 4.0) / n
            q = [(sx * (hw + 0.008), ya + 0.15, 2.2), (sx * (hw + 0.008), ya + 1.35, 2.2), (sx * (hw + 0.008), ya + 1.35, 2.9),
                 (sx * (hw + 0.008), ya + 0.15, 2.9)]
            kit.p("Windows", "windows").face(q if sx > 0 else q[::-1], uvs=tc.cell_uv(tc.WIN["bk_cafe" if lit else "bk_dark"],
                                                                                         sub=(0.06, 0.4, 0.94, 0.94)), toward=(sx, 0, 0))
        for y in (y0 + 0.9, y1 - 0.9):
            kit.p("Doors", "trim_green").face([(sx * (hw + 0.006), y - 0.45, 1.2), (sx * (hw + 0.006), y + 0.45, 1.2),
                                               (sx * (hw + 0.006), y + 0.45, 3.5), (sx * (hw + 0.006), y - 0.45, 3.5)][:: sx],
                                              toward=(sx, 0, 0))
    kit.p("Underframe", "metal_dark").box((-1.3, y0 + 3.0, 0.7), (1.3, y1 - 3.0, 1.1))
    truck(kit, y0 + 2.6, w)
    truck(kit, y1 - 2.6, w)
    kit.collide((-hw, y0 + 0.4, 0.0), (hw, y1 - 0.4, 4.38))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, kit = tc.begin(n, p["module"])
    Ll, Lc, gap, w = p["loco"], p["coach"], p["gap"], p["width"]
    total = Ll + 2 * Lc + 2 * gap
    y = -total / 2
    loco(kit, y, y + Ll, w)
    y += Ll + gap
    coach(kit, y, y + Lc, w)
    y += Lc + gap
    coach(kit, y, y + Lc, w)
    for k in range(2):                                     # the couplers
        yc = -total / 2 + Ll + gap / 2 + k * (Lc + gap)
        kit.p("Couplers", "metal_dark").box((-0.15, yc - gap / 2 - 0.2, 0.8), (0.15, yc + gap / 2 + 0.2, 1.05))
    far = tc.Far(n)
    y = -total / 2
    far.box((-w / 2, y, 0.9), (w / 2, y + Ll, 3.6), "trim_green", top="trim_green", skip="b")
    for k in range(2):
        ya = -total / 2 + Ll + gap + k * (Lc + gap)
        far.box((-w / 2, ya + 0.4, 0.9), (w / 2, ya + Lc - 0.4, 4.3), "trim_green", top="metal_galv", skip="b")
    kit.info.update(walk_in=False, length_m=round(total, 2), footprint=[-w / 2, round(-total / 2, 3), w / 2, round(total / 2, 3)],
                    rail="z = 0 at the top of rail, gauge 1.435")
    parts = tc.finish(kit, col, root, far)
    return root, parts
