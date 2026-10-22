"""The cold plunge's secret (the bathhouse; design/grounds/pool_house.md): everything in it that moves,
on one signal (`plunge`; the level names it `ph_plunge`), with no key:

  Water    the plunge's water, a box filling the basin to 8 cm under the floor; on: it drains
           (slides 2.5 m down, out of sight under the basin floor, 4 s); off: it comes back,
           after the slab has risen (delayOff)
  Blocker  nobody walks into the full plunge: a moving collider over the basin, 1 m above the
           floor (its box is spanned by two 1 mm triangles hidden in the stone); drained, it's
           gone under the floor and the steps can be walked
  Slab     the stone panel in the plunge's south wall, from the basin floor (= the secret
           stair's landing, z -1.2) to 1 m above the room's floor: once the water is gone it
           sinks into the floor (delay), opening the way down; it rises before the water returns

The switches that drive it are ph_valve (one by the plunge, one at the stair's head). Origin: the
plunge's centre (bathhouse_plan.PLUNGE: 2.7 x 2.2 m inside, world x 40.0, y 41.75) at the floor;
the slab stands on the basin's south wall line (world y 40.5, local y -1.25)."""
import importlib
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ph_common as pc  # noqa: E402

importlib.reload(pc)
common = pc.common

NAME = "PHPlunge"
P = dict(name=NAME, size=(2.7, 2.2), floor=-1.2, water_z=-0.08, wall_y=-1.25, slab=(1.48, 0.24), slab_top=1.0,
         drain=2.5, sink=2.25, signal="plunge")


def react(signal, distance, duration, **extra):
    d = {"signal": signal, "on": {"slide": {"axis": "y", "distance": -distance}}, "duration": duration,
         "motor": False, "power": False}
    d.update(extra)
    return d


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = pc.start(n)
    W, D = p["size"]
    fl, wz = p["floor"], p["water_z"]
    sig = p["signal"]

    water = common.empty(f"{n}_Water", col)
    water.parent = root
    water["react"] = react(sig, p["drain"], 4.0, delayOff=3.4)
    wbox = pc.box(f"{n}_NoCollide_WaterBox", (-W / 2 + 0.01, -D / 2 + 0.01, fl + 0.02), (W / 2 - 0.01, D / 2 - 0.01, wz),
                  pc.water("M_PH_WaterCold", (0.008, 0.035, 0.04), 0.55), col, water)
    # only the top is ever seen (and the drained box sinks out of sight): keep just it
    me = wbox.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z < 0.9], context="FACES")
    uv = bm.loops.layers.uv.new("UVMap") if not bm.loops.layers.uv else bm.loops.layers.uv[0]
    for f in bm.faces:
        for lp in f.loops:
            lp[uv].uv = (lp.vert.co.x, lp.vert.co.y)
    bm.to_mesh(me)
    bm.free()
    wbox["fx"] = "water"
    wbox["tile"] = 1.2
    pc.no_bake_light(wbox)

    blocker = common.empty(f"{n}_Blocker", col)
    blocker.parent = root
    blocker["react"] = react(sig, 2.6, 4.0, collide=True)
    bm = bmesh.new()
    for c in ((-W / 2 - 0.05, -D / 2 - 0.05, fl), (W / 2 + 0.05, D / 2 + 0.05, 1.0)):
        x, y, z = c
        vs = [bm.verts.new((x, y, z)), bm.verts.new((x + 0.001, y, z)), bm.verts.new((x, y + 0.001, z))]
        bm.faces.new(vs)
    common.mesh_object(f"{n}_Blocker_Span", bm, col, common.pbr_material("M_PH_Hidden", (0.1, 0.12, 0.11), roughness=0.9),
                       blocker, smooth=False)

    slab = common.empty(f"{n}_Slab", col, (0, p["wall_y"], 0))
    slab.parent = root
    slab["react"] = react(sig, p["sink"], 3.5, delay=3.2, collide=True)
    sw, st = p["slab"]
    # the slab: the plunge's stone under the waterline, the cold room's dark coursed stone over it
    # (its courses don't quite meet the wall's: the only tell)
    stone_dark = common.pbr_material("M_PH_StoneDark", (0.1, 0.105, 0.1), roughness=0.8)
    common.set_base_color_map(stone_dark, pc.textures.load(pc.ph_textures.coursed_stone(
        name="T_PH_StoneDark_BaseColor", seed=72, dark=True)))
    lower = pc.box(f"{n}_Slab_Lower", (-sw / 2, -st / 2, fl + 0.004), (sw / 2, st / 2, 0.0), pc.pool_stone(), col, slab,
                   uv_tile=1.2)
    upper = pc.box(f"{n}_Slab_Upper", (-sw / 2, -st / 2, 0.0), (sw / 2, st / 2, p["slab_top"] - 0.004), stone_dark, col,
                   slab, uv_tile=2.0)
    for o in (lower, upper):
        o.data.uv_layers.active_index = 0
    return pc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
