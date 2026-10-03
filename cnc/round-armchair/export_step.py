"""Assembled STEP of the round armchair frame (build123d, exact cut geometry).

Every part is its flattened cut profile (outline minus openings/mortises)
extruded to the board thickness and placed where it sits in the chair, so
the STEP is the DXF in 3D, not a separate model. Units: mm.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))  # shared code, lower priority

from build123d import Compound, Face, Location, Wire, export_step, extrude

import chair_geometry as C
import sofa_layout as L


def solid(loops, dx=0.0, dy=0.0):
    wires = [Wire.make_polygon([(x + dx, y + dy, 0.0)
                                for x, y in L.flatten_loop(l, 12)], close=True)
             for l in loops]
    face = Face(wires[0], wires[1:])
    return extrude(face, amount=C.T)


def radial(sol, theta):
    """Plate drawn in (r, z) -> vertical radial plane at plan angle theta,
    centred on that plane."""
    return (Location((0, 0, 0), (0, 0, 1), theta)
            * Location((0, 0, 0), (1, 0, 0), 90)
            * Location((0, 0, -C.T / 2))) * sol


def assembly():
    items = []
    for p in C.build_parts():
        if p.key in ("BASE", "SEAT") or p.key.startswith("BAND"):
            z = {"BASE": 0.0, "SEAT": C.SEAT_Z}.get(p.key, C.BAND_Z)
            s = Location((0, 0, z)) * solid(p.loops)
            s.label = f"P{p.num:02d} {p.label}"
            items.append(s)
        else:
            angs = ([a for a in C.BODY_ANGLES if C._type_angle(a) == C._type_angle(p.angles[0])]
                    if p.key.startswith("BODY") else list(p.angles))
            for i, a in enumerate(angs, 1):
                if p.key.startswith("BODY"):
                    s = radial(solid(p.loops, dx=C.body_in(a)), a)
                else:
                    s = radial(solid(p.loops, dx=C.back_in(a) - C.SHOULDER, dy=C.SEAT_Z), a)
                s.label = f"P{p.num:02d} {p.label} {i}/{len(angs)} @{a:g}deg"
                items.append(s)
    return items


def main(out: Path) -> Compound:
    items = assembly()
    comp = Compound(label="round-tub-armchair", children=items)
    export_step(comp, str(out))
    print(f"wrote {out}: {len(items)} solids")
    return comp


if __name__ == "__main__":
    out = HERE / "out" / "round-armchair.step"
    out.parent.mkdir(exist_ok=True)
    main(out)
