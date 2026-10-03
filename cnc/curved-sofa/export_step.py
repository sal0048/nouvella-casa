"""Exact 3D assembly of the curved sofa: every DXF part placed in the sofa.

    python3 export_step.py            -> out/curved-sofa.step + clash check

Plan parts (rails, deck) lie flat at their height. Elevation parts (ribs, arm
panels) stand on the radial line at their angle, x running out from R_IN,
centred on that line. Back stiles stand tangentially on STILE_R, 70 mm wide,
their tenon starting at the seat (BACK-BOT rail) level.
"""

from __future__ import annotations

import itertools
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from build123d import Compound, Face, Plane, Wire, export_step, extrude

import sofa_geometry as G
import sofa_layout as L


def solid(loops, plane, centred=True):
    if centred:
        plane = plane.offset(-G.T / 2)
    wires = [Wire.make_polygon([plane.from_local_coords((x, y, 0.0)) for x, y in L.flatten_loop(l, 24)],
                               close=True) for l in loops]
    return extrude(Face(wires[0], wires[1:]), amount=G.T, dir=plane.z_dir)


def radial_plane(phi):
    a = math.radians(90.0 + phi)
    r = (math.cos(a), math.sin(a), 0.0)
    return Plane(origin=(G.R_IN * r[0], G.R_IN * r[1], 0.0), x_dir=r,
                 z_dir=(r[1], -r[0], 0.0))          # r x Z: local y is up


def stile_plane(phi):
    a = math.radians(90.0 + phi)
    r = (math.cos(a), math.sin(a), 0.0)
    t = (-r[1], r[0], 0.0)
    o = (G.STILE_R * r[0] - t[0] * G.STILE_W / 2, G.STILE_R * r[1] - t[1] * G.STILE_W / 2, G.SEAT_TOP)
    return Plane(origin=o, x_dir=t, z_dir=(t[1], -t[0], 0.0))


def assembly():
    parts = {p.key: p for p in G.build_parts()}
    items = []

    def add(s, p, k, n):
        s.label = f"P{p.num:02d} {p.label} {k}/{n}"
        items.append(s)

    for key in ("BASE_IN", "BASE_OUT"):
        p = parts[key]
        add(solid(p.loops, Plane.XY.offset(G.RAIL_BY_KEY[key].z0), centred=False), p, 1, 1)
    p = parts["RIB"]
    for i, phi in enumerate(G.RIB_ANGLES, 1):
        add(solid(p.loops, radial_plane(phi)), p, i, len(G.RIB_ANGLES))
    for key in ("SEAT_IN", "SEAT_OUT", "BACK_BOT", "BACK_MID", "BACK_TOP"):
        p = parts[key]
        add(solid(p.loops, Plane.XY.offset(G.RAIL_BY_KEY[key].z0), centred=False), p, 1, 1)
    p = parts["ARM"]
    for i, phi in enumerate(G.ARM_ANGLES, 1):
        add(solid(p.loops, radial_plane(phi)), p, i, len(G.ARM_ANGLES))
    for i in range(3):
        p = parts[f"DECK{i + 1}"]
        add(solid(p.loops, Plane.XY.offset(G.SEAT_TOP), centred=False), p, 1, 1)
    p = parts["STILE"]
    for i, phi in enumerate(G.STILE_ANGLES, 1):
        add(solid(p.loops, stile_plane(phi)), p, i, len(G.STILE_ANGLES))
    return items


def clashes(items):
    boxes = [s.bounding_box() for s in items]
    hit = []
    for i, j in itertools.combinations(range(len(items)), 2):
        a, b = boxes[i], boxes[j]
        if (a.min.X < b.max.X and b.min.X < a.max.X and a.min.Y < b.max.Y and b.min.Y < a.max.Y
                and a.min.Z < b.max.Z and b.min.Z < a.max.Z):
            v = (items[i] & items[j]).volume
            if v > 1e-3:
                hit.append((items[i].label, items[j].label, round(v, 1)))
    return hit


if __name__ == "__main__":
    items = assembly()
    comp = Compound(children=items)
    out = HERE / "out" / "curved-sofa.step"
    out.parent.mkdir(exist_ok=True)
    export_step(comp, str(out))
    bb = comp.bounding_box()
    print(f"wrote {out}: {len(items)} solids, {bb.size.X:.0f} x {bb.size.Y:.0f} x {bb.size.Z:.0f} mm")
    hit = clashes(items)
    print(f"clashes: {len(hit)}", *hit[:12], sep="\n  ")
