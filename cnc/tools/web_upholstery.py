"""Upholstery shells for the web x-ray viewer, from each model's Blender renderer.

    /root/.venvs/blender/bin/python tools/web_upholstery.py pebble lena curl tub

Runs the model's own render_blender.build_upholstery() (the sales-visual
foam shell, not a pattern) and writes its triangles to
cnc/web/models/<key>.uph.bin.txt, registered in <key>.json. The shell is moved
into the viewer frame by matching the model's render_blender.build_frame()
bounding box to the exact frame from tools/web_export.py (translation only;
a size mismatch stops the export).
"""

from __future__ import annotations

import inspect
import base64
import json
import struct
import subprocess
import sys
from pathlib import Path

CNC = Path(__file__).resolve().parents[1]
OUT = CNC / "web" / "models"
DIRS = {"pebble": "pebble-sofa", "lena": "lena-sofa", "curl": "curl-chair", "tub": "round-armchair"}
TONES = ["fabric", "accent"]          # first material passed in, second (grey cushions / plinth)


def world_box(objs):
    import bpy
    dg = bpy.context.evaluated_depsgraph_get()
    lo, hi = [1e9] * 3, [-1e9] * 3
    for ob in objs:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        for v in me.vertices:
            w = ev.matrix_world @ v.co
            for i in range(3):
                lo[i], hi[i] = min(lo[i], w[i]), max(hi[i], w[i])
        ev.to_mesh_clear()
    return lo, hi


def one(key):
    import bpy
    d = CNC / DIRS[key]
    sys.path.insert(0, str(d))
    sys.path.append(str(CNC / "curved-sofa"))
    import render_blender as R

    meta = json.loads((OUT / f"{key}.json").read_text())
    lo_w = [min(p["box"][i] for p in meta["pieces"]) for i in range(3)]
    hi_w = [max(p["box"][i + 3] for p in meta["pieces"]) for i in range(3)]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    wood = bpy.data.materials.new("wood")
    R.build_frame(wood)
    bpy.context.view_layer.update()
    frame = [o for o in bpy.context.scene.objects if o.type in ("MESH", "CURVE") and o.name.startswith("P")]
    lo_b, hi_b = world_box(frame)
    size_b = [(hi_b[i] - lo_b[i]) * 1000 for i in range(3)]
    size_w = [hi_w[i] - lo_w[i] for i in range(3)]
    if any(abs(a - b) > 3.0 for a, b in zip(size_b, size_w)):
        raise SystemExit(f"{key}: Blender frame {size_b} != exact frame {size_w}, not exporting")
    off = [lo_w[i] - lo_b[i] * 1000 for i in range(3)]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    n = len(inspect.signature(R.build_upholstery).parameters)
    mats = [bpy.data.materials.new(t) for t in TONES[:n]]
    R.build_upholstery(*mats)
    dg = bpy.context.evaluated_depsgraph_get()
    verts, idx, parts = [], [], []
    for ob in [o for o in bpy.context.scene.objects if o.type in ("MESH", "CURVE")]:
        for m in ob.modifiers:
            if m.type == "SUBSURF":
                m.levels = m.render_levels = min(m.render_levels, 1)
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        tone = 0
        if ob.active_material is not None and ob.active_material.name.startswith(TONES[1]):
            tone = 1
        base, i0 = len(verts) // 3, len(idx)
        mw = ob.matrix_world
        for v in me.vertices:
            p = mw @ v.co
            verts += [p.x * 1000 + off[0], p.y * 1000 + off[1], p.z * 1000 + off[2]]
        for t in me.loop_triangles:
            idx += [base + t.vertices[0], base + t.vertices[1], base + t.vertices[2]]
        parts.append({"name": ob.name, "tone": tone, "v": [base, len(me.vertices)], "i": [i0, len(idx) - i0]})
        ev.to_mesh_clear()
    blob = struct.pack(f"<{len(verts)}f", *verts) + struct.pack(f"<{len(idx)}I", *idx)
    (OUT / f"{key}.uph.bin.txt").write_text(base64.b64encode(blob).decode())
    meta["upholstery"] = {"parts": parts, "nverts": len(verts) // 3, "nidx": len(idx)}
    (OUT / f"{key}.json").write_text(json.dumps(meta, ensure_ascii=False, separators=(",", ":")))
    print(f"{key}: upholstery {len(parts)} shells, {len(idx) // 3} triangles, offset {[round(o) for o in off]}")


if __name__ == "__main__":
    if "--child" in sys.argv:
        one(sys.argv[1])
    else:
        for k in sys.argv[1:] or list(DIRS):
            subprocess.run([sys.executable, __file__, k, "--child"], check=True)
