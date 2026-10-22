"""Street furniture and small props of the town kit (instanced, <= 1.5k triangles each). Not an
asset: each prop is exported by a thin module town_<prop>.py that calls build("<prop>").

Every prop: origin at the centre of its footprint on the ground, front -Y, one LOD1 (its
bounding box in the dominant swatch), colliders. The too-tidy street furniture: black
powder-coated steel, cedar slats, fresh paint.
"""
import importlib
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import town_common as tc  # noqa: E402

importlib.reload(tc.tt)
importlib.reload(tc)
V = tc.V
PROPS = {}


def prop(name, far_key="trim_black"):
    def deco(fn):
        PROPS[name] = (fn, far_key)
        return fn
    return deco


# ---------------------------------------------------------------- street lighting

@prop("streetlight")
def _streetlight(kit, basket=False):
    """Downtown acorn lamp post, 4.5 m: fluted cast base, a slim shaft, an acorn globe (glow)
    under a finial cap; basket=True adds an arm with a hanging flower basket."""
    B = kit.p("Post", "trim_black")
    B.cyl((0, 0), 0.24, 0.0, 0.12, sides=8, caps="t")
    B.cyl((0, 0), 0.2, 0.12, 0.9, sides=8, caps="", r1=0.12)
    B.cyl((0, 0), 0.14, 0.9, 1.0, sides=8, caps="t")
    B.cyl((0, 0), 0.07, 1.0, 3.6, sides=8, caps="", r1=0.055)
    B.cyl((0, 0), 0.13, 3.6, 3.72, sides=8, caps="tb")
    G = kit.p("Globe", "glow_white")
    G.cyl((0, 0), 0.12, 3.72, 3.8, sides=10, caps="", r1=0.21)
    G.cyl((0, 0), 0.21, 3.8, 4.15, sides=10, caps="", r1=0.2)
    G.cyl((0, 0), 0.2, 4.15, 4.28, sides=10, caps="", r1=0.12)
    B.cyl((0, 0), 0.15, 4.28, 4.38, sides=8, caps="t", r1=0.1)
    B.cyl((0, 0), 0.03, 4.38, 4.5, sides=5, caps="t", r1=0.005)
    kit.collide((-0.24, -0.24, 0), (0.24, 0.24, 3.6))
    if basket:
        B.beam(V(0, 0, 3.2), V(0.75, 0, 3.2), 0.03, 0.03)
        B.beam(V(0, 0, 2.9), V(0.6, 0, 3.2), 0.02, 0.02)
        B.tube(V(0.75, 0, 3.2), V(0.75, 0, 2.95), 0.006, 3)
        basket_geom(kit, 0.75, 0.0, 2.55)


def basket_geom(kit, x, y, z):
    kit.p("Basket", "trim_black").cyl((x, y), 0.28, z, z + 0.32, sides=8, caps="b", r1=0.34)
    rng = random.Random(3)
    for k in range(14):
        a = 2 * math.pi * k / 14 + rng.uniform(-0.2, 0.2)
        r = rng.uniform(0.15, 0.38)
        colr = ("trim_green", "door_red", "neon_pink" if False else "trim_red", "paint_white", "trim_green", "paint_yellow")[k % 6]
        cx, cy = x + r * math.cos(a), y + r * math.sin(a)
        dz = -rng.uniform(0.0, 0.35) if r > 0.3 else 0.0
        kit.p("Blooms", colr).cbox((cx, cy, z + 0.38 + dz), (0.14, 0.14, 0.14))
    kit.p("Blooms", "trim_green").cyl((x, y), 0.33, z + 0.3, z + 0.48, sides=8, caps="t", r1=0.2)


@prop("flower_basket", "trim_green")
def _flower_basket(kit):
    """A hanging flower basket (for a lamp arm or a porch beam): the hook at the origin's top
    (z = 0.75 above the basket's bottom)."""
    basket_geom(kit, 0.0, 0.0, 0.0)
    for k in range(3):
        a = 2 * math.pi * k / 3
        kit.p("Chains", "trim_black").tube(V(0.3 * math.cos(a), 0.3 * math.sin(a), 0.32), V(0, 0, 0.75), 0.005, 3)


@prop("highway_light", "metal_galv")
def _highway_light(kit):
    """Cobra-head pole for the highway end, 10 m: a galvanised tapered pole, a davit arm, an
    LED head (its lens glows)."""
    G = kit.p("Pole", "metal_galv")
    kit.p("Base", "concrete").cyl((0, 0), 0.35, 0.0, 0.5, sides=8)
    G.cyl((0, 0), 0.13, 0.5, 9.4, sides=8, caps="", r1=0.08)
    G.polyline([V(0, 0, 9.2), V(0.4, 0, 9.85), V(1.2, 0, 10.0), V(2.2, 0, 10.0)], 0.05, sides=6)
    H = kit.p("Head", "metal_galv")
    H.box((2.1, -0.22, 9.85), (2.95, 0.22, 10.05))
    kit.p("Lens", "glow_white").face([(2.15, -0.18, 9.845), (2.9, -0.18, 9.845), (2.9, 0.18, 9.845), (2.15, 0.18, 9.845)],
                                     toward=(0, 0, -1))
    kit.collide((-0.35, -0.35, 0), (0.35, 0.35, 9.4))


# ---------------------------------------------------------------- street furniture

@prop("bench", "trim_brown")
def _bench(kit):
    """Park bench, 1.8 m: black cast ends, cedar seat and back slats, an armrest each end."""
    S = kit.p("Slats", "cedar")
    for k in range(4):
        S.box((-0.9, -0.25 + k * 0.11, 0.44), (0.9, -0.17 + k * 0.11, 0.47))
    for k in range(3):
        z = 0.58 + k * 0.13
        S.box((-0.9, 0.2 + k * 0.03, z), (0.9, 0.23 + k * 0.03, z + 0.09))
    E = kit.p("Ends", "trim_black")
    for x in (-0.8, 0.8):
        E.box((x - 0.03, -0.27, 0.0), (x + 0.03, -0.2, 0.44))
        E.box((x - 0.03, 0.17, 0.0), (x + 0.03, 0.24, 0.95))
        E.box((x - 0.03, -0.27, 0.4), (x + 0.03, 0.24, 0.44))
        E.box((x - 0.035, -0.3, 0.64), (x + 0.035, 0.2, 0.68))
        E.box((x - 0.03, -0.28, 0.44), (x + 0.03, -0.24, 0.66))
    kit.collide((-0.9, -0.3, 0), (0.9, 0.3, 0.47))


@prop("planter", "trim_green")
def _planter(kit):
    """A square planter (0.9 m), black steel with cedar cladding, clipped boxwood and flowers."""
    kit.p("Box", "cedar").box((-0.45, -0.45, 0.0), (0.45, 0.45, 0.7), skip="b")
    kit.p("Rim", "trim_black").box((-0.48, -0.48, 0.7), (0.48, 0.48, 0.75))
    kit.p("Box", "trim_black").box((-0.47, -0.47, 0.0), (0.47, 0.47, 0.08), skip="b")
    kit.p("Soil", "soot").face([(-0.42, -0.42, 0.74), (0.42, -0.42, 0.74), (0.42, 0.42, 0.74), (-0.42, 0.42, 0.74)], toward=(0, 0, 1))
    kit.p("Shrub", "trim_green").cyl((0, 0), 0.32, 0.74, 1.15, sides=8, caps="t", r1=0.22)
    rng = random.Random(7)
    for k in range(10):
        a = 2 * math.pi * k / 10
        kit.p("Blooms", ("door_red", "paint_white", "trim_red")[k % 3]).cbox((0.36 * math.cos(a), 0.36 * math.sin(a),
                                                                               0.8 + rng.uniform(0, 0.08)), (0.1, 0.1, 0.1))
    kit.collide((-0.48, -0.48, 0), (0.48, 0.48, 0.75))


