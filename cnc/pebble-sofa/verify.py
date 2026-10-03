"""Deterministic 2D checks on the Pebble sofa cut file."""

from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))  # shared code, lower priority

import ezdxf
from shapely.geometry import Polygon

import build
import joints as J
import labels as B
import pebble_geometry as C
import sofa_layout as L

FAIL = []
RESULTS = []          # (section, passed, message) for validation.json
_SECTION = [""]


def section(title: str) -> None:
    _SECTION[0] = title
    print(f"\n{title}")


def check(ok: bool, msg: str) -> None:
    print(("  ok   " if ok else "  FAIL ") + msg)
    RESULTS.append((_SECTION[0], bool(ok), msg))
    if not ok:
        FAIL.append(msg)


def main() -> int:
    parts, sheets = build.layout()

    section("[1] part topology")
    for p in parts:
        polys = [Polygon(L.flatten_loop(l)) for l in p.loops]
        ok = all(q.is_valid for q in polys) and all(polys[0].contains(h) for h in polys[1:])
        disjoint = all(not polys[i].intersects(polys[j])
                       for i in range(1, len(polys)) for j in range(i + 1, len(polys)))
        check(ok and disjoint, f"{p.num:02d} {p.label}: {len(p.loops)} loops, simple, "
                               f"holes inside and apart")

    section("[2] joints (Tokyo rule: 19 x 41 mortise for 18 mm board, 40 mm tab)")
    check(abs(C.SLOT_T - 19.0) < 1e-9 and abs(C.TAB_SLOT - 41.0) < 1e-9,
          f"mortise {C.TAB_SLOT:.0f} x {C.SLOT_T:.0f} mm, tab {C.TAB_W:.0f} mm, board {C.T:.0f} mm")
    sizes = Counter()
    for p in parts:
        for h in p.loops[1:]:
            if len(h) != 8:
                continue                      # rounded lightening hole, not a joint
            # mortises are rotated (radial, angled pebbles): measure the
            # rectangle through the vertices in its own frame
            r = Polygon([(v[0], v[1]) for v in h]).minimum_rotated_rectangle
            c = list(r.exterior.coords)
            sides = sorted((round(math.dist(c[0], c[1]), 2), round(math.dist(c[1], c[2]), 2)))
            sizes[tuple(sides)] += p.qty
    check(set(sizes) == {(19.0, 41.0)},
          f"{sum(sizes.values())} mortises, all 19 x 41 mm: {dict(sizes)}")
    check(C.RELIEF_R > C.JOINT.tool_d / 2, f"relief R{C.RELIEF_R:.1f} clears a "
                                           f"{C.JOINT.tool_d:.0f} mm cutter")
    section("[3] corner relief and cutter reach")
    r_tool = C.JOINT.tool_d / 2.0
    for p in parts:
        _, left = J.relieve_inside_corners(p.loops[0], C.RELIEF_R)
        solid = B.material(p.loops)
        uncut = solid.buffer(r_tool, quad_segs=32).buffer(-r_tool, quad_segs=32) \
            .difference(solid)
        worst = max((g.area for g in getattr(uncut, "geoms", [uncut])), default=0.0)
        check(left == 0 and worst < 0.5,
              f"{p.num:02d} {p.label}: {p.relieved} corners relieved, worst spot a "
              f"{C.JOINT.tool_d:.0f} mm bit cannot reach {worst:.2f} mm2")

    section("[4] nesting")
    for n_, placements in enumerate(sheets, 1):
        mats = [B.material(p.loops) for p in placements]
        close = min((mats[i].distance(mats[j]) for i in range(len(mats))
                     for j in range(i + 1, len(mats))), default=1e9)
        inside = all(p.x >= C.SHEET_MARGIN - 1e-6 and p.y >= C.SHEET_MARGIN - 1e-6
                     and p.x + p.w <= C.SHEET_W - C.SHEET_MARGIN + 1e-6
                     and p.y + p.h <= C.SHEET_H - C.SHEET_MARGIN + 1e-6
                     for p in placements)
        check(close >= C.PART_GAP - 0.05 and inside,
              f"sheet {n_}: {len(placements)} parts, closest {close:.1f} mm apart, "
              f"all inside the {C.SHEET_MARGIN:.0f} mm edge")
    counts = Counter(p.key for s in sheets for p in s)
    check(all(counts[p.key] == p.qty for p in parts),
          f"every part placed its full quantity ({sum(counts.values())} pieces)")

    section("[5] labels")
    labelled = B.all_labels(parts, sheets)
    labs = [lab for s in labelled for _, lab in s]
    check(all(lab is not None for lab in labs), f"{len(labs)} pieces labelled")
    bad = [lab.text for s in labelled for p, lab in s
           if lab and not B.material(p.loops).buffer(-B.EDGE_CLEAR + 0.01).contains(lab.box())]
    check(not bad, f"every label sits on material, {B.EDGE_CLEAR:.0f} mm from any cut")

    section("[6] built DXF")
    path = HERE / "out" / "pebble-sofa.dxf"
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    cut = msp.query('LWPOLYLINE[layer=="CUT"]')
    expected = sum(len(p.loops) * p.qty for p in parts)
    check(doc.units == ezdxf.units.MM, "units = mm")
    check(all(e.closed for e in cut) and len(cut) == expected,
          f"{len(cut)} closed CUT profiles (expected {expected})")
    check(len(msp.query('TEXT[layer=="ENGRAVE-LABEL"]')) == len(labs),
          f"{len(labs)} ENGRAVE-LABEL texts")
    keys = Counter()
    for e in cut:
        keys[tuple(round(c, 3) for pt in e.get_points("xyb") for c in pt)] += 1
    dup = sum(n - 1 for n in keys.values() if n > 1)
    check(dup == 0, f"no duplicate CUT profiles ({dup} found)")
    big = max(max(L.loops_bbox(p.loops)[2] - L.loops_bbox(p.loops)[0],
                  L.loops_bbox(p.loops)[3] - L.loops_bbox(p.loops)[1]) for p in parts)
    check(big <= C.SHEET_W - 2 * C.SHEET_MARGIN, f"longest part {big:.0f} mm fits the sheet")

    area = sum(L.part_area(p.loops) * p.qty for p in parts)
    print(f"\n[7] {sum(p.qty for p in parts)} pieces, {len(sheets)} sheets, "
          f"{area / 1e6:.2f} m2, frame ~{area / 1e6 * C.T / 1000 * 750:.0f} kg MDF, "
          f"")
    print("\nFAILURES:", len(FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
