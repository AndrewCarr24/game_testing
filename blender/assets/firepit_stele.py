"""Limestone stele: a tall slim block on a stepped plinth with a bronze inset band, the
terminus of the fire garden's north axis. Origin: base centre. Metres."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import firepit_common as fc  # noqa: E402

importlib.reload(fc)
common, outdoor = fc.common, fc.outdoor

NAME = "FirepitStele"
P = dict(name=NAME, width=0.8, depth=0.3, height=2.2)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = fc.new_asset(n)
    w, d, h = p["width"], p["depth"], p["height"]
    fc.merge_boxes(f"{n}_Stone", [((w + 0.5, d + 0.5, 0.12), (0, 0, 0.06), (0, 0, 0), 0.004),
                                  ((w, d, h - 0.12), (0, 0, 0.12 + (h - 0.12) / 2), (0, 0, 0), 0.006)],
                   outdoor.stone(), col, root, uv_tile=2.0)
    fc.box(f"{n}_Band", (0.06, d + 0.01, h - 0.6), (0.0, 0, 0.12 + (h - 0.6) / 2 + 0.1), outdoor.bronze(), col, root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts
