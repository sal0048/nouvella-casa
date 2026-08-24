"""Sheet nesting for the curved sofa cut file.

Flattens every part loop (bulges included) to sample points so bounding boxes
and areas are exact, then shelf-packs the instances onto 2440 x 1220 sheets.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import ezdxf
from ezdxf.math import bulge_to_arc

import sofa_geometry as G


def flatten_loop(loop, seg_per_arc: int = 48):
    """Sample a (x, y, bulge) loop into a closed polygon of points."""
    pts = []
    n = len(loop)
    for i in range(n):
        x0, y0, b = loop[i]
        x1, y1, _ = loop[(i + 1) % n]
        pts.append((x0, y0))
        if abs(b) < 1e-12:
            continue
        centre, _, _, r = bulge_to_arc((x0, y0), (x1, y1), b)
        # the bulge defines the included angle directly: positive is CCW
        sweep = 4.0 * math.atan(b)
        a0 = math.atan2(y0 - centre.y, x0 - centre.x)
        for k in range(1, seg_per_arc):
            a = a0 + sweep * k / seg_per_arc
            pts.append((centre.x + r * math.cos(a), centre.y + r * math.sin(a)))
    return pts


def loop_bbox(loop):
    pts = flatten_loop(loop)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def loops_bbox(loops):
    boxes = [loop_bbox(l) for l in loops]
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def polygon_area(pts) -> float:
    a = 0.0
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        a += x0 * y1 - x1 * y0
    return abs(a) / 2.0


def part_area(loops) -> float:
    """Outer loop area minus the area of every internal loop."""
    areas = [polygon_area(flatten_loop(l)) for l in loops]
    return areas[0] - sum(areas[1:])


def cut_length(loops) -> float:
    total = 0.0
    for loop in loops:
        pts = flatten_loop(loop)
        for i in range(len(pts)):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % len(pts)]
            total += math.hypot(x1 - x0, y1 - y0)
    return total


def normalise(loops):
    """Translate loops so the bounding box sits at the origin."""
    x0, y0, _, _ = loops_bbox(loops)
    return [G.translate_loop(l, -x0, -y0) for l in loops]


def rotate90(loops):
    return [[(-y, x, b) for x, y, b in l] for l in loops]


@dataclass
class Placement:
    key: str
    label: str
    instance: int
    loops: list          # already positioned inside the sheet
    x: float
    y: float
    w: float
    h: float
    rotated: bool


def pack(instances, sheet_w=G.SHEET_W, sheet_h=G.SHEET_H,
         margin=G.SHEET_MARGIN, gap=G.PART_GAP, collect=False):
    """First-fit-decreasing shelf packing with per-part 90 degree rotation."""
    usable_w = sheet_w - 2 * margin
    usable_h = sheet_h - 2 * margin

    items = []
    for key, label, idx, loops in instances:
        base = normalise(loops)
        rot = normalise(rotate90(loops))
        bw = loops_bbox(base)
        rw = loops_bbox(rot)
        items.append({
            "key": key, "label": label, "idx": idx,
            "orient": [
                (base, bw[2] - bw[0], bw[3] - bw[1], False),
                (rot, rw[2] - rw[0], rw[3] - rw[1], True),
            ],
        })

    # tall-and-narrow first; that shelf-packs the long curved rails and the
    # ribs far better than a width-first ordering.
    items.sort(key=lambda it: -max(it["orient"][0][1], it["orient"][0][2]))

    sheets = []          # list of {"shelves": [...]}
    for it in items:
        # preferred orientation: the one that is taller (narrow footprint),
        # falling back to the other when it does not fit the sheet at all.
        orients = sorted(it["orient"], key=lambda o: -o[2])
        orients = [o for o in orients if o[1] <= usable_w and o[2] <= usable_h]
        if not orients:
            raise ValueError(f"{it['label']} does not fit on a sheet")

        placed = False
        for sheet in sheets:
            for shelf in sheet["shelves"]:
                for loops, w, h, rot in orients:
                    if h <= shelf["h"] and shelf["used"] + w <= usable_w:
                        _place(shelf, it, loops, w, h, rot, margin, gap)
                        placed = True
                        break
                if placed:
                    break
            if placed:
                break
            loops, w, h, rot = orients[0]
            top = sheet["top"]
            if top + h <= usable_h:
                shelf = {"y": top, "h": h, "used": 0.0, "items": []}
                sheet["shelves"].append(shelf)
                sheet["top"] = top + h + gap
                _place(shelf, it, loops, w, h, rot, margin, gap)
                placed = True
                break
        if not placed:
            loops, w, h, rot = orients[0]
            sheet = {"shelves": [], "top": 0.0}
            shelf = {"y": 0.0, "h": h, "used": 0.0, "items": []}
            sheet["shelves"].append(shelf)
            sheet["top"] = h + gap
            sheets.append(sheet)
            _place(shelf, it, loops, w, h, rot, margin, gap)

    if collect:
        return sheets
    out = []
    for sheet in sheets:
        placements = []
        for shelf in sheet["shelves"]:
            placements.extend(shelf["items"])
        out.append(placements)
    return out


def _place(shelf, it, loops, w, h, rot, margin, gap):
    x = margin + shelf["used"]
    y = margin + shelf["y"]
    moved = [G.translate_loop(l, x, y) for l in loops]
    shelf["items"].append(Placement(it["key"], it["label"], it["idx"],
                                    moved, x, y, w, h, rot))
    shelf["used"] += w + gap


def free_rects(sheet, margin=G.SHEET_MARGIN, gap=G.PART_GAP,
               sheet_w=G.SHEET_W, sheet_h=G.SHEET_H):
    """Unused rectangles of a packed sheet: the tail of every shelf plus the
    strip above the last shelf."""
    usable_w = sheet_w - 2 * margin
    usable_h = sheet_h - 2 * margin
    rects = []
    for shelf in sheet["shelves"]:
        w = usable_w - shelf["used"]
        if w > 0:
            rects.append((margin + shelf["used"], margin + shelf["y"], w, shelf["h"]))
    top = sheet["top"]
    if usable_h - top > 0:
        rects.append((margin, margin + top, usable_w, usable_h - top))
    return rects


def fill(sheets, instances, gap=G.PART_GAP):
    """Grid-drop small filler parts into the leftover space of packed sheets."""
    queue = list(instances)
    for sheet in sheets:
        for rx, ry, rw, rh in free_rects(sheet):
            if not queue:
                break
            key, label, idx, loops = queue[0]
            base = normalise(loops)
            rot = normalise(rotate90(loops))
            bb, rb = loops_bbox(base), loops_bbox(rot)
            options = [(base, bb[2] - bb[0], bb[3] - bb[1], False),
                       (rot, rb[2] - rb[0], rb[3] - rb[1], True)]
            best = None
            for loops_o, w, h, rot_flag in options:
                if w > rw or h > rh:
                    continue
                count = int((rw + gap) // (w + gap)) * int((rh + gap) // (h + gap))
                if best is None or count > best[0]:
                    best = (count, loops_o, w, h, rot_flag)
            if best is None:
                continue
            _, loops_o, w, h, rot_flag = best
            cols = int((rw + gap) // (w + gap))
            rows = int((rh + gap) // (h + gap))
            for r in range(rows):
                for c in range(cols):
                    if not queue:
                        break
                    key, label, idx, _ = queue.pop(0)
                    x = rx + c * (w + gap)
                    y = ry + r * (h + gap)
                    moved = [G.translate_loop(l, x, y) for l in loops_o]
                    sheet["shelves"][0]["items"].append(
                        Placement(key, label, idx, moved, x, y, w, h, rot_flag))
            # keep the shelf bookkeeping honest: this space is now consumed
    return queue


def build_instances(parts, keys=None, exclude=None, material=None):
    inst = []
    for part in parts:
        if material and part.material != material:
            continue
        if keys is not None and part.key not in keys:
            continue
        if exclude and part.key in exclude:
            continue
        for i in range(part.qty):
            inst.append((part.key, part.label, i + 1, part.loops))
    return inst


def _flatten(raw_sheets, material):
    out = []
    for sheet in raw_sheets:
        placements = []
        for shelf in sheet["shelves"]:
            placements.extend(shelf["items"])
        out.append({"material": material, "placements": placements})
    return out


def layout():
    """Nest every part, grouped by material.

    Small backrest stiles are held back and dropped into the offcut space of
    the structural sheets rather than opening sheets of their own.
    """
    parts = G.build_parts()
    materials = []
    for part in parts:
        if part.material not in materials:
            materials.append(part.material)

    sheets = []
    for material in materials:
        filler = {"STILE"} if material == G.PLY15 else set()
        raw = pack(build_instances(parts, exclude=filler, material=material),
                   collect=True)
        if filler:
            leftover = fill(raw, build_instances(parts, keys=filler,
                                                 material=material))
            if leftover:
                raw += pack(leftover, collect=True)
        sheets += _flatten(raw, material)
    return parts, sheets
