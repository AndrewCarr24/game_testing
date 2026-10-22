"""The bath hall's pool water (the bathhouse; viewer/water_fx.js): the surface, 8 cm under the floor
(fx "water": the room's reflections with drifting ripples, see-through looking down) and, on the
pool floor, the light the moving surface throws (fx "caustics"). The pool is 11.2 x 6.0 m inside
its walls (bathhouse_plan.POOL), 1.32 m deep below the surface. Origin: the pool's centre at the
hall's floor level."""
import importlib
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ph_common as pc  # noqa: E402

importlib.reload(pc)
common = pc.common

NAME = "PHPoolWater"
P = dict(name=NAME, size=(11.2, 6.0), water_z=-0.08, floor_z=-1.4, cell=1.4, tile=1.0)


def surface(n, w, d, z, mat, col, parent, cell=1.4, tile=1.0, name="NoCollide_Water"):
    """The water plane, a grid (the water_fx ripples want UVs in metres)."""
    nx, ny = max(1, round(w / cell)), max(1, round(d / cell))
    bm = bmesh.new()
    vs = {(i, j): bm.verts.new((-w / 2 + w * i / nx, -d / 2 + d * j / ny, z)) for i in range(nx + 1) for j in range(ny + 1)}
    for i in range(nx):
        for j in range(ny):
            bm.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops:
            lp[uv].uv = (lp.vert.co.x / tile, lp.vert.co.y / tile)
    ob = common.mesh_object(f"{n}_{name}", bm, col, mat, parent, smooth=False)
    ob["fx"] = "water"
    ob["tile"] = 1.6
    return pc.no_bake_light(ob)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = pc.start(n)
    W, D = p["size"]
    surface(n, W, D, p["water_z"], pc.water(), col, root, p["cell"], p["tile"])
    pc.no_bake_light(pc.card(f"{n}_NoCollide_Caustics", W - 0.1, D - 0.1, pc.fx_material(), col, root,
                             at=(0, 0, p["floor_z"] + 0.012), facing="+z", fx="caustics",
                             aspect=(W - 0.1) / (D - 0.1), scale=1.1, strength=0.16, color=[0.8, 0.95, 0.85], stretch=1.0))
    return pc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
