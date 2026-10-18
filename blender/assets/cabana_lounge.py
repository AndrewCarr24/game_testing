"""Pool house lounge group on a flax rug: a three-seat sofa on a dark teak plinth with cream
cushions, two teak-framed armchairs, a limestone coffee table and a tray. The sofa faces -Y.
Origin: centre of the rug on the floor. Units are metres."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cabana_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common

NAME = "CabanaLounge"

P = dict(name=NAME, sofa_w=3.1, sofa_y=1.15, rug=(4.8, 3.4))


def armchair(n, tag, col, parent, m, loc, rot):
    g = cc.group(f"{n}_Chair{tag}", col, parent, loc, rot)
    box = cc.box
    # teak frame: two side frames and rails, seat and back cushions, a clay pillow
    for sx in (-1, 1):
        box(f"{n}_Arm{tag}{sx}", (sx * 0.36 - 0.045, -0.36, 0.10), (sx * 0.36 + 0.045, 0.40, 0.58), m["teak"], col, g,
            drop=("-z",))
    box(f"{n}_Base{tag}", (-0.34, -0.34, 0.12), (0.34, 0.40, 0.24), m["warm_dark"], col, g, drop=("-z",))
    box(f"{n}_Seat{tag}", (-0.33, -0.36, 0.24), (0.33, 0.30, 0.40), m["sand"], col, g, drop=("-z",), bevel=0.03)
    box(f"{n}_Back{tag}", (-0.33, 0.28, 0.30), (0.33, 0.42, 0.78), m["sand"], col, g, drop=("-z",))
    box(f"{n}_Pillow{tag}", (-0.17, 0.12, 0.40), (0.17, 0.25, 0.66), m["clay"], col, g, drop=("-z",))
    return g


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = cc.start(n)
    m = cc.M()
    box = cc.box
    W, sy = p["sofa_w"], p["sofa_y"]

    rw, rd = p["rug"]
    box(f"{n}_Rug", (-rw / 2, -rd / 2, 0), (rw / 2, rd / 2, 0.018), m["rug"], col, root, drop=("-z",))

    # sofa (faces -y): plinth, arms, three seat cushions, three back cushions, two pillows
    g = cc.group(f"{n}_Sofa", col, root, (0, sy, 0))
    box(f"{n}_SofaBase", (-W / 2, -0.46, 0.07), (W / 2, 0.48, 0.24), m["warm_dark"], col, g, drop=("-z",))
    for sx in (-1, 1):
        x0 = sx * (W / 2 - 0.10)
        box(f"{n}_SofaArm{sx}", (x0 - 0.10, -0.46, 0.07), (x0 + 0.10, 0.48, 0.60), m["teak"], col, g, drop=("-z",))
    cw = (W - 0.40) / 3
    for i in range(3):
        x = -W / 2 + 0.20 + cw * i
        box(f"{n}_SofaSeat{i}", (x + 0.008, -0.45, 0.24), (x + cw - 0.008, 0.30, 0.44), m["cream"], col, g, drop=("-z",), bevel=0.035)
        box(f"{n}_SofaBack{i}", (x + 0.008, 0.28, 0.30), (x + cw - 0.008, 0.48, 0.84), m["cream"], col, g, drop=("-z",))
    box(f"{n}_SofaPillowL", (-1.05, 0.08, 0.44), (-0.60, 0.26, 0.78), m["clay"], col, g, drop=("-z",))
    box(f"{n}_SofaPillowR", (0.62, 0.08, 0.44), (1.07, 0.26, 0.78), m["charcoal"], col, g, drop=("-z",))

    # coffee table + tray
    box(f"{n}_Table", (-0.70, -0.55, 0.0), (0.70, 0.20, 0.34), m["stone"], col, root, step=None, drop=("-z",))
    box(f"{n}_Tray", (-0.22, -0.32, 0.34), (0.22, -0.02, 0.37), m["bronze"], col, root, drop=("-z",))

    # armchairs facing the table from both sides
    armchair(n, "W", col, root, m, (-2.05, -0.55, 0.0), -90)
    armchair(n, "E", col, root, m, (2.05, -0.55, 0.0), 90)
    return cc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
