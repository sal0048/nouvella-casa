"""Joint rules for slot-and-tab plywood frames.

One ``JointSpec`` holds the three numbers every joint depends on: the real
sheet thickness, the fit clearance and the cutter diameter. Everything that
cuts a slot or relieves a corner derives from it, so re-measuring a sheet or
changing the bit is a one-line change.

Corner relief
-------------
A round cutter leaves a fillet of its own radius in every inside corner. A
square tab or a square rail edge then stops on that fillet instead of seating.
Every concave right-angle corner between two straight edges is therefore given
a relief circle centred on the corner (a 270 degree arc into the material),
the same "dogbone" the closed slots already used.

Loops are lists of ``(x, y, bulge)`` vertices, LWPOLYLINE style.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

DOGBONE_BULGE = math.tan(math.radians(270.0) / 4.0)   # 2.41421356


@dataclass(frozen=True)
class JointSpec:
    t: float            # measured sheet thickness, mm
    fit: float          # total clearance across a slot, mm
    tool_d: float       # cutter diameter, mm

    @property
    def slot_w(self) -> float:
        return self.t + self.fit

    @property
    def relief_r(self) -> float:
        """Relief radius: the cutter radius plus 0.2 mm so the bit clears it."""
        return self.tool_d / 2.0 + 0.2


def dogbone_rect(x0: float, y0: float, x1: float, y1: float, r: float) -> list:
    """CCW rectangle with a relief circle at every inside corner."""
    r = min(r, (x1 - x0) / 2.0 - 0.1, (y1 - y0) / 2.0 - 0.1)
    if r <= 0.2:
        return [(x0, y0, 0.0), (x1, y0, 0.0), (x1, y1, 0.0), (x0, y1, 0.0)]
    corners = [
        ((x0, y0), (0.0, -1.0), (1.0, 0.0)),
        ((x1, y0), (1.0, 0.0), (0.0, 1.0)),
        ((x1, y1), (0.0, 1.0), (-1.0, 0.0)),
        ((x0, y1), (-1.0, 0.0), (0.0, -1.0)),
    ]
    pts: list = []
    for (cx, cy), e1, e2 in corners:
        pts.append((cx - e1[0] * r, cy - e1[1] * r, DOGBONE_BULGE))
        pts.append((cx + e2[0] * r, cy + e2[1] * r, 0.0))
    return pts


def _signed_area(loop) -> float:
    a = 0.0
    n = len(loop)
    for i in range(n):
        x0, y0, _ = loop[i]
        x1, y1, _ = loop[(i + 1) % n]
        a += x0 * y1 - x1 * y0
    return a / 2.0


def relieve_inside_corners(loop, r: float, tol_deg: float = 1.0):
    """Return ``loop`` with a relief circle at every concave square corner.

    Only corners where both neighbouring segments are straight, meet at 90
    degrees (within ``tol_deg``) and are long enough to give up ``r`` at each
    relieved end are touched. Returns ``(new_loop, relieved_count)``.
    """
    n = len(loop)
    ccw = _signed_area(loop) > 0.0
    cos_tol = math.sin(math.radians(tol_deg))

    def unit(p, q):
        dx, dy = q[0] - p[0], q[1] - p[1]
        d = math.hypot(dx, dy)
        return (dx / d, dy / d, d) if d > 1e-9 else (0.0, 0.0, 0.0)

    # first pass: decide which corners get relief
    relieve = [False] * n
    for i in range(n):
        prev, cur, nxt = loop[i - 1], loop[i], loop[(i + 1) % n]
        if abs(prev[2]) > 1e-12 or abs(cur[2]) > 1e-12:
            continue                     # an arc touches this corner
        ex1, ey1, _ = unit(prev, cur)
        ex2, ey2, _ = unit(cur, nxt)
        if abs(ex1 * ex2 + ey1 * ey2) > cos_tol:
            continue                     # not a right angle
        cross = ex1 * ey2 - ey1 * ex2
        concave = cross < 0.0 if ccw else cross > 0.0
        relieve[i] = concave

    # second pass: drop corners whose edges are too short to give up r
    for i in range(n):
        if not relieve[i]:
            continue
        _, _, d_in = unit(loop[i - 1], loop[i])
        _, _, d_out = unit(loop[i], loop[(i + 1) % n])
        need_in = r * (2 if relieve[i - 1] else 1) + 0.2
        need_out = r * (2 if relieve[(i + 1) % n] else 1) + 0.2
        if d_in < need_in or d_out < need_out:
            relieve[i] = False

    out: list = []
    count = 0
    for i in range(n):
        x, y, b = loop[i]
        if not relieve[i]:
            out.append((x, y, b))
            continue
        ex1, ey1, _ = unit(loop[i - 1], loop[i])
        ex2, ey2, _ = unit(loop[i], loop[(i + 1) % n])
        cross = ex1 * ey2 - ey1 * ex2
        bulge = math.copysign(DOGBONE_BULGE, cross)
        out.append((x - ex1 * r, y - ey1 * r, bulge))
        out.append((x + ex2 * r, y + ey2 * r, b))
        count += 1
    return out, count
