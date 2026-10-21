"""A cluster of hand-thrown, aged terracotta pots of different sizes and shapes (rolled-rim
pots, a tall long-tom with a collar rim, a wide low bowl, a big low pot), grouped the way a
gardener would, each planted: a Boston fern, a clipped box ball, a little olive standard,
golden fountain grass, blue sedge, and star jasmine spilling over the rims. Variants:

  door   flanking the doorway: a tall long-tom with an olive standard, a rolled-rim pot of
         grass, a low bowl of jasmine
  mast   round a festoon mast's foot: a big low pot centred on the mast (jasmine trailing,
         sedge; its centre is kept clear for the mast) and a fern pot beside it
  corner three pots, fern / grass / box ball

Pots: one lathe each, traced from the foot up the outside, over a rolled rim (a real bead with
the wall's thickness), down the inside and across the soil to the centre, so a pot and its soil
are one mesh (one collider box) in one material. Hand-thrown: slightly out of round, the rim a
little wavy, a small lean, every pot's size jittered by its seed. The clay texture
(courtyard_pots_maps: Poly Haven planter_pot_clay scan detail + procedural ageing) has two
skins, a warm younger pot and a paler, lime-bloomed older one; v runs along the profile, so
the damp mossy foot, the lime tide line under the rim, the worn rim, the dark inside and the
top dressing land where they belong on every shape.

Plants: alpha-tested cards from courtyard_pots_maps' scan-built atlas (fern_02 fronds,
jasmine strands from periwinkle leaves and flowers, olive sprigs from shrub_02, box sprigs
and a box-leaf mat), bent along their length. Each card is two back-to-back single-sided
faces sharing an outward-and-up normal: three.js flips a double-sided face's normal when its
back is seen, which lit half the leaves from the floor (the old black look).

Collision: each pot is its own mesh; plants are NoCollide (the box ball sits inside its
pot's box). Origin: the cluster's main pot centre on the floor. Units are metres."""
import importlib
import math
import os
import random
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import courtyard_common as cc  # noqa: E402
import courtyard_pots_maps as maps  # noqa: E402

importlib.reload(cc)
importlib.reload(maps)
common = cc.common
textures = cc.textures

NAME = "CourtyardPots"

P = dict(
    name=NAME,
    variant="corner",
    seed=2,
)

# (x, y, shape, scale, plant)
VARIANTS = {
    "door": [(0.0, 0.0, "tom", 1.0, "shrub"), (0.48, -0.30, "roll", 0.85, "grass"),
             (-0.30, -0.42, "bowl", 0.8, "jasmine")],
    "mast": [(0.0, 0.0, "low", 1.0, "mast"), (0.62, -0.38, "roll", 0.75, "fern")],
    "corner": [(0.0, 0.0, "roll", 1.15, "fern"), (0.58, -0.22, "tom", 0.8, "grass"),
               (0.20, -0.62, "roll", 0.6, "box")],
}

# lathe profiles (r, z) at scale 1, in four runs: outside (foot .. neck, where the rim
# starts), rim (neck .. over the bead .. inner lip; its highest point is the apex), inside
# (lip .. where the soil meets the wall), soil (.. the centre, r = 0)
SHAPES = {
    # classic rolled-rim pot: a fat bead ~10 cm tall standing 4 cm proud of the wall
    "roll": dict(
        out=[(0.163, 0.0), (0.175, 0.012), (0.236, 0.30), (0.262, 0.425)],
        rim=[(0.281, 0.440), (0.297, 0.466), (0.299, 0.494), (0.287, 0.520), (0.264, 0.530), (0.247, 0.522)],
        ins=[(0.240, 0.478)],
        soil=[(0.13, 0.489), (0.035, 0.494), (0.0, 0.494)]),
    # long tom: tall, gently bellied, a thick collar with a bead at its top
    "tom": dict(
        out=[(0.153, 0.0), (0.165, 0.012), (0.192, 0.21), (0.224, 0.46), (0.246, 0.63), (0.250, 0.668)],
        rim=[(0.264, 0.677), (0.270, 0.703), (0.275, 0.729), (0.268, 0.745), (0.252, 0.750), (0.236, 0.745)],
        ins=[(0.230, 0.690)],
        soil=[(0.12, 0.698), (0.035, 0.703), (0.0, 0.703)]),
    # wide low bowl with a rolled lip
    "bowl": dict(
        out=[(0.135, 0.0), (0.148, 0.010), (0.235, 0.075), (0.315, 0.150), (0.355, 0.203)],
        rim=[(0.372, 0.213), (0.383, 0.230), (0.385, 0.248), (0.375, 0.260), (0.355, 0.264), (0.338, 0.257)],
        ins=[(0.330, 0.212)],
        soil=[(0.17, 0.222), (0.035, 0.226), (0.0, 0.226)]),
    # big low pot (the festoon mast stands in it)
    "low": dict(
        out=[(0.295, 0.0), (0.308, 0.012), (0.345, 0.14), (0.395, 0.29), (0.425, 0.385)],
        rim=[(0.440, 0.395), (0.452, 0.414), (0.456, 0.440), (0.448, 0.460), (0.428, 0.467), (0.408, 0.461)],
        ins=[(0.398, 0.410)],
        soil=[(0.20, 0.418), (0.05, 0.422), (0.0, 0.422)]),
}


