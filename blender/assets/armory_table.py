"""Armory layout table: the library reading table's cold twin. A 2.4 x 1.0 m brushed-stainless top at
0.92 m on a graphite frame, a lower shelf of olive ammo cans lit from beneath by a cold LED strip,
a black rubber bench mat on the top with an open hard rifle case (felt foam with cut-outs), a
cleaning rod, a torque driver, punches, hex keys, magazines, a solvent bottle. Everything on it is
fixed set dressing. Origin: floor centre; the long side faces -Y (both long sides are finished:
it stands in the middle of the room)."""
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

NAME = "ArmoryTable"

P = dict(
    name=NAME,
    size=(2.4, 1.0),
    top_z=0.92,
)

Z0 = 0.924   # top of the bench mat


def foam_block(m, x0, x1, y0, y1, zb, zt, cavs, flip=False):
    """A foam slab with rectangular cut-outs: cavs = [(x0, x1, y0, y1, level)], as stepped boxes.
    level = the cavity floor (cut from the top); flip=True: the cavity ceiling (cut from the bottom)."""
    def cl(v, lo, hi):
        return max(lo, min(hi, v))
    xs = sorted({x0, x1, *[cl(c[i], x0, x1) for c in cavs for i in (0, 1)]})
    ys = sorted({y0, y1, *[cl(c[i], y0, y1) for c in cavs for i in (2, 3)]})
    for xa, xb in zip(xs, xs[1:]):
        if xb - xa < 1e-4:
            continue
        runs = []
        for ya, yb in zip(ys, ys[1:]):
            if yb - ya < 1e-4:
                continue
            xm, ym = (xa + xb) / 2, (ya + yb) / 2
            hs = [c[4] for c in cavs if c[0] < xm < c[1] and c[2] < ym < c[3]]
            h = (max(hs) if hs else zb) if flip else (min(hs) if hs else zt)
            if runs and abs(runs[-1][2] - h) < 1e-6:
                runs[-1][1] = yb
            else:
                runs.append([ya, yb, h])
        for ya, yb, h in runs:
            lo, hi = (h, zt) if flip else (zb, h)
            m.box(((xa + xb) / 2, (ya + yb) / 2, (lo + hi) / 2), (xb - xa, yb - ya, hi - lo))


