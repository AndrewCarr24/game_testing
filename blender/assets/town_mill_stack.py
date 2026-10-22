"""The mill's round brick smokestack, kept as a landmark: a square stone-capped base, a
tapering round shaft of dark brick with corbelled bands, a corbelled crown, a lightning rod
and an aviation light. 34 m.

Origin: the ground centre; front -Y.
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

NAME = "TownMillStack"
P = dict(name=NAME, module="town_mill_stack", height=34.0, r0=1.6, r1=1.05, base_h=4.0)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, kit = tc.begin(n, p["module"])
    Hs, r0, r1, bh = p["height"], p["r0"], p["r1"], p["base_h"]
    B = kit.p("Base", "brick_red")
    kit.tints["Base"] = (0.72, 0.6, 0.55)
    B.box((-r0 - 0.4, -r0 - 0.4, 0.0), (r0 + 0.4, r0 + 0.4, bh), skip="bt")
    kit.p("BaseCap", "stone").box((-r0 - 0.55, -r0 - 0.55, bh), (r0 + 0.55, r0 + 0.55, bh + 0.35))
    S = kit.p("Shaft", "brick_red")
    kit.tints["Shaft"] = (0.66, 0.54, 0.5)
    z_top = Hs - 1.4
    S.cyl((0, 0), r0, bh + 0.35, z_top, sides=14, caps="", r1=r1)
    for f in (0.3, 0.6, 0.85):
        z = bh + 0.35 + (z_top - bh - 0.35) * f
        r = r0 + (r1 - r0) * f
        kit.p("Bands", "brick_red").cyl((0, 0), r + 0.07, z, z + 0.3, sides=14, caps="")
    C = kit.p("Crown", "brick_red")
    C.cyl((0, 0), r1 + 0.05, z_top, z_top + 0.4, sides=14, caps="", r1=r1 + 0.3)
    C.cyl((0, 0), r1 + 0.3, z_top + 0.4, Hs, sides=14, caps="", r1=r1 + 0.3)
    kit.p("Flue", "soot").cyl((0, 0), r1 - 0.1, Hs - 0.02, Hs - 0.01, sides=12)
    kit.tints["Crown"] = (0.62, 0.5, 0.46)
    kit.tints["Bands"] = (0.62, 0.5, 0.46)
    kit.p("Rod", "metal_dark").tube(V(r1 + 0.2, 0, Hs), V(r1 + 0.2, 0, Hs + 1.5), 0.02, 3)
    kit.p("Beacon", "neon_red").cyl((-(r1 + 0.2), 0), 0.1, Hs, Hs + 0.15, sides=6)
    kit.collide((-r0 - 0.55, -r0 - 0.55, 0), (r0 + 0.55, r0 + 0.55, Hs))
    far = tc.Far(n)
    far.box((-r0 - 0.4, -r0 - 0.4, 0.0), (r0 + 0.4, r0 + 0.4, bh), "brick_red", skip="b")
    far.cyl((0, 0), r0, bh, Hs, "brick_red", sides=8, cap=True, r1=r1 + 0.2)
    kit.info.update(walk_in=False, top_m=Hs, footprint=[-r0 - 0.55, -r0 - 0.55, r0 + 0.55, r0 + 0.55])
    parts = tc.finish(kit, col, root, far)
    return root, parts
