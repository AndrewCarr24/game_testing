"""Gate keypad / intercom pedestal: a slim dark-steel column with a bronze face plate, a
lit keypad window and a camera dome. Units are metres. The face (-Y) is where the driver
leans out. Origin: the foot of the column on the ground."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gate_common as gc  # noqa: E402

importlib.reload(gc)
common, outdoor = gc.common, gc.outdoor

NAME = "GateKeypad"

P = dict(name=NAME, w=0.22, d=0.16, height=1.15)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    parts = gc.Parts(n, col, root)
    V = gc.V
    hw, hd, H = p["w"] / 2, p["d"] / 2, p["height"]
    metal = parts.bm("Column", outdoor.dark_metal())
    gc.box(metal, V(-hw, -hd, 0), V(hw, hd, H), step=3.0, top=True, bottom=False)
    br = parts.bm("Plate", outdoor.bronze())
    gc.box(br, V(-hw + 0.03, -hd - 0.012, 0.58), V(hw - 0.03, -hd, 1.02), step=3.0, top=True, bottom=True, sides="s")
    lamp = parts.bm("Lamp", outdoor.lamp())
    gc.box(lamp, V(-0.045, -hd - 0.016, 0.88), V(0.045, -hd - 0.012, 0.96), step=3.0, top=False, sides="s")
    gc.box(lamp, V(-0.003, -hd - 0.016, 0.64), V(0.003, -hd - 0.012, 0.80), step=3.0, top=False, sides="s")
    gc.cylinder(metal, (0.0, -hd - 0.012), 0.022, 1.02, 1.06, sides=8)
    return root, parts.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
