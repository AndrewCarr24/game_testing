"""Pool house bar: a limestone-topped counter with bronze-clad front, a teak-and-dark back bar
with floating shelves and bottles against the wall, three stools and three pendants. The
counter faces -Y (guests), the back bar is at +Y. Origin: floor centre of the counter. Units are
metres."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cabana_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common

NAME = "CabanaBar"

P = dict(name=NAME, length=3.8, back_y=1.62, ceil=3.15)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = cc.start(n)
    m = cc.M()
    box, cyl = cc.box, cc.cyl
    Ln = p["length"]
    h = Ln / 2

    # counter: dark core, bronze fluted front boards, stone top with a waterfall-free overhang
    box(f"{n}_Core", (-h, -0.34, 0.08), (h, 0.32, 1.0), m["warm_dark"], col, root, drop=("-z", "-y"))
    nb = int(Ln / 0.26)
    for i in range(nb):
        x = -h + 0.1 + i * (Ln - 0.2) / (nb - 1)
        box(f"{n}_Flute{i}", (x - 0.07, -0.40, 0.08), (x + 0.07, -0.34, 1.0), m["bronze"], col, root, drop=("-z", "+y", "+z"))
    box(f"{n}_Top", (-h - 0.04, -0.46, 1.0), (h + 0.04, 0.42, 1.06), m["stone"], col, root, step=1.3, drop=("-z",))
    box(f"{n}_Foot", (-h, -0.30, 0.0), (h, 0.28, 0.08), m["dark"], col, root, drop=("-z",))
    box(f"{n}_Rail", (-h + 0.1, -0.52, 0.12), (h - 0.1, -0.49, 0.15), m["dark"], col, root, drop=("-z",))  # foot rail

    # back bar against the wall
    by = p["back_y"]
    box(f"{n}_BackLow", (-h, by, 0.0), (h, by + 0.55, 0.88), m["warm_dark"], col, root, step=2.0, drop=("-z", "+y"))
    box(f"{n}_BackTop", (-h, by - 0.02, 0.88), (h, by + 0.56, 0.93), m["stone"], col, root, step=1.3, drop=("-z",))
    box(f"{n}_BackPanel", (-h, by + 0.55, 0.93), (h, by + 0.60, 2.55), m["teak"], col, root, step=1.6, keep=("-y",))
    for i, z in enumerate((1.55, 2.10)):
        box(f"{n}_Shelf{i}", (-h + 0.2, by + 0.25, z), (h - 0.2, by + 0.55, z + 0.04), m["stone"], col, root, drop=("-z",))
    # bottles: groups of small boxes and a few cylinders on the shelves and the back-bar top
    colours = (m["charcoal"], m["bronze"], m["sand"], m["clay"])
    k = 0
    for z, y in ((0.93, by + 0.30), (1.59, by + 0.40)):
        for j in range(5):
            x = -h + 0.45 + j * (Ln - 0.9) / 4 + 0.07 * (k % 3)
            bh = 0.20 + 0.06 * ((j + k) % 3)
            cyl(f"{n}_Bottle{k}_{j}", (x, y), 0.032, z, z + bh, colours[(j + k) % 4], col, root, seg=6, caps=(False, True))
        k += 1

    # stools
    for i, x in enumerate((-1.0, 0.0, 1.0)):
        cyl(f"{n}_StoolSeat{i}", (x, -0.78), 0.19, 0.70, 0.76, m["sand"], col, root, seg=8, caps=(False, True))
        cyl(f"{n}_StoolPost{i}", (x, -0.78), 0.025, 0.04, 0.70, m["dark"], col, root, seg=6, caps=(False, False))
        cyl(f"{n}_StoolFoot{i}", (x, -0.78), 0.17, 0.0, 0.04, m["dark"], col, root, seg=8, caps=(False, True))

    # pendants
    for i, x in enumerate((-1.0, 0.0, 1.0)):
        cyl(f"{n}_PendantRod{i}", (x, 0.0), 0.006, 2.15, p["ceil"], m["dark"], col, root, seg=4, caps=(False, False))
        cyl(f"{n}_Pendant{i}", (x, 0.0), 0.16, 1.98, 2.15, m["dark"], col, root, seg=8, caps=(False, False), r1=0.05)
        cyl(f"{n}_PendantLamp{i}", (x, 0.0), 0.12, 1.975, 1.98, m["lamp"], col, root, seg=8, caps=(True, False))
    return cc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
