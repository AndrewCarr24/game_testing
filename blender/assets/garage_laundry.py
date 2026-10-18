"""Mudroom laundry wall: cream lacquer cabinetry with two full-height end units, a
front-loading washer and dryer under an oak worktop, drawer bases, a stainless
undermount sink with a bronze gooseneck tap, a sage tile splashback and wall
cupboards (an open oak shelf with baskets over the machines). Folded towels, a
laundry basket and detergent bottles on the counter.

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

NAME = "GarageLaundry"

P = dict(
    name=NAME,
    modules=(("tall", 0.6), ("washer", 0.64), ("dryer", 0.64), ("drawers", 0.8), ("sink", 0.95),
             ("drawers", 0.8), ("drawers", 0.8), ("tall", 0.6)),
    depth=0.64,
    counter_h=0.92,
    counter_t=0.04,
    tall_h=2.45,
    wall_z0=1.58,
    wall_z1=2.4,
    wall_depth=0.36,
    plinth_h=0.09,
)


def build(**overrides):
    p = {**P, **overrides}
    b = gk.Builder(p["name"])
    grd, al, glow = gk.graphite_dark(), gk.aluminium(), gk.led()
    cream, oak, sage = gk.cream(), gk.oak_light(), gk.sage()
    bronze = materials.bronze()
    steel = materials.steel()
    oat = gk.linen("M_Fabric_Oat", (0.42, 0.37, 0.30))
    ink = gk.linen("M_Fabric_Sage", (0.16, 0.22, 0.16))
    white = common.pbr_material("M_Mudroom_Appliance", (0.66, 0.66, 0.65), roughness=0.3, coat=0.15)
    dark_glass = materials.glass("M_Mudroom_DoorGlass", tint=(0.04, 0.05, 0.06), alpha=0.7, roughness=0.04)
    display = materials.emissive("M_Mudroom_Display", (0.5, 0.8, 1.0), 3.0)
    bottle = common.pbr_material("M_Mudroom_Bottle", (0.55, 0.55, 0.52), roughness=0.25)

    mods = p["modules"]
    W = sum(w for _, w in mods)
    D = p["depth"]
    yf, yb = -D / 2, D / 2
    x0 = -W / 2
    ph, ch, ct = p["plinth_h"], p["counter_h"], p["counter_t"]
    bh = ch - ct                        # carcass top
    g, dt = 0.003, 0.02
    H = p["tall_h"]

    xs = [x0]
    for _, w in mods:
        xs.append(xs[-1] + w)
    # indices of the module run between the tall units
    first = next(i for i, m in enumerate(mods) if m[0] != "tall")
    last = max(i for i, m in enumerate(mods) if m[0] != "tall")
    cx0, cx1 = xs[first], xs[last + 1]

    b.lo_hi("Plinth", (x0 + 0.02, yf + 0.05, 0), (-x0 - 0.02, yb - 0.02, ph), grd, bevel=0)
    b.lo_hi("Carcass", (cx0, yf + dt + 0.004, ph), (cx1, yb, bh), cream, bevel=0)

    sink_x = None
    for i, (kind, w) in enumerate(mods):
        xa, xb = xs[i], xs[i + 1]
        xc = (xa + xb) / 2
        if kind == "tall":
            b.lo_hi(f"Tall{i}_Carcass", (xa, yf + dt + 0.004, ph), (xb, yb, H), cream, bevel=0)
            b.lo_hi(f"Tall{i}_Door0", (xa + g, yf, ph + g), (xb - g, yf + dt, 1.3), cream, bevel=0.002)
            b.lo_hi(f"Tall{i}_Door1", (xa + g, yf, 1.3 + g), (xb - g, yf + dt, H - g), cream, bevel=0.002)
            px = xb - 0.05 if i == 0 else xa + 0.05
            b.box(f"Tall{i}_Pull", (0.014, 0.022, 0.5), (px, yf - 0.01, 1.2), bronze, bevel=0.002, seg=1)
        elif kind in ("washer", "dryer"):
            # white front-loader with a round glass door, control strip and knob
            b.lo_hi(f"{kind}{i}_Body", (xa + 0.01, yf + 0.01, ph), (xb - 0.01, yb - 0.02, bh - 0.002), white, bevel=0.006)
            fy = yf + 0.01
            zc = 0.5
            b.cyl(f"{kind}{i}_Ring", 0.225, 0.03, (xc, fy - 0.005, zc), al, axis="y", seg=24)
            b.cyl(f"{kind}{i}_Glass", 0.19, 0.04, (xc, fy - 0.012, zc), dark_glass, axis="y", seg=24)
            b.cyl(f"{kind}{i}_Drum", 0.15, 0.012, (xc, fy - 0.032, zc), grd, axis="y", seg=20, r2=0.13)
            b.lo_hi(f"{kind}{i}_Panel", (xa + 0.03, fy - 0.006, bh - 0.12), (xb - 0.03, fy, bh - 0.03), grd, bevel=0.003, seg=1)
            b.cyl(f"{kind}{i}_Knob", 0.022, 0.02, (xb - 0.12, fy - 0.014, bh - 0.075), al, axis="y", seg=14)
            b.lo_hi(f"{kind}{i}_Display", (xa + 0.09, fy - 0.012, bh - 0.09), (xa + 0.19, fy - 0.006, bh - 0.065), display, bevel=0, tile=0.25)
        else:
            b.lo_hi(f"Base{i}_Door0", (xa + g / 2, yf, bh - 0.17), (xb - g / 2, yf + dt, bh - g), cream, bevel=0.002) if kind == "drawers" else None
            if kind == "drawers":
                hs = [0.17, 0.26, bh - ph - 0.43 - 3 * g]
                z = bh - g
                for k, h in enumerate(hs):
                    b.lo_hi(f"Drawer{i}_{k}", (xa + g / 2, yf, z - h), (xb - g / 2, yf + dt, z), cream, bevel=0.002)
                    b.box(f"Drawer{i}_{k}_Pull", (w - 0.3, 0.016, 0.014), (xc, yf - 0.008, z - 0.03), bronze, bevel=0.0015, seg=1)
                    z -= h + g
            else:   # sink base: two doors
                sink_x = xc
                for k, sx in enumerate((-1, 1)):
                    xd0 = xa + g / 2 if sx < 0 else xc + g / 2
                    xd1 = xc - g / 2 if sx < 0 else xb - g / 2
                    b.lo_hi(f"Sink_Door{k}", (xd0, yf, ph + g), (xd1, yf + dt, bh - g), cream, bevel=0.002)
                    b.box(f"Sink_Door{k}_Pull", (0.014, 0.016, 0.3), (xc - sx * 0.04, yf - 0.008, bh - 0.3), bronze, bevel=0.0015, seg=1)

    # --- worktop: oak, with a cut-out for the sink (4 slabs around it)
    cl, cr = cx0, cx1
    ty0, ty1 = yf - 0.02, yb
    if sink_x is not None:
        sw, sd = 0.62, 0.38
        sy = (ty0 + ty1) / 2 + 0.02
        sl, sr = sink_x - sw / 2, sink_x + sw / 2
        sb, st_ = sy - sd / 2, sy + sd / 2
        b.lo_hi("Top_L", (cl, ty0, bh), (sl, ty1, ch), oak, bevel=0.002, tile=0.5)
        b.lo_hi("Top_R", (sr, ty0, bh), (cr, ty1, ch), oak, bevel=0.002, tile=0.5)
        b.lo_hi("Top_F", (sl, ty0, bh), (sr, sb, ch), oak, bevel=0.002, tile=0.5)
        b.lo_hi("Top_B", (sl, st_, bh), (sr, ty1, ch), oak, bevel=0.002, tile=0.5)
        # stainless bowl
        b.lo_hi("Sink_Floor", (sl, sb, ch - 0.2), (sr, st_, ch - 0.19), steel, bevel=0, tile=1.0)
        b.lo_hi("Sink_W0", (sl, sb, ch - 0.2), (sl + 0.006, st_, ch - 0.002), steel, bevel=0, tile=1.0)
        b.lo_hi("Sink_W1", (sr - 0.006, sb, ch - 0.2), (sr, st_, ch - 0.002), steel, bevel=0, tile=1.0)
        b.lo_hi("Sink_W2", (sl, sb, ch - 0.2), (sr, sb + 0.006, ch - 0.002), steel, bevel=0, tile=1.0)
        b.lo_hi("Sink_W3", (sl, st_ - 0.006, ch - 0.2), (sr, st_, ch - 0.002), steel, bevel=0, tile=1.0)
        # gooseneck tap
        ty = st_ + 0.06
        pts = common.fillet_polyline([(sink_x, ty, ch), (sink_x, ty, ch + 0.36), (sink_x, ty - 0.17, ch + 0.38),
                                      (sink_x, ty - 0.19, ch + 0.30)], 0.07, segments=6, closed=False)
        b.tube("Tap", pts, 0.012, bronze, res=6)
        b.cyl("Tap_Base", 0.026, 0.02, (sink_x, ty, ch + 0.01), bronze, seg=12)
        b.cyl("Tap_Lever", 0.008, 0.07, (sink_x + 0.035, ty, ch + 0.08), bronze, axis="x", seg=6)
    else:
        b.lo_hi("Top", (cl, ty0, bh), (cr, ty1, ch), oak, bevel=0.002, tile=0.5)

    # --- splashback (sage) and an LED line under the wall units
    wz0, wz1, wd = p["wall_z0"], p["wall_z1"], p["wall_depth"]
    b.lo_hi("Splash", (cl, yb - 0.016, ch), (cr, yb, wz0), sage, bevel=0, tile=0.5)
    wy0 = yb - wd
    # --- wall units: open oak shelf over the machines, cream doors elsewhere
    mach = [i for i, m in enumerate(mods) if m[0] in ("washer", "dryer")]
    ma_ = xs[mach[0]] if mach else cr
    mb_ = xs[mach[-1] + 1] if mach else cr
    for nm, (xa_, xb_) in (("A", (cl, ma_)), ("B", (mb_, cr))):
        if xb_ - xa_ > 0.01:
            b.lo_hi(f"Wall_Carcass{nm}", (xa_, wy0 + dt + 0.004, wz0), (xb_, yb, wz1), cream, bevel=0)
    for i in range(first, last + 1):
        kind, w = mods[i]
        xa, xb = xs[i], xs[i + 1]
        xc = (xa + xb) / 2
        if i in mach:
            continue
        b.lo_hi(f"Wall{i}_Door", (xa + g / 2, wy0, wz0 + g), (xb - g / 2, wy0 + dt, wz1 - g), cream, bevel=0.002)
        b.box(f"Wall{i}_Pull", (w - 0.3, 0.014, 0.014), (xc, wy0 - 0.007, wz0 + 0.05), bronze, bevel=0.0015, seg=1)
    if mach:
        ma, mb = xs[mach[0]], xs[mach[-1] + 1]
        b.lo_hi("Open_Back", (ma, yb - 0.012, wz0), (mb, yb, wz1), sage, bevel=0, tile=0.5)
        b.lo_hi("Open_Shelf", (ma, wy0, (wz0 + wz1) / 2 - 0.01), (mb, yb - 0.012, (wz0 + wz1) / 2 + 0.025), oak, bevel=0.003)
        b.lo_hi("Open_Top", (ma, wy0, wz1 - 0.025), (mb, yb, wz1), cream, bevel=0.003)
        # baskets on the shelf, towels on the lower shelf board
        zs = (wz0 + wz1) / 2 + 0.025
        for k in range(3):
            bx = ma + 0.28 + k * 0.4
            b.lo_hi(f"Basket{k}", (bx - 0.16, wy0 + 0.05, zs), (bx + 0.16, yb - 0.05, zs + 0.17), oat, bevel=0.02, tile=0.25, seg=2)
        for k in range(3):
            tz = wz0 + 0.0 + k * 0.045
            b.lo_hi(f"Towel{k}", (ma + 0.12 + k * 0.01, wy0 + 0.07, tz + 0.0), (ma + 0.5 + k * 0.01, yb - 0.06, tz + 0.045), ink if k % 2 else oat, bevel=0.012, tile=0.25, seg=2)
    b.lo_hi("Under_LED", (cl + 0.03, wy0 + 0.03, wz0 - 0.008), (cr - 0.03, wy0 + 0.05, wz0), glow, bevel=0, tile=1.0)

    # --- things on the counter
    dx = xs[first + 3] + 0.1 if first + 3 < len(xs) else cl + 1.0
    for k in range(4):   # folded towels
        b.lo_hi(f"Fold{k}", (dx, yf + 0.18, ch + k * 0.04), (dx + 0.34, yf + 0.5, ch + 0.04 + k * 0.04), ink if k % 2 else oat, bevel=0.01, tile=0.25, seg=2)
    bx = xs[last] + 0.4
    b.lo_hi("LaundryBasket", (bx - 0.28, yf + 0.1, ch), (bx + 0.28, yf + 0.5, ch + 0.32), oat, bevel=0.03, tile=0.25, seg=3)
    for k, sx in enumerate((-1, 1)):
        b.cyl(f"Bottle{k}", 0.04, 0.2, (sink_x + sx * 0.5 if sink_x else cl + 1, yb - 0.1, ch + 0.1), bottle, seg=10)
        b.cyl(f"Bottle{k}_Cap", 0.022, 0.05, (sink_x + sx * 0.5 if sink_x else cl + 1, yb - 0.1, ch + 0.225), bronze, seg=8)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
