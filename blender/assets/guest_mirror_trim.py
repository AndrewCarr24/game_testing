"""Mirror-wall trim for the gym: slim black mullions every 2 m dividing the
mirror into panels, a black skirting rail at the foot, and an oak stretching barre
on brass brackets at 1.0 m. 12.0 m long (along X). The origin is on the wall plane at
the floor, the trim stands out of the wall toward -Y at rotation 0; place it with
rotation 180 on the south wall (the wall at its back is at +Y here)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_mats  # noqa: E402

importlib.reload(guest_mats)
common = guest_mats.common

NAME = "GuestMirrorTrim"

P = dict(name=NAME, length=12.0, height=3.78, panels=6, barre_z=1.0)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    black, brass, oak = guest_mats.black(), guest_mats.brass(), guest_mats.oak()
    own = (col, root, n)
    A = guest_mats.add
    L, H, np_ = p["length"], p["height"], p["panels"]
    # wall is at y = 0 behind the trim (the trim stands toward -Y)
    A(own, "Skirt", common.box_bmesh((L, 0.025, 0.09)), black, (0, -0.0125, 0.045), 0.003)
    for i in range(np_ + 1):
        x = -L / 2 + i * L / np_
        x = max(-L / 2 + 0.02, min(L / 2 - 0.02, x))
        A(own, f"Mullion{i}", common.box_bmesh((0.04, 0.022, H)), black, (x, -0.011, H / 2), 0.003)
    # barre: oak round bar + brass brackets at the mullions
    bz = p["barre_z"]
    bar = common.mesh_object(f"{n}_Barre", guest_mats.cyl_bmesh(0.022, L - 0.1, seg=16, axis="x"), col, oak, root)
    bar.location = (0, -0.115, bz)
    common.box_uv(bar, 0.5)
    for i in range(np_ + 1):
        x = -L / 2 + i * L / np_
        x = max(-L / 2 + 0.2, min(L / 2 - 0.2, x)) if i in (0, np_) else x
        A(own, f"Bracket{i}", common.box_bmesh((0.03, 0.10, 0.012)), brass, (x + (0.0 if 0 < i < np_ else 0.0), -0.065, bz - 0.022 - 0.006), 0.002)
        A(own, f"BracketPlate{i}", common.box_bmesh((0.03, 0.006, 0.1)), brass, (x, -0.027, bz - 0.01), 0.002)
    parts = guest_mats.consolidate(root, max_dim=99)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
