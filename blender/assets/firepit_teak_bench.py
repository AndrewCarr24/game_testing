"""Slatted teak bench with a low back on black steel end frames, for the petanque court.
Long axis X, seat faces -Y. Origin: floor centre. Metres."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import firepit_common as fc  # noqa: E402

importlib.reload(fc)
common, outdoor = fc.common, fc.outdoor

NAME = "FirepitTeakBench"
P = dict(name=NAME, length=1.9, depth=0.46, seat_h=0.45, slats=5, slat_w=0.075, back_deg=-12.0)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = fc.new_asset(n)
    L, D, H = p["length"], p["depth"], p["seat_h"]
    teak, dark = outdoor.teak(), outdoor.dark_metal()
    ns, sw = p["slats"], p["slat_w"]
    gap = (D - 0.05 - ns * sw) / (ns - 1)
    seat = []
    for i in range(ns):
        y = -D / 2 + 0.025 + sw / 2 + i * (sw + gap)
        seat.append(((L, sw, 0.035), (0, y, H - 0.0175), (0, 0, 0), 0))
    fc.merge_boxes(f"{n}_Seat", seat, teak, col, root, uv_tile=0.5)
    # back: three slats on raked steel posts at the rear
    back = []
    for i in range(3):
        back.append(((L, 0.03, 0.08), (0, D / 2 - 0.06 - 0.0 , H + 0.14 + i * 0.12), (p["back_deg"], 0, 0), 0))
    fc.merge_boxes(f"{n}_Back", back, teak, col, root, uv_tile=0.5)
    frame = []
    for sx in (-1, 1):
        x = sx * (L / 2 - 0.12)
        frame.append(((0.04, 0.05, H - 0.035), (x, -D / 2 + 0.07, (H - 0.035) / 2), (0, 0, 0), 0))   # front leg
        frame.append(((0.04, 0.05, H - 0.035), (x, D / 2 - 0.07, (H - 0.035) / 2), (0, 0, 0), 0))    # rear leg
        frame.append(((0.04, 0.05, 0.34), (x, D / 2 - 0.045, H + 0.12), (p["back_deg"], 0, 0), 0))   # back post
    fc.merge_boxes(f"{n}_Frame", frame, dark, col, root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts
