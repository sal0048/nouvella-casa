# Kerf-bent cone with structural core

Our own parametric model of the kerf-bent cone technique from the workshop
video: Ø400 at the floor, Ø160 at the top, 450 high, MDF 18 throughout.
One kerfed shell wraps a structural core; two cones per 2440 x 1220 sheet.

```
python3 build.py              # out/CONE_18MM_CUT.dxf (clean) + labelled + out/parts/
python3 build.py --sets 2     # out/CONE_18MM_CUT_x2.dxf: two cones, one sheet
python3 verify.py             # deterministic checks (2D)
python3 verify_3d.py          # exact 3D assembly: clashes, bearing, out/cone.step
python3 dxf_vs_3d.py          # the shipped DXFs part by part = the verified 3D (0 mm2 difference)
python3 audit_dxf.py out/CONE_18MM_CUT.dxf   # rebuild the cone from the DXF alone + kerf-end lips
/root/.venvs/blender/bin/python render_blender.py hero|section
/root/.venvs/blender/bin/python render_exploded.py   # after exporting out/stl
```

## Parts (all MDF 18)

| # | Part | Role |
|---|------|------|
| 01 | SHELL | kerfed skin, whole cone, one piece (42 full + 41 short kerfs, 6 mm wood kept at both seam edges) |
| 02 | FORMER-BASE | floor disc, 4 mortises for core level 1 |
| 03 | FORMER-JOINT-LO | caps core level 1 |
| 04 | FORMER-JOINT-UP | glued on 03, mortises for core level 2 |
| 05 | FORMER-TOP | closes the cone top flush, caps core level 2 |
| 06-07 | CORE-1A / 1B | crossing plates (half-lap), level 1, at 0/90 deg |
| 08-09 | CORE-2A / 2B | crossing plates (half-lap), level 2, at 45/135 deg |

Load path: core plates -> tabs -> formers -> floor; the shell is the skin.
Short kerfs start where the full ones are 24 mm apart, so the wood between
kerfs stays 6-18 mm over the whole sector.

Assembly: core 1A x 1B into FORMER-BASE -> FORMER-JOINT-LO on top -> glue
FORMER-JOINT-UP on it -> core 2A x 2B into it -> FORMER-TOP -> wrap and glue
the SHELL onto the former edges (fill the 4.8 mm wedge under each former edge
with PU glue).

`out/parts/P00_BEND-TEST_x1.dxf` is a coupon with the tightest kerf pattern:
cut and bend it before cutting the shell.

## Why straight parallel kerfs work on a cone

Bent about its skin, the back face must shorten by 2π·d·cos α around the cone
(d = pocket depth, α = half apex angle), the same at every height, so
constant-width kerfs along the generatrices close evenly over their length.
Here 94 mm in total: at most 2.2 mm per kerf.

## Layers

`CUT` through cuts · `POCKET-KERF-15.5` kerf pockets on the BACK face,
15.5 mm deep, 6 mm wide; the cutter centre runs 3 mm past both curved edges,
so the round slot end leaves no full-thickness lip (V8 stopped 0.5 mm short
and left a 0.5-3.5 mm lip of 18 mm wood at every kerf end: fixed in V9,
checked by `audit_dxf.py`) ·
`ENGRAVE-LABEL` · `REFERENCE-SHEET` (the shells are too finely kerfed to
engrave: mark by hand).

## Parameters and provenance

| Parameter | Value | Status |
|-----------|-------|--------|
| Construction (kerfed cone, formers, collar) | - | FROM_REFERENCE_VIDEO |
| Base Ø / height | 400 / 450 | USER_CONFIRMED |
| Top Ø | 160 (40 % of base, as the post) | DESIGN_CHOICE_UNCONFIRMED |
| One shell, no collar | - | DESIGN_CHOICE (fewer seams) |
| Board | MDF 18 | USER_CONFIRMED |
| Core joints: slot 19, tab 40, 5 mm web | - | ADOPTED_FROM_TOKYO_PACK |
| No table top | - | USER_CONFIRMED |
| Mid formers (core joint) | 225 | DESIGN_CHOICE_UNCONFIRMED |
| Skin under the kerfs | 2.5 mm | ASSUMED_USER_INPUT_REQUIRED |
| Cutter Ø (= kerf width) | 6 mm | ASSUMED_USER_INPUT_REQUIRED |
| Kerf land at the top edge (wood between kerfs) | 6 mm -> pitch 12 | MATCHES_NLCNC_DEFAULT ("zig-zag spacing" 6, bit 6) |

## Status: CAD_COMPLETE_NOT_VALIDATED

Over each kerf the 2.5 mm skin bends at about R42 at worst (~3 % strain).
Whether it survives is unknown until the bend-test coupon is cut; if it
cracks, thin the skin or tighten the pitch.
