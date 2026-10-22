"""The water tower (freshly painted): a cylindrical tank (9 m across, 8.4 m tall) with an
ellipsoidal bottom, a conical cap and a finial, on four splayed legs with sway rods and
horizontal struts, a riser pipe, a ladder with a cage, a catwalk with a railing round the
tank's foot, the town's mountain pictogram painted on the tank (no lettering), an aviation
light on top. Top at 24 m (the cove's backdrop shows it).

Origin: the ground centre; front -Y (the pictogram's side).
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

NAME = "TownWaterTower"
P = dict(name=NAME, module="town_water_tower", r=4.5, tank_h=8.4, top=24.0, legs=4)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, kit = tc.begin(n, p["module"])
    r, th, top = p["r"], p["tank_h"], p["top"]
    cap_h = 1.9
    z1 = top - cap_h - 0.35                     # the tank's top rim
    z0 = z1 - th + 1.2                          # its bottom rim (the bowl hangs 1.2 below)
    zb = z0 - 1.2
    W = "paint_white"
    kit.p("Tank", W).cyl((0, 0), r, z0, z1, sides=20, caps="")
    bowl = kit.p("Tank", W)
    rings = [(r, z0), (r * 0.85, z0 - 0.55), (r * 0.55, z0 - 0.95), (0.6, zb + 0.05)]
    for (ra, za), (rb, zb_) in zip(rings, rings[1:]):
        bowl.cyl((0, 0), ra, zb_, za, sides=20, caps="", r1=ra) if False else None
        for i in range(20):
            a0, a1 = 2 * math.pi * i / 20, 2 * math.pi * (i + 1) / 20
            bowl.face([(ra * math.cos(a0), ra * math.sin(a0), za), (rb * math.cos(a0), rb * math.sin(a0), zb_),
                       (rb * math.cos(a1), rb * math.sin(a1), zb_), (ra * math.cos(a1), ra * math.sin(a1), za)],
                      toward=(math.cos(a0) + math.cos(a1), math.sin(a0) + math.sin(a1), -1))
    kit.p("Cap", W).cyl((0, 0), r + 0.15, z1, z1 + 0.2, sides=20, caps="")
    kit.p("Cap", W).cyl((0, 0), r + 0.15, z1 + 0.2, top - 0.35, sides=20, caps="", r1=0.5)
    kit.p("Finial", W).cyl((0, 0), 0.5, top - 0.35, top - 0.15, sides=8)
    kit.p("Finial", "metal_dark").cyl((0, 0), 0.08, top - 0.15, top - 0.05, sides=6)
    kit.p("Beacon", "neon_red").cyl((0, 0), 0.12, top - 0.05, top, sides=6)
    # the pictogram, painted on the tank's front (a curved patch of sign cell)
    S = kit.p("Emblem", "signs")
    uv = tc.sign_uv("outfitter")
    k = 8
    for i in range(k):
        a0 = -math.pi / 2 - 0.55 + 1.1 * i / k
        a1 = -math.pi / 2 - 0.55 + 1.1 * (i + 1) / k
        u0 = uv[0][0] + (uv[1][0] - uv[0][0]) * i / k
        u1 = uv[0][0] + (uv[1][0] - uv[0][0]) * (i + 1) / k
        rr = r + 0.01
        S.face([(rr * math.cos(a0), rr * math.sin(a0), z0 + 1.6), (rr * math.cos(a1), rr * math.sin(a1), z0 + 1.6),
                (rr * math.cos(a1), rr * math.sin(a1), z0 + 4.2), (rr * math.cos(a0), rr * math.sin(a0), z0 + 4.2)],
               uvs=[(u0, uv[0][1]), (u1, uv[0][1]), (u1, uv[2][1]), (u0, uv[2][1])],
               toward=(math.cos(a0) + math.cos(a1), math.sin(a0) + math.sin(a1), 0))
    # legs: splayed tubes from the tank's rim to the footings; struts and sway rods
    Lg = kit.p("Legs", W)
    legs = []
    for i in range(p["legs"]):
        a = math.pi / 4 + i * 2 * math.pi / p["legs"]
        top_p = V(r * 0.98 * math.cos(a), r * 0.98 * math.sin(a), z0 + 0.5)
        foot = V((r + 1.2) * math.cos(a), (r + 1.2) * math.sin(a), 0.35)
        Lg.tube(foot, top_p, 0.28, sides=8)
        kit.p("Footings", "concrete").box((foot.x - 0.7, foot.y - 0.7, 0.0), (foot.x + 0.7, foot.y + 0.7, 0.4), skip="b")
        kit.collide((foot.x - 0.7, foot.y - 0.7, 0), (foot.x + 0.7, foot.y + 0.7, 2.5))
        legs.append((foot, top_p))
    for f in (0.3, 0.62):
        pts = [foot.lerp(tp, f) for foot, tp in legs]
        for i in range(len(pts)):
            a_, b_ = pts[i], pts[(i + 1) % len(pts)]
            Lg.tube(a_, b_, 0.1, sides=6)
    rods = kit.p("Rods", "metal_galv")
    for f0, f1 in ((0.0, 0.3), (0.3, 0.62), (0.62, 0.98)):
        for i in range(len(legs)):
            (fa, ta), (fb, tb) = legs[i], legs[(i + 1) % len(legs)]
            rods.tube(fa.lerp(ta, f0), fb.lerp(tb, f1), 0.025, 4)
            rods.tube(fb.lerp(tb, f0), fa.lerp(ta, f1), 0.025, 4)
    kit.p("Riser", W).tube(V(0, 0, 0.0), V(0, 0, zb + 0.1), 0.55, sides=10)
    kit.p("Riser", "concrete").box((-1.0, -1.0, 0.0), (1.0, 1.0, 0.3), skip="b")
    kit.collide((-0.6, -0.6, 0), (0.6, 0.6, zb))
    # the catwalk at the tank's foot with a railing, the ladder up a leg and the tank
    cw = kit.p("Catwalk", "metal_dark")
    ring_in, ring_out = r + 0.05, r + 1.0
    for i in range(20):
        a0, a1 = 2 * math.pi * i / 20, 2 * math.pi * (i + 1) / 20
        cw.face([(ring_in * math.cos(a0), ring_in * math.sin(a0), z0 + 0.2), (ring_out * math.cos(a0), ring_out * math.sin(a0), z0 + 0.2),
                 (ring_out * math.cos(a1), ring_out * math.sin(a1), z0 + 0.2), (ring_in * math.cos(a1), ring_in * math.sin(a1), z0 + 0.2)],
                toward=(0, 0, 1))
        cw.face([(ring_in * math.cos(a0), ring_in * math.sin(a0), z0 + 0.15), (ring_out * math.cos(a0), ring_out * math.sin(a0), z0 + 0.15),
                 (ring_out * math.cos(a1), ring_out * math.sin(a1), z0 + 0.15), (ring_in * math.cos(a1), ring_in * math.sin(a1), z0 + 0.15)],
                toward=(0, 0, -1))
    rl = kit.p("Railing", W)
    ring = [V(ring_out * math.cos(2 * math.pi * i / 20), ring_out * math.sin(2 * math.pi * i / 20), z0 + 1.25) for i in range(20)]
    rl.polyline(ring, 0.03, sides=4, closed=True)
    rl.polyline([q - V(0, 0, 0.5) for q in ring], 0.02, sides=4, closed=True)
    for q in ring[::2]:
        rl.tube(q - V(0, 0, 1.05), q, 0.025, 4)
    foot, tp = legs[3]
    lad = kit.p("Ladder", "metal_galv")
    d = (tp - foot).normalized()
    side = V(-d.y, d.x, 0).normalized() * 0.22
    off = V(foot.x, foot.y, 0).normalized() * 0.4
    for s in (-1, 1):
        lad.tube(foot + off + side * s + V(0, 0, 2.5), tp + off + side * s, 0.02, 4)
    steps_n = int((tp - foot).length / 0.6)
    for k_ in range(2, steps_n):
        q = foot.lerp(tp, k_ / steps_n) + off
        lad.tube(q - side, q + side, 0.012, 3)

    far = tc.Far(n)
    far.cyl((0, 0), r, zb + 0.6, z1, "paint_white", sides=10, cap=False)
    far.cyl((0, 0), r + 0.15, z1, top - 0.35, "paint_white", sides=10, cap=False, r1=0.5)
    for foot, tp in legs:
        far.beam(foot, tp, 0.5, 0.5, "paint_white")
    far.beam(V(0, 0, 0), V(0, 0, zb), 0.9, 0.9, "paint_white")
    kit.info.update(walk_in=False, top_m=top, tank=[round(2 * r, 2), th], footprint=[-r - 1.9, -r - 1.9, r + 1.9, r + 1.9])
    parts = tc.finish(kit, col, root, far)
    return root, parts
