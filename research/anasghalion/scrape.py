"""Scrape the anasghalion.com CNC furniture catalog with Scrapling.

The site is WordPress + WooCommerce, so the public Store API returns the whole
catalog as JSON; no HTML parsing of product pages is needed.

    pip install "scrapling[fetchers]"
    python scrape.py            # writes products.json + products.csv next to this file
"""
import csv
import html
import json
import os
import re
from pathlib import Path

from scrapling.fetchers import Fetcher

BASE = "https://anasghalion.com/wp-json/wc/store/v1/products"
OUT = Path(__file__).parent
VERIFY = os.environ.get("REQUESTS_CA_BUNDLE", True)


def fetch_all():
    products, page = [], 1
    while True:
        r = Fetcher.get(f"{BASE}?per_page=100&page={page}", verify=VERIFY)
        r.raise_for_status() if hasattr(r, "raise_for_status") else None
        batch = json.loads(r.body)
        products += batch
        if len(batch) < 100:
            return products
        page += 1


def text(s):
    s = re.sub(r"<br\s*/?>|</p>", "\n", s or "")
    s = html.unescape(re.sub(r"<[^>]+>", "", s))
    return re.sub(r"[ \t]+", " ", s).strip()


def thickness_mm(desc):
    m = re.search(r"(\d{2})\s*mm", desc)
    return int(m.group(1)) if m else None


def wdh(desc):
    """First W/D/H triple in cm, from 'W98*D85*H79' or '233x90x54 cm' styles."""
    m = re.search(r"W\s*(\d+)\D{1,4}D\s*(\d+)\D{1,4}H\s*(\d+)", desc, re.I)
    if m:
        return tuple(int(x) for x in m.groups())
    m = re.search(r"D\s*(\d+)\D{1,4}H\s*(\d+)\D{1,4}W\s*(\d+)", desc, re.I)
    if m:
        d, h, w = m.groups()
        return int(w), int(d), int(h)
    m = re.search(r"(?<![\d×])(\d{2,3})\s*[x×*]\s*(\d{2,3})\s*[x×*]\s*(\d{2,3})\s*cm", desc, re.I)
    if m:
        return tuple(int(x) for x in m.groups())
    return tuple(label(desc, p) for p in LABELS)


LABELS = (
    r"\b(?:Width|W)",
    r"\b(?:Depth|D)(?!\s*Seat)",
    r"\b(?:Full\s*H[ei]*ght|H\.?\s*BACK|Height|Hight|H)(?!\s*Seat)",
)


def label(desc, pattern):
    """'Width : 95 CM', 'W : 272 CM' style labeled values."""
    m = re.search(pattern + r"\s*[:.]?\s*(\d+(?:\.\d+)?)\s*cm", desc, re.I)
    return float(m.group(1)) if m else None


def dimension_lines(desc):
    lines = dict.fromkeys(
        l.strip() for l in desc.splitlines()
        if re.search(r"\d+\s*(cm|CM)|\d+\s*[x×*]\s*\d+", l) and "1220" not in l and "122×244" not in l
    )
    return " / ".join(lines)


def normalize(p):
    desc = text(p["short_description"]) + "\n" + text(p["description"])
    minor = p["prices"]["currency_minor_unit"]
    price = lambda k: int(p["prices"][k]) / 10**minor if p["prices"][k] else None
    w, d, h = wdh(desc)
    return {
        "id": p["id"],
        "name": html.unescape(p["name"]),
        "url": p["permalink"],
        "categories": " | ".join(html.unescape(c["name"]) for c in p["categories"]),
        "price_usd": price("price"),
        "regular_price_usd": price("regular_price"),
        "on_sale": p["on_sale"],
        "sheet": "MDF/Plywood",
        "thickness_mm": thickness_mm(desc),
        "width_cm": w,
        "depth_cm": d,
        "height_cm": h,
        "dimensions_raw": dimension_lines(desc),
        "images": len(p["images"]),
        "main_image": p["images"][0]["src"] if p["images"] else None,
        "reviews": p["review_count"],
        "short_description": text(p["short_description"]),
    }


if __name__ == "__main__":
    raw = fetch_all()
    rows = [normalize(p) for p in raw]
    (OUT / "products.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    with open(OUT / "products.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} products -> {OUT}")
