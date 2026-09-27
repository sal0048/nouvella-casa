# Cone pedestal table (kerf-bent shell)

Our own parametric design of the technique in the workshop video: a flat
annular sector with radial kerfs pocketed into its back rolls into a cone,
held by internal formers, with a collar ring over the joint.

```
python3 build.py      # nest + out/cone-table.dxf + out/parts/*.dxf
python3 verify.py     # 35 deterministic checks
/root/.venvs/blender/bin/python render_blender.py hero|section
```

## Parts

| # | Part | Board | Qty | Notes |
|---|------|-------|-----|-------|
| 01 | SHELL-LOW | 10 mm | 1 | sector, 114 kerfs, z 0-400 |
| 02 | SHELL-UP | 10 mm | 1 | sector, 79 kerfs, z 400-714 |
| 03 | FORMER-BASE | 18 mm | 1 | disc R285.5, inside the foot |
| 04 | FORMER-JOINT-LO | 18 mm | 1 | ring R205.2, below the joint |
| 05 | FORMER-JOINT-UP | 18 mm | 1 | ring R201.5, above the joint |
| 06 | FORMER-TOP | 18 mm | 1 | disc R139.3, inside the top |
| 07 | COLLAR | 18 mm | 1 | ring R218.4-258.4, over the joint |
| 08 | SUB-TOP | 18 mm | 1 | Ø500 |
| 09 | TABLE-TOP | 18 mm | 1 | Ø800 |

One 2440 x 1220 sheet of 10 mm board, one of 18 mm.
`out/parts/P00_BEND-TEST_x1.dxf` is a 150 mm coupon with the tightest kerf
pattern: cut and bend it before cutting the shells.

## Why straight parallel kerfs work on a cone

Bent about its skin, the back face must shorten by 2π·d·cos α around the cone
(d = pocket depth, α = half apex angle) - the same amount at every height. So
constant-width kerfs along the generatrices close evenly over their length.
Here 46.1 mm in total, 0.4-0.6 mm per kerf.

## Layers

`CUT` through cuts · `POCKET-KERF-7.5` kerf pockets on the BACK face, 7.5 mm
deep, 6 mm wide, running 3 mm past both curved edges · `ENGRAVE-LABEL` ·
`REFERENCE-SHEET` (the shells are too finely kerfed to engrave: mark by hand).

## Parameters and provenance

| Parameter | Value | Status |
|-----------|-------|--------|
| Construction (kerfed cone, formers, collar) | - | FROM_REFERENCE_VIDEO |
| Table height | 750 | DESIGN_CHOICE_UNCONFIRMED |
| Top Ø / sub-top Ø | 800 / 500 | DESIGN_CHOICE_UNCONFIRMED |
| Cone Ø foot / top | 600 / 300 | DESIGN_CHOICE_UNCONFIRMED |
| Joint (collar) height | 400 | DESIGN_CHOICE_UNCONFIRMED |
| Shell board / skin | 10 / 2.5 mm | ASSUMED_USER_INPUT_REQUIRED |
| Formers, top board | 18 mm | USER_CONFIRMED (house standard) |
| Cutter Ø (= kerf width) | 6 mm | ASSUMED_USER_INPUT_REQUIRED |
| Kerf pitch at the top edge | 12 mm | DESIGN_CHOICE_UNCONFIRMED |

## Status: CAD_COMPLETE_NOT_VALIDATED

The skin bends at about R77 over each kerf on the upper shell (~1.6 % strain).
Whether 2.5 mm of your board survives that is unknown until the bend-test
coupon is cut. Stability: ~24 kg table, tips with ~72 kg pressed on the top
edge; add ballast on the base former for a café table.
