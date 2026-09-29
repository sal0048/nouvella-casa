"""Audit a cut file on its own: read only the DXF, rebuild the cone from it.

    python3 audit_dxf.py FILE.dxf [FILE2.dxf ...]

Nothing comes from table_geometry: the cone (base, top, height), the shell
thickness implied by the pocket layer, the kerf closure and the former
diameters are all measured from the file. So a stale or mixed-up file shows
up here even if the design code is right.
"""

from __future__ import annotations

import math
import re
import sys
from collections import defaultdict

import ezdxf
from shapely.geometry import LineString, Polygon

BOARD = 18.0


def loop_points(e, seg=0.5):
    """Polyline with bulges -> dense point list (arcs split every ~0.5 mm)."""
    pts = list(e.get_points("xyb"))
    out = []
    for i, (x0, y0, b) in enumerate(pts):
        x1, y1, _ = pts[(i + 1) % len(pts)]
        out.append((x0, y0))
        if abs(b) > 1e-12:
            c, r, a0, a1 = arc_of(x0, y0, x1, y1, b)
            n = max(2, int(abs(a1 - a0) * r / seg))
            for k in range(1, n):
                a = a0 + (a1 - a0) * k / n
                out.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
    return out


def arc_of(x0, y0, x1, y1, b):
    """Centre, radius and start/end angle of a bulge segment."""
    th = 4 * math.atan(b)
    ch = math.hypot(x1 - x0, y1 - y0)
    r = ch / (2 * math.sin(abs(th) / 2))
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    d = math.sqrt(max(r * r - (ch / 2) ** 2, 0))
    ux, uy = -(y1 - y0) / ch, (x1 - x0) / ch
    s = 1 if (b > 0) == (abs(th) < math.pi) else -1
    cx, cy = mx + s * d * ux, my + s * d * uy
    a0 = math.atan2(y0 - cy, x0 - cx)
    a1 = a0 + th
    return (cx, cy), r, a0, a1


def tool_lip_strip(cuts, pockets):
    """Flat bend-test strip (a rectangle with pockets across it): worst full-thickness
    lip left at a kerf end by the round end of the slot, or None if no strip."""
    worst = None
    for e, p in cuts:
        pts = list(e.get_points("xyb"))
        if len(pts) != 4 or any(abs(b) > 1e-12 for _, _, b in pts):   # straight rectangle only
            continue
        own = [q for q in pockets if p.contains(q.representative_point())]
        if not own:
            continue
        y0, y1 = p.bounds[1], p.bounds[3]
        for q in own:
            qx0, qy0, qx1, qy1 = q.bounds
            hw = (qx1 - qx0) / 2
            lip = max((qy0 + hw) - y0, y1 - (qy1 - hw))
            worst = lip if worst is None else max(worst, lip)
    return worst


