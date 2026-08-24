# Curved 3-seat sofa — CNC cut file

A crescent (curved) 3-seat sofa frame for CNC routing from 15 mm plywood,
assembled entirely with slot-and-tab joints and glue — no fasteners.

Modelled from the reference animation: radial ribs + curved rails + a slatted
backrest lattice, upholstered afterwards.

## Deliverables

| File | What it is |
|---|---|
| `out/curved-sofa.dxf` | the cut file — 8 nested sheets stacked in −Y, mm, closed profiles |
| `out/curved-sofa-cutting-plan.pdf` | 12-page shop pack: spec + material consumption, plan + section, parts index, foam/fabric schedule, one page per sheet |
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
| Plinth | 45 mm, three laminated base-rail layers |
| Material | 15 mm plywood ×7 sheets + 4 mm flexible ply ×1 sheet (2440 × 1220) |
| Net part area / frame mass | 6.42 m² + 2.01 m² / ≈63 kg bare frame |
| Foam / fabric | ≈272 litres HR foam, ≈9 linear m of 140 cm fabric |

## Parts (40 pieces, 18 distinct)

**15 mm plywood**

- `RIB` ×5 — radial rib, plinth to seat with a back post to 730 mm
- `ARM-PANEL-IN` ×2 — closes the seat structure at ±23.5°, takes the rail end tabs
- `ARM-PANEL-OUT` ×2 — the ends of the sofa at ±30°
- `ARM-CAP` ×2 — horizontal arm top plate spanning both arm panels
- `RAIL-BASE-IN` ×3 / `RAIL-BASE-OUT` ×3 — laminated into the 45 mm plinth
- `RAIL-SEAT-IN` / `RAIL-SEAT-OUT` — curved seat rails in open top notches
- `RAIL-BACK-BOT` / `-MID` / `-TOP` — the three curved backrest rails
- `SEAT-DECK-1..3` — seat deck sectors, located by tabs on the rib tops
- `BACK-STILE` ×12 — lattice slats, threaded down through all three back rails

**4 mm flexible plywood** (developed cylinders — they bend onto the frame)

- `SKIN-BASE-OUT`, `SKIN-BASE-IN` — wrap the base
- `SKIN-BACK` — wraps the outer face of the backrest

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
