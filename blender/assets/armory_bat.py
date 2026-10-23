"""An aluminium baseball bat for the armory (set dressing: no interact; 0.84 m / 33"): a satin
black anodised barrel (2 5/8") with a thin stainless band where the taper starts, a black
polymer end cap, black grip tape over the handle and a flared knob.

Stands upright on the barrel's end cap, handle up, the way bats lean in a rack: origin at the
centre of the end cap's base."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bunker_kit as bk  # noqa: E402
import library_kit as lk  # noqa: E402

importlib.reload(bk)
importlib.reload(lk)
common, materials = bk.common, bk.materials

NAME = "ArmoryBat"
P = dict(name=NAME, segments=14)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    s = p["segments"]

    cap, barrel, band, grip = lk.Mesh(), lk.Mesh(), lk.Mesh(), lk.Mesh()
    cap.lathe([(0.0, 0.0), (0.026, 0.0), (0.0315, 0.0035), (0.0334, 0.009), (0.0334, 0.012)], segs=s)
    barrel.lathe([(0.0333, 0.011), (0.0333, 0.40), (0.0320, 0.44), (0.0275, 0.49), (0.0215, 0.54),
                  (0.0165, 0.59), (0.0130, 0.63), (0.0122, 0.80), (0.0121, 0.810), (0.0140, 0.814),
                  (0.0215, 0.823), (0.0235, 0.830), (0.0225, 0.836), (0.016, 0.8395), (0.0, 0.84)], segs=s)
    band.lathe([(0.0337, 0.392), (0.0337, 0.404)], segs=s)
    grip.lathe([(0.0168, 0.598), (0.0149, 0.615), (0.0141, 0.68), (0.0136, 0.808)], segs=s)

    cap.to_object(f"{n}_Cap", col, bk.polymer(), root, smooth=True)
    barrel.to_object(f"{n}_Barrel", col, materials.black_metal(), root, smooth=True)
    band.to_object(f"{n}_Band", col, bk.stainless(), root, smooth=True)
    grip.to_object(f"{n}_Grip", col, bk.polymer(), root, smooth=True)
    return root, [o for o in root.children_recursive if o.type == "MESH"]


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
