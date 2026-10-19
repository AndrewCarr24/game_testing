"""Ink-blue variant of living_sofa (shorter, oat pillows)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import living_sofa  # noqa: E402

importlib.reload(living_sofa)

NAME = "LivingSofaInk"
P = dict(name=NAME, width=2.3, fabric_name="M_Fabric_InkVelvet", fabric=(0.014, 0.022, 0.042),
         pillow_name="M_Fabric_Oat", pillow=(0.50, 0.44, 0.35), leg="bronze",
         throw=("M_Fabric_Oat", (0.50, 0.44, 0.35)))


def build(**overrides):
    return living_sofa.build(**{**P, **overrides})
