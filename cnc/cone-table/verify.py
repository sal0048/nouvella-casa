"""Deterministic checks on the cone table cut file and geometry."""

from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))  # shared code, lower priority

import ezdxf
from shapely.geometry import Polygon

import build
import labels as B
import sofa_layout as L
import table_geometry as T

FAIL, RESULTS, NOTES = [], [], []
_SECTION = [""]
DENSITY = 750.0          # kg/m3 MDF


def section(title):
    _SECTION[0] = title
    print(f"\n{title}")


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    RESULTS.append((_SECTION[0], bool(ok), msg))
    if not ok:
        FAIL.append(msg)


def note(msg):
    print("  note " + msg)
    NOTES.append(msg)


def main() -> int:
    parts, groups = build.layout()
    by = {p.key: p for p in parts}
    lo, up = by["SHELL1"], by["SHELL2"]

    section("[1] part topology")
    for p in parts:
        cuts, kerfs = build.split_loops(p, p.loops)
        outer = Polygon(L.flatten_loop(cuts[0]))
        holes = [Polygon(L.flatten_loop(l)) for l in cuts[1:] + kerfs]
        ok = outer.is_valid and all(h.is_valid and outer.contains(h) for h in holes)
        apart = all(not holes[i].intersects(holes[j])
                    for i in range(len(holes)) for j in range(i + 1, min(len(holes), i + 2)))
        check(ok and apart, f"{p.num:02d} {p.label}: valid, {len(cuts) - 1} holes, "
                            f"{len(kerfs)} kerfs inside the outline and apart")

    section("[2] cone development (show face does not stretch)")
    for p in (lo, up):
        m = p.meta
        arc_out, arc_in = T.THETA * m["s_out"], T.THETA * m["s_in"]
        c_bot, c_top = 2 * math.pi * T.R(m["za"]), 2 * math.pi * T.R(m["zb"])
        check(abs(arc_out - c_bot) < 1e-6 and abs(arc_in - c_top) < 1e-6,
              f"{p.label}: edge arcs {arc_out:.1f}/{arc_in:.1f} mm = cone circumferences "
              f"at z {m['za']:.0f}/{m['zb']:.0f}")
        slant = m["s_out"] - m["s_in"]
        want = math.hypot(m["zb"] - m["za"], T.R(m["za"]) - T.R(m["zb"]))
        check(abs(slant - want) < 1e-6, f"{p.label}: pattern depth {slant:.1f} mm = slant height")
    check(abs(lo.meta["s_in"] - up.meta["s_out"]) < 1e-9,
          f"shells meet at the joint: {lo.meta['s_in']:.2f} mm both sides")

    section("[3] kerfs")
    need = T.closure_total()
    for p in (lo, up):
        n = p.meta["n_kerf"]
        per = need / n
        pitch_top = T.THETA * p.meta["s_in"] / n
        pitch_bot = T.THETA * p.meta["s_out"] / n
        check(per < T.TOOL_D, f"{p.label}: each kerf closes {per:.2f} mm of its "
                              f"{T.TOOL_D:.0f} mm width (back face never jams)")
        check(pitch_top - T.TOOL_D >= 4.0, f"{p.label}: {n} kerfs, rib {pitch_top - T.TOOL_D:.1f}"
                                          f"-{pitch_bot - T.TOOL_D:.1f} mm wide")
        # hinge estimate: the bend concentrates in the skin over each kerf
        r_face = T.R(p.meta["zb"]) / T.COS_A
        r_hinge = T.TOOL_D * r_face / pitch_top
        note(f"{p.label}: skin {T.SKIN} mm bends at ~R{r_hinge:.0f} over each kerf "
             f"(strain ~{T.SKIN / 2 / r_hinge * 100:.1f}%) - confirm with the bend-test coupon")
    check(T.SKIN >= 2.0 and T.DEPTH > 0, f"pocket depth {T.DEPTH:g} mm leaves a "
                                         f"{T.SKIN:g} mm skin on {T.T_SHELL:g} mm board")
    check(T.KERF_OVERRUN >= T.TOOL_D / 2, "kerf pockets run out through both curved edges")

    section("[4] formers and collar sit where they should")
    for k in ("FBASE", "FJLO", "FJUP", "FTOP"):
        m = by[k].meta
        tight = T.R_in(m["z1"]) - m["r"]
        loose = T.R_in(m["z0"]) - m["r"]
        check(tight > 0 and loose <= 5.0,
              f"{by[k].label}: {tight:.1f} mm clear at its upper face, {loose:.1f} mm at its "
              f"lower face (glue line)")
    rc = by["COLLAR"].meta["r"]
    z_rest = (T.R_BOT - rc) / (T.R_BOT - T.R_TOP) * T.H_CONE
    centre = z_rest + T.T_BOARD / 2
    check(abs(centre - T.Z_SPLIT) <= 3.0,
          f"collar slides down to z {z_rest:.1f}, centred {centre - T.Z_SPLIT:+.1f} mm "
          f"on the joint")
    check(T.SUBTOP_D / 2 >= T.R_TOP + 20.0,
          f"sub-top R{T.SUBTOP_D / 2:.0f} overlaps the cone rim R{T.R_TOP:.0f} by "
          f"{T.SUBTOP_D / 2 - T.R_TOP:.0f} mm")
    check(abs(T.H_CONE + 2 * T.T_BOARD - T.TABLE_H) < 1e-9,
          f"stack: cone {T.H_CONE:.0f} + sub-top + top = {T.TABLE_H:.0f} mm")

    section("[5] nesting")
    for mat, sheets in groups.items():
        for n, placements in enumerate(sheets, 1):
            mats = [B.material(pl.loops) for pl in placements]
            close = min((mats[i].distance(mats[j]) for i in range(len(mats))
                         for j in range(i + 1, len(mats))), default=1e9)
            inside = all(pl.x >= T.SHEET_MARGIN - 1e-6 and pl.y >= T.SHEET_MARGIN - 1e-6
                         and pl.x + pl.w <= T.SHEET_W - T.SHEET_MARGIN + 1e-6
                         and pl.y + pl.h <= T.SHEET_H - T.SHEET_MARGIN + 1e-6
                         for pl in placements)
            check(close >= T.PART_GAP - 0.05 and inside,
                  f"{mat} mm sheet {n}: {len(placements)} parts, closest {close:.1f} mm, "
                  f"all inside the {T.SHEET_MARGIN:.0f} mm edge")

    section("[6] built DXF")
    doc = ezdxf.readfile(HERE / "out" / "cone-table.dxf")
    msp = doc.modelspace()
    cut = msp.query('LWPOLYLINE[layer=="CUT"]')
    kerf = msp.query(f'LWPOLYLINE[layer=="{build.KERF_LAYER}"]')
    n_cut = sum((1 + p.n_holes) * p.qty for p in parts)
    n_kerf = sum(p.kerfs * p.qty for p in parts)
    check(doc.units == ezdxf.units.MM, "units = mm")
    check(len(cut) == n_cut and all(e.closed for e in cut), f"{len(cut)} closed CUT profiles")
    check(len(kerf) == n_kerf and all(e.closed for e in kerf),
          f"{len(kerf)} closed kerf pockets on {build.KERF_LAYER}")
    widths = set()
    for e in kerf:
        pts = list(e.get_points("xy"))
        widths.add(round(math.dist(pts[0], pts[1]), 3))
    check(widths == {T.TOOL_D}, f"every kerf is exactly {T.TOOL_D:.0f} mm wide")

    section("[7] stability (tipping with a load on the top edge)")
    vol = 0.0
    for p in parts:
        cuts, _ = build.split_loops(p, p.loops)
        area = Polygon(L.flatten_loop(cuts[0])).area - sum(
            Polygon(L.flatten_loop(h)).area for h in cuts[1:])
        th = T.T_SHELL if p.material == f"{T.T_SHELL:g}" else T.T_BOARD
        vol += area * th * p.qty
    mass = vol * 1e-9 * DENSITY
    lever = T.TOP_D / 2 - T.R_BOT
    tip = mass * T.R_BOT / lever
    check(tip >= 40.0, f"table ~{mass:.1f} kg; tips with {tip:.0f} kg pressed on the top edge "
                       f"(>= 40 kg)")
    note("add 5-10 kg ballast on FORMER-BASE if the table will be leaned on")

    print(f"\nFAILURES: {len(FAIL)}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