@prop("bollard")
def _bollard(kit):
    kit.p("Bollard", "trim_black").cyl((0, 0), 0.11, 0.0, 0.85, sides=8, caps="", r1=0.1)
    kit.p("Bollard", "trim_black").cyl((0, 0), 0.12, 0.85, 0.95, sides=8, caps="t", r1=0.06)
    kit.p("Band", "paint_white").cyl((0, 0), 0.112, 0.7, 0.76, sides=8, caps="")
    kit.collide((-0.12, -0.12, 0), (0.12, 0.12, 0.95))


@prop("trash_can")
def _trash_can(kit):
    """A black steel litter bin with a domed lid, cedar slats (and no litter)."""
    kit.p("Can", "trim_black").cyl((0, 0), 0.3, 0.0, 0.95, sides=10, caps="")
    for k in range(10):
        a = 2 * math.pi * (k + 0.5) / 10
        kit.p("Slats", "cedar").box((0.3 * math.cos(a) - 0.04, 0.3 * math.sin(a) - 0.04, 0.12),
                                    (0.3 * math.cos(a) + 0.04, 0.3 * math.sin(a) + 0.04, 0.85))
    kit.p("Lid", "trim_black").cyl((0, 0), 0.33, 0.95, 1.1, sides=10, caps="t", r1=0.18)
    kit.collide((-0.33, -0.33, 0), (0.33, 0.33, 1.1))


# ---------------------------------------------------------------- drive-through, gas station

@prop("menu_board", "trim_black")
def _menu_board(kit):
    """The drive-through menu-board pylon (two lit panels: blank menu rows and a burger
    pictogram) on a stone base, a speaker post with a small canopy beside it."""
    M = kit.p("Board", "trim_black")
    M.box((-1.35, -0.12, 0.6), (1.35, 0.12, 2.7))
    kit.p("Base", "ledgestone").box((-1.45, -0.25, 0.0), (1.45, 0.25, 0.6), skip="b")
    for k, kind in enumerate(("burger", "cafe")):
        a = -0.65 + k * 1.3
        kit.p("Panels", "signs", glow=True).face([(a - 0.6, -0.125, 1.95), (a + 0.6, -0.125, 1.95), (a + 0.6, -0.125, 2.55),
                                                  (a - 0.6, -0.125, 2.55)], uvs=tc.sign_uv(kind), toward=(0, -1, 0))
        kit.p("Panels", "glow_white").face([(a - 0.6, -0.125, 0.75), (a + 0.6, -0.125, 0.75), (a + 0.6, -0.125, 1.85),
                                            (a - 0.6, -0.125, 1.85)], toward=(0, -1, 0))
        for r in range(6):
            z = 0.85 + r * 0.17
            kit.p("Rows", "trim_black").face([(a - 0.5, -0.127, z), (a + 0.3, -0.127, z), (a + 0.3, -0.127, z + 0.05),
                                              (a - 0.5, -0.127, z + 0.05)], toward=(0, -1, 0))
            kit.p("Rows", "trim_red").face([(a + 0.38, -0.127, z), (a + 0.52, -0.127, z), (a + 0.52, -0.127, z + 0.05),
                                            (a + 0.38, -0.127, z + 0.05)], toward=(0, -1, 0))
    kit.collide((-1.45, -0.25, 0), (1.45, 0.25, 2.7))
    S = kit.p("Speaker", "trim_black")
    S.box((1.9, -0.2, 0.0), (2.25, 0.15, 1.45), skip="b")
    S.box((1.8, -0.35, 1.9), (2.35, 0.3, 1.98))
    S.box((2.05, 0.05, 1.45), (2.1, 0.12, 1.9))
    kit.p("Speaker", "neon_amber").box((1.95, -0.205, 1.2), (2.2, -0.2, 1.3))
    kit.p("Speaker", "screen").face([(1.95, -0.205, 0.8), (2.2, -0.205, 0.8), (2.2, -0.205, 1.1), (1.95, -0.205, 1.1)], toward=(0, -1, 0))
    kit.collide((1.9, -0.2, 0), (2.25, 0.15, 1.45))


