"""Wall-mounted smart-home control panel (entry): a 10-inch black glass panel (240 x 160 mm)
on a satin aluminium frame standing 12 mm off the wall, the home UI glowing on it. Decor:
no interact; the screen reacts to "power" (dark in a blackout).

Wall-mounted: origin at the panel's back centre (on the wall), front -Y; place at z = 1.45."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402

importlib.reload(ix_common)
common, materials = ix_common.common, ix_common.materials

NAME = "IX_ControlPanel"
P = dict(name=NAME, size=(0.24, 0.16, 0.012))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    alu = common.pbr_material("M_Aluminium_Satin", (0.70, 0.71, 0.72), roughness=0.32, metallic=1.0)
    glass = common.pbr_material("M_Glass_Black", (0.006, 0.006, 0.007), roughness=0.06, coat=1.0)
    w, h, t = p["size"]
    frame = common.mesh_object(f"{n}_Frame", ix_common.plate_bmesh(w + 0.006, h + 0.006, t, 0.006), col, alu, root)
    common.add_bevel(frame, 0.0015, segments=1)
    front = common.mesh_object(f"{n}_Glass", ix_common.plate_bmesh(w, h, 0.0012, 0.005), col, glass, root)
    front.location = (0, -t + 0.0002, 0)
    scr = ix_common.screen_quad(f"{n}_Screen", col, ix_common.screen_material(), root, w - 0.018, h - 0.018, -t - 0.0012)
    scr["react"] = ix_common.glow("power")
    return ix_common.finish(root)
