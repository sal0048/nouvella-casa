"""Assembled 3D preview of the round armchair frame (matplotlib).

Every flat part is placed where it sits in the chair and drawn as an
extruded 18 mm plate, so the render doubles as a fit check of the geometry.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.append(str(Path(__file__).resolve().parents[1] / "curved-sofa"))  # shared code, lower priority

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

import chair_geometry as C
import sofa_layout as L

WOOD, EDGE = "#d9b27c", "#7a5a32"


def slab(ax, pts3d_bottom, normal, colour=WOOD):
    """Draw a plate: its face, the opposite face T away along normal, sides."""
    nx, ny, nz = normal
    top = [(x + nx * C.T, y + ny * C.T, z + nz * C.T) for x, y, z in pts3d_bottom]
    faces = [pts3d_bottom, top]
    n = len(pts3d_bottom)
    step = max(1, n // 60)
    for i in range(0, n, step):
        j = (i + step) % n
        faces.append([pts3d_bottom[i], pts3d_bottom[j], top[j], top[i]])
    ax.add_collection3d(Poly3DCollection(faces, facecolor=colour, edgecolor=EDGE,
                                         linewidths=0.15, alpha=0.95))


def flat(ax, loops, z):
    slab(ax, [(x, y, z) for x, y in L.flatten_loop(loops[0], 8)], (0, 0, 1))


def ring(ax, loops, z):
    """A closed ring: quads between matching outer and inner stations."""
    outer = [(x, y) for x, y, _ in loops[0]]
    inner = [(x, y) for x, y, _ in reversed(loops[1])]
    faces = []
    n = len(outer)
    for i in range(n):
        j = (i + 1) % n
        for zz in (z, z + C.T):
            faces.append([(*outer[i], zz), (*outer[j], zz), (*inner[j], zz), (*inner[i], zz)])
        faces.append([(*outer[i], z), (*outer[j], z), (*outer[j], z + C.T), (*outer[i], z + C.T)])
    ax.add_collection3d(Poly3DCollection(faces, facecolor=WOOD, edgecolor=WOOD,
                                         linewidths=0.1, alpha=0.95))


def radial(ax, loops, theta, r0, z0):
    c, s = math.cos(math.radians(theta)), math.sin(math.radians(theta))
    pts = [((x + r0) * c, (x + r0) * s, y + z0) for x, y in L.flatten_loop(loops[0], 8)]
    # centre the plate on the radial plane
    slab(ax, [(px + s * C.T / 2, py - c * C.T / 2, pz) for px, py, pz in pts],
         (-s, c, 0))


def draw(ax, parts):
    for p in parts:
        if p.key == "BASE":
            ring(ax, p.loops, 0.0)
        elif p.key == "SEAT":
            ring(ax, p.loops, C.SEAT_Z)
        elif p.key.startswith("BAND"):
            flat(ax, p.loops, C.BAND_Z)
        elif p.key.startswith("BODY"):
            for a in C.BODY_ANGLES:
                if C._type_angle(a) == C._type_angle(p.angles[0]):
                    radial(ax, p.loops, a, C.body_in(a), 0.0)
        elif p.key.startswith("BACK"):
            for a in p.angles:
                radial(ax, p.loops, a, C.back_in(a) - C.SHOULDER, C.SEAT_Z)


def main(out: Path) -> None:
    parts = C.build_parts()
    fig = plt.figure(figsize=(12, 6.2))
    for k, (elev, azim, title) in enumerate([(22, -62, "front 3/4"),
                                             (16, 120, "rear 3/4")]):
        ax = fig.add_subplot(1, 2, k + 1, projection="3d")
        draw(ax, parts)
        ax.set_xlim(-500, 500); ax.set_ylim(-500, 500); ax.set_zlim(0, 820)
        ax.set_box_aspect((1000, 1000, 820))
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        ax.set_title(title, fontsize=10)
    fig.suptitle("Round tub armchair - 18 mm MDF frame, 950 x 920 x 800 mm",
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    print(f"wrote {out}")


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "out" / "round-armchair-3d.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    main(out)
