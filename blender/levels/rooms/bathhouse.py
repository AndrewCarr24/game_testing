"""The bathhouse's rooms (blender/levels/bathhouse_plan.py; design: design/grounds/pool_house.md).

One module for all of them (plan: module="bathhouse"): FINISHES, PLACEMENTS, LIGHTS per room, in
room-local metres ((0, 0) = the room's interior centre, z = its floor; +x east, +y north).

  ph_hall   the bath hall: 11.2 x 13.2 m, 5.4 m high, glass to the west (the lap pool), the
              pool on the lap pool's axis, the coursed-stone east wall that the water lights
  ph_fire   the fire bath: oxblood plaster, a hot pool, one slot of sky
  ph_steam  the steam room: dark teal mosaic, benches (a hiding place)
  ph_cold   the cold plunge: the secret's top (the plunge drains, a slab sinks)
  ph_stair  the secret stair: Ando's concrete, lit blue through the pool's glass end
  ph_rest   the rest room: oak and stone, a 15 m window to the north (the mountains)
"""
import importlib
import os

from lib import ph_textures, common, materials, textures

importlib.reload(ph_textures)


def _mat(name, color, roughness, tex=None, **kw):
    m = common.pbr_material(name, color, roughness=roughness, **kw)
    if tex:
        common.set_base_color_map(m, textures.load(tex))
    return m


def stone():
    return _mat("M_PH_Stone", (0.21, 0.21, 0.19), 0.86, ph_textures.coursed_stone())


def stone_dark():
    return _mat("M_PH_StoneDark", (0.1, 0.105, 0.1), 0.8,
                ph_textures.coursed_stone(name="T_PH_StoneDark_BaseColor", seed=72, dark=True))


def slab():
    return _mat("M_PH_Slab", (0.24, 0.235, 0.215), 0.5, ph_textures.slabs())


def slab_dark():
    return _mat("M_PH_SlabDark", (0.08, 0.085, 0.08), 0.42,
                ph_textures.slabs(name="T_PH_SlabDark_BaseColor", seed=74, color=(0.075, 0.085, 0.08)))


def pool_stone():
    """The pools' basins: the same slabs, a shade greener and darker under the water."""
    return _mat("M_PH_PoolStone", (0.12, 0.15, 0.14), 0.35,
                ph_textures.slabs(name="T_PH_PoolStone_BaseColor", seed=75, color=(0.11, 0.145, 0.135), rows=8))


def concrete():
    return _mat("M_PH_Concrete", (0.33, 0.325, 0.31), 0.78, ph_textures.ando_concrete())


def red():
    return _mat("M_PH_Red", (0.3, 0.042, 0.026), 0.92, ph_textures.lime_plaster())


def mosaic():
    return _mat("M_PH_Mosaic", (0.02, 0.05, 0.05), 0.18, ph_textures.mosaic())


def pale_ceiling():
    """The hall's ceiling: pale lime plaster, to catch the light off the water."""
    return _mat("M_PH_Ceiling", (0.62, 0.6, 0.555), 0.95)


def cedar():
    return _mat("M_PH_Cedar", (0.36, 0.22, 0.13), 0.7,
                textures.wood("T_PH_Cedar_BaseColor", (0.22, 0.12, 0.065), (0.42, 0.26, 0.15), seed=91, rings=26))


def oak():
    m = _mat("M_PH_Oak", (0.4, 0.27, 0.15), 0.5)
    common.set_base_color_map(m, textures.load(textures.oak_floor()))
    return m


FINISHES = {
    "ph_hall": dict(floor=slab, walls=stone, ceiling=pale_ceiling, floor_uv_tile=2.4, wall_uv_tile=2.0),
    "ph_fire": dict(floor=slab_dark, walls=red, ceiling=red, floor_uv_tile=2.4, wall_uv_tile=2.0),
    "ph_steam": dict(floor=mosaic, walls=mosaic, ceiling=mosaic, floor_uv_tile=0.5, wall_uv_tile=0.5),
    "ph_cold": dict(floor=slab_dark, walls=stone_dark, ceiling=stone_dark, floor_uv_tile=2.4, wall_uv_tile=2.0),
    "ph_stair": dict(floor=concrete, walls=concrete, ceiling=concrete, floor_uv_tile=1.82, wall_uv_tile=1.82),
    "ph_rest": dict(floor=oak, walls=stone, ceiling=cedar, floor_uv_tile=2.0, wall_uv_tile=2.0),
    "tunnel_landing": dict(floor=concrete, walls=concrete, ceiling=concrete, floor_uv_tile=1.82, wall_uv_tile=1.82),
}

# the materials of the shell pieces bathhouse_shell.py adds (basins, treads, ...)
SHELL = dict(pool=pool_stone, slab=slab, slab_dark=slab_dark, concrete=concrete, stone=stone, stone_dark=stone_dark)

LIGHTS_SIGNAL = "lights_bathhouse"

# room-local frames (interior centres, world): hall (32.75, 37.75), fire (41.75, 32.75),
# stair (40.0, 37.5, floor -4.2), steam (43.25, 37.5), cold (41.75, 42.5), rest (36.0, 46.5)
LIGHTS_ON = {"signal": "lights_bathhouse", "state": True}
PLUNGE = {"signal": {"plunge": "ph_plunge"}}

