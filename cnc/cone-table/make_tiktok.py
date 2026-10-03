"""9:16 TikTok/Reels cut of the cone assembly - one video per hook (A/B test
the hook only: same footage, same captions, same end card).

    python3 make_tiktok.py           # needs out/anim/f_*.png (render_assembly.py)

Writes out/tiktok/cone_hook_<k>.mp4 (1080x1920, 30 fps, no music: add the
trending sound inside TikTok).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont, features

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import anim_timeline as A  # noqa: E402
import make_video as MV    # noqa: E402  (step captions)

W, H, FPS = 1080, 1920, 30
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
OUT = HERE / "out" / "tiktok"

HOOKS = [
    "هذا المخروط خرج كامل من لوحة MDF وحدة",
    "لوحة خشب مستوية… ولات مخروط",
    "السر تاع الأثاث المدور: هذي الشقوق",
]
END_TITLE = "قاعدة مخروطية 40 × 45 سم"
END_LINE = "خشب MDF سمك 18 مم، مقطوع بالـ CNC"
BRAND = "Nouvella Casa"
CTA = "اطلبها دروك في الخاص"

HOOK_S, END_S = 2.5, 3.0                  # hook card, end card (seconds)
ANIM_SPEED = 1.6                          # assembly plays 1.6x faster


def font(path, size):
    return ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)


def rtl(d, xy, text, f, fill, anchor="mm"):
    d.text(xy, text, font=f, fill=fill, anchor=anchor, direction="rtl", language="ar")


def wrap(d, text, f, width):
    return MV.lines(d, text, f, width)


def backdrop():
    im = Image.new("RGB", (W, H), (236, 233, 228))
    d = ImageDraw.Draw(im)
    for y in range(H):                     # soft vertical gradient
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(240 - 25 * t), int(237 - 27 * t), int(232 - 30 * t)))
    return im


def place_square(im, sq, top=420, size=1080):
    s = sq.resize((size, size), Image.LANCZOS)
    im.paste(s, ((W - size) // 2, top))


def headline(im, text, f, y=250, color=(25, 22, 20), box=False):
    d = ImageDraw.Draw(im, "RGBA")
    rows = wrap(d, text, f, W - 120)
    lh = f.size + 22
    y0 = y - lh * (len(rows) - 1) / 2
    if box:
        d.rounded_rectangle([40, y0 - lh / 2 - 20, W - 40, y0 + lh * (len(rows) - 0.5) + 20],
                            radius=36, fill=(25, 22, 20, 225))
        color = (255, 255, 255)
    for k, r in enumerate(rows):
        rtl(d, (W / 2, y0 + k * lh), r, f, color)


def caption_band(im, text, f, y=1640):
    d = ImageDraw.Draw(im, "RGBA")
    rows = wrap(d, text, f, W - 140)
    lh = f.size + 18
    h = lh * len(rows) + 40
    d.rounded_rectangle([50, y - h / 2, W - 50, y + h / 2], radius=30, fill=(25, 22, 20, 200))
    for k, r in enumerate(rows):
        rtl(d, (W / 2, y - h / 2 + 20 + lh * (k + 0.5)), r, f, (255, 255, 255))


def frames(hook):
    anim = sorted((HERE / "out" / "anim").glob("f_*.png"))
    hero = Image.open(HERE / "out" / "render_hero.png").convert("RGB")
    # hero is 1200x1400: crop a square around the cone for the hook card
    hero_sq = hero.crop((0, 100, 1200, 1300))
    f_hook, f_cap = font(BOLD, 74), font(BOLD, 46)
    f_title, f_line, f_cta = font(BOLD, 70), font(REG, 42), font(BOLD, 60)

    # 1) hook: slow push-in on the finished cone, hook as the headline
    n = int(HOOK_S * FPS)
    for i in range(n):
        z = 1.0 + 0.06 * i / n
        c = hero_sq.width * (1 - 1 / z) / 2
        sq = hero_sq.crop((c, c, hero_sq.width - c, hero_sq.height - c))
        im = backdrop()
        place_square(im, sq)
        headline(im, hook, f_hook, y=260, box=True)
        yield im

    # 2) assembly, sped up, with the step captions from the long video
    n = int(len(anim) / ANIM_SPEED / 24 * FPS)
    for i in range(n):
        k = min(len(anim) - 1, int(i * ANIM_SPEED * 24 / FPS))
        im = backdrop()
        place_square(im, Image.open(anim[k]).convert("RGB"))
        headline(im, hook, font(BOLD, 52), y=250)
        caption_band(im, MV.caption_for(k + 1), f_cap)
        yield im

    # 3) end card: finished cone, size, material, call to action
    last = Image.open(anim[-1]).convert("RGB")
    n = int(END_S * FPS)
    for i in range(n):
        im = backdrop()
        place_square(im, last, top=380, size=1000)
        d = ImageDraw.Draw(im, "RGBA")
        rtl(d, (W / 2, 190), END_TITLE, f_title, (25, 22, 20))
        rtl(d, (W / 2, 290), END_LINE, f_line, (90, 80, 70))
        d.text((W / 2, 1790), BRAND, font=font(BOLD, 44), fill=(90, 80, 70), anchor="mm")
        pulse = 1.0 + 0.04 * (1 if (i // 12) % 2 == 0 else 0)
        bw, bh = 760 * pulse, 130 * pulse
        d.rounded_rectangle([W / 2 - bw / 2, 1620 - bh / 2, W / 2 + bw / 2, 1620 + bh / 2],
                            radius=65, fill=(200, 70, 40, 255))
        rtl(d, (W / 2, 1620), CTA, f_cta, (255, 255, 255))
        yield im


def encode(hook, path):
    proc = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-v", "error",
                             "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                             "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                             str(path)], stdin=subprocess.PIPE)
    count = 0
    for im in frames(hook):
        proc.stdin.write(im.tobytes())
        count += 1
    proc.stdin.close()
    proc.wait()
    return count


def main():
    assert features.check("raqm"), "Pillow needs raqm to shape Arabic"
    OUT.mkdir(parents=True, exist_ok=True)
    for k, hook in enumerate(HOOKS, 1):
        p = OUT / f"cone_hook_{k}.mp4"
        n = encode(hook, p)
        print(p.name, n, "frames", round(n / FPS, 1), "s", p.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
