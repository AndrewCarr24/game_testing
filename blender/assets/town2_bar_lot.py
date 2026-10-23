"""The bar's outside (town2_bar.py): the gravel lot (packed ruts, a ragged edge sinking into the
grass), railroad-tie wheel stops, two dark vans nose-out at the porch, three pickups, the pole
sign by the highway (a backlit cabinet, BAR in red neon, a marquee arrow), the utility pole and
its service drop, a dumpster, a propane tank, empties by the back exit; the porch (BAR neon over
the open door, a caged porch light, benches, a cooler, an ice machine); the river deck (picnic
tables, a barrel smoker, festoon lights) and a jon boat at the landing."""
import math
import random

from mathutils import Matrix, Vector

import town2_bar_vehicles as veh
from town2_bar_interior import neon_sign, _bar_item, WARM, _chair
from town2_bar_shell import _beam
import town2_bar_glow as glow

M = "PropsOut"


def gravel(k, P):
    x0, y0, x1, y1 = P["footprint"]
    L, D = P["L"], P["D"]
    rnd = random.Random(41)
    step = 1.0
    nx, ny = int((x1 - x0) / step), int((y1 - y0) / step)
    pd = P["porch_depth"]
    # holes: the building and the porch (raised, skirted), the deck's posts stand in the lot's south strip
    def covered(cx, cy):
        if -L / 2 + 0.05 < cx < L / 2 - 0.05 and -D / 2 + 0.05 < cy < D / 2 - 0.05:
            return True
        if P["porch_x0"] + 0.05 < cx < P["porch_x1"] - 0.05 and -D / 2 - pd + 0.05 < cy < -D / 2:
            return True
        return False
    # ruts: the drive from the highway (west) along the front, into the stalls
    ruts = [((44.0, -13.5), (-20.0, -13.5)), ((44.0, -15.2), (-20.0, -15.2)), ((30.0, -12.0), (18.0, -2.0))]

    def rut(px, py):
        best = 9.0
        for (a, b) in ruts:
            ax, ay = a
            bx, by = b
            dx, dy = bx - ax, by - ay
            t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
            best = min(best, math.hypot(px - ax - t * dx, py - ay - t * dy))
        return best

    def h(px, py):
        e = min(px - x0, x1 - px, py - y0, y1 - py)
        edge = -0.1 * max(0.0, 1 - e / 1.5) ** 1.5
        d = rut(px, py)
        r = -0.035 * math.exp(-(d / 0.3) ** 2)
        return 0.012 * math.sin(px * 1.7) * math.sin(py * 2.3) + r + edge
    import bmesh
    # in 6 m tiles (one lightmap island each: one 73 m island would set the whole atlas' scale)
    T = 6
    for tj in range(0, ny, T):
        for ti in range(0, nx, T):
            bm = bmesh.new()
            V = {}
            for j in range(tj, min(ny, tj + T) + 1):
                for i in range(ti, min(nx, ti + T) + 1):
                    px, py = x0 + i * step, y0 + j * step
                    # a ragged outline: the outer two rings pulled in by a smooth noise
                    ring = min(i, nx - i, j, ny - j)
                    if ring <= 1:
                        rag = (0.5 + 0.5 * math.sin(px * 0.37 + 2.1 * math.sin(py * 0.29)) * math.sin(py * 0.53 + px * 0.11)) * (1.6 if ring == 0 else 0.8)
                        cxm, cym = (x0 + x1) / 2, (y0 + y1) / 2
                        if i == 0 or i == nx or (ring == 1 and i in (1, nx - 1)):
                            px += rag * (1 if px < cxm else -1)
                        if j == 0 or j == ny or (ring == 1 and j in (1, ny - 1)):
                            py += rag * (1 if py < cym else -1)
                    V[(i, j)] = bm.verts.new((px, py, h(px, py)))
            tints = []
            for j in range(tj, min(ny, tj + T)):
                for i in range(ti, min(nx, ti + T)):
                    cx, cy = x0 + (i + 0.5) * step, y0 + (j + 0.5) * step
                    if covered(cx, cy):
                        continue
                    bm.faces.new([V[(i, j)], V[(i + 1, j)], V[(i + 1, j + 1)], V[(i, j + 1)]])
                    d = rut(cx, cy)
                    e = min(cx - x0, x1 - cx, cy - y0, y1 - cy)
                    t = 0.82 + 0.1 * rnd.random()
                    if d < 0.5:
                        t *= 0.78                     # packed, darker in the ruts
                    w = max(0.0, min(1.0, 1 - e / 3.0))
                    c = (t * (1 - 0.2 * w), t * (0.98 - 0.26 * w), t * (0.95 - 0.32 * w))
                    tints.append(c)
            loose = [v for v in bm.verts if not v.link_faces]
            bmesh.ops.delete(bm, geom=loose, context="VERTS")
            if tints:
                k.add(bm, "Gravel", tint=tints, lmw=0.3, vlit=False)
            else:
                bm.free()
    # wheel stops (railroad ties) along the porch front, and a few at the west stalls
    for x in (-5.2, -2.4, 0.8, 3.6, 6.6):
        _tie(k, x, -D / 2 - pd - 0.9, 0.0)
    for y in (-4.0, -0.8, 2.4):
        _tie(k, L / 2 + 5.6, y, 90.0)


