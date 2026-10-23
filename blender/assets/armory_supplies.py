"""Armory supplies: a 2.4 x 0.5 x 2.2 m run of graphite steel shelving, four shelves (blue water drums
on the floor shelf, kraft ration cases, olive ammo cans), a white wall-hung medical cabinet with a red
cross to its right, and at its left end a hook rail with two olive plate carriers and two gas masks.
All fixed set dressing. About 3.75 wide x 0.5 deep x 2.2 tall. Origin: floor centre of the whole run;
the BACK is the wall plane at y = +0.25 (the shelving's back posts touch it), the room is -Y."""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bunker_kit as bk  # noqa: E402
import library_kit  # noqa: E402
from library_kit import Mesh, common, materials  # noqa: E402

importlib.reload(bk)
importlib.reload(library_kit)
import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402


def _ortho(d):
    """Two unit vectors perpendicular to d (and each other): u x v = d."""
    d = Vector(d).normalized()
    a = Vector((0, 0, 1)) if abs(d.z) < 0.95 else Vector((1, 0, 0))
    u = d.cross(a).normalized()
    v = d.cross(u).normalized()
    return u, v


class M(Mesh):
    """library_kit.Mesh plus beveled boxes, cylinders/cones, spheres, tori, sweeps, prisms."""

    def _new_faces(self, before):
        return [f for f in self.bm.faces if f not in before]

    def _uv(self, faces, tile=None):
        self._set_uv_box(faces, (1, 1, 1), (0, 0), tile or self.tile)

    def rb(self, centre, size, bev=0.003, **kw):
        """Box with chamfered edges (one segment): catches a highlight on every edge."""
        before = set(self.bm.faces)
        verts = self.box(centre, size, **kw)
        edges = list({e for v in verts for e in v.link_edges})
        bmesh.ops.bevel(self.bm, geom=list(verts) + edges, offset=min(bev, min(size) * 0.45),
                        segments=1, affect="EDGES")
        self._uv(self._new_faces(before), kw.get("tile"))

    def cyl(self, a, b, r, r2=None, segs=16, caps=(True, True), smooth=True, tile=None, start=0.0):
        """Cylinder / cone from point a (radius r) to point b (radius r2); caps flat, sides smooth."""
        a, b = Vector(a), Vector(b)
        r2 = r if r2 is None else r2
        u, v = _ortho(b - a)
        bm = self.bm
        before = set(bm.faces)
        ang = [start + 2 * math.pi * i / segs for i in range(segs)]

        def ring(p, rad):
            return [bm.verts.new(p + rad * (math.cos(t) * u + math.sin(t) * v)) for t in ang]

        r0, r1 = ring(a, r), ring(b, r2)
        for i in range(segs):
            j = (i + 1) % segs
            f = bm.faces.new([r0[i], r0[j], r1[j], r1[i]])
            f.smooth = smooth
        if caps[0] and r > 1e-6:
            bm.faces.new(list(reversed(ring(a, r))))
        if caps[1] and r2 > 1e-6:
            bm.faces.new(ring(b, r2))
        self._uv(self._new_faces(before), tile)

    def sphere(self, c, r, segs=12, rings=8, squash=1.0):
        before = set(self.bm.faces)
        res = bmesh.ops.create_uvsphere(self.bm, u_segments=segs, v_segments=rings, radius=r)
        bmesh.ops.scale(self.bm, vec=(1, 1, squash), verts=res["verts"])
        bmesh.ops.translate(self.bm, vec=Vector(c), verts=res["verts"])
        fs = self._new_faces(before)
        for f in fs:
            f.smooth = True
        self._uv(fs)

    def sweep(self, pts, radii, segs=10, caps=True, frame0=None, scale_v=1.0):
        """Tube through points `pts` with a radius per point (parallel-transport frames).
        scale_v flattens the cross-section (an oval cable)."""
        bm = self.bm
        before = set(bm.faces)
        pts = [Vector(p) for p in pts]
        n = len(pts)
        if not hasattr(radii, "__len__"):
            radii = [radii] * n
        rings, prev_u = [], None
        for i, p in enumerate(pts):
            t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
            if prev_u is None:
                u = _ortho(t)[0] if frame0 is None else Vector(frame0)
                u = (u - t * u.dot(t)).normalized()
            else:
                u = (prev_u - t * prev_u.dot(t)).normalized()
            prev_u = u
            v = t.cross(u).normalized()
            rings.append((p, u, v))
        ang = [2 * math.pi * k / segs for k in range(segs)]

        def verts_of(i):
            p, u, v = rings[i]
            return [bm.verts.new(p + radii[i] * (math.cos(a) * u + math.sin(a) * v * scale_v)) for a in ang]

        vs = [verts_of(i) for i in range(n)]
        for i in range(n - 1):
            for k in range(segs):
                k2 = (k + 1) % segs
                f = bm.faces.new([vs[i][k], vs[i][k2], vs[i + 1][k2], vs[i + 1][k]])
                f.smooth = True
        if caps:
            bm.faces.new(list(reversed(verts_of(0))))
            bm.faces.new(verts_of(n - 1))
        fs = self._new_faces(before)
        bmesh.ops.recalc_face_normals(bm, faces=fs)
        self._uv(fs)

    def torus(self, c, R, r, axis=(0, 1, 0), segs=24, tsegs=8):
        bm = self.bm
        before = set(bm.faces)
        u, v = _ortho(axis)
        ax = Vector(axis).normalized()
        c = Vector(c)
        rows = []
        for i in range(segs):
            a = 2 * math.pi * i / segs
            dirv = math.cos(a) * u + math.sin(a) * v
            ctr = c + R * dirv
            rows.append([bm.verts.new(ctr + r * (math.cos(t) * dirv + math.sin(t) * ax))
                         for t in [2 * math.pi * k / tsegs for k in range(tsegs)]])
        for i in range(segs):
            i2 = (i + 1) % segs
            for k in range(tsegs):
                k2 = (k + 1) % tsegs
                f = bm.faces.new([rows[i][k], rows[i2][k], rows[i2][k2], rows[i][k2]])
                f.smooth = True
        fs = self._new_faces(before)
        bmesh.ops.recalc_face_normals(bm, faces=fs)
        self._uv(fs)

    def prism(self, pts, origin, u, v, depth, w=None):
        """Polygon `pts` (a, b) in the plane origin + a*u + b*v, extruded `depth` along w
        (default u x v)."""
        bm = self.bm
        u, v = Vector(u), Vector(v)
        w = (Vector(w) if w is not None else u.cross(v)).normalized()
        before = set(bm.faces)
        vs = [bm.verts.new(Vector(origin) + a * u + b * v) for a, b in pts]
        f = bm.faces.new(vs)
        res = bmesh.ops.extrude_face_region(bm, geom=[f])
        nv = [e for e in res["geom"] if isinstance(e, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, vec=w * depth, verts=nv)
        fs = self._new_faces(before)
        bmesh.ops.recalc_face_normals(bm, faces=fs)
        self._uv(fs)


def mark(*meshes):
    return [(m, set(m.bm.verts)) for m in meshes]


def xform(marks, matrix):
    """Rigidly move everything the meshes gained since mark() (a hinged lid, a tilted tool)."""
    for m, before in marks:
        bmesh.ops.transform(m.bm, matrix=matrix, verts=[v for v in m.bm.verts if v not in before])


def rot_about(point, axis, angle):
    p = Vector(point)
    return Matrix.Translation(p) @ Matrix.Rotation(angle, 4, axis) @ Matrix.Translation(-p)

NAME = "ArmorySupplies"

P = dict(
    name=NAME,
    shelf_z=(0.20, 0.80, 1.40, 2.00),
    shelf_x=-0.05,
    shelf_w=2.4,
    height=2.2,
)

WALL = 0.25
OX = 0.10          # shifts the whole run so it is centred on x = 0


def ammo_can(ol, gm, cx, cy, z, yaw=0.0):
    """M2A1-pattern can, lid on top, 0.30 x 0.15 x 0.18 (kept light: it appears 20 times)."""
    mk = mark(ol, gm)
    ol.box((0, 0, 0.087), (0.30, 0.15, 0.174))
    ol.box((0, 0, 0.174), (0.306, 0.156, 0.016))
    gm.box((0, -0.0795, 0.15), (0.034, 0.007, 0.040))
    gm.box((0, 0, 0.1845), (0.13, 0.016, 0.006))
    xform(mk, Matrix.Translation((cx, cy, z)) @ Matrix.Rotation(yaw, 4, "Z"))


def kraft_case(kr, po, wh, cx, cy, z, w=0.40, d=0.34, h=0.26, yaw=0.0, label=True):
    """A kraft ration case, taped shut."""
    mk = mark(kr, po, wh)
    kr.box((0, 0, h / 2), (w, d, h))
    po.box((0, 0, h + 0.0006), (0.055, d + 0.0005, 0.0012))                      # tape over the seam
    po.box((0, -d / 2 - 0.0006, h * 0.72), (0.055, 0.0012, h * 0.56))
    if label:
        wh.box((0.12, -d / 2 - 0.0008, h * 0.45), (0.13, 0.0012, 0.085))
        po.box((0.12, -d / 2 - 0.0016, h * 0.45), (0.10, 0.0006, 0.012))
    xform(mk, Matrix.Translation((cx, cy, z)) @ Matrix.Rotation(yaw, 4, "Z"))


def drum(bl, po, cx, cy, z, r=0.16, h=0.52):
    """A blue HDPE water drum: ribs, a chimed top, two bungs."""
    bl.cyl((cx, cy, z), (cx, cy, z + h), r, segs=14)
    for zz in (0.17, 0.34):
        bl.cyl((cx, cy, z + zz - 0.012), (cx, cy, z + zz + 0.012), r + 0.005, segs=14, caps=(False, False))
    bl.cyl((cx, cy, z + h), (cx, cy, z + h + 0.025), r + 0.004, r - 0.004, segs=14, caps=(False, True))
    for a, rr in ((55, 0.08), (200, 0.075)):
        px, py = cx + rr * math.cos(math.radians(a)), cy + rr * math.sin(math.radians(a))
        po.cyl((px, py, z + h + 0.018), (px, py, z + h + 0.04), 0.022, segs=8)


def hook(gm, x, y, z):
    gm.cyl((x, y, z), (x, y - 0.055, z), 0.006, segs=6)
    gm.cyl((x, y - 0.055, z), (x, y - 0.055, z + 0.04), 0.006, segs=6)
    gm.sphere((x, y - 0.055, z + 0.043), 0.0075, segs=6, rings=4)


def plate_carrier(ol, gm, po, x, y, z):
    """An olive plate carrier hanging by its shoulder straps from a hook at (x, y, z): origin at the hook,
    front toward -Y."""
    mk = mark(ol, gm, po)
    for sx in (-0.085, 0.085):
        ol.rb((sx, 0.0, -0.02), (0.05, 0.062, 0.014), bev=0.003)                    # strap over the hook
        ol.rb((sx, -0.036, -0.075), (0.05, 0.012, 0.12), bev=0.003)                  # front strap
        ol.rb((sx, 0.036, -0.075), (0.05, 0.012, 0.12), bev=0.003)                   # back strap
    ol.rb((0, -0.032, -0.235), (0.30, 0.040, 0.34), bev=0.012)                       # front panel
    ol.rb((0, 0.040, -0.225), (0.28, 0.030, 0.32), bev=0.010)                        # back panel
    for k in range(5):                                                               # MOLLE webbing rows
        ol.box((0, -0.0535, -0.11 - 0.04 * k), (0.27, 0.003, 0.009))
    for k, sx in enumerate((-0.085, 0.0, 0.085)):                                    # three mag pouches
        ol.rb((sx, -0.066, -0.305), (0.075, 0.036, 0.125), bev=0.006)
        ol.rb((sx, -0.088, -0.255), (0.077, 0.010, 0.04), bev=0.003)
        gm.cyl((sx, -0.094, -0.262), (sx, -0.098, -0.262), 0.0065, segs=8)
    ol.rb((0, -0.062, -0.15), (0.20, 0.028, 0.07), bev=0.005)                         # admin pouch
    po.box((0, -0.077, -0.15), (0.12, 0.002, 0.03))                                  # patch
    for sx in (-1, 1):                                                               # cummerbund tabs hanging behind
        ol.box((sx * 0.10, 0.062, -0.22), (0.09, 0.012, 0.24))
        gm.box((sx * 0.10, 0.0685, -0.30), (0.03, 0.002, 0.03))
    xform(mk, Matrix.Translation((x, y, z)))


def gas_mask(po, ol, gm, x, y, z):
    """A rubber gas mask hanging by its head harness: origin at the hook, face toward -Y."""
    mk = mark(po, ol, gm)
    hy = 0.0
    po.rb((0, hy - 0.05, -0.15), (0.17, 0.09, 0.19), bev=0.035)                       # face piece
    po.rb((0, hy - 0.06, -0.225), (0.115, 0.09, 0.075), bev=0.025)                    # chin / cheeks
    for sx in (-0.047, 0.047):                                                        # two lenses
        po.cyl((sx, hy - 0.092, -0.115), (sx, hy - 0.103, -0.115), 0.042, 0.04, segs=14)
        gm.cyl((sx, hy - 0.103, -0.115), (sx, hy - 0.107, -0.115), 0.034, segs=14)
    ol.cyl((0.0, hy - 0.10, -0.215), (0.0, hy - 0.185, -0.215), 0.046, 0.044, segs=14)  # filter canister
    gm.cyl((0.0, hy - 0.185, -0.215), (0.0, hy - 0.19, -0.215), 0.034, segs=12)
    gm.cyl((0.0, hy - 0.10, -0.215), (0.0, hy - 0.112, -0.215), 0.052, segs=14)       # its collar
    po.cyl((0.0, hy - 0.098, -0.176), (0.0, hy - 0.108, -0.176), 0.016, segs=8)       # speech diaphragm
    for sx in (-1, 1):                                                                # harness straps to the hook
        mk2 = mark(po)
        po.box((0, 0, 0.0), (0.016, 0.006, 0.20))
        xform(mk2, Matrix.Translation((sx * 0.045, hy - 0.05, -0.04)) @ Matrix.Rotation(math.radians(-sx * 22), 4, "Y"))
        po.box((sx * 0.085, hy - 0.05, -0.105), (0.014, 0.006, 0.07))
    po.rb((0, hy - 0.03, 0.0), (0.075, 0.02, 0.016), bev=0.003)                       # the harness crown
    xform(mk, Matrix.Translation((x, y, z)))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    ZS = p["shelf_z"]
    SX, SW, H = p["shelf_x"], p["shelf_w"], p["height"]
    D = 0.5

    gr, kr, bl, ol, wh = M(0.5), M(0.5), M(0.5), M(0.5), M(0.5)
    rd, po, gm = M(0.5), M(0.5), M(0.5)
    all_ = (gr, kr, bl, ol, wh, rd, po, gm)
    base = mark(*all_)

    # ---- the shelving ---------------------------------------------------------------------------------------
    xs = [SX - SW / 2 + 0.0225 + k * (SW - 0.045) / 3 for k in range(4)]
    for x in xs:
        for y in (-D / 2 + 0.0225, D / 2 - 0.0225):
            gr.rb((x, y, H / 2), (0.045, 0.045, H), bev=0.003)
            gm.cyl((x, y, 0.0), (x, y, 0.012), 0.026, segs=8)                       # feet
    for zt in ZS:
        for b in range(3):
            xc = (xs[b] + xs[b + 1]) / 2
            wd = xs[b + 1] - xs[b] - 0.045
            gr.box((xc, 0.0, zt - 0.0125), (wd + 0.04, D - 0.01, 0.025))
            gr.box((xc, -D / 2 + 0.0225, zt - 0.045), (wd + 0.045, 0.012, 0.07))   # front beam
            gr.box((xc, D / 2 - 0.0225, zt - 0.045), (wd + 0.045, 0.012, 0.07))    # back beam
    for zt in (ZS[-1] + 0.20,):
        gr.rb((SX, -D / 2 + 0.0225, zt), (SW, 0.04, 0.04), bev=0.003)                # top rails
        gr.rb((SX, D / 2 - 0.0225, zt), (SW, 0.04, 0.04), bev=0.003)
        for x in (xs[0], xs[-1]):
            gr.rb((x, 0.0, zt), (0.04, D - 0.09, 0.04), bev=0.003)
    for b in range(3):                                                                # back diagonal braces
        xc = (xs[b] + xs[b + 1]) / 2
        L = math.hypot(xs[b + 1] - xs[b], 2.0)
        ang = math.atan2(xs[b + 1] - xs[b], 2.0)
        mk = mark(gr)
        gr.box((0, 0, 0), (0.025, 0.006, L))
        xform(mk, Matrix.Translation((xc, WALL - 0.0035, 1.1)) @ Matrix.Rotation(-ang, 4, "Y"))

    # ---- floor shelf: blue drums and a stack of cases ---------------------------------------------------------
    z1 = ZS[0]
    for i in range(5):
        drum(bl, po, SX - 0.95 + 0.372 * i, -0.01 + 0.012 * ((i * 3) % 3 - 1), z1)
    kraft_case(kr, po, wh, SX + 0.89, 0.0, z1, w=0.42, d=0.36, h=0.25, yaw=math.radians(2))
    kraft_case(kr, po, wh, SX + 0.90, 0.0, z1 + 0.25, w=0.42, d=0.36, h=0.25, yaw=math.radians(-3), label=False)

    # ---- second shelf: kraft ration cases, two high -----------------------------------------------------------
    z2 = ZS[1]
    for i in range(5):
        xk = SX - 0.93 + 0.455 * i
        kraft_case(kr, po, wh, xk, 0.0, z2, yaw=math.radians((i * 5) % 7 - 3), label=(i != 3))
        if i != 3:
            kraft_case(kr, po, wh, xk + 0.004, 0.0, z2 + 0.26, yaw=math.radians((i * 3) % 5 - 2), label=(i % 2 == 0))
    kraft_case(kr, po, wh, SX + 0.89, 0.0, z2 + 0.0, w=0.40, d=0.34, h=0.20, yaw=math.radians(90), label=True)

    # ---- third shelf: ammo cans -------------------------------------------------------------------------------
    z3 = ZS[2]
    k = 0
    for i in range(7):
        for ry in (-0.115, 0.115):
            xx = SX - 0.96 + 0.32 * i
            ammo_can(ol, gm, xx, ry, z3, math.radians(((k * 7) % 5 - 2) * 0.8))
            if i in (0, 1, 3, 4, 6) and (i + (ry > 0)) % 2 == 0:
                ammo_can(ol, gm, xx + 0.004, ry, z3 + 0.18, math.radians(((k * 3) % 5 - 2) * 0.8))
            k += 1

    # ---- fourth shelf: more ammo, flat cases, a long tube ------------------------------------------------------
    z4 = ZS[3]
    for i in range(3):
        kraft_case(kr, po, wh, SX - 0.95 + 0.43 * i, 0.0, z4, w=0.40, d=0.34, h=0.20, yaw=math.radians(i * 2 - 2), label=(i == 1))
    ammo_can(ol, gm, SX + 0.60, 0.115, z4)
    ammo_can(ol, gm, SX + 0.60, -0.115, z4)
    ammo_can(ol, gm, SX + 0.90, 0.115, z4, math.radians(2))
    ammo_can(ol, gm, SX + 0.90, -0.115, z4)

    # ---- the white medical cabinet, wall-hung, to the right ---------------------------------------------------
    mx, mz, mw, md, mh = SX + SW / 2 + 0.07 + 0.30, 1.50, 0.58, 0.20, 0.74
    wh.rb((mx, WALL - md / 2, mz), (mw, md, mh), bev=0.008)
    fy = WALL - md
    wh.rb((mx, fy - 0.004, mz), (mw - 0.04, 0.010, mh - 0.04), bev=0.003)             # the door
    gm.box((mx, fy - 0.0105, mz), (0.002, 0.001, mh - 0.06))                          # seam shadow
    for sz in (-0.28, 0.28):
        gm.cyl((mx - mw / 2 + 0.012, fy - 0.007, mz + sz), (mx - mw / 2 + 0.012, fy - 0.007, mz + sz + 0.07), 0.007, segs=6)
    gm.rb((mx + mw / 2 - 0.06, fy - 0.015, mz), (0.014, 0.014, 0.12), bev=0.002)       # lever handle
    gm.cyl((mx + mw / 2 - 0.06, fy - 0.009, mz + 0.14), (mx + mw / 2 - 0.06, fy - 0.0125, mz + 0.14), 0.014, segs=10)
    c = 0.085
    cross = [(-c / 3, c), (c / 3, c), (c / 3, c / 3), (c, c / 3), (c, -c / 3), (c / 3, -c / 3),
             (c / 3, -c), (-c / 3, -c), (-c / 3, -c / 3), (-c, -c / 3), (-c, c / 3), (-c / 3, c / 3)]
    rd.prism(cross, (mx, fy - 0.0092, mz + 0.02), (1, 0, 0), (0, 0, 1), 0.0012, w=(0, 1, 0))
    wh.box((mx, fy - 0.0092, mz - 0.20), (0.26, 0.002, 0.05))                          # a plain label field
    gm.box((mx, fy - 0.0105, mz - 0.20), (0.23, 0.0005, 0.035))
    wh.rb((mx, WALL - md / 2, mz + mh / 2 + 0.005), (mw + 0.01, md + 0.01, 0.014), bev=0.003)   # cornice

    # ---- the hook rails at the left end -------------------------------------------------------------------------
    rx0, rx1 = SX - SW / 2 - 0.70, SX - SW / 2 - 0.08
    rxc = (rx0 + rx1) / 2
    for zr in (1.95, 1.34):
        gr.rb((rxc, WALL - 0.014, zr), (rx1 - rx0, 0.028, 0.04), bev=0.003)
    cols = (rxc - 0.165, rxc + 0.165)
    for cx in cols:
        hook(gm, cx, WALL - 0.028, 1.95 - 0.01)
        hook(gm, cx, WALL - 0.028, 1.34 - 0.01)
        plate_carrier(ol, gm, po, cx, WALL - 0.075, 1.968 - 0.0)
    for i, cx in enumerate(cols):
        gas_mask(po, ol, gm, cx + 0.005 * (1 - 2 * i), WALL - 0.065, 1.38)

    # shift the whole run so it is centred on x = 0
    xform(base, Matrix.Translation((OX, 0, 0)))

    # ---- objects --------------------------------------------------------------------------------------------------
    gr.to_object(f"{n}_Graphite", col, bk.graphite(), root)
    kr.to_object(f"{n}_Kraft", col, bk.kraft(), root)
    bl.to_object(f"{n}_Drums", col, bk.drum_blue(), root)
    ol.to_object(f"{n}_Olive", col, bk.olive(), root)
    wh.to_object(f"{n}_White", col, bk.white(), root)
    rd.to_object(f"{n}_Red", col, bk.red(), root)
    po.to_object(f"{n}_Polymer", col, bk.polymer(), root)
    gm.to_object(f"{n}_Gunmetal", col, bk.gunmetal(), root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
