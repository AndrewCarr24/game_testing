"""Set-dressing kit for the decor_c_* assets (library, office, gym, galleries). Not an asset.

A `Kit` collects geometry per material (one mesh object per material per asset, so a whole
vignette costs one draw call per material it uses) and the generators below add objects to it
under a transform: books and stacks, an open book, ceramics, bowls, lemons, trays, a carafe and
glasses, cup and saucer, reading glasses, laptop, notebook, pen, small sculptures, plants,
towels, a basket, yoga blocks, scatter cushions, a throw over a sofa arm and the gallery bench
and console.

Materials are all shared with the rest of the house (same names, same parameters), no new
textures: books use the library's spine atlas (T_Library_Spines: spines, cloth covers and the
cream paper strip for page edges), plants the library's leaf map.

Every part of a small object is named `<Asset>_<Material>_NoCollide` (no collider); only the
pieces a player could stand against (bench, console, floor planters, a basket) collide.
"""
import importlib
import math
import os
import random
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials, pickups, textures  # noqa: E402
import library_bookcase  # noqa: E402
import library_plant  # noqa: E402
import guest_mats  # noqa: E402
import library_kit  # noqa: E402

for _m in (common, textures, materials, pickups, library_bookcase, library_plant, guest_mats, library_kit):
    importlib.reload(_m)

TAU = 2 * math.pi


# ------------------------------------------------------------------------------ materials
# (name, colour, roughness exactly as the assets that first defined them)

def _leaf():
    m = common.pbr_material("M_Library_Leaf", (1, 1, 1), roughness=0.38)
    common.set_base_color_map(m, textures.load(library_plant.leaf_texture()))
    m.use_backface_culling = False
    return m


MATS = {
    "spines": library_bookcase.books_material,                                     # books, paper
    "glaze": lambda: common.pbr_material("M_Ceramic_Glaze", (0.55, 0.52, 0.46), roughness=0.18),
    "charcoal": lambda: common.pbr_material("M_Ceramic_Charcoal", (0.05, 0.05, 0.055), roughness=0.3),
    "bronze": materials.bronze,
    "walnut": materials.walnut,
    "black": materials.black_metal,                                                # M_Aluminium_Black
    "steel": materials.steel,
    "cognac": library_kit.leather_cognac,                                          # M_Leather_Cognac
    "leather_black": lambda: common.pbr_material("M_Leather_Black", (0.018, 0.016, 0.015), roughness=0.62),
    "leaf": _leaf,
    "soil": lambda: common.pbr_material("M_Plant_Soil", (0.025, 0.016, 0.010), roughness=1.0),
    "planter": lambda: common.pbr_material("M_Library_Planter", (0.46, 0.42, 0.35), roughness=0.85),
    "oat": lambda: materials.fabric("M_Fabric_Oat", (0.42, 0.37, 0.30)),
    "navy": lambda: materials.fabric("M_Fabric_LibraryNavy", (0.018, 0.028, 0.06)),
    "linen": lambda: materials.fabric("M_Fabric_Linen", (0.52, 0.49, 0.42)),
    "glass": lambda: materials.glass("M_Glass_Smoke", tint=(0.42, 0.40, 0.37), alpha=0.35, roughness=0.04),
    "lemon": lambda: common.pbr_material("M_Lemon", (0.75, 0.55, 0.03), roughness=0.5),
    "wicker": lambda: common.pbr_material("M_Wicker", (0.30, 0.21, 0.12), roughness=0.95),
    "oak": guest_mats.oak,                                                         # M_Oak_Light
    "sage": lambda: common.pbr_material("M_Mat_Sage", (0.17, 0.25, 0.15), roughness=0.75),
}
FABRIC = {"oat", "navy", "linen"}        # these carry the weave normal map: UVs at 0.25 m


# ------------------------------------------------------------------------------ transforms

def T(x=0.0, y=0.0, z=0.0, rz=0.0, rx=0.0, ry=0.0, s=1.0):
    """Translation @ Rz @ Ry @ Rx @ scale; angles in degrees."""
    m = Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(rz), 4, "Z") \
        @ Matrix.Rotation(math.radians(ry), 4, "Y") @ Matrix.Rotation(math.radians(rx), 4, "X")
    if s != 1.0:
        m = m @ Matrix.Scale(s, 4)
    return m


# ------------------------------------------------------------------------------ geometry

