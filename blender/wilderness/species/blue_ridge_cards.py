"""Twig cards for the Blue Ridge kit (Laurel Fork Cove, mid-June). Three shared atlases:

  br_broadleaf  2048 (+1024 normal): tulip poplar, red / white / chestnut oak, shagbark hickory, sugar maple,
                yellow buckeye (two twigs each) + hickory bark strips
  br_evergreen  2048 (+1024 normal): eastern hemlock sprays, white pine plumes, rosebay / Catawba
                rhododendron whorls (bud, first trusses, bloom), mountain laurel in bloom
  br_ground     1024 (+512 normal): Christmas fern, cinnamon fern (sterile + withered fertile), doghobble
                arching stems, moss fringe (Poly Haven moss_01 sprigs)
  tiles         opaque repeating textures for shell meshes and moss mats (rosebay, laurel, Catawba, moss)

Leaf colours are the brief's Appendix B (sRGB) and land as the alpha-weighted mean of each card
(leafcards prints and stores the measured mean). Every card is drawn top-down, stem base at (0, 0).
"""
import math
import random

from mathutils import Vector

import leafcards as lc
from leafcards import Card, at, curve, rot

V = Vector
TWIG = "#5B4A3A"      # generic grey-brown twig
PET = "#6B7A3A"       # green petiole


# =============================================================================================
# textures: name -> (function, args...) (hashed for the cache)
def scan_sprite(src, key_d, key_a, idx, mul=(1, 1, 1)):
    """idx-th sprite (left to right, top row first) found in a Poly Haven atlas by its alpha."""
    import numpy as np
    key = (src, key_d, key_a)
    cache = scan_sprite.__dict__.setdefault("cache", {})
    if key not in cache:
        full, _ = lc.scan_tex(src, key_d, key_a, (0, 0, 1, 1))
        a = full[..., 3] > 0.5
        h, w = a.shape
        rows = a.any(1)
        # split into bands of rows with alpha, then columns within each band
        bands, inb, y0 = [], False, 0
        for y in range(h):
            if rows[y] and not inb:
                inb, y0 = True, y
            elif not rows[y] and inb:
                inb = False
                if y - y0 > 8:
                    bands.append((y0, y))
        if inb:
            bands.append((y0, h))
        sprites = []
        for b0, b1 in bands:
            cols = a[b0:b1].any(0)
            inc, x0 = False, 0
            for x in range(w + 1):
                v = cols[x] if x < w else False
                if v and not inc:
                    inc, x0 = True, x
                elif not v and inc:
                    inc = False
                    if x - x0 > 6:
                        sub = a[b0:b1, x0:x]
                        ys = np.where(sub.any(1))[0]
                        sprites.append(full[b0 + ys[0]:b0 + ys[-1] + 1, x0:x].copy())
        cache[key] = sprites
    sp = cache[key][idx % len(cache[key])].copy()
    sp[..., :3] *= np.array(mul, np.float32)
    return sp, sp.shape[1] / sp.shape[0]


