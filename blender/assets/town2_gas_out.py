"""The gas station's outdoor pieces (town2_gas.py places them): the fuel dispenser, the pump
island, bollards, the canopy column, the island trash/squeegee stand, the monument price sign,
the ice merchandiser, the propane exchange cage, the firewood rack, the air machine, trash cans,
a bench, clipped shrubs and beds, the rooftop units, the dumpster enclosure and the van.
Every function builds at its own origin (floor at z = 0, front -Y unless it says otherwise).
References: a modern multi-product dispenser of the Gilbarco Encore / Wayne Anthem kind (white
hydraulics cabinet, a dark glass electronics head with the LCD, the card reader and a media
screen, three nozzles a side, an ad topper), a Leer-type outdoor ice merchandiser, a Blue Rhino
style propane exchange cage.
"""
import math
import random

import bmesh
from mathutils import Vector

V = Vector


# ------------------------------------------------------------------ pumps
def dispenser(kit, diesel=False):
    """A two-sided multi-product dispenser, long axis along y (1.3 m), faces +-x, on an island top."""
    W = kit.p("white", "ext", lmw=1.2)
    D = kit.p("charcoal", "ext", lmw=1.2)
    B = kit.p("black", "ext", lmw=1.0)
    L = kit.p("lightgrey", "ext", lmw=1.0)
    S = kit.p("signs", "ext")
    hw, hl = 0.29, 0.62
    D.box((-hw - 0.03, -hl - 0.03, 0), (hw + 0.03, hl + 0.03, 0.12), bevel=0.015, skip="z")
    W.box((-hw, -hl, 0.12), (hw, hl, 1.0), bevel=0.02, skip="z")
    W.box((-hw - 0.02, -hl - 0.02, 1.0), (hw + 0.02, hl + 0.02, 1.88), bevel=0.03)
    for s in (-1, 1):
        fx = s * hw
        # hydraulics doors: a proud panel with louvers
        L.box((min(fx, fx + s * 0.012), -hl + 0.06, 0.2), (max(fx, fx + s * 0.012), hl - 0.06, 0.92), bevel=0.006)
        for k in range(6):
            z = 0.32 + k * 0.08
            B.box((min(fx + s * 0.012, fx + s * 0.018), -0.32, z), (max(fx + s * 0.012, fx + s * 0.018), 0.32, z + 0.022))
        # the electronics head: dark glass bezel
        gx = s * (hw + 0.02)
        B.box((min(gx, gx + s * 0.012), -hl + 0.04, 1.06), (max(gx, gx + s * 0.012), hl - 0.04, 1.84), bevel=0.01)
        fx2 = gx + s * 0.016
        face = "X" if s > 0 else "x"
        # the screens (y runs the other way on the -x face: the panel helper keeps them readable)
        S.panel((fx2, 0.06 * s, 1.62), face, 0.40, 0.20, cell=kit.cell("signs", "pump_screen"))
        S.panel((fx2, -0.34 * s, 1.36), face, 0.20, 0.20, cell=kit.cell("signs", "pump_media"))
        S.panel((fx2, 0.08 * s, 1.17), face, 0.44, 0.08, cell=kit.cell("signs", "grades"))
        # keypad, card reader, receipt slot
        D.box((min(fx2, fx2 + s * 0.02), 0.14 * s - 0.07, 1.27), (max(fx2, fx2 + s * 0.02), 0.14 * s + 0.07, 1.43), bevel=0.005)
        for r_ in range(3):
            for c_ in range(3):
                L.box((min(fx2 + s * 0.02, fx2 + s * 0.028), 0.14 * s - 0.05 + c_ * 0.035, 1.3 + r_ * 0.04),
                      (max(fx2 + s * 0.02, fx2 + s * 0.028), 0.14 * s - 0.025 + c_ * 0.035, 1.325 + r_ * 0.04))
        L.box((min(fx2, fx2 + s * 0.03), 0.38 * s - 0.06, 1.3), (max(fx2, fx2 + s * 0.03), 0.38 * s + 0.06, 1.38), bevel=0.008)
        B.box((min(fx2 + s * 0.03, fx2 + s * 0.032), 0.38 * s - 0.04, 1.34), (max(fx2 + s * 0.03, fx2 + s * 0.032), 0.38 * s + 0.04, 1.345))
        # nozzle boots, nozzles and hoses (three grades; the last green on the diesel pump)
        for k, yb in enumerate((-0.42, 0.0, 0.42)):
            bx = s * (hw + 0.005)
            D.box((min(bx, bx + s * 0.07), yb - 0.05, 0.86), (max(bx, bx + s * 0.07), yb + 0.05, 1.0), bevel=0.008)
            noz = kit.p("green" if (diesel and k == 2) else "black", "ext", lmw=0.6)
            # the handle (angled), the guard, the spout into the boot
            with kit.at((bx + s * 0.06, yb, 0.98), rot=0 if s > 0 else 180, ry=-35):
                noz.box((-0.02, -0.025, -0.02), (0.18, 0.025, 0.035), bevel=0.01)
                kit.p("steel", "ext", lmw=0.4).tube([(0.0, 0, 0.0), (-0.06, 0, -0.03), (-0.1, 0, -0.1)], 0.011, sides=6)
                noz.box((0.03, -0.022, -0.07), (0.15, 0.022, -0.055))
            # the hose: out of the topper's corner, a sagging loop, into the handle's back
            hx = s * (hw + 0.03)
            top = (hx, yb * 1.3 + (0.05 if yb >= 0 else -0.05), 1.86)
            mid = (s * (hw + 0.28), yb * 1.5, 0.55 + 0.05 * k)
            end = (bx + s * 0.22, yb, 1.0)
            pts = [top, (s * (hw + 0.12), yb * 1.4, 1.5), (s * (hw + 0.24), yb * 1.5, 1.0), mid, (s * (hw + 0.3), yb * 1.2, 0.75), end]
            kit.p("hose", "ext", lmw=0.3).tube(smooth_path(pts, 3), 0.016, sides=6, caps=False)
    # the topper: white with the station's green band and a small pump mark
    W.box((-hw - 0.03, -hl - 0.05, 1.88), (hw + 0.03, hl + 0.05, 2.32), bevel=0.02)
    for s in (-1, 1):
        fx = s * (hw + 0.031)
        face = "X" if s > 0 else "x"
        S.panel((fx, 0, 2.0), face, 1.2, 0.07, cell=kit.cell("signs", "band"))
        S.panel((fx, -0.38 * s, 2.2), face, 0.2, 0.2, cell=kit.cell("signs", "logo"))
    kit.collide((-hw - 0.05, -hl - 0.05, 0), (hw + 0.05, hl + 0.05, 2.32))


