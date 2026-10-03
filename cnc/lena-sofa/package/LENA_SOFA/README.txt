LENA SOFA - CNC DIGITAL PRODUCT PACKAGE
Generated 2026-10-01 from cnc/lena-sofa (parametric source).

PROJECT STATUS: CAD_COMPLETE_NOT_VALIDATED
  all automated checks pass, but CNC_BIT_DIAMETER and MATERIAL_THICKNESS are unconfirmed and change the cut geometry
PHYSICAL TEST STATUS: NOT PERFORMED (fit untested)

FOLDERS
  01_DXF/             full_nesting.dxf (4 sheets) + individual_parts/ (one per part)
  02_3D/              product.step (exact solids), product.obj/.mtl, product.stl - mm
  03_DOCUMENTATION/   dimensions, parts_list, assembly_guide (6 steps), cnc_notes (PDF)
  04_PREVIEWS/        hero_render, assembled_view, exploded_view, dimension_view, cnc_layout
  05_DATA/            parameters.json (with provenance), parts.json, validation.json

OPEN INPUTS (needed before cutting)
  - CNC_BIT_DIAMETER: What cutter diameter will cut this job? (dogbones assume 6 mm)
  - MATERIAL_THICKNESS: Caliper the real sheet in 3 places (nominal 18 mm).
  - SHEET_SIZE: Confirm the sheet size from your supplier (2440 x 1220 assumed).
  - OVERALL_DIMENSIONS: Confirm or change the frame 2200 x 860 x 800 mm, seat frame 330, arms 570 (finished about 226 x 90 x 85 cm, seat ~45 cm).

======================================================================
SALES LISTING (draft)
======================================================================

PRODUCT TITLE
Lena Sofa - CNC Cut Files (3-seat, 18 mm MDF, slot-and-tab frame)

SHORT DESCRIPTION
A 3-seat sofa frame with four arched back cushions and round drum arms. Cuts from
4 sheets of 18 mm MDF and slots together with glue - no screws, no metal.

FULL DESCRIPTION
22 CNC-cut pieces: 3 seat ribs with back posts, 4 back arches, 3 seat rails, 4 arm
panels with 6 drum spacers, and 2 seat decks. Every piece is numbered in assembly
order and engraved; the layout is nested for 4 standard sheets. The assembly
order is checked in 3D. Parametric source included: change the size, board
thickness or cutter and regenerate every file.

WHAT'S INCLUDED
- Full nesting DXF (4 sheets) + one DXF per part (mm, 1:1, closed profiles)
- 3D model: STEP (exact solids), OBJ, STL
- Assembly guide (6 steps), parts list, dimensions and CNC notes (PDF)
- Renders: hero (upholstered), assembled frame, exploded view, layout
- Data: parameters.json, parts.json, validation.json

MATERIAL REQUIREMENTS
- 4 x MDF sheet 2440 x 1220 x 18 mm (measure the real thickness)
- PVA D3 wood glue, frame staples
- Foam (seat 120-140 mm, back cushions, arm wrap 20-30 mm), fabric - not included

TOOLS REQUIRED
- CNC router with a 2440 x 1220 bed
- 6 mm flat end mill (dogbones are sized for it - see CNC notes)
- Staple gun, clamps

DIFFICULTY LEVEL
Intermediate (CNC setup + careful dry fit)

ASSEMBLY TIME ESTIMATE
ESTIMATED 2-3 h for the frame, excluding cutting and upholstery (not yet timed on a build)

DIMENSIONS
Frame 2200 W x 860 D x 800 H mm; arms 570; seat frame
330; finished about 2260 x 900 x 850 mm, seat ~450 mm

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
