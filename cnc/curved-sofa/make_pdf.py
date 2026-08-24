"""Render the curved-sofa cut file to a printable multi-page PDF.

Page 1   specification, material summary and bill of materials
Page 2   plan view and rib section with the controlling dimensions
Page 3   parts index - one of every distinct part
Page 4   foam, webbing and fabric consumption
Page 5+  one nesting page per 2440 x 1220 sheet, drawn to scale
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
SHEET_PAGE_OFFSET = 5        # nesting sheet 1 is page 5


def _page(fig_title: str, note: str = ""):
    fig = plt.figure(figsize=A3)
    fig.patch.set_facecolor("white")
    fig.text(0.035, 0.955, TITLE, fontsize=15, fontweight="bold", color=INK)
    fig.text(0.035, 0.930, fig_title, fontsize=10.5, color=ACCENT)
    fig.text(0.965, 0.955, "15 mm + 4 mm PLYWOOD  |  mm  |  1:1 DXF",
             fontsize=9, color=REF, ha="right")
    fig.text(0.965, 0.930, note, fontsize=9, color=REF, ha="right")
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


def sector_area(r_in: float, r_out: float, sweep_deg: float) -> float:
    """Plan area of an annular sector, mm^2."""
    return math.radians(sweep_deg) / 2.0 * (r_out ** 2 - r_in ** 2)


def material_rows(parts, sheets):
    rows = []
    for material, thick in ((G.PLY15, G.T), (G.PLY4, G.SKIN_T)):
        mp = [p for p in parts if p.material == material]
        if not mp:
            continue
        area = sum(L.part_area(p.loops) * p.qty for p in mp)
        cut = sum(L.cut_length(p.loops) * p.qty for p in mp)
        n = sum(1 for s in sheets if s["material"] == material)
        rows.append({
            "material": material, "thick": thick, "sheets": n,
            "pieces": sum(p.qty for p in mp), "area": area, "cut": cut,
            "use": area / (n * G.SHEET_W * G.SHEET_H) * 100.0,
            "mass": area / 1e6 * thick / 1000.0 * 600.0,
        })
    return rows


# --------------------------------------------------------------------------

def page_spec(pdf, parts, sheets):
    fig = _page("1  -  SPECIFICATION, MATERIAL AND BILL OF MATERIALS")

    plan_depth = G.R_OUT - G.R_IN * math.cos(math.radians(G.HALF_SWEEP))
    width = 2 * G.R_OUT * math.sin(math.radians(G.HALF_SWEEP))
    seat_arc = math.radians(2 * G.ARM_IN_ANGLE) * 1650.0

    spec = [
        ("Overall width (chord of the back)", f"{width:.0f} mm"),
        ("Overall depth over the crescent", f"{plan_depth:.0f} mm"),
        ("Radial depth of the seating band", f"{G.DEPTH:.0f} mm"),
        ("Plan sweep / back radius", f"{2*G.HALF_SWEEP:.0f} deg  /  R{G.R_OUT:.0f} mm"),
        ("Usable seat arc between the arms", f"{seat_arc:.0f} mm  (3 x {seat_arc/3:.0f})"),
        ("Plinth height", f"{G.PLINTH_H + G.T:.0f} mm (3 laminae)"),
        ("Seat frame above the floor", f"{G.DECK_TOP + G.PLINTH_H:.0f} mm"),
        ("Seat height with a 100 mm cushion", f"~{G.DECK_TOP + G.PLINTH_H + 100:.0f} mm"),
        ("Arm height above the floor", f"{G.ARM_TOP + G.PLINTH_H:.0f} mm"),
        ("Backrest height above the floor", f"{G.BACK_TOP + G.PLINTH_H:.0f} mm"),
        ("Joint clearance", f"slots {G.SLOT_T:.1f} mm for {G.T:.0f} mm plate"),
        ("Corner relief", f"dogbone R{G.DOGBONE_R:.1f} mm (6 mm cutter)"),
    ]
    y = 0.855
    fig.text(0.035, 0.885, "SPECIFICATION", fontsize=10, fontweight="bold", color=INK)
    for k, v in spec:
        fig.text(0.035, y, k, fontsize=8.4, color=INK)
        fig.text(0.290, y, v, fontsize=8.4, color=ACCENT, fontweight="bold")
        y -= 0.0235

    # ---- material summary ------------------------------------------------
    rows = material_rows(parts, sheets)
    fig.text(0.035, 0.545, "MATERIAL CONSUMPTION", fontsize=10,
             fontweight="bold", color=INK)
    hdr = [("MATERIAL", 0.035), ("SHEETS", 0.185), ("PIECES", 0.243),
           ("NET AREA", 0.300), ("SHEET USE", 0.368), ("CUT PATH", 0.437)]
    for text, x in hdr:
        fig.text(x, 0.520, text, fontsize=7.6, color=REF, fontweight="bold")
    y = 0.494
    for r in rows:
        fig.text(0.035, y, f"{r['material']}  ({G.SHEET_W:.0f} x {G.SHEET_H:.0f})",
                 fontsize=8.4, color=INK)
        fig.text(0.192, y, f"{r['sheets']}", fontsize=8.4, color=ACCENT,
                 fontweight="bold")
        fig.text(0.250, y, f"{r['pieces']}", fontsize=8.4, color=INK)
        fig.text(0.300, y, f"{r['area']/1e6:.2f} m2", fontsize=8.4, color=INK)
        fig.text(0.368, y, f"{r['use']:.0f} %", fontsize=8.4, color=INK)
        fig.text(0.437, y, f"{r['cut']/1000:.0f} m", fontsize=8.4, color=INK)
        y -= 0.024
    total_sheets = sum(r["sheets"] for r in rows)
    total_mass = sum(r["mass"] for r in rows)
    fig.text(0.035, y - 0.006,
             f"TOTAL  {total_sheets} sheets   -   bare frame mass ~{total_mass:.0f} kg "
             f"at 600 kg/m3, before foam and fabric",
             fontsize=8.6, fontweight="bold", color=ACCENT)
    fig.text(0.035, y - 0.034,
             "Buy one spare 15 mm sheet: the nesting is shelf-packed, and a "
             "mis-cut curved rail is the expensive one to redo.",
             fontsize=7.8, color=REF)

    # ---- bill of materials ----------------------------------------------
    fig.text(0.520, 0.885, "BILL OF MATERIALS", fontsize=10, fontweight="bold",
             color=INK)
    for text, x in (("PART", 0.520), ("QTY", 0.652), ("SIZE (mm)", 0.692),
                    ("FUNCTION", 0.790)):
        fig.text(x, 0.860, text, fontsize=7.6, color=REF, fontweight="bold")
    y = 0.836
    current = None
    for part in parts:
        if part.material != current:
            current = part.material
            fig.text(0.520, y, current, fontsize=7.6, color=ACCENT,
                     fontweight="bold")
            y -= 0.020
        b = L.loops_bbox(part.loops)
        fig.text(0.520, y, part.label, fontsize=8.2, color=INK)
        fig.text(0.656, y, str(part.qty), fontsize=8.2, color=INK)
        fig.text(0.692, y, f"{b[2]-b[0]:.0f} x {b[3]-b[1]:.0f}", fontsize=8.2,
                 color=INK)
        fig.text(0.790, y, part.note, fontsize=7.2, color=REF)
        y -= 0.0225
    fig.text(0.520, y - 0.004, f"TOTAL  {sum(p.qty for p in parts)} pieces",
             fontsize=8.6, fontweight="bold", color=ACCENT)

    assembly = [
        "1.  Glue up the plinth: 3 laminae each of RAIL-BASE-IN and RAIL-BASE-OUT.",
        "2.  Drop the 5 RIBs and the 2 ARM-PANEL-INs onto the plinth rails.",
        "3.  Drop RAIL-SEAT-IN / -OUT and RAIL-BACK-BOT / -MID into the rib notches;",
        "      they end at the inner arm panels with tabs through them.",
        "4.  Slide the 2 ARM-PANEL-INs home over those end tabs.",
        "5.  Drop RAIL-BACK-TOP in - it runs the full width through both arm panels.",
        "6.  Thread the 12 BACK-STILEs down through the three back rails.",
        "7.  Drop the 2 ARM-PANEL-OUTs on, then the 2 ARM-CAPs into the top notches.",
        "8.  Drop the three SEAT-DECK sectors over the rib tabs.",
        "9.  Bend and glue the three 4 mm SKINs around the base and the back.",
        "10. Glue every joint (PVA D3) and clamp. No fasteners are required.",
    ]
    y0 = 0.360
    fig.text(0.035, y0 + 0.030, "ASSEMBLY SEQUENCE", fontsize=10,
             fontweight="bold", color=INK)
    for i, line in enumerate(assembly):
        fig.text(0.035, y0 - i * 0.0235, line, fontsize=8.2, color=INK)

    pdf.savefig(fig)
    plt.close(fig)


def page_assembly(pdf, parts):
    fig = _page("2  -  PLAN VIEW AND RIB SECTION")

    ax = fig.add_axes([0.045, 0.10, 0.50, 0.78])
    ax.set_aspect("equal")
    ax.axis("off")

    for rail in G.RAILS:
        half = rail.half_sweep
        loop = G.sector_loop(rail.r_in, rail.r_out, 90 - half, 90 + half)
        ax.add_patch(MplPolygon(L.flatten_loop(loop), closed=True, facecolor=FILL,
                                edgecolor=CUT, lw=0.7, zorder=2))
    for i in range(3):
        a1, a2 = G.DECK_SEAMS[i], G.DECK_SEAMS[i + 1]
        loop = G.sector_loop(G.DECK_R_IN, G.DECK_R_OUT, 90 + a1, 90 + a2)
        ax.add_patch(MplPolygon(L.flatten_loop(loop), closed=True, facecolor="none",
                                edgecolor=ACCENT, lw=0.7, ls="--", zorder=4))
    for sign in (-1, 1):
        loop = G.sector_loop(G.ARM_CAP_R_IN, G.ARM_CAP_R_OUT,
                             90 + sign * G.ARM_IN_ANGLE if sign > 0
                             else 90 - G.ARM_OUT_ANGLE,
                             90 + G.ARM_OUT_ANGLE if sign > 0
                             else 90 - G.ARM_IN_ANGLE)
        ax.add_patch(MplPolygon(L.flatten_loop(loop), closed=True,
                                facecolor="#e6ded0", edgecolor=CUT, lw=0.7, zorder=3))
    for phi in G.RIB_ANGLES:
        a = math.radians(90 + phi)
        ax.plot([G.R_IN * math.cos(a), G.R_OUT * math.cos(a)],
                [G.R_IN * math.sin(a), G.R_OUT * math.sin(a)],
                color=INK, lw=1.4, zorder=5)
    for phi in G.ARM_IN_ANGLES + G.ARM_OUT_ANGLES:
        a = math.radians(90 + phi)
        ax.plot([G.R_IN * math.cos(a), G.R_OUT * math.cos(a)],
                [G.R_IN * math.sin(a), G.R_OUT * math.sin(a)],
                color=INK, lw=2.6, zorder=6)
    for phi in G.STILE_ANGLES:
        a = math.radians(90 + phi)
        ax.plot([2090 * math.cos(a), 2200 * math.cos(a)],
                [2090 * math.sin(a), 2200 * math.sin(a)],
                color=ACCENT, lw=1.0, zorder=7)

    w = 2 * G.R_OUT * math.sin(math.radians(G.HALF_SWEEP))
    y_dim = G.R_IN * math.cos(math.radians(G.HALF_SWEEP)) - 190
    dim_line(ax, (-w / 2, y_dim), (w / 2, y_dim), f"{w:.0f} overall width", off=25)
    x_dim = -w / 2 - 190
    y0 = G.R_IN * math.cos(math.radians(G.HALF_SWEEP))
    dim_line(ax, (x_dim, y0), (x_dim, G.R_OUT), f"{G.R_OUT - y0:.0f} depth", off=0)
    ax.text(0, G.R_OUT + 90,
            f"PLAN  -  sweep {2*G.HALF_SWEEP:.0f} deg, back R{G.R_OUT:.0f}",
            ha="center", fontsize=9, color=INK, fontweight="bold")
    ax.text(0, y_dim - 210,
            "thick lines: 4 arm panels    thin: 5 ribs    "
            "dashed: seat deck    shaded: arm caps",
            ha="center", fontsize=7.5, color=REF)
    ax.set_xlim(-w / 2 - 330, w / 2 + 140)
    ax.set_ylim(y_dim - 330, G.R_OUT + 190)

    ax2 = fig.add_axes([0.575, 0.14, 0.395, 0.66])
    ax2.set_aspect("equal")
    ax2.axis("off")
    rib = next(p for p in parts if p.key == "RIB")
    draw_loops(ax2, rib.loops, offset=(0.0, G.PLINTH_H))
    plinth = G.RAIL_BY_KEY["BASE_OUT"]
    for x0, x1 in ((20.0, 120.0), (780.0, 880.0)):
        ax2.add_patch(MplPolygon([(x0, 0), (x1, 0), (x1, G.PLINTH_H), (x0, G.PLINTH_H)],
                                 closed=True, facecolor="#e6ded0", edgecolor=CUT,
                                 lw=0.7, zorder=2))
    for z, name in [(0, "floor"),
                    (G.PLINTH_H, f"plinth top {G.PLINTH_H:.0f}"),
                    (G.DECK_TOP + G.PLINTH_H, f"seat frame {G.DECK_TOP+G.PLINTH_H:.0f}"),
                    (G.ARM_TOP + G.PLINTH_H, f"arm {G.ARM_TOP+G.PLINTH_H:.0f}"),
                    (G.BACK_TOP + G.PLINTH_H, f"back top {G.BACK_TOP+G.PLINTH_H:.0f}")]:
        ax2.plot([-70, G.DEPTH + 70], [z, z], color=REF, lw=0.6, ls=":")
        ax2.text(G.DEPTH + 80, z, name, fontsize=7.5, color=REF, va="center")
    top = G.BACK_TOP + G.PLINTH_H
    dim_line(ax2, (0, -110), (G.DEPTH, -110), f"{G.DEPTH:.0f} radial depth", off=18)
    dim_line(ax2, (-120, 0), (-120, top), f"{top:.0f}", off=0)
    ax2.text(G.DEPTH / 2, top + 90, "SECTION THROUGH A RIB (radial)",
             ha="center", fontsize=9, color=INK, fontweight="bold")
    ax2.text(G.DEPTH / 2, -230,
             "shaded blocks: the two extra plinth laminae under the base rails",
             ha="center", fontsize=7.5, color=REF)
    ax2.set_xlim(-380, G.DEPTH + 380)
    ax2.set_ylim(-300, top + 160)

    pdf.savefig(fig)
    plt.close(fig)


def page_parts_index(pdf, parts, sheets):
    where = {}
    for n, sheet in enumerate(sheets, 1):
        for pl in sheet["placements"]:
            where.setdefault(pl.key, set()).add(n)

    total_pieces = sum(p.qty for p in parts)
    fig = _page(f"3  -  PARTS INDEX  -  {len(parts)} distinct parts, "
                f"{total_pieces} pieces")

    cols = 6
    cw, ch = 0.155, 0.256
    for i, part in enumerate(parts):
        r, c = divmod(i, cols)
        ax = fig.add_axes([0.038 + c * cw, 0.645 - r * ch, cw * 0.86, ch * 0.66])
        ax.set_aspect("equal")
        ax.axis("off")
        x0, y0, x1, y1 = L.loops_bbox(part.loops)
        w, h = x1 - x0, y1 - y0
        face = "#e8eef5" if part.material == G.PLY4 else FILL
        draw_loops(ax, part.loops, facecolor=face, offset=(-x0, -y0), lw=0.7)
        span = max(w, h)
        ax.set_xlim(w / 2 - span * 0.58, w / 2 + span * 0.58)
        ax.set_ylim(h / 2 - span * 0.58, h / 2 + span * 0.58)
        sheets_txt = ",".join(str(n) for n in sorted(where.get(part.key, [])))
        ax.set_title(f"{part.label}   x{part.qty}", fontsize=8.0, color=INK,
                     fontweight="bold", pad=6)
        ax.text(0.5, -0.06, f"{w:.0f} x {h:.0f} mm", transform=ax.transAxes,
                ha="center", va="top", fontsize=7.0, color=REF)
        ax.text(0.5, -0.145, f"sheet {sheets_txt}", transform=ax.transAxes,
                ha="center", va="top", fontsize=7.0, color=ACCENT)

    fig.text(0.038, 0.058,
             "Each part is fitted to its own frame, so the drawings are NOT to a "
             "common scale - read the millimetre size under each one.",
             fontsize=8, color=REF)
    fig.text(0.038, 0.042,
             "Blue-tinted parts are 4 mm flexible plywood; everything else is "
             "15 mm. The sheet number tells you which nesting page it is on.",
             fontsize=8, color=REF)
    pdf.savefig(fig)
    plt.close(fig)


def page_foam(pdf):
    fig = _page("4  -  FOAM, FABRIC AND CONSUMABLES")

    seat_sweep = 2 * G.DECK_EDGE
    arm_sweep = G.ARM_OUT_ANGLE - G.ARM_IN_ANGLE
    back_h = G.BACK_TOP - G.DECK_TOP
    base_h = G.DECK_TOP + G.PLINTH_H
    arm_h = G.ARM_TOP - G.DECK_TOP + 220.0

    def arc(r, sweep):
        return math.radians(sweep) * r

    seat_area = sector_area(G.DECK_R_IN, G.DECK_R_OUT, seat_sweep)
    seat_perimeter = (2 * (G.DECK_R_OUT - G.DECK_R_IN)
                      + arc(G.DECK_R_IN, seat_sweep) + arc(G.DECK_R_OUT, seat_sweep))
    back_area = sector_area(1990.0, 2140.0, 2 * G.ARM_IN_ANGLE)
    arm_area = sector_area(G.DECK_R_IN, G.ARM_CAP_R_OUT, arm_sweep)

    # ---- foam -----------------------------------------------------------
    foam = [
        ("Seat cushion", "HR foam 35 kg/m3", seat_area, 120.0, 1,
         f"annular sector R{G.DECK_R_IN:.0f}-{G.DECK_R_OUT:.0f}, {seat_sweep:.1f} deg"),
        ("Back cushion", "HR foam 30 kg/m3", back_area, back_h, 1,
         f"{back_h:.0f} tall against the lattice, 150 deep"),
        ("Arm bolster", "HR foam 30 kg/m3", arm_area, 220.0, 2,
         "over the arm cap; the front roll is carved from the block"),
    ]
    fig.text(0.035, 0.880, "FOAM SCHEDULE", fontsize=10, fontweight="bold", color=INK)
    for text, x in (("ITEM", 0.035), ("SPEC", 0.160), ("QTY", 0.290),
                    ("PLAN AREA", 0.330), ("THICK / HT", 0.408),
                    ("VOLUME", 0.487), ("NOTE", 0.560)):
        fig.text(x, 0.853, text, fontsize=7.6, color=REF, fontweight="bold")
    y = 0.827
    total_vol = 0.0
    for name, spec, area, thick, qty, note in foam:
        vol = area * thick * qty / 1e9
        total_vol += vol
        fig.text(0.035, y, name, fontsize=8.4, color=INK)
        fig.text(0.160, y, spec, fontsize=8.0, color=INK)
        fig.text(0.295, y, str(qty), fontsize=8.4, color=INK)
        fig.text(0.330, y, f"{area/1e6:.2f} m2", fontsize=8.4, color=INK)
        fig.text(0.408, y, f"{thick:.0f} mm", fontsize=8.4, color=INK)
        fig.text(0.487, y, f"{vol*1000:.0f} L", fontsize=8.4, color=ACCENT,
                 fontweight="bold")
        fig.text(0.560, y, note, fontsize=7.4, color=REF)
        y -= 0.027
    fig.text(0.035, y - 0.004,
             f"TOTAL FOAM  {total_vol*1000:.0f} litres = {total_vol:.3f} m3   -   "
             f"about {total_vol*32:.0f} kg, cut from bought blocks against the "
             f"SEAT-DECK and ARM-CAP parts used as templates",
             fontsize=8.6, fontweight="bold", color=ACCENT)

    # ---- sheet goods ----------------------------------------------------
    sheet_goods = [
        ("Polyester wadding 200 g/m2", seat_area + back_area * 2 + arm_area * 2,
         "under every cover"),
        ("Stretch calico, first cover", seat_area + arc(2140.0, 2 * G.ARM_IN_ANGLE)
         * back_h, "platform + inside back"),
        ("Black cambric dust cover", sector_area(G.R_IN, G.R_OUT, 2 * G.HALF_SWEEP),
         "stapled under the plinth"),
    ]
    fig.text(0.035, 0.680, "SHEET GOODS", fontsize=10, fontweight="bold", color=INK)
    y = 0.652
    for name, area, note in sheet_goods:
        fig.text(0.035, y, name, fontsize=8.4, color=INK)
        fig.text(0.300, y, f"{area/1e6:.2f} m2", fontsize=8.4, color=ACCENT,
                 fontweight="bold")
        fig.text(0.375, y, note, fontsize=7.4, color=REF)
        y -= 0.026

    # ---- cover panels ---------------------------------------------------
    panels = [
        ("Seat cushion, top and bottom", 2 * seat_area),
        ("Seat cushion border", seat_perimeter * 120.0),
        ("Back cushion, front and back",
         (arc(1990.0, 2 * G.ARM_IN_ANGLE) + arc(2140.0, 2 * G.ARM_IN_ANGLE)) * back_h),
        ("Back cushion top and ends", back_area + 2 * 150.0 * back_h),
        ("Arm covers, both arms",
         2 * (2 * (G.ARM_CAP_R_OUT - G.DECK_R_IN) * arm_h
              + arc(G.ARM_CAP_R_OUT, arm_sweep) * (arm_h + 300.0))),
        ("Base outer and front faces",
         (arc(G.R_OUT, 2 * G.HALF_SWEEP) + arc(G.R_IN, 2 * G.HALF_SWEEP)) * base_h),
        ("Base ends, both", 2 * G.DEPTH * base_h),
        ("Seat platform, inside back", seat_area),
    ]
    fig.text(0.560, 0.680, "COVER PANEL SCHEDULE", fontsize=10,
             fontweight="bold", color=INK)
    y = 0.652
    total_cover = 0.0
    for name, area in panels:
        total_cover += area
        fig.text(0.560, y, name, fontsize=8.4, color=INK)
        fig.text(0.860, y, f"{area/1e6:.2f} m2", fontsize=8.4, color=INK)
        y -= 0.026
    waste, bolt_w = 1.5, 1.40
    linear = total_cover / 1e6 * waste / bolt_w
    fig.text(0.560, y - 0.004, f"NET COVER AREA  {total_cover/1e6:.2f} m2",
             fontsize=8.6, fontweight="bold", color=INK)
    fig.text(0.560, y - 0.032,
             f"FABRIC TO BUY  {linear:.0f} linear metres on a {bolt_w*100:.0f} cm bolt",
             fontsize=9.2, fontweight="bold", color=ACCENT)
    fig.text(0.560, y - 0.058,
             f"Includes a {(waste-1)*100:.0f} % allowance: a crescent frame nests "
             "badly and every panel is cut on a curve.",
             fontsize=7.8, color=REF)
    fig.text(0.560, y - 0.078,
             "Add another 30 % for a directional, striped or patterned fabric.",
             fontsize=7.8, color=REF)

    extras = [
        "Elastic webbing 50 mm: 9 radial runs x 900 mm plus 15 % tension = 9.5 m, "
        "with 18 clips.",
        "Staples 10 mm: roughly 900 for a frame this size.",
        "PVA D3 wood glue: about 1.0 litre for the plinth lamination and every "
        "slot joint.",
        "Spray contact adhesive for foam: 1 aerosol per 2 m2 of foam face, so 3 cans.",
        "Feet are not in the cut file - the 45 mm laminated plinth IS the foot. "
        "Add bought glides, or a 60 mm metal leg set if the sofa should sit higher.",
    ]
    fig.text(0.035, 0.300, "OTHER CONSUMABLES", fontsize=10, fontweight="bold",
             color=INK)
    y = 0.268
    for line in extras:
        for j, chunk in enumerate(_wrap(line, 96)):
            fig.text(0.035 + (0.010 if j else 0.0), y,
                     ("-  " if not j else "   ") + chunk, fontsize=8.2, color=INK)
            y -= 0.023
        y -= 0.006

    pdf.savefig(fig)
    plt.close(fig)


def _wrap(text: str, width: int) -> list:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


def page_sheet(pdf, index, total, sheet):
    placements = sheet["placements"]
    counts = Counter(p.label for p in placements)
    note = ", ".join(f"{k} x{v}" for k, v in sorted(counts.items()))
    fig = _page(f"{index + SHEET_PAGE_OFFSET}  -  NESTING SHEET {index + 1} OF "
                f"{total}  -  {sheet['material']}", note)

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

    face = "#e8eef5" if sheet["material"] == G.PLY4 else FILL
    for p in placements:
        draw_loops(ax, p.loops, facecolor=face)
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
        page_foam(pdf)
        for i, sheet in enumerate(sheets):
            page_sheet(pdf, i, len(sheets), sheet)
        info = pdf.infodict()
        info["Title"] = "Curved 3-seat sofa - CNC cutting plan"
        info["Subject"] = "slot-and-tab plywood frame, cut layout and consumption"
    print(f"wrote {out}  ({4 + len(sheets)} pages)")


if __name__ == "__main__":
    main()
