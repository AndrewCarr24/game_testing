"""The pump room's sump: a galvanised pit grate (rusting at the edges) in a concrete kerb with a
yellow-painted edge, two vertical blue pump motors standing on it, their discharge pipes rising,
joining through a gate valve with a red handwheel and running up to 2.6 m, then 2.0 m along +X
into the wall; a grey control box on the +X wall with two pilot lamps (the green one is lit,
`..._LED_Green`).

Footprint 2.2 (x) x 1.8 (y) x 3.0 (z), origin on the floor at the middle of the footprint, front
(the side you walk up to) faces -Y. It stands in a corner: the pipe enters the wall at x = +1.1
(the control box is hung on the same wall) and the kerb is 0.0 from y = +-0.9, so give the asset
a room corner or a 2.2 x 1.8 clear pad with the +X side at a wall.

Collision: the kerb is one solid 0.22 m slab the player steps onto and walks across (the grate
and the pit floor are NoCollide), each pump has its own box, the pipework is `Piping` (skipped:
overhead and thin), so nothing blocks but the motors and the control box.
"""
import importlib
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bunker_door  # noqa: E402

importlib.reload(bunker_door)
Geo, bk = bunker_door.Geo, bunker_door.bk
common, lk = bk.common, bunker_door.lk

NAME = "PumpStation"

P = dict(
    name=NAME,
    kerb_cx=-0.2,          # the kerb is 1.8 x 1.8 outside, a 1.6 m grate inside
    kerb_w=0.10,
    kerb_h=0.22,
    grate_top=0.19,
    pump_x=-0.30,
    pump_y=0.42,
    pipe_r=0.045,
    riser_x=-0.62,         # the pump risers
    main_x=-0.90,          # where they join and rise
    join_z=1.20,
    top_z=2.60,
    wall_x=1.10,
    valve_z=1.62,
)


