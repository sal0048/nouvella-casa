"""Export every model's exact 3D frame for the web x-ray viewer (cnc/web/).

    python3 tools/web_export.py                 # all models
    python3 tools/web_export.py pebble lena     # some

Each model runs in its own process (the model folders reuse module names).
The frame comes from the model's own verified 3D assembly (the solids the
STEP files and the 3D checks use), tessellated as-is, so the viewer shows
exactly what the CNC cuts. Per model it writes
    cnc/web/models/<key>.bin.txt   float32 xyz (mm) then uint32 triangle indices
    cnc/web/models/<key>.json   pieces (label, stage, approach direction,
                                 vertex/index ranges) and the stage list
The upholstery shells come from tools/web_upholstery.py (Blender).
"""

from __future__ import annotations

import base64
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

CNC = Path(__file__).resolve().parents[1]
OUT = CNC / "web" / "models"

UP, X, NX, Y, NY = (0, 0, -1), (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)

# stages: (key, english, arabic, what happens, label regex). Pieces come in
# stage order; "travel" is the direction a piece moves to reach its place.
MODELS = {
    "pebble": {
        "dir": "pebble-sofa", "name": "Pebble", "ar": "كنبة Pebble", "kind": "كنبة مقسومة 3 م",
        "stages": [
            ("BASE", "FOUNDATION", "القاعدة", "حلقتين على الأرض، فيهم التجاويف اللي تدخل فيهم أرجل الأضلاع.", r"BASE-RING"),
            ("BODY", "RIBS", "الأضلاع", "52 ضلع يدخلو في الحلقة من الفوق. الحافة المنفوخة هي اللي تعطي الجنب المدوّر.", r" RIB-[LR]"),
            ("SEAT", "SEAT RING", "حلقة القعدة", "تنزل فوق الأضلاع على علو 330 ملم وتقفلهم. عليها يتشد الحزام المطاطي.", r"SEAT-RING"),
            ("PLATE", "PLATES", "قواعد الوسائد", "4 صفائح بيضاوية تتلصق وتتبرغى على حلقة القعدة.", r"-PLATE"),
            ("PRIB", "DOME RIBS", "أضلاع الوسائد", "مقاطع القبة تدخل في الصفيحة من الفوق.", r"PEBBLE-..-RIB"),
            ("SPINE", "SPINE", "العمود الفقري", "ينزل فوق الأضلاع بالطول (egg-crate) ويقفل الوسادة.", r"-SPINE"),
        ],
    },
    "lena": {
        "dir": "lena-sofa", "name": "Lena", "ar": "كنبة Lena", "kind": "كنبة 3 بلايص",
        "stages": [
            ("BACK", "BACK FRAME", "الظهر", "الأضلاع واقفين والأقواس تدخل بيناتهم من الجنب: هذا هو هيكل الظهر.", r"RIB-|BACK-ARCH"),
            ("RAILS", "RAILS", "العوارض", "3 عوارض تنزل من الفوق في الأضلاع: قدّام، وسط، ولور.", r"RAIL-"),
            ("INNER", "INNER ARMS", "الذراع الداخلي", "لوحة الذراع الداخلية تدخل على الجنب في رؤوس العوارض.", r"ARM-INNER"),
            ("SPACERS", "SPACERS", "الفواصل", "6 فواصل تعطي للذراع عرضو (drum).", r"ARM-SPACER"),
            ("OUTER", "OUTER ARMS", "الذراع الخارجي", "اللوحة الخارجية تقفل الذراع.", r"ARM-OUTER"),
            ("DECK", "SEAT DECK", "لوح القعدة", "زوج ألواح ينزلو على العوارض.", r"SEAT-DECK"),
        ],
        "sequence": ("lena-sofa/verify_3d.py", "SEQUENCE"),
    },
    "curl": {
        "dir": "curl-chair", "name": "Curl", "ar": "كرسي Curl", "kind": "فوتاي لاونج",
        "stages": [
            ("BASE", "FOUNDATION", "القاعدة", "حلقة القاعدة على الأرض.", r"BASE-RING"),
            ("BODY", "BODY RIBS", "أضلاع الجسم", "20 ضلع يدخلو في الحلقة ويعطيو الجنب المدوّر.", r"BODY-RIB"),
            ("SEAT", "SEAT RING", "حلقة القعدة", "تنزل فوق أضلاع الجسم وتقفلهم.", r"SEAT-RING"),
            ("BACK", "BACK RIBS", "أضلاع الظهر", "أضلاع الظهر تلف من لور ومن جهة وحدة برك.", r"BACK-RIB"),
            ("BAND", "BANDS", "أحزمة الظهر", "3 أحزمة تربط أضلاع الظهر.", r"BACK-BAND"),
        ],
    },
    "tub": {
        "dir": "round-armchair", "name": "Tub", "ar": "فوتاي Tub", "kind": "فوتاي مدوّر (Edra)",
        "stages": [
            ("BASE", "FOUNDATION", "القاعدة", "حلقة القاعدة على الأرض.", r"BASE-RING"),
            ("BODY", "BODY RIBS", "أضلاع الجسم", "20 ضلع يدخلو في الحلقة ويعطيو الشكل المدوّر.", r"BODY-RIB"),
            ("SEAT", "SEAT RING", "حلقة القعدة", "تنزل فوق أضلاع الجسم وتقفلهم.", r"SEAT-RING"),
            ("BACK", "BACK RIBS", "أضلاع الظهر", "أضلاع الظهر تدور على الكرسي كامل.", r"BACK-RIB"),
            ("BAND", "BANDS", "أحزمة الظهر", "3 أحزمة تربط أضلاع الظهر.", r"BACK-BAND"),
        ],
    },
    "cone": {
        "dir": "cone-table", "name": "Cone V10", "ar": "طابلة Cone", "kind": "طابلة مخروط 17 ملم · 49 تحفيرة كاملة",
        "loader": "cone", "ghost": 2,
        "stages": [
            ("CORE", "CORE", "القلب", "4 لوحات 17 ملم يتعشقو في بعضاهم على شكل صليب، طابقين.", r"CORE-"),
            ("FORMERS", "FORMERS", "الحلقات", "4 حلقات تحدد شكل المخروط وتشد القلب، 0.5 ملم تحت الغلاف للكولّة.", r"FORMER-"),
            ("SHELL", "KERF SHELL", "الغلاف المطوي", "لوحة 17 ملم بـ 49 تحفيرة كاملة من التحت للفوق، 2 ملم تحت الوجه. «أشعة» تبيّن التحفيرات من الداخل.", r"SHELL"),
        ],
    },
    "crescent": {
        "dir": "curved-sofa", "name": "Crescent", "ar": "كنبة مقوّسة", "kind": "كنبة هلال 3 بلايص · contreplaqué 15",
        "stages": [
            ("BASE", "BASE RAILS", "عوارض الأرض", "زوج عوارض مقوّسين على الأرض.", r"RAIL-BASE"),
            ("RIBS", "RIBS", "الأضلاع", "7 أضلاع ينزلو على عوارض الأرض.", r" RIB "),
            ("SEAT", "SEAT RAILS", "عوارض القعدة", "زوج عوارض ينزلو في رؤوس الأضلاع.", r"RAIL-SEAT"),
            ("BACKR", "BACK RAILS", "عوارض الظهر", "3 عوارض تدخل من لور في الأعمدة.", r"RAIL-BACK"),
            ("ARMS", "ARM PANELS", "الأذرع", "لوحتين يتزلقو على رؤوس العوارض من الجنب.", r"ARM-PANEL"),
            ("DECK", "SEAT DECK", "لوح القعدة", "3 قطع تنزل على الأضلاع والعوارض.", r"SEAT-DECK"),
            ("STILES", "STILES", "أعمدة الظهر", "14 عمود ينزلو من الفوق في العوارض.", r"BACK-STILE"),
        ],
    },
}
CRESCENT_TRAVEL = {"RAIL-BACK-BOT": NY, "RAIL-BACK-MID": NY}


