"""Wall-mounted smart-home control panel (entry): a 10-inch black glass panel (240 x 160 mm)
on a satin aluminium frame standing 12 mm off the wall, the home UI glowing on it. Decor:
no interact; the screen reacts to "power" (dark in a blackout). The doorbell chime sounds from
it (see _doorbell).

Wall-mounted: origin at the panel's back centre (on the wall), front -Y; place at z = 1.45."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402

importlib.reload(ix_common)
common, materials = ix_common.common, ix_common.materials

NAME = "IX_ControlPanel"
P = dict(name=NAME, size=(0.24, 0.16, 0.012))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    alu = common.pbr_material("M_Aluminium_Satin", (0.70, 0.71, 0.72), roughness=0.32, metallic=1.0)
    glass = common.pbr_material("M_Glass_Black", (0.006, 0.006, 0.007), roughness=0.06, coat=1.0)
    w, h, t = p["size"]
    frame = common.mesh_object(f"{n}_Frame", ix_common.plate_bmesh(w + 0.006, h + 0.006, t, 0.006), col, alu, root)
    common.add_bevel(frame, 0.0015, segments=1)
    front = common.mesh_object(f"{n}_Glass", ix_common.plate_bmesh(w, h, 0.0012, 0.005), col, glass, root)
    front.location = (0, -t + 0.0002, 0)
    scr = ix_common.screen_quad(f"{n}_Screen", col, ix_common.screen_material(), root, w - 0.018, h - 0.018, -t - 0.0012)
    scr["react"] = ix_common.glow("power")
    _doorbell(n, col, root, w, h, t)
    return ix_common.finish(root)


def call_texture(w=384, h=256):
    """The panel while the doorbell rings (no words): a dark navy screen, a big glowing ring
    with a bell-dot at its centre and two ripples round it."""
    import numpy as np
    from lib import textures
    path = os.path.join(textures.TEX_DIR, "T_IX_PanelCall_Emissive.png")
    if os.path.exists(path):
        return path
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    img = np.zeros((h, w, 3), np.float32) + np.array([0.008, 0.016, 0.035])
    cyan = np.array([0.35, 0.85, 1.0])
    cx, cy = w / 2, h / 2
    d = np.hypot(x - cx, y - cy)
    img += np.clip(1 - np.abs(d - 0.26 * h) / 5.0, 0, 1)[..., None] * cyan
    for k, a in ((0.36, 0.45), (0.46, 0.2)):
        img += np.clip(1 - np.abs(d - k * h) / 3.0, 0, 1)[..., None] * cyan * a
    img += np.clip(1 - d / (0.1 * h), 0, 1)[..., None] ** 0.5 * cyan
    return textures._save("T_IX_PanelCall_Emissive", textures._to_srgb(np.clip(img, 0, 1)))


def _doorbell(n, col, root, w, h, t):
    """Distractions (viewer/devices.js): the house's doorbell chime sounds from this panel.
    Rung from the tablet's Devices page (signal "doorbell"): 4 s of chimes, loud, then it stops
    by itself; meanwhile the screen flashes a calling ring (signal "doorbell_flash")."""
    from lib import textures
    m = common.pbr_material("M_IX_PanelCall", (0.0, 0.0, 0.0), roughness=0.12)
    b = next(nd for nd in m.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    if not b.inputs["Emission Color"].is_linked:
        tex = m.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = textures.load(call_texture())
        m.node_tree.links.new(tex.outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 2.5
    call = ix_common.screen_quad(f"{n}_Call", col, m, root, w - 0.018, h - 0.018, -t - 0.0016)
    call["react"] = {"signal": "doorbell_flash", "on": "show", "off": "hide"}
    snd = common.empty(f"{n}_Chime", col, (0, -0.05, 0))
    snd.parent = root
    snd["noisemaker"] = {"signal": "doorbell", "loudness": 1.3, "every": 1.3, "for": 4.0, "sfx": "doorbell",
                         "flash": "doorbell_flash", "flashEvery": 0.5,
                         "source": "doorbell", "label": "Doorbell", "statusOn": "RINGING"}
