"""Round tub armchair - slot-and-tab MDF frame, geometry only.

Construction (all flat 18 mm plates, stacked vertically):

* BASE-RING   floor ring, rounded-square in plan
* BODY-RIB    radial ribs between the base ring and the seat ring; their
              outer edge bulges out past both rings, which gives the round
              "pumpkin" belly under the upholstery
* SEAT-RING   ring at seat height, carries the body ribs from above and the
              back ribs on top
* BACK-RIB    radial ribs around the back and arms, standing on the seat
              ring, taller at the back than at the arm ends
* BACK-BAND   three flat bands that drop over the back rib tops and rest on
              a 10 mm shoulder on each rib, locking their spacing

Joint rules follow the bought Tokyo sofa pack: 18 mm board, 19 mm slots
(1 mm clearance), 40 mm tabs, 10 mm part spacing.

Plan frame: +Y is the back, -Y the front; plan angles are standard math
angles from +X. Rib parts are drawn in their own radial plane: x is the
distance from the chair axis, y is height.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "curved-sofa"))

import joints as J  # noqa: E402

JOINT = J.JointSpec(t=18.0, fit=1.0, tool_d=6.0)
T = JOINT.t
SLOT_T = JOINT.slot_w            # 19 mm
TAB_W = 40.0                     # tab length along the rib
TAB_SLOT = TAB_W + JOINT.fit     # 41 mm mortise
RELIEF_R = JOINT.relief_r

SHEET_W, SHEET_H = 2440.0, 1220.0
SHEET_MARGIN = 9.0
PART_GAP = 10.0

# plan: superellipse |x/A|^N + |y/B|^N = 1 at the widest point of the belly
A, B, N = 475.0, 460.0, 2.6      # overall 950 x 920 mm

SEAT_TOP = 330.0                 # top of seat ring; ~430 with a 100 mm cushion
SEAT_Z = SEAT_TOP - T            # underside of seat ring
BAND_Z = 520.0                   # underside of the back band
ARM_TOP = 600.0                  # back rib height at the arm ends
BACK_TOP = 800.0                 # back rib height at the centre of the back

S_BASE = 0.86                    # base ring outer, as a fraction of R(theta)
S_SEAT = 0.93                    # rib outer edge where it meets the seat ring
RIB_IN = 70.0                    # body rib inner edge, inside the base ring edge
BASE_W = 110.0                   # base ring width
SEAT_LIP = 15.0                  # seat ring overhang past the rib edge

BACK_D = 110.0                   # back rib depth above the band shoulder
SHOULDER = 10.0                  # extra depth below the band, both sides
BAND_MARGIN = 25.0               # band material beyond the rib, each side

BODY_ANGLES = [9.0 + 18.0 * k for k in range(20)]
BACK_ANGLES = [-18.0 + 18.0 * k for k in range(13)]        # -18 .. 198
BAND_SPLITS = [-27.0, 45.0, 135.0, 207.0]                    # 3 bands

Loop = list


def R(theta: float) -> float:
    """Plan radius of the belly outline at plan angle theta (deg)."""
    c, s = abs(math.cos(math.radians(theta))), abs(math.sin(math.radians(theta)))
    return ((c / A) ** N + (s / B) ** N) ** (-1.0 / N)


def polar(r: float, theta: float):
    a = math.radians(theta)
    return r * math.cos(a), r * math.sin(a)


def belly(z: float) -> float:
    """Rib outer edge as a fraction of R: 0.86 at the floor, 1.0 at the
    widest point, 0.93 under the seat ring (a parabola through the three)."""
    t = z / SEAT_Z
    tm = 1.0 / (1.0 + math.sqrt((1.0 - S_SEAT) / (1.0 - S_BASE)))
    k = (1.0 - S_BASE) / tm ** 2
    return 1.0 - k * (t - tm) ** 2


def back_height(theta: float) -> float:
    """Back rib top: ARM_TOP at the arm ends rising to BACK_TOP at the back."""
    a0, a1 = BACK_ANGLES[0], BACK_ANGLES[-1]
    u = (theta - a0) / (a1 - a0)
    return ARM_TOP + (BACK_TOP - ARM_TOP) * math.sin(math.pi * u) ** 1.5


# rib radial stations (absolute distance from the chair axis)
def body_in(theta):  return S_BASE * R(theta) - RIB_IN
def back_out(theta): return S_SEAT * R(theta) + SEAT_LIP - 5.0
def back_in(theta):  return back_out(theta) - BACK_D


def body_tab(theta):
    r0 = body_in(theta) + 8.0
    return r0, r0 + TAB_W


def back_tab(theta):
    r1 = back_out(theta) - 12.0
    return r1 - TAB_W, r1


# --------------------------------------------------------------------------
# Loop helpers
# --------------------------------------------------------------------------

def plan_curve(scale: float, offset: float, a0=0.0, a1=360.0, n=180):
    """Points on scale*R(theta)+offset from a0 to a1 (deg), inclusive."""
    return [(*polar(scale * R(a) + offset, a), 0.0)
            for a in (a0 + (a1 - a0) * i / n for i in range(n + 1))]


def mortise(r0: float, r1: float, theta: float) -> Loop:
    """Radial 41 x 19 mortise with dogbones, spanning r0..r1 (tab span)."""
    hx, hy = (r1 - r0 + JOINT.fit) / 2.0, SLOT_T / 2.0
    loop = J.dogbone_rect(-hx, -hy, hx, hy, RELIEF_R)
    rc = 0.5 * (r0 + r1)
    c, s = math.cos(math.radians(theta)), math.sin(math.radians(theta))
    cx, cy = rc * c, rc * s
    return [(cx + x * c - y * s, cy + x * s + y * c, b) for x, y, b in loop]


def _slot(r0, r1, theta):
    """Slot the full rib depth plus fit, for the band to drop over a rib."""
    r0, r1 = r0 - JOINT.fit / 2.0, r1 + JOINT.fit / 2.0
    hx, hy = (r1 - r0) / 2.0, SLOT_T / 2.0
    loop = J.dogbone_rect(-hx, -hy, hx, hy, RELIEF_R)
    rc = 0.5 * (r0 + r1)
    c, s = math.cos(math.radians(theta)), math.sin(math.radians(theta))
    return [(rc * c + x * c - y * s, rc * s + x * s + y * c, b) for x, y, b in loop]


# --------------------------------------------------------------------------
# Parts
# --------------------------------------------------------------------------

@dataclass
class Part:
    key: str
    label: str
    qty: int
    loops: list = field(default_factory=list)
    note: str = ""
    angles: tuple = ()
    num: int = 0
    relieved: int = 0


def base_ring() -> list:
    outer = plan_curve(S_BASE, 0.0)[:-1]
    inner = list(reversed(plan_curve(S_BASE, -BASE_W)[:-1]))
    loops = [outer, inner]
    for a in BODY_ANGLES:
        loops.append(mortise(*body_tab(a), a))
    return loops


def seat_ring() -> list:
    outer = plan_curve(S_SEAT, SEAT_LIP)[:-1]
    inner = list(reversed(plan_curve(S_BASE, -RIB_IN - 25.0)[:-1]))
    loops = [outer, inner]
    for a in BODY_ANGLES:
        loops.append(mortise(*body_tab(a), a))
    for a in BACK_ANGLES:
        loops.append(mortise(*back_tab(a), a))
    return loops


def body_rib(theta: float) -> list:
    r_in = body_in(theta)
    t0, t1 = body_tab(theta)
    rr = R(theta)
    pts: Loop = [(r_in, T, 0.0), (t0, T, 0.0), (t0, 0.0, 0.0), (t1, 0.0, 0.0),
                 (t1, T, 0.0)]
    steps = 28
    for i in range(steps + 1):
        z = T + (SEAT_Z - T) * i / steps
        pts.append((belly(z) * rr, z, 0.0))
    pts += [(t1, SEAT_Z, 0.0), (t1, SEAT_TOP, 0.0), (t0, SEAT_TOP, 0.0),
            (t0, SEAT_Z, 0.0), (r_in, SEAT_Z, 0.0)]
    return [[(x - r_in, y, b) for x, y, b in pts]]


def back_rib(theta: float) -> list:
    ri, ro = back_in(theta), back_out(theta)
    t0, t1 = back_tab(theta)
    top = back_height(theta)
    lo, hi = ri - SHOULDER, ro + SHOULDER
    pts: Loop = [
        (lo, SEAT_TOP, 0.0), (t0, SEAT_TOP, 0.0), (t0, SEAT_Z, 0.0),
        (t1, SEAT_Z, 0.0), (t1, SEAT_TOP, 0.0), (hi, SEAT_TOP, 0.0),
        (hi, BAND_Z, 0.0), (ro, BAND_Z, 0.0),
        (ro, top - 30.0, 0.0), (ro - 30.0, top, 0.0), (ri, top, 0.0),
        (ri, BAND_Z, 0.0), (lo, BAND_Z, 0.0),
    ]
    return [[(x - lo, y - SEAT_Z, b) for x, y, b in pts]]


def back_band(a0: float, a1: float) -> list:
    ro = S_SEAT
    outer = plan_curve(ro, SEAT_LIP - 5.0 + BAND_MARGIN, a0, a1, 60)
    inner = list(reversed(plan_curve(ro, SEAT_LIP - 5.0 - BACK_D - BAND_MARGIN,
                                     a0, a1, 60)))
    loops = [outer + inner]
    for a in BACK_ANGLES:
        if a0 < a < a1:
            loops.append(_slot(back_in(a), back_out(a), a))
    return loops


def _type_angle(theta: float) -> float:
    """Ribs at theta, 180-theta, -theta, 180+theta have the same profile."""
    t = theta % 180.0
    return round(min(t, 180.0 - t), 6)


def build_parts() -> list:
    parts: list = [
        Part("BASE", "BASE-RING", 1, base_ring(), "floor ring"),
        Part("SEAT", "SEAT-RING", 1, seat_ring(), "seat ring, ribs above and below"),
    ]
    groups: dict = {}
    for a in BODY_ANGLES:
        groups.setdefault(_type_angle(a), []).append(a)
    for i, (ta, angs) in enumerate(sorted(groups.items()), 1):
        parts.append(Part(f"BODY{i}", f"BODY-RIB-{chr(64 + i)}", len(angs),
                          body_rib(angs[0]), f"body rib at {', '.join(f'{x:g}' for x in angs)} deg",
                          tuple(angs)))
    groups = {}
    for a in BACK_ANGLES:
        groups.setdefault((round(R(a), 6), round(back_height(a), 6)), []).append(a)
    for i, (_, angs) in enumerate(sorted(groups.items(), key=lambda kv: kv[0][1]), 1):
        parts.append(Part(f"BACK{i}", f"BACK-RIB-{chr(64 + i)}", len(angs),
                          back_rib(angs[0]), f"back rib at {', '.join(f'{x:g}' for x in angs)} deg",
                          tuple(angs)))
    for i in range(len(BAND_SPLITS) - 1):
        a0, a1 = BAND_SPLITS[i], BAND_SPLITS[i + 1]
        parts.append(Part(f"BAND{i + 1}", f"BACK-BAND-{i + 1}", 1, back_band(a0, a1),
                          "drops over the back rib tops onto the shoulders",
                          (a0, a1)))
    for num, part in enumerate(parts, 1):
        part.num = num
        outline, part.relieved = J.relieve_inside_corners(part.loops[0], RELIEF_R)
        part.loops = [outline] + part.loops[1:]
    return parts
