"""Product presentation sheets for our CNC technical files.

    python3 make_sheets.py cone-table [sheet ...]
    python3 make_sheets.py round-armchair
    python3 make_sheets.py all

Layout follows the reference set in ref/ (cover, six square sheets, three A4
technical pages) with Nouvella Casa branding. Every number printed comes from
products.py, which reads it from the product's own cut files and data and
asserts it against the 3D checks. Renders are transparent PNGs from each
product's Blender script (cnc/<product>/out/sheets/).
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import ezdxf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "cnc" / "cone-table"))
import audit_dxf as A  # noqa: E402
import products  # noqa: E402

FD = HERE / "fonts"
P: dict = {}                 # the product being drawn (set in main)

HANDLE = "@nouvella_casa"
BRAND = "Nouvella Casa"
INK = (24, 22, 20)
PAPER = (247, 246, 242)
RED = (200, 16, 30)
OLIVE = (128, 122, 88)
DEEP = (52, 44, 38)          # cover background (warm dark brown)
SAND = (236, 226, 212)
ACCENT = (200, 70, 40)


def F(weight, size):
    return ImageFont.truetype(str(FD / f"Poppins-{weight}.ttf"), size)


def cm(x):
    return f"{x:g}"


# ---------------------------------------------------------------- pieces
def render(view):
    """Transparent render cropped to the object (faint shadow-catcher alpha ignored)."""
    im = Image.open(P["ren"] / f"{P['views'][view]}.png").convert("RGBA")
    return im.crop(im.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox())


def fit(im, w, h):
    s = min(w / im.width, h / im.height)
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)


def put(canvas, im, cx, cy, w, h, shadow=True):
    """Paste an RGBA cut-out centred in a box, with a soft ground shadow."""
    im = fit(im, w, h)
    x, y = int(cx - im.width / 2), int(cy - im.height / 2)
    if shadow:
        sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).ellipse([x + im.width * 0.12, y + im.height - im.height * 0.035,
                                    x + im.width * 0.88, y + im.height + im.height * 0.035],
                                   fill=(0, 0, 0, 70))
        canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(im.width * 0.04)))
    canvas.alpha_composite(im, (x, y))
    return x, y, im.width, im.height


def cloudy(w, h, seed=3):
    """Light grey cloud backdrop (reference sheets 1-5)."""
    rnd = random.Random(seed)
    base = Image.new("RGB", (w, h), (238, 238, 238))
    d = ImageDraw.Draw(base)
    for _ in range(90):
        r = rnd.randint(w // 10, w // 3)
        x, y = rnd.randint(-r, w), rnd.randint(h // 3, h + r)
        g = rnd.randint(150, 205)
        d.ellipse([x - r, y - r * 0.6, x + r, y + r * 0.6], fill=(g, g, g))
    for _ in range(40):
        r = rnd.randint(w // 12, w // 4)
        x, y = rnd.randint(-r, w), rnd.randint(-r, h // 2)
        g = rnd.randint(215, 245)
        d.ellipse([x - r, y - r * 0.6, x + r, y + r * 0.6], fill=(g, g, g))
    base = base.filter(ImageFilter.GaussianBlur(w * 0.05))
    top = Image.new("RGB", (w, h), (250, 250, 250))
    mask = Image.linear_gradient("L").resize((w, h)).point(lambda v: 255 - int(v * 0.85))
    return Image.composite(top, base, mask).convert("RGBA")


def cone_icon(d, cx, cy, h, color, line):
    top, bot = h * 0.2, h * 0.46
    y0, y1 = cy - h / 2, cy + h / 2
    d.polygon([(cx - top, y0), (cx + top, y0), (cx + bot, y1), (cx - bot, y1)], fill=color)
    for k in range(-3, 4):
        f = k / 3.5
        d.line([(cx + f * top, y0 + 3), (cx + f * bot, y1 - 3)], fill=line, width=max(1, int(h / 60)))


def seal(size, fill=(40, 38, 36), fg=(255, 255, 255)):
    """Round brand seal: cone mark + NOUVELLA CASA + tagline."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, size - 1, size - 1], fill=fill)
    cone_icon(d, size / 2, size * 0.36, size * 0.34, fg, fill)
    d.text((size / 2, size * 0.64), "NOUVELLA CASA", font=F("SemiBold", int(size * 0.085)),
           fill=fg, anchor="mm")
    d.text((size / 2, size * 0.75), "C N C   F U R N I T U R E", font=F("Medium", int(size * 0.042)),
           fill=(*fg, 200), anchor="mm")
    d.text((size / 2, size * 0.82), "D E S I G N", font=F("Medium", int(size * 0.042)),
           fill=(*fg, 200), anchor="mm")
    return im


