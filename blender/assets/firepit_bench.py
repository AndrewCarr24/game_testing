"""Built-in curved fire bench: a limestone base swept round 270 degrees of a 4.7 m
radius circle (open toward -Y, the house) with charcoal cushions in twelve gapped sections.
Origin: circle centre, bottom at z = 0 (place on the terrace top). Units are metres."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import firepit_common as fc  # noqa: E402

importlib.reload(fc)
common, outdoor = fc.common, fc.outdoor

NAME = "FirepitBench"
P = dict(
    name=NAME,
    r_in=4.05,
    r_out=4.70,
    base_h=0.36,
    cushion_h=0.11,
    start_deg=-45.0,      # the arc runs from -45 round through north to 225 (gap faces -Y)
    span_deg=270.0,
    pieces=12,
    gap_deg=0.9,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = fc.new_asset(n)
    ri, ro, bh = p["r_in"], p["r_out"], p["base_h"]
    a0, span = p["start_deg"], p["span_deg"]

    bm = fc.sweep_bm([(ro, 0), (ro, bh), (ri, bh), (ri, 0)], a0, a0 + span, 36)
    fc.finish(bm, f"{n}_Base", col, root, outdoor.stone(), uv_tile=2.0)

    bm = bmesh.new()
    ci, co, ch = ri + 0.03, ro - 0.03, p["cushion_h"]
    prof = [(co, 0), (co, ch - 0.035), (co - 0.05, ch), (ci + 0.05, ch), (ci, ch - 0.035), (ci, 0)]
    step = span / p["pieces"]
    for k in range(p["pieces"]):
        s0 = a0 + k * step + p["gap_deg"] / 2
        fc.sweep_bm(prof, s0, s0 + step - p["gap_deg"], 2, z0=bh, bm=bm)
    fc.finish(bm, f"{n}_Cushions", col, root, fc.charcoal_cushion())

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts
