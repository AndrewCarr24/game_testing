"""Gate pier: a monolithic limestone shaft with a shadow-gap band, a thin overhanging cap,
a vertical light slot on its inner face (+X) and a stone wing wall on its outer side (-X)
that closes the gap between the pier and the end of the hedge. Place the east pier rotated
180 degrees. Units are metres. Origin: the pier's centre on the ground.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gate_common as gc  # noqa: E402

importlib.reload(gc)
common, outdoor = gc.common, gc.outdoor

NAME = "GatePier"

P = dict(
    name=NAME,
    width=1.2,          # x
    depth=1.4,          # y, the hedge's thickness
    shaft_h=2.96,
    band_h=0.06,
    cap_h=0.18,
    cap_over=0.07,
    wing_len=0.65,
    wing_h=2.8,         # flush with the hedge
    slot_w=0.07,
    slot_z=(1.75, 2.65),
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    parts = gc.Parts(n, col, root)
    sb = parts.bm("Stone", outdoor.stone(), 2.0)
    w2, d2 = p["width"] / 2, p["depth"] / 2
    sh, wh = p["shaft_h"], p["wing_h"]
    V, X, Y, Z = gc.V, gc.V(1, 0, 0), gc.V(0, 1, 0), gc.V(0, 0, 1)

    # shaft: four faces, the west one only above the wing
    gc.box(sb, V(-w2, -d2, 0), V(w2, d2, sh), sides="nse", top=False)
    gc.grid_face(sb, V(-w2, d2, wh), -Y, Z, p["depth"], sh - wh)
    # wing wall (west): both long faces and the top; its end is inside the hedge
    gc.box(sb, V(-w2 - p["wing_len"], -d2, 0), V(-w2, d2, wh), sides="ns", top=True)
    # shadow-gap band (dark, inset) and cap
    inset = 0.045
    gc.box(parts.bm("Band", outdoor.dark_metal()), V(-w2 + inset, -d2 + inset, sh), V(w2 - inset, d2 - inset, sh + p["band_h"]),
           sides="nsew", top=False)
    o = p["cap_over"]
    zc = sh + p["band_h"]
    gc.box(sb, V(-w2 - o, -d2 - o, zc), V(w2 + o, d2 + o, zc + p["cap_h"]), sides="nsew", top=True, bottom=True)
    # light slot on the inner face, standing 1.5 cm proud, with a dark surround
    z0, z1 = p["slot_z"]
    sw = p["slot_w"]
    lamp = outdoor.lamp()
    gc.box(parts.bm("Lamp", lamp), V(w2, -sw / 2, z0), V(w2 + 0.012, sw / 2, z1), sides="e", top=False)
    gc.box(parts.bm("Band", outdoor.dark_metal()), V(w2, -sw / 2 - 0.02, z0 - 0.02), V(w2 + 0.006, sw / 2 + 0.02, z1 + 0.02),
           sides="nsew", top=True)
    return root, parts.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
