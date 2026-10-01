"""Assemble the Lena sofa digital-product package.

    python package.py            # after build.py, export_step.py and the
                                 # Blender renders (render_blender.py)

Writes package/LENA_SOFA/ in the standard layout:
01_DXF, 02_3D, 03_DOCUMENTATION, 04_PREVIEWS, 05_DATA, README.txt.

Every parameter carries a provenance status, and the product status is
derived from the validation results and the open inputs - it is never set
by hand. A render is not evidence of manufacturability; the checks are.
"""

from __future__ import annotations

import json
import math
import shutil
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))  # shared code, lower priority

import ezdxf
import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

import build
import lena_geometry as C
import labels as B
import sofa_layout as L
import verify
import verify_3d

PRODUCT = "LENA_SOFA"
ROOT = HERE / "package" / PRODUCT
OUT = HERE / "out"
INK, REF, ACCENT = "#1f2328", "#6e7781", "#9a6700"

# --------------------------------------------------------------------------
# parameters and their provenance
# --------------------------------------------------------------------------
# status vocabulary
USER = "USER_CONFIRMED"
TOKYO = "ADOPTED_FROM_TOKYO_PACK"      # joint practice copied from the bought pack
DESIGN = "DESIGN_CHOICE_UNCONFIRMED"   # chosen by us; user to confirm or change
ASSUMED = "ASSUMED_USER_INPUT_REQUIRED"
DERIVED = "DERIVED"
UNKNOWN = "UNKNOWN"

PARAMETERS = [
    # name, value, unit, status, note
    ("MATERIAL", "MDF", "", USER, "user works in MDF; birch plywood also suitable"),
    ("MATERIAL_THICKNESS", C.T, "mm", USER, "NOMINAL - measure the real sheet before cutting"),
    ("CLEARANCE", C.JOINT.fit, "mm", TOKYO, "total across each slot - UNTESTED FIT"),
    ("SLOT_WIDTH", C.SLOT_T, "mm", DERIVED, "MATERIAL_THICKNESS + CLEARANCE"),
    ("TAB_LENGTH", C.TAB_W, "mm", TOKYO, ""),
    ("MORTISE_LENGTH", C.TAB_SLOT, "mm", DERIVED, "TAB_LENGTH + CLEARANCE"),
    ("SLOT_DEPTH", C.T, "mm", DERIVED, "through-mortises; rail halvings to mid-height"),
    ("CNC_BIT_DIAMETER", C.JOINT.tool_d, "mm", ASSUMED, "sizes every dogbone relief"),
    ("RELIEF_RADIUS", C.RELIEF_R, "mm", DERIVED, "CNC_BIT_DIAMETER / 2 + 0.2"),
    ("KERF_COMPENSATION", None, "mm", UNKNOWN, "apply the tool-radius offset in CAM; "
                                                 "the DXF is net part geometry"),
    ("SHEET_SIZE", "2440 x 1220", "mm", ASSUMED, "standard sheet; confirm the supplier size"),
    ("PART_GAP", C.PART_GAP, "mm", TOKYO, ""),
    ("SHEET_EDGE", C.SHEET_MARGIN, "mm", TOKYO, "clamping margin"),
    ("WIDTH", C.W, "mm", DESIGN, "outer arm face to outer arm face"),
    ("DEPTH", C.D, "mm", DESIGN, "frame; + back foam"),
    ("HEIGHT", C.ARCH_TOP, "mm", DESIGN, "arch crowns; + 40~50 mm back cushion"),
    ("SEAT_FRAME_HEIGHT", C.SEAT_TOP, "mm", DESIGN, "deck top; + 120~140 mm seat cushion = ~450"),
    ("ARM_HEIGHT", C.ARM_TOP + C.DRUM_R, "mm", DESIGN, "top of the drum (spacer caps)"),
    ("ARM_WIDTH", C.ARM_W, "mm", DESIGN, ""),
    ("SEAT_BAYS", C.BAYS, "", DESIGN, f"one arch per bay, {C.BAY:.1f} mm clear each"),
    ("POST_HEIGHT", C.POST_TOP, "mm", DESIGN, "rib / arm post tops behind the arches"),
    ("PLINTH_RECESS", C.PLINTH, "mm", DESIGN, f"between {C.FOOT_LEN:.0f} mm feet front and back"),
    ("GRAIN_DIRECTION", None, "", DERIVED, "not applicable to MDF; for plywood, run "
                                              "rail grain along the length"),
]

