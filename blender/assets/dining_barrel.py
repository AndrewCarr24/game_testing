"""French-oak barrique (225 l Bordeaux style) standing on end as a wine-room high table.

28 riven oak staves (a wider bung stave at the front), each with eased edges meeting its
neighbours in a fine V joint, bulging smoothly to the bilge; the stave ends run past the
sunk head as the chime, chamfered outside, toasted inside, with the head's bevel seated in
the croze (a dark line round the head). Six blackened iron hoops (head, quarter and bilge
pairs), each with its riveted lap joint, the rivets lined up down one side. An oak bung in
the bung stave with a wine stain and drips round it.

Every stave and head board has its own piece of a scanned oak (Poly Haven oak_veneer_01,
CC0), tone and grain in one baked atlas, T_DiningBarrel_BaseColor / _Normal
(dining_barrel_tex.py), so the staves read as individual timbers.

Vertex AO (lib/vertex_ao.py, baked per vertex at export) is planned for: profile rows sit
1.2 cm off every hoop edge (the hoops' shadow stays in the narrow band next to them instead
of smearing over a whole stave face) and no stave vertex lies under the bung.

Origin: floor centre. 0.63 m across the bilge, 0.92 m tall (the chime top, where the tasting
board rests). Front (the bung) faces -Y. Units are metres.
"""
import importlib
import math
import os
import random
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402
import dining_barrel_tex as btex  # noqa: E402

importlib.reload(common)
importlib.reload(materials)
importlib.reload(btex)

NAME = "DiningBarrel"

P = dict(
    name=NAME, height=0.92, r_end=0.265, r_mid=0.315, staves=28,
    bung_w=1.35,            # bung stave width / an ordinary stave's
    stave_t=0.022,          # stave thickness at the chime
    joint=0.0045,           # width of each stave's eased edge (arc, m)
    joint_dip=0.0018,       # depth of the V joint between staves
    head_sink=0.024,        # head top below the chime top
    hoops=((0.055, 0.045), (0.175, 0.040), (0.325, 0.042)),   # (centre z, width) from each end
    hoop_t=0.0025,          # hoop thickness proud of the staves
    hoop_segs=40,
    hoop_finish="black",    # "black" (blackened iron) or "galvanised"
    rivet_angle=-40.0,      # degrees (atan2 in plan; -90 = front): the rivet line
    seed=11,
)

EPS = 0.012                 # profile rows this far off each hoop edge (vertex AO stays local)
MAX_BAND = 0.086            # longest stave band between profile rows


def barrel_r(z, H, r_end, r_mid):
    t = z / H * 2 - 1
    return r_end + (r_mid - r_end) * (1 - t * t)


# ----------------------------------------------------------------------------- layout

def layout(p):
    """Stave angles and profile rows: shared by the mesh and the texture atlas."""
    H, re_, rm = p["height"], p["r_end"], p["r_mid"]
    n = p["staves"]
    rnd = random.Random(p["seed"])
    w = [p["bung_w"]] + [1.0 + rnd.uniform(-0.06, 0.06) for _ in range(n - 1)]
    tot = sum(w)
    span = [2 * math.pi * x / tot for x in w]
    # stave 0 (the bung stave) centred on the front (-Y)
    th0 = -math.pi / 2 - span[0] / 2
    edges = [th0]
    for s in span:
        edges.append(edges[-1] + s)
    staves = []
    for k in range(n):
        staves.append(dict(a=edges[k], b=edges[k + 1], c=(edges[k] + edges[k + 1]) / 2,
                           width=span[k] * (rm + 0.002), crown=rnd.uniform(-0.0005, 0.0005)))
    # profile rows (outer surface)
    zs = {0.0, H - 0.009, H / 2}
    hoops = []
    for c, hw in p["hoops"]:
        for zc in (c, H - c):
            lo, hi = zc - hw / 2, zc + hw / 2
            hoops.append((lo, hi))
            zs.update((lo - EPS, hi + EPS))
    zs = sorted(zs)
    rows = [zs[0]]
    for z in zs[1:]:
        k = math.ceil((z - rows[-1]) / MAX_BAND - 1e-6)
        rows += [rows[-1] + (z - rows[-1]) * i / k for i in range(1, k)] + [z]
    rows = [z for z in rows if 0 <= z <= H - 0.009]
    outer = []
    for z in rows:
        outer.append((barrel_r(z, H, re_, rm), z))
    outer.append((re_ - 0.006, H))          # top chamfer (the chanfrein)
    s = [0.0]
    for (r0, z0), (r1, z1) in zip(outer[:-1], outer[1:]):
        s.append(s[-1] + math.hypot(r1 - r0, z1 - z0))
    r_in = re_ - p["stave_t"]
    zh = H - p["head_sink"]
    return dict(H=H, staves=staves, outer=outer, s=s, length=s[-1], hoops=sorted(hoops),
                r_in=r_in, zh=zh, bung_z=H / 2, r_head=r_in - 0.002)