T_BROAD = {
    "poplar_leaf": (lc.leaf_tex, "tulip", "#8DB04A", 176, None, "pinnate", 0.16, 0.5),
    "red_oak_leaf": (lc.leaf_tex, "red_oak", "#3F5E2A", 176, None, "pinnate", 0.14, 0.5),
    "white_oak_leaf": (lc.leaf_tex, "white_oak", "#4A6A36", 176, None, "pinnate", 0.12, 0.5),
    "chestnut_oak_leaf": (lc.leaf_tex, "chestnut_oak", "#6B8A36", 176, None, "pinnate", 0.16, 0.5),
    "hickory_leaflet": (lc.leaf_tex, "leaflet_serrate", "#4F7230", None, 160, "pinnate", 0.12, 0.5),
    "hickory_terminal": (lc.leaf_tex, "leaflet_obovate", "#4F7230", None, 176, "pinnate", 0.12, 0.5),
    "maple_leaf": (lc.leaf_tex, "maple", "#4E7A2C", 176, None, "palmate", 0.16, 0.5),
    "buckeye_leaflet": (lc.leaf_tex, "leaflet_serrate", "#6E9438", None, 176, "pinnate", 0.14, 0.5),
    "hickory_strip": (lc.leaf_tex, "bark_strip", "#7E786E", None, 192, "parallel", 0.35, 0.9, 0.25),
}
T_EVER = {
    "hem_needle": (lc.leaf_tex, "needle", "#22382B", None, 64, "midrib", 0.25, 0.0, 0.1),
    "hem_needle_new": (lc.leaf_tex, "needle", "#55763A", None, 64, "midrib", 0.15, 0.0, 0.05),
    "pine_needle": (lc.strip_tex, "#3F5E43", "#5F8060"),
    "rosebay_leaf": (lc.leaf_tex, "rhodo", "#2B4729", None, 192, "pinnate", 0.22, 0.45, 0.14, 0.1, "#9EA868", 1,
                     None, None, None, 0.18),
    "rosebay_bud": (lc.leaf_tex, "bud", "#A7A46A", None, 64, "midrib", 0.2, 0.3),
    "rosebay_floret": (lc.leaf_tex, "floret5", "#F2ECEC", 96, None, None, 0, 0.2, 0.05, 0.05, None, 3,
                       ("#A8BC58", 9, 0.3, 0.035, (-40, 40)), None, ("#E9DFB8", 0.12)),
    "laurel_leaf": (lc.leaf_tex, "laurel", "#3D582C", None, 128, "pinnate", 0.2, 0.4, 0.12, 0.1, "#A4B06A", 1,
                    None, None, None, 0.15),
    "laurel_floret": (lc.leaf_tex, "floret_cup", "#F3D9E0", 64, None, None, 0, 0.15, 0.06, 0.03, None, 5,
                      ("#9C2E52", 10, 0.3, 0.05, None), ("#E592B2", 0.3, 0.42), ("#C9D79A", 0.09)),
    "laurel_bud": (lc.leaf_tex, "round", "#E07FA4", 40, None, None, 0, 0.2, 0.2, 0.05),
    "catawba_leaf": (lc.leaf_tex, "catawba", "#33502F", None, 160, "pinnate", 0.2, 0.45, 0.12, 0.1, "#8E9C5C", 1,
                     None, None, None, 0.18),
    "catawba_floret": (lc.leaf_tex, "floret5", "#B65A9E", 96, None, None, 0, 0.25, 0.08, 0.06, None, 7,
                       ("#D4C25A", 8, 0.3, 0.035, (-35, 35)), None, ("#E8B9D8", 0.12)),
    "catawba_bud": (lc.leaf_tex, "bud", "#8C2F6A", None, 48, "midrib", 0.2, 0.3),
}
T_GROUND = {
    "xmas_pinna": (lc.leaf_tex, "xmas_pinna", "#2F5027", None, 96, "midrib", 0.18, 0.45, 0.15, 0.08),
    "cinn_pinna": (lc.leaf_tex, "cinn_pinna", "#5E8838", None, 128, "midrib", 0.2, 0.4, 0.1, 0.12),
    "cinn_fertile": (lc.leaf_tex, "bud", "#8A5A2E", None, 48, None, 0, 0.6, 0.2, 0.15),
    "doghobble_leaf": (lc.leaf_tex, "doghobble", "#355A2B", None, 160, "pinnate", 0.2, 0.45, 0.12, 0.1, "#94A262", 1,
                       None, None, None, 0.3),
    "doghobble_new": (lc.leaf_tex, "doghobble", "#7C6234", None, 160, "pinnate", 0.15, 0.4, 0.1, 0.05),
}
T_UNDER = {
    # flowering dogwood: ovate, entire, short-pointed, the arcuate veins sweeping toward the tip
    "dogwood_leaf": (lc.leaf_tex, "catawba", "#557B35", None, 160, "pinnate", 0.22, 0.45, 0.1, 0.12, "#A2B276", 1,
                     None, None, None, 0.42),
    "dogwood_fruit": (lc.leaf_tex, "round", "#7E9A44", 24, None, None, 0, 0.2, 0.2, 0.05),
    # sourwood: elliptic, finely serrate, glossy; the June flower panicles still in bud
    "sourwood_leaf": (lc.leaf_tex, "leaflet_serrate", "#4C702F", None, 176, "pinnate", 0.14, 0.4),
    "sourwood_bud": (lc.leaf_tex, "bud", "#ECE9CF", None, 28, None, 0, 0.2, 0.2, 0.05),
    # flame azalea: elliptic, soft, pale green; funnel flowers orange with a yellow blotch, long stamens
    "azalea_leaf": (lc.leaf_tex, "laurel", "#62853F", None, 112, "pinnate", 0.16, 0.4, 0.1, 0.1, "#A8BC74", 1),
    "azalea_floret": (lc.leaf_tex, "floret5", "#F08A2A", 96, None, None, 0, 0.25, 0.08, 0.06, None, 9,
                      ("#F7C03C", 8, 0.34, 0.045, (-30, 30)), None, ("#E0601A", 0.14)),
}
for _i in range(9):
    T_GROUND[f"moss_{_i}"] = (scan_sprite, "moss_01", "Diffuse", "Alpha", _i, (0.8, 1.9, 1.3))


# =============================================================================================
# layout helpers
def tints(rng, lo=0.82, hi=1.1):
    return rng.uniform(lo, hi)


def alt_leaves(c, pts, n, tex, L, pet, ang, rng, f0=0.15, f1=0.97, droop=0.1, fold=0.12, terminal=True,
               pet_col=PET, Ljit=0.18, hue=0.05, lift=0.004, shrink=0.25):
    side = rng.choice((-1, 1))
    for i in range(n):
        f = f0 + (f1 - f0) * (i + 0.5) / n
        p, t = at(pts, f)
        pd = rot(t, side * (ang + rng.uniform(-12, 12)))
        q = p + pd * pet * rng.uniform(0.7, 1.15)
        c.stem([p, q], 0.0016, 0.001, pet_col)
        ld = rot(pd, -side * rng.uniform(5, 25))
        Ls = L * (1 - shrink * (1 - f)) * rng.uniform(1 - Ljit, 1 + Ljit * 0.5)
        c.leaf(tex, q, ld, Ls, tint=tints(rng), hue=rng.uniform(-hue, hue), droop=droop, fold=fold,
               roll=math.radians(rng.uniform(-15, 15)), lift=lift + rng.uniform(0, 0.01))
        side = -side
    if terminal:
        p, t = at(pts, 1.0)
        q = p + t * pet * 0.6
        c.stem([p, q], 0.0016, 0.001, pet_col)
        c.leaf(tex, q, rot(t, rng.uniform(-10, 10)), L * rng.uniform(0.85, 1.0), tint=tints(rng),
               hue=rng.uniform(-hue, hue), droop=droop, fold=fold, lift=lift + 0.012)


