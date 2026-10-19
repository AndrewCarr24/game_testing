"""Library side chair for the reading table: walnut frame with tapered front legs, raked
rear legs, aprons and a low H-stretcher, a walnut back board carrying a cognac leather
back pad, a welted leather seat pad, bronze shoes; every frame edge is chamfered.
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


def grain_uv(ob):
    """The walnut map's grain runs along v; kit.Mesh puts u along a part's length."""
    for d in ob.data.uv_layers["UVMap"].data:
        pass  # the walnut scan is rotated so its grain runs along u (polyhaven_textures ROTATE): no swap


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
    pad_t = 0.05
    z_rail_top = SH - pad_t                       # the seat pad sits on the rails
    rail_h = 0.075
    # front legs: tapered toward the floor, up to the underside of the seat pad
    for sx in (-1, 1):
        x = sx * (W / 2 - t / 2)
        h = z_rail_top
        wood.box((x, -D / 2 + t / 2, h / 2), (t * 0.74, t * 0.74, h), taper=(1.35, 1.35), shift=(0.1 * sx, 0))
        brz.box((x, -D / 2 + t / 2, 0.006), (t * 0.62, t * 0.62, 0.012))
        # rear leg: raked back so it passes the seat rail at seat height and carries the back
        h = BH - 0.02
        yb_ = D / 2 - t / 2 - SH * math.tan(rake)
        wood.box((x, yb_ + math.sin(rake) * h * 0.5, h / 2 * math.cos(rake) + 0.004),
                 (t, t, h), rot=(-rake, "x"), shift=(0.3 * sx, 0.4))
        brz.box((x, yb_ - 0.002, 0.006), (t * 0.8, t * 0.8, 0.012))
    # seat rails (aprons) and a low H-stretcher
    za = z_rail_top - rail_h / 2
    wood.box((0, -D / 2 + t / 2, za), (W - 2 * t, 0.022, rail_h), shift=(0.2, 0.2))
    wood.box((0, D / 2 - t / 2, za), (W - 2 * t, 0.022, rail_h), shift=(0.6, 0.2))
    for sx in (-1, 1):
        wood.box((sx * (W / 2 - t / 2), 0, za), (0.022, D - t, rail_h), shift=(0.1, 0.5))
        wood.box((sx * (W / 2 - t / 2), -0.01, 0.15), (0.018, D - t - 0.02, 0.026), shift=(0.3, 0.1))
    wood.box((0, -0.01, 0.15), (W - 2 * t, 0.018, 0.022), shift=(0.5, 0.3))
    # back board between the rear legs, raked with them; the leather pad is on its face
    zb0, zb1 = SH + 0.14, BH - 0.015
    zc_b = (zb0 + zb1) / 2
    yb_c = D / 2 - t / 2 + (zc_b - SH) * math.tan(rake)
    wood.box((0, yb_c, zc_b), (W - 2 * t + 0.004, 0.016, zb1 - zb0), rot=(-rake, "x"), shift=(0.1, 0.7))
    frame = wood.to_object(f"{n}_Frame", col, walnut, root)
    grain_uv(frame)
    common.add_bevel(frame, 0.0025, segments=1)
    caps = brz.to_object(f"{n}_Caps", col, bronze, root)

    # leather: a welted seat pad (stops at the rear legs) and a back pad on the board
    import library_armchair as la
    pads = []

    def pad(name, size, centre, cuts, drop, crown, tilt=0.0, welt=None):
        ob = common.mesh_object(name, la.cushion_bm(size, cuts, 0.016, crown, drop), col, lea, root)
        ob.location = centre
        ob.rotation_euler = (tilt, 0, 0)
        common.add_subsurf(ob, levels=1, render_levels=1)
        common.box_uv(ob, tile=0.2)
        pads.append(ob)
        if welt:
            w = common.tube_object(f"{name}_Welt", la.welt_points(size, welt, 0.016), 0.0035, col, lea, root,
                                   closed=True, profile_res=1)
            w.location = centre
            w.rotation_euler = (tilt, 0, 0)
            common.box_uv(w, tile=0.2)
            pads.append(w)

    y0, y1 = -D / 2 - 0.004, D / 2 - t - 0.002
    pad(f"{n}_Seat", (W - 0.008, y1 - y0, pad_t), (0, (y0 + y1) / 2, SH - pad_t / 2), (3, 3, 2), ("-z",),
        {"+z": 0.012, "-y": 0.004}, welt="+z")
    bt = 0.03
    yp = yb_c - (0.008 + bt / 2) * math.cos(rake)
    zp = zc_b + 0.012 - (0.008 + bt / 2) * math.sin(rake) * 0
    pad(f"{n}_Back", (W - 2 * t - 0.03, bt, zb1 - zb0 - 0.035), (0, yp, zp), (3, 2, 3), ("+y",),
        {"-y": 0.01}, tilt=-rake)
    kit.merge_objects(pads, f"{n}_Leather", col, root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
