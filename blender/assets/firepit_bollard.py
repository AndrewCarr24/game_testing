"""Low path bollard light: a black steel post with a warm lens band under a flat cap.
Origin: base centre. Metres."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import firepit_common as fc  # noqa: E402

importlib.reload(fc)
common, outdoor = fc.common, fc.outdoor

NAME = "FirepitBollard"
P = dict(name=NAME, size=0.11, height=0.50, lens_h=0.07)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = fc.new_asset(n)
    s, h, lh = p["size"], p["height"], p["lens_h"]
    fc.merge_boxes(f"{n}_Body", [((s, s, h - lh - 0.04), (0, 0, (h - lh - 0.04) / 2), (0, 0, 0), 0),
                                 ((s + 0.03, s + 0.03, 0.04), (0, 0, h - 0.02), (0, 0, 0), 0)],
                   outdoor.dark_metal(), col, root)
    fc.box(f"{n}_Lens", (s - 0.01, s - 0.01, lh), (0, 0, h - 0.04 - lh / 2), outdoor.lamp(), col, root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts
