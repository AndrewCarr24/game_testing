"""Ground textures for the wilderness terrain (Laurel Fork Cove): Poly Haven (CC0) photo scans,
colour maps only (the terrain shader has no normal mapping), shipped as 1024 WebP.

  python3 -I blender/wilderness/ground_textures.py        # fetch + convert (needs cwebp)

Downloads into build/wilderness/ground/src/<id>/ (its own folder, data only), writes
build/wilderness/ground/T_Wild_<Layer>.webp and ground.json (layer -> file, Poly Haven id, tile
metres). The runtime tints each layer toward the brief's palette from the texture's own mean
colour (measured at load), so swapping a scan here never changes the level's colours.
"""
import json
import os
import subprocess
import urllib.request

PROJECT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(PROJECT, "build", "wilderness", "ground")
SRC = os.path.join(OUT, "src")
UA = {"User-Agent": "game_testing-ground-fetch/1.0 (CC0 assets)"}

# layer -> (Poly Haven id, tile metres, why); the splat's channels: r grass / moss, g forest floor,
# b rock, rest path + creek bed; `bed` is the creek bed seen through the water (water shader)
LAYERS = {
    "grass": ("leafy_grass", 2.6, "hay meadow, the bald's grass, moss patches on the cove floor (tinted)"),
    "litter": ("forest_leaves_02", 2.4, "the cove floor: last autumn's leaves, brown (#4A3A28)"),
    "rock": ("lichen_rock", 4.0, "grey gneiss with pale lichen: cliffs, lookouts, the falls' amphitheatre"),
    "path": ("rocky_trail", 2.2, "worn trail dirt with roots and stones; talus"),
    "bed": ("river_small_rocks", 1.8, "gold-brown cobbles under the tea-clear creek"),
}


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def fetch(ph_id, res="1k"):
    folder = os.path.join(SRC, ph_id)
    p = os.path.join(folder, f"{ph_id}_diff_{res}.jpg")
    if os.path.exists(p):
        return p
    files = json.loads(_get(f"https://api.polyhaven.com/files/{ph_id}"))
    entry = files["Diffuse"][res]["jpg"]
    os.makedirs(folder, exist_ok=True)
    data = _get(entry["url"])
    with open(p + ".part", "wb") as fh:
        fh.write(data)
    os.replace(p + ".part", p)
    return p


def main():
    os.makedirs(OUT, exist_ok=True)
    info = {}
    for layer, (ph_id, tile, why) in LAYERS.items():
        src = fetch(ph_id)
        name = f"T_Wild_{layer.title()}.webp"
        dst = os.path.join(OUT, name)
        subprocess.run(["cwebp", "-quiet", "-q", "80", "-m", "6", "-resize", "1024", "1024", src, "-o", dst], check=True)
        info[layer] = dict(file=name, polyhaven=ph_id, tile_m=tile, bytes=os.path.getsize(dst), use=why,
                           url=f"https://polyhaven.com/a/{ph_id}", license="CC0")
        print(f"{layer:7s} {ph_id:20s} -> {name} {os.path.getsize(dst) // 1024} KB")
    with open(os.path.join(OUT, "ground.json"), "w") as fh:
        json.dump(info, fh, indent=1)


if __name__ == "__main__":
    main()
