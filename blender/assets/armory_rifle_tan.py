"""armory_rifle in flat dark earth (tan stock and handguard): set dressing for the safe wall."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import armory_rifle  # noqa: E402

importlib.reload(armory_rifle)
common = armory_rifle.common

NAME = "ArmoryRifleTan"
P = dict(name=NAME, variant="tan")


def build(**overrides):
    return armory_rifle.build(**{**P, **overrides})