class Acc:
    """Geometry for one material: a bmesh with a UV layer. Every primitive takes a
    transform M and its faces' smooth flags are set here (flat boxes, smooth lathes with
    sharp rims)."""

    def __init__(self, tile=0.25):
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.tile = tile

    def _face(self, verts, uvs, smooth):
        try:
            f = self.bm.faces.new(verts)
        except ValueError:
            return None
        f.smooth = smooth
        for lp, uv in zip(f.loops, uvs):
            lp[self.uv].uv = uv
        return f

    def poly(self, pts, M, uvs=None, smooth=False):
        vs = [self.bm.verts.new(M @ Vector(p)) for p in pts]
        if uvs is None:
            uvs = [(p[0] / self.tile, p[1] / self.tile) for p in pts]
        return self._face(vs, uvs, smooth)

    def lathe(self, prof, M, segs=16, sharp=(), smooth=True, phase=0.0, uv=None, close=False):
        """Solid of revolution about local Z from [(r, z), ...]. Faces face outward when the
        profile runs up the outside, inward across a top and down an inside. sharp: profile
        indices whose ring edges stay hard. uv: (u0, v0, u1, v1) to squeeze the whole
        surface into an atlas rect; default world-scale."""
        bm = self.bm
        rows = []
        for r, z in prof:
            if abs(r) < 1e-7:
                v = bm.verts.new(M @ Vector((0, 0, z)))
                rows.append([v] * segs)
            else:
                rows.append([bm.verts.new(M @ Vector((r * math.cos(TAU * (s + phase) / segs),
                                                       r * math.sin(TAU * (s + phase) / segs), z)))
                             for s in range(segs)])
        lens = [0.0]
        for i in range(1, len(prof)):
            lens.append(lens[-1] + math.hypot(prof[i][0] - prof[i - 1][0], prof[i][1] - prof[i - 1][1]))
        rmax = max(max(r for r, _ in prof), 1e-3)
        total = max(lens[-1], 1e-6)
        for i in range(len(prof) - 1):
            for s in range(segs):
                s2 = (s + 1) % segs
                quad = [(rows[i][s], s, i), (rows[i][s2], s + 1, i), (rows[i + 1][s2], s + 1, i + 1),
                        (rows[i + 1][s], s, i + 1)]
                uniq = []
                for q in quad:
                    if all(q[0] is not o[0] for o in uniq):
                        uniq.append(q)
                if len(uniq) < 3:
                    continue
                if uv:
                    u0, v0, u1, v1 = uv
                    uvs = [(u0 + (u1 - u0) * ss / segs, v0 + (v1 - v0) * lens[ii] / total) for _, ss, ii in uniq]
                else:
                    uvs = [(TAU * rmax * ss / segs / self.tile, lens[ii] / self.tile) for _, ss, ii in uniq]
                self._face([q[0] for q in uniq], uvs, smooth)
        for i in sharp:
            ring = rows[i]
            if ring[0] is ring[1]:
                continue
            for s in range(segs):
                e = bm.edges.get((ring[s], ring[(s + 1) % segs]))
                if e:
                    e.smooth = False
        if close:     # cap the last ring (a flat top)
            ring = rows[-1]
            z = prof[-1][1]
            r = prof[-1][0]
            uvs = [(r * math.cos(TAU * s / segs) / self.tile, r * math.sin(TAU * s / segs) / self.tile)
                   for s in range(segs)]
            f = self._face(ring, uvs, False)
            if f is not None:
                cen = M @ Vector((0, 0, z + 1))
                if (cen - f.calc_center_median()).dot(f.normal) < 0:
                    f.normal_flip()
        return rows

    def box(self, size, M, skip=(), uvrect=None, bevel=0.0, seg=1, smooth=False, tile=None):
        """Box centred at the local origin. skip: faces to leave out ('-z', '+y', ...).
        uvrect: {face: (u0, v0, u1, v1)} atlas rects (face's local extent maps onto it)
        or one rect for all faces; default world-scale box UVs. bevel: chamfer width."""
        tile = tile or self.tile
        sx, sy, sz = (s / 2 for s in size)
        bm = self.bm
        corners = {}
        for ix in (-1, 1):
            for iy in (-1, 1):
                for iz in (-1, 1):
                    corners[(ix, iy, iz)] = Vector((ix * sx, iy * sy, iz * sz))
        F = {"-x": [(-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)],
             "+x": [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)],
             "-y": [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)],
             "+y": [(-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)],
             "-z": [(-1, -1, -1), (-1, 1, -1), (1, 1, -1), (1, -1, -1)],
             "+z": [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]}
        AX = {"x": 0, "y": 1, "z": 2}
        vmap = {}
        faces = []
        for name, cs in F.items():
            if name in skip and not bevel:
                continue
            vs = []
            for c in cs:
                if c not in vmap:
                    vmap[c] = bm.verts.new(corners[c])
                vs.append(vmap[c])
            na = AX[name[1]]
            a, b = [i for i in range(3) if i != na]
            if size[b] > size[a]:
                a, b = b, a
            rect = uvrect.get(name) if isinstance(uvrect, dict) else uvrect
            uvs = []
            for c in cs:
                co = corners[c]
                if rect:
                    fa = (co[a] / (2 * (sx, sy, sz)[a]) + 0.5)
                    fb = (co[b] / (2 * (sx, sy, sz)[b]) + 0.5)
                    uvs.append((rect[0] + (rect[2] - rect[0]) * fa, rect[1] + (rect[3] - rect[1]) * fb))
                else:
                    uvs.append((co[a] / tile, co[b] / tile))
            f = self._face(vs, uvs, smooth)
            if f is not None:
                faces.append((name, f))
        newv = list(vmap.values())
        if bevel:
            edges = list({e for v in newv for e in v.link_edges})
            res = bmesh.ops.bevel(bm, geom=newv + edges, offset=bevel, segments=seg, affect="EDGES",
                                  profile=0.5, clamp_overlap=True)
            newv = list({v for v in newv if v.is_valid} | set(res["verts"]))
            for f in res["faces"]:
                f.smooth = smooth
                # bevel strips: world-scale UVs
                n = [abs(c) for c in f.normal]
                na = n.index(max(n))
                a, b = [i for i in range(3) if i != na]
                for lp in f.loops:
                    lp[self.uv].uv = (lp.vert.co[a] / tile, lp.vert.co[b] / tile)
            if skip:
                for name, f in faces:
                    if name in skip and f.is_valid:
                        bm.faces.remove(f)
        bmesh.ops.transform(bm, matrix=M, verts=newv)
        return newv

    def grid(self, P, uvs, smooth=True):
        """Quad grid from a 2D list of points P[i][j] (already transformed) and matching UVs."""
        bm = self.bm
        V = [[bm.verts.new(p) for p in row] for row in P]
        for i in range(len(P) - 1):
            for j in range(len(P[0]) - 1):
                self._face([V[i][j], V[i + 1][j], V[i + 1][j + 1], V[i][j + 1]],
                           [uvs[i][j], uvs[i + 1][j], uvs[i + 1][j + 1], uvs[i][j + 1]], smooth)
        return V

    def tube(self, pts, r, M, sides=6, smooth=True, caps=False, closed=False):
        """Swept circle along a polyline (local points), parallel-transported frames so it
        never twists. closed: the last point joins the first (rings, loops)."""
        bm = self.bm
        P = [M @ Vector(p) for p in pts]
        n = len(P)

        def tangent(i):
            if closed:
                return (P[(i + 1) % n] - P[(i - 1) % n]).normalized()
            return (P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized()

        t0 = tangent(0)
        up = Vector((0, 0, 1)) if abs(t0.z) < 0.9 else Vector((1, 0, 0))
        a = t0.cross(up).normalized()
        rings = []
        tp = t0
        for i, p in enumerate(P):
            t = tangent(i)
            a = (tp.rotation_difference(t) @ a)
            a = (a - t * a.dot(t)).normalized()
            tp = t
            b = t.cross(a).normalized()
            rings.append([bm.verts.new(p + (a * math.cos(TAU * s / sides) + b * math.sin(TAU * s / sides)) * r)
                          for s in range(sides)])
        if closed:
            rings.append(rings[0])
        for i in range(len(rings) - 1):
            for s in range(sides):
                s2 = (s + 1) % sides
                self._face([rings[i][s], rings[i][s2], rings[i + 1][s2], rings[i + 1][s]],
                           [(s / sides, i * 0.1), ((s + 1) / sides, i * 0.1), ((s + 1) / sides, (i + 1) * 0.1),
                            (s / sides, (i + 1) * 0.1)], smooth)
        if caps:
            for ring in (rings[0][::-1], rings[-1]):
                self._face(ring, [(0, 0)] * sides, False)
        return rings


class Kit:
    def __init__(self):
        self.accs = {}

    def __getitem__(self, key):
        if key not in self.accs:
            self.accs[key] = Acc(0.25 if key in FABRIC else 0.5)
        return self.accs[key]

    def finish(self, n, col, root, collide=()):
        """One mesh object per material: `<n>_<Key>_NoCollide`, or `<n>_<Key>` for keys in
        `collide` (benches, consoles, planters)."""
        # loose things become pickups (lib/pickups.py), the rest stays one mesh per material
        out = pickups.emit(self, n, col, root, [a.bm for a in self.accs.values()], lambda a: a.bm, lambda key: MATS[key](),
                           collide)
        for key, acc in self.accs.items():
            if not acc.bm.faces:
                acc.bm.free()
                continue
            label = key.replace("_", " ").title().replace(" ", "")
            name = f"{n}_{label}" + ("" if key in collide else "_NoCollide")
            out.append(common.mesh_object(name, acc.bm, col, MATS[key](), root, smooth=False))
        self.accs = {}
        return out


def new_asset(name):
    col = common.fresh_collection(name)
    root = common.empty(name, col)
    return col, root, Kit()


def done(kit, n, col, root, collide=()):
    kit.finish(n, col, root, collide)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


# ------------------------------------------------------------------------------ the spine atlas
# T_Library_Spines: 16 x 3 spine cells (64 x 256 px each) over a cream paper strip (rows 768+)

def _px(x, y):
    return x / 1024.0, 1.0 - y / 1024.0


def spine_rect(cell):
    """The whole spine cell, rotated so the spine's length runs along the rect's u."""
    px, py = (cell % 16) * 64, (cell // 16) * 256
    u0, v1 = _px(px + 2, py + 2)
    u1, v0 = _px(px + 62, py + 254)
    return (u0, v0, u1, v1)


def cover_rect(cell):
    """Board cover: a plain strip of the cell's leather or cloth (no gilt)."""
    px, py = (cell % 16) * 64, (cell // 16) * 256
    u0, v1 = _px(px + 3, py + 120)
    u1, v0 = _px(px + 6, py + 200)
    return (u0, v0, u1, v1)


def paper_rect(rnd, lines=12):
    """Page edges: a patch of the paper strip with `lines` fine lines across it."""
    span = min(lines * 3, 200)
    y = 768 + 8 + rnd.uniform(0, 1016 - 776 - span)
    x = rnd.uniform(0, 700)
    u0, v1 = _px(x, y)
    u1, v0 = _px(x + 200, y + span)
    return (u0, v0, u1, v1)


# cells whose cover colours read well lying flat (deep cloth, leather, a few pale)
COVER_CELLS = list(range(48))


# ------------------------------------------------------------------------------ books

def book(k, M, w, d, t, cell, rnd, flip_rect=False):
    """A hardback lying flat, spine on the -y side: boards (cell's cover colour) and a
    spine wrapped round a page block inset 3 mm on head, tail and fore-edge. w = spine
    length (x), d = depth (y), t = thickness. Origin: centre of the underside."""
    s = k["spines"]
    ct = min(0.0035, t * 0.15)
    ins = 0.003
    cov = cover_rect(cell)
    sp = spine_rect(cell)
    # boards (top and bottom), skip the faces against the page block / spine
    s.box((w, d - ct, ct), M @ T(0, ct / 2, ct / 2), skip=("+z", "-y"), uvrect=cov)
    s.box((w, d - ct, ct), M @ T(0, ct / 2, t - ct / 2), skip=("-z", "-y"), uvrect=cov)
    # spine: the cell runs along x (its length)
    s.box((w, ct, t), M @ T(0, -d / 2 + ct / 2, t / 2), skip=("+y",),
          uvrect={"-y": sp, "-x": cov, "+x": cov, "+z": cov, "-z": cov})
    # page block
    pr = paper_rect(rnd, lines=max(3, int(t * 400)))
    s.box((w - 2 * ins, d - ct - ins, t - 2 * ct), M @ T(0, ct / 2 - ins / 2, t / 2), skip=("-y", "+z", "-z"),
          uvrect=pr)


def book_stack(k, M, rnd, n=3, w=(0.24, 0.33), d=(0.28, 0.36), t=(0.022, 0.048), turn=4.0, cells=None):
    """n books lying flat, largest at the bottom, each nudged and turned a little; spines
    mostly to the front, the odd one turned round. Returns the top's height."""
    z = 0.0
    dims = sorted(((rnd.uniform(*w), rnd.uniform(*d), rnd.uniform(*t)) for _ in range(n)),
                  key=lambda b: -b[0] * b[1])
    for i, (bw, bd, bt) in enumerate(dims):
        if i:      # never wider than the one below
            pw, pd = dims[i - 1][:2]
            bw, bd = min(bw, pw - 0.01), min(bd, pd - 0.008)
            dims[i] = (bw, bd, bt)
        cell = (cells[i % len(cells)] if cells else rnd.choice(COVER_CELLS))
        rz = rnd.uniform(-turn, turn) + (180 if rnd.random() < 0.25 else 0)
        book(k, M @ T(rnd.uniform(-0.008, 0.008), rnd.uniform(-0.008, 0.008), z, rz=rz), bw, bd, bt, cell, rnd)
        z += bt
    return z, dims[-1]


def open_book(k, M, rnd, w=0.21, d=0.27, cell=None):
    """An open book lying on its back: two boards, pages rising from the gutter in a soft
    curve to the fore-edges. w = one page's width (x), d = page height (y)."""
    s = k["spines"]
    cell = rnd.randrange(48) if cell is None else cell
    ct, t = 0.0035, 0.013          # board, half the page block
    cov = cover_rect(cell)
    for side in (-1, 1):
        s.box((w + 0.004, d + 0.006, ct), M @ T(side * (w / 2 + 0.006), 0, ct / 2), skip=("-z",), uvrect=cov)
    s.box((0.012, d + 0.006, ct), M @ T(0, 0, ct / 2 - 0.001), skip=("-z",), uvrect=spine_rect(cell))
    # page halves: profile across x, extruded along y
    nx = 7
    for side in (-1, 1):
        tops = []
        for i in range(nx + 1):
            f = i / nx
            x = 0.003 + f * (w - 0.004)
            h = ct + t * (0.25 + 0.85 * (1 - math.exp(-f * 7))) - t * 0.18 * f * f
            tops.append((side * x, h))
        P, U = [], []
        pr = paper_rect(rnd, lines=60)
        for j, y in enumerate((-d / 2, d / 2)):
            P.append([M @ Vector((x, y, h)) for x, h in tops])
            U.append([(pr[0] + (pr[2] - pr[0]) * (abs(x) / w), pr[1] + (pr[3] - pr[1]) * j) for x, h in tops])
        if side < 0:
            P, U = P[::-1], U[::-1]
        s.grid(P, U, smooth=True)
        # head, tail and fore-edge
        er = paper_rect(rnd, lines=4)
        for y, sg in ((-d / 2, -1), (d / 2, 1)):
            pts = [(tops[0][0], y, ct)] + [(x, y, h) for x, h in tops] + [(tops[-1][0], y, ct)]
            if (sg < 0) == (side > 0):
                pts = pts[::-1]
            s.poly(pts, M, uvs=[(er[0] + 0.01 * i, er[1] + (er[3] - er[1]) * (p[2] / (ct + t))) for i, p in enumerate(pts)])
        xe, he = tops[-1]
        fe = [(xe, -d / 2, ct), (xe, d / 2, ct), (xe, d / 2, he), (xe, -d / 2, he)]
        if side < 0:
            fe = fe[::-1]
        s.poly(fe, M, uvs=[(er[0], er[1]), (er[2], er[1]), (er[2], er[3]), (er[0], er[3])])


# ------------------------------------------------------------------------------ ceramics

VESSELS = {
    # outer profiles (r, z) from the foot up, then the lip; inner wall goes down `inside` m
    "bottle": dict(prof=[(0.040, 0.0), (0.052, 0.012), (0.066, 0.07), (0.068, 0.12), (0.055, 0.18), (0.024, 0.235),
                         (0.016, 0.27), (0.015, 0.33), (0.019, 0.345)], inside=0.05, sharp=(0,)),
    "moon": dict(prof=[(0.040, 0.0), (0.060, 0.018), (0.088, 0.065), (0.094, 0.11), (0.084, 0.16), (0.055, 0.2),
                       (0.034, 0.215), (0.036, 0.228)], inside=0.04, sharp=(0,)),
    "cylinder": dict(prof=[(0.050, 0.0), (0.056, 0.006), (0.058, 0.03), (0.058, 0.15), (0.0575, 0.158)],
                     inside=0.06, sharp=(0,)),
    "amphora": dict(prof=[(0.035, 0.0), (0.042, 0.01), (0.07, 0.09), (0.082, 0.17), (0.07, 0.25), (0.04, 0.31),
                          (0.034, 0.36), (0.045, 0.40), (0.05, 0.408)], inside=0.06, sharp=(0,)),
    "bud": dict(prof=[(0.026, 0.0), (0.034, 0.008), (0.046, 0.045), (0.042, 0.075), (0.016, 0.105), (0.011, 0.13),
                      (0.014, 0.137)], inside=0.03, sharp=(0,)),
}


def vessel(k, M, kind, mat, scale=1.0, segs=20):
    """A closed-form vase: outer profile, a rolled lip and the inside wall down a little
    (dark enough below that). Bottom left open (it sits on a surface)."""
    v = VESSELS[kind]
    prof = [(r * scale, z * scale) for r, z in v["prof"]]
    rt, zt = prof[-1]
    wall = 0.005 * scale
    prof += [(rt - wall * 0.5, zt + 0.002 * scale), (rt - wall, zt - 0.003 * scale),
             (prof[-2][0] - wall, prof[-2][1] - v["inside"] * scale * 0.4), (0.0, zt - v["inside"] * scale)]
    k[mat].lathe(prof, M, segs=segs, sharp=v["sharp"])
    return zt + 0.002 * scale


def bowl(k, M, mat, r=0.15, h=0.07, foot=0.45, segs=18, wall=0.006):
    """An open bowl with a foot ring and a rounded lip; the inside is visible."""
    n = 6
    prof = [(r * foot, 0.0), (r * foot + 0.004, 0.006)]
    for i in range(1, n + 1):
        a = i / n
        prof.append((r * foot + (r - r * foot) * math.sin(a * math.pi / 2), 0.006 + (h - 0.006) * (1 - math.cos(a * math.pi / 2)) ** 0.9))
    prof.append((r - wall * 0.5, h + 0.0025))
    for i in range(n, -1, -1):
        a = i / n
        rr = (r - wall) * math.sin(a * math.pi / 2)
        zz = 0.012 + (h - 0.012) * (1 - math.cos(a * math.pi / 2)) ** 0.9
        prof.append((max(rr, 0.0), zz))
    k[mat].lathe(prof, M, segs=segs, sharp=(0,))
    return h


def lemon(k, M, r=0.034, segs=8, mat="lemon"):
    """A lemon on its side: an ellipsoid with a nub at both ends."""
    L = r * 1.32
    prof = [(0.0, -L - 0.004), (r * 0.18, -L), (r * 0.62, -L * 0.75), (r * 0.92, -L * 0.38), (r, 0.0),
            (r * 0.92, L * 0.38), (r * 0.62, L * 0.75), (r * 0.18, L), (0.0, L + 0.004)]
    k[mat].lathe(prof, M @ T(0, 0, r * 0.97, ry=90), segs=segs)


def lemon_bowl(k, M, rnd, mat="charcoal", r=0.15, n=6):
    h = bowl(k, M, mat, r=r, h=0.068)
    spots = [(0.0, 0.0, 0.0)] + [(math.cos(a) * r * 0.5, math.sin(a) * r * 0.5, 0.0)
                                 for a in (rnd.uniform(0, TAU) + i * TAU / (n - 1) for i in range(n - 1))]
    for i, (x, y, _) in enumerate(spots[:n]):
        d = math.hypot(x, y)
        z = 0.012 + (0.025 * (d / (r * 0.5)) ** 2 if d else 0.0) + (0.03 if i == 0 else 0.0)
        lemon(k, M @ T(x, y, z, rz=rnd.uniform(0, 360), rx=rnd.uniform(-15, 15)), r=rnd.uniform(0.031, 0.036))
    return h


def candle_dish(k, M, mat="bronze"):
    """A low bronze dish (catchall, a pair of keys or a candle)."""
    bowl(k, M, mat, r=0.075, h=0.022, foot=0.7, segs=16, wall=0.003)


# ------------------------------------------------------------------------------ table things

def tray(k, M, w=0.42, d=0.28, mat="walnut", rim=0.028, t=0.012):
    """Rectangular tray: a base and four chamfered rails."""
    a = k[mat]
    a.box((w, d, t), M @ T(0, 0, t / 2), skip=("-z",), bevel=0.002)
    rt = 0.009
    for sx in (-1, 1):
        a.box((rt, d, rim), M @ T(sx * (w / 2 - rt / 2), 0, rim / 2), skip=("-z",), bevel=0.0025)
    for sy in (-1, 1):
        a.box((w - 2 * rt, rt, rim), M @ T(0, sy * (d / 2 - rt / 2), rim / 2), skip=("-z",), bevel=0.0025)
    return t


def tumbler(k, M, r=0.034, h=0.092, mat="glass", segs=14):
    k[mat].lathe([(r * 0.92, 0.0), (r, 0.004), (r * 1.02, h), (r * 1.02 - 0.0025, h + 0.001), (r * 0.98 - 0.0025, 0.014),
                  (0.0, 0.012)], M, segs=segs, sharp=(0,))


def carafe(k, M, mat="glass", segs=16):
    k[mat].lathe([(0.052, 0.0), (0.058, 0.006), (0.066, 0.05), (0.066, 0.12), (0.055, 0.17), (0.034, 0.2),
                  (0.03, 0.235), (0.034, 0.25), (0.0315, 0.252), (0.027, 0.236), (0.031, 0.2), (0.052, 0.17),
                  (0.062, 0.12), (0.062, 0.05), (0.0, 0.012)], M, segs=segs, sharp=(0,))


def cup_saucer(k, M, mat="glaze", coffee="charcoal"):
    """Espresso cup on a saucer, handle to +x."""
    a = k[mat]
    a.lathe([(0.04, 0.0), (0.045, 0.004), (0.066, 0.011), (0.069, 0.014), (0.066, 0.015), (0.04, 0.009), (0.0, 0.009)],
            M, segs=18, sharp=(0, 3))
    z0 = 0.009
    a.lathe([(0.022, z0), (0.026, z0 + 0.004), (0.034, z0 + 0.03), (0.036, z0 + 0.055), (0.0335, z0 + 0.056),
             (0.031, z0 + 0.03), (0.0, z0 + 0.012)], M, segs=16, sharp=(0,))
    if coffee:
        k[coffee].lathe([(0.0, z0 + 0.044), (0.0322, z0 + 0.044)], M, segs=16)
    pts = [(0.034 + 0.016 * math.sin(a_), 0, z0 + 0.03 + 0.015 * math.cos(a_)) for a_ in
           (math.pi * (0.05 + 0.9 * i / 6) for i in range(7))]
    a.tube(pts, 0.0035, M, sides=5)


def mug(k, M, mat="glaze", coffee="charcoal"):
    a = k[mat]
    h = 0.095
    a.lathe([(0.036, 0.0), (0.04, 0.005), (0.041, h), (0.0385, h + 0.001), (0.0375, 0.012), (0.0, 0.01)],
            M, segs=16, sharp=(0, 2))
    if coffee:
        k[coffee].lathe([(0.0, h - 0.02), (0.038, h - 0.02)], M, segs=16)
    pts = [(0.04 + 0.022 * math.sin(a_), 0, 0.05 + 0.026 * math.cos(a_)) for a_ in
           (math.pi * (0.04 + 0.92 * i / 7) for i in range(8))]
    a.tube(pts, 0.005, M, sides=5)


def reading_glasses(k, M, mat="black", folded=True):
    """Tortoiseshell-dark frames, folded, lying on the surface; lenses in smoked glass
    would be another draw call, so frames only (thin black acetate reads at a glance)."""
    a = k[mat]
    rr, rx = 0.024, 0.032           # lens rim radius, lens centre offset
    zc = 0.022 if folded else 0.026
    for sx in (-1, 1):
        ring = [(sx * rx + rr * math.cos(t) * 1.1, 0.0, zc + rr * math.sin(t) * 0.85)
                for t in (TAU * i / 12 for i in range(12))]
        a.tube(ring, 0.0024, M, sides=4, closed=True)
    a.tube([(-rx + rr * 0.95, 0, zc + 0.008), (0, 0, zc + 0.013), (rx - rr * 0.95, 0, zc + 0.008)], 0.0022, M, sides=4)
    for sx in (-1, 1):
        x0 = sx * (rx + rr * 1.08)
        if folded:     # temples folded flat behind the lenses
            pts = [(x0, 0.0, zc + 0.01), (x0 - sx * 0.006, 0.012, zc + 0.006), (-sx * 0.02, 0.016, 0.004 + 0.004 * (sx > 0)),
                   (-sx * 0.045, 0.016, 0.003 + 0.004 * (sx > 0))]
        else:
            pts = [(x0, 0.0, zc + 0.01), (x0 + sx * 0.002, 0.06, zc + 0.008), (x0 + sx * 0.004, 0.12, zc + 0.002),
                   (x0 + sx * 0.003, 0.135, zc - 0.012)]
        a.tube(pts, 0.002, M, sides=4)


def rounded_slab(a, w, d, t, r, M, seg=3, bottom=False, uv_tile=None):
    """Plan-rounded slab (laptop, notebook, coaster)."""
    pts = []
    for cx, cy, a0 in ((w / 2 - r, d / 2 - r, 0), (-w / 2 + r, d / 2 - r, 90), (-w / 2 + r, -d / 2 + r, 180),
                       (w / 2 - r, -d / 2 + r, 270)):
        for i in range(seg + 1):
            ang = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    tile = uv_tile or a.tile
    top = a.poly([(x, y, t) for x, y in pts], M, uvs=[(x / tile, y / tile) for x, y in pts])
    if bottom:
        a.poly([(x, y, 0) for x, y in pts[::-1]], M)
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        a.poly([(x0, y0, 0), (x1, y1, 0), (x1, y1, t), (x0, y0, t)], M,
               uvs=[(i * 0.02, 0), ((i + 1) * 0.02, 0), ((i + 1) * 0.02, t / tile), (i * 0.02, t / tile)])
    return top


def laptop(k, M, mat="black"):
    """A closed laptop: base and lid with a hairline between them."""
    w, d = 0.312, 0.221
    rounded_slab(k[mat], w, d, 0.0075, 0.012, M, seg=3)
    rounded_slab(k[mat], w - 0.001, d - 0.001, 0.0062, 0.0115, M @ T(0, 0, 0.0083), seg=3)
    k["steel"].box((0.025, 0.0012, 0.0016), M @ T(0, -d / 2 + 0.0004, 0.0078), skip=("+y",))   # lid notch


def notebook(k, M, rnd, w=0.148, d=0.21, t=0.016, cover="leather_black"):
    """A hardback notebook: cover boards, page block, an elastic band."""
    ct = 0.0022
    rounded_slab(k[cover], w, d, ct, 0.006, M)
    rounded_slab(k[cover], w, d, ct, 0.006, M @ T(0, 0, t - ct))
    k[cover].box((0.004, d, t), M @ T(-w / 2 + 0.002, 0, t / 2), skip=("+x",))
    pr = paper_rect(rnd, lines=5)
    k["spines"].box((w - 0.006, d - 0.006, t - 2 * ct), M @ T(0.001, 0, t / 2), skip=("-x", "+z", "-z"), uvrect=pr)
    k[cover].box((0.007, d + 0.002, t + 0.0016), M @ T(w / 2 - 0.022, 0, t / 2 + 0.0002), skip=("-z",))


def pen(k, M, mat="bronze", L=0.14):
    a = k[mat]
    a.lathe([(0.0, 0.0), (0.0025, 0.012), (0.0048, 0.02), (0.0052, L * 0.62), (0.0055, L * 0.64), (0.0055, L - 0.004),
             (0.004, L), (0.0, L)], M @ T(0, 0, 0.0055, ry=90) @ T(0, 0, -L / 2), segs=8, sharp=(3, 4))


def sculpture(k, M, kind="ring", mat="bronze", base="walnut"):
    """Small objects for a stack's top or a console: a bronze ring on a block, a split
    sphere, a stack of three pebbles."""
    if kind == "ring":
        k[base].box((0.11, 0.07, 0.035), M @ T(0, 0, 0.0175), skip=("-z",), bevel=0.003)
        R, r = 0.075, 0.011
        pts = [(R * math.sin(TAU * i / 22), 0, 0.035 + R + R * math.cos(TAU * i / 22) * -1) for i in range(22)]
        k[mat].tube(pts, r, M, sides=8, closed=True)
        return 0.035 + 2 * R + r
    if kind == "sphere":
        a = k[mat]
        r = 0.055
        prof = [(0.0, 0.0)] + [(r * math.sin(math.pi * i / 8), r - r * math.cos(math.pi * i / 8)) for i in range(1, 8)] + [(0.0, 2 * r)]
        a.lathe(prof, M @ T(-0.004, 0, 0, rz=10), segs=16)
        return 2 * r
    if kind == "pebbles":
        a = k[mat]
        z = 0.0
        for i, (rx, rz) in enumerate(((0.06, 0.022), (0.045, 0.019), (0.03, 0.016))):
            prof = [(0.0, 0.0), (rx * 0.7, 0.002), (rx, rz * 0.45), (rx * 0.8, rz * 0.85), (0.0, rz)]
            a.lathe(prof, M @ T(0.004 * i, -0.003 * i, z, rz=i * 37), segs=14)
            z += rz * 0.92
        return z
    raise ValueError(kind)


def bookends_stack(k, M, rnd, n=5):
    """A short row of upright books between two bronze L bookends (for a console)."""
    x = 0.0
    s = k["spines"]
    items = []
    for i in range(n):
        t = rnd.uniform(0.022, 0.045)
        h = rnd.uniform(0.21, 0.29)
        dd = rnd.uniform(0.15, 0.2)
        items.append((x + t / 2, t, h, dd, rnd.randrange(48)))
        x += t + 0.001
    off = -x / 2
    for cx, t, h, dd, cell in items:
        # upright: spine faces -y, the cell's length runs up z
        sp = spine_rect(cell)
        rect = (sp[0], sp[1], sp[2], sp[3])
        s.box((t, dd, h), M @ T(off + cx, 0, h / 2), skip=("-z",),
              uvrect={"-y": rect, "+z": paper_rect(rnd, 3), "+y": cover_rect(cell), "-x": cover_rect(cell),
                      "+x": cover_rect(cell)})
    for sx in (-1, 1):
        k["bronze"].box((0.004, 0.13, 0.15), M @ T(sx * (x / 2 + 0.002), 0, 0.075), skip=("-z",), bevel=0.001)
    return x + 0.008


# ------------------------------------------------------------------------------ plants

def _leaf_strip(a, base, d, L, Wd, pitch, droop, roll, rows=4, shape=(0.30, 0.78, 1.0, 0.82)):
    """One leaf: a strip folded along its midrib (3 verts across), tip collapsed."""
    bm, uvl = a.bm, a.uv
    side = Vector((-d.y, d.x, 0))
    grid = []
    for r in range(rows + 1):
        t = r / rows
        dist = t * L
        along = d * (math.cos(pitch) * dist) + Vector((0, 0, math.sin(pitch) * dist - droop * t * t))
        half = Wd * 0.5 * shape[r] if r < rows else 0.0
        fold = 0.12 * Wd * math.sin(math.pi * min(t * 1.2, 1.0))
        c = base + along
        sd = side * math.cos(roll) + Vector((0, 0, math.sin(roll)))
        grid.append([bm.verts.new(c - sd * half - Vector((0, 0, fold))), bm.verts.new(c),
                     bm.verts.new(c + sd * half - Vector((0, 0, fold)))])
    for r in range(rows):
        for cc in range(2):
            if r == rows - 1:
                if cc == 0:
                    quad, uvs = [grid[r][0], grid[r][1], grid[r + 1][1]], [(0, r / rows), (0.5, r / rows), (0.5, 1)]
                else:
                    quad, uvs = [grid[r][1], grid[r][2], grid[r + 1][1]], [(0.5, r / rows), (1, r / rows), (0.5, 1)]
            else:
                quad = [grid[r][cc], grid[r][cc + 1], grid[r + 1][cc + 1], grid[r + 1][cc]]
                uvs = [(cc * 0.5, r / rows), (cc * 0.5 + 0.5, r / rows), (cc * 0.5 + 0.5, (r + 1) / rows),
                       (cc * 0.5, (r + 1) / rows)]
            a._face(quad, uvs, True)


def _stem(a, pts, r, M):
    """Thin stem in the leaf material, mapped onto the leaf map's midrib."""
    rings = a.tube(pts, r, M, sides=4)
    for ring in rings:
        for v in ring:
            for lp in v.link_loops:
                lp[a.uv].uv = (0.5, 0.15)


def pot(k, M, mat, r=0.075, h=0.085, kind="cylinder", segs=20, soil=True, dress="charcoal", seed=1):
    """A planter: open underneath, a rim with thickness, the inside down to a top dressing
    of small pebbles (`dress` material: black pebbles in charcoal, or M_Plant_Soil)."""
    if kind == "cylinder":
        prof = [(r * 0.92, 0.0), (r * 0.97, 0.004), (r, 0.02), (r, h - 0.004), (r - 0.003, h), (r - 0.007, h - 0.004),
                (r - 0.007, h - 0.025)]
        sharp = (0, 4)
    elif kind == "bowl":
        prof = [(r * 0.55, 0.0), (r * 0.6, 0.004), (r * 0.85, h * 0.25), (r * 0.98, h * 0.6), (r, h - 0.003),
                (r - 0.004, h), (r - 0.008, h - 0.004), (r - 0.012, h - 0.03)]
        sharp = (0,)
    else:      # "tall": a tapered stoneware floor planter
        prof = [(r * 0.8, 0.0), (r * 0.84, 0.01), (r * 0.98, h * 0.75), (r, h - 0.006), (r - 0.004, h),
                (r - 0.012, h - 0.006), (r - 0.012, h - 0.05)]
        sharp = (0, 3)
    k[mat].lathe(prof, M, segs=segs, sharp=sharp)
    if soil:
        top_dressing(k, M, prof[-1][0] + 0.001, h - 0.024, dress, random.Random(seed), segs=segs)
    return h - 0.024


def top_dressing(k, M, r, z, mat, rnd, segs=16):
    """A pebbly disc: three jittered rings, so it catches light like gravel."""
    a = k[mat]
    bm = a.bm
    c = bm.verts.new(M @ Vector((0, 0, z + 0.002)))
    rings = []
    for ri, f in enumerate((0.35, 0.7, 1.0)):
        n = segs
        rings.append([bm.verts.new(M @ Vector((r * f * math.cos(TAU * (s + 0.5 * (ri % 2)) / n),
                                               r * f * math.sin(TAU * (s + 0.5 * (ri % 2)) / n),
                                               z + (rnd.uniform(-0.004, 0.004) if f < 1 else -0.003))))
                      for s in range(n)])
    for s in range(segs):
        a._face([c, rings[0][s], rings[0][(s + 1) % segs]], [(0, 0)] * 3, True)
    for ri in range(2):
        A, B = rings[ri], rings[ri + 1]
        for s in range(segs):
            s2 = (s + 1) % segs
            a._face([A[s], B[s], B[s2], A[s2]], [(0, 0)] * 4, True)


def snake_plant(k, M, rnd, n=12, height=0.75, spread=0.1, z0=0.0, width=0.075):
    """Sansevieria: stiff, broad sword leaves standing nearly upright in a loose clump, a few
    shorter ones splaying out, each slightly cupped and twisted, with a sharp tip."""
    a = k["leaf"]
    bm = a.bm
    for i in range(n):
        ang = i * 2.399963 + rnd.uniform(-0.3, 0.3)
        rad = spread * math.sqrt(rnd.random())
        L = height * (rnd.uniform(0.75, 1.0) if i < n * 0.6 else rnd.uniform(0.45, 0.7))
        Wd = width * rnd.uniform(0.8, 1.15) * (0.8 + 0.2 * L / height)
        lean = math.radians(rnd.uniform(2, 9) + 22 * (1 - L / height) + 10 * rad / max(spread, 1e-3))
        d = Vector((math.cos(ang), math.sin(ang), 0))
        side = Vector((-d.y, d.x, 0))
        base = Vector((rad * math.cos(ang), rad * math.sin(ang), z0))
        twist = rnd.uniform(-0.5, 0.5)
        rows = 6
        grid = []
        for r in range(rows + 1):
            t = r / rows
            up = Vector((0, 0, 1)) * math.cos(lean * t) + d * math.sin(lean * t)
            c = base + up * (L * t)
            # broad from just above the base, holding its width, narrowing to a sharp tip
            half = Wd * 0.5 * (0.45 + 0.55 * min(t / 0.25, 1.0)) * (1 - max(t - 0.55, 0) / 0.45) ** 0.8
            tw = twist * t
            sd = side * math.cos(tw) + d * math.sin(tw)
            cup = up.cross(sd).normalized() * (half * 0.35)       # the edges fold forward a little
            grid.append([M @ (c - sd * half + cup), M @ c, M @ (c + sd * half + cup)])
        V = [[bm.verts.new(p) for p in row] for row in grid]
        for r in range(rows):
            for cc in range(2):
                quad = [V[r][cc], V[r][cc + 1], V[r + 1][cc + 1], V[r + 1][cc]]
                uvs = [(cc * 0.5, r / rows), (cc * 0.5 + 0.5, r / rows), (cc * 0.5 + 0.5, (r + 1) / rows),
                       (cc * 0.5, (r + 1) / rows)]
                if r == rows - 1:          # the tip
                    quad = [V[r][cc], V[r][cc + 1], V[r + 1][1]]
                    uvs = [uvs[0], uvs[1], (0.5, 1.0)]
                a._face(quad, uvs, True)


def leafy_plant(k, M, rnd, n=26, height=0.32, spread=0.16, z0=0.0, leaf=(0.07, 0.1)):
    """A small potted plant for a desk or shelf (pilea / rubber-plant habit): thin stems
    arching out of the pot, each ending in a broad leaf, smaller leaves near the centre."""
    a = k["leaf"]
    for i in range(n):
        f = i / max(n - 1, 1)
        ang = i * 2.399963 + rnd.uniform(-0.2, 0.2)
        reach = spread * (0.25 + 0.75 * rnd.random() ** 0.7)
        top = z0 + height * (0.45 + 0.55 * rnd.random()) * (1 - 0.35 * reach / spread)
        d = Vector((math.cos(ang), math.sin(ang), 0))
        p0 = Vector((rnd.uniform(-0.01, 0.01), rnd.uniform(-0.01, 0.01), z0 - 0.005))
        p2 = Vector((d.x * reach, d.y * reach, top))
        p1 = Vector((d.x * reach * 0.3, d.y * reach * 0.3, z0 + (top - z0) * 0.85))
        pts = [tuple(p0.lerp(p1, t).lerp(p1.lerp(p2, t), t)) for t in (0, 0.5, 1.0)]
        _stem(a, pts, 0.0022, M)
        L = rnd.uniform(*leaf) * (0.75 + 0.35 * reach / spread)
        base = M @ Vector(pts[-1])
        dd = (M.to_3x3() @ d).normalized()
        _leaf_strip(a, base, dd, L, L * rnd.uniform(0.7, 0.85), math.radians(rnd.uniform(-5, 30)),
                    L * rnd.uniform(0.1, 0.25), rnd.uniform(-0.3, 0.3))


# ------------------------------------------------------------------------------ soft things

def pillow(k, M, mat, w=0.5, h=0.5, t=0.16, n=8, chop=0.03, rnd=None):
    """Scatter cushion standing on its edge, front -y: two crowned faces meeting at a seam
    with pointed corners, a slight waist, and the stylist's karate-chop dent on top."""
    a = k[mat]
    rnd = rnd or random.Random(1)
    front, back = [], []
    for i in range(n + 1):
        u = -1 + 2 * i / n
        rf, rb = [], []
        for j in range(n + 1):
            v = -1 + 2 * j / n
            x = u * w / 2 * (1 - 0.09 * (1 - v * v))
            z = v * h / 2 * (1 - 0.09 * (1 - u * u))
            bulge = (max(1 - u * u, 0) ** 0.42) * (max(1 - v * v, 0) ** 0.42)
            dent = chop * math.exp(-(u / 0.22) ** 2) * max(v, 0) ** 2
            z -= dent
            yb = t / 2 * bulge
            wob = 0.004 * math.sin(3 * u + 2 * v + rnd.uniform(0, 1)) * bulge
            rf.append(M @ Vector((x, -yb - wob, z + h / 2)))
            rb.append(M @ Vector((x, yb + wob * 0.5, z + h / 2)))
        front.append(rf)
        back.append(rb)
    bm = a.bm
    V = {}

    def vert(side, i, j, p):
        edge = i in (0, n) or j in (0, n)
        key = ("e", i, j) if edge else (side, i, j)
        if key not in V:
            V[key] = bm.verts.new(p)
        return V[key]

    for side, G in (("f", front), ("b", back)):
        for i in range(n):
            for j in range(n):
                q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
                vs = [vert(side, ii, jj, G[ii][jj]) for ii, jj in q]
                uvs = [(G[ii][jj].x / 0.25, G[ii][jj].z / 0.25) for ii, jj in q]
                if side == "b":
                    vs, uvs = vs[::-1], uvs[::-1]
                a._face(vs, uvs, True)
    # the seam: hard edge around the border
    for (i, j), (i2, j2) in [(((i, 0), (i + 1, 0))) for i in range(n)] + [(((i, n), (i + 1, n))) for i in range(n)] + \
            [(((0, j), (0, j + 1))) for j in range(n)] + [(((n, j), (n, j + 1))) for j in range(n)]:
        e = bm.edges.get((V[("e", i, j)], V[("e", i2, j2)]))
        if e:
            e.smooth = False


def throw_over_arm(k, M, mat, arm_w=0.2, arm_top=0.40, seat=0.23, width=0.55, inner_run=0.2,
                   th=0.010, rnd=None, n=22, m=9):
    """A folded throw draped over a sofa arm (arm centred on x = 0, outside towards +x):
    lying on the seat, up the inside of the arm, over its crowned top and hanging down the
    outside to z = 0 (the asset's origin). width runs along y."""
    rnd = rnd or random.Random(3)
    a = k[mat]
    hw = arm_w / 2
    # centre line of the fabric's inner face (touching the sofa), x/z
    path = [(-hw - inner_run, seat + 0.008), (-hw - inner_run * 0.55, seat + 0.016), (-hw - 0.07, seat + 0.024),
            (-hw - 0.026, seat + 0.07), (-hw - 0.016, seat + 0.14), (-hw - 0.012, arm_top - 0.06),
            (-hw + 0.006, arm_top + 0.012), (-hw * 0.4, arm_top + 0.032), (hw * 0.4, arm_top + 0.032),
            (hw - 0.004, arm_top + 0.014), (hw + 0.018, arm_top - 0.06), (hw + 0.022, arm_top * 0.55),
            (hw + 0.032, arm_top * 0.2), (hw + 0.046, 0.012)]
    # resample by arc length
    segl = [math.hypot(path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1]) for i in range(len(path) - 1)]
    tot = sum(segl)
    S = []
    for i in range(n + 1):
        s = tot * i / n
        j = 0
        while j < len(segl) - 1 and s > segl[j]:
            s -= segl[j]
            j += 1
        f = min(s / segl[j], 1.0)
        S.append((path[j][0] + (path[j + 1][0] - path[j][0]) * f, path[j][1] + (path[j + 1][1] - path[j][1]) * f))
    # 2D normals pointing away from the sofa
    N = []
    for i in range(n + 1):
        x0, z0 = S[max(i - 1, 0)]
        x1, z1 = S[min(i + 1, n)]
        tx, tz = x1 - x0, z1 - z0
        L = math.hypot(tx, tz) or 1
        N.append((-tz / L, tx / L))     # left of travel = away from the arm
    arc = [0.0]
    for i in range(1, n + 1):
        arc.append(arc[-1] + math.hypot(S[i][0] - S[i - 1][0], S[i][1] - S[i - 1][1]))
    ph = [rnd.uniform(0, TAU) for _ in range(3)]

    def fold(i, j):
        """Ripples along the drape: strong where it hangs or lies loose, none over the top."""
        x, z = S[i]
        over = 1.0 if (abs(x) < hw + 0.01 and z > arm_top - 0.03) else 0.0
        yv = -width / 2 + width * j / m
        if over:
            return 0.0
        if x > 0:          # hanging: two or three soft vertical folds, deepening toward the hem
            amp = 0.004 + 0.026 * (1 - z / max(arm_top, 1e-3)) ** 1.3
            return amp * (math.sin(yv * 24 + ph[0]) * 0.75 + math.sin(yv * 47 + ph[1]) * 0.25)
        # up the inside and lying on the seat: soft, irregular bunching
        amp = 0.008 + 0.012 * max(0.0, 1 - (z - seat) / 0.12)
        return amp * (math.sin(yv * 17 + ph[0] + arc[i] * 4) * 0.6 + math.sin(yv * 37 + ph[1] - arc[i] * 6) * 0.4)

    inner, outer = [], []
    for i in range(n + 1):
        ri, ro = [], []
        for j in range(m + 1):
            yv = -width / 2 + width * j / m
            off = fold(i, j)
            sag = 0.0
            x, z = S[i]
            if x > hw and i == n:                  # hem: the corners drop a little lower
                sag = -0.012 * (abs(yv) / (width / 2)) ** 2
            nx, nz = N[i]
            xi, zi = x + nx * off, z + nz * off + sag
            ri.append(M @ Vector((xi, yv, zi)))
            ro.append(M @ Vector((xi + nx * th, yv, zi + nz * th)))
        inner.append(ri)
        outer.append(ro)
    U = [[(arc[i] / 0.25, (-width / 2 + width * j / m) / 0.25) for j in range(m + 1)] for i in range(n + 1)]
    Vo = a.grid(outer, U, smooth=True)
    Vi = a.grid([row[::-1] for row in inner], [row[::-1] for row in U], smooth=True)
    # edges between the two layers (all four sides)
    bm = a.bm
    for i in range(n):
        for j_o, j_i in ((0, m), (m, 0)):
            q = [Vo[i][j_o], Vo[i + 1][j_o], Vi[i + 1][j_i], Vi[i][j_i]]
            if j_o == m:
                q = q[::-1]
            a._face(q, [(0, 0), (0.1, 0), (0.1, 0.05), (0, 0.05)], True)
    for i, flip in ((0, True), (n, False)):
        for j in range(m):
            q = [Vo[i][j], Vo[i][j + 1], Vi[i][m - j - 1], Vi[i][m - j]]
            if flip:
                q = q[::-1]
            a._face(q, [(0, 0), (0.1, 0), (0.1, 0.05), (0, 0.05)], True)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))


