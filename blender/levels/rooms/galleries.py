"""The gallery ring around the courtyard, both floors (gallery_* and ugallery_*).
Each gallery is 3.5 m wide (3.2 inside); the courtyard side is glass. Artworks hang
on solid stretches of the outer walls: picture origins sit on the wall face, centred
1.6 m up; rot 0 faces south (a north wall), 180 faces north (a south wall)."""

ART_Z = 1.6
PLACEMENTS = {
    # upper north gallery: the long wall between the bedroom and office doors
    "ugallery_n": [
        ("art_dune", (-8.0, 1.6, ART_Z), 0),             # photograph
        ("art_squares_ochre", (-3.4, 1.6, ART_Z), 0),    # nested squares, floater frame
        ("art_colour_chart", (1.6, 1.6, ART_Z), 0),      # watercolour swatches, box frame
    ],
    # ground south gallery: the wall beside the entry opening
    "gallery_s": [
        ("art_zip_red", (-6.0, -1.6, ART_Z), 180),       # red field with zips
        ("art_fog_pines", (-1.0, -1.6, ART_Z), 180),     # photograph, matted
    ],
}

# --- set dressing (decor_c_*): a few pauses along the ring, on the solid outer walls only, so
# the 3.2 m walkway stays clear (each gallery uses at most three materials: walnut, charcoal
# ceramic, and leaves or books). Walnut benches under the big pieces, walnut consoles with
# books and charcoal vessels on bare stretches, snake plants in charcoal planters.
DECOR = {
    "gallery_s": [
        ("decor_c_gallery_bench", (-6.0, -1.37), 180),            # under the red zip painting
        ("decor_c_plant_snake", (-3.5, -1.3), 40),                # between the two pieces
    ],
    "gallery_n": [
        ("decor_c_vignette_gallery", (-6.75, 1.415), 0),          # bare wall west of the great-room opening
    ],
    "gallery_w": [
        ("decor_c_gallery_bench", (-1.37, 0.0), 90),              # between the two great-room openings
    ],
    "gallery_e": [
        ("decor_c_vignette_gallery", (1.415, -2.6), -90, ),       # south of the door
    ],
    "ugallery_n": [
        ("decor_c_gallery_bench", (-8.0, 1.37), 0),               # under the dune photograph
        ("decor_c_vignette_gallery", (-0.9, 1.415), 0),           # between the ochre squares and the chart
    ],
    "ugallery_e": [
        ("decor_c_gallery_bench", (1.37, 1.2), -90),
        ("decor_c_plant_snake", (1.3, 5.75), 10),
    ],
    "ugallery_s": [
        ("decor_c_plant_snake", (-8.7, -1.3), 70),                # the solid stretch by the door
    ],
}
for _room, _items in DECOR.items():
    PLACEMENTS.setdefault(_room, []).extend(_items)

# --- lighting: a downlight on the line of every mullion of the courtyard glass ---------------
# The glass bays set the rhythm: across from each mullion, a small recessed downlight
# (light_u_downlight) sits 0.75 m off the outer wall and washes it in a soft scallop, so
# walking the ring you pass light / bay / light like the colonnade of a cloister, and the
# art on the outer walls is lit wherever it hangs. Where the outer side is open (a doorway,
# a balustrade over the entry or the great room, a window) the same downlight drops a pool on
# the floor instead. The corner squares get one downlight each. No ceiling strips.
CEIL = {"gallery_s": 4.2, "gallery_n": 4.2, "gallery_w": 4.2, "gallery_e": 4.2,
        "ugallery_s": 3.8, "ugallery_n": 3.8, "ugallery_w": 3.8, "ugallery_e": 3.8}
# per gallery: run axis ("x" for s/n, "y" for w/e), the outer wall's local coordinate, the
# glass spans (plan.CUTS, local) whose mullions set the rhythm, and the open stretches of the
# outer side (local, along the run)
_RUNS = {
    "gallery_s": ("x", -1.6, [(-10, -1.5), (1.5, 10)], [(2.5, 7.0)]),
    "gallery_n": ("x", 1.6, [(-10, 10)], [(-13.0, -10.5), (-3.0, 3.0)]),
    "gallery_w": ("y", -1.6, [(-7, 7)], [(-5.5, -1.5), (1.5, 5.5)]),
    "gallery_e": ("y", 1.6, [(-7, 7)], [(2.95, 4.05)]),
    "ugallery_s": ("x", -1.6, [(-10, 10)], [(-8.0, 8.0), (8.5, 13.0), (-11.3, -10.2)]),
    "ugallery_n": ("x", 1.6, [(-10, 10)], [(-12.3, -11.2), (6.2, 7.3)]),
    "ugallery_w": ("y", -1.6, [(-7, 7)], [(-7.0, 7.0)]),
    "ugallery_e": ("y", 1.6, [(-7, 7)], [(-6.5, -0.5), (2.95, 4.05)]),
}
DL_OFF = 0.75          # downlight distance from the outer wall
DL_POWER = {0: 130.0, 1: 110.0}     # W per spot, ground / upper floor


def _mullions(a0, a1, pitch=1.5):
    """Mullion positions exactly as house.glazing() spaces them."""
    n = max(1, int(round((a1 - a0) / pitch)))
    return [a0 + i * (a1 - a0) / n for i in range(n + 1)]


def _gallery_lighting(room):
    axis, wall, spans, open_ = _RUNS[room]
    zc = CEIL[room]
    upper = room.startswith("u")
    lim = 13.35 if axis == "x" else 6.85
    at = sorted({round(m, 3) for a0, a1 in spans for m in _mullions(a0, a1) if abs(m) < lim - 0.3})
    if axis == "x":
        at += [-11.75, 11.75]                 # the corner squares belong to the s / n galleries
    inward = -1 if wall > 0 else 1
    off = wall + inward * DL_OFF
    places, lights = [], []
    for a in at:
        corner = abs(a) > 10.5
        is_open = any(o0 - 0.2 <= a <= o1 + 0.2 for o0, o1 in open_)
        c = 0.0 if corner else off
        xy = (a, c) if axis == "x" else (c, a)
        places.append(("light_u_downlight", (*xy, zc), 0))
        pos = (*xy, zc - 0.03)
        if corner or is_open:
            aim = (*xy, 0.0)
            lights.append(dict(kind="spot", pos=pos, aim=aim, power=DL_POWER[upper] * 0.8, angle=80.0, blend=0.8,
                               color=(1.0, 0.82, 0.62)))
        else:
            aim = (a, wall, 1.1) if axis == "x" else (wall, a, 1.1)
            lights.append(dict(kind="spot", pos=pos, aim=aim, power=DL_POWER[upper], angle=75.0, blend=0.7,
                               color=(1.0, 0.82, 0.62)))
    return places, lights


LIGHTS = {}
for _room in _RUNS:
    _p, _l = _gallery_lighting(_room)
    PLACEMENTS.setdefault(_room, []).extend(_p)
    LIGHTS[_room] = _l


# --- interactivity (prompts/interactivity.md): no doors, so no switch: the ring's fixtures share
# lights_galleries, on at the start (the tablet can switch it)
import importlib as _il  # noqa: E402
import ix_common  # noqa: E402

_il.reload(ix_common)
PLACEMENTS = {_r: ix_common.wire(_v, "galleries", state=True) for _r, _v in PLACEMENTS.items()}
