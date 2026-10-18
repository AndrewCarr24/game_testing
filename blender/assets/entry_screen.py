"""Slatted walnut privacy screen: a free-standing panel of vertical walnut fins between a
heavy walnut head beam and a bronze-capped black plinth. 1.5 m wide, 0.09 m deep,
2.6 m tall, with a see-through gap between the fins.

Origin: floor centre. The long face looks toward -Y. Units are metres.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "EntryScreen"

P = dict(
    name=NAME,
    width=1.5, depth=0.09, height=2.6,
    fin_w=0.045, fin_gap=0.028,
    plinth_h=0.07, beam_h=0.10,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    walnut = materials.walnut()
    bronze = materials.bronze()
    black = materials.black_metal()
    W, D, H = p["width"], p["depth"], p["height"]
    ph, bh = p["plinth_h"], p["beam_h"]

    def box(name, size, loc, mat, bevel=0.002, wood=False):
        ob = common.mesh_object(f"{n}_{name}", common.box_bmesh(size), col, mat, root, smooth=False)
        ob.location = loc
        if bevel:
            common.add_bevel(ob, bevel, segments=2)
        if wood:
            common.box_uv(ob, tile=0.5)
        return ob

    box("Plinth", (W, D, ph - 0.012), (0, 0, (ph - 0.012) / 2), black, bevel=0.001)
    box("PlinthCap", (W + 0.01, D + 0.01, 0.012), (0, 0, ph - 0.006), bronze, bevel=0.001)
    box("Beam", (W + 0.02, D + 0.03, bh), (0, 0, H - bh / 2), walnut, bevel=0.004, wood=True)
    box("Rail", (W - 0.02, D * 0.45, 0.03), (0, 0, ph + 0.015), walnut, bevel=0.001, wood=True)
    pitch = p["fin_w"] + p["fin_gap"]
    count = int((W - 0.02) // pitch)
    x0 = -(count - 1) * pitch / 2
    fin_h = H - bh - ph - 0.03
    for i in range(count):
        ob = box(f"Fin_{i:02d}", (p["fin_w"], D * 0.85, fin_h), (x0 + i * pitch, 0, ph + 0.03 + fin_h / 2), walnut,
                 bevel=0.003, wood=True)
        # vary the grain between fins
        uv = ob.data.uv_layers["UVMap"]
        for d in uv.data:
            d.uv = (d.uv[0] + 0.137 * i, d.uv[1] + 0.071 * i)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
