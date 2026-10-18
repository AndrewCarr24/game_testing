"""Den rug: deep charcoal-green field with a narrow walnut-brown border (living_rug variant)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import living_rug  # noqa: E402

importlib.reload(living_rug)

NAME = "LivingRugDen"
P = dict(name=NAME, size=(6.2, 4.6), border=0.12,
         field_name="M_Fabric_RugMoss", field=(0.030, 0.050, 0.040),
         border_name="M_Fabric_RugCocoa", border_c=(0.085, 0.050, 0.030))


def build(**overrides):
    return living_rug.build(**{**P, **overrides})
