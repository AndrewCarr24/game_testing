"""The bathhouse (the pool house): a detached building on the lap pool's axis, as plan data.

plan.py merges ROOMS and CUTS into its own (one marked block at its end), so house.py builds the
shell, mansion.py dresses the rooms (blender/levels/rooms/bathhouse.py), the bake lights them and
the engine treats them like every room. What house.py can't make (the pool basins, the secret
stair's solid treads and ramp, skylight glass, invisible blockers over the water) is built by
blender/levels/bathhouse_shell.py from the constants below. Design: design/grounds/pool_house.md.

Blender world metres, z up; floor z 0 (the lawn is 8 cm lower). Every room carries
building="bathhouse": the grounds leave it out of the main house's footprint (ground_colliders),
clad it in stone with a sedum roof (grounds.house_exterior) and cut the lawn under it.

    y 48.5 +-------------------------------------------------+
           |  ph_rest  (long north window)                  |
    y 44.5 +----------------------+-----------+---------------+
           |                      | ph_cold | (plunge = the |
           |  ph_hall           |  plunge   |  secret door) |
           |  5.4 m, glass west   +-----+-----+----------+----+ y 40.5
           |  indoor pool on the  |bath_|   ph_steam   |
           |  lap pool's axis     |stair|                |
           |                      |(-4.2|                |
    y 34.5 |                      +-----+----------------+    y 34.5
           |                      |  ph_fire  (red, hot pool)|
    y 31.0 +----------------------+---------------------------+
          x 27                  x 38.5  41.5               x 45
"""

T = 0.15
B = "bathhouse"

HALL = (27.0, 31.0, 38.5, 44.5)
FIRE = (38.5, 31.0, 45.0, 34.5)
STAIR = (38.5, 34.5, 41.5, 40.5)
STEAM = (41.5, 34.5, 45.0, 40.5)
COLD = (38.5, 40.5, 45.0, 44.5)
REST = (27.0, 44.5, 45.0, 48.5)
FOOTPRINT = (27.0, 31.0, 45.0, 48.5)

H_HALL, H_FIRE, H_STEAM, H_COLD, H_REST = 5.4, 3.0, 2.6, 3.6, 3.2
DEEP = -4.2                    # the tunnel's floor (the secret-passage workstream's landing)
LANDING_Z = -1.2               # the stair's top landing = the drained plunge's floor

# --- water (all surfaces 8 cm under the floor, flush stone copings)
WATER_Z = -0.08
POOL = (27.15, 34.9, 38.35, 40.9)          # the hall's pool (inside its walls): the lap pool's y 34.9..40.9, on its axis
POOL_FLOOR = -1.4
POOL_WINDOW = (35.0, 40.2, -1.32, -0.18)   # glass in the pool's east end = the stair's west wall (y0, y1, z0, z1)
HOT = (40.0, 32.15, 43.5, 33.35)           # the fire bath's hot pool (inside its walls)
HOT_FLOOR = -0.75
# the pool runs wall to wall: the hall's north half (the arrival) reaches its south half (the
# doors out) only through the stone rooms (cold -> steam -> fire) or over these stepping stones
# across the water, half a metre inside the glass, in full view of the lawn
STONES_X = (27.7, 28.3)
STONES = [(35.2, 35.75), (36.05, 36.6), (36.9, 37.45), (37.75, 38.3), (38.6, 39.15), (39.45, 40.0), (40.3, 40.85)]
STONE_TOP = -0.015
PLUNGE = (38.65, 40.65, 41.35, 42.85)      # the cold plunge (interior); its floor is the landing
PLUNGE_STEPS = 5                           # risers of 0.2 m rising north from y 41.35 to the floor at 42.85
SLAB_DOOR = (39.25, 40.75)                 # the sinking stone slab in the plunge's south wall (x span)
SLAB_TOP = 1.0

# --- the secret stair (rises north from the tunnel landing to the plunge)
STAIR_RISERS = 17
STAIR_Y0 = 34.65                           # first riser
STAIR_RUN = 0.28

# skylights (ceiling_holes) and their glass
SKY_HALL = (37.55, 31.5, 38.35, 44.0)      # a slot along the east wall: light washes down the stone
SKY_STAIR = (38.95, 34.95, 41.05, 40.05)   # the top of the shaft
SKY_FIRE = (39.1, 33.95, 44.4, 34.35)      # a slot along the red room's north wall

# the passage workstream's landing (x 38.5..41.5, y 31.5..34.5, z -4.2) as a stand-in room, so
# the stair can be walked and tested before their tunnel is merged. The orchestrator drops it
# (STUB_LANDING = False) when their landing room exists.
STUB_LANDING = True
LANDING = (38.5, 31.5, 41.5, 34.5)

