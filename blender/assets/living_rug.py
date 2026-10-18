"""Large flat-weave wool rug: a tonal field inside a slightly raised-edge border band,
both in woven fabric materials (shared weave normal map). Units are metres; origin is
the floor centre; the long side runs along X. Variants: living_rug_b, living_rug_den.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "LivingRug"

P = dict(
    name=NAME,
    size=(5.2, 3.8),
    border=0.16,
    gap=0.025,                       # fine line between field and border (border shows through)
    field_name="M_Fabric_RugOat", field=(0.40, 0.355, 0.285),
    border_name="M_Fabric_RugTaupe", border_c=(0.21, 0.175, 0.14),
    thickness=0.014,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    fm = materials.fabric(p["field_name"], p["field"], roughness=1.0)
    bm_ = materials.fabric(p["border_name"], p["border_c"], roughness=1.0)
    w, d = p["size"]
    t = p["thickness"]
    outer = common.mesh_object(f"{n}_Border", common.rounded_slab_bmesh(w, d, t, 0.03), col, bm_, root)
    outer.location = (0, 0, t / 2)
    common.add_bevel(outer, 0.004, segments=2)
    common.box_uv(outer, 0.25)
    b = p["border"] + p["gap"]
    inner = common.mesh_object(f"{n}_Field", common.rounded_slab_bmesh(w - 2 * b, d - 2 * b, t, 0.02), col, fm, root)
    inner.location = (0, 0, t / 2 + 0.003)
    common.add_bevel(inner, 0.003, segments=2)
    common.box_uv(inner, 0.25)
    # inner border band: a thin line of border colour between field and border band
    parts = [outer, inner]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
