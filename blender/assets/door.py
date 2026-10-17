"""Full-height walnut door for a wall opening, with black stops, bar pulls on
both sides and a keycard reader on the wall beside it.

Origin: bottom centre of the opening, on the wall's centre plane. The room side
is +Y; the door swings 90 degrees into the room about a hinge on the -X jamb.
The hinge empty carries the `interact` definition (rotate); whether a given
door is locked is decided by the level, not here."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, textures  # noqa: E402

importlib.reload(common)
importlib.reload(textures)

NAME = "Door"

P = dict(
    name=NAME,
    opening=(1.1, 2.5),     # width, height
    wall_t=0.2,
    gap=0.004,              # clearance around the slab
    floor_gap=0.008,
    slab_t=0.045,
    stop=(0.015, 0.02),     # width into the opening, depth
    pull_len=0.7,
    pull_z=1.05,            # centre height of the bar pull
    reader_enabled=True,    # keycard reader beside the door (False for an ordinary door)
    reader=(0.07, 0.012, 0.11),
    reader_offset=0.18,     # from the latch-side jamb to the reader centre
    reader_z=1.2,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    walnut = common.pbr_material("M_Walnut", (0.105, 0.042, 0.016), roughness=0.5, coat=0.25)
    common.set_base_color_map(walnut, textures.load(textures.walnut()))
    black = common.pbr_material("M_Aluminium_Black", (0.02, 0.02, 0.022), roughness=0.35, metallic=0.7)
    led = common.pbr_material("M_LED_Status", (0.05, 0.0, 0.0), roughness=0.4)
    bsdf = next(nd for nd in led.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Emission Color"].default_value = (1.0, 0.05, 0.02, 1)
    bsdf.inputs["Emission Strength"].default_value = 6.0

    w, h = p["opening"]
    g, st = p["gap"], p["slab_t"]
    sw, sh = w - 2 * g, h - p["floor_gap"] - g

    # hinge on the -X jamb, on the slab's room-side face, so the open slab stays
    # inside the opening instead of cutting into the jamb
    hinge = common.empty(f"{n}_Hinge", col, (-w / 2 + g, st / 2, 0))
    hinge.parent = root
    hinge["interact"] = {
        "type": "rotate",
        "axis": common.to_gltf((0, 0, 1)),    # door's local up
        "angle": 90,
        "duration": 0.9,
        "range": 1.8,
        "side": "both",
        "collide": True,                      # the slab is a moving collider
        "prompt": "Open door",
        "promptActive": "Close door",
        "lockedPrompt": "Locked · keycard required",
        "unlockPrompt": "Unlock with keycard",
    }

    if p["reader_enabled"]:
        hinge["interact"]["indicator"] = f"{n}_ReaderLED"   # turns green when unlocked

    slab = common.mesh_object(f"{n}_Slab", common.box_bmesh((sw, st, sh)), col, walnut, hinge)
    slab.location = (sw / 2, -st / 2, p["floor_gap"] + sh / 2)
    common.add_bevel(slab, 0.002, segments=2)
    common.box_uv(slab, tile=0.5)

    # vertical bar pulls on both faces near the latch edge (slab-local, hinge space)
    px = sw - 0.07
    z0, z1 = p["pull_z"] - p["pull_len"] / 2, p["pull_z"] + p["pull_len"] / 2
    for side, face, out in (("Room", 0.0, 0.05), ("Hall", -st, -0.05)):
        pts = common.fillet_polyline([(px, face, z0), (px, face + out, z0), (px, face + out, z1), (px, face, z1)],
                                     0.012, segments=6, closed=False)
        common.tube_object(f"{n}_Pull_{side}", pts, 0.009, col, black, hinge, closed=False)

    # stops on the hall side of the slab: jambs + head (static)
    sx, sd = p["stop"]
    y_stop = -st / 2 - sd / 2
    for name, size, loc in (
        ("Stop_L", (sx, sd, h), (-w / 2 + sx / 2, y_stop, h / 2)),
        ("Stop_R", (sx, sd, h), (w / 2 - sx / 2, y_stop, h / 2)),
        ("Stop_Head", (w, sd, sx), (0, y_stop, h - sx / 2)),
    ):
        ob = common.mesh_object(f"{n}_{name}", common.box_bmesh(size), col, black, root, smooth=False)
        ob.location = loc

    # keycard reader on the room-side wall face, beside the latch jamb
    if not p["reader_enabled"]:
        parts = [o for o in root.children_recursive if o.type == "MESH"]
        return root, parts
    rw, rt, rh = p["reader"]
    ry = p["wall_t"] / 2 + rt / 2
    rx = w / 2 + p["reader_offset"]
    reader = common.mesh_object(f"{n}_Reader", common.box_bmesh((rw, rt, rh)), col, black, root)
    reader.location = (rx, ry, p["reader_z"])
    common.add_bevel(reader, 0.004, segments=3)
    lamp = common.mesh_object(f"{n}_ReaderLED", common.box_bmesh((0.036, 0.003, 0.006)), col, led, root)
    lamp.location = (rx, ry + rt / 2 + 0.001, p["reader_z"] + rh / 2 - 0.018)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