def smooth_path(pts, n=3):
    """Catmull-Rom through pts, n segments between each pair."""
    P = [V(p) for p in pts]
    out = []
    for i in range(len(P) - 1):
        p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, len(P) - 1)]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-1])
    return out


def island(kit, length=6.6, width=1.25, h=0.15):
    """A pump island: concrete with bullnose ends and a steel edge, along y, centred, top at h."""
    C = kit.p("concrete", "ext", lmw=0.8)
    E = kit.p("steel", "ext", lmw=0.6)
    r = width / 2
    seg = 10
    outline = []
    for k in range(seg + 1):
        a = math.pi + math.pi * k / seg
        outline.append((r * math.cos(a), -length / 2 + r + r * math.sin(a)))
    for k in range(seg + 1):
        a = math.pi * k / seg
        outline.append((r * math.cos(a), length / 2 - r + r * math.sin(a)))
    C.slab(outline, 0.0, h - 0.01, caps="top")
    inner = [(x * 0.94, y * (1 - 0.06 * r / (length / 2))) for x, y in outline]
    # the steel nosing band round the top edge
    n = len(outline)
    for i in range(n):
        (ax, ay), (bx, by) = outline[i], outline[(i + 1) % n]
        E.face([(ax, ay, h - 0.012), (bx, by, h - 0.012), (bx, by, h), (ax, ay, h)])
    kit.collide((-r, -length / 2, 0), (r, length / 2, h))
    for s in (-1, 1):
        with kit.at((0, s * (length / 2 - 0.35), h)):
            bollard(kit, 1.0, "safety")


def bollard(kit, h=1.05, color="safety", r=0.085):
    """A steel pipe bollard with a domed cap and a reflective band."""
    B = kit.p(color, "ext", lmw=0.5)
    B.cyl((0, 0), r, 0, h - r * 0.4, seg=12, caps="none")
    B.lathe([(r, 0), (r * 0.92, r * 0.35), (r * 0.6, r * 0.62), (0.0, r * 0.7)], z=h - r * 0.4, seg=12)
    kit.p("white", "ext", lmw=0.3).cyl((0, 0), r + 0.003, h - 0.28, h - 0.2, seg=12, caps="none")
    kit.collide((-r, -r, 0), (r, r, h))


def column(kit, h, stone_h=1.3):
    """A canopy column: a white square steel post on a ledgestone wrap with a cast cap."""
    S = kit.p("stone", "ext", lmw=0.8)
    W = kit.p("white", "ext", lmw=0.7)
    C = kit.p("concrete", "ext", lmw=0.6)
    S.box((-0.38, -0.38, 0), (0.38, 0.38, stone_h), skip="z")
    C.box((-0.43, -0.43, stone_h), (0.43, 0.43, stone_h + 0.07), bevel=0.015)
    W.box((-0.2, -0.2, stone_h + 0.07), (0.2, 0.2, h), bevel=0.012, skip="zZ")
    # the emergency stop on its plate, a fire extinguisher bracket
    kit.p("red", "ext", lmw=0.3).box((-0.06, -0.205, 1.62), (0.06, -0.2, 1.78))
    kit.p("red", "ext", lmw=0.3).cyl((0.0, -0.24), 0.07, 0.8, 1.25, seg=10)
    kit.p("black", "ext", lmw=0.3).cyl((0.0, -0.24), 0.03, 1.25, 1.33, seg=8)
    kit.collide((-0.38, -0.38, 0), (0.38, 0.38, h))


def island_stand(kit):
    """The trash can and squeegee station on the island: a green steel can on a post, the towel
    dispenser above, the washer bucket."""
    G = kit.p("green_dark", "ext", lmw=0.5)
    B = kit.p("black", "ext", lmw=0.4)
    B.cyl((0, 0), 0.035, 0, 1.45, seg=8, caps="top")
    G.lathe([(0.0, 0.0), (0.2, 0.0), (0.21, 0.6), (0.19, 0.62), (0.0, 0.62)], z=0.05, seg=14)
    kit.p("black", "ext").cyl((0, 0), 0.215, 0.62, 0.68, seg=14)
    kit.p("white", "ext", lmw=0.4).box((-0.12, -0.07, 1.2), (0.12, 0.07, 1.5), bevel=0.02)
    kit.p("blue", "ext", lmw=0.3).lathe([(0.0, 0.0), (0.11, 0.0), (0.13, 0.22), (0.0, 0.22)], c=(0.0, 0.27), z=0.72, seg=10)
    kit.p("black", "ext").box((0.02, 0.22, 0.75), (0.035, 0.32, 1.12))
    kit.collide((-0.22, -0.22, 0), (0.22, 0.22, 1.5))


