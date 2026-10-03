# Source trace: anasghalion.com vs a suspected Russian designer

Question: does Anas Ghalion resell CNC frames designed by a Russian designer?

## Method
- Catalog of cncframes.furniture-3d.com (Alexandr Trubnikov, Russian-speaking
  frame designer) pulled via its WooCommerce Store API -> `cncframes_products.json` (24 models).
- 480 Anas images vs 205 cncframes images compared with perceptual hashes
  (pHash + dHash). Best pair distance 14/64 (copies are usually < 8).
- Closest pairs checked by eye -> `pairs.jpg`: different construction style.
- Yandex reverse image search on 24 Anas frame images.

## Findings (2026-09-28)
- CONFIRMED: Anas copies the *look* from real brands (Edra, Necchi, Blok, ...),
  found by Yandex in retail shops.
- NOT FOUND: any image or design match with Trubnikov / furniture-3d.
- HINTS ONLY: product names "kreslo Chair" (кресло) and "Voloshin Sofa";
  the Wing Sofa image also appears on 3ddd.ru (Russian 3D model library).

`img/` (downloaded third-party images, 229 MB) is not committed.
