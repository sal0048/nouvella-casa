CURL LOUNGE CHAIR - CNC DIGITAL PRODUCT PACKAGE
Generated 2026-09-29 from cnc/curl-chair (parametric source).

PROJECT STATUS: CAD_COMPLETE_NOT_VALIDATED
  all automated checks pass, but CNC_BIT_DIAMETER and MATERIAL_THICKNESS are unconfirmed and change the cut geometry
PHYSICAL TEST STATUS: NOT PERFORMED (fit untested)

FOLDERS
  01_DXF/             full_nesting.dxf (2 sheets) + individual_parts/ (one per part)
  02_3D/              product.step (exact solids), product.obj/.mtl, product.stl - mm
  03_DOCUMENTATION/   dimensions, parts_list, assembly_guide, cnc_notes (PDF)
  04_PREVIEWS/        hero_render, assembled_view, exploded_view, dimension_view, cnc_layout
  05_DATA/            parameters.json (with provenance), parts.json, validation.json

OPEN INPUTS (needed before cutting)
  - CNC_BIT_DIAMETER: What cutter diameter will cut this job? (dogbones assume 6 mm)
  - MATERIAL_THICKNESS: Caliper the real sheet in 3 places (nominal 18 mm).
  - SHEET_SIZE: Confirm the sheet size from your supplier (2440 x 1220 assumed).
  - OVERALL_DIMENSIONS: Confirm or change the frame 980 x 880 x 530 mm, seat frame 270 (finished 100 x 90 x 63 cm with foam and 4 cm legs).

======================================================================
SALES LISTING (draft)
======================================================================

PRODUCT TITLE
Curl Lounge Chair - CNC Cut Files (18 mm MDF, slot-and-tab frame)

SHORT DESCRIPTION
A low lounge chair frame whose back rolls around the back and one side, open on
the other. Cuts from 2 sheets of 18 mm MDF and slots together with glue - no
screws, no metal. Upholster it in boucle or velvet.

FULL DESCRIPTION
38 CNC-cut pieces build a rounded frame: a floor ring, 20 bulging body ribs, a seat
ring, 13 back ribs and 3 locking bands. Every piece is numbered and
engraved; the layout is nested for 2 standard sheets. Parametric source
included: change the size, board thickness or cutter and regenerate every file.

WHAT'S INCLUDED
- Full nesting DXF (2 sheets) + one DXF per part (mm, 1:1, closed profiles)
- 3D model: STEP (exact solids), OBJ, STL
- Assembly guide, parts list, dimensions and CNC notes (PDF)
- Renders: hero (upholstered), assembled frame, exploded view, layout
- Data: parameters.json, parts.json, validation.json

MATERIAL REQUIREMENTS
- 2 x MDF sheet 2440 x 1220 x 18 mm (measure the real thickness)
- PVA D3 wood glue, frame staples
- Elastic webbing, foam (seat 120-160 mm, back 50-70 mm, wrap 10-30 mm), fabric, 40 mm legs - not included in the files

TOOLS REQUIRED
- CNC router with a 2440 x 1220 bed
- 6 mm flat end mill (dogbones are sized for it - see CNC notes)
- Staple gun, clamps

DIFFICULTY LEVEL
Intermediate (CNC setup + careful dry fit)

ASSEMBLY TIME ESTIMATE
ESTIMATED 2-3 h for the frame, excluding cutting and upholstery (not yet timed on a build)

DIMENSIONS
980 W x 880 D x 530 H mm; arms 440; seat frame
270; finished about 1000 x 900 x 630 mm with foam and 40 mm legs

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
