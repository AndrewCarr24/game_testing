"""The gallery ring around the courtyard, both floors (gallery_* and ugallery_*).
Each gallery is 3.5 m wide (3.2 inside); the courtyard side is glass. Artworks hang
on solid stretches of the outer walls: picture origins sit on the wall face, centred
1.6 m up; rot 0 faces south (a north wall), 180 faces north (a south wall)."""

ART_Z = 1.6
PLACEMENTS = {
    # upper north gallery: the long wall between the bedroom and office doors
    "ugallery_n": [
        ("art_colorfield_a", (-8.0, 1.6, ART_Z), 0),
        ("art_geometric_a", (-3.4, 1.6, ART_Z), 0),
        ("art_linework_a", (1.6, 1.6, ART_Z), 0),
    ],
    # ground south gallery: the wall beside the entry opening
    "gallery_s": [
        ("art_colorfield_b", (-6.0, -1.6, ART_Z), 180),
        ("art_geometric_b", (-1.0, -1.6, ART_Z), 180),
    ],
}

LIGHTS = {
    "gallery_s": [dict(kind="strip", pos=(0, 0), size=(24.0, 0.08), power=160.0)],
    "gallery_n": [dict(kind="strip", pos=(0, 0), size=(24.0, 0.08), power=160.0)],
    "gallery_w": [dict(kind="strip", pos=(0, 0), size=(0.08, 11.0), power=80.0)],
    "gallery_e": [dict(kind="strip", pos=(0, 0), size=(0.08, 11.0), power=80.0)],
    "ugallery_s": [dict(kind="strip", pos=(0, 0), size=(24.0, 0.08), power=150.0)],
    "ugallery_n": [dict(kind="strip", pos=(0, 0), size=(24.0, 0.08), power=150.0)],
    "ugallery_w": [dict(kind="strip", pos=(0, 0), size=(0.08, 11.0), power=75.0)],
    "ugallery_e": [dict(kind="strip", pos=(0, 0), size=(0.08, 11.0), power=75.0)],
}
