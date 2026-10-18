"""Large square cantilever umbrella: charcoal canvas canopy (3.2 m square, shallow hip
roof with a valance) on an offset dark-metal pole with a horizontal arm, on a weighted
square base. Origin: the base centre on the floor; the canopy extends toward +Y
(rotate 180 for the other way). Real geometry; the canopy is a patch cut into 0.8 m
cells so it shades the baked deck properly."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pool_common as pc  # noqa: E402

importlib.reload(pc)
common = pc.common

NAME = "PoolUmbrella"

P = dict(
    name=NAME,
    size=3.2,
    offset=1.9,          # pole to canopy centre
    eave_z=2.33,
    peak_z=2.86,
    valance=0.13,
    pole_top=2.97,
    pole=0.075,
    cells=4,
)


def build(**overrides):
    p = {**P, **overrides}
    b = pc.Builder(p["name"])
    metal, canvas = pc.outdoor.dark_metal(), pc.canvas()
    conc = pc.outdoor.concrete()
    s, off, ez, pz, v = p["size"], p["offset"], p["eave_z"], p["peak_z"], p["valance"]
    h = s / 2
    # base: a weighted slab and a plinth, then the pole and the arm
    b.box(conc, (-0.45, -0.45, 0.0), (0.45, 0.45, 0.07), skip=("-z",), step=1.5)
    b.box(metal, (-0.2, -0.2, 0.07), (0.2, 0.2, 0.12), skip=("-z",))
    pw = p["pole"] / 2
    b.box(metal, (-pw, -pw, 0.12), (pw, pw, p["pole_top"]), skip=("-z",), step=1.5)
    aw = 0.05
    b.box(metal, (-aw / 2, -pw, p["pole_top"] - 0.07), (aw / 2, off + 0.04, p["pole_top"]), skip=("-y",), step=1.5)
    # hub post from the arm down to the canopy peak
    b.box(metal, (-0.025, off - 0.025, pz - 0.02), (0.025, off + 0.025, p["pole_top"] - 0.07), skip=("-z", "+z"))
    # canopy
    def zf(x, y):
        d = max(abs(x), abs(y - off)) / h
        return pz - (pz - ez) * d
    n = p["cells"]
    b.patch(canvas, -h, off - h, h, off + h, n, n, zf, up=True)
    b.patch(canvas, -h, off - h, h, off + h, n, n, lambda x, y: zf(x, y) - 0.012, up=False)
    # valance (vertical band round the eaves)
    corners = [(-h, off - h), (h, off - h), (h, off + h), (-h, off + h)]
    for (ax, ay), (bx, by), nrm in zip(corners, corners[1:] + corners[:1], ((0, -1), (1, 0), (0, 1), (-1, 0))):
        b.vwall(canvas, (ax, ay), (bx, by), ez - v, ez, nrm, step=1.6)
        b.vwall(canvas, (ax, ay), (bx, by), ez - v, ez, (-nrm[0], -nrm[1]), step=1.6)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    pc.report(root, parts)
