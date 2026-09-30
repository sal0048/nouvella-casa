"""Nouvella Casa — vertical 9:16 ad (French overlays) built from one product photo.

Usage:  python3 make_video.py  ->  nouvella_casa_salon_fr.mp4
Needs:  pip install pillow numpy imageio-ffmpeg
"""
import math
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).parent
W, H, FPS = 1080, 1920, 30
XFADE = 0.5  # seconds of crossfade between shots
SRC = Image.open(HERE / "assets/salon.png").convert("RGB")
SW, SH = SRC.size

F = lambda name, size: ImageFont.truetype(str(HERE / "fonts" / name), size)
SERIF = "playfair-display-latin-500-normal.woff"
SERIF_I = "playfair-display-latin-400-italic.woff"
SANS = "montserrat-latin-400-normal.woff"
SANS_B = "montserrat-latin-600-normal.woff"
GOLD = (214, 184, 140)

# Each shot: duration, camera start/end (center x, center y, crop height in source px), text lines.
SHOTS = [
    dict(d=3.0, a=(627, 640, 1254), b=(627, 640, 1254), kind="intro"),
    dict(d=3.2, a=(360, 627, 1254), b=(900, 627, 1254),
         title="Le salon qui change tout", sub="Design contemporain · Confort absolu"),
    dict(d=3.0, a=(820, 500, 700), b=(830, 510, 560),
         title="Des détails qui font la différence", sub="Coussins texturés, tons chauds"),
    dict(d=3.0, a=(690, 830, 760), b=(740, 820, 620),
         title="L'art de recevoir", sub="Une table basse aux lignes arrondies"),
    dict(d=3.0, a=(300, 680, 640), b=(330, 700, 780),
         title="Doux au toucher", sub="Un tissu texturé qui invite à se poser"),
    dict(d=3.0, a=(1010, 640, 820), b=(960, 650, 820),
         title="Pensé pour votre espace", sub="Un angle généreux, une allure moderne"),
    dict(d=3.3, a=(640, 660, 820), b=(627, 640, 1254),
         title="Plus qu'un meuble…", sub="un art de vivre."),
    dict(d=4.5, a=(627, 640, 1254), b=(627, 640, 1100), kind="outro"),
]


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


def camera(shot, t):
    k = ease(t)
    cx, cy, ch = (a + (b - a) * k for a, b in zip(shot["a"], shot["b"]))
    cw = ch * W / H
    x0 = min(max(cx - cw / 2, 0), SW - cw)
    y0 = min(max(cy - ch / 2, 0), SH - ch)
    img = SRC.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))
    return img.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))


def gradient(top_alpha, bottom_alpha, start=0.55):
    g = np.zeros((H, 1), np.float32)
    ys = np.linspace(0, 1, H)
    top = top_alpha * np.clip(1 - ys / 0.22, 0, 1)
    bottom = bottom_alpha * np.clip((ys - start) / (1 - start), 0, 1) ** 1.3
    g[:, 0] = top + bottom
    a = (np.clip(g, 0, 1) * 255).astype(np.uint8).repeat(W, 1)
    over = Image.new("RGBA", (W, H), (12, 10, 9, 0))
    over.putalpha(Image.fromarray(a))
    return over


BOTTOM_GRAD = gradient(0.35, 0.85)


def text_c(draw, y, s, font, fill, alpha, spacing=0, shadow=True):
    if alpha <= 0:
        return
    if spacing:
        widths = [draw.textlength(c, font=font) for c in s]
        total = sum(widths) + spacing * (len(s) - 1)
        x = (W - total) / 2
        for c, w in zip(s, widths):
            draw.text((x, y), c, font=font, fill=fill + (int(255 * alpha),))
            x += w + spacing
        return
    x = (W - draw.textlength(s, font=font)) / 2
    if shadow:
        draw.text((x + 2, y + 3), s, font=font, fill=(0, 0, 0, int(140 * alpha)))
    draw.text((x, y), s, font=font, fill=fill + (int(255 * alpha),))


def wrap(draw, s, font, maxw):
    words, lines, cur = s.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if draw.textlength(t, font=font) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w_
    return lines + [cur]