OPEN_INPUTS = [
    ("CNC_BIT_DIAMETER", "What cutter diameter will cut this job? (dogbones assume 6 mm)"),
    ("MATERIAL_THICKNESS", "Caliper the real sheet in 3 places (nominal 18 mm)."),
    ("SHEET_SIZE", "Confirm the sheet size from your supplier (2440 x 1220 assumed)."),
    ("OVERALL_DIMENSIONS", f"Confirm or change the frame {C.W:.0f} x {C.D:.0f} x {C.ARCH_TOP:.0f} mm, seat frame {C.SEAT_TOP:.0f}, arms {C.ARM_TOP + C.DRUM_R:.0f} (finished about 226 x 90 x 85 cm, seat ~45 cm)."),
]


# --------------------------------------------------------------------------
# 3D outline helpers (for drawings)
# --------------------------------------------------------------------------

def instances(parts):
    """(part, None, 3D polyline of the outline) per piece."""
    out = []
    for p, k, plane, w0, loops in C.instances(parts):
        pts = [C.to3d(plane, w0 + C.T / 2, u, v) for u, v in L.flatten_loop(loops[0], 8)]
        out.append((p, None, pts))
    return out


def dim(ax, p0, p1, text, off, vertical=False, status=DESIGN):
    (x0, y0), (x1, y1) = p0, p1
    if vertical:
        ax.annotate("", (x0 + off, y0), (x1 + off, y1),
                    arrowprops=dict(arrowstyle="<->", color=ACCENT, lw=0.8))
        ax.text(x0 + off + 12, (y0 + y1) / 2, text, rotation=90, va="center",
                fontsize=8, color=ACCENT)
    else:
        ax.annotate("", (x0, y0 + off), (x1, y1 + off),
                    arrowprops=dict(arrowstyle="<->", color=ACCENT, lw=0.8))
        ax.text((x0 + x1) / 2, y0 + off + 12, text, ha="center", fontsize=8, color=ACCENT)


def dimension_figure(parts):
    inst = instances(parts)
    fig, axes = plt.subplots(1, 3, figsize=(16, 6.2), gridspec_kw={"width_ratios": [2.4, 1, 2.4]})
    views = ((axes[0], (0, 2), "FRONT ELEVATION"), (axes[1], (1, 2), "SIDE (from the left)"),
             (axes[2], (0, 1), "PLAN"))
    for ax, (i, j), title in views:
        for p, a, pts in inst:
            xs = [q[i] for q in pts]
            ys = [q[j] for q in pts]
            ax.plot(xs + xs[:1], ys + ys[:1], lw=0.35, color=INK)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title, fontsize=10, color=INK, loc="left")
    a1, a2, a3 = axes
    dim(a1, (0, 0), (C.W, 0), f"W {C.W:.0f}", -80)
    dim(a1, (C.W, 0), (C.W, C.ARCH_TOP), f"H {C.ARCH_TOP:.0f}", 90, vertical=True)
    dim(a1, (0, 0), (0, C.ARM_TOP + C.DRUM_R), f"arm {C.ARM_TOP + C.DRUM_R:.0f}", -110, vertical=True)
    dim(a1, (C.SEAT_X0, 0), (C.SEAT_X0, C.SEAT_TOP), f"seat {C.SEAT_TOP:.0f}", 120, vertical=True)
    dim(a2, (0, 0), (C.D, 0), f"D {C.D:.0f}", -80)
    dim(a2, (C.D, 0), (C.D, C.POST_TOP), f"post {C.POST_TOP:.0f}", 70, vertical=True)
    dim(a3, (0, 0), (C.W, 0), f"W {C.W:.0f}", -80)
    dim(a3, (C.W, 0), (C.W, C.D), f"D {C.D:.0f}", 90, vertical=True)
    a3.text(C.W / 2, -150, "FRONT", ha="center", fontsize=8, color=REF)
    fig.text(0.02, 0.02, "All dimensions mm. Overall dimensions are DESIGN CHOICES "
             "(unconfirmed) - see 05_DATA/parameters.json. Board 18 mm NOMINAL.",
             fontsize=8, color=REF)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    return fig


