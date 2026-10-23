"""Armory security station: a graphite desk 2.4 x 0.8 m (right-hand drawer pedestal, left open for the
chair), a 3 x 2 bank of thin 27 inch monitors on a graphite wall-mount frame (each screen a 2 x 2
camera-feed grid in the shared dim screen material), a keyboard, mouse, PTZ joystick, a radio with its
handset in a cradle, and a black mesh task chair pushed in under the desk. Fixed set dressing.
Origin: desk centre on the floor. The BACK is the wall plane at y = +0.40 (desk back edge, monitor frame);
the room is -Y; the chair stands at y -0.05 .. -0.66."""
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

NAME = "ArmorySecurity"

P = dict(
    name=NAME,
    desk=(2.4, 0.8),
    desk_z=0.74,
    chair_x=-0.20,
    chair_yaw=6.0,
)

WALL = 0.40


def monitor(po, gm, scr, led, cx, cz):
    """A thin 27 inch monitor on a wall arm: front plane at y = 0.29."""
    po.rb((cx, 0.298, cz), (0.626, 0.012, 0.372), bev=0.0035)                      # bezel / panel
    po.rb((cx, 0.316, cz + 0.004), (0.56, 0.026, 0.30), bev=0.004, taper=(0.82, 0.96))   # back housing
    for sx in (-1, 1):                                                              # four feed tiles
        for sz in (-1, 1):
            scr.box((cx + sx * 0.1495, 0.2885, cz + sz * 0.0875 + 0.004), (0.2985, 0.0014, 0.1695))
    led.box((cx + 0.285, 0.2895, cz - 0.1735), (0.006, 0.001, 0.003))              # power light
    for sx in (-0.15, 0.15):                                                        # arm tabs to the frame
        gm.rb((cx + sx, 0.347, cz + 0.004), (0.07, 0.032, 0.05), bev=0.003)


