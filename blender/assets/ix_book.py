"""Hardback book (235 x 160 x 32 mm): cloth-covered boards with a rounded spine, a cream page
block set 3 mm inside the boards. A throwable pickup (item "book", noise 0.6, doesn't shatter):
a lure that thuds where it lands. Lies flat, spine to -X; origin at the centre of its underside."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402

importlib.reload(ix_common)
common, materials = ix_common.common, ix_common.materials

NAME = "IX_Book"
P = dict(name=NAME, size=(0.235, 0.16, 0.032), cloth="M_Book_Cloth_Green", color=(0.03, 0.07, 0.05))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    root["interact"] = ix_common.pickup("book", "Book", throwable=True, noise=0.6, shatter=False)
    cloth = materials.fabric(p["cloth"], p["color"], roughness=0.85)
    pages = common.pbr_material("M_Book_Pages", (0.70, 0.66, 0.57), roughness=0.9)
    w, d, t = p["size"]
    b = 0.003
    for k, z in enumerate((b / 2, t - b / 2)):
        ob = common.mesh_object(f"{n}_Board{k}", common.box_bmesh((w, d, b)), col, cloth, root)
        ob.location = (0, 0, z)
        common.add_bevel(ob, 0.001, segments=1)
        common.box_uv(ob, 0.25)
    sp = common.mesh_object(f"{n}_Spine", ix_common.lathe_bmesh([(t / 2, -d / 2), (t / 2, d / 2)], 12), col, cloth,
                            root)
    sp.rotation_euler = (1.5708, 0, 0)
    sp.scale = (0.35, 1, 1)
    sp.location = (-w / 2 + 0.001, 0, t / 2)
    common.box_uv(sp, 0.25)
    blk = common.mesh_object(f"{n}_Pages", common.box_bmesh((w - 0.006, d - 0.006, t - 2 * b - 0.0004)), col, pages,
                             root)
    blk.location = (0.0, 0, t / 2)
    common.add_bevel(blk, 0.0015, segments=1)
    common.box_uv(blk, 0.25)
    return ix_common.finish(root)
