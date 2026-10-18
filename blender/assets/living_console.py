"""Console / credenza: a walnut top slab and lower shelf between two bronze slab
end-panels, with a thin black drawer reveal and bronze pulls. Faces -Y (front); back at
+Y; origin is the floor centre. Variants via overrides (width, top material).
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "LivingConsole"

P = dict(name=NAME, width=2.3, depth=0.42, height=0.82, top_t=0.045, shelf_z=0.24, shelf_t=0.03,
         panel_t=0.022, inset=0.10, wood="walnut", drawers=True)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    wood = materials.walnut() if p["wood"] == "walnut" else materials.smoked_oak()
    bronze = materials.bronze()
    black = materials.black_metal()
    w, d, h, tt = p["width"], p["depth"], p["height"], p["top_t"]

    def box(name, mat, size, loc, bevel=0.003, uv=0.5):
        ob = common.mesh_object(f"{n}_{name}", common.box_bmesh(size), col, mat, root, smooth=False)
        ob.location = loc
        if bevel:
            common.add_bevel(ob, bevel, segments=2)
        common.box_uv(ob, uv)
        return ob

    box("Top", wood, (w, d, tt), (0, 0, h - tt / 2), 0.005)
    pt = p["panel_t"]
    for s, sx in (("L", -1), ("R", 1)):
        box(f"Panel{s}", bronze, (pt, d - 0.06, h - tt), (sx * (w / 2 - p["inset"]), 0, (h - tt) / 2), 0.003)
    sw = w - 2 * p["inset"] - pt
    box("Shelf", wood, (sw, d - 0.06, p["shelf_t"]), (0, 0, p["shelf_z"]), 0.003)
    if p["drawers"]:
        # a drawer bank under the top: a recessed black reveal + three pulls
        dh = 0.17
        box("DrawerFace", wood, (sw - 0.02, 0.02, dh), (0, -d / 2 + 0.05, h - tt - dh / 2 - 0.01), 0.004)
        box("DrawerBack", black, (sw, d - 0.1, dh + 0.02), (0, 0.02, h - tt - dh / 2 - 0.01), 0.0, uv=1.0)
        n_p = 3
        for i in range(n_p):
            x = (-sw / 2 + sw * (i + 0.5) / n_p)
            box(f"Pull{i}", bronze, (0.22, 0.014, 0.014), (x, -d / 2 + 0.05 - 0.017, h - tt - 0.05), 0.004)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
