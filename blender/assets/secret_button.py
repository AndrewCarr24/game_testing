"""The secret stair's button (design/house/secret_passage.md): a round brass push button in a
round bronze plate with a thin cold-white lit ring, on the shaft's concrete wall at its first
landing, under the library's floor. It is on the same signal as the library's rolling ladder
("secret_library"): pressed, the folding floor above opens or closes (and the ladder rolls with
it: every switch on a signal follows it).

Wall-mounted: origin at the centre of the plate's back (on the wall face), front -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402

importlib.reload(ix_common)
common = ix_common.common

NAME = "SecretButton"

P = dict(
    name=NAME,
    plate_size=(0.11, 0.11, 0.012),
    plate="bronze",
    plate_shape="round",
    part="button",
    rocker_size=(0.046, 0.046, 0.014),
    paddle=("M_SecretButton_Brass", (0.55, 0.40, 0.18)),
    ring=0.031,
    led=("M_SecretButton_Ring", (0.80, 0.90, 1.0), 2.5),
    signal="secret_library",
    state=False,
    prompt="Open the floor above",
    promptActive="Close the floor above",
    travel={"axis": "-z", "distance": 0.006},
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    ix_common.switch(n, col, root, p)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts
