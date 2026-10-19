"""Floor pieces for the entry wing (origin = floor centre). Variants (`variant`):

  branch_vase     a tall matte stoneware floor vase with a few bare sculptural branches (~1.7 m);
                  the vase collides, the branches don't
  umbrella_stand  a bronze umbrella stand with two furled umbrellas (walnut crook handles);
                  the stand collides
  shoes           a pair of cognac loafers set down side by side (no collider)
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

NAME = "DecorAFloor"

P = dict(name=NAME, variant="branch_vase", seed=3, vase="stoneware", branches=5, height=1.75)


def _branch(B, rnd, start, direction, length, r0, depth=0):
    """A bare branch: a gently wandering tapered tube with one or two side shoots."""
    pts = [Vector(start)]
    d = Vector(direction).normalized()
    n = 6
    for i in range(n):
        d = (d + Vector((rnd.uniform(-0.25, 0.25), rnd.uniform(-0.25, 0.25), rnd.uniform(-0.05, 0.15)))).normalized()
        pts.append(pts[-1] + d * length / n)
    B.add("twig", kit.tube([tuple(p) for p in pts], r0, sides=5, taper=r0 * 0.25))
    if depth < 2:
        for k in range(2 if depth == 0 else 1):
            i = rnd.randint(2, n - 2)
            side = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(0.2, 0.9)))
            _branch(B, rnd, pts[i], (d + side).normalized(), length * rnd.uniform(0.3, 0.45), r0 * 0.5, depth + 1)


def branch_vase(B, rnd, p):
    key = p["vase"]
    h, r = 0.62, 0.16
    outer = [(r * 0.62, 0.0), (r * 0.7, 0.01), (r * 0.94, h * 0.25), (r, h * 0.48), (r * 0.82, h * 0.72),
             (r * 0.48, h * 0.88), (r * 0.42, h * 0.97), (r * 0.46, h)]
    B.add(key, kit.lathe(kit.open_vessel(outer, wall=0.012, floor=0.03, per=1, inner_n=2), 18))
    top = p["height"]
    for i in range(p["branches"]):
        a = 2 * math.pi * i / p["branches"] + rnd.uniform(-0.3, 0.3)
        lean = rnd.uniform(0.18, 0.42)
        start = (0.02 * math.cos(a), 0.02 * math.sin(a), h - 0.12)
        dirn = (lean * math.cos(a), lean * math.sin(a), 1.0)
        _branch(B, rnd, start, dirn, (top - h) * rnd.uniform(0.75, 1.1), 0.009)


def umbrella(B, M, rnd, canopy="coat_navy", handle="walnut"):
    """A furled umbrella standing on its tip: pleated canopy, ferrule, shaft, a crook handle."""
    segs = 8
    prof = [(0.004, 0.06), (0.022, 0.22), (0.034, 0.42), (0.03, 0.56), (0.012, 0.66), (0.007, 0.68)]
    bm = kit.lathe(prof, segs * 2, sharp=80)
    for v in bm.verts:                      # pleats: alternate verts pulled in
        ang = math.atan2(v.co.y, v.co.x)
        k = round(ang / (math.pi / segs))
        if k % 2:
            v.co.x *= 0.72
            v.co.y *= 0.72
    for f in bm.faces:
        f.smooth = False
    B.add(canopy, bm, M)
    B.add("black", kit.tube([(0, 0, 0.0), (0, 0, 0.065)], 0.004, sides=5, cap=False), M)
    B.add("black", kit.tube([(0, 0, 0.66), (0, 0, 0.80)], 0.0055, sides=6, cap=False), M)
    hook = [(0, 0, 0.80), (0, 0, 0.84)] + [(0.035 - 0.035 * math.cos(math.pi * k / 6), 0, 0.84 + 0.035 * math.sin(math.pi * k / 6))
                                          for k in range(1, 8)]
    B.add(handle, kit.tube(hook, 0.0085, sides=6), M)


def umbrella_stand(B, rnd, p):
    r, h = 0.11, 0.48
    B.add("bronze", kit.lathe([(0.0, 0.0), (r, 0.0), (r, h), (r - 0.004, h), (r - 0.004, 0.012), (0.0, 0.012)], 20, sharp=50))
    umbrella(B, at(0.03, 0.02, 0.012, 20, tilt=(9, "Y")), rnd, "coat_navy")
    umbrella(B, at(-0.04, -0.02, 0.012, 200, tilt=(7, "X")), rnd, "coat_charcoal")


def shoe(B, M, leather="leather", sole="wool"):
    """A penny loafer (right shoe; mirror for the left): a sole, an upper lofted from rings
    over the sole outline, a leather vamp and a dark opening behind it, a penny strap."""
    L, n = 0.27, 16

    def outline(k=1.0):
        pts = []
        for i in range(n):
            t = 2 * math.pi * i / n
            c, s_ = math.cos(t), math.sin(t)
            x = math.copysign(abs(c) ** 0.75, c)               # blunter toe and heel than an ellipse
            hw = 0.047 if c > 0 else 0.039
            hw *= 1.0 - 0.22 * max(0.0, c) ** 3
            pts.append((L / 2 * x * k, hw * s_ * k + 0.006 * max(c, 0.0)))
        return pts

    def h(x):                                               # top of the upper along the shoe
        t = x / (L / 2)
        return 0.064 + 0.004 * -t if t < 0.05 else 0.064 - 0.028 * ((t - 0.05) / 0.95) ** 1.3

    sole_r = [[(x, y, z) for x, y in outline(1.0)] for z in (0.0, 0.017)]
    B.add(sole, kit.loft(sole_r, smooth=False), M)
    rings = []
    for k, f in ((1.0, 0.0), (0.97, 0.5), (0.88, 0.86), (0.66, 1.0)):
        rings.append([(x, y, 0.017 + (h(x / k) - 0.017) * f) for x, y in outline(k)])
    B.add(leather, kit.loft(rings, smooth=True, sharp_rows=(0,)), M)
    top = rings[-1]
    front = [i for i in range(n) if top[i][0] >= -0.004]
    rear = [i for i in range(n) if top[i][0] <= 0.004]
    bm = bmesh.new()                                        # vamp: leather over the front of the foot
    bm.faces.new([bm.verts.new(top[i]) for i in front])
    B.add(leather, bm, M)
    bm = bmesh.new()                                        # opening: the dark lining, sunk inside the collar
    cx = sum(top[i][0] for i in rear) / len(rear)
    bm.faces.new([bm.verts.new((cx + (top[i][0] - cx) * 0.94, top[i][1] * 0.92, top[i][2] - 0.022)) for i in rear])
    B.add(sole, bm, M)
    # penny strap across the vamp, following its curve
    zs = h(0.03)
    pts = [(0.03, y, zs - 0.012 * (y / 0.04) ** 2) for y in (-0.042, -0.02, 0.0, 0.02, 0.042)]
    bm = bmesh.new()
    rows = [[bm.verts.new((x + o, y, z + 0.003)) for o in (-0.007, 0.007)] for x, y, z in pts]
    for a, b in zip(rows, rows[1:]):
        bm.faces.new((a[0], a[1], b[1], b[0]))
    B.add(leather, bm, M)


def shoes(B, rnd, p):
    shoe(B, at(0.0, -0.06, 0, 4))
    m = at(0.02, 0.07, 0, -6)
    from mathutils import Matrix
    shoe(B, m @ Matrix.Scale(-1, 4, Vector((0, 1, 0))))


RECIPES = {f.__name__: f for f in (branch_vase, umbrella_stand, shoes)}


def build(**overrides):
    p = {**P, **overrides}
    rnd = random.Random(p["seed"])
    collide = {"branch_vase": ("stoneware", p["vase"]), "umbrella_stand": ("bronze",)}.get(p["variant"], ())
    B = kit.Builder(p["name"], collide=collide)
    RECIPES[p["variant"]](B, rnd, p)
    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