# --------------------------------------------------------------------------
# documents
# --------------------------------------------------------------------------

def page(title, subtitle=""):
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.text(0.035, 0.955, f"LENA SOFA  /  {title}", fontsize=13,
             fontweight="bold", color=INK)
    if subtitle:
        fig.text(0.035, 0.925, subtitle, fontsize=9, color=REF)
    fig.add_artist(plt.Line2D([0.035, 0.965], [0.912, 0.912], color=REF, lw=0.6))
    fig.text(0.035, 0.025, f"{PRODUCT}  -  generated {date.today()}  -  mm  -  "
             "status: see README / validation.json", fontsize=7, color=REF)
    return fig


def table(fig, rows, cols, x0=0.035, y0=0.87, dy=0.028, size=8.2):
    for k, (head, x) in enumerate(cols):
        fig.text(x0 + x, y0, head, fontsize=size - 0.6, color=REF, fontweight="bold")
    y = y0 - dy
    for row in rows:
        for (head, x), val in zip(cols, row):
            fig.text(x0 + x, y, str(val), fontsize=size, color=INK)
        y -= dy
    return y


def parts_list_pdf(parts, path):
    with PdfPages(path) as pdf:
        fig = page("PARTS LIST", f"{len(parts)} unique parts, "
                                 f"{sum(p.qty for p in parts)} pieces, "
                                 f"{C.T:.0f} mm board (nominal)")
        rows = []
        for p in parts:
            b = L.loops_bbox(p.loops)
            rows.append((f"P{p.num:02d}", p.label, p.qty,
                         f"{b[2] - b[0]:.0f} x {b[3] - b[1]:.0f}",
                         f"{L.part_area(p.loops) / 1e4:.1f}", len(p.loops) - 1,
                         p.note[:58]))
        y = table(fig, rows, [("ID", 0), ("PART", 0.05), ("QTY", 0.19), ("SIZE mm", 0.23),
                              ("AREA dm2", 0.34), ("CUT-OUTS", 0.42), ("ROLE / POSITION", 0.51)])
        fig.text(0.035, y - 0.02, "Every piece is engraved with its ID, name and instance "
                 "(e.g. '09 ARM-SPACER 2/6'). Part numbers follow the assembly order.", fontsize=8, color=REF)
        pdf.savefig(fig)
        plt.close(fig)


def assembly_steps():
    return [
        ("BACK", "STEP 01 - Back chain: ribs and arches",
         "Stand P01 RIB-A on the floor. Push two P03 BACK-ARCHes into its post mortises, one "
         "from each side. Slide P02 RIB-B onto the right arch's free tabs, add the third arch, "
         "then the second RIB-A and the fourth arch. The ribs stand 426.5 mm apart (clear) - "
         "every arch is the same part."),
        ("RAILS", "STEP 02 - Seat rails",
         "Drop P04 RAIL-FRONT, P05 RAIL-MID and P06 RAIL-BACK down into the slots in the rib "
         "tops (rail slots face down). Each rail must seat fully: its top flush with the rib "
         "tops. The rail end tabs stick out past the outer arches."),
        ("INNER", "STEP 03 - Inner arm panels",
         "Slide P07 ARM-INNER-L onto the left ends: the rail tabs and the first arch's tabs go "
         "through its mortises together. Same for P08 ARM-INNER-R on the right. L and R differ "
         "only in the arch mortise heights - check the engraving."),
        ("SPACERS", "STEP 04 - Arm spacers",
         "Push three P09 ARM-SPACERs into each inner arm panel from outside, round drum cap up. "
         "The cap rests on the panel top edge."),
        ("OUTER", "STEP 05 - Outer arm panels",
         "Slide each P10 ARM-OUTER onto the spacers' free tabs until the caps rest on its top "
         "edge too. The arms are now closed boxes."),
        ("DECK", "STEP 06 - Seat decks",
         "Lower the two P11 SEAT-DECKs onto the RIB-A top tabs; they meet over the middle rib. "
         "The second deck is the same part turned over. Check the frame is square, then glue "
         "(PVA D3) every joint and staple the tabs."),
    ]


