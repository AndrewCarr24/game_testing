"""town2_diner: the diner on Sourwood's strip (design/town/diner.md).

A restored 1950s-style stainless dining car (a 60 x 16 ft Jerry O'Mahony-type car, centre
vestibule) trucked in and set on a fieldstone plinth, with a black board-and-batten kitchen and
restroom annex behind it under a standing-seam roof: the Northeast's dining-car type with the
mountain town's polish. Parking in front off the highway, a pylon sign at the road, the service
yard behind.

Asset frame: metres, z up, origin at the lot's centre on the pad (z = 0), front (the highway)
toward -Y. build() rebuilds the collection from scratch; blender/town/diner/build.py merges it
per material, lightmaps, bakes and exports it (assets/models/town2_diner.gltf + .json).
Parts: town2_diner_car (the car's shell), _annex (kitchen + restrooms shell), _fit (the dining
room's fixtures), _kitchen (the line and the back of house), _site (the lot, sign, cars),
_props (the small things), all through town2_diner_geo.Parts with town2_diner_mats' palette.
"""
import importlib
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import town2_diner_geo as G  # noqa: E402
import town2_diner_mats as MT  # noqa: E402

MODULES = ["town2_diner_car", "town2_diner_annex", "town2_diner_rest", "town2_diner_fit", "town2_diner_kitchen", "town2_diner_site", "town2_diner_props", "town2_diner_cars", "town2_diner_lod"]
importlib.reload(G)
importlib.reload(MT)

NAME = "Town2Diner"
FZ = 0.54
P = dict(
    site=(30.0, 30.0),            # the lot (x, y); the sidecar footprint (the world builder's pad)
    height=6.2,                   # to the roof sign's top
    fz=FZ,                        # the car's (and annex's) floor over the lot
    walk_z=0.17,                  # the sidewalk's top
    lot_z=0.02,                   # the asphalt's top
    car=dict(x0=-9.15, x1=9.15, yf=0.5, yb=5.4, r=0.35),
    vest_w=2.2, vest_d=1.25, door_w=1.5, step_w=2.6,
    band=(2.62, 3.32),            # the red terrazzo band under the stools (y)
    rest_door=(-8.35, -7.35),     # openings in the car's back wall (x)
    kitchen_door=(7.3, 8.3),
    pass_=(-1.2, 1.2), pass_z=(FZ + 1.12, FZ + 1.95),
    annex=dict(x0=-8.85, x1=8.85, y0=5.4, y1=11.4),
    # colours (linear): porcelain enamel red, cream enamel, the roof, brass
    red=(0.30, 0.016, 0.014), cream=(0.60, 0.53, 0.40), ss=(1, 1, 1), roof=(0.30, 0.30, 0.31),
    brass=(0.80, 0.55, 0.25), black=(0.022, 0.022, 0.024), vinyl=(0.32, 0.018, 0.02),
    # the parked cars (town2_diner_cars.py): kind, x, y, yaw (deg: -90 = nose to +y), tint
    cars=[("wagon", -7.65, -4.55, -90, (0.16, 0.2, 0.24)), ("pickup", 10.95, -4.3, -90, (0.07, 0.11, 0.075)),
          ("van", -4.2, 13.45, 0, (0.035, 0.037, 0.04))],
)
P["pass"] = P.pop("pass_")


def build(**overrides):
    p = {**P, **overrides}
    p["car"] = dict(P["car"], **overrides.get("car", {}))
    col = _fresh(NAME)
    root = bpy.data.objects.new(NAME, None)
    col.objects.link(root)
    M = MT.palette()
    k = G.Parts(col, root)
    k.site, k.height = p["site"], p["height"]
    C = p["car"]
    fz = p["fz"]
    # interior volumes (parts centred in them take the atlas's interior half)
    k.inside.append(((C["x0"] + 0.1, C["yf"] + 0.1, fz - 0.06), (C["x1"] - 0.1, C["yb"] - 0.05, fz + 3.0)))
    k.inside.append(((-p["vest_w"] / 2 + 0.05, C["yf"] - p["vest_d"] + 0.1, fz - 0.07), (p["vest_w"] / 2 - 0.05, C["yf"] + 0.1, fz + 2.3)))
    A = p["annex"]
    k.inside.append(((A["x0"] + 0.1, A["y0"], fz - 0.06), (A["x1"] - 0.1, A["y1"] - 0.1, fz + 2.5)))
    cams(k, p)
    for name in MODULES:
        try:
            mod = importlib.import_module(name)
        except ModuleNotFoundError as e:
            if e.name != name:
                raise
            print("diner: skip", name)
            continue
        importlib.reload(mod)
        mod.build(k, M, p)
    k.dead = dead_volumes(p)
    return root, k


