"""Deterministic checks on the built curved-sofa cut file."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ezdxf
from shapely.geometry import Polygon

import joints as J
import labels as B
import sofa_geometry as G
import sofa_layout as L

FAIL = []


def check(ok: bool, msg: str) -> None:
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        FAIL.append(msg)


def main() -> int:
    parts, sheets = L.layout()

    print("\n[1] per-part loop topology (holes inside the outline, no crossings)")
    for part in parts:
        polys = [Polygon(L.flatten_loop(l)) for l in part.loops]
        outer = polys[0]
        check(outer.is_valid, f"{part.label}: outer contour is simple")
        for i, hole in enumerate(polys[1:], 1):
            check(hole.is_valid, f"{part.label}: internal loop {i} is simple")
            check(outer.contains(hole),
                  f"{part.label}: internal loop {i} lies inside the outline")
        for i in range(1, len(polys)):
            for j in range(i + 1, len(polys)):
                check(not polys[i].intersects(polys[j]),
                      f"{part.label}: internal loops {i}/{j} do not overlap")

    print("\n[2] parts do not overlap on the sheets")
    for n, placements in enumerate(sheets, 1):
        polys = [(p.label, B.material(p.loops)) for p in placements]
        bad = 0
        close = 0.0
        for i in range(len(polys)):
            for j in range(i + 1, len(polys)):
                if polys[i][1].intersects(polys[j][1]):
                    bad += 1
                close = min(close or 1e9, polys[i][1].distance(polys[j][1]))
        check(bad == 0, f"sheet {n}: {len(placements)} parts, {bad} overlaps")
        check(close >= G.PART_GAP - 0.05,
              f"sheet {n}: closest parts {close:.1f} mm apart (>= {G.PART_GAP:.0f})")
        for p in placements:
            inside = (p.x >= G.SHEET_MARGIN - 1e-6
                      and p.y >= G.SHEET_MARGIN - 1e-6
                      and p.x + p.w <= G.SHEET_W - G.SHEET_MARGIN + 1e-6
                      and p.y + p.h <= G.SHEET_H - G.SHEET_MARGIN + 1e-6)
            if not inside:
                check(False, f"sheet {n}: {p.label} {p.instance} outside the margin")
        check(True, f"sheet {n}: every part inside the {G.SHEET_MARGIN:.0f} mm sheet margin")

    print("\n[3] requested dimensions")
    rib = next(p for p in parts if p.key == "RIB")
    bx = L.loops_bbox(rib.loops)
    check(abs((bx[2] - bx[0]) - G.DEPTH) < 0.01, f"rib radial depth = {bx[2]-bx[0]:.1f} mm (900)")
    check(abs((bx[3] - bx[1]) - G.BACK_TOP) < 0.01, f"rib height = {bx[3]-bx[1]:.1f} mm (760)")
    width = 2 * G.R_OUT * __import__("math").sin(__import__("math").radians(G.HALF_SWEEP))
    check(abs(width - 2200.0) < 0.5, f"sofa overall width across the back = {width:.0f} mm (2200)")
    depth_plan = G.R_OUT - G.R_IN * __import__("math").cos(
        __import__("math").radians(G.HALF_SWEEP))
    print(f"       plan depth over the crescent = {depth_plan:.0f} mm")
    print(f"       seat frame top = {G.DECK_TOP:.0f} mm, back top = {G.BACK_TOP:.0f} mm")

    print("\n[4] built DXF")
    path = Path(__file__).resolve().parent / "out" / "curved-sofa.dxf"
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    check(doc.units == ezdxf.units.MM, f"document units = {doc.units} (4 = mm)")
    by_layer = Counter(e.dxf.layer for e in msp)
    print(f"       entities by layer: {dict(by_layer)}")
    cut = msp.query('LWPOLYLINE[layer=="CUT"]')
    check(all(e.closed for e in cut), f"all {len(cut)} CUT polylines are closed")
    expected = sum(len(p.loops) * p.qty for p in parts)
    check(len(cut) == expected, f"CUT polyline count = {len(cut)} (expected {expected})")
    ref = msp.query('LWPOLYLINE[layer=="REFERENCE-SHEET"]')
    check(len(ref) == len(sheets), f"{len(ref)} sheet outlines (expected {len(sheets)})")

    print("\n[5] slot fit")
    check(abs(G.SLOT_T - 15.4) < 1e-9, f"every plate slot = {G.SLOT_T} mm for {G.T} mm ply")
    check(G.DOGBONE_R * 2 < G.SLOT_T, f"dogbone relief R{G.DOGBONE_R:.1f} fits a {G.SLOT_T} mm slot")
    check(G.DOGBONE_R > G.JOINT.tool_d / 2.0,
          f"relief R{G.DOGBONE_R:.1f} clears a {G.JOINT.tool_d:.0f} mm cutter")

    print("\n[6] corner relief (a round cutter cannot cut a square inside corner)")
    for part in parts:
        _, left = J.relieve_inside_corners(part.loops[0], G.DOGBONE_R)
        check(left == 0, f"{part.num:02d} {part.label}: {part.relieved} inside corners "
                         f"relieved, {left} square corners left")
    r_tool = G.JOINT.tool_d / 2.0
    for part in parts:
        # a round bit of radius r can only produce the morphological closing
        # of the part; anything the closing adds is material it leaves behind
        solid = B.material(part.loops)
        made = solid.buffer(r_tool, quad_segs=32).buffer(-r_tool, quad_segs=32)
        # one unrelieved square corner leaves (1 - pi/4) r^2 = 1.93 mm2 by
        # itself; judge the worst single spot, not the sum of curve-fit noise
        uncut = made.difference(solid)
        worst = max((g.area for g in getattr(uncut, "geoms", [uncut])), default=0.0)
        check(worst < 0.5, f"{part.num:02d} {part.label}: worst spot a "
                           f"{G.JOINT.tool_d:.0f} mm cutter cannot reach {worst:.2f} mm2")

    print("\n[7] engrave labels: one per piece, fully on material")
    labelled = B.all_labels(parts, sheets)
    placed = [lab for sheet in labelled for _, lab in sheet]
    check(all(lab is not None for lab in placed),
          f"{sum(lab is not None for lab in placed)}/{len(placed)} pieces carry a label")
    for sheet in labelled:
        for p, lab in sheet:
            if lab is None:
                continue
            safe = B.material(p.loops).buffer(-B.EDGE_CLEAR + 0.01)
            if not safe.contains(lab.box()):
                check(False, f"{lab.text} runs off the material")
    check(True, f"every label keeps {B.EDGE_CLEAR:.0f} mm clear of the cut")
    nums = [p.num for p in parts]
    check(nums == list(range(1, len(parts) + 1)), f"part numbers 01-{len(parts):02d}, no gaps")
    msp_labels = msp.query('TEXT[layer=="ENGRAVE-LABEL"]')
    check(len(msp_labels) == len(placed),
          f"{len(msp_labels)} ENGRAVE-LABEL texts in the DXF (expected {len(placed)})")

    area = sum(L.part_area(p.loops) * p.qty for p in parts)
    cutlen = sum(L.cut_length(p.loops) * p.qty for p in parts)
    print(f"\n[8] material: {area/1e6:.2f} m2 of parts on {len(sheets)} sheets "
          f"({area/1e6/(len(sheets)*2.44*1.22)*100:.0f}% of sheet area), "
          f"cut path {cutlen/1000:.0f} m, "
          f"frame mass ~{area/1e6*G.T/1000*600:.0f} kg at 600 kg/m3")

    print("\nFAILURES:", len(FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
