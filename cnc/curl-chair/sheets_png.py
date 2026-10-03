"""Draw the nested sheets of out/curl-chair.dxf to out/curl-chair-sheets.png."""

from pathlib import Path

import ezdxf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
doc = ezdxf.readfile(HERE / "out" / "curl-chair.dxf")
msp = doc.modelspace()
boards = sorted((e for e in msp if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "REFERENCE-SHEET"),
                key=lambda e: -max(p[1] for p in e.get_points("xy")))
fig, axes = plt.subplots(len(boards), 1, figsize=(8, 4.3 * len(boards)))
for k, (ax, b) in enumerate(zip(axes, boards)):
    ys = [p[1] for p in b.get_points("xy")]
    y0, y1 = min(ys), max(ys)
    for e in msp:
        if e.dxftype() != "LWPOLYLINE" or e.dxf.layer not in ("CUT", "REFERENCE-SHEET"):
            continue
        pts = [(x, y) for x, y, *_ in e.flattening(0.5)] if hasattr(e, "flattening") else list(e.get_points("xy"))
        if not pts or not (y0 - 1 <= pts[0][1] <= y1 + 1):
            continue
        xs, yy = zip(*(pts + [pts[0]]))
        ax.plot(xs, yy, lw=0.6 if e.dxf.layer == "CUT" else 1.0, color="black")
    for t in msp.query('TEXT[layer=="ENGRAVE-LABEL"]'):
        if y0 <= t.dxf.insert[1] <= y1:
            ax.text(t.dxf.insert[0], t.dxf.insert[1], t.dxf.text, fontsize=3.5, ha="center", va="center",
                    rotation=t.dxf.rotation)
    ax.set_title(f"SHEET {k + 1}/{len(boards)}  -  2440 x 1220 x 18 mm MDF", loc="left", fontsize=9)
    ax.set_aspect("equal"); ax.axis("off")
fig.tight_layout()
fig.savefig(HERE / "out" / "curl-chair-sheets.png", dpi=200)
print("wrote out/curl-chair-sheets.png")
