"""Replace generated texture maps with photo-scanned ones from Poly Haven (CC0), keeping
each map's file name, size, tile and average colour, so nothing else changes: the scan
supplies real grain, joints, pores and wear; the original's mean colour (the palette the
room was designed with) is kept by a per-channel gain in linear space.

  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
      --python blender/tools/polyhaven_textures.py [-- NAME ...]

For every entry in MAP: downloads the scan's diffuse map (2k JPG, cached in
build/polyhaven/), tiles it to cover our tile size, resamples it to the size our map
already has, colour-matches it and overwrites assets/textures/<name>.png (the original is
kept once in build/texture_originals/), then rewrites the exported
assets/models/textures/<name>.webp at the size the game already loads. Writes
assets/textures/polyhaven.json (what came from where). Lighting bakes are unaffected
(lightmaps hold light, not colour).

Before adding a map, check every material that uses it (grep the texture name in
blender/): a floor scan with plank joints or tile grids looks wrong on furniture that shares
the map, and a scan's grain direction must match ours (along u; see ROTATE).
"""
import json
import math
import os
import shutil
import sys
import urllib.request

import bpy
import numpy as np

PROJECT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SRC = os.path.join(PROJECT, "assets", "textures")
OUT = os.path.join(PROJECT, "assets", "models", "textures")
CACHE = os.path.join(PROJECT, "build", "polyhaven")
ORIG = os.path.join(PROJECT, "build", "texture_originals")

# our map -> (Poly Haven texture id, our tile in metres = metres one image covers in game).
# Tried and dropped as replacements (kept generated): the entry / living limestone
# (interior_tiles: small tiles, reads as a bathroom; now an overlay instead), dining slate
# (slate_floor: rustic crazy paving), garage concrete (speckled, terrazzo-like; now an
# overlay), mudroom tile (patchy, rustic). Poly Haven's tile scans run small and rustic;
# this house wants large-format, clean stone.
MAP = {
    "T_OakFloor_BaseColor":        ("laminate_floor_02", 2.0),
    "T_OakFloorPale_BaseColor":    ("laminate_floor_02", 2.0),
    "T_OakFloorSmoked_BaseColor":  ("wood_floor", 2.0),
    "T_Guest_Oak_BaseColor":       ("oak_veneer_01", 1.5),   # furniture + gym panels: veneer, no planks
    "T_Walnut_BaseColor":          ("walnut_veneer", 0.5),
    # courtyard paving AND stone furniture / coping / outdoor walls share this one: keep the
    # original (plain slabs) and add the scan's detail only (a tile scan put joints on benches)
    "T_Courtyard_Limestone_BaseColor": ("beige_wall_001", 2.0, "overlay", 0.8),
    "T_Kitchen_Stone_BaseColor":   ("grey_tiles", 2.4),
    "T_Guest_Rubber_BaseColor":    ("rubber_tiles", 1.5),
    "T_Courtyard_Teak_BaseColor":  ("teak_veneer", 0.5),
    "T_Out_Gravel_BaseColor":      ("clean_pebbles", 2.0),
    # overlay: keep the original's design (slab layout, joints, tones) and multiply in only
    # the scan's fine detail (its luminance relative to its mean), at this strength
    "T_Entry_Limestone":           ("beige_wall_001", 2.0, "overlay", 0.9),
    "T_Living_Limestone_BaseColor": ("beige_wall_001", 2.4, "overlay", 0.9),
    "T_Garage_Concrete_BaseColor": ("concrete_floor_02", 6.0, "overlay", 0.3),
}


def srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def load_rgb(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[..., :3]
    cs = img.colorspace_settings.name
    bpy.data.images.remove(img)
    # Blender gives float pixels already linear for float images; byte images come as stored (sRGB)
    return px, (w, h), cs


def resize(px, w, h):
    """Box/area resample with Blender (image.scale), in the stored colour space."""
    ih, iw, _ = px.shape
    img = bpy.data.images.new("_resize", iw, ih, alpha=False, float_buffer=True)
    img.pixels.foreach_set(np.concatenate([px, np.ones((ih, iw, 1), np.float32)], axis=2).ravel())
    img.scale(w, h)
    out = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[..., :3]
    bpy.data.images.remove(img)
    return out


def save_rgb(px_srgb, path, fmt):
    h, w, _ = px_srgb.shape
    img = bpy.data.images.new("_save", w, h, alpha=False)
    img.pixels.foreach_set(np.concatenate([px_srgb, np.ones((h, w, 1), np.float32)], axis=2).astype(np.float32).ravel())
    img.filepath_raw = path
    img.file_format = fmt
    img.save(quality=88) if fmt == "WEBP" else img.save()
    bpy.data.images.remove(img)


UA = {"User-Agent": "game_testing-texture-fetch/1.0 (Blender; CC0 assets)"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA)) as r:
        return r.read()


def fetch(ph_id):
    os.makedirs(CACHE, exist_ok=True)
    meta_path = os.path.join(CACHE, f"{ph_id}.json")
    if not os.path.exists(meta_path):
        open(meta_path, "wb").write(get(f"https://api.polyhaven.com/files/{ph_id}"))
    info = json.loads(get(f"https://api.polyhaven.com/info/{ph_id}"))
    files = json.load(open(meta_path))
    diff = files.get("Diffuse") or files.get("diffuse") or files.get("Color")
    url = diff["2k"]["jpg"]["url"]
    img_path = os.path.join(CACHE, f"{ph_id}_diff_2k.jpg")
    if not os.path.exists(img_path):
        open(img_path, "wb").write(get(url))
    size_m = (info.get("dimensions") or [2000, 2000])[0] / 1000.0
    return img_path, size_m, url


# scans whose grain runs along v, turned 90 degrees so it runs along u like our generated
# woods (box_uv puts u along a board's length; every asset is written for that)
ROTATE = {"T_Walnut_BaseColor", "T_Guest_Oak_BaseColor"}   # (the teak scan already runs along u)

# new maps made from a scan (no generated original): name -> (Poly Haven id, tile in metres,
# target mean colour (linear), detail contrast 0..1, size in px)
GENERATE = {
    # the house's warm-white walls: a painted plaster scan, kept subtle (walls are huge)
    "T_Plaster_Wall_BaseColor": ("painted_plaster_wall", 1.0, (0.72, 0.70, 0.66), 0.55, 512),
    # the courtyard floor alone (M_Courtyard_Paving): sandstone flags in random courses, a 3 m
    # scan at its real scale (slabs ~0.6-1 m); generated rather than colour-matched so the
    # scan's blue-grey slabs come out one warm grey (the brief: warm, not cold blue-grey)
    "T_Courtyard_Paving_BaseColor": ("large_grey_tiles", 3.0, (0.30, 0.275, 0.24), 0.95, 1024),
}