def _tie(k, x, y, yaw):
    Mx = Matrix.Translation((x, y, 0.0)) @ Matrix.Rotation(math.radians(yaw), 4, "Z")
    k.box("Deck", (-1.1, -0.11, -0.03), (1.1, 0.11, 0.15), M=Mx, bevel=0.015, tint=(0.35, 0.3, 0.27), lmw=0.15)
    c = Mx @ Vector((0, 0, 0))
    if yaw == 0:
        k.collider(c.x - 1.1, c.y - 0.11, 0.0, c.x + 1.1, c.y + 0.11, 0.15)
    else:
        k.collider(c.x - 0.11, c.y - 1.1, 0.0, c.x + 0.11, c.y + 1.1, 0.15)


def pole_sign(k, P):
    x, y = P["sign"]
    yaw = P["sign_yaw"]
    Ms = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(math.radians(yaw), 4, "Z")
    w = 3.6
    zs0, zs1 = 5.2, 7.0
    # two steel pipe posts on concrete piers
    for s in (-1, 1):
        p = Ms @ Vector((0, s * 1.2, 0))
        k.cyl(M, (p.x, p.y, -0.1), (p.x, p.y, 0.35), 0.3, sides=12, uv=("cell", "concrete"), lmw=0.1)
        k.cyl(M, (p.x, p.y, 0.3), (p.x, p.y, zs1 + 1.6), 0.14, sides=12, uv=("cell", "paint_grey"), lmw=0.15)
        k.collider(p.x - 0.3, p.y - 0.3, 0.0, p.x + 0.3, p.y + 0.3, zs1)
    # the cabinet: a red frame, two backlit faces, BAR in red neon on both
    k.box(M, (-0.22, -w / 2, zs0), (0.22, w / 2, zs1), M=Ms, bevel=0.04, segs=2, uv=("cell", "paint_red"), lmw=0.2)
    for s in (-1, 1):
        k.box(M, (s * 0.225 - 0.003, -w / 2 + 0.12, zs0 + 0.12), (s * 0.225 + 0.003, w / 2 - 0.12, zs1 - 0.12), M=Ms, uv=("cell", "sign_face"), lmw=0.0)
        o = Ms @ Vector((s * 0.29, 0.0, (zs0 + zs1) / 2))
        r = (Ms.to_3x3() @ Vector((0, s, 0)))
        neon_sign(k, tuple(o), tuple(r), (0, 0, 1), 0.9, "BAR", mat=M, power=0.0, backing=False, lights=False, lmw=0.05,
                  tube=0.014, halo=0.2)
        k.light("POINT", tuple(Ms @ Vector((s * 1.2, 0.0, (zs0 + zs1) / 2))), (1.0, 0.2, 0.1), 40.0, radius=0.5)
    # the arrow above it: a yellow board with marquee bulbs along its edge, bent down toward the bar
    arrow = [(-1.9, 0.0), (0.9, 0.0), (0.9, -0.35), (1.9, 0.35), (0.9, 1.05), (0.9, 0.7), (-1.9, 0.7)]
    Ma = Ms @ Matrix.Translation((0.0, 0.0, zs1 + 0.25)) @ Matrix.Rotation(math.radians(-90), 4, "Z") @ Matrix.Rotation(math.radians(90), 4, "X") \
        @ Matrix.Rotation(math.radians(-14), 4, "Z")
    k.prism(M, arrow, -0.08, 0.08, M=Ma, bevel=0.02, uv=("cell", "paint_yellow"), lmw=0.15)
    edge = arrow + [arrow[0]]
    pts = []
    for a, b in zip(edge[:-1], edge[1:]):
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 0.3))
        for i in range(n):
            t = (i + 0.5) / n
            pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    cx = sum(p[0] for p in arrow) / len(arrow)
    cy = sum(p[1] for p in arrow) / len(arrow)
    for (px, py) in pts:
        qx, qy = px + (cx - px) * 0.1, py + (cy - py) * 0.1
        for s in (-1, 1):
            q = Ma @ Vector((qx, qy, s * 0.085))
            k.lathe(M, [(0.0, -0.035), (0.03, -0.02), (0.035, 0.0), (0.02, 0.03), (0.0, 0.035)], sides=6, M=Matrix.Translation(q), uv=("cell", "bulbs_marquee"), lmw=0.0)
            glow.halo(k, tuple(q + (Ma.to_3x3() @ Vector((0, 0, s * 0.02)))), 0.22, "amber", normal=tuple(Ma.to_3x3() @ Vector((0, 0, s))))
    k.light("POINT", tuple(Ma @ Vector((0.0, 0.35, 0.0))), (1.0, 0.62, 0.25), 25.0, radius=1.0)


