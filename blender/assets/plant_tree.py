"""Tree generator for the estate's planting (wrapped by plant_tree_round / _olive /
_cypress / _multistem / _fruit). `build(kind=..., seed=...)` makes a trunk, limbs and a
branching skeleton (trunk, limbs, branches, twigs) carrying many small leaf clumps with gaps
between them, so the crown is open and ragged with limbs showing; all low-poly: outdoors everything is merged and lit per vertex (baked).

Origin: trunk base on the ground, z up, units metres. Materials: outdoor.foliage() for the
green crowns, flat colours for olive / birch (silver-green, light green), flat bark.
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plant_common as pc  # noqa: E402

importlib.reload(pc)
common, outdoor = pc.common, pc.outdoor

NAME = "PlantTree"
P = dict(name=NAME, kind="round", seed=3)

# crown colours (linear RGB)
OLIVE_LEAF = (0.088, 0.108, 0.062)       # silver-green
BIRCH_LEAF = (0.062, 0.128, 0.026)       # fresh light green
BIRCH_BARK = (0.46, 0.44, 0.39)          # pale papery trunk
APPLE_RED = (0.30, 0.025, 0.02)
OLIVE_BARK = (0.11, 0.095, 0.08)         # grey-brown, lighter than the shared bark


def v3(x, y, z):
    return Vector((x, y, z))


def polar(r, a, z):
    return v3(r * math.cos(a), r * math.sin(a), z)


def limb_to(bm, start, end, r0, r1, rng, sides=5, bend=0.25, mid=2, **kw):
    """Gently bowed limb from start to end."""
    start, end = Vector(start), Vector(end)
    d = end - start
    side = Vector((-d.y, d.x, 0))
    side = side.normalized() * d.length * bend * rng.uniform(-1, 1) if side.length > 1e-4 else Vector()
    ctrl = [start, start.lerp(end, 0.5) + side + v3(0, 0, d.length * 0.05), end]
    pts = pc.spline(ctrl, per=mid)
    pc.sweep(bm, pts, pc.taper(len(pts), r0, r1), sides=sides, rng=rng, noise=0.06)
    return pts


# ------------------------------------------------------------------ kinds
def leafy(crown, rng, tip, d, n, rmin, rmax, spread, kinds=("ico", "pad"), droop=0.35, squash=0.55):
    """n leaf clumps around a branch tip: one on the end, the rest scattered back along the
    last bit of the branch, so the tip reads as a loose sprig with gaps, not one ball."""
    tip = Vector(tip)
    d = Vector(d).normalized()
    for i in range(n):
        if i == 0:
            c = tip + d * rmax * 0.25
        else:
            c = tip - d * rng.uniform(0.2, 1.0) * spread + v3(rng.uniform(-1, 1), rng.uniform(-1, 1),
                                                              rng.uniform(-0.45, 0.7)) * spread * 0.7
        out = v3(c.x, c.y, 0)
        out = out.normalized() * droop if out.length > 0.05 else v3(0, 0, 0)
        pc.clump(crown, c, rng.uniform(rmin, rmax), rng, kind=rng.choice(kinds), up=v3(-out.x, -out.y, 1.0),
                 squash=squash)


def grow_crown(bk, crown, rng, base, d0, plan, clumps, inner=None, upbias=0.3):
    """Recursive branching. plan: list of levels (n forks, angle, length, r0, r1, sides, segs,
    droop); the last level's tips get leaf clumps (kwargs in `clumps`)."""
    tips = []

    def rec(start, d, level, r_in):
        n, ang, length, r0, r1, sides, segs, droop = plan[level]
        for bd in pc.fork_dirs(d, n, ang, rng):
            if level > 0:
                bd = (bd + v3(0, 0, upbias)).normalized()
            last = level == len(plan) - 1
            end, ed, _ = pc.branch(bk, start, bd, length * rng.uniform(0.85, 1.15), r0, r1, rng, sides=sides,
                                   segs=segs, bend=0.12, droop=droop, tip=last)
            if last:
                tips.append((end, ed))
            else:
                if inner and level == len(plan) - 2:
                    leafy(crown, rng, end, ed, **inner)
                rec(end, ed, level + 1, r1)

    rec(Vector(base), Vector(d0), 0, 0)
    for tip, d in tips:
        leafy(crown, rng, tip, d, **clumps)
    return tips