# ----------------------------------------------------------------------------- mesh helpers

def _face(bm, verts, want, uv_layer=None, uvs=None):
    """Face from `verts`, wound so its normal points along `want`."""
    f = bm.faces.new(verts)
    f.normal_update()
    if f.normal.dot(Vector(want)) < 0:
        f.normal_flip()
    if uv_layer is not None and uvs is not None:
        lut = {v: uv for v, uv in zip(verts, uvs)}
        for loop in f.loops:
            loop[uv_layer].uv = lut[loop.vert]
    f.smooth = True
    return f


def _pol(r, th, z):
    return Vector((r * math.cos(th), r * math.sin(th), z))


# ----------------------------------------------------------------------------- body

def body_bmesh(p, L, A):
    """Staves (outer surface, chamfers, chime top and its toasted inner face) and the head,
    one bmesh with atlas UVs."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    st = L["staves"]
    n = len(st)
    e, dip = p["joint"], p["joint_dip"]
    H, r_in, zh = L["H"], L["r_in"], L["zh"]
    outer = L["outer"]
    no = len(outer)
    # full profile: outer rows, then over the top and down the inside of the chime
    prof = outer + [(r_in + 0.002, H), (r_in, zh - 0.003)]
    kinds = ["outer"] * no + ["top", "inner"]
    # columns: per stave J (joint, shared with the previous stave), a, b
    cols = []
    for k, s in enumerate(st):
        cols.append(("J", k, s["a"]))
        cols.append(("a", k, s["a"] + e / p["r_mid"]))
        cols.append(("b", k, s["b"] - e / p["r_mid"]))
    grid = []
    for i, (r, z) in enumerate(prof):
        row = []
        for kind, k, th in cols:
            rr = r
            if kinds[i] == "outer" and i < no - 1:
                rr = r - dip if kind == "J" else r + st[k]["crown"]
            elif i == no - 1:                       # chamfer top edge: half the joint
                rr = r - dip * 0.5 if kind == "J" else r
            row.append(bm.verts.new(_pol(rr, th, z)))
        grid.append(row)

    def uv_for(i, ci, k, piece):
        """Atlas uv of grid vertex (row i, column ci) as part of stave k's `piece`."""
        _, _, th = cols[ci]
        d = (th - st[k]["c"] + math.pi) % (2 * math.pi) - math.pi
        r, z = prof[i]
        if piece == "outer":
            return A.stave_uv(k, d * r, L["s"][i])
        if piece == "top":
            return A.patch_uv("end", k, d * r, prof[no - 1][0] - r)
        return A.patch_uv("toast", k, d * r, H - z)

    nc = len(cols)
    sharp_rows = {no - 2, no - 1, no}          # the chamfer, top and inner corners
    for i in range(len(prof) - 1):
        piece = "outer" if i < no - 1 else "top" if i == no - 1 else "inner"
        for k in range(n):
            c0 = 3 * k
            for c in (c0, c0 + 1, c0 + 2):
                c1 = (c + 1) % nc
                vs = [grid[i][c], grid[i][c1], grid[i + 1][c1], grid[i + 1][c]]
                uvs = [uv_for(i, c, k, piece), uv_for(i, c1, k, piece),
                       uv_for(i + 1, c1, k, piece), uv_for(i + 1, c, k, piece)]
                _face(bm, vs, _out_dir(piece, (vs[0].co + vs[2].co) / 2), uvl, uvs)
    bm.edges.ensure_lookup_table()
    # sharp: the stave joints (vertical edges of the J columns) and the chamfer/chime corners
    jset = {grid[i][3 * k] for i in range(no) for k in range(n)}
    for ed in bm.edges:
        a, b = ed.verts
        if a in jset and b in jset and abs(a.co.z - b.co.z) > 1e-6:
            ed.smooth = False
    for i in sharp_rows:
        if i < len(grid):
            for c in range(nc):
                ed = bm.edges.get((grid[i][c], grid[i][(c + 1) % nc]))
                if ed is not None:
                    ed.smooth = False

    # head: bevel seated in the croze, rim, rings, centre
    segs = 48
    rings = [(r_in + 0.003, zh - 0.006), (L["r_head"], zh), (L["r_head"] - 0.015, zh), (L["r_head"] - 0.06, zh)]
    hv = [[bm.verts.new(_pol(r, 2 * math.pi * j / segs, z)) for j in range(segs)] for r, z in rings]
    centre = bm.verts.new((0, 0, zh))
    for i in range(len(rings) - 1):
        for j in range(segs):
            j1 = (j + 1) % segs
            vs = [hv[i][j], hv[i][j1], hv[i + 1][j1], hv[i + 1][j]]
            _face(bm, vs, (0, 0, 1), uvl, [A.head_uv(v.co.x, v.co.y) for v in vs])
    for j in range(segs):
        vs = [hv[-1][j], hv[-1][(j + 1) % segs], centre]
        _face(bm, vs, (0, 0, 1), uvl, [A.head_uv(v.co.x, v.co.y) for v in vs])
    for j in range(segs):
        ed = bm.edges.get((hv[1][j], hv[1][(j + 1) % segs]))
        if ed is not None:
            ed.smooth = False
    return bm


