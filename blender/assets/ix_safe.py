"""Floor safe: a heavy graphite steel box (50 mm walls) with an inset door on two barrel
hinges, a three-spoke chrome handle wheel and a brass key cylinder, a felt-lined interior
with one shelf. The door is an interactable (`rotate`, "Open safe"); the level locks it
with a key ({"lock": "key_safe"}). Whatever the level attaches to `IX_Safe_Inside` (a
static node on the safe's floor carrying `inside`: the door's name) can only be taken
while the door is open, and doesn't swing with it.

Also the base of `ix_gun_locker` (style="locker": a tall steel locker with shelves, a bar
handle and vent slots). Front faces -Y, origin at the floor centre, the door hinges on -X."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402

importlib.reload(ix_common)
common, materials = ix_common.common, ix_common.materials

NAME = "IX_Safe"
P = dict(
    name=NAME,
    style="safe",                  # safe | locker
    size=(0.56, 0.50, 0.70),       # W, D, H
    wall=0.05,                     # steel thickness
    door_t=0.07,
    shelves=(0.36,),               # shelf heights (top faces), from the floor
    inside_z=0.36,                 # where <n>_Inside sits: on the shelf (None: the interior floor)
    plinth=0.0,                    # recessed black plinth height (lockers)
    open_angle=-100,               # swings out (-Y) about the hinge on -X
    prompt="Open safe", prompt_active="Close safe",
    body=("M_Safe_Graphite", (0.030, 0.032, 0.035), 0.42, 0.55),
    lining=("M_Safe_Felt", (0.030, 0.045, 0.040), 0.95, 0.0),
)


def _box(n, part, size, loc, col, mat, parent, bevel=0.0):
    ob = common.mesh_object(f"{n}_{part}", common.box_bmesh(size), col, mat, parent, smooth=False)
    ob.location = loc
    if bevel:
        common.add_bevel(ob, bevel, segments=2)
    common.box_uv(ob, 0.5)
    return ob


def _cyl(bm, r, depth, loc, axis="Y", segs=16):
    rot = {"X": Matrix.Rotation(math.pi / 2, 4, "Y"), "Y": Matrix.Rotation(math.pi / 2, 4, "X"),
           "Z": Matrix.Identity(4)}[axis]
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r, radius2=r, depth=depth,
                          matrix=Matrix.Translation(loc) @ rot)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    body = common.pbr_material(p["body"][0], p["body"][1], roughness=p["body"][2], metallic=p["body"][3])
    lining = common.pbr_material(p["lining"][0], p["lining"][1], roughness=p["lining"][2])
    chrome = common.pbr_material("M_Chrome", (0.85, 0.85, 0.86), roughness=0.12, metallic=1.0)
    brass = common.pbr_material("M_Brass", (0.78, 0.56, 0.24), roughness=0.3, metallic=1.0)
    dark = common.pbr_material("M_Key_Hole", (0.01, 0.01, 0.01), roughness=0.9)
    black = materials.black_metal()

    W, D, H = p["size"]
    t, dt, pl = p["wall"], p["door_t"], p["plinth"]
    yf, yb = -D / 2, D / 2
    z0 = pl                                   # the box sits on its plinth
    if pl:
        _box(n, "Plinth", (W - 0.06, D - 0.08, pl), (0, 0.01, pl / 2), col, black, root)
    # the shell: back, sides, top, bottom (static, each its own collider)
    _box(n, "Back", (W, t, H - pl), (0, yb - t / 2, z0 + (H - pl) / 2), col, body, root, 0.003)
    for side, sx in (("L", -1), ("R", 1)):
        _box(n, f"Side_{side}", (t, D - t, H - pl), (sx * (W - t) / 2, yf + (D - t) / 2, z0 + (H - pl) / 2),
             col, body, root, 0.004)
    _box(n, "Top", (W - 2 * t, D - t, t), (0, yf + (D - t) / 2, H - t / 2), col, body, root, 0.003)
    _box(n, "Bottom", (W - 2 * t, D - t, t), (0, yf + (D - t) / 2, z0 + t / 2), col, body, root, 0.003)
    # felt lining a few mm inside the steel, behind the door
    iw, ih = W - 2 * t, H - pl - 2 * t
    idp = D - t - dt                         # interior depth behind the closed door
    yi = yf + dt + idp / 2
    lt = 0.004
    _box(n, "Lining_Back", (iw, lt, ih), (0, yb - t - lt / 2, z0 + t + ih / 2), col, lining, root)
    _box(n, "Lining_Floor", (iw, idp, lt), (0, yi, z0 + t + lt / 2), col, lining, root)
    for side, sx in (("L", -1), ("R", 1)):
        _box(n, f"Lining_{side}", (lt, idp, ih), (sx * (iw - lt) / 2, yi, z0 + t + ih / 2), col, lining, root)
    for k, zs in enumerate(p["shelves"]):
        _box(n, f"Shelf{k}", (iw - 2 * lt, idp - 0.02, 0.012), (0, yi + 0.01, zs - 0.006), col, body, root, 0.002)
    inside = common.empty(f"{n}_Inside", col, (0, yi - idp * 0.1, p["inside_z"] if p["inside_z"] else z0 + t + lt))
    inside.parent = root
    inside["inside"] = f"{n}_Door"           # the door that closes it (prompts/interactivity.md)

    # --- the door: hinge empty on the -X edge of the opening, at the front face
    gap = 0.003
    dw, dh = iw - 2 * gap, ih - 2 * gap
    hinge = common.empty(f"{n}_Door", col, (-iw / 2, yf, z0 + t + ih / 2))
    hinge.parent = root
    hinge["interact"] = {
        "type": "rotate", "axis": common.to_gltf((0, 0, 1)), "angle": p["open_angle"],
        "duration": 0.9 if p["style"] == "safe" else 0.7, "range": 1.5, "side": "both",
        "prompt": p["prompt"], "promptActive": p["prompt_active"],
    }
    # door parts in hinge space: the slab spans x 0..dw, y 0..dt (inward), z -dh/2..dh/2
    slab = _box(n, "Door_Slab", (dw, dt, dh), (gap + dw / 2, dt / 2, 0), col, body, hinge, 0.004)
    # a shallow raised panel on the face, 6 mm proud
    _box(n, "Door_Panel", (dw - 0.07, 0.006, dh - 0.07), (gap + dw / 2, -0.003, 0), col, body, hinge, 0.002)
    hw = bmesh.new()
    if p["style"] == "safe":
        # three-spoke handle wheel (chrome) right of centre, key cylinder above it
        cx, cz = gap + dw * 0.62, -0.02
        _cyl(hw, 0.022, 0.03, (cx, -0.021, cz))
        for k in range(3):
            a = math.radians(90 + 120 * k)
            ex, ez = cx + 0.075 * math.cos(a), cz + 0.075 * math.sin(a)
            pts = [(cx + 0.015 * math.cos(a), -0.03, cz + 0.015 * math.sin(a)), (ex, -0.03, ez)]
            common.tube_object(f"{n}_Door_Spoke{k}", pts, 0.0055, col, chrome, hinge, closed=False)
            bmesh.ops.create_uvsphere(hw, u_segments=10, v_segments=6, radius=0.011,
                                      matrix=Matrix.Translation((ex, -0.03, ez)))
        key = (cx, cz + 0.15)
    else:
        # a vertical bar handle on standoffs near the latch edge, key cylinder above it
        hx = gap + dw - 0.06
        pts = common.fillet_polyline([(hx, 0.0, -0.15), (hx, -0.045, -0.15), (hx, -0.045, 0.15), (hx, 0.0, 0.15)],
                                     0.015, segments=5, closed=False)
        common.tube_object(f"{n}_Door_Handle", pts, 0.009, col, chrome, hinge, closed=False)
        key = (hx, 0.24)
        # vent slots top and bottom
        vb = bmesh.new()
        for zc in (dh / 2 - 0.12, -dh / 2 + 0.12):
            for k in range(6):
                bmesh.ops.create_cube(vb, size=1.0, matrix=Matrix.Translation((gap + dw / 2, -0.0062, zc + (k - 2.5) * 0.022)) @
                                      Matrix.Diagonal((dw * 0.55, 0.002, 0.008, 1)))
        common.mesh_object(f"{n}_Door_Vents", vb, col, dark, hinge, smooth=False)
    common.mesh_object(f"{n}_Door_Hub", hw, col, chrome, hinge)
    kb = bmesh.new()
    _cyl(kb, 0.016, 0.012, (key[0], -0.006, key[1]), segs=20)
    common.mesh_object(f"{n}_Door_Lock", kb, col, brass, hinge)
    _box(n, "Door_Keyhole", (0.004, 0.002, 0.014), (key[0], -0.0125, key[1]), col, dark, hinge)
    # barrel hinges on the -X edge (static: the door turns about them)
    hb = bmesh.new()
    for zc in ((-dh / 2 + 0.12, dh / 2 - 0.12) if H < 1 else (-dh / 2 + 0.2, 0.0, dh / 2 - 0.2)):
        _cyl(hb, 0.012, 0.09, (-iw / 2, yf - 0.006, z0 + t + ih / 2 + zc), axis="Z", segs=12)
    common.mesh_object(f"{n}_Hinges", hb, col, body, root)
    _ = slab
    return ix_common.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
