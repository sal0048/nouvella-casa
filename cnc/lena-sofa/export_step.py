"""Assembled STEP of the Lena sofa frame (build123d, exact cut geometry).

Every piece is its cut profile (outline minus mortises) extruded to the board
thickness and placed by lena_geometry.instances(), so the STEP is the DXF in
3D, not a separate model. Units: mm.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))  # shared code, lower priority

from build123d import Compound, Face, Location, Plane, Wire, export_step, extrude

import lena_geometry as G
import sofa_layout as L

# plane -> (origin axis for the thickness, u direction, extrusion normal)
PLANES = {
    "XY": lambda w: Plane(origin=(0, 0, w), x_dir=(1, 0, 0), z_dir=(0, 0, 1)),
    "YZ": lambda w: Plane(origin=(w, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0)),
    "XZ": lambda w: Plane(origin=(0, w + G.T, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0)),
}


def solid(loops, plane):
    wires = [Wire.make_polygon([plane.from_local_coords((x, y, 0.0))
                                for x, y in L.flatten_loop(l, 12)], close=True)
             for l in loops]
    return extrude(Face(wires[0], wires[1:]), amount=G.T, dir=plane.z_dir)


def assembly():
    items = []
    for p, k, plane, w0, loops in G.instances():
        s = solid(loops, PLANES[plane](w0))
        s.label = f"P{p.num:02d} {p.label} {k}/{p.qty}"
        items.append(s)
    return items


def main(out: Path) -> Compound:
    comp = Compound(children=assembly())
    export_step(comp, str(out))
    bb = comp.bounding_box()
    print(f"wrote {out}: {len(comp.children)} solids, "
          f"{bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm")
    return comp


if __name__ == "__main__":
    main(HERE / "out" / "lena-sofa.step")