# ------------------------------------------------------------------ the forecourt's furniture
def monument_sign(kit):
    """The price sign at the road: a ledgestone base, a two-faced cabinet (the pump mark on the
    station green, four LED price lines), a cap. Faces -y and +y."""
    S = kit.p("stone", "ext", lmw=0.8)
    C = kit.p("concrete", "ext", lmw=0.6)
    K = kit.p("charcoal", "ext", lmw=0.8)
    G = kit.p("signs", "ext")
    S.box((-1.45, -0.42, 0), (1.45, 0.42, 0.85), skip="z")
    C.box((-1.52, -0.48, 0.85), (1.52, 0.48, 0.93), bevel=0.02)
    K.box((-1.28, -0.24, 0.93), (1.28, 0.24, 3.25), bevel=0.02)
    K.box((-1.36, -0.3, 3.25), (1.36, 0.3, 3.36), bevel=0.02)
    for s in (-1, 1):
        fy = s * 0.241
        face = "Y" if s > 0 else "y"
        G.panel((0.0, fy, 2.62), face, 2.36, 1.02, cell=kit.cell("signs", "band"))
        G.panel((-0.62 * s, fy + s * 0.006, 2.62), face, 0.9, 0.9, cell=kit.cell("signs", "logo"))
        G.panel((0.0, fy, 1.55), face, 2.36, 1.18, cell=kit.cell("signs", "price"))
    kit.collide((-1.52, -0.48, 0), (1.52, 0.48, 3.36))


def ice_chest(kit):
    """An outdoor ice merchandiser (1.6 x 0.8 x 1.3): white, two printed doors, the condensing
    unit's grille on top."""
    W = kit.p("propane_white", "ext", lmw=0.9)
    D = kit.p("graphite", "ext", lmw=0.6)
    W.box((-0.8, -0.4, 0.08), (0.8, 0.4, 1.25), bevel=0.03)
    D.box((-0.78, -0.38, 0), (0.78, 0.38, 0.08))
    for k in (-1, 1):
        x0, x1 = (-0.76, -0.02) if k < 0 else (0.02, 0.76)
        kit.p("goods", "ext", lmw=0.6).box((x0, -0.415, 0.16), (x1, -0.4, 1.12), cell=kit.cell("goods", "ice_panel"), front="y")
        D.box((x1 - 0.08 if k < 0 else x0 + 0.02, -0.44, 0.6), (x1 - 0.02 if k < 0 else x0 + 0.08, -0.415, 0.78), bevel=0.008)
    D.box((-0.7, -0.3, 1.25), (0.7, 0.3, 1.33), bevel=0.01)
    for k in range(10):
        kit.p("black", "ext", lmw=0.2).box((-0.65 + k * 0.13, -0.31, 1.27), (-0.6 + k * 0.13, -0.3, 1.31))
    kit.collide((-0.8, -0.44, 0), (0.8, 0.4, 1.33))


def propane_cage(kit, rng):
    """A propane exchange cage (1.7 x 0.8 x 1.8): white steel frame, a bar mesh, two shelves of
    20 lb cylinders (white and grey), the sign on top."""
    F = kit.p("propane_white", "ext", lmw=0.6)
    Bars = kit.p("lightgrey", "ext", lmw=0.25)
    w, d, h = 1.7, 0.8, 1.8
    for x in (-w / 2, w / 2):
        for y in (-d / 2, d / 2):
            F.box((x - 0.025, y - 0.025, 0), (x + 0.025, y + 0.025, h))
    for z in (0.05, 0.9, h - 0.04):
        F.box((-w / 2, -d / 2 - 0.02, z - 0.02), (w / 2, -d / 2 + 0.02, z + 0.03))
        F.box((-w / 2, d / 2 - 0.02, z - 0.02), (w / 2, d / 2 + 0.02, z + 0.03))
        F.box((-w / 2 - 0.02, -d / 2, z - 0.02), (-w / 2 + 0.02, d / 2, z + 0.03))
        F.box((w / 2 - 0.02, -d / 2, z - 0.02), (w / 2 + 0.02, d / 2, z + 0.03))
    F.box((-w / 2, -d / 2, 0.88), (w / 2, d / 2, 0.92))          # shelf
    F.box((-w / 2, -d / 2, h - 0.03), (w / 2, d / 2, h + 0.01))  # roof
    n = int(w / 0.07)
    for k in range(1, n):
        x = -w / 2 + k * w / n
        Bars.box((x - 0.005, -d / 2 - 0.01, 0.05), (x + 0.005, -d / 2, h - 0.04))
    for k in range(1, 10):
        y = -d / 2 + k * d / 10
        for x in (-w / 2, w / 2):
            Bars.box((x - 0.006, y - 0.005, 0.05), (x + 0.006, y + 0.005, h - 0.04))
    for zb in (0.06, 0.93):
        for k in range(4):
            col = "propane_white" if rng.random() < 0.7 else "lightgrey"
            T = kit.p(col, "ext", lmw=0.3)
            cx = -w / 2 + 0.22 + k * 0.42
            prof = [(0.0, 0.0), (0.15, 0.0), (0.155, 0.03), (0.155, 0.36), (0.13, 0.42), (0.06, 0.45), (0.0, 0.45)]
            T.lathe(prof, c=(cx, 0.02), z=zb, seg=12)
            kit.p("steel", "ext", lmw=0.2).cyl((cx, 0.02), 0.09, zb + 0.45, zb + 0.55, seg=10, caps="none")
            kit.p("lightgrey", "ext", lmw=0.2).cyl((cx, 0.02), 0.025, zb + 0.45, zb + 0.5, seg=6)
    kit.p("goods", "ext", lmw=0.4).box((-0.4, -d / 2 - 0.03, h - 0.42), (0.4, -d / 2 - 0.01, h - 0.06), cell=kit.cell("goods", "propane_panel"), front="y")
    kit.collide((-w / 2 - 0.03, -d / 2 - 0.03, 0), (w / 2 + 0.03, d / 2 + 0.03, h))


