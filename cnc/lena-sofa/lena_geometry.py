"""Lena 3-seat sofa - slot-and-tab MDF frame, geometry only.

Our own frame for the Lena silhouette (four arched back cushions over a
straight seat, rounded drum arms). Every part is a flat 18 mm plate in one
of three orthogonal planes, so the whole frame is an egg-crate:

* ARM-OUTER / ARM-INNER  side panels (YZ plane), two per arm
* ARM-SPACER   tombstone plates (XZ) between the two arm panels; below the
               panel tops they tab into both panels, above they widen to the
               full arm and sit on the panel edges - the round "drum" top
* RIB          seat ribs (YZ) with a back post, between the arms
* RAIL         front / mid / back seat rails (XZ), cross-halved into the ribs
               and tabbed into the inner arm panels
* DECK         two seat decks (XY) on the rib and rail tops, in front of
               the back posts
* BACK-ARCH    four tombstone back panels (XZ), one per bay, tabbed into the
               posts either side - the Lena arches

Assembly order (each step only moves parts along one axis into free space):
back chain (ribs and arches slid together in x) -> rails dropped into the
rib halvings -> inner arm panels slid in x onto the rail and end-arch tabs ->
spacers -> outer arm panels -> decks dropped onto the rib tabs.

Frame: x across the sofa (left arm at x = 0), y front (0) to back, z up.
Each part is drawn in world coordinates of its own plane: (y, z) for YZ,
(x, z) for XZ, (x, y) for XY. ``instances()`` gives the through-thickness
position of every piece; STEP, 3D checks and renders all use it.

Joint rules follow the bought Tokyo pack: 18 mm board, 19 mm slots (1 mm
clearance), 40 mm tabs in 41 mm mortises, 10 mm part spacing.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

from shapely.geometry import Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

sys.path.append(str(Path(__file__).resolve().parents[1] / "curved-sofa"))  # shared code

import joints as J  # noqa: E402

JOINT = J.JointSpec(t=18.0, fit=1.0, tool_d=6.0)
T = JOINT.t
F = JOINT.fit
SLOT_T = JOINT.slot_w            # 19 mm
TAB_W = 40.0
TAB_SLOT = TAB_W + F             # 41 mm
RELIEF_R = JOINT.relief_r

SHEET_W, SHEET_H = 2440.0, 1220.0
SHEET_MARGIN = 9.0
PART_GAP = 10.0

# ---- overall -------------------------------------------------------------
W = 2200.0                       # overall frame width
ARM_W = 220.0                    # one arm, outer face to inner face
D = 860.0                        # frame depth
SEAT_TOP = 330.0                 # deck top; ~450 with a 120 mm cushion
DECK_Z = SEAT_TOP - T            # rib / rail tops
ARM_TOP = 460.0                  # arm panel top; spacer drum rises above it
DRUM_R = ARM_W / 2.0             # drum top radius -> arms 570
POST_Y = 630.0                   # back posts start here
POST_TOP = 720.0
ARCH_TOP = 800.0                 # arch crowns stand 80 mm above the posts
FOOT_LEN = 120.0                 # feet front and back, plinth recess between
PLINTH = 40.0
FRONT_R = 100.0                  # arm front-top round
BACK_R = 80.0                    # post back-top round

SEAT_X0, SEAT_X1 = ARM_W, W - ARM_W          # 220 .. 1980
BAYS = 4
BAY = (SEAT_X1 - SEAT_X0 - (BAYS - 1) * T) / BAYS          # 426.5 clear
RIB_X = [SEAT_X0 + k * BAY + (k - 1) * T for k in range(1, BAYS)]   # rib x0
SPLIT_X = RIB_X[1] + T / 2                   # deck split on the middle rib

# rails: (key, y0, z_bottom, tab centres into the arm-inner panels)
RAILS = [("FRONT", 30.0, 50.0, (120.0, 250.0)),
         ("MID", 340.0, 150.0, (231.0,)),
         ("BACK", 600.0, 100.0, (160.0, 260.0))]
DECK_TABS = [(150.0, 190.0), (450.0, 490.0)]   # rib top tabs (y spans)
DECK_Y1 = POST_Y - 5.0                       # deck stops in front of the posts

ARCH_Y = 660.0
ARCH_Z0 = SEAT_TOP                           # held by its 4 tabs, level with the deck top
ARCH_TABS_L = (360.0, 500.0)                 # tab centres, left edge
ARCH_TABS_R = (430.0, 560.0)                 # right edge, staggered

SPACER_Y = [90.0, 300.0, 510.0]
SPACER_Z0 = 60.0
SPACER_TABS = (160.0, 360.0)

Loop = list
ARC_SEG = 24


# --------------------------------------------------------------------------
# shapely <-> loops
# --------------------------------------------------------------------------

def arc_pts(cx, cy, r, a0, a1, n=ARC_SEG):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def to_loop(poly: Polygon) -> Loop:
    poly = orient(poly.simplify(0.001), 1.0)
    pts = list(poly.exterior.coords)[:-1]
    return [(round(x, 4), round(y, 4), 0.0) for x, y in pts]


def mortise(u0, u1, v0, v1) -> Loop:
    """Closed mortise with dogbones, exact u0..u1 x v0..v1 (already sized)."""
    return J.dogbone_rect(u0, v0, u1, v1, RELIEF_R)


def mort_for_tab(uc0, uc1, vc) -> Loop:
    """Mortise for a T-thick plate occupying u in [uc0, uc1] with a 40 mm tab
    centred at v = vc."""
    return mortise(uc0 - F / 2, uc1 + F / 2, vc - TAB_SLOT / 2, vc + TAB_SLOT / 2)


def rounded_hole(u0, v0, u1, v1, r=30.0) -> Loop:
    """Lightening / breathing hole: rounded rectangle (no square corners to relieve)."""
    pts = (arc_pts(u1 - r, v0 + r, r, -90, 0, 8)[:-1] + arc_pts(u1 - r, v1 - r, r, 0, 90, 8)[:-1]
           + arc_pts(u0 + r, v1 - r, r, 90, 180, 8)[:-1] + arc_pts(u0 + r, v0 + r, r, 180, 270, 8)[:-1])
    return [(round(x, 4), round(y, 4), 0.0) for x, y in pts]


# lightening holes in every rib: under the seat between the rails, and in the post
RIB_HOLES = [(80.0, 75.0, 310.0, 150.0), (390.0, 75.0, 570.0, 170.0), (720.0, 380.0, 810.0, 640.0)]
# lightening holes in the arm panels, clear of every spacer / rail / arch mortise
ARM_HOLES = [(130.0, 75.0, 280.0, 320.0), (375.0, 75.0, 490.0, 320.0), (720.0, 380.0, 810.0, 640.0)]
# breathing holes in each deck, between the rails and clear of the rib line
DECK_HOLES = [(290.0, 95.0, 590.0, 300.0), (720.0, 95.0, 1030.0, 300.0),
              (290.0, 400.0, 590.0, 560.0), (720.0, 400.0, 1030.0, 560.0)]


def finish(outline: Polygon, holes: list):
    loop, n = J.relieve_inside_corners(to_loop(outline), RELIEF_R)
    return [loop] + holes, n


# --------------------------------------------------------------------------
# profiles
# --------------------------------------------------------------------------

def side_outline(top_front: float, front_round: float) -> Polygon:
    """YZ outline shared by arms and ribs: feet, plinth recess, post at the back."""
    pts = [(0.0, 0.0), (FOOT_LEN, 0.0), (FOOT_LEN, PLINTH), (D - FOOT_LEN, PLINTH),
           (D - FOOT_LEN, 0.0), (D, 0.0)]
    pts += arc_pts(D - BACK_R, POST_TOP - BACK_R, BACK_R, 0.0, 90.0)
    pts += [(POST_Y, POST_TOP), (POST_Y, top_front)]
    if front_round > 0:
        pts += arc_pts(front_round, top_front - front_round, front_round, 90.0, 180.0)
    else:
        pts += [(0.0, top_front)]
    return Polygon(pts)


def rail_slot_in_rib(y0, zb) -> Polygon:
    zmid = (zb + DECK_Z) / 2
    return box(y0 - F / 2, zmid, y0 + T + F / 2, DECK_Z + 1.0)


def rib(with_tabs: bool):
    poly = side_outline(DECK_Z, 0.0)
    if with_tabs:
        poly = unary_union([poly] + [box(a, DECK_Z - 1.0, b, SEAT_TOP) for a, b in DECK_TABS])
    for _, y0, zb, _ in RAILS:
        poly = poly.difference(rail_slot_in_rib(y0, zb))
    holes = [mort_for_tab(ARCH_Y, ARCH_Y + T, z) for z in ARCH_TABS_L + ARCH_TABS_R]
    holes += [rounded_hole(*h) for h in RIB_HOLES]
    return finish(poly, holes)


def arm_panel(side: str = ""):
    """side '' = outer panel, 'L' / 'R' = inner panel of that arm (the end
    arch tabs in at the left or right edge heights)."""
    poly = side_outline(ARM_TOP, FRONT_R)
    holes = [mort_for_tab(y, y + T, z) for y in SPACER_Y for z in SPACER_TABS]
    if side:
        holes += [mort_for_tab(y0, y0 + T, z) for _, y0, _, zs in RAILS for z in zs]
        zs = ARCH_TABS_L if side == "L" else ARCH_TABS_R
        holes += [mort_for_tab(ARCH_Y, ARCH_Y + T, z) for z in zs]
    holes += [rounded_hole(*h) for h in ARM_HOLES]
    return finish(poly, holes)


def rail(y0, zb, tab_zs):
    """XZ, x from the left arm-inner outer face to the right one."""
    body = box(SEAT_X0, zb, SEAT_X1, DECK_Z)
    tabs = [box(SEAT_X0 - T, z - TAB_W / 2, SEAT_X0 + 1, z + TAB_W / 2) for z in tab_zs]
    tabs += [box(SEAT_X1 - 1, z - TAB_W / 2, SEAT_X1 + T, z + TAB_W / 2) for z in tab_zs]
    poly = unary_union([body] + tabs)
    zmid = (zb + DECK_Z) / 2
    for x0 in RIB_X:
        poly = poly.difference(box(x0 - F / 2, zb - 1.0, x0 + T + F / 2, zmid))
    return finish(poly, [])


def deck():
    """Left deck, XY. The right deck is the same part, mirrored."""
    poly = box(SEAT_X0, 0.0, SPLIT_X, DECK_Y1)
    holes = [mortise(RIB_X[0] - F / 2, RIB_X[0] + T + F / 2, a - F / 2, b + F / 2)
             for a, b in DECK_TABS]
    holes += [rounded_hole(*h, r=40.0) for h in DECK_HOLES]
    return finish(poly, holes)


def bay_x(k):
    x0 = SEAT_X0 if k == 0 else RIB_X[k - 1] + T
    x1 = SEAT_X1 if k == BAYS - 1 else RIB_X[k]
    return x0, x1


def arch():
    """First bay's arch, XZ; every bay is the same width, so one part."""
    x0, x1 = bay_x(0)
    a, b = x0 + F / 2, x1 - F / 2
    r = (b - a) / 2
    pts = [(a, ARCH_Z0), (b, ARCH_Z0)] + arc_pts(a + r, ARCH_TOP - r, r, 0.0, 180.0)
    body = Polygon(pts)
    tabs = [box(x0 - T, z - TAB_W / 2, a + 1, z + TAB_W / 2) for z in ARCH_TABS_L]
    tabs += [box(b - 1, z - TAB_W / 2, x1 + T, z + TAB_W / 2) for z in ARCH_TABS_R]
    return finish(unary_union([body] + tabs), [])