# ----------------------------------------------------------------------------- materials

def clay_mat():
    """Aged terracotta, pots and their top dressing (two skins in one atlas)."""
    m = common.pbr_material("M_CourtyardPots_Terracotta", (1, 1, 1), roughness=0.88)
    if not any(nd.type == "TEX_IMAGE" for nd in m.node_tree.nodes):
        base, nor = maps.clay()
        common.set_base_color_map(m, textures.load(base))
        common.set_normal_map(m, textures.load(nor, non_color=True), 1.0)
    m.use_backface_culling = True
    return m


def leaf_mat():
    """Pot plants: the scan-built atlas, alpha-tested (glTF MASK), single-sided (the cards are
    doubled back to back, each side keeping the outward normal)."""
    m = common.pbr_material("M_CourtyardPots_Foliage", (1, 1, 1), roughness=0.6)
    nodes, links = m.node_tree.nodes, m.node_tree.links
    if not any(nd.type == "TEX_IMAGE" for nd in nodes):
        img = textures.load(maps.foliage())
        img.alpha_mode = "STRAIGHT"
        bsdf = next(nd for nd in nodes if nd.type == "BSDF_PRINCIPLED")
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.location = (bsdf.location.x - 700, bsdf.location.y)
        rnd = nodes.new("ShaderNodeMath")
        rnd.operation = "ROUND"
        rnd.location = (bsdf.location.x - 350, bsdf.location.y - 250)
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(tex.outputs["Alpha"], rnd.inputs[0])
        links.new(rnd.outputs[0], bsdf.inputs["Alpha"])
    m.use_backface_culling = True
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "DITHERED"
    return m


# ----------------------------------------------------------------------------- pots

def _profile(shape, scale):
    """Points (r, z) and each one's fraction p along the clay skin (maps.P_* keypoints)."""
    sh = SHAPES[shape]
    pts = [(r * scale, z * scale) for r, z in sh["out"] + sh["rim"] + sh["ins"] + sh["soil"]]
    n_out, n_rim, n_ins = len(sh["out"]), len(sh["rim"]), len(sh["ins"])
    i_neck = n_out - 1
    rim_idx = range(n_out, n_out + n_rim)
    i_apex = max(rim_idx, key=lambda i: pts[i][1])
    i_lip = n_out + n_rim - 1
    i_wall = i_lip + n_ins
    keys = [(0, 0.0), (1, maps.P_FOOT), (i_neck, maps.P_NECK), (i_apex, maps.P_APEX), (i_lip, maps.P_LIP),
            (i_wall, maps.P_WALL), (len(pts) - 1, 1.0)]
    arc = [0.0]
    for a, b in zip(pts[:-1], pts[1:]):
        arc.append(arc[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    ps = [0.0] * len(pts)
    for (ia, pa), (ib, pb) in zip(keys[:-1], keys[1:]):
        for i in range(ia, ib + 1):
            t = (arc[i] - arc[ia]) / max(arc[ib] - arc[ia], 1e-9)
            ps[i] = pa + (pb - pa) * t
    return pts, ps, dict(neck=i_neck, apex=i_apex, lip=i_lip, wall=i_wall)


def pot(name, shape, scale, loc, col, mat, root, rng, skin):
    """One hand-thrown pot with its soil. Returns (soil z, inner rim radius, outer rim radius,
    rim top z) in the pot's own frame (it stands at loc)."""
    pts, ps, idx = _profile(shape, scale)
    rmax = max(r for r, z in pts)
    H = max(z for r, z in pts)
    segs = 28 if rmax < 0.22 else 32 if rmax < 0.33 else 36
    reps = max(1, round(2 * math.pi * rmax / maps.U_M))
    u_off = rng.uniform(0, 1)
    # hand-thrown: out of round (2 and 3 lobes), a wavy rim, a slight lean
    e1, e2, e3 = rng.uniform(0.002, 0.005), rng.uniform(0.005, 0.010), rng.uniform(0.002, 0.005)
    f1, f2, f3 = (rng.uniform(0, 6.283) for _ in range(3))
    wav, fw = rng.uniform(0.0015, 0.003), rng.uniform(0, 6.283)
    lean = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)).normalized() * rng.uniform(0.006, 0.014)
    rot = rng.uniform(0, 6.283)

    def place(r, z, th):
        h = z / H
        k = 1 + e1 * math.cos(th - f1) * 0.5 + e2 * math.cos(2 * (th - f2)) * (0.35 + 0.65 * h) \
            + e3 * math.cos(3 * (th - f3)) * h
        zz = z + wav * math.sin(2 * th + fw) * h ** 6
        a = th + rot
        return Vector((r * k * math.cos(a) + lean.x * zz, r * k * math.sin(a) + lean.y * zz, zz))

    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rows = []
    for (r, z) in pts:
        if r < 1e-9:
            rows.append(None)
        else:
            rows.append([bm.verts.new(place(r, z, 2 * math.pi * s / segs)) for s in range(segs)])
    centre = bm.verts.new(place(0.0, pts[-1][1], 0.0))
    for i in range(len(pts) - 1):
        a, b = rows[i], rows[i + 1]
        va, vb = maps.skin_v(skin, ps[i]), maps.skin_v(skin, ps[i + 1])
        for s in range(segs):
            t = (s + 1) % segs
            ua, ub = s / segs * reps + u_off, (s + 1) / segs * reps + u_off
            if b is None:
                f = bm.faces.new((a[s], a[t], centre))
                uvs = ((ua, va), (ub, va), ((ua + ub) / 2, vb))
            else:
                f = bm.faces.new((a[s], a[t], b[t], b[s]))
                uvs = ((ua, va), (ub, va), (ub, vb), (ua, vb))
            for lp, uv in zip(f.loops, uvs):
                lp[uvl].uv = uv
    # the soil meets the inside wall in a crease
    w = rows[idx["wall"]]
    for s in range(segs):
        e = bm.edges.get((w[s], w[(s + 1) % segs]))
        if e:
            e.smooth = False
    ob = common.mesh_object(name, bm, col, mat, root, smooth=True)
    ob.location = loc
    r_in = pts[idx["lip"]][0]
    r_out = max(r for r, z in pts[idx["neck"]:idx["lip"] + 1])
    return pts[-1][1], r_in, r_out, pts[idx["apex"]][1], lean


# ----------------------------------------------------------------------------- plants

GAP = 0.0015


class Planting:
    """Leaf cards and bent strips, each emitted twice back to back (single-sided material),
    with per-vertex normals for volumetric shading."""

    def __init__(self, rng):
        self.rng = rng
        self.bm = bmesh.new()
        self.uvl = self.bm.loops.layers.uv.new("UVMap")
        self.normals = []

    def _face(self, cos, uvs, nrms):
        # the two sides sit GAP apart along the face normal, so a ray-traced bake (the room's
        # lightmap, or the vertex AO should these leaves ever be included) never starts a ray
        # inside the twin
        fn = (cos[1] - cos[0]).cross(cos[2] - cos[0])
        if fn.length < 1e-12:
            fn = (cos[2] - cos[0]).cross(cos[3] - cos[0]) if len(cos) > 3 else Vector((0, 0, 1))
        fn = fn.normalized() * GAP
        vs = []
        for co, nn in zip(cos, nrms):
            vs.append(self.bm.verts.new(co + fn))
            self.normals.append(nn)
        f = self.bm.faces.new(vs)
        for lp, uv in zip(f.loops, uvs):
            lp[self.uvl].uv = uv
        vb = []
        for co, nn in zip(cos, nrms):
            vb.append(self.bm.verts.new(co - fn))
            self.normals.append(nn)
        g = self.bm.faces.new(list(reversed(vb)))
        for lp, uv in zip(g.loops, list(reversed(uvs))):
            lp[self.uvl].uv = uv

    def strip(self, pts, hws, cell, normals, flip=None, window=1.0):
        """A bent card: the cell's centre line follows pts (base first), hws: half-width
        vector per point, normals: one per point; window < 1 maps only that central fraction
        of the cell's width onto the card."""
        u0, v0, du, dv = maps.cell_uv(cell)
        if window < 1.0:
            u0, du = u0 + du * (1 - window) / 2, du * window
        if flip if flip is not None else self.rng.random() < 0.5:
            ul, ur = u0 + du, u0
        else:
            ul, ur = u0, u0 + du
        seg = [0.0]
        for a, b in zip(pts[:-1], pts[1:]):
            seg.append(seg[-1] + (b - a).length)
        for i in range(len(pts) - 1):
            va, vb = v0 + dv * seg[i] / seg[-1], v0 + dv * seg[i + 1] / seg[-1]
            cos = [pts[i] - hws[i], pts[i] + hws[i], pts[i + 1] + hws[i + 1], pts[i + 1] - hws[i + 1]]
            self._face(cos, [(ul, va), (ur, va), (ur, vb), (ul, vb)], [normals[i], normals[i], normals[i + 1],
                                                                       normals[i + 1]])

    def card(self, centre, right, up, cell, normal):
        self.strip([centre - up, centre + up], [right, right], cell, [normal, normal])

    def mesh(self, bm, normals):
        """Merge a closed mesh (the box ball's core) with its own UVs and normals."""
        vm = {}
        for v, nn in zip(bm.verts, normals):
            vm[v] = self.bm.verts.new(v.co)
            self.normals.append(nn)
        uv_src = bm.loops.layers.uv.active
        for f in bm.faces:
            g = self.bm.faces.new([vm[v] for v in f.verts])
            for lp, ls in zip(g.loops, f.loops):
                lp[self.uvl].uv = ls[uv_src].uv

    def finish(self, name, col, mat, root):
        if not self.bm.verts:
            self.bm.free()
            return None
        ns = list(self.normals)
        ob = common.mesh_object(name, self.bm, col, mat, root, smooth=True)
        cc.set_vertex_normals(ob.data, ns)
        return ob


UP = Vector((0, 0, 1))


def _arc(base, d, length, elev0, curl, n, droop=0.0):
    """Points along an arching stem: starts at elevation elev0 (rad) heading along d, the
    elevation falling linearly by `curl` over its length (an arching frond or blade)."""
    pts = [Vector(base)]
    ds = length / (n - 1)
    for i in range(1, n):
        t = (i - 0.5) / (n - 1)
        e = elev0 - curl * t - droop * t * t
        pts.append(pts[-1] + (d * math.cos(e) + UP * math.sin(e)) * ds)
    return pts


def _side(pts, i, d):
    tan = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
    s = tan.cross(UP)
    if s.length < 1e-4:
        s = d.cross(UP)
    return tan, s.normalized()


def _twisted(pts, d, hw, widths, twist):
    """Half-width vectors: horizontal across the stem, rolled about it up to `twist` rad."""
    out = []
    n = len(pts)
    for i in range(n):
        tan, s = _side(pts, i, d)
        q = Matrix.Rotation(twist * i / (n - 1), 3, tan)
        out.append((q @ s) * hw * widths[i])
    return out


def fern(pl, c, L, n):
    """Boston fern: fronds from the crown, the inner ones near upright, the outer ones arching
    out over the rim and down."""
    rng = pl.rng
    a0 = rng.uniform(0, 2 * math.pi)
    for j in range(n):
        a = a0 + j * 2.399 + rng.uniform(-0.2, 0.2)          # golden angle: no gaps, no rows
        d = Vector((math.cos(a), math.sin(a), 0))
        inner = j % 3 == 0
        l = L * (rng.uniform(0.55, 0.75) if inner else rng.uniform(0.80, 1.08))
        elev = rng.uniform(1.15, 1.35) if inner else rng.uniform(0.75, 1.05)
        curl = rng.uniform(0.9, 1.3) if inner else rng.uniform(1.8, 2.6)
        base = c + d * rng.uniform(0.01, 0.05) + Vector((0, 0, 0.01))
        pts = _arc(base, d, l, elev, curl, 6)
        widths = [0.45, 0.95, 1.0, 0.95, 0.8, 0.55]
        hws = _twisted(pts, d, l * 0.085, widths, rng.uniform(-0.5, 0.5))
        nn = [(d * (0.25 + 0.35 * i / 5) + UP).normalized() for i in range(6)]
        pl.strip(pts, hws, ("frondA", "frondB", "frondC")[j % 3], nn)


