"""Motorised roller blinds for one glass wall (a run of window bays): per bay a slim black
aluminium cassette tucked into the window reveal right under the ceiling, a fabric blind
(linen greige or charcoal blackout) and a weighted aluminium bottom rail.

Interactivity (prompts/interactivity.md), signal "blinds" (the level renames it per room,
{"signal": "blinds_<room>"}); on = blinds down:
  <n>_Fabric_NoCollide  one mesh for every bay's fabric, its origin at the roller inside the
                        cassette. Authored rolled up: squashed to a 3 cm sliver inside the
                        cassettes (object scale), so the bake and the room above never see a
                        4-8 m panel. react: scale along y to full length; block_sight; collide (solid when down).
  <n>_Rail_NoCollide    the bottom rails (one mesh): react slide down by the same travel,
                        same duration, so they stay on the fabric's bottom edge.
The cassettes are static (batched with the room's other black metal).

Local frame: origin on the floor at the centre of the run, y = 0 on the glass line, the room
on the -Y side (front faces -Y, like every asset). Window bays come from house.glazing:
round(width / 1.5) equal bays separated by 50 mm mullions; the reveal is the 0.15 m wall lining."""
import importlib
import os
import sys

import bmesh
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "IX_Blind"

P = dict(
    name=NAME,
    bays=8,
    bay_w=1.5,
    top=4.2,                  # opening head = ceiling, from the room's floor
    fabric="linen",           # "linen" (greige, light-filtering) | "blackout" (charcoal)
    cassette=(0.075, 0.092),  # depth (y), height (z)
    cassette_y=-0.07,         # its back face, just in front of the mullions (+-0.06)
    fabric_y=-0.104,
    rail=(0.014, 0.022),      # depth, height
    floor_gap=0.015,          # rail bottom above the floor when fully down
    speed=1.2,                # m/s
    signal="blinds",
    stowed=1,                 # 0 = build it lowered (previews only)
)

STOW_H = 0.03                 # rolled-up fabric left hanging inside the cassette


def fabric_mat(kind):
    if kind == "blackout":
        return materials.fabric("M_Blind_Blackout", (0.045, 0.044, 0.046), roughness=0.92)
    return materials.fabric("M_Blind_Linen", (0.36, 0.33, 0.28), roughness=0.95)


def boxes_bmesh(boxes):
    """One bmesh of axis-aligned boxes [(centre, size)]."""
    bm = bmesh.new()
    for c, s in boxes:
        m = Matrix.Translation(c) @ Matrix.Diagonal((*s, 1.0))
        bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    return bm


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    metal = materials.black_metal()
    cloth = fabric_mat(p["fabric"])

    nb, bw = p["bays"], p["bay_w"]
    xs = [(-nb / 2 + i + 0.5) * bw for i in range(nb)]
    cd, ch = p["cassette"]
    top = p["top"]
    cb = top - 0.003 - ch                     # cassette bottom
    zp = cb + STOW_H                          # roller line (fabric origin)
    rd, rh = p["rail"]
    z_bottom = p["floor_gap"] + rh            # fabric bottom edge, fully down
    hd = zp - z_bottom                        # fabric length, fully down
    travel = hd - STOW_H
    duration = round(min(8.0, max(3.0, travel / p["speed"])), 1)

    # cassettes: one per bay, 4 mm apart over the mullions
    yc = p["cassette_y"] - cd / 2
    cas = common.mesh_object(f"{n}_Cassette_NoCollide",
                             boxes_bmesh([((x, yc, cb + ch / 2), (bw - 0.004, cd, ch)) for x in xs]),
                             col, metal, root, smooth=False)
    common.add_bevel(cas, 0.003, segments=1)

    # fabric: a panel per bay hanging from the roller line, 30 mm narrower than the bay
    bm = bmesh.new()
    fw = bw - 0.03
    for x in xs:
        v = [bm.verts.new(co) for co in ((x - fw / 2, 0, -hd), (x + fw / 2, 0, -hd), (x + fw / 2, 0, 0), (x - fw / 2, 0, 0))]
        bm.faces.new(v)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:                         # face the room (-Y)
        if f.normal.y > 0:
            f.normal_flip()
    fab = common.mesh_object(f"{n}_Fabric_NoCollide", bm, col, cloth, root, smooth=False)
    common.box_uv(fab, tile=0.25)
    fab.location = (0, p["fabric_y"], zp)
    s0 = STOW_H / hd
    fab["react"] = {"signal": p["signal"], "on": {"scale": {"axis": "y", "to": round(1.0 / s0, 4)}},
                    "duration": duration, "block_sight": True,
                    "collide": True}   # (a lowered blind is solid: no walking through it, or out a glass door behind it)

    # bottom rails: hang just under the cassettes while rolled up
    rail = common.mesh_object(f"{n}_Rail_NoCollide",
                              boxes_bmesh([((x, 0, -rh / 2), (fw + 0.004, rd, rh)) for x in xs]),
                              col, metal, root, smooth=False)
    common.add_bevel(rail, 0.004, segments=1)
    rail.location = (0, p["fabric_y"], cb)
    rail["react"] = {"signal": p["signal"], "on": {"slide": {"axis": "y", "distance": -round(travel, 4)}},
                     "duration": duration}

    if p["stowed"]:
        fab.scale = (1, 1, s0)
    else:
        rail.location.z -= travel

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
