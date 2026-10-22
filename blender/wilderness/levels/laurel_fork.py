"""Laurel Fork Cove (design/wilderness/blue_ridge/brief.md): the level config for the wilderness
terrain generator, plus the steps that turn it into a walkable runtime world.

Every authored feature is in the ESTATE frame (x east, y north, z = the estate lawn, house at
the origin), exactly as the brief's tables give them; terrain local = estate + (0, OFFSET_Y).
The runtime (viewer/wild/) works in terrain-local three.js coordinates:
    three (x, y, z) = (estate x, height, -(estate y + OFFSET_Y)).

  PY=/Applications/Blender.app/Contents/Resources/5.0/python/bin/python3.11
  $PY blender/wilderness/levels/laurel_fork.py               # terrain + checks + world (~1.5 min)
  $PY blender/wilderness/levels/laurel_fork.py --quick       # 3 m cells, for shape iteration
  $PY blender/wilderness/levels/laurel_fork.py --steps checks,world   # reuse the last terrain

Outputs: build/wilderness/laurel_fork/ (terrain.build's files, checks.json) and
build/wilderness/laurel_fork/world/ (what viewer/wild_proto.html?world=laurel_fork streams).
No Blender needed (numpy only), so no run slot.
"""
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import terrain  # noqa: E402

NAME = "laurel_fork"
OFFSET_Y = 810.0
GATE = (19.75, -62.0)
LAWN_Z = -0.08                       # plan.LAWN_Z: the lawn sits 8 cm under the estate's z = 0
HOUSE_EYE = (0.0, 0.0, 7.0)          # the house's upper floor, the target of the lookout views

