"""Products for the gas station's shelves and coolers (town2_gas_in.py places them): real shapes
on the one packaging atlas (town2_gas_pack.py), packed in rows of facings with the irregularity
of a real shelf (some pulled forward, a gap where something sold, a bag slumped).

Every product is built at its own origin: base at z = 0, centred on x = 0, its front face at
y = 0 looking -y, its depth toward +y. `row()` fills a shelf (local frame: the shelf runs along
+x from 0 to L, its front edge at y = 0, top at z = 0, back toward +y) and is placed with kit.at().
"""
import math

import bmesh
from mathutils import Vector

V = Vector


def _cell(kit, key):
    return kit.cell("goods", key)


# ------------------------------------------------------------------ shapes
def bottle(kit, br, key, h=0.235, r=0.033, seg=8, lod=False):
    """A 20 oz PET bottle: base, ribbed body, label waist, shoulder, neck, cap (its label cell
    wraps once round it, the front at -y)."""
    # (seen through cooler glass by the hundred: 6 sides, a label waist, the shoulder, the cap)
    seg = 6
    prof = [(r * 0.85, 0.0), (r, 0.02), (r * 0.95, h * 0.4), (r, h * 0.64), (r * 0.74, h * 0.78), (r * 0.42, h * 0.87), (r * 0.46, h * 0.9),
            (r * 0.46, h), (0.0, h)]
    with kit.at((0, r, 0), rot=90):
        br.lathe(prof, seg=seg, cell=_cell(kit, key), cap_top=False)


def can(kit, br, key, h=0.122, r=0.033, seg=10, lod=False):
    """A 12 oz (or a 16 oz tall) aluminium can: necked top, the rim."""
    seg = 7
    prof = [(r * 0.84, 0.0), (r, 0.01), (r, h * 0.9), (r * 0.82, h), (0.0, h)]
    with kit.at((0, r, 0), rot=90):
        br.lathe(prof, seg=seg, cell=_cell(kit, key), cap_top=False)


def jar(kit, br, key, h=0.14, r=0.042, seg=8):
    prof = [(r * 0.9, 0.0), (r, 0.012), (r, h * 0.8), (r * 0.94, h * 0.86), (r * 0.94, h), (0.0, h)]
    with kit.at((0, r, 0), rot=90):
        br.lathe(prof, seg=seg, cell=_cell(kit, key), cap_top=False)


def bag(kit, br, key, w, h, d, rng, nu=4, nv=5):
    """A pillow bag (chips): a puffed front and back, flat crimped seals top and bottom, crinkled."""
    u0, v0, u1, v1 = _cell(kit, key)
    pts = {}
    for side in (-1, 1):
        for j in range(nv + 1):
            for i in range(nu + 1):
                u, v = i / nu, j / nv
                seal = 1.0 if 0.1 < v < 0.9 else 0.0
                puff = math.sin(math.pi * u) ** 0.7 * math.sin(math.pi * min(max((v - 0.1) / 0.8, 0), 1)) ** 0.6 * seal
                jit = (rng.random() - 0.5) * 0.008 * seal
                x = (u - 0.5) * w * (1 - 0.06 * puff)
                y = d / 2 + side * (d / 2) * (puff + jit * 4) + side * 0.002
                z = v * h + (rng.random() - 0.5) * 0.004 * seal
                pts[(side, i, j)] = (x, y, z)
    for side in (-1, 1):
        for j in range(nv):
            for i in range(nu):
                q = [pts[(side, i, j)], pts[(side, i + 1, j)], pts[(side, i + 1, j + 1)], pts[(side, i, j + 1)]]
                uv = [(u0 + (u1 - u0) * a / nu, v0 + (v1 - v0) * b / nv) for a, b in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))]
                if side > 0:
                    q, uv = q[::-1], [(u0 + u1 - a, b) for a, b in uv[::-1]]
                br.face(q, uv, smooth=True)
    # the side gussets: close the edges
    for i_edge in (0, nu):
        for j in range(nv):
            a, b = pts[(-1, i_edge, j)], pts[(-1, i_edge, j + 1)]
            c, dd = pts[(1, i_edge, j + 1)], pts[(1, i_edge, j)]
            q = [a, b, c, dd] if i_edge == 0 else [dd, c, b, a]
            br.face(q, [(u0 + 0.01 * (u1 - u0), v0 + (v1 - v0) * (j + 0.5) / nv)] * 4, smooth=False)


