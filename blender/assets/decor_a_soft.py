"""Soft things and a few personal objects for benches, a vanity and the den sectional
(origin = the centre of the surface, placed at its height; front -y). Variants (`variant`):

  bench_entry      entry_bench (2.3 m, rot 90 on the entry's west wall): a folded throw at one end,
                   art books with a bowl at the other
  bench_cloak      the cloakroom's long entry_bench: a felt hat and a folded scarf
  bench_hatboxes   the cloakroom's south bench (1.45 m): two stacked hat boxes, a folded throw
  bench_powder     the powder room bench: a walnut tray of rolled hand towels and a candle
  vanity           the powder vanity (top 0.805 m, basin at x 0): folded linen hand towels,
                   a soap pump and a bud vase on a stone tray
  sectional_throw  placed exactly like living_sectional (its origin): a throw over its left arm

No colliders.
"""
import importlib
import math
import os
import random
import sys

import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_a_kit as kit  # noqa: E402
from decor_a_kit import at  # noqa: E402

importlib.reload(kit)
common = kit.common

NAME = "DecorASoft"

P = dict(name=NAME, variant="bench_entry", seed=7, palette="neutral", base="", base_z=0.0, base_rot=0.0)


def hat(B, M, felt="coat_camel", band="coat_charcoal"):
    """Felt fedora lying crown-up: a curled brim, a tapered crown with a pinched top, a band."""
    brim = [(0.0, 0.004), (0.095, 0.004), (0.15, 0.002), (0.172, 0.008), (0.178, 0.016), (0.171, 0.017),
            (0.15, 0.010), (0.095, 0.012)]
    bm = kit.lathe(brim, 20, sharp=60)
    for v in bm.verts:                      # an oval brim, its sides curled up a little
        v.co.y *= 0.88
        v.co.z += 0.012 * (v.co.x / 0.175) ** 2
    B.add(felt, bm, M)
    crown = [(0.092, 0.010), (0.090, 0.05), (0.083, 0.095), (0.07, 0.118), (0.035, 0.124), (0.0, 0.118)]
    bm = kit.lathe(crown, 16, sharp=70)
    for v in bm.verts:
        v.co.y *= 0.85
        if v.co.z > 0.1:                    # centre-dent and front pinch
            v.co.z -= 0.02 * max(0.0, 1 - (abs(v.co.x) / 0.06) ** 2) * (1 - abs(v.co.y) / 0.08)
    B.add(felt, bm, M)
    bm = kit.lathe([(0.0925, 0.012), (0.0915, 0.034), (0.0905, 0.034)], 16)
    for v in bm.verts:
        v.co.y *= 0.85
    B.add(band, bm, M)


def hatbox(B, M, r=0.17, h=0.17, key="oat", strap="leather"):
    B.add(key, kit.lathe([(r, 0.0), (r, h - 0.03)], 24), M)
    B.add(key, kit.lathe([(r + 0.006, h - 0.045), (r + 0.006, h), (r * 0.7, h + 0.002), (0.0, h + 0.002)], 24, sharp=50), M)
    # a leather strap over the lid, down both sides
    s = r + 0.009
    pts = [(-s, 0, h - 0.05), (-s, 0, h - 0.005), (-r * 0.6, 0, h + 0.006), (r * 0.6, 0, h + 0.006), (s, 0, h - 0.005),
           (s, 0, h - 0.05)]
    bm = bmesh.new()
    rows = [[bm.verts.new((x, y + o, z)) for o in (-0.012, 0.012)] for x, y, z in pts]
    for a, b in zip(rows, rows[1:]):
        f = bm.faces.new((a[0], b[0], b[1], a[1]))
        f.smooth = False
    for f in bm.faces:            # face outward (up on the lid, away from the box on the sides)
        c = f.calc_center_median()
        f.normal_update()
        if f.normal.dot(Vector((c.x, 0.0, c.z - (h - 0.06)))) < 0:
            f.normal_flip()
    B.add(strap, bm, M)


def rolled_towel(B, M, key="oat", L=0.24, r=0.032):
    """A rolled hand towel lying along x: a spiral end on each side."""
    prof = [(0.0, -L / 2), (r * 0.6, -L / 2 - 0.001), (r, -L / 2 + 0.006), (r, L / 2 - 0.006), (r * 0.6, L / 2 + 0.001),
            (0.0, L / 2)]
    bm = kit.lathe(prof, 12, sharp=60)
    # lie it down on its side
    for v in bm.verts:
        x, y, z = v.co
        v.co = Vector((z, y, x + r))
    B.add(key, bm, M)


def soap_pump(B, M, body="porcelain", pump="bronze_polished"):
    B.add(body, kit.lathe([(0.0, 0.0), (0.034, 0.0), (0.036, 0.008), (0.036, 0.13), (0.026, 0.15), (0.012, 0.155),
                           (0.0, 0.155)], 14, sharp=50), M)
    B.add(pump, kit.lathe([(0.012, 0.155), (0.012, 0.17), (0.007, 0.172), (0.007, 0.19), (0.0, 0.19)], 10, sharp=50), M)
    B.add(pump, kit.box((0.012, 0.045, 0.012), (0, -0.018, 0.19)), M)
    B.add(pump, kit.lathe([(0.0, 0.0), (0.012, 0.0), (0.012, 0.012), (0.0, 0.012)], 8), M @ at(0, 0, 0.184))