def assembly_guide_pdf(parts, path, previews):
    with PdfPages(path) as pdf:
        fig = page("ASSEMBLY GUIDE", "frame only - upholstery is outside this pack")
        img = mpimg.imread(previews / "hero_render.png")
        ax = fig.add_axes([0.03, 0.08, 0.46, 0.8])
        ax.imshow(img)
        ax.axis("off")
        img = mpimg.imread(previews / "exploded_view.png")
        ax = fig.add_axes([0.51, 0.08, 0.46, 0.8])
        ax.imshow(img)
        ax.axis("off")
        pdf.savefig(fig)
        plt.close(fig)
        for key, title, text in assembly_steps():
            fig = page(title)
            ax = fig.add_axes([0.03, 0.08, 0.6, 0.8])
            ax.imshow(mpimg.imread(OUT / f"lena-sofa-step-{key.lower()}.png"))
            ax.axis("off")
            fig.text(0.65, 0.80, text, fontsize=10, color=INK, wrap=True,
                     va="top", ha="left")
            fig.text(0.65, 0.20, "New parts are shown in terracotta, a few cm before\n"
                     "they slide into place along their tabs.", fontsize=8.5,
                     color=REF, va="top")
            pdf.savefig(fig)
            plt.close(fig)
        fig = page("BEFORE YOU GLUE")
        notes = [
            "Dry-fit the whole frame first. The 1 mm clearance is an UNTESTED FIT:",
            "cut one test slot on an offcut and try a tab before cutting the sheets.",
            "",
            "If tabs are loose, lower CLEARANCE; if tight, measure the board and raise",
            "MATERIAL_THICKNESS - then regenerate (build.py) rather than sanding.",
            "",
            "Glue: PVA D3 in every mortise and halving. Staples through the tabs.",
            "The arches are held only by their tabs: glue all 16 of them.",
            "Seat: foam directly on the decks (breathing holes are cut in).",
            "",
            "ASSEMBLY SEQUENCE: checked in 3D - every piece slides home along one axis",
            "without touching what is already built. Not yet confirmed on a real build.",
        ]
        for k, line in enumerate(notes):
            fig.text(0.06, 0.84 - k * 0.04, line, fontsize=10.5, color=INK)
        pdf.savefig(fig)
        plt.close(fig)


def dimensions_pdf(parts, path):
    with PdfPages(path) as pdf:
        fig = dimension_figure(parts)
        pdf.savefig(fig)
        plt.close(fig)
        fig = page("PARAMETERS", "every value with its provenance status")
        rows = [(n, "" if v is None else (f"{v:g}" if isinstance(v, (int, float)) else v),
                 u, s, note[:52]) for n, v, u, s, note in PARAMETERS]
        table(fig, rows, [("PARAMETER", 0), ("VALUE", 0.2), ("UNIT", 0.29),
                          ("STATUS", 0.34), ("NOTE", 0.57)], dy=0.027, size=7.8)
        pdf.savefig(fig)
        plt.close(fig)


