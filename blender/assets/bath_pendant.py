"""Sculptural pendant: a brass ceiling canopy and a cluster of five alabaster globes
hung on fine brass rods at staggered heights.

Origin: the ceiling attachment point (the canopy's top face). Place it with z = ceiling
height; it hangs down to about 1.9 m below. The front faces -Y (symmetric).
"""
import importlib
import math
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import bath_common as bc  # noqa: E402

importlib.reload(common)
importlib.reload(bc)

NAME = "BathPendant"

# (dx, dy, drop to the globe centre, radius)
GLOBES = [(0.00, 0.00, 1.95, 0.135), (0.30, 0.10, 1.55, 0.105), (-0.26, 0.16, 1.30, 0.12),
          (0.10, -0.30, 1.10, 0.095), (-0.18, -0.20, 1.75, 0.10)]

P = dict(name=NAME, emission=3.0, segs=32)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    brass = bc.brass()
    glow = materials.emissive("M_Bath_Alabaster", (1.0, 0.84, 0.62), 2.6)

    canopy = bc.lathe([(0.0, 0.0), (0.16, 0.0), (0.16, -0.012), (0.12, -0.03), (0.0, -0.03)], 40)
    common.mesh_object(f"{n}_Canopy", canopy, col, brass, root)
    rods = bmesh.new()
    for dx, dy, drop, r in GLOBES:
        bc.cylinder_between(rods, (dx * 0.4, dy * 0.4, -0.03), (dx, dy, -drop + r), 0.003, 8)
    common.mesh_object(f"{n}_PipingRods", rods, col, brass, root)
    for i, (dx, dy, drop, r) in enumerate(GLOBES):
        prof = [(0.0, -r)]
        for k in range(1, 12):
            a = -math.pi / 2 + math.pi * k / 12
            prof.append((r * math.cos(a), r * math.sin(a)))
        prof.append((0.0, r))
        g = common.mesh_object(f"{n}_Globe_{i}", bc.lathe(prof, p["segs"]), col, glow, root)
        g.location = (dx, dy, -drop)
        cap = bc.lathe([(0.0, 0.0), (0.02, 0.0), (0.02, 0.012), (0.0, 0.012)], 16)
        c = common.mesh_object(f"{n}_Cap_{i}", cap, col, brass, root)
        c.location = (dx, dy, -drop + r - 0.004)
    bc.merge(root, bc.children(root, "_Globe_"), f"{n}_PipingGlobes")
    bc.merge(root, bc.by_material(root, brass), f"{n}_PipingBrass")
    return root, bc.parts_of(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
