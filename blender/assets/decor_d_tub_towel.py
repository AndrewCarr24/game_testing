"""A bath towel hung over the freestanding tub's rim: down the outside, over the rounded
lip, a short way down the inside, following bath_tub's rim profile. The rim runs along X;
origin: the outer edge of the flat rim top (z = 0 = rim top), outside = -Y."""
import importlib
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import decor_d_kit as kit  # noqa: E402

importlib.reload(kit)

NAME = "DecorD_TubTowel"
P = dict(name=NAME, width=0.42, thick=0.012, drop_out=0.36, drop_in=0.15, cloth="ivory")

# bath_tub rim section, (y, z) relative to the outer edge of the rim top: outside wall going
# up, over the top, down the inside
RIM = [(-0.031, -0.20), (-0.0295, -0.12), (-0.027, -0.07), (-0.022, -0.028), (-0.017, -0.015), (-0.011, -0.006),
       (-0.005, -0.0015), (0.0, 0.0), (0.008, 0.0005), (0.016, 0.0), (0.022, -0.003), (0.028, -0.009), (0.034, -0.018),
       (0.040, -0.031), (0.052, -0.062), (0.068, -0.11)]


def build(**overrides):
    p = {**P, **overrides}
    B = kit.Builder(p["name"])
    t = p["thick"]
    path = [(-0.033 - 0.004, -p["drop_out"]), (-0.032, -0.28)] + RIM
    # inside: continue down the slope to drop_in
    (ya, za), (yb, zb) = RIM[-2], RIM[-1]
    k = (p["drop_in"] + zb) / max(zb - za, -1e-6)
    path.append((yb + (yb - ya) * 0.6, -p["drop_in"]))
    out = kit.drape_band(path, t, gap=0.0015)
    bm = kit.bv.soft_extrude(out, -p["width"] / 2, p["width"] / 2, ease=0.012, inset=0.005)
    for f in bm.faces:
        f.smooth = True
    B.add(p["cloth"], bm)
    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    print(NAME, kit.common.triangle_count(parts))
