"""Low-pile charcoal wool rug. Origin is the floor centre."""
import importlib
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, textures  # noqa: E402

importlib.reload(common)
importlib.reload(textures)

NAME = "Rug"

P = dict(name=NAME, size=(3.0, 2.2), thickness=0.012, corner=0.03)


def rug_bmesh(w, d, t, corner, binding=0.03, roll=0.0025, segments=8):
    """A rug lying on the floor (z = 0 underneath, not modelled): a flat field inside a
    bound edge `binding` wide that rolls up `roll` above the field and down round the
    outer edge to the floor, the way a serged or taped border sits."""
    prof = [(binding, t), (binding * 0.8, t + roll * 0.6), (binding * 0.45, t + roll), (binding * 0.15, t + roll * 0.7),
            (0.0015, t * 0.6), (0.0, 0.0)]
    bm = bmesh.new()
    rings = []
    for inset, z in prof:
        hw, hd = w / 2 - inset, d / 2 - inset
        pts = common.fillet_polyline([(-hw, -hd, 0), (hw, -hd, 0), (hw, hd, 0), (-hw, hd, 0)],
                                     max(corner - inset, 0.004), segments=segments, closed=True)
        rings.append([bm.verts.new((q.x, q.y, z)) for q in pts])
    m = len(rings[0])
    for a, c in zip(rings[:-1], rings[1:]):
        for i in range(m):
            j = (i + 1) % m
            bm.faces.new((a[i], a[j], c[j], c[i]))
    bm.faces.new(rings[0])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:            # an open shell: make sure everything faces up and out
        if f.normal.z < -0.01:
            f.normal_flip()
    return bm


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    wool = common.pbr_material("M_Wool_Charcoal", (0.06, 0.06, 0.065), roughness=0.95)
    common.set_base_color_map(wool, textures.load(textures.wool()))

    w, d = p["size"]
    rug = common.mesh_object(f"{n}_Body", rug_bmesh(w, d, p["thickness"], max(p["corner"], 0.03)), col, wool, root)
    common.box_uv(rug, tile=0.5)

    parts = [rug]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
