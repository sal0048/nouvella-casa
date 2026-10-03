"""Kerf-bent cone - structural core, formers and shell, geometry only.

Construction
------------
* CORE-1A/1B, CORE-2A/2B  the structure. In each cone section two 15 mm
                        plates cross on the axis (half-lap), with tabs top and
                        bottom into mortises in the formers (Tokyo joints).
                        Level 2 is turned 45 degrees to level 1.
* FORMER-BASE/JOINT-LO/JOINT-UP/TOP  full discs. They carry the core tabs
                        and hold the shell round. JOINT-LO and JOINT-UP are
                        glued face to face at the joint.
* SHELL                 one flat annular sector of 18 mm board with radial
                        kerfs pocketed into the BACK face; it rolls around
                        the skeleton into the cone and is glued to the
                        former edges. It is the skin, not the structure.
                        (ONE_SHELL = False splits it in two at Z_SPLIT with
                        a COLLAR over the joint, as in the reference video.)

No table top: FORMER-TOP closes the cone flush at the top.

Why straight, parallel kerfs work on a cone
-------------------------------------------
Bent about its skin, a board of kerfed depth d must shorten its back face by
2*pi*d*cos(alpha) around the cone (alpha = half apex angle), and that amount
is the same at every height. Kerfs of constant width, running along the
cone generatrices (radial lines of the flat sector), therefore close by the
same amount along their whole length.

Frame: z up from the floor, cone axis = z. The pattern is the development of
the show (outer) face, which is the layer that does not stretch.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "curved-sofa"))  # shared code, lower priority

import joints as J  # noqa: E402

# --------------------------------------------------------------------------
# Parameters - provenance lives in package.py / parameters.json
# --------------------------------------------------------------------------
T_BOARD = 17.0           # core, formers, collar (V10: the workshop board is 17 mm)
T_SHELL = 17.0           # kerf-bent shell board
SKIN = 2.0               # material left on the show face under each kerf (V9: 2.5, cracked)
TOOL_D = 6.0             # kerf width = cutter diameter
KERF_LAND = 4.0          # least wood between two kerfs, at the narrow (top) edge
KERF_PITCH_MIN = TOOL_D + KERF_LAND      # 10 mm: least pitch, at the narrow edge
KERF_OVERRUN = 0.1       # the cutter CENTRE runs this far past a curved edge (V10: was 3)
KERF_TRIM = 0.5          # pocket drawn this far inside the outline (nesting sees the outline);
                         # build.py adds KERF_TRIM + TOOL_D/2 + KERF_OVERRUN so the round
                         # end of the slot clears the edge: no full-thickness lip at kerf ends

R_BOT = 200.0            # cone outer radius at the floor (base 400 mm)
R_TOP = 80.0             # cone outer radius at the top (top 160 mm = 40% of base, as the post)
H_CONE = 450.0           # cone height
Z_SPLIT = 225.0          # mid formers: joint between the two core levels
ONE_SHELL = True         # one kerfed sector for the whole cone (no seam, no collar)

FIT = 0.5                # radial clearance formers / collar
COLLAR_W = 30.0

JOINT = J.JointSpec(t=T_BOARD, fit=1.0, tool_d=TOOL_D)   # Tokyo rule: slot t + 1
TAB_W = 40.0             # core tab length (Tokyo)
TAB_MIN = 15.0           # shortest tab worth keeping near the narrow top
TAB_CLEAR = 5.0          # plate material between a tab root relief and the half-lap
MORTISE_WEB = 5.0        # former material outside a mortise
CORE_FIT = 1.0           # core plate edge inside the shell

SHEET_W, SHEET_H = 2440.0, 1220.0
SHEET_MARGIN = 10.0
PART_GAP = 10.0

# --------------------------------------------------------------------------
# Cone
# --------------------------------------------------------------------------
SLANT = math.hypot(H_CONE, R_BOT - R_TOP)
SIN_A = (R_BOT - R_TOP) / SLANT          # alpha = half apex angle
COS_A = H_CONE / SLANT
THETA = 2.0 * math.pi * SIN_A            # developed sector angle (rad)
DEPTH = T_SHELL - SKIN                   # kerf pocket depth


def R(z: float) -> float:
    """Outer (show face) radius of the cone at height z."""
    return R_BOT + (R_TOP - R_BOT) * z / H_CONE


def R_in(z: float) -> float:
    """Inner (back face) radius at height z, measured horizontally."""
    return R(z) - T_SHELL / COS_A


def s_of(z: float) -> float:
    """Developed radius (distance from the cone apex along the face)."""
    return R(z) / SIN_A


def closure_total() -> float:
    """Back-face shortening needed around the cone (mm), any height."""
    return 2.0 * math.pi * DEPTH * COS_A


# --------------------------------------------------------------------------
# Parts
# --------------------------------------------------------------------------
Loop = list


@dataclass
class Part:
    key: str
    label: str
    qty: int
    loops: list = field(default_factory=list)   # [outline, holes..., kerfs...]
    note: str = ""
    material: str = ""                           # board thickness, groups the sheets
    n_holes: int = 0                             # loops[1:1+n_holes] are through holes
    kerfs: int = 0                               # loops[1+n_holes:] are kerf pockets
    num: int = 0
    relieved: int = 0
    meta: dict = field(default_factory=dict)


def circle(r: float, cx=0.0, cy=0.0) -> Loop:
    """Closed circle as two bulge arcs, CCW."""
    return [(cx + r, cy, 1.0), (cx - r, cy, 1.0)]


def ring(r_out: float, r_in: float) -> list:
    inner = [(-r_in, 0.0, -1.0), (r_in, 0.0, -1.0)]   # CW hole
    return [circle(r_out), inner]


def sector(s_in: float, s_out: float, theta: float) -> Loop:
    """Annular sector, apex at origin, symmetric about +y, CCW."""
    a0, a1 = math.pi / 2 - theta / 2, math.pi / 2 + theta / 2
    b = math.tan(theta / 4.0)
    p = lambda s, a: (s * math.cos(a), s * math.sin(a))
    return [(*p(s_in, a0), 0.0), (*p(s_out, a0), b),
            (*p(s_out, a1), 0.0), (*p(s_in, a1), -b)]


def kerf_count(s_in: float) -> int:
    """Hinges round the cone: the kerfs plus the seam, which bends like one."""
    return math.floor(THETA * s_in / (TOOL_D + KERF_LAND))


def hinge_angle(s_in: float) -> float:
    """Bend each hinge takes (rad). Every kerf is a generatrix of the cone,
    so this is the same at every height: a kerf must run the full length.
    (V9 added short kerfs on the wide half; where they stopped, the hinge
    angle halved abruptly and the shell cracked there.)"""
    return 2.0 * math.pi * COS_A / kerf_count(s_in)


def seam_relief(s_in: float) -> float:
    """Back-face strip taken off each seam edge so the two edges close like
    a kerf. Needed: half a hinge about the show face, T x tan(hinge/2)
    (1.1 mm). Cut as the cutter centred on the edge line, so the pocket
    leaves the part by half a cutter only, like every kerf end: 3 mm."""
    need = T_SHELL * math.tan(hinge_angle(s_in) / 2)
    return max(need + 0.1, TOOL_D / 2)


def kerf_layout(s_in: float, s_out: float) -> list:
    """(angle, r0, r1) of every kerf: all full length, equal angles, the
    seam counted as one hinge (half a pitch of wood each side of it)."""
    a0 = math.pi / 2 - THETA / 2
    n = kerf_count(s_in)
    return [(a0 + THETA * k / n, s_in, s_out) for k in range(1, n)]


def seam_rects(s_in: float, s_out: float, trim: float = KERF_TRIM) -> list:
    """Seam-edge pockets, back face, same depth as the kerfs: seam_relief()
    inside each straight edge and run out past it so the strip is one
    cutter wide (build.py extends them through both curved edges too)."""
    w_in, w_out = seam_relief(s_in), TOOL_D - seam_relief(s_in)
    out = []
    for a, sign in ((math.pi / 2 - THETA / 2, 1.0), (math.pi / 2 + THETA / 2, -1.0)):
        c, s = math.cos(a), math.sin(a)
        nx, ny = -s * sign, c * sign                # into the part
        r0, r1 = s_in + trim, s_out - trim
        pts = [(r0, -w_out), (r0, w_in), (r1, w_in), (r1, -w_out)]   # kerf_rects corner order
        out.append([(r * c + d * nx, r * s + d * ny, 0.0) for r, d in pts])
    return out


def kerf_rects(s_in: float, s_out: float, trim: float = KERF_TRIM) -> list:
    """Kerf pockets as rectangles along the generatrices, kept KERF_TRIM
    inside the outline for nesting (build.py extends them through both
    curved edges)."""
    hw = TOOL_D / 2.0
    out = []
    for a, r0, r1 in kerf_layout(s_in, s_out):
        c, s = math.cos(a), math.sin(a)
        r0 = r0 + trim if r0 == s_in else r0
        r1 = r1 - trim
        nx, ny = -s, c
        out.append([(r0 * c + hw * nx, r0 * s + hw * ny, 0.0),
                    (r0 * c - hw * nx, r0 * s - hw * ny, 0.0),
                    (r1 * c - hw * nx, r1 * s - hw * ny, 0.0),
                    (r1 * c + hw * nx, r1 * s + hw * ny, 0.0)])
    return out


def shell(key, label, za, zb) -> Part:
    s_out, s_in = s_of(za), s_of(zb)
    kerfs = kerf_rects(s_in, s_out) + seam_rects(s_in, s_out)
    n = len(kerfs)
    loops = [sector(s_in, s_out, THETA)] + kerfs
    return Part(key, label, 1, loops,
                f"cone shell z {za:.0f}-{zb:.0f}, kerfs on the back face",
                material=f"{T_SHELL:g}", kerfs=n,
                meta=dict(za=za, zb=zb, s_in=s_in, s_out=s_out, n_kerf=n,
                          n_full=len(kerf_layout(s_in, s_out)), n_hinge=kerf_count(s_in)))


def former_radius(z0: float, z1: float) -> float:
    """Largest vertical-edged disc that fits the cone between z0 and z1:
    limited by the narrow (upper) end, less the fit."""
    return R_in(max(z0, z1)) - FIT


def core_hw(z: float) -> float:
    """Half width of a core plate at height z (edge follows the shell)."""
    return R_in(z) - CORE_FIT


def tab_spans(r_former: float) -> list:
    """Tab spans (x0, x1) for a plate edge entering a former of radius
    r_former: one tab each side of the half-lap slot, clear of the tab-root
    reliefs and leaving MORTISE_WEB of former outside the mortise."""
    lo = JOINT.slot_w / 2 + JOINT.relief_r + TAB_CLEAR
    # the corner reliefs are circles on the mortise corners: their far
    # point is hypot(end, half width) + r from the former centre
    reach = r_former - MORTISE_WEB - JOINT.relief_r
    hi = math.sqrt(reach ** 2 - (JOINT.slot_w / 2) ** 2) - JOINT.fit / 2
    w = min(TAB_W, hi - lo)
    if w < TAB_MIN:
        raise ValueError(f"no room for a tab in a former of radius {r_former:.1f}")
    c = (lo + hi) / 2
    return [(-c - w / 2, -c + w / 2), (c - w / 2, c + w / 2)]


def centre_tab(r_former: float) -> list:
    """One tab across the axis, for a former too small for two per side."""
    reach = r_former - MORTISE_WEB - JOINT.relief_r
    hi = math.sqrt(reach ** 2 - (JOINT.slot_w / 2) ** 2) - JOINT.fit / 2
    if 2 * hi < TAB_MIN:
        raise ValueError(f"no room for a centre tab in a former of radius {r_former:.1f}")
    return [(-hi, hi)]


def top_tabs(r_former: float, slot_from_top: bool) -> list:
    """Tabs on a plate's top edge. If the former is too small for a tab each
    side of the half-lap, the plate that is solid at the top (half-lap from
    the bottom) gets one centre tab and the other plate gets none: it is
    locked by the half-lap and glued under the former."""
    try:
        return tab_spans(r_former)
    except ValueError:
        return [] if slot_from_top else centre_tab(r_former)


def core_plate(za: float, zb: float, slot_from_top: bool) -> tuple:
    """One crossing plate between formers at za (top of the lower former)
    and zb (bottom of the upper former), drawn in its own plane: x across
    the cone, y = z. Returns (loop, bottom tab spans, top tab spans)."""
    hb, ht = core_hw(za), core_hw(zb)
    bot = tab_spans(former_radius(za - T_BOARD, za))
    top = top_tabs(former_radius(zb, zb + T_BOARD), slot_from_top)
    zm = (za + zb) / 2
    sw = JOINT.slot_w / 2
    pts = [(-hb, za)]
    for x0, x1 in bot:                       # bottom edge, left to right
        pts += [(x0, za), (x0, za - T_BOARD), (x1, za - T_BOARD), (x1, za)]
    if not slot_from_top:
        pts = pts[:5] + [(-sw, za), (-sw, zm), (sw, zm), (sw, za)] + pts[5:]
    pts += [(hb, za), (ht, zb)]
    # top edge, right to left: tabs and (plate A) the half-lap slot
    feats = [(x0, x1, "tab") for x0, x1 in top]
    if slot_from_top:
        feats.append((-sw, sw, "slot"))
    for x0, x1, kind in sorted(feats, key=lambda f: -f[1]):
        y = zb + T_BOARD if kind == "tab" else zm
        pts += [(x1, zb), (x1, y), (x0, y), (x0, zb)]
    pts += [(-ht, zb)]
    return [(x, y, 0.0) for x, y in pts], bot, top


def mortise(x0: float, x1: float, phi: float) -> Loop:
    """Through mortise in a former for a tab spanning x0..x1 on a plate
    whose plane is at plan angle phi (deg)."""
    hx, hy = (x1 - x0 + JOINT.fit) / 2, JOINT.slot_w / 2
    loop = J.dogbone_rect(-hx, -hy, hx, hy, JOINT.relief_r)
    xc = (x0 + x1) / 2
    c, s = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    return [(xc * c + x * c - y * s, xc * s + x * s + y * c, b) for x, y, b in loop]


def build_parts() -> list:
    zj0, zj1 = Z_SPLIT - T_BOARD, Z_SPLIT + T_BOARD
    zt0 = H_CONE - T_BOARD
    rb = former_radius(0.0, T_BOARD)
    rj_lo = former_radius(zj0, Z_SPLIT)
    rj_up = former_radius(Z_SPLIT, zj1)
    rt = former_radius(zt0, H_CONE)
    rc = R(Z_SPLIT - T_BOARD / 2) + FIT       # collar bottom face rests here

    # core levels: (za, zb, plan angle of plate A)
    levels = [(T_BOARD, zj0, 0.0), (zj1, zt0, 45.0)]
    cores, holes = [], {"FBASE": [], "FJLO": [], "FJUP": [], "FTOP": []}
    below = {0: "FBASE", 1: "FJUP"}
    above = {0: "FJLO", 1: "FTOP"}
    for lv, (za, zb, phi) in enumerate(levels, 1):
        for tag, from_top, ang in (("A", True, phi), ("B", False, phi + 90.0)):
            loop, bot, top = core_plate(za, zb, from_top)
            key = f"CORE{lv}{tag}"
            cores.append(Part(key, f"CORE-{lv}{tag}", 1, [loop],
                              f"level {lv}, plane {ang:g} deg, half-lap from "
                              f"{'top' if from_top else 'bottom'}",
                              meta=dict(za=za, zb=zb, phi=ang, bot=bot, top=top,
                                        from_top=from_top)))
            holes[below[lv - 1]] += [mortise(x0, x1, ang) for x0, x1 in bot]
            holes[above[lv - 1]] += [mortise(x0, x1, ang) for x0, x1 in top]

    def former(key, label, r, z0, z1, note):
        h = holes[key]
        return Part(key, label, 1, [circle(r)] + h, note, n_holes=len(h),
                    meta=dict(z0=z0, z1=z1, r=r))

    parts = [
        former("FBASE", "FORMER-BASE", rb, 0.0, T_BOARD, "floor disc, core level 1 stands in it"),
        former("FJLO", "FORMER-JOINT-LO", rj_lo, zj0, Z_SPLIT, "caps core level 1"),
        former("FJUP", "FORMER-JOINT-UP", rj_up, Z_SPLIT, zj1, "carries core level 2, glued on JOINT-LO"),
        former("FTOP", "FORMER-TOP", rt, zt0, H_CONE, "closes the cone top, caps core level 2"),
    ] + cores
    if ONE_SHELL:
        shells = [shell("SHELL1", "SHELL", 0.0, H_CONE)]
    else:
        shells = [shell("SHELL1", "SHELL-LOW", 0.0, Z_SPLIT),
                  shell("SHELL2", "SHELL-UP", Z_SPLIT, H_CONE)]
        parts.append(Part("COLLAR", "COLLAR", 1, ring(rc + COLLAR_W, rc), "outside, over the joint",
                          n_holes=1, meta=dict(z0=Z_SPLIT - T_BOARD / 2, z1=Z_SPLIT + T_BOARD / 2, r=rc)))
    parts = shells + parts
    for num, p in enumerate(parts, 1):
        p.num = num
        if not p.kerfs:
            p.material = f"{T_BOARD:g}"
        if p.key.startswith("CORE"):
            outline, p.relieved = J.relieve_inside_corners(p.loops[0], JOINT.relief_r)
            p.loops = [outline]
    return parts


def coupon() -> Part:
    """Bend-test strip: same kerf pattern at the tightest radius."""
    s_in = s_of(H_CONE)
    pitch = THETA * s_in / kerf_count(s_in)
    n, length, width = 12, 12 * pitch, 150.0
    loops = [[(0, 0, 0), (length, 0, 0), (length, width, 0), (0, width, 0)]]
    hw = TOOL_D / 2
    for k in range(n):
        x = pitch * (k + 0.5)
        loops.append([(x - hw, KERF_TRIM, 0), (x + hw, KERF_TRIM, 0),
                      (x + hw, width - KERF_TRIM, 0), (x - hw, width - KERF_TRIM, 0)])
    return Part("COUPON", "BEND-TEST", 1, loops, "cut and bend first",
                material=f"{T_SHELL:g}", kerfs=n, meta=dict(pitch=pitch))
