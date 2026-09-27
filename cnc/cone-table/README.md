# Cone coffee-table base (kerf-bent shell)

Our own parametric model of the kerf-bent cone technique from the workshop
video. The size follows the published post specs (height 400, top 120,
base 300, MDF 15), read as cone diameters; the files themselves are ours.

```
python3 build.py              # out/cone-table.dxf + out/parts/*.dxf
python3 build.py --sets 2     # out/cone-table_x2.dxf: two tables, one sheet
python3 verify.py             # deterministic checks
/root/.venvs/blender/bin/python render_blender.py hero|section
```

## Parts (all 15 mm MDF, one 2440 x 1220 sheet holds two tables)

| # | Part | Notes |
|---|------|-------|
| 01 | SHELL-LOW | sector, 53 kerf pockets, cone z 0-220 |
| 02 | SHELL-UP | sector, 32 kerf pockets, cone z 220-400 |
| 03 | FORMER-BASE | disc inside the foot, carries the ballast |
| 04 | FORMER-JOINT-LO | ring just below the joint |
| 05 | FORMER-JOINT-UP | ring just above the joint |
| 06 | FORMER-TOP | disc inside the cone top, sub-top screws in |
| 07 | COLLAR | ring over the joint |
| 08 | SUB-TOP | Ø300 under the top |
| 09 | TABLE-TOP | Ø500 |

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
| Table top Ø / sub-top Ø | 500 / 300 | DESIGN_CHOICE_UNCONFIRMED |
| Ballast on the base former | 20 kg | DESIGN_CHOICE_UNCONFIRMED |
| Joint (collar) height | 220 | DESIGN_CHOICE_UNCONFIRMED |
| Skin under the kerfs | 2.5 mm | ASSUMED_USER_INPUT_REQUIRED |
| Cutter Ø (= kerf width) | 6 mm | ASSUMED_USER_INPUT_REQUIRED |
| Kerf pitch at the top edge | 12 mm | DESIGN_CHOICE_UNCONFIRMED |

## Stability

A 300 mm base cannot hold a big top by itself. Load that tips the table when
pressed on the top edge:

| Top Ø | no ballast | 10 kg | 20 kg |
|-------|-----------|-------|-------|
| 450 | 14 kg | 34 kg | 54 kg |
| 500 | 11 kg | 26 kg | 41 kg |
| 600 | 8 kg | 18 kg | 28 kg |

Default: Ø500 top with 20 kg (steel plate or concrete) on the base former.

## Status: CAD_COMPLETE_NOT_VALIDATED

Over each kerf the 2.5 mm skin bends at about R31 on the upper shell
(~4 % strain), which is severe for MDF. Whether it survives is unknown until
the bend-test coupon is cut; if it cracks, thin the skin or tighten the pitch.
