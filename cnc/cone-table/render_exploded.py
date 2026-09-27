"""Exploded view from the exact 3D parts (out/stl, written by verify_3d
export). Run with the Blender venv."""

import math
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
COLORS = {"SHELL": (0.30, 0.16, 0.07), "CORE": (0.55, 0.33, 0.12),
          "FORMER": (0.72, 0.60, 0.42), "COLLAR": (0.85, 0.84, 0.80)}

bpy.ops.wm.read_factory_settings(use_empty=True)
mats = {}
for k, rgb in COLORS.items():
    m = bpy.data.materials.new(k)
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*rgb, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
    mats[k] = m
for f in sorted((HERE / "out" / "stl").glob("*.stl")):
    bpy.ops.wm.stl_import(filepath=str(f))
    ob = bpy.context.selected_objects[0]
    ob.scale = (0.001, 0.001, 0.001)
    ob.data.materials.append(next(v for k, v in mats.items() if f.stem.startswith(k)))
    for poly in ob.data.polygons:
        poly.use_smooth = False
bpy.ops.mesh.primitive_plane_add(size=10)
bpy.ops.object.light_add(type="AREA", location=(1.2, -1.6, 2.0))
L = bpy.context.object
L.data.energy, L.data.size = 300, 2.0
L.rotation_euler = (math.radians(40), 0, math.radians(35))
bpy.ops.object.light_add(type="AREA", location=(-1.5, 0.8, 1.2))
F = bpy.context.object
F.data.energy, F.data.size = 90, 3.0
F.rotation_euler = (math.radians(60), 0, math.radians(-120))
bpy.ops.object.camera_add(location=(0.9, -1.55, 0.95))
cam = bpy.context.object
bpy.ops.object.empty_add(location=(0.26, 0, 0.36))
t = cam.constraints.new("TRACK_TO")
t.target = bpy.context.object
cam.data.lens = 40
sc = bpy.context.scene
sc.camera = cam
w = bpy.data.worlds.new("w")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.95, 0.95, 0.95, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.3
sc.world = w
sc.render.engine = "CYCLES"
sc.cycles.samples = 48
sc.render.resolution_x, sc.render.resolution_y = 1400, 1100
sc.view_settings.view_transform = "AgX"
sc.render.filepath = str(HERE / "out" / "render_exploded.png")
bpy.ops.render.render(write_still=True)