def cnc_notes_pdf(parts, sheets, results, path, previews):
    with PdfPages(path) as pdf:
        fig = page("CNC NOTES", f"{len(sheets)} sheets {C.SHEET_W:.0f} x {C.SHEET_H:.0f} x "
                                f"{C.T:.0f} mm (sheet size ASSUMED)")
        lines = [
            ("Units / scale", "millimetres, 1:1 - never rescale the DXF"),
            ("Layers", "CUT (all closed, cut through)  /  ENGRAVE-LABEL (0.5-1 mm)  /  "
                       "REFERENCE-SHEET (do not cut)"),
            ("Joints", f"through-mortises {C.TAB_SLOT:.0f} x {C.SLOT_T:.0f} mm for "
                       f"{C.TAB_W:.0f} mm tabs in {C.T:.0f} mm board - UNTESTED FIT"),
            ("Corner relief", f"R{C.RELIEF_R:.1f} dogbone in every inside corner, sized for a "
                              f"{C.JOINT.tool_d:.0f} mm bit (ASSUMED)"),
            ("Cutter offset", "apply the normal tool-radius offset on every CUT contour; "
                              "no extra compensation inside slots"),
            ("Cut order", "engrave, then inside contours (mortises, openings), then outlines"),
            ("Hold-down", f"parts {C.PART_GAP:.0f} mm apart, {C.SHEET_MARGIN:.0f} mm clamp "
                          "edge; add onion-skin or tabs for small ribs"),
            ("Small parts", "spacers and arches sit next to long rails - add tabs or "
                            "onion-skin so they cannot move on the last pass"),
        ]
        for k, (a, b) in enumerate(lines):
            fig.text(0.04, 0.85 - k * 0.05, a, fontsize=9.5, color=REF, fontweight="bold")
            fig.text(0.21, 0.85 - k * 0.05, b, fontsize=9.5, color=INK)
        pdf.savefig(fig)
        plt.close(fig)
        fig = page("CUTTING LAYOUT")
        ax = fig.add_axes([0.03, 0.06, 0.94, 0.84])
        ax.imshow(mpimg.imread(previews / "cnc_layout.png"))
        ax.axis("off")
        pdf.savefig(fig)
        plt.close(fig)
        fig = page("VALIDATION", "automated checks - geometry, joints, 3D assembly")
        y = 0.87
        for sec, ok, msg in results:
            fig.text(0.04, y, "PASS" if ok else "FAIL", fontsize=7.4,
                     color="#1a7f37" if ok else "#cf222e", fontweight="bold")
            fig.text(0.08, y, f"{sec}  {msg}"[:150], fontsize=7.4, color=INK)
            y -= 0.0165
            if y < 0.06:
                pdf.savefig(fig)
                plt.close(fig)
                fig = page("VALIDATION (cont.)")
                y = 0.87
        pdf.savefig(fig)
        plt.close(fig)


# --------------------------------------------------------------------------
# DXF per part, data, status
# --------------------------------------------------------------------------

def part_dxfs(parts, folder):
    folder.mkdir(parents=True, exist_ok=True)
    for p in parts:
        doc = ezdxf.new("R2010", setup=True)
        doc.units = ezdxf.units.MM
        doc.header["$INSUNITS"] = 4
        doc.layers.add("CUT", color=1)
        doc.layers.add("ENGRAVE-LABEL", color=3)
        msp = doc.modelspace()
        loops = L.normalise(p.loops)
        for loop in loops:
            msp.add_lwpolyline(loop, format="xyb", close=True, dxfattribs={"layer": "CUT"})
        lab = B.place(loops, B.texts(p.num, p.label, 1, 1))
        if lab:
            from ezdxf.enums import TextEntityAlignment
            msp.add_text(lab.text, height=lab.height,
                         dxfattribs={"layer": "ENGRAVE-LABEL", "rotation": lab.angle}
                         ).set_placement((lab.x, lab.y), align=TextEntityAlignment.MIDDLE_CENTER)
        doc.saveas(folder / f"P{p.num:02d}_{p.label}_x{p.qty}.dxf")


def parts_json(parts):
    rows = []
    for p in parts:
        b = L.loops_bbox(p.loops)
        rows.append({
            "part_id": f"P{p.num:02d}",
            "name": p.label,
            "quantity": p.qty,
            "material": "MDF",
            "thickness_mm": C.T,
            "thickness_status": "NOMINAL_USER_CONFIRMED",
            "flat_size_mm": {"x": round(b[2] - b[0], 2), "y": round(b[3] - b[1], 2)},
            "area_mm2": round(L.part_area(p.loops), 1),
            "cutouts": len(p.loops) - 1,
            "corners_relieved": p.relieved,
            "plane": p.plane,
            "assembly_group": p.group,
            "role": p.note,
            "geometry_status": "PARAMETRIC_DESIGN_CHOICE",
            "manufacturing_status": "UNTESTED_FIT",
        })
    return rows


