"""Garage door (8.5 x 3.2 m): a canopy up-and-over door in charcoal powder-coated steel,
four horizontal flush sections with shadow grooves, a slim bronze pull, black steel jamb and
head trims. Placed by plan.py's garage opening (door="ix_garage_door", swing="garage").

Interactivity: `<n>_Leaf` (an empty on the pivot line, 2.3 m up) carries a react on signal
"garage_door": on = rotate -90 degrees about x, so the bottom swings out and up and the leaf
ends level at 2.3 m, a 2.3 m canopy outside and 0.9 m inside under the 4.2 m ceiling (clear
of the cars). The switch is an ix_switch_garage by the mudroom door.

Origin: floor centre of the opening on the door line; the outside faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_common  # noqa: E402
import ix_blind  # noqa: E402  (boxes_bmesh)

importlib.reload(ix_common)
importlib.reload(ix_blind)
common, materials = ix_common.common, ix_common.materials

NAME = "IX_GarageDoor"
P = dict(name=NAME, opening=(8.5, 3.2), pivot_z=2.3, sections=4, t=0.045, signal="garage_door")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    skin = common.pbr_material("M_GarageDoor", (0.18, 0.18, 0.19), roughness=0.4, metallic=0.6)
    black = materials.black_metal()
    bronze = materials.bronze()
    W, H = p["opening"]
    t, g = p["t"], 0.006
    leaf = common.empty(f"{n}_Leaf", col, (0, 0, p["pivot_z"]))
    leaf.parent = root
    # collide: the leaf is solid (a moving collider that follows it: closed, a wall; open, a canopy overhead)
    leaf["react"] = {"signal": p["signal"], "on": {"rotate": {"axis": "x", "angle": -90}}, "duration": 4.5, "collide": True}
    lw, lh = W - 2 * g, H - g - 0.01
    sh = lh / p["sections"]
    secs = [((0, 0, 0.01 + (k + 0.5) * sh - p["pivot_z"]), (lw, t, sh - 0.012)) for k in range(p["sections"])]
    panel = common.mesh_object(f"{n}_Leaf_Panels", ix_blind.boxes_bmesh(secs), col, skin, leaf, smooth=False)
    common.add_bevel(panel, 0.004, segments=1)
    grooves = [((0, t / 2 - 0.006, 0.01 + k * sh - p["pivot_z"]), (lw - 0.02, 0.012, 0.014))
               for k in range(1, p["sections"])]
    common.mesh_object(f"{n}_Leaf_Grooves", ix_blind.boxes_bmesh(grooves), col, black, leaf, smooth=False)
    pull = common.mesh_object(f"{n}_Leaf_Pull", common.box_bmesh((0.6, 0.03, 0.025)), col, bronze, leaf)
    pull.location = (0, -t / 2 - 0.015, 0.01 + 0.5 * sh - p["pivot_z"] + 0.15)
    common.add_bevel(pull, 0.005, segments=2)
    # static trims round the opening (inside face), so the jambs read finished
    tr = 0.06
    trims = [((-W / 2 - tr / 2, t / 2 + 0.02, H / 2), (tr, 0.04, H)), ((W / 2 + tr / 2, t / 2 + 0.02, H / 2), (tr, 0.04, H)),
             ((0, t / 2 + 0.02, H + tr / 2), (W + 2 * tr, 0.04, tr))]
    trim = common.mesh_object(f"{n}_Trim_NoCollide", ix_blind.boxes_bmesh(trims), col, black, root, smooth=False)
    common.add_bevel(trim, 0.003, segments=1)
    return ix_common.finish(root)