def grass(pl, c, H, cell="grass", n=12, spread=0.04, upright=False):
    """Fountain grass: blade-fan cards from the crown, a few upright in the middle, the rest
    arching out and over so their tips fall below the rim like a waterfall. upright: a tall
    vase of near-vertical blades, only the tips bowing (a feather-reed type, for the long-tom)."""
    rng = pl.rng
    a0 = rng.uniform(0, 2 * math.pi)
    for j in range(n):
        a = a0 + j * 2.399 + rng.uniform(-0.2, 0.2)
        d = Vector((math.cos(a), math.sin(a), 0))
        up = j < max(2, n // 5)
        if upright:
            l = H * rng.uniform(0.70, 1.0)
            elev = rng.uniform(1.42, 1.54) if up else rng.uniform(1.25, 1.45)
            curl = rng.uniform(0.15, 0.4) if up else rng.uniform(0.5, 1.1)
        else:
            l = H * (rng.uniform(0.75, 0.9) if up else rng.uniform(0.85, 1.15))
            elev = rng.uniform(1.25, 1.40) if up else rng.uniform(0.95, 1.25)
            curl = rng.uniform(0.6, 1.0) if up else rng.uniform(2.0, 2.8)
        base = c + d * rng.uniform(0.0, spread) - Vector((0, 0, 0.01))
        pts = _arc(base, d, l, elev, curl, 5)
        hws = _twisted(pts, d, l * 0.075, [0.3, 0.75, 1.0, 1.05, 1.1], rng.uniform(-0.9, 0.9))
        nn = [(d * (0.3 + 0.5 * i / 4) + UP * 0.9).normalized() for i in range(5)]
        pl.strip(pts, hws, cell, nn, window=rng.uniform(0.6, 0.85))


def trailers(pl, c, r_in, r_out, z_rim, n, rng, drop=(0.18, 0.35), a0=None, arc_span=2 * math.pi):
    """Star jasmine strands from the soil, over the rim and hanging down the pot's side."""
    a0 = rng.uniform(0, 6.28) if a0 is None else a0
    for k in range(n):
        a = a0 + (k + rng.uniform(-0.3, 0.3)) * arc_span / n
        d = Vector((math.cos(a), math.sin(a), 0))
        dz = min(rng.uniform(*drop), z_rim - 0.04)
        c0 = Vector((c.x, c.y, 0))
        out = rng.uniform(0.02, 0.05)
        pts = [c0 + d * r_in * rng.uniform(0.35, 0.6) + Vector((0, 0, c.z + 0.015)),
               c0 + d * (r_in * 0.92) + Vector((0, 0, z_rim + 0.035)),
               c0 + d * (r_out + 0.025) + Vector((0, 0, z_rim + 0.01)),
               c0 + d * (r_out + out) + Vector((0, 0, z_rim - 0.07)),
               c0 + d * (r_out + out + 0.01) + Vector((0, 0, z_rim - dz * 0.6)),
               c0 + d * (r_out + out * 0.8) + Vector((0, 0, z_rim - dz))]
        side = d.cross(UP)
        # sideways sway at the tip, the strand rolled a little off the pot's surface
        pts[-1] += side * rng.uniform(-0.04, 0.04)
        pts[-2] += side * rng.uniform(-0.02, 0.02)
        hw = 0.050 * rng.uniform(0.85, 1.15)
        tilt = rng.uniform(-0.5, 0.5)
        hws = []
        for i, q in enumerate(pts):
            s = (Matrix.Rotation(tilt * (i / 5), 3, UP) @ side) if i >= 2 else side
            hws.append(s * hw * (0.8 if i == 0 else 1.0))
        nn = [UP, (d * 0.5 + UP).normalized(), (d + UP * 0.6).normalized(), (d + UP * 0.25).normalized(),
              (d + UP * 0.2).normalized(), (d + UP * 0.2).normalized()]
        pl.strip(pts, hws, "jasmineA" if rng.random() < 0.5 else "jasmineB", nn)


def jasmine_mound(pl, c, r_in, n, rng):
    """Jasmine filling a pot: short shoots arching up from the soil and lying across it."""
    a0 = rng.uniform(0, 6.28)
    for k in range(n):
        a = a0 + k * 2.399
        d = Vector((math.cos(a), math.sin(a), 0))
        l = rng.uniform(0.20, 0.34)
        base = c + d * rng.uniform(0.0, r_in * 0.45)
        pts = _arc(base, d, l, rng.uniform(0.9, 1.3), rng.uniform(1.8, 2.6), 5)
        hws = _twisted(pts, d, 0.052, [0.8, 1, 1, 1, 0.9], rng.uniform(-0.6, 0.6))
        nn = [(d * 0.3 + UP).normalized()] * 5
        pl.strip(pts, hws, "jasmineA" if k % 2 else "jasmineB", nn)


def olive_head(pl, centre, r, cards):
    """A little olive standard's crown: sprig cards on a loose ellipsoid, tips outward."""
    rng = pl.rng
    for _ in range(cards):
        while True:
            d = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.7, 1)))
            if 0.25 < d.length <= 1.0:
                break
        d.normalize()
        pos = centre + Vector((d.x * r, d.y * r, d.z * r * 0.8)) * rng.uniform(0.35, 0.75)
        up = (d * 0.85 + UP * 0.45 + Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)) * 0.25).normalized()
        right = up.cross(Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))).normalized()
        s = r * rng.uniform(0.75, 1.0)
        nn = (d * 0.75 + UP * 0.5).normalized()
        pl.card(pos + up * s * 0.4, right * s * 0.31, up * s * 0.5, "oliveA" if rng.random() < 0.55 else "oliveB", nn)


