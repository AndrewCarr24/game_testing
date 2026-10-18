"""Low landscape bollard for the drive: a 14 cm square dark-steel post with a warm light
band under a thin cap. Units are metres. Origin: the foot of the post on the ground."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gate_common as gc  # noqa: E402

importlib.reload(gc)
common, outdoor = gc.common, gc.outdoor

NAME = "GateBollard"

P = dict(name=NAME, size=0.14, height=0.78, band=(0.67, 0.72), cap=0.045, cap_over=0.02)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    parts = gc.Parts(n, col, root)
    V = gc.V
    h = p["size"] / 2
    metal = parts.bm("Post", outdoor.dark_metal())
    z0, z1 = p["band"]
    gc.box(metal, V(-h, -h, 0), V(h, h, z0), step=3.0, top=False)
    gc.box(metal, V(-h, -h, z1), V(h, h, p["height"] - p["cap"]), step=3.0, top=False, bottom=True)
    lamp = parts.bm("Lamp", outdoor.lamp())
    e = 0.004
    gc.box(lamp, V(-h - e, -h - e, z0), V(h + e, h + e, z1), step=3.0, top=False, bottom=False)
    o = p["cap_over"]
    gc.box(metal, V(-h - o, -h - o, p["height"] - p["cap"]), V(h + o, h + o, p["height"]), step=3.0,
           top=True, bottom=True)
    return root, parts.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
