"""Gallery sculpture: two interlocked, tilted bronze rings with a polished-steel
sphere, on a white-marble plinth. ~1.75 m tall. Origin: floor centre.
"""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import living_side_table  # noqa: E402
from lib import common, materials, textures  # noqa: E402

importlib.reload(living_side_table)
lathe = living_side_table.lathe

NAME = "LivingSculpture"

P = dict(name=NAME, plinth=(0.46, 0.46, 0.85), ring_r=0.30, tube_r=0.032)


def ring(n, name, col, mat, root, r, tube, centre, tilt_x, tilt_y, spin=0.0, segs=36):
    pts = []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        x, y, z = r * math.cos(a), r * math.sin(a), 0.0
        # tilt about x then y
        y, z = y * math.cos(tilt_x) - z * math.sin(tilt_x), y * math.sin(tilt_x) + z * math.cos(tilt_x)
        x, z = x * math.cos(tilt_y) + z * math.sin(tilt_y), -x * math.sin(tilt_y) + z * math.cos(tilt_y)
        pts.append((centre[0] + x, centre[1] + y, centre[2] + z))
    ob = common.tube_object(f"{n}_{name}", pts, tube, col, mat, root, closed=True, profile_res=4)
    common.box_uv(ob, 0.5)
    ob["low"] = min(pts, key=lambda q: q[2])
    return ob


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    marble = common.pbr_material("M_Marble_White", (0.8, 0.79, 0.77), roughness=0.12)
    common.set_base_color_map(marble, textures.load(textures.marble()))
    bronze = materials.bronze()
    steel = materials.steel()
    px, py, pz = p["plinth"]
    sg = 0.03     # the marble block sits on a recessed black shadow-gap base
    plinth = common.mesh_object(f"{n}_Plinth", common.box_bmesh((px, py, pz - sg)), col, marble, root, smooth=False)
    plinth.location = (0, 0, sg + (pz - sg) / 2)
    foot = common.mesh_object(f"{n}_PlinthBase", common.box_bmesh((px - 0.04, py - 0.04, sg)), col,
                              materials.black_metal(), root, smooth=False)
    foot.location = (0, 0, sg / 2)
    common.box_uv(foot, 0.5)
    common.add_bevel(plinth, 0.006, segments=2)
    common.box_uv(plinth, 1.0)
    r, t = p["ring_r"], p["tube_r"]
    zc = pz + r + 0.1
    ra = ring(n, "RingA", col, bronze, root, r, t, (0, 0, zc), math.radians(78), math.radians(18))
    rb = ring(n, "RingB", col, bronze, root, r * 0.9, t * 0.85, (0.05, 0, zc + 0.02), math.radians(20), math.radians(-72))
    # spokes from the hub sphere out to the low point of each ring: the rings are carried
    for k, rg in enumerate((ra, rb)):
        lo = rg["low"]
        common.tube_object(f"{n}_Spoke{k}", [(0.0, 0.0, zc), tuple(lo)], 0.008, col, bronze, root, closed=False,
                           profile_res=1)
        del rg["low"]
    # armature: a bronze mounting disc on the plinth and a slim rod up to the sphere,
    # which carries both rings
    mount = common.mesh_object(f"{n}_Mount", lathe([(0.0, pz), (0.07, pz), (0.07, pz + 0.008), (0.064, pz + 0.014),
                                                    (0.012, pz + 0.018), (0.012, zc), (0.0, zc)], 20, closed=False),
                               col, bronze, root)
    common.box_uv(mount, 0.5)
    ball = common.mesh_object(f"{n}_Sphere", lathe([(0, -0.07), (0.05, -0.05), (0.07, 0), (0.05, 0.05), (0, 0.07)], 24),
                              col, steel, root)
    ball.location = (0.0, 0.0, zc)
    common.box_uv(ball, 0.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