def generate(name, ph_id, tile, colour, contrast, size):
    img_path, size_m, url = fetch(ph_id)
    scan, _, _ = load_rgb(img_path)
    k = max(1, round(tile / size_m))
    cell = resize(scan, size // k, size // k)
    lin = srgb_to_lin(np.clip(np.tile(cell, (k, k, 1)), 0, 1))
    lum = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    detail = 1 + contrast * (lum / max(float(lum.mean()), 1e-4) - 1)
    out = np.array(colour, np.float32)[None, None, :] * detail[..., None]
    save_rgb(lin_to_srgb(out), os.path.join(SRC, f"{name}.png"), "PNG")
    print(f"GEN {name}: {ph_id} ({size_m:.2f} m, x{k} over {tile} m), {size}px")
    return {"polyhaven": ph_id, "mode": "generate", "url": f"https://polyhaven.com/a/{ph_id}", "file": url,
            "license": "CC0", "scan_metres": round(size_m, 3), "repeats": k, "our_tile_metres": tile,
            "colour": list(colour), "contrast": contrast}


def restore_dropped():
    """Maps replaced earlier but no longer in MAP go back to their generated originals."""
    for f in sorted(os.listdir(ORIG)) if os.path.isdir(ORIG) else []:
        name = f[:-4]
        if name in MAP:
            continue
        shutil.copy(os.path.join(ORIG, f), os.path.join(SRC, f))
        webp = os.path.join(OUT, f"{name}.webp")
        if os.path.exists(webp):
            cur = bpy.data.images.load(webp)
            ww, wh = cur.size
            bpy.data.images.remove(cur)
            px, _, _ = load_rgb(os.path.join(SRC, f))
            save_rgb(np.clip(resize(px, ww, wh), 0, 1), webp, "WEBP")
        os.remove(os.path.join(ORIG, f))
        print(f"RESTORED {name}")


def main(only):
    os.makedirs(ORIG, exist_ok=True)
    restore_dropped()
    manifest_path0 = os.path.join(SRC, "polyhaven.json")
    if os.path.exists(manifest_path0):
        m0 = json.load(open(manifest_path0))
        json.dump({k: v for k, v in m0.items() if k in MAP or k in GENERATE}, open(manifest_path0, "w"), indent=2)
    manifest_path = os.path.join(SRC, "polyhaven.json")
    manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}
    for name, entry in MAP.items():
        ph_id, tile = entry[:2]
        mode, strength = (entry[2], entry[3]) if len(entry) > 2 else ("replace", 1.0)
        if only and name not in only:
            continue
        src_png = os.path.join(SRC, f"{name}.png")
        orig_png = os.path.join(ORIG, f"{name}.png")
        if not os.path.exists(orig_png):
            shutil.copy(src_png, orig_png)               # the generated original, kept once
        orig, (ow, oh), _ = load_rgb(orig_png)
        target_mean = srgb_to_lin(orig).reshape(-1, 3).mean(axis=0)

        img_path, size_m, url = fetch(ph_id)
        scan, _, _ = load_rgb(img_path)                    # sRGB values as stored
        if name in ROTATE:
            scan = np.ascontiguousarray(np.rot90(scan))
        # repeats of the scan across our tile (integer, so it still tiles seamlessly)
        k = max(1, round(tile / size_m))
        cell = resize(scan, ow // k, oh // k)
        tiled = np.tile(cell, (k, k, 1))
        if tiled.shape[:2] != (oh, ow):
            tiled = resize(tiled, ow, oh)
        lin = srgb_to_lin(np.clip(tiled, 0, 1))
        if mode == "overlay":
            lum = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
            detail = lum / max(float(lum.mean()), 1e-4)
            lin = srgb_to_lin(orig) * (1 + strength * (detail - 1))[..., None]
            gain = np.ones(3)
        else:
            gain = target_mean / np.maximum(lin.reshape(-1, 3).mean(axis=0), 1e-4)
            lin = lin * gain
        srgb = lin_to_srgb(lin)
        save_rgb(srgb, src_png, "PNG")
        # the exported copy the game loads: same name, same size as now
        webp = os.path.join(OUT, f"{name}.webp")
        if os.path.exists(webp):
            cur = bpy.data.images.load(webp)
            ww, wh = cur.size
            bpy.data.images.remove(cur)
            save_rgb(lin_to_srgb(resize(lin, ww, wh)), webp, "WEBP")
        manifest[name] = {"polyhaven": ph_id, "mode": mode, "strength": strength,
                          "url": f"https://polyhaven.com/a/{ph_id}", "file": url,
                          "license": "CC0", "scan_metres": round(size_m, 3), "repeats": k,
                          "our_tile_metres": tile, "gain": [round(float(g), 3) for g in gain]}
        print(f"TEX {name}: {ph_id} {mode} ({size_m:.2f} m, x{k} over {tile} m), gain {np.round(gain, 2)}")
    for name, args in GENERATE.items():
        if only and name not in only:
            continue
        manifest[name] = generate(name, *args)
    json.dump(manifest, open(manifest_path, "w"), indent=2)


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
main(set(argv))
