"""Per-product data for make_sheets.py. Every number is read from the product's
own cut files, geometry module or package data, and asserted against what the
3D checks measured, so a stale file stops the sheets instead of printing a
wrong number.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import ezdxf

ROOT = Path(__file__).resolve().parents[2]
CNC = ROOT / "cnc"


def cm(x):
    return f"{x:g}"


def outer_count(path, layer="CUT"):
    """Number of parts in a DXF. A CUT loop inside an even number of other loops is a
    part outline, inside an odd number it is a hole; parts nested in another part's
    opening (small ribs inside a ring) are therefore still counted as parts."""
    sys.path.insert(0, str(CNC / "cone-table"))
    import audit_dxf as A
    from shapely.geometry import Polygon
    polys = [Polygon(A.loop_points(e, seg=3.0)) for e in ezdxf.readfile(path).modelspace()
             if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == layer]
    depth = [sum(q is not p and q.area > p.area and q.contains(p.representative_point()) for q in polys)
             for p in polys]
    return sum(d % 2 == 0 for d in depth)


# --------------------------------------------------------------------- cone
def cone():
    d = CNC / "cone-table"
    sys.path.insert(0, str(d))
    import table_geometry as T
    cut1, cut2 = d / "out" / "CONE_18MM_CUT.dxf", d / "out" / "CONE_18MM_CUT_x2.dxf"
    n1 = Counter(e.dxf.layer for e in ezdxf.readfile(cut1).modelspace())
    n2 = Counter(e.dxf.layer for e in ezdxf.readfile(cut2).modelspace())
    pocket = next(l for l in n1 if l.startswith("POCKET"))
    parts = sorted((p.stem.split("_")[0], p.stem.split("_")[1])
                   for p in (d / "out" / "parts").glob("P*_x1.dxf") if "BEND-TEST" not in p.stem)
    base, top, h = 2 * T.R(0) / 10, 2 * T.R(T.H_CONE) / 10, T.H_CONE / 10
    per_board = round(n2["CUT"] / n1["CUT"])
    board, skin, kerfs, cuts = T.T_BOARD, T.SKIN, n1[pocket], n1["CUT"]
    assert (base, top, h, per_board, len(parts), board) == (40, 16, 45, 2, 9, 18), \
        (base, top, h, per_board, len(parts))
    names = {"SHELL": "Shell (kerfed)", "FORMER-BASE": "Former base", "FORMER-JOINT-LO": "Former joint low",
             "FORMER-JOINT-UP": "Former joint up", "FORMER-TOP": "Former top (top)",
             "CORE-1A": "Core 1A", "CORE-1B": "Core 1B", "CORE-2A": "Core 2A", "CORE-2B": "Core 2B"}
    return dict(
        slug="cone-table", name="Cone", kind="Table", ren=d / "out" / "sheets",
        views=dict(finished="finished", skeleton="skeleton", cutaway="cutaway",
                   exploded="exploded", top="top"),
        board_mm=board, sheet=(T.SHEET_H / 10, T.SHEET_W / 10),
        dims=[f"Base : Ø {cm(base)} cm", f"Top : Ø {cm(top)} cm", f"H : {cm(h)} cm"],
        mat=[f"MDF : {board:g} mm", f"{cm(T.SHEET_H / 10)}x{cm(T.SHEET_W / 10)}  CM"],
        cover_line=f"MDF {board:g} mm · Ø{cm(base)} × H{cm(h)} cm",
        bullets=["Ready-to-cut DXF for CNC", f"{per_board} tables from one board",
                 "No mould, no steam bending"],
        p_main=(f"A sculpted cone table cut from flat {board:g} mm MDF. The shell bends around "
                f"CNC-cut formers thanks to {kerfs} calculated kerf pockets, no mould and no steam."),
        p_joint=("Core halves slot into four round formers. Tab and mortise joints lock the "
                 "skeleton square before the shell goes on."),
        p_file=(f"{cuts} cut contours, {len(parts)} parts, one board. Nested, layered and checked: "
                f"every kerf depth leaves a {skin:g} mm skin on {board:g} mm board."),
        board_lines=[f"available  {cm(T.SHEET_H / 10)} x{cm(T.SHEET_W / 10)} cm - {board / 10:g} cm",
                     f"{per_board} tables per board"],
        files=["1- 2D/DXF file For CNC (1 table / board).",
               f"2- 2D/DXF file For CNC ({per_board} tables / board).",
               "3- STL-STEP files FOR VIEW.", "4- Assembly animation (MP4)."],
        nests=[(cut1, 0, "x1"), (cut2, 0, f"x{per_board}")],
        parts=[(num, names[p], 1) for num, p in parts],
        parts_line=f"{len(parts)} parts · {cuts} contours",
        # A1 callouts: (text, text xy, which render, target as a fraction of its box, bend)
        callouts=[(f"MDF {board:g} mm", (340, 170), "sk", (0.42, 0.05), 0.25, "right"),
                  ("4 round formers", (935, 935), "sk", (0.80, 0.47), -0.2, "left"),
                  (f"Kerf skin\n{skin:g} mm", (300, 1080), "fi", (0.38, 0.45), -0.3, "below"),
                  (f"{kerfs} kerf pockets", (380, 1950), "fi", (0.62, 0.72), 0.3, "top")],
    )


# ------------------------------------------------------------ round armchair
def armchair():
    d = CNC / "round-armchair"
    pk = d / "package" / "ROUND_TUB_ARMCHAIR"
    params = {p["name"]: p["value"] for p in json.loads((pk / "05_DATA" / "parameters.json").read_text())}
    parts = json.loads((pk / "05_DATA" / "parts.json").read_text())
    nest = pk / "01_DXF" / "full_nesting.dxf"
    lay = Counter(e.dxf.layer for e in ezdxf.readfile(nest).modelspace() if e.dxftype() == "LWPOLYLINE")
    boards = lay["REFERENCE-SHEET"]
    pieces = sum(p["quantity"] for p in parts)
    w, dp, h = params["WIDTH"] / 10, params["DEPTH"] / 10, params["HEIGHT"] / 10
    arm, seat = params["ARM_HEIGHT"] / 10, params["SEAT_FRAME_HEIGHT"] / 10
    board = params["MATERIAL_THICKNESS"]
    ribs = sum(p["quantity"] for p in parts if p["name"].startswith("BODY-RIB"))
    back = sum(p["quantity"] for p in parts if p["name"].startswith("BACK-RIB"))
    bands = sum(p["quantity"] for p in parts if p["name"].startswith("BACK-BAND"))
    # what the file actually holds must match the data sheet
    assert outer_count(nest) == pieces == 38 and boards == 2 and len(parts) == 17, \
        (outer_count(nest), pieces, boards)
    assert (w, dp, h, board, ribs, back, bands) == (95, 92, 80, 18, 20, 13, 3)
    sheet = tuple(float(v) / 10 for v in params["SHEET_SIZE"].split(" x "))[::-1]
    return dict(
        slug="round-armchair", name="Tub", kind="Armchair", ren=d / "out" / "sheets",
        views=dict(finished="upholstered", skeleton="frame", cutaway="frame-back",
                   exploded="exploded", top="top"),
        board_mm=board, sheet=sheet,
        dims=[f"W : {cm(w)} cm", f"D : {cm(dp)} cm", f"H : {cm(h)} cm", f"Arms : {cm(arm)} cm",
              f"Seat frame : {cm(seat)} cm"],
        mat=[f"MDF : {board:g} mm", f"{cm(sheet[0])}x{cm(sheet[1])}  CM  x{boards}"],
        cover_line=f"MDF {board:g} mm · {cm(w)} × {cm(dp)} × H{cm(h)} cm",
        bullets=["Ready-to-cut DXF for CNC", f"{pieces} parts on {boards} boards",
                 "Slot & tab, no screws"],
        p_main=(f"A round tub lounge chair framed in {board:g} mm MDF. {ribs} bulging body ribs "
                f"between two rings give the soft round belly; {back} back and arm ribs rise "
                f"from the seat ring."),
        p_joint=(f"Ribs drop into the ring mortises and {bands} back bands lock their spacing "
                 f"from above. Glue every joint: no screws, no metal."),
        p_file=(f"{pieces} parts, {len(parts)} shapes, {boards} boards. Every piece is engraved "
                f"with its number, so parts sort straight off the bed."),
        board_lines=[f"available  {cm(sheet[0])} x{cm(sheet[1])} cm - {board / 10:g} cm",
                     f"{boards} boards per chair"],
        files=[f"1- 2D/DXF file For CNC ({boards} boards).",
               f"2- One DXF per part ({len(parts)} files).",
               "3- STEP-OBJ-STL files FOR VIEW.", "4- PDF: assembly, parts, dimensions."],
        nests=[(nest, 0, "1"), (nest, 1, "2")],
        parts=[(p["part_id"], p["name"].replace("-", " ").title().replace("Rib", "rib")
                .replace("Ring", "ring").replace("Band", "band"), p["quantity"]) for p in parts],
        parts_line=f"{pieces} parts · {len(parts)} shapes",
        callouts=[(f"MDF {board:g} mm", (340, 170), "sk", (0.50, 0.08), 0.25, "right"),
                  (f"{ribs} body ribs", (1110, 980), "sk", (0.70, 0.78), -0.2, "left"),
                  ("Foam seat\n10~12.5 cm", (300, 1080), "fi", (0.42, 0.42), -0.3, "below"),
                  (f"{back} back ribs", (380, 1950), "fi", (0.66, 0.30), 0.3, "top")],
    )


def curl():
    d = CNC / "curl-chair"
    pk = d / "package" / "CURL_LOUNGE_CHAIR"
    params = {p["name"]: p["value"] for p in json.loads((pk / "05_DATA" / "parameters.json").read_text())}
    parts = json.loads((pk / "05_DATA" / "parts.json").read_text())
    nest1, nest2 = pk / "01_DXF" / "full_nesting.dxf", pk / "01_DXF" / "full_nesting_x2.dxf"
    boards = sum(1 for e in ezdxf.readfile(nest1).modelspace()
                 if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "REFERENCE-SHEET")
    boards2 = sum(1 for e in ezdxf.readfile(nest2).modelspace()
                  if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "REFERENCE-SHEET")
    pieces = sum(p["quantity"] for p in parts)
    board = params["MATERIAL_THICKNESS"]
    ribs = sum(p["quantity"] for p in parts if p["name"].startswith("BODY-RIB"))
    back = sum(p["quantity"] for p in parts if p["name"].startswith("BACK-RIB"))
    bands = sum(p["quantity"] for p in parts if p["name"].startswith("BACK-BAND"))
    assert outer_count(nest1) == pieces == 38 and outer_count(nest2) == 76, (outer_count(nest1), pieces)
    assert (boards, boards2, board, ribs, back, bands, len(parts)) == (2, 3, 18, 20, 13, 3, 19)
    # finished size = frame + foam + 4 cm legs (the Alba reference size)
    assert (params["WIDTH"], params["DEPTH"], params["HEIGHT"], params["SEAT_FRAME_HEIGHT"]) == \
        (980, 880, 530, 270), params
    sheet = tuple(float(v) / 10 for v in params["SHEET_SIZE"].split(" x "))[::-1]
    return dict(
        slug="curl-chair", name="Curl", kind="Lounge chair", ren=d / "out" / "sheets",
        views=dict(finished="upholstered", skeleton="frame", cutaway="frame-back",
                   exploded="exploded", top="top", step1="step-base", step2="step-body",
                   step3="step-seat", step4="step-back", step5="step-band"),
        board_mm=board, sheet=sheet,
        # assembly order = render_blender.STEP_ORDER; the new layer of each step is terracotta
        steps=[("step1", "Base ring", "P01 flat on a level floor, mortises facing up.", "x1"),
               ("step2", "Body ribs", f"P03-P07 into the base mortises, bulge outward. The "
                f"letter A-E on each rib gives its place (parts list).", f"x{ribs}"),
               ("step3", "Seat ring", f"P02 down onto the rib tabs, all round. The {back} outer "
                f"mortises face up.", "x1"),
               ("step4", "Back ribs", "P08-P16 into the outer mortises. A and B are the low open "
                "ends, I sits at the centre of the back.", f"x{back}"),
               ("step5", "Back bands", "P17-P19 over the rib tops onto the 10 mm shoulders. "
                "Check it is square, then glue (PVA D3) and staple.", f"x{bands}"),
               ("skeleton", "Frame ready", "98 x 88 x 53 cm. Now foam, fabric and 4 cm legs.",
                "")],
        # finished (frame + foam + legs) and the frame itself as verify_3d measures it
        dims=["W : 100 cm", "D : 90 cm", "H : 63 cm", "Frame : 98 x 88 x 53 cm", "Legs : 4 cm"],
        mat=[f"MDF : {board:g} mm", f"{cm(sheet[0])}x{cm(sheet[1])}  CM"],
        cover_line=f"MDF {board:g} mm · 100 × 90 × H63 cm",
        bullets=["Ready-to-cut DXF for CNC", f"2 chairs from {boards2} boards",
                 "Slot & tab, no screws"],
        p_main=(f"A low lounge chair whose back rolls around the back and one side. {ribs} bulging "
                f"body ribs shape the round seat block; {back} back ribs carry the roll and ease "
                f"down at both open ends."),
        p_joint=(f"Ribs drop into the ring mortises and {bands} back bands lock their spacing "
                 f"from above. Glue every joint: no screws, no metal."),
        p_file=(f"{pieces} parts, {len(parts)} shapes. One chair on {boards} boards, two chairs on "
                f"{boards2}. Every piece is engraved with its number."),
        board_lines=[f"available  {cm(sheet[0])} x{cm(sheet[1])} cm - {board / 10:g} cm",
                     f"2 chairs from {boards2} boards"],
        files=[f"1- 2D/DXF file For CNC (1 chair, {boards} boards).",
               f"2- 2D/DXF file For CNC (2 chairs, {boards2} boards).",
               "3- STEP-OBJ-STL files FOR VIEW.", "4- PDF: assembly, parts, dimensions."],
        nests=[(nest2, 0, "1"), (nest2, 1, "2"), (nest2, 2, "3")],
        parts=[(p["part_id"], p["name"].replace("-", " ").title().replace("Rib", "rib")
                .replace("Ring", "ring").replace("Band", "band"), p["quantity"]) for p in parts],
        parts_line=f"{pieces} parts · {len(parts)} shapes",
        callouts=[(f"MDF {board:g} mm", (340, 170), "sk", (0.50, 0.10), 0.25, "right"),
                  (f"{ribs} body ribs", (1110, 980), "sk", (0.72, 0.80), -0.2, "left"),
                  ("Foam seat\n12~16 cm", (300, 1080), "fi", (0.40, 0.40), -0.3, "below"),
                  ("Foam back 5~7 cm", (380, 1950), "fi", (0.70, 0.22), 0.3, "top")],
    )


def lena():
    d = CNC / "lena-sofa"
    pk = d / "package" / "LENA_SOFA"
    params = {p["name"]: p["value"] for p in json.loads((pk / "05_DATA" / "parameters.json").read_text())}
    parts = json.loads((pk / "05_DATA" / "parts.json").read_text())
    nest1 = pk / "01_DXF" / "full_nesting.dxf"
    boards = sum(1 for e in ezdxf.readfile(nest1).modelspace()
                 if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "REFERENCE-SHEET")
    pieces = sum(p["quantity"] for p in parts)
    board = params["MATERIAL_THICKNESS"]
    q = {p["name"]: p["quantity"] for p in parts}
    arches, spacers = q["BACK-ARCH"], q["ARM-SPACER"]
    ribs = q["RIB-A"] + q["RIB-B"]
    assert outer_count(nest1) == pieces == 22, (outer_count(nest1), pieces)
    assert (boards, board, ribs, arches, spacers, len(parts)) == (4, 18, 3, 4, 6, 11)
    assert (params["WIDTH"], params["DEPTH"], params["HEIGHT"], params["SEAT_FRAME_HEIGHT"],
            params["ARM_HEIGHT"]) == (2200, 860, 800, 330, 570), params
    sheet = tuple(float(v) / 10 for v in params["SHEET_SIZE"].split(" x "))[::-1]
    return dict(
        slug="lena-sofa", name="Lena", kind="Sofa", ren=d / "out" / "sheets",
        views=dict(finished="upholstered", skeleton="frame", cutaway="frame-back",
                   exploded="exploded", top="top", step1="step-back", step2="step-rails",
                   step3="step-inner", step4="step-spacers", step5="step-outer",
                   step6="step-deck"),
        board_mm=board, sheet=sheet,
        # assembly order = lena_geometry.GROUP_ORDER, checked in 3D by verify_3d.py
        steps=[("step1", "Back chain", "P01-P03: ribs and arches slide together. Two arches "
                "tab into every post.", f"x{ribs + arches}"),
               ("step2", "Seat rails", "P04-P06 drop into the slots on the rib tops, "
                "flush with them.", "x3"),
               ("step3", "Inner arms", "P07 left and P08 right slide onto the rail and arch "
                "tabs.", "x2"),
               ("step4", "Arm spacers", "P09 into the inner panels, round cap up, resting on "
                "the panel edge.", f"x{spacers}"),
               ("step5", "Outer arms", "P10 onto the spacers' free tabs. The arms are closed "
                "boxes.", "x2"),
               ("step6", "Seat decks", "P11 onto the rib tabs. Check it is square, then glue "
                "and staple.", "x2")],
        dims=["W : 226 cm", "D : 90 cm", "H : 85 cm", "Seat : 45 cm",
              "Frame : 220x86x80"],
        mat=[f"MDF : {board:g} mm", f"{cm(sheet[0])}x{cm(sheet[1])}  CM"],
        cover_line=f"MDF {board:g} mm · 226 × 90 × H85 cm",
        bullets=["Ready-to-cut DXF for CNC", f"One sofa from {boards} boards",
                 "Slot & tab, no screws"],
        p_main=(f"A 3-seat sofa with {arches} arched back cushions and round drum arms. "
                f"{ribs} seat ribs carry the back posts; the {arches} arches tab into them "
                f"and give the Lena silhouette."),
        p_joint=(f"Rails halve into the ribs, the arms slide onto the rail tabs, {spacers} "
                 f"spacers close the drums. Glue every joint: no screws, no metal."),
        p_file=(f"{pieces} parts, {len(parts)} shapes, on {boards} boards. Every piece is "
                f"engraved with its number in assembly order."),
        board_lines=[f"available  {cm(sheet[0])} x{cm(sheet[1])} cm - {board / 10:g} cm",
                     f"1 sofa from {boards} boards"],
        files=[f"1- 2D/DXF file For CNC ({boards} boards).",
               "2- One DXF per part (11 shapes).",
               "3- STEP-OBJ-STL files FOR VIEW.", "4- PDF: assembly, parts, dimensions."],
        nests=[(nest1, k, str(k + 1)) for k in range(boards)],
        parts=[(p["part_id"], p["name"].replace("-", " ").title().replace("Inner L", "inner L")
                .replace("Inner R", "inner R"), p["quantity"]) for p in parts],
        parts_line=f"{pieces} parts · {len(parts)} shapes",
        callouts=[(f"MDF {board:g} mm", (330, 200), "sk", (0.42, 0.20), 0.25, "right"),
                  (f"{arches} back arches", (300, 900), "sk", (0.40, 0.10), 0.3, "top"),
                  ("Foam seat\n12~14 cm", (300, 1130), "fi", (0.45, 0.55), -0.3, "below"),
                  ("Drum arms", (1150, 1930), "fi", (0.88, 0.62), 0.3, "top")],
    )


PRODUCTS = {"cone-table": cone, "round-armchair": armchair, "curl-chair": curl,
            "lena-sofa": lena}