def firewood_rack(kit, rng):
    """A black steel rack of shrink-wrapped firewood bundles (two shelves)."""
    B = kit.p("black", "ext", lmw=0.4)
    w, d = 1.1, 0.55
    for x in (-w / 2, w / 2):
        for y in (-d / 2, d / 2):
            B.box((x - 0.02, y - 0.02, 0), (x + 0.02, y + 0.02, 1.2))
    for z in (0.08, 0.62):
        B.box((-w / 2, -d / 2, z), (w / 2, d / 2, z + 0.03))
    for z in (0.11, 0.65):
        for b in range(2):
            cx = -0.26 + b * 0.52
            for k in range(7):
                a = k / 7 * 2 * math.pi
                rr = 0.09 if k else 0.0
                y = 0.0 + rr * math.cos(a) * 1.1
                zz = z + 0.16 + rr * math.sin(a) * 0.9
                col = "tan" if rng.random() < 0.6 else "wood_dark"
                with kit.at((cx, y, zz), ry=90):
                    kit.p(col, "ext", lmw=0.15).cyl((0, 0), 0.052 + 0.01 * rng.random(), -0.2, 0.2, seg=7)
    kit.collide((-w / 2 - 0.02, -d / 2 - 0.02, 0), (w / 2 + 0.02, d / 2 + 0.02, 1.2))


def air_machine(kit):
    """A coin air machine on its pad: a green-and-white pedestal, the lit tyre pictogram, a coiled
    hose on its hook."""
    G = kit.p("green", "ext", lmw=0.8)
    W = kit.p("white", "ext", lmw=0.8)
    kit.p("concrete", "ext", lmw=0.5).box((-0.6, -0.6, 0), (0.6, 0.6, 0.1), bevel=0.02, skip="z")
    G.box((-0.22, -0.18, 0.1), (0.22, 0.18, 1.05), bevel=0.02)
    W.box((-0.24, -0.2, 1.05), (0.24, 0.2, 1.42), bevel=0.02)
    kit.p("signs", "ext").panel((0, -0.201, 1.25), "y", 0.3, 0.3, cell=kit.cell("signs", "air"))
    kit.p("steel", "ext", lmw=0.3).box((-0.08, -0.19, 0.8), (0.08, -0.18, 0.92))
    kit.p("black", "ext").box((0.22, -0.03, 0.85), (0.3, 0.03, 0.9))
    pts = []
    for k in range(25):
        a = k / 24 * 2 * math.pi * 1.6
        pts.append((0.32 + 0.02 * k / 24, 0.16 * math.cos(a), 0.68 + 0.17 * math.sin(a)))
    kit.p("hose", "ext", lmw=0.2).tube(pts, 0.012, sides=6)
    kit.collide((-0.24, -0.2, 0), (0.34, 0.2, 1.42))
    for x in (-0.48, 0.48):
        with kit.at((x, -0.48, 0.1)):
            bollard(kit, 0.9, "safety", 0.07)


def trash_can(kit):
    """A square steel litter receptacle with a domed top and a push flap."""
    K = kit.p("charcoal", "ext", lmw=0.6)
    K.box((-0.28, -0.28, 0), (0.28, 0.28, 0.85), bevel=0.02)
    K.lathe([(0.3, 0.0), (0.28, 0.08), (0.2, 0.16), (0.0, 0.19)], z=0.85, seg=4, cap_top=False)
    kit.p("black", "ext").box((-0.15, -0.29, 0.6), (0.15, -0.27, 0.78))
    kit.collide((-0.3, -0.3, 0), (0.3, 0.3, 1.0))


def bench(kit):
    """A black steel slat bench (1.8 m)."""
    B = kit.p("black", "ext", lmw=0.5)
    for x in (-0.8, 0.8):
        B.box((x - 0.03, -0.25, 0), (x + 0.03, 0.25, 0.44))
        B.box((x - 0.03, 0.2, 0.44), (x + 0.03, 0.26, 0.85))
    for k in range(5):
        y = -0.24 + k * 0.1
        B.box((-0.9, y, 0.44), (0.9, y + 0.07, 0.47))
    for k in range(3):
        z = 0.55 + k * 0.1
        B.box((-0.9, 0.24, z), (0.9, 0.27, z + 0.07))
    kit.collide((-0.9, -0.25, 0), (0.9, 0.27, 0.47))


def shrub(kit, rng, r=0.45, h=None, col="leaf", sub=2):
    """A clipped shrub (boxwood / dwarf juniper): a jittered, slightly flattened sphere."""
    h = h or r * 1.6
    tbm = bmesh.new()
    bmesh.ops.create_icosphere(tbm, subdivisions=sub, radius=1.0)
    for v in tbm.verts:
        n = v.co.normalized()
        j = 1 + 0.08 * (rng.random() - 0.5) + 0.05 * math.sin(n.x * 7 + n.y * 5)
        v.co = V((n.x * r * j, n.y * r * j, max(n.z, -0.3) * h / 2 * j + h / 2 * 0.85))
    kit.p(col, "ext", lmw=0.25).mesh(tbm, smooth=True)


def bed(kit, rng, x0, y0, x1, y1, shrubs=(), curb=0.15):
    """A planting bed: a concrete curb, mulch, clipped shrubs at shrubs [(x, y, r)]."""
    C = kit.p("concrete", "ext", lmw=0.4)
    M = kit.p("mulch", "ext", lmw=0.3)
    t = 0.15
    C.box((x0, y0, 0), (x1, y0 + t, curb), skip="z")
    C.box((x0, y1 - t, 0), (x1, y1, curb), skip="z")
    C.box((x0, y0 + t, 0), (x0 + t, y1 - t, curb), skip="z")
    C.box((x1 - t, y0 + t, 0), (x1, y1 - t, curb), skip="z")
    M.box((x0 + t, y0 + t, 0), (x1 - t, y1 - t, curb - 0.03), skip="zxXyY")
    for (x, y, r) in shrubs:
        with kit.at((x, y, curb - 0.03), rot=rng.random() * 360):
            shrub(kit, rng, r, col="leaf" if rng.random() < 0.7 else "leaf_light")
    kit.collide((x0, y0, 0), (x1, y1, curb))