def insta(d, x, y, s, color=INK):
    """Instagram-style glyph drawn from primitives (rounded square, lens, dot)."""
    w = max(2, int(s * 0.09))
    d.rounded_rectangle([x, y, x + s, y + s], radius=s * 0.28, outline=color, width=w)
    d.ellipse([x + s * 0.28, y + s * 0.28, x + s * 0.72, y + s * 0.72], outline=color, width=w)
    r = s * 0.06
    d.ellipse([x + s * 0.74 - r, y + s * 0.26 - r, x + s * 0.74 + r, y + s * 0.26 + r], fill=color)


def vtext(canvas, text, x, y, font, fill=INK, anchor_bottom=True):
    """Text rotated 90 deg (reads bottom-to-top), placed with its left edge at x."""
    bb = font.getbbox(text)
    im = Image.new("RGBA", (bb[2] + 10, bb[3] + 10), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((5, 5), text, font=font, fill=fill)
    im = im.rotate(90, expand=True)
    canvas.alpha_composite(im, (int(x), int(y - im.height if anchor_bottom else y)))
    return im.size


def wrap(d, text, font, width):
    rows, cur = [], ""
    for w in text.split():
        t = f"{cur} {w}".strip()
        if cur and d.textlength(t, font=font) > width:
            rows.append(cur)
            cur = w
        else:
            cur = t
    return rows + [cur]


def para(d, text, x, y, width, font, fill=INK, gap=1.35, align="left"):
    for k, r in enumerate(wrap(d, text, font, width)):
        xx = x + (width - d.textlength(r, font=font)) if align == "right" else x
        d.text((xx, y + k * font.size * gap), r, font=font, fill=fill)
    return y + len(wrap(d, text, font, width)) * font.size * gap


def bullets(d, items, x, y, font, color=(40, 110, 200)):
    for k, t in enumerate(items):
        yy = y + k * font.size * 1.45
        c = (x + font.size * 0.3, yy + font.size * 0.62)
        s = font.size * 0.22
        d.polygon([(c[0], c[1] - s), (c[0] + s, c[1]), (c[0], c[1] + s), (c[0] - s, c[1])], fill=color)
        d.text((x + font.size * 1.0, yy), t, font=font, fill=INK)


def header(canvas, w, sub=None):
    sub = sub or f"{P['name']} {P['kind']}"
    d = ImageDraw.Draw(canvas)
    d.text((90, 70), sub, font=F("Bold", 24), fill=INK)
    d.line([(0, 104), (w * 0.69, 104)], fill=(28, 30, 60), width=3)
    d.text((w - 110, 100), HANDLE, font=F("Medium", 22), fill=INK, anchor="rm")


def nest(path, board, w, h, line=(70, 70, 70), board_line=(90, 90, 90), kerf=(150, 150, 150)):
    """Draw one board of the real cut file (board outline, cut loops, kerf pockets),
    fitted to w x h. Boards are the BOARD-* / REFERENCE-SHEET rectangles, left to right."""
    doc = ezdxf.readfile(path)
    boards, loops = [], {"CUT": [], "POCKET": []}
    for e in doc.modelspace():
        if e.dxftype() != "LWPOLYLINE":
            continue
        pts = A.loop_points(e, seg=2.0)
        if e.dxf.layer.startswith(("BOARD", "REFERENCE-SHEET")):
            boards.append(pts)
        elif e.dxf.layer.split("-")[0] in loops:
            loops[e.dxf.layer.split("-")[0]].append(pts)
    # sheet order as the files lay them out: left to right, then top to bottom
    # (the round-armchair nest stacks SHEET 1/2 above SHEET 2/2)
    boards.sort(key=lambda l: (round(min(p[0] for p in l)), -max(p[1] for p in l)))
    bl = boards[board]
    x0, y0 = min(p[0] for p in bl), min(p[1] for p in bl)
    bw, bh = max(p[0] for p in bl) - x0, max(p[1] for p in bl) - y0

    def inside(l):
        cx, cy = l[0]
        return x0 - 1 <= cx <= x0 + bw + 1 and y0 - 1 <= cy <= y0 + bh + 1

    rot = bw > bh and h > w          # portrait slot: stand the board up
    if rot:
        bw, bh = bh, bw
    s = min((w - 4) / bw, (h - 4) / bh)
    im = Image.new("RGBA", (int(bw * s) + 4, int(bh * s) + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def tf(p):
        x, y = p[0] - x0, p[1] - y0
        if rot:
            x, y = y, x
        return (2 + x * s, im.height - 2 - y * s)

    for key, col, wd in (("POCKET", kerf, 1), ("CUT", line, 2)):
        for l in loops[key]:
            if inside(l):
                d.line([tf(p) for p in l] + [tf(l[0])], fill=col, width=wd)
    d.line([tf(p) for p in bl] + [tf(bl[0])], fill=board_line, width=2)
    return im


def arrow(d, a, b, bend=0.35, color=INK, width=4):
    """Curved callout line from a (dot) to b (arrow head)."""
    (x0, y0), (x1, y1) = a, b
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    nx, ny = -(y1 - y0), (x1 - x0)
    cx, cy = mx + nx * bend, my + ny * bend
    pts = [((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1,
            (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1) for t in [i / 40 for i in range(41)]]
    d.line(pts, fill=color, width=width, joint="curve")
    r = width * 2.2
    d.ellipse([x0 - r, y0 - r, x0 + r, y0 + r], fill=color)
    ang = math.atan2(y1 - pts[-3][1], x1 - pts[-3][0])
    L = width * 6
    d.polygon([(x1, y1), (x1 - L * math.cos(ang - 0.4), y1 - L * math.sin(ang - 0.4)),
               (x1 - L * math.cos(ang + 0.4), y1 - L * math.sin(ang + 0.4))], fill=color)


def footer_social(canvas, w, h, dark=INK):
    d = ImageDraw.Draw(canvas)
    s = int(w * 0.04)
    insta(d, w - 110 - s - d.textlength(HANDLE, font=F("SemiBold", int(s * 0.62))) - 14, h - 70 - s, s, dark)
    d.text((w - 110, h - 70 - s / 2), HANDLE, font=F("SemiBold", int(s * 0.62)), fill=dark, anchor="rm")


# ---------------------------------------------------------------- sheets
def s_cover():
    W = 1600
    c = Image.new("RGBA", (W, W), (*DEEP, 255))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle([70, 92, 440, 178], radius=12, fill=(245, 243, 238))
    d.text((255, 135), "SHOP NOW", font=F("Bold", 50), fill=DEEP, anchor="mm")
    d.text((140, 300), "TECHNICAL", font=F("SemiBold", 86), fill=(245, 243, 238))
    d.text((190, 395), "FILES.", font=F("SemiBold", 86), fill=(245, 243, 238))
    put(c, render("exploded"), 1010, 560, 560, 860, shadow=False)
    c.alpha_composite(seal(300), (1270, 60))
    put(c, render("finished"), 430, 1060, 640, 760)
    d.text((1480, 1000), P["name"], font=F("SemiBold", 150), fill=(245, 243, 238), anchor="rm")
    kind, size = f"{P['kind'].lower()}.", 150
    while F("SemiBold", size).getlength(kind) > 680:      # keep clear of the render on the left
        size -= 6
    d.text((1480, 1160), kind, font=F("SemiBold", size), fill=(245, 243, 238), anchor="rm")
    d.text((1480, 1290), P["cover_line"],
           font=F("Medium", 40), fill=SAND, anchor="rm")
    insta(d, 70, 1470, 64, (245, 243, 238))
    d.text((160, 1502), HANDLE, font=F("Medium", 44), fill=(245, 243, 238), anchor="lm")
    d.text((1510, 1502), BRAND, font=F("Medium", 44), fill=(245, 243, 238), anchor="rm")
    return c


def s1():
    W = 1080
    c = cloudy(W, W, 3)
    d = ImageDraw.Draw(c)
    put(c, render("finished"), 330, 330, 420, 440)
    put(c, render("cutaway"), 890, 190, 220, 260)
    bullets(d, P["bullets"], 640, 350, F("SemiBold", 27))
    d.text((70, 560), P["name"], font=F("ExtraBold", 190), fill=(0, 0, 0))
    d.text((520, 790), P["kind"], font=F("Bold", 42), fill=(0, 0, 0), anchor="rm")
    put(c, render("skeleton"), 800, 740, 380, 400)
    d.text((70, 1000), BRAND, font=F("SemiBold", 26), fill=INK, anchor="lm")
    d.text((990, 1000), HANDLE, font=F("SemiBold", 26), fill=INK, anchor="rm")
    return c


def s2():
    W = 1080
    c = cloudy(W, W, 5)
    header(c, W)
    d = ImageDraw.Draw(c)
    put(c, render("finished"), 330, 470, 400, 560)
    put(c, render("skeleton"), 780, 560, 380, 500)
    vtext(c, "Structure Wood.", 40, 900, F("SemiBold", 44))
    para(d, P["p_main"], 150, 860, 800, F("Medium", 25))
    footer_social(c, W, W)
    return c


def s3():
    W = 1080
    c = cloudy(W, W, 7)
    header(c, W)
    d = ImageDraw.Draw(c)
    put(c, render("cutaway"), 600, 480, 440, 600)
    vtext(c, "TECHNICAL FILE.", W - 110, 820, F("Bold", 48))
    para(d, P["p_joint"], 80, 190, 250, F("Medium", 23))
    para(d, P["p_file"], 90, 820, 820, F("Medium", 25))
    footer_social(c, W, W)
    return c


def s4():
    W = 1080
    c = cloudy(W, W, 11)
    header(c, W)
    d = ImageDraw.Draw(c)
    put(c, render("exploded"), 330, 560, 380, 800)
    put(c, render("top"), 780, 520, 380, 460)
    vtext(c, "Structure Wood.", 40, 900, F("SemiBold", 44))
    para(d, P["p_joint"], 590, 800, 400, F("Medium", 23))
    footer_social(c, W, W)
    return c


def s5():
    W = 1080
    c = cloudy(W, W, 13)
    header(c, W)
    put(c, render("skeleton"), 250, 380, 300, 400)
    put(c, render("top"), 560, 380, 300, 400)
    put(c, render("exploded"), 840, 560, 260, 800)
    put(c, render("cutaway"), 400, 780, 300, 360)
    c.alpha_composite(seal(140), (80, 860))
    vtext(c, "TECHNICAL FILE.", W - 80, 1000, F("Bold", 40))
    footer_social(c, W, W)
    return c


def s6():
    W = 1080
    fin = render("finished")
    c = Image.new("RGBA", (W, W), (238, 234, 228, 255))
    bg = fit(fin, 900, 900)
    bg.putalpha(bg.getchannel("A").point(lambda v: v * 0.22))
    c.alpha_composite(bg, ((W - bg.width) // 2 + 80, W - bg.height))
    header(c, W)
    d = ImageDraw.Draw(c)
    put(c, render("exploded"), 230, 330, 260, 440, shadow=False)
    c.alpha_composite(seal(330), (420, 170))
    vtext(c, "Structure Wood.", 880, 520, F("SemiBold", 44))
    vtext(c, "TECHNICAL FILE.", 950, 520, F("Bold", 50))
    for k, t in enumerate(P["board_lines"]):
        d.text((620, 590 + k * 50), t, font=F("Bold", 34), fill=(28, 30, 60), anchor="mm")
    x = 100
    for path, board, label in P["nests"]:
        n = nest(path, board, min(170, 430 // len(P["nests"]) - 30), 330)   # stay left of the contact block
        c.alpha_composite(n, (int(x), 690))
        d.text((x + n.width / 2, 1040), label, font=F("SemiBold", 22), fill=INK, anchor="mm")
        x += n.width + 30
    s = 64
    d.ellipse([560, 780, 560 + s, 780 + s], fill=(28, 30, 60))
    insta(d, 560 + 14, 780 + 14, s - 28, (255, 255, 255))
    d.text((640, 812), HANDLE.upper(), font=F("SemiBold", 36), fill=(28, 30, 60), anchor="lm")
    d.text((640, 890), "Order the file in DM", font=F("Medium", 30), fill=(28, 30, 60), anchor="lm")
    return c


def a4_frame(title):
    W, H = 1600, 2263
    c = Image.new("RGBA", (W, H), (*PAPER, 255))
    d = ImageDraw.Draw(c)
    d.rectangle([0, 968, 214, 2010], fill=(10, 10, 14))
    size = 150
    while F("Bold", size).getlength(title) > 880:
        size -= 4
    vtext(c, title, 60, 940, F("Bold", size), fill=(0, 0, 0))
    d.text((150, 2072), BRAND, font=F("SemiBold", 44), fill=(28, 30, 60), anchor="lm")
    d.text((150, 2150), HANDLE, font=F("Medium", 38), fill=(28, 30, 60), anchor="lm")
    d.text((980, 2158), f"Model :  {P['name']} {P['kind']}", font=F("Bold", 44), fill=INK, anchor="mm")
    insta(d, 1380, 2080, 120, INK)
    return c, d


def a_tech():
    c, d = a4_frame("Technical file")
    sk = put(c, render("skeleton"), 780, 560, 560, 760, shadow=False)
    fi = put(c, render("finished"), 830, 1500, 660, 900)
    lab = F("Bold", 44)
    box = {"sk": sk, "fi": fi}
    for text, (x, y), which, (fx, fy), bend, side in P["callouts"]:
        d.multiline_text((x, y), text, font=lab, fill=OLIVE, spacing=6)
        l, t, r, b = d.multiline_textbbox((x, y), text, font=lab, spacing=6)
        dot = {"right": (r + 30, (t + b) / 2), "left": (l - 25, (t + b) / 2),
               "below": (l + 60, b + 25), "top": (l + 180, t - 20)}[side]
        bx = box[which]
        arrow(d, dot, (bx[0] + bx[2] * fx, bx[1] + bx[3] * fy), bend=bend)
    d.text((1370, 140), "The Dimension:", font=F("Bold", 46), fill=RED, anchor="mm")
    for k, t in enumerate(P["dims"]):
        d.text((1370, 215 + k * 58), t, font=F("Bold", 40), fill=INK, anchor="mm")
    c.alpha_composite(seal(260), (1240, 215 + len(P["dims"]) * 58 + 40))
    d.text((1400, 1560), "The Material:", font=F("Bold", 46), fill=RED, anchor="mm")
    for k, t in enumerate(P["mat"]):
        d.text((1400, 1640 + k * 50), t, font=F("Bold", 38), fill=INK, anchor="mm")
    return c


def a_structure():
    c, d = a4_frame("Structure Wood")
    ex = put(c, render("exploded"), 700, 1000, 640, 1700, shadow=False)
    put(c, render("top"), 1300, 1560, 420, 520)
    d.text((1300, 160), "The Parts:", font=F("Bold", 46), fill=RED, anchor="mm")
    n = len(P["parts"])
    step, fnt = (54, F("SemiBold", 36)) if n <= 10 else (46, F("SemiBold", 30))
    for k, (num, name, qty) in enumerate(P["parts"]):
        d.text((1300, 240 + k * step), f"{num}  {name}" + (f"  x{qty}" if qty > 1 else ""),
               font=fnt, fill=INK, anchor="mm")
    y = 240 + n * step + 20
    d.text((1300, y), P["parts_line"], font=F("Bold", 38), fill=OLIVE, anchor="mm")
    c.alpha_composite(seal(240), (1180, int(y + 50)))
    return c


def a_files():
    c, d = a4_frame("Structure Wood")
    c.alpha_composite(seal(520), (300, 90))
    d.text((1180, 280), f"MDF : {P['board_mm']:g} mm", font=F("Bold", 76), fill=RED, anchor="mm")
    d.text((1180, 380), f"{cm(P['sheet'][0])}x{cm(P['sheet'][1])}  CM", font=F("Bold", 76), fill=RED,
           anchor="mm")
    step = 1260 / len(P["nests"])     # spread the boards over x 320..1580
    x = 320 + (step - min(460, step - 40)) / 2
    labels = []
    for path, board, label in P["nests"]:
        im = nest(path, board, int(min(460, step - 40)), 900)
        faint = im.copy()
        faint.putalpha(im.getchannel("A").point(lambda v: v * 0.55))
        c.alpha_composite(faint, (int(x), 780))
        labels.append((x + im.width / 2, 780 + im.height + 40, label))
        x += step
    fnt = F("Bold", 46)
    for k, t in enumerate(P["files"]):
        y = 760 + k * 230
        w = d.textlength(t, font=fnt)
        x = 960 - w / 2
        d.rectangle([x - 10, y - 8, x + w + 10, y + 62], fill=(*PAPER, 215))
        d.text((x, y), t, font=fnt, fill=INK)
        d.line([(x, y + 62), (x + w, y + 62)], fill=INK, width=4)
    for lx, ly, label in labels:
        d.text((lx, ly), label, font=F("SemiBold", 40), fill=INK, anchor="mm")
    return c


SHEETS = {"0_cover": s_cover, "1_hero": s1, "2_shell": s2, "3_cutaway": s3, "4_structure": s4,
          "5_views": s5, "6_technical-file": s6, "A1_technical": a_tech, "A2_structure": a_structure,
          "A3_files": a_files}

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    only = sys.argv[2:]
    for slug in (products.PRODUCTS if which == "all" else [which]):
        P.clear()
        P.update(products.PRODUCTS[slug]())
        out = HERE / "out" / slug
        out.mkdir(parents=True, exist_ok=True)
        for name, fn in SHEETS.items():
            if only and name not in only:
                continue
            fn().convert("RGB").save(out / f"{name}.jpg", quality=92)
        print(slug, "->", out.relative_to(HERE))
