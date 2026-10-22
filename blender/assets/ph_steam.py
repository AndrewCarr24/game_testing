"""The steam room's fittings (the bathhouse): two-tier benches clad in the room's dark teal mosaic
along both long walls, the steam itself, and a hiding place in it.

  Steam   soft vapour cards hanging through the room (fx "steam", viewer/water_fx.js) on an
          empty whose react blocks sight while the steam is on (block_sight; its box is the room):
          nobody sees into, out of or across a steam room in use. Signal `steam` (the level:
          `ph_steam`, on from the start); not electric
  Hide    "Sit in the steam": on the west bench's lower tier, cover open, looking across the aisle
          at the doors (interact `hide`, viewer/hiding.js)

Fits the steam room inside (bathhouse_plan.STEAM: 3.2 x 5.7 m, 2.6 m high; the doors at the
ends of a middle aisle x -0.6..0.5): benches run 3.2 m, clear of the doors' swings.
Origin: the room's interior centre on its floor."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ph_common as pc  # noqa: E402

importlib.reload(pc)
common = pc.common
sys.path.insert(0, HERE)
import ix_common as ix  # noqa: E402

importlib.reload(ix)

NAME = "PHSteam"
P = dict(name=NAME, room=(3.2, 5.7, 2.6), length=3.2, lower=(0.8, 0.45), upper=(0.42, 0.9), signal="steam")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = pc.start(n)
    tile = pc.mosaic()
    RW, RD, RH = p["room"]
    L = p["length"]
    (ld, lh), (ud, uh) = p["lower"], p["upper"]
    for side, sx in (("W", -1), ("E", 1)):
        wall = sx * RW / 2
        pc.box(f"{n}_Bench{side}_Lower", (min(wall, wall - sx * ld), -L / 2, 0), (max(wall, wall - sx * ld), L / 2, lh), tile, col,
               root, uv_tile=0.5, bevel=0.01)
        pc.box(f"{n}_Bench{side}_Upper", (min(wall, wall - sx * ud), -L / 2, lh), (max(wall, wall - sx * ud), L / 2, uh), tile, col,
               root, uv_tile=0.5, bevel=0.01)
    steam = common.empty(f"{n}_Steam", col, (0, 0, 0))
    steam.parent = root
    # (a still "slide": block_sight wants a react, and a show/hide one would copy the cards' shader
    # materials, freezing their time; the steam is always on)
    steam["react"] = {"signal": p["signal"], "on": {"slide": {"axis": "y", "distance": 0.0}}, "motor": False,
                      "power": False, "block_sight": True, "duration": 0.1}
    for i, y in enumerate((-2.1, -0.75, 0.6, 1.95)):
        pc.no_bake_light(pc.card(f"{n}_NoCollide_Vapour{i}", RW - 0.2, RH - 0.25, pc.fx_material(), col, steam,
                                 at=(0, y, (RH - 0.25) / 2 + 0.05), facing="-y" if i % 2 else "+y", fx="steam",
                                 aspect=(RW - 0.2) / (RH - 0.25), strength=0.075, seed=float(i), color=[0.9, 0.95, 1.0]))
    # sitting on the west bench, the back to the wall, looking across at the aisle
    ix.hide_spot(root, col, n, eye=(-RW / 2 + 0.38, 0.0, lh + 0.78), exit=[(0.0, 0.0, 0.0), (0.0, 0.8, 0.0)],
                 prompt="Sit in the steam", leave="Get up", cover="open", facing=(1, 0, 0), pitch=-4.0,
                 look={"yaw": 70, "pitch": 30})
    return pc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
