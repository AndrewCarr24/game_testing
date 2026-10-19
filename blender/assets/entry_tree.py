"""Indoor specimen tree for the double-height hall: a multi-stemmed olive-like tree
about 4.6 m tall in a honed limestone planter. Forked bark-coloured trunks (tapered
cones) carry foliage masses (jittered blobs textured with a dense leaf pattern,
T_Entry_Leaves, 1024, generated here when missing).

Origin: floor centre of the planter. Units are metres.
"""
import importlib
import math
import os
import random
import sys

import bmesh
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials, textures  # noqa: E402
import entry_sculpture  # noqa: E402  (limestone material)

importlib.reload(common)
importlib.reload(textures)
importlib.reload(entry_sculpture)

NAME = "EntryTree"

P = dict(
    name=NAME,
    height=4.6,
    seed=3,
    planter_r=0.50, planter_h=0.72, planter_wall=0.07,
    stems=4,
    blob_segments=7, blob_rings=4,     # the layout's foliage envelopes (the random stream depends on it)
)


def leaves(n=1024, seed=8, force=False):
    """Dense olive leaves, tileable: many small pointed ellipses in two greens over a
    dark ground, so foliage masses read as leaves from a few metres. One tile = 0.5 m."""
    name = "T_Entry_Leaves"
    path = os.path.join(textures.TEX_DIR, name + ".png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    img = np.zeros((n, n, 3))
    img[:] = np.array([0.045, 0.07, 0.035])
    greens = [np.array(c) for c in ((0.20, 0.30, 0.13), (0.26, 0.36, 0.17), (0.34, 0.43, 0.24), (0.16, 0.24, 0.12))]
    yy, xx = np.mgrid[0:n, 0:n]
    order = []
    for _ in range(2600):
        order.append((rng.uniform(0, n), rng.uniform(0, n), rng.uniform(0, math.pi),
                      rng.uniform(26, 46), rng.uniform(6, 10), rng.integers(0, 4), rng.uniform(0.75, 1.15)))
    for (cx, cy, ang, L, W, gi, shade) in order:
        # draw on a small window (wrapped) around the leaf
        r = int(L) + 2
        xs = (np.arange(-r, r + 1) + int(cx)) % n
        ys = (np.arange(-r, r + 1) + int(cy)) % n
        dx, dy = np.meshgrid(np.arange(-r, r + 1) + (int(cx) - cx), np.arange(-r, r + 1) + (int(cy) - cy))
        c, s = math.cos(ang), math.sin(ang)
        u = (dx * c + dy * s) / L
        v = (-dx * s + dy * c) / W
        # pointed ellipse: width tapers towards both ends
        mask = (np.abs(v) < (1 - np.abs(u) ** 1.6) ) & (np.abs(u) < 1)
        mid = (np.abs(v) < 0.12) & (np.abs(u) < 0.95)           # lighter midrib
        col = greens[gi][None, None, :] * shade * (1.0 - 0.25 * (v > 0))[..., None]   # one half a little darker
        sub = img[np.ix_(ys, xs)]
        sub[mask] = col[mask]
        sub[mid & mask] = col[mid & mask] * 1.35
        img[np.ix_(ys, xs)] = sub
    return textures._save(name, textures._to_srgb(np.clip(img, 0, 1)))


def tapered(bm, a, b, r1, r2, segs=7):
    a, b = Vector(a), Vector(b)
    d = b - a
    rot = d.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=segs, radius1=r1, radius2=r2, depth=d.length,
                          matrix=Matrix.Translation((a + b) / 2) @ rot)


def blob(bm, c, r, segs, rings, rnd):
    ret = bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=r, matrix=Matrix.Translation(c))
    for v in ret["verts"]:
        v.co += Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * r * 0.22
        v.co.z = c.z + (v.co.z - c.z) * 0.8             # slightly flattened masses


