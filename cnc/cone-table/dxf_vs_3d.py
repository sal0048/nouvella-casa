"""Close the loop between the files we ship and the 3D that was verified.

    python3 dxf_vs_3d.py

verify_3d.py builds the assembly from table_geometry's part profiles. This
script reads the DXF files themselves (per-part files, CUT x1, CUT x2), finds
every part in them, lays it back onto the profile the 3D was built from
(best rigid move, mirror allowed) and measures the area that differs, for the
outline+holes and for the kerf pockets. Zero difference means the 3D built
from the DXF is the 3D that passed verify_3d.py (no clash, every part bears).
"""

from __future__ import annotations

import glob
import math
import sys
from collections import Counter
from pathlib import Path

import ezdxf
from scipy.optimize import minimize_scalar
from shapely import affinity
from shapely.geometry import Polygon
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))
import audit_dxf as A  # noqa: E402
import build as B  # noqa: E402
import table_geometry as T  # noqa: E402

SEG = 0.3            # mm arc sampling, same for both sides
TOL = 0.5            # mm2 of differing area allowed (arc sampling noise)
fails = []


def poly(loop):
    class L:  # audit_dxf.loop_points wants an entity with get_points
        def get_points(self, fmt):
            return loop
    return Polygon(A.loop_points(L(), seg=SEG)).buffer(0)


def design():
    out = {}
    for p in T.build_parts():
        holes = [poly(l) for l in p.loops[1:1 + p.n_holes]]
        body = poly(p.loops[0]).difference(unary_union(holes)) if holes else poly(p.loops[0])
        # the DXF runs the pockets out through the edges (build.kerf_polys); inside the
        # part that is all that matters, so both sides are compared clipped to the part
        pockets = (unary_union([Polygon(q).buffer(0) for q in B.kerf_polys(p.loops[1 + p.n_holes:])])
                   .intersection(body) if p.kerfs else None)
        out[p.label] = (body, pockets, p.qty)
    return out


def dxf_parts(path):
    """Group a DXF into parts: each outer CUT loop with the loops inside it."""
    doc = ezdxf.readfile(path)
    cut, pockets = [], []
    for e in doc.modelspace():
        if e.dxftype() != "LWPOLYLINE":
            continue
        pts = list(e.get_points("xyb"))
        if e.dxf.layer == "CUT":
            cut.append(poly(pts))
        elif e.dxf.layer.startswith("POCKET"):
            pockets.append(poly(pts))
    cut.sort(key=lambda g: -g.area)
    outers = []
    for g in cut:
        host = next((o for o in outers if o[0].contains(g.representative_point())), None)
        if host is None:
            outers.append([g, []])
        else:
            host[1].append(g)
    # a pocket belongs to the part it overlaps most (seam pockets lie mostly outside it)
    owner = [max(range(len(outers)), key=lambda i: q.intersection(outers[i][0]).area) for q in pockets]
    parts = []
    for i, (o, holes) in enumerate(outers):
        body = o.difference(unary_union(holes)) if holes else o
        pk = [q for q, k in zip(pockets, owner) if k == i]
        parts.append((body, unary_union(pk) if pk else None))
    return parts


def align(src, ref):
    """Best rigid move (+ optional mirror) of src onto ref; returns (diff area, transform)."""
    best = (float("inf"), None)
    for mirror in (False, True):
        s = affinity.scale(src, -1, 1, origin=src.centroid) if mirror else src
        s = affinity.translate(s, ref.centroid.x - s.centroid.x, ref.centroid.y - s.centroid.y)

        def cost(a):
            return affinity.rotate(s, a, origin=ref.centroid).symmetric_difference(ref).area
        a0 = min(range(0, 360, 2), key=cost)
        r = minimize_scalar(cost, bounds=(a0 - 2, a0 + 2), method="bounded",
                            options={"xatol": 1e-7})
        if r.fun < best[0]:
            best = (r.fun, (mirror, s.centroid, r.x, src.centroid))
    return best


def apply(g, tf, ref, src):
    mirror, _, ang, c0 = tf
    if mirror:
        g = affinity.scale(g, -1, 1, origin=c0)
        c = affinity.scale(src, -1, 1, origin=c0).centroid
    else:
        c = src.centroid
    g = affinity.translate(g, ref.centroid.x - c.x, ref.centroid.y - c.y)
    return affinity.rotate(g, ang, origin=ref.centroid)


def compare(path, want, ref):
    print(f"\n== {Path(path).relative_to(HERE)}")
    got = dxf_parts(path)
    used, found = set(), Counter()
    for label, (body, pk, _) in ref.items():
        need = want.get(label, 0)
        cands = [i for i, (b, _) in enumerate(got) if i not in used and abs(b.area - body.area) < 50]
        for _ in range(need):
            scored = []
            for i in cands:
                if i in used:
                    continue
                d, tf = align(got[i][0], body)
                scored.append((d, i, tf))
            if not scored:
                break
            d, i, tf = min(scored)
            used.add(i)
            dp = 0.0
            if pk is not None:
                gp = got[i][1]
                dp = pk.area if gp is None else (apply(gp, tf, body, got[i][0]).intersection(body)
                                                 .symmetric_difference(pk).area)
            ok = d < TOL and dp < TOL
            found[label] += ok
            tag = "ok  " if ok else "FAIL"
            extra = f", kerf pockets differ {dp:.3f} mm2" if pk is not None else ""
            print(f"  {tag} {label}: outline+holes differ {d:.3f} mm2 of {body.area / 100:.0f} cm2{extra}"
                  + (" (mirrored in file)" if tf[0] else ""))
            if not ok:
                fails.append(f"{path}: {label}")
    extra = len(got) - len(used)
    for label, n in want.items():
        if found[label] != n:
            fails.append(f"{path}: {label} found {found[label]}/{n}")
            print(f"  FAIL {label}: {found[label]}/{n} copies match")
    print(f"  {len(used)} parts matched, {extra} unexpected loops" + ("" if not extra else "  <- FAIL"))
    if extra:
        fails.append(f"{path}: {extra} unexpected parts")


def main():
    ref = design()
    for f in sorted(glob.glob(str(HERE / "out" / "parts" / "P*_x1.dxf"))):
        label = Path(f).stem.split("_")[1]
        if label in ref:
            compare(f, {label: 1}, ref)
    compare(HERE / "out" / f"CONE_{T.T_SHELL:g}MM_CUT.dxf", {k: v[2] for k, v in ref.items()}, ref)
    compare(HERE / "out" / f"CONE_{T.T_SHELL:g}MM_CUT_x2.dxf", {k: 2 * v[2] for k, v in ref.items()}, ref)
    print(f"\nRESULT: {'OK, the DXF is the verified 3D' if not fails else f'{len(fails)} problem(s)'}")
    for x in fails:
        print("  FAIL", x)
    return not fails


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
