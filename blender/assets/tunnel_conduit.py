"""A 6.0 m run of services along a tunnel wall: a galvanised ladder cable tray (0.3 wide) at 2.35
with black and grey cables in it, three grey conduits below it clamped to galvanised strut
brackets every 1.5 m, and a junction box where the conduits end at the +X end.

Origin: the floor point under the run's middle, on the wall plane. The run lies along x and
stands off the wall toward -Y (the wall is at y = 0). Nothing reaches below z = 1.6 (it is
mounted overhead), so it never blocks the walkway."""
import importlib
import math
import os
import random
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bunker_door  # noqa: E402

importlib.reload(bunker_door)
Geo, bk = bunker_door.Geo, bunker_door.bk
common = bk.common

NAME = "TunnelConduit"

P = dict(
    name=NAME,
    length=6.0,
    tray_z=2.35,
    tray_w=0.30,
    tray_off=0.06,            # tray's wall-side edge, off the wall
    pitch=1.5,                # bracket spacing
    conduit_z=(2.10, 1.935, 1.77),
    conduit_r=(0.016, 0.016, 0.0125),
    seed=7,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    gal, pvc, black = bk.galvanised(), bk.pvc(), bk.polymer()
    L = p["length"]
    x0, x1 = -L / 2, L / 2
    tz, tw, to = p["tray_z"], p["tray_w"], p["tray_off"]
    rng = random.Random(p["seed"])
    brackets = [x0 + 0.75 + p["pitch"] * i for i in range(int(L / p["pitch"]))]     # -2.25, -0.75, 0.75, 2.25
    box_x0, box_x1 = x1 - 0.30, x1 - 0.02            # the junction box
    ys = -(to + tw / 2)                               # tray centre line

    # ---- galvanised: tray, rungs, brackets, clamps ----
    g = Geo()
    for sy in (-1, 1):                                # side rails with a top lip turned inwards
        ry = ys + sy * (tw / 2 - 0.002)
        g.box((0, ry, tz + 0.025), (L, 0.004, 0.05))
        g.box((0, ry - sy * 0.008, tz + 0.049), (L, 0.016, 0.003))
    nr = int(L / 0.3)
    for i in range(nr + 1):                           # ladder rungs every 300 mm
        g.box((x0 + 0.02 + i * (L - 0.04) / nr, ys, tz + 0.006), (0.026, tw - 0.01, 0.005))
    for bx in brackets:
        g.box((bx, -0.02, 2.05), (0.04, 0.04, 0.92))                             # strut channel on the wall
        g.box((bx, -(to + tw) / 2 - 0.02 + 0.0, tz - 0.004), (0.04, tw + to - 0.04, 0.005))   # tray arm
        g.beam((bx, -0.045, 2.15), (bx, -(to + tw) + 0.03, tz - 0.004), (0.004, 0.036), up=(1, 0, 0))   # brace
        for cz, cr in zip(p["conduit_z"], p["conduit_r"]):                         # U-clamps round the conduits
            yc = -0.04 - cr
            g.box((bx, yc - cr - 0.003, cz), (0.034, 0.004, 2 * cr + 0.012))
            g.box((bx, yc, cz + cr + 0.003), (0.034, 2 * cr, 0.004))
            g.box((bx, yc, cz - cr - 0.003), (0.034, 2 * cr, 0.004))
    g.finish(f"{n}_Steel", col, gal, root)

    # ---- grey PVC: conduits, couplers, the junction box ----
    g = Geo()
    for cz, cr in zip(p["conduit_z"], p["conduit_r"]):
        yc = -0.04 - cr
        g.cyl(((x0 + box_x0) / 2, yc, cz), cr, box_x0 - x0, "x", segs=10)
        for cx in (x0 + 2.0, x0 + 4.0):                                           # couplers
            g.cyl((cx, yc, cz), cr + 0.004, 0.07, "x", segs=10)
        g.cyl((box_x0 + 0.015, yc, cz), cr + 0.006, 0.03, "x", segs=10)           # hub into the box
    bw, bh, bd = box_x1 - box_x0, 0.42, 0.14
    g.box(((box_x0 + box_x1) / 2, -bd / 2, 1.935), (bw, bd, bh))
    g.box(((box_x0 + box_x1) / 2, -bd - 0.004, 1.935), (bw + 0.016, 0.008, bh + 0.016))    # lid
    for sx in (-1, 1):
        for sz in (-1, 1):
            g.cyl(((box_x0 + box_x1) / 2 + sx * (bw / 2 - 0.02), -bd - 0.012, 1.935 + sz * (bh / 2 - 0.02)), 0.007, 0.008, "y", segs=6)
    for gx in (-0.07, 0.0, 0.07):                                                 # glands out of the bottom
        g.cyl(((box_x0 + box_x1) / 2 + gx, -bd / 2, 1.935 - bh / 2 - 0.017), 0.012, 0.034, "z", segs=8)
    g.finish(f"{n}_PVC", col, pvc, root)

    # ---- cables in the tray: a loose bundle, black and grey ----
    cables = [(-0.10, 0.012, black), (-0.14, 0.009, pvc), (-0.18, 0.012, black), (-0.22, 0.008, black),
              (-0.26, 0.010, pvc), (-0.29, 0.007, black)]
    made = {}
    for k, (dy, r, mat) in enumerate(cables):
        pts = []
        ph = rng.uniform(0, 6.28)
        for i in range(13):
            x = x0 + 0.01 + i * (L - 0.02) / 12
            pts.append((x, dy + 0.008 * math.sin(ph + x * 1.7), tz + 0.011 + r * (k % 2) * 0.6 + 0.003 * math.sin(ph + x * 2.3)))
        made.setdefault(mat.name, (mat, []))[1].append(
            common.tube_object(f"{n}_Cable{k}", pts, r, col, mat, root, closed=False, profile_res=1))
    for mat, objs in made.values():                  # one mesh per material
        bunker_door.lk.merge_objects(objs, f"{n}_Cables_{'Black' if mat is black else 'Grey'}", col, root)

    return root, [o for o in root.children_recursive if o.type == "MESH"]


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
