"""Smaller cherry blossom arrangement for the powder room: entry_flowers' generator (the same
hand-thrown ash-glazed vase, water, branches, flowers, textures and materials) with five
shorter branches, a tighter spray and its own triangle budget.
Origin: centre of the vase underside."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entry_flowers  # noqa: E402

importlib.reload(entry_flowers)
common = entry_flowers.common

NAME = "EntryFlowersSmall"
P = dict(name=NAME, branches=5, spray=(0.42, 0.62), seed=9, vase_h=0.36,
         vase_profile=entry_flowers.P["vase_profile"], vase_segs=28,
         fit=(0.54, 0.66, 0.81),        # overall size (as before)
         forks=(1, 1),
         lean=(22, 50),
         tiles=(1, 0, 5, 2),            # paler blossom: it stands against dark marble
         fallen=2,
         tris=9800)


def build(**overrides):
    return entry_flowers.build(**{**entry_flowers.P, **P, **overrides})


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
