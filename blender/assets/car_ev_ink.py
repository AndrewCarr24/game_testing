"""Second garage car: car_ev in ink blue."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import car_ev  # noqa: E402

importlib.reload(car_ev)
common = car_ev.common

NAME = "CarEV_Ink"
P = dict(name=NAME, paint="ink")


def build(**overrides):
    return car_ev.build(**{**P, **overrides})