def fan(c, p, d, n, tex, L, spread, pet, rng, droop=0.12, fold=0.14, pet_col=PET, lift=0.006, Ljit=0.2, hue=0.04):
    for i in range(n):
        a = -spread + 2 * spread * (i + rng.uniform(0.2, 0.8)) / n
        ld = rot(d, a)
        q = p + ld * pet * rng.uniform(0.6, 1.2)
        if pet > 0.004:
            c.stem([p, q], 0.0015, 0.001, pet_col)
        Ls = L * rng.uniform(1 - Ljit, 1.0) * (1 - 0.25 * abs(a) / max(spread, 1))
        c.leaf(tex, q, ld, Ls, tint=tints(rng), hue=rng.uniform(-hue, hue), droop=droop, fold=fold,
               roll=math.radians(rng.uniform(-20, 20)), lift=lift + rng.uniform(0, 0.012))


def pinnate_compound(c, p, d, rachis, pairs, lat, term, Ls, rng, pet_col=PET, lift=0.008):
    pts = curve(p, d, rachis, rng.uniform(-0.3, 0.3), 6)
    c.stem(pts, 0.0022, 0.0012, pet_col)
    for k in range(pairs):
        f = 0.35 + 0.55 * k / max(1, pairs - 1) if pairs > 1 else 0.6
        q, t = at(pts, f)
        for side in (-1, 1):
            Lk = Ls[k] * rng.uniform(0.9, 1.08)
            c.leaf(lat, q, rot(t, side * rng.uniform(52, 70)), Lk, tint=tints(rng), hue=rng.uniform(-0.04, 0.04),
                   droop=0.08, fold=0.1, roll=math.radians(rng.uniform(-15, 15)), lift=lift + rng.uniform(0, 0.01))
    q, t = at(pts, 1.0)
    c.leaf(term, q, t, Ls[-1], tint=tints(rng), droop=0.08, fold=0.1, lift=lift + 0.012)


def palmate_compound(c, p, d, pet, n, tex, Ls, spread, rng, pet_col=PET, lift=0.008):
    q = p + d * pet
    c.stem([p, q], 0.0022, 0.0015, pet_col)
    for i in range(n):
        a = -spread + 2 * spread * i / max(1, n - 1)
        k = abs(i - (n - 1) / 2) / max(1, (n - 1) / 2)
        c.leaf(tex, q, rot(d, a + rng.uniform(-6, 6)), Ls * (1 - 0.42 * k) * rng.uniform(0.9, 1.05), tint=tints(rng),
               hue=rng.uniform(-0.04, 0.04), droop=0.1, fold=0.12, lift=lift + rng.uniform(0, 0.01))


def whorl(c, p, n, tex, L, rng, droop=0.22, fold=0.2, a0=None, lift=0.01, Ljit=0.15, tilt_d=None):
    a0 = rng.uniform(0, 360) if a0 is None else a0
    for i in range(n):
        a = a0 + 360 * (i + rng.uniform(-0.2, 0.2)) / n
        ld = rot((0, 1, 0), a)
        if tilt_d is not None:
            ld = (ld + tilt_d * 0.6).normalized()
        c.leaf(tex, p + ld * 0.006, ld, L * rng.uniform(1 - Ljit, 1.0), tint=tints(rng, 0.85, 1.12),
               hue=rng.uniform(-0.03, 0.03), droop=droop, fold=fold, roll=math.radians(rng.uniform(-18, 18)),
               lift=lift + rng.uniform(0, 0.02) * (1 if i % 2 else 0.4))


def truss(c, p, r, n, floret, size, rng, bud=None, nbud=0, lift=0.05):
    """A dome of florets seen from above (golden-angle disc, outer ones tilted out and lower)."""
    for i in range(n):
        f = math.sqrt((i + 0.5) / n)
        a = i * 137.508
        q = p + rot((0, 1, 0), a) * (r * f)
        d = rot((0, 1, 0), a + rng.uniform(-40, 40))
        c.leaf(floret, q - d * size * 0.5, d, size * rng.uniform(0.88, 1.08), tint=tints(rng, 0.92, 1.06), fold=0.25,
               droop=0.0, lift=lift - 0.02 * f + rng.uniform(0, 0.006))
    for i in range(nbud):
        a = rng.uniform(0, 360)
        q = p + rot((0, 1, 0), a) * (r * rng.uniform(0.2, 1.05))
        d = rot((0, 1, 0), a)
        c.leaf(bud, q, d, size * 0.55 * rng.uniform(0.8, 1.1), tint=tints(rng, 0.9, 1.05), fold=0.3, droop=0,
               lift=lift + 0.01)


# =============================================================================================
# broadleaf cards (canopy: tops seen from far below, so the twig reads by silhouette and colour)
def poplar_a():
    c = Card((0.56, 0.56), (500, 500), seed=11)
    r = c.rng
    pts = curve((0, 0, 0), (0.1, 1, 0), 0.38, 0.25, 8, 0.04, r)
    c.stem(pts, 0.004, 0.0025, "#6A4B3A")
    alt_leaves(c, pts, 6, "poplar_leaf", 0.125, 0.07, 62, r, f0=0.12, droop=0.06, fold=0.08)
    return c


def poplar_b():
    c = Card((0.6, 0.6), (500, 500), seed=12)
    r = c.rng
    main = curve((0, 0, 0), (-0.05, 1, 0), 0.4, -0.2, 8, 0.03, r)
    c.stem(main, 0.005, 0.003, "#6A4B3A")
    alt_leaves(c, main, 5, "poplar_leaf", 0.12, 0.065, 60, r, f0=0.35, droop=0.06, fold=0.08)
    for f, s in ((0.3, 1), (0.55, -1)):
        p, t = at(main, f)
        br = curve(p, rot(t, s * 48), 0.2, -s * 0.3, 6, 0.04, r)
        c.stem(br, 0.003, 0.002, "#6A4B3A")
        alt_leaves(c, br, 3, "poplar_leaf", 0.11, 0.06, 58, r, f0=0.2, droop=0.06, fold=0.08)
    return c


