"""Geometry for the interactive web viewer (web/pebble-xray.html).

    python3 export_web.py            -> out/web/pebble.json + web/pebble-xray.html

pieces: every cut piece as its flat loops (mm, outer first, holes after) plus
the 4x4 placement matrix, so the browser extrudes exactly what the CNC cuts.
The matrix maps (u, v, w) with w in [-T/2, T/2] to the world, the same frame
render_blender.plate() uses. upholstery: the approximate foam shells of
render_blender.build_upholstery() as row grids (sales visual, not a pattern).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))

import pebble_geometry as G
import sofa_layout as L

CX, CY = 1550.0, 560.0           # same world centring as the renders


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def pieces():
    out = []
    for p, k, o, u, v, c in G.instances():
        n = cross(u, v)
        lift = 0.0 if c else G.T / 2
        O = [o[i] + n[i] * lift for i in range(3)]
        O = [O[0] - CX, O[1] - CY, O[2]]
        # column-major 4x4 for THREE.Matrix4.fromArray
        m = [*u, 0, *v, 0, *n, 0, *O, 1]
        loops = [[round(c_, 1) for xy in L.flatten_loop(lp, 10) for c_ in xy] for lp in p.loops]
        out.append({"n": p.num, "k": k, "of": len(p.place), "label": p.label, "group": p.group,
                    "note": p.note, "m": [round(x, 4) for x in m], "loops": loops})
    return out


def upholstery():
    foam = 40.0
    shells = []
    w = lambda x, y, z: [round(x - CX, 1), round(y - CY, 1), round(z, 1)]
    for m in G.MODULES:
        angs = [i * 3.0 for i in range(120)]
        rows = []
        for k in range(12):
            z = 25.0 + (G.SEAT_TOP + 40.0 - 25.0) * k / 11
            f = G.belly(min(z, G.SEAT_Z)) if z <= G.SEAT_Z else G.S_SEAT + 0.02
            rows.append([w(m.cx + (f * m.R(a) + foam) * math.cos(math.radians(a)),
                           m.cy + (f * m.R(a) + foam) * math.sin(math.radians(a)), z) for a in angs])
        for shrink, dz in ((0.96, 110.0), (0.85, 128.0), (0.55, 136.0), (0.0, 138.0)):
            rows.append([w(m.cx + shrink * (G.S_SEAT * m.R(a) + 20) * math.cos(math.radians(a)),
                           m.cy + shrink * (G.S_SEAT * m.R(a) + 20) * math.sin(math.radians(a)),
                           G.SEAT_TOP + dz) for a in angs])
        shells.append({"key": m.key, "tone": "beige", "rows": rows})
    for p in G.PEBBLES:
        z0 = G.SEAT_TOP + 20.0
        ring = []
        for i in range(72):
            a = 2 * math.pi * i / 72
            c, s = math.cos(a), math.sin(a)
            ring.append((math.copysign(abs(c) ** (2 / p.N), c), math.copysign(abs(s) ** (2 / p.N), s)))
        rows = [[w(p.px, p.py, z0)] * len(ring),
                [w(*G.to_world(p, (p.a + foam) * 1.05 * u, (p.b + foam) * 1.05 * t), z0) for u, t in ring]]
        for f in (0.0, 0.2, 0.4, 0.55, 0.7, 0.82, 0.91, 0.97, 1.0):
            sc = max(0.0, 1 - f ** G.PEB_E) ** (1 / G.PEB_E) if f < 1 else 0.0
            grow = 1.0 + 0.12 * (1 - f)
            rows.append([w(*G.to_world(p, (p.a + foam) * grow * sc * u, (p.b + foam) * grow * sc * t),
                           z0 + (p.H + foam) * f) for u, t in ring])
        shells.append({"key": p.key, "tone": "grey" if p.key in ("BL", "AR") else "beige", "rows": rows})
    return shells


def main():
    data = {"T": G.T, "groups": G.GROUP_ORDER, "pieces": pieces(), "upholstery": upholstery(),
            "modules": [{"key": m.key, "cx": m.cx - CX, "cy": m.cy - CY} for m in G.MODULES],
            "seat_top": G.SEAT_TOP}
    out = HERE / "out" / "web" / "pebble.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, separators=(",", ":")))
    print(f"wrote {out}: {len(data['pieces'])} pieces, {out.stat().st_size / 1024:.0f} KB")
    page = (HERE / "web" / "pebble-xray.template.html").read_text()
    html = HERE / "web" / "pebble-xray.html"
    html.write_text(page.replace("/*DATA*/", out.read_text().replace("</", "<\\/")))
    print(f"wrote {html}: {html.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