@prop("clearance_bar", "paint_yellow")
def _clearance_bar(kit):
    """The drive-through clearance gantry: yellow posts, a bar at 2.9 m with black bands, a
    hanging height chain."""
    G = kit.p("Gantry", "paint_yellow")
    for x in (-2.0, 2.0):
        G.box((x - 0.08, -0.08, 0.0), (x + 0.08, 0.08, 3.1), skip="b")
        kit.collide((x - 0.08, -0.08, 0), (x + 0.08, 0.08, 3.1))
    G.box((-2.0, -0.07, 2.85), (2.0, 0.07, 3.0))
    for x in (-1.2, -0.4, 0.4, 1.2):
        kit.p("Bands", "trim_black").box((x - 0.2, -0.075, 2.85), (x + 0.2, 0.075, 3.0))
    kit.p("Chain", "metal_galv").tube(V(0, 0, 2.85), V(0, 0, 2.45), 0.01, 3)


@prop("pump", "paint_white")
def _pump(kit):
    """A fuel dispenser on its island end (the same as the gas station's)."""
    import town_gas_station as g
    importlib.reload(g)
    g.dispenser(kit, 0.0, 0.0)


@prop("ice_chest", "plastic_white")
def _ice_chest(kit):
    kit.p("Chest", "plastic_white").box((-1.0, -0.4, 0.0), (1.0, 0.4, 1.2), skip="b")
    kit.p("Chest", "glow_cool").face([(-0.8, -0.405, 0.85), (0.8, -0.405, 0.85), (0.8, -0.405, 1.1), (-0.8, -0.405, 1.1)], toward=(0, -1, 0))
    for x in (-0.5, 0.5):
        kit.p("Handles", "chrome").box((x - 0.15, -0.43, 0.6), (x + 0.15, -0.4, 0.64))
    kit.collide((-1.0, -0.4, 0), (1.0, 0.4, 1.2))


# ---------------------------------------------------------------- evidence and set dressing

@prop("crate_stack", "deck")
def _crate_stack(kit):
    """Crates on two pallets, shrink-wrapped (a dull wrap swatch over the stack)."""
    for px in (-0.6, 0.6):
        P_ = kit.p("Pallets", "deck")
        for y in (-0.55, 0.0, 0.55):
            P_.box((px - 0.6, y - 0.05, 0.0), (px + 0.6, y + 0.05, 0.1), skip="b")
        P_.box((px - 0.6, -0.6, 0.1), (px + 0.6, 0.6, 0.14))
        for i in range(2):
            for j in range(2):
                for k in range(2 if px < 0 else 3):
                    x0 = px - 0.58 + i * 0.58
                    y0 = -0.58 + j * 0.58
                    kit.p("Crates", "deck").box((x0, y0, 0.14 + k * 0.48), (x0 + 0.56, y0 + 0.56, 0.14 + (k + 1) * 0.48 - 0.02))
        h = 0.14 + (2 if px < 0 else 3) * 0.48
        kit.p("Wrap", "bottle_clear").box((px - 0.61, -0.61, 0.12), (px + 0.61, 0.61, h + 0.01), skip="b")
    kit.collide((-1.2, -0.6, 0), (1.2, 0.6, 1.6))


