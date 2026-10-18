"""Book-matched marble slab wall cladding (shared builder for bath_wall_*.py).

A run of full-height slabs (about 1.2 m wide, 3 cm thick, 4 mm joints) in pairs:
each pair is one block of marble opened like a book, so the veins mirror across the
pair's centre line; different pairs use different cuts of the stone. The whole wall
is one mesh (one draw call, one collider).

Origin: the wall face at floor level, centred on the run. The slabs stand in front of
the wall (toward -Y, the back of the asset is the wall at +Y); the run extends along X.
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

NAME = "BathSlabWall"

P = dict(
    name=NAME,
    tone="light",                   # "light" Calacatta-style or "dark" Marquina-style
    # intervals of cladding: (x0, x1, z0, z1) in metres along the wall
    runs=[(-4.85, 4.85, 0.0, 3.8)],
    slab_w=1.2,
    thickness=0.03,
    joint=0.004,
    tile=2.4,                       # metres of wall per texture tile
    cuts=[(0.0, 1), (0.37, -1), (0.71, 1), (0.18, -1)],   # per pair: v offset, v direction
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    mat = bc.marble_wall() if p["tone"] == "light" else bc.marble_dark()
    t, jt, tile = p["thickness"], p["joint"], p["tile"]

    k = 0                                         # slab counter across all runs (drives the pairing)
    for ri, (x0, x1, z0, z1) in enumerate(p["runs"]):
        cnt = max(1, math.ceil((x1 - x0) / p["slab_w"] - 1e-6))
        w = (x1 - x0) / cnt
        bm = bmesh.new()
        info = []
        for i in range(cnt):
            xs = x0 + i * w
            res = bmesh.ops.create_cube(bm, size=1.0)
            bmesh.ops.scale(bm, vec=(w - jt, t, z1 - z0), verts=res["verts"])
            bmesh.ops.translate(bm, vec=(xs + w / 2, -t / 2, (z0 + z1) / 2), verts=res["verts"])
            info.append((k, xs))
            k += 1
        # one mesh per run, so every run gets its own collider (a door gap stays open)
        ob = common.mesh_object(f"{n}_Slabs_{ri}", bm, col, mat, root, smooth=False)
        me = ob.data
        uv = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:                  # six quad faces per slab, in creation order
            kk, xs = info[poly.index // 6]
            pair, side = divmod(kk, 2)
            v0, vdir = p["cuts"][pair % len(p["cuts"])]
            for li in poly.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                if poly.normal.y < -0.9:
                    f = (co.x - xs) / w
                    u = (0.0 if side == 0 else 0.5) + 0.5 * f
                    v = v0 + vdir * (co.z - z0) / tile
                else:
                    u, v = co.x / tile, co.z / tile
                uv.data[li].uv = (u, v)
    return root, bc.parts_of(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