def dead_volumes(p):
    """Where nobody can look (build.py deletes faces that face only into these): under the
    floors, inside the car's wall cavities (above and below the window band), above the vault
    and the annex ceiling, under the lot."""
    C, A, fz = p["car"], p["annex"], p["fz"]
    ceil = C["ceil_z"]
    vx, vy0 = p["vest_w"] / 2, C["yf"] - p["vest_d"]
    zw0, zw1, ze = C["zw0"], C["zw1"], C["ze"]

    def box(lo, hi):
        return lambda x, y, z: lo[0] < x < hi[0] and lo[1] < y < hi[1] and lo[2] < z < hi[2]
    r = C["r"]

    def in_car(x, y, e=0.012):
        """Inside the car's rounded plan outline (by e)."""
        qx = max(abs(x - (C["x0"] + C["x1"]) / 2) - ((C["x1"] - C["x0"]) / 2 - r), 0.0)
        qy = max(abs(y - (C["yf"] + C["yb"]) / 2) - ((C["yb"] - C["yf"]) / 2 - r), 0.0)
        return (qx * qx + qy * qy) ** 0.5 < r - e
    d = [
        lambda x, y, z: z < fz - 0.03 and z > -2 and in_car(x, y),
        box((-vx + 0.05, vy0 + 0.05, -2), (vx - 0.05, C["yf"] + 0.01, fz - 0.03)),
        box((A["x0"], A["y0"] - 0.01, -2), (A["x1"], A["y1"], fz - 0.03)),
        box((-20, -20, -5), (20, 20, -0.005)),                                     # under the lot
        # the car's cavities: front (both halves), ends; below the sill, above the head
        lambda x, y, z: (C["yf"] + 0.005 < y < C["yi0"] - 0.005 or C["yi1"] + 0.005 < y < C["yb"] - 0.005 or
                         x < C["xi0"] - 0.005 or x > C["xi1"] + 0.005)
        and in_car(x, y)
        and (fz - 0.1 < z < zw0 - 0.035 or zw1 + 0.05 < z < ze + 0.02),
        # above the vault, under the barrel roof
        lambda x, y, z: in_car(x, y, 0.0) and ceil(y) + 0.01 < z < C["roof_z"](y) - 0.01,
        # above the annex ceiling
        box((A["x0"], A["y0"], A["cz"] + 0.03), (A["x1"], A["y1"], fz + 2.6)),
    ]
    return d


def cams(k, p):
    fz = p["fz"]
    k.cameras.update({
        "front": ((7.5, -16.5, 1.65), (-1.0, 2.5, 1.9), 26),
        "corner": ((-17.0, -12.0, 1.7), (-3.0, 3.0, 1.6), 24),
        "aerial": ((14.0, -24.0, 14.0), (0.0, 3.0, 0.0), 30),
        "counter": ((7.8, 1.5, fz + 1.62), (-6.0, 4.2, fz + 0.9), 18),
        "booths": ((-8.3, 2.4, fz + 1.55), (4.0, 1.0, fz + 0.9), 18),
        "door": ((0.0, 1.1, fz + 1.6), (0.0, 7.0, fz + 1.2), 16),
        "pass": ((0.2, 2.3, fz + 1.55), (0.0, 7.5, fz + 1.3), 22),
        "kitchen": ((6.4, 6.9, fz + 1.65), (-3.0, 6.9, fz + 0.9), 16),
        "back": ((12.0, 18.0, 2.2), (2.0, 8.0, 1.2), 22),
        "far": ((70.0, -22.0, 1.7), (0.0, 0.0, 2.0), 30),
        "far2": ((-130.0, -25.0, 1.7), (0.0, 0.0, 2.0), 30),
        "farup": ((30.0, -110.0, 45.0), (0.0, 0.0, 0.0), 30),
        "turn": ((3.5, 2.45, fz + 1.5), (2.2, 1.0, fz + 0.45), 20),
        "juke": ((-5.4, 2.6, fz + 1.6), (-8.9, 3.6, fz + 1.1), 20),
        "rest": ((-6.35, 8.6, fz + 1.6), (-8.3, 10.7, fz + 0.6), 16),
        "lot": ((-6.0, -11.5, 0.45), (0.0, 1.0, 2.6), 20),
    })


def _fresh(name):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    for ob in list(col.all_objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    return col