def rooftop_unit(kit):
    """A packaged rooftop HVAC unit (2.2 x 1.3 x 1.1) on its curb: grey cabinet, two fan grilles."""
    G = kit.p("lightgrey", "ext", lmw=0.3)
    D = kit.p("graphite", "ext", lmw=0.2)
    D.box((-1.15, -0.7, 0), (1.15, 0.7, 0.2))
    G.box((-1.1, -0.65, 0.2), (1.1, 0.65, 1.2), bevel=0.02)
    for x in (-0.5, 0.5):
        D.cyl((x, 0), 0.36, 1.2, 1.24, seg=16)
        kit.p("black", "ext", lmw=0.1).cyl((x, 0), 0.3, 1.24, 1.25, seg=16)
    for k in range(8):
        D.box((-1.0 + k * 0.25, -0.66, 0.35), (-0.9 + k * 0.25, -0.65, 0.9))


def dumpster_enclosure(kit, rng):
    """A ledgestone enclosure (5 x 3.6 x 1.9) with cedar-slat gates standing open, a green
    front-load dumpster inside. Opens to -y."""
    S = kit.p("stone", "ext", lmw=0.5)
    C = kit.p("concrete", "ext", lmw=0.4)
    W, D, H = 5.0, 3.6, 1.9
    S.box((-W / 2, D / 2 - 0.25, 0), (W / 2, D / 2, H), skip="z")
    S.box((-W / 2, -D / 2, 0), (-W / 2 + 0.25, D / 2 - 0.25, H), skip="z")
    S.box((W / 2 - 0.25, -D / 2, 0), (W / 2, D / 2 - 0.25, H), skip="z")
    C.box((-W / 2 - 0.03, D / 2 - 0.28, H), (W / 2 + 0.03, D / 2 + 0.03, H + 0.07))
    C.box((-W / 2 - 0.03, -D / 2 - 0.03, H), (-W / 2 + 0.28, D / 2 - 0.28, H + 0.07))
    C.box((W / 2 - 0.28, -D / 2 - 0.03, H), (W / 2 + 0.03, D / 2 - 0.28, H + 0.07))
    kit.collide((-W / 2, D / 2 - 0.25, 0), (W / 2, D / 2, H))
    kit.collide((-W / 2, -D / 2, 0), (-W / 2 + 0.25, D / 2, H))
    kit.collide((W / 2 - 0.25, -D / 2, 0), (W / 2, D / 2, H))
    # gates swung open against the side walls (outside)
    for s in (-1, 1):
        x = s * (W / 2 + 0.06)
        with kit.at((x, -D / 2, 0), rot=0):
            for k in range(12):
                y = -0.02 - k * 0.19
                kit.p("wood_dark", "ext", lmw=0.3).box((-0.03, y - 0.16, 0.12), (0.03, y, 1.75))
            kit.p("black", "ext", lmw=0.2).box((-0.04, -2.3, 0.3), (0.04, 0.0, 0.36))
            kit.p("black", "ext", lmw=0.2).box((-0.04, -2.3, 1.45), (0.04, 0.0, 1.51))
        kit.collide((x - 0.05, -D / 2 - 2.3, 0), (x + 0.05, -D / 2, 1.75))
    # the dumpster
    G = kit.p("green_dark", "ext", lmw=0.5)
    with kit.at((0, 0.35, 0)):
        G.box((-1.0, -0.8, 0.12), (1.0, 0.8, 1.35), bevel=0.03)
        kit.p("black", "ext", lmw=0.3).extrude([(-1.02, -0.85, 1.35), (1.02, -0.85, 1.35), (1.02, -0.85, 1.42), (-1.02, -0.85, 1.6)], (0, 1.7, 0))
        for x in (-0.8, 0.8):
            kit.p("black", "ext").cyl((x, -0.6), 0.06, 0.0, 0.12, seg=8)
            kit.p("black", "ext").cyl((x, 0.6), 0.06, 0.0, 0.12, seg=8)
        kit.collide((-1.02, -0.85, 0), (1.02, 0.85, 1.6))


