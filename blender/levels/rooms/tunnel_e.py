"""The service tunnel, east leg (below ground; design/house/secret_passage.md): 48.2 x 2.7 m,
2.8 m high, from the armory's blast door east under the courtyard, the east gallery, the garage
and the terrace to the pump room. Raw concrete, a galvanised cable tray and three conduits along
the north wall, a drainage channel along the south edge, a caged bulkhead light every 6 m: pools
of light with dusk between them, the far end always a little brighter than where you are. Under
the courtyard (x -14 here) the courtyard's planting has been leaking for years: the floor is wet.

Local coords: (0, 0) = the interior centre (world 14.25, -2.4), z = 0 the floor (world -4.2);
x runs east. The blast door is at the west end (x -24.1), the pump room opens at the east end.
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

RUNS = (-21.0, -15.0, -9.0, -3.0, 3.0, 9.0, 15.0, 21.0)       # 6 m services runs / bays
LAMP_Z = 2.15
PLACEMENTS = (
    [("tunnel_conduit", (x, 1.35), 0) for x in RUNS]
    + [("tunnel_channel", (x, -1.2), 0) for x in RUNS]
    + [("tunnel_bulkhead", (x, 1.35, LAMP_Z), 0) for x in RUNS]
    + [("tunnel_puddle", (-14.0, 0.15), 0),                       # under the courtyard
       ("tunnel_puddle_small", (6.5, -0.4), 30)]
)

_LAMP = (1.0, 0.88, 0.72)
LIGHTS = [dict(kind="point", pos=(x, 1.18, LAMP_Z), power=38.0, color=_LAMP, signal=None) for x in RUNS]

PROBE = (0.0, 0.0, 1.6)
