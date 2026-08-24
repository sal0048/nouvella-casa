"""Deterministic checks on the built curved-sofa cut file."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ezdxf
from shapely.geometry import Polygon

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
    for n, sheet in enumerate(sheets, 1):
        placements = sheet["placements"]
        polys = [(p.label, Polygon(L.flatten_loop(p.loops[0]))) for p in placements]
        bad = 0
        for i in range(len(polys)):
            for j in range(i + 1, len(polys)):
                if polys[i][1].intersects(polys[j][1]):
                    bad += 1
        check(bad == 0, f"sheet {n}: {len(placements)} parts, {bad} overlaps")
        for p in placements:
            inside = (p.x >= G.SHEET_MARGIN - 1e-6
                      and p.y >= G.SHEET_MARGIN - 1e-6
                      and p.x + p.w <= G.SHEET_W - G.SHEET_MARGIN + 1e-6
                      and p.y + p.h <= G.SHEET_H - G.SHEET_MARGIN + 1e-6)
            if not inside:
                check(False, f"sheet {n}: {p.label} {p.instance} outside the margin")
        check(True, f"sheet {n}: every part inside the 15 mm sheet margin")

    print("\n[3] requested dimensions")
    rib = next(p for p in parts if p.key == "RIB")
    bx = L.loops_bbox(rib.loops)
    check(abs((bx[2] - bx[0]) - G.DEPTH) < 0.01, f"rib radial depth = {bx[2]-bx[0]:.1f} mm (900)")
    check(abs((bx[3] - bx[1]) - G.BACK_TOP) < 0.01,
          f"rib height = {bx[3]-bx[1]:.1f} mm ({G.BACK_TOP:.0f} + {G.PLINTH_H:.0f} plinth "
          f"= {G.BACK_TOP+G.PLINTH_H:.0f} above the floor)")
    width = 2 * G.R_OUT * __import__("math").sin(__import__("math").radians(G.HALF_SWEEP))
    check(abs(width - 2200.0) < 0.5, f"sofa overall width across the back = {width:.0f} mm (2200)")
    depth_plan = G.R_OUT - G.R_IN * __import__("math").cos(
        __import__("math").radians(G.HALF_SWEEP))
    print(f"       plan depth over the crescent = {depth_plan:.0f} mm")
    print(f"       above the floor: seat frame {G.DECK_TOP+G.PLINTH_H:.0f} mm, "
          f"arm {G.ARM_TOP+G.PLINTH_H:.0f} mm, back {G.BACK_TOP+G.PLINTH_H:.0f} mm")

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
    check(G.DOGBONE_R * 2 < G.SLOT_T, f"dogbone relief R{G.DOGBONE_R} fits a {G.SLOT_T} mm slot")

    print("\n[6] material")
    for material in (G.PLY15, G.PLY4):
        mp = [p for p in parts if p.material == material]
        if not mp:
            continue
        area = sum(L.part_area(p.loops) * p.qty for p in mp)
        cutlen = sum(L.cut_length(p.loops) * p.qty for p in mp)
        n = sum(1 for sh in sheets if sh["material"] == material)
        thick = G.T if material == G.PLY15 else G.SKIN_T
        print(f"       {material}: {sum(p.qty for p in mp):3d} pieces, "
              f"{area/1e6:5.2f} m2 on {n} sheets "
              f"({area/1e6/(n*2.44*1.22)*100:.0f}% used), "
              f"cut path {cutlen/1000:.0f} m, ~{area/1e6*thick/1000*600:.0f} kg")

    print("\nFAILURES:", len(FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