def _oak(seed, tex, L, clusters, size):
    c = Card((size, size), (500, 500), seed=seed)
    r = c.rng
    main = curve((0, 0, 0), (0.05, 1, 0), size * 0.36, r.uniform(-0.3, 0.3), 8, 0.06, r)
    c.stem(main, 0.005, 0.003, "#5E5246")
    tips = [(at(main, 1.0), main)]
    for k in range(clusters - 1):
        f = 0.3 + 0.3 * k / max(1, clusters - 2)
        p, t = at(main, f)
        s = 1 if k % 2 == 0 else -1
        br = curve(p, rot(t, s * r.uniform(45, 62)), size * r.uniform(0.16, 0.22), -s * 0.4, 6, 0.06, r)
        c.stem(br, 0.0035, 0.0022, "#5E5246")
        tips.append((at(br, 1.0), br))
    for (p, t), _ in tips:
        fan(c, p, t, r.randint(6, 8), tex, L, 95, 0.012, r, droop=0.1, fold=0.16)
    return c


def red_oak_a():
    return _oak(21, "red_oak_leaf", 0.15, 2, 0.5)


def red_oak_b():
    return _oak(22, "red_oak_leaf", 0.14, 3, 0.5)


def white_oak_a():
    return _oak(31, "white_oak_leaf", 0.14, 2, 0.5)


def white_oak_b():
    return _oak(32, "white_oak_leaf", 0.13, 3, 0.5)


def chestnut_oak_a():
    return _oak(41, "chestnut_oak_leaf", 0.15, 2, 0.5)


def chestnut_oak_b():
    return _oak(42, "chestnut_oak_leaf", 0.14, 3, 0.5)


def _hickory(seed, n_leaves):
    c = Card((0.8, 0.8), (500, 500), seed=seed)
    r = c.rng
    tw = curve((0, 0, 0), (0, 1, 0), 0.14, 0.1, 4, 0.02, r)
    c.stem(tw, 0.005, 0.004, "#6B5E50")
    p, t = at(tw, 1.0)
    for k in range(n_leaves):
        a = -50 + 100 * k / max(1, n_leaves - 1) + r.uniform(-8, 8)
        pinnate_compound(c, p, rot(t, a), r.uniform(0.25, 0.32), 2, "hickory_leaflet", "hickory_terminal",
                         [0.09, 0.13, 0.16], r)
    return c


def hickory_a():
    return _hickory(51, 3)


def hickory_b():
    return _hickory(52, 4)


def hickory_strips():
    c = Card((0.16, 0.5), (160, 500), seed=55)
    r = c.rng
    for i, x in enumerate((-0.05, 0.0, 0.05)):
        c.leaf("hickory_strip", (x, 0.01, 0), (r.uniform(-0.05, 0.05), 1, 0), r.uniform(0.42, 0.48),
               tint=r.uniform(0.8, 1.1), fold=0.35, droop=0.0, lift=0.01 * i)
    return c


def _maple(seed, pairs):
    c = Card((0.5, 0.5), (500, 500), seed=seed)
    r = c.rng
    tw = curve((0, 0, 0), (0.03, 1, 0), 0.24, r.uniform(-0.15, 0.15), 6, 0.02, r)
    c.stem(tw, 0.004, 0.0028, "#6E5642")
    for k in range(pairs):
        p, t = at(tw, 0.35 + 0.6 * k / max(1, pairs))
        for s in (-1, 1):
            d = rot(t, s * r.uniform(55, 72))
            q = p + d * r.uniform(0.06, 0.09)
            c.stem([p, q], 0.0016, 0.0011, "#8A6A3A")
            c.leaf("maple_leaf", q, rot(d, -s * r.uniform(5, 20)), r.uniform(0.11, 0.13), tint=tints(r),
                   hue=r.uniform(-0.04, 0.04), droop=0.06, fold=0.1, lift=0.006 + r.uniform(0, 0.01))
    p, t = at(tw, 1.0)
    for s in (-1, 1):
        d = rot(t, s * r.uniform(22, 35))
        q = p + d * 0.06
        c.stem([p, q], 0.0015, 0.001, "#8A6A3A")
        c.leaf("maple_leaf", q, d, r.uniform(0.11, 0.13), tint=tints(r), droop=0.06, fold=0.1, lift=0.02)
    return c


def maple_a():
    return _maple(61, 2)


def maple_b():
    return _maple(62, 3)


def _buckeye(seed, pairs):
    c = Card((0.6, 0.6), (500, 500), seed=seed)
    r = c.rng
    tw = curve((0, 0, 0), (0, 1, 0), 0.16, 0.1, 4, 0.02, r)
    c.stem(tw, 0.006, 0.0045, "#7A6A58")
    for k in range(pairs):
        p, t = at(tw, 0.45 + 0.55 * k / max(1, pairs - 1) if pairs > 1 else 1.0)
        for s in (-1, 1):
            d = rot(t, s * r.uniform(30, 60))
            palmate_compound(c, p, d, r.uniform(0.09, 0.13), 5, "buckeye_leaflet", 0.15, 62, r)
    return c


def buckeye_a():
    return _buckeye(71, 1)


def buckeye_b():
    return _buckeye(72, 2)


