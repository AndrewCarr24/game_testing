"""The tunnel bulkhead light, dead: lens dark, cage bent, the fixture hanging off one screw at an
angle with a cable dangling. A thin module over tunnel_bulkhead (see there for the orientation)."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tunnel_bulkhead  # noqa: E402

importlib.reload(tunnel_bulkhead)
common = tunnel_bulkhead.common

NAME = "TunnelBulkheadDead"
P = dict(name=NAME, dead=True)


def build(**overrides):
    return tunnel_bulkhead.build(**{**P, **overrides})
