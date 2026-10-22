"""Walkable structures of the town kit (not assets: exported by thin modules):

  footbridge     the modern steel greenway footbridge (the river walk to Mill Hill): a 64 m
                 weathering-steel Warren pony truss each side of a 2.5 m deck of boards, a
                 stainless handrail, LED strips under the rail; two intermediate supports
                 (origin: the deck's top at mid-span, z = 0; it runs along Y)
  tunnel_portal  the heritage line's tunnel portal: a cut-stone face with a semicircular arch
                 and voussoirs, a keystone, a blank date stone, a coping, wing walls into the
                 hill, 20 m of lined bore going dark, the track bed with ties and rails
                 (origin: the track bed's centre at the face; the bore runs +Y into the hill)
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


def footbridge(kit):
    L, W, H = 64.0, 2.5, 1.35
    y0, y1 = -L / 2, L / 2
    kit.p("Deck", "deck").box((-W / 2, y0, -0.12), (W / 2, y1, 0.0))
    kit.collide((-W / 2 - 0.2, y0, -0.12), (W / 2 + 0.2, y1, 0.0))
    G = kit.p("Truss", "mean:brick_red") if False else kit.p("Truss", "trim_brown")
    n = 32
    for sx in (-1, 1):
        x = sx * (W / 2 + 0.1)
        G.beam(V(x, y0, -0.35), V(x, y1, -0.35), 0.18, 0.5)
        G.beam(V(x, y0, H), V(x, y1, H), 0.16, 0.16)
        for i in range(n):
            ya, yb = y0 + L * i / n, y0 + L * (i + 1) / n
            za, zb = (-0.1, H) if i % 2 == 0 else (H, -0.1)
            G.beam(V(x, ya, za), V(x, yb, zb), 0.08, 0.1)
        kit.p("Handrail", "chrome").tube(V(x - sx * 0.12, y0, H - 0.2), V(x - sx * 0.12, y1, H - 0.2), 0.025, 6)
        kit.p("RailLED", "glow_white").face([(x - sx * 0.14, y0, H - 0.24), (x - sx * 0.1, y0, H - 0.24), (x - sx * 0.1, y1, H - 0.24),
                                             (x - sx * 0.14, y1, H - 0.24)], toward=(0, 0, -1))
        kit.collide((x - 0.1, y0, 0.0), (x + 0.1, y1, H + 0.1))
    for y in (y0 + L / 3, y0 + 2 * L / 3):
        kit.p("Supports", "concrete").box((-1.0, y - 0.6, -6.0), (1.0, y + 0.6, -0.6))
        kit.p("Supports", "trim_brown").box((-1.5, y - 0.3, -0.6), (1.5, y + 0.3, -0.35))
        kit.collide((-1.0, y - 0.6, -6.0), (1.0, y + 0.6, -0.6))
    for y in (y0, y1):
        kit.p("Abutments", "concrete").box((-2.0, y - (1.0 if y < 0 else 0.0), -1.5), (2.0, y + (0.0 if y < 0 else 1.0), 0.0), skip="")
    far = tc.Far(kit.name)
    for sx in (-1, 1):
        far.beam(V(sx * 1.35, y0, -0.35), V(sx * 1.35, y1, -0.35), 0.2, 0.5, "trim_brown")
        far.beam(V(sx * 1.35, y0, H), V(sx * 1.35, y1, H), 0.16, 0.16, "trim_brown")
    far.box((-W / 2, y0, -0.12), (W / 2, y1, 0.0), "deck", skip="b")
    kit.entrance((0.0, y0, 0.0), "-Y", W, kind="path", note="deck top z = 0; the other end at +Y")
    kit.info.update(walk_in=False, deck_top_z=0.0, footprint=[-2.0, y0 - 1.0, 2.0, y1 + 1.0])
    return far


def tunnel_portal(kit):
    W, Hf, bw, bh, L = 12.0, 10.0, 6.0, 7.5, 20.0
    r = bw / 2
    spring = bh - r
    S = kit.p("Face", "fieldstone")
    # the face: a wall with the arched bore cut out (the arch as a polygon fan of quads)
    arc = [(r * math.cos(math.pi * k / 12), spring + r * math.sin(math.pi * k / 12)) for k in range(13)]
    tc.wall(S, "S", 0.0, -W / 2, -r, 0.0, Hf)
    tc.wall(S, "S", 0.0, r, W / 2, 0.0, Hf)
    for (a0, z0), (a1, z1) in zip(arc, arc[1:]):
        lo, hi = min(a0, a1), max(a0, a1)
        S.face([(a0, 0.0, z0), (a1, 0.0, z1), (a1, 0.0, Hf), (a0, 0.0, Hf)], toward=(0, -1, 0))
    S.face([(-r, 0.0, 0.0), (r, 0.0, 0.0), (r, 0.0, 0.0), (-r, 0.0, 0.0)], toward=(0, -1, 0)) if False else None
    # voussoirs round the arch, a keystone, the blank date stone, the coping
    Vs = kit.p("Voussoirs", "stone")
    for k in range(12):
        t0, t1 = math.pi * k / 12, math.pi * (k + 1) / 12
        p0 = [(r * math.cos(t), spring + r * math.sin(t)) for t in (t0, t1)]
        p1 = [((r + 0.7) * math.cos(t), spring + (r + 0.7) * math.sin(t)) for t in (t0, t1)]
        Vs.face([(p0[0][0], -0.12, p0[0][1]), (p1[0][0], -0.12, p1[0][1]), (p1[1][0], -0.12, p1[1][1]), (p0[1][0], -0.12, p0[1][1])][::-1],
                toward=(0, -1, 0))
    Vs.box((-0.4, -0.25, bh - 0.05), (0.4, 0.0, bh + 0.95))
    kit.p("DateStone", "stone").box((-1.0, -0.2, bh + 1.3), (1.0, 0.0, bh + 2.0))
    kit.p("Coping", "stone").box((-W / 2 - 0.2, -0.35, Hf), (W / 2 + 0.2, 0.6, Hf + 0.4))
    for x in (-W / 2, W / 2):                              # pilasters at the face's ends
        kit.p("Coping", "stone").box((x - 0.5, -0.3, 0.0), (x + 0.5, 0.0, Hf))
    # wing walls angling back into the hill, stepped down
    for sx in (-1, 1):
        a = V(sx * W / 2, 0.0, 0.0)
        b = V(sx * (W / 2 + 6.0), -4.5, 0.0)
        Wg = kit.p("Wings", "fieldstone")
        Wg.face([a, b, b + V(0, 0, 3.0), a + V(0, 0, Hf)], toward=(sx * 0.6, -0.8, 0) if sx > 0 else (sx * 0.6, -0.8, 0))
        Wg.face([a + V(0, 0.8, 0), b + V(0, 0.8, 0), b + V(0, 0.8, 3.0), a + V(0, 0.8, Hf)], toward=(-sx * 0.6, 0.8, 0))
        kit.p("Coping", "stone").beam(a + V(0, 0.4, Hf + 0.1), b + V(0, 0.4, 3.1), 1.0, 0.25)
        lo = V(min(a.x, b.x), min(a.y, b.y), 0)
        hi = V(max(a.x, b.x), max(a.y, b.y) + 0.8, Hf)
        kit.collide((lo.x, lo.y, 0), (hi.x, hi.y, Hf))
    kit.collide((-W / 2 - 0.5, -0.3, 0), (-r, 0.6, Hf + 0.4))
    kit.collide((r, -0.3, 0), (W / 2 + 0.5, 0.6, Hf + 0.4))
    kit.collide((-r, -0.3, bh), (r, 0.6, Hf + 0.4))
    # the lined bore, going dark: the lining faces inward, the far end black
    Ln = kit.p("Bore", "concrete")
    for (a0, z0), (a1, z1) in zip(arc, arc[1:]):
        Ln.face([(a0, 0.0, z0), (a1, 0.0, z1), (a1, L, z1), (a0, L, z0)], toward=(-a0 - a1, 0, -(z0 + z1 - 2 * spring)))
    for sx in (-1, 1):
        Ln.face([(sx * r, 0.0, 0.0), (sx * r, L, 0.0), (sx * r, L, spring), (sx * r, 0.0, spring)], toward=(-sx, 0, 0))
        kit.collide((sx * r - (0.3 if sx > 0 else -0.0) - (0.0 if sx > 0 else 0.3), 0.0, 0), (sx * r + (0.3 if sx > 0 else 0.0), L, bh))
    kit.p("BoreEnd", "soot").face([(-r, L, 0.0), (r, L, 0.0), (r, L, bh), (-r, L, bh)], toward=(0, -1, 0))
    kit.p("BoreDark", "shade").face([(-r, L * 0.6, 0.01), (r, L * 0.6, 0.01), (r, L, 0.01), (-r, L, 0.01)], toward=(0, 0, 1))
    # the track: ballast, ties, rails, from the face into the dark
    kit.p("Ballast", "stone").face([(-1.8, -6.0, 0.0), (1.8, -6.0, 0.0), (1.8, L, 0.0), (-1.8, L, 0.0)], toward=(0, 0, 1))
    for k in range(int((L + 6.0) / 0.6)):
        y = -6.0 + k * 0.6
        kit.p("Ties", "darkwood").box((-1.3, y - 0.11, 0.0), (1.3, y + 0.11, 0.15), skip="b")
    for x in (-0.72, 0.72):
        kit.p("Rails", "metal_galv").box((x - 0.04, -6.0, 0.15), (x + 0.04, L, 0.3), skip="b")
    far = tc.Far(kit.name)
    far.box((-W / 2, -0.3, 0), (-r, 0.0, Hf), "fieldstone", skip="b")
    far.box((r, -0.3, 0), (W / 2, 0.0, Hf), "fieldstone", skip="b")
    far.box((-r, -0.3, bh), (r, 0.0, Hf), "fieldstone", skip="b")
    far.quad("S", 0.05, -r, r, 0.0, bh, "soot", d=0.0)
    kit.entrance((0.0, -0.5, 0.0), "-Y", bw, kind="rail", note="the track enters the bore (+Y), dark at 20 m")
    kit.info.update(walk_in=True, bore=[bw, bh, L], footprint=[-W / 2 - 6.0, -4.5, W / 2 + 6.0, L])
    return far


FNS = {"footbridge": footbridge, "tunnel_portal": tunnel_portal}


def build(name, **overrides):
    module = f"town_{name}"
    nm = "Town" + "".join(w.capitalize() for w in name.split("_"))
    col, root, kit = tc.begin(nm, module)
    far = FNS[name](kit)
    parts = tc.finish(kit, col, root, far)
    return root, parts
