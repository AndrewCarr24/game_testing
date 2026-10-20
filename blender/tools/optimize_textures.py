"""Shrink the exported furniture textures for the web (run headless after a level build;
build_level.py does it automatically when it exports).

  Blender -b --factory-startup --python blender/tools/optimize_textures.py

Every texture in assets/models/textures/ larger than 512 px is scaled to 512, except the
ones the house shell uses (floors and walls are seen up close across whole rooms, so they
stay 1024). Prop textures at 512 cost a quarter of the GPU memory and download.
"""
import json
import os

import bpy

PROJECT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
TEX = os.path.join(PROJECT, "assets", "models", "textures")
MAX = 512


def shell_textures():
    with open(os.path.join(PROJECT, "assets", "models", "mansion_shell.gltf")) as f:
        g = json.load(f)
    return {os.path.basename(i.get("uri", "")) for i in g.get("images", [])}


# fine detail maps shrink even when the shell uses them (a 0.25 m fabric weave at 1024 was the
# biggest single download and 5.6 MB of GPU memory, for no visible gain over 512)
ALWAYS_SHRINK = {"T_Fabric_Normal.webp"}
# rugs are drawn with the shell (to get the bake's contact shadows) but are still prop-sized detail
ALWAYS_SHRINK_IF = lambda name: "Rug" in name


def main():
    keep = {n for n in shell_textures() - ALWAYS_SHRINK if not ALWAYS_SHRINK_IF(n)}
    # the Grimble is 7.3 m tall and seen from 2 m away: its textures keep their full size
    keep |= {n for n in os.listdir(TEX) if n.startswith("T_Grimble_")}
    shrunk = 0
    for name in sorted(os.listdir(TEX)):
        if not name.endswith((".webp", ".png", ".jpg")) or name in keep:
            continue
        path = os.path.join(TEX, name)
        img = bpy.data.images.load(path)
        w, h = img.size
        if max(w, h) > MAX:
            f = MAX / max(w, h)
            img.scale(max(1, round(w * f)), max(1, round(h * f)))
            img.filepath_raw = path
            img.file_format = "WEBP" if name.endswith(".webp") else img.file_format
            img.save(quality=85) if name.endswith(".webp") else img.save()
            shrunk += 1
        bpy.data.images.remove(img)
    print(f"TEXTURES shrunk {shrunk} to {MAX}px; kept {len(keep)} shell textures at full size")


main()
