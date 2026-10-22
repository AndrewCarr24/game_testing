"""One span of the old steel Pratt through truss, rehabilitated as the road bridge into town
(freshly repainted green): eight panels, inclined end posts, verticals, diagonals sloping to
the centre, top struts with X bracing, a portal at each end with LED lamps, floor beams and
stringers under a concrete deck with two 3.3 m lanes (asphalt, a double yellow centre line,
white edge lines), curbs, and a cantilevered concrete sidewalk outside the east truss with a
railing. Two spans end to end make the bridge (the layout places them on town_bridge_pier).

Origin: the deck's top surface (z = 0) at the span's centre; the road runs along Y (front
-Y = the approach from the estate); the sidewalk is on +X. below_m = depth of the floor system.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import town_common as tc  # noqa: E402

importlib.reload(tc.tt)
importlib.reload(tc)
V = tc.V

NAME = "TownTrussSpan"
P = dict(name=NAME, module="town_truss_span", length=38.0, panels=8, truss_x=4.0, height=7.6, walk=1.6, bake=False)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, kit = tc.begin(n, p["module"])
    L, NP, TX, Ht = p["length"], p["panels"], p["truss_x"], p["height"]
    y0, y1 = -L / 2, L / 2
    pl = L / NP
    ys = [y0 + i * pl for i in range(NP + 1)]
    G = "trim_green"
    zb = -0.55                      # the bottom chord's centre line
    zt = zb + Ht
    M = kit.p("Truss", G)
    for sx in (-TX, TX):
        # bottom chord, top chord (between the end posts' heads), end posts, verticals, diagonals
        M.beam(V(sx, y0, zb), V(sx, y1, zb), 0.42, 0.5)
        M.beam(V(sx, ys[1], zt), V(sx, ys[-2], zt), 0.5, 0.45)
        M.beam(V(sx, y0, zb), V(sx, ys[1], zt), 0.5, 0.45)
        M.beam(V(sx, y1, zb), V(sx, ys[-2], zt), 0.5, 0.45)
        for i in range(1, NP):
            M.beam(V(sx, ys[i], zb), V(sx, ys[i], zt), 0.32, 0.36)
        for i in range(1, NP // 2):                    # diagonals slope down toward the centre
            M.beam(V(sx, ys[i], zt), V(sx, ys[i + 1], zb), 0.24, 0.3)
            j = NP - i
            M.beam(V(sx, ys[j], zt), V(sx, ys[j - 1], zb), 0.24, 0.3)
        for i in (NP // 2 - 1, NP // 2):              # counters in the middle panels
            M.beam(V(sx, ys[i], zb), V(sx, ys[i + 1], zt), 0.12, 0.16)
        # gusset plates at the panel points
        for i in range(NP + 1):
            for z in ((zb,) if i in (0, NP) else (zb, zt)):
                kit.p("Gussets", G).box((sx - 0.28, ys[i] - 0.5, z - 0.45), (sx + 0.28, ys[i] + 0.5, z + 0.45))
        # rivet-line bands on the chords read at distance as the old steel: a darker swatch strip
        kit.collide((sx - 0.25, y0, -0.1), (sx + 0.25, y1, 1.3))
    # top struts and X bracing; the portals with LED lamps
    T = kit.p("Bracing", G)
    for i in range(1, NP):
        T.beam(V(-TX, ys[i], zt), V(TX, ys[i], zt), 0.25, 0.3)
    for i in range(1, NP - 1):
        T.beam(V(-TX, ys[i], zt + 0.05), V(TX, ys[i + 1], zt + 0.05), 0.08, 0.08)
        T.beam(V(TX, ys[i], zt + 0.08), V(-TX, ys[i + 1], zt + 0.08), 0.08, 0.08)
    for (ya, yb) in ((ys[0], ys[1]), (ys[-1], ys[-2])):
        f = 0.62
        yp = ya + (yb - ya) * f                     # the portal sits on the end posts, 5.6 m up
        zp = zb + Ht * f
        kit.p("Portal", G).beam(V(-TX, yp, zp), V(TX, yp, zp), 0.3, 0.9)
        kit.p("Portal", G).beam(V(-TX, yp, zp - 0.45), V(-TX + 1.4, yp, zp - 1.7), 0.2, 0.2)
        kit.p("Portal", G).beam(V(TX, yp, zp - 0.45), V(TX - 1.4, yp, zp - 1.7), 0.2, 0.2)
        for x in (-1.6, 1.6):
            kit.p("PortalLamps", "trim_black").box((x - 0.25, yp - 0.2, zp - 0.6), (x + 0.25, yp + 0.2, zp - 0.45))
            kit.p("PortalLamps", "glow_white").face([(x - 0.2, yp - 0.15, zp - 0.605), (x + 0.2, yp - 0.15, zp - 0.605),
                                                     (x + 0.2, yp + 0.15, zp - 0.605), (x - 0.2, yp + 0.15, zp - 0.605)],
                                                    toward=(0, 0, -1))
        kit.collide((-TX, yp - 0.15, zp - 0.45), (TX, yp + 0.15, zp + 0.45))
    # floor beams, stringers, the deck
    F = kit.p("Floor", "metal_dark")
    for i in range(NP + 1):
        F.beam(V(-TX, ys[i], -0.62), V(TX + p["walk"], ys[i], -0.62), 0.3, 0.7)
    for x in (-2.6, -0.9, 0.9, 2.6):
        F.beam(V(x, y0, -0.42), V(x, y1, -0.42), 0.25, 0.35)
    D = kit.p("Deck", "concrete")
    D.box((-TX + 0.25, y0, -0.25), (TX - 0.25, y1, -0.05), skip="t")
    kit.p("Road", "asphalt").face([(-3.5, y0, 0.0), (3.5, y0, 0.0), (3.5, y1, 0.0), (-3.5, y1, 0.0)], toward=(0, 0, 1))
    for x in (-0.12, 0.12):
        kit.p("Lines", "paint_yellow").face([(x - 0.05, y0, 0.004), (x + 0.05, y0, 0.004), (x + 0.05, y1, 0.004), (x - 0.05, y1, 0.004)],
                                            toward=(0, 0, 1))
    for x in (-3.3, 3.3):
        kit.p("Lines", "paint_white").face([(x - 0.06, y0, 0.004), (x + 0.06, y0, 0.004), (x + 0.06, y1, 0.004), (x - 0.06, y1, 0.004)],
                                           toward=(0, 0, 1))
    Cb = kit.p("Curbs", "concrete")
    for (a, b) in ((-TX + 0.25, -3.5), (3.5, TX - 0.25)):
        Cb.box((a, y0, -0.05), (b, y1, 0.2), skip="b")
    kit.collide((-TX, y0, -0.7), (TX + p["walk"] + 0.3, y1, 0.0))
    # the cantilevered sidewalk outside the east truss, its railing
    wx0, wx1 = TX + 0.3, TX + 0.3 + p["walk"]
    kit.p("Walkway", "concrete").box((wx0, y0, -0.2), (wx1, y1, 0.12), skip="")
    for y in ys:
        kit.p("Brackets", "metal_dark").beam(V(TX, y, -0.9), V(wx1 - 0.1, y, -0.22), 0.15, 0.2)
    tc.railing(kit, (wx1 - 0.05, y0), (wx1 - 0.05, y1), 0.12, h=1.07, spacing=0.13, mat=G, style="bars")
    kit.p("WalkLights", "glow_white").face([(wx1 - 0.1, y0, 0.125), (wx1 - 0.04, y0, 0.125), (wx1 - 0.04, y1, 0.125),
                                            (wx1 - 0.1, y1, 0.125)], toward=(0, 0, 1))

    far = tc.Far(n)
    for sx in (-TX, TX):
        far.beam(V(sx, y0, zb), V(sx, y1, zb), 0.4, 0.5, G)
        far.beam(V(sx, ys[1], zt), V(sx, ys[-2], zt), 0.5, 0.45, G)
        far.beam(V(sx, y0, zb), V(sx, ys[1], zt), 0.5, 0.45, G)
        far.beam(V(sx, y1, zb), V(sx, ys[-2], zt), 0.5, 0.45, G)
        for i in range(2, NP - 1, 2):
            far.beam(V(sx, ys[i], zb), V(sx, ys[i], zt), 0.32, 0.36, G)
        for i in (1, NP - 1):
            far.beam(V(sx, ys[i], zt), V(sx, ys[i + (1 if i == 1 else -1)], zb), 0.25, 0.3, G)
    far.box((-TX, y0, -0.7), (wx1, y1, 0.0), "stone", top="tar")
    kit.entrance((0.0, y0, 0.0), "-Y", 7.0, kind="road", note="deck top z = 0; the other end at +Y")
    kit.info.update(walk_in=False, deck_top_z=0.0, lanes=2, sidewalk="x 4.3..5.9 at z 0.12",
                    footprint=[round(-TX - 0.3, 3), y0, round(wx1, 3), y1])
    parts = tc.finish(kit, col, root, far)
    return root, parts