def box_ball(pl, centre, r, rng):
    """Clipped box: a lumpy core in the dense leaf mat, shingled with small sprig cards so its
    outline is leafy, not a smooth ball."""
    tmp = bmesh.new()
    bmesh.ops.create_icosphere(tmp, subdivisions=2, radius=r * 0.9)
    ph = [rng.uniform(0, 6.28) for _ in range(3)]
    for v in tmp.verts:
        dd = v.co.normalized()
        f = 1 + 0.06 * math.sin(5.0 * dd.x + ph[0]) * math.sin(4.0 * dd.y + ph[1]) * math.sin(4.5 * dd.z + ph[2])
        v.co = dd * r * 0.9 * f
        v.co.z *= 0.88
    bmesh.ops.delete(tmp, geom=[f for f in tmp.faces if all(v.co.z < -r * 0.5 for v in f.verts)], context="FACES")
    u0, v0, du, dv = maps.cell_uv("boxMat")
    uvl = tmp.loops.layers.uv.new("UVMap")
    for f in tmp.faces:
        # per face, the plane it faces most (triplanar): no stretched streaks down the sides
        f.normal_update()
        ax = max(range(3), key=lambda k: abs(f.normal[k]))
        a, b = [k for k in range(3) if k != ax]
        for lp in f.loops:
            co = lp.vert.co
            lp[uvl].uv = (u0 + du * (0.5 + 0.47 * co[a] / r), v0 + dv * (0.5 + 0.47 * co[b] / r))
    for v in tmp.verts:
        v.co += centre
    nrm = [((v.co - centre).normalized() * 0.8 + UP * 0.3).normalized() for v in tmp.verts]
    pl.mesh(tmp, nrm)
    tmp.free()
    n = int(105 * (r / 0.2) ** 2)
    for k in range(n):
        # even spread over the upper 85% of the ball (spiral)
        t = (k + 0.5) / n
        z = 1 - 1.75 * t
        rr = math.sqrt(max(0.0, 1 - z * z))
        a = k * 2.399
        d = Vector((rr * math.cos(a), rr * math.sin(a), z))
        pos = centre + Vector((d.x, d.y, d.z * 0.88)) * r * rng.uniform(0.90, 0.98)
        # a tangent direction (random about the normal); the shingle lies along it, tip lifting
        t0 = d.cross(UP) if abs(d.z) < 0.95 else Vector((1, 0, 0))
        t0 = (Matrix.Rotation(rng.uniform(0, 2 * math.pi), 3, d) @ t0).normalized()
        up = (t0 * 0.85 + d * rng.uniform(0.2, 0.4)).normalized()
        right = up.cross(d).normalized()
        right = (right + d * rng.uniform(-0.3, 0.3)).normalized()
        s = rng.uniform(0.12, 0.16) * (r / 0.2) ** 0.5
        nn = (d * 0.8 + UP * 0.3).normalized()
        pl.card(pos + up * s * 0.30, right * s * 0.31, up * s * 0.5, "boxSprig", nn)