# =============================================================================================
# conifers
def _hemlock(seed, size, length):
    c = Card(size, (500, int(round(500 * size[1] / size[0]))) if size[0] >= size[1] else
             (int(round(500 * size[0] / size[1])), 500), seed=seed)
    r = c.rng

    def needles(pts, lmax, new_from=0.85):
        cum = sum((b - a).length for a, b in zip(pts, pts[1:]))
        n = int(cum / 0.0021)
        for i in range(n):
            f = (i + 0.5) / n
            p, t = at(pts, f)
            new = f > new_from
            ln = lmax * (0.55 + 0.45 * math.sin(math.pi * min(1, 0.25 + 0.75 * (1 - f) + 0.2)))
            for s in (-1, 1):
                c.leaf("hem_needle_new" if new else "hem_needle", p, rot(t, s * r.uniform(70, 95)),
                       ln * r.uniform(0.85, 1.1), tint=r.uniform(0.85, 1.1), fold=0.0, droop=0.0,
                       lift=0.002 + r.uniform(0, 0.002))
            if r.random() < 0.18:      # small twisted needles lying on top of the twig
                c.leaf("hem_needle_new" if new else "hem_needle", p, rot(t, r.uniform(-30, 30)), ln * 0.6,
                       tint=r.uniform(0.95, 1.15), fold=0, droop=0, lift=0.006)
    main = curve((0, 0, 0), (0.0, 1, 0), length, r.uniform(-0.2, 0.2), 10, 0.03, r)
    c.stem(main, 0.0035, 0.0012, "#6E5440")
    needles(main, 0.015, 0.96)
    s = r.choice((-1, 1))
    f = 0.06
    while f < 0.9:
        p, t = at(main, f)
        L = length * 0.5 * (1 - f) ** 0.8 + 0.025
        br = curve(p, rot(t, s * r.uniform(50, 66)), L, -s * r.uniform(0.0, 0.35), 6, 0.04, r)
        c.stem(br, 0.0018, 0.0008, "#6E5440")
        needles(br, 0.013, 0.9)
        if L > 0.06:                    # second order
            ss = r.choice((-1, 1))
            g = 0.18
            while g < 0.8:
                q, tt = at(br, g)
                L2 = L * 0.4 * (1 - g) + 0.01
                b2 = curve(q, rot(tt, ss * r.uniform(45, 60)), L2, 0.0, 3, 0.03, r)
                c.stem(b2, 0.0012, 0.0006, "#6E5440")
                needles(b2, 0.011, 0.86)
                g += r.uniform(0.12, 0.18)
                ss = -ss
        f += r.uniform(0.05, 0.075)
        s = -s
    return c


def hemlock_a():
    return _hemlock(81, (0.36, 0.5), 0.47)


def hemlock_b():
    return _hemlock(82, (0.5, 0.5), 0.46)


def _plume(c, p, d, length, r, fasc_from=0.35):
    pts = curve(p, d, length, r.uniform(-0.25, 0.25), 8, 0.03, r)
    c.stem(pts, 0.004, 0.0025, "#5E4E3E")
    n = int(length * (1 - fasc_from) / 0.007)
    for i in range(n):
        f = fasc_from + (1 - fasc_from) * (i + 0.5) / n
        q, t = at(pts, f)
        for k in range(5):
            a = r.uniform(18, 52) * r.choice((-1, 1))
            ln = r.uniform(0.075, 0.11) * (0.75 + 0.25 * f)
            c.leaf("pine_needle", q, rot(t, a), ln * math.cos(math.radians(r.uniform(0, 40))), tint=r.uniform(0.85, 1.12),
                   fold=0, droop=r.uniform(0.0, 0.08), lift=0.004 + r.uniform(0, 0.01))
    q, t = at(pts, 1.0)
    for k in range(10):
        c.leaf("pine_needle", q, rot(t, r.uniform(-25, 25)), r.uniform(0.07, 0.1), tint=r.uniform(0.95, 1.15), fold=0,
               droop=0.0, lift=0.012)


def pine_a():
    c = Card((0.24, 0.5), (240, 500), seed=91)
    _plume(c, V((0, 0, 0)), V((0, 1, 0)), 0.36, c.rng)
    return c


def pine_b():
    c = Card((0.5, 0.5), (500, 500), seed=92)
    r = c.rng
    main = curve((0, 0, 0), (0, 1, 0), 0.18, 0.1, 4, 0.02, r)
    c.stem(main, 0.006, 0.005, "#5E4E3E")
    p, t = at(main, 1.0)
    for a in (-38, 0, 36):
        _plume(c, p, rot(t, a + r.uniform(-8, 8)), r.uniform(0.25, 0.3), r, 0.2)
    return c


# =============================================================================================
# heaths (Ericaceae): rosebay, Catawba, mountain laurel
def rosebay_a():                 # terminal whorl with this year's flower bud
    c = Card((0.56, 0.56), (500, 500), seed=101)
    r = c.rng
    st = curve((0, 0, 0), (0, 1, 0), 0.24, 0.15, 5, 0.04, r)
    c.stem(st, 0.007, 0.006, "#6E6258")
    p, _ = at(st, 1.0)
    whorl(c, p, 9, "rosebay_leaf", 0.21, r, droop=0.18, fold=0.22)
    c.leaf("rosebay_bud", p - V((0, 0.02, 0)), V((0, 1, 0)), 0.045, fold=0.4, droop=0, lift=0.06)
    return c


def rosebay_b():                 # forked: two older whorls lower down
    c = Card((0.56, 0.56), (500, 500), seed=102)
    r = c.rng
    st = curve((0, 0, 0), (0, 1, 0), 0.12, 0.0, 3, 0.03, r)
    c.stem(st, 0.008, 0.007, "#6E6258")
    p, t = at(st, 1.0)
    for s in (-1, 1):
        b = curve(p, rot(t, s * 34), 0.17, -s * 0.3, 5, 0.05, r)
        c.stem(b, 0.006, 0.005, "#6E6258")
        q, _ = at(b, 1.0)
        whorl(c, q, 8, "rosebay_leaf", 0.16, r, droop=0.25, fold=0.22, tilt_d=rot(t, s * 34))
    return c


