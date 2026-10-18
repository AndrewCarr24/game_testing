"""One limestone stepping slab (1.2 x 0.6 m) set flush in the lawn; UVs cover a single 1.0 x 0.5
slab of the limestone texture so it reads as a cut paver. Origin: slab centre at lawn level."""
import importlib
import os
import sys

import bmesh  # noqa: F401

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cabana_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common

NAME = "CabanaSlab"

P = dict(name=NAME, size=(1.2, 0.6), height=0.04)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = cc.start(n)
    m = cc.M()
    W, D = p["size"]
    ob = cc.box(f"{n}_Slab", (-W / 2, -D / 2, 0.0), (W / 2, D / 2, p["height"]), m["stone"], col, root, drop=("-z",))
    me = ob.data
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = ((co.x / W + 0.5) * 0.46 + 0.02, (co.y / D + 0.5) * 0.21 + 0.02) if poly.normal.z > 0.5 else (0.02, 0.02)
    return cc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
