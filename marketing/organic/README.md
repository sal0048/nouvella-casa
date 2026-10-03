# Organic winners → trial-reel remixes

Data: Instagram insights for all 69 reels on nouvella_casa, pulled 2026-09-28.

## What worked organically (2025-2026, shared to feed)

| Reel | Product | Views | Reach | Shares | Saves | Avg watch |
|---|---|---|---|---|---|---|
| DavguyaODKg | ORION glass | 1595 | 1314 | 13 | 5 | 3.7 s |
| DavBnbxN3_L | bean marble set | 1555 | 1078 | 8 | 15 | 3.7 s |
| Da8uaUluyk5 | bean marble set | 1360 | 1122 | 26 | 27 | 5.2 s |
| DatcYPFNIkH | bean marble set | 1110 | 1019 | 6 | 7 | 2.7 s |
| DcsY5vuES8Z | bean marble set (same footage as Da8u) | 914 | 744 | 27 | 21 | 5.5 s |
| DaYjLl9OKBN | ORION + black glass | 929 | 788 | 10 | 3 | 4.4 s |

Patterns:
- Real product, real living room, natural light; no people, no voice.
- Short (5-17 s); the 5 s loops get the most views per reach.
- The bean marble set is the hero product (4 of the top 6).
- Material + craft lines ("Une pièce unique, sculptée à la main. Marbre naturel, hêtre massif")
  get the most shares and saves; the top two captions were French.
- Watch time is 3-5 s: the first second decides.

## Earlier trial reels

- July 2026, a few per day: 100-360 views each.
- 2026-09-10, about 20 in one day: 0-58 views each (median under 10).

## Remix plan (make_remix.py)

5 sources × 10 hooks (5 Darija, 5 French) × 10 treatments = 500 recipes, 100 per source.
Rendered lazily by remix_queue.py right before publishing; 10 per day, 2 per source.
