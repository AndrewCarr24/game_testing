"""The steam room's doors (the bathhouse): a leaf of thick frosted glass in a slim dark bronze frame,
a bronze bar pull on both faces. Like door.py: origin at the bottom centre of the opening on the
wall's centre plane; the room side is +Y; it swings 90 degrees into the room about a hinge on the
-X jamb (the hinge empty carries the `rotate` interact). Opening 1.1 x 2.4 m."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ph_common as pc  # noqa: E402

importlib.reload(pc)
common = pc.common
materials = pc.materials

NAME = "PHDoorSteam"
P = dict(name=NAME, opening=(1.1, 2.4), gap=0.004, floor_gap=0.008, leaf_t=0.04, frame=0.045)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = pc.start(n)
    bronze = pc.dark_bronze()
    frosted = common.pbr_material("M_PH_Frosted", (0.55, 0.6, 0.6), roughness=0.45)
    materials._alpha_blend(frosted, 0.72)
    w, h = p["opening"]
    g, t, f = p["gap"], p["leaf_t"], p["frame"]
    sw, sh = w - 2 * g, h - p["floor_gap"] - g
    hinge = common.empty(f"{n}_Hinge", col, (-w / 2 + g, t / 2, 0))
    hinge.parent = root
    hinge["interact"] = {"type": "rotate", "axis": common.to_gltf((0, 0, 1)), "angle": 90, "duration": 0.9, "range": 1.8,
                         "side": "both", "collide": True, "prompt": "Open door", "promptActive": "Close door"}
    z0 = p["floor_gap"]
    # frame: stiles and rails (one mesh), glass in it
    import bmesh
    fr = bmesh.new()
    for lo, hi in (((0, -t, z0), (f, 0, z0 + sh)), ((sw - f, -t, z0), (sw, 0, z0 + sh)),
                   ((f, -t, z0), (sw - f, 0, z0 + f)), ((f, -t, z0 + sh - f), (sw - f, 0, z0 + sh))):
        b = common.box_bmesh([hi[i] - lo[i] for i in range(3)])
        bmesh.ops.translate(b, vec=[(hi[i] + lo[i]) / 2 for i in range(3)], verts=b.verts)
        me = pc.bpy.data.meshes.new("_tmp")
        b.to_mesh(me)
        b.free()
        fr.from_mesh(me)
        pc.bpy.data.meshes.remove(me)
    common.mesh_object(f"{n}_Frame", fr, col, bronze, hinge, smooth=False)
    pc.box(f"{n}_Glass", (f, -t * 0.7, z0 + f), (sw - f, -t * 0.3, z0 + sh - f), frosted, col, hinge)
    px = sw - 0.09
    for side, y0, y1 in (("Room", 0.0, 0.035), ("Hall", -t - 0.035, -t)):
        pc.box(f"{n}_Pull_{side}", (px - 0.012, y0, 0.75), (px + 0.012, y1, 1.45), bronze, col, hinge)
    return pc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