def folded_towel(k, M, mat, w=0.30, d=0.22, t=0.034):
    """A towel folded in thirds: a soft slab, the folded edge rounded toward -y."""
    k[mat].box((w, d, t), M @ T(0, 0, t / 2), skip=("-z",), bevel=t * 0.42, seg=3, smooth=True)


def rolled_towel(k, M, mat, L=0.30, r=0.05, segs=10, upright=False):
    """A rolled towel lying along x (or standing, upright=True, base at z = 0): a cylinder
    whose ends show the last turn of the roll as a shallow step."""
    a = k[mat]
    e = 0.0
    prof = [(0.0, -L / 2 + 0.0015), (r * 0.55, -L / 2 + 0.002), (r * 0.6, -L / 2 + 0.0045), (r * 0.9, -L / 2 + 0.004),
            (r, -L / 2 + 0.014), (r, L / 2 - 0.014), (r * 0.9, L / 2 - 0.004), (r * 0.6, L / 2 - 0.0045),
            (r * 0.55, L / 2 - 0.002), (0.0, L / 2 - 0.0015)]
    if upright:
        a.lathe(prof, M @ T(0, 0, L / 2 - 0.0015), segs=segs, sharp=(2, 7))
    else:
        a.lathe(prof, M @ T(0, 0, r, ry=90), segs=segs, sharp=(2, 7))
    return e


