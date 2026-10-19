"""Desk chair: the lounge chair generator with desk-height proportions and
black leather. Everything structural is recomputed from these overrides.

After lounge_chair.build() the cushions are re-meshed here (lounge_chair itself is
shared with other rooms and stays untouched): per-axis cuts instead of a dense grid,
no faces against the seat board or the back panel, and lighter welts that sit on the
cushion's subdivided edge. The walnut parts get their UVs turned so the grain runs
along each board."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import library_armchair  # noqa: E402  (cushion_bm, welt_points, grain_uv)
import lounge_chair  # noqa: E402

importlib.reload(lounge_chair)
importlib.reload(library_armchair)
common = lounge_chair.common

NAME = "DeskChair"

P = dict(
    name=NAME,
    leather_name="M_Leather_Black",
    leather=(0.018, 0.016, 0.015),
    half_width=0.29,
    runner_front=-0.30,
    runner_back=0.30,
    front_rake=0.03,
    arm_z=0.66,
    low_rail_z=0.34,        # seat top lands at ~0.475 m
    back_rail_z=0.60,
    board_half_width=0.27,
    back_tilt_deg=9.0,
    back_panel_h=0.58,
    cushion_half_width=0.26,
    seat_cushion_t=0.10,
    back_cushion_t=0.09,
    back_cushion_h=0.50,
    arm_cap=(0.06, 0.44, 0.02),
    cushion_edge=0.022,
)

# lounge_chair's crowns, kept so the re-meshed cushions have the same shape
CUSHIONS = {
    "SeatCushion": dict(crown={"+z": 0.016, "-y": 0.008, "+y": 0.002, "+x": 0.006, "-x": 0.006},
                        cuts=(4, 4, 2), drop=("-z",), welts=("+z", "-z"), channels=None),
    "BackCushion": dict(crown={"-y": 0.018, "+y": 0.004, "+z": 0.01, "+x": 0.006, "-x": 0.006},
                        cuts=(4, 2, 7), drop=("+y",), welts=("-y",), channels=("-y", "z", 0.032, (3, 5))),
}


def build(**overrides):
    import bpy
    p = {**P, **overrides}
    root, parts = lounge_chair.build(**p)
    n = p["name"]
    e = p["cushion_edge"]
    col = root.users_collection[0]
    obs = {o.name: o for o in root.children_recursive}
    for key, spec in CUSHIONS.items():
        ob = obs[f"{n}_{key}"]
        corner = max(ob.data.vertices, key=lambda v: v.co.x + v.co.y + v.co.z).co
        size = (2 * corner.x, 2 * corner.y, 2 * corner.z)
        bm = library_armchair.cushion_bm(size, spec["cuts"], e, spec["crown"], spec["drop"],
                                           channels=spec["channels"])
        me = bpy.data.meshes.new(ob.data.name)
        bm.to_mesh(me)
        bm.free()
        for poly in me.polygons:
            poly.use_smooth = True
        me.materials.append(ob.data.materials[0])
        old = ob.data
        ob.data = me
        bpy.data.meshes.remove(old)
        common.box_uv(ob, tile=0.2)
        # welts: drop lounge_chair's dense piping, add lighter loops on the visible faces
        for k in range(2):
            pipe = obs.get(f"{n}_{key}_Piping{k}")
            if pipe is not None:
                me_old = pipe.data
                bpy.data.objects.remove(pipe, do_unlink=True)
                bpy.data.meshes.remove(me_old)
        for i, face in enumerate(spec["welts"]):
            pts = library_armchair.welt_points(size, face, e)
            w = common.tube_object(f"{n}_{key}_Piping{i}", pts, 0.0045, col, ob.data.materials[0], ob.parent,
                                   closed=True, profile_res=1)
            w.location = ob.location
            w.rotation_euler = ob.rotation_euler
            common.box_uv(w, tile=0.2)
    for o in root.children_recursive:
        if o.type == "MESH" and o.data.materials and o.data.materials[0].name == "M_Walnut":
            library_armchair.grain_uv(o)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
