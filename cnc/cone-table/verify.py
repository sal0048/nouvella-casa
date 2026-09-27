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
    shells = [p for p in parts if p.kerfs]

    section("[2] cone development (show face does not stretch)")
    for p in shells:
        m = p.meta
        arc_out, arc_in = T.THETA * m["s_out"], T.THETA * m["s_in"]
        c_bot, c_top = 2 * math.pi * T.R(m["za"]), 2 * math.pi * T.R(m["zb"])
        check(abs(arc_out - c_bot) < 1e-6 and abs(arc_in - c_top) < 1e-6,
              f"{p.label}: edge arcs {arc_out:.1f}/{arc_in:.1f} mm = cone circumferences "
              f"at z {m['za']:.0f}/{m['zb']:.0f}")
        slant = m["s_out"] - m["s_in"]
        want = math.hypot(m["zb"] - m["za"], T.R(m["za"]) - T.R(m["zb"]))
        check(abs(slant - want) < 1e-6, f"{p.label}: pattern depth {slant:.1f} mm = slant height")
    if len(shells) == 2:
        check(abs(shells[0].meta["s_in"] - shells[1].meta["s_out"]) < 1e-9,
              f"shells meet at the joint: {shells[0].meta['s_in']:.2f} mm both sides")

    section("[3] kerfs")
    need = T.closure_total()
    for p in shells:
        m = p.meta
        lay = T.kerf_layout(m["s_in"], m["s_out"])
        worst_hinge, pitches = 1e9, []
        for i in range(200):                      # sample along the generatrix
            sv = m["s_in"] + (m["s_out"] - m["s_in"]) * (i + 0.5) / 200
            count = sum(1 for _, r0, r1 in lay if r0 <= sv <= r1)
            pitch = T.THETA * sv / count
            pitches.append(pitch)
            r_face = sv * T.SIN_A / T.COS_A       # R / cos(alpha)
            worst_hinge = min(worst_hinge, T.TOOL_D * r_face / pitch)
        per = need / m["n_full"]
        check(per < T.TOOL_D, f"{p.label}: each kerf closes at most {per:.2f} mm of its "
                              f"{T.TOOL_D:.0f} mm width (back face never jams)")
        check(min(pitches) - T.TOOL_D >= 4.0,
              f"{p.label}: {m['n_full']} full + {m['n_kerf'] - m['n_full']} short kerfs, "
              f"wood between kerfs {min(pitches) - T.TOOL_D:.1f}-{max(pitches) - T.TOOL_D:.1f} mm")
        note(f"{p.label}: skin {T.SKIN} mm bends at ~R{worst_hinge:.0f} over each kerf at worst "
             f"(strain ~{T.SKIN / 2 / worst_hinge * 100:.1f}%) - confirm with the bend-test coupon")
    check(T.SKIN >= 2.0 and T.DEPTH > 0, f"pocket depth {T.DEPTH:g} mm leaves a "
                                         f"{T.SKIN:g} mm skin on {T.T_SHELL:g} mm board")
    check(T.KERF_OVERRUN >= T.TOOL_D / 2, "full kerfs run out through both curved edges, short ones through the wide edge")

    section("[4] formers and collar sit where they should")
    for k in ("FBASE", "FJLO", "FJUP", "FTOP"):
        m = by[k].meta
        tight = T.R_in(m["z1"]) - m["r"]
        loose = T.R_in(m["z0"]) - m["r"]
        wedge = T.T_BOARD * (T.SIN_A / T.COS_A)       # vertical edge vs sloped shell
        check(0 < tight <= 1.0 and abs(loose - tight - wedge) < 0.05,
              f"{by[k].label}: bears on the shell along its upper edge ({tight:.1f} mm); "
              f"the {wedge:.1f} mm wedge below is pure cone slope")
    note(f"the formers' vertical edges leave a {T.T_BOARD * T.SIN_A / T.COS_A:.1f} mm wedge "
         f"under the shell: fill it with PU glue or a bead of filler")
    if "COLLAR" in by:
        rc = by["COLLAR"].meta["r"]
        z_rest = (T.R_BOT - rc) / (T.R_BOT - T.R_TOP) * T.H_CONE
        centre = z_rest + T.T_BOARD / 2
        check(abs(centre - T.Z_SPLIT) <= 3.0,
              f"collar slides down to z {z_rest:.1f}, centred {centre - T.Z_SPLIT:+.1f} mm "
              f"on the joint")
    check(abs(by["FTOP"].meta["z1"] - T.H_CONE) < 1e-9,
          f"FORMER-TOP closes the cone flush at z {T.H_CONE:.0f} (no table top)")

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

    section("[7] structural core")
    import joints as J
    cores = [p for p in parts if p.key.startswith("CORE")]
    formers = {k: by[k] for k in ("FBASE", "FJLO", "FJUP", "FTOP")}
    below = {1: "FBASE", 2: "FJUP"}
    above = {1: "FJLO", 2: "FTOP"}
    for p in cores:
        m = p.meta
        lv = int(p.key[4])
        gaps = [T.R_in(z) - T.core_hw(z) for z in (m["za"], m["zb"])]
        check(min(gaps) >= 0.5, f"{p.label}: plate edge {min(gaps):.1f} mm inside the shell "
                                f"along its whole height (edge follows the cone)")
        miss = 0
        for key, spans in ((below[lv], m["bot"]), (above[lv], m["top"])):
            cents = [Polygon(L.flatten_loop(h)).centroid for h in formers[key].loops[1:]]
            for x0, x1 in spans:
                xc = (x0 + x1) / 2
                c, s_ = math.cos(math.radians(m["phi"])), math.sin(math.radians(m["phi"]))
                if not any(abs(q.x - xc * c) < 0.05 and abs(q.y - xc * s_) < 0.05 for q in cents):
                    miss += 1
        tabs = [x1 - x0 for x0, x1 in m["bot"] + m["top"]]
        check(miss == 0 and min(tabs) >= T.TAB_MIN,
              f"{p.label}: {len(m['bot'])} + {len(m['top'])} tabs ({min(tabs):.1f}-"
              f"{max(tabs):.1f} mm) each land in a mortise of {below[lv]} / {above[lv]}")
        solid = B.material(p.loops)
        r_tool = T.TOOL_D / 2
        uncut = solid.buffer(r_tool, quad_segs=32).buffer(-r_tool, quad_segs=32).difference(solid)
        worst = max((g.area for g in getattr(uncut, "geoms", [uncut])), default=0.0)
        check(p.relieved >= 4 and worst < 0.5,
              f"{p.label}: {p.relieved} inside corners relieved, worst spot the cutter "
              f"cannot reach {worst:.2f} mm2")
    for lv in (1, 2):
        a_, b_ = by[f"CORE{lv}A"].meta, by[f"CORE{lv}B"].meta
        check(a_["from_top"] and not b_["from_top"] and abs((a_["phi"] - b_["phi"]) % 180 - 90) < 1e-9,
              f"level {lv}: plates cross at 90 deg, half-laps meet at mid height "
              f"({(a_['za'] + a_['zb']) / 2:.0f} mm), slot {T.JOINT.slot_w:g} mm for {T.T_BOARD:g} mm board")
    for key, f in formers.items():
        worst = min(f.meta["r"] - max(math.hypot(x, y) for x, y in L.flatten_loop(h))
                    for h in f.loops[1:])
        check(worst >= T.MORTISE_WEB - 0.05,
              f"{f.label}: {len(f.loops) - 1} mortises, thinnest web to the rim {worst:.1f} mm")
    from shapely.affinity import rotate
    from shapely.geometry import box
    from shapely.ops import unary_union
    holes_lo = unary_union([Polygon(L.flatten_loop(h)) for h in by["FJLO"].loops[1:]])
    worst = 1.0
    for k in ("CORE2A", "CORE2B"):
        m = by[k].meta
        for x0, x1 in m["bot"]:
            foot = rotate(box(x0, -T.T_BOARD / 2, x1, T.T_BOARD / 2), m["phi"], origin=(0, 0))
            worst = min(worst, 1 - foot.intersection(holes_lo).area / foot.area)
    check(worst >= 0.8, f"level 2 turned 45 deg: every tab end sits >= {worst * 100:.0f}% "
                        f"on solid JOINT-LO (>= 80%)")
    # bearing: 150 kg standing on the top, carried by the top tabs of level 2
    # (the untabbed plate's top edge also bears under FORMER-TOP: ignored)
    area = sum((x1 - x0) * T.T_BOARD for x0, x1 in by["CORE2A"].meta["top"] + by["CORE2B"].meta["top"])
    stress = 150 * 9.81 / area
    check(stress < 3.0, f"150 kg on the top: {stress:.2f} MPa on the core tab ends "
                        f"(< 3 MPa, conservative for MDF)")

    print(f"\nFAILURES: {len(FAIL)}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