def load_solids(key, cfg):
    d = CNC / cfg["dir"]
    sys.path.insert(0, str(d))
    sys.path.append(str(CNC / "curved-sofa"))
    if cfg.get("loader") == "cone":            # V10, 17 mm: the kerfed shell replaces the plain wall
        import shell3d
        import verify_3d as V
        return [shell3d.kerfed_shell()] + [s for s in V.assembly() if not s.label.startswith("SHELL")]
    import export_step as E
    return E.assembly()


def travel_for(key, cfg, label, stage):
    if "sequence" in cfg:
        f, name = cfg["sequence"]
        src = (CNC / f).read_text()
        ns = {}
        block = src[src.index(name + " = ["):]
        block = block[:block.index("]\n") + 1]
        exec("X = (1, 0, 0)\nNX, NZ = (-1, 0, 0), (0, 0, -1)\n" + block, ns)
        seq = ns[name]
        for i, (lab, d) in enumerate(seq):
            if lab == label:
                return d, i
    if key == "crescent":
        for k, d in CRESCENT_TRAVEL.items():
            if k in label:
                return d, None
        if "ARM-PANEL" in label:
            return ("tangent",), None
    return UP, None


def export_one(key):
    cfg = MODELS[key]
    solids = load_solids(key, cfg)
    stages = cfg["stages"]
    verts, idx, pieces = [], [], []
    for n, s in enumerate(solids):
        label = s.label
        st = next((i for i, (_, _, _, _, rx) in enumerate(stages) if re.search(rx, label)), None)
        if st is None:
            raise SystemExit(f"{key}: no stage for {label}")
        tol = 0.6 if st == len(stages) - 1 and key == "cone" else 0.25
        vs, tris = s.tessellate(tol, 0.25)
        bb = s.bounding_box()
        d, order = travel_for(key, cfg, label, st)
        if d == ("tangent",):          # arm panels slide outward along the arc tangent
            c = bb.center()
            d = (1.0 if c.X < 0 else -1.0, 0.0, 0.0)
        pieces.append({"label": label, "stage": st, "travel": list(d), "order": order if order is not None else n,
                       "v": [len(verts) // 3, len(vs)], "i": [len(idx), len(tris) * 3],
                       "box": [round(x, 1) for x in (bb.min.X, bb.min.Y, bb.min.Z, bb.max.X, bb.max.Y, bb.max.Z)]})
        base = len(verts) // 3
        for v in vs:
            verts += [v.X, v.Y, v.Z]
        for t in tris:
            idx += [base + t[0], base + t[1], base + t[2]]
    # shift so the frame sits centred on the origin, on the floor
    xs, ys, zs = verts[0::3], verts[1::3], verts[2::3]
    cx, cy, z0 = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)
    for i in range(0, len(verts), 3):
        verts[i] -= cx; verts[i + 1] -= cy; verts[i + 2] -= z0
    for p in pieces:
        b = p["box"]
        p["box"] = [round(b[0] - cx, 1), round(b[1] - cy, 1), round(b[2] - z0, 1),
                    round(b[3] - cx, 1), round(b[4] - cy, 1), round(b[5] - z0, 1)]
    OUT.mkdir(parents=True, exist_ok=True)
    blob = struct.pack(f"<{len(verts)}f", *verts) + struct.pack(f"<{len(idx)}I", *idx)
    (OUT / f"{key}.bin.txt").write_text(base64.b64encode(blob).decode())
    size = [round(max(xs) - min(xs)), round(max(ys) - min(ys)), round(max(zs) - min(zs))]
    meta = {"key": key, "name": cfg["name"], "ar": cfg["ar"], "kind": cfg["kind"],
            "stages": [{"key": k, "en": en, "ar": ar, "text": t} for k, en, ar, t, _ in stages],
            "pieces": pieces, "nverts": len(verts) // 3, "nidx": len(idx), "size": size,
            "shift": [cx, cy, z0], "upholstery": None, "ghost": cfg.get("ghost")}
    old = OUT / f"{key}.json"
    if old.exists():                                   # keep the upholstery block from the Blender pass
        meta["upholstery"] = json.loads(old.read_text()).get("upholstery")
    old.write_text(json.dumps(meta, ensure_ascii=False, separators=(",", ":")))
    print(f"{key}: {len(pieces)} pieces, {len(idx) // 3} triangles, {size[0]} x {size[1]} x {size[2]} mm, "
          f"{(OUT / f'{key}.bin.txt').stat().st_size / 1024:.0f} KB")


def main():
    if "--child" in sys.argv:
        return export_one(sys.argv[1])
    for k in sys.argv[1:] or list(MODELS):
        subprocess.run([sys.executable, __file__, k, "--child"], check=True)
    index = [{"key": k, "name": MODELS[k]["name"], "ar": MODELS[k]["ar"]} for k in MODELS
             if (OUT / f"{k}.json").exists()]
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False))


if __name__ == "__main__":
    main()
