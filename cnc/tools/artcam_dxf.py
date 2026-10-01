"""Rewrite a DXF so ArtCAM imports it cleanly.

    python3 artcam_dxf.py in.dxf [out_dir]

ArtCAM (2008 - 2018) reads DXF R12 most reliably. Newer files (R2010,
LWPOLYLINE, extended layer names) can import empty, lose arcs or open
the vectors. This writes two files next to each other:

  <name>_ArtCAM_R12.dxf        R12, every loop a closed 2D POLYLINE, arcs kept
                               as bulges (exact geometry)
  <name>_ArtCAM_R12_lines.dxf  R12, arcs flattened to short straight segments
                               (max 0.02 mm off the arc) - the fallback if an
                               ArtCAM version mis-reads bulges

Layer names are made R12-safe (A-Z 0-9 _ - $ only, so "POCKET-KERF-15.5"
becomes "POCKET-KERF-15_5"). Text is dropped (ArtCAM imports it as vectors
you would then have to delete). R12 has no units field: choose millimetres
in ArtCAM's import dialog. Both outputs are re-read and compared loop by
loop with the source (count, closed, area) before the script reports OK.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import ezdxf
import ezdxf.bbox
from shapely.geometry import Polygon

SAGITTA = 0.02          # mm, max distance of a flattened segment from its arc


def safe_layer(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_$-]", "_", name).upper()[:31] or "0"


def flatten(points, closed=True):
    """(x, y, bulge) vertices -> (x, y) with arcs split into short chords."""
    out = []
    n = len(points)
    for i in range(n if closed else n - 1):
        x0, y0, b = points[i]
        x1, y1, _ = points[(i + 1) % n]
        out.append((x0, y0))
        if abs(b) < 1e-12:
            continue
        theta = 4.0 * math.atan(b)                     # included angle, signed
        chord = math.hypot(x1 - x0, y1 - y0)
        if chord < 1e-9:
            continue
        r = chord / (2.0 * math.sin(abs(theta) / 2.0))
        steps = max(2, math.ceil(abs(theta) / (2.0 * math.acos(max(-1.0, 1.0 - SAGITTA / r)))))
        # arc centre
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        d = math.sqrt(max(r * r - (chord / 2) ** 2, 0.0))
        ux, uy = -(y1 - y0) / chord, (x1 - x0) / chord
        sgn = 1.0 if (b > 0) == (abs(theta) < math.pi) else -1.0
        cx, cy = mx + sgn * d * ux, my + sgn * d * uy
        a0 = math.atan2(y0 - cy, x0 - cx)
        for k in range(1, steps):
            a = a0 + theta * k / steps
            out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def loops_of(path):
    """[(layer, [(x, y, bulge)...], closed)] for every polyline in the file."""
    doc = ezdxf.readfile(path)
    out = []
    for e in doc.modelspace():
        t = e.dxftype()
        if t == "LWPOLYLINE":
            pts = [(x, y, b) for x, y, _, _, b in e.get_points("xyseb")]
            out.append((e.dxf.layer, pts, e.closed))
        elif t == "POLYLINE":
            pts = [(v.dxf.location.x, v.dxf.location.y, v.dxf.get("bulge", 0.0)) for v in e.vertices]
            out.append((e.dxf.layer, pts, e.is_closed))
        elif t in ("TEXT", "MTEXT"):
            continue
        else:
            raise SystemExit(f"unsupported entity {t} on layer {e.dxf.layer}: extend artcam_dxf.py")
    return doc, out


def write(loops, layers, path, lines):
    doc = ezdxf.new("R12")
    for name, color in layers.items():
        if name not in doc.layers:
            doc.layers.add(safe_layer(name), color=color)
    msp = doc.modelspace()
    for layer, pts, closed in loops:
        attribs = {"layer": safe_layer(layer)}
        if lines:
            msp.add_polyline2d(flatten(pts, closed), close=closed, dxfattribs=attribs)
        else:
            pl = msp.add_polyline2d([(x, y) for x, y, _ in pts], close=closed, dxfattribs=attribs)
            for v, (_, _, b) in zip(pl.vertices, pts):
                if abs(b) > 1e-12:
                    v.dxf.bulge = b
    # real drawing extents: some importers size the model from the header
    # (ezdxf writes the empty-drawing defaults 1e+20 on save, so patch the text)
    box = ezdxf.bbox.extents(msp)
    doc.saveas(path)
    txt = Path(path).read_text(encoding="cp1252")
    for var, vals in (("$EXTMIN", (box.extmin.x, box.extmin.y, 0.0)),
                      ("$EXTMAX", (box.extmax.x, box.extmax.y, 0.0)),
                      ("$LIMMIN", (min(0.0, box.extmin.x), min(0.0, box.extmin.y))),
                      ("$LIMMAX", (box.extmax.x, box.extmax.y))):
        codes = (" 10", " 20", " 30")[:len(vals)]
        lines = txt.split("\n")
        i = lines.index(var)                 # value pairs follow the name
        for k, (c, v) in enumerate(zip(codes, vals)):
            assert lines[i + 1 + 2 * k].strip() == c.strip()
            lines[i + 2 + 2 * k] = f"{v:.4f}"
        txt = "\n".join(lines)
    Path(path).write_text(txt, encoding="cp1252")


def area(pts, closed):
    flat = flatten(pts, closed)          # a 2-vertex loop with bulges is a full circle
    return Polygon(flat).area if closed and len(flat) > 2 else 0.0


def main(src: Path, out_dir: Path) -> int:
    doc, loops = loops_of(src)
    layers = {l.dxf.name: l.dxf.color for l in doc.layers if l.dxf.name not in ("0", "Defpoints")}
    stem = src.stem.split("-", 1)[-1] if re.match(r"^[0-9a-f]{8}-", src.stem) else src.stem
    ok = True
    for suffix, lines in (("_ArtCAM_R12", False), ("_ArtCAM_R12_lines", True)):
        dst = out_dir / f"{stem}{suffix}.dxf"
        write(loops, layers, dst, lines)
        _, back = loops_of(dst)
        same = len(back) == len(loops) and all(
            c0 == c1 and safe_layer(l0) == l1 and abs(area(p0, c0) - area(p1, c1)) < 0.5
            for (l0, p0, c0), (l1, p1, c1) in zip(loops, back))
        ver = ezdxf.readfile(dst).dxfversion
        print(f"{'OK  ' if same else 'FAIL'} {dst.name}: {ver}, {len(back)} loops, "
              f"{sum(c for *_, c in back)} closed, layers {sorted({l for l, *_ in back})}")
        ok &= same
    return 0 if ok else 1


if __name__ == "__main__":
    src = Path(sys.argv[1])
    raise SystemExit(main(src, Path(sys.argv[2]) if len(sys.argv) > 2 else src.parent))
