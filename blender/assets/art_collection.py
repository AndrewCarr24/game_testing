"""The house's art collection: one entry per hanging picture (picture_frame variants).

Pure data (no bpy). Each piece: outer `size` (w, h) in metres, `frame` treatment, its
painting (`style` from art_painters + `spec`), the texture's long side `px` (soft fields
and photographs 192-256, hard edges and fine lines 384-512), `rough` / `metal` of the
artwork's surface, and where it hangs (`at`, for reference only; placements live in the
room modules). Every piece is hung exactly once.

Frames (all reuse shared materials; only the artwork's material is unique):
  metal    slim black-metal frame (M_Aluminium_Black), white mat of width `border`
           (0 = no mat, photograph to the frame), glass
  wood     the same in walnut or smoked oak (`wood`), wider face
  box      deep white box frame (M_Picture_Mat), the work on paper floated on a white
           backing with a `margin` all round, glass
  canvas   unframed canvas on a deep stretcher, painted edges, no glass
  floater  canvas set into a black-metal tray frame with a shadow gap, no glass
"""
import random

FRAMES = {
    "metal": dict(face=0.02, depth=0.04),
    "wood": dict(face=0.032, depth=0.035),
    "box": dict(face=0.022, depth=0.05),
    "canvas": dict(depth=0.04),
    "floater": dict(face=0.012, gap=0.012, depth=0.05),
}

MAT_T = 0.0035          # mat board thickness (the bevel)
ART_OVERLAP = 0.012     # artwork runs this far behind the mat / frame lip


def art_size(v):
    """(w, h) of the painted surface in metres for a variant."""
    w, h = v["size"]
    fr = v.get("frame", "metal")
    if fr in ("metal", "wood"):
        face = FRAMES[fr]["face"]
        b = v.get("border", 0.09)
        if b <= 0:
            return w - 2 * face + 2 * ART_OVERLAP, h - 2 * face + 2 * ART_OVERLAP
        return (w - 2 * (face + b) - 2 * MAT_T + 2 * ART_OVERLAP,
                h - 2 * (face + b) - 2 * MAT_T + 2 * ART_OVERLAP)
    if fr == "box":
        m = v.get("margin", 0.06)
        face = FRAMES["box"]["face"]
        return w - 2 * (face + m), h - 2 * (face + m)
    if fr == "floater":
        f = FRAMES["floater"]
        return w - 2 * (f["face"] + f["gap"]), h - 2 * (f["face"] + f["gap"])
    return w, h


def texture_px(v):
    """Texture (w, h) in px: the long side is the variant's px."""
    aw, ah = art_size(v)
    n = v.get("px", 512)
    if aw >= ah:
        return n, max(16, int(round(n * ah / aw / 4)) * 4)
    return max(16, int(round(n * aw / ah / 4)) * 4), n


def _wine_rings(seed):
    r = random.Random(seed)
    wines = [(0.46, 0.08, 0.17), (0.40, 0.10, 0.22), (0.52, 0.12, 0.16), (0.36, 0.09, 0.14)]
    out = []
    # a loose diagonal drift of glasses set down and picked up again
    for k in range(11):
        t = k / 10
        cx = 0.25 + 0.50 * t + r.gauss(0, 0.08)
        cy = 0.20 + 0.60 * t + r.gauss(0, 0.05) + 0.06 * (k % 3 - 1)
        out.append((min(0.80, max(0.20, cx)), min(0.84, max(0.14, cy)), r.uniform(0.062, 0.074),
                    r.uniform(0.75, 1.0), r.choice(wines)))
    drops = [(r.uniform(0.2, 0.8), r.uniform(0.2, 0.85), r.uniform(0.002, 0.006), r.choice(wines)) for _ in range(9)]
    return out, drops


_RINGS, _DROPS = _wine_rings(7)

INK = (0.05, 0.05, 0.055)