ROOMS = {
    "ph_hall":  dict(rect=HALL, level=0, height=H_HALL, building=B, module=B, facade="stone",
                       floor_holes=[(POOL[0] - T, POOL[1] - T, POOL[2] + T, POOL[3] + T)], ceiling_holes=[SKY_HALL]),
    "ph_fire":  dict(rect=FIRE, level=0, height=H_FIRE, building=B, module=B, facade="stone",
                       floor_holes=[(HOT[0] - T, HOT[1] - T, HOT[2] + T, HOT[3] + T)], ceiling_holes=[SKY_FIRE]),
    "ph_stair": dict(rect=STAIR, level=-1, z0=DEEP, height=H_HALL - DEEP, building=B, module=B, facade="stone",
                       ceiling_holes=[SKY_STAIR]),
    "ph_steam": dict(rect=STEAM, level=0, height=H_STEAM, building=B, module=B, facade="stone"),
    "ph_cold":  dict(rect=COLD, level=0, height=H_COLD, building=B, module=B, facade="stone",
                       floor_holes=[(PLUNGE[0] - T, PLUNGE[1] - T, PLUNGE[2] + T, PLUNGE[3])]),
    "ph_rest":  dict(rect=REST, level=0, height=H_REST, building=B, module=B, facade="stone"),
}
if STUB_LANDING:
    ROOMS["tunnel_landing"] = dict(rect=LANDING, level=-1, z0=DEEP, height=3.0, building=B, module=B, facade="stone", stub=True)

CUTS = [
    # ---- the hall's west wall: glass, floor to ceiling, 1.5 m bays, onto the lawn and the lap pool
    dict(kind="window", facade=True, axis="y", line=27.0, span=(31.0, 32.5), z=(0, H_HALL)),
    dict(kind="opening", axis="y", line=27.0, span=(32.5, 34.0), z=(0, 3.0), door="door_glass", swing="ph_hall",
         swing_out=True, inset=0.0, reveal=False),
    dict(kind="window", facade=True, axis="y", line=27.0, span=(32.5, 34.0), z=(3.0, H_HALL)),
    dict(kind="window", facade=True, axis="y", line=27.0, span=(34.0, 44.5), z=(0, H_HALL)),
    # the hall's south wall: the way in from the house's terrace, and one tall slot of glass
    dict(kind="opening", axis="x", line=31.0, span=(29.6, 30.7), z=(0, 2.5), door="door_plain", swing="ph_hall"),
    dict(kind="window", facade=True, axis="x", line=31.0, span=(35.0, 35.6), z=(0, H_HALL)),
    # hall <-> the stone rooms: plain openings (no doors: you turn a corner into each, as at Vals)
    dict(kind="opening", axis="y", line=38.5, span=(31.45, 32.65), z=(0, 2.4)),             # -> fire bath
    dict(kind="opening", axis="y", line=38.5, span=(43.1, 44.35), z=(0, 2.4)),              # -> cold plunge
    dict(kind="opening", axis="x", line=44.5, span=(30.0, 36.0), z=(0, 2.8)),               # -> rest room
    # the pool's east end is glass: below the hall floor, it is the secret stair's west wall
    dict(kind="window", axis="y", line=38.5, span=POOL_WINDOW[:2], z=POOL_WINDOW[2:]),
    # ---- the stone rooms
    dict(kind="opening", axis="x", line=34.5, span=(42.65, 43.75), z=(0, 2.4), door="ph_door_steam", swing="ph_steam"),
    dict(kind="opening", axis="x", line=40.5, span=(42.65, 43.75), z=(0, 2.4), door="ph_door_steam", swing="ph_steam"),
    dict(kind="opening", axis="x", line=44.5, span=(42.85, 43.95), z=(0, 2.4)),             # cold <-> rest
    dict(kind="opening", axis="y", line=45.0, span=(32.35, 33.45), z=(0, 2.5), door="door_plain", swing="ph_fire"),
    dict(kind="window", facade=True, axis="y", line=45.0, span=(41.35, 41.85), z=(0.55, 3.3)),          # the cold room's slit
    dict(kind="window", facade=True, axis="x", line=48.5, span=(28.5, 43.5), z=(0.45, 2.85)),           # the rest room's long window
    # ---- the secret: the plunge's south wall is the stair's head; a stone slab sinks out of it
    dict(kind="opening", axis="x", line=40.5, span=SLAB_DOOR, z=(LANDING_Z, SLAB_TOP)),
    # the tunnel landing (the passage workstream's) opens into the stair's foot
    dict(kind="opening", axis="x", line=34.5, span=(38.65, 41.35), z=(DEEP, DEEP + 2.9)),
]

# where the lawn's 1 m ground collider (ground_colliders.base) and the lawn mesh are cut away
LAWN_HOLES = [FOOTPRINT]
