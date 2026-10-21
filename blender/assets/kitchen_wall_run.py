"""Kitchen wall of full-height walnut cabinetry, floor to ceiling (4.2 m): a pantry
bank, two integrated steel fridge-freezer columns, a double-oven tower and a run of
base drawers with a Calacatta counter and slab backsplash under lit upper cabinets.

The pantry bank is a hiding spot (prompts/interactivity.md `hide`): a walk-in larder behind its
two tall doors (black lining, high shelves of jars, the doors hung from empties on their hinge
lines); E swings them open, the player steps in and they pull to, leaving a crack to peek through.

Run along X (left = counter end, right = pantry end), 6.7 m long, back against +Y,
fronts face -Y. Origin is the floor centre of the footprint."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitchen_lib as L  # noqa: E402

importlib.reload(L)
common, materials = L.common, L.materials

NAME = "KitchenWallRun"

P = dict(
    name=NAME,
    depth=0.66,
    plinth=0.10,
    counter_z=0.92,
    counter_t=0.04,
    tall_z=2.40,           # top of the lower fronts in the tall zones
    band_z=2.43,           # bottom of the upper band
    top_z=4.19,            # just below the 4.2 m ceiling
    upper_depth=0.38,
    counter=[(0.9, "dr3"), (0.6, "dr1"), (0.9, "d2"), (0.7, "dr3")],   # sink over the 0.9 d2, dishwasher beside
    fridge_w=0.9,
    oven_w=0.8,
    pantry_w=1.0,
    hide=True,             # the pantry is a hiding spot (hollow, doors on hinges)
)


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402  (react definitions, prompts/interactivity.md)

importlib.reload(ix_common)


hinge = L.hinge


def doors(b, p, ovens, fridge):
    """The ovens (and the steam oven) drop open (hinged along the bottom front edge), the two
    fridge columns swing open as a French pair (hinged on their outer edges), all from the -Y fronts."""
    for tag, xm, z0 in ovens:
        L.oven_hinge(b, tag, xm, fridge["yf"], z0)
    for i, (hx, angle) in enumerate(fridge["hinges"]):
        hinge(b, f"Fridge{i}", ("Door", "Handle"), (hx, fridge["yf"], 0.0), {
            "type": "rotate", "axis": common.to_gltf((0, 0, 1)), "angle": angle, "duration": 0.9, "range": 1.6,
            "side": "both", "collide": True, "prompt": "Open fridge", "promptActive": "Close fridge"})


def build(**overrides):
    p = {**P, **overrides}
    b = L.Builder(p["name"])
    walnut = materials.walnut()
    bronze = materials.bronze()
    steel = L.brushed_steel()
    black = L.carcass()
    glass = L.black_glass()
    marble = L.calacatta_mat()
    led = materials.emissive("M_LED_Warm", (1.0, 0.8, 0.55), 4.0)

    D = p["depth"]
    yf = -D / 2
    yb = D / 2
    t = 0.02
    ph = p["plinth"]
    cz, ct = p["counter_z"], p["counter_t"]
    fr = L.Fronts(b, walnut, bronze, yf)
    fr_up = L.Fronts(b, walnut, bronze, yb - p["upper_depth"])

    cw = sum(w for w, _ in p["counter"])
    widths = [("counter", cw), ("oven", p["oven_w"]), ("fridge", 2 * p["fridge_w"]), ("pantry", p["pantry_w"])]
    total = sum(w for _, w in widths)
    x = -total / 2
    xs = {}
    for k, w in widths:
        xs[k] = (x, x + w)
        x += w

    # --- shared plinth (recessed, black) and one carcass block per zone
    b.box("Plinth", (total - 0.04, D - 0.07 - 0.02, ph), (0, (yf + 0.07 + yb - 0.02) / 2 - 0.0, ph / 2),
          black, bevel=0, tile=0)

    def tall_body(k):
        x0, x1 = xs[k]
        b.box(f"{k}_Body", (x1 - x0, yb - (yf + t), p["top_z"] - ph), ((x0 + x1) / 2, (yf + t + yb) / 2, (ph + p["top_z"]) / 2),
              black, bevel=0, tile=0)

    # --- counter zone: drawers, an integrated dishwasher, the sink base and a Calacatta top
    x0, x1 = xs["counter"]
    units = L.span(x0, p["counter"])
    sa, sc, _ = units[2]
    sx = (sa + sc) / 2
    sw, sd = 0.76, 0.42
    sy = yf + 0.06 + sd / 2
    hxa, hxb, hya, hyb = sx - sw / 2, sx + sw / 2, sy - sd / 2, sy + sd / 2
    zs = cz - ct - 0.25
    for tag, a, c, z1_ in (("Counter_BodyL", x0, hxa - 0.03, cz - ct), ("Counter_BodyR", hxb + 0.03, x1, cz - ct),
                           ("Counter_BodySink", hxa - 0.03, hxb + 0.03, zs)):
        b.box(tag, (c - a, yb - (yf + t), z1_ - ph), ((a + c) / 2, (yf + t + yb) / 2, (ph + z1_) / 2),
              black, bevel=0, tile=0)
    for i, (a, c, kind) in enumerate(units):
        fr.unit(kind, a, c, ph, cz - ct, f"Base{i}")
    L.slab_with_holes(b, "Counter_Top", x0, x1, yf - 0.02, yb, cz - ct / 2, ct, [(hxa, hxb, hya, hyb)], marble,
                      bevel=0.003, seg=2, tile=1.5)
    L.undermount_sink(b, "Sink", sx, sy, sw, sd, 0.22, cz - ct, steel, materials.steel(), corner=0.035,
                      drain=(0.18, 0.06))
    L.gooseneck_tap(b, "Tap", sx, hyb + 0.065, cz, bronze, reach=0.34, rise=0.36, lever=1, toward=-1)
    b.box("Backsplash", (x1 - x0, 0.02, p["tall_z"] - cz), ((x0 + x1) / 2, yb - 0.01, (cz + p["tall_z"]) / 2),
          marble, bevel=0.001, tile=1.5, world_uv=True)
    b.box("Upper_Body", (x1 - x0, p["upper_depth"] - t, p["top_z"] - p["tall_z"]),
          ((x0 + x1) / 2, yb - (p["upper_depth"] - t) / 2, (p["tall_z"] + p["top_z"]) / 2), black, bevel=0, tile=0)
    mid = (x0 + x1) / 2
    for i, (a, c) in enumerate(((x0, mid), (mid, x1))):
        fr_up.unit("d2", a, c, p["band_z"], p["top_z"], f"Upper{i}")
    # LED strip under the upper cabinets
    b.box("Counter_LED", (x1 - x0 - 0.1, 0.02, 0.012), ((x0 + x1) / 2, yb - p["upper_depth"] + 0.05, p["tall_z"] - 0.006),
          led, bevel=0, tile=0)
    # open end panel on the visible (left) end of the run
    b.box("EndPanel", (0.03, D + 0.0, p["top_z"]), (x0 - 0.015 + 0.0, 0.0, p["top_z"] / 2),
          walnut, bevel=0.002, seg=1, shift=(0.5, 0.1))

    # --- oven tower: carcass above and below; between them a black fascia with the oven
    #     cavities set into it, behind three steel doors with smoked windows
    x0, x1 = xs["oven"]
    xm = (x0 + x1) / 2
    zlo, zhi = 0.53, 2.23
    for tag, za_, zb_ in (("oven_BodyLow", ph, zlo), ("oven_BodyHigh", zhi, p["top_z"])):
        b.box(tag, (x1 - x0, yb - (yf + t), zb_ - za_), (xm, (yf + t + yb) / 2, (za_ + zb_) / 2), black, bevel=0, tile=0)
    b.box("oven_Back", (x1 - x0, 0.02, zhi - zlo), (xm, yb - 0.01, (zlo + zhi) / 2), black, bevel=0, tile=0)
    b.box("oven_SideL", (0.02, yb - (yf + t), zhi - zlo), (x0 + 0.01, (yf + t + yb) / 2, (zlo + zhi) / 2), black,
          bevel=0, tile=0)
    fr.unit("dr1", x0, x1, ph, 0.52, "OvenDrawer")
    ow = x1 - x0 - 0.04
    oglass = L.oven_glass()
    band = L.black_glass()
    cavity = L.dark_glaze()
    polished = materials.steel()
    holes = []
    for tag, z0_, z1_, dep in (("OvenA", 0.54, 1.14, 0.42), ("OvenB", 1.16, 1.76, 0.42), ("Steam", 1.78, 2.22, 0.36)):
        xa, xb, za, zb = L.oven_door(b, tag, xm - ow / 2, xm + ow / 2, z0_, z1_, yf, steel, oglass, band, led, steel,
                                     band=0.08 if tag != "Steam" else 0.07)
        holes.append((xa - 0.004, xb + 0.004, za - 0.004, zb + 0.004))
        L.oven_cavity(b, tag, xa - 0.004, xb + 0.004, za - 0.004, zb + 0.004, yf + t + 0.012, dep, cavity, polished,
                      racks=2 if tag != "Steam" else 1)
    L.panel_with_holes(b, "oven_Fascia", x0, x1, zlo, zhi, yf + t, 0.012, holes, black, bevel=0, seg=1)
    fr.slab("OvenFiller", x0, x1, 2.24, p["tall_z"])
    fr_t = L.Fronts(b, walnut, bronze, yf)
    fr_t.unit("d1", x0, x1, p["band_z"], p["top_z"], "OvenUpper")

    # --- fridge columns (integrated, steel): solid carcass above the doors; below them a black
    #     fascia round two lit cavities (kitchen_lib.fridge_interior), seen with the doors open
    x0, x1 = xs["fridge"]
    fw = p["fridge_w"]
    tz = p["tall_z"]
    b.box("fridge_Body", (x1 - x0, yb - (yf + t), p["top_z"] - tz), ((x0 + x1) / 2, (yf + t + yb) / 2, (tz + p["top_z"]) / 2),
          black, bevel=0, tile=0)
    y_in = yf + 0.027                    # just behind the doors (0.026 thick)
    fz0, fz1 = ph + 0.05, tz - 0.06
    holes = [(a + 0.035, a + fw - 0.035, fz0, fz1) for a in (x0, x0 + fw)]
    L.panel_with_holes(b, "fridge_Fascia", x0, x1, ph, tz, y_in, 0.012, holes, black, bevel=0, seg=1)
    contents = [
        [[("milk", 0.12), ("milk", 0.22), ("tub", 0.45), ("tub", 0.66)],
         [("jars", 0.1), ("water", 0.55), ("water", 0.66)],
         [("wine", 0.12), ("wine", 0.22), ("wine", 0.32), ("tub", 0.6)],
         [("tub", 0.15), ("jars", 0.45)], []],
        [[("tub", 0.15), ("tub", 0.38), ("water", 0.62)],
         [("wine", 0.1), ("milk", 0.25), ("jars", 0.42)],
         [("tub", 0.2), ("tub", 0.42), ("milk", 0.68)],
         [("water", 0.12), ("water", 0.23)], []],
    ]
    for i, (xa, xb, za, zb) in enumerate(holes):
        L.fridge_interior(b, f"FridgeInner{i}", xa, xb, za, zb, y_in + 0.012, yb - 0.03 - (y_in + 0.012), contents[i],
                          seed=5 + i)
    for i, (a, c) in enumerate(((x0, x0 + fw), (x0 + fw, x1))):
        b.box(f"Fridge{i}_Door", (fw - 0.004, 0.026, p["tall_z"] - ph - 0.004), ((a + c) / 2, yf + 0.013, (ph + p["tall_z"]) / 2),
              steel, bevel=0.003, seg=2, tile=0)
        # long steel bar handle near the meeting edge
        hx = (x0 + fw) + (-0.045 if i == 0 else 0.045)
        fr.vbar(f"Fridge{i}_Handle", hx, 0.75 if i == 0 else 0.85, 1.9, r=0.011, stand=0.04)
        fr_t.unit("d1", a, c, p["band_z"], p["top_z"], f"FridgeUpper{i}")
    # narrow dark vents at the foot
    b.box("Fridge_Grille", (2 * fw - 0.1, 0.006, 0.05), ((x0 + x1) / 2, yf + 0.06, ph - 0.015), black, bevel=0, tile=0)

    # --- pantry bank
    x0, x1 = xs["pantry"]
    if p["hide"]:
        larder(b, p, x0, x1, yf + t, yb, black, walnut, "pantry")
    else:
        tall_body("pantry")
    fr.unit("d2", x0, x1, ph, p["tall_z"], "Pantry")
    fr_t.unit("d2", x0, x1, p["band_z"], p["top_z"], "PantryUpper")

    # interactivity: ovens and fridge doors open; the under-cabinet LED follows the lights,
    # the oven displays the power
    xo = (xs["oven"][0] + xs["oven"][1]) / 2
    x0f, x1f = xs["fridge"]
    doors(b, p, [("OvenA", xo, 0.54), ("OvenB", xo, 1.16), ("Steam", xo, 1.78)],
          dict(yf=yf, hinges=[(x0f, -90), (x1f, 90)]))
    ix_common.tag_emissive(b.root)
    ix_common.tag_emissive(b.root, "power", names=("Display", "FridgeLight"))
    if p["hide"]:
        hiding(b, x0, x1, yf, t, "Pantry", {walnut.name: "Leaf", bronze.name: "Pull"})
    return b.finish()


def larder(b, p, x0, x1, y0, y1, black, walnut, tag):
    """A tall bank hollow behind its doors (a walk-in larder; also kitchen_pantry's): black lining
    (back, sides, a floor over the plinth), the upper cupboard solid above the doors, two high
    walnut shelves of jars at the back. Parts are `<tag>_*`."""
    ph, tz, top = p["plinth"], p["tall_z"], p["top_z"]
    xc, w, d, lt = (x0 + x1) / 2, x1 - x0, y1 - y0, 0.018
    b.box(f"{tag}_Back", (w, lt, tz - ph), (xc, y1 - lt / 2, (ph + tz) / 2), black, bevel=0, tile=0)
    for k, x in (("L", x0 + lt / 2), ("R", x1 - lt / 2)):
        b.box(f"{tag}_Side{k}", (lt, d - lt, tz - ph), (x, y0 + (d - lt) / 2, (ph + tz) / 2), black, bevel=0, tile=0)
    b.box(f"{tag}_Floor", (w - 2 * lt, d - lt, 0.02), (xc, y0 + (d - lt) / 2, ph + 0.01), black, bevel=0, tile=0)
    b.box(f"{tag}_BodyUpper", (w, d, top - tz), (xc, y0 + d / 2, (tz + top) / 2), black, bevel=0, tile=0)
    sd = 0.24
    jars = []
    for i, z in enumerate((1.92, 2.18)):
        b.box(f"{tag}_Shelf{i}", (w - 2 * lt, sd, 0.022), (xc, y1 - lt - sd / 2, z), walnut, bevel=0.0015, shift=(0.3 * i, 0.5))
        for j, (dx, h) in enumerate(((-0.33, 0.16), (-0.18, 0.2), (0.0, 0.14), (0.17, 0.19), (0.32, 0.15))):
            if (i + j) % 4 == 3:
                continue
            jars.append((xc + dx, y1 - lt - sd / 2, z + 0.011, h))
    glass = L.black_glass()
    for k, (x, y, z, h) in enumerate(jars):
        r = 0.045 + 0.01 * (k % 2)
        b.lathe(f"{tag}_Jar{k}", [(0.0, 0.0), (r, 0.0), (r, h * 0.86), (r * 0.7, h * 0.9), (r * 0.7, h), (0.0, h)],
                glass, loc=(x, y, z), segs=14, uv_tile=0)


def hiding(b, x0, x1, yf, t, tag, names):
    """Hang a tall 'd2' unit's two doors (`<tag>_DoorL/R`, each with its pull) from empties on
    their outer hinge lines, merged per material (`names`: material -> suffix), and make the larder
    behind them a hiding spot: the eye a hand behind the doors, the exit in front."""
    xc, root, col, n = (x0 + x1) / 2, b.root, b.col, b.n
    doors = []
    for side, hx, sx in (("L", x0, -1), ("R", x1, 1)):
        parts = [o for o in root.children if o.name in (f"{n}_{tag}_Door{side}", f"{n}_{tag}_Pull{side}")]
        pv = ix_common.pivot(root, col, f"{n}_{tag}Door{side}", (hx, yf, 0.0), parts)
        ix_common.merge_parts(pv, names)
        doors.append((pv, sx * 100, sx * 10))
    ix_common.hide_spot(root, col, f"{n}_{tag}", (xc, yf + t + 0.15, 1.6), [(xc, yf - 0.55, 0.0), (xc, yf - 0.85, 0.0)],
                        "Hide in the pantry", "Leave the pantry", doors=doors, pitch=-4)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
