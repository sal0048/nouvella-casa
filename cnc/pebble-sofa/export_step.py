"""Assembled STEP of the Pebble sofa frame (build123d, exact cut geometry).
Every piece = its cut profile extruded to T and placed by its frame."""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))

from build123d import Compound, Face, Plane, Vector, Wire, export_step, extrude

import pebble_geometry as G
import sofa_layout as L


def frame_plane(o, u, v, centred):
    n = Vector(*u).cross(Vector(*v))
    origin = Vector(*o) - (n * (G.T / 2) if centred else Vector(0, 0, 0))
    return Plane(origin=origin, x_dir=Vector(*u), z_dir=n)


def solid(loops, plane):
    wires = [Wire.make_polygon([plane.from_local_coords((x, y, 0.0))
                                for x, y in L.flatten_loop(l, 12)], close=True) for l in loops]
    return extrude(Face(wires[0], wires[1:]), amount=G.T, dir=plane.z_dir)


def assembly():
    items = []
    for p, k, o, u, v, c in G.instances():
        s = solid(p.loops, frame_plane(o, u, v, c))
        s.label = f"P{p.num:02d} {p.label} {k}/{p.qty}"
        items.append(s)
    return items


if __name__ == "__main__":
    comp = Compound(children=assembly())
    export_step(comp, str(HERE / "out" / "pebble-sofa.step"))
    bb = comp.bounding_box()
    print(f"{len(comp.children)} solids, {bb.size.X:.0f} x {bb.size.Y:.0f} x {bb.size.Z:.0f} mm")
