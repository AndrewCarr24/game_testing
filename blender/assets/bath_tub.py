"""Freestanding stone bathtub: a honed white stone oval with a soft rounded rim, an
inset bowl with a sloped backrest end and a recessed plinth, plus a floor-mounted
brass tub filler (standpipe, arched spout, two lever handles) at the head end.

The body is lofted from rings (a superellipse footprint, inset by a distance that
varies with height), so the wall has real thickness. Origin: centre of the footprint
on the floor. Long axis is X; the filler stands at +X; the front faces -Y.
"""
import importlib
import math
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common  # noqa: E402
import bath_common as bc  # noqa: E402

importlib.reload(common)
importlib.reload(bc)

NAME = "BathTub"

P = dict(
    name=NAME,
    length=1.78, width=0.84, height=0.58,
    expo=2.5,                  # superellipse exponent of the footprint (2 = ellipse)
    segs=72,
    # outer wall profile: (z, inset d metres from the outline)
    outer=[(0.0, 0.17), (0.012, 0.155), (0.05, 0.105), (0.12, 0.05), (0.26, 0.012), (0.40, 0.0),
           (0.50, 0.004), (0.55, 0.018), (0.572, 0.04), (0.58, 0.07)],
    # rim top and inner wall: down into the bowl
    inner=[(0.58, 0.092), (0.572, 0.108), (0.55, 0.12), (0.47, 0.147), (0.34, 0.20),
           (0.22, 0.262), (0.14, 0.31), (0.105, 0.35)],
    bowl_floor=0.095,
    head_shift=0.05,           # the bowl floor is pushed toward -X (sloped back end)
    filler_x=0.14,             # standpipe distance beyond the +X end
)


superellipse, loft = bc.superellipse, bc.loft


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    stone, brass, ceramic = bc.stone(), bc.brass(), bc.ceramic()

    A, B = p["length"] / 2, p["width"] / 2
    segs, expo = p["segs"], p["expo"]

    def ring(z, d, dx=0.0):
        pts = superellipse(max(A - d, 0.01), max(B - d, 0.01), expo, segs)
        return (z, [(x + dx, y) for x, y in pts])

    rings = [("pole", 0, 0, 0.0)]
    rings += [ring(z, d) for z, d in p["outer"]]
    # inner wall: bowl floor shifts toward -X as it descends (a reclined, sloped back)
    z_top = p["inner"][0][0]
    z_bot = p["inner"][-1][0]
    for z, d in p["inner"]:
        k = (z_top - z) / (z_top - z_bot)
        rings.append(ring(z, d, -p["head_shift"] * k * k))
    rings.append(("pole", -p["head_shift"], 0, p["bowl_floor"]))
    bm = loft(rings, segs)
    body = common.mesh_object(f"{n}_Body", bm, col, stone, root)
    for e in body.data.edges:
        e.use_edge_sharp = False
    # simple planar UVs (plain material, but keep a UV map for the lightmap path)
    common.box_uv(body, tile=1.0)

    # drain cover in the bowl floor
    dz = p["bowl_floor"]
    bc_ = bc.lathe([(0.0, dz + 0.0035), (0.026, dz + 0.0035), (0.028, dz + 0.001), (0.028, dz - 0.002), (0.0, dz - 0.002)], 24)
    drain = common.mesh_object(f"{n}_Drain", bc_, col, brass, root)
    drain.location = (-p["head_shift"], 0, 0.0)

    # overflow slot ring on the inner wall near the +X end (small brass disc)
    # ---- floor-mounted filler at the +X end -----------------------------------
    fx = A + p["filler_x"]
    foot = bc.lathe([(0.0, 0.0), (0.075, 0.0), (0.075, 0.012), (0.052, 0.016), (0.034, 0.022),
                     (0.020, 0.040), (0.0, 0.040)], 32)
    common.mesh_object(f"{n}_FillerFoot", foot, col, brass, root).location = (fx, 0, 0)
    top_z = 0.92
    pts = [(fx, 0, 0.035), (fx, 0, top_z - 0.20)]
    # arched spout: up, over the rim toward -X, down
    arc = []
    r = 0.16
    cx = fx - r
    for k in range(0, 13):
        a = math.pi * k / 12
        arc.append((cx + r * math.cos(a), 0, top_z - 0.20 + r * 0.55 * math.sin(a) + 0.0))
    pipe = [(fx, 0, 0.035), (fx, 0, top_z - 0.20 + 0.01)] + arc[1:]
    pipe.append((cx - r, 0, top_z - 0.20 - 0.07))
    # smoother: fillet corners
    pts = common.fillet_polyline(pipe, 0.05, segments=5, closed=False)
    common.tube_object(f"{n}_FillerPipe", pts, 0.0175, col, brass, root, closed=False, profile_res=4)
    # lever handles on either side of the standpipe
    for sgn, nm in ((-1, "L"), (1, "R")):
        hb = bmesh.new()
        bc.cylinder_between(hb, (fx, sgn * 0.02, 0.683), (fx, sgn * 0.060, 0.683), 0.011, 16)
        bc.cylinder_between(hb, (fx, sgn * 0.058, 0.683), (fx, sgn * 0.140, 0.700), 0.0065, 12)
        bc.cylinder_between(hb, (fx, sgn * 0.140, 0.700), (fx, sgn * 0.150, 0.702), 0.0095, 12)
        common.mesh_object(f"{n}_Lever_{nm}", hb, col, brass, root)
    # valve collar
    collar = bc.lathe([(0.0175, 0.64), (0.027, 0.64), (0.027, 0.725), (0.0175, 0.725)], 24, closed=True)
    common.mesh_object(f"{n}_FillerCollar", collar, col, brass, root).location = (fx, 0, 0)
    # a slim brass strip around the footprint base (plinth shadow line is in the stone)

    bc.merge(root, bc.by_material(root, brass), f"{n}_PipingBrass")
    return root, bc.parts_of(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