def _out_dir(piece, mid):
    radial = Vector((mid.x, mid.y, 0)).normalized()
    if piece == "outer":
        return radial
    if piece == "top":
        return Vector((0, 0, 1))
    return -radial


# ----------------------------------------------------------------------------- hoops

def hoops_bmesh(p, L):
    bm = bmesh.new()
    H, re_, rm, t = L["H"], p["r_end"], p["r_mid"], p["hoop_t"]
    segs = p["hoop_segs"]
    rnd = random.Random(p["seed"] + 5)
    R = lambda z: barrel_r(z, H, re_, rm)
    for lo, hi in L["hoops"]:
        ring = []
        for r, z in ((R(lo) + t, lo), (R(hi) + t, hi), (R(hi) - 0.001, hi)):
            ring.append([bm.verts.new(_pol(r, 2 * math.pi * j / segs, z)) for j in range(segs)])
        for j in range(segs):
            j1 = (j + 1) % segs
            th = 2 * math.pi * (j + 0.5) / segs
            _face(bm, [ring[0][j], ring[0][j1], ring[1][j1], ring[1][j]], _pol(1, th, 0))
            _face(bm, [ring[1][j], ring[1][j1], ring[2][j1], ring[2][j]], (0, 0, 1))
            ed = bm.edges.get((ring[1][j], ring[1][j1]))
            ed.smooth = False
        # riveted lap joint: the band's outer end lies over itself for ~6 cm
        phi = math.radians(p["rivet_angle"] + rnd.uniform(-5, 5))
        _lap(bm, R, lo, hi, t, phi, segs)
    return bm


def _lap(bm, R, lo, hi, t, phi, segs):
    rc = R((lo + hi) / 2)
    half = 0.032 / rc
    n = 4
    # chord sag of the hoop's own facets: keep the lap clear of them
    sag = rc * (1 - math.cos(math.pi / segs))
    cols = []
    for i in range(n + 1):
        u = i / n
        th = phi - half + 2 * half * u
        th_ = 0.0006 + 0.0010 * u          # thin (lapped-under) end -> thick (outer end) step
        cols.append((th, th_))
    rows = lambda th, thick: [(R(lo + 0.0015) + t + thick, lo + 0.0015), (R(hi - 0.0012) + t + thick, hi - 0.0012),
                              (R(hi - 0.0012) + t - sag - 0.0004, hi - 0.0012)]
    grid = [[bm.verts.new(_pol(r, th, z)) for r, z in rows(th, thick)] for th, thick in cols]
    for i in range(n):
        th = (cols[i][0] + cols[i + 1][0]) / 2
        a, b = grid[i], grid[i + 1]
        _face(bm, [a[0], b[0], b[1], a[1]], _pol(1, th, 0))
        _face(bm, [a[1], b[1], b[2], a[2]], (0, 0, 1))
    end = grid[-1]
    th_end = cols[-1][0]
    tang = Vector((-math.sin(th_end), math.cos(th_end), 0))
    base_lo = bm.verts.new(_pol(R(lo + 0.0015) + t - sag - 0.0004, th_end, lo + 0.0015))
    f = _face(bm, [end[0], end[1], end[2], base_lo], tang)
    for ed in f.edges:
        ed.smooth = False
    for i in range(n):
        ed = bm.edges.get((grid[i][1], grid[i + 1][1]))
        if ed is not None:
            ed.smooth = False
    # two rivets through the lap
    for du in (-0.4, 0.4):
        th = phi + du * half
        thick = 0.0006 + 0.0010 * (0.5 + du / 2)
        zc = (lo + hi) / 2
        base = _pol(R(zc) + t + thick - 0.0002, th, zc)
        _rivet(bm, base, Vector((math.cos(th), math.sin(th), 0)), Vector((-math.sin(th), math.cos(th), 0)))