def _tube(bm, pts, radii, sides=5):
    rings = []
    for i, (q, r) in enumerate(zip(pts, radii)):
        tan = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        a = tan.cross(Vector((1, 0, 0)) if abs(tan.x) < 0.9 else Vector((0, 1, 0))).normalized()
        b = tan.cross(a)
        rings.append([bm.verts.new(q + (a * math.cos(2 * math.pi * k / sides) + b * math.sin(2 * math.pi * k / sides)) * r)
                      for k in range(sides)])
    for ra, rb in zip(rings[:-1], rings[1:]):
        for k in range(sides):
            bm.faces.new((ra[k], ra[(k + 1) % sides], rb[(k + 1) % sides], rb[k]))
    tip = bm.verts.new(pts[-1] + (pts[-1] - pts[-2]).normalized() * radii[-1])
    for k in range(sides):
        bm.faces.new((rings[-1][k], rings[-1][(k + 1) % sides], tip))


# ----------------------------------------------------------------------------- build

def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rng = random.Random(p["seed"])
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    clay, leaf = clay_mat(), leaf_mat()
    pl = Planting(rng)
    stems = bmesh.new()
    skin0 = rng.randrange(2)
    for i, (x, y, shape, s, plant) in enumerate(VARIANTS[p["variant"]]):
        s *= rng.uniform(0.97, 1.03)
        skin = (skin0 + i) % 2
        zs, r_in, r_out, z_top, lean = pot(f"{n}_Pot{i}", shape, s, (x, y, 0), col, clay, root, rng, skin)
        # plants follow the pot's lean
        c = Vector((x, y, 0)) + Vector((lean.x * zs, lean.y * zs, zs))
        if plant == "fern":
            fern(pl, c, 0.60 * s + 0.22, 20)
        elif plant == "grass":
            if shape == "tom":
                grass(pl, c, 1.15 * s + 0.30, "grass", 24, 0.05, upright=True)
            else:
                grass(pl, c, 0.42 * s + 0.26, "grass", 27)
        elif plant == "shrub":
            # a little multi-stemmed olive standard: three bare stems, then the crown
            r = 0.40 * s
            head = c + Vector((0, 0, 0.44 + r * 0.6))
            for k in range(3):
                a = k * 2.1 + rng.uniform(-0.3, 0.3)
                top = head + Vector((math.cos(a) * r * 0.22, math.sin(a) * r * 0.22, -r * 0.15))
                mid = c.lerp(top, 0.5) + Vector((rng.uniform(-0.025, 0.025), rng.uniform(-0.025, 0.025), 0))
                pts = [c + Vector((math.cos(a) * 0.025, math.sin(a) * 0.025, -0.02)), mid, top]
                _tube(stems, pts, [0.016, 0.012, 0.007])
            olive_head(pl, head, r, 46)
            jasmine_mound(pl, c, r_in, 6, rng)
        elif plant == "box":
            r = 0.21 * s + 0.07
            box_ball(pl, c + Vector((0, 0, r * 0.55)), r, rng)
        elif plant == "jasmine":
            jasmine_mound(pl, c, r_in, 16, rng)
            trailers(pl, c, r_in, r_out, z_top, 14, rng, (0.12, 0.22))
        elif plant == "mast":
            # a ring of sedge round the mast (its foot clear) and jasmine spilling over the rim
            for k in range(5):
                a = k * 2 * math.pi / 5 + rng.uniform(-0.3, 0.3)
                grass(pl, c + Vector((math.cos(a) * 0.24 * s, math.sin(a) * 0.24 * s, 0)), 0.56, "sedge", 6, 0.0)
            trailers(pl, c, r_in, r_out, z_top, 16, rng, (0.2, 0.36))
        if plant in ("fern", "grass", "box") and shape != "tom":
            trailers(pl, c, r_in, r_out, z_top, 4, rng, (0.1, 0.25))
    leaves = pl.finish(f"{n}_PlantsNoCollide", col, leaf, root)
    # (alpha-cut leaves bake their vertex AO opaque: lib/vertex_ao)
    if stems.verts:
        common.mesh_object(f"{n}_StemsNoCollide", stems, col, cc.bark_mat(), root, smooth=True)
    else:
        stems.free()
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
