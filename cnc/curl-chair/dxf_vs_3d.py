"""The cut file is the verified 3D: every part found in out/curl-chair.dxf is laid
back onto the profile verify_3d.py assembles (best rigid move, mirror allowed)
and the differing area is measured. Parts nested inside another part's opening
are found by even-odd depth, so small ribs inside a ring count as parts.

    python3 dxf_vs_3d.py
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import ezdxf
from shapely.geometry import Polygon
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))
sys.path.append(str(HERE.parents[0] / "cone-table"))
import importlib.util  # noqa: E402

import chair_geometry as C  # noqa: E402

# the cone's checker holds the shared poly()/align(); same file name, so load it by path
_spec = importlib.util.spec_from_file_location("cone_dxf_vs_3d", HERE.parents[0] / "cone-table" / "dxf_vs_3d.py")
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

TOL = 0.5   # mm2, arc sampling noise


def design():
    out = {}
    for p in C.build_parts():
        body = V.poly(p.loops[0])
        holes = [V.poly(l) for l in p.loops[1:]]
        out[p.label] = (body.difference(unary_union(holes)) if holes else body, p.qty)
    return out


def dxf_parts(path):
    polys = [V.poly(list(e.get_points("xyb"))) for e in ezdxf.readfile(path).modelspace()
             if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "CUT"]
    depth = [sum(q is not p and q.area > p.area and q.contains(p.representative_point()) for q in polys)
             for p in polys]
    parts = []
    for i, p in enumerate(polys):
        if depth[i] % 2:
            continue
        holes = [q for j, q in enumerate(polys) if depth[j] == depth[i] + 1
                 and p.contains(q.representative_point())]
        parts.append(p.difference(unary_union(holes)) if holes else p)
    return parts


def main(name="curl-chair.dxf", sets=1):
    print(f"== out/{name}")
    ref = {k: (b, q * sets) for k, (b, q) in design().items()}
    got = dxf_parts(HERE / "out" / name)
    used, fails = set(), []
    for label, (body, qty) in ref.items():
        found = 0
        for _ in range(qty):
            cands = [(i, g) for i, g in enumerate(got) if i not in used and abs(g.area - body.area) < 50]
            scored = sorted(((V.align(g, body)[0], i) for i, g in cands), key=lambda t: t[0])
            if scored and scored[0][0] < TOL:
                used.add(scored[0][1])
                found += 1
        worst = min((V.align(g, body)[0] for i, g in enumerate(got) if i in used
                     and abs(g.area - body.area) < 50), default=float("nan"))
        ok = found == qty
        print(("  ok   " if ok else "  FAIL ") + f"{label}: {found}/{qty} copies match the 3D profile"
              f" (best {worst:.3f} mm2 of {body.area / 100:.0f} cm2)")
        if not ok:
            fails.append(label)
    extra = len(got) - len(used)
    print(f"  {len(used)} parts matched, {extra} unexpected" + ("  <- FAIL" if extra else ""))
    print("RESULT:", "OK, the DXF is the verified 3D" if not fails and not extra else "FAIL")
    return not fails and not extra


if __name__ == "__main__":
    ok = main()
    if (HERE / "out" / "curl-chair_x2.dxf").exists():
        ok = main("curl-chair_x2.dxf", 2) and ok
    sys.exit(0 if ok else 1)
