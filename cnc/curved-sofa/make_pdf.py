"""Render the curved-sofa cut file to a printable multi-page PDF.

Page 1  specification + bill of materials + assembly sequence
Page 2  plan view and rib section with the controlling dimensions
Page 3+ one nesting page per 2440 x 1220 sheet, drawn to scale
"""

from __future__ import annotations

import math
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Polygon as MplPolygon

import sofa_geometry as G
import sofa_layout as L

A3 = (16.54, 11.69)          # inches, landscape
INK = "#1b1b1b"
CUT = "#c02525"
FILL = "#f2ede4"
REF = "#9aa0a6"
ACCENT = "#2f5d8c"

TITLE = "CURVED 3-SEAT SOFA  /  CNC FRAME"
SUBTITLE = "slot-and-tab plywood frame, cut layout"


def _page(fig_title: str, sheet_note: str = ""):
    fig = plt.figure(figsize=A3)
    fig.patch.set_facecolor("white")
    fig.text(0.035, 0.955, TITLE, fontsize=15, fontweight="bold", color=INK)
    fig.text(0.035, 0.930, fig_title, fontsize=10.5, color=ACCENT)
    fig.text(0.965, 0.955, f"15 mm PLYWOOD  |  mm  |  1:1 DXF",
             fontsize=9, color=REF, ha="right")
    fig.text(0.965, 0.930, sheet_note, fontsize=9, color=REF, ha="right")
    fig.lines.append(plt.Line2D([0.035, 0.965], [0.915, 0.915],
                                transform=fig.transFigure, color=REF, lw=0.8))
    fig.text(0.035, 0.028, f"generated {date.today().isoformat()}  -  "
                           f"curved-sofa.dxf.py  -  all dimensions in millimetres",
             fontsize=7.5, color=REF)
    return fig


def draw_loops(ax, loops, facecolor=FILL, edgecolor=CUT, lw=0.9, offset=(0.0, 0.0)):
    ox, oy = offset
    outer = [(x + ox, y + oy) for x, y in L.flatten_loop(loops[0])]
    ax.add_patch(MplPolygon(outer, closed=True, facecolor=facecolor,
                            edgecolor=edgecolor, lw=lw, zorder=2))
    for loop in loops[1:]:
        pts = [(x + ox, y + oy) for x, y in L.flatten_loop(loop)]
        ax.add_patch(MplPolygon(pts, closed=True, facecolor="white",
                                edgecolor=edgecolor, lw=lw, zorder=3))


def dim_line(ax, p0, p1, text, off=0.0, color=ACCENT, fs=8):
    (x0, y0), (x1, y1) = p0, p1
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="<->", color=color, lw=0.8))
    ax.text((x0 + x1) / 2, (y0 + y1) / 2 + off, text, color=color, fontsize=fs,
            ha="center", va="bottom", bbox=dict(fc="white", ec="none", pad=0.8))


# --------------------------------------------------------------------------

