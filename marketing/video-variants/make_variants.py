"""Brand + hook variants of one vertical video (A/B test the hook only).

    python3 make_variants.py <input.mp4> [--count N]

For every hook: the Nouvella Casa badge sits over the bottom-right corner
(where the generator's mark is), the hook shows for the first 3 s at the top,
and the call-to-action card shows for the last 2.5 s. Audio is kept.
Writes out/<stem>_hook_XX.mp4 and out/logo_nouvella_casa.png.

Post these with the platform's "AI-generated" label switched on.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont, features

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
FF = imageio_ffmpeg.get_ffmpeg_exe()
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

BRAND = "Nouvella Casa"
INK = (32, 26, 22)
SAND = (236, 226, 212)
ACCENT = (200, 70, 40)

# generator mark (Gemini sparkle) measured on 1080x1920: centre and half size
MARK_C, MARK_R = (900, 1740), 45

HOOKS = [
    "طاولة قهوة كيما تاع الفنادق… في دارك",
    "الصالون تاعك ناقصو غير هاذي",
    "طاولة ماشي كيما الطاولات",
    "هاذي الطاولة يسقسيو عليها كامل الضياف",
    "القاعدة؟ خشب مقطوع بالـ CNC",
    "تحب تبدل الصالون بلا ما تبدل كلش؟",
    "من الورشة تاعنا… لدارك",
    "شكل مدور، تصميم عصري، وصنعة دزيرية",
    "وقف! شوف القاعدة تاع هاذ الطاولة",
    "إذا عجبتك، اكتب «طاولة» في التعليقات",
]
CTA = "اطلبها دروك في الخاص"


def font(path, size):
    return ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)


def cone_icon(d, cx, cy, h, color):
    """Small slatted cone: the product's own silhouette as the brand mark."""
    top, bot = h * 0.28, h * 0.46
    y0, y1 = cy - h / 2, cy + h / 2
    d.polygon([(cx - top, y0), (cx + top, y0), (cx + bot, y1), (cx - bot, y1)], fill=color)
    for k in range(-3, 4):
        f = k / 3.5
        d.line([(cx + f * top, y0 + 3), (cx + f * bot, y1 - 3)], fill=SAND, width=2)


def logo(path: Path, scale=1.0):
    """Stand-alone logo (transparent PNG): cone mark + wordmark."""
    w, h = int(760 * scale), int(200 * scale)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cone_icon(d, h * 0.5, h * 0.5, h * 0.62, INK)
    d.text((h * 0.95, h * 0.30), "NOUVELLA", font=font(BOLD, int(64 * scale)), fill=INK, anchor="lm")
    d.text((h * 0.97, h * 0.70), "C A S A", font=font(REG, int(40 * scale)), fill=ACCENT, anchor="lm")
    im.save(path)
    return im


def badge(W, H):
    """Full-frame overlay: rounded brand badge centred on the generator mark."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    bw, bh = 330, 104
    cx, cy = MARK_C
    cx = min(cx, W - bw / 2 - 16)
    x0, y0 = cx - bw / 2, cy - bh / 2
    d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=bh / 2, fill=(*SAND, 245))
    cone_icon(d, x0 + 58, cy, 60, INK)
    d.text((x0 + 100, cy - 16), "NOUVELLA", font=font(BOLD, 34), fill=INK, anchor="lm")
    d.text((x0 + 102, cy + 22), "C A S A", font=font(REG, 22), fill=ACCENT, anchor="lm")
    assert x0 <= MARK_C[0] - MARK_R and x0 + bw >= MARK_C[0] + MARK_R
    assert y0 <= MARK_C[1] - MARK_R and y0 + bh >= MARK_C[1] + MARK_R
    return im


def rtl_block(W, H, text, y, size, box=True):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font(BOLD, size)
    words, rows, cur = text.split(), [], ""
    for wd in words:
        t = f"{cur} {wd}".strip()
        if cur and d.textlength(t, font=f, direction="rtl", language="ar") > W - 160:
            rows.append(cur)
            cur = wd
        else:
            cur = t
    rows.append(cur)
    lh = size + 24
    top = y - lh * len(rows) / 2
    if box:
        d.rounded_rectangle([50, top - 26, W - 50, top + lh * len(rows) + 26], radius=40,
                            fill=(*INK, 225))
    for k, r in enumerate(rows):
        d.text((W / 2, top + lh * (k + 0.5)), r, font=f, fill=(255, 255, 255), anchor="mm",
               direction="rtl", language="ar")
    return im


def cta(W, H):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font(BOLD, 60)
    bw, bh, cy = 760, 140, 360
    d.rounded_rectangle([W / 2 - bw / 2, cy - bh / 2, W / 2 + bw / 2, cy + bh / 2],
                        radius=bh / 2, fill=(*ACCENT, 250))
    d.text((W / 2, cy), CTA, font=f, fill=(255, 255, 255), anchor="mm",
           direction="rtl", language="ar")
    return im


def probe(path):
    out = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True).stderr
    import re
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out)
    size = re.search(r"Video: .*?, (\d{3,5})x(\d{3,5})", out)
    secs = int(dur[1]) * 3600 + int(dur[2]) * 60 + float(dur[3])
    return secs, int(size[1]), int(size[2])


def main():
    assert features.check("raqm"), "Pillow needs raqm to shape Arabic"
    src = Path(sys.argv[1])
    count = int(sys.argv[sys.argv.index("--count") + 1]) if "--count" in sys.argv else len(HOOKS)
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / "_layers"
    tmp.mkdir(exist_ok=True)
    dur, W, H = probe(src)
    logo(OUT / "logo_nouvella_casa.png")
    badge(W, H).save(tmp / "badge.png")
    cta(W, H).save(tmp / "cta.png")
    t_end = max(0.0, dur - 2.5)
    made = []
    for k, hook in enumerate(HOOKS[:count], 1):
        rtl_block(W, H, hook, 300, 64).save(tmp / f"hook_{k:02d}.png")
        dst = OUT / f"{src.stem}_hook_{k:02d}.mp4"
        flt = ("[0:v][1:v]overlay=0:0[a];"
               "[a][2:v]overlay=0:0:enable='lt(t,3)'[b];"
               f"[b][3:v]overlay=0:0:enable='gte(t,{t_end:.2f})'[v]")
        subprocess.run([FF, "-y", "-v", "error", "-i", str(src),
                        "-loop", "1", "-i", str(tmp / "badge.png"),
                        "-loop", "1", "-i", str(tmp / f"hook_{k:02d}.png"),
                        "-loop", "1", "-i", str(tmp / "cta.png"),
                        "-filter_complex", flt, "-map", "[v]", "-map", "0:a?",
                        "-t", f"{dur:.3f}", "-c:v", "libx264", "-crf", "24", "-preset", "medium",
                        "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
                        str(dst)], check=True)
        made.append({"file": dst.name, "hook": hook})
        print(dst.name, dst.stat().st_size)
    (OUT / "variants.json").write_text(json.dumps(made, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