def rosebay_c():                 # whorl with one of the first white trusses (creekside, mid-June)
    c = Card((0.56, 0.56), (500, 500), seed=103)
    r = c.rng
    st = curve((0, 0, 0), (0, 1, 0), 0.24, -0.1, 5, 0.04, r)
    c.stem(st, 0.007, 0.006, "#6E6258")
    p, _ = at(st, 1.0)
    whorl(c, p, 9, "rosebay_leaf", 0.2, r, droop=0.2, fold=0.22)
    truss(c, p, 0.07, 16, "rosebay_floret", 0.038, r, lift=0.08)
    return c


def catawba_a():                 # Catawba in peak bloom (the Knob): truss over a whorl
    c = Card((0.4, 0.4), (400, 400), seed=111)
    r = c.rng
    st = curve((0, 0, 0), (0, 1, 0), 0.17, 0.1, 4, 0.03, r)
    c.stem(st, 0.006, 0.005, "#6A5E52")
    p, _ = at(st, 1.0)
    whorl(c, p, 8, "catawba_leaf", 0.115, r, droop=0.15, fold=0.2)
    truss(c, p, 0.075, 15, "catawba_floret", 0.05, r, "catawba_bud", 3, lift=0.08)
    return c


def catawba_b():                 # leaves only, two whorls (the dome's sides)
    c = Card((0.4, 0.4), (400, 400), seed=112)
    r = c.rng
    st = curve((0, 0, 0), (0, 1, 0), 0.08, 0.0, 3, 0.03, r)
    c.stem(st, 0.007, 0.006, "#6A5E52")
    p, t = at(st, 1.0)
    for s in (-1, 1):
        b = curve(p, rot(t, s * 32), 0.12, -s * 0.2, 4, 0.04, r)
        c.stem(b, 0.005, 0.004, "#6A5E52")
        q, _ = at(b, 1.0)
        whorl(c, q, 7, "catawba_leaf", 0.1, r, droop=0.2, fold=0.2, tilt_d=rot(t, s * 32))
    return c


def _laurel(seed, bloom):
    c = Card((0.36, 0.36), (400, 400), seed=seed)
    r = c.rng
    st = curve((0, 0, 0), (0, 1, 0), 0.1, 0.2, 3, 0.04, r)
    c.stem(st, 0.005, 0.004, "#7A4A36")
    p, t = at(st, 1.0)
    for a in (-40, 5, 45):
        b = curve(p, rot(t, a + r.uniform(-10, 10)), r.uniform(0.1, 0.14), r.uniform(-0.4, 0.4), 5, 0.06, r)
        c.stem(b, 0.0035, 0.0025, "#7A4A36")
        alt_leaves(c, b, 5, "laurel_leaf", 0.075, 0.008, 50, r, f0=0.45, droop=0.08, fold=0.18, terminal=False,
                   pet_col="#6A7A3A")
        q, tt = at(b, 1.0)
        if bloom:
            truss(c, q + tt * 0.02, 0.045, 16, "laurel_floret", 0.02, r, "laurel_bud", 6, lift=0.05)
        else:
            whorl(c, q, 6, "laurel_leaf", 0.07, r, droop=0.1, fold=0.18, tilt_d=tt)
    return c


def laurel_a():
    return _laurel(121, False)


def laurel_b():
    return _laurel(122, True)


# =============================================================================================
# ground layer
def _frond(c, base, d, stipe, blade, pairs, tex, Lmax, r, stipe_col, shape="lanceolate", ang=(72, 84)):
    pts = curve(base, d, stipe + blade, r.uniform(-0.15, 0.15), 12, 0.01, r)
    c.stem(pts, 0.0028, 0.0012, stipe_col)
    f0 = stipe / (stipe + blade)
    for k in range(pairs):
        g = (k + 0.5) / pairs
        f = f0 + (1 - f0) * g
        p, t = at(pts, f)
        if shape == "lanceolate":           # widest a third of the way up, tapering to the tip
            env = math.sin(math.pi * min(1, 0.25 + 0.95 * g)) * (1 - 0.6 * g)
        else:                                # cinnamon fern: oblong, abrupt taper at the top
            env = math.sin(math.pi * min(1, 0.12 + 0.9 * g)) ** 0.5
        L = Lmax * max(0.18, env)
        for s in (-1, 1):
            dd = rot(t, s * r.uniform(*ang))
            c.leaf(tex, p + dd * 0.002, dd, L * r.uniform(0.92, 1.05), tint=r.uniform(0.85, 1.1), fold=0.14,
                   droop=0.05, roll=(0 if s < 0 else math.pi) + math.radians(r.uniform(-10, 10)),
                   lift=0.004 + 0.0005 * k)


def xmas_fern_a():
    c = Card((0.16, 0.56), (144, 504), seed=131)
    _frond(c, V((0, 0, 0)), V((0, 1, 0)), 0.1, 0.43, 22, "xmas_pinna", 0.05, c.rng, "#5A5A30")
    return c


def xmas_fern_b():
    c = Card((0.15, 0.48), (156, 500), seed=132)
    _frond(c, V((0, 0, 0)), V((0.04, 1, 0)), 0.08, 0.38, 20, "xmas_pinna", 0.046, c.rng, "#5A5A30")
    return c


def cinn_fern_a():
    c = Card((0.24, 0.9), (136, 510), seed=141)
    _frond(c, V((0, 0, 0)), V((0, 1, 0)), 0.14, 0.72, 20, "cinn_pinna", 0.095, c.rng, "#6E7A3A", "oblong",
           (62, 76))
    return c


