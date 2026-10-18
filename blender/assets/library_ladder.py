"""Rolling library ladder: two walnut stiles, round rungs, and bronze hooks and wheels
at the top that run on the bookcases' bronze rail. The origin is on the floor directly
under the rail (the top of the ladder); the ladder leans toward -Y with its foot
`lean` metres out, so rotate 180 for the south wall (shelves behind it, on +Y)."""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import library_kit as kit  # noqa: E402
from library_kit import Mesh, common, materials  # noqa: E402

importlib.reload(kit)

NAME = "LibraryLadder"

P = dict(
    name=NAME,
    rail_z=3.2,          # must match library_bookcase rail_z
    lean=0.95,           # horizontal run from the rail to the foot
    width=0.46,
    stile=(0.045, 0.022),
    rung_gap=0.30,
    rung_r=0.015,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    walnut, bronze = materials.walnut(), materials.bronze()

    lean, rz = p["lean"], p["rail_z"]
    length = math.hypot(lean, rz)
    ang = math.atan2(lean, rz)                       # from vertical
    sy, cz = math.sin(ang), math.cos(ang)
    off = -0.04                                      # the stiles hang just in front of the rail

    def pt(s):
        """(y, z) at distance s up the stile from the foot."""
        return (-lean + s * sy + off, s * cz)

    wood, brz = Mesh(0.5), Mesh(0.5)
    hw = p["width"] / 2
    sw, sd = p["stile"]
    s0 = 0.03
    top = length + 0.10 - s0                         # stiles stand above the rail
    mid = pt(s0 + top / 2)
    for sx in (-1, 1):
        wood.box((sx * hw, mid[0], mid[1]), (sd, sw, top), rot=(-ang, "x"), shift=(0.2 * sx, 0.1))
    n_rungs = int((length - 0.35) // p["rung_gap"]) + 1
    for i in range(n_rungs):
        y, z = pt(0.32 + i * p["rung_gap"])
        wood.box((0, y, z), (p["width"], 0.032, 0.032), rot=(-ang, "x"), shift=(0.3 * i, 0.2))
    # the top rung is a wide handrail
    y, z = pt(length + 0.04)
    wood.box((0, y, z), (p["width"] + 0.04, 0.05, 0.04), rot=(-ang, "x"), shift=(0.7, 0.2))
    for sx in (-1, 1):
        x = sx * hw
        yh, zh = pt(length - 0.02)
        brz.box((x, yh + 0.02, zh + 0.02), (0.03, 0.10, 0.012))         # hook plate over the rail
        brz.box((x, 0.014, rz + 0.032), (0.03, 0.012, 0.07))            # lip behind the rail
        brz.box((x, yh * 0.5, zh - 0.01), (0.034, 0.05, 0.05))          # collar on the stile
        fy, fz = pt(0.0)
        brz.box((x, fy - 0.012, 0.014), (0.036, 0.06, 0.028))           # foot cap
    wood.to_object(f"{n}_Wood", col, walnut, root)
    brz.to_object(f"{n}_Bronze", col, bronze, root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
