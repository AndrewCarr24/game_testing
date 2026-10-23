"""The pump room (below ground; design/house/secret_passage.md): 6.7 x 7.7 m, 3.2 m high, at the
tunnel's turn under the tennis lawn. The sump: two blue pumps over a grated pit that keep the
tunnels dry, their discharge pipes up into the wall, an amber work lamp over them; the hum of
the motors is the loudest thing below ground. The east tunnel comes in from the west (y
-1.25..1.45), the north tunnel leaves from the north-west (x -3.35..-0.65).

Local coords: (0, 0) = the interior centre (world 42.0, -2.5), z = 0 the floor (world -4.2).
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets"))
import bunker_kit  # noqa: E402

importlib.reload(bunker_kit)

FINISHES = dict(
    floor=lambda: bunker_kit.concrete("M_Tunnel_Floor", (0.21, 0.21, 0.205), roughness=0.72),
    floor_uv_tile=6.0,
    walls=lambda: bunker_kit.concrete("M_Tunnel_Wall", (0.33, 0.33, 0.32), roughness=0.9),
    wall_uv_tile=3.0,
    ceiling=lambda: bunker_kit.concrete("M_Tunnel_Ceiling", (0.25, 0.25, 0.245), roughness=0.92),
)

PLACEMENTS = [
    ("pump_station", (2.25, -1.5), 0),                        # its pipe side (+x) into the east wall
    ("tunnel_bulkhead", (3.35, 1.9, 2.4), -90),               # the work lamp's neighbour (east wall)
    ("tunnel_bulkhead", (-1.6, -3.85, 2.3), 180),             # south wall, facing north
    ("tunnel_conduit", (0.0, -3.85), 180),                    # along the south wall
    ("tunnel_puddle_small", (-0.6, -1.9), 15),
]

LIGHTS = [
    dict(kind="point", pos=(1.4, -0.4, 2.9), power=80.0, color=(1.0, 0.56, 0.24), signal=None),   # amber work lamp
    dict(kind="point", pos=(3.2, 1.9, 2.4), power=30.0, color=(1.0, 0.88, 0.72), signal=None),
    dict(kind="point", pos=(-1.6, -3.7, 2.3), power=30.0, color=(1.0, 0.88, 0.72), signal=None),
]

PROBE = (-1.0, 0.5, 1.6)