# ------------------------------------------------------------------ the van out back
def van(kit, rng, doors_open=True):
    """A dark high-roof cargo van (5.9 x 2.0 x 2.6), nose to -x... built along +x = forward,
    centred; rear doors swung open; inside: crates, duffels, a coil of rope, a tarp."""
    P = kit.p("van", "ext", lmw=0.9)
    T = kit.p("van_trim", "ext", lmw=0.6)
    G = kit.p("glass_dark", "ext")
    L = 5.9
    w = 2.0
    hw = w / 2
    x0 = -L / 2
    # side profile in (x, z): the rear, the roof, the windshield, the bonnet, the nose
    prof = [(x0, 0.38), (x0 + 5.9, 0.38), (x0 + 5.9, 0.62), (x0 + 5.82, 0.95), (x0 + 5.35, 1.12),
            (x0 + 4.75, 1.32), (x0 + 4.2, 2.1), (x0 + 4.0, 2.42), (x0 + 3.85, 2.55), (x0 + 0.08, 2.58), (x0, 2.5)]
    # body: the profile extruded across the width, with chamfered sides (in two shells)
    poly = [(x, -hw + 0.04, z) for x, z in prof]
    P.extrude(poly[::-1], (0, w - 0.08, 0))
    # the sides' slight tumblehome: thin outer panels
    for s in (-1, 1):
        y = s * (hw - 0.04)
        pts = [(x0 + 0.05, y, 0.42), (x0 + 4.7, y, 0.42), (x0 + 4.7, y, 1.25), (x0 + 4.15, y, 2.05), (x0 + 0.05, y, 2.05)]
        if s < 0:
            pts = pts[::-1]
        P.face([(px, py + s * 0.035, pz) for px, py, pz in pts])
        # windows: the cab's door glass and the windshield
        wp = [(x0 + 4.0, s * (hw + 0.0), 1.45), (x0 + 4.55, s * (hw + 0.0), 1.45), (x0 + 4.25, s * (hw + 0.0), 2.0), (x0 + 3.95, s * (hw + 0.0), 2.0)]
        if s < 0:
            wp = wp[::-1]
        G.face(wp)
        # door seams, handle, mirror
        T.box((x0 + 3.9, s * hw - 0.01, 0.5), (x0 + 3.92, s * hw + 0.01, 2.0))
        T.box((x0 + 3.55, s * hw - 0.005 + s * 0.0, 1.25), (x0 + 3.7, s * hw + s * 0.02, 1.3))
        with kit.at((x0 + 4.45, s * (hw + 0.12), 1.75)):
            T.box((-0.06, -0.1, -0.15), (0.06, 0.1, 0.15), bevel=0.02)
        # the sliding door's track
        T.box((x0 + 1.2, s * hw - 0.01, 1.98), (x0 + 3.85, s * hw + s * 0.025, 2.01))
        # wheel arches and wheels
        for xw in (x0 + 1.05, x0 + 4.55):
            with kit.at((xw, s * (hw - 0.12), 0.38), rx=90):
                kit.p("tyre", "ext", lmw=0.4).cyl((0, 0), 0.37, -0.13, 0.13, seg=18)
            hub_x = s * (hw - 0.12 + 0.132)
            with kit.at((xw, hub_x, 0.38), rx=90 * s):
                kit.p("darksteel", "ext", lmw=0.3).cyl((0, 0), 0.2, 0.0, 0.01, seg=12)
            kit.p("van_trim", "ext", lmw=0.3).extrude([(xw - 0.48, s * hw, 0.42), (xw - 0.42, s * hw, 0.72), (xw - 0.18, s * hw, 0.84),
                                                      (xw + 0.18, s * hw, 0.84), (xw + 0.42, s * hw, 0.72), (xw + 0.48, s * hw, 0.42)][::1 if s > 0 else -1],
                                                     (0, s * 0.04, 0), caps=False)
    # windshield
    G.face([(x0 + 4.72, -hw + 0.12, 1.36), (x0 + 4.72, hw - 0.12, 1.36), (x0 + 4.17, hw - 0.14, 2.1), (x0 + 4.17, -hw + 0.14, 2.1)])
    # bumpers, grille, lamps, plates
    T.box((x0 + 5.82, -hw, 0.36), (x0 + 6.0, hw, 0.62), bevel=0.04)
    T.box((x0 + 5.86, -0.55, 0.66), (x0 + 5.92, 0.55, 0.92), bevel=0.02)
    for s in (-1, 1):
        kit.p("white", "ext", lmw=0.2).box((x0 + 5.84, s * 0.85 - 0.12, 0.78), (x0 + 5.9, s * 0.85 + 0.12, 0.92), bevel=0.01)
        kit.p("red", "ext", lmw=0.2).box((x0 - 0.04, s * 0.92 - 0.06, 0.9), (x0 + 0.0, s * 0.92 + 0.06, 1.5))
    T.box((x0 - 0.12, -hw, 0.34), (x0 + 0.05, hw, 0.55), bevel=0.03)
    kit.p("white", "ext", lmw=0.2).box((x0 + 5.995, -0.26, 0.4), (x0 + 6.005, 0.26, 0.52))
    # the cargo bay (open): a dark floor and walls inside the rear opening, the load
    K = kit.p("charcoal", "ext", lmw=0.5)
    K.box((x0 + 0.02, -hw + 0.06, 0.62), (x0 + 3.6, hw - 0.06, 0.66))
    K.panel((x0 + 3.6, 0, 1.6), "x", 1.86, 1.9)
    if doors_open:
        for s in (-1, 1):
            # each leaf hinged at the rear corner, swung ~100 degrees open
            with kit.at((x0, s * hw, 0.4), rot=-s * 100):
                lo, hi = ((-0.05, -0.95, 0.02), (0.0, 0.0, 2.12)) if s > 0 else ((-0.05, 0.0, 0.02), (0.0, 0.95, 2.12))
                P.box(lo, hi, bevel=0.01)
                G.panel((-0.051, -0.48 if s > 0 else 0.48, 1.65), "x", 0.7, 0.55)
        # the load: plastic crates, duffels, a rope coil, a folded tarp
        for k in range(3):
            for j in range(2):
                kit.p("black", "ext", lmw=0.3).box((x0 + 0.3 + k * 0.62, -0.75 + j * 0.62, 0.66), (x0 + 0.85 + k * 0.62, -0.25 + j * 0.62, 0.98), bevel=0.01)
        for k in range(2):
            with kit.at((x0 + 2.2 + k * 0.6, 0.45, 0.82)):
                kit.p("charcoal", "ext", lmw=0.3).lathe([(0, -0.16), (0.16, -0.14), (0.18, 0.0), (0.16, 0.14), (0.0, 0.16)], seg=8, cap_top=False)
        rope = [(x0 + 1.0 + 0.2 * math.cos(a * 0.4), 0.55 + 0.2 * math.sin(a * 0.4), 0.7 + 0.012 * a) for a in range(40)]
        kit.p("tan", "ext", lmw=0.2).tube(rope, 0.015, sides=5)
        kit.p("blue", "ext", lmw=0.3).box((x0 + 2.8, -0.85, 0.66), (x0 + 3.5, -0.2, 0.8), bevel=0.03)
    kit.collide((x0 - 0.12, -hw, 0), (x0 + 6.0, hw, 2.58))


