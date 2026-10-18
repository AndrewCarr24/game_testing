"""Download Poly Haven (CC0) models as glTF (1k textures) into build/polyhaven/models/<id>/,
for offline renders (the horizon panorama). Usable as a module: fetch_model(id) -> .gltf path.

  python3 blender/tools/polyhaven_models.py island_tree_02 jacaranda_tree ...
"""
import json
import os
import sys
import urllib.request

PROJECT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ROOT = os.path.join(PROJECT, "build", "polyhaven", "models")
UA = {"User-Agent": "game_testing-model-fetch/1.0 (CC0 assets)"}


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA)) as r:
        return r.read()


def fetch_model(ph_id, res="1k"):
    folder = os.path.join(ROOT, ph_id)
    files = json.loads(_get(f"https://api.polyhaven.com/files/{ph_id}"))
    g = files["gltf"][res]["gltf"]
    path = os.path.join(folder, os.path.basename(g["url"]))
    if not os.path.exists(path):
        os.makedirs(folder, exist_ok=True)
        for rel, inc in g.get("include", {}).items():
            dst = os.path.join(folder, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if not os.path.exists(dst):
                open(dst, "wb").write(_get(inc["url"]))
        open(path, "wb").write(_get(g["url"]))
    return path


if __name__ == "__main__":
    for i in sys.argv[1:]:
        print(fetch_model(i))
