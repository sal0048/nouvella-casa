"""Blender renders of the Pebble sofa (Cycles, CPU, headless).

    /root/.venvs/blender/bin/python render_blender.py frame|upholstered|exploded|export [--sheet]

Frame = exact cut geometry (pebble_geometry.instances()). The upholstered
view is an approximate foam shell (sales visual, not a pattern).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))

import bpy
from mathutils import Matrix, Vector

import pebble_geometry as G
import sofa_layout as L

MM = 0.001
CX, CY = 1550.0, 560.0

def reset(samples: int, size: int):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x = sc.render.resolution_y = size
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = -0.6
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.93, 0.91, 0.88, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.25
    sc.world = world
    return sc


def material_wood():
    m = bpy.data.materials.new("birch")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.55
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.inputs["Scale"].default_value = 3.0
    wave.inputs["Distortion"].default_value = 6.0
    wave.inputs["Detail"].default_value = 3.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.62, 0.45, 0.27, 1)
    ramp.color_ramp.elements[1].color = (0.80, 0.63, 0.42, 1)
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def material_highlight():
    """Warm terracotta birch for the parts added in an assembly step."""
    m = material_wood()
    m.name = "birch-new"
    ramp = next(n for n in m.node_tree.nodes if n.type == "VALTORGB")
    ramp.color_ramp.elements[0].color = (0.62, 0.20, 0.07, 1)
    ramp.color_ramp.elements[1].color = (0.80, 0.34, 0.14, 1)
    return m


def material_boucle():
    m = bpy.data.materials.new("boucle")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.80, 0.76, 0.70, 1)
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Sheen Weight"].default_value = 0.8
    bsdf.inputs["Sheen Tint"].default_value = (0.9, 0.85, 0.8, 1)
    # bouclé: small curly loops = voronoi cells plus a finer noise
    noise = nt.nodes.new("ShaderNodeTexVoronoi")
    noise.inputs["Scale"].default_value = 90.0
    fine = nt.nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 400.0
    mix = nt.nodes.new("ShaderNodeMath")
    mix.operation = "ADD"
    nt.links.new(noise.outputs["Distance"], mix.inputs[0])
    nt.links.new(fine.outputs["Fac"], mix.inputs[1])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.9
    bump.inputs["Distance"].default_value = 0.004
    nt.links.new(mix.outputs["Value"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def floor_and_lights():
    bpy.ops.mesh.primitive_plane_add(size=40)
    floor = bpy.context.object
    m = bpy.data.materials.new("floor")
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.55, 0.50, 0.45, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.8
    floor.data.materials.append(m)
    for loc, energy, size in [((3.6, -4.0, 3.4), 800, 3.0), ((-4.2, -1.4, 2.6), 280, 4.0),
                              ((0.6, 4.2, 3.0), 340, 2.4)]:
        bpy.ops.object.light_add(type="AREA", location=loc)
        light = bpy.context.object
        light.data.energy = energy
        light.data.size = size
        direction = -light.location
        light.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def camera(azim_deg: float, elev_deg: float, dist: float, target_z: float):
    a, e = math.radians(azim_deg), math.radians(elev_deg)
    loc = (dist * math.cos(e) * math.cos(a), dist * math.cos(e) * math.sin(a),
           target_z + dist * math.sin(e))
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.object
    cam.data.lens = 50
    bpy.ops.object.empty_add(location=(0, 0, target_z))
    track = cam.constraints.new("TRACK_TO")
    track.target = bpy.context.object
    bpy.context.scene.camera = cam



def grid_mesh(name, rows, mat, closed_u=True, subdiv=2):
    """Quad mesh from rows of vertices (each row a ring or an open strip)."""
    verts = [v for row in rows for v in row]
    n = len(rows[0])
    faces = []
    for i in range(len(rows) - 1):
        for j in range(n if closed_u else n - 1):
            k = (j + 1) % n
            faces.append((i * n + j, i * n + k, (i + 1) * n + k, (i + 1) * n + j))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(mat)
    for poly in me.polygons:
        poly.use_smooth = True
    mod = ob.modifiers.new("soft", "SUBSURF")
    mod.levels = mod.render_levels = subdiv
    return ob




def material_grey():
    m = material_boucle()
    m.name = "boucle-grey"
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.42, 0.42, 0.43, 1)
    return m


def plate(name, loops, o, u, v, centred, mat, shift=(0, 0, 0)):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    cu.extrude = G.T / 2 * MM
    for loop in loops:
        pts = L.flatten_loop(loop, 12)
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for p, (x, y) in zip(sp.points, pts):
            p.co = (x * MM, y * MM, 0.0, 1.0)
        sp.use_cyclic_u = True
    ob = bpy.data.objects.new(name, cu)
    ob.data.materials.append(mat)
    bpy.context.collection.objects.link(ob)
    U, V = Vector(u), Vector(v)
    N = U.cross(V)
    O = Vector(o) + (N * 0 if centred else N * (G.T / 2)) + Vector(shift)
    O = Vector(((O.x - CX) * MM, (O.y - CY) * MM, O.z * MM))
    ob.matrix_world = Matrix(((U.x, V.x, N.x, O.x), (U.y, V.y, N.y, O.y), (U.z, V.z, N.z, O.z), (0, 0, 0, 1)))
    return ob


EXPLODE = {"BASE": 0, "BODY": 160, "SEAT": 480, "PLATE": 700, "PRIB": 900, "SPINE": 1150}


STEP_HOVER = {"BASE": 0, "BODY": 120, "SEAT": 160, "PLATE": 160, "PRIB": 160, "SPINE": 180}


def build_frame(mat, exploded=False, upto=None, hi_mat=None):
    order = G.GROUP_ORDER
    for p, k, o, u, v, c in G.instances():
        if upto and order.index(p.group) > order.index(upto):
            continue
        dz = EXPLODE[p.group] if exploded else (STEP_HOVER[p.group] if p.group == upto else 0)
        use = hi_mat if (hi_mat is not None and p.group == upto) else mat
        plate(f"P{p.num:02d} {p.label} {k}", p.loops, o, u, v, c, use, (0, 0, dz))


def export_meshes(out_dir: Path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build_frame(material_wood())
    for ob in bpy.context.scene.objects:
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
    bpy.ops.object.convert(target="MESH")
    bpy.ops.wm.obj_export(filepath=str(out_dir / "pebble-sofa.obj"), global_scale=1000.0, export_materials=True)
    bpy.ops.wm.stl_export(filepath=str(out_dir / "pebble-sofa.stl"), global_scale=1000.0)


def world(x, y, z):
    return ((x - CX) * MM, (y - CY) * MM, z * MM)


def build_upholstery(beige, grey):
    foam = 40.0
    for m in G.MODULES:
        angs = [i * 3.0 for i in range(120)]
        rows = []
        for k in range(12):
            z = 25.0 + (G.SEAT_TOP + 40.0 - 25.0) * k / 11
            f = G.belly(min(z, G.SEAT_Z)) if z <= G.SEAT_Z else G.S_SEAT + 0.02
            rows.append([world(m.cx + (f * m.R(a) + foam) * math.cos(math.radians(a)),
                               m.cy + (f * m.R(a) + foam) * math.sin(math.radians(a)), z) for a in angs])
        for shrink, dz in ((0.96, 110.0), (0.85, 128.0), (0.55, 136.0), (0.0, 138.0)):
            rows.append([world(m.cx + shrink * (G.S_SEAT * m.R(a) + 20) * math.cos(math.radians(a)),
                               m.cy + shrink * (G.S_SEAT * m.R(a) + 20) * math.sin(math.radians(a)),
                               G.SEAT_TOP + dz) for a in angs])
        grid_mesh(f"seat-{m.key}", rows, beige)
    for p in G.PEBBLES:
        mat = grey if p.key in ("BL", "AR") else beige
        z0 = G.SEAT_TOP + 20.0
        ring = []
        for i in range(64):
            a = 2 * math.pi * i / 64
            c, s = math.cos(a), math.sin(a)
            ring.append((math.copysign(abs(c) ** (2 / p.N), c), math.copysign(abs(s) ** (2 / p.N), s)))
        rows = []
        for f in (0.0, 0.3, 0.55, 0.75, 0.9, 0.97, 1.0):          # height fraction of the dome
            sc = max(0.0, 1 - f ** G.PEB_E) ** (1 / G.PEB_E) if f < 1 else 0.0
            sc = max(sc, 0.0)
            z = z0 + (p.H + foam) * f
            grow = 1.0 + 0.12 * (1 - f)
            rows.append([world(*G.to_world(p, (p.a + foam) * grow * sc * u, (p.b + foam) * grow * sc * t), z)
                         for u, t in ring])
        bottom = [world(*G.to_world(p, (p.a + foam) * 1.05 * u, (p.b + foam) * 1.05 * t), z0) for u, t in ring]
        rows.insert(0, [world(p.px, p.py, z0)] * len(ring))
        rows.insert(1, bottom)
        grid_mesh(f"pebble-{p.key}", rows, mat)


def render(mode, sheet=False):
    samples, size = (96, 1500) if not sheet else (64, 1300)
    sc = reset(samples, size)
    sc.render.resolution_y = int(size * 0.62)
    floor_and_lights()
    if sheet:
        sc.render.film_transparent = True
        sc.render.image_settings.color_mode = "RGBA"
        next(o for o in sc.objects if o.type == "MESH").hide_render = True
    if mode.startswith("step-"):
        build_frame(material_wood(), upto=mode[5:].upper(), hi_mat=material_highlight())
        camera(-62.0, 28.0, 6.0, 0.30)
    elif mode == "frame":
        build_frame(material_wood()); camera(-62.0, 26.0, 5.6, 0.30)
    elif mode == "exploded":
        build_frame(material_wood(), exploded=True); camera(-62.0, 22.0, 7.0, 0.70)
    elif mode == "top":
        build_frame(material_wood()); camera(-90.0, 70.0, 6.0, 0.20)
    else:
        build_upholstery(material_boucle(), material_grey()); camera(-70.0, 14.0, 5.4, 0.38)
    out = (HERE / "out" / "sheets" / f"{mode}.png") if sheet else (HERE / "out" / f"pebble-sofa-{mode}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = str(out)
    bpy.ops.render.render(write_still=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "frame"
    if mode == "export":
        export_meshes(HERE / "out")
    else:
        render(mode, sheet="--sheet" in sys.argv)
