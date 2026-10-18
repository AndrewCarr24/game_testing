"""Dining sideboard: a long, low smoked-oak credenza with four fluted (ribbed) doors,
a honed white-marble top, slim bronze pulls and a recessed black plinth.

Units are metres. Faces -Y (doors on the -Y side, the back goes against a wall),
origin at the floor centre. Length along X.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import bmesh  # noqa: E402
from lib import common, materials, textures  # noqa: E402
from mathutils import Matrix  # noqa: E402

importlib.reload(common)
importlib.reload(materials)
importlib.reload(textures)

NAME = "DiningSideboard"

P = dict(
    name=NAME,
    length=2.5,
    depth=0.52,
    height=0.84,
    plinth_h=0.10,
    plinth_inset=0.045,
    top_t=0.03,
    top_overhang=0.012,
    doors=4,
    gap=0.004,
    rib_w=0.020,
    rib_gap=0.007,
    door_t=0.022,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    oak = materials.smoked_oak()
    bronze = materials.bronze()
    dark = materials.black_metal()
    marble = common.pbr_material("M_Marble_White", (0.8, 0.79, 0.77), roughness=0.3)
    common.set_base_color_map(marble, textures.load(textures.marble()))

    L, D, H = p["length"], p["depth"], p["height"]
    ph, T = p["plinth_h"], p["top_t"]
    inset = p["plinth_inset"]

    plinth = common.mesh_object(f"{n}_Plinth", common.box_bmesh((L - 2 * inset, D - 2 * inset, ph)),
                                col, dark, root)
    plinth.location = (0, 0, ph / 2)
    common.box_uv(plinth, 0.5)

    body_h = H - T - ph
    body_d = D - 0.03          # leaves room for the doors on the front
    carcass = common.mesh_object(f"{n}_Carcass", common.box_bmesh((L - 0.02, body_d, body_h)),
                                 col, oak, root)
    y_back = D / 2
    carcass.location = (0, y_back - body_d / 2, ph + body_h / 2)
    common.add_bevel(carcass, 0.005, 2)
    common.box_uv(carcass, 0.5)

    top = common.mesh_object(f"{n}_Top",
                             common.box_bmesh((L + 2 * p["top_overhang"], D + p["top_overhang"], T)),
                             col, marble, root)
    top.location = (0, p["top_overhang"] / 2 * 0 , H - T / 2)
    common.add_bevel(top, 0.004, 2)
    common.box_uv(top, 1.0)

    # --- fluted doors: a backing panel and a row of vertical ribs per door
    nd = p["doors"]
    inner = L - 0.02
    dw = (inner - (nd + 1) * p["gap"]) / nd
    dh = body_h - 2 * p["gap"]
    dz0 = ph + p["gap"]
    front_y = y_back - body_d - p["door_t"] / 2 + 0.002   # door backing centre
    rib_d = 0.014
    pull_bm = bmesh.new()
    backs, ribs = bmesh.new(), bmesh.new()
    for i in range(nd):
        cx = -inner / 2 + p["gap"] + dw / 2 + i * (dw + p["gap"])
        bmesh.ops.create_cube(backs, size=1.0, matrix=Matrix.Translation((cx, front_y, dz0 + dh / 2)) @
                              Matrix.Diagonal((dw, p["door_t"], dh, 1)))
        pitch = p["rib_w"] + p["rib_gap"]
        k = int((dw - 0.02) // pitch)
        x0 = cx - (k - 1) * pitch / 2
        for j in range(k):
            bmesh.ops.create_cube(ribs, size=1.0,
                                  matrix=Matrix.Translation((x0 + j * pitch, front_y - p["door_t"] / 2 - rib_d / 2 + 0.002,
                                                             dz0 + dh / 2)) @
                                  Matrix.Diagonal((p["rib_w"], rib_d, dh - 0.03, 1)))
        # slim vertical bronze pull on the inside edge of each door pair
        side = 1 if i % 2 == 0 else -1
        px = cx + side * (dw / 2 - 0.035)
        bmesh.ops.create_cone(pull_bm, cap_ends=True, cap_tris=False, segments=8, radius1=0.008, radius2=0.008,
                              depth=0.42,
                              matrix=Matrix.Translation((px, front_y - p["door_t"] / 2 - rib_d - 0.022, dz0 + dh * 0.55)))
        for dz in (-0.19, 0.19):
            bmesh.ops.create_cone(pull_bm, cap_ends=True, cap_tris=False, segments=6, radius1=0.004, radius2=0.004,
                                  depth=0.024,
                                  matrix=Matrix.Translation((px, front_y - p["door_t"] / 2 - rib_d - 0.008, dz0 + dh * 0.55 + dz)) @
                                  Matrix.Rotation(1.5708, 4, "X"))
    backs_ob = common.mesh_object(f"{n}_DoorPanels", backs, col, oak, root, smooth=False)
    ribs_ob = common.mesh_object(f"{n}_Ribs", ribs, col, oak, root, smooth=False)
    pulls = common.mesh_object(f"{n}_Pulls", pull_bm, col, bronze, root)
    for ob in (backs_ob, ribs_ob, pulls):
        common.box_uv(ob, 0.5)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
