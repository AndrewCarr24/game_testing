"""Column speaker (the great room's sound system): a slim elliptical column (200 x 160 mm,
1.09 m tall) wrapped in ink-blue acoustic fabric, a bronze cap and plinth on a
shadow-gap stem, a fine LED ring on the cap and a light line down the front that glow while
music plays, and a dark touch disc in the ring.

Interactive (prompts/interactivity.md, viewer/devices.js): the button is a switch on signal
"music" (the level renames it per room: {"signal": {"music": "music_great_room"}}); while it's
on (and the house has power) the ring glows and the speaker is a `noisemaker` the Grimble hears
(loud, until switched off here or from the tablet's Devices page). Placed as a pair, both
switch and sound together.

Origin: the centre of the plinth's underside; front faces -Y."""
import importlib
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402

importlib.reload(ix_common)
common, materials = ix_common.common, ix_common.materials

NAME = "IX_Speaker"
P = dict(name=NAME, width=0.20, depth=0.16, height=1.09, signal="music", loudness=1.2)


def _squash(ob, k):
    """Scale a lathed (round) part to the column's elliptical plan (y = depth / width)."""
    ob.scale = (1.0, k, 1.0)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    # three materials, two of them the great room's own (bronze, the ink sofa's fabric): each
    # new material is a draw call in every room batch it's in
    alu = materials.bronze()
    fabric = materials.fabric("M_Fabric_Ink", (0.018, 0.024, 0.04), roughness=0.8)
    led = materials.emissive("M_IX_SpeakerLED", (1.0, 0.80, 0.58), 8.0)

    w, d, h = p["width"], p["depth"], p["height"]
    k = d / w
    r = w / 2
    # plinth: a low rounded slab, then a dark stem (the column floats on a shadow gap)
    plinth = common.mesh_object(f"{n}_Plinth", common.rounded_slab_bmesh(w + 0.05, d + 0.05, 0.022, 0.05, segments=6),
                                col, alu, root)
    plinth.location = (0, 0, 0.011)
    common.add_bevel(plinth, 0.003, segments=2)
    stem = common.mesh_object(f"{n}_Stem", ix_common.lathe_bmesh([(0.0, 0.022), (r * 0.55, 0.022), (r * 0.55, 0.045),
                                                                  (0.0, 0.045)], segments=24), col, fabric, root)
    _squash(stem, k)
    # the column: fabric, a gentle barrel (widest at mid height), closed at both ends
    z0, z1 = 0.045, h - 0.028
    prof = [(0.0, z0), (r * 0.93, z0)]
    for i in range(1, 8):
        t = i / 8
        prof.append((r * (0.93 + 0.07 * math.sin(math.pi * t)), z0 + (z1 - z0) * t))
    prof += [(r * 0.93, z1), (0.0, z1)]
    body = common.mesh_object(f"{n}_Body", ix_common.lathe_bmesh(prof, segments=32, sharp=[1, len(prof) - 2]),
                              col, fabric, root)
    _squash(body, k)
    common.box_uv(body, 0.2)
    # cap: satin aluminium, slightly domed
    cap = common.mesh_object(f"{n}_Cap", ix_common.lathe_bmesh(
        [(0.0, z1), (r * 0.95, z1), (r * 0.97, z1 + 0.012), (r * 0.9, h - 0.004), (r * 0.6, h), (0.0, h)],
        segments=32, sharp=[1]), col, alu, root)
    _squash(cap, k)
    # LED ring round the touch button (follows the music)
    ring = common.mesh_object(f"{n}_Ring", ix_common.lathe_bmesh(
        [(r * 0.30, h - 0.002), (r * 0.30, h + 0.0008), (r * 0.36, h + 0.0008), (r * 0.36, h - 0.002)],
        segments=32, sharp=[1, 2]), col, led, root)
    _squash(ring, k)
    ring["react"] = ix_common.glow(p["signal"])
    # and a fine light line down the front at mid height (visible across the room)
    zm = z0 + (z1 - z0) * 0.5
    line = common.mesh_object(f"{n}_Line", common.box_bmesh((0.008, 0.002, 0.5)), col, led, root)
    line.location = (0, -r * k - 0.0002, zm)
    line["react"] = ix_common.glow(p["signal"])

    # touch button: a dark disc in the ring; the switch is an empty over it with no mesh of its
    # own (a touch button doesn't move, and a moving part couldn't join the room's batch)
    disc = common.mesh_object(f"{n}_Button_Disc", ix_common.lathe_bmesh(
        [(0.0, h), (r * 0.26, h), (r * 0.26, h + 0.002), (0.0, h + 0.0025)], segments=24), col, fabric, root)
    _squash(disc, k)
    btn = common.empty(f"{n}_Button", col, (0, 0, h + 0.002))
    btn.parent = root
    btn["interact"] = {"type": "switch", "signal": p["signal"], "state": False, "prompt": "Play music",
                       "promptActive": "Stop music", "range": 1.3, "duration": 0.12}

    # the sound: from the drivers' height, loud, until it's switched off
    snd = common.empty(f"{n}_Sound", col, (0, 0, 0.8))
    snd.parent = root
    snd["noisemaker"] = {"signal": p["signal"], "loudness": p["loudness"], "every": 1.5, "sfx": "music",
                         "source": "music", "label": "Music"}
    _uv_all(root)
    return ix_common.finish(root)


def _uv_all(root):
    """Every mesh gets UVs: the room batches group by material AND vertex layout, so a mesh
    without them would be a draw call of its own."""
    for ob in root.children_recursive:
        if ob.type == "MESH" and not ob.data.uv_layers:
            common.box_uv(ob, 0.25)
