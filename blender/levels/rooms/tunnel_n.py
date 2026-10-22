"""The service tunnel, north leg (below ground; design/house/secret_passage.md): 32.7 x 2.7 m,
2.8 m high, from the pump room north under the tennis lawn to the landing below the pool house
(its last 3 m, y 13.35..16.35 here = world 31.5..34.5; the pool house's way up starts at its
open north edge).

The length is a choice: after two lit bays the bulkheads are dead for 16 m (one hangs off its
screw), the floor is under a sheet of standing water that holds the far lights upside down, and
the only light is ahead: the landing's cold lamp, and whatever the flashlight shows. Then two
lit bays again and the landing.

Local coords: (0, 0) = the interior centre (world 40.0, 18.0), z = 0 the floor (world -4.2);
y runs north. The bulkheads and services are on the east wall (x 1.35), the channel on the west.
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

RUNS = (-13.0, -7.0, -1.0, 5.0, 11.0)       # 6 m services runs along the east wall
LIT = (-14.0, -8.0, 8.5, 12.0)              # lit bulkheads (y); the dark stretch is -5..7
DEAD = (-2.0, 4.0)
LAMP_Z = 2.15
PLACEMENTS = (
    [("tunnel_conduit", (1.35, y), -90) for y in RUNS]
    + [("tunnel_channel", (-1.2, y), 90) for y in RUNS]
    + [("tunnel_bulkhead", (1.35, y, LAMP_Z), -90) for y in LIT]
    + [("tunnel_bulkhead_dead", (1.35, y, LAMP_Z), -90) for y in DEAD]
    + [("tunnel_bulkhead", (1.35, 15.0, LAMP_Z), -90),           # the landing's
       ("tunnel_puddle", (0.0, 1.0), 90),                         # the dark stretch's standing water
       ("tunnel_puddle", (0.1, -3.2), 95),
       ("tunnel_puddle_small", (-0.3, 5.6), 70)]
)

_LAMP = (1.0, 0.88, 0.72)
LIGHTS = (
    [dict(kind="point", pos=(1.18, y, LAMP_Z), power=38.0, color=_LAMP, signal=None) for y in LIT]
    # the landing: a cold lamp (the pool house's way up starts at the north edge)
    + [dict(kind="point", pos=(1.18, 15.0, LAMP_Z), power=55.0, color=(0.86, 0.92, 1.0), signal=None)]
)

PROBE = (0.0, 0.0, 1.6)