def stem(bm, pts, radii, rnd, sides=10):
    """One trunk as a continuous tube (rings shared, no seams between segments): a root
    flare where it leaves the soil, a slight twist and an irregular, knobbly section, so
    it reads as wood up close rather than a stack of cones."""
    pts = [Vector(q) for q in pts]
    d0 = (pts[1] - pts[0])
    pts = [pts[0], pts[0] + d0 * 0.10, pts[0] + d0 * 0.28] + pts[1:]
    radii = [radii[0] * 1.75, radii[0] * 1.22, radii[0] * 1.04] + radii[1:]
    n = len(pts)
    rings = []
    ref = Vector((1, 0, 0))
    bumps = [rnd.uniform(-1, 1) for _ in range(sides)]          # ridges running up the bark
    for k, q in enumerate(pts):
        d = (pts[min(k + 1, n - 1)] - pts[max(k - 1, 0)]).normalized()
        u = (ref - d * ref.dot(d)).normalized()
        w = d.cross(u)
        twist = 0.06 * k
        ring = []
        for j in range(sides):
            a = 2 * math.pi * j / sides + twist
            rr = radii[k] * (1 + 0.07 * bumps[j] + 0.04 * rnd.uniform(-1, 1))
            ring.append(bm.verts.new(q + (u * math.cos(a) + w * math.sin(a)) * rr))
        rings.append(ring)
    for k in range(n - 1):
        A, B = rings[k], rings[k + 1]
        for j in range(sides):
            bm.faces.new((A[j], A[(j + 1) % sides], B[(j + 1) % sides], B[j]))


def envelope(c, r, segs, rings, rnd):
    """The foliage mass the layout was designed with (same random draws as blob()), built
    in a scratch mesh: returns its bounding box, which the new core and sprigs stay inside."""
    tmp = bmesh.new()
    blob(tmp, c, r, segs, rings, rnd)
    lo = Vector([min(v.co[a] for v in tmp.verts) for a in range(3)])
    hi = Vector([max(v.co[a] for v in tmp.verts) for a in range(3)])
    tmp.free()
    return lo, hi


def core(bm, c, r, rnd):
    """Dense dark middle of a mass: a jittered, flattened icosahedron (20 triangles)."""
    ret = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r, matrix=Matrix.Translation(c))
    for v in ret["verts"]:
        v.co += Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * r * 0.15
        v.co.z = c.z + (v.co.z - c.z) * 0.8


def clamp(v, lo, hi):
    return Vector([min(max(v[a], lo[a]), hi[a]) for a in range(3)])