def utility_pole(k, P):
    x, y = P["pole"]
    top = 9.5
    k.cyl(M, (x, y, -0.5), (x, y, top), 0.15, r1=0.12, sides=10, uv=("cell", "pole_wood"), lmw=0.15)
    k.collider(x - 0.15, y - 0.15, 0.0, x + 0.15, y + 0.15, top)
    k.box(M, (x - 1.2, y - 0.05, top - 0.6), (x + 1.2, y + 0.05, top - 0.48), uv=("cell", "pole_wood"), lmw=0.05)
    for dx in (-1.05, 0.0, 1.05):
        k.cyl(M, (x + dx, y, top - 0.48), (x + dx, y, top - 0.3), 0.04, sides=6, uv=("cell", "glass_green"), lmw=0.0)
    # the transformer can, the cobra-head lamp on its arm (off: dusk-to-dawn, not dusk yet)
    k.lathe(M, [(0.0, 0.0), (0.26, 0.0), (0.27, 0.05), (0.27, 0.85), (0.24, 0.9), (0.0, 0.92)], sides=12, M=Matrix.Translation((x + 0.38, y, top - 2.2)),
            uv=("cell", "paint_grey"), lmw=0.1)
    k.tube(M, [(x, y, 6.2), (x + 0.8, y - 0.6, 6.6), (x + 1.8, y - 1.3, 6.7)], 0.03, sides=6, uv=("cell", "aluminium"), lmw=0.02)
    k.lathe(M, [(0.0, 0.0), (0.16, 0.02), (0.2, 0.08), (0.12, 0.14), (0.0, 0.15)], sides=10,
            M=Matrix.Translation((x + 2.0, y - 1.45, 6.55)) @ Matrix.Rotation(math.radians(90), 4, "Y") @ Matrix.Scale(1.0, 4, (0, 0, 1)), uv=("cell", "aluminium"), lmw=0.02)
    k.lathe(M, [(0.0, 0.0), (0.14, 0.0)], sides=10, M=Matrix.Translation((x + 2.0, y - 1.45, 6.53)), uv=("cell", "sodium" if P.get("yard_light") else "glass_clear"), lmw=0.0,
            cap0=False, cap1=False)
    if P.get("yard_light"):
        k.light("SPOT", (x + 2.0, y - 1.45, 6.4), (1.0, 0.5, 0.15), 260.0, radius=0.1, angle=110.0, blend=0.6, aim=(x + 4.0, y - 3.0, 0.0))
    # wires: the service drop to the east gable, the line out toward the highway (sagging)
    L, D = P["L"], P["D"]
    def sag(a, b, s, n=12):
        a, b = Vector(a), Vector(b)
        return [tuple(a.lerp(b, i / n) + Vector((0, 0, -s * 4 * (i / n) * (1 - i / n)))) for i in range(n + 1)]
    k.tube(M, sag((x, y, top - 1.4), (-L / 2 - 0.1, -2.5, P["plate"] + 0.6), 0.5), 0.008, sides=4, uv=("cell", "plastic_black"), lmw=0.0)
    k.box(M, (-L / 2 - 0.12, -2.6, P["plate"] - 1.8), (-L / 2 - 0.02, -2.4, P["plate"] + 0.7), uv=("cell", "galvanized"), lmw=0.02)
    k.box(M, (-L / 2 - 0.2, -2.75, 1.4), (-L / 2 - 0.02, -2.25, 1.9), bevel=0.01, uv=("cell", "galvanized"), lmw=0.05)
    for wy in (-0.06, 0.06):
        k.tube(M, sag((x - 1.05, y + wy, top - 0.3), (x - 70.0, y + wy - 6.0, top - 0.6), 1.6, 20), 0.007, sides=4, uv=("cell", "plastic_black"), lmw=0.0)
        k.tube(M, sag((x + 1.05, y + wy, top - 0.3), (x + 60.0, y + wy - 2.0, top - 0.4), 1.4, 20), 0.007, sides=4, uv=("cell", "plastic_black"), lmw=0.0)


