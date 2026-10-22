"""Poly Haven (CC0) source maps for the vegetation spike: leaf/twig atlases with their separate
alpha maps (Poly Haven's glTF downloads drop the alpha: their leaf JPEGs are RGB only) and bark
textures. Downloaded once into build/wilderness/veg/src/<id>/<id>_<map>_<res>.<ext>.

  python3 blender/wilderness/veg_sources.py            # fetch everything in SOURCES
  (in Blender) veg_sources.path("fir_tree_01", "twig_alpha") -> local file
"""
import json
import os
import sys
import urllib.request

PROJECT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ROOT = os.path.join(PROJECT, "build", "wilderness", "veg", "src")
UA = {"User-Agent": "game_testing-veg-fetch/1.0 (CC0 assets)"}

# id -> maps (Poly Haven map keys). Models' leaf atlases + texture-library barks.
SOURCES = {
    "fir_tree_01": ["twig_diff", "twig_alpha", "twig_nor_gl", "bark_diff", "bark_nor_gl"],
    "tree_small_02": ["leaves_diff", "leaves_alpha", "leaves_nor_gl"],
    "island_tree_02": ["leaves_diff", "leaves_alpha", "leaves_nor_gl"],
    "jacaranda_tree": ["leaves_diff", "leaves_alpha"],
    "fern_02": ["Diffuse", "Alpha", "nor_gl"],
    "grass_medium_01": ["Diffuse", "Alpha", "nor_gl"],
    "shrub_02": ["Diffuse", "Alpha", "nor_gl"],
    "pine_bark": ["Diffuse", "nor_gl"],
    "bark_brown_02": ["Diffuse", "nor_gl"],
    # Blue Ridge kit (design/wilderness/blue_ridge/plants.md lists which species uses which scan)
    "pine_tree_01": ["twig_diff", "twig_alpha", "twig_nor_gl"],          # long-needle twig: white pine
    "moss_01": ["Diffuse", "Alpha", "nor_gl"],                           # moss cushion atlas
    "tree_bark_03": ["Diffuse", "nor_gl"],                               # tulip poplar
    "jolcham_oak_bark_01": ["Diffuse", "nor_gl"],                        # northern red oak
    "bark_willow": ["Diffuse", "nor_gl"],                                # chestnut oak
    "bark_willow_02": ["Diffuse", "nor_gl"],                             # white oak
    "metasequoia_bark": ["Diffuse", "nor_gl"],                           # shagbark hickory, laurel stems
    "trident_maple_bark": ["Diffuse", "nor_gl"],                         # sugar maple
    "bark_platanus": ["Diffuse", "nor_gl"],                              # yellow buckeye
    "sakura_bark": ["Diffuse", "nor_gl"],                                # rhododendron stems
    "knotted_pine_bark": ["Diffuse", "nor_gl"],                          # eastern hemlock (young)
    "rough_wood": ["Diffuse", "nor_gl"],                                 # chestnut ghosts (barkless)
    "mossy_rock": ["Diffuse", "nor_gl"],                                 # creek boulders (gneiss + lichen)
    "forest_leaves_02": ["Diffuse", "nor_gl"],                           # root-wad soil / litter
}
# texture-library assets name their colour map "Diffuse" in the files API (models too, for
# single-material ones); prefer png for alpha / normal maps, jpg for colour
PREF = {"alpha": ("png", "jpg"), "nor_gl": ("png", "jpg")}


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


_files = {}


def _listing(ph_id):
    if ph_id not in _files:
        _files[ph_id] = json.loads(_get(f"https://api.polyhaven.com/files/{ph_id}"))
    return _files[ph_id]


def path(ph_id, key, res="1k"):
    """Local path of map `key` of `ph_id` at `res`, downloading it if needed."""
    folder = os.path.join(ROOT, ph_id)
    for ext in ("png", "jpg"):
        p = os.path.join(folder, f"{ph_id}_{key}_{res}.{ext}")
        if os.path.exists(p):
            return p
    entry = _listing(ph_id)[key][res]
    kind = next((k for k in PREF if k in key.lower()), None)
    ext = next(e for e in PREF.get(kind, ("jpg", "png")) if e in entry)
    p = os.path.join(folder, f"{ph_id}_{key}_{res}.{ext}")
    os.makedirs(folder, exist_ok=True)
    data = _get(entry[ext]["url"])
    with open(p + ".part", "wb") as fh:
        fh.write(data)
    os.replace(p + ".part", p)
    return p


if __name__ == "__main__":
    res = sys.argv[1] if len(sys.argv) > 1 else "1k"
    for ph_id, keys in SOURCES.items():
        for k in keys:
            print(path(ph_id, k, res))