def leaf_cards(bm, c, r, count, rnd, lo, hi):
    """Sprigs of leaves shingled over a foliage mass: broad pointed diamonds (two triangles
    each) lying almost tangent to the mass, tips lifted outwards and drooping a little like
    olive shoots. Their box-projected leaf texture reads as a cluster of leaves per card,
    and they break up the mass's outline. Clamped into the mass's envelope (lo, hi)."""
    for _ in range(count):
        d = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1) * 0.7 + 0.35)).normalized()
        base = c + d * r * rnd.uniform(0.62, 0.8)
        # tangent direction, lifted outwards and pulled down a little
        tan = d.cross(Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))).normalized()
        t = (tan + d * rnd.uniform(0.35, 0.7) + Vector((0, 0, -0.25))).normalized()
        side = t.cross(d).normalized()
        L, W = r * rnd.uniform(0.75, 1.0), r * rnd.uniform(0.38, 0.5)
        tip = base + t * L
        reach = (tip - c).length
        if reach > r * 1.3:                     # stay inside the old mass's envelope
            L *= (r * 1.3 - (base - c).length) / max(reach - (base - c).length, 1e-6)
            tip = base + t * L
        mid = base + t * (L * 0.45) + d * (0.02 * r)
        back = base - t * (L * 0.15)
        vs = [bm.verts.new(clamp(q, lo, hi)) for q in
              (back, mid + side * W / 2, tip, mid - side * W / 2)]
        bm.faces.new(vs)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])

    stone = entry_sculpture.limestone_material()
    bark = common.pbr_material("M_Entry_Bark", (0.17, 0.14, 0.11), roughness=0.9)
    foliage = common.pbr_material("M_Entry_Leaves", (1, 1, 1), roughness=0.75)
    common.set_base_color_map(foliage, textures.load(leaves()))
    soil = common.pbr_material("M_Entry_Soil", (0.05, 0.04, 0.03), roughness=1.0)

    # ---- planter: a thick honed limestone drum (hollow ring + soil disc) ------------------
    R, H, w = p["planter_r"], p["planter_h"], p["planter_wall"]
    ring = [(R - w, 0.0), (R, 0.0), (R, H), (R - w, H)]
    # outer wall, rim and inner wall as one lathe
    import table_lamp
    prof = [(R - w, 0.0), (R, 0.0), (R, H - 0.01), (R - 0.01, H), (R - w + 0.01, H), (R - w, H - 0.01)]
    planter = common.mesh_object(f"{n}_Planter", table_lamp.lathe(prof, 56, sharp=40), col, stone, root)
    common.box_uv(planter, tile=8.0)
    uvl = planter.data.uv_layers["UVMap"]
    for d in uvl.data:
        d.uv = (d.uv[0] * 1.0 + 0.2, d.uv[1] + 0.2)
    base = common.mesh_object(f"{n}_Soil", table_lamp.lathe(
        [(0.0, H - 0.07), (R - w + 0.005, H - 0.07), (R - w + 0.005, H - 0.04), (0.0, H - 0.04)], 40), col, soil, root)
    floor_disc = common.mesh_object(f"{n}_PlanterFloor", table_lamp.lathe(
        [(0.0, 0.0), (R - 0.01, 0.0), (R - 0.01, 0.03), (0.0, 0.03)], 40), col, stone, root)

    common.box_uv(floor_disc, tile=2.0)

    # ---- trunk and branches ---------------------------------------------------------------
    trunk = bmesh.new()
    branches = bmesh.new()
    blobs = bmesh.new()
    cards = bmesh.new()
    rnd_c = random.Random(p["seed"] + 100)       # leaf sprigs: own stream, layout unchanged
    rnd_b = random.Random(p["seed"] + 200)       # bark ridges
    top = p["height"]
    z0 = H - 0.05
    for s in range(p["stems"]):
        a = 2 * math.pi * s / p["stems"] + rnd.uniform(-0.4, 0.4)
        d = Vector((math.cos(a), math.sin(a), 0))
        base_p = Vector((d.x * 0.07, d.y * 0.07, z0))
        # stem rises with a gentle S-curve, leaning outward
        lean = rnd.uniform(0.05, 0.12)
        H_s = top * rnd.uniform(0.62, 0.80)
        pts = [base_p]
        segs = 6
        for k in range(1, segs + 1):
            t = k / segs
            pts.append(Vector((d.x * (0.07 + lean * H_s * t ** 1.7 + 0.05 * math.sin(t * 6 + s)),
                               d.y * (0.07 + lean * H_s * t ** 1.7 + 0.05 * math.sin(t * 6 + s)),
                               z0 + H_s * t)))
        radii = [0.055 * (1 - 0.65 * k / segs) for k in range(segs + 1)]
        stem(trunk, pts, radii, rnd_b)
        # branches off the upper half
        tips = [pts[-1]]
        for k in range(4, segs):
            for _ in range(rnd.randint(1, 2)):
                ang = rnd.uniform(0, 2 * math.pi)
                dirv = Vector((math.cos(ang) * 0.7, math.sin(ang) * 0.7, 0.8)).normalized()
                length = rnd.uniform(0.5, 1.0)
                e = pts[k] + dirv * length
                tapered(branches, pts[k], e, radii[k] * 0.45, 0.012)
                tips.append(e)
        # foliage masses at every tip and along the upper branches
        for tp in tips:
            for _ in range(rnd.randint(5, 7)):
                off = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.2, 0.9))) * 0.36
                rr = rnd.uniform(0.15, 0.27)
                # a small dense core (keeps the canopy from looking see-through) under a coat of
                # leaf sprigs, all inside the envelope of the original mass
                lo, hi = envelope(tp + off, rr, p["blob_segments"], p["blob_rings"], rnd)
                core(blobs, tp + off, rr * 0.74, rnd_c)
                leaf_cards(cards, tp + off, rr, int(6 + 30 * rr), rnd_c, lo, hi)
    common.mesh_object(f"{n}_Trunks", trunk, col, bark, root)
    common.mesh_object(f"{n}_Branches", branches, col, bark, root)
    for f in cards.faces:
        f.smooth = True
    fol = common.mesh_object(f"{n}_Foliage", blobs, col, foliage, root)
    sprig = common.mesh_object(f"{n}_FoliageSprigs", cards, col, foliage, root)
    # one mesh for the canopy (one draw call): join the sprigs into the masses
    import bpy
    vl = bpy.context.view_layer
    for o in vl.objects.selected:
        o.select_set(False)
    fol.select_set(True)
    sprig.select_set(True)
    vl.objects.active = fol
    bpy.ops.object.join()
    common.box_uv(fol, tile=0.5)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