def tree_round(p, rng, bk, crown):
    """Broad deciduous tree, 12 m: a thick forking trunk, three limbs, branches and twigs,
    with ~30 small leaf clumps along the outer twigs: open, ragged, limbs showing."""
    end, d, _ = pc.branch(bk, (0, 0, 0), (0.04, 0.02, 1), 4.4, 0.5, 0.3, rng, sides=7, segs=3, bend=0.04,
                          tip=False)
    plan = [(3, 30, 4.4, 0.27, 0.13, 5, 2, 0.04),
            (2, 30, 3.2, 0.13, 0.055, 4, 1, 0.08),
            (2, 32, 2.0, 0.055, 0.02, 3, 1, 0.15)]
    tips = grow_crown(bk, crown, rng, end, d, plan,
                      dict(n=3, rmin=1.3, rmax=2.0, spread=1.5, droop=0.4, squash=0.7, kinds=("ico", "pad", "pad")),
                      inner=dict(n=1, rmin=1.3, rmax=1.8, spread=1.0, droop=0.4, squash=0.7), upbias=0.35)
    # a few clumps over the middle so the crown is a dome, not a flat plate
    top = max(t[0].z for t in tips)
    for i in range(2):
        a = rng.uniform(0, 6.28)
        pc.clump(crown, polar(rng.uniform(0.3, 2.2), a, top - rng.uniform(0.2, 1.6)), rng.uniform(1.5, 2.1), rng,
                 kind="ico", squash=0.75, up=v3(0, 0, 1))


def tree_olive(p, rng, bk, crown):
    """Gnarled multi-stem olive, 5 m: thick fluted stems forking low, small silver clumps."""
    a0 = rng.uniform(0, 6.28)
    ends = []
    for i in range(3):
        a = a0 + i * 2.09 + rng.uniform(-0.3, 0.3)
        lean = rng.uniform(0.9, 1.15)
        pts = pc.spline([v3(rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05), 0),
                         polar(0.14 * lean, a, 0.55), polar(0.5 * lean, a + 0.6, 1.2),
                         polar(0.8 * lean, a + 0.2, 1.6 + 0.3 * i), polar(1.0 * lean, a, 2.0 + 0.5 * i)], per=1)
        rad = pc.taper(len(pts), 0.27, 0.1, flare=0.12, flare_len=0.12)
        pc.sweep(bk, pts, rad, sides=6, lobe=0.3, lobes=3, twist=0.9 + i, noise=0.12, rng=rng, tip=False)
        ends.append((pts[-1], (pts[-1] - pts[-2]).normalized()))
    plan = [(3, 38, 1.5, 0.1, 0.04, 4, 1, 0.1)]
    for end, d in ends:
        d = v3(d.x * 1.1, d.y * 1.1, d.z * rng.uniform(0.7, 1.0))
        grow_crown(bk, crown, rng, end, d, plan, dict(n=2, rmin=0.75, rmax=1.15, spread=0.9, droop=0.35,
                                                       kinds=("ico", "pad", "pad"), squash=0.7), upbias=0.15)