def spacer():
    """Left arm's spacer, XZ (x 0 .. ARM_W)."""
    xi0, xi1 = T + F / 2, ARM_W - T - F / 2
    body = box(xi0, SPACER_Z0, xi1, ARM_TOP + 1)
    cap = Polygon([(0.0, ARM_TOP), (ARM_W, ARM_TOP)] +
                  arc_pts(DRUM_R, ARM_TOP, DRUM_R, 0.0, 180.0, 36))
    tabs = [box(0.0, z - TAB_W / 2, xi0 + 1, z + TAB_W / 2) for z in SPACER_TABS]
    tabs += [box(xi1 - 1, z - TAB_W / 2, ARM_W, z + TAB_W / 2) for z in SPACER_TABS]
    return finish(unary_union([body, cap] + tabs), [])


# --------------------------------------------------------------------------
# parts and their placements
# --------------------------------------------------------------------------

@dataclass
class Part:
    key: str
    label: str
    qty: int
    loops: list = field(default_factory=list)
    note: str = ""
    plane: str = "YZ"
    group: str = ""                     # assembly layer
    place: list = field(default_factory=list)   # (thickness offset, du, mirror_about)
    num: int = 0
    relieved: int = 0


def build_parts() -> list:
    P = []

    def add(key, label, made, note, plane, group, place):
        loops, n = made
        P.append(Part(key, label, len(place), loops, note, plane, group, place, relieved=n))

    add("RIBA", "RIB-A", rib(True), "seat rib + back post, deck tabs",
        "YZ", "BACK", [(RIB_X[0], 0, None), (RIB_X[2], 0, None)])
    add("RIBB", "RIB-B", rib(False), "middle rib + post, under the deck split",
        "YZ", "BACK", [(RIB_X[1], 0, None)])
    add("ARCH", "BACK-ARCH", arch(), "Lena back arch, one per bay, tabbed into the posts",
        "XZ", "BACK", [(ARCH_Y, bay_x(k)[0] - bay_x(0)[0], None) for k in range(BAYS)])
    for key, y0, zb, zs in RAILS:
        add(f"R{key[:3]}", f"RAIL-{key}", rail(y0, zb, zs),
            f"seat rail, halved into the ribs, tabs into the arms", "XZ", "RAILS",
            [(y0, 0, None)])
    add("ARML", "ARM-INNER-L", arm_panel("L"), "left inner arm panel: rails, spacers, end arch",
        "YZ", "INNER", [(ARM_W - T, 0, None)])
    add("ARMR", "ARM-INNER-R", arm_panel("R"), "right inner arm panel: rails, spacers, end arch",
        "YZ", "INNER", [(SEAT_X1, 0, None)])
    add("SPAC", "ARM-SPACER", spacer(), "joins the arm panels, round drum top",
        "XZ", "SPACERS", [(y, dx, None) for dx in (0.0, W - ARM_W) for y in SPACER_Y])
    add("ARMO", "ARM-OUTER", arm_panel(), "outer arm panel, spacer mortises",
        "YZ", "OUTER", [(0.0, 0, None), (W - T, 0, None)])
    add("DECK", "SEAT-DECK", deck(), "seat deck on rib and rail tops (2nd one flipped)",
        "XY", "DECK", [(DECK_Z, 0, None), (DECK_Z, 0, SPLIT_X)])
    for n, p in enumerate(P, 1):
        p.num = n
    return P


GROUP_ORDER = ["BACK", "RAILS", "INNER", "SPACERS", "OUTER", "DECK"]


def mirror_loops(loops, c):
    """Mirror about u = c. A reflection reverses the winding, so every bulge
    changes sign; the vertex order is kept (each bulge stays with its segment)."""
    return [[(2 * c - x, y, -b) for x, y, b in l] for l in loops]


def instances(parts=None):
    """(part, k, plane, w0, loops) for every piece; loops in world (u, v) of
    the plane, w0..w0+T the through-thickness position."""
    out = []
    for p in parts or build_parts():
        for k, (w0, du, mir) in enumerate(p.place, 1):
            loops = [[(x + du, y, b) for x, y, b in l] for l in p.loops]
            if mir is not None:
                loops = mirror_loops(loops, mir)
            out.append((p, k, p.plane, w0, loops))
    return out


def to3d(plane, w, u, v):
    if plane == "YZ":
        return (w, u, v)
    if plane == "XZ":
        return (u, w, v)
    return (u, v, w)
