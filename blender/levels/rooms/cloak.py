"""Cloakroom (ground floor, east of the entry): 5.2 x 9.2 m inside, 4.2 m high. The door is
on the west wall at y -2.8..-1.7 and swings in (keep x -2.6..-1.3, y -3..-0.5 clear).

Four built-in walnut coat closets (two along the north wall, two along the east wall),
a full-length mirror between sconces on the west wall, a long leather bench on a rug in
the middle, a bench and a painting on the south wall. Smoked oak floor, warm plaster.
Local coords: (0, 0) = room centre; +x east, +y north.
"""
from lib import common, textures


def _floor():
    m = common.pbr_material("M_OakFloor_Smoked", (0.08, 0.055, 0.035), roughness=0.75, coat=0.0)
    common.set_base_color_map(m, textures.load(textures.wood(
        "T_OakFloorSmoked_BaseColor", dark=(0.030, 0.020, 0.013), light=(0.095, 0.066, 0.043), rings=30, seed=31)))
    return m


FINISHES = dict(
    floor=_floor,
    walls=lambda: common.pbr_material("M_Plaster_Cloak", (0.50, 0.45, 0.385), roughness=0.92),
    ceiling=lambda: common.pbr_material("M_Ceiling_Warm", (0.48, 0.46, 0.43), roughness=0.9),
)

PLACEMENTS = [
    # --- north wall: two closets (2.29 m wide) from the west wall to the east run's front (x 1.98)
    ("entry_coat_closet", (-1.455, 4.29), 0),
    ("entry_coat_closet", (0.835, 4.29), 0),
    # --- east wall: two closets facing west, from the north run's front (y 3.98) south; the
    #     corner square behind both runs' end panels is closed off (a blind corner)
    ("entry_coat_closet", (2.29, 2.835), -90),
    ("entry_coat_closet", (2.29, 0.545), -90),
    # --- west wall: full-length mirror between sconces
    ("entry_mirror_tall", (-2.6, 1.2, 1.25), 90),
    ("entry_sconce", (-2.6, 0.2, 1.75), 90),
    ("entry_sconce", (-2.6, 2.2, 1.75), 90),
    # --- the middle: rug and a long bench
    ("rug", (-0.3, 0.7), 90),
    ("entry_bench", (-0.3, 0.7), 90),
    # --- south: bench and painting
    ("bench", (0.4, -4.37), 180),
    # --- lighting (see LIGHTS): a bronze valance over the mirror wall, ceiling cans over the
    #     bench, the south wall and the door
    ("light_g_cove_down", (-2.6, -2.0, 3.9), 90),
    ("light_g_cove_down", (-2.6, 2.0, 3.9), 90),
    ("light_g_downlight", (-0.3, 0.7, 4.2), 0),
    ("light_g_downlight", (0.4, -3.7, 4.2), 0),
    ("light_g_downlight", (-1.0, -2.3, 4.2), 0),
    # --- set dressing (decor_a_*)
    ("decor_a_soft_bench_cloak", (-0.3, 0.7, 0.47), 90),        # felt hat, folded scarf
    ("decor_a_floor_shoes", (0.32, -0.15, 0.012), 75),          # loafers on the rug by the bench
    ("decor_a_soft_bench_hatboxes", (0.4, -4.37, 0.46), 180),   # hat boxes, folded throw
    ("decor_a_floor_umbrella_stand", (-2.36, -3.4), 0),         # by the door, outside its swing
    ("decor_a_floor_b", (2.12, -4.12), 0),                      # branches in a floor vase (SE corner)
]

# Lighting: a boutique dressing room. The walnut closets glow from inside (the LED under
# each hat shelf lights the coats) and light hidden on top of them washes the ceiling; the
# tall mirror stands between its two sconces under a bronze valance washing that wall; cans
# pool light on the leather bench, the south wall and the way in. No ceiling lines.
LIGHTS = [
    # hat-shelf LEDs (shelf 2.30 m), north pair and east pair
    dict(kind="area", pos=(-1.455, 4.08, 2.27), size=(2.1, 0.05), aim=(-1.455, 3.9, 0.0), power=45.0, color=(1.0, 0.82, 0.58)),
    dict(kind="area", pos=(0.835, 4.08, 2.27), size=(2.1, 0.05), aim=(0.835, 3.9, 0.0), power=45.0, color=(1.0, 0.82, 0.58)),
    dict(kind="area", pos=(2.08, 2.835, 2.27), size=(2.1, 0.05), aim=(1.9, 2.835, 0.0), power=45.0, color=(1.0, 0.82, 0.58)),
    dict(kind="area", pos=(2.08, 0.545, 2.27), size=(2.1, 0.05), aim=(1.9, 0.545, 0.0), power=45.0, color=(1.0, 0.82, 0.58)),
    # on top of the 3 m closets, up onto the ceiling
    dict(kind="area", pos=(-0.31, 4.25, 3.04), size=(4.5, 0.3), aim=(-0.31, 4.25, 4.2), power=300.0, color=(1.0, 0.84, 0.66)),
    dict(kind="area", pos=(2.3, 1.69, 3.04), size=(0.3, 4.5), aim=(2.3, 1.69, 4.2), power=300.0, color=(1.0, 0.84, 0.66)),
    # valance wash down the mirror wall (lip down at 3.9 m)
    dict(kind="area", pos=(-2.5, 0.0, 3.84), size=(7.8, 0.06), aim=(-2.1, 0.0, 0.5), power=260.0, color=(1.0, 0.82, 0.6)),
    # mirror sconces
    dict(kind="point", pos=(-2.3, 0.2, 1.75), power=80.0, color=(1.0, 0.78, 0.5)),
    dict(kind="point", pos=(-2.3, 2.2, 1.75), power=80.0, color=(1.0, 0.78, 0.5)),
    # cans
    dict(kind="spot", pos=(-0.3, 0.7, 4.08), aim=(-0.3, 0.7, 0.0), power=420.0, angle=60, blend=0.6),
    dict(kind="spot", pos=(0.4, -3.7, 4.08), aim=(0.4, -4.5, 1.2), power=260.0, angle=46, blend=0.5),
    dict(kind="spot", pos=(-1.0, -2.3, 4.08), aim=(-1.0, -2.3, 0.0), power=380.0, angle=60, blend=0.6),
]


# --- interactivity (prompts/interactivity.md): the light switch by the door (W wall, latch side),
# interactive props, and this room's light fixtures wired to lights_cloak (ix_common.wire)
import importlib as _il  # noqa: E402
import ix_common  # noqa: E402

_il.reload(ix_common)
PLACEMENTS = list(PLACEMENTS) + [
    ('ix_switch', (-2.6, -2.97, 1.1), 90, {'signal': 'lights_cloak', 'state': True}),
]
PLACEMENTS = ix_common.wire(PLACEMENTS, "cloak")