def cinn_fertile():
    c = Card((0.08, 0.62), (64, 496), seed=142)
    r = c.rng
    pts = curve((0, 0, 0), (0, 1, 0), 0.6, 0.05, 10, 0.01, r)
    c.stem(pts, 0.0028, 0.0018, "#7A5A34")
    for k in range(18):
        p, t = at(pts, 0.45 + 0.55 * (k + 0.5) / 18)
        for s in (-1, 1):
            c.leaf("cinn_fertile", p, rot(t, s * r.uniform(20, 40)), r.uniform(0.02, 0.03), tint=r.uniform(0.8, 1.1),
                   fold=0.2, droop=0, lift=0.004)
    return c


def _doghobble(seed):
    c = Card((0.44, 1.0), (220, 500), seed=seed)
    r = c.rng
    pts = curve((0.03, 0, 0), (0.3, 1, 0), 0.9, 0.85, 12, 0.02, r)
    c.stem(pts, 0.004, 0.0018, "#7A4A34")
    s = 1
    n = 15
    for k in range(n):
        f = 0.18 + 0.8 * (k + 0.5) / n
        p, t = at(pts, f)
        d = rot(t, s * r.uniform(48, 64))
        new = f > 0.82
        c.leaf("doghobble_new" if new else "doghobble_leaf", p + d * 0.004, d,
               r.uniform(0.095, 0.125) * (0.65 if new else 1.0), tint=r.uniform(0.85, 1.1), fold=0.16, droop=0.1,
               roll=math.radians(r.uniform(-15, 15)), lift=0.006)
        s = -s
    return c


def doghobble_a():
    return _doghobble(151)


def doghobble_b():
    return _doghobble(152)


def moss_fringe():
    c = Card((0.3, 0.08), (480, 128), seed=161)
    r = c.rng
    x = -0.145
    while x < 0.145:
        k = r.randrange(9)
        c.leaf(f"moss_{k}", (x, 0.0, 0), (r.uniform(-0.25, 0.25), 1, 0), r.uniform(0.04, 0.075), tint=r.uniform(0.8, 1.15),
               fold=0, droop=0, lift=r.uniform(0, 0.01))
        x += r.uniform(0.008, 0.016)
    return c


# =============================================================================================
# understory (Appendix B's 4%: flowering dogwood, sourwood) and the bald's edge (flame azalea)
def _dogwood(seed, pairs, fruit):
    c = Card((0.42, 0.42), (400, 400), seed=seed)
    r = c.rng
    tw = curve((0, 0, 0), (0.05, 1, 0), 0.2, r.uniform(-0.2, 0.2), 6, 0.02, r)
    c.stem(tw, 0.004, 0.003, "#6E5C4E")
    for k in range(pairs):
        p, t = at(tw, 0.4 + 0.55 * k / max(1, pairs))
        for s in (-1, 1):                      # opposite, on short petioles, tipped up
            d = rot(t, s * r.uniform(48, 64))
            q = p + d * r.uniform(0.012, 0.02)
            c.leaf("dogwood_leaf", q, rot(d, -s * r.uniform(8, 22)), r.uniform(0.095, 0.115), tint=tints(r),
                   hue=r.uniform(-0.04, 0.03), droop=0.12, fold=0.18, lift=0.006 + r.uniform(0, 0.01))
    p, t = at(tw, 1.0)
    for s in (-1, 1):
        d = rot(t, s * r.uniform(18, 30))
        c.leaf("dogwood_leaf", p + d * 0.01, d, r.uniform(0.1, 0.12), tint=tints(r), droop=0.12, fold=0.18, lift=0.02)
    if fruit:                                  # this year's drupes, still green in June
        for i in range(7):
            q = p + rot((0, 1, 0), r.uniform(0, 360)) * r.uniform(0.004, 0.014)
            c.leaf("dogwood_fruit", q, rot((0, 1, 0), r.uniform(0, 360)), 0.009, tint=tints(r, 0.9, 1.1), fold=0,
                   droop=0, lift=0.03)
    return c


def dogwood_a():
    return _dogwood(181, 2, True)


def dogwood_b():
    return _dogwood(182, 3, False)


def _sourwood(seed, racemes):
    c = Card((0.46, 0.46), (400, 400), seed=seed)
    r = c.rng
    tw = curve((0, 0, 0), (-0.05, 1, 0), 0.3, r.uniform(-0.25, 0.25), 8, 0.03, r)
    c.stem(tw, 0.0035, 0.0022, "#7A5E48")
    alt_leaves(c, tw, 6, "sourwood_leaf", 0.13, 0.012, 50, r, f0=0.15, droop=0.1, fold=0.14, terminal=not racemes)
    if racemes:                                # a spray of one-sided racemes from the tip, in bud
        p, t = at(tw, 1.0)
        for a in (-34, -12, 10, 32):
            rc = curve(p, rot(t, a + r.uniform(-8, 8)), r.uniform(0.09, 0.13), r.uniform(-0.5, 0.5), 6, 0.01, r)
            c.stem(rc, 0.0012, 0.0008, "#C9C6A4")
            for k in range(14):
                q, tt = at(rc, 0.1 + 0.9 * (k + 0.5) / 14)
                c.leaf("sourwood_bud", q, rot(tt, 90), 0.007, tint=tints(r, 0.92, 1.05), fold=0, droop=0, lift=0.02)
    return c


def sourwood_a():
    return _sourwood(191, False)


def sourwood_b():
    return _sourwood(192, True)


