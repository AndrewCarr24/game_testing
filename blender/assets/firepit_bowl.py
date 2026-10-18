"""Central fire bowl: a wide shallow dark-steel bowl on a drum plinth of limestone, glowing
embers and charcoal lumps inside (outdoor.lamp), and a ring of black basalt pebbles round
the plinth. Origin: centre, bottom at z = 0 (place on the terrace top). Units are metres."""
import importlib
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import firepit_common as fc  # noqa: E402
from mathutils import Vector  # noqa: E402

importlib.reload(fc)
common, outdoor = fc.common, fc.outdoor

NAME = "FirepitBowl"
P = dict(
    name=NAME,
    plinth_r=1.0,
    plinth_h=0.22,
    pebble_r=2.0,
    bowl_r=0.80,
    bowl_top=0.60,       # rim height above the terrace
    seed=7,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = fc.new_asset(n)
    pr, ph = p["plinth_r"], p["plinth_h"]
    br, bt = p["bowl_r"], p["bowl_top"]

    # stone drum plinth (chamfered top edge)
    bm = fc.lathe_bm([(pr, 0), (pr, ph - 0.03), (pr - 0.04, ph), (0, ph)], 24, closed=False)
    bm.normal_update()
    fc.fix_outward(bm)
    fc.finish(bm, f"{n}_Plinth", col, root, outdoor.stone(), uv_tile=2.0)

    # pebble ring on the terrace (flat basalt, a hair above the paving)
    bm = bmesh.new()
    segs = 24
    ring = [(bm.verts.new(((pr + 0.0) * math.cos(t), (pr + 0.0) * math.sin(t), 0.005)),
             bm.verts.new((p["pebble_r"] * math.cos(t), p["pebble_r"] * math.sin(t), 0.005)))
            for t in (2 * math.pi * k / segs for k in range(segs))]
    for k in range(segs):
        a, b = ring[k], ring[(k + 1) % segs]
        bm.faces.new((a[0], a[1], b[1], b[0]))
    bm.normal_update()
    fc.orient_up(bm)
    fc.finish(bm, f"{n}_Pebbles", col, root, fc.basalt())

    # dark steel bowl, thin walled
    z0 = ph
    prof = [(0.34, 0.0), (0.58, 0.13), (br, bt - ph),
            (br - 0.05, bt - ph), (br - 0.08, bt - ph - 0.05), (0.0, 0.3)]
    bm = fc.lathe_bm(prof, 24, z0=z0, closed=False)
    bm.normal_update()
    fc.fix_outward(bm)
    fc.finish(bm, f"{n}_Bowl", col, root, outdoor.dark_metal())

    # embers: a glowing bed and lumps heaped inside
    rng = random.Random(p["seed"])
    bed_z = z0 + 0.36
    bm = bmesh.new()
    fc.lathe_bm([(0.64, 0), (0.60, 0.05), (0.38, 0.1), (0.0, 0.12)], 16, bm=bm, z0=bed_z - 0.03, closed=False)
    bm.normal_update()
    fc.fix_outward(bm)
    fc.finish(bm, f"{n}_EmberBed", col, root, fc.ember())

    glow, dark = bmesh.new(), bmesh.new()
    for i in range(8):
        a = rng.uniform(0, 2 * math.pi)
        d = (0.5 * math.sqrt(rng.random())) * 1.0
        r = rng.uniform(0.07, 0.12)
        target = glow if i % 3 else dark
        tmp = bmesh.new()
        bmesh.ops.create_cube(tmp, size=2.0)
        for v in tmp.verts:
            v.co = Vector((v.co.x * r * rng.uniform(0.7, 1.2), v.co.y * r * rng.uniform(0.7, 1.2),
                           v.co.z * r * rng.uniform(0.5, 0.8)))
        fc.transform(tmp, (d * math.cos(a), d * math.sin(a), bed_z + 0.09 - d * 0.1), (0, 0, rng.uniform(0, 90)))
        me = fc.bpy.data.meshes.new("_t")
        tmp.to_mesh(me)
        tmp.free()
        target.from_mesh(me)
        fc.bpy.data.meshes.remove(me)
    fc.finish(glow, f"{n}_Embers", col, root, fc.ember())
    fc.finish(dark, f"{n}_Coals", col, root, fc.coal())

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts
