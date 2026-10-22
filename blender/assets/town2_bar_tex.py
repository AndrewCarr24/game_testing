"""Textures and materials of the bar (town2_bar.py).

Scanned surfaces (Poly Haven, CC0): each scan is fetched once (build/polyhaven), resampled to
our tile and graded to the bar's palette per channel (the scan's own colour variation kept,
its mean moved to ours), written as PNG sources in build/town2_bar/tex/ (the glTF exporter
writes the WebP copies to assets/models/textures/T_Town2_Bar_*.webp).

The props atlas (ATLAS): every small thing (metals, felt, velvet, neon, bulbs, bottles, screens,
vehicles' paint, the mask) is a swatch in one 512 px atlas with its own roughness / metallic
(ORM, 256 px) and emission (256 px), so all props are one material (one draw call) inside and
one outside (the same three images; only the reflections differ)."""
import hashlib
import json
import math
import os
import urllib.request

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
CACHE = os.path.join(PROJECT, "build", "polyhaven")
SRC = os.path.join(PROJECT, "build", "town2_bar", "tex")
UA = {"User-Agent": "game_testing-texture-fetch/1.0 (Blender; CC0 assets)"}

# our map -> (Poly Haven id, our tile in metres, target mean colour (linear), contrast, px, turn 90)
SCANS = {
    "Floor":  ("old_wooden_floor_02", 2.0, (0.085, 0.056, 0.036), 1.15, 512, False),
    "Pine":   ("stained_pine", 1.8, (0.13, 0.066, 0.032), 1.0, 512, True),
    "Wood":   ("dark_wood", 2.0, (0.085, 0.034, 0.018), 1.0, 512, False),
    "Vinyl":  ("leather_red_02", 0.5, (0.19, 0.016, 0.016), 0.9, 256, False),
    "Block":  ("concrete_block_wall", 2.0, (0.15, 0.062, 0.045), 1.1, 512, False),     # painted oxblood, weathered
    "Siding": ("black_painted_planks", 1.6, (0.5, 0.5, 0.5), 1.1, 256, False),
    "Roof":   ("worn_corrugated_iron", 1.8, (0.36, 0.33, 0.3), 1.2, 256, True),
    "Deck":   ("weathered_planks", 2.0, (0.2, 0.165, 0.13), 1.05, 512, False),
    "Gravel": ("gravel", 2.5, (0.12, 0.1, 0.078), 1.1, 256, False),
}


def srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def fetch(ph_id, res="2k"):
    """The scan's diffuse (or first colour variant), cached; and its real width in metres."""
    os.makedirs(CACHE, exist_ok=True)
    meta = os.path.join(CACHE, f"{ph_id}.json")
    info_p = os.path.join(CACHE, f"{ph_id}.info.json")
    if not os.path.exists(meta):
        open(meta, "wb").write(get(f"https://api.polyhaven.com/files/{ph_id}"))
    if not os.path.exists(info_p):
        open(info_p, "wb").write(get(f"https://api.polyhaven.com/info/{ph_id}"))
    files, info = json.load(open(meta)), json.load(open(info_p))
    key = next(k for k in ("Diffuse", "diffuse", "Color", "coll1") if files.get(k))
    path = os.path.join(CACHE, f"{ph_id}_diff_{res}.jpg")
    if not os.path.exists(path):
        open(path, "wb").write(get(files[key][res]["jpg"]["url"]))
    return path, (info.get("dimensions") or [2000, 2000])[0] / 1000.0


def load_px(path):
    """Pixels as stored (sRGB for 8-bit images), rows top-down."""
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], np.float32).reshape(h, w, 4)[::-1, :, :3]
    bpy.data.images.remove(img)
    return px


def resize(px, w, h):
    ih, iw, _ = px.shape
    img = bpy.data.images.new("_t2b_resize", iw, ih, alpha=False, float_buffer=True)
    img.pixels.foreach_set(np.concatenate([px[::-1], np.ones((ih, iw, 1), np.float32)], axis=2).ravel())
    img.scale(w, h)
    out = np.array(img.pixels[:], np.float32).reshape(h, w, 4)[::-1, :, :3]
    bpy.data.images.remove(img)
    return out