# ------------------------------------------------------------------ large forms (brief, Appendix A)
RIDGES = [
    # the main (south) ridge, broken west of the Gap by the Laurel River's gorge (the river comes
    # in from the south there, where no route crosses the crest)
    dict(kind="ridge", name="laurel_ridge_west", sharp=1.0, points=[
        (-1500, -1160, 185, 1000), (-1100, -1175, 175, 900), (-830, -1188, 140, 520)]),
    dict(kind="ridge", name="laurel_ridge", sharp=1.0, points=[
        (-400, -1212, 105, 460), (-300, -1215, 125, 850),   # the Gap
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
    # the creek's line over the falls lip (pins the D8 channel to the lip: the droplet erosion is
    # chaotic, so any change elsewhere could otherwise slide the creek off the cliff's end)
    dict(kind="valley", name="falls_notch", points=[(-20, -650, 3, 50), (-60, -655, 5, 44), (-94, -659, 6, 36)]),
    # the Laurel River (Nantahala-sized: ~320 km² above the cove, 25-34 m wide): in from the south
    # through its gorge west of the Gap, north to meet Laurel Fork below the falls, then west
    # through the Narrows and out of the square toward the town, the valley opening as it goes
    dict(kind="valley", name="laurel_river", points=[
        # (depths: the square tilts down to the south, so the gorge is cut less there; the bed falls
        # from ~-135 at the south edge to ~-150 at the confluence; an S-bend at y -1420..-1160, the
        # long pool against its east cut bank with a cobble bar inside)
        (-660, -2400, 50, 700), (-630, -1750, 60, 560), (-640, -1420, 84, 520), (-572, -1290, 98, 490), (-598, -1160, 110, 470),
        (-575, -1010, 83, 420), (-548, -850, 58, 380), (-528, -745, 18, 360)]),
    dict(kind="valley", name="laurel_river_lower", points=[
        (-528, -745, 18, 360), (-700, -752, 20, 420), (-900, -762, 30, 520), (-1300, -780, 95, 760),
        (-1800, -800, 110, 1100), (-2500, -820, 120, 1300)]),
]
# where the Laurel River comes in (its catchment is outside the square), and the town it leads to
RIVER_INFLOW = dict(name="laurel_river", x=-628.0, y=-1555.0, r=60.0, area=3.2e8)
TOWN = dict(name="town", center=(-1900.0, -800.0), rect=(-2300.0, -1150.0, -1450.0, -480.0), z=-191.0,
            note="a small mountain town on the river flats, 1.1-1.9 km downstream of the square's west edge")

# ------------------------------------------------------------------ hooks
KNICKS = [dict(name="laurel_falls", height=16.0, width=170.0, lip=4.0, fade=60.0,
               points=[(-88, -657), (-130, -664), (-200, -680), (-330, -695), (-450, -705), (-620, -725), (-900, -745)],
               pool=dict(center=(-104, -662), radius=15.0, depth=5.0)),
          # the river's rapids: a ledge drop at the head of the Narrows and a shoal upstream of the
          # confluence (steps the water shader turns white; boulders are placed on them)
          dict(name="narrows_ledge", height=2.5, width=100.0, lip=3.0, fade=60.0,
               points=[(-610, -742), (-700, -752), (-900, -762), (-1150, -772)]),
          dict(name="shoals", height=1.6, width=90.0, lip=5.0, fade=60.0,
               points=[(-582, -1060), (-572, -990), (-548, -850), (-530, -760), (-600, -745), (-700, -752),
                       (-900, -762), (-1150, -772)])]
# the Laurel River's channel (terrain.apply_channel_profiles / apply_channel_beds): its 1.5-3% fall
# through the gorge gathered into a pool-drop sequence, as on the Nantahala and the Linville below
# their falls: long glassy pools, shallow riffles over cobbles, boulder rapids, two ledges; the bed
# deep in the pools and against the outside of bends, bedrock shelves on one side of two pools.
# The line follows the carved main stem from the inflow to the lip of the Narrows cascade (the
# cascade, the confluence and the reach below toward the town are untouched).
RIVER_CHANNEL = dict(
    name="laurel_river", half_width=60.0, fade=40.0,
    points=[(-642, -1565), (-639, -1463), (-633, -1419), (-642, -1373), (-631, -1322), (-610, -1275),
            (-586, -1181), (-590, -1133), (-598, -1083), (-581, -1037), (-579, -989), (-573, -941),
            (-569, -893), (-566, -814)],
    steps=[dict(at=(-612, -1462), length=34.0, kind="rapid", depth=0.7),            # Inflow rapid
           dict(at=(-617, -1368), length=9.0, kind="ledge", hole=3.6),              # the first ledge
           dict(at=(-604, -1236), length=40.0, kind="riffle", depth=0.45),          # tailout riffle of the long pool
           dict(at=(-592, -1128), length=42.0, kind="rapid", depth=0.7),
           dict(at=(-584, -1074), length=78.0, kind="rapid", depth=0.65),           # the Shoals
           dict(at=(-575, -948), length=10.0, kind="ledge", hole=3.8),              # Laurel Ledge
           dict(at=(-570, -893), length=26.0, kind="riffle", depth=0.5)],           # into the bridge pool
    bed=dict(pool_depth=3.3, riffle_depth=0.55, lip_depth=0.35, bend_k=110.0, min_width=15.0,
             shelves=[dict(start=(-618, -1345), end=(-606, -1262), side=+1, depth=0.22, **{"from": 0.2}),
                      dict(start=(-579, -995), end=(-575, -958), side=-1, depth=0.28, **{"from": 0.25})],
             cut_bank=dict(kap=0.004, deg=62.0, width=6.0)))
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
# The estate: the lawn rect outside the hedge (x +-90, y +-80) held at lawn height. Only its
# south strip (y -42..-80) lies in the terrain square; the rest is in the backdrop (a hole).
ESTATE_LAWN = dict(x=(-90.0, 90.0), y=(-80.0, 80.0))
PADS = [   # (later pads win where they overlap: the lawn last)
    dict(name="gate", center=(20, -95), radius=32, falloff=30, height=LAWN_Z),
    dict(name="gap", center=(-300, -1218), radius=24, falloff=16),
    dict(name="estate_lawn", center=(0.0, -61.0), half=(90.0, 19.0), falloff=10, height=LAWN_Z, reach=60.0),
]
PATHS = [
    dict(name="creek_trail", width=2.0, shoulder=3.0, max_grade=0.22, smooth=24.0, ford=True,
         switchbacks=dict(half_width=60.0),
         bank_deg=34.0, cut_deg=50.0, reach=16.0, points=[
             # (around Gate Rock's west end, where the ledge fades, instead of down its face)
             (20, -100), (-20, -150), (-82, -186), (-102, -214), (-70, -262), (-48, -330), (-12, -440), (32, -540), (58, -596),
             (10, -603), (-50, -612), (-88, -616), (-122, -622), (-146, -642), (-155, -672),
             (-162, -702), (-205, -775),
             # Hemlock Hollow: the brief's hand-drawn legs ran E-W across the draw (26-29 m of cut and
             # fill); only waypoints here, the generator lays the switchbacks along the contours
             (-262, -930), (-300, -1215)]),
    dict(name="ridge_trail", width=2.0, shoulder=3.0, max_grade=0.30, smooth=30.0, ford=True,
         switchbacks=dict(half_width=30.0),
         bank_deg=34.0, cut_deg=50.0, reach=14.0, points=[
             (20, -100), (110, -130), (200, -200), (280, -300), (340, -400), (388, -520),
             (415, -640), (428, -730), (436, -800), (450, -880), (458, -985),
             # (around the east end of the Knob's 30 m north face, then over the bald to its top)
             (524, -1024), (506, -1066), (466, -1072), (360, -1108),
             (240, -1140), (120, -1158), (62, -1160), (-60, -1185), (-180, -1205), (-300, -1215)]),
    dict(name="painted_spur", width=1.5, shoulder=2.0, max_grade=0.30, smooth=12.0, ford=True,
         bank_deg=34.0, cut_deg=50.0, reach=10.0, points=[(185, -1152), (170, -1100), (180, -1060), (163, -1027)]),
    # the estate road: the drive leaves the gate as gravel and turns east along the bench, then
    # down the foot of Raven Spur (wave 2 arrives on it); graded like a road
    dict(name="estate_road", width=4.0, shoulder=3.0, max_grade=0.10, smooth=40.0, ford=True,
         bank_deg=30.0, cut_deg=45.0, reach=24.0, switchbacks=dict(half_width=40.0), road=True,
         points=[(20, -66), (40, -86), (100, -100), (180, -112), (270, -140), (370, -185), (470, -240),
                 (560, -300), (640, -360), (740, -430)]),
    # Route D (to the town, the level beyond): from the footlog down Laurel Fork's south bank to the
    # swinging bridge over the Laurel River (built by laurel_fork_world: BRIDGE), then the river
    # road on the far bank, an old railroad grade, downstream out of the square to the town
    dict(name="river_trail", width=1.6, shoulder=2.0, max_grade=0.28, smooth=16.0, ford=True,
         bank_deg=34.0, cut_deg=50.0, reach=10.0, switchbacks=dict(half_width=30.0),
         points=[(-162, -704), (-222, -726), (-300, -746), (-380, -770), (-450, -800), (-500, -835), (-520, -848)]),
    dict(name="river_road", width=4.5, shoulder=3.0, max_grade=0.03, smooth=40.0, ford=False,
         bank_deg=34.0, cut_deg=50.0, reach=20.0, road=True, river_offset=4.0, grade_from="start",
         points=[(-668, -1574), (-664, -1500), (-650, -1400), (-656, -1300), (-634, -1200), (-636, -1100),
                 (-628, -1000), (-614, -925), (-612, -850), (-612, -795), (-650, -781), (-720, -783), (-766, -786)]),
    # Route C: the lane through the laurel hell (a 45 m thicket band, its tunnel along this line)
    # and up a bear path to Painted Rock. The raw lane is 42 deg at p50 (558 of 810 m over the 40
    # deg walking limit), so it gets a faint corridor: 3 m (two cells: a narrower bench on a 40 deg side
    # slope pinched the walker), steep (45%), switchbacks, a 6 m
    # reach (as a 40 m-reach corridor it cut a 20 m scar across the cove head). Not painted as trail.
    dict(name="route_c", width=3.0, shoulder=1.5, max_grade=0.45, smooth=10.0, ford=True,
         bank_deg=40.0, cut_deg=55.0, reach=6.0, switchbacks=dict(half_width=22.0, max_cut=2.0), trail=False,
         points=[(250, -255), (262, -340), (300, -460), (318, -575), (300, -700), (255, -820),
                 (200, -930), (175, -990), (163, -1027)]),
]
ROUTE_C = next(p for p in PATHS if p["name"] == "route_c")["points"]

# ------------------------------------------------------------------ landmarks (brief table)
LANDMARKS = dict(
    gate=(20, -62), gate_rock=(-40, -205), poplar_cove=(10, -380), falls_lip=(-92, -658),
    plunge_pool=(-104, -662), footlog=(-155, -672), hemlock_hollow=(-260, -900),
    raven_rock=(384, -880), knob=(466, -1068), knob_face_top=(444, -1042),
    painted_rock=(162, -1018), gap=(-300, -1218), confluence=(-545, -745), swinging_bridge=(-575, -848), narrows_cascade=(-575, -790),
    narrows=(-640, -748), river_inflow=(-628, -1570), river_exit=(-768, -752))
# the swinging bridge over the Laurel River: the crossing line (east -> west); laurel_fork_world fits
# its ends to the first ground 1.5 m over the water on each bank
# (upstream of the Narrows cascade, where the Laurel River drops ~18 m into the Narrows at the confluence)
BRIDGE = dict(a=(-500, -848), b=(-640, -848), deck_over_water=6.0, width=1.2)
# checked views to the house. The Knob's moved from the brief's west rock (384, -1060), which
# stood on a flat half-disc the cliff hook used to raise past the knob_face's end (fixed), to the
# top of that 30 m north face, the bald's north rim (laurel_fork_checks: 7.5 m over the terrain)
LOOKOUTS = dict(raven=(384, -880), knob=(444, -1042), painted=(162, -1018))
MEADOW = [(-190, -42), (230, -42), (240, -95), (205, -150), (120, -172), (20, -178), (-80, -170), (-160, -140), (-200, -95)]
BALD = dict(center=(466, -1068), radius=140.0)


def local(pt):
    return (pt[0], pt[1] + OFFSET_Y) + tuple(pt[2:])


def channel_local(c):
    b = dict(c["bed"], shelves=[dict(sh, start=local(sh["start"]), end=local(sh["end"])) for sh in c["bed"].get("shelves", [])])
    return dict(c, points=[local(q) for q in c["points"]], steps=[dict(st, at=local(st["at"])) for st in c["steps"]], bed=b)


def terrain_overrides(cell=1.5):
    shp = [dict(s, points=[local(q) for q in s["points"]]) for s in RIDGES + VALLEYS]
    ex, ey = ESTATE_LAWN["x"], ESTATE_LAWN["y"]
    return dict(
        name=NAME, seed=11, size=1536.0, cell=cell, base=-55.0, tilt=(0.03, 0.04),
        shapes=shp, shape_jitter=28.0,
        detail=dict(warp=60.0, warp_wavelength=600.0, low_amp=16.0, low_wavelength=280.0,
                    high_amp=28.0, high_wavelength=320.0, mountain=(0.1, 0.7)),
        # old, rounded mountains: strong hillslope diffusion, few droplets (0.8 rilled badlands)
        erosion=dict(fluvial=dict(k=0.018, iters=50, diffusion=0.8),
                     droplets=dict(per_cell=0.15), thermal=dict(talus_deg=36.0)),
        hydro=dict(river_area=8.0e4, width_k=8.0, width=(2.5, 34.0), depth_k=0.07, depth0=0.6, bank_drop=0.25, bank_w=5.0,
                   inflows=[dict(RIVER_INFLOW, x=RIVER_INFLOW["x"], y=RIVER_INFLOW["y"] + OFFSET_Y)],
                   floodplain=dict(width=34.0, rise=0.035, max_above=4.0, min_width=15.0),
                   bank_deg=18.0, lake_min_area=300.0, lake_min_depth=1.5, freeboard=0.2,
                   beach_w=3.0, beach_deg=12.0,
                   # the creek meanders between its fixed points: the falls and the plunge pool, the
                   # footlog ford and the Poplar branch ford (terrain local coordinates)
                   meander=dict(amp=30.0, wavelength=110.0, seed=5,
                                protect=[(-96.0, 150.0, 40.0, 35.0), (-104.0, 148.0, 26.0, 20.0),
                                         (-155.0, 138.5, 22.0, 30.0), (60.0, 220.0, 16.0, 20.0),
                                         (-575.0, -38.0, 30.0, 30.0)])),      # (the swinging bridge's crossing)
        knicks=[dict(k, points=[local(q) for q in k["points"]],
                     **({"pool": dict(k["pool"], center=local(k["pool"]["center"]))} if k.get("pool") else {}))
                for k in KNICKS],
        cliffs=[dict(c, points=[local(q) for q in c["points"]]) for c in CLIFFS],
        channels=[channel_local(RIVER_CHANNEL)],
        pads=[dict(p, center=local(p["center"])) for p in PADS],
        paths=[dict(p, points=[local(q) for q in p["points"]]) for p in PATHS],
        # forested slopes reach 45 deg in the southern Appalachians: rock only above ~50 or on cliffs
        masks=dict(rock_deg=(48.0, 58.0), cliff_rock=1.0),
        palette=dict(grass=(0.045, 0.075, 0.025), dry=(0.13, 0.085, 0.045), alpine=(0.05, 0.07, 0.035),
                     rock=(0.20, 0.20, 0.18), scree=(0.11, 0.12, 0.08), dirt=(0.10, 0.07, 0.04),
                     gravel=(0.22, 0.19, 0.14), mud=(0.12, 0.09, 0.05), forest=(0.035, 0.06, 0.025)),
        # the ring: real mountains beyond the cove (the views back to the house look over it)
        backdrop=dict(holes=[(ex[0], ey[0] + OFFSET_Y, ex[1], ey[1] + OFFSET_Y, LAWN_Z, 60.0),
                             # the river's corridor west of the square and the town's basin: kept open
                             # (the ring's framing hills would otherwise dam the valley)
                             (-1500.0, -790.0 + OFFSET_Y, -900.0, -728.0 + OFFSET_Y, -188.5, 120.0),
                             (TOWN["rect"][0], TOWN["rect"][1] + OFFSET_Y, TOWN["rect"][2], TOWN["rect"][3] + OFFSET_Y, TOWN["z"], 380.0)],
                      rock_deg=(44.0, 56.0),
                      frame_height=170.0, frame_wavelength=1100.0),
    )


def fit_river(name, cell):
    """The river road and the swinging bridge follow the river as it was actually carved (the
    meanders and the D8 network decide where): from a first pass's rivers mask, the road runs 18 m
    off the main stem's west bank and the combined river's south bank, and the bridge spans the
    main stem on BRIDGE's line. Paths are laid after the hydrology, so the river doesn't move."""
    import numpy as np
    D = os.path.join(terrain.OUT_ROOT, name)
    r = terrain.read_png_fast(os.path.join(D, "masks", "rivers.png"))[::-1] > 127
    n = r.shape[0]
    half = 768.0

    def cells_row(ye, x0, x1):
        j = int(round((ye + OFFSET_Y + half) / cell))
        xs = np.where(r[j])[0] * cell - half
        return xs[(xs > x0) & (xs < x1)]

    def cells_col(xe, y0, y1):
        i = int(round((xe + half) / cell))
        ys = np.where(r[:, i])[0] * cell - half - OFFSET_Y
        return ys[(ys > y0) & (ys < y1)]
    road = []
    for ye in np.arange(-1574.0, -805.0, 30.0):
        xs = cells_row(ye, -720, -480)
        if len(xs):
            road.append((float(xs.min() - 22.0), float(ye)))
    corner = None
    west = []
    for xe in np.arange(-640.0, -767.0, -25.0):
        ys = cells_col(xe, -830, -690)
        if len(ys):
            west.append((float(xe), float(ys.min() - 22.0)))
    if road and west:
        corner = (road[-1][0] - 10.0, west[0][1] - 10.0)
        road = road + [corner] + west + [(-766.0, west[-1][1])]
    # the bridge: the main stem's banks on BRIDGE's line
    yb = (BRIDGE["a"][1] + BRIDGE["b"][1]) / 2
    xs = cells_row(yb, -700, -480)
    bridge = dict(BRIDGE)
    if len(xs):
        bridge["a"] = (float(xs.max() + 7.0), yb)
        bridge["b"] = (float(xs.min() - 7.0), yb)
    fit = dict(road=[[round(x, 1), round(y, 1)] for x, y in road], bridge=bridge)
    with open(os.path.join(D, "river_fit.json"), "w") as fh:
        json.dump(fit, fh, indent=1)
    return fit


def build_terrain(cell=1.5, name=NAME):
    ov = terrain_overrides(cell)
    ov["name"] = name
    # pass 1 without the river road and trail end, to see where the river went
    ov1 = dict(ov, paths=[p for p in ov["paths"] if p["name"] != "river_road"])
    terrain.build(**ov1)
    fit = fit_river(name, cell)
    paths = []
    for p in ov["paths"]:
        if p["name"] == "river_road" and len(fit["road"]) > 3:
            p = dict(p, points=[local(q) for q in fit["road"]])
        if p["name"] == "river_trail":
            # (to the foot of the bridge's steps, on its axis)
            (ax, ay), (bx, by) = fit["bridge"]["a"], fit["bridge"]["b"]
            L = math.hypot(bx - ax, by - ay)
            foot = (ax - (bx - ax) / L * 10, ay - (by - ay) / L * 10)
            p = dict(p, points=p["points"][:-1] + [local(foot)])
        paths.append(p)
    return terrain.build(**dict(ov, paths=paths))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="3 m cells")
    ap.add_argument("--steps", default="terrain,checks,world")
    ap.add_argument("--name", default=None)
    a = ap.parse_args()
    cell = 3.0 if a.quick else 1.5
    name = a.name or (NAME + ("_quick" if a.quick else ""))
    steps = a.steps.split(",")
    t0 = time.time()
    if "terrain" in steps:
        st = build_terrain(cell, name)
        for pth in st["paths"]:
            print(f"  path {pth['name']:12s} {pth['length_m']:7.1f} m  cut/fill max {pth['max_cut_fill_m']} m at "
                  f"{pth['max_cut_fill_at']} p95 {pth['cut_fill_p95_m']} m")
            for sb in pth.get("switchbacks", []):
                print("     switchbacks", sb)
    if "checks" in steps:
        import laurel_fork_checks
        laurel_fork_checks.run(name)
    if "world" in steps:
        import laurel_fork_world
        laurel_fork_world.run(name)
    print(f"done in {time.time() - t0:.0f} s")