def azalea_a():                  # flame azalea in bloom (mid-June at the bald's edge): a truss over a leaf whorl
    c = Card((0.36, 0.36), (360, 360), seed=201)
    r = c.rng
    st = curve((0, 0, 0), (0, 1, 0), 0.13, 0.15, 4, 0.03, r)
    c.stem(st, 0.004, 0.003, "#6E5A48")
    p, _ = at(st, 1.0)
    whorl(c, p, 6, "azalea_leaf", 0.07, r, droop=0.12, fold=0.16)
    truss(c, p, 0.06, 8, "azalea_floret", 0.045, r, lift=0.07)
    return c


def azalea_b():                  # leaves only, an open forked twig
    c = Card((0.36, 0.36), (360, 360), seed=202)
    r = c.rng
    st = curve((0, 0, 0), (0, 1, 0), 0.08, 0.0, 3, 0.03, r)
    c.stem(st, 0.004, 0.003, "#6E5A48")
    p, t = at(st, 1.0)
    for s in (-1, 1):
        b = curve(p, rot(t, s * 30), 0.11, -s * 0.2, 4, 0.04, r)
        c.stem(b, 0.003, 0.0022, "#6E5A48")
        q, _ = at(b, 1.0)
        whorl(c, q, 5, "azalea_leaf", 0.065, r, droop=0.15, fold=0.16, tilt_d=rot(t, s * 30))
    return c


# =============================================================================================
# opaque shell / mat tiles (seamless: leaves wrap around the window)
def _tile(seed, size, px, bg, items, trusses=()):
    c = Card((size, size), (px, px), seed=seed)
    c.opaque_bg = bg
    c.wrap = True
    r = c.rng
    for floret, n, R, fs, nf in trusses:        # flower trusses as clusters (how a bald reads from 20 m)
        for i in range(n):
            truss(c, V((r.uniform(-size / 2, size / 2), r.uniform(0, size), 0)), R, nf, floret, fs, r, lift=0.12)
    for tex, n, L, lift in items:
        for i in range(n):
            x, y = r.uniform(-size / 2, size / 2), r.uniform(0, size)
            d = rot((0, 1, 0), r.uniform(0, 360))
            c.leaf(tex, (x, y, 0), d, L * r.uniform(0.8, 1.1), tint=r.uniform(0.7, 1.08), hue=r.uniform(-0.04, 0.04),
                   fold=0.2, droop=0.1, lift=lift + r.uniform(0, 0.05))
    return c


def rosebay_tile():
    return _tile(171, 0.9, 320, "#1E2E1C", [("rosebay_leaf", 80, 0.19, 0.0)])


def laurel_tile():
    return _tile(172, 0.6, 320, "#243420", [("laurel_leaf", 130, 0.075, 0.0)], [("laurel_floret", 4, 0.045, 0.02, 16)])


def catawba_tile():
    return _tile(173, 0.7, 320, "#26381F", [("catawba_leaf", 95, 0.11, 0.0)], [("catawba_floret", 3, 0.075, 0.05, 15)])


def moss_tile():
    c = Card((0.25, 0.25), (256, 256), seed=174)
    c.opaque_bg = "#2E4A1E"
    c.wrap = True
    r = c.rng
    for i in range(520):
        x, y = r.uniform(-0.125, 0.125), r.uniform(0, 0.25)
        c.leaf(f"moss_{r.randrange(9)}", (x, y, 0), rot((0, 1, 0), r.uniform(0, 360)), r.uniform(0.03, 0.05),
               tint=r.uniform(0.7, 1.15), fold=0, droop=0, lift=r.uniform(0, 0.03))
    return c


ATLASES = {
    "br_broadleaf": dict(size=2048, nor_size=1024, textures=T_BROAD, cards={
        "poplar_a": poplar_a, "poplar_b": poplar_b, "red_oak_a": red_oak_a, "red_oak_b": red_oak_b,
        "white_oak_a": white_oak_a, "white_oak_b": white_oak_b, "chestnut_oak_a": chestnut_oak_a,
        "chestnut_oak_b": chestnut_oak_b, "hickory_a": hickory_a, "hickory_b": hickory_b,
        "hickory_strips": hickory_strips, "maple_a": maple_a, "maple_b": maple_b, "buckeye_a": buckeye_a,
        "buckeye_b": buckeye_b}),
    "br_evergreen": dict(size=2048, nor_size=1024, textures=T_EVER, cards={
        "hemlock_a": hemlock_a, "hemlock_b": hemlock_b, "pine_a": pine_a, "pine_b": pine_b,
        "rosebay_a": rosebay_a, "rosebay_b": rosebay_b, "rosebay_c": rosebay_c, "catawba_a": catawba_a,
        "catawba_b": catawba_b, "laurel_a": laurel_a, "laurel_b": laurel_b,
        "rosebay_tile": rosebay_tile, "laurel_tile": laurel_tile, "catawba_tile": catawba_tile}),
    "br_ground": dict(size=1024, nor_size=512, textures=T_GROUND, cards={
        "xmas_fern_a": xmas_fern_a, "xmas_fern_b": xmas_fern_b, "cinn_fern_a": cinn_fern_a,
        "cinn_fertile": cinn_fertile, "doghobble_a": doghobble_a, "doghobble_b": doghobble_b,
        "moss_fringe": moss_fringe, "moss_tile": moss_tile}),
    "br_understory": dict(size=1024, nor_size=512, textures=T_UNDER, cards={
        "dogwood_a": dogwood_a, "dogwood_b": dogwood_b, "sourwood_a": sourwood_a, "sourwood_b": sourwood_b,
        "azalea_a": azalea_a, "azalea_b": azalea_b}),
}
