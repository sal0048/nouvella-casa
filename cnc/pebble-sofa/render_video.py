"""Assembly animation frames for the Pebble sofa (Cycles, CPU, headless).

    /root/.venvs/blender/bin/python render_video.py OUT_DIR [--fps 15] [--samples 12]

Every piece is the exact cut geometry (pebble_geometry.instances()) and comes
down vertically in GROUP_ORDER, the same motion verify_3d.py [3D-4] proves is
clash-free. A piece is terracotta while it moves and turns birch once seated.
Writes OUT_DIR/f_0000.png ... plus timeline.json (frame -> group, pieces seated)
for the overlay pass (video_compose.py), and with --stills (or --stills-only)
the two hero stills for the frame -> upholstered crossfade.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bpy
from mathutils import Vector

import pebble_geometry as G
import render_blender as R

DROP = 520.0                      # mm a piece starts above its seat
FALL = 12                         # frames to seat one piece
STAGGER = {"BASE": 6, "BODY": 1, "SEAT": 6, "PLATE": 3, "PRIB": 2, "SPINE": 4}
GAP = 6                           # frames between groups
HOLD = 10
ORBIT = 45                        # frames of the final camera move


def arg(name, default):
    return type(default)(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def schedule(inst):
    """start frame per instance; ribs sweep round each module."""
    order = {g: i for i, g in enumerate(G.GROUP_ORDER)}

    def key(n):
        p, k, o, u, v, c = inst[n]
        ang = math.atan2(u[1], u[0]) if p.group == "BODY" else 0.0
        return order[p.group], p.key[4] if p.group == "BODY" else "", ang, n

    seq = sorted(range(len(inst)), key=key)
    start, f, groups = {}, 0, []
    for g in G.GROUP_ORDER:
        ns = [n for n in seq if inst[n][0].group == g]
        g0 = f
        for i, n in enumerate(ns):
            start[n] = f + i * STAGGER[g]
        f = max(start[n] for n in ns) + FALL + GAP
        groups.append((g, g0, f, len(ns)))
    return start, f, groups


def camera_at(cam, target, azim, elev, dist, tz):
    a, e = math.radians(azim), math.radians(elev)
    cam.location = (dist * math.cos(e) * math.cos(a), dist * math.cos(e) * math.sin(a), tz + dist * math.sin(e))
    target.location = (0, 0, tz)


def main():
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    sc = R.reset(arg("--samples", 12), 1280)
    sc.render.resolution_y = 720
    sc.render.use_persistent_data = True
    R.floor_and_lights()
    wood, hot = R.material_wood(), R.material_highlight()
    inst = G.instances()
    obs = []
    for p, k, o, u, v, c in inst:
        ob = R.plate(f"P{p.num:02d} {p.label} {k}", p.loops, o, u, v, c, wood)
        obs.append((ob, ob.location.copy()))
    R.camera(-95.0, 24.0, 6.4, 0.32)
    cam, target = sc.camera, next(o for o in sc.objects if o.type == "EMPTY")
    cam.constraints[0].target = target

    start, end, groups = schedule(inst)
    total = end + HOLD + ORBIT
    timeline = []
    only = set() if "--stills-only" in sys.argv else set(range(arg("--from", 0), arg("--to", total)))
    for f in range(total):
        seated = 0
        for n, (ob, home) in enumerate(obs):
            t = (f - start[n]) / FALL
            ob.hide_render = t < 0
            ob.location = home + Vector((0, 0, DROP * 0.001 * (1 - ease(t))))
            ob.data.materials[0] = hot if 0 <= t < 1.4 else wood
            seated += t >= 1
        if f < end + HOLD:
            s = f / (end + HOLD)
            camera_at(cam, target, -100 + 38 * s, 24 - 4 * s, 5.7 - 0.4 * s, 0.30)
        else:
            s = ease((f - end - HOLD) / ORBIT)
            camera_at(cam, target, -62 + 40 * s, 20 + 6 * s, 5.3 - 0.2 * s, 0.30)
        grp = next((g for g, g0, g1, _ in groups if g0 <= f < g1), "DONE")
        timeline.append({"f": f, "group": grp, "seated": seated, "total": len(obs)})
        if f in only:
            sc.render.filepath = str(out / f"f_{f:04d}.png")
            bpy.ops.render.render(write_still=True)
            print(f"frame {f + 1}/{total}", flush=True)
    (out / "timeline.json").write_text(json.dumps({"fps": arg("--fps", 15), "groups": groups,
                                                   "frames": timeline}, indent=0))
    if "--stills" in sys.argv or "--stills-only" in sys.argv:
        # hero pose of render_blender's upholstered view: bare frame, then the upholstered sofa
        sc.cycles.samples = 48
        camera_at(cam, target, -70.0, 14.0, 5.4, 0.38)
        sc.render.filepath = str(out / "still_frame.png")
        bpy.ops.render.render(write_still=True)
        for ob, _ in obs:
            ob.hide_render = True
        R.build_upholstery(R.material_boucle(), R.material_grey())
        sc.render.filepath = str(out / "still_upholstered.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