def box(kit, br, key, w, h, d, bevel=0.0):
    br.box((-w / 2, 0.0, 0.0), (w / 2, d, h), cell=_cell(kit, key), front="y", bevel=bevel, skip="z")


def jug(kit, br, key, w=0.17, h=0.27, d=0.1):
    """A quart / gallon jug (motor oil, washer fluid): rounded body, a handle, the cap."""
    br.box((-w / 2, 0.0, 0.0), (w / 2, d, h * 0.82), cell=_cell(kit, key), front="y", bevel=0.016, skip="z")
    br.box((-w / 2 + 0.02, 0.01, h * 0.82), (w / 2 - 0.05, d - 0.01, h * 0.9), cell=_cell(kit, key), front="y")
    kit.p("black", br.zone, lmw=0.1, group=br.lmg if br.lmg[0] else None).cyl((w / 2 - 0.035, d / 2), 0.018, h * 0.82, h, seg=6, caps="top")


def carton(kit, br, key, w=0.07, h=0.2, d=0.07):
    """A gable-top carton (milk, juice)."""
    br.box((-w / 2, 0.0, 0.0), (w / 2, d, h * 0.82), cell=_cell(kit, key), front="y", bevel=0.002, skip="z")
    u0, v0, u1, v1 = _cell(kit, key)
    sl = [(u0 + 0.5 * (u1 - u0), v1 - 0.02 * (v1 - v0))] * 4
    br.face([(-w / 2, 0.0, h * 0.82), (w / 2, 0.0, h * 0.82), (w / 2, d / 2, h * 0.98), (-w / 2, d / 2, h * 0.98)], sl)
    br.face([(w / 2, d, h * 0.82), (-w / 2, d, h * 0.82), (-w / 2, d / 2, h * 0.98), (w / 2, d / 2, h * 0.98)], sl)
    br.face([(-w / 2, 0.0, h * 0.82), (-w / 2, d / 2, h * 0.98), (-w / 2, d, h * 0.82)], sl)
    br.face([(w / 2, d, h * 0.82), (w / 2, d / 2, h * 0.98), (w / 2, 0.0, h * 0.82)], sl)
    br.box((-w / 2, d / 2 - 0.004, h * 0.98), (w / 2, d / 2 + 0.004, h), cell=_cell(kit, key), front="y")


# product kinds: (builder, width, height, depth, keys)
KINDS = {
    "bottle": ("bottle", 0.072, 0.235, 0.07, [f"bottle{i}" for i in range(8)]),
    "can": ("can", 0.068, 0.122, 0.068, [f"can{i}" for i in range(8)]),
    "tallcan": ("tallcan", 0.068, 0.157, 0.068, [f"can{i}" for i in (2, 3, 4, 5)]),
    "jar": ("jar", 0.088, 0.14, 0.088, [f"jar{i}" for i in range(4)]),
    "bag_s": ("bag", 0.17, 0.24, 0.07, [f"bag{i}" for i in range(16)]),
    "bag_m": ("bag", 0.22, 0.31, 0.085, [f"bag{i}" for i in range(16)]),
    "bag_l": ("bag", 0.27, 0.37, 0.1, [f"bag{i}" for i in range(16)]),
    "pouch": ("bag", 0.15, 0.2, 0.05, [f"pouch{i}" for i in range(4)]),
    "box_c": ("box", 0.19, 0.28, 0.06, ["box0", "box2", "box4", "box6"]),
    "box_s": ("box", 0.14, 0.18, 0.05, ["box1", "box3", "box5", "box7"]),
    "candy": ("box", 0.2, 0.08, 0.13, ["box1", "box3", "box5", "box7", "tickets"]),
    "jug": ("jug", 0.17, 0.27, 0.1, [f"jug{i}" for i in range(4)]),
    "carton": ("carton", 0.075, 0.2, 0.075, [f"carton{i}" for i in range(4)]),
    "case": ("box", 0.27, 0.13, 0.4, [f"case{i}" for i in range(4)]),
}


