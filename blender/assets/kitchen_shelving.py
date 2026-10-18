"""Scullery south wall: smoked-oak low cabinets with a walnut butcher-block top, a
blackened-steel rail of hanging copper pans, and two walnut shelves with woven
baskets and folded linen.

4.0 m long along X, 0.5 m deep, back against +Y, fronts face -Y. Origin is the floor
centre."""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitchen_lib as L  # noqa: E402

importlib.reload(L)
common, materials = L.common, L.materials

NAME = "KitchenShelving"

P = dict(
    name=NAME,
    length=3.9,
    depth=0.52,
    plinth=0.10,
    counter_z=0.92,
    counter_t=0.06,
    units=[(1.0, "dr3"), (0.95, "d2"), (0.95, "d2"), (1.0, "dr3")],
    rail_z=2.35,
)


def pan(b, name, x, y, z, r, depth, mat_in, mat_out, handle=0.26, hook_z=None):
    """A copper pan hanging flat against the wall (axis -Y), handle up to the rail."""
    prof = [(0.0, 0.0), (r * 0.9, 0.0), (r, depth * 0.3), (r, depth), (r - 0.004, depth), (r * 0.9 - 0.004, 0.006), (0.0, 0.006)]
    ob = b.lathe(name, prof, mat_out, loc=(x, y, z), segs=18, sharp=50, uv_tile=0.3)
    ob.rotation_euler = (math.radians(90), 0, 0)        # axis along -Y: opening faces the room
    return ob


def build(**overrides):
    p = {**P, **overrides}
    b = L.Builder(p["name"])
    oak = materials.smoked_oak()
    walnut = materials.walnut()
    bronze = materials.bronze()
    black = L.carcass()
    dark = materials.black_metal()
    copper = common.pbr_material("M_Copper", (0.62, 0.30, 0.17), roughness=0.3, metallic=1.0)
    linen = L.cream_fabric()
    linen2 = materials.fabric("M_Fabric_Stone", (0.16, 0.15, 0.14))
    wicker = common.pbr_material("M_Wicker", (0.30, 0.21, 0.12), roughness=0.95)

    Lx, D = p["length"], p["depth"]
    yf, yb = -D / 2, D / 2
    t = 0.02
    ph, cz, ct = p["plinth"], p["counter_z"], p["counter_t"]
    x0, x1 = -Lx / 2, Lx / 2
    fr = L.Fronts(b, oak, bronze, yf)
    b.box("Plinth", (Lx - 0.04, D - 0.09, ph), (0, (yf + 0.07 + yb - 0.02) / 2, ph / 2), black, bevel=0, tile=0)
    b.box("Body", (Lx, yb - (yf + t), cz - ct - ph), (0, (yf + t + yb) / 2, (ph + cz - ct) / 2), black, bevel=0, tile=0)
    for i, (a, c, kind) in enumerate(L.span(x0, p["units"])):
        fr.unit(kind, a, c, ph, cz - ct, f"Base{i}")
    b.box("Top", (Lx + 0.02, D + 0.02, ct), (0, 0.0, cz - ct / 2), walnut, bevel=0.004, seg=2, tile=0.5, shift=(0.15, 0.4))

    # backsplash panel and the pan rail
    rz = p["rail_z"]
    b.box("Backboard", (Lx, 0.02, 1.9), (0, yb - 0.01, cz + 0.95), oak, bevel=0.001, tile=0.5, shift=(0.1, 0.6))
    b.tube("Rail_Bar", [(x0 + 0.12, yb - 0.09, rz), (x1 - 0.12, yb - 0.09, rz)], 0.011, dark, closed=False, res=3)
    for k, hx in enumerate((x0 + 0.12, x1 - 0.12)):
        b.tube(f"Rail_Arm{k}", [(hx, yb - 0.02, rz), (hx, yb - 0.09, rz)], 0.011, dark, closed=False, res=3)
    pans = [(-1.55, 0.14), (-1.05, 0.11), (-0.55, 0.095), (0.0, 0.13), (0.5, 0.1), (1.0, 0.12), (1.55, 0.09)]
    for i, (px, r) in enumerate(pans):
        zc = rz - 0.34 - r * 0.0
        py = yb - 0.1
        pan(b, f"Pan{i}", px, py - 0.03, zc, r, 0.075, copper, copper)
        # handle: a slim bar from the pan rim up to the rail
        b.tube(f"PanHandle{i}", [(px, py + 0.0, zc + r), (px, py + 0.0, rz - 0.01)], 0.008, copper, closed=False, res=3)
        b.tube(f"PanHook{i}", [(px, py + 0.0, rz - 0.01), (px, py - 0.0, rz + 0.0)], 0.009, dark, closed=False, res=3)

    # two walnut shelves with baskets and linen
    sdp = 0.3
    syc = yb - sdp / 2 - 0.02
    for i, z in enumerate((1.28, 1.63)):
        pass
    # shelves sit behind the pans, in the gaps: use short shelves at the ends and centre
    shelf_runs = [(-1.95, -1.15), (-0.35, 0.35), (1.15, 1.95)]
    for si, (a, c) in enumerate(shelf_runs):
        for i, z in enumerate((1.25, 1.62)):
            b.box(f"Shelf{si}_{i}", (c - a, sdp, 0.035), ((a + c) / 2, syc, z), walnut, bevel=0.003, seg=1, tile=0.5,
                  shift=(0.2 * si, 0.2 * i))
    # baskets and stacks (simple lathed/boxed forms)
    for (bx, bz, br) in ((-1.7, 1.25, 0.12), (-1.35, 1.25, 0.1), (1.35, 1.25, 0.12), (1.7, 1.25, 0.1), (0.0, 1.25, 0.14)):
        prof = [(0.0, 0.0), (br * 0.85, 0.0), (br, 0.16), (br - 0.006, 0.16), (br * 0.85 - 0.006, 0.01), (0.0, 0.01)]
        b.lathe(f"Basket_{bx:.2f}", prof, wicker, loc=(bx, syc, bz + 0.0175), segs=14, sharp=70, uv_tile=0.3)
    for k, (lx, lz) in enumerate(((-1.7, 1.62), (-1.3, 1.62), (1.3, 1.62), (1.7, 1.62), (-0.1, 1.62), (0.15, 1.62))):
        n = 5 + k % 3
        for j in range(n):
            b.box(f"Linen{k}_{j}", (0.34, 0.24, 0.035), (lx, syc, lz + 0.0175 + 0.0175 + j * 0.036), linen if (k + j) % 3 else linen2,
                  bevel=0.006, seg=1, tile=0.25)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