def status_from(results, open_inputs):
    """Derive the product status; never upgrade without evidence."""
    failed = [r for r in results if not r[1]]
    if failed:
        return "CAD_COMPLETE_NOT_VALIDATED", "automated checks failed"
    blocking = [n for n, _ in open_inputs if n in ("CNC_BIT_DIAMETER", "MATERIAL_THICKNESS")]
    if blocking:
        return ("CAD_COMPLETE_NOT_VALIDATED",
                "all automated checks pass, but " + " and ".join(blocking) +
                " are unconfirmed and change the cut geometry")
    return "CNC_READY_PENDING_PHYSICAL_TEST", "checks pass; no physical test yet"


# --------------------------------------------------------------------------

def listing(parts, sheets):
    n = sum(p.qty for p in parts)
    return f"""PRODUCT TITLE
Lena Sofa - CNC Cut Files (3-seat, 18 mm MDF, slot-and-tab frame)

SHORT DESCRIPTION
A 3-seat sofa frame with four arched back cushions and round drum arms. Cuts from
{len(sheets)} sheets of 18 mm MDF and slots together with glue - no screws, no metal.

FULL DESCRIPTION
{n} CNC-cut pieces: 3 seat ribs with back posts, 4 back arches, 3 seat rails, 4 arm
panels with 6 drum spacers, and 2 seat decks. Every piece is numbered in assembly
order and engraved; the layout is nested for {len(sheets)} standard sheets. The assembly
order is checked in 3D. Parametric source included: change the size, board
thickness or cutter and regenerate every file.

WHAT'S INCLUDED
- Full nesting DXF ({len(sheets)} sheets) + one DXF per part (mm, 1:1, closed profiles)
- 3D model: STEP (exact solids), OBJ, STL
- Assembly guide (6 steps), parts list, dimensions and CNC notes (PDF)
- Renders: hero (upholstered), assembled frame, exploded view, layout
- Data: parameters.json, parts.json, validation.json

MATERIAL REQUIREMENTS
- {len(sheets)} x MDF sheet 2440 x 1220 x 18 mm (measure the real thickness)
- PVA D3 wood glue, frame staples
- Foam (seat 120-140 mm, back cushions, arm wrap 20-30 mm), fabric - not included

TOOLS REQUIRED
- CNC router with a 2440 x 1220 bed
- {C.JOINT.tool_d:.0f} mm flat end mill (dogbones are sized for it - see CNC notes)
- Staple gun, clamps

DIFFICULTY LEVEL
Intermediate (CNC setup + careful dry fit)

ASSEMBLY TIME ESTIMATE
ESTIMATED 2-3 h for the frame, excluding cutting and upholstery (not yet timed on a build)

DIMENSIONS
Frame {C.W:.0f} W x {C.D:.0f} D x {C.ARCH_TOP:.0f} H mm; arms {C.ARM_TOP + C.DRUM_R:.0f}; seat frame
{C.SEAT_TOP:.0f}; finished about 2260 x 900 x 850 mm, seat ~450 mm

LICENSE TERMS
[PLACEHOLDER - e.g. personal and commercial production of the furniture allowed;
redistribution or resale of the files prohibited]

CNC NOTES
See 03_DOCUMENTATION/cnc_notes.pdf.

IMPORTANT DISCLAIMERS
- This design has passed automated geometry, joint and 3D-assembly checks but has
  NOT yet been physically cut and assembled. Cut a test slot before the full job.
- Renders are visualisations; the upholstered image is an approximation.
- Check local furniture safety requirements before selling finished pieces.
"""


