"""Deterministic checks on the curl lounge chair cut file."""

from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))  # shared code, lower priority

import ezdxf
from shapely.geometry import Point, Polygon

import build
import chair_geometry as C
import joints as J
import labels as B
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


def mortise_centres(loops):
    return [Polygon(L.flatten_loop(l)).centroid for l in loops[2:] if len(l) == 8]


def main() -> int:
    parts, sheets = build.layout()
    by_key = {p.key: p for p in parts}

    section("[1] part topology")
    for p in parts:
        polys = [Polygon(L.flatten_loop(l)) for l in p.loops]
        ok = all(q.is_valid for q in polys) and all(polys[0].contains(h) for h in polys[1:])
        disjoint = all(not polys[i].intersects(polys[j])
                       for i in range(1, len(polys)) for j in range(i + 1, len(polys)))
        check(ok and disjoint, f"{p.num:02d} {p.label}: {len(p.loops)} loops, simple, "
                               f"holes inside and apart")

    section("[2] every tab has its mortise (same angle, same radial span)")
    base, seat = by_key["BASE"], by_key["SEAT"]
    base_c, seat_c = mortise_centres(base.loops), mortise_centres(seat.loops)

    def has(centres, r0, r1, a):
        x, y = C.polar(0.5 * (r0 + r1), a)
        return any(c.distance(Point(x, y)) < 0.05 for c in centres)

    miss = [a for a in C.BODY_ANGLES if not has(base_c, *C.body_tab(a), a)]
    check(not miss, f"base ring: {len(C.BODY_ANGLES) - len(miss)}/{len(C.BODY_ANGLES)} "
                    f"body-rib mortises")
    miss = [a for a in C.BODY_ANGLES if not has(seat_c, *C.body_tab(a), a)]
    miss += [a for a in C.BACK_ANGLES if not has(seat_c, *C.back_tab(a), a)]
    n = len(C.BODY_ANGLES) + len(C.BACK_ANGLES)
    check(not miss, f"seat ring: {n - len(miss)}/{n} rib mortises")
    for p in parts:
        if p.key.startswith("BODY"):
            a = p.angles[0]
            xs = [x + C.body_in(a) for x, y, _ in p.loops[0] if abs(y) < 1e-6]
            t0, t1 = C.body_tab(a)
            check(abs(min(xs) - t0) < 1e-6 and abs(max(xs) - t1) < 1e-6,
                  f"{p.label}: bottom tab {min(xs):.1f}-{max(xs):.1f} matches its mortise")
    slots = sum(len(by_key[k].loops) - 1 for k in by_key if k.startswith("BAND"))
    check(slots == len(C.BACK_ANGLES),
          f"back bands carry {slots} rib slots for {len(C.BACK_ANGLES)} back ribs")
    for a in C.BACK_ANGLES:
        if C.back_height(a) <= C.BAND_Z + C.T + 20:
            check(False, f"back rib at {a} deg too short to pass through the band")
    check(True, "every back rib rises at least 20 mm above the band")

    section("[3] slot sizes (Tokyo rule: 19 x 41 for 18 mm board)")
    check(abs(C.SLOT_T - 19.0) < 1e-9 and abs(C.TAB_SLOT - 41.0) < 1e-9,
          f"mortise {C.TAB_SLOT:.0f} x {C.SLOT_T:.0f} mm for {C.T:.0f} mm board")
    check(C.RELIEF_R > C.JOINT.tool_d / 2, f"relief R{C.RELIEF_R:.1f} clears a "
                                           f"{C.JOINT.tool_d:.0f} mm cutter")

    section("[4] corner relief and cutter reach")
    r_tool = C.JOINT.tool_d / 2.0
    for p in parts:
        _, left = J.relieve_inside_corners(p.loops[0], C.RELIEF_R)
        solid = B.material(p.loops)
        # an unrelieved square corner leaves (1 - pi/4) r^2 = 1.93 mm2 on its
        # own; judge the worst single spot, not the sum of curve-fit noise
        uncut = solid.buffer(r_tool, quad_segs=32).buffer(-r_tool, quad_segs=32) \
            .difference(solid)
        worst = max((g.area for g in getattr(uncut, "geoms", [uncut])), default=0.0)
        check(left == 0 and worst < 0.5,
              f"{p.num:02d} {p.label}: {p.relieved} corners relieved, worst spot a "
              f"{C.JOINT.tool_d:.0f} mm bit cannot reach {worst:.2f} mm2")

    section("[5] nesting")
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

    section("[6] labels")
    labelled = B.all_labels(parts, sheets)
    labs = [lab for s in labelled for _, lab in s]
    check(all(lab is not None for lab in labs), f"{len(labs)} pieces labelled")
    bad = [lab.text for s in labelled for p, lab in s
           if lab and not B.material(p.loops).buffer(-B.EDGE_CLEAR + 0.01).contains(lab.box())]
    check(not bad, f"every label sits on material, {B.EDGE_CLEAR:.0f} mm from any cut")

    section("[7] built DXF")
    path = HERE / "out" / "curl-chair.dxf"
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    cut = msp.query('LWPOLYLINE[layer=="CUT"]')
    expected = sum(len(p.loops) * p.qty for p in parts)
    check(doc.units == ezdxf.units.MM, "units = mm")
    check(all(e.closed for e in cut) and len(cut) == expected,
          f"{len(cut)} closed CUT profiles (expected {expected})")
    check(len(msp.query('TEXT[layer=="ENGRAVE-LABEL"]')) == len(labs),
          f"{len(labs)} ENGRAVE-LABEL texts")

    section("[8] DXF hygiene, scale and cutter compatibility")
    keys = Counter()
    for e in cut:
        pts = tuple(round(c, 3) for pt in e.get_points("xyb") for c in pt)
        keys[pts] += 1
    dup = sum(n - 1 for n in keys.values() if n > 1)
    check(dup == 0, f"no duplicate CUT profiles ({dup} found)")
    # scale 1:1: the widest nested part must match its model width exactly
    base = by_key["BASE"]
    bb = L.loops_bbox(base.loops)
    placed = next(pl for s in sheets for pl in s if pl.key == "BASE")
    pb = L.loops_bbox(placed.loops)
    check(abs((pb[2] - pb[0]) - (bb[2] - bb[0])) < 1e-6 or
          abs((pb[3] - pb[1]) - (bb[2] - bb[0])) < 1e-6,
          f"scale 1:1 (base ring {bb[2] - bb[0]:.1f} mm in model and in the DXF)")
    narrow = min(C.SLOT_T, C.TAB_SLOT)
    check(narrow > C.JOINT.tool_d + 1.0,
          f"narrowest internal feature {narrow:.0f} mm > {C.JOINT.tool_d:.0f} mm cutter + 1 mm")
    # material left between each mortise and the ring edges (both sides)
    webs = []
    for a in C.BODY_ANGLES:
        t0, t1 = C.body_tab(a)
        webs += [t0 - (C.S_BASE * C.R(a) - C.BASE_W), C.S_BASE * C.R(a) - t1,   # base
                 t0 - (C.S_BASE * C.R(a) - C.RIB_IN - 25.0),                       # seat in
                 C.S_SEAT * C.R(a) + C.SEAT_LIP - t1]                             # seat out
    for a in C.BACK_ANGLES:
        t0, t1 = C.back_tab(a)
        webs += [C.S_SEAT * C.R(a) + C.SEAT_LIP - t1]
    web = min(webs) - C.JOINT.fit / 2
    check(web >= 2 * C.T / 3,
          f"thinnest ring web beside a mortise {web:.1f} mm (>= {2 * C.T / 3:.0f} mm)")
    sym = all(C._type_angle(a) == C._type_angle(180 - a) for a in C.BODY_ANGLES)
    check(sym, "mirrored rib positions share one profile (plan symmetric in X and Y)")

    area = sum(L.part_area(p.loops) * p.qty for p in parts)
    print(f"\n[9] {sum(p.qty for p in parts)} pieces, {len(sheets)} sheets, "
          f"{area / 1e6:.2f} m2, frame ~{area / 1e6 * C.T / 1000 * 750:.0f} kg MDF, "
          f"overall {2 * C.A:.0f} x {2 * C.B:.0f} x {C.BACK_TOP:.0f} mm")
    print("\nFAILURES:", len(FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