def basket(k, M, mat="wicker", r=0.21, h=0.30, segs=16):
    """A woven basket: banded wall (alternating rows), a rolled rim, open inside."""
    prof = [(r * 0.88, 0.0), (r * 0.9, 0.012)]
    rows = 9
    for i in range(1, rows + 1):
        z = 0.012 + (h - 0.03) * i / rows
        rr = r * (0.9 + 0.1 * i / rows) + (0.003 if i % 2 else 0.0)
        prof.append((rr, z))
    prof += [(r + 0.012, h - 0.008), (r + 0.006, h + 0.004), (r - 0.008, h), (r - 0.01, h - 0.02), (r * 0.86, 0.03),
             (0.0, 0.025)]
    k[mat].lathe(prof, M, segs=segs, sharp=(0,))


# ------------------------------------------------------------------------------ gallery furniture

def gallery_bench(k, M, w=1.6, d=0.4, h=0.45, mat="walnut"):
    """Solid walnut bench: a 60 mm top on two slab ends set in, a shadow gap under the top."""
    a = k[mat]
    tt = 0.06
    a.box((w, d, tt), M @ T(0, 0, h - tt / 2), bevel=0.004, seg=2)
    for sx in (-1, 1):
        a.box((0.06, d - 0.05, h - tt - 0.012), M @ T(sx * (w / 2 - 0.2), 0, (h - tt - 0.012) / 2), skip=("-z",),
              bevel=0.003)
        a.box((0.04, d - 0.09, 0.012), M @ T(sx * (w / 2 - 0.2), 0, h - tt - 0.006), skip=("-z", "+z"))
    a.box((w - 0.4 - 0.06, 0.035, 0.05), M @ T(0, 0, 0.1), bevel=0.002)


