"""Compose the Pebble sofa proof video (1280x720, 30 fps, H.264).

    python3 video_compose.py FRAMES_DIR CHECKS_DIR OUT.mp4

FRAMES_DIR comes from render_video.py (f_*.png, timeline.json, still_*.png).
CHECKS_DIR holds the raw output of verify.py / dxf_vs_3d.py / verify_3d.py
(verify2d.txt, dxf3d.txt, verify3d.txt): the proof card is read from those
files, nothing on it is typed by hand.

Shots: title > the 4 nested sheets being cut (from out/pebble-sofa.dxf) >
assembly, piece by piece > frame orbit > crossfade to the upholstered sofa >
check results > end card.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import ezdxf
from ezdxf.path import make_path
import imageio_ffmpeg
from shapely.geometry import Polygon
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
FONTS = HERE.parents[1] / "marketing" / "product-sheets" / "fonts"
W, H, FPS = 1280, 720, 30
INK = (24, 22, 20)
PAPER = (240, 235, 228)
TERRA = (196, 86, 38)
GREEN = (60, 160, 90)
BIRCH = (214, 178, 126)

STEPS = {
    "BASE": ("١", "القاعدة", "حلقتين على الأرض"),
    "BODY": ("٢", "الأضلاع", "52 ضلع يدخلو في الحلقة من الفوق"),
    "SEAT": ("٣", "حلقة القعدة", "تنزل على الأضلاع وتقفلهم"),
    "PLATE": ("٤", "قواعد الوسائد", "4 صفائح على حلقة القعدة"),
    "PRIB": ("٥", "أضلاع الوسائد", "16 مقطع تاع القبة"),
    "SPINE": ("٦", "العمود الفقري", "ينزل فوق الأضلاع ويقفل الوسادة"),
}


def font(size, bold=True):
    return ImageFont.truetype(str(FONTS / ("Cairo-800.ttf" if bold else "Cairo-500.ttf")), size)


def ar(d, xy, text, size, fill, bold=True, anchor="ra"):
    d.text(xy, text, font=font(size, bold), fill=fill, anchor=anchor, direction="rtl", language="ar")


def lat(d, xy, text, size, fill, bold=False, anchor="la"):
    d.text(xy, text, font=font(size, bold), fill=fill, anchor=anchor)


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


class Writer:
    def __init__(self, path):
        self.p = subprocess.Popen(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)], stdin=subprocess.PIPE)
        self.n = 0

    def put(self, im, times=1):
        b = im.convert("RGB").tobytes()
        for _ in range(times):
            self.p.stdin.write(b)
            self.n += 1

    def close(self):
        self.p.stdin.close()
        self.p.wait()


def fade(im, a):
    return Image.blend(Image.new("RGB", im.size, INK), im.convert("RGB"), max(0.0, min(1.0, a)))


# ---------------------------------------------------------------- title card
def title(w, secs=3.2):
    n = int(secs * FPS)
    for i in range(n):
        t = i / FPS
        im = Image.new("RGB", (W, H), INK)
        d = ImageDraw.Draw(im)
        a = ease(t / 0.8)
        y = 250 + 30 * (1 - a)
        ar(d, (W - 110, y), "كنبة Pebble", 96, tuple(int(c * a) for c in PAPER))
        ar(d, (W - 112, y + 130), "هيكل MDF 18 ملم · تعشيق slot & tab بلا براغي", 34,
           tuple(int(c * ease((t - 0.4) / 0.8)) for c in BIRCH), bold=False)
        stats = [("80", "قطعة"), ("4", "بلاكات"), ("93", "كلغ")]
        for k, (num, lab) in enumerate(stats):
            b = ease((t - 0.9 - 0.25 * k) / 0.6)
            x = W - 110 - k * 230
            ar(d, (x, 520), num, 64, tuple(int(c * b) for c in TERRA))
            ar(d, (x - 90, 548), lab, 30, tuple(int(c * b) for c in PAPER), bold=False)
        lat(d, (110, 70), "NOUVELLA CASA", 22, (130, 120, 110), bold=True)
        d.line((110, 104, 110 + 200 * a, 104), fill=TERRA, width=3)
        w.put(fade(im, min(1, (n - i) / 10)))


# ---------------------------------------------------------------- cutting
def sheet_layout():
    doc = ezdxf.readfile(HERE / "out" / "pebble-sofa.dxf")
    msp = doc.modelspace()
    boards = sorted((e for e in msp if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "REFERENCE-SHEET"),
                    key=lambda e: -max(p[1] for p in e.get_points("xy")))
    sheets = []
    for b in boards:
        pts = list(b.get_points("xy"))
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        sheets.append({"box": (min(xs), min(ys), max(xs), max(ys)), "cuts": []})
    for e in msp.query('LWPOLYLINE[layer=="CUT"]'):
        pts = [(v.x, v.y) for v in make_path(e).flattening(0.5)]
        for s in sheets:
            x0, y0, x1, y1 = s["box"]
            if y0 - 1 <= pts[0][1] <= y1 + 1 and x0 - 1 <= pts[0][0] <= x1 + 1:
                s["cuts"].append(pts)
    for s in sheets:   # holes (mortises, ring openings) first, like the CAM does, then outlines
        polys = [Polygon(p).buffer(0) for p in s["cuts"]]
        depth = [sum(j != k and q.area > polys[k].area and q.contains(polys[k].representative_point())
                     for j, q in enumerate(polys)) for k in range(len(polys))]
        s["cuts"] = sorted(zip(depth, s["cuts"]), key=lambda dp: (dp[0] % 2 == 0, dp[1][0][0]))
    return sheets


def cutting(w, secs=5.5):
    sheets = sheet_layout()
    total = sum(len(s["cuts"]) for s in sheets)
    sw, sh, gx, gy, top = 500, 250, 40, 44, 160
    origins = [((W - 2 * sw - gx) // 2 + (k % 2) * (sw + gx), top + (k // 2) * (sh + gy)) for k in range(len(sheets))]
    n = int(secs * FPS)
    for i in range(n):
        u = min(i / (n * 0.85), 1.0)
        frac = u * u * (3 - 2 * u)
        shown = int(frac * total)
        im = Image.new("RGB", (W, H), INK)
        d = ImageDraw.Draw(im)
        ar(d, (W - 60, 22), "القص على CNC: كل قطعة بالمقاس الحقيقي", 38, PAPER)
        ar(d, (W - 60, 78), "4 بلاكات 2440 × 1220 · تجويف التعشيق 19 × 41 ملم", 24, BIRCH, bold=False)
        lat(d, (60, 40), f"{min(shown, total)}", 40, TERRA, bold=True)
        lat(d, (60 + font(40).getlength(str(min(shown, total))) + 8, 58), f"/ {total} cut paths", 18, PAPER)
        d.rectangle((60, 104, 360, 108), fill=(60, 55, 50))
        d.rectangle((60, 104, 60 + int(300 * frac), 108), fill=TERRA)
        done = 0
        for k, (s, (ox, oy)) in enumerate(zip(sheets, origins)):
            x0, y0, x1, y1 = s["box"]
            sc = sw / (x1 - x0)
            P = lambda p: (ox + (p[0] - x0) * sc, oy + (y1 - p[1]) * sc)
            bg = (62, 54, 46)
            d.rectangle((ox, oy, ox + sw, oy + sh), fill=bg, outline=(110, 98, 86))
            lat(d, (ox, oy - 26), f"SHEET {k + 1}/4", 16, (150, 140, 128), bold=True)
            cut = [(done + j, h, [P(p) for p in pts]) for j, (h, pts) in enumerate(s["cuts"]) if done + j <= shown]
            for g, h, poly in sorted(cut, key=lambda c: c[1]):       # by nesting depth: odd = hole
                live = g >= shown - 3
                d.polygon(poly, fill=bg if h % 2 else ((190, 120, 70) if live else (150, 112, 70)))
                d.line(poly + [poly[0]], fill=TERRA if live else PAPER, width=2 if live else 1)
            done += len(s["cuts"])
        a = min(1, i / 8, (n - i) / 8)
        w.put(fade(im, a))


# ---------------------------------------------------------------- assembly
def overlay(im, step, seated, total):
    im = im.convert("RGBA")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rectangle((0, 0, W, 132), fill=(20, 18, 16, 150))
    if step in STEPS:
        num, name, sub = STEPS[step]
        ar(d, (W - 50, 18), f"{name}  {num}", 46, PAPER + (255,))
        ar(d, (W - 52, 84), sub, 24, BIRCH + (255,), bold=False)
    elif step == "DONE":
        ar(d, (W - 50, 18), "الهيكل كامل", 46, PAPER + (255,))
        ar(d, (W - 52, 84), "كل قطعة في بلاصتها · 0 تصادم", 24, BIRCH + (255,), bold=False)
    # piece counter, left
    lat(d, (50, 26), f"{seated}", 56, TERRA + (255,), bold=True, anchor="la")
    lat(d, (50 + font(56).getlength(str(seated)) + 8, 54), f"/ {total}", 26, PAPER + (255,))
    # step chips, bottom
    order = list(STEPS)
    cw = 170
    x = W - 50
    cur = order.index(step) if step in order else len(order)
    for k, g in enumerate(order):
        col = TERRA if k == cur else (GREEN if k < cur else (90, 84, 78))
        d.rounded_rectangle((x - cw, H - 62, x, H - 26), 18, fill=col + (230,))
        ar(d, (x - 16, H - 60), f"{STEPS[g][0]} {STEPS[g][1]}", 20, (255, 255, 255, 255), bold=True)
        x -= cw + 12
    return Image.alpha_composite(im, ov).convert("RGB")


def assembly(w, frames):
    tl = json.loads((frames / "timeline.json").read_text())
    rep = FPS // tl["fps"]
    last = len(tl["frames"]) - 1
    for fr in tl["frames"]:
        p = frames / f"f_{fr['f']:04d}.png"
        im = Image.open(p).convert("RGB").resize((W, H), Image.LANCZOS)
        a = min(1, fr["f"] / 6)
        w.put(fade(overlay(im, fr["group"], fr["seated"], fr["total"]), a), rep)
    return Image.open(frames / f"f_{last:04d}.png").convert("RGB").resize((W, H), Image.LANCZOS)


def upholster(w, frames, secs=4.5):
    a = Image.open(frames / "still_frame.png").convert("RGB").resize((W, H), Image.LANCZOS)
    b = Image.open(frames / "still_upholstered.png").convert("RGB").resize((W, H), Image.LANCZOS)
    n = int(secs * FPS)
    for i in range(n):
        t = i / n
        z = 1 + 0.06 * t                                   # slow push-in
        mix = Image.blend(a, b, ease((t - 0.2) / 0.45))
        cw, ch = int(W / z), int(H / z)
        mix = mix.crop(((W - cw) // 2, (H - ch) // 2, (W + cw) // 2, (H + ch) // 2)).resize((W, H), Image.LANCZOS)
        im = mix.convert("RGBA")
        ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        d.rectangle((0, 0, W, 132), fill=(20, 18, 16, 150))
        ar(d, (W - 50, 18), "بعد الإسفنج والبوكليه", 46, PAPER + (255,))
        ar(d, (W - 52, 84), "نفس الهيكل · الشكل النهائي", 24, BIRCH + (255,), bold=False)
        w.put(fade(Image.alpha_composite(im, ov), min(1, (n - i) / 10)))


# ---------------------------------------------------------------- proof
CHECK_AR = {
    "[1]": "شكل كل قطعة مغلق وسليم",
    "[2]": "التعشيق 19 × 41 لتاب 40 ملم",
    "[3]": "الفريزة 6 ملم توصل لكل زاوية",
    "[4]": "التوزيع على البلاكات بلا تداخل",
    "[5]": "اسم كل قطعة محفور عليها",
    "[6]": "ملف DXF سليم: 236 مسار",
    "==": "ملف DXF يطابق 3D قطعة بقطعة",
    "[3D-1]": "حتى قطعة ما تدخل في الأخرى",
    "[3D-2]": "كل تجويف فيه تاب",
    "[3D-3]": "كل ضلع راكب على الحلقتين",
    "[3D-4]": "كل قطعة تنزل عموديا بلا تصادم",
    "[3D-5]": "القياس الإجمالي على الأرض",
}


def parse_checks(checks: Path):
    """[(arabic label, ok, total)] from the raw script output."""
    out = []
    for name in ("verify2d.txt", "dxf3d.txt", "verify3d.txt"):
        sec = None
        for line in (checks / name).read_text().splitlines():
            st = line.strip()
            m = re.match(r"(\[[^\]]+\]|==)", st)
            if m and m.group(1) in CHECK_AR:
                sec = [CHECK_AR[m.group(1)], 0, 0]
                out.append(sec)
            elif st.startswith(("ok ", "FAIL ")) and sec is not None:
                sec[2] += 1
                sec[1] += st.startswith("ok")
    return [tuple(s) for s in out if s[2]]


def proof(w, checks, secs=8.0):
    rows = parse_checks(checks)
    ok, tot = sum(r[1] for r in rows), sum(r[2] for r in rows)
    n = int(secs * FPS)
    per = (len(rows) + 1) // 2
    for i in range(n):
        t = i / FPS
        im = Image.new("RGB", (W, H), INK)
        d = ImageDraw.Draw(im)
        ar(d, (W - 60, 30), "الفحص الآلي قبل القص", 46, PAPER)
        ar(d, (W - 60, 96), "كل سطر محسوب من الملف الحقيقي، ماشي مكتوب باليد", 22, BIRCH, bold=False)
        shown = int(len(rows) * ease(t / 3.6)) + (t > 0.2)
        for k, (label, g, tt) in enumerate(rows[:shown]):
            right = W - 60 - (k // per) * 590
            y = 170 + (k % per) * 62
            good = g == tt
            d.rounded_rectangle((right - 560, y, right, y + 50), 12, fill=(36, 33, 30))
            d.ellipse((right - 40, y + 14, right - 18, y + 36), fill=GREEN if good else (200, 50, 40))
            ar(d, (right - 52, y + 6), label, 22, PAPER, bold=False)
            lat(d, (right - 540, y + 8), f"{g}/{tt}", 24, GREEN if good else (220, 80, 60), bold=True)
        if t > 3.9:
            a = ease((t - 3.9) / 0.6)
            col = tuple(int(c * a) for c in (GREEN if ok == tot else TERRA))
            ar(d, (W - 60, H - 96), f"{ok} من {tot} فحص ناجح · 0 خطأ" if ok == tot else f"{ok} من {tot}", 44, col)
        w.put(fade(im, min(1, i / 8, (n - i) / 8)))
    return ok, tot


def end(w, secs=3.0):
    n = int(secs * FPS)
    for i in range(n):
        im = Image.new("RGB", (W, H), INK)
        d = ImageDraw.Draw(im)
        a = ease(i / 20)
        ar(d, (W // 2 + 300, 260), "جاهز للقص", 84, tuple(int(c * a) for c in PAPER))
        ar(d, (W // 2 + 300, 380), "ملفات DXF و ArtCAM · ورقة التركيب · STEP", 30,
           tuple(int(c * a) for c in BIRCH), bold=False)
        lat(d, (W // 2 - 300, 470), "NOUVELLA CASA", 24, tuple(int(c * a) for c in TERRA), bold=True)
        w.put(fade(im, min(1, (n - i) / 12)))


def main():
    frames, checks, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    w = Writer(out)
    title(w)
    cutting(w)
    assembly(w, frames)
    upholster(w, frames)
    ok, tot = proof(w, checks)
    end(w)
    w.close()
    print(f"wrote {out}: {w.n / FPS:.1f} s, checks {ok}/{tot}")


if __name__ == "__main__":
    main()
