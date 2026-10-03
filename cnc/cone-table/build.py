"""Nest the cone table parts per board thickness and write the CNC file.

Layers
------
CUT                 through cuts (outlines, ring openings)
POCKET-KERF-7.5     kerf pockets on the BACK face of the shell, depth
                    T_SHELL - SKIN, full width = cutter diameter
ENGRAVE-LABEL       part number + name on the part itself
REFERENCE-SHEET     sheet outlines, titles and labels for parts too narrow
                    to engrave (not cut)
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))  # shared code, lower priority

import ezdxf
from ezdxf.enums import TextEntityAlignment

import labels as B
import sofa_layout as L
import table_geometry as T

OUT = HERE / "out"
SHEET_PITCH_Y = T.SHEET_H + 250.0
KERF_LAYER = f"POCKET-KERF-{T.DEPTH:g}"
BOARD_LAYER = "BOARD-2440x1220"     # sheet frame, reference only (not cut)


def layout(sets: int = 1):
    """{material: sheets} with every part nested by its true shape.
    sets > 1 nests that many complete tables together."""
    parts = T.build_parts()
    for p in parts:
        p.qty *= sets
    groups = {}
    for mat in sorted({p.material for p in parts}, key=float):
        sub = [p for p in parts if p.material == mat]
        groups[mat] = L.nest(L.build_instances(sub), sheet_w=T.SHEET_W,
                             sheet_h=T.SHEET_H, margin=T.SHEET_MARGIN,
                             gap=T.PART_GAP)
    return parts, groups


def kerf_len(rect):
    (x0, y0, _), _, _, (x3, y3, _) = rect
    return math.hypot(x3 - x0, y3 - y0)


def extend_kerf(rect, by, full=True):
    """Lengthen a kerf rectangle along its long axis so the pocket runs out
    through the wide edge, and through the narrow edge too if it is a
    full-length kerf (short in-between kerfs stop inside the part)."""
    (x0, y0, _), (x1, y1, _), (x2, y2, _), (x3, y3, _) = rect
    ux, uy = x3 - x0, y3 - y0
    n = math.hypot(ux, uy)
    ux, uy = ux / n * by, uy / n * by
    vx, vy = (ux, uy) if full else (0.0, 0.0)
    return [(x0 - vx, y0 - vy), (x1 - vx, y1 - vy), (x2 + ux, y2 + uy), (x3 + ux, y3 + uy)]


def kerf_polys(kerfs, dy=0.0):
    longest = max((kerf_len(k) for k in kerfs), default=0.0)
    by = T.KERF_TRIM + T.TOOL_D / 2 + T.KERF_OVERRUN      # cutter centre KERF_OVERRUN past the edge
    return [[(x, y + dy) for x, y in extend_kerf(k, by, kerf_len(k) > longest - 1.0)]
            for k in kerfs]


def split_loops(part, loops):
    k0 = 1 + part.n_holes
    return loops[:k0], loops[k0:]


def write_dxf(parts, groups, path: Path, clean: bool = False) -> dict:
    """clean=True: machine file - CUT, kerf pockets and the board frame on
    its own layer; no text, no text styles."""
    by_key = {p.key: p for p in parts}
    # clean: no text styles either, so viewers do not ask for fonts
    doc = ezdxf.new("R2010", setup=not clean)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()
    doc.layers.add("CUT", color=1)
    doc.layers.add(KERF_LAYER, color=5)
    if clean:
        doc.layers.add(BOARD_LAYER, color=8)
    if not clean:
        doc.layers.add("ENGRAVE-LABEL", color=3)
        doc.layers.add("REFERENCE-SHEET", color=8)

    stats = dict(cut=0, kerf=0, engraved=0, reference=0, sheets=0)
    row = 0
    for mat, sheets in groups.items():
        labelled = B.all_labels(parts, sheets)
        for index, sheet in enumerate(labelled):
            oy = -row * SHEET_PITCH_Y
            row += 1
            stats["sheets"] += 1
            if clean:
                msp.add_lwpolyline([(0, oy), (T.SHEET_W, oy), (T.SHEET_W, oy + T.SHEET_H),
                                    (0, oy + T.SHEET_H)], format="xy", close=True,
                                   dxfattribs={"layer": BOARD_LAYER})
                for pl, _ in sheet:
                    cuts, kerfs = split_loops(by_key[pl.key], pl.loops)
                    for loop in cuts:
                        msp.add_lwpolyline([(x, y + oy, b) for x, y, b in loop], format="xyb",
                                           close=True, dxfattribs={"layer": "CUT"})
                        stats["cut"] += 1
                    for poly in kerf_polys(kerfs, oy):
                        msp.add_lwpolyline(poly, format="xy", close=True,
                                           dxfattribs={"layer": KERF_LAYER})
                        stats["kerf"] += 1
                continue
            msp.add_lwpolyline([(0, oy), (T.SHEET_W, oy), (T.SHEET_W, oy + T.SHEET_H),
                                (0, oy + T.SHEET_H)], format="xy", close=True,
                               dxfattribs={"layer": "REFERENCE-SHEET"})
            msp.add_text(f"{mat} mm BOARD - SHEET {index + 1}/{len(sheets)} - 2440 x 1220"
                         + ("  (kerf side = BACK face, show face down)" if mat == f"{T.T_SHELL:g}" else ""),
                         height=40.0, dxfattribs={"layer": "REFERENCE-SHEET"}
                         ).set_placement((0.0, oy + T.SHEET_H + 55.0))
            for pl, lab in sheet:
                part = by_key[pl.key]
                cuts, kerfs = split_loops(part, pl.loops)
                for loop in cuts:
                    msp.add_lwpolyline([(x, y + oy, b) for x, y, b in loop], format="xyb",
                                       close=True, dxfattribs={"layer": "CUT"})
                    stats["cut"] += 1
                for poly in kerf_polys(kerfs, oy):
                    msp.add_lwpolyline(poly, format="xy", close=True,
                                       dxfattribs={"layer": KERF_LAYER})
                    stats["kerf"] += 1
                text = f"{part.num:02d} {part.label}"
                if lab is not None:
                    msp.add_text(lab.text, height=lab.height, rotation=lab.angle,
                                 dxfattribs={"layer": "ENGRAVE-LABEL"}).set_placement(
                        (lab.x, lab.y + oy), align=TextEntityAlignment.MIDDLE_CENTER)
                    stats["engraved"] += 1
                else:
                    msp.add_text(text + "  (mark by hand)", height=25.0,
                                 dxfattribs={"layer": "REFERENCE-SHEET"}).set_placement(
                        (pl.x + pl.w / 2, pl.y + pl.h / 2 + oy),
                        align=TextEntityAlignment.MIDDLE_CENTER)
                    stats["reference"] += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(path)
    return stats


def write_part(part, path: Path):
    """One part, unnested, at the origin (individual_parts/)."""
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()
    doc.layers.add("CUT", color=1)
    doc.layers.add(KERF_LAYER, color=5)
    loops = L.normalise(part.loops)
    cuts, kerfs = split_loops(part, loops)
    for loop in cuts:
        msp.add_lwpolyline(loop, format="xyb", close=True, dxfattribs={"layer": "CUT"})
    for poly in kerf_polys(kerfs):
        msp.add_lwpolyline(poly, format="xy", close=True, dxfattribs={"layer": KERF_LAYER})
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(path)


def main():
    sets = int(sys.argv[sys.argv.index("--sets") + 1]) if "--sets" in sys.argv else 1
    parts, groups = layout(sets)
    name = "cone-table.dxf" if sets == 1 else f"cone-table_x{sets}.dxf"
    stats = write_dxf(parts, groups, OUT / name)
    clean = f"CONE_{T.T_SHELL:g}MM_CUT.dxf" if sets == 1 else f"CONE_{T.T_SHELL:g}MM_CUT_x{sets}.dxf"
    print("clean:", write_dxf(parts, groups, OUT / clean, clean=True))
    if sets == 1:
        for p in parts + [T.coupon()]:
            write_part(p, OUT / "parts" / f"P{p.num:02d}_{p.label}_x{p.qty}.dxf")
    for mat, sheets in groups.items():
        print(f"{mat} mm: {len(sheets)} sheet(s): "
              + " | ".join(", ".join(pl.label for pl in s) for s in sheets))
    print(stats)


if __name__ == "__main__":
    main()
