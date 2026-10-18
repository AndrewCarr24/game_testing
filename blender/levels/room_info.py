"""Describe a room for whoever dresses it, in room-local coordinates.

  python3 blender/levels/room_info.py kitchen

(0, 0) is the room's interior centre at floor level; +x east, +y north. Lists the
interior size, ceiling height, and every door, opening, window and balustrade on its
walls, with positions along each wall, so furniture can be laid out without blocking them.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan  # noqa: E402


def info(room):
    r = plan.ROOMS[room]
    x0, y0, x1, y1 = r["rect"]
    kind = r.get("kind", "room")
    T = 0 if kind == "courtyard" else plan.T
    ix0, iy0, ix1, iy1 = x0 + T, y0 + T, x1 - T, y1 - T
    cx, cy = (ix0 + ix1) / 2, (iy0 + iy1) / 2
    z0 = plan.LEVEL_Z[r["level"]]
    h = plan.TOP - z0 if (r.get("double") or kind == "courtyard") else plan.HEIGHT[r["level"]]
    lines = [f"ROOM {room}: {kind}, level {r['level']} ({'ground' if r['level'] == 0 else 'upper'})"
             + (", double height" if r.get("double") else ""),
             f"  interior {ix1 - ix0:.2f} m (x, west-east) by {iy1 - iy0:.2f} m (y, south-north), "
             f"ceiling {h:.2f} m" + (" (open to the sky)" if kind == "courtyard" else ""),
             f"  local x from {-(ix1 - ix0) / 2:.2f} to {(ix1 - ix0) / 2:.2f}, y from {-(iy1 - iy0) / 2:.2f} to "
             f"{(iy1 - iy0) / 2:.2f}; walls at those limits",
             "  on its walls (positions are local; heights from this room's floor):"]
    walls = {"N": ("x", y1), "S": ("x", y0), "E": ("y", x1), "W": ("y", x0)}
    found = False
    for side, (axis, line) in walls.items():
        span = (x0, x1) if axis == "x" else (y0, y1)
        for c in plan.CUTS:
            if c["axis"] != axis or abs(c["line"] - line) > 1e-6:
                continue
            a0, a1 = max(span[0], c["span"][0]), min(span[1], c["span"][1])
            cz0, cz1 = max(z0, c["z"][0]), min(z0 + h, c["z"][1])
            if a1 - a0 < 1e-3 or cz1 - cz0 < 1e-3:
                continue
            off = cx if axis == "x" else cy
            what = c["kind"] + (f" with a door ({c['door']}" + (", locked: " + c["lock"] if c.get("lock") else "") + ")"
                                if c.get("door") else "")
            lines.append(f"    {side} wall: {what} from {a0 - off:+.2f} to {a1 - off:+.2f} "
                         f"(along {'x' if axis == 'x' else 'y'}), height {cz0 - z0:.1f}..{cz1 - z0:.1f}")
            found = True
    for a, b in plan.OPEN:
        if room in (a, b):
            lines.append(f"    open (no wall) to {b if room == a else a}")
            found = True
    if not found:
        lines.append("    (no openings)")
    if plan.STAIR["room"] == room:
        s = plan.STAIR
        lines.append(f"  STAIR: floating stair along the north wall, x {s['x'][0] - cx:+.2f}..{s['landing'][1] - cx:+.2f}, "
                     f"y {s['y'][0] - cy:+.2f}..{s['y'][1] - cy:+.2f}; keep that strip (and 1 m in front) clear")
    return "\n".join(lines)


if __name__ == "__main__":
    for name in sys.argv[1:] or plan.ROOMS:
        print(info(name))
        print()
