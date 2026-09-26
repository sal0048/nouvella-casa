"""Geometry model for the curved (crescent) 3-seat sofa CNC frame.

Pure geometry: no ezdxf document is built here. Every part is described as a
list of closed loops; a loop is a list of ``(x, y, bulge)`` vertices in the
LWPOLYLINE sense (the bulge belongs to the segment leaving that vertex).

Coordinate systems
------------------
* Plan parts (rails, seat deck) are built in the sofa plan frame: the arc is
  centred on the +Y axis, ``alpha`` is the standard math angle from +X.
* Elevation parts (ribs, arm panels) are built in a local frame where
  ``x`` runs radially outward from ``R_IN`` and ``y`` is height above floor.

All dimensions are millimetres.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import joints as J

# --------------------------------------------------------------------------
# Material and global sofa dimensions
# --------------------------------------------------------------------------

# Measure the real sheet with calipers and set t here; plywood sold as 15 mm
# is often 14.5-15.2 mm. fit is the total clearance across every slot.
JOINT = J.JointSpec(t=15.0, fit=0.4, tool_d=6.0)

T = JOINT.t                   # plywood thickness
FIT = JOINT.fit               # total slot clearance (slot = T + FIT)
SLOT_T = JOINT.slot_w
DOGBONE_R = JOINT.relief_r    # corner relief radius (cutter radius + 0.2)

SHEET_W = 2440.0
SHEET_H = 1220.0
SHEET_MARGIN = 15.0
PART_GAP = 12.0

R_OUT = 2200.0                # outer (back) face radius in plan
DEPTH = 900.0                 # radial depth of the sofa band
R_IN = R_OUT - DEPTH          # 1300.0
HALF_SWEEP = 30.0             # degrees, half of the plan sweep

SEAT_TOP = 330.0              # top of ribs / underside of seat deck
DECK_TOP = SEAT_TOP + T       # 345.0
BACK_TOP = 760.0              # top of backrest
ARM_TOP = 620.0               # top of arm panel
ARM_NOSE_R = 120.0            # front radius of the arm silhouette
FOOT_ARCH = 55.0              # height of the relief arch between the two feet

# Radial members (angles measured from the +Y symmetry axis, degrees)
RIB_ANGLES = [-27.0, -18.0, -9.0, 0.0, 9.0, 18.0, 27.0]
ARM_ANGLES = [-HALF_SWEEP, HALF_SWEEP]

# Backrest stiles
STILE_W = 70.0
STILE_TENON_W = 60.0
STILE_R = 2140.0              # radial centreline of the back lattice
STILE_ANGLES = (
    [-28.5, 28.5]
    + [c + d for c in (-22.5, -13.5, -4.5, 4.5, 13.5, 22.5) for d in (-3.0, 3.0)]
)

# Seat deck: three sectors, seams midway between ribs
DECK_R_IN = R_IN
DECK_R_OUT = 1990.0
DECK_EDGE = HALF_SWEEP - 0.4  # clear the 15 mm arm panels
DECK_SEAMS = [-DECK_EDGE, -13.5, 13.5, DECK_EDGE]

# Rib locating tabs into the deck (radial spans in rib-local x)
RIB_TABS = [(220.0, 280.0), (520.0, 580.0)]

TAB_LEN = 15.0                # rail end tab length through the arm panels
RAIL_TAB_W = 60.0             # radial width of a rail end tab


@dataclass(frozen=True)
class Rail:
    """A horizontal curved rail: an annular band lying flat in plan."""

    key: str
    label: str
    x0: float                 # rib-local radial start (0 == R_IN)
    x1: float                 # rib-local radial end
    z0: float                 # underside height
    joint: str                # how the ribs receive it
    stile_slot_w: float = 0.0 # >0 => carries backrest stile slots

    @property
    def r_in(self) -> float:
        return R_IN + self.x0

    @property
    def r_out(self) -> float:
        return R_IN + self.x1

    @property
    def z1(self) -> float:
        return self.z0 + T

    @property
    def r_mid(self) -> float:
        return 0.5 * (self.r_in + self.r_out)


RAILS = [
    Rail("BASE_IN",  "RAIL-BASE-IN",   20.0, 120.0,   0.0, "bottom_notch"),
    Rail("BASE_OUT", "RAIL-BASE-OUT", 780.0, 880.0,   0.0, "bottom_notch"),
    Rail("SEAT_IN",  "RAIL-SEAT-IN",   10.0, 110.0, 315.0, "top_notch"),
    Rail("SEAT_OUT", "RAIL-SEAT-OUT", 590.0, 690.0, 315.0, "top_notch"),
    Rail("BACK_BOT", "RAIL-BACK-BOT", 790.0, 900.0, 330.0, "outer_notch", STILE_TENON_W),
    Rail("BACK_MID", "RAIL-BACK-MID", 790.0, 900.0, 520.0, "outer_notch", STILE_W),
    Rail("BACK_TOP", "RAIL-BACK-TOP", 790.0, 890.0, 745.0, "post_top_notch", STILE_W),
]
RAIL_BY_KEY = {r.key: r for r in RAILS}


# --------------------------------------------------------------------------
# Loop primitives
# --------------------------------------------------------------------------

Loop = list  # list[tuple[float, float, float]]

def dogbone_rect(x0: float, y0: float, x1: float, y1: float,
                 r: float = DOGBONE_R) -> Loop:
    """CCW rectangle with dogbone relief at every inside corner."""
    return J.dogbone_rect(x0, y0, x1, y1, r)


def stadium(x0: float, x1: float, yc: float, r: float) -> Loop:
    """CCW rounded slot (stadium) with semicircular ends, horizontal axis."""
    xl, xr = x0 + r, x1 - r
    return [(xl, yc - r, 0.0), (xr, yc - r, 1.0), (xr, yc + r, 0.0), (xl, yc + r, 1.0)]


def rotate_loop(loop: Loop, angle_deg: float) -> Loop:
    c, s = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
    return [(x * c - y * s, x * s + y * c, b) for x, y, b in loop]


def translate_loop(loop: Loop, dx: float, dy: float) -> Loop:
    return [(x + dx, y + dy, b) for x, y, b in loop]


def mirror_loop_x(loop: Loop) -> Loop:
    """Mirror about the Y axis; reverses orientation, so flip bulges."""
    out = [(-x, y, -b) for x, y, b in loop]
    return _reverse_loop(out)


def _reverse_loop(loop: Loop) -> Loop:
    """Reverse traversal while keeping bulges attached to the right segments."""
    n = len(loop)
    rev: Loop = []
    for i in range(n):
        src = loop[(n - i) % n]
        bulge_owner = loop[(n - i - 1) % n]
        rev.append((src[0], src[1], bulge_owner[2]))
    return rev


def polar(r: float, alpha_deg: float) -> tuple[float, float]:
    a = math.radians(alpha_deg)
    return r * math.cos(a), r * math.sin(a)


def rect_at_polar(r_center: float, alpha_deg: float, radial: float,
                  tangential: float, dogbone: bool = True) -> Loop:
    """A slot whose long axis is radial, centred on (r_center, alpha)."""
    hx, hy = radial / 2.0, tangential / 2.0
    loop = dogbone_rect(-hx, -hy, hx, hy) if dogbone else [
        (-hx, -hy, 0.0), (hx, -hy, 0.0), (hx, hy, 0.0), (-hx, hy, 0.0)]
    loop = rotate_loop(loop, alpha_deg)
    cx, cy = polar(r_center, alpha_deg)
    return translate_loop(loop, cx, cy)


def sector_loop(r_in: float, r_out: float, a1_deg: float, a2_deg: float,
                tabs: tuple[float, float] | None = None) -> Loop:
    """CCW annular sector from a1 to a2 (a2 > a1), optional end tabs.

    ``tabs`` is the radial span of a tab added at both end faces, protruding
    ``TAB_LEN`` tangentially outward.
    """
    delta = math.radians(a2_deg - a1_deg)
    bulge = math.tan(delta / 4.0)
    pts: Loop = []

    # outward-pointing tangential normals at the two end faces
    a1, a2 = math.radians(a1_deg), math.radians(a2_deg)
    d1 = (math.sin(a1), -math.cos(a1))
    d2 = (-math.sin(a2), math.cos(a2))

    pts.append((*polar(r_in, a1_deg), 0.0))
    if tabs:
        t0, t1 = tabs
        p0, p1 = polar(t0, a1_deg), polar(t1, a1_deg)
        pts.append((*p0, 0.0))
        pts.append((p0[0] + TAB_LEN * d1[0], p0[1] + TAB_LEN * d1[1], 0.0))
        pts.append((p1[0] + TAB_LEN * d1[0], p1[1] + TAB_LEN * d1[1], 0.0))
        pts.append((*p1, 0.0))
    pts.append((*polar(r_out, a1_deg), bulge))
    pts.append((*polar(r_out, a2_deg), 0.0))
    if tabs:
        t0, t1 = tabs
        p1, p0 = polar(t1, a2_deg), polar(t0, a2_deg)
        pts.append((*p1, 0.0))
        pts.append((p1[0] + TAB_LEN * d2[0], p1[1] + TAB_LEN * d2[1], 0.0))
        pts.append((p0[0] + TAB_LEN * d2[0], p0[1] + TAB_LEN * d2[1], 0.0))
        pts.append((*p0, 0.0))
    pts.append((*polar(r_in, a2_deg), -bulge))
    return pts


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
    num: int = 0              # part number engraved on every piece
    relieved: int = 0         # concave outline corners given a dogbone


def _rib_outline() -> Loop:
    """Shared lower outline (floor edge, base-rail notches, foot arch)."""
    base_in = RAIL_BY_KEY["BASE_IN"]
    base_out = RAIL_BY_KEY["BASE_OUT"]
    pts: Loop = [(0.0, 0.0, 0.0)]

    # bottom edge: base-rail notches + foot arch
    for rail in (base_in, base_out):
        pts += [(rail.x0, 0.0, 0.0), (rail.x0, T + FIT / 2, 0.0),
                (rail.x1, T + FIT / 2, 0.0), (rail.x1, 0.0, 0.0)]
        if rail is base_in:
            pts += [(150.0, 0.0, 0.0), (150.0, FOOT_ARCH, 0.0),
                    (750.0, FOOT_ARCH, 0.0), (750.0, 0.0, 0.0)]
    pts.append((DEPTH, 0.0, 0.0))
    return pts


def rib_loops() -> list:
    """Radial rib: floor to seat level, with a back post up to BACK_TOP."""
    seat_in = RAIL_BY_KEY["SEAT_IN"]
    seat_out = RAIL_BY_KEY["SEAT_OUT"]
    back_bot = RAIL_BY_KEY["BACK_BOT"]
    back_mid = RAIL_BY_KEY["BACK_MID"]
    back_top = RAIL_BY_KEY["BACK_TOP"]

    pts = _rib_outline()

    # right (outer) edge, with the two outer-edge notches for BACK_BOT/BACK_MID
    for rail in (back_bot, back_mid):
        pts += [(DEPTH, rail.z0, 0.0), (rail.x0, rail.z0, 0.0),
                (rail.x0, rail.z1 + FIT, 0.0), (DEPTH, rail.z1 + FIT, 0.0)]
    pts.append((DEPTH, BACK_TOP, 0.0))

    # post top edge, with the open notch for BACK_TOP
    pts += [(back_top.x1, BACK_TOP, 0.0), (back_top.x1, back_top.z0 - FIT / 2, 0.0),
            (back_top.x0, back_top.z0 - FIT / 2, 0.0), (back_top.x0, BACK_TOP, 0.0)]
    pts += [(700.0, BACK_TOP, 0.0), (700.0, SEAT_TOP, 0.0)]

    # seat-level top edge travelling back toward x = 0:
    # SEAT_OUT notch, two deck tabs, SEAT_IN notch
    pts += [(seat_out.x1, SEAT_TOP, 0.0), (seat_out.x1, seat_out.z0 - FIT / 2, 0.0),
            (seat_out.x0, seat_out.z0 - FIT / 2, 0.0), (seat_out.x0, SEAT_TOP, 0.0)]
    for x0, x1 in reversed(RIB_TABS):
        pts += [(x1, SEAT_TOP, 0.0), (x1, DECK_TOP, 0.0),
                (x0, DECK_TOP, 0.0), (x0, SEAT_TOP, 0.0)]
    pts += [(seat_in.x1, SEAT_TOP, 0.0), (seat_in.x1, seat_in.z0 - FIT / 2, 0.0),
            (seat_in.x0, seat_in.z0 - FIT / 2, 0.0), (seat_in.x0, SEAT_TOP, 0.0)]
    pts.append((0.0, SEAT_TOP, 0.0))

    loops = [pts]
    loops.append(stadium(230.0, 670.0, 190.0, 55.0))          # lightening
    loops.append(stadium(745.0, 875.0, 620.0, 40.0))          # post lightening
    return loops


def arm_loops() -> list:
    """End / arm panel: same footprint, arm silhouette, rails engage by tabs."""
    seat_in = RAIL_BY_KEY["SEAT_IN"]
    seat_out = RAIL_BY_KEY["SEAT_OUT"]
    back_bot = RAIL_BY_KEY["BACK_BOT"]
    back_mid = RAIL_BY_KEY["BACK_MID"]
    back_top = RAIL_BY_KEY["BACK_TOP"]

    pts = _rib_outline()
    pts.append((DEPTH, BACK_TOP, 0.0))

    tab_top = _tab_span(back_top)
    pts += [(tab_top[1], BACK_TOP, 0.0), (tab_top[1], back_top.z0 - FIT / 2, 0.0),
            (tab_top[0], back_top.z0 - FIT / 2, 0.0), (tab_top[0], BACK_TOP, 0.0)]
    pts += [(700.0, BACK_TOP, 0.0), (700.0, ARM_TOP, 0.0)]

    # arm top, then the rounded nose down the front edge
    nose_x = ARM_NOSE_R
    nose_y = ARM_TOP - ARM_NOSE_R
    quarter = math.tan(math.radians(90.0) / 4.0)
    pts += [(nose_x, ARM_TOP, quarter), (0.0, nose_y, 0.0), (0.0, 0.0, 0.0)]

    loops = [pts]
    for rail in (seat_in, seat_out, back_bot, back_mid):
        t0, t1 = _tab_span(rail)
        loops.append(dogbone_rect(t0 - FIT / 2, rail.z0 - FIT / 2,
                                  t1 + FIT / 2, rail.z1 + FIT / 2))
    loops.append(stadium(230.0, 670.0, 190.0, 55.0))
    loops.append(stadium(200.0, 600.0, 480.0, 60.0))
    return loops


def _tab_span(rail: Rail) -> tuple[float, float]:
    mid = 0.5 * (rail.x0 + rail.x1)
    return mid - RAIL_TAB_W / 2.0, mid + RAIL_TAB_W / 2.0


def rail_loops(rail: Rail) -> list:
    """A curved rail: annular band with end tabs and optional stile slots."""
    half = HALF_SWEEP - math.degrees((T / 2.0) / rail.r_mid)
    tab_r = (R_IN + _tab_span(rail)[0], R_IN + _tab_span(rail)[1])
    outline = sector_loop(rail.r_in, rail.r_out, 90.0 - half, 90.0 + half, tabs=tab_r)
    loops = [outline]
    if rail.stile_slot_w:
        for phi in STILE_ANGLES:
            loops.append(rect_at_polar(STILE_R, 90.0 + phi,
                                       SLOT_T, rail.stile_slot_w + FIT))
    return loops


def deck_loops(a1: float, a2: float) -> list:
    """One seat-deck sector with rib locating slots and vent slots."""
    outline = sector_loop(DECK_R_IN, DECK_R_OUT, 90.0 + a1, 90.0 + a2)
    loops = [outline]
    for phi in RIB_ANGLES + ARM_ANGLES:
        if not (a1 + 0.4 < phi < a2 - 0.4):
            continue
        for x0, x1 in RIB_TABS:
            loops.append(rect_at_polar(R_IN + (x0 + x1) / 2.0, 90.0 + phi,
                                       (x1 - x0) + FIT, SLOT_T))
    # ventilation slots between the two rib-tab rings
    mid_r = R_IN + 400.0
    span = a2 - a1
    for frac in (0.28, 0.72):
        phi = a1 + span * frac
        vent = stadium(-75.0, 75.0, 0.0, 27.0)
        vent = rotate_loop(vent, 90.0 + phi)
        cx, cy = polar(mid_r, 90.0 + phi)
        loops.append(translate_loop(vent, cx, cy))
    return loops


def stile_loops() -> list:
    """Backrest stile: 70 mm wide, reduced to a 60 mm tenon at the bottom."""
    h = BACK_TOP - SEAT_TOP
    s = (STILE_W - STILE_TENON_W) / 2.0
    return [[
        (s, 0.0, 0.0), (STILE_W - s, 0.0, 0.0), (STILE_W - s, T, 0.0),
        (STILE_W, T, 0.0), (STILE_W, h, 0.0), (0.0, h, 0.0),
        (0.0, T, 0.0), (s, T, 0.0),
    ]]


def build_parts() -> list:
    parts: list = []
    parts.append(Part("RIB", "RIB", len(RIB_ANGLES), rib_loops(),
                      "radial rib, drops onto base rails"))
    parts.append(Part("ARM", "ARM-PANEL", len(ARM_ANGLES), arm_loops(),
                      "end panel, slides on tangentially over the rail tabs"))
    for rail in RAILS:
        parts.append(Part(rail.key, rail.label, 1, rail_loops(rail),
                          f"z {rail.z0:.0f}-{rail.z1:.0f} mm, {rail.joint}"))
    for i in range(3):
        parts.append(Part(f"DECK{i + 1}", f"SEAT-DECK-{i + 1}", 1,
                          deck_loops(DECK_SEAMS[i], DECK_SEAMS[i + 1]),
                          "rests on ribs + both seat rails"))
    parts.append(Part("STILE", "BACK-STILE", len(STILE_ANGLES), stile_loops(),
                      "threads down through the three back rails"))

    for num, part in enumerate(parts, 1):
        part.num = num
        outline, part.relieved = J.relieve_inside_corners(part.loops[0], DOGBONE_R)
        part.loops = [outline] + part.loops[1:]
    return parts
