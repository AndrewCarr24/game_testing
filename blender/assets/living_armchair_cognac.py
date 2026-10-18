"""Cognac-velvet variant of living_armchair."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import living_armchair  # noqa: E402

importlib.reload(living_armchair)

NAME = "LivingArmchairCognac"
P = dict(name=NAME, fabric_name="M_Fabric_Cognac", fabric=(0.20, 0.085, 0.035))


def build(**overrides):
    return living_armchair.build(**{**P, **overrides})