def back_lot(k, P):
    L, D, f = P["L"], P["D"], P["floor"]
    # the dumpster by the back exit, its lids
    dx, dy = -L / 2 - 3.2, 2.8
    Md = Matrix.Translation((dx, dy, 0)) @ Matrix.Rotation(math.radians(8), 4, "Z")
    k.prism(M, [(-0.95, -1.0), (0.95, -1.0), (0.95, 1.0), (-0.95, 1.0)], 0.12, 1.15, M=Md, bevel=0.03, uv=("cell", "dumpster"), lmw=0.3)
    for s in (-1, 1):
        k.box(M, (-0.97, -1.02 if s < 0 else 0.0, 1.15), (0.97, 0.0 if s < 0 else 1.02, 1.22), M=Md @ Matrix.Rotation(math.radians(4 * s), 4, "Y"), bevel=0.01, uv=("cell", "plastic_black"), lmw=0.1)
    for sx in (-0.8, 0.8):
        for sy in (-0.85, 0.85):
            k.cyl(M, tuple(Md @ Vector((sx, sy, 0.0))), tuple(Md @ Vector((sx, sy, 0.12))), 0.06, sides=8, uv=("cell", "rubber"), lmw=0.02)
    k.collider(dx - 1.1, dy - 1.15, 0.0, dx + 1.1, dy + 1.15, 1.25)
    # the propane tank on its saddles
    px, py = -L / 2 - 2.6, 6.6
    Mp = Matrix.Translation((px, py, 0.75)) @ Matrix.Rotation(math.pi / 2, 4, "Y")
    prof = [(0.0, -0.95), (0.25, -0.9), (0.36, -0.75), (0.4, -0.55), (0.4, 0.55), (0.36, 0.75), (0.25, 0.9), (0.0, 0.95)]
    k.lathe(M, prof, sides=16, M=Mp, uv=("cell", "propane"), lmw=0.3)
    for s in (-0.55, 0.55):
        k.box(M, (px + s - 0.08, py - 0.3, 0.0), (px + s + 0.08, py + 0.3, 0.45), uv=("cell", "concrete"), lmw=0.05)
    k.cyl(M, (px, py, 1.15), (px, py, 1.32), 0.07, sides=8, uv=("cell", "steel_dark"), lmw=0.02)
    k.collider(px - 0.95, py - 0.4, 0.0, px + 0.95, py + 0.4, 1.2)
    # empties by the back exit: kegs, beer crates, a pallet; an old chest freezer
    ex = -L / 2 - 0.7
    for i, (yy, n) in enumerate(((-3.0, 2), (-2.4, 1))):
        for j in range(n):
            k.lathe(M, [(0.0, 0.0), (0.2, 0.0), (0.205, 0.05), (0.2, 0.08), (0.205, 0.5), (0.2, 0.55), (0.12, 0.585), (0.0, 0.59)], sides=14,
                    M=Matrix.Translation((ex - 0.15 * i, yy, j * 0.6)), uv=("cell", "keg"), lmw=0.15)
    for z in range(3):
        k.box(M, (ex - 1.4, -4.6, z * 0.27), (ex - 0.9, -4.2, z * 0.27 + 0.26), bevel=0.01, uv=("cell", "plastic_red"), lmw=0.1)
    for i in range(5):
        k.box(M, (ex - 1.3, -3.95 + i * 0.27, 0.1), (ex - 0.1, -3.95 + i * 0.27 + 0.1, 0.13), uv=("cell", "wood_light"), lmw=0.03)
    for yy in (-3.95, -3.45, -2.95):
        k.box(M, (ex - 1.3, yy, 0.0), (ex - 0.1, yy + 0.09, 0.1), uv=("cell", "wood_light"), lmw=0.03)
    k.collider(ex - 1.45, -4.65, 0.0, ex + 0.25, -2.2, 1.2)