def product(kit, br, kind, key, rng, lod=False):
    b, w, h, d, _ = KINDS[kind]
    if b == "bottle":
        bottle(kit, br, key, lod=lod)
    elif b == "can":
        can(kit, br, key, lod=lod)
    elif b == "tallcan":
        can(kit, br, key, h=0.157, lod=lod)
    elif b == "jar":
        jar(kit, br, key)
    elif b == "bag":
        bag(kit, br, key, w, h * rng.uniform(0.96, 1.03), d, rng)
    elif b == "box":
        box(kit, br, key, w, h, d)
    elif b == "jug":
        jug(kit, br, key, w, h, d)
    elif b == "carton":
        carton(kit, br, key, w, h, d)


def row(kit, rng, L, depth, kinds, zone="int", group_axis=None, rows=1, gap=0.06, back_lod=False, slump=True):
    """Fill a shelf 0..L (local, front at y = 0, facing -y) with runs of facings: each run one
    product kind and one key (2-6 facings), `rows` deep (the rows behind at low detail when
    back_lod). A few facings missing (sold), some pulled forward, bags leaning."""
    g = kit.group(group_axis) if group_axis is not None else None
    br = kit.p("goods", zone, lmw=0.6, group=g)
    x = 0.015
    run, kind, key = 0, None, None
    while True:
        if run <= 0:
            kind = kinds[rng.randrange(len(kinds))]
            key = rng.choice(KINDS[kind][4])
            run = rng.randint(2, 6)
        _, w, h, d, _ = KINDS[kind]
        if x + w > L - 0.01:
            break
        run -= 1
        if rng.random() < gap:              # a sold-out facing
            x += w + 0.006
            continue
        n = min(rows, max(1, int(depth / (d + 0.004))))
        pull = rng.uniform(0.0, 0.025) if rng.random() < 0.35 else 0.0
        yy = 0.012 - pull
        yaw = rng.uniform(-6, 6) if kind.startswith(("bag", "pouch", "bottle")) else rng.uniform(-1.5, 1.5)
        tilt = rng.uniform(-6, 2) if slump and kind.startswith("bag") else 0.0
        with kit.at((x + w / 2, yy, 0.0), rot=yaw, rx=tilt):
            product(kit, br, kind, key, rng)
        if n > 1 and kind.startswith("bag"):
            # (bags: a second real row, leaning back on the first)
            with kit.at((x + w / 2 + rng.uniform(-0.01, 0.01), yy + d * 0.8, 0.0), rot=rng.uniform(-8, 8), rx=-8):
                product(kit, br, kind, key, rng)
        elif n > 1:
            # (the rows behind the facing: one block for all of them, its sides and top in the
            # product's colours; seen past the front one and from above)
            hb = h * (0.9 if kind.startswith(("bag", "pouch")) else 0.97)
            with kit.at((x + w / 2, yy + d + 0.006, 0.0)):
                kit.p("goods", zone, lmw=0.3, group=g).box((-w / 2 + 0.006, 0.0, 0.0), (w / 2 - 0.006, (n - 1) * (d + 0.004), hb),
                                                             cell=_cell(kit, key), front="y", skip="zy")
        x += w + rng.uniform(0.004, 0.014)


def tag_rail(kit, L, z, y=0.0, zone="int", h=0.04):
    """The shelf-edge data strip: the atlas's tag cell repeated every ~0.6 m (faces -y)."""
    cell = kit.cell("goods", "tags")
    br = kit.p("goods", zone, lmw=0.4)
    n = max(1, round(L / 0.6))
    for k in range(n):
        a0, a1 = L * k / n, L * (k + 1) / n
        u0, v0, u1, v1 = cell
        vv0 = v0 + (v1 - v0) * 0.75
        br.face([(a0, y, z - h), (a1, y, z - h), (a1, y, z), (a0, y, z)], [(u0, vv0), (u1, vv0), (u1, v1), (u0, v1)])
    kit.p("lightgrey", zone, lmw=0.2).box((0.0, y + 0.002, z - h - 0.004), (L, y + 0.012, z - h), skip="")
