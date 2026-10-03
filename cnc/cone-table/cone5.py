"""Cone D400 with a KERFED 5 mm skin - the piece, a bend-test coupon and
the gabarit in ONE file, as the workshop asked.

V1 of this file used a plain 5 mm sector: the workshop cut it and it would
not bend round the cone (5 mm MDF at R80 is ~3 % strain on the face). Now the
back face is kerfed like V9: 6 mm pockets, KERF_DEPTH deep, leaving SKIN_LEFT
of wood under the show face.

    python3 cone5.py              # out/cone5/CONE_5MM_piece_et_gabarit.dxf + ArtCAM R12

Board A, 5 mm: the SHELL (annular sector, kerf pockets on its BACK face) and
  a BEND-TEST strip with the tightest kerf pitch - cut and bend it first.
  With kerfs the show face is the layer that does not stretch, so the sector
  is developed on the OUTER face (as V9); the kerfs close on the back.
Board B, 18 mm: the gabarit
  * inside  - FORMER discs + crossing CORE plates (the V9 skeleton, resized
              for a 5 mm skin). The skin is bent round them and glued; they
              stay inside as the structure.
  * outside - the 4 clamp rings of jig.py (bore = cone at that height). They
              slide down from the top and hold the skin round while the glue
              sets, then come off and are reused.

Same cone as V9: base 400, top 160, height 450 (outer face).
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))

import joints as J
import table_geometry as G

G.T_BOARD = 18.0                  # this variant's gabarit stays on 18 mm (the V10 cone is 17)
G.JOINT = J.JointSpec(t=G.T_BOARD, fit=1.0, tool_d=G.TOOL_D)

SKIN = 5.0                        # board thickness of the shell
SKIN_LEFT = 1.0                   # wood kept under the show face (V2: was 1.5, it cracked)
TOP_D = 240.0                     # V2: was 160 - too tight a radius for kerfed MDF
KERF_LAND = 3.0                   # V2: was 6 - wood between kerfs, pitch 9 at the top
MAX_STRAIN = 0.0065               # MDF skin: keep the bending strain under ~0.65 %
G.T_SHELL = SKIN                  # formers and core follow the thinner skin
G.SKIN = SKIN_LEFT
G.DEPTH = SKIN - SKIN_LEFT        # 4 mm kerf pockets
# V1 (top 160, skin 1.5, pitch 12) cracked in the workshop: each kerf had to
# hinge 8.3 deg and the 1.5 mm skin stretched ~1.8 %. Skin strain over a kerf is
#   e = skin * (2 pi cos(alpha) / n_kerfs) / (2 * kerf_width)
# so it falls with a thinner skin, more kerfs (narrow lands) and a bigger top.
G.R_TOP = TOP_D / 2
G.SLANT = math.hypot(G.H_CONE, G.R_BOT - G.R_TOP)
G.SIN_A = (G.R_BOT - G.R_TOP) / G.SLANT
G.COS_A = G.H_CONE / G.SLANT
G.THETA = 2.0 * math.pi * G.SIN_A
G.KERF_LAND = KERF_LAND
G.KERF_PITCH_MIN = G.TOOL_D + KERF_LAND
KERF_LAYER = f"POCHE_KERF_{G.DEPTH:g}MM"

import ezdxf                      # noqa: E402
from shapely.geometry import Polygon  # noqa: E402

import build                      # noqa: E402  (kerf pocket extension, as V9)
import jig                        # noqa: E402
import sofa_layout as L           # noqa: E402

OUT = HERE / "out" / "cone5"
SHEET_W, SHEET_H, MARGIN, GAP = 2440.0, 1220.0, 10.0, 10.0
BOARD_GAP = 300.0                 # space between the two boards in the drawing


class P:
    def __init__(self, key, label, loops, layer):
        self.key, self.label, self.qty, self.loops, self.layer = key, label, 1, loops, layer


def parts():
    sh, cp = G.shell("SHELL", "SHELL-5MM", 0.0, G.H_CONE), G.coupon()
    inside = [p for p in G.build_parts() if not p.key.startswith("SHELL")]
    rings = jig.parts()
    thin = [P("SHELL", "SHELL-5MM", sh.loops, "PIECE_5MM"), P("COUPON", "BEND-TEST", cp.loops, "PIECE_5MM")]
    for p in thin:                 # loops[0] = outline, the rest = kerf pockets
        p.kerfs = len(p.loops) - 1
    return (thin,
            [P(p.key, p.label, p.loops, "GABARIT_INTERIEUR_18MM") for p in inside] +
            [P(r.key, r.label, r.loops, "GABARIT_BAGUES_18MM") for r in rings])


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    thin, thick = parts()
    fails = []
    boards = []
    for group, title in ((thin, "5MM"), (thick, "18MM")):
        sheets = L.nest(L.build_instances(group), sheet_w=SHEET_W, sheet_h=SHEET_H,
                        margin=MARGIN, gap=GAP)
        if len(sheets) != 1:
            fails.append(f"{title}: needs {len(sheets)} boards")
        boards.append((title, group, sheets[0]))

    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    for name, col in (("PIECE_5MM", 1), (KERF_LAYER, 6), ("GABARIT_INTERIEUR_18MM", 5), ("GABARIT_BAGUES_18MM", 3),
                      ("PLANCHE_5MM", 8), ("PLANCHE_18MM", 8)):
        doc.layers.add(name, color=col)
    msp = doc.modelspace()
    for k, (title, group, placed) in enumerate(boards):
        oy = k * (SHEET_H + BOARD_GAP)
        msp.add_lwpolyline([(0, oy), (SHEET_W, oy), (SHEET_W, oy + SHEET_H), (0, oy + SHEET_H)],
                           close=True, dxfattribs={"layer": f"PLANCHE_{title}"})
        by = {p.key: p for p in group}
        mats = []
        for pl in placed:
            part = by[pl.key]
            nk = getattr(part, "kerfs", 0)
            cuts = pl.loops[:len(pl.loops) - nk]
            for loop in cuts:
                msp.add_lwpolyline([(x, y + oy, b) for x, y, b in loop], format="xyb", close=True,
                                   dxfattribs={"layer": part.layer})
            if nk:                 # pockets run out through the edges (V9 lip fix)
                for poly in build.kerf_polys(pl.loops[len(pl.loops) - nk:], oy):
                    msp.add_lwpolyline(poly, format="xy", close=True, dxfattribs={"layer": KERF_LAYER})
            m = Polygon(L.flatten_loop(cuts[0]))
            for h in cuts[1:]:
                m = m.difference(Polygon(L.flatten_loop(h)))
            mats.append(m)
        close = min((mats[i].distance(mats[j]) for i in range(len(mats))
                     for j in range(i + 1, len(mats))), default=99)
        if close < GAP - 0.05:
            fails.append(f"{title}: parts {close:.1f} mm apart")
        print(f"board {title}: {len(placed)} parts, closest {close:.1f} mm")

    # the show face closes exactly: arc length of the flat sector = outer circumference
    s_out, s_in = G.s_of(0.0), G.s_of(G.H_CONE)
    for z, s in ((0.0, s_out), (G.H_CONE, s_in)):
        if abs(G.THETA * s - 2 * math.pi * G.R(z)) > 1e-6:
            fails.append(f"skin does not close at z={z}")
    lay = G.kerf_layout(s_in, s_out)
    n_full = sum(1 for _, r0, _ in lay if r0 == s_in)
    per = G.closure_total() / n_full
    print(f"kerfs: {len(lay)} ({n_full} full length), {G.DEPTH:g} mm deep x {G.TOOL_D:g} mm, "
          f"{SKIN_LEFT:g} mm skin; back face closes {G.closure_total():.1f} mm in total, "
          f"~{per:.2f} mm per full kerf")
    if per >= G.TOOL_D:
        fails.append("kerfs cannot close enough")
    hinge = 2 * math.pi * G.COS_A / n_full                     # rad per kerf
    strain = SKIN_LEFT * hinge / (2 * G.TOOL_D)
    print(f"skin over each kerf hinges {math.degrees(hinge):.1f} deg: strain {100 * strain:.2f} % "
          f"(limit {100 * MAX_STRAIN:.2f} %; V1 was 1.81 % and cracked)")
    if strain > MAX_STRAIN:
        fails.append(f"skin strain {100 * strain:.2f} % too high")
    # formers sit just inside the skin, rings just outside
    f = {p.key: p for p in thick}
    # a straight-edged 18 mm disc in a cone: it fits at its TOP face (fit gap),
    # and leaves a wedge below (18 x tan(alpha)) that the PU glue fills
    r_base = Polygon(L.flatten_loop(f["FBASE"].loops[0])).bounds[2]
    gap_in = (G.R(G.T_BOARD) - SKIN / G.COS_A) - r_base
    wedge = (G.R(0) - SKIN / G.COS_A) - r_base
    print(f"skin: sector {s_in:.1f}-{s_out:.1f} mm radius, {math.degrees(G.THETA):.2f} deg, "
          f"flat width {2 * s_out * math.sin(G.THETA / 2):.0f} mm")
    print(f"base former {gap_in:.2f} mm inside the skin at its top face, {wedge:.1f} mm at the floor "
          f"(fill with PU glue); rings: bores = outer face "
          f"({', '.join(f'{2 * r.r_in:.0f}' for r in jig.parts())})")
    if not (0 < gap_in <= G.FIT + 1e-6):
        fails.append(f"base former gap {gap_in:.2f}")

    path = OUT / "CONE_5MM_KERF_V2_piece_et_gabarit.dxf"
    doc.saveas(path)
    r = subprocess.run([sys.executable, str(HERE.parents[0] / "tools" / "artcam_dxf.py"), str(path)],
                       capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode:
        fails.append("ArtCAM export check failed")
    print("FAILURES:", fails or 0)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