PLACEMENTS = {
    "ph_hall": [
        ("ph_pool_water", (0.0, 0.15), 0),
        # the low sun off the water, on the east wall over the pool's end
        ("ph_caustics", (5.59, 0.15, 2.6), -90),
        # a long bench on the north walkway facing the water, a short one on the south walkway
        ("ph_bench_long", (-0.6, 5.1), 0),
        ("ph_bench", (2.2, -5.3), 180),
        ("ph_towels", (4.6, -6.6), 180),
        # the light switch by the door in from the house's terrace (latch side)
        ("ix_switch", (-1.82, -6.6, 1.1), 180, LIGHTS_ON),
    ],
    "ph_fire": [
        ("ph_hot_water", (0.0, 0.0), 0),
    ],
    "ph_stair": [
        ("ph_pool_window", (-1.64, 0.1, 3.45), 0),
        ("ph_caustics_stair", (1.34, 0.1, 3.6), -90),
        ("ph_handrail", (1.35, -2.85, 0.0), 0),
        # the wheel at the head of the stair: drains the plunge above, the slab sinks
        ("ph_valve", (1.35, 2.5, 4.15), -90, PLUNGE),
    ],
    "ph_steam": [
        ("ph_steam", (0.0, 0.0), 0, {"signal": {"steam": "ph_steam"}, "state": True}),
    ],
    "ph_cold": [
        ("ph_plunge", (-1.75, -0.75), 0, PLUNGE),
        ("ph_valve", (0.25, -1.85, 0.95), 180, PLUNGE),
        ("ph_bench_short", (2.83, -0.1), 90),
    ],
    "ph_rest": [
        # loungers facing the long north window (feet to the glass), either side of the way in
        *[("ph_lounger", (x, -0.15), 180) for x in (-8.05, -7.15)],
        *[("ph_lounger", (x, -0.15), 180) for x in (1.2, 2.1, 3.0, 3.9, 4.8)],
        ("ph_towels", (-8.85, 0.0), 90),
    ],
    "tunnel_landing": [],
}

# all baked (golden hour, the lights on): the light the building makes of water and stone
LIGHTS = {
    "ph_hall": [
        # under the water: the pool lit from its floor, a soft warm wash on the ceiling
        dict(kind="area", pos=(-2.8, 0.15, -1.3), size=(5.0, 5.4), aim=(-2.8, 0.15, 3.0), power=55.0, color=(1.0, 0.86, 0.66)),
        dict(kind="area", pos=(2.8, 0.15, -1.3), size=(5.0, 5.4), aim=(2.8, 0.15, 3.0), power=55.0, color=(1.0, 0.86, 0.66)),
        # down the east wall from the skylight slot: the coursed stone grazed from above
        *[dict(kind="spot", pos=(5.25, y, 5.3), aim=(5.62, y, 0.0), power=30.0, angle=34.0, blend=0.7, color=(1.0, 0.8, 0.58))
          for y in (-6.0, -3.6, -1.2, 1.2, 3.6, 6.0)],
    ],
    "ph_fire": [
        dict(kind="area", pos=(0.0, 0.0, -0.68), size=(3.3, 1.0), aim=(0.0, 0.0, 3.0), power=40.0, color=(1.0, 0.58, 0.34)),
        dict(kind="area", pos=(0.0, 1.38, 2.96), size=(5.0, 0.3), aim=(0.0, 1.6, 0.0), power=35.0, color=(1.0, 0.75, 0.55)),
    ],
    "ph_steam": [
        dict(kind="area", pos=(0.0, 0.0, 2.55), size=(1.0, 4.4), aim=(0.0, 0.0, 0.0), power=16.0, color=(0.75, 0.9, 1.0)),
    ],
    "ph_stair": [
        # the pool's glass end: cold light through the water
        dict(kind="area", pos=(-1.25, 0.1, 3.45), size=(5.0, 1.0), aim=(1.35, 0.1, 2.6), power=85.0, color=(0.45, 0.85, 0.95)),
        # small warm lights under the handrail, down onto the treads
        *[dict(kind="area", pos=(1.25, y, 1.02 + (y + 2.85) * 0.63), size=(0.5, 0.05), aim=(1.0, y, 0.0), power=3.0,
               color=(1.0, 0.78, 0.55)) for y in (-2.2, -0.9, 0.4, 1.6)],
    ],
    "ph_cold": [
        dict(kind="area", pos=(-1.75, -1.1, -1.15), size=(2.4, 0.6), aim=(-1.75, -1.1, 3.0), power=22.0, color=(0.8, 0.92, 1.0)),
        dict(kind="spot", pos=(-1.75, 0.5, 3.5), aim=(-1.75, -1.85, 0.4), power=18.0, angle=32.0, blend=0.8, color=(1.0, 0.85, 0.7)),
    ],
    "ph_rest": [
        # a cove along the south wall washing the cedar ceiling
        dict(kind="area", pos=(0.0, -1.7, 2.7), size=(16.0, 0.3), aim=(0.0, -1.5, 3.2), power=110.0, color=(1.0, 0.82, 0.62)),
    ],
    "tunnel_landing": [
        dict(kind="area", pos=(0.0, 0.0, 2.9), size=(1.0, 2.0), aim=(0.0, 0.0, 0.0), power=12.0, color=(1.0, 0.85, 0.7)),
    ],
}

PROBE = {"ph_hall": (0.0, -4.6, 1.6), "ph_stair": (0.0, 0.0, 3.6)}
