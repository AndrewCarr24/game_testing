"""Low teak lounger for the in-water sun shelf: the same lounger, frame 20 cm off the floor,
a gentler back, no towel. Foot end toward -Y, origin on the shelf floor. Real geometry."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pool_common as pc  # noqa: E402
import pool_lounger as pl  # noqa: E402

importlib.reload(pc)
importlib.reload(pl)
common = pc.common

NAME = "PoolLoungerLow"

P = {**pl.P, "name": NAME, "frame_z": 0.20, "back_deg": 30.0, "back_len": 1.0, "towel": False}


def build(**overrides):
    p = {**P, **overrides}
    b = pc.Builder(p["name"])
    pl.lounger(b, p)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    pc.report(root, parts)
