"""Pebble Rubble sectional sofa - slot-and-tab MDF frame, geometry only.

Our own frame for the Pebble silhouette (reference: Anas Ghalion post,
3100 wide, two seat blobs 1350 + 1750, depth 1110 / 1130). Two modules, each
built on the tub-armchair engine, plus four "pebble" cushions on top:

* SEAT MODULE (left, right): superellipse "blob" in plan
    BASE-RING   floor ring
    BODY-RIB    radial ribs, outer edge bulging past both rings (round sides)
    SEAT-RING   wide ring at seat height; elastic webbing across its opening
* PEBBLE (back-L, end-L, back-R, arm-R): a dome over an oval footprint
    PLATE       flat oval, screwed and glued onto the seat ring
    RIB         transverse dome sections, slotted from the top
    SPINE       lengthwise dome section, slotted from the bottom; drops over
                the ribs (egg-crate) and tabs into the plate

Frame: x right, y front (0) to back, z up. Every piece is a flat plate placed
by a frame (origin, u, v): it is drawn in (u, v) and its thickness runs along
n = u x v, centred on the frame unless it is a flat plate (bottom at origin).
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

from shapely.geometry import Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

sys.path.append(str(Path(__file__).resolve().parents[1] / "curved-sofa"))

import joints as J  # noqa: E402

JOINT = J.JointSpec(t=18.0, fit=1.0, tool_d=6.0)
T = JOINT.t
F = JOINT.fit
SLOT_T = JOINT.slot_w            # 19
TAB_W = 40.0
TAB_SLOT = TAB_W + F             # 41
RELIEF_R = JOINT.relief_r

SHEET_W, SHEET_H = 2440.0, 1220.0
SHEET_MARGIN = 9.0
PART_GAP = 10.0

SEAT_TOP = 330.0                 # seat ring top; foam 100~120 -> seat ~440
SEAT_Z = SEAT_TOP - T
S_BASE, S_SEAT = 0.88, 0.95      # base ring / seat ring edge as a fraction of the belly
RIB_IN = 70.0                    # body rib inner end, inside the base ring edge
BASE_W = 130.0
SEAT_LIP = 15.0
SEAT_BAND = 190.0                # seat ring width at the narrowest
RIB_PITCH = 175.0                # body rib spacing along the belly
FOOT = 40.0                      # pebble rib height at its ends
PEB_E = 2.6                      # dome section exponent: 2 = ellipse, higher = fuller, flatter top cushion


@dataclass
class Module:
    key: str
    cx: float
    cy: float
    A: float                     # belly half width
    B: float                     # belly half depth
    N: float = 3.0

    def R(self, th):
        c, s = abs(math.cos(math.radians(th))), abs(math.sin(math.radians(th)))
        return ((c / self.A) ** self.N + (s / self.B) ** self.N) ** (-1.0 / self.N)


@dataclass
class Pebble:
    key: str
    module: str
    px: float
    py: float
    a: float                     # plate half length (along phi)
    b: float                     # plate half width
    phi: float                   # long axis, deg from +x
    H: float                     # dome height above the plate top
    n_ribs: int
    N: float = 2.4


# finished dims from the reference drawing, frame = finished - foam
MODULES = [Module("L", 675.0, 555.0, 640.0, 520.0), Module("R", 2225.0, 565.0, 840.0, 530.0)]
PEBBLES = [
    Pebble("BL", "L", 830.0, 830.0, 460.0, 180.0, 0.0, 300.0, 5),     # back left, 1056 x 433
    Pebble("EL", "L", 225.0, 640.0, 160.0, 150.0, 90.0, 250.0, 2),    # end left, 403 x 386
    Pebble("BR", "R", 1950.0, 820.0, 530.0, 205.0, 0.0, 320.0, 6),    # back right, 1215 x 495
    Pebble("AR", "R", 2830.0, 590.0, 330.0, 185.0, -60.0, 270.0, 3),  # arm right, 457 x 750
]
MOD = {m.key: m for m in MODULES}

Loop = list


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def to_loop(poly: Polygon) -> Loop:
    poly = orient(poly.simplify(0.001), 1.0)
    return [(round(x, 4), round(y, 4), 0.0) for x, y in list(poly.exterior.coords)[:-1]]


def finish(outline: Polygon, holes: list):
    loop, n = J.relieve_inside_corners(to_loop(outline), RELIEF_R)
    return [loop] + holes, n


def rect_mortise(cx, cy, ang_deg, length):
    """19 wide mortise, `length` long along ang (already includes fit)."""
    hx, hy = length / 2, SLOT_T / 2
    loop = J.dogbone_rect(-hx, -hy, hx, hy, RELIEF_R)
    c, s = math.cos(math.radians(ang_deg)), math.sin(math.radians(ang_deg))
    return [(cx + x * c - y * s, cy + x * s + y * c, b) for x, y, b in loop]


def module_curve(m: Module, scale, offset, n=240):
    return [(m.cx + (scale * m.R(a) + offset) * math.cos(math.radians(a)),
             m.cy + (scale * m.R(a) + offset) * math.sin(math.radians(a)))
            for a in (360.0 * i / n for i in range(n))]


def rib_angles(m: Module):
    """Body rib angles at even spacing along the belly in the first quadrant,
    mirrored into the other three (so mirrored ribs share one profile)."""
    n = 4000
    th = [90.0 * i / n for i in range(n + 1)]
    pts = [(m.R(a) * math.cos(math.radians(a)), m.R(a) * math.sin(math.radians(a))) for a in th]
    s = [0.0]
    for p, q in zip(pts, pts[1:]):
        s.append(s[-1] + math.dist(p, q))
    quarter = s[-1]
    k = max(1, round(quarter / RIB_PITCH))
    q = []
    for j in range(k):
        target = quarter * (j + 0.5) / k
        i = next(i for i, v in enumerate(s) if v >= target)
        q.append(round(th[i], 4))
    return sorted({a for x in q for a in (x, 180.0 - x, 180.0 + x, 360.0 - x)})


def belly(z):
    t = z / SEAT_Z
    tm = 1.0 / (1.0 + math.sqrt((1.0 - S_SEAT) / (1.0 - S_BASE)))
    k = (1.0 - S_BASE) / tm ** 2
    return 1.0 - k * (t - tm) ** 2


def body_in(m, th): return S_BASE * m.R(th) - RIB_IN


def body_tab(m, th):
    r0 = body_in(m, th) + 8.0
    return r0, r0 + TAB_W


def radial_mortise(m, th, r0, r1):
    rc = (r0 + r1) / 2
    c, s = math.cos(math.radians(th)), math.sin(math.radians(th))
    return rect_mortise(m.cx + rc * c, m.cy + rc * s, th, r1 - r0 + F)


# --------------------------------------------------------------------------
# seat module parts
# --------------------------------------------------------------------------

def base_ring(m):
    outer = Polygon(module_curve(m, S_BASE, 0.0))
    inner = Polygon(module_curve(m, S_BASE, -BASE_W))
    holes = [radial_mortise(m, a, *body_tab(m, a)) for a in rib_angles(m)]
    loop = to_loop(outer)
    return [loop, [(x, y, 0.0) for x, y in reversed(list(inner.exterior.coords)[:-1])]] + holes, 0


def seat_ring(m):
    outer = Polygon(module_curve(m, S_SEAT, SEAT_LIP))
    inner = Polygon(module_curve(m, S_SEAT, SEAT_LIP - SEAT_BAND))
    holes = [radial_mortise(m, a, *body_tab(m, a)) for a in rib_angles(m)]
    return [to_loop(outer), [(x, y, 0.0) for x, y in reversed(list(inner.exterior.coords)[:-1])]] + holes, 0


def body_rib(m, th):
    """Drawn in (r, z), r from the module centre; relieved like the tub."""
    r_in = body_in(m, th)
    t0, t1 = body_tab(m, th)
    rr = m.R(th)
    pts = [(r_in, T), (t0, T), (t0, 0.0), (t1, 0.0), (t1, T)]
    for i in range(29):
        z = T + (SEAT_Z - T) * i / 28
        pts.append((belly(z) * rr, z))
    pts += [(t1, SEAT_Z), (t1, SEAT_TOP), (t0, SEAT_TOP), (t0, SEAT_Z), (r_in, SEAT_Z)]
    return finish(Polygon(pts), [])


def type_angle(th):
    t = th % 180.0
    return round(min(t, 180.0 - t), 4)


# --------------------------------------------------------------------------
# pebbles: dome over a superellipse footprint, local axes e (long), t (across)
# --------------------------------------------------------------------------

def half_width(p: Pebble, s):
    u = min(1.0, abs(s) / p.a)
    return p.b * (1.0 - u ** p.N) ** (1.0 / p.N)


def bulge(u):
    """Cushion section: 1 at the middle, 0 at |u| = 1, full shoulders."""
    return max(0.0, 1.0 - min(1.0, abs(u)) ** PEB_E) ** (1.0 / PEB_E)


def dome_h(p: Pebble, s):
    return FOOT + (p.H - FOOT) * bulge(s / p.a)


def stations(p: Pebble):
    lim = 0.72 * p.a
    if p.n_ribs == 1:
        return [0.0]
    return [-lim + 2 * lim * k / (p.n_ribs - 1) for k in range(p.n_ribs)]


def axes(p: Pebble):
    c, s = math.cos(math.radians(p.phi)), math.sin(math.radians(p.phi))
    return (c, s), (-s, c)


def to_world(p: Pebble, s, t):
    (ex, ey), (tx, ty) = axes(p)
    return p.px + s * ex + t * tx, p.py + s * ey + t * ty


def plate_outline(p: Pebble):
    pts = []
    for i in range(160):
        a = 2 * math.pi * i / 160
        c, s = math.cos(a), math.sin(a)
        su = math.copysign(abs(c) ** (2 / p.N), c) * p.a
        tu = math.copysign(abs(s) ** (2 / p.N), s) * p.b
        pts.append(to_world(p, su, tu))
    return Polygon(pts)


def rib_tab_spans(p: Pebble, s):
    w = half_width(p, s) - 8.0
    c = max(SLOT_T / 2 + RELIEF_R + 12 + TAB_W / 2, w * 0.55)
    return [(-c - TAB_W / 2, -c + TAB_W / 2), (c - TAB_W / 2, c + TAB_W / 2)]


def spine_tab_spans(p: Pebble):
    st = stations(p)
    ends = [-0.9 * p.a] + st + [0.9 * p.a]
    out = []
    for a, b in zip(ends, ends[1:]):
        mid = (a + b) / 2
        if b - a > TAB_W + 2 * (SLOT_T / 2 + RELIEF_R + 8):
            out.append((mid - TAB_W / 2, mid + TAB_W / 2))
    return out


def pebble_rib(p: Pebble, s):
    """Drawn in (t, z), z from the plate top."""
    w = half_width(p, s) - 8.0
    h = dome_h(p, s)
    pts = [(-w + t_ * 2 * w / 40, FOOT + (h - FOOT) * bulge((-w + t_ * 2 * w / 40) / w))
           for t_ in range(41)]
    body = Polygon([(-w, 0.0)] + pts + [(w, 0.0)])
    tabs = [box(a, -T, b, 1.0) for a, b in rib_tab_spans(p, s)]
    poly = unary_union([body] + tabs)
    poly = poly.difference(box(-SLOT_T / 2, h / 2, SLOT_T / 2, h + 5))      # spine slot from the top
    return finish(poly, [])


def spine(p: Pebble):
    """Drawn in (s, z)."""
    L = 0.9 * p.a
    pts = [(-L + k * 2 * L / 60, dome_h(p, -L + k * 2 * L / 60)) for k in range(61)]
    body = Polygon([(-L, 0.0)] + pts + [(L, 0.0)])
    tabs = [box(a, -T, b, 1.0) for a, b in spine_tab_spans(p)]
    poly = unary_union([body] + tabs)
    for s in stations(p):
        poly = poly.difference(box(s - SLOT_T / 2, -1.0, s + SLOT_T / 2, dome_h(p, s) / 2))
    return finish(poly, [])


def plate(p: Pebble):
    holes = []
    (ex, ey), (tx, ty) = axes(p)
    for s in stations(p):
        for a, b in rib_tab_spans(p, s):
            cx, cy = to_world(p, s, (a + b) / 2)
            holes.append(rect_mortise(cx, cy, p.phi + 90.0, b - a + F))
    for a, b in spine_tab_spans(p):
        cx, cy = to_world(p, (a + b) / 2, 0.0)
        holes.append(rect_mortise(cx, cy, p.phi, b - a + F))
    return [to_loop(plate_outline(p))] + holes, 0


# --------------------------------------------------------------------------
# parts and placements
# --------------------------------------------------------------------------

@dataclass
class Part:
    key: str
    label: str
    qty: int
    loops: list
    note: str
    group: str
    place: list = field(default_factory=list)    # [(origin, u, v, centred)]
    num: int = 0
    relieved: int = 0


Z = (0.0, 0.0, 1.0)
GROUP_ORDER = ["BASE", "BODY", "SEAT", "PLATE", "PRIB", "SPINE"]


def build_parts():
    P = []

    def add(key, label, made, note, group, place):
        loops, n = made
        P.append(Part(key, label, len(place), loops, note, group, place, relieved=n))

    for m in MODULES:
        flat = lambda z: [((0.0, 0.0, z), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), False)]
        add(f"BASE{m.key}", f"BASE-RING-{m.key}", base_ring(m), "floor ring", "BASE", flat(0.0))
        add(f"SEAT{m.key}", f"SEAT-RING-{m.key}", seat_ring(m), "seat ring, webbing across", "SEAT", flat(SEAT_Z))
        groups = {}
        for a in rib_angles(m):
            groups.setdefault(type_angle(a), []).append(a)
        for i, (_, angs) in enumerate(sorted(groups.items())):
            place = [((m.cx, m.cy, 0.0), (math.cos(math.radians(a)), math.sin(math.radians(a)), 0.0), Z, True)
                     for a in angs]
            add(f"BODY{m.key}{i:02d}", f"RIB-{m.key}{chr(65 + i)}", body_rib(m, angs[0]),
                f"body rib at {', '.join(f'{x:g}' for x in angs)} deg", "BODY", place)
    for p in PEBBLES:
        z0 = SEAT_TOP + T          # plate top
        add(f"PL{p.key}", f"PEBBLE-{p.key}-PLATE", plate(p), "screwed + glued on the seat ring",
            "PLATE", [((0.0, 0.0, SEAT_TOP), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), False)])
        (ex, ey), (tx, ty) = axes(p)
        st = stations(p)
        # mirror-symmetric stations share a profile
        seen = {}
        for s in st:
            seen.setdefault(round(abs(s), 3), []).append(s)
        for j, (_, ss) in enumerate(sorted(seen.items())):
            place = [((*to_world(p, s, 0.0), z0), (tx, ty, 0.0), Z, True) for s in ss]
            add(f"PR{p.key}{j}", f"PEBBLE-{p.key}-RIB{j + 1}", pebble_rib(p, ss[0]),
                f"dome section at {', '.join(f'{x:+.0f}' for x in ss)} mm", "PRIB", place)
        add(f"SP{p.key}", f"PEBBLE-{p.key}-SPINE", spine(p), "drops over the ribs", "SPINE",
            [((p.px, p.py, z0), (ex, ey, 0.0), Z, True)])
    for n, part in enumerate(P, 1):
        part.num = n
    return P


def instances(parts=None):
    """(part, k, origin, u, v, centred) for every piece."""
    out = []
    for p in parts or build_parts():
        for k, (o, u, v, c) in enumerate(p.place, 1):
            out.append((p, k, o, u, v, c))
    return out
