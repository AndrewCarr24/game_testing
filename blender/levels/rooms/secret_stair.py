"""The secret stair (below ground; design/house/secret_passage.md): a 1.95 x 5.18 m concrete shaft,
8.4 m tall, from the bunker's floor (z -4.2) up to the underside of the library's floor. It stands
in the den's south-east corner (the den sees it as a closet with a dark glass slot).

A blackened-steel scissor stair with a steel spine between its two lanes (plan.FLIGHTS,
LANDINGS, DIVIDERS; house.py builds them):
  F1  the library's folding floor (lane W): from the library down to L1 (z 2.22, under the
      library's south bookcases), where the button is
  F2  lane E north to L2 (z 0.02): the den's floor level; the slot into the den is in the west
      wall at eye height (smoked glass: dark from the den, which is lit)
  F3  lane W south to L3 (z -2.18)
  F4  lane E north to the floor; the steel door north into the armory, a second button by it
The light changes colour on the way down: each flight's handrail has a LED line under it, warm
(2700 K) under the library, cooling to the armory's 6000 K at the bottom.

Local coords: (0, 0) = the shaft's interior centre (world -14.625, -17.26), z = 0 its floor
(world -4.2): add 4.2 to a world height. Lane W x -0.975..-0.025, lane E x 0.025..0.975.
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets"))
import bunker_kit  # noqa: E402

importlib.reload(bunker_kit)

Z = 4.2                              # world z -> local: + Z
L1, L2, L3 = 2.2167 + Z, 0.0167 + Z, -2.1833 + Z

FINISHES = dict(
    floor=lambda: bunker_kit.concrete("M_Shaft_Concrete_Floor", (0.20, 0.20, 0.195), roughness=0.7),
    floor_uv_tile=6.0,
    walls=lambda: bunker_kit.concrete("M_Shaft_Concrete", (0.36, 0.355, 0.345), roughness=0.88),
    wall_uv_tile=3.0,
    ceiling=lambda: bunker_kit.concrete("M_Shaft_Concrete_Ceiling", (0.16, 0.16, 0.155), roughness=0.9),
)

PLACEMENTS = [
    # the button at L1 (east wall, facing west), and by the door at the bottom
    ("secret_button", (0.975, -2.05, L1 + 1.1), -90),
    ("secret_button", (0.975, 1.95, 1.1), -90),
]

# the handrails' LED lines (one hidden source per flight under its outer rail, aimed down the
# treads): warm under the library, cold by the armory; the first landing has a small warm light
# under the library's floor; L2 (the slot) is left dim so the den can't see in. The bunker has its
# own power: signal None (never switched, on without the house's power).
_WARM, _MID, _COLD = (1.0, 0.74, 0.50), (1.0, 0.88, 0.74), (0.86, 0.92, 1.0)
LIGHTS = [
    dict(kind="area", pos=(-0.2, -2.05, 8.33), size=(0.5, 0.6), aim=(-0.2, -2.05, L1), power=22.0,
         color=_WARM, signal=None),                                                          # L1
    dict(kind="area", pos=(0.90, 0.0, 6.26), size=(0.05, 2.8), aim=(0.90, 0.0, 5.0), power=40.0,
         color=_WARM, signal=None),                                                          # F2
    dict(kind="area", pos=(-0.90, 0.0, 4.06), size=(0.05, 2.8), aim=(-0.90, 0.0, 2.8), power=40.0,
         color=_MID, signal=None),                                                           # F3
    dict(kind="area", pos=(0.90, -0.1, 1.95), size=(0.05, 2.6), aim=(0.90, -0.1, 0.7), power=40.0,
         color=_COLD, signal=None),                                                          # F4
    dict(kind="area", pos=(-0.4, 2.3, 2.6), size=(0.9, 0.05), aim=(-0.4, 2.3, 0.0), power=35.0,
         color=_COLD, signal=None),                                                          # the door
]

PROBE = (0.0, 2.0, L2 + 1.6)
