"""Part numbering and engrave-label placement.

Every piece carries its part number and instance ("07 RIB 3/7"), engraved on
the part itself so it can be sorted straight off the machine bed. The label is
placed where it provably sits on material: the text box, grown by a safety
margin, must lie inside the part outline minus its holes. Longest text first,
then shorter fallbacks, then smaller heights, until one fits.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from shapely import affinity
from shapely.geometry import Polygon, box
from shapely.ops import polylabel

import sofa_layout as L

CHAR_W = 0.72          # conservative glyph advance as a fraction of height
EDGE_CLEAR = 4.0       # mm of material kept between text and any cut
HEIGHTS = (22.0, 18.0, 14.0, 11.0, 9.0, 7.0)
ANGLES = range(0, 180, 15)


@dataclass(frozen=True)
class Label:
    text: str
    x: float
    y: float
    height: float
    angle: float           # degrees, text baseline direction

    def box(self) -> Polygon:
        """Footprint of the text as a rectangle centred on (x, y)."""
        w = len(self.text) * CHAR_W * self.height
        rect = box(-w / 2.0, -self.height / 2.0, w / 2.0, self.height / 2.0)
        rect = affinity.rotate(rect, self.angle, origin=(0, 0))
        return affinity.translate(rect, self.x, self.y)


def material(loops) -> Polygon:
    """The part as a solid: outline minus every internal loop."""
    solid = Polygon(L.flatten_loop(loops[0]))
    for hole in loops[1:]:
        solid = solid.difference(Polygon(L.flatten_loop(hole)))
    return solid


def texts(num: int, label: str, instance: int, qty: int) -> list:
    """Candidate label strings, most informative first."""
    tag = f"{num:02d}"
    inst = f"{instance}/{qty}" if qty > 1 else ""
    full = " ".join(s for s in (tag, label, inst) if s)
    short = " ".join(s for s in (tag, inst) if s)
    return [full, short, tag]


def place(loops, candidates) -> Label | None:
    """Best label that fits on the part's material, or None."""
    solid = material(loops)
    safe = solid.buffer(-EDGE_CLEAR)
    if safe.is_empty:
        return None
    # anchor candidates: pole of inaccessibility of each piece of the safe area
    pieces = list(safe.geoms) if hasattr(safe, "geoms") else [safe]
    anchors = [polylabel(p, tolerance=1.0) for p in
               sorted(pieces, key=lambda g: -g.area)]
    for text in candidates:
        for h in HEIGHTS:
            for a in anchors:
                for ang in ANGLES:
                    lab = Label(text, a.x, a.y, h, float(ang))
                    if safe.contains(lab.box()):
                        return lab
    return None


def label_for(part, placement) -> Label | None:
    return place(placement.loops,
                 texts(part.num, part.label, placement.instance, part.qty))


def all_labels(parts, sheets) -> list:
    """Per sheet, a list of (placement, Label | None)."""
    by_key = {p.key: p for p in parts}
    return [[(pl, label_for(by_key[pl.key], pl)) for pl in placements]
            for placements in sheets]
