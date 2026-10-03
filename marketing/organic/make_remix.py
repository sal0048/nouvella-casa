"""Remix the account's best organic reels into trial-reel variants.

    python3 make_remix.py plan                 # write out/remix_manifest.json (500 recipes)
    python3 make_remix.py render ID [ID ...]   # render recipes to out/remix/<ID>.mp4

Sources are nouvella_casa's own top organic reels (see README.md for the numbers).
Each source gets 100 recipes = 10 hooks (5 Darija, 5 French: the top two organic
reels had French captions) x 10 visual treatments. Recipes render lazily, right
before they are published, so only what goes out is stored.

Queue order: 10 per campaign day, 2 per source, and each source's first ten
recipes use all ten hooks once, so the first five days compare hooks per source.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "video-variants"))
import make_variants as M  # noqa: E402

SRC = HERE / "src"
OUT = HERE / "out"
TMP = OUT / "_layers"
W, H = 1080, 1920
FF = M.FF

# code: (file, product, material line for captions, hooks)
BEAN_HOOKS = [
    "طاولة واحدة… والصالون تبدل كامل",
    "رخام طبيعي وخشب الزان: هاذي هي",
    "القطعة لي كل ضيف يسقسي عليها",
    "شكل حبة الفول: أحسن طاولة للصالون",
    "من الورشة تاعنا لدارك، بلا وسيط",
    "Une pièce unique, sculptée à la main",
    "Marbre naturel · hêtre massif",
    "La table basse qui change tout le salon",
    "Fabriquée en Algérie, pensée pour vous",
    "Et si une seule pièce suffisait ?",
]
ORION_HOOKS = [
    "زجاج مقسّى وخشب الزان",
    "طاولة تبان خفيفة… وهي قوية",
    "زوج طبقات زجاج، رجلين خشب",
    "هاذي ماشي طاولة عادية",
    "من الورشة تاعنا لدارك، بلا وسيط",
    "ORION · bois hêtre, verre trempé",
    "Légère à l'œil, solide au quotidien",
    "Deux plateaux de verre, un design unique",
    "Fabriquée en Algérie, pensée pour vous",
    "Le salon mérite mieux qu'une table ordinaire",
]
SOURCES = {
    "A": ("Da8uaUluyk5.mp4", "bean", "Marbre naturel, hêtre massif.", BEAN_HOOKS),
    "B": ("DavguyaODKg.mp4", "orion", "Bois hêtre, verre trempé.", ORION_HOOKS),
    "C": ("DavBnbxN3_L.mp4", "bean", "Marbre naturel, hêtre massif.", BEAN_HOOKS),
    "D": ("DatcYPFNIkH.mp4", "bean", "Marbre naturel, hêtre massif.", BEAN_HOOKS),
    "E": ("DaYjLl9OKBN.mp4", "orion", "Bois hêtre, verre trempé.", ORION_HOOKS),
}
# name, extra filter, zoom, speed (no mirror: the sources carry burned-in text)
TREATMENTS = [
    ("original", "", 1.00, 1.00),
    ("zoom", "", 1.08, 1.00),
    ("warm", "colorbalance=rs=.05:bs=-.05,eq=saturation=1.08", 1.00, 1.00),
    ("cool", "colorbalance=bs=.04,eq=contrast=1.05", 1.00, 1.00),
    ("fast", "", 1.00, 1.10),
    ("slow", "", 1.00, 0.92),
    ("zoom-warm", "colorbalance=rs=.04:bs=-.04", 1.12, 1.00),
    ("bright", "eq=brightness=.03:saturation=1.05", 1.00, 1.00),
    ("zoom-fast", "", 1.05, 1.08),
    ("contrast", "eq=contrast=1.08:saturation=1.03", 1.00, 1.00),
]
CTA_AR = ["ابعثلنا في الخاص للثمن والمقاسات.", "اكتب «طاولة» في التعليقات ونجاوبوك.",
          "للطلب والمعلومات: الخاص مفتوح."]
CTA_FR = ["Commandez en DM.", "Prix et dimensions en message privé.", "Écrivez « table » en commentaire."]
TAGS = ["#ديكور", "#طاولة_قهوة", "#الجزائر", "#tablebasse", "#coffeetable", "#decoration",
        "#homedecor", "#interiordesign", "#algerie", "#dz", "#salon", "#furniture"]
MIN_LEN = 9.0          # shorter sources play twice so hook and CTA both fit


def caption(src, h, t):
    _, _, material, hooks = SOURCES[src]
    fr = h >= 5
    cta = (CTA_FR if fr else CTA_AR)[(h + t) % 3]
    tags = " ".join(dict.fromkeys(TAGS[(h * 3 + t + k * 5) % len(TAGS)] for k in range(5)))
    return "\n".join([hooks[h], material, cta, "", "Nouvella Casa", tags])


def plan():
    rows = []
    for k in range(10):                      # block k: every hook once, treatment shifted
        for h in range(10):
            for s in SOURCES:
                t = (h + k + "ABCDE".index(s)) % 10
                rows.append({"id": f"{s}{h}{t}", "src": s, "hook": h, "treatment": t})
    # 10 per day, interleaving sources: day d takes positions [10d, 10d+10)
    ordered = []
    per_src = {s: [r for r in rows if r["src"] == s] for s in SOURCES}
    for i in range(100):
        for s in SOURCES:
            ordered.append(per_src[s][i])
    out = []
    for n, r in enumerate(ordered):
        hooks = SOURCES[r["src"]][3]
        out.append({**r, "day": n // 10 + 1, "file": f"{r['id']}.mp4",
                    "source_reel": SOURCES[r["src"]][0][:-4],
                    "hook_text": hooks[r["hook"]], "lang": "fr" if r["hook"] >= 5 else "ar",
                    "treatment_name": TREATMENTS[r["treatment"]][0],
                    "caption": caption(r["src"], r["hook"], r["treatment"])})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "remix_manifest.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(len(out), "recipes")


def text_block(text, rtl, y=300, size=64):
    """Hook card; Arabic is shaped right-to-left, French left-to-right."""
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = M.font(M.BOLD, size)
    kw = {"direction": "rtl", "language": "ar"} if rtl else {"direction": "ltr", "language": "fr"}
    rows, cur = [], ""
    for wd in text.split():
        t = f"{cur} {wd}".strip()
        if cur and d.textlength(t, font=f, **kw) > W - 160:
            rows.append(cur)
            cur = wd
        else:
            cur = t
    rows.append(cur)
    lh = size + 24
    top = y - lh * len(rows) / 2
    d.rounded_rectangle([50, top - 26, W - 50, top + lh * len(rows) + 26], radius=40, fill=(*M.INK, 225))
    for k, r in enumerate(rows):
        d.text((W / 2, top + lh * (k + 0.5)), r, font=f, fill=(255, 255, 255), anchor="mm", **kw)
    return im


def hook_card(text, rtl):
    import hashlib
    p = TMP / f"hook_{hashlib.md5(text.encode()).hexdigest()[:10]}.png"
    if not p.exists():
        text_block(text, rtl).save(p)
    return p


def render(rid):
    rec = next(r for r in json.loads((OUT / "remix_manifest.json").read_text()) if r["id"] == rid)
    fname, _, _, hooks = SOURCES[rec["src"]]
    src = SRC / fname
    dur, sw, sh = M.probe(src)
    loops = 2 if dur < MIN_LEN else 1
    base = dur * loops
    _, vf, zoom, speed = TREATMENTS[rec["treatment"]]
    out_dur = base / speed
    TMP.mkdir(parents=True, exist_ok=True)
    cta = TMP / "cta.png"
    if not cta.exists():
        M.cta(W, H).save(cta)
    chain = [f"scale={W}:{H}:force_original_aspect_ratio=decrease"]
    fg = ",".join(chain)
    v = (f"[0:v]split[a][b];[b]scale={W}:{H}:force_original_aspect_ratio=increase,"
         f"crop={W}:{H},boxblur=24:2[bg];[a]{fg}[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2")
    if zoom != 1:
        v += f",scale=trunc(iw*{zoom}/2)*2:-2,crop={W}:{H}"
    if vf:
        v += "," + vf
    if speed != 1:
        v += f",setpts=PTS/{speed}"
    v += ",setpts=PTS-STARTPTS,fps=30[s]"
    a = f"[0:a]atempo={speed}," if speed != 1 else "[0:a]"
    flt = (f"{v};[s][1:v]overlay=0:0:enable='lt(t,3)'[h];"
           f"[h][2:v]overlay=0:0:enable='gte(t,{out_dur - 2.5:.2f})'[out];"
           f"{a}afade=t=out:st={out_dur - 0.8:.2f}:d=0.8[au]")
    dst = OUT / "remix" / rec["file"]
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([FF, "-y", "-v", "error", "-stream_loop", str(loops - 1), "-i", str(src),
                    "-loop", "1", "-i", str(hook_card(hooks[rec["hook"]], rec["hook"] < 5)),
                    "-loop", "1", "-i", str(cta),
                    "-filter_complex", flt, "-map", "[out]", "-map", "[au]",
                    "-t", f"{out_dur:.3f}", "-c:v", "libx264", "-crf", "24", "-preset", "medium",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart", str(dst)], check=True)
    return dst


if __name__ == "__main__":
    if sys.argv[1] == "plan":
        plan()
    else:
        for rid in sys.argv[2:]:
            print(render(rid))
