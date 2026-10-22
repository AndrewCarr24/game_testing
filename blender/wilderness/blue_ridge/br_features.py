"""Blue Ridge concept: every authored feature in the ESTATE frame (x east, y north, z = lawn).
Shared by the terrain test run and the map generator so they cannot drift.
Terrain local frame = estate + (0, OFFSET_Y)."""
OFFSET_Y = 810.0
GATE = (19.75, -62.0)

RIDGES = [
    dict(kind="ridge", name="laurel_ridge", sharp=1.0, points=[   # the main (south) ridge
        (-900, -1180, 175, 1000), (-560, -1200, 160, 950), (-300, -1215, 125, 850),   # the Gap
        (-80, -1190, 195, 1000), (60, -1175, 215, 1050), (290, -1120, 245, 1100),
        (470, -1070, 270, 1150), (700, -1110, 245, 1100), (900, -1150, 220, 1000)]),
    dict(kind="ridge", name="raven_spur", sharp=1.0, points=[     # Knob -> Raven Rock -> gate bench
        (470, -1070, 270, 700), (455, -860, 210, 620), (430, -650, 165, 560),
        (360, -420, 100, 480), (250, -230, 42, 380), (150, -120, 8, 240)]),
]
VALLEYS = [
    dict(kind="valley", name="cove", points=[                       # the broad cove bowl
        (430, -560, 20, 420), (250, -600, 45, 700), (0, -650, 55, 900),
        (-400, -700, 58, 900), (-900, -740, 60, 900)]),
    dict(kind="valley", name="gorge", points=[                      # the inner creek gorge
        (320, -590, 8, 100), (120, -620, 24, 180), (-100, -660, 32, 220),
        (-450, -705, 36, 240), (-900, -745, 38, 240)]),
    dict(kind="valley", name="poplar_branch", points=[              # tributary: the old-growth cove
        (-30, -170, 6, 110), (0, -320, 20, 200), (55, -480, 26, 230), (95, -600, 8, 160)]),
    dict(kind="valley", name="hemlock_hollow", points=[             # north-facing draw up to the Gap
        (-320, -1110, 8, 160), (-265, -930, 24, 220), (-200, -760, 12, 200)]),
]
POOL = dict(kind="basin", name="plunge_pool", center=(-110, -661), radius=(12, 9), angle=10, depth=4.0)

# proposed generator hook (not in terrain.py yet): after erosion, lower the channel below a lip
KNICKS = [dict(name="laurel_falls", height=16.0, width=170.0, lip=4.0, fade=60.0,
               points=[(-88, -657), (-130, -664), (-200, -680), (-330, -695), (-450, -705), (-620, -725), (-900, -745)],
               pool=dict(center=(-104, -662), radius=15.0, depth=5.0))]

