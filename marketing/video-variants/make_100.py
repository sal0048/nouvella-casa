"""100 reels = 10 hooks x 10 visual treatments, scheduled 10 per day.

    python3 make_100.py <input.mp4> [--music-from SECONDS] [--jobs N] [--day D]

Each day gets all 10 hooks once and all 10 treatments once (Latin square:
treatment = (hook + day) % 10), so a day's results compare hooks fairly and
the 10 days together compare treatments. Every reel has its own caption.
The treatments (zoom, speed, grade, trim; no mirror: the source has
burned-in Arabic text) make each file visibly
different, not a byte-copy of the same clip.

Writes out/reels/reel_DD_KK.mp4 and out/reels/manifest.json.
"""

from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

import make_variants as M

OUT = M.OUT / "reels"
TMP = M.OUT / "_layers"
FF = M.FF

# name, extra video filter, mirror, zoom, speed, trim-start (s)
TREATMENTS = [
    ("original", "", False, 1.00, 1.00, 0.0),
    ("slow", "", False, 1.00, 0.92, 0.0),
    ("zoom", "", False, 1.08, 1.00, 0.0),
    ("zoom-cool", "colorbalance=bs=.04,eq=contrast=1.05", False, 1.05, 1.00, 0.0),
    ("warm", "colorbalance=rs=.05:gs=.01:bs=-.05,eq=saturation=1.10", False, 1.00, 1.00, 0.0),
    ("cool-contrast", "eq=contrast=1.07:saturation=0.95,colorbalance=bs=.04", False, 1.00, 1.00, 0.0),
    ("fast", "", False, 1.00, 1.10, 0.0),
    ("late-start", "", False, 1.00, 1.00, 1.5),
    ("zoom-warm", "colorbalance=rs=.04:bs=-.04", False, 1.12, 1.00, 0.0),
    ("fast-bright", "eq=brightness=.03:saturation=1.05", False, 1.00, 1.08, 0.0),
]

# openers follow the hook's angle; bodies change by day; closers rotate
OPENERS = [
    "طاولة قهوة بستيل الفنادق، ولكن في دارك.",
    "الصالون ساعات يكون ناقصو قطعة وحدة برك.",
    "ماشي طاولة عادية: القاعدة هي لي تحكي.",
    "القطعة لي كل ضيف يسقسي عليها.",
    "القاعدة خدمة CNC بالمقاس، خشب مقطوع بدقة.",
    "تبدل روح الصالون بلا ما تبدل كلش.",
    "من الورشة تاعنا، مباشرة لدارك.",
    "شكل مدور، خطوط نظيفة، وصنعة محلية.",
    "ركز في القاعدة… هنا الفرق.",
    "إذا عجبتك، قولها في التعليقات.",
]
BODIES = [
    "تصميم يزيد الدفا للصالون ويخلي العين تحبس عليه.",
    "تنفع مع الصالون العصري ومع الكلاسيكي.",
    "خط مدور يكسر القواطع الحادة تاع الأثاث.",
    "قطعة وحدة تعطي للبيت لوك جديد.",
    "خدمة ورشة، ماشي منتوج مستورد.",
    "تفاصيل صغيرة تبان كبيرة كي تشوفها قدامك.",
    "بساطة في الشكل، قوة في الحضور.",
    "للي يحب الديكور الهادي والمرتب.",
    "تشوفها مرة، تبقى في بالك.",
    "حاجة مختلفة على الطاولات لي تعودنا عليهم.",
]
CLOSERS = [
    "ابعثلنا في الخاص للثمن والمقاسات.",
    "اكتب «طاولة» في التعليقات ونجاوبوك.",
    "للطلب والمعلومات: الخاص مفتوح.",
    "سقسينا على الألوان والمقاسات في الخاص.",
    "احفظ الفيديو وابعثو للي راه يجهز في دارو.",
]
TAGS = ["#ديكور", "#ديكور_منزلي", "#طاولة_قهوة", "#أثاث", "#الجزائر", "#صالون",
        "#decor", "#homedecor", "#coffeetable", "#interiordesign", "#furniture", "#dz"]


def caption(hook, day):
    tags = [TAGS[(hook + day + j * 5) % len(TAGS)] for j in range(5)]
    return "\n".join([OPENERS[hook], BODIES[day], CLOSERS[(hook + 2 * day) % len(CLOSERS)],
                      "", "Nouvella Casa", " ".join(dict.fromkeys(tags))])


def mark_after(W, H, mirror, zoom):
    """Where the generator mark lands after zoom (centre crop) and mirror."""
    x, y = M.MARK_C
    x, y = W / 2 + (x - W / 2) * zoom, H / 2 + (y - H / 2) * zoom
    if mirror:
        x = W - x
    return (x, y), M.MARK_R * zoom


def badge_at(W, H, c, r):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    bw, bh = 330, 104
    cx = min(max(c[0], bw / 2 + 16), W - bw / 2 - 16)
    cy = min(max(c[1], bh / 2 + 16), H - bh / 2 - 16)
    x0, y0 = cx - bw / 2, cy - bh / 2
    d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=bh / 2, fill=(*M.SAND, 245))
    M.cone_icon(d, x0 + 58, cy, 60, M.INK)
    d.text((x0 + 100, cy - 16), "NOUVELLA", font=M.font(M.BOLD, 34), fill=M.INK, anchor="lm")
    d.text((x0 + 102, cy + 22), "C A S A", font=M.font(M.REG, 22), fill=M.ACCENT, anchor="lm")
    assert x0 <= c[0] - r and x0 + bw >= c[0] + r, "badge misses the mark (x)"
    assert y0 <= c[1] - r and y0 + bh >= c[1] + r, "badge misses the mark (y)"
    return im


