"""Entry bench: a long, low cognac-leather cushion (piped, softly crowned) on two
solid walnut slab ends joined by a bronze rail, with a black recessed foot. 2.3 m
long so two people can sit and pull on shoes.

Origin: floor centre. Front faces -Y (the seat's open side). Units are metres.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "EntryBench"

P = dict(
    name=NAME,
    width=2.3,
    depth=0.46,
    height=0.47,
    cushion_t=0.095,
    crown=0.014,
    cushion_edge=0.028,
    piping_r=0.0042,
    slab_t=0.07,            # walnut end slabs
    slab_inset=0.12,
    slab_depth=0.36,
    foot_h=0.025,
    rail=(0.02, 0.05),      # bronze flat rail section (thickness, height)
    leather=(0.23, 0.075, 0.025),
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    walnut = materials.walnut()
    bronze = materials.bronze()
    black = materials.black_metal()
    leather = common.pbr_material("M_Leather_Cognac", p["leather"], roughness=0.62)
    common.set_normal_map(leather, textures.load(textures.leather_normal(), non_color=True), 0.6)

    W, D, H = p["width"], p["depth"], p["height"]
    ct, crown = p["cushion_t"], p["crown"]
    cush_top_box = H - crown * 0.75 - 0.002
    cush_bot = cush_top_box - ct
    wood = []

    # end slabs
    st, sd, sin_, fh = p["slab_t"], p["slab_depth"], p["slab_inset"], p["foot_h"]
    sh = cush_bot - 0.004 - fh
    for side, sx in (("L", -1), ("R", 1)):
        x = sx * (W / 2 - sin_ - st / 2)
        slab = common.mesh_object(f"{n}_End_{side}", common.box_bmesh((st, sd, sh)), col, walnut, root, smooth=False)
        slab.location = (x, 0, fh + sh / 2)
        common.add_bevel(slab, 0.004, segments=2)
        foot = common.mesh_object(f"{n}_Foot_{side}", common.box_bmesh((st - 0.012, sd - 0.03, fh)), col, black, root,
                                  smooth=False)
        foot.location = (x, 0, fh / 2)
        wood.append(slab)

    # bronze rail between the slabs, low at the back
    rt, rh = p["rail"]
    span = W - 2 * sin_ - 2 * st + 0.01
    rail = common.mesh_object(f"{n}_Rail", common.box_bmesh((span, rt, rh)), col, bronze, root, smooth=False)
    rail.location = (0, sd / 2 - 0.05, cush_bot - 0.004 - rh / 2 - 0.01)
    common.add_bevel(rail, 0.0015, segments=2)
    # hidden black deck
    deck = common.mesh_object(f"{n}_Deck", common.box_bmesh((W - 0.12, D - 0.06, 0.012)), col, black, root, smooth=False)
    deck.location = (0, 0, cush_bot - 0.004 - 0.006)

    # cushion + piping
    size = (W - 0.008, D - 0.008, ct)
    e = p["cushion_edge"]
    cush = common.mesh_object(
        f"{n}_Cushion",
        common.cushion_bmesh(size, edge=e, crown={"+z": crown, "-z": 0.0, "+x": 0.004, "-x": 0.004, "+y": 0.004, "-y": 0.004}),
        col, leather, root)
    cush.location = (0, 0, cush_bot + ct / 2)
    common.add_subsurf(cush)
    leather_parts = [cush]
    for i, pts in enumerate(common.piping_loop(size, "z", e / 6, e * 0.9)):
        pipe = common.tube_object(f"{n}_Cushion_Piping{i}", pts, p["piping_r"], col, leather, root, closed=True, profile_res=2)
        pipe.location = cush.location
        leather_parts.append(pipe)

    for ob in wood:
        common.box_uv(ob, tile=0.5)
    for ob in leather_parts:
        common.box_uv(ob, tile=0.2)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