def porch_dressing(k, P):
    L, D, f = P["L"], P["D"], P["floor"]
    yw = -D / 2
    dx = P["door_x"]
    # the front door: open into the room, back against the wall (the doorway stays clear)
    Mdoor = Matrix.Translation((dx + 0.5, yw + 0.25, f + 0.01)) @ Matrix.Rotation(math.radians(-86), 4, "Z")
    k.box("Wood", (-1.0, 0.0, 0.0), (0.0, 0.05, 2.17), M=Mdoor, bevel=0.008, tint=(0.55, 0.3, 0.25), lmw=0.6)
    k.box("Props", (-0.94, -0.06, 0.95), (-0.86, 0.0, 1.05), M=Mdoor, uv=("cell", "brass"), lmw=0.01)
    c = Mdoor @ Vector((-0.5, 0.025, 1.0))
    k.collider(c.x - 0.15, c.y - 0.5, f, c.x + 0.15, c.y + 0.5, f + 2.17)
    # BAR in neon over the door (pink-red on a black backer), the caged porch light
    k.box(M, (dx - 0.7, yw - 0.04, f + 2.44), (dx + 0.7, yw, f + 3.0), uv=("cell", "paint_black"), lmw=0.2)
    neon_sign(k, (dx, yw - 0.09, f + 2.72), (1, 0, 0), (0, 0, 1), 0.4, "BAR", mat=M, power=22.0, backing=False, lmw=0.05, tube=0.009, halo=0.1)
    lx = dx - 1.0
    k.lathe(M, [(0.0, 0.0), (0.07, 0.0), (0.07, 0.03), (0.0, 0.035)], sides=8, M=Matrix.Translation((lx, yw - 0.02, f + 2.2)) @ Matrix.Rotation(math.pi / 2, 4, "X"), uv=("cell", "iron_black"), lmw=0.0)
    k.lathe(M, [(0.0, 0.0), (0.035, 0.02), (0.04, 0.08), (0.0, 0.14)], sides=8, M=Matrix.Translation((lx, yw - 0.1, f + 2.2)) @ Matrix.Rotation(math.pi / 2, 4, "X"), uv=("cell", "bulb"), lmw=0.0)
    k.light("POINT", (lx, yw - 0.18, f + 2.2), WARM, 18.0, radius=0.04)
    glow.halo(k, (lx, yw - 0.16, f + 2.2), 0.4, "warm")
    # BAR in big red neon on the west gable, for the highway (no backer: tubes on the block)
    gx = P["L"] / 2 + 0.06
    for yy in (-1.2, 1.2):
        k.box(M, (gx - 0.06, yy - 0.03, f + 1.55), (gx + 0.02, yy + 0.03, f + 2.95), uv=("cell", "iron_black"), lmw=0.05)
    neon_sign(k, (gx + 0.05, 0.0, f + 2.25), (0, 1, 0), (0, 0, 1), 1.05, "BAR", mat=M, power=0.0, lights=False, backing=False, lmw=0.05,
              tube=0.013, halo=0.18)
    k.light("POINT", (gx + 0.5, 0.0, f + 2.25), (1.0, 0.08, 0.04), 55.0, radius=0.6)
    # benches, a cooler, a sand-bucket ashtray, an ice machine at the east end
    for bx in (-4.0, 2.0):
        by = yw - 0.45
        k.box("Deck", (bx - 0.9, by - 0.2, f + 0.42), (bx + 0.9, by + 0.2, f + 0.47), bevel=0.008, tint=(0.7, 0.7, 0.7), lmw=0.3)
        k.box("Deck", (bx - 0.9, by + 0.17, f + 0.5), (bx + 0.9, by + 0.21, f + 0.85), bevel=0.008, tint=(0.7, 0.7, 0.7), lmw=0.2)
        for sx in (-0.8, 0.8):
            k.box("Deck", (bx + sx - 0.03, by - 0.2, f), (bx + sx + 0.03, by + 0.21, f + 0.42), tint=(0.6, 0.6, 0.6), lmw=0.05)
        k.collider(bx - 0.9, by - 0.2, f, bx + 0.9, by + 0.21, f + 0.47)
    _bar_item(k, "beer", -3.5, yw - 0.45, f + 0.47)
    _bar_item(k, "beer", 2.4, yw - 0.4, f + 0.47)
    cx_ = dx + 1.4
    k.box(M, (cx_ - 0.4, yw - 0.62, f), (cx_ + 0.4, yw - 0.12, f + 0.85), bevel=0.04, segs=2, uv=("cell", "cooler_red"), lmw=0.3)
    k.box(M, (cx_ - 0.38, yw - 0.64, f + 0.6), (cx_ + 0.38, yw - 0.62, f + 0.66), uv=("cell", "chrome"), lmw=0.02)
    k.collider(cx_ - 0.4, yw - 0.62, f, cx_ + 0.4, yw - 0.12, f + 0.85)
    k.lathe(M, [(0.15, 0.0), (0.17, 0.42), (0.18, 0.44)], sides=10, M=Matrix.Translation((dx + 2.2, yw - 0.3, f)), uv=("cell", "paint_red"), lmw=0.05, cap1=False)
    k.lathe(M, [(0.0, 0.4), (0.165, 0.4)], sides=10, M=Matrix.Translation((dx + 2.2, yw - 0.3, f)), uv=("cell", "concrete"), lmw=0.02, cap0=False, cap1=False)
    ix = P["porch_x0"] + 0.7
    k.box(M, (ix - 0.5, yw - 0.85, f), (ix + 0.5, yw - 0.08, f + 1.9), bevel=0.02, uv=("cell", "stainless"), lmw=0.4)
    k.box(M, (ix - 0.4, yw - 0.87, f + 0.3), (ix + 0.4, yw - 0.85, f + 1.2), uv=("cell", "aluminium"), lmw=0.05)
    k.collider(ix - 0.5, yw - 0.85, f, ix + 0.5, yw - 0.08, f + 1.9)


