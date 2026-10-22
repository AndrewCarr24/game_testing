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
    """Images the house shell uses, except those used only by borrowed pieces (rugs, wall art:
    drawn with the shell for its lightmap, but prop-sized detail)."""
    with open(os.path.join(PROJECT, "assets", "models", "mansion_shell.gltf")) as f:
        g = json.load(f)
    borrowed = lambda name: name.endswith(("_Rug", "_Art"))
    mat_users = {}
    for node in g.get("nodes", []):
        if "mesh" not in node:
            continue
        for prim in g["meshes"][node["mesh"]].get("primitives", []):
            if "material" in prim:
                mat_users.setdefault(prim["material"], set()).add(borrowed(node.get("name", "")))
    keep = set()
    for mi, mat in enumerate(g.get("materials", [])):
        if mat_users.get(mi) == {True}:
            continue
        texs = [v["index"] for v in _texture_refs(mat)]
        for t in texs:
            src = g["textures"][t].get("source")
            if src is None:            # WebP via EXT_texture_webp
                src = g["textures"][t].get("extensions", {}).get("EXT_texture_webp", {}).get("source")
            if src is not None:
                keep.add(os.path.basename(g["images"][src].get("uri", "")))
    return keep


def _texture_refs(obj):
    """Every {"index": ...} texture reference inside a glTF material (any extension)."""
    if isinstance(obj, dict):
        if "index" in obj and isinstance(obj["index"], int) and len(obj) <= 4:
            yield obj
        for v in obj.values():
            yield from _texture_refs(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _texture_refs(v)


# fine detail maps shrink even when the shell uses them (a 0.25 m fabric weave at 1024 was the
# biggest single download and 5.6 MB of GPU memory, for no visible gain over 512)
ALWAYS_SHRINK = {"T_Fabric_Normal.webp"}
# rugs are drawn with the shell (to get the bake's contact shadows) but are still prop-sized detail
# (shell_textures() also leaves out whatever only rugs and wall art use)
ALWAYS_SHRINK_IF = lambda name: "Rug" in name


def main():
    keep = {n for n in shell_textures() - ALWAYS_SHRINK if not ALWAYS_SHRINK_IF(n)}
    # the Grimble is 7.3 m tall and seen from 2 m away: its colour maps keep their full size;
    # its normal maps (broad folds and fur grain) stop at 1024 (~33 MB of GPU memory saved)
    keep |= {n for n in os.listdir(TEX) if n.startswith("T_Grimble_") and "Normal" not in n}
    # [invader-character] the invader's body set is 1024 by design (seen at arm's length when it grabs
    # you; one set shared by every invader, the outfits only swap the base colour)
    keep |= {n for n in os.listdir(TEX) if n.startswith("T_Invader_")}
    shrunk = 0
    for name in sorted(os.listdir(TEX)):
        if not name.endswith((".webp", ".png", ".jpg")) or name in keep:
            continue
        path = os.path.join(TEX, name)
        img = bpy.data.images.load(path)
        w, h = img.size
        cap = 1024 if name.startswith("T_Grimble_") else MAX
        if max(w, h) > cap:
            f = cap / max(w, h)
            img.scale(max(1, round(w * f)), max(1, round(h * f)))
            img.filepath_raw = path
            img.file_format = "WEBP" if name.endswith(".webp") else img.file_format
            img.save(quality=85) if name.endswith(".webp") else img.save()
            shrunk += 1
        bpy.data.images.remove(img)
    print(f"TEXTURES shrunk {shrunk} to {MAX}px; kept {len(keep)} shell textures at full size")


main()