def save_png(name, srgb, folder=SRC):
    """srgb rows top-down -> folder/name.png; returns the path."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name + ".png")
    h, w, _ = srgb.shape
    img = bpy.data.images.new("_t2b_save", w, h, alpha=False)
    img.pixels.foreach_set(np.concatenate([srgb[::-1], np.ones((h, w, 1), np.float32)], axis=2).astype(np.float32).ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    return path


def scan_texture(name, force=False):
    ph, tile, mean, contrast, size, turn = SCANS[name]
    key = hashlib.md5(json.dumps(SCANS[name]).encode()).hexdigest()[:8]
    out = os.path.join(SRC, f"T_Town2_Bar_{name}.png")
    stamp = out + ".key"
    if not force and os.path.exists(out) and os.path.exists(stamp) and open(stamp).read() == key:
        return out
    path, metres = fetch(ph)
    scan = load_px(path)
    k = max(1, round(tile / metres))
    cell = resize(scan, size // k, size // k)
    lin = srgb_to_lin(np.clip(np.tile(cell, (k, k, 1)), 0, 1))
    if turn:
        lin = np.rot90(lin).copy()
    m = lin.reshape(-1, 3).mean(axis=0)
    t = np.array(mean, np.float32)
    lum = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    lm = float(lum.mean())
    # per channel: the scan's variation around its own mean, moved to ours (chroma kept, softened)
    rel = lin / np.maximum(m, 1e-4)
    rel = 0.6 * rel + 0.4 * (lum / max(lm, 1e-4))[..., None]
    res = t * (1 + contrast * (rel - 1))
    save_png(f"T_Town2_Bar_{name}", lin_to_srgb(np.clip(res, 0, 1)))
    open(stamp, "w").write(key)
    print(f"TEX {name}: {ph} ({metres:.2f} m, x{k} over {tile} m) -> {size}px")
    return out


# ------------------------------------------------------------------ the props atlas
# swatch -> (cell (col, row[, w, h]), base (linear), roughness, metallic, emission (linear 0..1), pattern)
def _sw(cell, base, rough=0.5, metal=0.0, emit=(0, 0, 0), pat="flat"):
    return dict(cell=cell, base=base, rough=rough, metal=metal, emit=emit, pat=pat)


ATLAS = {
    # metals
    "chrome": _sw((0, 0), (0.80, 0.80, 0.80), 0.12, 1.0, pat="brushed"),
    "brass": _sw((1, 0), (0.72, 0.50, 0.22), 0.3, 1.0, pat="brushed"),
    "steel_dark": _sw((2, 0), (0.22, 0.22, 0.23), 0.45, 1.0, pat="brushed"),
    "iron_black": _sw((3, 0), (0.035, 0.034, 0.033), 0.55, 0.7),
    "mirror": _sw((4, 0), (0.80, 0.77, 0.72), 0.04, 1.0, pat="mirror"),
    "keg": _sw((5, 0), (0.62, 0.62, 0.62), 0.3, 1.0, pat="brushed"),
    "stainless": _sw((6, 0), (0.55, 0.55, 0.56), 0.35, 1.0, pat="brushed"),
    "galvanized": _sw((7, 0), (0.42, 0.43, 0.43), 0.55, 0.9, pat="mottle"),
    "copper": _sw((8, 0), (0.70, 0.36, 0.20), 0.35, 1.0),
    "aluminium": _sw((9, 0), (0.6, 0.6, 0.62), 0.4, 1.0, pat="brushed"),
    "rust": _sw((10, 0), (0.18, 0.07, 0.03), 0.85, 0.2, pat="mottle"),
    "gunmetal": _sw((11, 0), (0.12, 0.12, 0.13), 0.35, 1.0),
    # soft / plastic / paper
    "felt": _sw((0, 1), (0.012, 0.085, 0.035), 0.95, pat="felt"),
    "felt_rail": _sw((1, 1), (0.01, 0.06, 0.025), 0.9, pat="felt"),
    "velvet": _sw((2, 1), (0.3, 0.012, 0.018), 0.8, pat="velvet"),
    "shade_green": _sw((3, 1), (0.02, 0.12, 0.045), 0.3),
    "shade_inner": _sw((4, 1), (0.75, 0.72, 0.62), 0.5, emit=(0.5, 0.42, 0.3)),
    "rubber": _sw((5, 1), (0.018, 0.018, 0.018), 0.85),
    "plastic_black": _sw((6, 1), (0.015, 0.015, 0.016), 0.35),
    "plastic_white": _sw((7, 1), (0.62, 0.61, 0.58), 0.4),
    "plastic_red": _sw((8, 1), (0.42, 0.02, 0.02), 0.4),
    "plastic_blue": _sw((9, 1), (0.02, 0.06, 0.3), 0.4),
    "cardboard": _sw((10, 1), (0.33, 0.22, 0.12), 0.9, pat="mottle"),
    "paper": _sw((11, 1), (0.66, 0.63, 0.55), 0.85),
    "mask": _sw((12, 1), (0.76, 0.74, 0.69), 0.45, pat="mask"),
    "leather": _sw((13, 1), (0.09, 0.045, 0.02), 0.55),
    "canvas": _sw((14, 1), (0.25, 0.23, 0.17), 0.9, pat="felt"),
    "tolex": _sw((15, 1), (0.02, 0.02, 0.02), 0.7, pat="felt"),
    # paints
    "paint_white": _sw((0, 2), (0.7, 0.69, 0.64), 0.55, pat="mottle"),
    "paint_cream": _sw((1, 2), (0.6, 0.52, 0.36), 0.6, pat="mottle"),
    "paint_green": _sw((2, 2), (0.025, 0.07, 0.04), 0.5, pat="mottle"),
    "paint_red": _sw((3, 2), (0.3, 0.03, 0.02), 0.5),
    "paint_yellow": _sw((4, 2), (0.6, 0.42, 0.04), 0.5),
    "paint_black": _sw((5, 2), (0.02, 0.02, 0.02), 0.5),
    "paint_grey": _sw((6, 2), (0.2, 0.2, 0.2), 0.6, pat="mottle"),
    "safe": _sw((7, 2), (0.06, 0.08, 0.07), 0.4),
    "dumpster": _sw((8, 2), (0.03, 0.09, 0.05), 0.6, 0.3, pat="mottle"),
    "propane": _sw((9, 2), (0.72, 0.72, 0.68), 0.35, 0.2),
    "pole_wood": _sw((10, 2), (0.07, 0.05, 0.035), 0.9, pat="grain"),
    "concrete": _sw((11, 2), (0.32, 0.31, 0.29), 0.9, pat="mottle"),
    "asphalt": _sw((12, 2), (0.05, 0.05, 0.05), 0.9, pat="mottle"),
    "wood_light": _sw((13, 2), (0.32, 0.2, 0.1), 0.7, pat="grain"),
    "cooler_red": _sw((14, 2), (0.38, 0.02, 0.02), 0.35),
    "enamel_white": _sw((15, 2), (0.75, 0.74, 0.7), 0.25),
    # emissive
    "neon_pink": _sw((0, 3), (0.9, 0.3, 0.6), 0.3, emit=(1.0, 0.12, 0.42)),
    "neon_green": _sw((1, 3), (0.4, 0.9, 0.4), 0.3, emit=(0.18, 1.0, 0.26)),
    "neon_blue": _sw((2, 3), (0.4, 0.5, 0.9), 0.3, emit=(0.12, 0.32, 1.0)),
    "neon_red": _sw((3, 3), (0.9, 0.3, 0.2), 0.3, emit=(1.0, 0.07, 0.035)),
    "neon_amber": _sw((4, 3), (0.9, 0.6, 0.3), 0.3, emit=(1.0, 0.45, 0.08)),
    "neon_white": _sw((5, 3), (0.9, 0.9, 0.9), 0.3, emit=(1.0, 0.85, 0.72)),
    "neon_purple": _sw((6, 3), (0.6, 0.4, 0.9), 0.3, emit=(0.55, 0.12, 1.0)),
    "bulb": _sw((7, 3), (0.9, 0.8, 0.6), 0.2, emit=(1.0, 0.72, 0.42)),
    "bulb_dim": _sw((8, 3), (0.8, 0.6, 0.4), 0.2, emit=(0.55, 0.33, 0.14)),
    "glow_amber": _sw((9, 3), (0.8, 0.5, 0.2), 0.3, emit=(0.5, 0.24, 0.05)),
    "cooler_glow": _sw((13, 6), (0.7, 0.72, 0.75), 0.3, emit=(0.08, 0.09, 0.1)),
    "amber_glass": _sw((15, 6), (0.35, 0.15, 0.03), 0.15, emit=(0.16, 0.07, 0.012)),
    "glow_red": _sw((10, 3), (0.5, 0.05, 0.03), 0.4, emit=(0.4, 0.03, 0.015)),
    "glow_green": _sw((11, 3), (0.1, 0.4, 0.15), 0.4, emit=(0.06, 0.3, 0.1)),
    "screen_blue": _sw((12, 3), (0.05, 0.08, 0.12), 0.1, emit=(0.12, 0.2, 0.32)),
    "sodium": _sw((13, 3), (0.9, 0.6, 0.3), 0.2, emit=(1.0, 0.42, 0.08)),
    "led_white": _sw((14, 3), (0.9, 0.9, 0.9), 0.2, emit=(0.8, 0.82, 0.85)),
    "exit_red": _sw((15, 3), (0.6, 0.05, 0.04), 0.3, emit=(0.7, 0.04, 0.02)),
    # vehicles
    "truck_red": _sw((0, 4), (0.22, 0.035, 0.025), 0.45, pat="paint_old"),
    "truck_blue": _sw((1, 4), (0.035, 0.065, 0.12), 0.4, pat="paint_old"),
    "truck_white": _sw((2, 4), (0.55, 0.54, 0.5), 0.45, pat="paint_old"),
    "truck_tan": _sw((3, 4), (0.3, 0.24, 0.15), 0.5, pat="paint_old"),
    "van_black": _sw((4, 4), (0.012, 0.013, 0.014), 0.22),
    "van_grey": _sw((5, 4), (0.08, 0.085, 0.09), 0.3),
    "tire": _sw((6, 4), (0.02, 0.02, 0.02), 0.85, pat="felt"),
    "wheel_steel": _sw((7, 4), (0.35, 0.35, 0.35), 0.4, 0.9),
    "glass_dark": _sw((8, 4), (0.01, 0.012, 0.014), 0.04, 0.0),
    "headlight": _sw((9, 4), (0.7, 0.7, 0.7), 0.1, 0.5),
    "taillight": _sw((10, 4), (0.3, 0.01, 0.01), 0.15),
    "bedliner": _sw((11, 4), (0.025, 0.025, 0.025), 0.9, pat="felt"),
    "primer": _sw((12, 4), (0.15, 0.15, 0.14), 0.7, pat="mottle"),
    "mudflap": _sw((13, 4), (0.015, 0.015, 0.015), 0.8),
    "plate": _sw((14, 4), (0.6, 0.6, 0.58), 0.4, pat="plate"),
    "turn_amber": _sw((15, 4), (0.5, 0.25, 0.02), 0.15),
    # pool balls, cue, glass
    "ball_white": _sw((0, 5), (0.75, 0.73, 0.66), 0.1),
    "ball_yellow": _sw((1, 5), (0.7, 0.5, 0.02), 0.1),
    "ball_blue": _sw((2, 5), (0.02, 0.05, 0.4), 0.1),
    "ball_red": _sw((3, 5), (0.55, 0.02, 0.015), 0.1),
    "ball_purple": _sw((4, 5), (0.16, 0.02, 0.3), 0.1),
    "ball_orange": _sw((5, 5), (0.7, 0.18, 0.01), 0.1),
    "ball_green": _sw((6, 5), (0.01, 0.2, 0.06), 0.1),
    "ball_maroon": _sw((7, 5), (0.2, 0.015, 0.02), 0.1),
    "ball_black": _sw((8, 5), (0.01, 0.01, 0.01), 0.1),
    "cue": _sw((9, 5, 1, 1), (0.5, 0.36, 0.2), 0.35, pat="cue"),
    "chalk": _sw((10, 5), (0.05, 0.2, 0.5), 0.9),
    "glass_amber": _sw((11, 5), (0.32, 0.12, 0.02), 0.06, emit=(0.06, 0.02, 0.0)),
    "glass_green": _sw((12, 5), (0.03, 0.14, 0.04), 0.06, emit=(0.008, 0.03, 0.008)),
    "glass_clear": _sw((13, 5), (0.4, 0.42, 0.42), 0.04),
    "glass_brown": _sw((14, 5), (0.12, 0.04, 0.01), 0.06),
    "ice": _sw((15, 5), (0.5, 0.55, 0.58), 0.1),
    # 2x2 detail swatches
    "dartboard": _sw((0, 8, 2, 2), (0.1, 0.1, 0.1), 0.8, pat="dartboard"),
    "crt_a": _sw((2, 8, 2, 2), (0.05, 0.06, 0.07), 0.1, emit=(0.3, 0.4, 0.5), pat="crt"),
    "crt_b": _sw((4, 8, 2, 2), (0.05, 0.06, 0.07), 0.1, emit=(0.3, 0.4, 0.5), pat="crt"),
    "crt_c": _sw((6, 8, 2, 2), (0.05, 0.06, 0.07), 0.1, emit=(0.3, 0.4, 0.5), pat="crt"),
    "crt_d": _sw((8, 8, 2, 2), (0.05, 0.06, 0.07), 0.1, emit=(0.3, 0.4, 0.5), pat="crt"),
    "tv_game": _sw((10, 8, 2, 2), (0.05, 0.06, 0.07), 0.1, emit=(0.4, 0.5, 0.4), pat="tv"),
    "juke_cards": _sw((12, 8, 2, 2), (0.6, 0.58, 0.5), 0.3, emit=(0.5, 0.45, 0.35), pat="cards"),
    "grille": _sw((14, 8, 2, 1), (0.3, 0.3, 0.3), 0.4, 0.9, pat="grille"),
    "speaker": _sw((14, 9, 2, 1), (0.03, 0.03, 0.03), 0.9, pat="grille"),
    # 1x2 gradients (the jukebox's lit panels, bottles' bodies), 3x2 the pole sign's face
    "juke_orange": _sw((0, 10, 1, 2), (0.8, 0.4, 0.1), 0.2, emit=(1.0, 0.42, 0.06), pat="vgrad"),
    "juke_yellow": _sw((1, 10, 1, 2), (0.8, 0.7, 0.2), 0.2, emit=(1.0, 0.78, 0.2), pat="vgrad"),
    "juke_red": _sw((2, 10, 1, 2), (0.8, 0.1, 0.05), 0.2, emit=(1.0, 0.08, 0.03), pat="vgrad"),
    "juke_green": _sw((3, 10, 1, 2), (0.2, 0.6, 0.2), 0.2, emit=(0.2, 0.85, 0.25), pat="vgrad"),
    "juke_blue": _sw((4, 10, 1, 2), (0.2, 0.3, 0.8), 0.2, emit=(0.15, 0.3, 1.0), pat="vgrad"),
    "sign_face": _sw((5, 10, 3, 2), (0.7, 0.68, 0.6), 0.3, emit=(0.9, 0.8, 0.62), pat="sign"),
    "bulbs_marquee": _sw((8, 10, 2, 1), (0.8, 0.6, 0.3), 0.2, emit=(1.0, 0.6, 0.22)),
    "crate_label": _sw((10, 10, 2, 1), (0.4, 0.3, 0.18), 0.9, pat="crate"),
    "cig_machine": _sw((12, 10, 2, 2), (0.3, 0.3, 0.3), 0.3, emit=(0.25, 0.22, 0.18), pat="cig"),
    "beer_mirror": _sw((14, 10, 2, 2), (0.5, 0.42, 0.25), 0.1, 0.8, pat="beer_mirror"),
    "corkboard": _sw((0, 12, 2, 2), (0.3, 0.2, 0.1), 0.9, pat="cork"),
    "blueprint": _sw((2, 12, 2, 2), (0.05, 0.12, 0.3), 0.8, pat="blueprint"),
    "photos": _sw((4, 12, 2, 2), (0.3, 0.3, 0.3), 0.6, pat="photos"),
    "radio_face": _sw((6, 12, 2, 1), (0.05, 0.05, 0.05), 0.5, emit=(0.0, 0.0, 0.0), pat="radio"),
    "map_board": _sw((8, 12, 2, 2), (0.5, 0.48, 0.4), 0.8, pat="topo"),
}
# bottle bodies: 1x2 cells, glass colour, label colour, label accent, glow (lit from below)
BOTTLES = {
    "b_amber": ((0.32, 0.12, 0.02), (0.62, 0.55, 0.4), (0.3, 0.02, 0.02), (0.55, 0.24, 0.04)),
    "b_whiskey": ((0.42, 0.16, 0.03), (0.08, 0.07, 0.06), (0.6, 0.45, 0.15), (0.7, 0.3, 0.05)),
    "b_green": ((0.03, 0.15, 0.05), (0.6, 0.58, 0.5), (0.03, 0.08, 0.03), (0.06, 0.28, 0.08)),
    "b_clear": ((0.45, 0.46, 0.44), (0.7, 0.68, 0.6), (0.05, 0.05, 0.25), (0.5, 0.48, 0.4)),
    "b_rum": ((0.25, 0.08, 0.015), (0.5, 0.06, 0.04), (0.6, 0.5, 0.3), (0.5, 0.16, 0.02)),
    "b_blue": ((0.03, 0.06, 0.25), (0.7, 0.7, 0.68), (0.05, 0.05, 0.05), (0.06, 0.14, 0.5)),
    "b_tequila": ((0.5, 0.45, 0.25), (0.2, 0.25, 0.1), (0.6, 0.55, 0.35), (0.65, 0.5, 0.18)),
    "b_black": ((0.03, 0.025, 0.02), (0.6, 0.5, 0.25), (0.3, 0.02, 0.02), (0.08, 0.04, 0.01)),
    "b_gin": ((0.25, 0.4, 0.38), (0.6, 0.62, 0.6), (0.1, 0.2, 0.4), (0.3, 0.55, 0.5)),
    "b_beer": ((0.16, 0.06, 0.01), (0.55, 0.1, 0.05), (0.7, 0.65, 0.5), (0.25, 0.08, 0.01)),
    "b_wine": ((0.03, 0.06, 0.02), (0.65, 0.6, 0.5), (0.25, 0.02, 0.05), (0.05, 0.08, 0.02)),
    "b_vodka": ((0.5, 0.52, 0.52), (0.2, 0.3, 0.6), (0.7, 0.7, 0.7), (0.6, 0.6, 0.58)),
}
for k, nm in enumerate(BOTTLES):
    ATLAS[nm] = _sw((k, 6, 1, 2), BOTTLES[nm][0], 0.06, pat="bottle")
CELLS = {k: v["cell"] for k, v in ATLAS.items()}


def _rng(name):
    return np.random.default_rng(int(hashlib.md5(name.encode()).hexdigest()[:8], 16))


def _noise(h, w, rng, scale=4.0):
    n = rng.standard_normal((h, w))
    k = int(max(1, scale))
    for _ in range(2):
        n = (n + np.roll(n, k, 0) + np.roll(n, -k, 0) + np.roll(n, k, 1) + np.roll(n, -k, 1)) / 5
    return n / (np.abs(n).max() + 1e-6)


def _pattern(name, sw, h, w, plan=None):
    """(base linear (h, w, 3), emission multiplier (h, w)) of a swatch's pattern."""
    rng = _rng(name)
    base = np.ones((h, w, 3), np.float32) * np.array(sw["base"], np.float32)
    em = np.ones((h, w), np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = (xx + 0.5) / w, 1 - (yy + 0.5) / h          # v up
    p = sw["pat"]
    if p == "flat":
        base *= 1 + 0.03 * _noise(h, w, rng, 2)[..., None]
    elif p == "brushed":
        n = rng.standard_normal((h, 1)) * 0.5 + _noise(h, w, rng, 1) * 0.3
        base *= (1 + 0.06 * n)[..., None]
    elif p == "mottle":
        base *= (1 + 0.14 * _noise(h, w, rng, 3) + 0.05 * rng.standard_normal((h, w)))[..., None]
    elif p == "felt":
        base *= (1 + 0.12 * rng.standard_normal((h, w)) + 0.06 * _noise(h, w, rng, 3))[..., None]
    elif p == "velvet":
        base *= (1 + 0.1 * rng.standard_normal((h, w)))[..., None]
    elif p == "grain":
        g = np.sin(v * 40 + 3 * _noise(h, w, rng, 4)) * 0.5 + 0.5
        base *= (0.85 + 0.3 * g)[..., None]
    elif p == "mirror":
        # silvering gone at the edges (an old back-bar mirror): darker, foxed rim
        e = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
        fox = np.clip(1 - e * 6, 0, 1) * (0.5 + 0.5 * _noise(h, w, rng, 2))
        base *= (1 - 0.55 * fox)[..., None]
    elif p == "mask":
        base *= (1 + 0.04 * _noise(h, w, rng, 3))[..., None]
    elif p == "paint_old":
        base *= (1 + 0.1 * _noise(h, w, rng, 3))[..., None]
    elif p == "plate":
        band = (np.abs(v - 0.5) < 0.12)
        base[band] *= 0.4
    elif p == "cue":
        t = v
        col = np.where(t[..., None] < 0.3, np.array([0.03, 0.02, 0.015]), np.array([0.5, 0.36, 0.2]))
        col = np.where((np.abs(t - 0.3) < 0.02)[..., None], np.array([0.6, 0.6, 0.6]), col)
        base = col.astype(np.float32)
    elif p == "dartboard":
        r = np.hypot(u - 0.5, v - 0.5) * 2
        a = (np.arctan2(v - 0.5, u - 0.5) / (2 * np.pi) * 20 + 0.5) % 20
        seg = np.floor(a).astype(int) % 2
        black, cream = np.array([0.02, 0.02, 0.02]), np.array([0.55, 0.5, 0.36])
        red, green = np.array([0.35, 0.02, 0.02]), np.array([0.02, 0.18, 0.06])
        c = np.where(seg[..., None] == 0, black, cream)
        ring = ((r > 0.58) & (r < 0.63)) | ((r > 0.92) & (r < 0.98))
        c = np.where(ring[..., None], np.where(seg[..., None] == 0, red, green), c)
        c = np.where((r < 0.08)[..., None], green, c)
        c = np.where((r < 0.035)[..., None], red, c)
        c = np.where((r > 0.98)[..., None], black * 0.5, c)
        base = c.astype(np.float32)
    elif p == "crt":
        # a security camera's feed: a grey-blue scene (lawn, a house's low dark mass, sky), soft,
        # with scan lines; each of the four looks at a different part of it
        k = int(name[-1], 36) % 4 if name[-1].isalpha() else 0
        hor = 0.55 + 0.1 * k / 3
        sky = np.array([0.5, 0.58, 0.62]); lawn = np.array([0.22, 0.28, 0.25]); dark = np.array([0.08, 0.09, 0.1])
        c = np.where((v > hor)[..., None], sky, lawn)
        x0 = 0.15 + 0.18 * k
        house = (u > x0) & (u < x0 + 0.5) & (v > hor - 0.12) & (v < hor + 0.12 + 0.06 * np.sin(u * 9 + k))
        c = np.where(house[..., None], dark, c)
        win = house & (np.abs(((u - x0) * 14) % 1 - 0.5) < 0.18) & (np.abs(v - hor) < 0.05)
        c = np.where(win[..., None], np.array([0.6, 0.62, 0.55]), c)
        c = c * (0.85 + 0.15 * (np.sin(yy * np.pi * 0.5) ** 2))[..., None]
        c = c * (1 + 0.08 * rng.standard_normal((h, w)))[..., None]
        edge = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
        c = c * np.clip(edge * 10, 0.3, 1)[..., None]
        base = (c * 0.35).astype(np.float32)
        em = (np.clip(c.mean(axis=2) / 0.45, 0, 1.6)).astype(np.float32)
    elif p == "tv":
        field = np.array([0.08, 0.35, 0.1]); stands = np.array([0.25, 0.22, 0.2])
        c = np.where((v < 0.62)[..., None], field, stands)
        lines = (np.abs(((u * 5 + v * 0.5) % 1) - 0.5) < 0.02) & (v < 0.62)
        c = np.where(lines[..., None], np.array([0.7, 0.75, 0.7]), c)
        dots = (rng.random((h, w)) > 0.985) & (v < 0.55) & (v > 0.15)
        c = np.where(dots[..., None], np.array([0.6, 0.1, 0.1]), c)
        bar = (v > 0.86) & (v < 0.94) & (u > 0.05) & (u < 0.4)
        c = np.where(bar[..., None], np.array([0.1, 0.1, 0.3]), c)
        base = (c * 0.3).astype(np.float32)
        em = (c.mean(axis=2) / 0.3).astype(np.float32)
    elif p == "cards":
        # the selection cards behind the glass: rows of white strips with faint (unreadable) lines
        c = np.ones((h, w, 3)) * np.array([0.08, 0.06, 0.05])
        cu, cv = (u * 4) % 1, (v * 10) % 1
        card = (cu > 0.06) & (cu < 0.94) & (cv > 0.12) & (cv < 0.88)
        c = np.where(card[..., None], np.array([0.7, 0.66, 0.55]), c)
        ln = card & (np.abs(cv - 0.5) < 0.06) & ((rng.random((h, w)) > 0.3))
        c = np.where(ln[..., None], np.array([0.25, 0.1, 0.08]), c)
        base = c.astype(np.float32)
        em = (c.mean(axis=2) / 0.6).astype(np.float32)
    elif p == "grille":
        g = (np.sin(u * w * 0.9) * np.sin(v * h * 0.9)) > 0.1
        base *= np.where(g, 1.0, 0.25)[..., None]
    elif p == "vgrad":
        t = v
        base *= (0.6 + 0.4 * t)[..., None]
        em = (0.45 + 0.55 * np.sin(np.pi * t) ** 0.7 + 0.1 * np.sin(t * 30)).astype(np.float32)
    elif p == "sign":
        # the pole sign's backlit face: cream panel, a red border
        e = np.minimum(np.minimum(u, 1 - u) * 3, np.minimum(v, 1 - v) * 2)
        c = np.where((e < 0.12)[..., None], np.array([0.45, 0.03, 0.02]), np.array([0.75, 0.7, 0.55]))
        base = c.astype(np.float32)
        em = np.where(e < 0.12, 0.25, 1.0).astype(np.float32)
    elif p == "crate":
        base *= (1 + 0.2 * _noise(h, w, rng, 3))[..., None]
        st = np.abs(v - 0.5) < 0.18
        base[st] *= np.array([1.6, 0.4, 0.3])
    elif p == "cig":
        c = np.ones((h, w, 3)) * np.array([0.35, 0.35, 0.36])
        cu, cv = (u * 6) % 1, (v * 3) % 1
        pack = (cu > 0.15) & (cu < 0.85) & (cv > 0.3) & (cv < 0.9) & (v > 0.35)
        cols = np.array([[0.5, 0.05, 0.03], [0.7, 0.68, 0.6], [0.05, 0.1, 0.35], [0.6, 0.5, 0.1], [0.05, 0.25, 0.08], [0.4, 0.4, 0.4]])
        idx = (np.floor(u * 6).astype(int) + np.floor(v * 3).astype(int) * 2) % 6
        c = np.where(pack[..., None], cols[idx], c)
        base = c.astype(np.float32)
        em = np.where(v > 0.35, 0.9, 0.1).astype(np.float32)
    elif p == "beer_mirror":
        # a gilded-frame bar mirror with a beer glass pictogram etched in
        e = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
        c = np.where((e < 0.1)[..., None], np.array([0.5, 0.34, 0.1]), np.array([0.3, 0.3, 0.3]))
        glass = (np.abs(u - 0.5) < 0.12 - (0.7 - v) * 0.05) & (v > 0.25) & (v < 0.72)
        c = np.where(glass[..., None], np.array([0.55, 0.38, 0.08]), c)
        foam = (np.abs(u - 0.5) < 0.13) & (v > 0.66) & (v < 0.76)
        c = np.where(foam[..., None], np.array([0.7, 0.68, 0.6]), c)
        base = c.astype(np.float32)
    elif p == "cork":
        base *= (1 + 0.25 * rng.standard_normal((h, w)))[..., None]
        # pinned sheets and photos (blank: no writing), a red string between pins
        for k in range(7):
            x0, y0 = rng.uniform(0.05, 0.7), rng.uniform(0.05, 0.7)
            sx, sy = rng.uniform(0.15, 0.25), rng.uniform(0.12, 0.22)
            m = (u > x0) & (u < x0 + sx) & (v > y0) & (v < y0 + sy)
            col = np.array([0.62, 0.6, 0.55]) if k % 3 else np.array([0.2, 0.22, 0.2])
            base[m] = col
        line = np.abs((v - 0.2) - (u - 0.1) * 0.8) < 0.006
        base[line] = np.array([0.5, 0.02, 0.02])
    elif p == "blueprint":
        # a plan of the estate's house (blender/levels/plan.py rooms): white lines on blue
        c = np.ones((h, w, 3)) * np.array([0.03, 0.09, 0.28])
        if plan:
            for (x0, y0, x1, y1) in plan:
                for (a, b, cc, d) in ((x0, y0, x1, y0), (x0, y1, x1, y1), (x0, y0, x0, y1), (x1, y0, x1, y1)):
                    m = (u >= min(a, cc) - 0.004) & (u <= max(a, cc) + 0.004) & (v >= min(b, d) - 0.004) & (v <= max(b, d) + 0.004)
                    c[m] = np.array([0.6, 0.65, 0.7])
        grid = (np.abs((u * 20) % 1 - 0.5) > 0.48) | (np.abs((v * 20) % 1 - 0.5) > 0.48)
        c[grid] = c[grid] * 1.25
        base = c.astype(np.float32)
    elif p == "photos":
        c = np.ones((h, w, 3)) * np.array([0.05, 0.04, 0.03])
        for k in range(4):
            x0, y0 = (k % 2) * 0.5 + 0.04, (k // 2) * 0.5 + 0.04
            m = (u > x0) & (u < x0 + 0.42) & (v > y0) & (v < y0 + 0.42)
            sub_v = (v - y0) / 0.42
            col = np.where((sub_v > 0.55)[..., None], np.array([0.45, 0.5, 0.55]), np.array([0.2, 0.25, 0.15]))
            hs = m & (sub_v > 0.35) & (sub_v < 0.62) & (np.abs((u - x0) / 0.42 - 0.5) < 0.3)
            c = np.where(m[..., None], col, c)
            c = np.where(hs[..., None], np.array([0.6, 0.58, 0.52]), c)
        base = c.astype(np.float32)
    elif p == "radio":
        c = np.ones((h, w, 3)) * np.array([0.03, 0.03, 0.03])
        win = (u > 0.08) & (u < 0.45) & (v > 0.3) & (v < 0.75)
        c[win] = np.array([0.5, 0.25, 0.02])
        em = np.where(win, 1.0, 0.0).astype(np.float32)
        base = c.astype(np.float32)
    elif p == "topo":
        n = _noise(h, w, rng, 6)
        lines = np.abs((n * 8) % 1 - 0.5) < 0.06
        base = np.where(lines[..., None], np.array([0.3, 0.22, 0.12]), np.array([0.62, 0.6, 0.5])).astype(np.float32)
        road = np.abs(v - 0.5 - 0.2 * np.sin(u * 5)) < 0.01
        base[road] = np.array([0.5, 0.05, 0.03])
    elif p == "bottle":
        glass, label, accent, glow = [np.array(c, np.float32) for c in BOTTLES[name]]
        c = np.ones((h, w, 3)) * glass
        # v: 0 base .. 0.58 shoulder; label band 0.14..0.46; neck 0.58..0.9 (a foil band); cap
        lab = (v > 0.14) & (v < 0.46)
        c[lab] = label
        stripe = lab & (np.abs(v - 0.3) < 0.04)
        c[stripe] = accent
        foil = (v > 0.78) & (v < 0.9)
        c[foil] = accent * 0.8 + 0.1
        cap = v > 0.93
        c[cap] = np.array([0.4, 0.38, 0.3])
        # highlight streak
        c *= (1 + 0.25 * np.exp(-((u - 0.3) / 0.06) ** 2))[..., None]
        base = c.astype(np.float32)
        lit = ~lab & ~foil & ~cap
        em = np.where(lit, 0.6 + 0.8 * np.clip(1 - v, 0, 1), 0.06).astype(np.float32)
        sw = dict(sw, emit=tuple(glow))
    return base, em, sw


def atlas_textures(force=False, plan=None):
    """The props atlas: BaseColor 512, ORM 256 (G roughness, B metallic), Emissive 256."""
    key = hashlib.md5((json.dumps({k: [list(map(float, np.ravel(x))) if isinstance(x, tuple) else x for x in v.values()] for k, v in ATLAS.items()}, sort_keys=True, default=str)
                       + json.dumps(BOTTLES) + json.dumps(plan)).encode()).hexdigest()[:8]
    names = {m: os.path.join(SRC, f"T_Town2_Bar_Atlas_{m}.png") for m in ("BaseColor", "ORM", "Emissive")}
    stamp = names["BaseColor"] + ".key"
    if not force and all(os.path.exists(p) for p in names.values()) and os.path.exists(stamp) and open(stamp).read() == key:
        return names
    N, n = 512, 256
    base = np.zeros((N, N, 3), np.float32) + 0.2
    orm = np.zeros((n, n, 3), np.float32)
    orm[..., 0], orm[..., 1] = 1.0, 0.6
    emi = np.zeros((n, n, 3), np.float32)
    cs, cs2 = N // 16, n // 16
    for name, sw in ATLAS.items():
        c = sw["cell"]
        w, h = (c[2], c[3]) if len(c) > 2 else (1, 1)
        b, e, sw2 = _pattern(name, sw, h * cs, w * cs, plan)
        x0, y0 = c[0] * cs, c[1] * cs
        base[y0:y0 + h * cs, x0:x0 + w * cs] = np.clip(b, 0, 1)
        X0, Y0 = c[0] * cs2, c[1] * cs2
        orm[Y0:Y0 + h * cs2, X0:X0 + w * cs2, 1] = sw["rough"]
        orm[Y0:Y0 + h * cs2, X0:X0 + w * cs2, 2] = sw["metal"]
        if any(sw2["emit"]):
            es = resize(np.repeat(e[..., None], 3, axis=2), w * cs2, h * cs2)[..., 0]
            emi[Y0:Y0 + h * cs2, X0:X0 + w * cs2] = np.clip(np.array(sw2["emit"], np.float32) * es[..., None], 0, 1)
    save_png("T_Town2_Bar_Atlas_BaseColor", lin_to_srgb(base))
    # (ORM is data: stored linear, read Non-Color)
    save_png("T_Town2_Bar_Atlas_ORM", np.clip(orm, 0, 1))
    save_png("T_Town2_Bar_Atlas_Emissive", lin_to_srgb(emi))
    open(stamp, "w").write(key)
    print("TEX atlas: 512 base, 256 ORM, 256 emissive")
    return names


# ------------------------------------------------------------------ materials
# material key -> (texture, roughness, metallic, inside?, specular)
MATS = {
    "Floor": dict(tex="Floor", rough=0.62, inside=True),
    "Pine": dict(tex="Pine", rough=0.55, inside=True),
    "Wood": dict(tex="Wood", rough=0.32, inside=True),
    "Vinyl": dict(tex="Vinyl", rough=0.38, inside=True),
    "Props": dict(tex="Atlas", inside=True),
    "Glass": dict(tex=None, rough=0.05, inside=False, alpha=0.22),
    "Block": dict(tex="Block", rough=0.85, inside=False),
    "Siding": dict(tex="Siding", rough=0.75, inside=False),
    "Roof": dict(tex="Roof", rough=0.5, metal=0.55, inside=False),
    "Deck": dict(tex="Deck", rough=0.8, inside=False),
    "Gravel": dict(tex="Gravel", rough=0.95, inside=False),
    "PropsOut": dict(tex="Atlas", inside=False),
    "Glow": dict(tex="Glow", inside=None),
}
GLOW_STRENGTH = 2.2
TILES = {"Floor": 2.0, "Pine": 1.8, "Wood": 2.0, "Vinyl": 0.5, "Block": 2.0, "Siding": 1.6, "Roof": 1.8,
         "Deck": 2.0, "Gravel": 2.5, "Glass": 1.0}
EMISSION_STRENGTH = 4.0


def _img(path, non_color=False):
    name = os.path.splitext(os.path.basename(path))[0]
    img = bpy.data.images.get(name)
    if img is None:
        img = bpy.data.images.load(path)
        img.name = name
    img.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
    return img


def glow_texture():
    import town2_bar_glow as glow
    os.makedirs(SRC, exist_ok=True)
    rgba = glow.texture()
    path = os.path.join(SRC, "T_Town2_Bar_Glow.png")
    h, w, _ = rgba.shape
    img = bpy.data.images.new("_t2b_glow", w, h, alpha=True)
    px = rgba[::-1].copy()
    px[..., :3] = lin_to_srgb(px[..., :3])
    img.pixels.foreach_set(px.astype(np.float32).ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    return path


def materials(plan=None, force=False):
    """Blender materials for the bake (texture x the Tint colour attribute) keyed as MATS; each
    has a "_base_link" note so export_prep() can drop the tint multiply (three.js multiplies
    COLOR_0 itself)."""
    paths = {k: scan_texture(k, force) for k in SCANS}
    atl = atlas_textures(force, plan)
    out = {}
    for key, m in MATS.items():
        name = f"M_Town2_Bar_{key}"
        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        outn = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(bsdf.outputs["BSDF"], outn.inputs["Surface"])
        tint = nt.nodes.new("ShaderNodeVertexColor")
        tint.layer_name = "Tint"
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs["Factor"].default_value = 1.0
        mA, mB = [s for s in mul.inputs if s.type == "RGBA"][:2]
        mO = next(s for s in mul.outputs if s.type == "RGBA")
        nt.links.new(tint.outputs["Color"], mB)
        nt.links.new(mO, bsdf.inputs["Base Color"])
        if m["tex"] == "Glow":
            ig = nt.nodes.new("ShaderNodeTexImage"); ig.image = _img(glow_texture())
            ig.image.alpha_mode = "STRAIGHT"
            nt.links.new(ig.outputs["Color"], mA)
            nt.links.new(ig.outputs["Alpha"], bsdf.inputs["Alpha"])
            nt.links.new(ig.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = GLOW_STRENGTH
            bsdf.inputs["Roughness"].default_value = 1.0
            try:
                mat.surface_render_method = "BLENDED"
            except AttributeError:
                mat.blend_method = "BLEND"
            mat.use_backface_culling = False
        elif m["tex"] == "Atlas":
            ib = nt.nodes.new("ShaderNodeTexImage"); ib.image = _img(atl["BaseColor"])
            io = nt.nodes.new("ShaderNodeTexImage"); io.image = _img(atl["ORM"], True)
            ie = nt.nodes.new("ShaderNodeTexImage"); ie.image = _img(atl["Emissive"])
            for i in (ib, io, ie):
                i.interpolation = "Linear"
            nt.links.new(ib.outputs["Color"], mA)
            sep = nt.nodes.new("ShaderNodeSeparateColor")
            nt.links.new(io.outputs["Color"], sep.inputs["Color"])
            nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
            nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
            nt.links.new(ie.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = EMISSION_STRENGTH
        elif m["tex"]:
            ib = nt.nodes.new("ShaderNodeTexImage"); ib.image = _img(paths[m["tex"]])
            nt.links.new(ib.outputs["Color"], mA)
            bsdf.inputs["Roughness"].default_value = m.get("rough", 0.5)
            bsdf.inputs["Metallic"].default_value = m.get("metal", 0.0)
        else:
            mA.default_value = (0.02, 0.025, 0.028, 1)
            bsdf.inputs["Roughness"].default_value = m.get("rough", 0.05)
        if "alpha" in m:
            bsdf.inputs["Alpha"].default_value = m["alpha"]
            try:
                mat.surface_render_method = "BLENDED"
            except AttributeError:
                mat.blend_method = "BLEND"
        out[key] = mat
    return out


def export_prep(mat):
    """For the glTF export: base colour straight from the image (COLOR_0 carries the tint)."""
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    mix = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeMix"), None)
    if mix is None:
        return
    mA = [s for s in mix.inputs if s.type == "RGBA"][0]
    img = next((l.from_node for l in nt.links if l.to_node == mix and l.to_socket == mA), None)
    for l in list(nt.links):
        if l.to_node == bsdf and l.to_socket.name == "Base Color":
            nt.links.remove(l)
    if img is not None:
        nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = mA.default_value