def deck_dressing(k, P):
    D, f = P["D"], P["floor"]
    dx0, dx1, dy1 = P["deck_x0"], P["deck_x1"], P["deck_y1"]
    y0 = D / 2
    rnd = random.Random(13)
    for (tx, ty, a) in ((6.6, 9.4, 0), (9.6, 9.6, 6), (12.4, 9.3, -4)):
        _picnic(k, tx, ty, f, a)
    # the barrel smoker
    sx, sy = dx0 + 0.9, y0 + 0.9
    Ms = Matrix.Translation((sx, sy, f + 0.72)) @ Matrix.Rotation(math.pi / 2, 4, "Y")
    k.lathe(M, [(0.0, -0.45), (0.3, -0.45), (0.3, 0.45), (0.0, 0.45)], sides=14, M=Ms, uv=("cell", "iron_black"), lmw=0.3)
    k.cyl(M, (sx + 0.3, sy, f + 0.95), (sx + 0.3, sy, f + 1.55), 0.05, sides=8, uv=("cell", "rust"), lmw=0.05)
    for lx in (-0.35, 0.35):
        for ly in (-0.2, 0.2):
            k.cyl(M, (sx + lx, sy + ly, f), (sx + lx * 0.8, sy + ly * 0.5, f + 0.5), 0.015, sides=4, uv=("cell", "iron_black"), lmw=0.01)
    k.collider(sx - 0.5, sy - 0.3, f, sx + 0.5, sy + 0.3, f + 1.0)
    # festoon lights: tall posts at the corners and the middle, bulbs every 0.5 m on sagging wire
    posts = [(dx0 + 0.06, dy1 - 0.08), ((dx0 + dx1) / 2, dy1 - 0.08), (dx1 - 0.06, dy1 - 0.08)]
    zt = f + 2.9
    for (px, py) in posts:
        k.box("Deck", (px - 0.045, py - 0.045, f), (px + 0.045, py + 0.045, zt + 0.1), tint=(0.8, 0.8, 0.8), lmw=0.1)
    anchors = [(dx0 + 0.3, y0 + 0.05, P["plate"] - 0.35), ((dx0 + dx1) / 2, y0 + 0.05, P["plate"] - 0.35), (dx1 - 0.3, y0 + 0.05, P["plate"] - 0.35)]
    runs = [(anchors[0], (posts[1][0], posts[1][1], zt)), (anchors[1], (posts[0][0], posts[0][1], zt)), (anchors[1], (posts[2][0], posts[2][1], zt)),
            (anchors[2], (posts[1][0], posts[1][1], zt)), ((posts[0][0], posts[0][1], zt), (posts[2][0], posts[2][1], zt))]
    nl = 0
    for (a, b) in runs:
        a, b = Vector(a), Vector(b)
        Lr = (b - a).length
        n = max(2, int(Lr / 0.5))
        pts = [a.lerp(b, i / n) + Vector((0, 0, -0.35 * 4 * (i / n) * (1 - i / n))) for i in range(n + 1)]
        k.tube(M, [tuple(p) for p in pts], 0.004, sides=4, uv=("cell", "plastic_black"), lmw=0.0)
        for i, p in enumerate(pts[1:-1]):
            k.lathe(M, [(0.0, -0.09), (0.022, -0.075), (0.028, -0.05), (0.012, -0.025), (0.008, 0.0)], sides=6, M=Matrix.Translation(p), uv=("cell", "bulb"), lmw=0.0)
            glow.halo(k, tuple(p + Vector((0, 0, -0.06))), 0.2, "warm", crossed=2)
            if i % 4 == 2:
                k.light("POINT", tuple(p + Vector((0, 0, -0.06))), WARM, 3.5, radius=0.03)
                nl += 1
    # a couple of monobloc chairs by the rail
    for (cx_, cy_, a) in ((14.5, 8.0, 200), (5.2, 10.9, 20)):
        _chair(k, cx_, cy_, f, a)
    # the jon boat at the landing
    lx0, ly0, lx1, ly1, zb = P["_landing"]
    veh.jon_boat(k, lx1 + 0.9, (ly0 + ly1) / 2 + 0.3, zb - 0.38, 92)


