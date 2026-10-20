"""Garage breaker panel: a light-grey powder-coated steel distribution board (560 x 720 x
110 mm, open front) with three DIN rows of white breakers, a big red-on-yellow rotary main
isolator (a `switch` on signal "power", starting on; a green LED beside it is its indicator)
and an empty main-fuse carrier under it (a `use` needing item "fuse": with the fuse armed,
Enter puts it in and sets "power" true).

Wall-mounted: origin at the enclosure's back centre (on the wall), front -Y; place at z = 1.45."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402
import ix_blind  # noqa: E402  (boxes_bmesh)

importlib.reload(ix_common)
importlib.reload(ix_blind)
common, materials = ix_common.common, ix_common.materials

NAME = "IX_BreakerPanel"
P = dict(name=NAME, size=(0.56, 0.72, 0.11), rows=3, per_row=14)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    steel = common.pbr_material("M_Breaker_Steel", (0.56, 0.57, 0.56), roughness=0.55, metallic=0.25)
    back = common.pbr_material("M_Breaker_Backplate", (0.30, 0.31, 0.31), roughness=0.6, metallic=0.3)
    plastic = common.pbr_material("M_Breaker_Plastic", (0.74, 0.74, 0.71), roughness=0.45)
    black = common.pbr_material("M_Rubber_Black", (0.018, 0.018, 0.019), roughness=0.75)
    yellow = common.pbr_material("M_Breaker_Yellow", (0.75, 0.52, 0.02), roughness=0.4)
    red = common.pbr_material("M_Breaker_Red", (0.50, 0.02, 0.015), roughness=0.35, coat=0.3)
    brass = common.pbr_material("M_Brass", (0.78, 0.56, 0.24), roughness=0.3, metallic=1.0)
    led = materials.emissive("M_Breaker_LED", (0.05, 1.0, 0.25), 3.0)
    W, H, D = p["size"]
    t = 0.0015 * 2

    # enclosure: back, four sides with a folded front lip
    shell = ix_blind.boxes_bmesh([
        ((0, -t / 2, 0), (W, t, H)),
        ((-W / 2 + t / 2, -D / 2, 0), (t, D, H)), ((W / 2 - t / 2, -D / 2, 0), (t, D, H)),
        ((0, -D / 2, H / 2 - t / 2), (W, D, t)), ((0, -D / 2, -H / 2 + t / 2), (W, D, t)),
        ((-W / 2 + 0.012, -D + t / 2, 0), (0.024, t, H)), ((W / 2 - 0.012, -D + t / 2, 0), (0.024, t, H)),
        ((0, -D + t / 2, H / 2 - 0.012), (W, t, 0.024)), ((0, -D + t / 2, -H / 2 + 0.012), (W, t, 0.024))])
    enc = common.mesh_object(f"{n}_Enclosure", shell, col, steel, root, smooth=False)
    common.add_bevel(enc, 0.001, segments=1)
    plate = common.mesh_object(f"{n}_Backplate", common.box_bmesh((W - 0.05, 0.004, H - 0.05)), col, back, root,
                               smooth=False)
    plate.location = (0, -t - 0.002, 0)

    # DIN rows: rail, breakers (one mesh), their toggles (one mesh)
    mw, mh, md = 0.018, 0.085, 0.062
    rows_z = [0.17, 0.02, -0.13]
    bodies, toggles, rails = [], [], []
    for z in rows_z:
        rails.append(((0, -0.012, z), (W - 0.08, 0.008, 0.035)))
        x0 = -p["per_row"] * mw / 2
        for k in range(p["per_row"]):
            w_ = mw * (2 if k == 0 else 1) - 0.0006
            if k == 1:
                continue
            x = x0 + (k + (0.5 if k == 0 else 0.5)) * mw
            if k == 0:
                x = x0 + mw
            bodies.append(((x, -0.016 - md / 2, z), (w_, md, mh)))
            toggles.append(((x, -0.016 - md - 0.006, z + 0.006), (w_ * 0.45, 0.012, 0.014)))
    common.mesh_object(f"{n}_Rails", ix_blind.boxes_bmesh(rails), col, steel, root, smooth=False)
    br = common.mesh_object(f"{n}_Breakers", ix_blind.boxes_bmesh(bodies), col, plastic, root, smooth=False)
    common.add_bevel(br, 0.0012, segments=1)
    common.mesh_object(f"{n}_Toggles", ix_blind.boxes_bmesh(toggles), col, black, root, smooth=False)

    # main isolator: yellow plate, red rotary handle on its own empty
    mx, mz = 0.0, H / 2 - 0.085
    base = common.mesh_object(f"{n}_IsolatorPlate", ix_common.plate_bmesh(0.11, 0.09, 0.03, 0.006), col, yellow, root)
    base.location = (mx, -0.02, mz)
    common.add_bevel(base, 0.002, segments=1)
    hub = common.empty(f"{n}_MainSwitch", col, (mx, -0.05, mz))
    hub.parent = root
    hub["interact"] = {"type": "switch", "signal": "power", "state": True, "prompt": "Switch the power on",
                       "promptActive": "Switch the power off", "range": 1.4, "duration": 0.35,
                       "travel": {"axis": "z", "angle": -90}, "indicator": f"{n}_PowerLED"}
    knob = ix_common.lathe_bmesh([(0, 0), (0.022, 0), (0.024, 0.004), (0.022, 0.012), (0, 0.012)], 20)
    bmesh.ops.rotate(knob, verts=knob.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "X"))
    common.mesh_object(f"{n}_MainSwitch_Hub", knob, col, red, hub)
    handle = common.mesh_object(f"{n}_MainSwitch_Handle", common.box_bmesh((0.085, 0.022, 0.024)), col, red, hub)
    handle.location = (0, -0.022, 0)
    common.add_bevel(handle, 0.004, segments=2)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.004, radius2=0.004, depth=0.004,
                          matrix=Matrix.Rotation(math.radians(90), 4, "X"))
    ledo = common.mesh_object(f"{n}_PowerLED", bm, col, led, root, smooth=False)
    ledo.location = (mx + 0.075, -0.036, mz + 0.025)

    # main-fuse carrier: a black block with two brass clips and the empty slot between them
    fz = rows_z[-1] - 0.12
    carrier = common.mesh_object(f"{n}_FuseCarrier", common.box_bmesh((0.11, 0.05, 0.045)), col, black, root)
    carrier.location = (0, -0.03, fz)
    common.add_bevel(carrier, 0.003, segments=1)
    common.mesh_object(f"{n}_FuseClips", ix_blind.boxes_bmesh(
        [((sx * 0.027, -0.058, fz), (0.010, 0.010, 0.020)) for sx in (-1, 1)]), col, brass, root, smooth=False)
    slot = common.empty(f"{n}_FuseSlot", col, (0, -0.06, fz))
    slot.parent = root
    slot["interact"] = {"type": "use", "needs": "fuse", "needsName": "fuse", "consume": True, "prompt": "Insert fuse",
                        "promptDone": "Main fuse in place", "signal": "power", "value": True, "range": 1.4}
    return ix_common.finish(root)
