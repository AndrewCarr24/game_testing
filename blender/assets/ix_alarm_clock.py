"""Bedside alarm clock: a small walnut block (130 x 62 x 72 mm) with a smoked black glass face,
amber seven-segment digits glowing behind it ("06:30"), a satin aluminium snooze bar on top
and a pin-prick alarm LED in the face's corner.

Interactive (prompts/interactivity.md, viewer/devices.js): the snooze bar is a switch on signal
"alarm" ("Set alarm"): once set (alarm LED on) it waits 10 s, then rings for 12 s, loud, the
digits blinking (signal "alarm_display", which rests on), and switches itself off; pressing it
again before then cancels it. Run after setting it: it pulls the Grimble to the room (or the
one under it). Also on the tablet's Devices page. Needs house power.

Origin: the centre of its underside; front (the face) faces -Y."""
import importlib
import os
import sys

import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402

importlib.reload(ix_common)
common, materials = ix_common.common, ix_common.materials

NAME = "IX_AlarmClock"
P = dict(name=NAME, size=(0.13, 0.062, 0.072), signal="alarm", display="alarm_display",
         delay=10.0, ring=12.0, loudness=1.2)

# seven-segment digit shapes: segments a b c d e f g
SEGS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc",
        "7": "abc", "8": "abcdefg", "9": "abcdfg"}


def digits_texture(text="06:30", w=256, h=96):
    """Amber seven-segment digits on black (the face's emission map)."""
    import numpy as np
    from lib import textures
    path = os.path.join(textures.TEX_DIR, "T_IX_ClockDigits_Emissive.png")
    if os.path.exists(path):
        return path
    img = np.zeros((h, w, 3), np.float32)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    amber = np.array([1.0, 0.42, 0.06])
    dim = np.array([0.035, 0.014, 0.003])          # unlit segments faintly visible
    dw, dh, t = 34.0, 64.0, 7.0                     # digit box and stroke
    y0 = (h - dh) / 2

    def seg(x0, y0_, x1, y1_):
        return ((x >= x0) & (x <= x1) & (y >= y0_) & (y <= y1_)).astype(np.float32)

    def digit(cx, ch):
        lit = SEGS.get(ch, "")
        l, r = cx - dw / 2, cx + dw / 2
        m = y0 + dh / 2
        boxes = {"a": (l + 2, y0, r - 2, y0 + t), "g": (l + 2, m - t / 2, r - 2, m + t / 2),
                 "d": (l + 2, y0 + dh - t, r - 2, y0 + dh),
                 "f": (l, y0 + 2, l + t, m - 2), "b": (r - t, y0 + 2, r, m - 2),
                 "e": (l, m + 2, l + t, y0 + dh - 2), "c": (r - t, m + 2, r, y0 + dh - 2)}
        out = np.zeros((h, w, 3), np.float32)
        for s, bx in boxes.items():
            out += seg(*bx)[..., None] * (amber if s in lit else dim)
        return out

    xs = [40, 84, 0, 160, 204]
    for cx, ch in zip(xs, text):
        if ch == ":":
            continue
        img += digit(cx, ch)
    for cy in (y0 + dh * 0.3, y0 + dh * 0.7):      # the colon
        img += (np.hypot(x - 122, y - cy) < 4.5)[..., None] * amber
    img = np.clip(img, 0, 1)
    return textures._save("T_IX_ClockDigits_Emissive", textures._to_srgb(img))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    walnut = materials.walnut()
    alu = common.pbr_material("M_Aluminium_Satin", (0.70, 0.71, 0.72), roughness=0.32, metallic=1.0)
    glass = common.pbr_material("M_Glass_Black", (0.006, 0.006, 0.007), roughness=0.06, coat=1.0)
    led = materials.emissive("M_IX_ClockAlarmLED", (1.0, 0.18, 0.04), 3.0)
    from lib import textures
    face_m = common.pbr_material("M_IX_ClockDigits", (0.0, 0.0, 0.0), roughness=0.1)
    b = next(nd for nd in face_m.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    if not b.inputs["Emission Color"].is_linked:
        tex = face_m.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = textures.load(digits_texture())
        face_m.node_tree.links.new(tex.outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 2.2

    w, d, h = p["size"]
    body = common.mesh_object(f"{n}_Body", common.rounded_slab_bmesh(w, d, h, 0.012, 5), col, walnut, root)
    body.location = (0, 0, h / 2)
    common.add_bevel(body, 0.003, segments=2)
    common.box_uv(body, 0.5)
    # the face: black glass, the digits glowing just behind it (both follow the display signal)
    fw, fh = w - 0.022, h - 0.026
    front = common.mesh_object(f"{n}_Glass", ix_common.plate_bmesh(fw + 0.006, fh + 0.006, 0.0015, 0.004), col, glass, root)
    front.location = (0, -d / 2 + 0.0004, h * 0.48)
    digits = ix_common.screen_quad(f"{n}_Digits", col, face_m, root, fw * 0.9, fh * 0.75, -d / 2 - 0.0016)
    digits.location.z = h * 0.48
    digits["react"] = ix_common.glow(p["display"])
    dot = common.mesh_object(f"{n}_AlarmLED", common.box_bmesh((0.003, 0.001, 0.003)), col, led, root)
    dot.location = (fw / 2 - 0.004, -d / 2 - 0.0012, h * 0.48 + fh / 2 - 0.004)
    dot["react"] = ix_common.glow(p["signal"])        # on while the alarm is set or ringing
    # snooze bar on the top; the switch is an empty over it with no mesh of its own (the bar
    # stays put, so the clock is one batch with the room)
    bm = common.rounded_slab_bmesh(w * 0.62, 0.016, 0.005, 0.004, 3)
    bmesh.ops.translate(bm, vec=(0, 0.004, h + 0.0025), verts=bm.verts)
    common.mesh_object(f"{n}_Snooze_Bar", bm, col, alu, root)
    bar = common.empty(f"{n}_Snooze", col, (0, 0.004, h + 0.005))
    bar.parent = root
    bar["interact"] = {"type": "switch", "signal": p["signal"], "state": False,
                       "prompt": f"Set alarm ({int(p['delay'])} s)", "promptActive": "Cancel alarm",
                       "range": 1.3, "duration": 0.12}

    snd = common.empty(f"{n}_Sound", col, (0, 0, h / 2))
    snd.parent = root
    snd["noisemaker"] = {"signal": p["signal"], "loudness": p["loudness"], "every": 1.0, "delay": p["delay"],
                         "for": p["ring"], "flash": p["display"], "flashRest": True, "flashEvery": 0.5,
                         "sfx": "alarm_clock", "source": "alarm_clock", "label": "Alarm clock",
                         "statusOn": "RINGING"}
    for ob in root.children_recursive:      # UVs everywhere: batches group by vertex layout too
        if ob.type == "MESH" and not ob.data.uv_layers:
            common.box_uv(ob, 0.25)
    return ix_common.finish(root)
