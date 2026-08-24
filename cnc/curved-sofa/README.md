# Curved 3-seat sofa — CNC cut file

A crescent (curved) 3-seat sofa frame for CNC routing from 15 mm plywood,
assembled entirely with slot-and-tab joints and glue — no fasteners.

Modelled from the reference animation: radial ribs + curved rails + a slatted
backrest lattice, upholstered afterwards.

## Deliverables

| File | What it is |
|---|---|
| `out/curved-sofa.dxf` | the cut file — 6 nested sheets, mm, closed profiles |
| `out/curved-sofa-cutting-plan.pdf` | 8-page shop pack: spec, BOM, plan + section, one page per sheet |
| `out/curved-sofa-preview.png` | 3D flat-pattern preview rendered from the DXF |

## Key dimensions

| | |
|---|---|
| Overall width (chord of the back) | 2200 mm |
| Overall depth over the crescent | 1074 mm |
| Radial depth of the seating band | 900 mm |
| Plan sweep / back radius | 60° / R2200 mm |
| Seat frame height | 345 mm (≈445 mm with a 100 mm cushion) |
| Backrest height | 760 mm |
| Arm height | 620 mm |
| Material | 15 mm plywood, 2440 × 1220 sheets — 6 sheets |
| Net part area / frame mass | 5.82 m² / ≈52 kg |

## Parts (33 total)

- `RIB` ×7 — radial rib, floor to seat with a back post to 760 mm
- `ARM-PANEL` ×2 — end panels, slide on tangentially over the rail end tabs
- `RAIL-BASE-IN` / `RAIL-BASE-OUT` — curved floor rails, the ribs drop onto them
- `RAIL-SEAT-IN` / `RAIL-SEAT-OUT` — curved seat rails in open top notches
- `RAIL-BACK-BOT` / `-MID` / `-TOP` — the three curved backrest rails
- `SEAT-DECK-1..3` — seat deck sectors, located by tabs on the rib tops
- `BACK-STILE` ×14 — lattice slats, threaded down through all three back rails

## Layers

| Layer | Contents |
|---|---|
| `CUT` | every cut contour — outer profiles, slots, lightening holes (all closed) |
| `ENGRAVE-LABEL` | part identification text |
| `REFERENCE-SHEET` | 2440 × 1220 sheet outlines and titles — not cut |

## Machining

Slots are cut at 15.4 mm for 15.0 mm plate and carry dogbone corner relief
(R3.2, sized for a 6 mm cutter) already in the geometry — apply only the normal
tool-radius offset on the contour, no extra compensation inside the slots.
Test one slot on an offcut first; if the sheet measures under 14.6 mm, change
`FIT` in `sofa_geometry.py` and regenerate.

## Regenerating

```bash
python -m venv .venv && .venv/bin/pip install ezdxf shapely matplotlib
.venv/bin/python curved-sofa.dxf.py          # writes out/curved-sofa.dxf
.venv/bin/python make_pdf.py                 # writes out/curved-sofa-cutting-plan.pdf
.venv/bin/python verify.py                   # deterministic geometry checks
```

Through the `text-to-cad` DXF skill:

```bash
python <dxf-skill>/scripts/gen curved-sofa.dxf.py=out/curved-sofa.dxf
python <dxf-skill>/scripts/gen --validate out/curved-sofa.dxf
```

## Source layout

- `sofa_geometry.py` — all dimensions and part profiles as named parameters
- `sofa_layout.py` — arc flattening, areas, and the sheet nesting
- `curved-sofa.dxf.py` — the `gen_dxf()` entry point the skill CLI builds
- `make_pdf.py` — the shop pack
- `verify.py` — topology, nesting, dimension and DXF checks