def page_spec(pdf, parts, sheets):
    fig = _page("1  -  SPECIFICATION AND BILL OF MATERIALS")

    total_area = sum(L.part_area(p.loops) * p.qty for p in parts)
    total_cut = sum(L.cut_length(p.loops) * p.qty for p in parts)
    plan_depth = G.R_OUT - G.R_IN * math.cos(math.radians(G.HALF_SWEEP))
    width = 2 * G.R_OUT * math.sin(math.radians(G.HALF_SWEEP))

    spec = [
        ("Overall width (chord of the back)", f"{width:.0f} mm"),
        ("Overall depth over the crescent", f"{plan_depth:.0f} mm"),
        ("Radial depth of the seating band", f"{G.DEPTH:.0f} mm"),
        ("Plan sweep / back radius", f"{2*G.HALF_SWEEP:.0f} deg  /  R{G.R_OUT:.0f} mm"),
        ("Seat frame height (add cushion)", f"{G.DECK_TOP:.0f} mm"),
        ("Backrest height", f"{G.BACK_TOP:.0f} mm"),
        ("Arm height", f"{G.ARM_TOP:.0f} mm"),
        ("Material", f"{G.T:.0f} mm birch plywood, {G.SHEET_W:.0f} x {G.SHEET_H:.0f} mm"),
        ("Sheets required", f"{len(sheets)}"),
        ("Net part area", f"{total_area/1e6:.2f} m2"),
        ("Total cut path", f"{total_cut/1000:.0f} m"),
        ("Frame mass (600 kg/m3)", f"~{total_area/1e6*G.T/1000*600:.0f} kg"),
        ("Joint clearance", f"slots {G.SLOT_T:.1f} mm for {G.T:.0f} mm plate"),
        ("Corner relief", f"dogbone R{G.DOGBONE_R:.1f} mm (6 mm cutter)"),
    ]

    y = 0.855
    fig.text(0.035, 0.885, "SPECIFICATION", fontsize=10, fontweight="bold", color=INK)
    for k, v in spec:
        fig.text(0.035, y, k, fontsize=8.4, color=INK)
        fig.text(0.290, y, v, fontsize=8.4, color=ACCENT, fontweight="bold")
        y -= 0.0235

    fig.text(0.520, 0.885, "BILL OF MATERIALS", fontsize=10, fontweight="bold", color=INK)
    fig.text(0.520, 0.860, "PART", fontsize=7.6, color=REF, fontweight="bold")
    fig.text(0.652, 0.860, "QTY", fontsize=7.6, color=REF, fontweight="bold")
    fig.text(0.692, 0.860, "SIZE (mm)", fontsize=7.6, color=REF, fontweight="bold")
    fig.text(0.790, 0.860, "FUNCTION", fontsize=7.6, color=REF, fontweight="bold")
    y = 0.836
    for part in parts:
        b = L.loops_bbox(part.loops)
        fig.text(0.520, y, part.label, fontsize=8.2, color=INK)
        fig.text(0.656, y, str(part.qty), fontsize=8.2, color=INK)
        fig.text(0.692, y, f"{b[2]-b[0]:.0f} x {b[3]-b[1]:.0f}", fontsize=8.2, color=INK)
        fig.text(0.790, y, part.note, fontsize=7.2, color=REF)
        y -= 0.0235
    fig.text(0.520, y - 0.004, f"TOTAL  {sum(p.qty for p in parts)} parts",
             fontsize=8.6, fontweight="bold", color=ACCENT)

    assembly = [
        "1.  Lay RAIL-BASE-IN and RAIL-BASE-OUT flat on the floor, concentric.",
        "2.  Drop the 7 RIBs onto them; the notches in the rib feet fix every rib angle.",
        "3.  Drop RAIL-SEAT-IN and RAIL-SEAT-OUT into the open notches in the rib tops.",
        "4.  Drop RAIL-BACK-TOP into the notches in the tops of the back posts.",
        "5.  Slide RAIL-BACK-BOT and RAIL-BACK-MID in from the outside of the posts.",
        "6.  Slide the two ARM-PANELs on tangentially - the rail end tabs pass through them.",
        "7.  Thread the 14 BACK-STILEs down through the three back rails; the 60 mm tenon",
        "      seats in RAIL-BACK-BOT, the 70 mm shoulder lands on top of it.",
        "8.  Drop the three SEAT-DECK sectors over the rib tabs; they bear on both seat rails.",
        "9.  Glue every joint (PVA D3) and clamp. No fasteners are required.",
    ]
    cutting = [
        "-  Cut every CUT-layer contour through: internal contours first, outer profile last.",
        "-  6 mm compression or up-cut spiral; climb finish pass; 0.1 mm onion skin or tabs.",
        "-  Dogbone relief is already in the geometry - do not add extra cutter compensation",
        "    to the slots, only the usual tool-radius offset on the contour itself.",
        "-  Slots are cut 15.4 mm for 15.0 mm ply. Test one slot on an offcut before the run;",
        "    if your sheet measures under 14.6 mm, edit FIT in sofa_geometry.py and regenerate.",
        "-  Grain direction: run the sheet grain along the length of the curved rails.",
        "-  Nesting is shelf-packed at ~33 percent sheet use; a true nesting optimiser can",
        "    interleave the curved rails and typically saves one sheet.",
        "-  This is the frame only. Foam, webbing and fabric are not part of this cut file.",
    ]
    y0 = 0.400
    fig.text(0.035, y0 + 0.030, "ASSEMBLY SEQUENCE", fontsize=10,
             fontweight="bold", color=INK)
    for i, line in enumerate(assembly):
        fig.text(0.035, y0 - i * 0.0250, line, fontsize=8.4, color=INK)
    fig.text(0.520, y0 + 0.030, "CUTTING NOTES", fontsize=10,
             fontweight="bold", color=INK)
    for i, line in enumerate(cutting):
        fig.text(0.520, y0 - i * 0.0250, line, fontsize=8.4, color=INK)

    pdf.savefig(fig)
    plt.close(fig)