def pipe(col, root, name, pts, r, mat, bend=0.12):
    return common.tube_object(name, common.fillet_polyline(pts, bend, segments=4, closed=False), r, col, mat, root,
                              closed=False, profile_res=2)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    gal, rust, blue, red = bk.galvanised(), bk.rust(), bk.pump_blue(), bk.red()
    yellow, pvc, black = bk.safety_yellow(), bk.pvc(), bk.polymer()
    concrete = bk.concrete()
    green = bk._emit("M_Pump_LED_Green", (0.15, 1.0, 0.25), 5.0)

    cx, kw, kh, gt = p["kerb_cx"], p["kerb_w"], p["kerb_h"], p["grate_top"]
    half = 0.9                                   # the kerb is 1.8 square, centred (cx, 0)
    gi = half - kw                               # the grate's half size: 0.8 -> 1.6 m

    # ---- concrete kerb: four slabs, one mesh (a solid 0.22 m step: the player walks across it) ----
    g = Geo(tile=6.0)
    g.box((cx, -(half - kw / 2), kh / 2), (2 * half, kw, kh))
    g.box((cx, half - kw / 2, kh / 2), (2 * half, kw, kh))
    g.box((cx - (half - kw / 2), 0, kh / 2), (kw, 2 * gi, kh))
    g.box((cx + (half - kw / 2), 0, kh / 2), (kw, 2 * gi, kh))
    g.finish(f"{n}_Kerb", col, concrete, root, bevel=0.004)
    g = Geo()                                    # yellow paint on the kerb's top edge, inner half
    t = 0.0025
    w = kw * 0.55
    g.box((cx, -(half - w / 2), kh + t / 2), (2 * half, w, t))
    g.box((cx, half - w / 2, kh + t / 2), (2 * half, w, t))
    g.box((cx - (half - w / 2), 0, kh + t / 2), (w, 2 * gi, t))
    g.box((cx + (half - w / 2), 0, kh + t / 2), (w, 2 * gi, t))
    g.finish(f"{n}_KerbYellow_NoCollide", col, yellow, root)

    # ---- the pit and its grate ----
    g = Geo()
    g.box((cx, 0, 0.03), (2 * gi, 2 * gi, 0.01))
    g.finish(f"{n}_PitFloor_NoCollide", col, black, root)
    g = Geo()
    nb = 40
    for i in range(nb):                                          # bearing bars along y, 40 mm pitch
        x = cx - gi + 0.02 + i * (2 * gi - 0.04) / (nb - 1)
        g.box((x, 0, gt - 0.02), (0.005, 2 * gi - 0.06, 0.04))
    for j in range(9):                                           # cross bars
        y = -gi + 0.05 + j * (2 * gi - 0.1) / 8
        g.box((cx, y, gt - 0.012), (2 * gi - 0.06, 0.008, 0.008))
    g.finish(f"{n}_Grate_NoCollide", col, gal, root)
    g = Geo()                                                    # the rusted perimeter angle + patches
    for sy in (-1, 1):
        g.box((cx, sy * (gi - 0.015), gt - 0.02), (2 * gi, 0.03, 0.04))
    for sx in (-1, 1):
        g.box((cx + sx * (gi - 0.015), 0, gt - 0.02), (0.03, 2 * gi - 0.06, 0.04))
    for (fx, fy, fl, fw) in ((-0.62, -0.74, 0.34, 0.06), (0.50, 0.74, 0.26, 0.05), (-0.74, 0.30, 0.05, 0.30),
                             (0.76, -0.35, 0.05, 0.22)):          # corroded bar ends along the frame
        g.box((cx + fx, fy, gt - 0.001), (fl, fw, 0.004))
    g.finish(f"{n}_GrateRust_NoCollide", col, rust, root)

    # ---- the two pumps ----
    px, py = p["pump_x"], p["pump_y"]
    for tag, sy in (("A", -1), ("B", 1)):
        g = Geo()
        y = sy * py
        zc = gt
        g.cyl((px, y, zc + 0.012), 0.19, 0.024, "z", segs=16)                       # base plate
        g.cyl((px, y, zc + 0.13), 0.19, 0.20, "z", segs=18, r2=0.15)                # volute casing
        g.cyl((px, y, zc + 0.265), 0.13, 0.07, "z", segs=16)                        # neck
        g.cyl((px, y, zc + 0.31), 0.19, 0.025, "z", segs=18)                        # motor foot flange
        g.cyl((px, y, zc + 0.64), 0.155, 0.63, "z", segs=18)                        # motor can
        for k in range(7):                                                          # cooling fins
            g.cyl((px, y, zc + 0.40 + k * 0.075), 0.168, 0.016, "z", segs=18)
        g.cyl((px, y, zc + 1.0), 0.16, 0.05, "z", segs=18)                          # fan cowl band
        g.cyl((px, y, zc + 1.05), 0.14, 0.06, "z", segs=18, r2=0.09)                # cowl dome
        g.torus((px, y, zc + 1.11), 0.028, 0.008, "z", segs=10, tsegs=5)            # lifting eye
        g.box((px + 0.18, y, zc + 0.62), (0.12, 0.13, 0.12))                        # terminal box
        g.box((px + 0.245, y, zc + 0.62), (0.012, 0.15, 0.14))
        g.cyl((px - 0.215, y, zc + 0.12), 0.045, 0.11, "x", segs=10)                # discharge nozzle
        g.finish(f"{n}_Pump_{tag}", col, blue, root)

    # ---- pipework (NoCollide by name: "Piping") ----
    pr = p["pipe_r"]
    rx, mx, jz, tz, wx = p["riser_x"], p["main_x"], p["join_z"], p["top_z"], p["wall_x"]
    pipes = []
    for tag, sy in (("A", -1), ("B", 1)):
        y = sy * py
        pipes.append(pipe(col, root, f"pa{tag}", [(px - 0.26, y, gt + 0.12), (rx, y, gt + 0.12), (rx, y, jz), (mx, y, jz),
                                                  (mx, 0, jz)], pr, gal))
    pipes.append(pipe(col, root, "pm", [(mx, 0, jz - 0.0), (mx, 0, tz), (wx, 0, tz)], pr * 1.2, gal, bend=0.18))
    lk.merge_objects(pipes, f"{n}_Piping_Steel", col, root)
    g = Geo()
    # flanges at the pump nozzles and either side of the valve, couplings on the run (rust)
    for sy in (-1, 1):
        g.cyl((px - 0.26, sy * py, gt + 0.12), 0.075, 0.025, "x", segs=12)
    vz = p["valve_z"]
    for dz in (-0.14, 0.14):
        g.cyl((mx, 0, vz + dz), 0.085, 0.025, "z", segs=12)
    for cxp in (-0.2, 0.55):
        g.cyl((cxp, 0, tz), pr * 1.2 + 0.014, 0.06, "x", segs=12)
    g.cyl((wx - 0.04, 0, tz), pr * 1.2 + 0.03, 0.025, "x", segs=12)                  # wall flange
    g.cyl((wx - 0.008, 0, tz), pr * 1.2 + 0.03, 0.016, "x", segs=12)
    g.cyl((mx, 0, vz), 0.075, 0.26, "z", segs=12)                                    # gate valve body
    g.box((mx, -0.05, vz), (0.11, 0.1, 0.13))                                        # bonnet block
    g.cyl((mx, -0.12, vz), 0.045, 0.12, "y", segs=10)                                # bonnet
    g.box((mx, -0.19, vz), (0.12, 0.014, 0.05))                                      # yoke
    g.cyl((mx, -0.28, vz), 0.01, 0.2, "y", segs=6)                                   # stem
    g.finish(f"{n}_Piping_Valve", col, rust, root)
    g = Geo()                                                                        # supports: strut post + clamps + rods
    postx, posty = mx, 0.115
    g.box((postx, posty, 1.32), (0.04, 0.04, 2.24))
    for cz in (1.86, 2.26):
        g.cyl((mx, 0, cz), 0.057, 0.03, "z", segs=10)
        g.box((mx, 0.07, cz), (0.05, 0.05, 0.03))
    for hx in (-0.1, 0.5):
        g.cyl((hx, 0, tz + 0.2), 0.006, 0.4, "z", segs=5)
        g.box((hx, 0, tz + 0.058), (0.03, 0.08, 0.008))
    g.finish(f"{n}_Piping_Supports", col, gal, root)
    g = Geo()                                                                        # the red handwheel
    g.torus((mx, -0.32, vz), 0.12, 0.012, "y", segs=20, tsegs=6)
    g.cyl((mx, -0.32, vz), 0.03, 0.04, "y", segs=8)
    for k in range(4):
        a = math.pi / 2 * k + math.pi / 4
        g.box((mx + 0.06 * math.cos(a), -0.32, vz + 0.06 * math.sin(a)), (0.12, 0.012, 0.012), rot=(-a, "y"))
    g.finish(f"{n}_Piping_Handwheel", col, red, root)

    # ---- the control box on the +X wall ----
    bx, by, bz = wx - 0.11, -0.1, 1.20
    g = Geo()
    g.box((bx, by, bz), (0.22, 0.42, 0.56))
    g.box((bx - 0.114, by, bz), (0.012, 0.40, 0.54))                                  # door
    g.cyl((bx, by + 0.05, bz + 0.28 + 0.1), 0.012, 0.2, "z", segs=8)                  # conduit up the wall
    g.cyl((bx, by + 0.05, bz + 0.28 + 0.012), 0.022, 0.024, "z", segs=8)
    g.finish(f"{n}_ControlBox", col, pvc, root, bevel=0.003)
    g = Geo()
    g.cyl((bx - 0.126, by - 0.12, bz + 0.16), 0.022, 0.012, "x", segs=12)
    g.finish(f"{n}_LED_Green", col, green, root)
    g = Geo()
    g.cyl((bx - 0.126, by - 0.05, bz + 0.16), 0.022, 0.012, "x", segs=12)
    g.finish(f"{n}_Lamp_Off", col, red, root)
    g = Geo()                                                                         # selector, plate, lock
    g.cyl((bx - 0.13, by + 0.05, bz + 0.08), 0.032, 0.02, "x", segs=12)
    g.box((bx - 0.13, by + 0.05, bz + 0.08), (0.012, 0.012, 0.05), rot=(0.7, "x"))
    g.box((bx - 0.121, by - 0.085, bz - 0.06), (0.004, 0.16, 0.07))
    g.cyl((bx - 0.126, by + 0.16, bz - 0.2), 0.014, 0.012, "x", segs=8)
    g.finish(f"{n}_ControlBox_Fittings_NoCollide", col, black, root)

    return root, [o for o in root.children_recursive if o.type == "MESH"]


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