def sprig(B, M, rnd, h=0.34, n=3):
    """A few blossom twigs for a bud vase (entry_flowers' twig and blossom materials)."""
    for i in range(n):
        a = 2 * math.pi * i / n + rnd.uniform(-0.4, 0.4)
        lean = rnd.uniform(0.06, 0.14)
        top = Vector((lean * math.cos(a), lean * math.sin(a), h * rnd.uniform(0.8, 1.05)))
        pts = [Vector((0, 0, 0.0)), Vector((0, 0, 0.1)), top * 0.6 + Vector((0, 0, 0.06)), top]
        B.add("twig", kit.tube([tuple(p) for p in pts], 0.0028, sides=4, taper=0.0012), M)
        for k in range(4):
            t = 0.45 + 0.17 * k
            c = pts[2].lerp(pts[3], (t - 0.45) / 0.55) if t > 0.45 else pts[2]
            e = kit.ellipsoid(0.011, 0.011, 0.008, 6, 4, z0=0.0)
            B.add("blossom" if k % 2 == 0 else "blossom_blush", e,
                  M @ at(c.x + rnd.uniform(-0.01, 0.01), c.y + rnd.uniform(-0.01, 0.01), c.z, rnd.uniform(0, 90)))


def bench_entry(B, rnd, p):
    kit.folded(B, at(0.70, 0.0, -0.004, 4), "oat", w=0.44, d=0.34, layers=3, t=0.016)
    z = kit.stack(B, at(-0.72, 0.01, -0.004, -6), rnd, n=2, size=(0.34, 0.27), palette=p["palette"])
    kit.bowl(B, at(-0.71, 0.0, z - 0.004), "stoneware", r=0.09, h=0.045, foot=0.55)


def bench_cloak(B, rnd, p):
    hat(B, at(0.45, 0.02, -0.006, 25))
    kit.folded(B, at(-0.55, 0.0, -0.004, -5), "coat_navy", w=0.36, d=0.26, layers=4, t=0.011)


def bench_hatboxes(B, rnd, p):
    hatbox(B, at(-0.42, 0.0, 0.0, 10), r=0.18, h=0.17)
    hatbox(B, at(-0.43, 0.01, 0.174, -14), r=0.145, h=0.14, key="coat_camel")
    kit.folded(B, at(0.4, 0.0, -0.004, 3), "coat_oat", w=0.42, d=0.3, layers=3, t=0.015)


def bench_powder(B, rnd, p):
    M = at(-0.42, 0.0, -0.003, 0)
    kit.tray(B, M, "walnut", w=0.36, d=0.24, h=0.03)
    for i in range(3):
        rolled_towel(B, M @ at(0.0, -0.065 + 0.065 * i, 0.006), L=0.28, r=0.03)
    kit.candle(B, at(0.0, 0.03, -0.003), r=0.042, h=0.095, holder="stoneware")


def vanity(B, rnd, p):
    kit.folded(B, at(-0.58, -0.02, 0.0, 3), "oat", w=0.26, d=0.19, layers=3, t=0.014, crown=0.003)
    kit.folded(B, at(-0.58, -0.02, 0.040, -2), "oat", w=0.26, d=0.19, layers=2, t=0.014, crown=0.003)
    M = at(0.56, 0.02, 0.0, -4)
    kit.tray(B, M, "stoneware", w=0.30, d=0.17, h=0.018, rim=0.007, r=0.02)
    soap_pump(B, M @ at(-0.07, 0.0, 0.005))
    kit.vase(B, M @ at(0.07, 0.01, 0.005), "porcelain", "bud", h=0.13, r=0.042)
    sprig(B, M @ at(0.07, 0.01, 0.1), rnd, h=0.24, n=3)


def sectional_throw(B, rnd, p):
    import living_sectional
    import living_sofa
    sp = living_sectional.P
    w, d, cl = sp["width"], sp["depth"], sp["chaise_len"]
    total_d = d + cl
    x0 = -w / 2
    y_front = total_d / 2 - d
    bm = living_sofa.throw_bmesh(x0, x0 + sp["arm_w"], sp["arm_top"] + 0.012, y_front + 0.2, y_front + 0.66,
                                 drop_in=0.12, drop_out=0.32, seed=5)
    B.add("ink", bm, smooth=True)


RECIPES = {f.__name__: f for f in (bench_entry, bench_cloak, bench_hatboxes, bench_powder, vanity, sectional_throw)}



def build(**overrides):
    p = {**P, **overrides}
    rnd = random.Random(p["seed"])
    B = kit.Builder(p["name"])
    RECIPES[p["variant"]](B, rnd, p)
    if p["base"]:
        kit.with_base(B, p["base"], at(0, 0, -p["base_z"], p["base_rot"]))
    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
