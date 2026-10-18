"""Library reading armchair: a deep, low club chair in navy wool with a firm seat
cushion, rolled arms, a tall softly raked back and slim bronze-capped walnut legs.
Origin: floor centre; faces -Y. About 0.86 x 0.9 x 0.92 m."""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import library_kit as kit  # noqa: E402
from library_kit import Mesh, common, materials  # noqa: E402

importlib.reload(kit)

NAME = "LibraryArmchair"

P = dict(
    name=NAME,
    fabric="navy",           # "navy" | "oat" | "cognac" | "green"
    width=0.88,
    depth=0.9,
    leg_h=0.13,
    seat_h=0.44,             # top of the seat cushion
    arm_h=0.62,
    arm_w=0.17,
    back_h=0.93,
    cuts=3,
    seats=1,                 # seat / back cushions across (a sofa has 2-3)
)


def cushion(name, size, centre, col, mat, root, crown=None, edge=0.03, tilt=0.0, cuts=3, tile=0.25):
    ob = common.mesh_object(name, common.cushion_bmesh(size, cuts=cuts, edge=edge, crown=crown or {}), col, mat, root)
    ob.location = centre
    ob.rotation_euler = (tilt, 0, 0)
    common.add_subsurf(ob, levels=1, render_levels=1)
    common.box_uv(ob, tile=tile)
    return ob


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    walnut, bronze = materials.walnut(), materials.bronze()
    fab = {"navy": kit.linen_navy, "oat": kit.linen_oat, "cognac": kit.leather_cognac,
           "green": kit.leather_green}[p["fabric"]]()
    W, D, lh = p["width"], p["depth"], p["leg_h"]
    aw = p["arm_w"]
    tile = 0.2 if p["fabric"] in ("cognac", "green") else 0.25
    c = p["cuts"]

    # base block (slightly short of the arms' height), arms, back, seat cushion
    base_top = 0.30
    cushion(f"{n}_Base", (W - 0.04, D - 0.06, base_top - lh), (0, 0.0, lh + (base_top - lh) / 2), col, fab, root,
            {"+z": 0.0, "-y": 0.012}, 0.03, cuts=c, tile=tile)
    for sx in (-1, 1):
        cushion(f"{n}_Arm_{'L' if sx < 0 else 'R'}", (aw, D - 0.04, p["arm_h"] - lh),
                (sx * (W - aw) / 2, 0.0, lh + (p["arm_h"] - lh) / 2), col, fab, root,
                {"+z": 0.028, "+x": 0.01, "-x": 0.01, "-y": 0.012}, 0.04, cuts=c, tile=tile)
    tilt = math.radians(-9)
    bd = 0.21
    inner = W - 2 * aw
    ns = p["seats"]
    sd_ = D - bd - 0.08
    for i in range(ns):
        xc = -inner / 2 + (i + 0.5) * inner / ns
        tag = "" if ns == 1 else f"_{i}"
        cushion(f"{n}_Back{tag}", (inner / ns + 0.02, bd, p["back_h"] - 0.28),
                (xc, D / 2 - bd / 2 - 0.02, 0.28 + (p["back_h"] - 0.28) / 2),
                col, fab, root, {"-y": 0.025, "+z": 0.02}, 0.05, tilt=tilt, cuts=c, tile=tile)
        cushion(f"{n}_Seat{tag}", (inner / ns - 0.005, sd_, p["seat_h"] - base_top),
                (xc, -D / 2 + sd_ / 2 + 0.035, base_top + (p["seat_h"] - base_top) / 2),
                col, fab, root, {"+z": 0.03, "-y": 0.012}, 0.045, cuts=c, tile=tile)

    kit.merge_objects([o for o in root.children if o.name.startswith(f"{n}_")], f"{n}_Upholstery", col, root)

    # legs: tapered walnut with bronze caps
    wood, brz = Mesh(0.5), Mesh(0.5)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (W / 2 - 0.08), sy * (D / 2 - 0.1)
            wood.box((x, y, lh / 2 + 0.01), (0.05, 0.05, lh - 0.02), taper=(1.5, 1.5), shift=(sx * 0.3, sy * 0.2))
            brz.box((x, y, 0.008), (0.044, 0.044, 0.016))
    wood.to_object(f"{n}_Legs", col, walnut, root)
    brz.to_object(f"{n}_Caps", col, bronze, root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
