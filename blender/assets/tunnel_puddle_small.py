"""The small standing-water patch (1.2 x 0.8 m): tunnel_puddle's `small` variant under its own
name, for levels that place it by asset name."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tunnel_puddle  # noqa: E402

importlib.reload(tunnel_puddle)
common = tunnel_puddle.common

NAME = "TunnelPuddleSmall"
P = dict(name=NAME, variant="small")


def build(**overrides):
    return tunnel_puddle.build(**{**P, **overrides})