@prop("table_phones", "trim_black")
def _table_phones(kit):
    """A folding table with thirty mobile phones laid out in rows, screens dark."""
    kit.p("Top", "plastic_white").box((-1.2, -0.4, 0.71), (1.2, 0.4, 0.75))
    for x in (-1.05, 1.05):
        kit.p("Legs", "metal_galv").polyline([V(x, -0.35, 0.0), V(x, -0.3, 0.71)], 0.012, 4)
        kit.p("Legs", "metal_galv").polyline([V(x, 0.35, 0.0), V(x, 0.3, 0.71)], 0.012, 4)
    rng = random.Random(30)
    for i in range(10):
        for j in range(3):
            x, y = -1.05 + i * 0.235, -0.24 + j * 0.24
            rot = rng.uniform(-0.12, 0.12)
            cs, sn = math.cos(rot), math.sin(rot)
            w, l = 0.04, 0.08
            pts = [(x + cs * a - sn * b, y + sn * a + cs * b) for a, b in ((-w, -l), (w, -l), (w, l), (-w, l))]
            kit.p("Phones", "metal_dark").prism(pts, 0.75, 0.758, caps="t")
            kit.p("Screens", "glass_dark").face([(px_, py_, 0.7585) for px_, py_ in
                                                 [(x + cs * a * 0.88 - sn * b * 0.9, y + sn * a * 0.88 + cs * b * 0.9) for a, b in
                                                  ((-w, -l), (w, -l), (w, l), (-w, l))]], toward=(0, 0, 1))
    kit.collide((-1.2, -0.4, 0), (1.2, 0.4, 0.75))


@prop("crt_wall", "metal_dark")
def _crt_wall(kit):
    """A wall of twenty stacked old TV sets (5 x 4) on a steel shelf, screens glowing."""
    kit.p("Shelf", "metal_dark").box((-2.0, -0.3, 0.0), (2.0, 0.3, 0.3), skip="b")
    rng = random.Random(4)
    for i in range(5):
        for j in range(4):
            x = -1.6 + i * 0.8
            z = 0.3 + j * 0.52
            w = rng.uniform(0.66, 0.76)
            kit.p("Sets", ("trim_brown", "metal_dark", "plastic_white", "trim_black")[(i + j) % 4]).box(
                (x - w / 2, -0.28, z), (x + w / 2, 0.28, z + 0.5))
            kit.p("Screens", ("glow_cool", "glow_white", "neon_blue", "glow_cool")[(i * 3 + j) % 4]).face(
                [(x - w / 2 + 0.07, -0.285, z + 0.07), (x + w / 2 - 0.16, -0.285, z + 0.07), (x + w / 2 - 0.16, -0.285, z + 0.44),
                 (x - w / 2 + 0.07, -0.285, z + 0.44)], toward=(0, -1, 0))
            kit.p("Knobs", "chrome").box((x + w / 2 - 0.12, -0.29, z + 0.3), (x + w / 2 - 0.07, -0.28, z + 0.35))
    kit.collide((-2.0, -0.3, 0), (2.0, 0.3, 2.4))


@prop("estate_model", "paint_white")
def _estate_model(kit):
    """A museum vitrine (3 x 2 x 1.2) holding a scale model of the estate: the house's L of
    white blocks round its courtyard, the lawn, the hedge, the pool, tiny figures."""
    kit.p("Plinth", "darkwood").box((-1.5, -1.0, 0.0), (1.5, 1.0, 0.85), skip="b")
    kit.p("Glass", "windows").box((-1.45, -0.95, 0.85), (1.45, 0.95, 0.86))     # (the top's painted glass edge)
    kit.p("Frame", "brass")
    for (x, y) in ((-1.45, -0.95), (1.45, -0.95), (1.45, 0.95), (-1.45, 0.95)):
        kit.p("Frame", "brass").box((x - 0.02, y - 0.02, 0.85), (x + 0.02, y + 0.02, 1.2))
    kit.p("Frame", "brass").box((-1.47, -0.97, 1.18), (1.47, 0.97, 1.2))
    kit.p("Lawn", "trim_green").face([(-1.35, -0.85, 0.87), (1.35, -0.85, 0.87), (1.35, 0.85, 0.87), (-1.35, 0.85, 0.87)], toward=(0, 0, 1))
    s = 0.02                                          # 1:50 (the house is ~52 x 40 m)
    W = kit.p("House", "paint_white")
    for (x0, y0, x1, y1) in ((-26, -20, 26, -10), (-26, 10, 26, 20), (-26, -10, -16, 10), (16, -10, 26, 10)):
        W.box((x0 * s, y0 * s, 0.87), (x1 * s, y1 * s, 0.87 + 8.4 * s))
    kit.p("Courtyard", "stone").face([(-16 * s, -10 * s, 0.875), (16 * s, -10 * s, 0.875), (16 * s, 10 * s, 0.875),
                                      (-16 * s, 10 * s, 0.875)], toward=(0, 0, 1))
    Hd = kit.p("Hedge", "trim_green")
    for (x0, y0, x1, y1) in ((-1.35, -0.8, 1.35, -0.77), (-1.35, 0.77, 1.35, 0.8), (-1.35, -0.8, -1.32, 0.8), (1.32, -0.8, 1.35, 0.8)):
        Hd.box((x0, y0, 0.87), (x1, y1, 0.91))
    kit.p("Pool", "paint_blue").face([(0.7, -0.6, 0.875), (1.1, -0.6, 0.875), (1.1, -0.4, 0.875), (0.7, -0.4, 0.875)], toward=(0, 0, 1))
    rng = random.Random(11)
    for k in range(14):
        x, y = rng.uniform(-1.2, 1.2), rng.uniform(-0.75, -0.45)
        kit.p("Figures", "trim_black").box((x - 0.006, y - 0.006, 0.87), (x + 0.006, y + 0.006, 0.905))
    kit.collide((-1.5, -1.0, 0), (1.5, 1.0, 1.2))


@prop("raft", "metal_galv")
def _raft(kit):
    """A 14 ft grey river raft: two tubes and bow/stern, three thwarts, a floor."""
    G = kit.p("Tubes", "metal_galv")
    pts = [V(-1.6 * math.cos(t) * (1 if abs(math.cos(t)) > 0 else 1), 0.78 * math.sin(t), 0.25) for t in
           [2 * math.pi * k / 20 for k in range(20)]]
    pts = [V(q.x * (1.3 if abs(q.x) > 1.2 else 1.25), q.y, q.z) for q in pts]
    G.polyline(pts, 0.24, sides=8, closed=True)
    for x in (-0.7, 0.0, 0.7):
        G.tube(V(x, -0.7, 0.3), V(x, 0.7, 0.3), 0.12, 6)
    kit.p("Floor", "rubber").face([(-1.8, -0.6, 0.06), (1.8, -0.6, 0.06), (1.8, 0.6, 0.06), (-1.8, 0.6, 0.06)], toward=(0, 0, 1))
    kit.p("Line", "trim_black").polyline([V(q.x * 1.06, q.y * 1.15, 0.42) for q in pts], 0.008, sides=3, closed=True)
    kit.collide((-2.15, -1.0, 0), (2.15, 1.0, 0.5))


# ---------------------------------------------------------------- build

def build(name, module=None, **overrides):
    fn, far_key = PROPS[name]
    module = module or f"town_{name}"
    nm = "Town" + "".join(w.capitalize() for w in module[5:].split("_"))
    col, root, kit = tc.begin(nm, module)
    fn(kit, **overrides)
    far = tc.Far(nm)
    lo = [min(c[i] for c in kit.colliders) for i in range(3)] if kit.colliders else [-0.2, -0.2, 0]
    hi = [max(c[i + 3] for c in kit.colliders) for i in range(3)] if kit.colliders else [0.2, 0.2, 1]
    far.box(lo, hi, far_key, skip="b")
    kit.info.update(walk_in=False, prop=True, footprint=[round(lo[0], 3), round(lo[1], 3), round(hi[0], 3), round(hi[1], 3)])
    parts = tc.finish(kit, col, root, far)
    return root, parts
