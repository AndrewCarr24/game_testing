"""Entry light sculpture: a cascade of glowing opal orbs on hair-thin black cables,
falling from a bronze ceiling canopy through the double-height hall. The strands
are longest at the centre (a teardrop silhouette), carry one to three orbs of
varied size, and two slim bronze halo rings float in the cloud.

Origin: the floor point under the fixture's centre; the canopy touches z = ceiling
(8.4 m). The lowest orb hangs about 3.5 m up, so nobody can bump into it.
Units are metres.
"""
import importlib
import math
import os
import random
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import table_lamp  # noqa: E402  (lathe, cylinder_between)

importlib.reload(common)
importlib.reload(materials)

NAME = "EntryChandelier"

P = dict(
    name=NAME,
    ceiling=8.4,
    canopy_r=1.15,
    canopy_t=0.08,
    strands=34,
    spread=1.05,             # strand anchor radius on the canopy
    z_low=3.55,              # lowest orb centre (the centre strand)
    z_high=6.3,              # shortest outer strand's orb
    orb_segments=12,
    orb_rings=7,
    halo=[(1.45, 5.25), (0.9, 4.45)],   # (radius, z) of the bronze rings
    halo_tube=0.014,
    emission=3.2,
    seed=11,
)


def orb(bm, centre, radius, segs, rings):
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=radius,
                              matrix=Matrix.Translation(centre))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])

    bronze = materials.bronze()
    black = materials.black_metal()
    opal = materials.emissive("M_Entry_Orb_Opal", (1.0, 0.86, 0.66), p["emission"])
    gold = materials.emissive("M_Entry_Orb_Gold", (1.0, 0.70, 0.36), p["emission"] * 0.9)

    zc = p["ceiling"]
    ct = p["canopy_t"]
    cr = p["canopy_r"]

    # ---- bronze canopy: a shallow rounded disc with a stepped black boss -------------
    prof = [(0.0, zc), (cr - 0.03, zc), (cr, zc - 0.02), (cr, zc - ct + 0.02), (cr - 0.03, zc - ct), (0.0, zc - ct)]
    canopy = common.mesh_object(f"{n}_Canopy", table_lamp.lathe(prof, 64, sharp=50), col, bronze, root)
    boss = common.mesh_object(
        f"{n}_Boss", table_lamp.lathe([(0.0, zc - ct), (0.55, zc - ct), (0.55, zc - ct - 0.025),
                                       (0.0, zc - ct - 0.025)], 48), col, black, root)

    # ---- strands: anchors on a Fibonacci disc, drop depends on distance from centre ----
    anchors = []
    golden = math.pi * (3 - math.sqrt(5))
    N = p["strands"]
    for i in range(N):
        r = p["spread"] * math.sqrt((i + 0.5) / N)
        a = i * golden
        anchors.append((r * math.cos(a), r * math.sin(a), r))

    orbs_a, orbs_b = bmesh.new(), bmesh.new()
    cables = bmesh.new()
    z_top = zc - ct - 0.025
    for (ax, ay, r) in anchors:
        t = (r / p["spread"])
        # teardrop: the centre hangs lowest, the rim is short; some jitter for rhythm
        z_end = p["z_low"] + (p["z_high"] - p["z_low"]) * (t ** 1.25) + rnd.uniform(-0.25, 0.25)
        # the orbs spread a little outwards as they go down (round the middle, tapering to a point)
        belly = 1.0 + 0.55 * math.sin(math.pi * min(1.0, (zc - z_end) / (zc - p["z_low"])) ** 1.0)
        ex, ey = ax * belly, ay * belly
        count = 1 + (1 if rnd.random() < 0.65 else 0) + (1 if rnd.random() < 0.3 else 0)
        zs = [z_end]
        for k in range(1, count):
            zs.append(z_end + k * rnd.uniform(0.45, 0.8))
        zs = [z for z in zs if z < z_top - 0.8]
        if not zs:
            zs = [z_end]
        low = min(zs)
        # cable from the canopy to the lowest orb of the strand
        table_lamp.cylinder_between(cables, (ax, ay, z_top), (ex, ey, low), 0.0035, segs=5)
        for z in zs:
            f = (z_top - z) / max(z_top - low, 1e-6)          # 0 at the canopy, 1 at the lowest orb
            px, py = ax + (ex - ax) * f, ay + (ey - ay) * f
            size = rnd.choice((0.075, 0.095, 0.115, 0.14)) * (1.25 if z == low else 0.85)
            target = orbs_b if rnd.random() < 0.22 else orbs_a
            orb(target, Vector((px, py, z)), size, p["orb_segments"], p["orb_rings"])

    common.mesh_object(f"{n}_OrbsOpal", orbs_a, col, opal, root)
    common.mesh_object(f"{n}_OrbsGold", orbs_b, col, gold, root)
    common.mesh_object(f"{n}_Cables", cables, col, black, root, smooth=False)

    # ---- two bronze halo rings hung on three cables each ------------------------------
    cab = bmesh.new()
    for (rr, hz) in p["halo"]:
        pts = [(rr * math.cos(2 * math.pi * s / 72), rr * math.sin(2 * math.pi * s / 72), hz) for s in range(72)]
        common.tube_object(f"{n}_Halo_{int(rr * 100)}", pts, p["halo_tube"], col, bronze, root, closed=True, profile_res=2)
        for k in range(3):
            a = math.radians(30 + 120 * k)
            table_lamp.cylinder_between(cab, (min(rr, cr - 0.1) * math.cos(a), min(rr, cr - 0.1) * math.sin(a), z_top),
                                        (rr * math.cos(a), rr * math.sin(a), hz), 0.0025, segs=5)
    common.mesh_object(f"{n}_HaloCables", cab, col, black, root, smooth=False)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
