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

Every piece is engraved with its part number, name and instance
(`01 RIB 3/7`), and the same number is circled on the PDF sheet pages and in
the bill of materials, so parts can be sorted straight off the bed.

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
| `ENGRAVE-LABEL` | part number + name + instance, placed on the part's own material (4 mm clear of any cut), rotated to fit curved parts |
| `REFERENCE-SHEET` | 2440 × 1220 sheet outlines and titles — not cut |

## Machining

All joint dimensions come from one line in `sofa_geometry.py`:

```python
JOINT = J.JointSpec(t=15.0, fit=0.4, tool_d=6.0)
```

- `t` — the **measured** sheet thickness (calipers, several spots). "15 mm"
  plywood is often 14.5–15.2 mm.
- `fit` — total clearance across a slot: slots are cut at `t + fit` (15.4 mm).
- `tool_d` — the cutter diameter. Every inside corner gets a relief circle of
  `tool_d/2 + 0.2` (R3.2) centred on the corner: closed slots **and** the open
  notches, tab roots and shoulders on the outlines, 62 corners in total.
  Without it a round bit leaves a fillet in each corner and the mating part
  stops short of seating.

Apply only the normal tool-radius offset on the contour; the relief is
already in the geometry. Test one slot on an offcut first, then adjust `t` or
`fit` and regenerate — `verify.py` re-checks everything.

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

- `joints.py` — `JointSpec` (thickness, fit, cutter) and inside-corner relief
- `labels.py` — part numbering and on-material engrave-label placement
- `sofa_geometry.py` — all dimensions and part profiles as named parameters
- `sofa_layout.py` — arc flattening, areas, and the sheet nesting
- `curved-sofa.dxf.py` — the `gen_dxf()` entry point the skill CLI builds
- `make_pdf.py` — the shop pack
- `verify.py` — topology, nesting, dimension and DXF checks
