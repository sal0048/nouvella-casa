"""Cone pedestal table - kerf-bent shell, geometry only.

Construction
------------
* SHELL-LOW / SHELL-UP  two flat annular sectors of thin board. Radial kerfs
                        are pocketed into the BACK face, leaving a thin skin
                        on the show face, so each sector rolls into a cone
                        frustum. The two frusta stack into one tall cone.
* FORMER-BASE           full disc inside the cone foot (floor side, ballast).
* FORMER-JOINT x2       two rings stacked across the joint inside the cone;
                        each shell glues onto one of them.
* FORMER-TOP            disc inside the cone top; the sub-top screws to it.
* COLLAR                flat ring outside the joint, hides the seam.
* SUB-TOP               disc under the table top, spreads the load.
* TOP                   the table top.

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

# --------------------------------------------------------------------------
# Parameters - provenance lives in package.py / parameters.json
# --------------------------------------------------------------------------
TOP_D = 500.0            # table top diameter
SUBTOP_D = 300.0
T_BOARD = 15.0           # formers, collar, sub-top, top
T_SHELL = 15.0           # kerf-bent shell board
SKIN = 2.5               # material left on the show face under each kerf
TOOL_D = 6.0             # kerf width = cutter diameter
KERF_PITCH_MIN = 12.0    # kerf pitch at the tightest (top) edge of a shell
KERF_OVERRUN = 3.0       # kerf pocket runs past both curved edges

R_BOT = 150.0            # cone outer radius at the floor (base 300 mm)
R_TOP = 60.0             # cone outer radius under the sub-top (top 120 mm)
H_CONE = 400.0           # cone height (base height 400 mm)
TABLE_H = H_CONE + 2 * T_BOARD          # 430 with sub-top and top
Z_SPLIT = 220.0          # joint between the two shells (collar height)

FIT = 0.5                # radial clearance formers / collar
FORMER_RING_W = 35.0     # joint former ring width
COLLAR_W = 30.0
BALLAST_KG = 20.0        # steel/concrete on FORMER-BASE

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
    return math.ceil(THETA * s_in / KERF_PITCH_MIN)


def kerf_rects(s_in: float, s_out: float, n: int, trim: float = 0.5) -> list:
    """Kerf pockets as rectangles along the generatrices, kept just inside
    the outline for nesting (build.py extends them by KERF_OVERRUN)."""
    a0 = math.pi / 2 - THETA / 2
    hw = TOOL_D / 2.0
    out = []
    for k in range(n):
        a = a0 + THETA * (k + 0.5) / n
        c, s = math.cos(a), math.sin(a)
        r0, r1 = s_in + trim + hw, s_out - trim - hw   # corners stay inside
        nx, ny = -s, c
        out.append([(r0 * c + hw * nx, r0 * s + hw * ny, 0.0),
                    (r0 * c - hw * nx, r0 * s - hw * ny, 0.0),
                    (r1 * c - hw * nx, r1 * s - hw * ny, 0.0),
                    (r1 * c + hw * nx, r1 * s + hw * ny, 0.0)])
    return out


def shell(key, label, za, zb) -> Part:
    s_out, s_in = s_of(za), s_of(zb)
    n = kerf_count(s_in)
    loops = [sector(s_in, s_out, THETA)] + kerf_rects(s_in, s_out, n)
    return Part(key, label, 1, loops,
                f"cone shell z {za:.0f}-{zb:.0f}, kerfs on the back face",
                material=f"{T_SHELL:g}", kerfs=n,
                meta=dict(za=za, zb=zb, s_in=s_in, s_out=s_out, n_kerf=n))


def former_radius(z0: float, z1: float) -> float:
    """Largest vertical-edged disc that fits the cone between z0 and z1:
    limited by the narrow (upper) end, less the fit."""
    return R_in(max(z0, z1)) - FIT


def build_parts() -> list:
    zj0, zj1 = Z_SPLIT - T_BOARD, Z_SPLIT + T_BOARD
    rb = former_radius(0.0, T_BOARD)
    rj_lo = former_radius(zj0, Z_SPLIT)
    rj_up = former_radius(Z_SPLIT, zj1)
    rt = former_radius(H_CONE - T_BOARD, H_CONE)
    rc = R(Z_SPLIT - T_BOARD / 2) + FIT       # collar bottom face rests here
    parts = [
        shell("SHELL1", "SHELL-LOW", 0.0, Z_SPLIT),
        shell("SHELL2", "SHELL-UP", Z_SPLIT, H_CONE),
        Part("FBASE", "FORMER-BASE", 1, [circle(rb)], "inside cone foot, z 0-18",
             meta=dict(z0=0.0, z1=T_BOARD, r=rb)),
        Part("FJLO", "FORMER-JOINT-LO", 1, ring(rj_lo, rj_lo - FORMER_RING_W),
             "inside, just below the joint", n_holes=1,
             meta=dict(z0=zj0, z1=Z_SPLIT, r=rj_lo)),
        Part("FJUP", "FORMER-JOINT-UP", 1, ring(rj_up, rj_up - FORMER_RING_W),
             "inside, just above the joint", n_holes=1,
             meta=dict(z0=Z_SPLIT, z1=zj1, r=rj_up)),
        Part("FTOP", "FORMER-TOP", 1, [circle(rt)], "inside cone top, sub-top screws in",
             meta=dict(z0=H_CONE - T_BOARD, z1=H_CONE, r=rt)),
        Part("COLLAR", "COLLAR", 1, ring(rc + COLLAR_W, rc), "outside, over the joint",
             n_holes=1, meta=dict(z0=Z_SPLIT - T_BOARD / 2, z1=Z_SPLIT + T_BOARD / 2, r=rc)),
        Part("SUBTOP", "SUB-TOP", 1, [circle(SUBTOP_D / 2)], "under the top",
             meta=dict(z0=H_CONE, z1=H_CONE + T_BOARD)),
        Part("TOP", "TABLE-TOP", 1, [circle(TOP_D / 2)], "table top",
             meta=dict(z0=H_CONE + T_BOARD, z1=TABLE_H)),
    ]
    for num, p in enumerate(parts, 1):
        p.num = num
        if not p.kerfs:
            p.material = f"{T_BOARD:g}"
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
        loops.append([(x - hw, 0.5 + 0, 0), (x + hw, 0.5, 0),
                      (x + hw, width - 0.5, 0), (x - hw, width - 0.5, 0)])
    return Part("COUPON", "BEND-TEST", 1, loops, "cut and bend first",
                material=f"{T_SHELL:g}", kerfs=n, meta=dict(pitch=pitch))
