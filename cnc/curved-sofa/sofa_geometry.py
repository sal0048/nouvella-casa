"""Geometry model for the curved (crescent) 3-seat sofa CNC frame.

Pure geometry: no ezdxf document is built here. Every part is described as a
list of closed loops; a loop is a list of ``(x, y, bulge)`` vertices in the
LWPOLYLINE sense (the bulge belongs to the segment leaving that vertex).

Coordinate systems
------------------
* Plan parts (rails, seat deck, arm caps) are built in the sofa plan frame:
  the arc is centred on the +Y axis, ``alpha`` is the standard math angle
  from +X.
* Elevation parts (ribs, arm panels) are built in a local frame where ``x``
  runs radially outward from ``R_IN`` and ``y`` is height above the top face
  of the plinth.  Add ``PLINTH_H`` to get the height above the floor.

All dimensions are millimetres.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Materials
# --------------------------------------------------------------------------

T = 15.0                      # structural plywood thickness
FIT = 0.4                     # total slot clearance (slot = T + FIT)
SLOT_T = T + FIT
DOGBONE_R = 3.2               # corner relief radius (6 mm cutter + clearance)

SKIN_T = 4.0                  # flexible plywood skin thickness

PLY15 = "15 mm PLYWOOD"
PLY4 = "4 mm FLEXIBLE PLYWOOD"

SHEET_W = 2440.0
SHEET_H = 1220.0
SHEET_MARGIN = 15.0
PART_GAP = 12.0

# --------------------------------------------------------------------------
# Global sofa dimensions
# --------------------------------------------------------------------------

R_OUT = 2200.0                # outer (back) face radius in plan
DEPTH = 900.0                 # radial depth of the sofa band
R_IN = R_OUT - DEPTH          # 1300.0
HALF_SWEEP = 30.0             # degrees, half of the plan sweep

PLINTH_LAYERS = 2             # laminae glued under the base rails
PLINTH_H = PLINTH_LAYERS * T  # 30 mm of plinth below the frame

# heights are local: floor level = -PLINTH_H
SEAT_TOP = 300.0              # top of ribs / underside of seat deck
DECK_TOP = SEAT_TOP + T       # 315.0  -> 345 mm above the floor
BACK_TOP = 730.0              # -> 760 mm above the floor
ARM_TOP = 590.0               # -> 620 mm above the floor
ARM_NOSE_R = 120.0            # front radius of the arm silhouette
FOOT_ARCH = 55.0              # relief arch between the two feet of a rib

# Radial members (angles measured from the +Y symmetry axis, degrees)
RIB_ANGLES = [-16.0, -8.0, 0.0, 8.0, 16.0]
ARM_IN_ANGLE = 23.5           # inner arm panel: the seat structure ends here
ARM_OUT_ANGLE = HALF_SWEEP    # outer arm panel: the end of the sofa
ARM_IN_ANGLES = [-ARM_IN_ANGLE, ARM_IN_ANGLE]
ARM_OUT_ANGLES = [-ARM_OUT_ANGLE, ARM_OUT_ANGLE]

# Backrest stiles: two per bay between the seat-structure radial members
STILE_W = 70.0
STILE_TENON_W = 60.0
STILE_R = 2140.0              # radial centreline of the back lattice
_BAY_EDGES = sorted([-ARM_IN_ANGLE] + RIB_ANGLES + [ARM_IN_ANGLE])
STILE_ANGLES = [
    a + (b - a) * f
    for a, b in zip(_BAY_EDGES, _BAY_EDGES[1:])
    for f in (1 / 3, 2 / 3)
]

# Seat deck: three sectors between the inner arm panels
DECK_R_IN = R_IN
DECK_R_OUT = 1990.0
DECK_EDGE = ARM_IN_ANGLE - 0.4
DECK_SEAMS = [-DECK_EDGE, -11.5, 11.5, DECK_EDGE]

# Rib locating tabs into the deck (radial spans in rib-local x)
RIB_TABS = [(220.0, 280.0), (520.0, 580.0)]

# Arm cap: a horizontal plate closing the top of each arm box
ARM_CAP_R_IN = R_IN
ARM_CAP_R_OUT = 1990.0
ARM_CAP_TABS = [(150.0, 250.0), (500.0, 600.0)]   # rib-local radial spans

TAB_LEN = 15.0                # tab length through a panel
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
    span: str                 # "full" to the outer arm panels, "seat" to the inner ones
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

    @property
    def half_sweep(self) -> float:
        """Angular half span to the *inner face* of the panel it dies into."""
        edge = ARM_OUT_ANGLE if self.span == "full" else ARM_IN_ANGLE
        offset = math.degrees((T / 2.0) / self.r_mid)
        return edge + offset if self.span == "full" else edge - offset

    @property
    def has_tabs(self) -> bool:
        return self.span == "seat"


RAILS = [
    Rail("BASE_IN",  "RAIL-BASE-IN",   20.0, 120.0,   0.0, "bottom_notch", "full"),
    Rail("BASE_OUT", "RAIL-BASE-OUT", 780.0, 880.0,   0.0, "bottom_notch", "full"),
    Rail("SEAT_IN",  "RAIL-SEAT-IN",   10.0, 110.0, 285.0, "top_notch", "seat"),
    Rail("SEAT_OUT", "RAIL-SEAT-OUT", 590.0, 690.0, 285.0, "top_notch", "seat"),
    Rail("BACK_BOT", "RAIL-BACK-BOT", 790.0, 900.0, 300.0, "outer_notch", "seat",
         STILE_TENON_W),
    Rail("BACK_MID", "RAIL-BACK-MID", 790.0, 900.0, 490.0, "outer_notch", "seat",
         STILE_W),
    Rail("BACK_TOP", "RAIL-BACK-TOP", 790.0, 890.0, 715.0, "post_top_notch", "full",
         STILE_W),
]
RAIL_BY_KEY = {r.key: r for r in RAILS}


# --------------------------------------------------------------------------
# Loop primitives
# --------------------------------------------------------------------------

Loop = list  # list[tuple[float, float, float]]

_DOGBONE_BULGE = math.tan(math.radians(270.0) / 4.0)   # 2.41421356


def dogbone_rect(x0: float, y0: float, x1: float, y1: float,
                 r: float = DOGBONE_R) -> Loop:
    """CCW rectangle with 270-degree dogbone relief at every inside corner."""
    r = min(r, (x1 - x0) / 2.0 - 0.1, (y1 - y0) / 2.0 - 0.1)
    if r <= 0.2:
        return [(x0, y0, 0.0), (x1, y0, 0.0), (x1, y1, 0.0), (x0, y1, 0.0)]
    corners = [
        ((x0, y0), (0.0, -1.0), (1.0, 0.0)),
        ((x1, y0), (1.0, 0.0), (0.0, 1.0)),
        ((x1, y1), (0.0, 1.0), (-1.0, 0.0)),
        ((x0, y1), (-1.0, 0.0), (0.0, -1.0)),
    ]
    pts: Loop = []
    for (cx, cy), e1, e2 in corners:
        pts.append((cx - e1[0] * r, cy - e1[1] * r, _DOGBONE_BULGE))
        pts.append((cx + e2[0] * r, cy + e2[1] * r, 0.0))
    return pts


def stadium(x0: float, x1: float, yc: float, r: float) -> Loop:
    """CCW rounded slot (stadium) with semicircular ends, horizontal axis."""
    xl, xr = x0 + r, x1 - r
    return [(xl, yc - r, 0.0), (xr, yc - r, 1.0), (xr, yc + r, 0.0), (xl, yc + r, 1.0)]


def rounded_rect(x0: float, y0: float, x1: float, y1: float, r: float) -> Loop:
    """CCW rectangle with radiused (not dogboned) corners."""
    q = math.tan(math.radians(90.0) / 4.0)
    return [
        (x0 + r, y0, 0.0), (x1 - r, y0, q),
        (x1, y0 + r, 0.0), (x1, y1 - r, q),
        (x1 - r, y1, 0.0), (x0 + r, y1, q),
        (x0, y1 - r, 0.0), (x0, y0 + r, q),
    ]


def rotate_loop(loop: Loop, angle_deg: float) -> Loop:
    c, s = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
    return [(x * c - y * s, x * s + y * c, b) for x, y, b in loop]


def translate_loop(loop: Loop, dx: float, dy: float) -> Loop:
    return [(x + dx, y + dy, b) for x, y, b in loop]


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
                tabs: list | None = None) -> Loop:
    """CCW annular sector from a1 to a2 (a2 > a1), with optional end tabs.

    ``tabs`` is a list of radial spans; each one becomes a tab at both end
    faces, protruding ``TAB_LEN`` tangentially outward.
    """
    delta = math.radians(a2_deg - a1_deg)
    bulge = math.tan(delta / 4.0)
    a1, a2 = math.radians(a1_deg), math.radians(a2_deg)
    d1 = (math.sin(a1), -math.cos(a1))
    d2 = (-math.sin(a2), math.cos(a2))
    spans = sorted(tabs or [])

    pts: Loop = [(*polar(r_in, a1_deg), 0.0)]
    for t0, t1 in spans:
        p0, p1 = polar(t0, a1_deg), polar(t1, a1_deg)
        pts.append((*p0, 0.0))
        pts.append((p0[0] + TAB_LEN * d1[0], p0[1] + TAB_LEN * d1[1], 0.0))
        pts.append((p1[0] + TAB_LEN * d1[0], p1[1] + TAB_LEN * d1[1], 0.0))
        pts.append((*p1, 0.0))
    pts.append((*polar(r_out, a1_deg), bulge))
    pts.append((*polar(r_out, a2_deg), 0.0))
    for t0, t1 in reversed(spans):
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
    material: str = PLY15


def _tab_span(rail: Rail) -> tuple[float, float]:
    mid = 0.5 * (rail.x0 + rail.x1)
    return mid - RAIL_TAB_W / 2.0, mid + RAIL_TAB_W / 2.0


def _bottom_outline() -> Loop:
    """Shared lower outline: floor edge, base-rail notches, foot arch."""
    base_in = RAIL_BY_KEY["BASE_IN"]
    base_out = RAIL_BY_KEY["BASE_OUT"]
    pts: Loop = [(0.0, 0.0, 0.0)]
    for rail in (base_in, base_out):
        pts += [(rail.x0, 0.0, 0.0), (rail.x0, T + FIT / 2, 0.0),
                (rail.x1, T + FIT / 2, 0.0), (rail.x1, 0.0, 0.0)]
        if rail is base_in:
            pts += [(150.0, 0.0, 0.0), (150.0, FOOT_ARCH, 0.0),
                    (750.0, FOOT_ARCH, 0.0), (750.0, 0.0, 0.0)]
    pts.append((DEPTH, 0.0, 0.0))
    return pts


def _back_top_notch(pts: Loop) -> None:
    """Open notch in the top of a back post for RAIL-BACK-TOP."""
    rail = RAIL_BY_KEY["BACK_TOP"]
    pts += [(rail.x1, BACK_TOP, 0.0), (rail.x1, rail.z0 - FIT / 2, 0.0),
            (rail.x0, rail.z0 - FIT / 2, 0.0), (rail.x0, BACK_TOP, 0.0)]


def rib_loops() -> list:
    """Radial rib: floor to seat level, with a back post up to BACK_TOP."""
    seat_in = RAIL_BY_KEY["SEAT_IN"]
    seat_out = RAIL_BY_KEY["SEAT_OUT"]

    pts = _bottom_outline()

    # outer edge, with the outer-edge notches for BACK_BOT and BACK_MID
    for key in ("BACK_BOT", "BACK_MID"):
        rail = RAIL_BY_KEY[key]
        pts += [(DEPTH, rail.z0, 0.0), (rail.x0, rail.z0, 0.0),
                (rail.x0, rail.z1 + FIT, 0.0), (DEPTH, rail.z1 + FIT, 0.0)]
    pts.append((DEPTH, BACK_TOP, 0.0))
    _back_top_notch(pts)
    pts += [(700.0, BACK_TOP, 0.0), (700.0, SEAT_TOP, 0.0)]

    # seat-level top edge: SEAT_OUT notch, two deck tabs, SEAT_IN notch
    pts += [(seat_out.x1, SEAT_TOP, 0.0), (seat_out.x1, seat_out.z0 - FIT / 2, 0.0),
            (seat_out.x0, seat_out.z0 - FIT / 2, 0.0), (seat_out.x0, SEAT_TOP, 0.0)]
    for x0, x1 in reversed(RIB_TABS):
        pts += [(x1, SEAT_TOP, 0.0), (x1, DECK_TOP, 0.0),
                (x0, DECK_TOP, 0.0), (x0, SEAT_TOP, 0.0)]
    pts += [(seat_in.x1, SEAT_TOP, 0.0), (seat_in.x1, seat_in.z0 - FIT / 2, 0.0),
            (seat_in.x0, seat_in.z0 - FIT / 2, 0.0), (seat_in.x0, SEAT_TOP, 0.0)]
    pts.append((0.0, SEAT_TOP, 0.0))

    return [pts,
            stadium(230.0, 670.0, 175.0, 50.0),
            stadium(745.0, 875.0, 590.0, 40.0)]


def arm_panel_loops(inner: bool) -> list:
    """Arm panel.

    ``inner``  the panel at +/-23.5 deg: the seat and lower back rails die
               into it, so it carries their end-tab slots.
               The outer panel at +/-30 deg is tied by the base rails, the
               top back rail and the arm cap only.
    """
    pts = _bottom_outline()
    pts.append((DEPTH, BACK_TOP, 0.0))
    _back_top_notch(pts)
    pts += [(700.0, BACK_TOP, 0.0), (700.0, ARM_TOP, 0.0)]

    # arm top edge with the two open notches for the arm cap tabs
    for x0, x1 in reversed(ARM_CAP_TABS):
        pts += [(x1, ARM_TOP, 0.0), (x1, ARM_TOP - T - FIT / 2, 0.0),
                (x0, ARM_TOP - T - FIT / 2, 0.0), (x0, ARM_TOP, 0.0)]

    # rounded nose down the front edge
    quarter = math.tan(math.radians(90.0) / 4.0)
    pts += [(ARM_NOSE_R, ARM_TOP, quarter), (0.0, ARM_TOP - ARM_NOSE_R, 0.0),
            (0.0, 0.0, 0.0)]

    loops = [pts]
    if inner:
        for key in ("SEAT_IN", "SEAT_OUT", "BACK_BOT", "BACK_MID"):
            rail = RAIL_BY_KEY[key]
            t0, t1 = _tab_span(rail)
            loops.append(dogbone_rect(t0 - FIT / 2, rail.z0 - FIT / 2,
                                      t1 + FIT / 2, rail.z1 + FIT / 2))
    loops.append(stadium(230.0, 670.0, 175.0, 50.0))
    loops.append(stadium(200.0, 600.0, 430.0, 55.0))
    return loops


def rail_loops(rail: Rail) -> list:
    """A curved rail: annular band with optional end tabs and stile slots."""
    half = rail.half_sweep
    tabs = None
    if rail.has_tabs:
        t0, t1 = _tab_span(rail)
        tabs = [(R_IN + t0, R_IN + t1)]
    loops = [sector_loop(rail.r_in, rail.r_out, 90.0 - half, 90.0 + half, tabs=tabs)]
    if rail.stile_slot_w:
        for phi in STILE_ANGLES:
            loops.append(rect_at_polar(STILE_R, 90.0 + phi,
                                       SLOT_T, rail.stile_slot_w + FIT))
    return loops


def arm_cap_loops() -> list:
    """Horizontal plate closing the top of an arm box, between both panels."""
    d = math.degrees((T / 2.0) / ARM_CAP_R_OUT)
    half = (ARM_OUT_ANGLE - ARM_IN_ANGLE) / 2.0 - d
    a1, a2 = 90.0 - half, 90.0 + half
    tabs = [(R_IN + x0, R_IN + x1) for x0, x1 in ARM_CAP_TABS]
    outline = sector_loop(ARM_CAP_R_IN, ARM_CAP_R_OUT, a1, a2, tabs=tabs)
    mid_r = (ARM_CAP_R_IN + ARM_CAP_R_OUT) / 2.0
    vent = rotate_loop(stadium(-140.0, 140.0, 0.0, 32.0), (a1 + a2) / 2.0)
    cx, cy = polar(mid_r, (a1 + a2) / 2.0)
    return [outline, translate_loop(vent, cx, cy)]


def deck_loops(a1: float, a2: float) -> list:
    """One seat-deck sector, built centred on the axis for a tight nesting box."""
    mid = (a1 + a2) / 2.0
    half = (a2 - a1) / 2.0
    loops = [sector_loop(DECK_R_IN, DECK_R_OUT, 90.0 - half, 90.0 + half)]
    a1, a2 = -half, half
    for phi in [r - mid for r in RIB_ANGLES]:
        if not (a1 + 0.4 < phi < a2 - 0.4):
            continue
        for x0, x1 in RIB_TABS:
            loops.append(rect_at_polar(R_IN + (x0 + x1) / 2.0, 90.0 + phi,
                                       (x1 - x0) + FIT, SLOT_T))
    mid_r = R_IN + 400.0
    span = a2 - a1
    for frac in (0.28, 0.72):
        phi = a1 + span * frac
        vent = rotate_loop(stadium(-75.0, 75.0, 0.0, 27.0), 90.0 + phi)
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


def skin_loops(radius: float, sweep_deg: float, height: float) -> list:
    """A developed (unrolled) cylindrical skin panel, 4 mm flexible ply."""
    width = radius * math.radians(sweep_deg)
    return [rounded_rect(0.0, 0.0, width, height, 12.0)]


def build_parts() -> list:
    parts: list = []
    parts.append(Part("RIB", "RIB", len(RIB_ANGLES), rib_loops(),
                      "radial rib, drops onto the base rails"))
    parts.append(Part("ARM_IN", "ARM-PANEL-IN", 2, arm_panel_loops(inner=True),
                      "closes the seat structure, takes the rail end tabs"))
    parts.append(Part("ARM_OUT", "ARM-PANEL-OUT", 2, arm_panel_loops(inner=False),
                      "the end of the sofa, tied by the arm cap"))
    parts.append(Part("ARM_CAP", "ARM-CAP", 2, arm_cap_loops(),
                      "arm top plate between both arm panels"))
    for rail in RAILS:
        qty = 1 + PLINTH_LAYERS if rail.key.startswith("BASE") else 1
        note = f"z {rail.z0 + PLINTH_H:.0f}-{rail.z1 + PLINTH_H:.0f} mm, {rail.joint}"
        if qty > 1:
            note = f"3 laminae = {PLINTH_H + T:.0f} mm plinth, floor level"
        parts.append(Part(rail.key, rail.label, qty, rail_loops(rail), note))
    for i in range(3):
        parts.append(Part(f"DECK{i + 1}", f"SEAT-DECK-{i + 1}", 1,
                          deck_loops(DECK_SEAMS[i], DECK_SEAMS[i + 1]),
                          "rests on the ribs and both seat rails"))
    parts.append(Part("STILE", "BACK-STILE", len(STILE_ANGLES), stile_loops(),
                      "threads down through the three back rails"))

    skin_h_base = DECK_TOP + PLINTH_H
    skin_h_back = BACK_TOP - DECK_TOP
    parts.append(Part("SKIN_BASE_OUT", "SKIN-BASE-OUT", 1,
                      skin_loops(R_OUT, 2 * HALF_SWEEP, skin_h_base),
                      "wraps the outer face of the base", PLY4))
    parts.append(Part("SKIN_BASE_IN", "SKIN-BASE-IN", 1,
                      skin_loops(R_IN, 2 * HALF_SWEEP, skin_h_base),
                      "wraps the front face of the base", PLY4))
    parts.append(Part("SKIN_BACK", "SKIN-BACK", 1,
                      skin_loops(R_OUT, 2 * ARM_IN_ANGLE, skin_h_back),
                      "wraps the outer face of the backrest", PLY4))
    return parts
