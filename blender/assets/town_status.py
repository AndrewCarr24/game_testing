"""Write design/town/kit_status.md from the town kit's sidecars (assets/models/town_*.json).
Not an asset; plain python:  python3 blender/assets/town_status.py
"""
import glob
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "design", "town", "kit_status.md")

WHAT = {
    "town_bar": "**the roadhouse (hero)**: cinder block + board, deep porch with neon (BAR, bottle, cocktail, star), roof sign, river deck with steps to the water; inside a 14 m bar, back bar, 5 booths, pool table, jukebox, stage, restroom hall, back room (table, hook rail, monitors) with its door ajar",
    "town_shop_a": "brick shopfront, boutique / outdoor gear, forest-green awning",
    "town_shop_b": "brick shopfront, coffee, burgundy awning, a bench; walk-in front room (counter, espresso, pastry case, tables)",
    "town_shop_c": "painted-brick shopfront (pale pink), ice cream / sweets, striped awning",
    "town_shop_d": "the bank branch: dark brick, stone pilasters and cornice, an ATM; walk-in front room (teller line, vault door)",
    "town_shop_wide": "double shopfront, outfitter / fly shop, navy awnings",
    "town_shop_realty": "double shopfront, the real-estate office: photo boards of estates in the windows; walk-in front room",
    "town_shop_mountain": "extra: a new-build mountain-style shop (gable front, cedar king-post truss, board-and-batten, black canopy)",
    "town_church": "white frame church, square steeple to 21 m (belfry, clock face without numerals, spire, cross), pointed windows, double door up 5 steps; walk-in nave (20 pews, chancel)",
    "town_gas_station": "canopy over 3 pump islands (6 dispensers, lit band, LED panels), price pylon, walk-in convenience store (2 aisles, coolers, counter, coffee), ice chest, propane cage, air pump",
    "town_fastfood": "burger drive-through: chain-style box, tilted red-brown roof band (lit underside), burger pictogram, big windows, drive-through window on +X; walk-in dining room (booths, tables), counter, kitchen",
    "town_plaza": "1980s strip plaza, 4 x 16 m units (vacant, laundromat, pharmacy with a green neon cross, video store), shingled mansard over a covered walk; walk-in video store (racks, counter, posters) and its back room (CRT wall spot)",
    "town_depot": "the depot museum: board-and-batten, deep bracketed eaves, the agent's bay; walk-in waiting room (benches, vitrines, ticket window) and freight room (raised 1.25 m, model table spot); freight platform with a 1.15 m crawl space",
    "town_truss_span": "steel Pratt through truss, 38 m, repainted green: two lanes on a concrete deck, a cantilevered sidewalk, LED portal lamps; deck top z = 0",
    "town_bridge_pier": "cut-stone pier with a pointed cutwater; origin = cap top (bearing seat 0.95 m under the spans' deck top); scale in z",
    "town_water_tower": "steel tank on four legs (9 m tank, 24 m top), catwalk, ladder, the mountain pictogram, a red beacon",
    "town_streetlight": "downtown acorn lamp post, 4.5 m (glow globe)",
    "town_streetlight_basket": "the acorn lamp post with a flower-basket arm",
    "town_flower_basket": "a hanging flower basket (hook at z 0.75)",
    "town_highway_light": "cobra-head pole, 10 m",
    "town_bench": "park bench, cedar slats, black ends",
    "town_planter": "cedar planter with boxwood and flowers",
    "town_bollard": "black bollard",
    "town_trash_can": "black litter bin with cedar slats",
    "town_menu_board": "drive-through menu board (lit panels, blank rows) + speaker post",
    "town_clearance_bar": "drive-through clearance gantry",
    "town_pump": "fuel dispenser",
    "town_ice_chest": "ice chest",
    "town_crate_stack": "crates on pallets, shrink-wrapped",
    "town_table_phones": "folding table with thirty phones, screens dark",
    "town_crt_wall": "a wall of twenty old TV sets, screens glowing",
    "town_estate_model": "museum vitrine with a scale model of the estate",
    "town_raft": "14 ft grey river raft",
}

HEAD = """# Town buildings kit: status (kit agent -> layout agent)

Source of truth for the names, sizes, footprints, entrances and triangle counts of `blender/assets/town_*.py`.
**Generated** from the sidecars by `python3 blender/assets/town_status.py` (re-run after builds).
Each asset exports `assets/models/<name>.gltf` (+ `.bin`, Draco) and a sidecar `assets/models/<name>.json`
(size, bounds, `below_m`, colliders, entrances, tris, lights, notes). Answers `kit_request.md` **v2**.

## Contract
- **Frame**: metres; origin = floor centre at the main door's sill (z = 0 = the pad); front (street, main door) -Y;
  yaw-only placement. `below_m` = how far anything hangs below the pad. Footprints below include porches,
  steps, canopies, platforms and decks: `[x0, y0, x1, y1]` in the asset frame.
- **Materials: 2 for the whole kit.** `M_Town_Atlas` (opaque; base colour `T_Town_Atlas`, 2048, WebP in the
  export) and `M_Town_Glow` (the same atlas as emission: neon tubes, lamp shades, bulbs, back-lit bottles,
  screens, lit signs, streetlight globes; draw it unlit, colour x intensity). No transparency anywhere, no
  alpha-tested material: glass is painted into the atlas (window cells show curtains, blinds, a cafe's pendants,
  shelves, tapes...; sash frames painted in). Materials are single-sided (`doubleSided` false): from inside a
  walk-in, its windows' painted glass culls and the street shows through.
- **COLOR_0 (`AO` in Blender) on every mesh**: 1 = unchanged. Two uses, both multiplied into the base colour:
  (1) **tints** (`tints` in the sidecar: whole parts recoloured, e.g. brick tones, so one region serves several
  buildings); (2) **baked interior light** in the walk-ins (their lamps and glowing pieces baked with Cycles:
  warm pools under the shades, a pink wash under the neon, dark between). Outside the rooms it stays 1 (or the
  tint). For the film-set look inside a walk-in, shade its interior unlit (albedo x COLOR_0, about x 1.3) or at
  least do not let the sky light flatten it; the lamps are also listed in the sidecar (`lights`).
- **How one atlas repeats**: faces are split at every tile boundary of their world-scale UVs (u along a wall, v =
  height), so each piece maps inside its region (8 px wrapped gutters). Regions: board-and-batten white /
  charcoal / sage, lap siding cream / white, ledgestone, fieldstone, red brick, white brick, black and green
  standing seam, architectural shingle, corrugated, cedar, painted block, concrete, asphalt, deck boards, plaster,
  wood floor, checker, tile, dark wood, varnished wood, polished concrete, windows, signs, a flat palette (64
  swatches incl. each big region's mean colour, which the LOD1s use). Layout: `assets/textures/town_polyhaven.json`.
- **LOD1**: a child mesh `<Root>_LOD1` in the same glTF, palette swatches only, for > 120 m (hidden in the
  Blender previews). Triangles below.
- **Colliders**: AABBs `[x0, y0, z0, x1, y1, z1]` in the asset frame, in the sidecar and in the root node's extras
  (`town`, a JSON string). Walk-ins: walls split at the doors; counters, booths, tables, shelves, stairs.
- **Doors** of walk-ins: `<Root>_Door_<n>` empties at the hinge with `interact` (`rotate`) extras, leaf meshes under
  them. The door openings have no static collider (a closed leaf is inert in the wild runtime). Other doors are
  closed and part of the walls.
- **Signs**: pictograms only (cup, burger, mountains, cassette, star badge, cocktail glass, pediment, pump), plus
  neon tube shapes; one generic word, **BAR**, in neon at the roadhouse. No names, slogans, dates, brands.
- **Scans** (Poly Haven, CC0) behind the atlas: weathered_plank_siding, white_planks_clean, rustic_stone_wall_02,
  stone_wall, factory_brick, whitewashed_brick, japanese_cedar_planks, worn_corrugated_iron, metal_plate,
  concrete_floor_02, asphalt_02, weathered_planks, painted_plaster_wall, wood_floor_worn, dark_wood, wood_table_001,
  smooth_concrete_floor, old_linoleum_flooring_01, square_tiles.
- **References** (what the look is matched to): Marshall NC Main Street (Commons `Main_Street,_Marshall,_NC_(39724136513).jpg`),
  Saluda's Main Street (`Saluda_Historic_District.jpg`, `Thompson's_Grocery_Market.jpg`, `Saluda_Library_and_Old_Rail_Depot.jpg`),
  Hot Springs NC (`Town_of_Hot_Springs_and_Bridge_Street.jpg`, `Bridge_over_the_French_Broad_River.jpg`,
  `Dorland_Memorial_Presbyterian_Church,_Hot_Springs,_NC_(46619175092).jpg`), the polished new-build look of
  Highlands / Blowing Rock / Cashiers main streets (stone bases, board-and-batten, black standing seam).

## Assets
"""


