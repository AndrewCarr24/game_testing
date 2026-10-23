"""A caged oval bulkhead light for the tunnel walls: a cast black-aluminium oval base, an opal
glass dome (`..._Glow`, lit) under a galvanised strap cage, a short grey conduit up out of the
top through a gland. About 0.28 wide, 0.12 deep, 0.18 tall (+ the conduit stub).

Origin: the centre of its back on the wall plane; it faces -Y (place on walls with rotation).
`tunnel_bulkhead_dead` builds the same with `dead=True`: lens dead, cage bent, the fixture
hanging off one screw at an angle, a cable dangling.
"""
import importlib
import math
import os
import sys

from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bunker_door  # noqa: E402

importlib.reload(bunker_door)
Geo, bk = bunker_door.Geo, bunker_door.bk
common = bk.common
materials = bk.materials

NAME = "TunnelBulkhead"

P = dict(
    name=NAME,
    dead=False,
    a=0.12,            # half width of the oval base
    b=0.09,            # half height
    base_d=0.034,      # depth of the cast base
    dome_h=0.075,      # how far the glass dome stands out of the base's front rim
    ribs=4,
    segs=16,
)


def dome_point(p, phi, th, y0):
    """Point on the dome (phi 0 = rim .. 90 degrees = apex) at angle th round the axis."""
    r = 0.93 * math.cos(phi)
    return Vector((p["a"] * r * math.cos(th), -(y0 + p["dome_h"] * math.sin(phi)), p["b"] * r * math.sin(th)))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    dead = p["dead"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    holder = root
    if dead:
        holder = common.empty(f"{n}_Hang", col)
        holder.parent = root

    body_m, cage_m, pvc, lens = materials.black_metal(), bk.galvanised(), bk.pvc(), bk.lens(not dead)
    a, b, bd = p["a"], p["b"], p["base_d"]

    # ---- cast base: a shallow oval pan with a rolled rim, mounting ears, a conduit boss on top ----
    g = Geo()
    g.oval_lathe([(1.0, 0.0), (1.0, bd - 0.006), (0.985, bd), (0.90, bd), (0.90, bd - 0.01), (0.0, bd - 0.01)],
                 a, b, segs=p["segs"])
    for sx in (-1, 1):                                                           # mounting ears with screws
        g.box((sx * (a + 0.01), -0.006, 0), (0.02, 0.012, 0.030))
    g.cyl((0, -(bd / 2), b + 0.007), 0.017, 0.022, "z", segs=8)                 # boss for the gland
    g.cyl((0, -(bd / 2), b - 0.008), 0.024, 0.016, "z", segs=10)                 # swell where the boss joins
    body = g.finish(f"{n}_Body", col, body_m, holder)

    # ---- the glass dome and its gasket ----
    prof = []
    steps = 5
    for i in range(steps + 1):
        phi = math.radians(90 * i / steps)
        prof.append((0.93 * math.cos(phi) * 0.985, bd + 0.0 + p["dome_h"] * math.sin(phi) * 0.985 - 0.006))
    g = Geo()
    g.oval_lathe(prof, a, b, segs=p["segs"])
    glow_name = f"{n}_Lens" if dead else f"{n}_Glow"
    g.finish(glow_name, col, lens, holder)

    # ---- the strap cage: ribs over the dome, two hoops, a front boss ----
    y0 = bd - 0.006
    g = Geo()
    lift = 1.035            # cage stands a hair off the glass
    thick = 0.0035
    for k in range(p["ribs"]):
        th = math.pi * 2 * k / p["ribs"] + math.pi / p["ribs"] * 0
        pts = []
        for i in range(0, 5):
            phi = math.radians(90 * i / 4)
            q = dome_point(p, phi, th, y0)
            q = Vector((q.x * lift, q.y - (lift - 1) * 0.3, q.z * lift))
            pts.append(q)
        if dead and k in (1, 2, 4):                                              # bent ribs
            bend = {1: (0.016, 0.0, 0.02), 2: (-0.012, -0.012, 0.006), 4: (0.0, -0.016, -0.02)}[k]
            pts = [q + Vector(bend) * math.sin(math.pi * i / 4) ** 1.3 for i, q in enumerate(pts)]
        for q0, q1 in zip(pts[:-1], pts[1:]):
            g.strap(q0, q1, 0.009, thick, up=(0, 1, 0))
    nr = p["segs"]
    for phi_deg, wdt in (() if dead else ((42, 0.008),)):                        # hoop (torn off on the dead one)
        phi = math.radians(phi_deg)
        ring = [dome_point(p, phi, 2 * math.pi * s / nr, y0) for s in range(nr)]
        ring = [Vector((q.x * lift, q.y - (lift - 1) * 0.3, q.z * lift)) for q in ring]
        if dead:
            ring = [q + Vector((0.01, -0.006, 0.014)) * math.sin(2 * math.pi * s / nr * 0.5) for s, q in enumerate(ring)]
        for s in range(nr):
            q0, q1 = ring[s], ring[(s + 1) % nr]
            g.strap(q0, q1, wdt, thick, up=(0, 1, 0))
    top = dome_point(p, math.radians(90), 0, y0)
    g.cyl((0, top.y - 0.002, 0), 0.014, 0.01, "y", segs=8)                      # boss where the ribs meet
    for sx in (-1, 1):                                                           # the two ear screws
        g.cyl((sx * (a + 0.01), -0.014, 0), 0.0075, 0.006, "y", segs=8)
    g.cyl((0, -(bd / 2), b + 0.019), 0.0105, 0.016, "z", segs=8)                # galvanised gland nut on the boss
    cage = g.finish(f"{n}_Cage", col, cage_m, holder)

    # ---- the conduit stub, up out of the gland ----
    g = Geo()
    g.cyl((0, -(bd / 2), b + 0.019 + 0.075), 0.0105, 0.15, "z", segs=8)
    g.cyl((0, -(bd / 2), b + 0.019 + 0.15), 0.014, 0.02, "z", segs=8)           # cut end / coupler
    g.finish(f"{n}_Conduit", col, pvc, holder)

    if dead:
        _dead(p, n, col, root, holder, pvc)

    return root, [o for o in root.children_recursive if o.type == "MESH"]


def _dead(p, n, col, root, holder, pvc):
    """Hang the fixture off its right-hand screw (the pivot), twisted and pulled off the wall at the
    left, with a cable dangling from the broken-off conduit and the left screw gone."""
    from mathutils import Euler
    a = p["a"]
    px = a + 0.01
    pivot = Vector((px, 0, 0))
    holder.location = pivot
    for ob in holder.children:                      # parts are modelled about the wall centre
        ob.location = -pivot
    rot = Euler((math.radians(-9), math.radians(34), 0)).to_matrix()
    holder.rotation_euler = Euler((math.radians(-9), math.radians(34), 0))
    g = Geo()                                       # the screw that still holds it, and a scrap of plate
    g.cyl((px, -0.007, 0), 0.0075, 0.014, "y", segs=6)
    g.box((px, -0.002, 0), (0.026, 0.004, 0.034))
    g.finish(f"{n}_Screw", col, bk.galvanised(), root)
    tip = Vector((0, -0.017, 0.255))                # the conduit's cut end, fixture coords
    w = pivot + rot @ (tip - pivot)
    pts = [w, w + Vector((-0.01, -0.03, 0.035)), w + Vector((-0.09, -0.05, 0.0)), w + Vector((-0.15, -0.045, -0.2)),
           w + Vector((-0.15, -0.04, -0.34))]
    common.tube_object(f"{n}_Cable", common.fillet_polyline(pts, 0.05, segments=1, closed=False), 0.0055, col,
                       bk.polymer(), root, closed=False, profile_res=1)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