# ------------------------------------------------------------------ the van, second pass
def _ring(w, z0, zt, rt=0.16, rb=0.06, tumble=0.95, n_arc=4):
    """A van body's cross-section (y, z), closed, counter-clockwise seen from +x."""
    pts = [(0.0, z0)]
    for k in range(n_arc + 1):                                  # bottom corner (+y)
        a = -math.pi / 2 + (math.pi / 2) * k / n_arc
        pts.append((w - rb + rb * math.cos(a), z0 + rb + rb * math.sin(a)))
    wt = w * tumble
    for k in range(n_arc + 1):                                  # top corner (+y)
        a = (math.pi / 2) * k / n_arc
        pts.append((wt - rt + rt * math.cos(a), zt - rt + rt * math.sin(a)))
    pts.append((0.0, zt))
    half = pts[1:-1]
    mirror = [(-y, z) for (y, z) in reversed(half)]
    return pts[:-1] + [(0.0, zt)] + mirror


def _loft(br, stations, close_front=True, inward=False):
    """Quads between consecutive rings; stations = [(x, ring)], each ring the same length."""
    rings = [[(x, y, z) for (y, z) in ring] for x, ring in stations]
    n = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            q = [a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]]
            if inward:
                q = q[::-1]
            br.face(q, smooth=True)
    if close_front:
        br.face(list(reversed(rings[-1])) if not inward else rings[-1], smooth=False)