def main():
    rows = []
    for p in sorted(glob.glob(os.path.join(ROOT, "assets", "models", "town_*.json"))):
        d = json.load(open(p))
        name = os.path.basename(p)[:-5]
        if not os.path.exists(os.path.join(ROOT, "assets", "models", name + ".gltf")):
            continue
        rows.append((name, d))
    out = [HEAD]
    out.append("| name | what | w x d x h (m) | footprint [x0, y0, x1, y1] | below_m | walk-in | entrances | LOD0 / LOD1 tris |")
    out.append("|---|---|---|---|---|---|---|---|")
    for name, d in rows:
        s = d["size"]
        ent = "; ".join(f"{e['kind']} {e['facing']} at ({e['pos'][0]}, {e['pos'][1]}) w {e['width']}" + (f" ({e['note']})" if e.get("note") else "")
                        for e in d.get("entrances", [])) or "-"
        fp = d.get("footprint", "")
        out.append(f"| `{name}` | {WHAT.get(name, '')} | {s[0]} x {s[1]} x {s[2]} | {fp} | {d.get('below_m', 0)} | "
                   f"{'**yes**' if d.get('walk_in') else 'no'} | {ent} | {d.get('tris_lod0')} / {d.get('tris_lod1')} |")
    out.append("")
    out.append("## Notes per asset")
    for name, d in rows:
        extra = {k: v for k, v in d.items() if k in ("rooms", "deck_top_z", "sidewalk", "lane", "crawl_space", "hooks",
                                                     "crt_wall_spot", "model_table_spot", "top_m", "tank", "party_walls",
                                                     "tints", "lighting", "units")}
        if extra:
            out.append(f"- `{name}`: " + "; ".join(f"{k}: {v}" for k, v in extra.items()))
    out.append("")
    out.append(STILL)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write("\n".join(out) + "\n")
    print("wrote", OUT, len(rows), "assets")


STILL = """## Changed from kit_request.md v2 (and why)
- `town_bar` 30.9 x 21.1 (incl. the chimney, the porch, the deck and its steps down 1.8 m to the water): the brief's 30 x 18
  plus the steps. LOD0 25.0k (the budget's 25k).
- `town_church` 12.9 x 29.2 x 21.9: the 26 m nave + tower depth plus the five steps in front (below_m 0.9).
- `town_gas_station` 27.6 x 30.1: canopy 27 m wide (3 islands), store 18 x 12 behind it, the pylon at the canopy's front corner.
- `town_fastfood` 20.8 x 16.6 incl. the tilted band (0.55 m out all round) and the drive-through canopy on +X; the menu
  board, speaker and clearance bar are separate props (`town_menu_board`, `town_clearance_bar`).
- `town_depot` 33.8 x 15.6: the 32 x 10 depot plus its eaves and the 4 m platforms on +Y. The freight platform is 1.25 m
  high (not 1.1) so the crawl space under it is 1.15 m clear.
- Downtown shops are 8.1 x 19.6 (incl. the awning and back cornice): party walls flush at +-4.
- Not built yet (next): `town_sheriff`, `town_cottage_a/b/c`, `town_house_a/b/c`, `town_mill` + `_stack`, `town_church_hall`,
  `town_inn`, `town_motel_*`, `town_school`, `town_garage(_open)`, `town_shed`, `town_footbridge`, `town_tunnel_portal`,
  vehicles (`town_van`, `town_cruiser`, `town_suv`, `town_car`, `town_pickup`, `town_train`).
"""

if __name__ == "__main__":
    main()
