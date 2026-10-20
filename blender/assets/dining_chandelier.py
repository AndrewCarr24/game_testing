"""Sculptural linear chandelier for the dining table: a bronze ribbon tube that
meanders along the ceiling, with 15 opal-glass globes of different sizes hanging
from fine bronze cables at different heights (a loose, floating wave).

Origin: the underside of the lowest globe (z = 0); the ceiling mount is at the asset's
top (see the reported height), so place it at z = ceiling - height.
Long axis along X. Units are metres.
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "DiningChandelier"

P = dict(
    name=NAME,
    length=4.6,
    count=15,
    wander=0.30,           # sideways meander of the ribbon (m)
    drop_min=0.85,         # shortest drop (ceiling to the top of the globe)
    drop_max=1.75,
    globe_r=(0.075, 0.135),
    emission=3.2,
    segs=12,
    rings=8,
)


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402  (react definitions, prompts/interactivity.md)

importlib.reload(ix_common)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    bronze = materials.bronze()
    opal = materials.emissive("M_Chandelier_Opal", (1.0, 0.86, 0.66), p["emission"])
    dark = materials.black_metal()

    L, cnt = p["length"], p["count"]

    def ph(i, k):  # deterministic pseudo-random in [0, 1)
        return (math.sin(i * 12.9898 + k * 78.233) * 43758.5453) % 1.0

    # --- globe layout: ceiling at z = 0 for now, drops negative
    globes = []
    for i in range(cnt):
        t = i / (cnt - 1)
        x = (t - 0.5) * L
        y = p["wander"] * math.sin(t * 2 * math.pi * 1.1 + 0.6)
        r = p["globe_r"][0] + (p["globe_r"][1] - p["globe_r"][0]) * ph(i, 1)
        wave = 0.5 + 0.5 * math.sin(i * 0.9 + 0.4)
        drop = p["drop_min"] + (p["drop_max"] - p["drop_min"]) * (0.6 * wave + 0.4 * ph(i, 2))
        globes.append((x, y, -drop - r, r))
    squash = 1.08
    lowest = min(z - r * squash for _, _, z, r in globes)
    top = -lowest                          # ceiling height above the lowest underside
    globes = [(x, y, z + top, r) for x, y, z, r in globes]

    # --- ceiling ribbon: a smooth Catmull-Rom tube through the drop points
    q = [Vector((x, y, top)) for x, y, _, _ in globes]
    q = [q[0] + Vector((-0.25, 0, 0))] + q + [q[-1] + Vector((0.25, 0, 0))]
    pts = []
    for i in range(1, len(q) - 2):
        p0, p1, p2, p3 = q[i - 1], q[i], q[i + 1], q[i + 2]
        for k in range(4):
            t = k / 4
            pts.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    pts.append(q[-2])
    common.tube_object(f"{n}_Ribbon", [tuple(v) for v in pts], 0.014, col, dark, root,
                       closed=False, profile_res=2)

    bm_cable, bm_cap, bm_glow = bmesh.new(), bmesh.new(), bmesh.new()
    cap_h = 0.035
    for x, y, gz, r in globes:
        bmesh.ops.create_uvsphere(bm_glow, u_segments=p["segs"], v_segments=p["rings"], radius=r,
                                  matrix=Matrix.Translation((x, y, gz)) @ Matrix.Diagonal((1, 1, squash, 1)))
        z_cap0 = gz + r * squash - 0.006
        bmesh.ops.create_cone(bm_cable, cap_ends=True, cap_tris=False, segments=6,
                              radius1=0.0035, radius2=0.0035, depth=top - (z_cap0 + cap_h),
                              matrix=Matrix.Translation((x, y, (top + z_cap0 + cap_h) / 2)))
        bmesh.ops.create_cone(bm_cap, cap_ends=True, cap_tris=False, segments=12,
                              radius1=r * 0.38, radius2=r * 0.26, depth=cap_h,
                              matrix=Matrix.Translation((x, y, z_cap0 + cap_h / 2)))
        bmesh.ops.create_cone(bm_cap, cap_ends=True, cap_tris=False, segments=10,
                              radius1=0.022, radius2=0.022, depth=0.012,
                              matrix=Matrix.Translation((x, y, top - 0.02)))
    common.mesh_object(f"{n}_Cables", bm_cable, col, bronze, root)
    common.mesh_object(f"{n}_Caps", bm_cap, col, bronze, root)
    common.mesh_object(f"{n}_Globes", bm_glow, col, opal, root)

    for ob in root.children_recursive:
        if ob.type == "MESH":
            common.box_uv(ob, 0.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    ix_common.tag_emissive(root)   # interactivity: glowing parts follow the room's light switch
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
