"""Photoreal Blender renders of the round armchair (Cycles, CPU, headless).

    /root/.venvs/blender/bin/python render_blender.py frame      # bare MDF frame
    /root/.venvs/blender/bin/python render_blender.py upholstered
    /root/.venvs/blender/bin/python render_blender.py exploded
    /root/.venvs/blender/bin/python render_blender.py export     # OBJ + STL

The frame is built from the exact cut geometry in chair_geometry.py: every
part becomes an 18 mm extruded curve (openings and mortises included) placed
where it sits in the chair. The upholstered view wraps that frame in an
approximate foam-and-fabric shell; it is a sales visual, not a pattern.

Blender needs numpy < 2, so it lives in its own venv (see README).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))  # shared code, lower priority

import bpy

import chair_geometry as C
import sofa_layout as L

MM = 0.001


# --------------------------------------------------------------------------
# scene
# --------------------------------------------------------------------------

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
    for loc, energy, size in [((2.2, -2.4, 2.6), 380, 2.0), ((-2.6, -0.8, 1.8), 110, 3.0),
                              ((0.5, 2.8, 2.2), 160, 1.5)]:
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


# --------------------------------------------------------------------------
# frame: every cut part as an extruded 2D curve
# --------------------------------------------------------------------------

def plate(name, loops, mat, dx=0.0, dy=0.0):
    """Extruded 18 mm plate from loops (outline + openings), centred on z=0."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    cu.extrude = C.T / 2 * MM
    for loop in loops:
        pts = L.flatten_loop(loop, 12)
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for p, (x, y) in zip(sp.points, pts):
            p.co = ((x + dx) * MM, (y + dy) * MM, 0.0, 1.0)
        sp.use_cyclic_u = True
    ob = bpy.data.objects.new(name, cu)
    ob.data.materials.append(mat)
    bpy.context.collection.objects.link(ob)
    return ob


# exploded view: lift per assembly layer (mm) and push ribs outward
EXPLODE = {"BASE": 0.0, "BODY": 180.0, "SEAT": 460.0, "BACK": 620.0, "BAND": 900.0}
EXPLODE_OUT = {"BODY": 90.0, "BACK": 60.0}


def build_frame(mat, exploded=False):
    def lift(key):
        return EXPLODE[key] if exploded else 0.0

    def push(key, a):
        if not exploded:
            return 0.0, 0.0
        d = EXPLODE_OUT.get(key, 0.0)
        return d * math.cos(math.radians(a)) * MM, d * math.sin(math.radians(a)) * MM

    for p in C.build_parts():
        if p.key in ("BASE", "SEAT") or p.key.startswith("BAND"):
            z = {"BASE": 0.0, "SEAT": C.SEAT_Z}.get(p.key, C.BAND_Z)
            ob = plate(f"P{p.num:02d} {p.label}", p.loops, mat)
            ob.location.z = (z + C.T / 2 + lift(p.key[:4])) * MM
        elif p.key.startswith("BODY"):
            for a in C.BODY_ANGLES:
                if C._type_angle(a) == C._type_angle(p.angles[0]):
                    ob = plate(f"P{p.num:02d} {p.label} @{a:g}", p.loops, mat, dx=C.body_in(a))
                    ob.rotation_euler = (math.pi / 2, 0.0, math.radians(a))
                    px, py = push("BODY", a)
                    ob.location = (px, py, lift("BODY") * MM)
        elif p.key.startswith("BACK"):
            for a in p.angles:
                ob = plate(f"P{p.num:02d} {p.label} @{a:g}", p.loops, mat,
                           dx=C.back_in(a) - C.SHOULDER, dy=C.SEAT_Z)
                ob.rotation_euler = (math.pi / 2, 0.0, math.radians(a))
                px, py = push("BACK", a)
                ob.location = (px, py, lift("BACK") * MM)


