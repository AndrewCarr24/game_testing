"""Desk chair: the lounge chair generator with desk-height proportions and
black leather. Everything structural is recomputed from these overrides."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lounge_chair  # noqa: E402

importlib.reload(lounge_chair)
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


def build(**overrides):
    return lounge_chair.build(**{**P, **overrides})


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
