"""Library side chair for the reading table: walnut frame with raked rear legs and a
curved top rail, cognac leather seat and back pads on a slim bronze-capped frame.
Origin: floor centre; faces -Y. About 0.5 x 0.55 x 0.92 m."""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import library_kit as kit  # noqa: E402
from library_kit import Mesh, common, materials  # noqa: E402

importlib.reload(kit)

NAME = "LibraryChair"

P = dict(name=NAME, leather="cognac", seat_h=0.46, back_h=0.93, w=0.50, d=0.52, rake=8.0)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    walnut, bronze = materials.walnut(), materials.bronze()
    lea = kit.leather_green() if p["leather"] == "green" else kit.leather_cognac()
    W, D, SH, BH = p["w"], p["d"], p["seat_h"], p["back_h"]
    rake = math.radians(p["rake"])

    wood, brz = Mesh(0.5), Mesh(0.5)
    t = 0.038
    # front legs (tapered), rear legs raking back to the top rail
    for sx in (-1, 1):
        x = sx * (W / 2 - t / 2)
        wood.box((x, -D / 2 + t / 2, (SH - 0.04) / 2), (t, t, SH - 0.04), taper=(1.0, 1.0), shift=(0.1 * sx, 0))
        brz.box((x, -D / 2 + t / 2, 0.007), (t * 0.8, t * 0.8, 0.014))
        # rear leg: raked back so it meets the seat rail at seat height
        h = BH - 0.05
        yb_ = D / 2 - t / 2 - SH * math.tan(rake)
        wood.box((x, yb_ + math.sin(rake) * h * 0.5, h / 2 * math.cos(rake) + 0.004),
                 (t, t, h), rot=(-rake, "x"), shift=(0.3 * sx, 0.4))
        brz.box((x, yb_ - 0.002, 0.007), (t * 0.8, t * 0.8, 0.014))
    # seat rails and back rails
    za = SH - 0.07
    wood.box((0, -D / 2 + t / 2, za), (W - 2 * t, 0.025, 0.09), shift=(0.2, 0.2))
    wood.box((0, D / 2 - t / 2 + 0.01, za), (W - 2 * t, 0.025, 0.09), shift=(0.6, 0.2))
    for sx in (-1, 1):
        wood.box((sx * (W / 2 - t / 2), 0, za), (0.025, D - t, 0.09), shift=(0.1, 0.5))
    # top rail across the rear legs
    ytop = D / 2 - t / 2 + (BH - 0.075 - SH) * math.tan(rake)
    wood.box((0, ytop, BH - 0.075), (W, 0.045, 0.1), rot=(-rake, "x"), shift=(0.1, 0.7))
    wood.to_object(f"{n}_Frame", col, walnut, root)
    brz.to_object(f"{n}_Caps", col, bronze, root)

    # leather: seat pad and back pad
    def pad(name, size, centre, tilt=0.0, crown=None):
        ob = common.mesh_object(name, common.cushion_bmesh(size, cuts=3, edge=0.02, crown=crown or {}), col, lea, root)
        ob.location = centre
        ob.rotation_euler = (tilt, 0, 0)
        common.add_subsurf(ob, levels=1, render_levels=1)
        common.box_uv(ob, tile=0.2)
        return ob

    pad(f"{n}_Seat", (W - 0.02, D - 0.02, 0.06), (0, 0.0, SH - 0.03), crown={"+z": 0.014})
    yb = D / 2 - t / 2 + 0.3 * math.tan(rake) - 0.03
    pad(f"{n}_Back", (W - 0.1, 0.035, 0.32), (0, yb + 0.01, SH + 0.3), tilt=-rake, crown={})
    kit.merge_objects([o for o in root.children if o.name in (f"{n}_Seat", f"{n}_Back")], f"{n}_Leather", col, root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
