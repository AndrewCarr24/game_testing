"""Light switch: a slim graphite wall plate with one black rocker and a pin-prick amber
locator LED (the switch's indicator: lit while the lights are on and the house has power).
A `switch` on signal "lights" (the level renames it per room: {"signal": "lights_<room>"}),
starting on.

Wall-mounted: origin at the centre of the plate's back (on the wall face), front -Y;
place it with z = 1.1 (the plate's centre height)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402

importlib.reload(ix_common)
common = ix_common.common

NAME = "IX_Switch"

P = dict(
    name=NAME,
    plate_size=(0.086, 0.086, 0.008),     # w, h, t
    rocker_size=(0.040, 0.058, 0.006),
    plate="graphite",
    signal="lights",
    state=True,
    prompt="Turn on lights",
    promptActive="Turn off lights",
    glyphs=[],                            # (x, z, w, h) raised marks on the rocker
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    ix_common.switch(n, col, root, p)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
