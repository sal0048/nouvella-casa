"""Nest the curl lounge chair parts and write the CNC cut file.

Layers
------
CUT               closed cut profiles (outlines, ring openings, mortises)
ENGRAVE-LABEL     part number + name + instance, placed on the part itself
REFERENCE-SHEET   sheet outlines and titles (not cut)
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))  # shared code, lower priority

import ezdxf
from ezdxf.enums import TextEntityAlignment

import chair_geometry as C
import labels as B
import sofa_layout as L

SHEET_PITCH_Y = C.SHEET_H + 250.0
OUT = HERE / "out"


def layout(sets: int = 1):
    parts = C.build_parts()
    for p in parts:
        p.qty *= sets
    sheets = L.nest(L.build_instances(parts), sheet_w=C.SHEET_W, sheet_h=C.SHEET_H,
                    margin=C.SHEET_MARGIN, gap=C.PART_GAP)
    return parts, sheets


def write_dxf(parts, sheets, path: Path) -> list:
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()
    doc.layers.add("CUT", color=1)
    doc.layers.add("ENGRAVE-LABEL", color=3)
    doc.layers.add("REFERENCE-SHEET", color=8)

    labelled = B.all_labels(parts, sheets)
    for index, sheet in enumerate(labelled):
        oy = -index * SHEET_PITCH_Y
        msp.add_lwpolyline(
            [(0, oy), (C.SHEET_W, oy), (C.SHEET_W, oy + C.SHEET_H), (0, oy + C.SHEET_H)],
            format="xy", close=True, dxfattribs={"layer": "REFERENCE-SHEET"})
        msp.add_text(
            f"SHEET {index + 1}/{len(sheets)}  -  2440 x 1220 x {C.T:.0f} mm MDF",
            height=40.0, dxfattribs={"layer": "REFERENCE-SHEET"},
        ).set_placement((0.0, oy + C.SHEET_H + 55.0))
        for p, lab in sheet:
            for loop in p.loops:
                msp.add_lwpolyline([(x, y + oy, b) for x, y, b in loop], format="xyb",
                                   close=True, dxfattribs={"layer": "CUT"})
            if lab is None:
                raise ValueError(f"no room to engrave a label on {p.label} {p.instance}")
            msp.add_text(lab.text, height=lab.height,
                         dxfattribs={"layer": "ENGRAVE-LABEL", "rotation": lab.angle},
                         ).set_placement((lab.x, lab.y + oy),
                                         align=TextEntityAlignment.MIDDLE_CENTER)
    doc.saveas(path)
    return labelled


def main() -> None:
    OUT.mkdir(exist_ok=True)
    sets = int(sys.argv[sys.argv.index("--sets") + 1]) if "--sets" in sys.argv else 1
    name = "curl-chair.dxf" if sets == 1 else f"curl-chair_x{sets}.dxf"
    parts, sheets = layout(sets)
    write_dxf(parts, sheets, OUT / name)
    area = sum(L.part_area(p.loops) * p.qty for p in parts)
    print(f"wrote {OUT / name}: {sum(p.qty for p in parts)} parts "
          f"on {len(sheets)} sheets, {area / 1e6:.2f} m2 of parts "
          f"({area / 1e6 / (len(sheets) * 2.44 * 1.22) * 100:.0f}% of the board)")


if __name__ == "__main__":
    main()
