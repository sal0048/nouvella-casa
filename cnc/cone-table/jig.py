"""Bending jig (gabarit) for the kerfed cone shell, as in the workshop video.

    python3 jig.py            # out/jig/CONE_JIG.dxf + ArtCAM R12 copies + preview

The shell is wrapped round the formers, then flat MDF rings slide down over
the cone from the top. Each ring's bore equals the cone's outer diameter at
one height, so it stops there and squeezes the shell round while the glue
sets. A base ring holds the bottom edge at exactly 400 mm.

  JIG-BASE   bore = cone at the floor + 0.5 mm, lies on the bench
  JIG-1..3   bores = cone at 1/4, 1/2, 3/4 height; push them down in that
             order (biggest first: a smaller ring above would block it)

A flat 18 mm ring on a 14.9 deg cone touches with its lower edge only; the
gap at its top edge is 18 x tan(alpha) = 4.8 mm per side, which is fine for
a clamp. Rings are 45 mm wide, so JIG-2 cuts inside the base ring's bore and
JIG-3 inside JIG-1's: the whole set takes about half a 1220 x 1220 piece.
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))

import ezdxf
from ezdxf.enums import TextEntityAlignment

import sofa_layout as L
import table_geometry as G

RING_W = 45.0                     # radial width; 45 lets each ring nest in the next bore
BASE_FIT = 0.5                    # bore clearance at the floor ring
HEIGHTS = [G.H_CONE * k / 4 for k in (1, 2, 3)]   # 112.5, 225, 337.5
OUT = HERE / "out" / "jig"
GAP, MARGIN = 10.0, 10.0


class Part:
    def __init__(self, key, label, r_in, z, note):
        self.key, self.label, self.qty = key, label, 1
        self.r_in, self.z, self.note = r_in, z, note
        self.loops = G.ring(r_in + RING_W, r_in)


def parts():
    out = [Part("JB", "JIG-BASE", G.R(0) + BASE_FIT, 0.0, "on the bench, holds the floor edge")]
    for k, z in enumerate(HEIGHTS, 1):
        out.append(Part(f"J{k}", f"JIG-{k}", G.R(z), z, f"stops at z = {z:g} mm"))
    return out


def tag(p):
    return f"{p.label}  bore {2 * p.r_in:.1f}  z{p.z:g}"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ps = parts()
    # concentric pairs: JIG-2 inside the base ring's bore, JIG-3 inside JIG-1's
    by = {p.key: p for p in ps}
    centres, x = {}, MARGIN
    for outer, inner in ((by["JB"], by["J2"]), (by["J1"], by["J3"])):
        R_o = outer.r_in + RING_W
        centres[outer.key] = centres[inner.key] = (x + R_o, MARGIN + R_o)
        x += 2 * R_o + GAP
    placed = [(p, [[(u + centres[p.key][0], v + centres[p.key][1], b) for u, v, b in l]
                   for l in p.loops]) for p in ps]
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.layers.add("CUT", color=1)
    doc.layers.add("ENGRAVE-LABEL", color=3)
    doc.layers.add("REFERENCE-SHEET", color=8)
    msp = doc.modelspace()
    fails = []
    from shapely.geometry import Polygon
    solids = [Polygon(L.flatten_loop(lp[0])).difference(Polygon(L.flatten_loop(lp[1])))
              for _, lp in placed]
    gaps = [solids[i].distance(solids[j]) for i in range(4) for j in range(i + 1, 4)]
    if min(gaps) < GAP - 0.01:
        fails.append(f"rings only {min(gaps):.1f} mm apart")
    for p, loops in placed:
        for loop in loops:
            msp.add_lwpolyline(loop, format="xyb", close=True, dxfattribs={"layer": "CUT"})
        b = L.loops_bbox(loops)
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        msp.add_text(tag(p), height=12, dxfattribs={"layer": "ENGRAVE-LABEL"}).set_placement(
            (cx, cy - p.r_in - RING_W / 2), align=TextEntityAlignment.MIDDLE_CENTER)
        # checks: the ring stops where the cone is as wide as its bore
        z_stop = (G.R_BOT - p.r_in) * G.H_CONE / (G.R_BOT - G.R_TOP) if p.z else 0.0
        if p.z and abs(z_stop - p.z) > 1e-6:
            fails.append(f"{p.label} stops at {z_stop:.2f}, wanted {p.z}")
        if abs((b[2] - b[0]) - 2 * (p.r_in + RING_W)) > 1e-6:
            fails.append(f"{p.label} scale")
    # order: a ring already in place blocks any bigger one coming down after it
    rs = sorted(ps[1:], key=lambda p: p.z)
    for lo, hi in zip(rs, rs[1:]):
        if hi.r_in + RING_W <= lo.r_in:
            fails.append(f"{hi.label} lets {lo.label} pass: order note is wrong")
    xs = [L.loops_bbox(loops) for _, loops in placed]
    used = (max(b[2] for b in xs) + MARGIN, max(b[3] for b in xs) + MARGIN)
    msp.add_lwpolyline([(0, 0), (used[0], 0), used, (0, used[1])], close=True,
                       dxfattribs={"layer": "REFERENCE-SHEET"})       # offcut size, not cut
    path = OUT / "CONE_JIG.dxf"
    doc.saveas(path)
    for p in ps:
        print(f"  {tag(p):38s} outer {2 * (p.r_in + RING_W):.1f}  {p.note}")
    print(f"wrote {path}: {len(ps)} rings on {used[0]:.0f} x {used[1]:.0f} mm of MDF 18, "
          f"closest {min(gaps):.1f} mm apart")
    preview(ps, OUT / "cone_jig_preview.png")
    r = subprocess.run([sys.executable, str(HERE.parents[0] / "tools" / "artcam_dxf.py"), str(path)],
                       capture_output=True, text=True)
    print(r.stdout.strip())
    fails += [] if r.returncode == 0 else ["ArtCAM export check failed"]
    print("FAILURES:", fails or 0)
    return 1 if fails or r.returncode else 0


def preview(ps, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 6))
    Rb, Rt, H = G.R_BOT, G.R_TOP, G.H_CONE
    ax.fill([-Rb, Rb, Rt, -Rt], [0, 0, H, H], color="#d8b98f", ec="#6b4f2a", lw=1.2)
    for z in (0.0, G.Z_SPLIT, H):
        ax.plot([-G.R(z) + 18, G.R(z) - 18], [z, z], color="#8a6a3f", lw=1, ls="--")
    for p in ps:
        z = p.z
        for s in (-1, 1):
            ax.add_patch(plt.Rectangle((s * p.r_in if s > 0 else -p.r_in - RING_W, z),
                                       RING_W, 18, color="#c8462a"))
        ax.text(p.r_in + RING_W + 12, z + 9, f"{p.label}  Ø{2 * p.r_in:.0f}  z{z:g}",
                va="center", fontsize=9)
    ax.set_aspect("equal")
    ax.set_xlim(-Rb - 80, Rb + 260)
    ax.set_ylim(-30, H + 40)
    ax.axis("off")
    ax.set_title("Cone bending jig: rings slide down from the top, biggest first", fontsize=10, loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    print(f"wrote {path}")


if __name__ == "__main__":
    raise SystemExit(main())
