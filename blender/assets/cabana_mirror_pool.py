"""A long black reflecting pool under the bathhouse rest room's window (after Tadao Ando's sheets
of still water: the Water Temple, the Church on the Water): 15 x 2.4 m of water held 6 cm under
a thin limestone rim 12 cm above the lawn, so from the room it reads as a dark mirror of the
sky and the cypresses with the hills beyond. Origin: the centre, lawn level."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cabana_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common
outdoor = cc.outdoor

NAME = "CabanaMirrorPool"

P = dict(name=NAME, size=(15.0, 2.4), rim=0.25, h=0.12, water=0.06)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = cc.start(n)
    m = cc.M()
    W, D = p["size"]
    r, h = p["rim"], p["h"]
    for nm, lo, hi in (("S", (-W / 2 - r, -D / 2 - r, 0), (W / 2 + r, -D / 2, h)),
                       ("N", (-W / 2 - r, D / 2, 0), (W / 2 + r, D / 2 + r, h)),
                       ("W", (-W / 2 - r, -D / 2, 0), (-W / 2, D / 2, h)),
                       ("E", (W / 2, -D / 2, 0), (W / 2 + r, D / 2, h))):
        cc.box(f"{n}_Rim{nm}", lo, hi, m["stone"], col, root, step=1.5, drop=("-z",))
    cc.grid(f"{n}_Water", (-W / 2, -D / 2), (W / 2, D / 2), h - p["water"], outdoor.water(), col, root, step=1.5)
    return cc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