def fade(t, d, t_in=0.35, t_out=0.3, delay=0.2):
    return max(0.0, min(1.0, (t - delay) / t_in, (d - t) / t_out))


def brand_mark(draw, alpha, y=110, big=False):
    s = 1.0 if not big else 1.9
    text_c(draw, y, "NC", F(SERIF, int(64 * s)), GOLD, alpha, shadow=False)
    text_c(draw, y + int(92 * s), "NOUVELLA CASA", F(SERIF, int(38 * s)), (245, 240, 232), alpha,
           spacing=int(6 * s), shadow=False)
    text_c(draw, y + int(145 * s), "MODERN FURNITURE", F(SANS, int(18 * s)), (225, 215, 200), alpha,
           spacing=int(7 * s), shadow=False)


def overlay(shot, t, d):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    kind = shot.get("kind")
    if kind == "intro":
        dim = Image.new("RGBA", (W, H), (12, 10, 9, int(255 * (0.62 - 0.22 * ease(t / d)))))
        layer.alpha_composite(dim)
        a = fade(t, d, 0.8, 0.5, 0.2)
        brand_mark(dr, a, y=int(700 - 20 * ease(t / d)), big=True)
        return layer
    if kind == "outro":
        dim = Image.new("RGBA", (W, H), (12, 10, 9, int(255 * min(0.78, 0.78 * t / 0.6))))
        layer.alpha_composite(dim)
        brand_mark(dr, fade(t, d, 0.6, 0.01, 0.3), y=330, big=True)
        a2 = fade(t, d, 0.5, 0.01, 1.0)
        for i, s in enumerate(["Qualité garantie", "Livraison rapide", "Disponible partout en Algérie"]):
            text_c(dr, 1000 + i * 70, "—  " + s + "  —", F(SANS, 36), (240, 235, 226), a2)
        a3 = fade(t, d, 0.5, 0.01, 1.8)
        if a3 > 0:
            bw, bh, by = 720, 110, 1330
            dr.rounded_rectangle(((W - bw) / 2, by, (W + bw) / 2, by + bh), radius=55,
                                 fill=GOLD + (int(255 * a3),))
            text_c(dr, by + 34, "COMMANDEZ MAINTENANT", F(SANS_B, 38), (25, 20, 16), a3, shadow=False)
            text_c(dr, by + 150, "Écrivez-nous en message privé", F(SERIF_I, 40), (240, 235, 226), a3)
        return layer
    layer.alpha_composite(BOTTOM_GRAD)

    a = fade(t, d)
    rise = int(30 * (1 - ease(a)))
    tf = F(SERIF, 76)
    lines = wrap(dr, shot["title"], tf, W - 140)
    y = 1440 - 90 * (len(lines) - 1) + rise
    for ln in lines:
        text_c(dr, y, ln, tf, (250, 246, 240), a)
        y += 92
    dr.line(((W - 120) / 2, y + 22, (W + 120) / 2, y + 22), fill=GOLD + (int(255 * a),), width=3)
    a2 = fade(t, d, delay=0.45)
    text_c(dr, y + 50, shot["sub"], F(SERIF_I if kind is None and shot["title"].endswith("…") else SANS, 40),
           (235, 228, 218), a2)
    return layer


def render(shot, t):
    base = camera(shot, t / shot["d"]).convert("RGBA")
    base.alpha_composite(overlay(shot, t, shot["d"]))
    return np.asarray(base.convert("RGB"), dtype=np.float32)


def main():
    out = HERE / "nouvella_casa_salon_fr.mp4"
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    xf = int(XFADE * FPS)
    for i, shot in enumerate(SHOTS):
        n = int(shot["d"] * FPS)
        nxt = SHOTS[i + 1] if i + 1 < len(SHOTS) else None
        start = xf if i > 0 else 0  # first xf frames were already blended into previous shot
        for f in range(start, n):
            t = f / FPS
            frame = render(shot, t)
            if nxt and f >= n - xf:
                k = (f - (n - xf) + 1) / (xf + 1)
                frame = frame * (1 - k) + render(nxt, (f - (n - xf)) / FPS) * k
            p.stdin.write(frame.clip(0, 255).astype(np.uint8).tobytes())
    p.stdin.close()
    p.wait()
    print("wrote", out)


if __name__ == "__main__":
    main()