def audit(path):
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    print(f"\n== {path}")
    layers = defaultdict(list)
    for e in msp:
        if e.dxftype() == "LWPOLYLINE":
            layers[e.dxf.layer].append(e)
    pocket_layers = [l for l in layers if l.startswith("POCKET")]
    texts = sum(1 for e in msp if e.dxftype() in ("TEXT", "MTEXT"))
    print(f"   layers: {', '.join(f'{k} {len(v)}' for k, v in layers.items())}; text entities {texts}")
    fails = []
    if texts:
        fails.append("file contains text (not a clean cut file)")
    depth = None
    for l in pocket_layers:
        m = re.search(r"([\d.]+)$", l)
        depth = float(m.group(1)) if m else None
    if depth is not None:
        skin = BOARD - depth
        print(f"   pocket depth {depth} mm -> skin {skin:g} mm on {BOARD:g} mm board")
        if abs(skin - 2.5) > 1e-6:
            fails.append(f"pocket depth {depth} mm is for another board: on 18 mm it leaves {skin:g} mm")

    cuts = [(e, Polygon(loop_points(e))) for e in layers.get("CUT", [])]
    pockets = [Polygon(loop_points(e)) for e in layers.get(pocket_layers[0], [])] if pocket_layers else []
    shells = [(e, p) for e, p in cuts if sum(p.contains(q.centroid) for q in pockets) > 10]
    print(f"   {len(cuts)} cut loops, {len(pockets)} pockets, {len(shells)} kerfed shell(s)")
    # pockets run out through the part edges: they must stay on the board and clear every other part
    boards = [Polygon(loop_points(e)) for l, v in layers.items() if l.startswith("BOARD") for e in v]
    outers = [p for _, p in cuts if not any(q.contains(p.representative_point()) and q.area > p.area
                                             for _, q in cuts)]
    hits = 0
    for q in pockets:
        own = next((p for p in outers if p.contains(q.representative_point())), None)
        others = [p for p in outers if p is not own]
        if any(q.intersects(p) for p in others) or (boards and not boards[0].buffer(1e-6).contains(q)):
            hits += 1
    if pockets:
        near = min((q.distance(p) for q in pockets for p in outers
                    if not p.contains(q.representative_point())), default=float("inf"))
        print(f"   pockets vs other parts / board: {hits} touch; closest other part {near:.1f} mm")
        if hits:
            fails.append(f"{hits} kerf pockets cut into another part or off the board")
    lip_strip = tool_lip_strip(cuts, pockets)
    if lip_strip is not None:
        print(f"   test strip: worst full-thickness lip at a kerf end {max(lip_strip, 0):.2f} mm")
        if lip_strip > 1e-6:
            fails.append(f"test strip kerfs leave a {lip_strip:.2f} mm full-thickness lip at the edge")
    cones = []
    for e, shell in shells:
        arcs = []
        pts = list(e.get_points("xyb"))
        for i, (x0, y0, b) in enumerate(pts):
            if abs(b) > 1e-9:
                x1, y1, _ = pts[(i + 1) % len(pts)]
                c, r, a0, a1 = arc_of(x0, y0, x1, y1, b)
                arcs.append((c, r, abs(a1 - a0)))
        big = [a for a in arcs if a[1] > 150]
        if not big:
            print("   flat test strip (no cone arcs): skin check only")
            continue
        c = big[0][0]
        rs = sorted({round(a[1], 3) for a in big})
        r_in, r_out = rs[0], rs[-1]
        theta = sum(a[2] for a in big if abs(a[1] - r_out) < 1e-3)
        L = r_out - r_in
        Rb, Rt = r_out * theta / (2 * math.pi), r_in * theta / (2 * math.pi)
        H = math.sqrt(L * L - (Rb - Rt) ** 2)
        cosa = H / L
        key = (round(r_in), round(r_out))
        if key in {k for k, _ in cones}:
            continue
        print(f"   shell flat: radii {r_in:.1f}/{r_out:.1f} mm, sector {math.degrees(theta):.2f} deg")
        print(f"   -> cone from the file: base D{2 * Rb:.1f}, top D{2 * Rt:.1f}, height {H:.1f} mm")
        # kerf capacity vs need: the back face must lose 2*pi*T*cos(a) of length at every radius
        need = 2 * math.pi * BOARD * cosa
        worst = (1e9, None)
        for k in range(1, 40):
            s = r_in + L * k / 40
            circ = LineString([(c[0] + s * math.cos(a), c[1] + s * math.sin(a))
                               for a in [math.atan2(shell.centroid.y - c[1], shell.centroid.x - c[0])
                                         + (j / 400 - 0.5) * theta * 1.02 for j in range(401)]])
            cap = sum(circ.intersection(q).length for q in pockets if shell.contains(q.centroid))
            n = sum(1 for q in pockets if shell.contains(q.centroid) and circ.intersects(q))
            if cap / need < worst[0]:
                worst = (cap / need, s, n, cap)
        ratio, s, n, cap = worst
        print(f"   kerfs: back face must shorten {need:.1f} mm; tightest radius {s:.0f} mm has "
              f"{n} kerfs = {cap:.1f} mm of gap ({ratio:.1f}x what is needed)")
        if ratio < 1:
            fails.append(f"kerfs cannot close the cone at radius {s:.0f} mm")
        # A 6 mm cutter in a 6 mm slot leaves a round end: wood survives at the slot flanks
        # up to (pocket end - TOOL_D/2). That wood must be past the curved edge, or a
        # full-thickness lip stays at the kerf end and the kerf cannot close there.
        own = [q for q in pockets if shell.contains(q.representative_point())]
        hw = min(min(math.dist(a, b) for a, b in zip(list(q.minimum_rotated_rectangle.exterior.coords),
                                                     list(q.minimum_rotated_rectangle.exterior.coords)[1:]))
                 for q in own) / 2
        lip_out, lip_in, n_full = [], [], 0
        for q in own:
            rr = [math.dist(c, p) for p in q.exterior.coords]
            lip_out.append(r_out - (max(rr) - hw))
            if min(rr) < r_in + L * 0.05:                    # full-length kerf: reaches the narrow edge too
                n_full += 1
                lip_in.append((min(rr) + hw) - r_in)
        wo, wi = max(lip_out), max(lip_in, default=-1)
        print(f"   kerf ends ({len(own)} at the wide edge, {n_full} at the narrow edge): worst "
              f"full-thickness lip {max(wo, 0):.2f} / {max(wi, 0):.2f} mm (cutter Ø{2 * hw:g})")
        if wo > 1e-6 or wi > 1e-6:
            fails.append(f"kerfs stop short of the curved edges: {max(wo, wi):.2f} mm of full "
                         f"{BOARD:g} mm wood stays at the kerf ends, the cone cannot close there")
        cones.append((key, (Rb, Rt, H, cosa)))
    # formers: discs; each must sit inside one of the cones (inner face at its height)
    discs = []
    for e2, p in cuts:
        q = list(p.minimum_rotated_rectangle.exterior.coords)
        a, b = math.dist(q[0], q[1]), math.dist(q[1], q[2])
        if abs(a - b) < 1.0 and a > 60 and p.area > 0.97 * math.pi * (a / 2) ** 2:
            discs.append(round(a / 2, 1))
    for r in sorted(set(discs), reverse=True):
        fits = []
        for _, (Rb, Rt, H, cosa) in cones:
            off = BOARD / cosa                      # horizontal wall thickness
            z = (Rb - off - r - 0.5) * H / (Rb - Rt)
            if -1 <= z <= H + 1:
                fits.append(z)
        where = ", ".join(f"{z:.0f}" for z in fits) if fits else "nowhere"
        print(f"   disc D{2 * r:.1f} (x{discs.count(r)}): 0.5 mm inside the shell at height {where} mm")
        if not fits:
            fails.append(f"disc D{2 * r:.1f} does not fit inside the cone(s) in this file")
    for f in fails:
        print("   FAIL", f)
    print("   RESULT:", "OK" if not fails else f"{len(fails)} problem(s)")
    return not fails


if __name__ == "__main__":
    ok = [audit(p) for p in sys.argv[1:]]
    sys.exit(0 if all(ok) else 1)