def gallery_console(k, M, w=1.6, d=0.36, h=0.8, mat="walnut"):
    """Slim walnut console: a thick top, two slab legs and a low shelf between them."""
    a = k[mat]
    tt = 0.045
    a.box((w, d, tt), M @ T(0, 0, h - tt / 2), bevel=0.004, seg=2)
    for sx in (-1, 1):
        a.box((0.045, d - 0.04, h - tt), M @ T(sx * (w / 2 - 0.1), 0, (h - tt) / 2), skip=("-z",), bevel=0.003)
    a.box((w - 0.2 - 0.045, d - 0.07, 0.03), M @ T(0, 0.01, 0.16), bevel=0.003)
    return h


# ------------------------------------------------------------------------------ groups

TRIOS = {
    # (kind, material, scale) back-left tall, middle, front-right small
    "mixed": [("bottle", "charcoal", 1.0), ("moon", "glaze", 0.95), ("bud", "charcoal", 1.0)],
    "glaze": [("amphora", "glaze", 0.9), ("cylinder", "glaze", 1.0), ("bud", "glaze", 1.1)],
    "charcoal": [("amphora", "charcoal", 0.95), ("moon", "charcoal", 0.85), ("bud", "charcoal", 1.0)],
    "pale": [("bottle", "glaze", 1.05), ("moon", "glaze", 0.8), ("cylinder", "charcoal", 0.7)],
}


def ceramic_trio(k, M, rnd, family="mixed", scale=1.0):
    """Three vessels of varied height in a loose triangle (odd number, a focal tall one)."""
    spots = [(-0.07, 0.05), (0.06, 0.035), (0.015, -0.07)]
    for (kind, mat, sc), (x, y) in zip(TRIOS[family], spots):
        vessel(k, M @ T((x + rnd.uniform(-0.01, 0.01)) * scale, (y + rnd.uniform(-0.01, 0.01)) * scale, 0,
                        rz=rnd.uniform(0, 360)), kind, mat, scale=sc * scale)


# ------------------------------------------------------------------ pickups
# the loose things a player expects to lift (lib/pickups.py has the rule): each call of these
# becomes its own pickup (a lemon bowl: the bowl and each lemon); books between bookends, trays,
# plants, cushions, throws, towels and baskets stay furniture
pickups.wrap(sys.modules[__name__], "accs", items=dict(
    book="book", open_book="book", vessel="vase", bowl="bowl", lemon="lemon", candle_dish="dish",
    tumbler="glass", carafe="carafe", cup_saucer="cup", mug="mug", reading_glasses="spectacles",
    laptop="laptop", notebook="notebook", sculpture="ornament",
), fixed=("bookends_stack",))
