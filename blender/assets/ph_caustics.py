"""Light thrown by moving water onto a wall (the bathhouse; viewer/water_fx.js fx "caustics"): an
additive card 1 cm off the wall, soft-edged, the pattern stretched upward as reflections off a
pool are. This one: the bath hall's east wall, where the low west sun off the pool lands (6.4 m
along the wall over the pool, 0.4..4.8 m up). Variants (ph_caustics_stair) set P. Origin: the
card's centre; it faces -y (place it rotated to face into the room)."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ph_common as pc  # noqa: E402

importlib.reload(pc)
common = pc.common

NAME = "PHCaustics"
P = dict(name=NAME, size=(6.4, 4.4), scale=1.5, strength=0.32, color=(1.0, 0.76, 0.48), stretch=1.8, seed=0.0)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = pc.start(n)
    w, h = p["size"]
    pc.no_bake_light(pc.card(f"{n}_NoCollide_Light", w, h, pc.fx_material(), col, root, facing="-y", fx="caustics",
                             aspect=w / h, scale=p["scale"], strength=p["strength"], color=list(p["color"]),
                             stretch=p["stretch"], seed=p["seed"]))
    return pc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
