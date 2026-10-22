"""Main-street storefront in the new Blue Ridge mountain style (Highlands NC / Blowing Rock /
Cashiers): a gable front with a deep overhang and an exposed cedar king-post truss, a stacked
ledgestone base, board-and-batten or cedar above, a black-framed storefront with a glass door
and transoms, a flat black steel canopy on tie rods, gooseneck lamps, a pictogram sign and a
blade sign. One or two storeys. A solid shell (dark glass shows a painted interior).

Origin: floor centre at the door sill; front (street) faces -Y. Variants: see VARIANTS
(build(variant=...)).
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import town_common as tc  # noqa: E402

importlib.reload(tc.tt)
importlib.reload(tc)

NAME = "TownShopMountain"

P = dict(
    name=NAME,
    module="town_shop_mountain",
    width=8.0,            # x
    depth=14.0,           # y
    storeys=1,
    storey_h=4.0,         # floor to plate (one storey); +3.0 per extra storey
    pitch=0.75,           # 9/12
    facade="bb_charcoal",
    base="ledgestone",
    base_h=0.55,
    roof="seam_black",
    trim="trim_black",
    timber="cedar",
    sign="cafe",
    blade=None,           # blade-sign kind (None: same as sign)
    glass=("bk_cafe", "bk_cafe", "bk_transom"),
    upper_cell="bk_blinds",
    side_windows=True,
)

VARIANTS = {
    "cafe": dict(facade="bb_charcoal", sign="cafe", glass=("bk_cafe", "bk_cafe", "bk_transom")),
    "outfitter": dict(facade="cedar", sign="outfitter", glass=("bk_display", "bk_shop", "bk_transom"),
                      width=10.0, depth=16.0, storeys=2, upper_cell="bk_office"),
    "boutique": dict(facade="bb_white", trim="trim_black", sign="bar", glass=("bk_display", "bk_display", "bk_transom"),
                     base="fieldstone", roof="seam_green"),
}


def build(**overrides):
    variant = overrides.pop("variant", None)
    p = {**P, **(VARIANTS.get(variant, {}) if variant else {}), **overrides}
    n = p["name"]
    col, root, kit = tc.begin(n, p["module"])
    W, D = p["width"], p["depth"]
    x0, x1, y0, y1 = -W / 2, W / 2, -D / 2, D / 2
    ze = p["storey_h"] + 3.0 * (p["storeys"] - 1)
    ridge = ze + W / 2 * p["pitch"]
    bh = p["base_h"]
    Fa = kit.p("Walls", p["facade"])
    Ba = kit.p("Base", p["base"])
    trim = p["trim"]

    # ---------------------------------------------------------------- front (S)
    gx0, gx1, gz0, gz1 = x0 + 0.9, x1 - 0.9, bh, 3.1
    dw = 1.1
    front_open = [(gx0, gx1, gz0, gz1), (-dw / 2, dw / 2, 0.0, gz0)]
    upper = []
    if p["storeys"] > 1:
        k = 3 if W >= 9 else 2
        for i in range(k):
            a = x0 + W * (i + 0.5) / k
            upper.append((a - 0.6, a + 0.6, 4.3, 6.1))
    tc.wall(Ba, "S", y0, x0, x1, 0.0, bh, front_open)
    tc.wall(Fa, "S", y0, x0, x1, bh, ze, front_open + upper, gable=ridge)
    tc.wbox(kit.p("Cap", "stone"), "S", y0, x0, gx0, bh - 0.04, bh + 0.02, 0, 0.05, skip="back")
    tc.wbox(kit.p("Cap", "stone"), "S", y0, gx1, x1, bh - 0.04, bh + 0.02, 0, 0.05, skip="back")
    # storefront: two glazed bays, the door bay with its transom
    g0, g1, gt = p["glass"]
    tc.glazing(kit, "S", y0, gx0, -dw / 2, gz0, gz1, cells=[g0, "bk_transom"], transom=2.5,
               mullions=[(gx0 - dw / 2) / 2], wall_part=Ba, depth=0.12)
    tc.glazing(kit, "S", y0, dw / 2, gx1, gz0, gz1, cells=[g1, "bk_transom"], transom=2.5,
               mullions=[(gx1 + dw / 2) / 2], wall_part=Ba, depth=0.12)
    tc.glazing(kit, "S", y0, -dw / 2, dw / 2, 2.5, gz1, cell=gt, depth=0.12)
    tc.reveals(Ba, "S", y0, [(-dw / 2, dw / 2, 0.0, 2.5)], 0.12, sill=False)
    tc.door(kit, "S", y0, 0.0, dw, 2.45, leaf="trim_black", trim=trim, style="glass", glass=g0, casing=0.0, depth=0.12)
    for (a0, a1, z0, z1) in upper:
        tc.window(kit, "S", y0, (a0 + a1) / 2, z0, a1 - a0, z1 - z0, cell=p["upper_cell"], trim=trim, wall_part=Fa,
                  casing=0.06)
    # canopy: flat black steel on tie rods, over the storefront
    Cn = kit.p("Canopy", "trim_black")
    cz = 3.35
    Cn.box((gx0 - 0.3, y0 - 1.5, cz), (gx1 + 0.3, y0, cz + 0.14))
    for x in (gx0 + 0.2, gx1 - 0.2):
        Cn.beam((x, y0, cz + 1.2), (x, y0 - 1.45, cz + 0.14), 0.025, 0.025)
    kit.p("CanopyLight", "lamp").face([(gx0, y0 - 1.3, cz - 0.002), (gx1, y0 - 1.3, cz - 0.002), (gx1, y0 - 1.2, cz - 0.002),
                                      (gx0, y0 - 1.2, cz - 0.002)], toward=(0, 0, -1))
    # sign band above the canopy, gooseneck lamps, blade sign
    # the sign stands on the canopy's front edge (lit from goosenecks on the wall)
    sw = min(2.4, W - 3.5)
    sh = sw / 4
    tc.sign(kit, "S", y0 - 1.45, 0.0, cz + 0.16, sw, sh, p["sign"], d=0.0)
    for a in (-sw / 2 - 0.4, sw / 2 + 0.4):
        tc.gooseneck(kit, "S", y0, a, cz + 1.0, arm=0.6)
    tc.blade_sign(kit, "S", y0, x1 - 0.5, 2.6, w=0.8, h=0.4, kind=p["blade"] or p["sign"], arm=0.95)
    # the exposed king-post truss in the front gable, under the overhang
    T = kit.p("Timber", p["timber"])
    yt = y0 - 0.45
    T.box((x0 - 0.1, yt - 0.1, ze - 0.12), (x1 + 0.1, yt + 0.1, ze + 0.12))          # tie beam
    T.box((-0.1, yt - 0.1, ze + 0.12), (0.1, yt + 0.1, ridge - 0.15))                # king post
    for s in (-1, 1):
        T.beam((s * W / 4 * 1.4, yt, ze + 0.1), (0, yt, ze + (ridge - ze) * 0.6), 0.14, 0.14)
    # ---------------------------------------------------------------- sides and back
    sw_open = []
    if p["side_windows"]:
        for yy in (y0 + D * 0.35, y0 + D * 0.7):
            sw_open.append((yy - 0.5, yy + 0.5, 1.2, 2.6))
    for side, plane in (("E", x1), ("W", x0)):
        tc.wall(Ba, side, plane, y0, y1, 0.0, bh)
        tc.wall(Fa, side, plane, y0, y1, bh, ze, sw_open)
        for (a0, a1, z0, z1) in sw_open:
            tc.window(kit, side, plane, (a0 + a1) / 2, z0, a1 - a0, z1 - z0, cell="bk_blinds", trim=trim, wall_part=Fa,
                      casing=0.06)
    back_open = [(x0 + 1.2, x0 + 2.2, 0.0, 2.2), (x1 - 2.4, x1 - 1.2, 1.2, 2.4)]
    tc.wall(Ba, "N", y1, x0, x1, 0.0, bh, back_open)
    tc.wall(Fa, "N", y1, x0, x1, bh, ze, back_open, gable=ridge)
    tc.door(kit, "N", y1, x0 + 1.7, 1.0, 2.2, leaf="metal_galv", trim=trim, wall_part=Ba, casing=0.06)
    tc.reveals(Fa, "N", y1, [(x0 + 1.2, x0 + 2.2, bh, 2.2)], 0.10, sill=False)
    tc.window(kit, "N", y1, x1 - 1.8, 1.2, 1.2, 1.2, cell="bk_blinds", trim=trim, wall_part=Fa, casing=0.06)
    tc.gooseneck(kit, "N", y1, x0 + 1.7, 2.6, arm=0.3)
    tc.hvac(kit, x1 - 1.2, y1 + 0.8)
    tc.meter(kit, "N", y1, x0 + 3.0)
    # roof
    tc.gable_roof(kit, x0, x1, y0, y1, ze, p["pitch"], axis="y", over_eave=0.45, over_gable=0.7, roof=p["roof"],
                  soffit="cedar" if p["timber"] == "cedar" else "trim", fascia=trim)
    for x in (x0 - 0.3, x1 + 0.3):
        tc.downspout(kit, x, y1 - 0.2, ze - 0.1)
    kit.collide((x0, y0, 0), (x1, y1, ze))

    # ---------------------------------------------------------------- LOD1
    far = tc.Far(n)
    far.gable(x0, x1, y0, y1, 0.0, ze, ridge, axis="y", wall=p["facade"], roof=p["roof"], over=0.6)
    far.box((x0, y0, 0), (x1, y1, bh), p["base"], skip="btk")
    far.quad("S", y0, gx0, gx1, gz0, gz1, "window_lit" if "cafe" in g0 else "glass_dark", d=0.02)
    far.quad("S", y0, -dw / 2, dw / 2, 0, gz0, "glass_dark", d=0.02)
    far.box((gx0 - 0.3, y0 - 1.5, cz), (gx1 + 0.3, y0, cz + 0.14), "trim_black", skip="b")
    for (a0, a1, z0, z1) in upper:
        far.quad("S", y0, a0, a1, z0, z1, "glass_dark")
    kit.entrance((0.0, y0 - 0.1, 0.0), "-Y", dw, kind="door", note="closed (glass)")
    kit.entrance((x0 + 1.7, y1 + 0.1, 0.0), "+Y", 1.0, kind="door", note="closed (back)")
    kit.info.update(variant=variant or "default", walk_in=False, storeys=p["storeys"],
                    footprint=[round(x0, 3), round(y0 - 1.5, 3), round(x1 + 0.45, 3), round(y1 + 1.3, 3)])
    parts = tc.finish(kit, col, root, far)
    return root, parts