def music_bed(src, s0, dur):
    """Loop the source's music [s0, end] three times with crossfades."""
    seg, bed = TMP / "music_seg.wav", TMP / "music_bed.wav"
    subprocess.run([FF, "-y", "-v", "error", "-ss", str(s0), "-t", str(dur - s0), "-i", str(src),
                    "-vn", "-c:a", "pcm_s16le", str(seg)], check=True)
    subprocess.run([FF, "-y", "-v", "error", "-i", str(seg), "-i", str(seg), "-i", str(seg),
                    "-filter_complex",
                    "[0:a][1:a]acrossfade=d=0.6:c1=tri:c2=tri[x];"
                    "[x][2:a]acrossfade=d=0.6:c1=tri:c2=tri[a]",
                    "-map", "[a]", "-c:a", "pcm_s16le", str(bed)], check=True)
    return bed


def render(src, dur, W, H, bed, day, hook):
    k = (hook + day) % len(TREATMENTS)
    name, vf, mirror, zoom, speed, trim = TREATMENTS[k]
    out_dur = (dur - trim) / speed
    t_end = out_dur - 2.5
    c, r = mark_after(W, H, mirror, zoom)
    tag = f"{day + 1:02d}_{hook + 1:02d}"
    bpath = TMP / f"badge_t{k:02d}.png"
    if not bpath.exists():
        badge_at(W, H, c, r).save(bpath)
    chain = []
    if zoom != 1:
        chain.append(f"scale=trunc(iw*{zoom}/2)*2:-2,crop={W}:{H}")
    if vf:
        chain.append(vf)
    if speed != 1:
        chain.append(f"setpts=PTS/{speed}")
    chain.append("setpts=PTS-STARTPTS")
    flt = (f"[0:v]{','.join(chain)}[s];[s][1:v]overlay=0:0[a];"
           f"[a][2:v]overlay=0:0:enable='lt(t,3)'[b];"
           f"[b][3:v]overlay=0:0:enable='gte(t,{t_end:.2f})'[v];"
           f"[4:a]atrim=0:{out_dur:.3f},afade=t=in:d=0.3,"
           f"afade=t=out:st={out_dur - 1:.2f}:d=1.0[au]")
    dst = OUT / f"reel_{tag}.mp4"
    subprocess.run([FF, "-y", "-v", "error", "-ss", str(trim), "-i", str(src),
                    "-loop", "1", "-i", str(bpath),
                    "-loop", "1", "-i", str(TMP / f"hook_{hook + 1:02d}.png"),
                    "-loop", "1", "-i", str(TMP / "cta.png"), "-i", str(bed),
                    "-filter_complex", flt, "-map", "[v]", "-map", "[au]",
                    "-t", f"{out_dur:.3f}", "-c:v", "libx264", "-crf", "25", "-preset", "medium",
                    "-threads", "2", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart", str(dst)], check=True)
    return {"id": tag, "file": dst.name, "day": day + 1, "slot": hook + 1,
            "hook": M.HOOKS[hook], "treatment": name, "duration": round(out_dur, 2),
            "caption": caption(hook, day), "status": "ready"}


def main():
    src = Path(sys.argv[1])
    s0 = float(sys.argv[sys.argv.index("--music-from") + 1]) if "--music-from" in sys.argv else 0.0
    jobs = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 2
    days = ([int(sys.argv[sys.argv.index("--day") + 1]) - 1] if "--day" in sys.argv
            else range(10))
    OUT.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    dur, W, H = M.probe(src)
    for h, text in enumerate(M.HOOKS):
        M.rtl_block(W, H, text, 300, 64).save(TMP / f"hook_{h + 1:02d}.png")
    M.cta(W, H).save(TMP / "cta.png")
    bed = music_bed(src, s0, dur)
    for k, t in enumerate(TREATMENTS):              # fail fast on badge geometry
        badge_at(W, H, *mark_after(W, H, t[2], t[3]))
    man_path = OUT / "manifest.json"
    manifest = {r["id"]: r for r in json.loads(man_path.read_text())} if man_path.exists() else {}
    todo = [(d, h) for d in days for h in range(10)]
    with ThreadPoolExecutor(jobs) as ex:
        for rec in ex.map(lambda dh: render(src, dur, W, H, bed, *dh), todo):
            old = manifest.get(rec["id"], {})
            if old.get("status") == "published":    # never forget a published reel
                rec.update({k: old[k] for k in old if k not in rec or k in ("status", "media_id",
                                                                             "permalink", "published_at")})
            manifest[rec["id"]] = rec
            print(rec["file"], rec["treatment"], rec["duration"], flush=True)
    man_path.write_text(json.dumps([manifest[k] for k in sorted(manifest)], ensure_ascii=False,
                                   indent=1))


if __name__ == "__main__":
    main()
