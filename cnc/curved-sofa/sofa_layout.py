"""Sheet nesting for the curved sofa cut file.

Flattens every part loop (bulges included) to sample points so bounding boxes
and areas are exact, then nests the instances by their true shape onto
2440 x 1220 sheets.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import shapely
from ezdxf.math import bulge_to_arc
from shapely.geometry import Polygon

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


# --------------------------------------------------------------------------
# True-shape nesting
# --------------------------------------------------------------------------
#
# Each part is rasterised on a RES grid after growing it by half the part gap
# plus half a cell diagonal. Two masks that share no cell are therefore
# provably at least PART_GAP apart (any point closer than that would lie in a
# cell whose centre both grown shapes cover). Every legal position of a part on
# a sheet is found at once with an FFT correlation of the sheet occupancy with
# the part mask, and the part goes to the lowest-left legal spot. That lets
# L-shaped ribs interlock and curved rails stack inside one another, which a
# bounding-box packer cannot do.

RES = 4.0                       # grid cell, mm
ANGLES = (0.0, 90.0, 180.0, 270.0)
REPAIR_ANGLES = tuple(float(a) for a in range(0, 360, 5))


def _outline(loops):
    return Polygon(flatten_loop(loops[0]))


def _material(loops):
    """Outline minus internal loops: big openings (ring centres) stay free
    for other parts; slots vanish once the mask is grown by the gap."""
    solid = _outline(loops)
    for hole in loops[1:]:
        solid = solid.difference(Polygon(flatten_loop(hole)))
    return solid


def _mask(loops, gap):
    """Conservative occupancy mask of a part whose bbox min sits at (0, 0).

    Returns (mask, off) where off is the number of cells the mask extends
    below/left of the part origin.
    """
    pad = gap / 2.0 + RES * math.sqrt(0.5)
    grown = _material(loops).buffer(pad, quad_segs=8)
    off = math.ceil(pad / RES)
    x0, y0, x1, y1 = grown.bounds
    nx = math.ceil(x1 / RES) + off
    ny = math.ceil(y1 / RES) + off
    xs = (np.arange(nx) - off + 0.5) * RES
    ys = (np.arange(ny) - off + 0.5) * RES
    gx, gy = np.meshgrid(xs, ys)
    inside = shapely.contains_xy(grown, gx, gy)
    return inside.astype(np.float64), off


def _legal(occ, mask):
    """Boolean map of top-left cells where ``mask`` fits on ``occ``."""
    ny, nx = occ.shape
    my, mx = mask.shape
    if my > ny or mx > nx:
        return None
    shape = (ny + my - 1, nx + mx - 1)
    f = np.fft.rfft2(occ, shape) * np.fft.rfft2(mask[::-1, ::-1], shape)
    conv = np.fft.irfft2(f, shape)
    valid = conv[my - 1:ny, mx - 1:nx]
    return valid < 0.5


def _best_spot(occ, orients, gravity):
    """Lowest-left (or lowest-down) legal spot over all orientations."""
    best, best_rank = None, None
    for ang, rl, w, h, mask, off in orients:
        legal = _legal(occ, mask)
        if legal is None or not legal.any():
            continue
        rows, cols = np.nonzero(legal)
        k = (np.lexsort((rows, cols)) if gravity == "left"
             else np.lexsort((cols, rows)))[0]
        rank = (cols[k], rows[k]) if gravity == "left" else (rows[k], cols[k])
        if best is None or rank < best_rank:
            best_rank = rank
            best = (cols[k], rows[k], ang, rl, w, h, mask, off)
    return best


def nest(instances, sheet_w=G.SHEET_W, sheet_h=G.SHEET_H,
         margin=G.SHEET_MARGIN, gap=G.PART_GAP,
         angles=ANGLES, gravity="left"):
    """Fill one sheet at a time with the largest remaining part that fits.

    Identical instances share their rotated masks. A sheet is closed only
    when no remaining part fits anywhere on it, so small parts are pulled
    into the gaps left by the big ones instead of opening new sheets.
    """
    nx = int((sheet_w - 2 * margin) // RES)
    ny = int((sheet_h - 2 * margin) // RES)

    def orient(loops, angs):
        out = []
        for ang in angs:
            rl = normalise([G.rotate_loop(l, ang) for l in loops])
            bb = loops_bbox(rl)
            mask, off = _mask(rl, gap)
            out.append((ang, rl, bb[2] - bb[0], bb[3] - bb[1], mask, off))
        return out

    def put(occ, spot, key, label, idx):
        j, i, ang, rl, w, h, mask, off = spot
        my, mx = mask.shape
        occ[i:i + my, j:j + mx] = np.maximum(occ[i:i + my, j:j + mx], mask)
        x = margin + (j + off) * RES
        y = margin + (i + off) * RES
        return Placement(key, label, idx, [G.translate_loop(l, x, y) for l in rl],
                         x, y, w, h, ang % 180.0 != 0.0)

    shapes = {}                      # key -> (orients, area)
    source = {}                      # key -> unrotated loops
    queue = []                       # (key, label, idx)
    for key, label, idx, loops in instances:
        if key not in shapes:
            shapes[key] = (orient(loops, angles), _outline(loops).area)
            source[key] = loops
        queue.append((key, label, idx))
    queue.sort(key=lambda q: (-shapes[q[0]][1], q[0], q[2]))

    sheets, grids = [], []
    while queue:
        occ = np.zeros((ny, nx))
        placements = []
        while True:
            tried = set()
            for n, (key, label, idx) in enumerate(queue):
                if key in tried:
                    continue
                tried.add(key)
                spot = _best_spot(occ, shapes[key][0], gravity)
                if spot is None:
                    continue
                placements.append(put(occ, spot, key, label, idx))
                del queue[n]
                break
            else:
                break                # nothing left fits this sheet
        if not placements:
            raise ValueError(f"{queue[0][1]} does not fit on a sheet")
        sheets.append(placements)
        grids.append(occ)

    # repair: try to empty the last sheet into the earlier ones, now with
    # fine rotations. Worth it whenever that sheet is only partly used.
    fine = {}
    while len(sheets) > 1:
        moved = []
        for p in sheets[-1]:
            if p.key not in fine:
                fine[p.key] = orient(source[p.key], REPAIR_ANGLES)
            for occ, placements in zip(grids[:-1], sheets[:-1]):
                spot = _best_spot(occ, fine[p.key], gravity)
                if spot is not None:
                    placements.append(put(occ, spot, p.key, p.label, p.instance))
                    moved.append(p)
                    break
        if len(moved) < len(sheets[-1]):
            # partial success still frees material on the last sheet, but the
            # moved parts have already been re-placed; keep the rest there
            sheets[-1] = [p for p in sheets[-1] if p not in moved]
            break
        sheets.pop()
        grids.pop()
    return sheets


def build_instances(parts, keys=None, exclude=None):
    inst = []
    for part in parts:
        if keys and part.key not in keys:
            continue
        if exclude and part.key in exclude:
            continue
        for i in range(part.qty):
            inst.append((part.key, part.label, i + 1, part.loops))
    return inst


def layout():
    """Nest every part by its true shape onto 2440 x 1220 sheets."""
    parts = G.build_parts()
    return parts, nest(build_instances(parts))
