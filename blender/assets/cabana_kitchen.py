"""Outdoor kitchen: an 8 m limestone counter run (steel fridge, dark metal cabinet fronts and
drawers, sink with tap, built-in grill under a dark hood, side burners) in front of a white
render back wall with a limestone splash, a teak shelf and a hood chimney. Cabinet fronts
face -Y (the cook stands at -Y, looking at the wall). Origin: floor centre of the counter."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cabana_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common

NAME = "CabanaKitchen"

P = dict(
    name=NAME,
    bays=(0.8, 0.8, 1.0, 1.4, 0.8, 0.8, 0.8, 0.8, 0.8),    # 8.0 m: fridge, doors, sink, grill, burner, doors, drawers
    depth=0.66,
    height=0.90,
    wall_h=2.35,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = cc.start(n)
    m = cc.M()
    box, cyl, quad = cc.box, cc.cyl, cc.quad
    bays = p["bays"]
    Ln = sum(bays)
    h = Ln / 2
    d, H = p["depth"], p["height"]
    y0, y1 = -d / 2, d / 2

    # carcass, toe recess, stone top
    box(f"{n}_Plinth", (-h + 0.06, y0 + 0.07, 0.0), (h - 0.06, y1, 0.09), m["dark"], col, root, drop=("-z", "+z", "+y"))
    box(f"{n}_Body", (-h, y0, 0.09), (h, y1, H - 0.05), m["warm_dark"], col, root, step=2.0, drop=("-z", "+z", "+y"))
    box(f"{n}_Top", (-h - 0.04, y0 - 0.06, H - 0.05), (h + 0.04, y1 + 0.04, H), m["stone"], col, root, step=1.35, drop=("-z",))
    # fronts
    x = -h
    for i, w in enumerate(bays):
        xc = x + w / 2
        gap = 0.012
        grill = (i == 3)
        sink = (i == 2)
        steel = (i == 0) or grill
        mat = m["steel"] if steel else m["dark"]
        if sink or (i in (1, 5)):
            leaves = 2 if (sink or i == 1) else 1
            lw = (w - gap * 2) / leaves
            for k in range(leaves):
                a = x + gap + k * lw
                box(f"{n}_Door{i}_{k}", (a + gap / 2, y0 - 0.02, 0.12), (a + lw - gap / 2, y0, H - 0.07), mat, col, root,
                    drop=("-z", "+z", "+y"))
                hx = a + (lw - 0.03 if k == 0 else 0.03)
                box(f"{n}_Pull{i}_{k}", (hx - 0.008, y0 - 0.03, H - 0.30), (hx + 0.008, y0 - 0.02, H - 0.12), m["bronze"], col,
                    root, drop=("-z", "+y"))
        else:
            # drawer stack: three drawers
            rows = (0.12, 0.40, 0.63) if not grill else (0.12, 0.50)
            tops = (0.38, 0.61, H - 0.07) if not grill else (0.48, H - 0.07)
            for k, (za, zb) in enumerate(zip(rows, tops)):
                box(f"{n}_Drawer{i}_{k}", (x + gap, y0 - 0.02, za + 0.005), (x + w - gap, y0, zb - 0.005), mat, col, root,
                    drop=("-z", "+z", "+y"))
                box(f"{n}_DrawerPull{i}_{k}", (xc - 0.18, y0 - 0.035, zb - 0.06), (xc + 0.18, y0 - 0.02, zb - 0.045), m["bronze"],
                    col, root, drop=("-z", "+y"))
        x += w

    # sink (bay 2): steel plate, dark basin, tap
    sx = -h + bays[0] + bays[1] + bays[2] / 2
    box(f"{n}_SinkPlate", (sx - 0.36, -0.20, H), (sx + 0.36, 0.20, H + 0.006), m["steel"], col, root, drop=("-z",))
    box(f"{n}_Basin", (sx - 0.30, -0.15, H + 0.006), (sx + 0.30, 0.15, H + 0.008), m["dark"], col, root, drop=("-z",))
    cyl(f"{n}_TapStem", (sx, 0.22), 0.014, H, H + 0.34, m["steel"], col, root, seg=6, caps=(False, True))
    box(f"{n}_TapArm", (sx - 0.012, 0.0, H + 0.32), (sx + 0.012, 0.23, H + 0.35), m["steel"], col, root, drop=("-z",))

    # grill (bay 3): steel base, lid, control panel, knobs, handle, hood and chimney on the wall
    gx = -h + sum(bays[:3]) + bays[3] / 2
    gw = bays[3] - 0.1
    box(f"{n}_GrillBase", (gx - gw / 2, y0 + 0.02, H), (gx + gw / 2, y1 - 0.04, H + 0.17), m["steel"], col, root,
        drop=("-z",), bevel=0.012)
    box(f"{n}_GrillLid", (gx - gw / 2, y0 + 0.02, H + 0.17), (gx + gw / 2, y1 - 0.04, H + 0.30), m["steel"], col, root,
        drop=("-z",), bevel=0.04)
    box(f"{n}_GrillHandle", (gx - gw / 2 + 0.06, y0 - 0.03, H + 0.20), (gx + gw / 2 - 0.06, y0 + 0.02, H + 0.225), m["dark"],
        col, root, drop=("-z",))
    for k in range(5):
        kx = gx - 0.44 + k * 0.22
        box(f"{n}_Knob{k}", (kx - 0.02, y0 - 0.03, H + 0.05), (kx + 0.02, y0, H + 0.09), m["dark"], col, root, keep=("-y", "+z"))

    # side burner (bay 4): dark glass plate with two burner rings
    bx = -h + sum(bays[:4]) + bays[4] / 2
    box(f"{n}_Burner", (bx - 0.33, -0.22, H), (bx + 0.33, 0.22, H + 0.012), m["dark"], col, root, drop=("-z",))
    for k, dx in enumerate((-0.15, 0.15)):
        cyl(f"{n}_Ring{k}", (bx + dx, 0.0), 0.08, H + 0.012, H + 0.03, m["steel"], col, root, seg=8, caps=(False, True))

    # back wall: white render, limestone splash, teak shelf, hood and chimney
    wy0, wy1, wh = y1 + 0.04, y1 + 0.34, p["wall_h"]
    box(f"{n}_Wall", (-h - 0.3, wy0, 0.0), (h + 0.3, wy1, wh), m["white"], col, root, step=1.5, drop=("-z",))
    box(f"{n}_Splash", (-h, wy0 - 0.03, H), (h, wy0, 1.40), m["stone"], col, root, step=1.5, drop=("-z", "+y"))
    box(f"{n}_WallStone", (-h - 0.3, wy1, 0.0), (h + 0.3, wy1 + 0.04, wh), m["stone"], col, root, step=1.5, drop=("-z", "-y"))
    box(f"{n}_WallCap", (-h - 0.34, wy0 - 0.04, wh), (h + 0.34, wy1 + 0.08, wh + 0.05), m["stone"], col, root, step=2.5, drop=("-z",))
    shx = -h + bays[0] + bays[1] + bays[2] / 2
    box(f"{n}_Shelf", (shx - 1.1, wy0 - 0.26, 1.55), (shx + 1.1, wy0, 1.59), m["teak"], col, root, drop=("-z",))
    box(f"{n}_Shelf2", (shx - 1.1, wy0 - 0.26, 1.90), (shx + 1.1, wy0, 1.94), m["teak"], col, root, drop=("-z",))
    box(f"{n}_Hood", (gx - 0.68, wy0 - 0.50, 1.55), (gx + 0.68, wy0, 2.02), m["dark"], col, root, drop=("-z", "+y"), bevel=0.02)
    box(f"{n}_Chimney", (gx - 0.25, wy0 - 0.30, 2.02), (gx + 0.25, wy0, wh + 0.1), m["dark"], col, root, drop=("-z", "+y"))
    # wall lights: two bronze half-cylinders above the table-side wall
    for k, lx in enumerate((-h + 0.6, h - 0.6)):
        box(f"{n}_Sconce{k}", (lx - 0.05, wy0 - 0.06, 1.7), (lx + 0.05, wy0, 2.0), m["bronze"], col, root, drop=("+y", "-z"))
        box(f"{n}_SconceLit{k}", (lx - 0.04, wy0 - 0.065, 1.7), (lx + 0.04, wy0 - 0.06, 1.95), m["lamp"], col, root, keep=("-y",))
    return cc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
