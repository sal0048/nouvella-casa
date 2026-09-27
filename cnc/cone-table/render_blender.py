"""Render the cone table with Blender (bpy). Run with the Blender venv:

    /root/.venvs/blender/bin/python render_blender.py [hero|section]
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import table_geometry as T  # noqa: E402  (pure python, no numpy needed)

MM = 0.001
OUT = HERE / "out"


def material(name, rgb, rough=0.55):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    return m


def cone(r0, r1, z0, z1, thick, mat, cut=False):
    bpy.ops.mesh.primitive_cone_add(vertices=160, radius1=r0 * MM, radius2=r1 * MM,
                                    depth=(z1 - z0) * MM, end_fill_type="NOTHING",
                                    location=(0, 0, (z0 + z1) / 2 * MM))
    ob = bpy.context.object
    sol = ob.modifiers.new("t", "SOLIDIFY")
    sol.thickness = thick * MM
    sol.offset = -1.0                      # grow inward from the show face
    if cut:
        bpy.ops.mesh.primitive_cube_add(size=2, location=(1, -1, T.TABLE_H * MM / 2))
        box = bpy.context.object
        box.hide_render = True
        bo = ob.modifiers.new("cut", "BOOLEAN")
        bo.object = box
        bo.operation = "DIFFERENCE"
    bpy.ops.object.shade_smooth()
    ob.data.materials.append(mat)
    return ob


def disc(r_out, z0, z1, mat, r_in=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=160, radius=r_out * MM,
                                        depth=(z1 - z0) * MM,
                                        location=(0, 0, (z0 + z1) / 2 * MM))
    ob = bpy.context.object
    if r_in > 0:
        bpy.ops.mesh.primitive_cylinder_add(vertices=160, radius=r_in * MM,
                                            depth=(z1 - z0 + 2) * MM,
                                            location=(0, 0, (z0 + z1) / 2 * MM))
        hole = bpy.context.object
        hole.hide_render = True
        bo = ob.modifiers.new("hole", "BOOLEAN")
        bo.object = hole
        bo.operation = "DIFFERENCE"
    ob.data.materials.append(mat)
    return ob


def main(mode="hero"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    oak = material("oak", (0.30, 0.16, 0.07), 0.45)
    edge = material("mdf_edge", (0.45, 0.33, 0.20), 0.8)
    white = material("collar", (0.86, 0.85, 0.82), 0.5)
    floor = material("floor", (0.93, 0.92, 0.90), 0.9)

    cut = mode == "section"
    cone(T.R(0), T.R(T.Z_SPLIT), 0, T.Z_SPLIT, T.T_SHELL, oak, cut)
    cone(T.R(T.Z_SPLIT), T.R(T.H_CONE), T.Z_SPLIT, T.H_CONE, T.T_SHELL, oak, cut)
    parts = {p.key: p for p in T.build_parts()}
    c = parts["COLLAR"].meta
    disc(c["r"] + T.COLLAR_W, c["z0"], c["z1"], white, c["r"])
    disc(T.SUBTOP_D / 2, T.H_CONE, T.H_CONE + T.T_BOARD, edge)
    disc(T.TOP_D / 2, T.H_CONE + T.T_BOARD, T.TABLE_H, oak)
    if cut:
        for k in ("FBASE", "FJLO", "FJUP", "FTOP"):
            m = parts[k].meta
            disc(m["r"], m["z0"], m["z1"], edge,
                 m["r"] - T.FORMER_RING_W if k in ("FJLO", "FJUP") else 0.0)

    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0))
    bpy.context.object.data.materials.append(floor)

    bpy.ops.object.light_add(type="AREA", location=(1.6, -1.8, 2.4))
    key = bpy.context.object
    key.data.energy = 350
    key.data.size = 2.0
    key.rotation_euler = (math.radians(42), 0, math.radians(40))
    bpy.ops.object.light_add(type="AREA", location=(-2.0, 1.0, 1.6))
    fill = bpy.context.object
    fill.data.energy = 90
    fill.data.size = 3.0
    fill.rotation_euler = (math.radians(60), 0, math.radians(-120))

    k = T.TOP_D / 800.0
    bpy.ops.object.camera_add(location=(1.55 * k, -1.95 * k, 1.05 * k))
    cam = bpy.context.object
    bpy.ops.object.empty_add(location=(0, 0, T.TABLE_H * MM * 0.45))
    tgt = bpy.context.object
    tr = cam.constraints.new("TRACK_TO")
    tr.target = tgt
    cam.data.lens = 50
    scene = bpy.context.scene
    scene.camera = cam
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.95, 0.95, 0.95, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.25
    scene.world = world
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 64
    scene.render.resolution_x, scene.render.resolution_y = 1200, 1400
    scene.view_settings.view_transform = "AgX"
    scene.render.filepath = str(OUT / f"render_{mode}.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "hero")
