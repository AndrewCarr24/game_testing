"""Thick oat linen bath mat: a field of soft lengthwise ribs (modelled, so they catch
the light and the AO) inside a rounded bound edge, with eased bound ends.
Origin: floor centre; the front faces -Y.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import bath_common as bc  # noqa: E402
import bath_vanity as bv  # noqa: E402  (soft_extrude)
import math  # noqa: E402

importlib.reload(common)
importlib.reload(bc)
importlib.reload(bv)

NAME = "BathMat"

P = dict(name=NAME, size=(1.3, 0.62), thickness=0.022, corner=0.07, ribs=11, binding=0.035)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    oat = materials.fabric("M_Fabric_Oat", (0.42, 0.37, 0.30))
    w, d = p["size"]
    t = p["thickness"]
    # cross-section across Y (counter-clockwise): flat underside, rounded bound edge,
    # ribs (crest at full thickness, valleys 40% lower), the other bound edge
    bw = p["binding"]
    out = [(d / 2 - 0.004, 0.0)]
    for k in range(5):                                 # +Y binding, rounding up and over
        a = -math.pi / 2 + (math.pi / 2) * k / 4
        out.append((d / 2 - 0.009 + 0.009 * math.cos(a), 0.009 + (t - 0.009) * (k / 4) ** 0.6 + 0.0 * math.sin(a)))
    out.append((d / 2 - bw, t))
    field = d - 2 * bw
    nr = p["ribs"]
    steps = nr * 4
    for k in range(1, steps):
        yy = d / 2 - bw - field * k / steps
        zz = t * (0.80 + 0.20 * math.cos(2 * math.pi * k / 4))
        out.append((yy, zz))
    out.append((-d / 2 + bw, t))
    for k in range(5):                                 # -Y binding
        a = (math.pi / 2) * k / 4
        out.append((-d / 2 + 0.009 - 0.009 * math.sin(a), t - (t - 0.009) * (k / 4) ** 1.6))
    out.append((-d / 2 + 0.004, 0.0))
    # this outline runs +Y -> -Y over the top: reverse so it is counter-clockwise in (y, z)
    out = out[::-1]
    ob = common.mesh_object(f"{n}_Mat", bv.soft_extrude(out, -w / 2, w / 2, ease=0.012, inset=0.006), col, oat, root)
    common.box_uv(ob, tile=0.25)
    return root, bc.parts_of(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
