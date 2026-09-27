"""Assembly animation from the exact parts (out/stl_asm, exported by
verify_3d.assembly()) - frames to out/anim/. Run with the Blender venv:

    /root/.venvs/blender/bin/python render_assembly.py [--preview]

make_video.py then adds the captions and encodes the MP4.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
import bmesh  # noqa: E402  (available only after bpy)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))
import table_geometry as T  # noqa: E402

MM = 0.001
from anim_timeline import DROP, END, FPS, STEPS, WRAP0, WRAP1  # noqa: E402
LIFT = 0.30                    # m above its seat when it appears
SEGMENTS = 36

COLORS = {"SHELL": (0.26, 0.13, 0.05), "CORE": (0.62, 0.40, 0.18),
          "FORMER": (0.80, 0.68, 0.48)}


def material(name, rgb, rough=0.55):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    return m


def show_from(ob, frame, until=None):
    """Hidden before `frame`, visible from it on (until `until`)."""
    keys = [(0, True), (frame - 1, True), (frame, False)]
    if until:
        keys += [(until - 1, False), (until, True)]
    for f, hide in keys:
        ob.hide_render = hide
        ob.hide_viewport = hide
        ob.keyframe_insert("hide_render", frame=max(f, 0))
        ob.keyframe_insert("hide_viewport", frame=max(f, 0))
    for fc in ob.animation_data.action.fcurves if hasattr(ob.animation_data.action, "fcurves") else []:
        for k in fc.keyframe_points:
            k.interpolation = "CONSTANT"


def drop(ob, frame):
    show_from(ob, frame)
    ob.location.z = LIFT
    ob.keyframe_insert("location", index=2, frame=frame)
    ob.location.z = 0.0
    ob.keyframe_insert("location", index=2, frame=frame + DROP)


def wedge(a0, a1, n=8):
    """One slice of the conical wall between plan angles a0..a1 (rad)."""
    me = bpy.data.meshes.new("wedge")
    bm = bmesh.new()
    zs = [0.0, T.H_CONE]
    ring = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        c, s = math.cos(a), math.sin(a)
        ring.append([bm.verts.new((T.R(z) * c * MM, T.R(z) * s * MM, z * MM)) for z in zs]
                    + [bm.verts.new((T.R_in(z) * c * MM, T.R_in(z) * s * MM, z * MM)) for z in zs])
    for i in range(n):
        o0, o1, i0, i1 = ring[i]
        p0, p1, j0, j1 = ring[i + 1]
        bm.faces.new((o0, p0, p1, o1))            # outer
        bm.faces.new((i0, i1, j1, j0))            # inner
        bm.faces.new((o1, p1, j1, i1))            # top rim
        bm.faces.new((o0, i0, j0, p0))            # bottom rim
    for q in (ring[0], ring[-1]):                 # side ends
        o0, o1, i0, i1 = q
        bm.faces.new((o0, o1, i1, i0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    for p in me.polygons:
        p.use_smooth = True
    return me


def main(preview=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats = {k: material(k, v) for k, v in COLORS.items()}
    for label, frame in STEPS:
        bpy.ops.wm.stl_import(filepath=str(HERE / "out" / "stl_asm" / f"{label}.stl"))
        ob = bpy.context.selected_objects[0]
        ob.data.transform(__import__("mathutils").Matrix.Scale(MM, 4))
        ob.data.materials.append(mats["CORE" if label.startswith("CORE") else "FORMER"])
        drop(ob, frame)

    # the shell wraps around: slices appear one after the other
    for k in range(SEGMENTS):
        a0 = -math.pi / 2 + 2 * math.pi * k / SEGMENTS
        ob = bpy.data.objects.new(f"shell{k}", wedge(a0, a0 + 2 * math.pi / SEGMENTS))
        bpy.context.collection.objects.link(ob)
        ob.data.materials.append(mats["SHELL"])
        show_from(ob, WRAP0 + round((WRAP1 - WRAP0) * k / SEGMENTS), until=WRAP1 + 6)
    # once closed, one smooth shell (no slice lines)
    ob = bpy.data.objects.new("shell", wedge(-math.pi / 2, 1.5 * math.pi, n=192))
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(mats["SHELL"])
    show_from(ob, WRAP1 + 6)

    bpy.ops.mesh.primitive_plane_add(size=12)
    floor = bpy.context.object
    floor.data.materials.append(material("floor", (0.92, 0.91, 0.89), 0.9))
    for loc, energy, size, rot in (((1.3, -1.5, 2.0), 260, 2.0, (40, 0, 40)),
                                   ((-1.6, 0.9, 1.3), 80, 3.0, (60, 0, -120))):
        bpy.ops.object.light_add(type="AREA", location=loc)
        L = bpy.context.object
        L.data.energy, L.data.size = energy, size
        L.rotation_euler = tuple(math.radians(r) for r in rot)

    # camera orbits slowly around the cone
    bpy.ops.object.empty_add(location=(0, 0, 0.21))
    pivot = bpy.context.object
    bpy.ops.object.camera_add(location=(0, -1.45, 0.78))
    cam = bpy.context.object
    cam.parent = pivot
    cam.data.lens = 70
    tr = cam.constraints.new("TRACK_TO")
    bpy.ops.object.empty_add(location=(0, 0, 0.23))
    tr.target = bpy.context.object
    pivot.rotation_euler.z = math.radians(-35)
    pivot.keyframe_insert("rotation_euler", index=2, frame=1)
    pivot.rotation_euler.z = math.radians(55)
    pivot.keyframe_insert("rotation_euler", index=2, frame=END)

    sc = bpy.context.scene
    sc.camera = cam
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.95, 0.95, 0.95, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.35
    sc.world = w
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 4 if preview else 12
    sc.cycles.use_denoising = True
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, END
    sc.render.resolution_x = sc.render.resolution_y = 720
    sc.view_settings.view_transform = "AgX"
    out = HERE / "out" / ("anim_preview" if preview else "anim")
    out.mkdir(parents=True, exist_ok=True)
    sc.render.filepath = str(out / "f_")
    sc.render.image_settings.file_format = "PNG"
    if preview:
        for f in (20, 80, 200, 300, 420):
            sc.frame_set(f)
            sc.render.filepath = str(out / f"p_{f:04d}.png")
            bpy.ops.render.render(write_still=True)
    else:
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main("--preview" in sys.argv)