def page_assembly(pdf, parts):
    fig = _page("2  -  PLAN VIEW AND RIB SECTION")

    # ---- plan view -------------------------------------------------------
    ax = fig.add_axes([0.045, 0.10, 0.50, 0.78])
    ax.set_aspect("equal")
    ax.axis("off")

    for rail in G.RAILS:
        half = G.HALF_SWEEP
        loop = G.sector_loop(rail.r_in, rail.r_out, 90 - half, 90 + half)
        pts = L.flatten_loop(loop)
        ax.add_patch(MplPolygon(pts, closed=True, facecolor=FILL,
                                edgecolor=CUT, lw=0.7, zorder=2))
    for i in range(3):
        loop = G.sector_loop(G.DECK_R_IN, G.DECK_R_OUT,
                             90 + G.DECK_SEAMS[i], 90 + G.DECK_SEAMS[i + 1])
        ax.add_patch(MplPolygon(L.flatten_loop(loop), closed=True, facecolor="none",
                                edgecolor=ACCENT, lw=0.7, ls="--", zorder=4))
    for phi in G.RIB_ANGLES + G.ARM_ANGLES:
        a = math.radians(90 + phi)
        ax.plot([G.R_IN * math.cos(a), G.R_OUT * math.cos(a)],
                [G.R_IN * math.sin(a), G.R_OUT * math.sin(a)],
                color=INK, lw=2.2 if phi in G.ARM_ANGLES else 1.4, zorder=5)
    for phi in G.STILE_ANGLES:
        a = math.radians(90 + phi)
        ax.plot([2090 * math.cos(a), 2200 * math.cos(a)],
                [2090 * math.sin(a), 2200 * math.sin(a)],
                color=ACCENT, lw=1.0, zorder=6)

    w = 2 * G.R_OUT * math.sin(math.radians(G.HALF_SWEEP))
    y_dim = G.R_IN * math.cos(math.radians(G.HALF_SWEEP)) - 190
    dim_line(ax, (-w / 2, y_dim), (w / 2, y_dim), f"{w:.0f} overall width", off=25)
    x_dim = -w / 2 - 190
    y0 = G.R_IN * math.cos(math.radians(G.HALF_SWEEP))
    dim_line(ax, (x_dim, y0), (x_dim, G.R_OUT), f"{G.R_OUT - y0:.0f} depth", off=0)
    ax.text(0, G.R_OUT + 90, f"PLAN  -  sweep {2*G.HALF_SWEEP:.0f} deg, back R{G.R_OUT:.0f}",
            ha="center", fontsize=9, color=INK, fontweight="bold")
    ax.text(0, y_dim - 210, "solid lines: 7 ribs + 2 arm panels    dashed: seat deck sectors",
            ha="center", fontsize=7.5, color=REF)
    ax.set_xlim(-w / 2 - 330, w / 2 + 140)
    ax.set_ylim(y_dim - 330, G.R_OUT + 190)

    # ---- rib section -----------------------------------------------------
    ax2 = fig.add_axes([0.575, 0.14, 0.395, 0.66])
    ax2.set_aspect("equal")
    ax2.axis("off")
    rib = next(p for p in parts if p.key == "RIB")
    draw_loops(ax2, rib.loops)
    for z, name in [(0, "floor"), (G.DECK_TOP, f"seat frame {G.DECK_TOP:.0f}"),
                    (G.BACK_TOP, f"back top {G.BACK_TOP:.0f}")]:
        ax2.plot([-70, G.DEPTH + 70], [z, z], color=REF, lw=0.6, ls=":")
        ax2.text(G.DEPTH + 80, z, name, fontsize=7.5, color=REF, va="center")
    dim_line(ax2, (0, -110), (G.DEPTH, -110), f"{G.DEPTH:.0f} radial depth", off=18)
    dim_line(ax2, (-120, 0), (-120, G.BACK_TOP), f"{G.BACK_TOP:.0f}", off=0)
    ax2.text(G.DEPTH / 2, G.BACK_TOP + 90, "SECTION THROUGH A RIB (radial)",
             ha="center", fontsize=9, color=INK, fontweight="bold")
    ax2.text(G.DEPTH / 2, -230,
             "seat height with a 100 mm cushion: ~445 mm",
             ha="center", fontsize=7.5, color=REF)
    ax2.set_xlim(-330, G.DEPTH + 330)
    ax2.set_ylim(-300, G.BACK_TOP + 160)

    pdf.savefig(fig)
    plt.close(fig)