CLIFFS = [
    dict(name="falls", points=[(-80, -720), (-92, -660), (-100, -600)], height=14.0, side=+1,
         edge=1.5, back=25.0, end_fade=22.0, jitter=1.2, talus_deg=45.0),
    dict(name="raven_rock", points=[(418, -735), (420, -800), (430, -860)], height=22.0, side=-1,
         edge=3.0, back=25.0, end_fade=30.0, jitter=3.0, talus_deg=40.0),
    dict(name="painted_rock", points=[(80, -1022), (132, -1020), (185, -1010)], height=18.0, side=+1,
         edge=2.5, back=20.0, end_fade=25.0, jitter=2.5, talus_deg=40.0),
    dict(name="knob_face", points=[(415, -1050), (465, -1036), (515, -1048)], height=30.0, side=+1,
         edge=2.0, back=15.0, end_fade=20.0, jitter=2.0, talus_deg=40.0),
    dict(name="gate_rock", points=[(10, -212), (-40, -205), (-90, -200)], height=18.0, side=+1,
         edge=1.5, back=15.0, end_fade=18.0, jitter=1.5, talus_deg=42.0),
]
# lookouts are NOT pads: apply_pads has no reach, so a high pad props up every slope > 33 deg around it
PADS = [
    dict(name="gate", center=(20, -95), radius=32, falloff=30, height=0.0),
    dict(name="gap", center=(-300, -1218), radius=24, falloff=16),
]
PATHS = [
    dict(name="creek_trail", width=2.0, shoulder=3.0, max_grade=0.22, smooth=24.0, ford=True,
         bank_deg=34.0, cut_deg=50.0, reach=16.0, points=[
             (20, -100), (-20, -150), (-62, -225), (-48, -330), (-12, -440), (32, -540), (58, -596),
             (10, -603), (-50, -612), (-88, -616), (-122, -622), (-146, -642), (-155, -672),
             (-162, -702), (-205, -775), (-300, -805), (-205, -870), (-320, -925), (-220, -990), (-330, -1050),
             (-250, -1110), (-320, -1165), (-300, -1215)]),
    dict(name="ridge_trail", width=2.0, shoulder=3.0, max_grade=0.24, smooth=30.0, ford=True,
         bank_deg=34.0, cut_deg=50.0, reach=14.0, points=[
             (20, -100), (110, -130), (200, -200), (280, -300), (340, -400), (388, -520),
             (415, -640), (428, -730), (436, -800), (450, -880), (458, -990), (466, -1065), (360, -1108),
             (240, -1140), (120, -1158), (62, -1160), (-60, -1185), (-180, -1205), (-300, -1215)]),
    dict(name="painted_spur", width=1.5, shoulder=2.0, max_grade=0.30, smooth=12.0, ford=True,
         bank_deg=34.0, cut_deg=50.0, reach=10.0, points=[(185, -1152), (170, -1100), (180, -1060), (163, -1027)]),
    dict(name="laurel_hell", width=1.2, shoulder=1.5, max_grade=0.36, smooth=16.0, ford=True,
         bank_deg=38.0, cut_deg=55.0, reach=40.0, points=[
             (250, -255), (262, -340), (300, -460), (318, -575), (300, -700), (255, -820),
             (200, -930), (175, -990), (163, -1027)]),
]


def local(pt):
    return (pt[0], pt[1] + OFFSET_Y) + tuple(pt[2:])


def terrain_overrides():
    shp = []
    for s in RIDGES + VALLEYS:
        shp.append(dict(s, points=[local(p) for p in s["points"]]))
    shp.append(dict(POOL, center=local(POOL["center"])))
    return dict(
        name="blue_ridge", seed=11, size=1536.0, cell=1.5, base=-55.0, tilt=(0.03, 0.04),
        shapes=shp, shape_jitter=28.0,
        detail=dict(warp=60.0, warp_wavelength=600.0, low_amp=16.0, low_wavelength=280.0,
                    high_amp=28.0, high_wavelength=320.0, mountain=(0.1, 0.7)),
        erosion=dict(fluvial=dict(k=0.018, iters=50, diffusion=0.8),
                     droplets=dict(per_cell=0.15), thermal=dict(talus_deg=36.0)),
        hydro=dict(river_area=8.0e4, width_k=8.0, width=(2.5, 12.0), bank_drop=0.25, bank_w=5.0,
                   bank_deg=18.0, lake_min_area=300.0, lake_min_depth=1.5, freeboard=0.2,
                   beach_w=3.0, beach_deg=12.0),
        cliffs=[dict(c, points=[local(p) for p in c["points"]]) for c in CLIFFS],
        pads=[dict(p, center=local(p["center"])) for p in PADS],
        paths=[dict(p, points=[local(q) for q in p["points"]]) for p in PATHS if p["name"] != "laurel_hell"],
        palette=dict(grass=(0.045, 0.075, 0.025), dry=(0.13, 0.085, 0.045), alpine=(0.05, 0.07, 0.035),
                     rock=(0.20, 0.20, 0.18), scree=(0.11, 0.12, 0.08), dirt=(0.10, 0.07, 0.04),
                     gravel=(0.22, 0.19, 0.14), mud=(0.12, 0.09, 0.05), forest=(0.035, 0.06, 0.025)),
    )
