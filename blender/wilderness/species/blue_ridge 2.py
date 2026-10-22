"""Blue Ridge plant kit (design/wilderness/blue_ridge/brief.md, Laurel Fork Cove, mid-June): species
parameters for blender/wilderness/trees.py (trees, shrubs, thickets, clumps, mats) and
blender/wilderness/deadwood.py (logs, stumps, boulders). Ids and budgets: design/wilderness/blue_ridge/plants.md.

  Blender -b --factory-startup --python blender/wilderness/trees.py -- --kit blue_ridge [--species tulip_poplar]

Each entry's `reference` is the real-world look it is art-directed against (field-guide descriptions;
USFS Silvics of North America, Sargent's Manual, NPS Great Smoky Mountains); `palette` the brief's
Appendix B leaf colour (sRGB). Variants (`variants`: n) are seeded re-growths of the same species,
ids <id>, <id>_2, <id>_3; they share textures and the base's impostor.
"""


def bark(src, tag, tile, tint=(1, 1, 1), sat=1.0, gain=1.0, rough=0.92):
    return dict(src=src, diff="Diffuse", nor="nor_gl", tile=tile, tag=tag, tint=tint, sat=sat, gain=gain, rough=rough)


def lv(seg, trop, wob, kids, start, angle, ratio, grav, L=None):
    d = dict(seg=seg, tropism=trop, wobble=wob, kids=kids, start=start, angle=angle, ratio=ratio, gravity=grav)
    if L:
        d["len"] = L
    return d


TWIG = lv(0.25, 0.05, 0.2, 0, 0, 0, 0, 0)

# LOD sets (tube sides, polyline step, branches kept, cards kept). Canopy trees: LOD0 <= 25 m (the
# brief: measured to the crown, so a 45 m poplar's crown is rarely LOD0), LOD1 to 60, LOD2 to 120,
# then the impostor (or the canopy shell).
BROAD_LODS = [dict(trunk=12, branch=6, thin=3, seg=2, min_len=0.8, keep=1.0, csegs=1, max_level=2, thick_r=0.09,
                   bark_cards=True),
              dict(trunk=8, branch=4, thin=3, seg=3, min_len=2.0, keep=0.26, csegs=1, max_level=1, thick_r=0.09),
              dict(trunk=6, branch=3, thin=0, seg=6, min_len=4.0, keep=0.07, csegs=1, max_level=1, thick_r=0.09)]
CONIFER_LODS = [dict(trunk=10, branch=4, thin=3, seg=3, min_len=0.6, keep=1.0, csegs=1, max_level=1, thick_r=0.06,
                     branch_cards=False),
                dict(trunk=7, branch=3, thin=0, seg=3, min_len=1.6, keep=0.24, csegs=1, max_level=1, thick_r=0.06,
                     branch_cards=True),
                dict(trunk=5, branch=0, thin=0, seg=6, min_len=99, keep=0.0, csegs=1, max_level=0, branch_cards=True)]
SHRUB_LODS = [dict(trunk=6, branch=5, thin=3, seg=1, min_len=0.0, keep=1.0, csegs=1, max_level=1, thick_r=0.025,
                   shell=700),
              dict(trunk=4, branch=3, thin=0, seg=2, min_len=0.7, keep=0.35, csegs=1, max_level=0, shell=260,
                   max_grow=1.6),
              dict(trunk=3, branch=0, thin=0, seg=4, min_len=99, keep=0.08, csegs=1, max_level=0, shell=110,
                   max_grow=1.8)]


