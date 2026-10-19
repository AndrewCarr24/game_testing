"""Large flat-weave wool rug: a tonal field inside a slightly raised-edge border band,
both in woven fabric materials (shared weave normal map). Units are metres; origin is
the floor centre; the long side runs along X. Variants: living_rug_b, living_rug_den.
"""
import importlib
import os
import sys

import bmesh

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


def rug_slab(w, d, t, corner, ease=0.003, segs=3):
    """Low-cost rug slab: a rounded-rectangle top with an eased (chamfered) edge and
    the side walls; no underside (it lies on the floor)."""
    hw, hd = w / 2, d / 2
    out = common.fillet_polyline([(-hw, -hd, 0), (hw, -hd, 0), (hw, hd, 0), (-hw, hd, 0)], corner, segments=segs)
    inn = common.fillet_polyline([(-hw + ease, -hd + ease, 0), (hw - ease, -hd + ease, 0), (hw - ease, hd - ease, 0),
                                  (-hw + ease, hd - ease, 0)], max(corner - ease, 0.001), segments=segs)
    bm = bmesh.new()
    rows = [[bm.verts.new((p.x, p.y, z)) for p in ring] for ring, z in ((out, -t / 2), (out, t / 2 - ease), (inn, t / 2))]
    n = len(out)
    for a, b in ((0, 1), (1, 2)):
        for k in range(n):
            j = (k + 1) % n
            bm.faces.new((rows[a][k], rows[a][j], rows[b][j], rows[b][k]))
    bm.faces.new(rows[2])
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for e in bm.edges:   # crisp where the eased edge meets the flat top
        if all(abs(v.co.z - t / 2) < 1e-6 for v in e.verts):
            e.smooth = False
    return bm


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    fm = materials.fabric(p["field_name"], p["field"], roughness=1.0)
    bm_ = materials.fabric(p["border_name"], p["border_c"], roughness=1.0)
    w, d = p["size"]
    t = p["thickness"]
    outer = common.mesh_object(f"{n}_Border", rug_slab(w, d, t, 0.03, 0.004), col, bm_, root)
    outer.location = (0, 0, t / 2)
    common.box_uv(outer, 0.25)
    b = p["border"] + p["gap"]
    inner = common.mesh_object(f"{n}_Field", rug_slab(w - 2 * b, d - 2 * b, t, 0.02, 0.003), col, fm, root)
    inner.location = (0, 0, t / 2 + 0.003)
    common.box_uv(inner, 0.25)
    # inner border band: a thin line of border colour between field and border band
    parts = [outer, inner]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
