"""THE BAR (town2_bar): Sourwood's roadhouse, the town's hero location (design/town/brief.md
section 4, design/town/bar.md). A long, low 1950s cinder-block roadhouse at the edge of town
on the river, across the tracks: a deep porch on the gravel lot with neon in every window,
pickups and two dark vans nose-out at the porch, a pole sign by the highway; inside a 14 m bar
with a back-bar of bottles lit from below in front of old mirrors, oxblood vinyl booths each
with its own red glass lamp, a pool table under a green-shaded lamp, a glowing jukebox, a small
stage with a red curtain, a restroom corridor to the back exit, and the back room behind the
bar's end, its door ajar (the masks on the hook rail, the monitors' blue light); a river deck
on posts over the bank with steps down to a landing at the water.

Built for the town runtime's contract (prompts/town_building.md): one mesh per material, all
light baked by blender/town/bar/build.py (Cycles: the golden-hour sun and sky, the lamps, the
neon) into one lightmap on TEXCOORD_1; emissive neon / bulbs / screens from the props atlas.

Frame: asset metres, front (the lot, the porch) faces -Y, x along the building (+X the west
gable, the highway end), z = 0 the lot's grade (the pad), the floor at P["floor"]. Root empty
Town2Bar, parts Town2Bar_<Material>; Town2Bar_LOD1 for far views."""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import town2_bar_kit as kit_mod  # noqa: E402
import town2_bar_tex as tex  # noqa: E402
import town2_bar_shell as shell  # noqa: E402
import town2_bar_interior as interior  # noqa: E402
import town2_bar_lot as lot  # noqa: E402

for m in (kit_mod, tex, shell, interior, lot):
    importlib.reload(m)

NAME = "Town2Bar"

P = dict(
    name=NAME, module="town2_bar",
    # the building
    L=32.0, D=14.0, wall=0.25, floor=0.45, ceiling=3.2, plate=3.95, pitch=0.25, overhang=0.6, gable_overhang=0.35,
    # partitions: the bar room / service block line (x), the back room / corridor line, the corridor / restrooms line (y)
    px=-10.4, pc=0.0, pr=-1.6, backroom_door=(4.95, 5.85),
    door_x=-8.4, front_windows=(-5.85, -3.9, -1.95, 0.0, 1.95, 3.9, 9.2), back_windows=(7.0, 12.2), deck_door_x=9.6,
    west_window=False,
    # the porch (front) and the river deck (back)
    porch_x0=-13.2, porch_x1=11.4, porch_depth=3.0, porch_posts=9, porch_beam=3.05,
    deck_x0=4.4, deck_x1=15.6, deck_y1=11.6, deck_ground=(-0.2, -1.2), stair_x=14.2, stair_steps=22, landing_z=-3.6,
    # the bar
    bar_x0=-10.0, bar_x1=4.2, bar_front=4.05, bar_h=1.07,
    # the lot (pad) footprint and the world placement (laurel_town.py layout_buildings: the site)
    footprint=(-26.0, -17.0, 47.0, 8.0),
    world=dict(x=-2112.0, y=-804.5, yaw=180.0),
    look="golden",
    interior_exposure=1.8,
)


def build(**overrides):
    """Builds the kit (geometry by material, colliders, lights) and returns it with P; the
    driver (blender/town/bar/build.py) turns it into objects, bakes and exports."""
    p = dict(P, **overrides)
    k = kit_mod.Kit(tiles=tex.TILES, cells=tex.CELLS)
    k.section = "shell"
    shell.build_shell(k, p)
    interior.build_interior(k, p)
    lot.build_lot(k, p)
    return k, p
