"""Flashlight: a compact anodised-aluminium torch (165 mm), knurled grip rings, a flared head
with a polished steel bezel, a faceted reflector behind a clear lens, a rubber tail switch
and a steel pocket clip. A pickup (item "flashlight"; the engine gives it the spot light).

Lies on its side along X; origin at the centre of its underside."""
import importlib
import os
import sys

from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402

importlib.reload(ix_common)
common, materials = ix_common.common, ix_common.materials

NAME = "IX_Flashlight"
P = dict(name=NAME, length=0.165, r_body=0.0135, r_head=0.0193, segments=20)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    root["interact"] = ix_common.pickup("flashlight", "Flashlight")

    alu = materials.black_metal()
    steel = materials.steel()
    rubber = common.pbr_material("M_Rubber_Black", (0.018, 0.018, 0.019), roughness=0.75)
    lens = materials.glass("M_Glass_Clear")
    L, rb, rh, seg = p["length"], p["r_body"], p["r_head"], p["segments"]
    g = rb - 0.0008                       # grip groove radius

    prof = [(0, 0.008), (rb - 0.0015, 0.008), (rb, 0.0095)]
    z = 0.024
    for k in range(6):                    # grip rings
        prof += [(rb, z), (g, z + 0.0008), (g, z + 0.0032), (rb, z + 0.004)]
        z += 0.0085
    prof += [(rb, 0.112), (rb + 0.0015, 0.118), (rh - 0.0005, 0.140), (rh - 0.0005, 0.153),
             (rh - 0.0025, 0.1545), (0.0158, 0.1545), (0.0158, 0.152), (0, 0.152)]
    body = common.mesh_object(f"{n}_Body", ix_common.lathe_bmesh(prof, seg, axis="x",
                              sharp=[2, len(prof) - 4, len(prof) - 3]), col, alu, root)
    tail = common.mesh_object(f"{n}_TailSwitch", ix_common.lathe_bmesh(
        [(0, 0.0), (0.006, 0.0006), (0.0095, 0.003), (0.0108, 0.0095), (0, 0.0095)], seg, axis="x"), col, rubber, root)
    bez = ix_common.lathe_bmesh([(0.0158, 0.1535), (rh, 0.1535), (rh, 0.1635), (rh - 0.001, L), (0.0162, L),
                                 (0.0158, 0.1535)], seg, axis="x", sharp=[1, 2, 4])
    import bmesh
    bmesh.ops.remove_doubles(bez, verts=bez.verts, dist=1e-6)
    bezel = common.mesh_object(f"{n}_Bezel", bez, col, steel, root)
    refl = common.mesh_object(f"{n}_Reflector", ix_common.lathe_bmesh(
        [(0.003, 0.153), (0.0158, 0.1625), (0.0158, 0.1628)], seg, axis="x"), col, steel, root)
    lens_ob = common.mesh_object(f"{n}_Lens", ix_common.lathe_bmesh(
        [(0, 0.1626), (0.0162, 0.1626), (0.0162, 0.1632), (0, 0.1632)], seg, axis="x"), col, lens, root, smooth=False)
    led = common.mesh_object(f"{n}_Emitter", common.box_bmesh((0.002, 0.0035, 0.0035)), col,
                             common.pbr_material("M_Flashlight_LED", (0.85, 0.82, 0.55), roughness=0.3), root,
                             smooth=False)
    led.location = (0.1535, 0, 0)
    clip = common.mesh_object(f"{n}_Clip", common.box_bmesh((0.062, 0.0065, 0.0012)), col, steel, root, smooth=False)
    clip.location = (0.05, 0, rb + 0.0016)
    common.add_bevel(clip, 0.0005, segments=1)
    clip_foot = common.mesh_object(f"{n}_ClipFoot", common.box_bmesh((0.006, 0.0065, 0.0022)), col, steel, root,
                                   smooth=False)
    clip_foot.location = (0.08, 0, rb + 0.0006)

    # lie it down: axis at the head's radius above the floor, centred along X
    for ob in root.children:
        ob.location = Vector(ob.location) + Vector((-L / 2, 0, rh))
    return ix_common.finish(root)
