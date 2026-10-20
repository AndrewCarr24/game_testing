"""Smart-home tablet on its charging dock: a slim aluminium tablet (248 x 179 x 6.5 mm, black
glass front, the home UI glowing on its screen) leaning back 20 degrees in landscape in a
walnut dock with a satin aluminium spine. The tablet is a pickup (item "tablet": armed +
Enter opens the smart-home screen) on its own empty, `<n>_Tablet`; the dock stays.
The screen reacts to "power" (dark in a blackout).

Origin: the dock's underside centre; front (the screen) faces -Y."""
import importlib
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402

importlib.reload(ix_common)
common, materials = ix_common.common, ix_common.materials

NAME = "IX_TabletDock"
P = dict(name=NAME, tablet=(0.248, 0.179, 0.0065), lean=20.0, dock=(0.15, 0.085, 0.022))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    walnut = materials.walnut()
    alu = common.pbr_material("M_Aluminium_Satin", (0.70, 0.71, 0.72), roughness=0.32, metallic=1.0)
    glass = common.pbr_material("M_Glass_Black", (0.006, 0.006, 0.007), roughness=0.06, coat=1.0)
    felt = common.pbr_material("M_Felt_Black", (0.02, 0.02, 0.02), roughness=1.0)

    dw, dd, dh = p["dock"]
    base = common.mesh_object(f"{n}_Dock", common.rounded_slab_bmesh(dw, dd, dh, 0.012, segments=4), col, walnut, root)
    base.location = (0, 0, dh / 2)
    common.add_bevel(base, 0.002, segments=1)
    common.box_uv(base, 0.5)
    pad = common.mesh_object(f"{n}_DockFeet", common.rounded_slab_bmesh(dw - 0.01, dd - 0.01, 0.001, 0.008, 3), col,
                             felt, root)
    pad.location = (0, 0, 0.0005)
    # aluminium spine the tablet leans on, and the slot lip in front of it
    lean = math.radians(p["lean"])
    spine = common.mesh_object(f"{n}_DockSpine", common.box_bmesh((dw * 0.7, 0.008, 0.07)), col, alu, root)
    spine.location = (0, 0.012 + 0.035 * math.sin(lean), dh + 0.035 * math.cos(lean) - 0.004)
    spine.rotation_euler = (-lean, 0, 0)
    common.add_bevel(spine, 0.002, segments=1)
    lip = common.mesh_object(f"{n}_DockLip", common.box_bmesh((dw, 0.006, 0.008)), col, alu, root)
    lip.location = (0, -0.014, dh + 0.004)
    common.add_bevel(lip, 0.0015, segments=1)

    # the tablet: its own empty at the bottom edge, leaning back
    tw, th, tt = p["tablet"]
    tab = common.empty(f"{n}_Tablet", col, (0, -0.004, dh + 0.0005))
    tab.parent = root
    tab.rotation_euler = (-lean, 0, 0)
    tab["interact"] = ix_common.pickup("tablet", "Tablet", "Take tablet")
    body = common.mesh_object(f"{n}_Tablet_Body", common.rounded_slab_bmesh(tw, th, tt, 0.012, segments=5), col, alu, tab)
    body.rotation_euler = (math.radians(90), 0, 0)
    body.location = (0, tt / 2, th / 2)
    front = common.mesh_object(f"{n}_Tablet_Glass", common.rounded_slab_bmesh(tw - 0.002, th - 0.002, 0.0006, 0.011, 5),
                               col, glass, tab)
    front.rotation_euler = (math.radians(90), 0, 0)
    front.location = (0, -0.0001, th / 2)
    scr = ix_common.screen_quad(f"{n}_Tablet_Screen", col, ix_common.screen_material(), tab,
                                tw - 0.03, th - 0.03, -0.0006)
    scr.location = (0, 0, th / 2)
    scr["react"] = ix_common.glow("power")
    return ix_common.finish(root)