def ammo_can(m_ol, m_gm, cx, cy, z, yaw=0.0):
    """M2A1-pattern can, lid on top: 0.30 x 0.15 x 0.18."""
    mk = mark(m_ol, m_gm)
    m_ol.rb((0, 0, 0.09), (0.30, 0.15, 0.18), bev=0.004)
    m_ol.box((0, 0, 0.165), (0.306, 0.156, 0.016))                       # lid band
    m_ol.box((0, 0, 0.1655), (0.28, 0.13, 0.017))                        # raised lid panel
    for sx in (-0.085, 0.085):                                           # stamped ribs on the long faces
        m_ol.box((sx, -0.0765, 0.085), (0.012, 0.003, 0.10))
        m_ol.box((sx, 0.0765, 0.085), (0.012, 0.003, 0.10))
    m_gm.box((0, -0.0795, 0.152), (0.036, 0.007, 0.040))                 # latch
    m_gm.box((0, -0.0825, 0.122), (0.02, 0.005, 0.014))
    m_gm.box((0, 0, 0.1795), (0.13, 0.016, 0.006))                       # carry handle: bar and two stubs
    for sx in (-0.07, 0.07):
        m_gm.box((sx, 0, 0.1745), (0.012, 0.016, 0.014))
    xform(mk, Matrix.Translation((cx, cy, z)) @ Matrix.Rotation(yaw, 4, "Z"))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    W, D = p["size"]
    H = p["top_z"]

    st, gr, ol = M(0.5), M(0.5), M(0.5)
    po, fe, gm, led = M(0.5), M(0.2), M(0.5), M(0.5)

    # ---- the table -------------------------------------------------------------------------------
    st.rb((0, 0, H - 0.02), (W, D, 0.04), bev=0.005)                              # stainless top
    gr.box((0, 0, 0.87), (W - 0.08, D - 0.08, 0.02))                              # underside: a shadow line
    lx, ly = W / 2 - 0.12, D / 2 - 0.10
    for sx in (-1, 1):
        for sy in (-1, 1):
            gr.rb((sx * lx, sy * ly, 0.45), (0.06, 0.06, 0.82 - 0.04 + 0.04), bev=0.003)   # legs (0.04 .. 0.86)
            po.cyl((sx * lx, sy * ly, 0.0), (sx * lx, sy * ly, 0.03), 0.032, segs=14)       # levelling feet
            st.cyl((sx * lx, sy * ly, 0.03), (sx * lx, sy * ly, 0.04), 0.012, segs=10)
        gr.rb((sx * lx, 0, 0.81), (0.045, 2 * ly - 0.06, 0.10), bev=0.003)         # top aprons
        gr.rb((0, sx * ly, 0.81), (2 * lx - 0.06, 0.045, 0.10), bev=0.003)
        gr.rb((sx * lx, 0, 0.20), (0.045, 2 * ly - 0.06, 0.04), bev=0.003)         # shelf rails
        gr.rb((0, sx * ly, 0.20), (2 * lx - 0.06, 0.045, 0.04), bev=0.003)
        gr.box((0, sx * (ly - 0.005), 0.255), (2 * lx - 0.06, 0.012, 0.03))        # shelf lips (front and back)
        gr.box((sx * (lx - 0.005), 0, 0.255), (0.012, 2 * ly - 0.06, 0.03))
        st.box((sx * lx, 0, 0.815), (0.047, 0.24, 0.045))                          # stainless badge plates on the ends
        gr.rb((0.0, sx * (ly + 0.016), 0.81), (1.30, 0.012, 0.085), bev=0.002)     # shallow drawer fronts, both long sides
        st.rb((0.0, sx * (ly + 0.034), 0.81), (0.30, 0.016, 0.014), bev=0.003)      # pull bar
    gr.rb((0, 0, 0.23), (2 * lx - 0.04, 2 * ly - 0.04, 0.02), bev=0.003)          # shelf panel (top at 0.24)
    for sy in (-0.20, 0.20):                                                       # cold strips under the shelf
        led.box((0, sy, 0.216), (2.0, 0.018, 0.006))

    # ---- ammo cans on the shelf --------------------------------------------------------------------
    zs = 0.24
    layout = [(-0.90, -0.26, 0), (-0.59, -0.26, 0), (-0.28, -0.26, 0), (-0.90, 0.26, 0), (-0.59, 0.26, 0),
              (-0.89, -0.26, 1), (-0.60, -0.26, 1), (-0.90, 0.26, 1),
              (0.55, -0.26, 0), (0.86, -0.26, 0), (0.55, 0.26, 0), (0.86, 0.26, 0), (0.70, -0.26, 1),
              (0.70, 0.26, 1)]
    for i, (cx, cy, lvl) in enumerate(layout):
        yaw = math.radians(((i * 7) % 5 - 2) * 0.9)
        ammo_can(ol, gm, cx, cy, zs + lvl * 0.18, yaw)
    ammo_can(ol, gm, 0.12, -0.26, zs, math.radians(-2))        # the odd ones out
    ammo_can(ol, gm, 0.16, 0.22, zs, math.radians(90))

    # ---- the rubber mat and the rifle case ------------------------------------------------------------
    po.rb((-0.15, 0.0, H + 0.002), (1.70, 0.80, 0.004), bev=0.0015)
    for ry in (-0.34, 0.34):                      # printed edge ribs of the mat
        po.box((-0.15, ry, H + 0.0045), (1.62, 0.006, 0.001))
    cx0, cy0 = -0.38, 0.14
    cmk = mark(po, fe, gm)
    CL, CW, CH = 1.10, 0.34, 0.10                  # case outer: length x, width y, base height z
    t = 0.012
    po.rb((0, 0, t / 2), (CL, CW, t), bev=0.003)                               # floor
    po.rb((0, -CW / 2 + t / 2, CH / 2), (CL, t, CH), bev=0.003)                # front wall
    po.rb((0, CW / 2 - t / 2, CH / 2), (CL, t, CH), bev=0.003)                 # back wall
    for sx in (-1, 1):
        po.rb((sx * (CL / 2 - t / 2), 0, CH / 2), (t, CW - 2 * t, CH), bev=0.003)
    for rx in (-0.36, 0.0, 0.36):                                              # moulded ribs on the front wall
        po.box((rx, -CW / 2 - 0.002, CH * 0.5), (0.20, 0.004, 0.05))
    po.rb((0, -CW / 2 - 0.008, 0.07), (0.16, 0.016, 0.03), bev=0.003)         # carry handle bracket
    cavs = [(-0.52, 0.52, 0.035, 0.105, 0.040), (-0.30, -0.06, 0.020, 0.125, 0.040),
            (-0.52, 0.00, -0.095, -0.020, 0.040), (0.30, 0.46, 0.050, 0.110, 0.030),
            (0.30, 0.46, -0.060, 0.030, 0.045)]
    for mx in (0.12, 0.19, 0.26):
        cavs.append((mx - 0.0275, mx + 0.0275, -0.125, -0.015, 0.030))
    foam_block(fe, -CL / 2 + t, CL / 2 - t, -CW / 2 + t, CW / 2 - t, t, 0.088, cavs)
    for sx in (-0.42, 0.0, 0.42):                                             # latches
        gm.rb((sx, -CW / 2 - 0.010, CH - 0.012), (0.045, 0.012, 0.035), bev=0.002)
        gm.box((sx, -CW / 2 - 0.0165, CH + 0.002), (0.02, 0.003, 0.012))
    for sx in (-0.40, 0.40):                                                   # hinge knuckles
        gm.cyl((sx - 0.04, CW / 2 + 0.005, CH), (sx + 0.04, CW / 2 + 0.005, CH), 0.008, segs=10)
    # lid, built closed on top of the base and swung open about the back rim
    lmk = mark(po, fe, gm)
    LH = 0.062
    zc = CH
    po.rb((0, 0, zc + LH - t / 2), (CL, CW, t), bev=0.003)
    po.rb((0, -CW / 2 + t / 2, zc + LH / 2), (CL, t, LH), bev=0.003)
    po.rb((0, CW / 2 - t / 2, zc + LH / 2), (CL, t, LH), bev=0.003)
    for sx in (-1, 1):
        po.rb((sx * (CL / 2 - t / 2), 0, zc + LH / 2), (t, CW - 2 * t, LH), bev=0.003)
    for rx in (-0.30, 0.30):
        po.box((rx, 0, zc + LH + 0.002), (0.30, 0.20, 0.004))                 # moulded panel on the lid back
    lcav = [(-0.50, -0.20, -0.10, 0.10, 0.012), (-0.12, 0.10, -0.10, 0.10, 0.012), (0.18, 0.30, -0.10, 0.10, 0.012),
            (0.34, 0.50, -0.05, 0.10, 0.012)]
    fz = zc + LH - t - 0.040
    lcav = [(a, b, c, d, fz + 0.022) for a, b, c, d, e in lcav]
    foam_block(fe, -CL / 2 + t, CL / 2 - t, -CW / 2 + t, CW / 2 - t, fz, zc + LH - t, lcav, flip=True)
    xform(lmk, rot_about((0, CW / 2, CH), "X", math.radians(-104)))
    xform(cmk, Matrix.Translation((cx0, cy0, Z0)))

    # ---- tools on the mat -----------------------------------------------------------------------------
    # cleaning rod: T handle, rod, brush
    ry, rz = -0.29, Z0 + 0.009
    gm.cyl((-0.82, ry, rz), (0.05, ry, rz), 0.0045, segs=8)
    po.cyl((-0.82, ry - 0.045, rz), (-0.82, ry + 0.045, rz), 0.0115, segs=10)
    po.cyl((-0.92, ry, rz), (-0.82, ry, rz), 0.0095, segs=10)
    st.cyl((0.05, ry, rz), (0.09, ry, rz), 0.007, 0.0045, segs=8)
    # torque driver
    tx, ty = 0.05, -0.20
    mk = mark(po, gm, st)
    po.cyl((0, 0, 0), (0.115, 0, 0), 0.0185, 0.0165, segs=14)
    st.cyl((0.115, 0, 0), (0.135, 0, 0), 0.0155, segs=14)
    gm.cyl((0.135, 0, 0), (0.30, 0, 0), 0.0055, segs=8)
    gm.cyl((0.30, 0, 0), (0.32, 0, 0), 0.0040, 0.0025, segs=8)
    xform(mk, Matrix.Translation((tx, ty, Z0 + 0.0185)) @ Matrix.Rotation(math.radians(-4), 4, "Z"))
    # three punches, fanned
    for k in range(3):
        mk = mark(gm)
        gm.cyl((0, 0, 0), (0.13, 0, 0), 0.004 + k * 0.0006, 0.0025, segs=8)
        xform(mk, Matrix.Translation((0.46, -0.30 + k * 0.022, Z0 + 0.005)) @ Matrix.Rotation(math.radians(6 - 5 * k), 4, "Z"))
    # hex keys: L shapes
    for k in range(4):
        gm.box((0.22 + k * 0.012, -0.10 - k * 0.0, Z0 + 0.0015), (0.0035, 0.07 + k * 0.012, 0.003))
        gm.box((0.22 + k * 0.012 + 0.025, -0.10 - 0.035 - k * 0.006, Z0 + 0.0015), (0.05, 0.0035, 0.003))
    # two rifle magazines lying on their sides
    for k, (mx, my, ya) in enumerate([(0.43, -0.06, 4), (0.55, 0.06, -3)]):
        mk = mark(po, gm)
        po.rb((-0.066, -0.004, 0.012), (0.072, 0.064, 0.024), bev=0.002, rot=(math.radians(-6), "z"))
        po.rb((0.0, 0, 0.012), (0.072, 0.064, 0.024), bev=0.002)
        po.rb((0.064, 0.006, 0.012), (0.072, 0.064, 0.024), bev=0.002, rot=(math.radians(6), "z"))
        gm.box((0.104, 0.014, 0.012), (0.012, 0.062, 0.0235), rot=(math.radians(6), "z"))
        gm.box((-0.104, -0.010, 0.012), (0.010, 0.066, 0.0245), rot=(math.radians(-6), "z"))
        for j in range(5):
            po.box((-0.05 + j * 0.024, 0.0, 0.0245), (0.004, 0.050, 0.001))
        xform(mk, Matrix.Translation((mx, my, Z0)) @ Matrix.Rotation(math.radians(ya + 90), 4, "Z"))
    # solvent bottle and a folded charcoal rag
    po.cyl((0.88, -0.22, Z0), (0.88, -0.22, Z0 + 0.10), 0.032, 0.03, segs=16)
    po.cyl((0.88, -0.22, Z0 + 0.10), (0.88, -0.22, Z0 + 0.118), 0.0325, 0.012, segs=16)
    gm.cyl((0.88, -0.22, Z0 + 0.118), (0.88, -0.22, Z0 + 0.135), 0.011, segs=12)
    st.cyl((0.88, -0.22, Z0 + 0.0), (0.88, -0.22, Z0 + 0.003), 0.033, segs=16)
    fe.rb((0.82, 0.15, Z0 + 0.007), (0.16, 0.11, 0.014), bev=0.004, rot=(math.radians(12), "z"))
    fe.rb((0.82, 0.15, Z0 + 0.019), (0.12, 0.09, 0.010), bev=0.003, rot=(math.radians(-5), "z"))

    # ---- objects --------------------------------------------------------------------------------------
    st.to_object(f"{n}_Stainless", col, bk.stainless(), root)
    gr.to_object(f"{n}_Graphite", col, bk.graphite(), root)
    ol.to_object(f"{n}_Olive", col, bk.olive(), root)
    po.to_object(f"{n}_Polymer", col, bk.polymer(), root)
    fe.to_object(f"{n}_Felt", col, bk.felt(), root)
    gm.to_object(f"{n}_Gunmetal", col, bk.gunmetal(), root)
    led.to_object(f"{n}_LED", col, bk.led(), root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
