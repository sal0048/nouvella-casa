"""Curved 3-seat sofa (crescent) - CNC cut layout, 15 mm plywood.

Standalone 2D drafting generator: every part of the slot-and-tab plywood frame
is nested onto 2440 x 1220 sheets and emitted as closed cut profiles.

Layers
------
CUT               closed cut profiles (outer contours, slots, lightening holes)
ENGRAVE-LABEL     part identification text
REFERENCE-SHEET   sheet outlines and sheet titles (not cut)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ezdxf

import sofa_geometry as G
import sofa_layout as L

SHEET_PITCH_Y = G.SHEET_H + 250.0

LAYER_CUT = "CUT"
LAYER_LABEL = "ENGRAVE-LABEL"
LAYER_REF = "REFERENCE-SHEET"


def gen_dxf():
    parts, sheets = L.layout()

    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4  # millimetres
    msp = doc.modelspace()

    doc.layers.add(LAYER_CUT, color=1)
    doc.layers.add(LAYER_LABEL, color=3)
    doc.layers.add(LAYER_REF, color=8)

    for index, sheet in enumerate(sheets):
        placements = sheet["placements"]
        oy = -index * SHEET_PITCH_Y

        msp.add_lwpolyline(
            [(0.0, oy), (G.SHEET_W, oy), (G.SHEET_W, oy + G.SHEET_H), (0.0, oy + G.SHEET_H)],
            format="xy", close=True, dxfattribs={"layer": LAYER_REF},
        )
        msp.add_text(
            f"SHEET {index + 1}/{len(sheets)}  -  2440 x 1220  -  {sheet['material']}",
            height=40.0, dxfattribs={"layer": LAYER_REF},
        ).set_placement((0.0, oy + G.SHEET_H + 55.0))

        for p in placements:
            for loop in p.loops:
                msp.add_lwpolyline(
                    [(x, y + oy, b) for x, y, b in loop],
                    format="xyb", close=True, dxfattribs={"layer": LAYER_CUT},
                )
            label = p.label if p.instance == 1 and _qty(parts, p.key) == 1 \
                else f"{p.label} {p.instance}/{_qty(parts, p.key)}"
            msp.add_text(
                label, height=22.0, dxfattribs={"layer": LAYER_LABEL},
            ).set_placement((p.x + 14.0, p.y + oy + 14.0))

    return {"document": doc}


def _qty(parts, key: str) -> int:
    for part in parts:
        if part.key == key:
            return part.qty
    return 1


if __name__ == "__main__":
    result = gen_dxf()
    out = Path(__file__).resolve().parent / "out" / "curved-sofa.dxf"
    out.parent.mkdir(parents=True, exist_ok=True)
    result["document"].saveas(out)
    print(f"wrote {out}")
