"""Cone D400 with a plain 5 mm skin (no kerfs) - the piece and its gabarit
in ONE file, as the workshop asked.

    python3 cone5.py              # out/cone5/CONE_5MM_piece_et_gabarit.dxf + ArtCAM R12

Board A, 5 mm (flexible MDF / plywood): the SHELL, a plain annular sector.
  It is developed on the MID-thickness surface: bent, the mid layer keeps its
  length, so the two straight edges meet exactly (no overlap, no gap).
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

import table_geometry as G

SKIN = 5.0
G.T_SHELL = SKIN                 # formers and core follow the thinner skin

import ezdxf                      # noqa: E402
from shapely.geometry import Polygon  # noqa: E402

import jig                        # noqa: E402
import sofa_layout as L           # noqa: E402

OUT = HERE / "out" / "cone5"
SHEET_W, SHEET_H, MARGIN, GAP = 2440.0, 1220.0, 10.0, 10.0
BOARD_GAP = 300.0                 # space between the two boards in the drawing


def r_mid(z):
    """Mid-thickness radius of the 5 mm skin (horizontal)."""
    return G.R(z) - (SKIN / 2) / G.COS_A


class P:
    def __init__(self, key, label, loops, layer):
        self.key, self.label, self.qty, self.loops, self.layer = key, label, 1, loops, layer


def parts():
    shell = G.sector(r_mid(G.H_CONE) / G.SIN_A, r_mid(0) / G.SIN_A, G.THETA)
    inside = [p for p in G.build_parts() if not p.key.startswith("SHELL")]
    rings = jig.parts()
    return ([P("SHELL", "SHELL-5MM", [shell], "PIECE_5MM")],
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
    for name, col in (("PIECE_5MM", 1), ("GABARIT_INTERIEUR_18MM", 5), ("GABARIT_BAGUES_18MM", 3),
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
            for loop in pl.loops:
                msp.add_lwpolyline([(x, y + oy, b) for x, y, b in loop], format="xyb", close=True,
                                   dxfattribs={"layer": by[pl.key].layer})
            m = Polygon(L.flatten_loop(pl.loops[0]))
            for h in pl.loops[1:]:
                m = m.difference(Polygon(L.flatten_loop(h)))
            mats.append(m)
        close = min((mats[i].distance(mats[j]) for i in range(len(mats))
                     for j in range(i + 1, len(mats))), default=99)
        if close < GAP - 0.05:
            fails.append(f"{title}: parts {close:.1f} mm apart")
        print(f"board {title}: {len(placed)} parts, closest {close:.1f} mm")

    # the skin closes exactly: arc length of the flat sector = mid circumference
    s_out, s_in = r_mid(0) / G.SIN_A, r_mid(G.H_CONE) / G.SIN_A
    for z, s in ((0.0, s_out), (G.H_CONE, s_in)):
        if abs(G.THETA * s - 2 * math.pi * r_mid(z)) > 1e-6:
            fails.append(f"skin does not close at z={z}")
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

    path = OUT / "CONE_5MM_piece_et_gabarit.dxf"
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
