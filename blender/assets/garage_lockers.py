"""Mudroom locker wall: four bays between cream lacquer partitions. Each bay has a
sage-painted back panel with an oak hook rail (bronze hooks, a coat and a bag hung
on them), an oak bench seat with a linen cushion, open shoe cubbies below holding
trainers and boots, and a cream cupboard above with a bronze pull.

Units are metres. The front faces -Y (back at +Y against the wall), the origin is
the floor centre.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import garage_cabinets as gk  # noqa: E402

importlib.reload(gk)
common, materials = gk.common, gk.materials

NAME = "GarageLockers"

P = dict(
    name=NAME,
    bays=4,
    bay_w=1.0,
    depth=0.56,
    height=2.5,
    part_t=0.025,
    bench_z=0.46,         # top of the oak seat
    seat_t=0.04,
    rail_z=1.62,
    cup_z0=1.95,
    coats=(0, 1, 0, 1),   # which bays carry a coat (variation by index parity)
    palette=0,
)

COATS = [
    [((0.06, 0.10, 0.19), "M_Coat_Navy"), ((0.35, 0.22, 0.10), "M_Coat_Camel")],
    [((0.16, 0.19, 0.10), "M_Coat_Olive"), ((0.14, 0.14, 0.15), "M_Coat_Grey")],
]


def build(**overrides):
    p = {**P, **overrides}
    b = gk.Builder(p["name"])
    grd, al = gk.graphite_dark(), gk.aluminium()
    cream, oak, sage = gk.cream(), gk.oak_light(), gk.sage()
    bronze = materials.bronze()
    oat = gk.linen("M_Fabric_Oat", (0.42, 0.37, 0.30))
    leather = common.pbr_material("M_Garage_Leather", (0.30, 0.17, 0.09), roughness=0.55)
    rubber = common.pbr_material("M_Garage_Tyre", (0.012, 0.012, 0.013), roughness=0.85)
    white = gk.white_lacquer()

    N, bw, D, H, pt = p["bays"], p["bay_w"], p["depth"], p["height"], p["part_t"]
    W = N * bw + (N + 1) * pt
    yf, yb = -D / 2, D / 2
    x0 = -W / 2
    bz, st = p["bench_z"], p["seat_t"]
    ph = 0.07

    # plinth, top, partitions
    b.lo_hi("Plinth", (x0 + 0.02, yf + 0.04, 0), (-x0 - 0.02, yb, ph), grd, bevel=0)
    b.lo_hi("Top", (x0 - 0.005, yf, H - 0.04), (-x0 + 0.005, yb, H), cream, bevel=0.003)
    for i in range(N + 1):
        xa = x0 + i * (bw + pt)
        b.lo_hi(f"Partition{i}", (xa, yf, ph), (xa + pt, yb, H - 0.04), cream, bevel=0.002)

    coat_defs = COATS[p["palette"] % len(COATS)]
    ncoat = 0
    for i in range(N):
        xa = x0 + pt + i * (bw + pt)
        xb = xa + bw
        xc = (xa + xb) / 2
        # back panel (sage) and the oak hook rail
        b.lo_hi(f"Back{i}", (xa, yb - 0.015, ph), (xb, yb, H - 0.04), sage, bevel=0, tile=0.5)
        b.lo_hi(f"Rail{i}", (xa, yb - 0.05, p["rail_z"] - 0.045), (xb, yb - 0.015, p["rail_z"] + 0.045), oak, bevel=0.003)
        for k in range(4):
            hx = xa + 0.14 + k * (bw - 0.28) / 3
            b.cyl(f"Hook{i}_{k}_Stem", 0.007, 0.05, (hx, yb - 0.075, p["rail_z"]), bronze, axis="y", seg=8)
            b.cyl(f"Hook{i}_{k}_Knob", 0.014, 0.022, (hx, yb - 0.095, p["rail_z"]), bronze, axis="y", seg=8, r2=0.009)
        # bench seat (oak) with a linen cushion, a shelf below for shoes
        b.lo_hi(f"Seat{i}", (xa, yf + 0.02, bz - st), (xb, yb - 0.015, bz), oak, bevel=0.004)
        b.lo_hi(f"Cushion{i}", (xa + 0.02, yf + 0.04, bz), (xb - 0.02, yb - 0.1, bz + 0.05), oat, bevel=0.018, tile=0.25, seg=3)
        b.lo_hi(f"Shelf{i}", (xa, yf + 0.04, 0.2), (xb, yb - 0.015, 0.2 + 0.025), oak, bevel=0.003)
        # shoes: trainers on the shelf, boots on the floor
        for k in range(2):
            sx = xa + 0.25 + k * 0.32
            b.box(f"Shoe{i}_{k}_Sole", (0.1, 0.29, 0.03), (sx, yf + 0.27, 0.225 + 0.015), rubber, bevel=0.01, seg=2)
            b.box(f"Shoe{i}_{k}_Upper", (0.09, 0.26, 0.07), (sx, yf + 0.265, 0.225 + 0.065), white if (i + k) % 2 else leather, bevel=0.025, seg=3)
            b.box(f"Boot{i}_{k}_Sole", (0.11, 0.3, 0.03), (sx + 0.0, yf + 0.27, ph + 0.015), rubber, bevel=0.01, seg=2)
            b.box(f"Boot{i}_{k}_Foot", (0.1, 0.27, 0.07), (sx, yf + 0.265, ph + 0.065), leather, bevel=0.025, seg=3)
            b.box(f"Boot{i}_{k}_Shaft", (0.09, 0.1, 0.1), (sx, yf + 0.37, ph + 0.15), leather, bevel=0.02, seg=3)
        # hung items: a coat in odd bays, a tote in even ones
        if p["coats"][i % len(p["coats"])]:
            col, mname = coat_defs[ncoat % 2]
            ncoat += 1
            coat = gk.common.pbr_material(mname, col, roughness=0.9)
            coat_m = materials.fabric(mname, col)
            b.lo_hi(f"Coat{i}_Body", (xc - 0.26, yb - 0.17, 0.78), (xc + 0.26, yb - 0.08, p["rail_z"] - 0.06), coat_m, bevel=0.035, seg=3, tile=0.25)
            for sx in (-1, 1):
                b.lo_hi(f"Coat{i}_Sleeve{sx}", (xc + sx * 0.26 - 0.045 + sx * 0.04, yb - 0.17, 0.82), (xc + sx * 0.26 + 0.045 + sx * 0.04, yb - 0.09, p["rail_z"] - 0.12), coat_m, bevel=0.03, seg=3, tile=0.25)
            b.lo_hi(f"Coat{i}_Hood", (xc - 0.16, yb - 0.14, p["rail_z"] - 0.1), (xc + 0.16, yb - 0.06, p["rail_z"] - 0.01), coat_m, bevel=0.03, seg=3, tile=0.25)
        else:
            b.lo_hi(f"Tote{i}", (xc - 0.17, yb - 0.17, 0.95), (xc + 0.17, yb - 0.09, 1.3), oat, bevel=0.02, seg=3, tile=0.25)
            b.lo_hi(f"Tote{i}_Strap", (xc - 0.012, yb - 0.1, 1.3), (xc + 0.012, yb - 0.085, p["rail_z"] - 0.02), leather, bevel=0.003, seg=1)
        # cupboard above: cream door, bronze pull; dark gap behind
        b.lo_hi(f"Cup{i}_Back", (xa, yb - 0.3, p["cup_z0"]), (xb, yb - 0.015, H - 0.04), grd, bevel=0)
        b.lo_hi(f"Cup{i}_Door", (xa + 0.003, yf + 0.18, p["cup_z0"] + 0.003), (xb - 0.003, yf + 0.2, H - 0.043), cream, bevel=0.002)
        b.box(f"Cup{i}_Pull", (0.16, 0.014, 0.014), (xc, yf + 0.18 - 0.007, p["cup_z0"] + 0.06), bronze, bevel=0.0015, seg=1)
        # a name plate: slim bronze label on the partition side of each bay
        b.box(f"Label{i}", (0.1, 0.004, 0.025), (xc, yf + 0.18 - 0.002, p["cup_z0"] - 0.025), bronze, bevel=0, seg=1, tile=0.25)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
