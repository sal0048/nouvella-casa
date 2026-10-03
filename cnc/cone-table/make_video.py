"""Add Darija step captions to out/anim/f_*.png and encode out/cone_assembly.mp4.

    python3 make_video.py            # needs Pillow with raqm (Arabic shaping), imageio-ffmpeg
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont, features

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import anim_timeline as A  # noqa: E402

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
S = dict(A.STEPS)

# (first frame, caption) - each caption holds until the next one
CAPTIONS = [
    (1, "الخطوة 1: حط الدائرة التحتانية على الأرض"),
    (S["CORE-1A"], "الخطوة 2: دخل اللوحتين في بعضهم (+) وفي الدائرة"),
    (S["FORMER-JOINT-LO"], "الخطوة 3: حط الدائرة الوسطانية فوق التنبات"),
    (S["FORMER-JOINT-UP"], "الخطوة 4: الصق الدائرة الثانية فوقها"),
    (S["CORE-2A"], "الخطوة 5: الطبقة الثانية تاع (+) مدورة 45 درجة"),
    (S["FORMER-TOP"], "الخطوة 6: سكر الفوق بالدائرة الصغيرة"),
    (A.WRAP0, "الخطوة 7: لف الغلاف والصقو على حواف الدواير"),
    (A.WRAP1 + 6, "خلاص: المخروط 40 × 16 × 45 سم، MDF 18"),
]


def caption_for(frame: int) -> str:
    text = CAPTIONS[0][1]
    for f, t in CAPTIONS:
        if frame >= f:
            text = t
    return text


def lines(d, text, font, width):
    """Greedy word wrap, measured with the shaped RTL text."""
    out, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and d.textlength(trial, font=font, direction="rtl", language="ar") > width:
            out.append(cur)
            cur = word
        else:
            cur = trial
    return out + [cur]


def caption(im, text, font):
    w, h = im.size
    d = ImageDraw.Draw(im, "RGBA")
    rows = lines(d, text, font, w - 40)
    band = 22 + 40 * len(rows)
    d.rectangle([0, h - band, w, h], fill=(20, 20, 20, 190))
    for k, row in enumerate(rows):
        tw = d.textlength(row, font=font, direction="rtl", language="ar")
        d.text(((w - tw) / 2, h - band + 10 + 40 * k), row, font=font,
               fill=(255, 255, 255), direction="rtl", language="ar")


def main():
    frames = sorted((HERE / "out" / "anim").glob("f_*.png"))
    out_dir = HERE / "out" / "anim_captioned"
    out_dir.mkdir(exist_ok=True)
    assert features.check("raqm"), "Pillow needs raqm to shape Arabic"
    font = ImageFont.truetype(FONT, 28, layout_engine=ImageFont.Layout.RAQM)
    for i, path in enumerate(frames, 1):
        im = Image.open(path).convert("RGB")
        caption(im, caption_for(i), font)
        im.save(out_dir / f"c_{i:04d}.png")
    mp4 = HERE / "out" / "cone_assembly.mp4"
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-v", "error",
                    "-framerate", str(A.FPS), "-i", str(out_dir / "c_%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                    "-movflags", "+faststart", str(mp4)], check=True)
    print(mp4, mp4.stat().st_size, "bytes,", len(frames), "frames")


if __name__ == "__main__":
    main()
