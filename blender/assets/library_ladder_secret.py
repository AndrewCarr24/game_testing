"""The library's rolling ladder as the latch of the secret passage (design/house/secret_passage.md):
the same walnut-and-bronze ladder (library_ladder.py), but the whole ladder is a `switch`: E rolls
it along its rail to the far end (`travel`), which sets signal "secret_library" and the floor at
its foot folds down into a stair (house.py fold_floor); E again rolls it back and the floor
closes. Nothing says so: it reads as pushing a library ladder, and the floor answers.

Origin as library_ladder (on the floor under the rail); `travel` is along the asset's x (glTF x),
so with the south wall's rotation 180 a negative distance rolls it east. The ladder blocks the
player while it stands still (collide), not while it rolls."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import library_ladder  # noqa: E402
from library_kit import common  # noqa: E402

importlib.reload(library_ladder)

NAME = "LibraryLadderSecret"

P = dict(
    name=NAME,
    travel=-4.55,         # m along the asset's x (rotation 180 on the south wall: +4.55 m east)
    duration=2.8,         # a heavy oak ladder on bronze rollers
    signal="secret_library",
    prompt="Push the ladder",
    prompt_active="Push the ladder back",
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    root, parts = library_ladder.build(name=n)
    col = root.users_collection[0]
    # everything hangs from one empty at the origin: the switch's moving part
    carriage = common.empty(f"{n}_Carriage", col)
    carriage.parent = root
    for ob in list(root.children):
        if ob is not carriage:
            ob.parent = carriage
    carriage["interact"] = {
        "type": "switch", "signal": p["signal"], "state": False,
        "prompt": p["prompt"], "promptActive": p["prompt_active"],
        "range": 1.3, "duration": p["duration"], "collide": True,
        "travel": {"axis": "x", "distance": p["travel"]},
    }
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
