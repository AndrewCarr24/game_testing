"""The two box parterres that flank the walks: a pale gravel bed in limestone kerbs holding a
single file of clipped box cubes, with a gap midway for the stone bench. Both sides in one
asset, mirrored about the pool axis. Garden frame (see garden_common)."""
import importlib
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garden_common as gc  # noqa: E402

importlib.reload(gc)
common, outdoor = gc.common, gc.outdoor

NAME = "GardenParterre"

P = dict(
    name=NAME,
    half_len=13.5,
    v_in=4.8,            # inner kerb face
    v_out=7.4,           # outer kerb face
    kerb=0.15,
    kerb_z=0.09,
    pitch=1.8,
    first=2.7,           # first cube from the centre (leaves the bench gap)
    cube=0.92,
    cube_h=0.78,
    seed=11,
)


def build(**overrides):
    p = {**P, **overrides}
    col, root = gc.new_asset(p["name"])
    rng = random.Random(p["seed"])
    b = gc.Builder()
    stone, gravel, leaf = outdoor.stone(), outdoor.gravel(), outdoor.foliage()
    H, k = p["half_len"], p["kerb"]
    for sy in (-1, 1):
        v0, v1 = sorted((sy * p["v_in"], sy * p["v_out"]))
        # kerbs: two long, two short
        for a0, a1 in ((v0, v0 + k), (v1 - k, v1)):
            b.box(stone, (-H, a0, 0), (H, a1, p["kerb_z"]), skip=("-z",), step=6.0, uv_tile=2.0)
        for x0, x1 in ((-H, -H + k), (H - k, H)):
            b.box(stone, (x0, v0 + k, 0), (x1, v1 - k, p["kerb_z"]), skip=("-z", "+y", "-y"), step=6.0, uv_tile=2.0)
        b.grid(gravel, (-H + k, v0 + k, gc.GRAVEL_Z), (2 * H - 2 * k, 0, 0), (0, v1 - v0 - 2 * k, 0), uv_tile=2.0)
        vc = (v0 + v1) / 2
        # paved pad for the bench in the cube gap
        b.box(stone, (-1.5, vc - 0.55, 0), (1.5, vc + 0.55, gc.PAVE_Z), skip=("-z",), uv_tile=2.0)
        x = p["first"]
        while x < H - k - p["cube"] / 2 - 0.3:
            for sx in (-1, 1):
                gc.clipped_cube(b, leaf, sx * x, vc, gc.GRAVEL_Z - 0.02, p["cube"] / 2,
                                p["cube_h"] + rng.uniform(-0.03, 0.03))
            x += p["pitch"]
    b.finish(p["name"], col, root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