def tree_multistem(p, rng, bk, crown):
    """Multi-stem birch-like tree, 7 m: pale slender stems forking into a few branches, light
    green clumps hung at different heights along them (airy, the stems show)."""
    a0 = rng.uniform(0, 6.28)
    for i in range(3):
        a = a0 + i * 2.09 + rng.uniform(-0.4, 0.4)
        lean = rng.uniform(0.7, 1.0)
        h = rng.uniform(2.9, 3.7)
        pts = pc.spline([v3(rng.uniform(-0.06, 0.06), rng.uniform(-0.06, 0.06), 0),
                         polar(0.4 * lean, a, h * 0.55), polar(0.75 * lean, a, h)], per=1)
        pc.sweep(bk, pts, pc.taper(len(pts), 0.12, 0.06, flare=0.04, flare_len=0.1), sides=5, noise=0.05,
                 rng=rng, tip=False)
        end, d = pts[-1], (pts[-1] - pts[-2]).normalized()
        plan = [(3, 30, 2.5, 0.06, 0.02, 4, 1, 0.05)]
        grow_crown(bk, crown, rng, end, d, plan, dict(n=3, rmin=0.65, rmax=1.05, spread=1.5, droop=0.3,
                                                       kinds=("pad", "pad", "ico"), squash=0.7), upbias=0.35)


def tree_fruit(p, rng, bk, crown, fruit):
    """Small apple tree, 4 m: short trunk, spreading limbs, clumps at the twig ends, a few apples."""
    end, d, _ = pc.branch(bk, (0, 0, 0), (0.03, 0.02, 1), 1.4, 0.17, 0.12, rng, sides=7, segs=2, bend=0.04,
                          tip=False)
    plan = [(3, 34, 1.5, 0.09, 0.045, 5, 1, 0.06), (2, 30, 1.0, 0.045, 0.02, 3, 1, 0.1)]
    tips = grow_crown(bk, crown, rng, end, d, plan, dict(n=3, rmin=0.8, rmax=1.25, spread=0.9, droop=0.35, squash=0.7,
                                                kinds=("ico", "pad", "pad")))
    for i in range(7):
        t, td = tips[i % len(tips)]
        pos = t + v3(rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), -rng.uniform(0.55, 0.9))
        g = bmesh.ops.create_icosphere(fruit, subdivisions=1, radius=0.095)
        bmesh.ops.translate(fruit, vec=pos, verts=g["verts"])


def tree_fir(p, rng, bk, crown):
    """Tall sparse fir, 12 m: a bare straight trunk and ~10 drooping branch tiers."""
    H = 12.0
    pts = pc.spline([v3(0, 0, 0), v3(0.1, 0, 3), v3(-0.05, 0.1, 7), v3(0.0, 0, H)], per=1)
    pc.sweep(bk, pts, pc.taper(len(pts), 0.22, 0.03), sides=5, tip=True)
    tiers = 10
    for i in range(tiers):
        t = i / (tiers - 1)
        z = 3.4 + (H - 4.2) * t + rng.uniform(-0.25, 0.25)
        R = (1.8 * (1 - t) ** 0.9 + 0.3) * rng.uniform(0.75, 1.15)
        n = 7
        a0 = rng.uniform(0, 6.28)
        ox, oy = rng.uniform(-0.35, 0.35), rng.uniform(-0.35, 0.35)
        apex = crown.verts.new((0, 0, z + 0.25 * R))
        under = crown.verts.new((ox * 0.5, oy * 0.5, z - 0.3))
        rim = []
        for k in range(n):
            th = a0 + 2 * math.pi * k / n + rng.uniform(-0.3, 0.3)
            rr = R * rng.uniform(0.4, 1.25)
            rim.append(crown.verts.new((ox + rr * math.cos(th), oy + rr * math.sin(th),
                                        z - 0.75 * R * rng.uniform(0.6, 1.2))))
        for k in range(n):
            j = (k + 1) % n
            crown.faces.new((rim[k], rim[j], apex)).smooth = True
            crown.faces.new((rim[j], rim[k], under)).smooth = True


