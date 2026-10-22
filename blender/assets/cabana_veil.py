"""A cedar lattice veil for the bath hall's west glass (after Kengo Kuma's timber screens: thin
battens close-set, read as a soft surface, not as bars). It hangs on dark steel outriggers 0.5 m
off the glass, from just over the door transom (3.1 m) up past the roof edge, so the low west
sun comes through it in stripes across the hall and its east wall while the lower glass stays
clear (the view down the water, and the danger of being seen). Battens 5 x 20 cm at 16 cm.
Origin: on the glass line (the hall's west wall, x = 27) at the middle of its 13.5 m run,
lawn level; the veil lies to -x (outside). No colliders (NoCollide): it's above head height."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cabana_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common

NAME = "CabanaVeil"

P = dict(name=NAME, length=13.5, z0=3.1, z1=5.75, off=0.5, w=0.05, d=0.2, pitch=0.16, floor=0.08)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = cc.start(n)
    m = cc.M()
    L, f = p["length"], p["floor"]
    z0, z1 = p["z0"] + f, p["z1"] + f
    xc = -p["off"] - p["d"] / 2
    count = int(L / p["pitch"])
    y0 = -(count - 1) * p["pitch"] / 2
    for i in range(count):
        y = y0 + i * p["pitch"]
        cc.box(f"{n}_NoCollide_Batten{i:03d}", (xc - p["d"] / 2, y - p["w"] / 2, z0), (xc + p["d"] / 2, y + p["w"] / 2, z1),
               m["teak"], col, root, drop=("+z",))
    # the steel: a top rail and a bottom rail through the battens, outriggers back to the glass line
    for nm, z in (("Top", z1 - 0.12), ("Bottom", z0 + 0.1)):
        cc.box(f"{n}_NoCollide_Rail{nm}", (xc - 0.015, -L / 2, z - 0.03), (xc + 0.015, L / 2, z + 0.03), m["dark"], col, root)
    k = 9
    for i in range(k + 1):
        y = -L / 2 + 0.2 + (L - 0.4) * i / k
        for z in (z1 - 0.12, z0 + 0.1):
            cc.box(f"{n}_NoCollide_Arm{i}_{int(z * 10)}", (xc, y - 0.02, z - 0.025), (-0.06, y + 0.02, z + 0.025), m["dark"], col, root)
    return cc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
