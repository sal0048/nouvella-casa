# Kerf-bent cone with structural core

Our own parametric model of the kerf-bent cone technique from the workshop
video. The size follows the published post specs (height 400, top 120,
base 300, MDF 15), read as cone diameters; the files themselves are ours.

```
python3 build.py              # out/cone-table.dxf + out/parts/*.dxf
python3 build.py --sets 2     # out/cone-table_x2.dxf: two cones nested together
python3 verify.py             # deterministic checks
/root/.venvs/blender/bin/python render_blender.py hero|section
```

## Parts (all MDF 15, one 2440 x 1220 sheet)

| # | Part | Role |
|---|------|------|
| 01 | SHELL-LOW | kerfed skin, cone z 0-220 |
| 02 | SHELL-UP | kerfed skin, cone z 220-400 |
| 03 | FORMER-BASE | floor disc, 4 mortises for core level 1 |
| 04 | FORMER-JOINT-LO | caps core level 1 |
| 05 | FORMER-JOINT-UP | glued on 04, 4 mortises for core level 2 |
| 06 | FORMER-TOP | closes the cone top flush, caps core level 2 |
| 07 | COLLAR | ring over the joint |
| 08-09 | CORE-1A / 1B | crossing plates (half-lap), level 1, at 0/90 deg |
| 10-11 | CORE-2A / 2B | crossing plates (half-lap), level 2, at 45/135 deg |

No table top. The load path is core plates -> tabs -> formers -> floor; the
kerfed shell is the skin. 150 kg standing on the top puts 1.3 MPa on the core
tab ends.

Assembly: core 1A x 1B into FORMER-BASE -> FORMER-JOINT-LO on top -> glue
FORMER-JOINT-UP on it -> core 2A x 2B into it -> FORMER-TOP -> wrap and glue
SHELL-LOW, then SHELL-UP, onto the former edges -> slide the COLLAR down from
the top.

`out/parts/P00_BEND-TEST_x1.dxf` is a coupon with the tightest kerf pattern:
cut and bend it before cutting the shells.

## Why straight parallel kerfs work on a cone

Bent about its skin, the back face must shorten by 2π·d·cos α around the cone
(d = pocket depth, α = half apex angle), the same at every height, so
constant-width kerfs along the generatrices close evenly over their length.
Here 76.6 mm in total: 1.4 mm per kerf on the lower shell, 2.4 mm on the upper.

## Layers

`CUT` through cuts · `POCKET-KERF-12.5` kerf pockets on the BACK face,
12.5 mm deep, 6 mm wide, running 3 mm past both curved edges ·
`ENGRAVE-LABEL` · `REFERENCE-SHEET` (the shells are too finely kerfed to
engrave: mark by hand).

## Parameters and provenance

| Parameter | Value | Status |
|-----------|-------|--------|
| Construction (kerfed cone, formers, collar) | - | FROM_REFERENCE_VIDEO |
| Cone height / top Ø / base Ø | 400 / 120 / 300 | FROM_PUBLISHED_POST (Ø vs R read from the fan angle) |
| Board | MDF 15 | FROM_PUBLISHED_POST |
| Core joints: slot 16, tab 40, 5 mm web | - | ADOPTED_FROM_TOKYO_PACK |
| No table top | - | USER_CONFIRMED |
| Joint (collar) height | 220 | DESIGN_CHOICE_UNCONFIRMED |
| Skin under the kerfs | 2.5 mm | ASSUMED_USER_INPUT_REQUIRED |
| Cutter Ø (= kerf width) | 6 mm | ASSUMED_USER_INPUT_REQUIRED |
| Kerf pitch at the top edge | 12 mm | DESIGN_CHOICE_UNCONFIRMED |

## Status: CAD_COMPLETE_NOT_VALIDATED

Over each kerf the 2.5 mm skin bends at about R31 on the upper shell
(~4 % strain), which is severe for MDF. Whether it survives is unknown until
the bend-test coupon is cut; if it cracks, thin the skin or tighten the pitch.