def tree_cypress(p, rng, bk, crown):
    """Italian cypress, 10 m, slim flame: one lumpy spindle (1.5 m wide, widest low), a stub of trunk."""
    sides = 8
    H, R = 10.0, 0.74
    ts = [0.0, 0.07, 0.15, 0.25, 0.36, 0.48, 0.6, 0.71, 0.81, 0.9, 0.96, 1.0]
    noise = pc.Lump(rng, 1.0)
    sway = rng.uniform(-0.3, 0.3)

    def prof(t):
        if t < 0.3:
            return R * (0.5 + 0.5 * math.sin(t / 0.3 * math.pi / 2))
        return R * max(0.0, 1.0 - (t - 0.3) / 0.7) ** 0.8

    vs = []
    for i, t in enumerate(ts):
        z = 0.3 + (H - 0.3) * t
        base = prof(t)
        ring = []
        if base <= 0:
            vs.append([crown.verts.new((0, 0, z))])
            continue
        for k in range(sides):
            th = 2 * math.pi * k / sides + i * 0.45
            f = 1 + 0.24 * noise(math.cos(th) * 2, math.sin(th) * 2, z * 0.8) + 0.12 * rng.uniform(-1, 1)
            ring.append(crown.verts.new((base * f * math.cos(th) + sway * t, base * f * math.sin(th), z)))
        vs.append(ring)
    for i in range(len(ts) - 1):
        a, b = vs[i], vs[i + 1]
        for k in range(sides):
            j = (k + 1) % sides
            if len(b) == 1:
                f = crown.faces.new((a[k], a[j], b[0]))
            else:
                f = crown.faces.new((a[k], a[j], b[j], b[k]))
            f.smooth = True
    cv = crown.verts.new((0, 0, 0.3))
    for k in range(sides):
        f = crown.faces.new((vs[0][(k + 1) % sides], vs[0][k], cv))
        f.smooth = True
    pts = pc.spline([v3(0, 0, 0), v3(0, 0, 0.3), v3(0, 0, 0.6)], per=1)
    pc.sweep(bk, pts, [0.16, 0.13, 0.1], sides=6, tip=False)


# ------------------------------------------------------------------ build
def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rng = pc.rng_for(p["seed"])
    col, root = pc.new_asset(n)
    kind = p["kind"]
    bark_bm, crown_bm, fruit_bm = bmesh.new(), bmesh.new(), bmesh.new()
    if kind == "round":
        tree_round(p, rng, bark_bm, crown_bm)
    elif kind == "olive":
        tree_olive(p, rng, bark_bm, crown_bm)
    elif kind == "cypress":
        tree_cypress(p, rng, bark_bm, crown_bm)
    elif kind == "multistem":
        tree_multistem(p, rng, bark_bm, crown_bm)
    elif kind == "fruit":
        tree_fruit(p, rng, bark_bm, crown_bm, fruit_bm)
    elif kind == "fir":
        tree_fir(p, rng, bark_bm, crown_bm)
    else:
        raise ValueError(kind)

    bark = {"olive": outdoor.flat("M_Out_OliveBark", OLIVE_BARK),
            "multistem": outdoor.flat("M_Out_BirchBark", BIRCH_BARK)}.get(kind, outdoor.bark())
    leaf = {"olive": lambda: outdoor.flat("M_Out_OliveLeaf", OLIVE_LEAF),
            "multistem": lambda: outdoor.flat("M_Out_BirchLeaf", BIRCH_LEAF)}.get(kind, outdoor.foliage)()
    for v in bark_bm.verts:
        v.co.z = max(v.co.z, 0.0)
    if bark_bm.verts:
        common.mesh_object(f"{n}_Trunk", bark_bm, col, bark, root)
    else:
        bark_bm.free()
    cr = common.mesh_object(f"{n}_Crown", crown_bm, col, leaf, root)
    if kind not in ("olive", "multistem"):
        common.box_uv(cr, tile=1.5)
    if fruit_bm.verts:
        for f in fruit_bm.faces:
            f.smooth = True
        common.mesh_object(f"{n}_Fruit", fruit_bm, col, outdoor.flat("M_Out_Apple", APPLE_RED), root)
    else:
        fruit_bm.free()
    return root, pc.parts_of(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
