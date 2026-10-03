"""3D assembly of the cone from the exact cut profiles (build123d).

Every flat part is its DXF profile (outline minus mortises) extruded to the
board thickness and placed where it sits. The kerfed shell is modelled as the
full conical wall (outer face R(z), inner face R_in(z)): the kerf pockets only
remove material from its back, so this is the conservative case for clashes.

Checks
* no two parts interpenetrate (tabs clear their mortises, the half-laps
  clear each other, the core and formers clear the shell);
* every part bears on what should carry it (contact, not floating);
* overall size.
Writes out/cone.step.
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))  # shared code, lower priority

from build123d import (Compound, Face, Location, Plane, Polyline, Wire,
                       export_step, extrude, make_face, revolve, Axis)

import sofa_layout as L
import table_geometry as T

TOUCH = 0.01          # mm: closer than this counts as bearing contact
CLASH = 1e-3          # mm3: more overlap than this is a clash
RESULTS = []


def check(section, ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    RESULTS.append((section, bool(ok), msg))


def loop_wire(loop):
    """Exact wire: straight segments stay lines, bulges become true arcs."""
    import math
    from build123d import Line, ThreePointArc
    edges = []
    n = len(loop)
    for i in range(n):
        x0, y0, bl = loop[i]
        x1, y1, _ = loop[(i + 1) % n]
        if abs(bl) < 1e-12:
            if math.hypot(x1 - x0, y1 - y0) > 1e-9:
                edges.append(Line((x0, y0), (x1, y1)))
            continue
        # arc midpoint: chord midpoint pushed out by the sagitta
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        dx, dy = x1 - x0, y1 - y0
        sag = bl * math.hypot(dx, dy) / 2
        nx, ny = dy / math.hypot(dx, dy), -dx / math.hypot(dx, dy)
        edges.append(ThreePointArc((x0, y0), (cx + nx * sag, cy + ny * sag), (x1, y1)))
    return Wire(edges)


def flat(loops, th):
    wires = [loop_wire(l) for l in loops]
    return extrude(Face(wires[0], wires[1:]), amount=th)


def plate(part):
    """Core plate drawn in (x, z) -> vertical plane at plan angle phi,
    centred on that plane."""
    sol = flat(part.loops, T.T_BOARD)
    return (Location((0, 0, 0), (0, 0, 1), part.meta["phi"])
            * Location((0, 0, 0), (1, 0, 0), 90)
            * Location((0, 0, -T.T_BOARD / 2))) * sol


def wall(za, zb):
    prof = Polyline((T.R_in(za), 0, za), (T.R(za), 0, za), (T.R(zb), 0, zb),
                    (T.R_in(zb), 0, zb), close=True)
    return revolve(make_face(prof), Axis.Z, 360)


def assembly():
    parts = {p.key: p for p in T.build_parts()}
    items = []
    for k in [k for k in ("SHELL1", "SHELL2") if k in parts]:
        m = parts[k].meta
        s = wall(m["za"], m["zb"])
        s.label = parts[k].label
        items.append(s)
    for k in [k for k in ("FBASE", "FJLO", "FJUP", "FTOP") if k in parts]:
        p = parts[k]
        s = Location((0, 0, p.meta["z0"])) * flat(p.loops, T.T_BOARD)
        s.label = p.label
        items.append(s)
    if "COLLAR" in parts:
        c = parts["COLLAR"]
        z_rest = (T.R_BOT - c.meta["r"]) / (T.R_BOT - T.R_TOP) * T.H_CONE
        s = Location((0, 0, z_rest)) * flat(c.loops, T.T_BOARD)
        s.label = c.label
        items.append(s)
    for p in parts.values():
        if p.key.startswith("CORE"):
            s = plate(p)
            s.label = p.label
            items.append(s)
    return items


def main():
    items = assembly()
    by = {s.label: s for s in items}
    boxes = [s.bounding_box() for s in items]

    def overlap(a, b):
        return (a.min.X < b.max.X and b.min.X < a.max.X and a.min.Y < b.max.Y
                and b.min.Y < a.max.Y and a.min.Z < b.max.Z and b.min.Z < a.max.Z)

    sec = "[3D-1] interference"
    print(f"\n{sec}")
    pairs = [(i, j) for i, j in itertools.combinations(range(len(items)), 2)
             if overlap(boxes[i], boxes[j])]
    clashes = []
    for i, j in pairs:
        v = (items[i] & items[j]).volume
        if v > CLASH:
            clashes.append(f"{items[i].label} x {items[j].label} ({v:.1f} mm3)")
    check(sec, not clashes, f"{len(pairs)} neighbouring pairs, {len(clashes)} interpenetrate"
                            + (": " + "; ".join(clashes) if clashes else ""))

    sec = "[3D-2] load path: every part bears on what carries it"
    print(f"\n{sec}")
    d = lambda a, b: by[a].distance_to(by[b])
    plan, levels, below, above = T.former_plan()
    rows = []
    for lv in range(1, len(levels) + 1):
        for t in "AB":
            rows += [(f"CORE-{lv}{t}", plan[below[lv]][0]), (f"CORE-{lv}{t}", plan[above[lv]][0])]
        rows.append((f"CORE-{lv}A", f"CORE-{lv}B"))
    if "FORMER-JOINT-UP" in by:
        rows.append(("FORMER-JOINT-UP", "FORMER-JOINT-LO"))
    if "COLLAR" in by:
        rows.append(("COLLAR", "SHELL-LOW"))
    for a, b in rows:
        dist = d(a, b)
        check(sec, dist <= TOUCH, f"{a} bears on {b} (gap {dist:.3f} mm)")
    one = "SHELL" in by
    for f, sh in [(f, s) for f, s in (("FORMER-BASE", "SHELL" if one else "SHELL-LOW"),
                  ("FORMER-JOINT-LO", "SHELL" if one else "SHELL-LOW"),
                  ("FORMER-JOINT-UP", "SHELL" if one else "SHELL-UP"),
                  ("FORMER-TOP", "SHELL" if one else "SHELL-UP")) if f in by]:
        dist = d(f, sh)
        check(sec, dist <= T.FIT + 0.01, f"{f} holds {sh}: {dist:.2f} mm glue line")

    sec = "[3D-3] overall size"
    print(f"\n{sec}")
    bb = Compound(children=items).bounding_box()
    check(sec, abs(bb.min.Z) < 1e-6 and abs(bb.max.Z - T.H_CONE) < 1e-6
          and abs(bb.size.X - 2 * T.R_BOT) < 1.0,
          f"cone {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm "
          f", standing on z = 0")

    export_step(Compound(children=items), str(HERE / "out" / "cone.step"))
    fails = sum(not r[1] for r in RESULTS)
    print(f"\n3D FAILURES: {fails}")
    return RESULTS


if __name__ == "__main__":
    raise SystemExit(1 if any(not r[1] for r in main()) else 0)
