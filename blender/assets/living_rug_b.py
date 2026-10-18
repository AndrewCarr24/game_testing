"""Second great-room rug: dusty ink-blue field, oat border (living_rug variant)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import living_rug  # noqa: E402

importlib.reload(living_rug)

NAME = "LivingRugB"
P = dict(name=NAME, size=(4.6, 3.6), border=0.10,
         field_name="M_Fabric_RugInk", field=(0.060, 0.080, 0.110),
         border_name="M_Fabric_RugOat", border_c=(0.40, 0.355, 0.285))


def build(**overrides):
    return living_rug.build(**{**P, **overrides})
