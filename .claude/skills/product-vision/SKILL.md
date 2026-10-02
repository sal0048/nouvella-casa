---
name: product-vision
description: Identify Sal's furniture models (Noya Home / Nouvella Casa) from a photo or video, and read videos frame by frame. Use whenever the user sends a product photo or video, asks "which model is this", or gives prices/supplier info about a pictured table or chair.
---

# Product vision — recognizing the models

## 1. Photo → model
1. Open every image in `refs/` (one labeled reference photo per model) and the table in section 3.
2. Compare the user's photo on: **top shape** (round / rectangle / cloud / triangle), **top material** (glass, marble, porcelain), **base type** (fluted round drum, crossed X legs, H legs…), **wood tone**, **number of pieces**.
3. Answer with the model name + confidence:
   - Clear match → "هادي **AXEL**".
   - Two candidates → name both and ask one question.
   - No match → say it is not in the references, and ask for the name. **Never guess a model name.**
4. When the user names a new model, save the photo to `refs/<MODEL>.jpg` (resize to ≤1024px with ffmpeg) and add a row to section 3.

## 2. Video → frames
Claude cannot hear audio. For a video:
```bash
ffmpeg -loglevel error -i input.mp4 -vf "fps=1,scale=640:-2" frames/f_%03d.jpg
# long video: use fps=1/3; then view a contact sheet:
ffmpeg -loglevel error -i input.mp4 -vf "fps=1/2,scale=320:-2,tile=4x4" sheet_%02d.jpg
```
Read the sheets, then specific frames. If speech matters, ask the user for the text.

## 3. Reference table
| Model | File | Key features | Sale price (DZD) | Source |
|---|---|---|---|---|
| ORION | refs/ORION.jpg | 2 round tables Ø70 + Ø50, **fluted round wood drum base**, marble or porcelain top | marble 29,000 / porcelain 23,000 | Aymen |
| AXEL | refs/AXEL.jpg | **rectangular glass** on **crossed X solid-wood legs**, 4 round metal pads holding the glass | 19,000 | assembly 8,500 or Aymen 12,000 |
| NUAGE | — (photo missing) | **cloud-shaped** top 110×60, marble/porcelain; Appoint = small round side table | 16,000–41,000 | assembly (base 9,000 / 4,500) |
| LOTUS | — (photo missing) | round Ø80, beech + glass | 23,000 | Aymen 13,000 |
| ARC | — (photo missing) | beech + glass, 100×60 / 110×60 | 22,000 | Aymen 13,000 or assembly 10,000 |
| ATLAS | — | beech + glass | 21,000 | Aymen 13,000 |
| STELLA | — | beech + glass, 80×80 | 21,500 | Hamza |
| RONDO | — | beech + glass | 26,500 | ? |
| TRIA (temp name) | — | **triangle glass** + varnished wood | 21,500–22,500 | unconfirmed |
| CHAISE H | refs/CHAISE_H.jpg | dark walnut frame, **H-shaped legs**, grey fabric, armrests | ? | ? |
| CHAISE A (غزال) | refs/CHAISE_A_ghazal.jpg | light natural wood, **angled A legs**, round beige tub back | 8,500 | ? |
| CHAISE 3 | refs/CHAISE_3.jpg | walnut, thin round legs, curved back with wood rim, light beige | 9,000 | ? |
| CHAISE 4 | refs/CHAISE_4.jpg | light curved bentwood legs, cream bouclé tub back | ? | ? |
| CASSATE | — | no photo yet | ? | ? |

Prices and costs: the source of truth is Airtable (base `app6Y6x2UZ7IdcjmM`, tables 💰 Variants and 🧩 مكونات التكلفة). Update this table when they change.
