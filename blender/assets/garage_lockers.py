"""Mudroom locker wall: four bays between cream lacquer partitions. Each bay has a
sage-painted back panel with an oak hook rail and bronze hooks, an oak bench seat with an
upholstered linen cushion (welted, crowned), open shoe cubbies below and a cream cupboard
above with a bronze pull.

The bays are dressed like a lived-in country-house mudroom, unevenly: garments that hang
like fabric (cloth-simulated in mud_common: a waxed field jacket, a camel coat, a quilted
gilet, a hooded jacket, a wool scarf over a hook), a felt hat, a canvas boat tote, a
furled umbrella, a leather dog lead; modelled trainers and penny loafers in the cubbies, a
pair of scanned Poly Haven wellies and a scanned bamboo basket in the boot bay, a folded
wool throw on one cushion. `palette` picks the outfit set, `coats` which bays hold a coat.

Units are metres. The front faces -Y (back at +Y against the wall), the origin is
the floor centre.
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import garage_cabinets as gk  # noqa: E402
import mud_common as mc  # noqa: E402

importlib.reload(gk)
importlib.reload(mc)
common, materials, textures = gk.common, gk.materials, mc.textures

NAME = "GarageLockers"

P = dict(
    name=NAME,
    bays=4,
    bay_w=1.0,
    depth=0.56,
    height=2.5,
    part_t=0.025,
    bench_z=0.46,         # top of the oak seat
    seat_t=0.04,
    rail_z=1.62,
    cup_z0=1.95,
    coats=(0, 1, 0, 1),   # which bays carry a coat (the others get lighter things: a hat, a tote...)
    palette=0,            # outfit set (OUTFITS)
)

# Hook-rail dressing. Coat bays take the next entry of "coat", the other bays the next of
# "light"; each entry is a list of (hook index 0..3, item). Under-bench dressing cycles per bay.
OUTFITS = [
    dict(coat=[[(1, "waxed_olive"), (3, "scarf_rust")], [(2, "coat_camel")]],
         light=[[(0, "hat"), (2, "lead")], [(1, "tote")]],
         under=["boots", "trainers", "loafers", "trainers_navy"],
         throw=2),
    dict(coat=[[(0, "gilet_navy"), (2, "scarf_oat")], [(1, "hooded_grey")]],
         light=[[(1, "tote"), (3, "umbrella")]],
         under=["trainers_navy", "loafers", "boots"],
         throw=None),
]


# ------------------------------------------------------------------ materials

def _fabric(name, rgb, roughness=0.9, strength=0.35):
    m = materials.fabric(name, rgb, roughness=roughness)
    nm = next((n for n in m.node_tree.nodes if n.type == "NORMAL_MAP"), None)
    if nm:
        nm.inputs["Strength"].default_value = strength
    return m


def _leather(name, rgb, roughness=0.55):
    m = common.pbr_material(name, rgb, roughness=roughness)
    common.set_normal_map(m, textures.load(textures.leather_normal(), non_color=True), 0.5)
    return m


def palette_materials():
    cognac = common.pbr_material("M_Leather_Cognac", (0.23, 0.075, 0.025), roughness=0.62)
    common.set_normal_map(cognac, textures.load(textures.leather_normal(), non_color=True), 0.6)
    wool = common.pbr_material("M_Wool_Charcoal", (0.06, 0.06, 0.065), roughness=0.95)
    common.set_base_color_map(wool, textures.load(textures.wool()))
    return dict(
        wax_olive=_fabric("M_Mud_Wax_Olive", (0.04, 0.046, 0.026), roughness=0.5),
        cord=_fabric("M_Mud_Cord_Brown", (0.06, 0.03, 0.014), strength=0.6),
        camel=_fabric("M_Coat_Camel", (0.35, 0.22, 0.10), roughness=0.95),
        navy=_fabric("M_Coat_Navy", (0.016, 0.022, 0.05), roughness=0.55),
        grey=_fabric("M_Coat_Grey", (0.11, 0.115, 0.12), roughness=0.7),
        rust=_fabric("M_Mud_Wool_Rust", (0.2, 0.05, 0.025), roughness=0.95, strength=0.6),
        oat_wool=_fabric("M_Mud_Wool_Oatmeal", (0.38, 0.33, 0.26), roughness=0.95, strength=0.6),
        canvas=_fabric("M_Mud_Canvas", (0.46, 0.42, 0.34), strength=0.5),
        felt=_fabric("M_Mud_Felt_Tobacco", (0.12, 0.075, 0.04), roughness=0.95, strength=0.2),
        band=common.pbr_material("M_Mud_Grosgrain", (0.02, 0.016, 0.013), roughness=0.6),
        canopy=_fabric("M_Mud_Umbrella", (0.012, 0.022, 0.018), roughness=0.45, strength=0.3),
        bridle=_leather("M_Mud_Leather_Bridle", (0.055, 0.024, 0.01), roughness=0.45),
        cognac=cognac,
        white=_leather("M_Mud_Leather_White", (0.70, 0.68, 0.64), roughness=0.45),
        suede=_fabric("M_Mud_Suede_Navy", (0.02, 0.028, 0.06), roughness=1.0, strength=0.25),
        sole=common.pbr_material("M_Mud_Sole", (0.62, 0.60, 0.55), roughness=0.75),
        sole_dark=common.pbr_material("M_Mud_Sole_Dark", (0.025, 0.02, 0.016), roughness=0.6),
        lining=common.pbr_material("M_Mud_Lining", (0.045, 0.04, 0.035), roughness=0.85),
        brass=materials.bronze(),
        wool=wool,
        boots=mc.scan_material("M_GarageLockers_Boots", "rubber_boots", "T_GarageLockers_Boots", 0.32,
                               fallback=(0.015, 0.05, 0.025)),
        basket=mc.scan_material("M_GarageLockers_Basket", "wicker_basket_02", "T_GarageLockers_Basket", 0.75,
                                fallback=(0.36, 0.22, 0.10)),
    )


# ------------------------------------------------------------------ dressing

def xf(bm, rot_x=0.0, rot_z=0.0, scale=1.0, move=(0, 0, 0)):
    m = Matrix.Translation(move) @ Matrix.Rotation(rot_z, 4, "Z") @ Matrix.Rotation(rot_x, 4, "X") @ Matrix.Scale(scale, 4)
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    return bm


def soft(b, name, bm, mats, loc, tile=0.25, sharp=1.2):
    """A non-colliding soft / small item: smooth shaded with crease edges kept sharp; merged
    into the Detail_Piping meshes (COLLIDER_SKIP), so hanging fabric never blocks the player."""
    ob = b._add(f"{name}_NoCollide", bm, mats[0], loc, tile, 0, 1, smooth=True, solid=False)
    for m in mats[1:]:
        ob.data.materials.append(m)
    ob.data.set_sharp_from_angle(angle=sharp)
    return ob


def scanned(b, name, bm, mat, loc):
    """A scanned mesh keeps its own UVs (Builder._add would box-project over them)."""
    ob = common.mesh_object(f"{b.n}_{name}_NoCollide", bm, b.col, mat, b.root, smooth=True)
    ob.location = loc
    b.items.append((ob, False))
    return ob


def hang(b, M, item, name, x, y_tip, z, wall, seed):
    """Put one item on the hook whose tip is at (x, y_tip, z)."""
    loc = (x, y_tip, z)
    if item == "waxed_olive":
        soft(b, name, mc.hook_jacket(wall=wall, tris=1100), [M["wax_olive"], M["cord"]], loc)
    elif item == "coat_camel":
        soft(b, name, mc.hook_jacket(length=0.95, width=0.245, depth=0.03, sleeve=0.6, collar=0.09, wall=wall,
                                     pockets="flap", stiff=0.7, mass=0.45, tris=1050),
             [M["camel"], M["camel"]], loc)
    elif item == "hooded_grey":
        soft(b, name, mc.hook_jacket(length=0.78, width=0.255, depth=0.035, hood=True, collar=0.0, wall=wall,
                                     pockets="flap", stiff=1.3, tris=1100), [M["grey"], M["grey"]], loc)
    elif item == "gilet_navy":
        soft(b, name, mc.hook_jacket(length=0.66, width=0.235, depth=0.035, sleeve=0, collar=0.06, pockets=None,
                                     quilt=0.07, voxel=0.02, tris=700, stiff=1.2, wall=wall),
             [M["navy"], M["navy"]], loc)
    elif item in ("scarf_rust", "scarf_oat"):
        soft(b, name, mc.scarf(wall=wall, seed=seed, tris=520), [M["rust" if item == "scarf_rust" else "oat_wool"]], loc)
    elif item == "hat":
        soft(b, name, xf(mc.felt_hat(), rot_x=math.radians(96)), [M["felt"], M["band"]],
             (x, y_tip + wall - 0.042, z - 0.08), sharp=1.0)
    elif item == "lead":
        soft(b, name, mc.dog_lead(), [M["bridle"], M["brass"]], loc)
    elif item == "umbrella":
        soft(b, name, mc.umbrella(), [M["canopy"], M["cognac"], M["brass"]], loc, sharp=0.9)
    elif item == "tote":
        bag, handles = mc.tote(wall=wall, tris=520)
        soft(b, name, bag, [M["canvas"], M["navy"]], loc)
        soft(b, name + "_Handles", handles, [M["navy"]], loc)


def shoe_pair(b, M, name, kind, x, y, z, rot=0.0, colour="white"):
    mats = {"white": [M["white"], M["sole"], M["lining"], M["sole"]],
            "navy": [M["suede"], M["sole"], M["lining"], M["sole"]],
            "cognac": [M["cognac"], M["sole_dark"], M["lining"], M["cognac"]]}[colour]
    length, width = (0.285, 0.102) if kind == "trainer" else (0.275, 0.094)
    for k, side in enumerate((-1, 1)):
        bm = mc.shoe(kind, length=length, width=width, side=side)
        a = rot + side * 0.05 + (0.06 if k else 0.0)
        xf(bm, rot_z=a)
        soft(b, f"{name}_{k}", bm, mats, (x + side * 0.062, y - 0.012 * k, z), tile=0.2, sharp=1.0)


def boots(b, M, name, x, y, z):
    bm = mc.scan_mesh("rubber_boots", ["rubber_boots_l", "rubber_boots_r"], 1800, scale=0.9)
    if bm is None:                     # offline first build: loafers stand in
        shoe_pair(b, M, name, "loafer", x, y, z, colour="cognac")
        return
    # toes out (-Y): the shaft stands over the heel, so it must be on the +Y side
    shaft = [v.co.y for v in bm.verts if v.co.z > 0.2]
    if sum(shaft) / len(shaft) < 0:
        xf(bm, rot_z=math.pi)
    scanned(b, name, bm, M["boots"], (x, y, z))


def basket(b, M, name, x, y, z, rot=0.0):
    bm = mc.scan_mesh("wicker_basket_02", ["wicker_basket_02_base"], 1100, scale=1.2, rotate_z=rot)
    if bm is None:
        return
    scanned(b, name, bm, M["basket"], (x, y, z))


# ------------------------------------------------------------------ asset

def build(**overrides):
    p = {**P, **overrides}
    b = gk.Builder(p["name"])
    grd = gk.graphite_dark()
    cream, oak, sage = gk.cream(), gk.oak_light(), gk.sage()
    bronze = materials.bronze()
    oat = gk.linen("M_Fabric_Oat", (0.42, 0.37, 0.30))
    M = palette_materials()

    N, bw, D, H, pt = p["bays"], p["bay_w"], p["depth"], p["height"], p["part_t"]
    W = N * bw + (N + 1) * pt
    yf, yb = -D / 2, D / 2
    x0 = -W / 2
    bz, st = p["bench_z"], p["seat_t"]
    ph = 0.07
    rz = p["rail_z"]
    y_tip = yb - 0.105           # hook knob tip
    wall = (yb - 0.015) - y_tip  # hook tip to the back panel

    # plinth, top, partitions
    b.lo_hi("Plinth", (x0 + 0.02, yf + 0.04, 0), (-x0 - 0.02, yb, ph), grd, bevel=0)
    b.lo_hi("Top", (x0 - 0.005, yf, H - 0.04), (-x0 + 0.005, yb, H), cream, bevel=0.003)
    for i in range(N + 1):
        xa = x0 + i * (bw + pt)
        b.lo_hi(f"Partition{i}", (xa, yf, ph), (xa + pt, yb, H - 0.04), cream, bevel=0.002)

    out = OUTFITS[p["palette"] % len(OUTFITS)]
    n_coat = n_light = 0
    for i in range(N):
        xa = x0 + pt + i * (bw + pt)
        xb = xa + bw
        xc = (xa + xb) / 2
        hooks = [xa + 0.14 + k * (bw - 0.28) / 3 for k in range(4)]
        under = out["under"][i % len(out["under"])]
        # back panel (sage) and the oak hook rail with bronze hooks
        b.lo_hi(f"Back{i}", (xa, yb - 0.015, ph), (xb, yb, H - 0.04), sage, bevel=0, tile=0.5)
        b.lo_hi(f"Rail{i}", (xa, yb - 0.05, rz - 0.045), (xb, yb - 0.015, rz + 0.045), oak, bevel=0.003)
        for k, hx in enumerate(hooks):
            b.cyl(f"Hook{i}_{k}_Stem", 0.007, 0.05, (hx, yb - 0.075, rz), bronze, axis="y", seg=8)
            b.cyl(f"Hook{i}_{k}_Knob", 0.014, 0.022, (hx, yb - 0.095, rz), bronze, axis="y", seg=8, r2=0.009)
        # bench seat (oak) with an upholstered cushion; a shoe shelf below (the boot bay has none)
        b.lo_hi(f"Seat{i}", (xa, yf + 0.02, bz - st), (xb, yb - 0.015, bz), oak, bevel=0.004)
        cw, cd = bw - 0.04, (yb - 0.1) - (yf + 0.04)
        cy = ((yb - 0.1) + (yf + 0.04)) / 2
        soft(b, f"Cushion{i}", mc.bench_cushion(cw, cd), [oat, oat], (xc, cy, bz), sharp=1.3)
        if out["throw"] == i:
            soft(b, f"Throw{i}", xf(mc.folded_throw(), rot_z=0.07), [M["wool"]], (xb - 0.27, cy + 0.02, bz + 0.068),
                 tile=0.5, sharp=1.3)
        shelf = under != "boots"
        if shelf:
            b.lo_hi(f"Shelf{i}", (xa, yf + 0.04, 0.2), (xb, yb - 0.015, 0.2 + 0.025), oak, bevel=0.003)
        sy = yf + 0.24
        if under == "boots":
            boots(b, M, f"Boots{i}", xa + 0.27, sy + 0.01, ph)
            basket(b, M, f"Basket{i}", xb - 0.25, sy + 0.04, ph, rot=0.08)
        elif under == "trainers":
            shoe_pair(b, M, f"Trainers{i}", "trainer", xa + 0.3, sy, 0.225, rot=0.05, colour="white")
        elif under == "trainers_navy":
            shoe_pair(b, M, f"Trainers{i}", "trainer", xb - 0.32, sy, 0.225, rot=-0.08, colour="navy")
        elif under == "loafers":
            shoe_pair(b, M, f"Loafers{i}", "loafer", xc + 0.12, sy + 0.02, ph, rot=-0.1, colour="cognac")
        # the hook rail: a coat bay takes the next coat outfit, the others something lighter
        if p["coats"][i % len(p["coats"])]:
            items = out["coat"][n_coat % len(out["coat"])]
            n_coat += 1
        else:
            items = out["light"][n_light % len(out["light"])]
            n_light += 1
        for k, item in items:
            hang(b, M, item, f"{item.title().replace('_', '')}{i}", hooks[k], y_tip, rz, wall, seed=i)
        # cupboard above: cream door, bronze pull; dark gap behind
        b.lo_hi(f"Cup{i}_Back", (xa, yb - 0.3, p["cup_z0"]), (xb, yb - 0.015, H - 0.04), grd, bevel=0)
        b.lo_hi(f"Cup{i}_Door", (xa + 0.003, yf + 0.18, p["cup_z0"] + 0.003), (xb - 0.003, yf + 0.2, H - 0.043), cream, bevel=0.002)
        b.box(f"Cup{i}_Pull", (0.16, 0.014, 0.014), (xc, yf + 0.18 - 0.007, p["cup_z0"] + 0.06), bronze, bevel=0.0015, seg=1)
        # a name plate: slim bronze label under each cupboard
        b.box(f"Label{i}", (0.1, 0.004, 0.025), (xc, yf + 0.18 - 0.002, p["cup_z0"] - 0.025), bronze, bevel=0, seg=1, tile=0.25)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