PIECES = {
    # ------------------------------------------------------------------ great room
    "kline_bars": dict(
        at="great_room S wall, west", size=(1.5, 2.3), frame="canvas", px=384, rough=0.85,
        style="ink", spec=dict(seed=301, ground=(0.89, 0.86, 0.79), ground2=(0.93, 0.91, 0.86), strokes=[
            dict(pts=[(0.30, -0.06), (0.34, 0.30), (0.29, 0.68), (0.32, 1.06)], w=0.075, c=INK, dry=0.15, bristle=0.25),
            dict(pts=[(-0.05, 0.20), (0.45, 0.31), (1.06, 0.50)], w=0.05, c=INK, dry=0.35),
            dict(pts=[(0.22, 0.80), (0.62, 0.75), (0.96, 0.78)], w=0.042, c=INK, dry=0.65),
            dict(pts=[(0.80, 0.06), (0.77, 0.46)], w=0.032, c=INK, dry=0.75),
            dict(pts=[(0.44, 0.56), (0.70, 0.60)], w=0.04, c=(0.91, 0.89, 0.83), a=0.9, dry=0.5),
        ])),
    "pencil_grid": dict(
        at="great_room S wall, beside the tall canvas", size=(1.1, 1.1), frame="canvas", px=384, rough=0.9,
        style="grid", spec=dict(seed=302, ground=(0.93, 0.915, 0.875), margin=0.035, rows=24, cols=0,
                                bands=[((0.93, 0.80, 0.76), 0.30), ((0.95, 0.94, 0.90), 0.2),
                                       ((0.80, 0.85, 0.88), 0.28), ((0.95, 0.94, 0.90), 0.2)] * 3,
                                pencil_a=0.5)),
    "seascape": dict(
        at="great_room S wall over the console", size=(2.2, 1.45), frame="metal", border=0.0, px=256, rough=0.35,
        style="photo", spec=dict(seed=303, scene="seascape", horizon=0.5,
                                 sky=[(0.60, 0.645, 0.67), (0.85, 0.86, 0.855)],
                                 sea=[(0.47, 0.51, 0.53), (0.28, 0.31, 0.34)], haze=0.035, grain=0.012)),
    "blocks_umber": dict(
        at="great_room E wall, north of the fireplace", size=(2.0, 1.6), frame="floater", px=384, rough=0.85,
        style="blocks", spec=dict(seed=304, under=(0.17, 0.12, 0.09), rows=[1.0, 1.1, 0.9],
                                  cols=[[1.2, 1.0, 1.4], [1.0, 1.3, 0.9], [1.4, 0.8, 1.1]],
                                  palette=[(0.33, 0.22, 0.15), (0.37, 0.39, 0.41), (0.68, 0.50, 0.27),
                                           (0.085, 0.075, 0.07), (0.68, 0.50, 0.46), (0.80, 0.76, 0.68)],
                                  order=[0, 4, 3, 5, 1, 2, 3, 0, 5])),
    "curve_vermilion": dict(
        at="great_room E wall, south of the fireplace", size=(2.0, 1.6), frame="canvas", px=384, rough=0.8,
        style="hardedge", spec=dict(seed=305, ground=(0.93, 0.92, 0.885), wobble=0.0002, shapes=[
            dict(t="circle", p=(-0.32, 1.62, 1.50), c=(0.84, 0.24, 0.10)),
        ])),
    "mono_ultramarine": dict(
        at="great_room N wall, east of the dining opening", size=(1.4, 1.8), frame="canvas", px=192, rough=0.9,
        style="mono", spec=dict(seed=306, c=(0.10, 0.15, 0.46), angles=(15, 75, 130), stretch=7, amp=0.05,
                                relief=0.12, tone=0.05)),
    "weave_indigo": dict(
        at="great_room N wall, west of the dining opening", size=(1.4, 1.8), frame="canvas", px=384, rough=0.95,
        style="weave", spec=dict(seed=307, mode="blocks", pitch_m=0.006,
                                 rows=[1.2, 0.7, 1.5, 0.5, 1.1],
                                 cols=[[1, 1.5], [2, 1, 1], [1, 1], [1, 3, 1], [1.3, 1]],
                                 palette=[(0.12, 0.16, 0.30), (0.84, 0.79, 0.67), (0.07, 0.07, 0.08),
                                          (0.36, 0.43, 0.56), (0.60, 0.30, 0.18)],
                                 order=[[0, 1], [2, 3, 0], [1, 0], [0, 4, 0], [3, 2]],
                                 insets=[(0.62, 0.30, 0.80, 0.42, 1), (0.15, 0.66, 0.30, 0.70, 1)])),
    # ------------------------------------------------------------------ dining
    "sweep_terracotta": dict(
        at="dining S wall, west segment", size=(1.3, 1.0), frame="canvas", px=384, rough=0.9,
        style="ink", spec=dict(seed=308, ground_kind="linen", ground=(0.80, 0.74, 0.62), strokes=[
            dict(pts=[(0.08, 0.76), (0.28, 0.36), (0.60, 0.24), (0.90, 0.48)], w=[0.06, 0.09, 0.08, 0.035],
                 c=(0.64, 0.29, 0.16), a=0.94, dry=0.6, bristle=0.5),
            dict(pts=[(0.14, 0.86), (0.55, 0.81), (0.92, 0.85)], w=0.011, c=(0.15, 0.14, 0.13), dry=0.4),
        ])),
    # ------------------------------------------------------------------ galleries
    "dune": dict(
        at="ugallery_n, west", size=(1.6, 1.1), frame="metal", border=0.0, px=256, rough=0.35,
        style="photo", spec=dict(seed=309, scene="dune",
                                 crest2=[(0, 0.30), (0.4, 0.21), (1, 0.12)],
                                 crest1=[(0, 0.95), (0.3, 0.66), (0.62, 0.44), (1.0, 0.34)],
                                 lit=[(0.86, 0.52, 0.30), (0.70, 0.36, 0.19)],
                                 shadow=[(0.27, 0.11, 0.09), (0.42, 0.19, 0.13)],
                                 far=[(0.90, 0.70, 0.52), (0.82, 0.54, 0.35)], ripples=34)),
    "squares_ochre": dict(
        at="ugallery_n, centre", size=(1.0, 1.0), frame="floater", px=256, rough=0.75,
        style="hardedge", spec=dict(seed=310, ground=(0.69, 0.45, 0.13), wobble=0.0002, grain=0.006, shapes=[
            dict(t="rect", r=(0.1, 0.15, 0.9, 0.95), c=(0.79, 0.57, 0.17)),
            dict(t="rect", r=(0.2, 0.30, 0.8, 0.90), c=(0.875, 0.69, 0.25)),
            dict(t="rect", r=(0.3, 0.45, 0.7, 0.85), c=(0.94, 0.82, 0.42)),
        ])),
    "colour_chart": dict(
        at="ugallery_n, east", size=(1.0, 1.3), frame="box", margin=0.07, px=384, rough=0.9,
        style="wash", spec=dict(seed=311, mode="chart", grid=(6, 4), margin=(0.11, 0.09, 0.13), a=0.8, colours=[
            (0.96, 0.86, 0.35), (0.95, 0.76, 0.28), (0.93, 0.62, 0.25), (0.90, 0.48, 0.24),
            (0.86, 0.36, 0.25), (0.78, 0.26, 0.28), (0.70, 0.24, 0.36), (0.58, 0.26, 0.44),
            (0.46, 0.30, 0.52), (0.36, 0.34, 0.58), (0.28, 0.40, 0.64), (0.24, 0.48, 0.68),
            (0.22, 0.56, 0.66), (0.22, 0.60, 0.58), (0.30, 0.62, 0.48), (0.44, 0.64, 0.40),
            (0.60, 0.66, 0.36), (0.74, 0.68, 0.36), (0.66, 0.54, 0.38), (0.55, 0.43, 0.34),
            (0.44, 0.36, 0.32), (0.36, 0.34, 0.34), (0.28, 0.28, 0.30), (0.18, 0.18, 0.20)])),
    "zip_red": dict(
        at="gallery_s, west", size=(1.6, 1.1), frame="canvas", px=384, rough=0.85,
        style="hardedge", spec=dict(seed=312, ground=(0.57, 0.065, 0.055), wobble=0.0008, grain=0.01, shapes=[
            dict(t="rect", r=(0.27, -0.1, 0.282, 1.1), c=(0.90, 0.86, 0.76), wob=3.0),
            dict(t="rect", r=(0.64, -0.1, 0.675, 1.1), c=(0.35, 0.035, 0.045)),
            dict(t="rect", r=(0.86, -0.1, 0.866, 1.1), c=(0.86, 0.36, 0.10), wob=2.0),
        ])),
    "fog_pines": dict(
        at="gallery_s, east", size=(1.0, 1.3), frame="metal", border=0.09, px=256, rough=0.4,
        style="photo", spec=dict(seed=313, scene="fog", fog=[(0.80, 0.82, 0.82), (0.88, 0.89, 0.88), (0.72, 0.74, 0.72)],
                                 layers=[(16, 0.005, 0.16, 3.0), (11, 0.008, 0.32, 1.8), (7, 0.012, 0.55, 0.9),
                                         (3, 0.020, 0.85, 0.3)],
                                 dark=(0.15, 0.17, 0.16), floor=(0.42, 0.45, 0.41), ground_y=0.9, grain=0.02)),
    # ------------------------------------------------------------------ den
    "stain_tall": dict(
        at="den N wall over the console", size=(1.2, 1.8), frame="canvas", px=256, rough=0.9,
        style="stain", spec=dict(seed=314, pools=[
            dict(e=(0.36, 0.30, 0.30, 0.21), c=(0.86, 0.60, 0.22), a=0.6),
            dict(e=(0.62, 0.52, 0.30, 0.20), c=(0.28, 0.52, 0.54), a=0.55),
            dict(e=(0.42, 0.74, 0.27, 0.15), c=(0.84, 0.42, 0.40), a=0.5),
            dict(e=(0.70, 0.20, 0.10, 0.07), c=(0.42, 0.28, 0.20), a=0.65, rough=0.25),
        ])),
    # ------------------------------------------------------------------ guest room
    "clouds": dict(
        at="guest_room W wall over the bed", size=(1.5, 1.0), frame="metal", border=0.07, px=256, rough=0.4,
        style="photo", spec=dict(seed=315, scene="clouds", sky=[(0.46, 0.61, 0.77), (0.77, 0.83, 0.87)],
                                 cloud=[(0.60, 0.63, 0.68), (0.98, 0.97, 0.95)], bias=-0.25, bank=1.2)),
    "wash_circles": dict(
        at="guest_room S wall over the desk", size=(0.6, 0.8), frame="wood", wood="oak", border=0.07, px=256,
        rough=0.9, style="wash", spec=dict(seed=316, mode="circles", circles=[
            (0.44, 0.38, 0.19, (0.32, 0.47, 0.70), 0.55),
            (0.58, 0.56, 0.17, (0.86, 0.66, 0.32), 0.5),
            (0.42, 0.68, 0.11, (0.80, 0.42, 0.36), 0.45)])),
    "bone_white": dict(
        at="guest_room N wall over the dresser", size=(0.8, 0.8), frame="canvas", px=192, rough=0.9,
        style="mono", spec=dict(seed=317, c=(0.90, 0.88, 0.82), angles=(0,), stretch=4, amp=0.03, relief=0.07,
                                tone=0.015, edge=0.02, dabs=150)),
    # ------------------------------------------------------------------ gym
    "target": dict(
        at="gym W wall", size=(1.2, 1.2), frame="canvas", px=256, rough=0.9,
        style="hardedge", spec=dict(seed=318, raw=True, ground=(0.82, 0.77, 0.66), soft=1.4, wobble=0.0015, shapes=[
            dict(t="circle", p=(0.5, 0.5, 0.065), c=(0.82, 0.16, 0.10)),
            dict(t="ring", p=(0.5, 0.5, 0.10, 0.155), c=(0.12, 0.25, 0.62)),
            dict(t="ring", p=(0.5, 0.5, 0.19, 0.27), c=(0.96, 0.76, 0.14)),
            dict(t="ring", p=(0.5, 0.5, 0.305, 0.335), c=(0.10, 0.10, 0.10)),
            dict(t="ring", p=(0.5, 0.5, 0.37, 0.455), c=(0.08, 0.50, 0.48)),
        ])),
    # ------------------------------------------------------------------ kitchen
    "still_life": dict(
        at="kitchen W wall, north of the opening", size=(0.8, 1.0), frame="canvas", px=256, rough=0.85,
        style="hardedge", spec=dict(seed=319, painterly=True, soft=1.6, wobble=0.0025,
                                    ground=(0.74, 0.70, 0.62), ground2=(0.64, (0.82, 0.77, 0.66)), shapes=[
            dict(t="rrect", r=(0.30, 0.30, 0.45, 0.67), rad=0.02, c=(0.60, 0.60, 0.56)),
            dict(t="rrect", r=(0.345, 0.14, 0.405, 0.33), rad=0.008, c=(0.60, 0.60, 0.56)),
            dict(t="rect", r=(0.47, 0.42, 0.66, 0.67), c=(0.87, 0.83, 0.73), dir=0),
            dict(t="rrect", r=(0.68, 0.50, 0.83, 0.675), rad=0.015, c=(0.73, 0.56, 0.32)),
            dict(t="ellipse", p=(0.755, 0.505, 0.056, 0.012), c=(0.58, 0.43, 0.24)),
            dict(t="rrect", r=(0.17, 0.45, 0.28, 0.672), rad=0.02, c=(0.47, 0.52, 0.57)),
            dict(t="rrect", r=(0.205, 0.36, 0.245, 0.47), rad=0.006, c=(0.47, 0.52, 0.57)),
        ], shadows=[dict(t="ellipse", p=(0.60, 0.685, 0.26, 0.016), a=0.22)])),
    "linen_check": dict(
        at="kitchen E wall, north of the opening", size=(0.85, 1.1), frame="box", margin=0.07, px=384, rough=0.95,
        style="weave", spec=dict(seed=320, mode="check", pitch_m=0.0035,
                                 warp=[(0.10, (0.86, 0.82, 0.72)), (0.014, (0.62, 0.24, 0.14)),
                                       (0.008, (0.86, 0.82, 0.72)), (0.014, (0.62, 0.24, 0.14)),
                                       (0.09, (0.86, 0.82, 0.72)), (0.005, (0.20, 0.20, 0.22))],
                                 weft=[(0.12, (0.86, 0.82, 0.72)), (0.010, (0.20, 0.20, 0.22)),
                                       (0.006, (0.86, 0.82, 0.72)), (0.024, (0.62, 0.24, 0.14)),
                                       (0.08, (0.86, 0.82, 0.72))], warp_off=0.03, weft_off=0.05)),
    # ------------------------------------------------------------------ mudroom
    "contour_map": dict(
        at="mudroom N wall", size=(0.8, 1.0), frame="box", margin=0.06, px=384, rough=0.9,
        style="contour", spec=dict(seed=321, beta=3.1, step=0.17, lake=-1.35,
                                   hills=[(0.62, 0.36, 0.16, 1.4), (0.30, 0.66, 0.12, 0.9)])),
    # ------------------------------------------------------------------ office
    "cyanotype_fern": dict(
        at="office W wall over the credenza, south of the pair", size=(0.6, 0.8), frame="wood", wood="walnut",
        border=0.07, px=384, rough=0.9,
        style="cyano", spec=dict(seed=322, plants=[("fern", 0.52, 0.96, 0.46, 0.08, 0.10),
                                                   ("fern", 0.36, 0.98, 0.20, 0.42, -0.10)])),
    "cyanotype_umbel": dict(
        at="office W wall over the credenza, north of the pair", size=(0.6, 0.8), frame="wood", wood="walnut",
        border=0.07, px=384, rough=0.9,
        style="cyano", spec=dict(seed=323, blue=(0.06, 0.19, 0.40), plants=[
            ("umbel", 0.50, 0.97, 0.47, 0.30, 0.34), ("umbel", 0.40, 0.97, 0.28, 0.52, 0.22),
            ("umbel", 0.58, 0.97, 0.72, 0.58, 0.20)])),
    "calligraphy": dict(
        at="office S wall, east of the door", size=(1.1, 0.85), frame="box", margin=0.07, px=384, rough=0.9,
        style="ink", spec=dict(seed=324, ground_kind="paper", ground=(0.94, 0.92, 0.87), strokes=[
            dict(pts=[(0.14, 0.72), (0.28, 0.26), (0.52, 0.20), (0.68, 0.56), (0.88, 0.38)],
                 w=[0.03, 0.075, 0.05, 0.035, 0.010], c=INK, dry=0.75, bristle=0.45),
        ], splatter=[(0.17, 0.74, 16, 0.045, 0.006, INK)])),
    "salt_ponds": dict(
        at="office S wall over the credenza", size=(1.6, 1.0), frame="metal", border=0.08, px=256, rough=0.4,
        style="photo", spec=dict(seed=325, scene="ponds", splits=30, earth=(0.66, 0.58, 0.48),
                                 palette=[(0.82, 0.48, 0.50), (0.88, 0.60, 0.48), (0.78, 0.62, 0.38),
                                          (0.30, 0.52, 0.52), (0.88, 0.86, 0.80), (0.52, 0.40, 0.30),
                                          (0.70, 0.30, 0.40)])),
    # ------------------------------------------------------------------ powder room
    "moon_sea": dict(
        at="powder W wall behind the WC", size=(1.0, 1.4), frame="metal", border=0.0, px=256, rough=0.35,
        style="photo", spec=dict(seed=326, scene="moon", horizon=0.56, sky=[(0.02, 0.03, 0.05), (0.08, 0.10, 0.14)],
                                 moon=(0.62, 0.22, 0.026), moonc=(0.95, 0.93, 0.86),
                                 sea=[(0.05, 0.06, 0.09), (0.015, 0.02, 0.03)], grain=0.03, vignette=0.12)),
    "gold_leaf": dict(
        at="powder S wall over the bench", size=(0.7, 0.7), frame="floater", px=256, rough=0.45, metal=0.5,
        style="gold", spec=dict(seed=327, panel=(0.12, 0.10, 0.88, 0.74), leaf=0.085)),
    # ------------------------------------------------------------------ primary suite
    "shoreline": dict(
        at="primary_bath S wall over the daybed", size=(1.6, 1.0), frame="metal", border=0.0, px=256, rough=0.35,
        style="photo", spec=dict(seed=328, scene="shore", shore=[(0, 0.22), (0.5, 0.44), (1, 0.78)],
                                 sand=(0.86, 0.78, 0.64), wet=(0.70, 0.62, 0.50),
                                 water=[(0.62, 0.85, 0.82), (0.40, 0.75, 0.75), (0.12, 0.48, 0.56), (0.05, 0.25, 0.38)],
                                 foam=[(0.004, 0.006, 0.9), (0.04, 0.008, 0.5), (0.10, 0.010, 0.25)])),
    "colorfield_dawn": dict(
        at="primary_bedroom W wall over the bed", size=(1.9, 1.1), frame="canvas", px=256, rough=0.85,
        style="colorfield", spec=dict(seed=329, ground=(0.74, 0.65, 0.59), blocks=[
            dict(box=(0.05, 0.09, 0.95, 0.47), glazes=[
                ((0.84, 0.66, 0.60), -0.012, 0.03, 0.4), ((0.90, 0.74, 0.68), 0.0, 0.02, 0.8),
                ((0.94, 0.82, 0.76), 0.04, 0.06, 0.4)]),
            dict(box=(0.05, 0.55, 0.95, 0.91), glazes=[
                ((0.72, 0.68, 0.60), -0.012, 0.03, 0.4), ((0.79, 0.75, 0.67), 0.0, 0.02, 0.8),
                ((0.85, 0.81, 0.73), 0.04, 0.06, 0.35)]),
        ])),
    "wash_horizon": dict(
        at="primary_bedroom E wall, south of the bath door", size=(0.8, 1.0), frame="box", margin=0.07, px=256,
        rough=0.9, style="wash", spec=dict(seed=330, mode="bands", xmargin=0.1, bands=[
            (0.20, 0.36, (0.76, 0.83, 0.90), 0.45), (0.39, 0.52, (0.62, 0.70, 0.80), 0.5),
            (0.55, 0.66, (0.56, 0.60, 0.63), 0.55), (0.69, 0.82, (0.44, 0.49, 0.52), 0.6)])),
    # ------------------------------------------------------------------ wine room
    "vineyard": dict(
        at="wine_room S wall over the leather nook", size=(2.4, 1.5), frame="metal", border=0.0, px=384, rough=0.35,
        style="photo", spec=dict(seed=331, scene="vineyard", splits=10, pitch=0.010,
                                 vines=[(0.30, 0.40, 0.18), (0.40, 0.46, 0.20), (0.55, 0.25, 0.18), (0.62, 0.48, 0.20)],
                                 soil=[(0.62, 0.50, 0.36), (0.55, 0.42, 0.30), (0.70, 0.60, 0.46)],
                                 track_c=(0.80, 0.74, 0.62))),
    "wine_rings": dict(
        at="wine_room S wall, pair (east)", size=(0.75, 0.95), frame="box", margin=0.07, px=384, rough=0.9,
        style="rings", spec=dict(seed=332, rings=_RINGS, drops=_DROPS)),
    "oxblood_zip": dict(
        at="wine_room S wall, pair (west)", size=(0.75, 0.95), frame="floater", px=192, rough=0.9,
        style="mono", spec=dict(seed=333, c=(0.30, 0.06, 0.07), angles=(0, 90), stretch=8, amp=0.04, relief=0.08,
                                zips=[dict(x=(0.48, 0.496), c=(0.74, 0.56, 0.26))])),
}