def _picnic(k, x, y, f, a):
    Mp = Matrix.Translation((x, y, f)) @ Matrix.Rotation(math.radians(a), 4, "Z")
    for i in range(5):
        yy = -0.38 + i * 0.19
        k.box("Deck", (-0.95, yy - 0.085, 0.72), (0.95, yy + 0.085, 0.76), M=Mp, bevel=0.006, tint=(0.75, 0.72, 0.68), lmw=0.4)
    for s in (-1, 1):
        for i in range(2):
            yy = s * (0.68 + i * 0.13)
            k.box("Deck", (-0.95, yy - 0.06, 0.42), (0.95, yy + 0.06, 0.46), M=Mp, bevel=0.006, tint=(0.75, 0.72, 0.68), lmw=0.25)
        _beam(k, "Deck", tuple(Mp @ Vector((s * 0.7, -0.9, 0.0))), tuple(Mp @ Vector((s * 0.7, 0.45, 0.74))), 0.04, 0.09, tint=(0.6, 0.6, 0.6), lmw=0.05)
        _beam(k, "Deck", tuple(Mp @ Vector((s * 0.7, 0.9, 0.0))), tuple(Mp @ Vector((s * 0.7, -0.45, 0.74))), 0.04, 0.09, tint=(0.6, 0.6, 0.6), lmw=0.05)
        k.box("Deck", (s * 0.7 - 0.02, -0.95, 0.38), (s * 0.7 + 0.02, 0.95, 0.42), M=Mp, tint=(0.6, 0.6, 0.6), lmw=0.03)
    c = Mp @ Vector((0, 0, 0))
    k.collider(c.x - 1.0, c.y - 0.95, f, c.x + 1.0, c.y + 0.95, f + 0.76)


