"""Low clipped hedge ring (0.8 m, 0.8 m thick) round the fire terrace, in four arcs with
2.6 m openings to the south (the house path), west (petanque), north and east. Origin:
circle centre, bottom on the lawn. Units are metres."""
import importlib
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import firepit_common as fc  # noqa: E402

importlib.reload(fc)
common, outdoor = fc.common, fc.outdoor

NAME = "FirepitHedgeRing"
P = dict(
    name=NAME,
    r_in=5.7,
    r_out=6.5,
    height=0.8,
    gaps=[(270.0, 2.6), (180.0, 2.6), (90.0, 2.6), (0.0, 2.6)],   # (centre azimuth, width m)
    steps=7,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = fc.new_asset(n)
    ri, ro, h = p["r_in"], p["r_out"], p["height"]
    rm = (ri + ro) / 2
    c = 0.1
    prof = [(ro, 0), (ro, h - c), (ro - c, h), (ri + c, h), (ri, h - c), (ri, 0)]
    gaps = sorted((a % 360, w) for a, w in p["gaps"])
    bm = None
    for k, (ga, gw) in enumerate(gaps):
        half = math.degrees(math.asin(gw / 2 / rm))
        na, nw = gaps[(k + 1) % len(gaps)]
        s0 = ga + half
        s1 = na - math.degrees(math.asin(nw / 2 / rm)) + (360 if na <= ga else 0)
        bm = fc.sweep_bm(prof, s0, s1, p["steps"], bm=bm)
    fc.finish(bm, f"{n}_Hedge", col, root, outdoor.foliage(), uv_tile=1.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts
