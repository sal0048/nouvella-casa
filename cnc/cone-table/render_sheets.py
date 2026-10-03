"""Transparent cut-out renders for the product sheets (one view per PNG).

    /root/.venvs/blender/bin/python render_sheets.py [--preview]

Views: finished (oak shell), skeleton (core + formers), cutaway (half shell),
exploded (skeleton parts spread vertically), top (skeleton from above).
Writes out/sheets/<view>.png, 1080x1080 RGBA.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
import bmesh  # noqa: E402  (after bpy)
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))
import render_studio as RS  # noqa: E402
import table_geometry as T  # noqa: E402

MM = 0.001
PARTS = ["FORMER-BASE", "CORE-1A", "CORE-1B", "FORMER-JOINT-LO", "FORMER-JOINT-UP",
         "CORE-2A", "CORE-2B", "FORMER-TOP"]
# exploded view: extra lift (m) per part
LIFT = {"FORMER-BASE": 0.0, "CORE-1A": 0.06, "CORE-1B": 0.06, "FORMER-JOINT-LO": 0.13,
        "FORMER-JOINT-UP": 0.19, "CORE-2A": 0.26, "CORE-2B": 0.26, "FORMER-TOP": 0.34}
OAK = ((0.24, 0.12, 0.05), (0.40, 0.22, 0.10), 0.45)
MDF = ((0.55, 0.38, 0.20), (0.72, 0.52, 0.30), 0.6)


def half_shell():
    """Back half of the wall, so the skeleton shows through the front."""
    me = bpy.data.meshes.new("half")
    bm = bmesh.new()
    n, zs = 96, (0.0, T.H_CONE)
    ring = []
    for i in range(n + 1):
        a = math.radians(-10) + math.pi * 1.1 * i / n
        c, s = math.cos(a), math.sin(a)
        ring.append([bm.verts.new((r * c * MM, r * s * MM, z * MM))
                     for r, z in ((T.R(zs[0]), zs[0]), (T.R(zs[1]), zs[1]),
                                  (T.R_in(zs[0]), zs[0]), (T.R_in(zs[1]), zs[1]))])
    for i in range(n):
        o0, o1, i0, i1 = ring[i]
        p0, p1, j0, j1 = ring[i + 1]
        for f in ((o0, p0, p1, o1), (i0, i1, j1, j0), (o1, p1, j1, i1), (o0, i0, j0, p0)):
            bm.faces.new(f)
    for q in (ring[0], ring[-1]):
        o0, o1, i0, i1 = q
        bm.faces.new((o0, o1, i1, i0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new("HALF", me)
    bpy.context.collection.objects.link(ob)
    return ob


def skeleton(mat, lift=False):
    obs = []
    for label in PARTS:
        bpy.ops.wm.stl_import(filepath=str(HERE / "out" / "stl_asm" / f"{label}.stl"))
        ob = bpy.context.selected_objects[0]
        ob.data.transform(Matrix.Scale(MM, 4))
        ob.data.materials.append(mat)
        if lift:
            ob.location.z += LIFT[label]
        obs.append(ob)
    return obs


def setup(view, preview):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    oak = RS.wood("oak", *OAK)
    mdf = RS.wood("mdf", *MDF)
    target_z = T.H_CONE * MM * 0.45
    cam_loc = (0.62, -1.7, 0.72)
    if view == "finished":
        RS.cone_shell().data.materials.append(oak)
        RS.cap().data.materials.append(oak)
    elif view == "skeleton":
        skeleton(mdf)
    elif view == "cutaway":
        skeleton(mdf)
        half_shell().data.materials.append(oak)
    elif view == "exploded":
        skeleton(mdf, lift=True)
        target_z, cam_loc = 0.38, (0.9, -2.3, 1.05)
    elif view == "top":
        skeleton(mdf)
        cam_loc = (0.35, -0.9, 1.55)
    mid = (0, 0, target_z)
    RS.area("KEY", (-0.9, -1.1, 1.3), 90, 1.4, mid, (1.0, 0.96, 0.9))
    RS.area("FILL", (1.3, -0.8, 0.6), 30, 2.0, mid, (0.95, 0.97, 1.0))
    RS.area("RIM", (0.4, 0.9, 1.4), 40, 1.0, mid, (1.0, 0.95, 0.88))
    bpy.ops.object.camera_add(location=cam_loc)
    cam = bpy.context.object
    RS.aim(cam, mid)
    cam.data.lens = 70
    sc = bpy.context.scene
    sc.camera = cam
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.92, 0.92, 0.92, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.3
    sc.world = w
    sc.render.film_transparent = True
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 16 if preview else 48
    sc.cycles.use_denoising = True
    sc.render.resolution_x = sc.render.resolution_y = 1080
    sc.render.resolution_percentage = 50 if preview else 100
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "AgX"
    # frame the objects: pull the camera back until everything fits
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in sc.objects if o.type == "MESH" for c in o.bound_box]
    for _ in range(40):
        ok = True
        for p in pts:
            co = __import__("bpy_extras.object_utils", fromlist=["x"]).world_to_camera_view(sc, cam, p)
            if not (0.08 < co.x < 0.92 and 0.06 < co.y < 0.94):
                ok = False
                break
        if ok:
            break
        cam.location = Vector(mid) + (cam.location - Vector(mid)) * 1.06
        bpy.context.view_layer.update()
    out = HERE / "out" / "sheets"
    out.mkdir(parents=True, exist_ok=True)
    sc.render.filepath = str(out / f"{view}.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    views = [a for a in sys.argv[1:] if not a.startswith("--")] or \
        ["finished", "skeleton", "cutaway", "exploded", "top"]
    for v in views:
        setup(v, "--preview" in sys.argv)
