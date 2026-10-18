"""Double vanity: a floating walnut cabinet (two drawer banks and a centre door) on a
recessed black plinth, a book-matched Calacatta slab top with a thin mitred lip, two
low vessel basins of honed stone with brass drains, and two wall-mounted brass spouts
with lever handles on small back plates (the back of the asset is the wall plane).

Origin: floor centre. The front faces -Y, the wall is at +Y (depth / 2).
"""
import importlib
import math
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import bath_common as bc  # noqa: E402

importlib.reload(common)
importlib.reload(bc)

NAME = "BathVanity"

P = dict(
    name=NAME,
    width=2.9,
    depth=0.58,
    plinth_h=0.10,
    plinth_inset=(0.06, 0.07),     # sides, front
    top_z=0.80,                    # top face of the counter
    top_t=0.04,
    gap=0.003,
    centre_w=0.46,
    basin_dx=0.76,                 # basin centres at +-basin_dx
    basin_r=0.245,
    basin_h=0.12,
)


def basin_profile(r, h, wall=0.014):
    """(r, z) of a shallow bowl: foot, belly, rounded flat rim, sloping inside to a flat bottom."""
    pts = [(0.0, 0.0), (r * 0.52, 0.0), (r * 0.70, 0.006), (r * 0.90, 0.045), (r, 0.092), (r, h - 0.012),
           (r - 0.004, h - 0.004), (r - wall / 2, h), (r - wall + 0.002, h - 0.004), (r - wall, h - 0.012),
           (r - wall - 0.004, h - 0.045), (r * 0.62, 0.032), (r * 0.30, 0.022), (0.0, 0.020)]
    return pts


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    walnut, black, brass = materials.walnut(), materials.black_metal(), bc.brass()
    marble, stone = bc.marble_wall(), bc.stone()

    W, D, ph = p["width"], p["depth"], p["plinth_h"]
    zt, tt, gap = p["top_z"], p["top_t"], p["gap"]
    yb, yf = D / 2, -D / 2                      # back (wall) and front of the cabinet
    top_front_over = 0.02

    # ---- recessed plinth
    pis, pif = p["plinth_inset"]
    bc.box(col, root, f"{n}_Plinth", (W - 2 * pis, D - pif - 0.02, ph), (0, (yf + pif + yb - 0.02) / 2, ph / 2),
           black, bevel=0.003)

    # ---- carcass (solid, behind the fronts) and fronts
    z0, z1 = ph, zt - tt
    cw = W - 0.04
    body = bc.box(col, root, f"{n}_Carcass", (cw, D - 0.03, z1 - z0), (0, yb - (D - 0.03) / 2, (z0 + z1) / 2),
                  walnut, bevel=0.002, uv_tile=0.5)
    ft = 0.022
    yfront = yf + ft / 2 + 0.0
    bank_w = (cw - p["centre_w"] - 4 * gap) / 2
    xs = [(-cw / 2 + gap + bank_w / 2, bank_w, "L"), (0.0, p["centre_w"], "C"), (cw / 2 - gap - bank_w / 2, bank_w, "R")]
    fz0, fz1 = z0 + gap, z1 - gap
    for xc, w, tag in xs:
        if tag == "C":
            panels = [("Door", fz0, fz1)]
        else:
            split = fz0 + (fz1 - fz0) * 0.60
            panels = [("DrawerLow", fz0, split - gap / 2), ("DrawerTop", split + gap / 2, fz1)]
        for nm, a, b in panels:
            f = bc.box(col, root, f"{n}_Front_{tag}_{nm}", (w, ft, b - a), (xc, yfront, (a + b) / 2), walnut,
                       bevel=0.0018, uv_tile=0.5)
            # slim brass edge pull along the top edge of each front
            pw = min(w - 0.12, 0.42) if tag != "C" else 0.0
            if tag == "C":
                bc.box(col, root, f"{n}_Pull_{tag}", (0.012, 0.016, 0.34), (xc + w / 2 - 0.05, yf - 0.004, (a + b) / 2 + 0.05),
                       brass, bevel=0.0035)
            else:
                bc.box(col, root, f"{n}_Pull_{tag}_{nm}", (pw, 0.016, 0.014), (xc, yf - 0.004, b - 0.03), brass, bevel=0.0035)

    # ---- marble top with a lip, slightly proud at the front
    tw, td = W + 0.0, D + top_front_over
    top = bc.box(col, root, f"{n}_Top", (tw, td, tt), (0, yb - td / 2, zt - tt / 2), marble, bevel=0.003, uv_tile=1.0)
    # thin dark shadow reveal between the cabinet and the top
    # ---- basins, drains, spouts
    for sgn, tag in ((-1, "L"), (1, "R")):
        cx = sgn * p["basin_dx"]
        cy = (yf + yb) / 2 + 0.01
        prof = basin_profile(p["basin_r"], p["basin_h"])
        bm = bc.lathe(prof, 56)
        # the profile is one continuous outline (outer up, inner down): closed shell via z order
        b = common.mesh_object(f"{n}_Basin_{tag}", bm, col, stone, root)
        b.location = (cx, cy, zt)
        bc.cylindrical_uv(b, tile=1.0)
        drain = bc.lathe([(0.0, 0.0215), (0.023, 0.0215), (0.025, 0.019), (0.025, 0.016), (0.0, 0.016)], 24)
        d = common.mesh_object(f"{n}_Drain_{tag}", drain, col, brass, root)
        d.location = (cx, cy, zt)
        # wall spout: back plate, tube forward + slight drop, handle
        sz = zt + 0.30
        plate = bc.lathe([(0.0, 0.0), (0.050, 0.0), (0.050, 0.012), (0.0, 0.012)], 32)
        pl = common.mesh_object(f"{n}_SpoutPlate_{tag}", plate, col, brass, root)
        pl.rotation_euler = (math.radians(90), 0, 0)      # axis along -Y
        pl.location = (cx, yb - 0.012, sz)
        pts = [(cx, yb - 0.01, sz), (cx, cy + 0.015, sz), (cx, cy - 0.015, sz), (cx, cy - 0.015, sz - 0.05)]
        pts = common.fillet_polyline([(cx, yb - 0.01, sz), (cx, cy - 0.02, sz), (cx, cy - 0.02, sz - 0.06)], 0.03,
                                     segments=6, closed=False)
        common.tube_object(f"{n}_Spout_{tag}", pts, 0.0105, col, brass, root, closed=False, profile_res=4)
        hb = bmesh.new()
        bc.cylinder_between(hb, (cx + 0.03, yb - 0.012, sz + 0.012), (cx + 0.07, yb - 0.04, sz + 0.012), 0.0065, 12)
        bc.cylinder_between(hb, (cx + 0.07, yb - 0.04, sz + 0.012), (cx + 0.13, yb - 0.048, sz + 0.04), 0.0055, 12)
        common.mesh_object(f"{n}_Lever_{tag}", hb, col, brass, root)

    bc.merge(root, bc.children(root, "_Carcass", "_Front_"), f"{n}_Cabinet")
    bc.merge(root, bc.by_material(root, brass), f"{n}_PipingBrass")
    bc.merge(root, bc.children(root, "_Basin_"), f"{n}_Basins")
    return root, bc.parts_of(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
