"""Cut-stone bridge pier with a pointed upstream cutwater: a battered shaft of coursed stone
under a projecting cap (the bearing seat for two town_truss_span ends).

Origin: the cap's top centre (z = 0, where the spans' floor beams bear: place it 0.95 m
under the spans' deck top); the pier hangs below to -height (below_m); the cutwater points
-Y (upstream: rotate it into the flow). The layout scales it in z.
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

NAME = "TownBridgePier"
P = dict(name=NAME, module="town_bridge_pier", width=4.0, length=10.0, height=10.0, batter=0.03)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, kit = tc.begin(n, p["module"])
    w, l, h, b = p["width"], p["length"], p["height"], p["batter"]
    S = kit.p("Stone", "fieldstone")

    def outline(z, grow):
        hw = w / 2 + grow
        hl = l / 2 - w / 2
        return [(0, -hl - hw * 1.3), (hw, -hl), (hw, hl), (hw * 0.6, hl + hw * 0.5), (-hw * 0.6, hl + hw * 0.5), (-hw, hl), (-hw, -hl)]
    top, bot = -0.45, -h
    o_top, o_bot = outline(top, 0.0), outline(bot, h * b)
    for i in range(len(o_top)):
        a0, a1 = o_top[i], o_top[(i + 1) % len(o_top)]
        b0, b1 = o_bot[i], o_bot[(i + 1) % len(o_bot)]
        S.face([(b0[0], b0[1], bot), (b1[0], b1[1], bot), (a1[0], a1[1], top), (a0[0], a0[1], top)])
    cap = outline(0, 0.25)
    C = kit.p("Cap", "concrete")
    C.prism(cap, top, 0.0, caps="t")
    kit.p("Bearings", "metal_dark").box((-1.0, -0.6, 0.0), (1.0, 0.6, 0.12))
    kit.collide((-w / 2 - 0.3, -l / 2 - 1.3, -h), (w / 2 + 0.3, l / 2 + 1.0, 0.0))
    far = tc.Far(n)
    far.box((-w / 2, -l / 2, -h), (w / 2, l / 2, 0.0), "fieldstone", top="stone")
    kit.info.update(walk_in=False, footprint=[-w / 2 - 0.3, round(-l / 2 - w / 2 * 1.3 + w / 2 - 0.3, 3), w / 2 + 0.3, round(l / 2 + 1.0, 3)])
    parts = tc.finish(kit, col, root, far)
    return root, parts
