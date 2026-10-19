"""Private gym (upper floor, north-west): 12.2 x 9.2 m inside, north wall glazed
(x -4.75..4.75), door on the west wall at y +1.2..+2.3. A mirror wall on the south
(stretching barre, dumbbell and kettlebell stands, a stretching mat), a row of
cardio facing the glass (two treadmills and a rower), a lifting corner with a bench
and, on the oak east wall, a functional trainer."""
import importlib
import os

import numpy as np

from lib import common, materials, textures

importlib.reload(materials)


def _rubber_floor():
    """Poured EPDM-flecked rubber: charcoal with warm grey and terracotta flecks."""
    path = os.path.join(textures.TEX_DIR, "T_Guest_Rubber_BaseColor.png")
    if not os.path.exists(path):
        rng = np.random.default_rng(77)
        n = 1024
        base = np.array([0.050, 0.050, 0.053])
        mott = textures._noise(n, 1.0, 1.0, 1.6, rng) * 0.012
        lin = np.ones((n, n, 3)) * base + mott[..., None]
        for col, cover in (((0.30, 0.29, 0.28), 0.035), ((0.30, 0.15, 0.08), 0.02), ((0.16, 0.19, 0.15), 0.02)):
            mask = rng.random((n, n)) < cover
            # fleck = a speck of 2 px
            mask = mask | np.roll(mask, 1, 0) | np.roll(mask, 1, 1)
            lin = np.where(mask[..., None], np.array(col) * (0.7 + 0.5 * rng.random((n, n, 1))), lin)
        textures._save("T_Guest_Rubber_BaseColor", textures._to_srgb(lin))
    m = common.pbr_material("M_Rubber_Floor", (0.06, 0.06, 0.063), roughness=0.82)
    common.set_base_color_map(m, textures.load(path))
    return m


def _oak_wall():
    m = common.pbr_material("M_Oak_Light", (0.42, 0.28, 0.15), roughness=0.55, coat=0.05)
    common.set_base_color_map(m, textures.load(textures.wood(
        "T_Guest_Oak_BaseColor", dark=(0.30, 0.19, 0.095), light=(0.55, 0.385, 0.215), rings=34, seed=41)))
    return m


def _mirror():
    return common.pbr_material("M_Mirror", (0.82, 0.84, 0.86), roughness=0.03, metallic=1.0)


FINISHES = dict(
    floor=_rubber_floor,
    floor_uv_tile=1.5,
    walls=lambda: common.pbr_material("M_Plaster_Greige", (0.40, 0.375, 0.34), roughness=0.92),
    ceiling=lambda: common.pbr_material("M_Ceiling_Warm", (0.48, 0.46, 0.43), roughness=0.9),
    walls_by_side={"S": _mirror, "E": _oak_wall},
)

PLACEMENTS = [
    # mirror wall (south): trim, dumbbells, kettlebells, stretching mat
    ("guest_mirror_trim", (0.0, -4.6), 180),
    ("guest_dumbbell_rack", (-3.3, -4.3), 180),
    ("guest_kettlebells", (-1.2, -4.38), 180),
    ("guest_mat", (2.6, -3.3), 0),
    # lifting: two benches between the rack and the middle of the room
    ("guest_weight_bench", (-3.0, -1.9), 90),
    ("guest_weight_bench", (-0.4, -1.9), 90),
    ("guest_mat", (-3.4, 2.7), 0),
    # cardio facing the glass
    ("guest_treadmill", (0.8, 2.55), 180),
    ("guest_treadmill", (2.1, 2.55), 180),
    ("guest_rower", (3.7, 2.45), 180),
    # functional trainer on the east wall, user facing west
    ("guest_cable_machine", (5.67, -0.9), -90),
    # a seat and some green by the door and window
    ("guest_bench", (-5.85, -1.6), 90),
    ("library_plant", (-4.4, 3.9), 0),
    ("library_plant", (4.4, 3.9), 0),
    ("art_target", (-6.09, 3.45, 1.6), 90),               # stained target canvas
]

# --- lighting --------------------------------------------------------------------------------
# A working room, so ceiling slots stay here (even, shadow-free light to train in), but placed
# with intent: one over the lifting zone, one over the cardio row facing the glass, and a slot
# tight to the oak east wall that grazes the wood from ceiling to floor behind the functional
# trainer. Two downlights wash the art by the door and the mirror wall's barre zone.
CEIL = 3.8
PLACEMENTS += [
    ("light_u_downlight", (-5.35, 3.5, CEIL), 0),          # art by the door
    ("light_u_downlight", (2.6, -3.9, CEIL), 0),           # stretching mat by the mirror
]

LIGHTS = [
    dict(kind="strip", pos=(-1.7, -1.9), size=(6.0, 0.08), power=130.0),     # lifting
    dict(kind="strip", pos=(2.0, 1.7), size=(5.0, 0.08), power=110.0),      # cardio row
    dict(kind="strip", pos=(5.82, -0.4), size=(0.08, 7.6), power=150.0),    # oak wall grazer slot
    dict(kind="spot", pos=(-5.35, 3.5, CEIL - 0.03), aim=(-6.1, 3.5, 1.5), power=160.0, angle=50.0, blend=0.75,
         color=(1.0, 0.88, 0.74)),
    dict(kind="spot", pos=(2.6, -3.9, CEIL - 0.03), aim=(2.6, -3.5, 0.0), power=170.0, angle=60.0, blend=0.8,
         color=(1.0, 0.90, 0.78)),
]

# --- set dressing (decor_c_*): spa touches, floor kept clear for training ---------------------
# On the bench by the door: a stack of folded linen towels with two rolls, and an oak tray with
# a carafe and two glasses. By the stretching mat: sage yoga blocks and a basket of rolled
# towels; a snake plant in a woven basket in the south-east corner, doubled by the mirror.
PLACEMENTS += [
    ("decor_c_towels", (-5.85, -2.0, 0.445), 90),
    ("decor_c_tray_carafe_oak", (-5.85, -1.15, 0.445), 90),
    ("decor_c_yoga_blocks", (3.97, -4.3), 4),
    ("decor_c_towel_basket", (4.55, -4.17), 0),
    ("decor_c_plant_snake_basket", (5.65, -4.17), 30),
]
