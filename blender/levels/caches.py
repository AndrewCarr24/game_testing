"""Locks, keys and caches: what is locked in the house, where its key is, and what's inside.
Exploring pays off without a goal or story (no notes, no codes): short chains of 2-3 steps,
each key opens one lock, every lock says what it needs ("Locked · needs the office key").

  A. the primary suite (keycard door; a quiet room to hide in, a battery in the nightstand)
     guest room nightstand drawer -> OFFICE KEY -> office door (and the gym behind it)
     -> office desk drawer -> KEYCARD -> primary suite door
  B. the car key (the car alarm is a distraction: see the distraction workstream)
     library reading table -> SAFE KEY -> office floor safe (behind the office door)
     -> CAR KEY + a battery
  C. the fuse and the flashlight (power: see the power workstream)
     garage workbench drawer -> CELLAR KEY -> wine room climate cabinet (glass door, the key
     shows through it) -> LOCKER KEY -> garage steel locker -> FUSE + FLASHLIGHT + a battery

In the open, unlocked: the tablet (kitchen dock), a battery on the kitchen counter, books,
bottles, vases. Locked doors take their lock from plan.CUTS (`lock=`); everything else is here.

mansion.py merges this into the rooms' PLACEMENTS (room_placements): LOCKS add {"lock": key}
to the room's first placement of an asset already dressed there, PLACEMENTS append props
(room-local; with "attach", in the host node's local frame: a drawer, or a container's
static `<Asset>_Inside` node). Hosts must come before what's attached to them, and `attach`
lands on the level's FIRST placement of the host asset.
"""

# key item id -> what it opens (for the test and the report; the engine reads locks from props)
KEYS = {
    "key_office": "office door",
    "keycard": "primary suite door",
    "key_safe": "office safe",
    "key_cellar": "wine room climate cabinet",
    "key_locker": "garage locker",
}

# room -> [(asset already placed in that room, key item id)]
LOCKS = {
    "wine_room": [("dining_climate_wall", "key_cellar")],
}

# key/drawer-local frames (from the host assets): nightstand drawer floor z -0.073 (y 0.02..0.34
# behind the front), guest nightstand -0.058 (y 0.02..0.32), workbench drawer -0.059 (y -0.41..0)
PLACEMENTS = {
    # A: the office key in the guest room's bed-side drawer (the north nightstand)
    "guest_room": [
        ("ix_key_office", (0.05, 0.12, -0.058), 25, {"attach": ("guest_nightstand", "GuestNightstand_Drawer")}),
    ],
    # A's reward: a battery in the primary bedroom's north nightstand drawer
    "primary_bedroom": [
        ("ix_battery", (-0.06, 0.16, -0.073), 70, {"attach": ("nightstand", "Nightstand_Drawer")}),
    ],
    # B: the safe key on the library's reading table, by the east lamp
    "library": [
        ("ix_key_safe", (2.0, 0.3, 0.76), 35),
    ],
    # B: the floor safe against the office's east wall, north of the gym door (front faces west)
    "office": [
        ("ix_safe", (6.33, 3.3), -90, {"lock": "key_safe"}),
        ("ix_car_key", (0.06, 0.0, 0.0), 20, {"attach": ("ix_safe", "IX_Safe_Inside")}),
        ("ix_battery", (-0.13, 0.04, 0.0), 75, {"attach": ("ix_safe", "IX_Safe_Inside")}),
    ],
    # C: the cellar key in the workbench drawer (where the fuse was); the locker on the west wall
    # beside the breaker panel (south of it, front facing east; its door swings south)
    "garage": [
        ("ix_key_cellar", (0.06, -0.15, -0.059), 20, {"attach": ("garage_workbench", "GarageWorkbench_Drawer")}),
        ("ix_gun_locker", (-5.83, -2.2), 90, {"lock": "key_locker"}),
        ("ix_flashlight", (-0.2, 0.0, 0.0), 8, {"attach": ("ix_gun_locker", "IX_GunLocker_Inside")}),
        ("ix_fuse", (0.08, -0.04, 0.0), -15, {"attach": ("ix_gun_locker", "IX_GunLocker_Inside")}),
        ("ix_battery", (0.26, 0.05, 0.0), 25, {"attach": ("ix_gun_locker", "IX_GunLocker_Inside")}),
    ],
    # C: the locker key on the climate cabinet's first shelf, behind the opening glass door
    "wine_room": [
        ("ix_key_locker", (0.0, 0.0, 0.0), 160, {"attach": ("dining_climate_wall", "DiningClimateWall_Inside")}),
    ],
}


def apply(room, placements):
    """The room's placements with this module's locks and props merged in (a new list)."""
    out = list(placements)
    for asset, key in LOCKS.get(room, []):
        for i, (a, loc, rot, *rest) in enumerate(out):
            if a == asset:
                out[i] = (a, loc, rot, {**(rest[0] if rest else {}), "lock": key})
                break
        else:
            print(f"CACHES: {room} has no {asset} to lock with {key}")
    return out + list(PLACEMENTS.get(room, []))
