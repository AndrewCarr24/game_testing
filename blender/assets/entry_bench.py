"""Entry bench: two long, low cognac-leather cushions (piped top and bottom, softly
crowned, pressed into each other at the middle) on a walnut platform with an eased
edge, carried by two solid walnut slab ends joined by a bronze rail, each end on a
black recessed foot. 2.3 m long so two people can sit and pull on shoes.

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
    cushion_t=0.072,
    cushions=2,
    cushion_gap=0.004,
    platform_t=0.026,       # walnut platform under the cushions (its edge shows below the leather)
    platform_inset=0.008,
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


def drop_underside(ob, z_cut):
    """Apply the modifiers and delete the faces lying flat on the platform (never seen)."""
    import bmesh
    import bpy
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear()
    bm = bmesh.new()
    bm.from_mesh(me)
    gone = [f for f in bm.faces if f.normal.z < -0.9 and max(v.co.z for v in f.verts) < z_cut]
    bmesh.ops.delete(bm, geom=gone, context="FACES")
    old = ob.data
    name = old.name
    bm.to_mesh(me)
    bm.free()
    ob.data = me
    bpy.data.meshes.remove(old)
    me.name = name


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
    pt, pin = p["platform_t"], p["platform_inset"]
    plat_bot = cush_bot - pt
    wood = []

    # walnut platform: the cushions sit on it, its eased edge shows as a dark line under them
    plat = common.mesh_object(f"{n}_Deck", common.box_bmesh((W - 2 * pin, D - 2 * pin, pt)), col, walnut, root,
                              smooth=False)
    plat.location = (0, 0, plat_bot + pt / 2)
    common.add_bevel(plat, 0.005, segments=2)
    wood.append(plat)

    # end slabs, tenoned into the platform's underside
    st, sd, sin_, fh = p["slab_t"], p["slab_depth"], p["slab_inset"], p["foot_h"]
    sh = plat_bot - fh + 0.002
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
    rail.location = (0, sd / 2 - 0.05, plat_bot - rh / 2 - 0.035)
    common.add_bevel(rail, 0.0015, segments=2)

    # cushions + piping (two, end to end, crowned sides pressing into each other)
    e = p["cushion_edge"]
    k = p["cushions"]
    cw = (W - 0.008 - (k - 1) * p["cushion_gap"]) / k
    leather_parts = []
    for i in range(k):
        x = -W / 2 + 0.004 + cw / 2 + i * (cw + p["cushion_gap"])
        size = (cw, D - 0.008, ct)
        cush = common.mesh_object(
            f"{n}_Cushion{'' if i == 0 else i}",
            common.cushion_bmesh(size, cuts=4, edge=e,
                                 crown={"+z": crown, "-z": 0.0, "+x": 0.006, "-x": 0.006, "+y": 0.004, "-y": 0.004}),
            col, leather, root)
        cush.location = (x, 0, cush_bot + ct / 2)
        common.add_subsurf(cush)
        drop_underside(cush, -ct / 2 + 0.002)
        leather_parts.append(cush)
        for j, pts in enumerate(common.piping_loop(size, "z", e / 6, e * 0.9)):
            pipe = common.tube_object(f"{n}_Cushion{'' if i == 0 else i}_Piping{j}", pts, p["piping_r"], col, leather,
                                      root, closed=True, profile_res=1)
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