def page_parts_index(pdf, parts, sheets):
    """One of every distinct part, each fitted to its own cell."""
    where = {}
    for n, placements in enumerate(sheets, 1):
        for pl in placements:
            where.setdefault(pl.key, set()).add(n)

    total_pieces = sum(p.qty for p in parts)
    fig = _page(f"3  -  PARTS INDEX  -  {len(parts)} distinct parts, "
                f"{total_pieces} pieces")

    cols = 5
    cw, ch = 0.186, 0.256
    for i, part in enumerate(parts):
        r, c = divmod(i, cols)
        ax = fig.add_axes([0.038 + c * cw, 0.645 - r * ch, cw * 0.86, ch * 0.66])
        ax.set_aspect("equal")
        ax.axis("off")
        x0, y0, x1, y1 = L.loops_bbox(part.loops)
        w, h = x1 - x0, y1 - y0
        draw_loops(ax, part.loops, offset=(-x0, -y0), lw=0.7)
        span = max(w, h)
        ax.set_xlim(w / 2 - span * 0.58, w / 2 + span * 0.58)
        ax.set_ylim(h / 2 - span * 0.58, h / 2 + span * 0.58)
        sheet_list = ",".join(str(n) for n in sorted(where.get(part.key, [])))
        ax.set_title(f"{part.label}   x{part.qty}", fontsize=8.4,
                     color=INK, fontweight="bold", pad=6)
        ax.text(0.5, -0.06, f"{w:.0f} x {h:.0f} mm", transform=ax.transAxes,
                ha="center", va="top", fontsize=7.2, color=REF)
        ax.text(0.5, -0.145, f"sheet {sheet_list}", transform=ax.transAxes,
                ha="center", va="top", fontsize=7.2, color=ACCENT)

    fig.text(0.038, 0.058,
             "Each part is fitted to its own frame, so the drawings are NOT to a "
             "common scale - read the millimetre size under each one.",
             fontsize=8, color=REF)
    fig.text(0.038, 0.042,
             "Every piece is 15 mm plywood; the sheet number tells you which "
             "nesting page it is cut from.",
             fontsize=8, color=REF)
    pdf.savefig(fig)
    plt.close(fig)


def page_sheet(pdf, index, total, placements):
    counts = Counter(p.label for p in placements)
    note = ", ".join(f"{k} x{v}" for k, v in sorted(counts.items()))
    fig = _page(f"{index + 4}  -  NESTING SHEET {index + 1} OF {total}", note)

    ax = fig.add_axes([0.035, 0.09, 0.93, 0.80])
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(MplPolygon([(0, 0), (G.SHEET_W, 0), (G.SHEET_W, G.SHEET_H),
                             (0, G.SHEET_H)], closed=True, facecolor="white",
                            edgecolor=REF, lw=1.2, zorder=1))
    m = G.SHEET_MARGIN
    ax.add_patch(MplPolygon([(m, m), (G.SHEET_W - m, m), (G.SHEET_W - m, G.SHEET_H - m),
                             (m, G.SHEET_H - m)], closed=True, facecolor="none",
                            edgecolor=REF, lw=0.5, ls=":", zorder=1))

    for p in placements:
        draw_loops(ax, p.loops)
        label = p.label if counts[p.label] == 1 and p.instance == 1 else \
            f"{p.label}\n{p.instance}"
        ax.text(p.x + p.w / 2, p.y + p.h / 2, label, fontsize=7.2, color=INK,
                ha="center", va="center", zorder=8,
                bbox=dict(fc="white", ec=REF, lw=0.4, alpha=0.85, pad=1.6))

    dim_line(ax, (0, -95), (G.SHEET_W, -95), f"{G.SHEET_W:.0f}", off=18)
    dim_line(ax, (-95, 0), (-95, G.SHEET_H), f"{G.SHEET_H:.0f}", off=0)
    ax.set_xlim(-260, G.SHEET_W + 120)
    ax.set_ylim(-230, G.SHEET_H + 120)

    pdf.savefig(fig)
    plt.close(fig)


def main() -> None:
    parts, sheets = L.layout()
    out = Path(__file__).resolve().parent / "out" / "curved-sofa-cutting-plan.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(out) as pdf:
        page_spec(pdf, parts, sheets)
        page_assembly(pdf, parts)
        page_parts_index(pdf, parts, sheets)
        for i, placements in enumerate(sheets):
            page_sheet(pdf, i, len(sheets), placements)
        info = pdf.infodict()
        info["Title"] = "Curved 3-seat sofa - CNC cutting plan"
        info["Subject"] = SUBTITLE
    print(f"wrote {out}  ({3 + len(sheets)} pages)")


if __name__ == "__main__":
    main()
