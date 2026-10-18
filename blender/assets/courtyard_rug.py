"""Outdoor flat-weave rug for the courtyard lounge: a sand body with a darker woven
border band (two thin slabs, weave normal map from the shared fabric texture).
Origin: floor centre, top at 1.4 cm. Units are metres."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import courtyard_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common
materials = cc.materials

NAME = "CourtyardRug"

P = dict(
    name=NAME,
    size=(3.7, 4.7),
    border=0.22,
    t=0.010,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    edge = materials.fabric("M_Fabric_Outdoor_Jute_Dark", (0.17, 0.14, 0.095), roughness=0.95)
    body = materials.fabric("M_Fabric_Outdoor_Jute", (0.33, 0.28, 0.19), roughness=0.95)
    w, d = p["size"]
    t = p["t"]
    cc.rbox(f"{n}_Border", (w, d, t), (0, 0, t / 2), edge, col, root, bevel=0.003, uv_tile=0.25, seg=1)
    b = p["border"]
    cc.rbox(f"{n}_Body", (w - 2 * b, d - 2 * b, t * 0.5), (0, 0, t + t * 0.25 - 0.0005), body, col, root, bevel=0.002,
            uv_tile=0.25, seg=1)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