KIT = {
    # =========================================================================================
    # canopy
    "tulip_poplar": dict(
        kind="broadleaf", group="canopy", title="Tulip poplar", latin="Liriodendron tulipifera", variants=3,
        community="cove / mesic (30%)", palette="#8DB04A",
        reference="The cove giant: a ruler-straight grey column, clear of limbs for 20-25 m, 1-2 m thick over a "
                  "flared base; a narrow, high crown of upswept limbs. Bark pale ash-grey in tight interlacing "
                  "furrows (a braided net), often green with algae on the wet side. Leaves 12-15 cm, four-lobed with "
                  "a square notched tip (a tulip / cat-face outline) on long petioles, held flat; mid-June they are "
                  "the yellowest green in the cove.",
        height=44.0, crown_base=24.0, envelope=((0, 0, 35.0), (7.2, 6.8, 10.0)), r_tip=0.011, pipe=2.0,
        trunk_r=0.72, trunk_taper=0.9, flare=0.55, flare_z=0.7, rad_k=[1.0, 3.0, 1.6], lean=0.015, stubs=7,
        levels=[lv(1.2, 0.0, 0.012, 16, 0.53, 40, 0.42, 0.0, L=44.0), lv(0.8, 0.05, 0.1, 6, 0.2, 46, 0.55, 0.04),
                lv(0.45, 0.06, 0.18, 6, 0.2, 52, 0.5, 0.05), TWIG],
        twig_len=(0.4, 0.8), fronds_per_twig=4, bend=0.1, card_scale=2.1,
        leaf=dict(atlas="br_broadleaf", cards=["poplar_a", "poplar_b"], weights=[1.0, 1.3]), leaf_rough=0.6,
        bark=bark("tree_bark_03", "poplar", (1.2, 1.6), (0.98, 1.0, 0.97), 0.6),
        card_roll=65, lods=BROAD_LODS, lod_dist=[0, 25, 60, 120]),
    "northern_red_oak": dict(
        kind="broadleaf", group="canopy", title="Northern red oak", latin="Quercus rubra", variants=2,
        community="oak-hickory, mid / upper slopes (18%)", palette="#3F5E2A",
        reference="A broad, rounded crown on a short, stout bole that forks into a few heavy ascending limbs at "
                  "8-12 m. Bark dark grey-brown with long, flat-topped light ridges, the 'ski tracks' running "
                  "down the trunk. Leaves 12-20 cm, 7-11 pointed lobes with bristle tips and sinuses cut halfway to "
                  "the midrib, crowded at the twig ends; dark, glossy, the darkest broadleaf green on the slope.",
        height=30.0, crown_base=10.0, envelope=((0, 0, 20.5), (9.0, 8.5, 9.0)), r_tip=0.011, pipe=2.0,
        trunk_r=0.55, trunk_taper=0.8, flare=0.5, flare_z=0.6, rad_k=[1.0, 3.2, 1.7], lean=0.05, stubs=4,
        levels=[lv(1.0, 0.0, 0.05, 9, 0.4, 38, 0.8, 0.0, L=21.0), lv(0.7, 0.04, 0.14, 7, 0.2, 48, 0.55, 0.05),
                lv(0.4, 0.05, 0.2, 5, 0.2, 52, 0.5, 0.06), TWIG],
        twig_len=(0.5, 1.0), fronds_per_twig=5, bend=0.12, card_scale=1.95,
        leaf=dict(atlas="br_broadleaf", cards=["red_oak_a", "red_oak_b"]), leaf_rough=0.5,
        bark=bark("jolcham_oak_bark_01", "redoak", (1.0, 1.4), (0.92, 0.9, 0.88), 0.5, 1.08),
        card_roll=65, lods=BROAD_LODS, lod_dist=[0, 25, 60, 120]),
    "white_oak": dict(
        kind="broadleaf", group="canopy", title="White oak", latin="Quercus alba", variants=2,
        community="oak-hickory, drier slopes", palette="#4A6A36",
        reference="Wide-spreading, open-grown look even in the forest: massive limbs leaving the trunk at wide angles, "
                  "a broad crown wider than tall. Bark pale ash-grey, scaly, in loose rectangular flakes and shallow "
                  "fissures. Leaves 12-20 cm with 7-9 rounded finger-like lobes, sinuses of varying depth, no bristles; "
                  "blue-green above, whitish beneath.",
        height=28.0, crown_base=8.0, envelope=((0, 0, 17.5), (10.5, 9.8, 8.0)), r_tip=0.011, pipe=2.0,
        trunk_r=0.55, trunk_taper=0.8, flare=0.45, flare_z=0.6, rad_k=[1.0, 3.2, 1.7], lean=0.05, stubs=4,
        levels=[lv(1.0, 0.0, 0.06, 9, 0.38, 55, 0.85, 0.0, L=17.0), lv(0.7, 0.02, 0.15, 7, 0.2, 50, 0.55, 0.07),
                lv(0.4, 0.04, 0.2, 5, 0.2, 52, 0.5, 0.06), TWIG],
        twig_len=(0.5, 1.0), fronds_per_twig=5, bend=0.12, card_scale=1.95,
        leaf=dict(atlas="br_broadleaf", cards=["white_oak_a", "white_oak_b"]), leaf_rough=0.6,
        bark=bark("bark_willow_02", "whiteoak", (0.9, 1.2), (1.0, 0.99, 0.96), 0.3, 0.92),
        card_roll=65, lods=BROAD_LODS, lod_dist=[0, 25, 60, 120]),
    "chestnut_oak": dict(
        kind="broadleaf", group="canopy", title="Chestnut oak", latin="Quercus montana", variants=2,
        community="dry crests, outcrop rims (10%)", palette="#6B8A36",
        reference="The ridge oak: a shorter, often crooked or leaning trunk, an open irregular crown with gaps, "
                  "over mountain laurel. Bark the deepest on the mountain: thick, dark grey-brown, cut into massive "
                  "blocky V-shaped ridges. Leaves 12-20 cm, obovate with a wavy margin of rounded teeth (like "
                  "chestnut), yellow-green and leathery.",
        height=22.0, crown_base=7.0, envelope=((0, 0, 15.0), (7.0, 6.2, 6.5)), r_tip=0.011, pipe=2.0,
        trunk_r=0.42, trunk_taper=0.8, flare=0.5, flare_z=0.5, rad_k=[1.0, 3.0, 1.6], lean=0.14, stubs=5,
        levels=[lv(0.9, 0.0, 0.1, 7, 0.38, 44, 0.75, 0.0, L=16.0), lv(0.6, 0.03, 0.22, 6, 0.2, 50, 0.55, 0.06),
                lv(0.4, 0.05, 0.25, 4, 0.2, 52, 0.5, 0.06), TWIG],
        twig_len=(0.5, 1.0), fronds_per_twig=5, bend=0.12, card_scale=1.95,
        leaf=dict(atlas="br_broadleaf", cards=["chestnut_oak_a", "chestnut_oak_b"]), leaf_rough=0.55,
        bark=bark("bark_willow", "chestnutoak", (0.9, 1.2), (0.92, 0.9, 0.88), 0.5, 1.12),
        card_roll=65, lods=BROAD_LODS, lod_dist=[0, 25, 60, 120]),
    "shagbark_hickory": dict(
        kind="broadleaf", group="canopy", title="Shagbark hickory", latin="Carya ovata", variants=2,
        community="oak-hickory, mid slopes (7%)", palette="#4F7230",
        reference="A tall straight trunk and a narrow oval crown. The bark is unmistakable: grey plates 30 cm to 1 m "
                  "long that come loose at both ends and curl away from the trunk (shaggy). Leaves 20-35 cm, "
                  "compound, five leaflets, the upper three much larger, finely toothed; dark yellow-green.",
        height=28.0, crown_base=13.0, envelope=((0, 0, 20.0), (5.6, 5.4, 8.5)), r_tip=0.011, pipe=2.0,
        trunk_r=0.36, trunk_taper=0.85, flare=0.35, flare_z=0.5, rad_k=[1.0, 2.6, 1.5], lean=0.03, stubs=5,
        levels=[lv(1.0, 0.0, 0.02, 11, 0.45, 42, 0.45, 0.0, L=28.0), lv(0.7, 0.05, 0.12, 6, 0.2, 46, 0.55, 0.04),
                lv(0.4, 0.06, 0.18, 4, 0.2, 50, 0.5, 0.05), TWIG],
        twig_len=(0.5, 1.0), fronds_per_twig=5, bend=0.12, card_scale=1.95,
        leaf=dict(atlas="br_broadleaf", cards=["hickory_a", "hickory_b", "hickory_strips"], weights=[1, 1, 0]),
        bark_cards=dict(card="hickory_strips", n=56, z=(0.6, 11.0), len=(0.55, 0.95)), leaf_rough=0.6,
        bark=bark("metasequoia_bark", "shagbark", (0.6, 1.2), (0.95, 0.95, 0.95), 0.15, 0.95),
        card_roll=65, lods=BROAD_LODS, lod_dist=[0, 25, 60, 120]),
    "sugar_maple": dict(
        kind="broadleaf", group="canopy", title="Sugar maple", latin="Acer saccharum", variants=2,
        community="rich coves (8%)", palette="#4E7A2C",
        reference="A dense, rounded-oval crown carried low (crown base 8 m), deep shade beneath. Bark grey, in "
                  "long irregular vertical plates that lift at one edge with age. Leaves opposite, 8-14 cm, palmate "
                  "with 5 lobes, U-shaped sinuses and a few large blunt teeth, on long petioles; medium green.",
        height=27.0, crown_base=8.0, envelope=((0, 0, 17.5), (7.4, 7.0, 9.2)), r_tip=0.011, pipe=2.0,
        trunk_r=0.42, trunk_taper=0.85, flare=0.4, flare_z=0.5, rad_k=[1.0, 2.8, 1.6], lean=0.03, stubs=4,
        levels=[lv(1.0, 0.0, 0.03, 13, 0.36, 40, 0.55, 0.0, L=26.0), lv(0.7, 0.05, 0.12, 7, 0.2, 45, 0.55, 0.04),
                lv(0.4, 0.06, 0.18, 5, 0.2, 50, 0.5, 0.05), TWIG],
        twig_len=(0.5, 1.0), fronds_per_twig=5, bend=0.12, card_scale=1.95,
        leaf=dict(atlas="br_broadleaf", cards=["maple_a", "maple_b"]), leaf_rough=0.6,
        bark=bark("bark_willow_02", "maple", (0.8, 1.2), (0.92, 0.92, 0.9), 0.3, 0.92),
        card_roll=65, lods=BROAD_LODS, lod_dist=[0, 25, 60, 120]),
    "yellow_buckeye": dict(
        kind="broadleaf", group="canopy", title="Yellow buckeye", latin="Aesculus flava", variants=2,
        community="high coves, wet (6%)", palette="#6E9438",
        reference="A big, clean cove tree with a rounded crown from 12 m. Bark smooth grey-brown breaking into "
                  "thin scaly plates that flake off in patches, like sycamore. Leaves opposite, palmately compound: "
                  "five finely toothed leaflets 10-15 cm radiating from a long stalk; bright yellow-green.",
        height=30.0, crown_base=12.0, envelope=((0, 0, 21.0), (8.2, 7.8, 8.8)), r_tip=0.011, pipe=2.0,
        trunk_r=0.5, trunk_taper=0.85, flare=0.4, flare_z=0.6, rad_k=[1.0, 2.8, 1.6], lean=0.03, stubs=4,
        levels=[lv(1.0, 0.0, 0.03, 11, 0.42, 44, 0.6, 0.0, L=28.0), lv(0.7, 0.04, 0.12, 6, 0.2, 48, 0.55, 0.05),
                lv(0.4, 0.06, 0.18, 4, 0.2, 52, 0.5, 0.05), TWIG],
        twig_len=(0.5, 1.0), fronds_per_twig=5, bend=0.12, card_scale=1.95,
        leaf=dict(atlas="br_broadleaf", cards=["buckeye_a", "buckeye_b"]), leaf_rough=0.6,
        bark=bark("bark_platanus", "buckeye", (1.0, 1.3), (0.95, 0.95, 0.95), 0.35, 1.25),
        card_roll=65, lods=BROAD_LODS, lod_dist=[0, 25, 60, 120]),
    "eastern_hemlock": dict(
        kind="conifer", group="canopy", title="Eastern hemlock", latin="Tsuga canadensis", variants=3,
        community="creekside (<= 40 m of water), north faces (12%)", palette="#2F4A3A",
        reference="The dark one: a broad, dense cone of near-black green from 5 m up, long limbs sweeping down "
                  "and out, the leader nodding over. Foliage in flat, lacy, two-ranked sprays of short 1.5 cm "
                  "needles; in June every tip carries a flush of soft lime new growth. Bark cinnamon-brown to grey, "
                  "in scaly ridges. Under it the light drops to almost nothing.",
        height=32.0, trunk_r=0.5, flare=0.5, crown_base=7.0, whorl_gap=0.72, whorl_n=(2, 3, 3, 4),
        branch_len=6.0, cone=0.85, elev_bottom=-8.0, elev_top=26.0, droop=28.0, upturn=10.0,
        twig_gap=0.46, twig_len=1.4, card_len=(0.95, 1.45), leader=2.0, leader_droop=1.6, branch_r=0.12,
        stubs=6, stub_k=1.8, trunk_wob=0.06,
        secondary=dict(gap=0.85, len_k=0.42, angle=55, droop=14, min_len=2.0, gap_k=1.3), spray_roll=50, spray2=0.6,
        leaf=dict(atlas="br_evergreen", cards=["hemlock_a", "hemlock_b"]), base_rects=(0, 1), leaf_rough=0.65,
        bark=bark("pine_bark", "hemlock", (0.7, 1.0), (0.9, 0.86, 0.84), 0.35, 1.2),
        lods=CONIFER_LODS, lod_dist=[0, 22, 50, 110]),
    "white_pine": dict(
        kind="conifer", group="canopy", title="Eastern white pine", latin="Pinus strobus", variants=2,
        community="south slopes, spurs; emergent over the oaks (5%)", palette="#4D6E4A",
        reference="The emergent: a tall, clean trunk, then widely spaced tiers of long horizontal limbs that "
                  "turn up at the ends; foliage in soft blue-green plumes of 10 cm needles in bundles of five, "
                  "clustered toward the limb tips; a ragged, flat or wind-flagged top over the canopy. Bark dark "
                  "grey, thick, in broad scaly ridges.",
        height=40.0, trunk_r=0.55, flare=0.4, crown_base=15.0, whorl_gap=1.7, whorl_n=(4, 5, 5), skip=0.3,
        profile="pine", branch_len=7.5, cone=0.6, elev_bottom=-6.0, elev_top=26.0, droop=8.0, upturn=30.0,
        twig_gap=0.28, twig_len=1.2, card_len=(0.8, 1.2), twig_from=0.42, twig_up=0.45, leader=2.5,
        branch_r=0.16, stubs=14, stub_k=1.6,
        secondary=dict(gap=0.75, len_k=0.5, angle=50, droop=4, min_len=2.0, gap_k=1.0), spray_roll=55, spray2=0.55,
        leaf=dict(atlas="br_evergreen", cards=["pine_a", "pine_b"], weights=[1, 1.4]), base_rects=(1, 0),
        leaf_rough=0.6, bark=bark("bark_brown_02", "wpine", (0.9, 1.3), (0.85, 0.82, 0.8), 0.5),
        lods=CONIFER_LODS, lod_dist=[0, 24, 55, 120]),
    "hemlock_snag": dict(
        kind="conifer", group="deadwood", title="Hemlock snag (adelgid-killed)", latin="Tsuga canadensis, dead",
        variants=1, community="creekside, hollows (a few)", palette=None, impostor=True,
        reference="The honest detail: since the 2000s the woolly adelgid has killed most untreated hemlocks. A "
                  "grey standing skeleton, bark sloughing, short brittle limb stubs, the top snapped off.",
        height=24.0, trunk_r=0.45, flare=0.5, crown_base=3.0, whorl_gap=0.8, whorl_n=(2, 3), branch_len=5.5,
        cone=0.85, elev_bottom=-20.0, elev_top=10.0, droop=20.0, upturn=0.0, twig_gap=1.0, twig_len=1.0,
        card_len=(0.5, 0.9), leader=1.0, branch_r=0.1, stubs=10, stub_k=1.5, dead=True, skip=0.35,
        bark=bark("rough_wood", "snag", (0.8, 1.2), (0.92, 0.92, 0.94), 0.3, 1.05),
        lods=[dict(trunk=10, branch=4, thin=3, seg=3, min_len=0.3, keep=0, csegs=1, max_level=1, thick_r=0.05),
              dict(trunk=7, branch=3, thin=0, seg=3, min_len=1.0, keep=0, csegs=1, max_level=1, thick_r=0.05),
              dict(trunk=5, branch=0, thin=0, seg=6, min_len=99, keep=0, csegs=1, max_level=0)],
        lod_dist=[0, 25, 60, 140], impostor_px=(512, 256)),

    # =========================================================================================
    # understory trees (Appendix B: 4% under the canopy)
    "flowering_dogwood": dict(
        kind="broadleaf", group="understory", title="Flowering dogwood", latin="Cornus florida", variants=1,
        community="under the cove and oak canopy (understory, 3-10 m)", palette="#557B35",
        reference="The understory's flat-topped little tree: a short, often crooked trunk, branches in level "
                  "tiers that spread wider than the tree is tall, twigs turned up at the ends. Bark dark grey-brown "
                  "broken into small square blocks (alligator hide). Leaves opposite, 8-12 cm, ovate with veins "
                  "curving toward the tip; by mid-June the white bracts are long gone and small green fruit clusters "
                  "sit at the twig ends.",
        height=8.0, crown_base=1.8, envelope=((0, 0, 5.0), (4.3, 4.0, 2.4)), r_tip=0.009, pipe=2.0,
        trunk_r=0.13, trunk_taper=0.8, flare=0.3, flare_z=0.3, rad_k=[1.0, 2.6, 1.5], lean=0.08, stubs=2,
        levels=[lv(0.5, 0.0, 0.08, 8, 0.28, 64, 0.85, 0.0, L=7.0), lv(0.4, 0.06, 0.15, 8, 0.15, 55, 0.55, 0.03),
                lv(0.25, 0.08, 0.2, 6, 0.15, 52, 0.5, 0.03), TWIG],
        twig_len=(0.3, 0.6), fronds_per_twig=6, bend=0.1, card_scale=1.75,
        leaf=dict(atlas="br_understory", cards=["dogwood_a", "dogwood_b"]), leaf_rough=0.6,
        bark=bark("pine_bark", "dogwood", (0.35, 0.5), (0.72, 0.7, 0.7), 0.25, 0.95),
        card_roll=60, lods=BROAD_LODS, lod_dist=[0, 18, 45, 100], impostor_px=(512, 256)),
    "sourwood": dict(
        kind="broadleaf", group="understory", title="Sourwood", latin="Oxydendrum arboreum", variants=1,
        community="oak slopes and crests (understory, 8-15 m)", palette="#4C702F",
        reference="A slender, often leaning understory tree with a narrow crown of drooping branches. Bark grey, "
                  "deeply furrowed into narrow scaly ridges. Leaves alternate, 10-18 cm, elliptic and finely toothed, "
                  "glossy; in mid-June the long one-sided flower sprays at the branch tips are still in creamy bud "
                  "(they open white in July, the sourwood honey flow).",
        height=12.0, crown_base=4.0, envelope=((0, 0, 8.4), (3.2, 3.0, 4.2)), r_tip=0.009, pipe=2.0,
        trunk_r=0.17, trunk_taper=0.85, flare=0.3, flare_z=0.4, rad_k=[1.0, 2.6, 1.5], lean=0.14, stubs=3,
        levels=[lv(0.6, 0.0, 0.06, 9, 0.34, 50, 0.55, 0.0, L=12.0), lv(0.5, -0.02, 0.14, 6, 0.2, 54, 0.55, 0.09),
                lv(0.3, 0.0, 0.2, 4, 0.2, 52, 0.5, 0.07), TWIG],
        twig_len=(0.35, 0.7), fronds_per_twig=4, bend=0.14, card_scale=1.5,
        leaf=dict(atlas="br_understory", cards=["sourwood_a", "sourwood_b"], weights=[1.0, 0.5]), leaf_rough=0.5,
        bark=bark("bark_willow", "sourwood", (0.5, 0.8), (0.9, 0.88, 0.86), 0.3, 1.05),
        card_roll=60, lods=BROAD_LODS, lod_dist=[0, 18, 45, 100], impostor_px=(512, 256)),

    # =========================================================================================
    # understory (heaths)
    "rosebay_rhododendron": dict(
        kind="shrub", group="understory", title="Rosebay rhododendron", latin="Rhododendron maximum", variants=2,
        community="laurel hell, creekside (mask)", palette="#2E4A2C", height=4.5,
        reference="Sinuous grey-brown stems 8-15 cm thick that lean, twist and interlock, bare below; the foliage "
                  "a layered roof at 2-5 m of leathery 15-25 cm leaves in drooping whorls at the branch ends, dark "
                  "and glossy with a pale midrib. Mid-June: big green flower buds, the first white trusses along "
                  "the creek.",
        stems=7, stem_tilt=(18, 50), stem_off=(0.05, 0.4), envelope=((0, 0, 2.9), (3.0, 2.8, 1.9)),
        r_tip=0.0065, pipe=2.0, flare=0.0, rad_k=[1.7, 1.25],
        levels=[lv(0.3, 0.012, 0.22, 5, 0.45, 38, 0.55, 0.06, L=4.8), lv(0.25, 0.03, 0.25, 4, 0.3, 40, 0.5, 0.05),
                lv(0.15, 0.05, 0.2, 0, 0, 0, 0, 0)],
        twig_len=(0.2, 0.4), fronds_per_twig=3, bend=0.06, card_scale=1.15, card_flat=0.75,
        leaf=dict(atlas="br_evergreen", cards=["rosebay_a", "rosebay_b", "rosebay_c"], weights=[1.0, 1.0, 0.22]),
        leaf_rough=0.46, bark=bark("sakura_bark", "rhodo", (0.35, 0.6), (0.88, 0.85, 0.8), 0.4),
        shell=dict(atlas="br_evergreen", tile="rosebay_tile", tile_m=0.9, radius=0.62, res=0.2, inset=0.0, zmin=1.6, voxel=0.9, ball_k=1.0, ao_k=0.7),
        lods=SHRUB_LODS, lod_dist=[0, 12, 30, 70], impostor_px=(512, 256)),
    "mountain_laurel": dict(
        kind="shrub", group="understory", title="Mountain laurel", latin="Kalmia latifolia", variants=2,
        community="dry crests, slicks, lookout rims (mask)", palette="#3F5A2E", height=3.0,
        reference="A gnarled, crooked multi-stem shrub 2-4 m, red-brown bark in shreddy strips, a dense rounded "
                  "head. Leaves 5-10 cm, elliptic, pointed both ends, glossy dark green, clustered toward the tips. "
                  "Mid-June it is in late bloom: domed clusters of white-pink cup flowers, pink buds like piped "
                  "icing.",
        stems=10, stem_tilt=(12, 45), stem_off=(0.03, 0.3), envelope=((0, 0, 1.75), (1.9, 1.75, 1.35)),
        r_tip=0.005, pipe=2.0, flare=0.0, rad_k=[1.6, 1.2],
        levels=[lv(0.2, 0.02, 0.32, 6, 0.35, 42, 0.55, 0.05, L=3.0), lv(0.16, 0.03, 0.3, 5, 0.25, 44, 0.5, 0.04),
                lv(0.1, 0.05, 0.2, 0, 0, 0, 0, 0)],
        twig_len=(0.15, 0.3), fronds_per_twig=2, bend=0.06, card_scale=1.3, card_flat=0.5,
        leaf=dict(atlas="br_evergreen", cards=["laurel_a", "laurel_b"], weights=[1.0, 0.9]), leaf_rough=0.42,
        bark=bark("metasequoia_bark", "laurel", (0.3, 0.6), (0.9, 0.85, 0.82), 0.8),
        shell=dict(atlas="br_evergreen", tile="laurel_tile", tile_m=0.6, radius=0.45, res=0.16, inset=0.0, zmin=1.0, voxel=0.65, ball_k=1.0, ao_k=0.5),
        lods=SHRUB_LODS, lod_dist=[0, 12, 30, 60], impostor_px=(512, 256)),
    "catawba_rhododendron": dict(
        kind="shrub", group="understory", title="Catawba rhododendron", latin="Rhododendron catawbiense",
        variants=2, community="the Knob's heath bald", palette="#33502F", height=2.6,
        reference="The bald's dome: a dense mounded shrub 1.5-3 m, leafy to the ground, 10 cm oval leathery "
                  "leaves in whorls. In the first half of June it is at peak: every whorl topped by a 12-15 cm "
                  "truss of lilac-magenta funnel flowers (#B65A9E), the whole bald pink-purple (Roan, Craggy "
                  "Gardens).",
        stems=11, stem_tilt=(10, 42), stem_off=(0.03, 0.3), envelope=((0, 0, 1.35), (1.6, 1.5, 1.3)),
        r_tip=0.005, pipe=2.0, flare=0.0, rad_k=[1.6, 1.2],
        levels=[lv(0.18, 0.02, 0.22, 6, 0.3, 40, 0.55, 0.05, L=2.5), lv(0.14, 0.04, 0.25, 5, 0.25, 42, 0.5, 0.04),
                lv(0.1, 0.05, 0.2, 0, 0, 0, 0, 0)],
        twig_len=(0.15, 0.3), fronds_per_twig=2, bend=0.05, card_scale=1.3, card_flat=0.62,
        leaf=dict(atlas="br_evergreen", cards=["catawba_a", "catawba_b"], weights=[1.6, 1.0]), leaf_rough=0.46,
        bark=bark("sakura_bark", "catawba", (0.3, 0.5), (0.9, 0.85, 0.8), 0.4),
        shell=dict(atlas="br_evergreen", tile="catawba_tile", tile_m=0.7, radius=0.5, res=0.16, inset=0.0, zmin=0.6, voxel=0.7, ball_k=1.0, ao_k=0.5),
        lods=SHRUB_LODS, lod_dist=[0, 12, 30, 70], impostor_px=(512, 256)),
    "flame_azalea": dict(
        kind="shrub", group="understory", title="Flame azalea", latin="Rhododendron calendulaceum", variants=1,
        community="the bald's edge, open crests (accent)", palette="#62853F", height=2.4,
        reference="An open, deciduous, few-stemmed shrub 2-3 m, not a dome: grey-brown stems, soft pale-green "
                  "leaves 5-8 cm clustered at the twig tips, and in mid-to-late June (Gregory Bald) clusters of "
                  "5-9 funnel flowers in flame orange (#F08A2A) with a yellow blotch and long curved stamens.",
        stems=6, stem_tilt=(10, 38), stem_off=(0.05, 0.35), envelope=((0, 0, 1.55), (1.3, 1.2, 1.0)),
        r_tip=0.005, pipe=2.0, flare=0.0, rad_k=[1.6, 1.2],
        levels=[lv(0.2, 0.02, 0.28, 5, 0.4, 40, 0.55, 0.04, L=2.4), lv(0.16, 0.03, 0.3, 4, 0.3, 42, 0.5, 0.04),
                lv(0.1, 0.05, 0.2, 0, 0, 0, 0, 0)],
        twig_len=(0.15, 0.3), fronds_per_twig=3, bend=0.06, card_scale=1.35, card_flat=0.55,
        leaf=dict(atlas="br_understory", cards=["azalea_a", "azalea_b"], weights=[1.3, 1.0]), leaf_rough=0.6,
        bark=bark("metasequoia_bark", "azalea", (0.3, 0.5), (0.8, 0.78, 0.76), 0.3),
        lods=SHRUB_LODS, lod_dist=[0, 12, 30, 70], impostor_px=(512, 256)),
    "rhodo_thicket": dict(
        kind="thicket", group="understory", title="Laurel hell tile (rosebay thicket)", latin="Rhododendron maximum",
        variants=1, community="laurel hell (5.5%): tile on a ~6.5 m grid, overlapping", palette="#2E4A2C",
        height=4.4, impostor=False,
        reference="A laurel hell from inside: a maze of twisted, leaning grey stems you have to crawl through, "
                  "under a continuous dark roof of leathery leaves at 1.5-4.5 m; sight under 5 m. From outside a "
                  "solid wall of dark glossy green.",
        tile=8.0, grid=3, stems=4, stem_tilt=(24, 62), stem_off=(0.05, 0.5),
        envelope=((0, 0, 2.7), (4.7, 4.7, 1.9)), r_tip=0.0065, pipe=2.0, flare=0.0, rad_k=[1.7, 1.25],
        levels=[lv(0.3, 0.01, 0.24, 5, 0.42, 40, 0.55, 0.07, L=4.6), lv(0.25, 0.03, 0.25, 4, 0.3, 40, 0.5, 0.05),
                lv(0.15, 0.05, 0.2, 0, 0, 0, 0, 0)],
        twig_len=(0.2, 0.4), fronds_per_twig=2, bend=0.06, card_scale=1.25, card_flat=0.7,
        leaf=dict(atlas="br_evergreen", cards=["rosebay_a", "rosebay_b", "rosebay_c"], weights=[1.0, 1.2, 0.08]),
        leaf_rough=0.46, bark=bark("sakura_bark", "rhodo", (0.35, 0.6), (0.88, 0.85, 0.8), 0.4),
        shell=dict(atlas="br_evergreen", tile="rosebay_tile", tile_m=0.9, radius=0.85, res=0.24, inset=0.0,
                   zmin=1.8, max_balls=1600, voxel=1.0, ball_k=1.0),
        lods=[dict(trunk=5, branch=4, thin=3, seg=1, min_len=0.0, keep=0.7, csegs=1, max_level=1, thick_r=0.025,
                   shell=800),
              dict(trunk=4, branch=3, thin=0, seg=3, min_len=1.2, keep=0.14, csegs=1, max_level=0, shell=300,
                   max_grow=1.6),
              dict(trunk=3, branch=0, thin=0, seg=4, min_len=99, keep=0.02, csegs=1, max_level=0, shell=150,
                   max_grow=1.8)],
        lod_dist=[0, 12, 35, 160]),
    "rhodo_tunnel": dict(
        kind="thicket", group="understory", title="Laurel hell tile with a crawl tunnel", latin="Rhododendron maximum",
        variants=1, community="route C: chain these along the authored lane", palette="#2E4A2C", height=4.4,
        impostor=False, seed_off=17,
        reference="Route C's bear path: the same thicket with a crouch-height tunnel worn through it (1.3 m wide, "
                  "1.25 m clear), twisting a little; stems arch over it, the leaf roof closes above.",
        tile=8.0, grid=3, stems=4, stem_tilt=(24, 62), stem_off=(0.05, 0.5),
        envelope=((0, 0, 2.7), (4.7, 4.7, 1.9)), r_tip=0.0065, pipe=2.0, flare=0.0, rad_k=[1.7, 1.25],
        tunnel=dict(w=1.3, h=1.25, len=8.0, bend=0.7),
        levels=[lv(0.3, 0.01, 0.24, 5, 0.42, 40, 0.55, 0.07, L=4.6), lv(0.25, 0.03, 0.25, 4, 0.3, 40, 0.5, 0.05),
                lv(0.15, 0.05, 0.2, 0, 0, 0, 0, 0)],
        twig_len=(0.2, 0.4), fronds_per_twig=2, bend=0.06, card_scale=1.25, card_flat=0.7,
        leaf=dict(atlas="br_evergreen", cards=["rosebay_a", "rosebay_b", "rosebay_c"], weights=[1.0, 1.2, 0.08]),
        leaf_rough=0.46, bark=bark("sakura_bark", "rhodo", (0.35, 0.6), (0.88, 0.85, 0.8), 0.4),
        shell=dict(atlas="br_evergreen", tile="rosebay_tile", tile_m=0.9, radius=0.85, res=0.24, inset=0.0,
                   zmin=1.8, max_balls=1600, voxel=1.0, ball_k=1.0),
        lods=[dict(trunk=5, branch=4, thin=3, seg=1, min_len=0.0, keep=0.7, csegs=1, max_level=1, thick_r=0.025,
                   shell=800),
              dict(trunk=4, branch=3, thin=0, seg=3, min_len=1.2, keep=0.14, csegs=1, max_level=0, shell=300,
                   max_grow=1.6),
              dict(trunk=3, branch=0, thin=0, seg=4, min_len=99, keep=0.02, csegs=1, max_level=0, shell=150,
                   max_grow=1.8)],
        lod_dist=[0, 12, 35, 160]),

    # =========================================================================================
    # ground layer
    "doghobble": dict(
        kind="clump", group="ground", title="Doghobble", latin="Leucothoe fontanesiana", variants=2,
        community="creek banks (mask)", palette="#355A2B", height=1.1,
        reference="Arching, fountain-like stems 1-1.5 m from the base, leaves alternate in two flat ranks, 8-12 cm, "
                  "lance-shaped with a long point, leathery and glossy; new tips bronze-red. Tangles the banks "
                  "(its name: bears get hobbled in it).",
        fronds=18, elev=(50, 76), bend=0.5, crown_r=0.28,
        leaf=dict(atlas="br_ground", cards=["doghobble_a", "doghobble_b"]), card_scale=1.15, leaf_rough=0.58,
        lods=[dict(fronds=18, csegs=4), dict(fronds=8, csegs=2), dict(fronds=4, csegs=1)],
        lod_dist=[0, 10, 25, 50]),
    "christmas_fern": dict(
        kind="clump", group="ground", title="Christmas fern", latin="Polystichum acrostichoides", variants=2,
        community="cove floor, slopes (ring within 25 m)", palette="#2F5027", height=0.55,
        reference="Knee-high evergreen clumps of arching once-cut fronds 30-60 cm, dark glossy green and "
                  "leathery; each pinna has a little upward 'ear' (a Christmas stocking). The cove floor's carpet "
                  "under the poplars.",
        fronds=22, elev=(44, 74), bend=0.3, crown_r=0.05,
        leaf=dict(atlas="br_ground", cards=["xmas_fern_a", "xmas_fern_b"]), card_scale=1.05, leaf_rough=0.58,
        lods=[dict(fronds=22, csegs=3), dict(fronds=10, csegs=2), dict(fronds=5, csegs=1)],
        lod_dist=[0, 8, 18, 30]),
    "cinnamon_fern": dict(
        kind="clump", group="ground", title="Cinnamon fern", latin="Osmundastrum cinnamomeum", variants=2,
        community="seeps, wet hollows", palette="#5E8838", height=1.1,
        reference="A tall vase of upright sterile fronds 0.6-1.2 m, deeply cut, light yellow-green; in the centre "
                  "the fertile fronds, by June withered cinnamon-brown spikes.",
        fronds=14, elev=(58, 80), bend=0.2, crown_r=0.07, frond_rects=[0],
        fertile=dict(rect=1, n=4, elev=(80, 88)),
        leaf=dict(atlas="br_ground", cards=["cinn_fern_a", "cinn_fertile"]), card_scale=1.15, leaf_rough=0.6,
        lods=[dict(fronds=14, csegs=3), dict(fronds=7, csegs=2), dict(fronds=4, csegs=1, fertile=False)],
        lod_dist=[0, 10, 22, 36]),
    "moss_cushion": dict(
        kind="mat", group="ground", title="Moss cushion", latin="Polytrichum / Thuidium mats", variants=2,
        community="rocks, logs, roots, wet north faces", palette="#4F7A2A", height=0.12, radius=0.5, oval=0.8,
        variant_dims=[(0.5, 0.12), (0.8, 0.09)],
        reference="Deep green moss cushions and mats on wet ground, roots and rock: a soft lumpy surface of "
                  "haircap-moss stars, ragged at the edges where single sprigs stand up.",
        shell=dict(atlas="br_ground", tile="moss_tile", tile_m=0.25),
        leaf=dict(atlas="br_ground", cards=["moss_fringe"]), leaf_rough=0.8, impostor=False,
        lods=[dict(rings=4, segs=14, fringe=14), dict(rings=2, segs=8, fringe=6, fringe_scale=1.3),
              dict(rings=1, segs=6, fringe=0)],
        lod_dist=[0, 8, 20, 40]),

    # =========================================================================================
    # dead wood and rock (blender/wilderness/deadwood.py)
    "chestnut_log": dict(
        kind="log", group="deadwood", title="Chestnut ghost (fallen giant)", latin="Castanea dentata, dead since the 1930s",
        variants=2, community="upper slopes, convex (where chestnut stood); 3-6 logs/ha with the blowdowns",
        reference="American chestnut killed by the blight 90 years ago, still lying where it fell: rot-proof, "
                  "barkless, weathered silver-grey with long checks along the grain and broken snags of limbs, "
                  "moss on the top; the big one 1.2 m thick with its root plate still up on end.",
        length=18.0, radius=0.62, taper=0.3, bend=0.3, sink=0.1, split=True, stubs=5, moss=0.5,
        wad=dict(radius=1.9, lift=1.6, reach=5.0, thick=0.6, roots=7),
        variant_over=[{}, dict(length=13.0, radius=0.42, wad=None, stubs=3, moss=0.65)],
        bark=bark("rough_wood", "ghost", (1.6, 2.6), (0.97, 0.97, 1.0), 0.2, 1.12, rough=0.85),
        soil=bark("forest_leaves_02", "soil", (1.2, 1.2), (0.8, 0.72, 0.62), 0.6, 0.62, rough=0.95),
        lods=[dict(sides=14, step=1, wad_segs=16, wad_rings=3, subdiv=3),
              dict(sides=8, step=2, wad_segs=10, wad_rings=2, subdiv=2, stubs=False),
              dict(sides=5, step=6, wad_segs=6, wad_rings=1, subdiv=1, stubs=False)],
        lod_dist=[0, 25, 60, 150]),
    "chestnut_log_propped": dict(
        kind="log", group="deadwood", title="Chestnut ghost propped on a boulder", latin="Castanea dentata, dead",
        variants=1, community="cove boulder fields, across trails",
        reference="A silver chestnut log that came down across a boulder: one end on the ground, the other "
                  "held up 1.2 m, so you can walk up it or crawl under the high end.",
        length=15.0, radius=0.48, taper=0.3, bend=0.2, sink=0.08, split=True, stubs=4, moss=0.4,
        prop=dict(x=11.5, height=1.25, boulder=(1.9, 1.6, 1.35)),
        bark=bark("rough_wood", "ghost", (1.6, 2.6), (0.97, 0.97, 1.0), 0.2, 1.12, rough=0.85),
        rock=bark("mossy_rock", "gneiss", (1.6, 1.6), (0.95, 0.95, 0.95), 0.75, 1.0, rough=0.8),
        lods=[dict(sides=12, step=1, subdiv=4), dict(sides=7, step=2, subdiv=3, stubs=False),
              dict(sides=5, step=6, subdiv=2, stubs=False)],
        lod_dist=[0, 25, 60, 150]),
    "blowdown_log": dict(
        kind="log", group="deadwood", title="Tulip poplar blowdown", latin="Liriodendron tulipifera, windthrown",
        variants=1, community="coves (blowdowns), high sediment",
        reference="A recent cove blowdown: a 1.4 m poplar with its grey braided bark still on, lying downslope, "
                  "its 5 m root plate of soil, rock and roots torn up on end beside the pit; ferns and moss "
                  "already on top.",
        length=22.0, radius=0.7, taper=0.4, bend=0.35, sink=0.1, stubs=6, moss=0.45,
        wad=dict(radius=2.4, lift=1.8, reach=5.5, thick=0.75, roots=9),
        bark=bark("tree_bark_03", "poplar", (1.2, 1.6), (0.98, 1.0, 0.97), 0.6),
        soil=bark("forest_leaves_02", "soil", (1.2, 1.2), (0.8, 0.72, 0.62), 0.6, 0.62, rough=0.95),
        lods=[dict(sides=14, step=1, wad_segs=16, wad_rings=3, subdiv=3),
              dict(sides=8, step=2, wad_segs=10, wad_rings=2, subdiv=2, stubs=False),
              dict(sides=5, step=6, wad_segs=6, wad_rings=1, subdiv=1, stubs=False)],
        lod_dist=[0, 25, 60, 150]),
    "chestnut_stump": dict(
        kind="stump", group="deadwood", title="Chestnut snag stump", latin="Castanea dentata, dead",
        variants=1, community="upper slopes",
        reference="What is left standing of a blight-killed chestnut: a silver, buttressed stump 1-1.5 m high, "
                  "snapped off in long jagged splinters, hollowing at the top.",
        height=1.35, radius=0.5, broken=True, flare=0.7, lobes=5, moss=0.3,
        bark=bark("rough_wood", "ghost", (1.6, 2.6), (0.97, 0.97, 1.0), 0.2, 1.12, rough=0.85),
        lods=[dict(sides=18, rings=7), dict(sides=10, rings=3), dict(sides=6, rings=2)],
        lod_dist=[0, 20, 50, 120]),
    "cut_stump": dict(
        kind="stump", group="deadwood", title="Old logging stump", latin="(cut c. 1910-30)",
        variants=1, community="logged slopes outside the old-growth cove",
        reference="A century-old crosscut-saw stump from the logging era: knee-high, the sawn top gone soft "
                  "and green with moss, bark long gone, buttress roots running into the litter.",
        height=0.7, radius=0.55, broken=False, flare=0.8, lobes=6, moss=0.75,
        bark=bark("rough_wood", "oldstump", (1.0, 1.2), (0.9, 0.86, 0.8), 0.4, 0.78, rough=0.9),
        lods=[dict(sides=18, rings=5), dict(sides=10, rings=3), dict(sides=6, rings=2)],
        lod_dist=[0, 20, 50, 100]),
    "creek_boulder": dict(
        kind="rock", group="rock", title="Creek boulder (mossy gneiss)", latin="Precambrian gneiss",
        variants=3, community="the creek, the Narrows (3-5 m), cove boulder fields",
        reference="Rounded, water-worn grey gneiss with pale lichen and black water streaks, the tops capped "
                  "in thick green moss wherever spray and shade keep them wet; from knee-high stepping stones to "
                  "the 4 m blocks of the Narrows.",
        dims=(2.3, 1.8, 1.3), variant_size=[(2.3, 1.8, 1.3), (1.1, 0.9, 0.7), (4.2, 3.2, 2.4)],
        facets=5, moss=0.6, tile=1.6,
        rock=bark("mossy_rock", "gneiss", (1.6, 1.6), (0.95, 0.95, 0.95), 0.75, 1.0, rough=0.8),
        lods=[dict(subdiv=4), dict(subdiv=3), dict(subdiv=2)],
        lod_dist=[0, 25, 60, 200]),
}