def main() -> None:
    parts, sheets = build.layout()
    if ROOT.exists():
        shutil.rmtree(ROOT)
    d = {k: ROOT / k for k in ("01_DXF", "02_3D", "03_DOCUMENTATION",
                               "04_PREVIEWS", "05_DATA")}
    for p in d.values():
        p.mkdir(parents=True)

    # 01 DXF
    build.write_dxf(parts, sheets, d["01_DXF"] / "full_nesting.dxf")
    part_dxfs(parts, d["01_DXF"] / "individual_parts")

    # 02 3D (built by export_step.py / render_blender.py export)
    for src, dst in (("lena-sofa.step", "product.step"), ("lena-sofa.stl", "product.stl"),
                     ("lena-sofa.obj", "product.obj"), ("lena-sofa.mtl", "product.mtl")):
        if (OUT / src).exists():
            shutil.copy(OUT / src, d["02_3D"] / dst)
    obj = d["02_3D"] / "product.obj"
    if obj.exists():
        obj.write_text(obj.read_text().replace("lena-sofa.mtl", "product.mtl"))

    # 04 previews
    for src, dst in (("lena-sofa-upholstered.png", "hero_render.png"),
                     ("lena-sofa-frame.png", "assembled_view.png"),
                     ("lena-sofa-exploded.png", "exploded_view.png"),
                     ("lena-sofa-sheets.png", "cnc_layout.png")):
        shutil.copy(OUT / src, d["04_PREVIEWS"] / dst)
    fig = dimension_figure(parts)
    fig.savefig(d["04_PREVIEWS"] / "dimension_view.png", dpi=120)
    plt.close(fig)

    # validation
    print("running validation ...")
    verify.RESULTS.clear()
    verify.FAIL.clear()
    verify.main()
    results = list(verify.RESULTS)
    verify_3d.RESULTS.clear()
    results += verify_3d.main()
    status, why = status_from(results, OPEN_INPUTS)

    # 03 documentation
    dimensions_pdf(parts, d["03_DOCUMENTATION"] / "dimensions.pdf")
    parts_list_pdf(parts, d["03_DOCUMENTATION"] / "parts_list.pdf")
    assembly_guide_pdf(parts, d["03_DOCUMENTATION"] / "assembly_guide.pdf", d["04_PREVIEWS"])
    cnc_notes_pdf(parts, sheets, results, d["03_DOCUMENTATION"] / "cnc_notes.pdf",
                  d["04_PREVIEWS"])

    # 05 data
    (d["05_DATA"] / "parameters.json").write_text(json.dumps(
        [{"name": n, "value": v, "unit": u, "status": s, "note": note}
         for n, v, u, s, note in PARAMETERS], indent=2))
    (d["05_DATA"] / "parts.json").write_text(json.dumps(parts_json(parts), indent=2))
    (d["05_DATA"] / "validation.json").write_text(json.dumps({
        "product": PRODUCT,
        "status": status,
        "status_reason": why,
        "physical_test": "NOT_PERFORMED",
        "fit": "UNTESTED_FIT",
        "checks_passed": sum(r[1] for r in results),
        "checks_failed": sum(not r[1] for r in results),
        "checks": [{"section": s, "passed": ok, "message": m} for s, ok, m in results],
        "open_inputs": [{"parameter": n, "question": q} for n, q in OPEN_INPUTS],
    }, indent=2))

    readme = f"""LENA SOFA - CNC DIGITAL PRODUCT PACKAGE
Generated {date.today()} from cnc/lena-sofa (parametric source).

PROJECT STATUS: {status}
  {why}
PHYSICAL TEST STATUS: NOT PERFORMED (fit untested)

FOLDERS
  01_DXF/             full_nesting.dxf ({len(sheets)} sheets) + individual_parts/ (one per part)
  02_3D/              product.step (exact solids), product.obj/.mtl, product.stl - mm
  03_DOCUMENTATION/   dimensions, parts_list, assembly_guide (6 steps), cnc_notes (PDF)
  04_PREVIEWS/        hero_render, assembled_view, exploded_view, dimension_view, cnc_layout
  05_DATA/            parameters.json (with provenance), parts.json, validation.json

OPEN INPUTS (needed before cutting)
""" + "\n".join(f"  - {n}: {q}" for n, q in OPEN_INPUTS) + "\n\n" + \
        "=" * 70 + "\nSALES LISTING (draft)\n" + "=" * 70 + "\n\n" + listing(parts, sheets)
    (ROOT / "README.txt").write_text(readme)
    print(f"\nPACKAGE {ROOT}\nSTATUS {status}: {why}")
    print(f"checks: {sum(r[1] for r in results)} passed, "
          f"{sum(not r[1] for r in results)} failed")


if __name__ == "__main__":
    main()
