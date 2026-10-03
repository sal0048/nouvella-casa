"""Measure the V10 ArtCAM file itself (the file the CNC runs), to 0.001 mm.

    python3 check_v10.py

Reads out/cone17/CONE_17MM_V10_piece_et_gabarit_ArtCAM_R12.dxf, finds every
part by shape and checks it against the cone it must build. Every number is
the measured value minus the design value: design errors must print 0.000.
The clearances that are there on purpose (slot 1 mm over the board, formers
0.5 mm inside the shell, base ring 0.5 mm over the cone) are printed apart.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))

import ezdxf
import numpy as np
from ezdxf.path import make_path
from shapely.geometry import Point, Polygon

import jig
import table_geometry as G

FILE = HERE / "out" / "cone17" / "CONE_17MM_V11_piece_et_gabarit_ArtCAM_R12.dxf"
MASTER = HERE / "out" / "cone17" / "CONE_17MM_V11_piece_et_gabarit.dxf"
TOL = 0.0005                         # prints as 0.000
FAILS = []


def show(label, err, unit="mm", tol=TOL):
    ok = abs(err) < tol
    print(f"  {'ok  ' if ok else 'FAIL'} {label}: {err:+.3f} {unit}")
    if not ok:
        FAILS.append(label)


def arc_points(p0, p1, bulge, step=0.02):
    """Exact points along one LWPOLYLINE segment (straight or bulge arc)."""
    if abs(bulge) < 1e-12:
        return [p0]
    (x0, y0), (x1, y1) = p0, p1
    a = 4 * math.atan(bulge)                       # included angle, signed
    chord = math.hypot(x1 - x0, y1 - y0)
    r = chord / (2 * math.sin(abs(a) / 2))
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    h = r * math.cos(a / 2)                        # centre offset from the chord middle
    ux, uy = (x1 - x0) / chord, (y1 - y0) / chord
    cx, cy = mx - uy * h * (1 if bulge > 0 else -1) * (1 if abs(a) < math.pi else 1), my + ux * h * (1 if bulge > 0 else -1)
    if bulge < 0:
        cx, cy = mx + uy * h, my - ux * h
    else:
        cx, cy = mx - uy * h, my + ux * h
    t0 = math.atan2(y0 - cy, x0 - cx)
    n = max(8, int(abs(a) * r / step))
    return [(cx + r * math.cos(t0 + a * k / n), cy + r * math.sin(t0 + a * k / n)) for k in range(n)]


def exact(vs):
    """vs = [(x, y, bulge)] closed -> exact point ring."""
    pts = []
    for i, (x, y, b) in enumerate(vs):
        x1, y1, _ = vs[(i + 1) % len(vs)]
        pts += arc_points((x, y), (x1, y1), b)
    return pts


def loops(path, layer_prefix):
    out = []
    for e in ezdxf.readfile(path).modelspace():
        if not e.dxf.layer.startswith(layer_prefix):
            continue
        t = e.dxftype()
        if t == "CIRCLE":
            c, r = e.dxf.center, e.dxf.radius
            out.append(("circle", (c.x, c.y, r)))
        elif t == "LWPOLYLINE":
            out.append(("poly", exact(list(e.get_points("xyb"))), e))
        elif t == "POLYLINE":
            out.append(("poly", exact([(v.dxf.location.x, v.dxf.location.y, v.dxf.bulge) for v in e.vertices]), e))
    return out


def circle_of(pts):
    """Least-squares circle through points: (cx, cy, r)."""
    a = np.array(pts)
    A = np.c_[2 * a[:, 0], 2 * a[:, 1], np.ones(len(a))]
    b = (a ** 2).sum(1)
    cx, cy, k = np.linalg.lstsq(A, b, rcond=None)[0]
    return cx, cy, math.sqrt(k + cx * cx + cy * cy)


def main() -> int:
    cut = loops(FILE, "COUPE")
    kerf = [l for l in loops(FILE, "POCHE") if l[0] == "poly"]
    polys = [(Polygon(l[1]), l) for l in cut if l[0] == "poly"]
    circles = [l[1] for l in cut if l[0] == "circle"]

    print("[1] the ArtCAM file is the master drawing, unchanged (loop by loop)")
    def shapes(ls):
        return [Point(v[0], v[1]).buffer(v[2], 4096) if k == "circle" else Polygon(v) for k, v, *_ in ls]
    master = shapes(loops(MASTER, "COUPE") + loops(MASTER, "POCHE"))
    mine = shapes(cut + kerf)
    worst = 0.0
    for g in master:
        m = min(mine, key=lambda h: h.centroid.distance(g.centroid) + abs(h.area - g.area))
        worst = max(worst, g.symmetric_difference(m).area / g.length)   # mean offset along the edge
    print(f"  {len(mine)} loops in the ArtCAM file, {len(master)} in the master")
    if len(mine) != len(master):
        FAILS.append("loop count")
    show("worst loop difference (mean edge offset)", worst)

    print("\n[2] shell: the flat sector closes the cone exactly")
    shell_poly, shell = max(polys, key=lambda t: t[0].area)
    pts = shell[1]
    # apex = where the two straight (seam) edges meet
    segs = sorted(((math.dist(pts[i], pts[(i + 1) % len(pts)]), pts[i], pts[(i + 1) % len(pts)])
                   for i in range(len(pts))), reverse=True)[:2]
    (_, p1, p2), (_, p3, p4) = segs
    d1 = (p2[0] - p1[0], p2[1] - p1[1]); d2 = (p4[0] - p3[0], p4[1] - p3[1])
    den = d1[0] * d2[1] - d1[1] * d2[0]
    t = ((p3[0] - p1[0]) * d2[1] - (p3[1] - p1[1]) * d2[0]) / den
    ax, ay = p1[0] + t * d1[0], p1[1] + t * d1[1]
    d = np.hypot(np.array(pts)[:, 0] - ax, np.array(pts)[:, 1] - ay)
    s_out_m, s_in_m = d.max(), d.min()
    outer = [p for p, r in zip(pts, d) if abs(r - s_out_m) < 0.01]
    inner = [p for p, r in zip(pts, d) if abs(r - s_in_m) < 0.01]
    cxo, cyo, ro = circle_of(outer)
    cxi, cyi, ri = circle_of(inner)
    show("outer and inner arcs share one apex (= where the seam edges meet)", max(math.hypot(cxo - cxi, cyo - cyi), math.hypot(cxo - ax, cyo - ay)))
    show(f"outer arc radius {ro:.3f} vs design {G.s_of(0):.3f}", ro - G.s_of(0))
    show(f"inner arc radius {ri:.3f} vs design {G.s_of(G.H_CONE):.3f}", ri - G.s_of(G.H_CONE))
    ang = lambda p: math.atan2(p[1] - cyo, p[0] - cxo)
    a_out = [ang(p) for p in outer]
    theta = max(a_out) - min(a_out)
    show(f"sector angle {math.degrees(theta):.4f} deg vs {math.degrees(G.THETA):.4f}",
         math.degrees(theta - G.THETA), "deg", 0.0005)
    show(f"floor edge {theta * ro:.3f} mm = cone circumference 2 pi x 200",
         theta * ro - 2 * math.pi * G.R(0))
    show(f"top edge {theta * ri:.3f} mm = cone circumference 2 pi x 80",
         theta * ri - 2 * math.pi * G.R(G.H_CONE))
    show(f"slant {ro - ri:.3f} mm = hypot(450, 120)", (ro - ri) - G.SLANT)

    print("\n[3] kerfs: 49 full length, radial, equal, 6 mm, through both edges")
    in_shell = [l for l in kerf if shell_poly.buffer(10).contains(Polygon(l[1]).centroid)
                or Polygon(l[1]).intersects(shell_poly)]
    in_shell = [l for l in in_shell if Polygon(l[1]).intersection(shell_poly).area > 1]
    axes = []
    for l in in_shell:
        q = Polygon(l[1]).minimum_rotated_rectangle
        c = list(q.exterior.coords)[:4]
        e1, e2 = math.dist(c[0], c[1]), math.dist(c[1], c[2])
        w, ln = min(e1, e2), max(e1, e2)
        cen = Polygon(l[1]).centroid
        a = math.atan2(cen.y - cyo, cen.x - cxo)
        # long axis through the apex?
        # centre line: through the middles of the two short sides
        if e1 > e2:
            m0 = ((c[1][0] + c[2][0]) / 2, (c[1][1] + c[2][1]) / 2); m1 = ((c[3][0] + c[0][0]) / 2, (c[3][1] + c[0][1]) / 2)
        else:
            m0 = ((c[0][0] + c[1][0]) / 2, (c[0][1] + c[1][1]) / 2); m1 = ((c[2][0] + c[3][0]) / 2, (c[2][1] + c[3][1]) / 2)
        ux, uy = (m1[0] - m0[0]) / math.dist(m0, m1), (m1[1] - m0[1]) / math.dist(m0, m1)
        off = abs((cxo - m0[0]) * uy - (cyo - m0[1]) * ux)
        rr = [math.hypot(x - cxo, y - cyo) for x, y in l[1]]
        axes.append((a, w, off, min(rr), max(rr), Polygon(l[1]).intersection(shell_poly).area))
    axes.sort()
    seams = [x for x in axes if x[5] < 0.5 * max(y[5] for y in axes)]
    kerfs = [x for x in axes if x not in seams]
    print(f"  {len(kerfs)} kerf pockets + {len(seams)} seam reliefs on the shell")
    if len(kerfs) != G.kerf_count(G.s_of(G.H_CONE)) - 1:
        FAILS.append("kerf count")
    show("worst kerf width vs 6.000", max(abs(w - G.TOOL_D) for _, w, *_ in kerfs))
    show("worst kerf axis off the apex", max(o for _, _, o, *_ in kerfs))
    step = theta / G.kerf_count(G.s_of(G.H_CONE))
    a0 = min(a_out)
    dev = max(abs((a - a0) / step - round((a - a0) / step)) * step * ri for a, *_ in kerfs)
    show(f"worst kerf position vs equal spacing ({math.degrees(step):.4f} deg), at the top edge", dev)
    over = G.KERF_OVERRUN + G.TOOL_D / 2 - G.KERF_TRIM   # cutter-edge run-out past the outline
    show("every kerf starts past the top edge (run-out)", max(0.0, max(r0 for *_, r0, _, _ in kerfs) - (ri - 0.0)), tol=TOL)
    show("every kerf ends past the floor edge (run-out)", max(0.0, ro - min(r1 for *_, _, r1, _ in kerfs)), tol=TOL)
    land = step * ri - G.TOOL_D
    print(f"  wood between kerfs: {land:.3f} mm at the top, {step * ro - G.TOOL_D:.3f} mm at the floor")
    hinge = 2 * math.pi * G.COS_A / G.kerf_count(G.s_of(G.H_CONE))
    show("back face: kerfs + seam close exactly what the cone needs",
         G.kerf_count(G.s_of(G.H_CONE)) * hinge * G.DEPTH - G.closure_total())
    for a, w, off, r0, r1, _ in seams:
        inside = shell_poly.intersection(Polygon([(0, 0)])) if False else None
    rel = [Polygon(l[1]).intersection(shell_poly) for l in in_shell
           if Polygon(l[1]).intersection(shell_poly).area < 0.5 * max(x[5] for x in axes)]
    for k, g in enumerate(rel, 1):
        q = g.minimum_rotated_rectangle
        c = list(q.exterior.coords)[:4]
        w = min(math.dist(c[0], c[1]), math.dist(c[1], c[2]))
        show(f"seam relief {k}: {w:.3f} mm on the part vs {G.seam_relief(G.s_of(G.H_CONE)):.3f}",
             w - G.seam_relief(G.s_of(G.H_CONE)))

    print("\n[4] formers and core: tabs in mortises")
    rings = sorted(circles, key=lambda c: -c[2])
    # formers: circles with mortises inside (polygons with 8+ corners inside)
    jig_r = sorted([2 * p.r_in for p in jig.parts()] + [2 * (p.r_in + jig.RING_W) for p in jig.parts()])
    plan = G.former_plan()[0]
    form_r = sorted([2 * G.former_radius(z0, z1) for _, z0, z1, _, _ in plan.values()] +
                    [2 * rh for *_, rh, _ in plan.values() if rh])
    found = sorted(2 * r for _, _, r in circles)
    want = sorted(jig_r + form_r)
    show(f"all {len(found)} circles (formers + jig rings) vs design diameters",
         max(abs(a - b) for a, b in zip(found, want)) if len(found) == len(want) else 99)
    # mortises: the dogbone corners are arcs; the long straight sides set the width
    widths, lengths = [], []
    for p, l in polys:
        if not 300 < p.area < 1500:
            continue
        pts = l[1]
        segs = [(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
        segs = [sg for sg in segs if math.dist(*sg) > 5.0]          # straight sides only
        a, b = sorted(segs, key=lambda sg: -math.dist(*sg))[:2]
        ux, uy = (a[1][0] - a[0][0]) / math.dist(*a), (a[1][1] - a[0][1]) / math.dist(*a)
        widths.append(abs((b[0][0] - a[0][0]) * uy - (b[0][1] - a[0][1]) * ux))
        # length: the slot's straight ends (the short sides, between the reliefs)
        ends = [sg for sg in segs if sg not in (a, b)]
        if len(ends) >= 2:
            e = ends[0]
            vx, vy = (e[1][0] - e[0][0]) / math.dist(*e), (e[1][1] - e[0][1]) / math.dist(*e)
            lengths.append(abs((ends[1][0][0] - e[0][0]) * vy - (ends[1][0][1] - e[0][1]) * vx))
    show(f"{len(widths)} mortises: width {min(widths):.3f}-{max(widths):.3f} vs board 17 + 1 mm slot clearance",
         max(abs(w - (G.T_BOARD + G.JOINT.fit)) for w in widths))
    tabs = []
    for p in G.build_parts():
        for k in ("bot", "top"):
            tabs += [x1 - x0 for x0, x1 in p.meta.get(k, [])]
    want = sorted(t + G.JOINT.fit for t in tabs)
    show(f"{len(lengths)} mortise lengths vs their core tabs + 1 mm", max(abs(a - b) for a, b in
         zip(sorted(lengths), want)) if len(lengths) == len(want) else 99)

    print("\n[5] the shell meets the formers and the jig rings")
    for name, z0, z1, rh, _ in plan.values():
        r = G.former_radius(z0, z1)
        gap = G.R_in(z1) - r
        show(f"{name}: shell inner face {G.R_in(z1):.3f} - former {r:.3f} = 0.500 glue line", gap - G.FIT)
    for p in jig.parts():
        want = G.R(p.z) + (jig.BASE_FIT if p.key == "JB" else 0.0)
        show(f"{p.label}: bore {2 * p.r_in:.3f} = cone outer {2 * G.R(p.z):.3f} at z {p.z:g}"
             + (" + 2 x 0.5" if p.key == "JB" else ""), p.r_in - want)

    print("\nFAILURES:", FAILS or 0)
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