def van2(kit, rng, doors_open=True):
    """A dark high-roof cargo van of the Sprinter / Transit kind (5.9 x 2.0 x 2.6, no badges): a
    lofted body (rounded sections, tumblehome, the sloped windshield and short bonnet), wheel
    arches with flares, four wheels (tyre, steel rim, hub), glass, door seams and handles, mirrors,
    lamps, grille, bumpers, a step; the rear doors swung open on a cargo bay of crates, duffels, rope
    and a tarp. Built along +x = forward, centred, on the ground."""
    P = kit.p("van", "ext", lmw=1.0)
    T = kit.p("van_trim", "ext", lmw=0.7)
    G = kit.p("glass_dark", "ext")
    L = 5.92
    x0 = -L / 2
    hw = 1.0
    xr, xf = x0 + 1.05, x0 + 4.55                               # wheel centres
    R = 0.37
    # stations: (x, half width, bottom, top); arches as raised bottoms over the wheels
    S = [(x0, 0.97, 0.42, 2.56), (x0 + 0.05, 0.99, 0.4, 2.6), (xr - 0.5, hw, 0.4, 2.6), (xr - 0.47, hw, 0.8, 2.6),
         (xr + 0.47, hw, 0.8, 2.6), (xr + 0.5, hw, 0.4, 2.6), (x0 + 3.85, hw, 0.4, 2.6), (x0 + 4.0, hw, 0.4, 2.52),
         (xf - 0.5, 0.995, 0.4, 2.3), (xf - 0.47, 0.99, 0.8, 2.22), (x0 + 4.75, 0.98, 0.8, 1.36), (xf + 0.47, 0.96, 0.8, 1.16),
         (xf + 0.5, 0.955, 0.42, 1.14), (x0 + 5.82, 0.92, 0.45, 1.0), (x0 + 5.9, 0.86, 0.5, 0.82)]
    stations = [(x, _ring(w, z0, zt, rt=min(0.16, (zt - z0) * 0.2))) for x, w, z0, zt in S]
    # (the rear is left open: the doors stand open on the bay)
    _loft(P, stations)
    # the cargo bay: a dark lining inside the opening, its floor, the bulkhead
    K = kit.p("charcoal", "ext", lmw=0.6)
    inner = [(x, _ring(w - 0.05, z0 + 0.22, zt - 0.06, rt=0.1)) for x, w, z0, zt in S[:2]] + [(x0 + 3.6, _ring(0.94, 0.62, 2.48, rt=0.1))]
    _loft(K, inner, close_front=True, inward=True)
    # rear frame: the door aperture's ring (body to lining)
    a_out, a_in = stations[0][1], inner[0][1]
    for i in range(len(a_out)):
        j = (i + 1) % len(a_out)
        P.face([(x0, *a_out[j]), (x0, *a_out[i]), (x0 + 0.0001, *a_in[i]), (x0 + 0.0001, *a_in[j])])
    K.box((x0 + 0.02, -0.92, 0.6), (x0 + 3.6, 0.92, 0.64))
    # wheel flares (black plastic arcs) and the wheels
    for xc in (xr, xf):
        for s in (-1, 1):
            arc = [(xc + 0.56 * math.cos(a), s * (hw + 0.015), 0.4 + 0.5 * math.sin(a)) for a in [math.pi * k / 10 for k in range(11)]]
            outer = [(xc + 0.64 * math.cos(a), s * (hw + 0.015), 0.4 + 0.58 * math.sin(a)) for a in [math.pi * k / 10 for k in range(11)]]
            for k in range(10):
                q = [arc[k], arc[k + 1], outer[k + 1], outer[k]]
                T.face(q if s < 0 else q[::-1])
            with kit.at((xc, s * (hw - 0.13), R), rx=90 * s):
                kit.p("tyre", "ext", lmw=0.5).lathe([(0.21, -0.12), (0.3, -0.125), (0.355, -0.11), (0.37, -0.06), (0.37, 0.06), (0.355, 0.11), (0.3, 0.125), (0.21, 0.125)], seg=18, cap_top=False)
                kit.p("darksteel", "ext", lmw=0.4).lathe([(0.0, 0.13), (0.06, 0.13), (0.07, 0.11), (0.21, 0.1), (0.215, 0.12)], seg=16, cap_top=False)
                for k in range(5):
                    a = 2 * math.pi * k / 5
                    kit.p("black", "ext", lmw=0.1).cyl((0.13 * math.cos(a), 0.13 * math.sin(a)), 0.03, 0.105, 0.112, seg=6)
    # glass: the windshield, the cab door windows
    sl = lambda x: next(w for (xx, w, z0, zt) in S if xx >= x)
    G.face([(x0 + 4.72, -0.9, 1.4), (x0 + 4.72, 0.9, 1.4), (x0 + 4.07, 0.92, 2.36), (x0 + 4.07, -0.92, 2.36)][::-1])
    for s in (-1, 1):
        y = s * (hw + 0.004)
        wp = [(x0 + 3.95, y, 1.45), (x0 + 4.62, y, 1.45), (x0 + 4.16, y, 2.22), (x0 + 3.95, y, 2.25)]
        G.face(wp if s > 0 else wp[::-1])
        # seams: the cab door, the sliding door; handles; the mirror on its arm; the side marker
        for xs in (x0 + 3.92, x0 + 4.66, x0 + 1.75, x0 + 3.0):
            T.box((xs - 0.006, y - 0.004, 0.45), (xs + 0.006, y + 0.004, 2.25 if xs < x0 + 4.0 else 1.38))
        T.box((x0 + 3.62, y - 0.01, 1.3), (x0 + 3.8, y + s * 0.025, 1.35), bevel=0.008)
        T.box((x0 + 2.7, y - 0.01, 1.2), (x0 + 2.88, y + s * 0.025, 1.25), bevel=0.008)
        T.box((x0 + 1.75, y - 0.01, 2.2), (x0 + 3.0, y + s * 0.02, 2.23))                  # the sliding door's track
        with kit.at((x0 + 4.5, s * (hw + 0.05), 1.7)):
            T.tube([(0, 0, -0.05), (0, s * 0.12, -0.02)], 0.015, sides=6)
            T.box((-0.05, s * 0.12 - 0.08, -0.22), (0.07, s * 0.12 + 0.08, 0.12), bevel=0.03, seg=2)
        kit.p("orange", "ext", lmw=0.1).box((x0 + 0.08, y - 0.005, 2.35), (x0 + 0.16, y + s * 0.01, 2.39))
    # the nose: grille, headlamps, bumpers, plate; the rear: lamps, bumper, step, plate
    T.box((x0 + 5.85, -0.6, 0.62), (x0 + 5.93, 0.6, 0.92), bevel=0.02)
    for k in range(4):
        kit.p("black", "ext", lmw=0.1).box((x0 + 5.93, -0.55, 0.66 + k * 0.065), (x0 + 5.935, 0.55, 0.69 + k * 0.065))
    for s in (-1, 1):
        G.face([(x0 + 5.86, s * 0.66, 0.84), (x0 + 5.86, s * 0.92, 0.86), (x0 + 5.74, s * 0.93, 1.02), (x0 + 5.8, s * 0.66, 0.98)][::1 if s > 0 else -1])
        kit.p("chrome", "ext", lmw=0.1).cyl((x0 + 5.83, s * 0.8), 0.05, 0.88, 0.92, seg=10)
        kit.p("red", "ext", lmw=0.2).box((x0 - 0.02, s * 0.9 - 0.07, 1.0), (x0 + 0.03, s * 0.9 + 0.07, 1.65), bevel=0.01)
    T.box((x0 + 5.75, -1.0, 0.36), (x0 + 6.02, 1.0, 0.62), bevel=0.05, seg=2)
    T.box((x0 - 0.12, -1.0, 0.34), (x0 + 0.08, 1.0, 0.56), bevel=0.04, seg=2)
    T.box((x0 - 0.2, -0.5, 0.3), (x0 - 0.05, 0.5, 0.34))
    kit.p("white", "ext", lmw=0.1).box((x0 + 6.02, -0.26, 0.42), (x0 + 6.03, 0.26, 0.54))
    kit.p("white", "ext", lmw=0.1).box((x0 - 0.13, -0.26, 0.6), (x0 - 0.12, 0.26, 0.72))
    if doors_open:
        for s in (-1, 1):
            # each rear leaf hinged at its corner, swung ~105 degrees out along the side
            with kit.at((x0, s * 0.97, 0.42), rot=-s * 105):
                lo, hi = ((-0.05, -0.95, 0.0), (0.0, 0.0, 2.12)) if s > 0 else ((-0.05, 0.0, 0.0), (0.0, 0.95, 2.12))
                P.box(lo, hi, bevel=0.015)
                G.panel((-0.051, -0.48 if s > 0 else 0.48, 1.65), "x", 0.62, 0.5)
                T.box((-0.07, (-0.12 if s > 0 else 0.06), 1.0), (-0.05, (-0.06 if s > 0 else 0.12), 1.2))
        # the load: plastic crates, duffels, a rope coil, a folded tarp
        for k in range(3):
            for j in range(2):
                kit.p("black", "ext", lmw=0.4).box((x0 + 0.3 + k * 0.62, -0.75 + j * 0.62, 0.64), (x0 + 0.85 + k * 0.62, -0.25 + j * 0.62, 0.96), bevel=0.012)
        for k in range(2):
            with kit.at((x0 + 2.2 + k * 0.6, 0.45, 0.8), ry=90):
                kit.p("charcoal", "ext", lmw=0.3).lathe([(0, -0.3), (0.13, -0.28), (0.16, -0.1), (0.16, 0.1), (0.13, 0.28), (0.0, 0.3)], seg=8)
        rope = [(x0 + 1.0 + 0.2 * math.cos(a * 0.4), 0.55 + 0.2 * math.sin(a * 0.4), 0.66 + 0.01 * a) for a in range(40)]
        kit.p("tan", "ext", lmw=0.2).tube(rope, 0.015, sides=5)
        kit.p("blue", "ext", lmw=0.3).box((x0 + 2.8, -0.85, 0.64), (x0 + 3.5, -0.2, 0.78), bevel=0.04)
    kit.collide((x0 - 0.12, -hw, 0), (x0 + 6.02, hw, 2.6))
