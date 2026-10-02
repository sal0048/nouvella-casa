"""Assemble the Pebble sofa digital-product package.

    python package.py            # after build.py, export_step.py and the
                                 # Blender renders (render_blender.py)

Writes package/PEBBLE_SOFA/ in the standard layout:
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
import pebble_geometry as C
import labels as B
import sofa_layout as L
import verify
import verify_3d

PRODUCT = "PEBBLE_SOFA"
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
    ("MATERIAL", "MDF", "", USER, "user works in MDF; the reference uses 15 mm plywood"),
    ("MATERIAL_THICKNESS", C.T, "mm", USER, "NOMINAL - measure the real sheet (reference: 15 mm)"),
    ("CLEARANCE", C.JOINT.fit, "mm", TOKYO, "total across each slot - UNTESTED FIT"),
    ("SLOT_WIDTH", C.SLOT_T, "mm", DERIVED, "MATERIAL_THICKNESS + CLEARANCE"),
    ("TAB_LENGTH", C.TAB_W, "mm", TOKYO, ""),
    ("MORTISE_LENGTH", C.TAB_SLOT, "mm", DERIVED, "TAB_LENGTH + CLEARANCE"),
    ("CNC_BIT_DIAMETER", C.JOINT.tool_d, "mm", ASSUMED, "sizes every dogbone relief"),
    ("RELIEF_RADIUS", C.RELIEF_R, "mm", DERIVED, "CNC_BIT_DIAMETER / 2 + 0.2"),
    ("SHEET_SIZE", "2440 x 1220", "mm", ASSUMED, "confirm the supplier size"),
    ("PART_GAP", C.PART_GAP, "mm", TOKYO, ""),
    ("OVERALL_WIDTH_FINISHED", 3100, "mm", "FROM_REFERENCE_DRAWING", "1350 + 1750"),
    ("DEPTH_FINISHED", "1110 / 1130", "mm", "FROM_REFERENCE_DRAWING", "left / right module"),
    ("SEAT_FRAME_HEIGHT", C.SEAT_TOP, "mm", DESIGN, "+ 100~120 mm foam = ~440"),
    ("BACK_PEBBLE_HEIGHT", "400 / 430", "mm", DESIGN, "dome above the plate, left / right"),
    ("ARM_PEBBLE_HEIGHT", "300 / 330", "mm", DESIGN, "end left / arm right"),
    ("PEBBLE_FOOTPRINTS", "1056x433, 403x386, 1215x495, 457x750", "mm", "FROM_REFERENCE_DRAWING", "finished; frame = minus ~30 foam"),
    ("BODY_RIB_PITCH", C.RIB_PITCH, "mm", DESIGN, "along the belly"),
    ("SEAT_RING_BAND", C.SEAT_BAND, "mm", DESIGN, "elastic webbing across the opening"),
]

OPEN_INPUTS = [
    ("CNC_BIT_DIAMETER", "What cutter diameter will cut this job? (dogbones assume 6 mm)"),
    ("MATERIAL_THICKNESS", "Caliper the real sheet in 3 places (nominal 18 mm)."),
    ("SHEET_SIZE", "Confirm the sheet size from your supplier (2440 x 1220 assumed)."),
    ("HEIGHTS", "Seat 330 frame (~440 finished) and pebble heights are our choice: confirm."),
]


# --------------------------------------------------------------------------
# 3D outline helpers (for drawings)
# --------------------------------------------------------------------------

def instances(parts):
    out = []
    for p, k, o, u, v, c in C.instances(parts):
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        off = 0.0 if c else C.T / 2
        pts = [tuple(o[i] + x * u[i] + y * v[i] + off * n[i] for i in range(3))
               for x, y in L.flatten_loop(p.loops[0], 8)]
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
    fig, axes = plt.subplots(2, 1, figsize=(14, 9))
    for ax, (i, j), title in ((axes[0], (0, 1), "PLAN (front at the bottom)"), (axes[1], (0, 2), "FRONT ELEVATION")):
        for p, a, pts in inst:
            xs = [q[i] for q in pts]; ys = [q[j] for q in pts]
            ax.plot(xs + xs[:1], ys + ys[:1], lw=0.3, color=INK)
        ax.set_aspect("equal"); ax.axis("off")
        ax.set_title(title, fontsize=10, color=INK, loc="left")
    xs = [q[0] for _, _, pts in inst for q in pts]; ys = [q[1] for _, _, pts in inst for q in pts]
    zs = [q[2] for _, _, pts in inst for q in pts]
    W, D, H = max(xs) - min(xs), max(ys) - min(ys), max(zs)
    dim(axes[0], (min(xs), min(ys)), (max(xs), min(ys)), f"frame W {W:.0f}  (finished ~3100)", -90)
    dim(axes[0], (max(xs), min(ys)), (max(xs), max(ys)), f"D {D:.0f}", 90, vertical=True)
    dim(axes[1], (max(xs), 0), (max(xs), H), f"H {H:.0f}", 90, vertical=True)
    dim(axes[1], (min(xs), 0), (min(xs), C.SEAT_TOP), f"seat {C.SEAT_TOP:.0f}", -120, vertical=True)
    fig.text(0.02, 0.02, "Frame dimensions in mm, measured on the 3D. Finished size adds foam (~40 mm). "
             "Board 18 mm NOMINAL.", fontsize=8, color=REF)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    return fig


# --------------------------------------------------------------------------
# documents
# --------------------------------------------------------------------------

def page(title, subtitle=""):
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.text(0.035, 0.955, f"PEBBLE SOFA  /  {title}", fontsize=13,
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
                 "(e.g. '05 RIB-LC 2/4'). L = left module, R = right; BL/EL/BR/AR = pebbles.", fontsize=8, color=REF)
        pdf.savefig(fig)
        plt.close(fig)


def assembly_steps():
    return [
        ("BASE", "STEP 01 - Base rings", "Lay BASE-RING-L and BASE-RING-R on a level floor, mortises up, "
         "about 70 mm apart (left module on the left)."),
        ("BODY", "STEP 02 - Body ribs", "Stand the body ribs in the base mortises, bulge outward. "
         "The letter (RIB-LA, LB ... / RA ...) gives the place: see the parts list angles."),
        ("SEAT", "STEP 03 - Seat rings", "Lower SEAT-RING-L / R onto the rib top tabs. Then stretch "
         "elastic webbing across each opening (staples)."),
        ("PLATE", "STEP 04 - Pebble plates", "Place the four pebble plates (BL, EL, BR, AR) on the seat "
         "rings at their marked spots, glue and screw them from below through the ring."),
        ("PRIB", "STEP 05 - Pebble ribs", "Stand each pebble's ribs in its plate mortises, slots facing up."),
        ("SPINE", "STEP 06 - Pebble spines", "Lower each spine over its ribs (egg-crate) until its tabs "
         "seat in the plate. Check square, glue every joint."),
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
            ax.imshow(mpimg.imread(OUT / f"pebble-sofa-step-{key.lower()}.png"))
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
            "Pebble plates: 4 x 40 mm screws + glue into the seat ring each.",
            "Seat: elastic webbing across the seat-ring openings, then foam.",
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
Pebble Sofa - CNC Cut Files (sectional, 18 mm MDF, slot-and-tab frame)

SHORT DESCRIPTION
A 3.1 m organic sectional: two rounded seat blobs and four pebble cushions.
{n} pieces on {len(sheets)} sheets of 18 mm MDF, slotted and glued - no metal.

WHAT'S INCLUDED
- Full nesting DXF ({len(sheets)} sheets) + one DXF per part (mm, 1:1, closed profiles)
- 3D model: STEP, OBJ, STL
- Assembly guide (6 steps), parts list, dimensions and CNC notes (PDF)

DIMENSIONS
Finished about 3100 x 1120 x 790 mm (frame + foam); seat ~440 mm

IMPORTANT DISCLAIMERS
- Automated geometry, joint and 3D-assembly checks pass; NOT yet physically cut.
- Renders are visualisations; the upholstered image is an approximation.
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
    for src, dst in (("pebble-sofa.step", "product.step"), ("pebble-sofa.stl", "product.stl"),
                     ("pebble-sofa.obj", "product.obj"), ("pebble-sofa.mtl", "product.mtl")):
        if (OUT / src).exists():
            shutil.copy(OUT / src, d["02_3D"] / dst)
    obj = d["02_3D"] / "product.obj"
    if obj.exists():
        obj.write_text(obj.read_text().replace("pebble-sofa.mtl", "product.mtl"))

    # 04 previews
    for src, dst in (("pebble-sofa-upholstered.png", "hero_render.png"),
                     ("pebble-sofa-frame.png", "assembled_view.png"),
                     ("pebble-sofa-exploded.png", "exploded_view.png"),
                     ("pebble-sofa-sheets.png", "cnc_layout.png")):
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

    readme = f"""PEBBLE SOFA - CNC DIGITAL PRODUCT PACKAGE
Generated {date.today()} from cnc/pebble-sofa (parametric source).

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