def chimney_and_roof(k, P):
    """A block chimney on the west gable (the stage's old stove) and a neon cocktail glass on a
    steel frame over the roof: the silhouette against the sunset."""
    L, D, f, plate = P["L"], P["D"], P["floor"], P["plate"]
    ridge = plate + D / 2 * P["pitch"]
    cx0, cx1, cy0, cy1 = L / 2, L / 2 + 0.9, 3.0, 4.3
    k.box("Block", (cx0, cy0, 0.0), (cx1, cy1, ridge + 1.3), tint=(0.85, 0.85, 0.85), lmw=0.7, skip=("-z",))
    k.box("Block", (cx0 - 0.05, cy0 - 0.05, ridge + 1.3), (cx1 + 0.05, cy1 + 0.05, ridge + 1.42), tint=(0.6, 0.6, 0.6), bevel=0.01, lmw=0.5)
    k.box(M, (cx0 + 0.25, cy0 + 0.3, ridge + 1.42), (cx1 - 0.25, cy1 - 0.3, ridge + 1.6), uv=("cell", "rust"), lmw=0.05)
    k.collider(cx0, cy0, 0.0, cx1, cy1, ridge + 1.4)
    # the rooftop sign: two steel posts off the front slope, a cocktail glass in pink / green neon
    sx, sy = 7.5, -2.6
    zr = plate + (D / 2 - abs(sy)) * P["pitch"]
    for dx in (-1.1, 1.1):
        k.box(M, (sx + dx - 0.05, sy - 0.05, zr - 0.05), (sx + dx + 0.05, sy + 0.05, zr + 3.4), uv=("cell", "paint_grey"), lmw=0.1)
        _beam(k, M, (sx + dx, sy + 0.05, zr + 1.6), (sx + dx, sy + 1.6, plate + (D / 2 - abs(sy + 1.6)) * P["pitch"]), 0.05, 0.05, uv=("cell", "paint_grey"), lmw=0.02)
    for zz in (zr + 1.05, zr + 3.3):
        k.box(M, (sx - 1.2, sy - 0.04, zz), (sx + 1.2, sy + 0.04, zz + 0.07), uv=("cell", "paint_grey"), lmw=0.05)
    neon_sign(k, (sx, sy - 0.1, zr + 2.2), (1, 0, 0), (0, 0, 1), 2.1, "cocktail", mat=M, power=0.0, lights=False, backing=False,
              lmw=0.05, tube=0.016, halo=0.22)
    k.light("POINT", (sx, sy - 0.6, zr + 2.4), (1.0, 0.15, 0.45), 60.0, radius=0.8)
    # downspouts at the front corners
    ov = P["overhang"]
    for x in (-L / 2 - 0.2, L / 2 + 0.2):
        k.cyl(M, (x, -D / 2 - ov + 0.02, plate - ov * P["pitch"] - 0.06), (x, -D / 2 - 0.08, plate - 0.6), 0.04, sides=8, uv=("cell", "galvanized"), lmw=0.02)
        k.cyl(M, (x, -D / 2 - 0.08, plate - 0.6), (x, -D / 2 - 0.08, 0.15), 0.045, sides=8, uv=("cell", "galvanized"), lmw=0.1)
        k.cyl(M, (x, -D / 2 - 0.08, 0.15), (x, -D / 2 - 0.45, 0.04), 0.045, sides=8, uv=("cell", "galvanized"), lmw=0.02)
    # the electric meter and a window air conditioner on the east end
    k.box(M, (-L / 2 - 0.25, 1.6, 0.9), (-L / 2, 2.4, 1.15), bevel=0.02, uv=("cell", "paint_cream"), lmw=0.1)


def build_lot(k, P):
    P.setdefault("sign", (40.5, -15.5))
    P.setdefault("sign_yaw", 35.0)
    P.setdefault("pole", (-21.0, -12.5))
    for fn in (gravel, pole_sign, utility_pole, back_lot, porch_dressing, deck_dressing, chimney_and_roof):
        k.section = fn.__name__
        fn(k, P)
    k.section = "vehicles"
    D, pd = P["D"], P["porch_depth"]
    yp = -D / 2 - pd
    # the invaders' vans, backed in to the porch (nose out), and the townspeople's pickups
    veh.van(k, -4.1, yp - 3.8, -90.0, "van_black")
    veh.van(k, -1.35, yp - 3.75, -88.5, "van_grey")
    veh.pickup(k, 3.4, yp - 3.6, 92.0, "truck_red", "90s", rust=True, extras=("toolbox",))
    veh.pickup(k, P["L"] / 2 + 3.2, -1.0, 178.0, "truck_white", "80s", rust=True, extras=("cargo",))
    veh.pickup(k, -P["L"] / 2 - 4.8, -9.5, 75.0, "truck_blue", "90s", rust=False)
