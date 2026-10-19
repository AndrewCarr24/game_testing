"""Halo pendant: a 1.2 m ring of brushed bronze with softly rounded edges, hung level on
three fine bronze cables from a round ceiling canopy. An opal diffuser band runs round its
underside (light down onto the seating below) and a narrower one round its top (an uplight
halo on the ceiling). A sculptural light over a lounge group: big enough to read as the
room's centrepiece, and hung high so it never meets the player's head.

Origin: the centre of the ring's underside (z = 0). `ceiling` is the distance from the origin
up to the ceiling: place it at z = ceiling height - P["ceiling"] (a 3.8 m room: z = 2.4).
The room module puts an `area` light under the ring and one over it. Units are metres.
"""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitchen_lib as L  # noqa: E402

importlib.reload(L)
common, materials = L.common, L.materials

NAME = "LightUHalo"

P = dict(
    name=NAME,
    radius=0.6,          # ring centreline
    width=0.06,          # radial width of the ring section
    height=0.045,
    ceiling=1.4,         # origin -> ceiling
    cables=3,
    segs=40,
    emission=5.0,
)


def build(**overrides):
    p = {**P, **overrides}
    b = L.Builder(p["name"])
    bronze = materials.bronze()
    glow = materials.emissive("M_LightU_Opal", (1.0, 0.84, 0.64), p["emission"])
    R, w, h, s = p["radius"], p["width"], p["height"], p["segs"]
    r0, r1 = R - w / 2, R + w / 2
    c = 0.012                       # corner round-over
    t = 0.005                       # the diffusers stand this far proud of the bronze

    # bronze ring: closed chamfered-rectangle section, revolved (outer face, top, inner face, bottom)
    sec = [(r0 + c, t), (r1 - c, t), (r1, t + c), (r1, t + h - c), (r1 - c, t + h), (r0 + c, t + h), (r0, t + h - c),
           (r0, t + c)]                # chamfered corners: they catch the light like a round-over
    b.lathe("Ring_NoCollide", sec, bronze, segs=s, sharp=60, uv_tile=0.3)
    # opal bands: flat annuli just proud of the bottom and the top
    rb0, rb1 = r0 + c * 0.7, r1 - c * 0.7
    down = b.lathe("Diffuser_NoCollide", [(rb1, 0.0), (rb0, 0.0), (rb0, t + 0.002), (rb1, t + 0.002)], glow, segs=s, sharp=30,
                   uv_tile=0)
    ru0, ru1 = R - w * 0.18, R + w * 0.18
    b.lathe("Uplight_NoCollide", [(ru0, t + h - 0.002), (ru1, t + h - 0.002), (ru1, t + h + 0.004), (ru0, t + h + 0.004)], glow,
            segs=s, sharp=30, uv_tile=0)

    # cables from three points on the ring's top up to a single canopy (a shallow cone of cables)
    top = p["ceiling"]
    zt = t + h + 0.004
    for i in range(p["cables"]):
        a = math.pi / 2 + 2 * math.pi * i / p["cables"]
        x, y = R * math.cos(a), R * math.sin(a)
        b.tube(f"Cable{i}_Piping", [(x, y, zt), (0.06 * math.cos(a), 0.06 * math.sin(a), top - 0.03)], 0.0018, bronze,
               closed=False, res=1)
        b.lathe(f"Grip{i}_Piping", [(0.0, zt - 0.003), (0.007, zt - 0.003), (0.007, zt + 0.014), (0.0035, zt + 0.02),
                                    (0.0, zt + 0.02)], bronze, loc=(x, y, 0), segs=8, uv_tile=0.3)
    b.lathe("Canopy", [(0.0, top - 0.035), (0.075, top - 0.035), (0.09, top - 0.02), (0.09, top + 0.002),
                       (0.0, top + 0.002)], bronze, segs=24, sharp=30, uv_tile=0.3)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
