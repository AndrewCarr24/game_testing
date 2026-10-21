"""Countertop blender (kitchen): a heavy brushed-steel base (170 x 170 x 105 mm, softly
rounded) on a black plinth, a dial on its front with a fine LED ring round it, a clear
jar (1.6 l) with a black lid, half full of a green smoothie.

Interactive (prompts/interactivity.md, viewer/devices.js): the dial is a switch on signal
"blender" (renamed per room: {"signal": {"blender": "blender_kitchen"}}). On (with power) it
runs for 6 s, very loud, then stops by itself: the LED ring glows and the jar (`<n>_Jar`, its
own empty) shakes on the base. A `noisemaker` the Grimble hears; also on the tablet's
Devices page.

Origin: the centre of the base's underside; front faces -Y."""
import importlib
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402

importlib.reload(ix_common)
common, materials = ix_common.common, ix_common.materials

NAME = "IX_Blender"
P = dict(name=NAME, base=(0.17, 0.17, 0.105), signal="blender", run=6.0, loudness=1.1)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    steel = materials.steel()
    dark = materials.black_metal()
    rubber = common.pbr_material("M_Rubber_Black", (0.015, 0.015, 0.016), roughness=0.85)
    glass = materials.glass("M_Glass_Jar", tint=(0.86, 0.9, 0.9), alpha=0.16, roughness=0.03)
    smoothie = common.pbr_material("M_Smoothie_Green", (0.20, 0.36, 0.06), roughness=0.55)
    led = materials.emissive("M_IX_BlenderLED", (0.55, 0.85, 1.0), 3.0)

    bw, bd, bh = p["base"]
    foot = common.mesh_object(f"{n}_Foot", common.rounded_slab_bmesh(bw - 0.012, bd - 0.012, 0.012, 0.03, 5),
                              col, rubber, root)
    foot.location = (0, 0, 0.006)
    base = common.mesh_object(f"{n}_Base", common.rounded_slab_bmesh(bw, bd, bh - 0.012, 0.035, 6), col, steel, root)
    base.location = (0, 0, 0.012 + (bh - 0.012) / 2)
    common.add_bevel(base, 0.008, segments=3)
    common.box_uv(base, 0.2)
    # the jar's seat on top of the base
    seat = common.mesh_object(f"{n}_Seat", ix_common.lathe_bmesh(
        [(0.0, bh), (0.062, bh), (0.062, bh + 0.016), (0.0, bh + 0.016)], segments=24, sharp=[1, 2]), col, dark, root)

    # dial: its own empty on the front face (the switch); the LED ring round it
    fy = -bd / 2
    dial = common.empty(f"{n}_Dial", col, (0, fy, bh * 0.5))
    dial.parent = root
    dial["interact"] = {"type": "switch", "signal": p["signal"], "state": False, "prompt": "Run the blender",
                        "promptActive": "Stop the blender", "range": 1.3, "duration": 0.15,
                        "travel": {"axis": "z", "angle": -40}}
    knob = common.mesh_object(f"{n}_Dial_Knob", ix_common.lathe_bmesh(
        [(0.0, 0.0), (0.024, 0.0), (0.024, 0.014), (0.02, 0.018), (0.0, 0.018)], segments=24, sharp=[1]),
        col, dark, dial)
    knob.rotation_euler = (math.radians(90), 0, 0)     # lathed along +z -> sticking out along -y
    tick = common.mesh_object(f"{n}_Dial_Tick", common.box_bmesh((0.003, 0.002, 0.014)), col, steel, dial)
    tick.location = (0, -0.0185, 0.011)
    ring = common.mesh_object(f"{n}_Ring", ix_common.lathe_bmesh(
        [(0.029, 0.0), (0.029, 0.0012), (0.033, 0.0012), (0.033, 0.0)], segments=32, sharp=[1, 2]), col, led, root)
    ring.rotation_euler = (math.radians(90), 0, 0)
    ring.location = (0, fy, bh * 0.5)
    ring["react"] = ix_common.glow(p["signal"])

    # the jar: its own empty (shaken while it runs), glass walls, smoothie, lid
    jar = common.empty(f"{n}_Jar", col, (0, 0, bh + 0.016))
    jar.parent = root
    jh = 0.235
    outer = [(0.0, 0.0), (0.056, 0.0), (0.058, 0.01), (0.066, jh * 0.5), (0.074, jh), (0.0, jh)]
    shell = common.mesh_object(f"{n}_Jar_Glass", ix_common.lathe_bmesh(outer, segments=24, sharp=[1]), col, glass, jar)
    fill = common.mesh_object(f"{n}_Jar_Smoothie", ix_common.lathe_bmesh(
        [(0.0, 0.012), (0.052, 0.012), (0.058, jh * 0.45), (0.0, jh * 0.45)], segments=24, sharp=[2]),
        col, smoothie, jar)
    lid = common.mesh_object(f"{n}_Jar_Lid", ix_common.lathe_bmesh(
        [(0.0, jh - 0.004), (0.077, jh - 0.004), (0.077, jh + 0.018), (0.03, jh + 0.022), (0.03, jh + 0.034),
         (0.0, jh + 0.034)], segments=24, sharp=[1, 2, 4]), col, rubber, jar)
    # handle: a grip joined to the jar by two arms
    import bmesh
    from mathutils import Matrix
    bm = bmesh.new()
    for size, loc in (((0.018, 0.03, jh * 0.62), (0.094, 0, jh * 0.55)),
                      ((0.036, 0.026, 0.02), (0.078, 0, jh * 0.26)),
                      ((0.034, 0.026, 0.02), (0.084, 0, jh * 0.85))):
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(loc) @ Matrix.Diagonal((*size, 1.0)))
    handle = common.mesh_object(f"{n}_Jar_Handle", bm, col, dark, jar)
    common.add_bevel(handle, 0.004, segments=2)

    snd = common.empty(f"{n}_Sound", col, (0, 0, bh + 0.08))
    snd.parent = root
    snd["noisemaker"] = {"signal": p["signal"], "loudness": p["loudness"], "every": 1.0, "for": p["run"],
                         "shake": f"{n}_Jar", "sfx": "blender", "source": "blender", "label": "Blender"}
    return ix_common.finish(root)
