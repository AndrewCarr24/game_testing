"""Deep upholstered armchair (a one-seat living_sofa module): squared padded arms, a loose
seat and back cushion on a recessed plinth. Faces -Y; origin is the floor centre.
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import living_sofa  # noqa: E402

importlib.reload(living_sofa)

NAME = "LivingArmchair"
P = dict(name=NAME, width=0.98, depth=0.96, pillows=0, fabric_name="M_Fabric_Oat", fabric=(0.50, 0.44, 0.35),
         arm_w=0.17, back_tilt_deg=14.0, leg="bronze")


def build(**overrides):
    return living_sofa.build(**{**P, **overrides})