def chair(gr, po, fe, gm, cx, cy, yaw):
    """Mesh task chair facing +Y, origin at the foot of the gas lift."""
    mk = mark(gr, po, fe, gm)
    # five-star base with casters
    for k in range(5):
        mk2 = mark(po, gm)
        po.rb((0.15, 0, 0.082), (0.31, 0.050, 0.036), bev=0.004, taper=(1.0, 0.7))
        gm.cyl((0.27, 0, 0.026), (0.27, 0, 0.060), 0.011, segs=8)                    # caster stem
        po.cyl((0.27, -0.012, 0.027), (0.27, 0.012, 0.027), 0.027, segs=10)          # caster wheel
        xform(mk2, Matrix.Rotation(math.radians(18 + 72 * k), 4, "Z"))
    po.cyl((0, 0, 0.065), (0, 0, 0.10), 0.055, 0.04, segs=14)
    gm.cyl((0, 0, 0.10), (0, 0, 0.36), 0.024, segs=12)                               # gas lift
    po.cyl((0, 0, 0.10), (0, 0, 0.26), 0.037, 0.034, segs=12)                        # telescoping cover
    po.rb((0, 0.0, 0.372), (0.20, 0.24, 0.05), bev=0.008)                            # tilt mechanism
    # seat: moulded shell + mesh pad + waterfall front
    po.rb((0, 0.0, 0.412), (0.50, 0.50, 0.034), bev=0.01)
    fe.rb((0, 0.0, 0.440), (0.45, 0.45, 0.030), bev=0.012)
    po.rb((0, 0.255, 0.425), (0.50, 0.03, 0.05), bev=0.012)
    po.rb((0, -0.255, 0.425), (0.50, 0.03, 0.05), bev=0.012)
    # back: the spine, a frame, the mesh and a lumbar bar
    bk_t = math.radians(7)
    mk3 = mark(po, fe, gr, gm)
    po.rb((0, -0.265, 0.55), (0.05, 0.035, 0.30), bev=0.006, rot=(0, "x"))
    for sx in (-1, 1):
        po.rb((sx * 0.2475, -0.285, 0.78), (0.028, 0.026, 0.60), bev=0.008, rot=(math.radians(-sx * 2.4), "y"))
    po.rb((0, -0.285, 1.085), (0.46, 0.026, 0.032), bev=0.008)
    po.rb((0, -0.285, 0.485), (0.52, 0.026, 0.034), bev=0.008)
    fe.rb((0, -0.285, 0.785), (0.47, 0.012, 0.57), bev=0.005, taper=(0.9, 1.0))
    po.rb((0, -0.268, 0.69), (0.40, 0.020, 0.07), bev=0.008)                          # lumbar
    for sz in (0.62, 0.87):                                                            # frame cross-ties behind the mesh
        po.rb((0, -0.298, sz), (0.46 - 0.04 * (sz - 0.6), 0.012, 0.016), bev=0.003)
    xform(mk3, rot_about((0, -0.25, 0.43), "X", bk_t))
    # arms: post, pad (the pads stay under the desk's 0.70 underside)
    for sx in (-1, 1):
        po.rb((sx * 0.275, 0.0, 0.54), (0.026, 0.05, 0.20), bev=0.004)
        po.rb((sx * 0.275, 0.02, 0.652), (0.065, 0.26, 0.032), bev=0.008)
        gm.rb((sx * 0.275, 0.0, 0.425), (0.012, 0.06, 0.03), bev=0.002)
    xform(mk, Matrix.Translation((cx, cy, 0)) @ Matrix.Rotation(math.radians(yaw), 4, "Z"))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    DW, DD = p["desk"]
    DZ = p["desk_z"]

    gr, st, po, fe, gm = M(0.5), M(0.5), M(0.5), M(0.2), M(0.5)
    scr, led = M(0.5), M(0.5)

    # ---- desk ---------------------------------------------------------------------------------------
    gr.rb((0, 0, DZ - 0.02), (DW, DD, 0.04), bev=0.004)
    st.box((0, -DD / 2 + 0.0005, DZ - 0.02), (DW - 0.01, 0.001, 0.036))                # stainless nosing strip
    hw = DW / 2
    gr.rb((-hw + 0.04, 0.0, 0.35), (0.04, DD - 0.06, 0.70), bev=0.003)               # left end panel
    gr.rb((hw - 0.04, 0.0, 0.35), (0.04, DD - 0.06, 0.70), bev=0.003)                # right end panel
    gr.rb((0.60, 0.0, 0.35), (0.02, DD - 0.06, 0.70), bev=0.003)                      # pedestal divider
    gr.box((0.875, 0.35, 0.35), (0.53, 0.02, 0.70))                                    # pedestal back
    gr.box((0.875, 0.0, 0.075), (0.53, DD - 0.10, 0.03))                                # pedestal floor
    gr.box((0.875, 0.0, 0.68), (0.53, DD - 0.10, 0.03))
    for i in range(3):                                                                # three drawers
        zc = 0.19 + i * 0.205
        gr.rb((0.875, -DD / 2 + 0.03, zc), (0.54, 0.022, 0.19), bev=0.003)
        st.rb((0.875, -DD / 2 + 0.0095, zc + 0.04), (0.30, 0.016, 0.014), bev=0.003)
        for sx in (-0.14, 0.14):
            st.box((0.875 + sx, -DD / 2 + 0.019, zc + 0.04), (0.014, 0.012, 0.014))
    gr.rb((-0.28, 0.355, 0.54), (1.74, 0.02, 0.32), bev=0.003)                        # modesty panel (back)
    po.rb((-0.28, 0.27, 0.665), (1.5, 0.12, 0.03), bev=0.003)                          # cable tray
    for sx in (-1, 1):                                                                # levelling feet
        for xx in (-hw + 0.04, hw - 0.04):
            po.cyl((xx, sx * (DD / 2 - 0.08), 0.0), (xx, sx * (DD / 2 - 0.08), 0.012), 0.03, segs=10)

    # ---- monitor wall -------------------------------------------------------------------------------
    pitch = 0.635
    rows = [1.135, 1.135 + 0.382]
    zlo, zhi = rows[0] - 0.205, rows[1] + 0.205
    for xp in (-1.0, -0.3175, 0.3175, 1.0):
        gr.rb((xp, WALL - 0.02, (zlo + zhi) / 2), (0.04, 0.04, zhi - zlo), bev=0.003)
    for zp in (zlo + 0.02, (rows[0] + rows[1]) / 2, zhi - 0.02):
        gr.rb((0, WALL - 0.02, zp), (2.04, 0.04, 0.04), bev=0.003)
    for cz in rows:
        for c in (-1, 0, 1):
            monitor(po, gm, scr, led, c * pitch, cz)
    po.rb((0, WALL - 0.025, zhi + 0.035), (2.04, 0.05, 0.06), bev=0.004)              # cable duct on top
    po.rb((-1.06, WALL - 0.025, (zlo + zhi) / 2 - 0.2), (0.06, 0.05, 0.9), bev=0.004)  # and down the side

    # ---- on the desk ----------------------------------------------------------------------------------
    kz = DZ
    mk = mark(po)
    po.rb((0, 0, 0.009), (0.45, 0.15, 0.018), bev=0.003)                              # keyboard
    for r in range(4):
        for k in range(14):
            po.box(((k - 6.5) * 0.0304, 0.050 - r * 0.0295, 0.0215), (0.027, 0.0245, 0.007))
    for kx, kw in ((-0.185, 0.03), (-0.150, 0.03), (-0.115, 0.03), (0.0, 0.17), (0.115, 0.03), (0.150, 0.03), (0.185, 0.03)):
        po.box((kx, 0.050 - 4 * 0.0295, 0.0215), (kw, 0.0245, 0.007))
    xform(mk, Matrix.Translation((-0.15, -0.12, kz)) @ rot_about((0, -0.07, 0), "X", math.radians(4)))
    po.rb((0.17, -0.11, kz + 0.014), (0.062, 0.104, 0.028), bev=0.012, taper=(0.82, 0.85))   # mouse
    st.box((0.17, -0.12, kz + 0.0285), (0.004, 0.032, 0.001))
    # PTZ joystick desk
    jx, jy = 0.37, -0.10
    po.rb((jx, jy, kz + 0.016), (0.20, 0.17, 0.032), bev=0.006, taper=(1.0, 0.8))
    gm.cyl((jx - 0.03, jy + 0.02, kz + 0.032), (jx - 0.03, jy + 0.02, kz + 0.10), 0.0095, segs=10)
    po.sphere((jx - 0.03, jy + 0.02, kz + 0.108), 0.024, segs=12, rings=8)
    for i in range(4):
        st.cyl((jx + 0.03 + 0.024 * (i % 2), jy - 0.01 + 0.03 * (i // 2), kz + 0.032),
               (jx + 0.03 + 0.024 * (i % 2), jy - 0.01 + 0.03 * (i // 2), kz + 0.038), 0.0085, segs=8)
    led.box((jx + 0.075, jy - 0.065, kz + 0.0325), (0.012, 0.004, 0.001))
    # the radio: a base unit, and the handset in a cradle on a short post, joined by a coiled cord
    rx, ry = -0.98, 0.17
    po.rb((rx, ry, kz + 0.035), (0.26, 0.17, 0.07), bev=0.005)
    st.rb((rx, ry - 0.0855, kz + 0.035), (0.24, 0.003, 0.05), bev=0.001)
    for sx in (-0.07, 0.01):
        gm.cyl((rx + sx, ry - 0.087, kz + 0.035), (rx + sx, ry - 0.100, kz + 0.035), 0.014, segs=12)
    led.box((rx + 0.085, ry - 0.0875, kz + 0.046), (0.03, 0.001, 0.005))
    gm.cyl((rx + 0.11, ry + 0.06, kz + 0.07), (rx + 0.115, ry + 0.07, kz + 0.40), 0.0045, segs=6)   # antenna
    gm.cyl((rx + 0.115, ry + 0.07, kz + 0.40), (rx + 0.116, ry + 0.07, kz + 0.41), 0.007, segs=6)
    cx_, cy_ = -0.70, 0.20
    po.rb((cx_, cy_, kz + 0.006), (0.12, 0.10, 0.012), bev=0.003)
    po.rb((cx_, cy_ + 0.035, kz + 0.11), (0.09, 0.02, 0.20), bev=0.004)
    po.rb((cx_ - 0.035, cy_ + 0.01, kz + 0.07), (0.012, 0.05, 0.12), bev=0.002)
    po.rb((cx_ + 0.035, cy_ + 0.01, kz + 0.07), (0.012, 0.05, 0.12), bev=0.002)
    mk = mark(po, gm, st)                                                             # handset
    po.rb((0, 0, 0.09), (0.052, 0.038, 0.18), bev=0.008, taper=(0.85, 1.0))
    po.rb((0, 0, 0.17), (0.058, 0.044, 0.05), bev=0.008)
    gm.rb((0, -0.0225, 0.115), (0.034, 0.005, 0.034), bev=0.001)                      # push to talk
    st.box((0, -0.0225, 0.165), (0.03, 0.002, 0.012))
    xform(mk, Matrix.Translation((cx_, cy_ - 0.002, kz + 0.025)))
    pts = []
    N = 44
    for k in range(N):
        t = k / (N - 1)
        x0 = cx_ - 0.05 - 0.16 * t
        pts.append(Vector((x0, cy_ + 0.012 * math.sin(2 * math.pi * 6 * t) * min(1, t * 8, (1 - t) * 8),
                           kz + 0.045 + 0.012 * math.cos(2 * math.pi * 6 * t) * min(1, t * 8, (1 - t) * 8))))
    po.sweep(pts, [0.0028] * N, segs=4)

    # ---- the chair ---------------------------------------------------------------------------------------
    chair(gr, po, fe, gm, p["chair_x"], -0.36, p["chair_yaw"])

    # ---- objects --------------------------------------------------------------------------------------------
    gr.to_object(f"{n}_Graphite", col, bk.graphite(), root)
    st.to_object(f"{n}_Stainless", col, bk.stainless(), root)
    po.to_object(f"{n}_Polymer", col, bk.polymer(), root)
    fe.to_object(f"{n}_Mesh", col, bk.felt(), root)
    gm.to_object(f"{n}_Gunmetal", col, bk.gunmetal(), root)
    scr.to_object(f"{n}_Screens", col, bk.screen(), root)
    led.to_object(f"{n}_LED", col, bk.led(), root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