def export_meshes(out_dir: Path):
    """Assembled frame as OBJ and STL (mm), for viewers and marketplaces."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build_frame(material_wood())
    for ob in bpy.context.scene.objects:
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
    bpy.ops.object.convert(target="MESH")
    bpy.ops.wm.obj_export(filepath=str(out_dir / "round-armchair.obj"),
                          global_scale=1000.0, export_materials=True)
    bpy.ops.wm.stl_export(filepath=str(out_dir / "round-armchair.stl"),
                          global_scale=1000.0)
    print(f"wrote {out_dir}/round-armchair.obj, .stl (mm)")


# --------------------------------------------------------------------------
# upholstery: a soft shell over the frame
# --------------------------------------------------------------------------

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


def build_upholstery(mat):
    foam = 45.0
    angs = [i * 3.0 for i in range(120)]
    # belly: the rib outer edge plus foam, from the floor to the seat top
    rows = []
    for k in range(13):
        z = 20.0 + (C.SEAT_TOP + 60.0 - 20.0) * k / 12
        f = C.belly(min(z, C.SEAT_Z)) if z <= C.SEAT_Z else C.S_SEAT + 0.02
        rows.append([((f * C.R(a) + foam) * math.cos(math.radians(a)) * MM,
                      (f * C.R(a) + foam) * math.sin(math.radians(a)) * MM, z * MM)
                     for a in angs])
    # close the top into the seat cushion, domed
    for k, shrink in enumerate((0.93, 0.8, 0.55, 0.0)):
        z = C.SEAT_TOP + 95.0 + 18.0 * (k / 3)
        rows.append([(shrink * (C.S_SEAT * C.R(a)) * math.cos(math.radians(a)) * MM,
                      shrink * (C.S_SEAT * C.R(a)) * math.sin(math.radians(a)) * MM,
                      z * MM) for a in angs])
    grid_mesh("belly+seat", rows, mat)

    # back and arms: a thick soft band over the back ribs
    a0, a1 = C.BACK_ANGLES[0] - 8.0, C.BACK_ANGLES[-1] + 8.0
    back_angs = [a0 + (a1 - a0) * i / 60 for i in range(61)]
    section = [(-C.BACK_D - foam, 0.0), (-C.BACK_D - foam, 0.55), (-C.BACK_D * 0.5, 1.08),
               (foam * 0.6, 1.02), (foam, 0.5), (foam, 0.0)]
    rows = []
    for a in back_angs:
        ro = C.back_out(min(max(a, C.BACK_ANGLES[0]), C.BACK_ANGLES[-1]))
        h = C.back_height(min(max(a, C.BACK_ANGLES[0]), C.BACK_ANGLES[-1])) + foam
        taper = min(1.0, (a - a0) / 10.0, (a1 - a) / 10.0)
        ring = []
        for dr, fz in section:
            r = ro + dr
            z = C.SEAT_TOP + 40.0 + (h - C.SEAT_TOP - 40.0) * fz * (0.55 + 0.45 * taper)
            ring.append((r * math.cos(math.radians(a)) * MM,
                         r * math.sin(math.radians(a)) * MM, z * MM))
        rows.append(ring)
    # close both arm ends: a half-size ring, then a point, so the
    # subdivision rounds them off like a stuffed arm
    for end, nxt in ((0, 1), (-1, -2)):
        ring, inner = rows[end], rows[nxt]
        cx = sum(p[0] for p in ring) / len(ring)
        cy = sum(p[1] for p in ring) / len(ring)
        cz = sum(p[2] for p in ring) / len(ring)
        ox = ring[0][0] - inner[0][0]
        oy = ring[0][1] - inner[0][1]
        half = [(cx + (x - cx) * 0.55 + ox * 0.6, cy + (y - cy) * 0.55 + oy * 0.6,
                 cz + (z - cz) * 0.55) for x, y, z in ring]
        tip = [(cx + ox, cy + oy, cz)] * len(ring)
        if end == 0:
            rows[:0] = [tip, half]
        else:
            rows += [half, tip]
    grid_mesh("back+arms", rows, mat)


# extra camera angles for the product sheets: mode -> (build, azim, elev, dist, target_z)
SHEET_VIEWS = {"frame-back": ("frame", 128.0, 24.0, 2.35, 0.38),
               "top": ("frame", -58.0, 62.0, 2.6, 0.30)}


def render(mode: str, sheet: bool = False):
    """sheet=True: transparent background with the floor as a shadow catcher,
    written to out/sheets/<mode>.png for marketing/product-sheets."""
    samples, size = (96, 1200) if not sheet else (64, 1080)
    sc = reset(samples, size)
    floor_and_lights()
    if sheet:
        sc.render.film_transparent = True
        sc.render.image_settings.color_mode = "RGBA"
        # no floor at all: a shadow catcher leaves a grey haze box around the chair;
        # the sheets draw their own soft ground shadow
        next(o for o in sc.objects if o.type == "MESH").hide_render = True
    build = SHEET_VIEWS.get(mode, (mode,))[0]
    if mode in SHEET_VIEWS:
        build_frame(material_wood())
        camera(*SHEET_VIEWS[mode][1:])
    elif build == "frame":
        build_frame(material_wood())
        camera(-58.0, 22.0, 2.35, 0.38)
    elif build == "exploded":
        build_frame(material_wood(), exploded=True)
        camera(-58.0, 18.0, 3.3, 0.72)
    else:
        build_upholstery(material_boucle())
        camera(-58.0, 16.0, 2.45, 0.40)
    out = (HERE / "out" / "sheets" / f"{mode}.png") if sheet else \
        (HERE / "out" / f"round-armchair-{mode}.png")
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