def _rivet(bm, base, nrm, tan, r=0.0046, h=0.0026, segs=6):
    up = Vector((0, 0, 1))
    ring0 = [bm.verts.new(base + (tan * math.cos(a) + up * math.sin(a)) * r)
             for a in (2 * math.pi * j / segs for j in range(segs))]
    ring1 = [bm.verts.new(base + nrm * (h * 0.7) + (tan * math.cos(a) + up * math.sin(a)) * r * 0.68)
             for a in (2 * math.pi * j / segs for j in range(segs))]
    apex = bm.verts.new(base + nrm * h)
    for j in range(segs):
        j1 = (j + 1) % segs
        _face(bm, [ring0[j], ring0[j1], ring1[j1], ring1[j]], nrm)
        _face(bm, [ring1[j], ring1[j1], apex], nrm)


# ----------------------------------------------------------------------------- bung

def bung_bmesh(p, L, A):
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    segs = 16
    prof = [(0.0255, -0.004), (0.0238, 0.0045), (0.0222, 0.0068), (0.0175, 0.0078)]   # tapered plug, eased top
    rows = [[bm.verts.new((r * math.cos(2 * math.pi * j / segs), r * math.sin(2 * math.pi * j / segs), h))
             for j in range(segs)] for r, h in prof]
    apex = bm.verts.new((0, 0, 0.0082))
    for i in range(len(rows) - 1):
        for j in range(segs):
            j1 = (j + 1) % segs
            vs = [rows[i][j], rows[i][j1], rows[i + 1][j1], rows[i + 1][j]]
            mid = (vs[0].co + vs[2].co) / 2
            _face(bm, vs, (mid.x, mid.y, 0.4 + i), uvl, [A.bung_uv(v.co.x, v.co.y) for v in vs])
    for j in range(segs):
        vs = [rows[-1][j], rows[-1][(j + 1) % segs], apex]
        _face(bm, vs, (0, 0, 1), uvl, [A.bung_uv(v.co.x, v.co.y) for v in vs])
    for j in range(segs):
        for i in (1, 2):
            bm.edges.get((rows[i][j], rows[i][(j + 1) % segs])).smooth = False
    # seat it in the bung stave (+Z -> -Y), on the stave's surface at the bung height
    s0 = L["staves"][0]
    r = barrel_r(L["bung_z"], L["H"], p["r_end"], p["r_mid"]) + s0["crown"]
    m = Matrix.Translation((0, -r, L["bung_z"])) @ Matrix.Rotation(math.radians(90), 4, "X")
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    return bm


# ----------------------------------------------------------------------------- build

def hoop_material(finish):
    if finish == "galvanised":
        return common.pbr_material("M_DiningBarrel_Galvanised", (0.50, 0.51, 0.52), roughness=0.5, metallic=1.0)
    return common.pbr_material("M_Hoop_Steel", (0.022, 0.021, 0.021), roughness=0.5, metallic=0.3)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    L = layout(p)
    A = btex.Atlas(L, p)
    oak = A.material()
    body = common.mesh_object(f"{n}_Body", body_bmesh(p, L, A), col, oak, root, smooth=False)
    hoops = common.mesh_object(f"{n}_Hoops", hoops_bmesh(p, L), col, hoop_material(p["hoop_finish"]), root,
                               smooth=False)
    bung = common.mesh_object(f"{n}_Bung_NoCollide", bung_bmesh(p, L, A), col, oak, root, smooth=False)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
