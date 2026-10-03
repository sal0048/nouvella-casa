"""Cone V11, all 17 mm: the kerfed shell, its bend-test coupon, the inside
gabarit (floor ring + one full-height cross + top disc) and the clamp
rings, in ONE ArtCAM file.

    python3 cone17.py     # out/cone17/CONE_17MM_V11_piece_et_gabarit(.dxf, _ArtCAM_R12, _lines)

V11 (workshop: "the gabarit looks unstudied"): the skeleton of the proven
conic-leg kits - a floor RING (60 mm band, not a full disc), ONE pair of
crossing plates the full height (V10: two levels and two mid discs) and
the top disc the table top screws into. The shell is unchanged from V10.

What changed from V9 (it cracked, workshop: "the inside cutting is wrong"):
  * every kerf runs the full length, floor edge to top edge. On a cone each
    kerf is a generatrix and must hinge the same angle all along it; V9's
    short kerfs stopped half way, the hinge angle jumped there and the
    shell split along those ends.
  * 49 kerfs + the seam = 50 equal hinges of 6.96 deg (V9: 42 at the top,
    8.3 deg), 2 mm skin (V9: 2.5): skin strain 2.0 % instead of 3.0 %.
  * the seam edges get a 1.1 mm back-face relief, same depth as the kerfs,
    so the two edges close like a kerf instead of jamming on the back.
  * board 17 mm everywhere (shell, formers, core, rings).

Layers: COUPE (through cuts), POCHE_KERF_15MM (pockets, BACK face of the
shell and coupon: show face down), PLANCHE (board outline, not cut).
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))

import ezdxf
from shapely.geometry import Polygon

import build
import jig
import sofa_layout as L
import table_geometry as G

OUT = HERE / "out" / "cone17"
NAME = f"CONE_{G.T_SHELL:g}MM_V11_piece_et_gabarit"
KERF_LAYER = f"POCHE_KERF_{G.DEPTH:g}MM"
SHEET_W, SHEET_H, MARGIN, GAP = G.SHEET_W, G.SHEET_H, G.SHEET_MARGIN, G.PART_GAP


class P:
    def __init__(self, key, label, loops, kerfs=0):
        self.key, self.label, self.qty, self.loops, self.kerfs = key, label, 1, loops, kerfs


def parts():
    out = []
    for p in G.build_parts():
        out.append(P(p.key, p.label, p.loops, p.kerfs))
    cp = G.coupon()
    out.append(P("COUPON", "BEND-TEST", cp.loops, cp.kerfs))
    out += [P(r.key, r.label, r.loops) for r in jig.parts()]
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ps = parts()
    sheets = L.nest(L.build_instances(ps), sheet_w=SHEET_W, sheet_h=SHEET_H, margin=MARGIN, gap=GAP)
    fails = []
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    for name, col in (("COUPE", 1), (KERF_LAYER, 5), ("PLANCHE", 8)):
        doc.layers.add(name, color=col)
    msp = doc.modelspace()
    by = {p.key: p for p in ps}
    for k, placed in enumerate(sheets):
        oy = k * (SHEET_H + 300.0)
        msp.add_lwpolyline([(0, oy), (SHEET_W, oy), (SHEET_W, oy + SHEET_H), (0, oy + SHEET_H)],
                           close=True, dxfattribs={"layer": "PLANCHE"})
        mats = []
        for pl in placed:
            part = by[pl.key]
            nk = part.kerfs
            cuts = pl.loops[:len(pl.loops) - nk]
            for loop in cuts:
                msp.add_lwpolyline([(x, y + oy, b) for x, y, b in loop], format="xyb", close=True,
                                   dxfattribs={"layer": "COUPE"})
            if nk:                         # pockets run out through the edges
                for poly in build.kerf_polys(pl.loops[len(pl.loops) - nk:], oy):
                    msp.add_lwpolyline(poly, format="xy", close=True, dxfattribs={"layer": KERF_LAYER})
            m = Polygon(L.flatten_loop(cuts[0]))
            for h in cuts[1:]:
                m = m.difference(Polygon(L.flatten_loop(h)))
            mats.append(m)
        close = min((mats[i].distance(mats[j]) for i in range(len(mats))
                     for j in range(i + 1, len(mats))), default=99)
        if close < GAP - 0.05:
            fails.append(f"sheet {k + 1}: parts {close:.1f} mm apart")
        print(f"sheet {k + 1}: {len(placed)} parts ({', '.join(pl.label for pl in placed)}), "
              f"closest {close:.1f} mm")
    if len(sheets) != 1:
        fails.append(f"needs {len(sheets)} sheets")

    s_in, s_out = G.s_of(G.H_CONE), G.s_of(0.0)
    lay = G.kerf_layout(s_in, s_out)
    hinge = G.hinge_angle(s_in)
    print(f"shell: {len(lay)} full-length kerfs + seam = {G.kerf_count(s_in)} hinges of "
          f"{math.degrees(hinge):.2f} deg, {G.DEPTH:g} deep x {G.TOOL_D:g} wide, {G.SKIN:g} mm skin "
          f"(strain {100 * G.SKIN * hinge / (2 * G.TOOL_D):.2f} %); wood between kerfs "
          f"{G.THETA * s_in / G.kerf_count(s_in) - G.TOOL_D:.1f} mm at the top, "
          f"{G.THETA * s_out / G.kerf_count(s_in) - G.TOOL_D:.1f} mm at the floor; "
          f"seam relief {G.seam_relief(s_in):.2f} mm")
    if any(r0 != s_in or r1 != s_out for _, r0, r1 in lay):
        fails.append("a kerf does not run the full length")

    path = OUT / f"{NAME}.dxf"
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
