"""Cove ledge for hidden indirect light: a slim wall-mounted valance in dark bronze (a
shelf board on a wall cleat with an upturned front lip), run along a wall just below the
ceiling. The LED behind the lip is an `area` light in the room's LIGHTS (on the ledge,
aimed at the ceiling or down the wall); the ledge is its visible reason. `up=False` turns
the profile over (lip hanging down, light aimed down the wall: a valance wash). A thin
emissive LED tape behind the lip follows the room's light switch (ix_common FIXTURES).

Origin: on the wall plane, at the centre of the ledge's underside (up) / top (down);
the ledge stands out toward -Y. Length runs along X. Variants: light_g_cove_<len>.py.
Units are metres.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import ix_common  # noqa: E402  (react definitions, prompts/interactivity.md)

importlib.reload(common)
importlib.reload(materials)
importlib.reload(ix_common)

NAME = "LightGCove"

P = dict(
    name=NAME,
    length=4.0,
    depth=0.16,           # wall to the front of the lip
    board=0.022,          # shelf thickness
    lip=0.10,             # lip height above the board
    lip_t=0.018,
    cleat=0.05,           # wall cleat height (under the board, at the wall)
    up=True,
    finish="bronze",      # "bronze" | "black"
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    mat = materials.bronze() if p["finish"] == "bronze" else materials.black_metal()
    L, D, bt, lh, lt, ch = p["length"], p["depth"], p["board"], p["lip"], p["lip_t"], p["cleat"]
    sg = 1.0 if p["up"] else -1.0

    def box(name, size, centre, bevel=0.003):
        ob = common.mesh_object(f"{n}_{name}", common.box_bmesh(size), col, mat, root, smooth=False)
        ob.location = centre
        if bevel:
            common.add_bevel(ob, bevel, segments=1)
        common.box_uv(ob, 0.5)
        return ob

    # board (its underside at z = 0 for an up-cove), lip at the front, cleat at the wall
    box("Board_NoCollide", (L, D - lt, bt), (0, -(D - lt) / 2, sg * bt / 2))
    box("Lip_NoCollide", (L, lt, bt + lh), (0, -D + lt / 2, sg * (bt + lh) / 2))
    box("Cleat_NoCollide", (L, 0.02, ch), (0, -0.01, -sg * ch / 2 + sg * 0.0), bevel=0.002)
    # the LED tape itself, on the board just behind the lip (hidden from below by the lip;
    # seen from the upper galleries): it glows with the room's light switch
    led = common.mesh_object(f"{n}_LED_NoCollide", common.box_bmesh((L - 0.06, 0.012, 0.004)), col,
                             materials.emissive("M_LED_Warm", (1.0, 0.8, 0.55), 4.0), root, smooth=False)
    led.location = (0, -(D - lt) + 0.012, sg * (bt + 0.002))
    ix_common.tag_emissive(root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
