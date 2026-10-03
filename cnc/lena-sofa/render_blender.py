"""Photoreal Blender renders of the Lena sofa (Cycles, CPU, headless).

    /root/.venvs/blender/bin/python render_blender.py frame        # bare MDF frame
    /root/.venvs/blender/bin/python render_blender.py upholstered
    /root/.venvs/blender/bin/python render_blender.py exploded
    /root/.venvs/blender/bin/python render_blender.py step-rails   # assembly step
    /root/.venvs/blender/bin/python render_blender.py export       # OBJ + STL
    add --sheet for a transparent render in out/sheets/ (product sheets)

The frame is built from the exact cut geometry (lena_geometry.instances()):
every piece is an 18 mm extruded curve, mortises and holes included, placed
where it sits. The upholstered view is an approximate foam-and-fabric shell
around that frame: a sales visual, not a pattern.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))  # shared code, lower priority

import bpy
from mathutils import Matrix

import lena_geometry as G
import sofa_layout as L

MM = 0.001
CX, CY = G.W / 2, G.D / 2          # scene origin at the middle of the sofa


# --------------------------------------------------------------------------
# scene (same studio as the curl chair, lights pushed out for a sofa)
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
    for loc, energy, size in [((3.2, -3.6, 3.2), 700, 2.8), ((-3.8, -1.2, 2.4), 240, 3.8),
                              ((0.6, 3.8, 2.8), 300, 2.2)]:
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



# --------------------------------------------------------------------------
# frame: every cut piece as an extruded 2D curve
# --------------------------------------------------------------------------

AXES = {"YZ": ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
        "XZ": ((1, 0, 0), (0, 0, 1), (0, -1, 0)),
        "XY": ((1, 0, 0), (0, 1, 0), (0, 0, 1))}


def plate(name, loops, plane, w0, mat, shift=(0.0, 0.0, 0.0)):
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
    u, v, w = AXES[plane]
    mid = w0 + G.T / 2
    loc = [0.0, 0.0, 0.0]
    loc[[abs(c) for c in w].index(1)] = mid
    loc = ((loc[0] - CX + shift[0]) * MM, (loc[1] - CY + shift[1]) * MM, (loc[2] + shift[2]) * MM)
    m = Matrix(((u[0], v[0], w[0], loc[0]), (u[1], v[1], w[1], loc[1]),
                (u[2], v[2], w[2], loc[2]), (0, 0, 0, 1)))
    ob.matrix_world = m
    return ob


# exploded view: offset per assembly group (mm); x offsets point away from the middle
EXPLODE = {"BACK": (0, 0, 0), "RAILS": (0, -380, 140), "INNER": (220, 0, 0),
           "SPACERS": (400, 0, 60), "OUTER": (580, 0, 0), "DECK": (0, -700, 560),
           "ARCH": (0, 260, 520)}         # arches lifted out of the posts, behind
# assembly-step views: how the new group hovers before it slides home (mm)
STEP_HOVER = {"BACK": (0, 0, 0), "RAILS": (0, 0, 230), "INNER": (230, 0, 0),
              "SPACERS": (200, 0, 0), "OUTER": (230, 0, 0), "DECK": (0, 0, 230)}


def build_frame(mat, exploded=False, upto=None, hi_mat=None):
    order = G.GROUP_ORDER
    for p, k, plane, w0, loops in G.instances():
        g = p.group
        if upto is not None and order.index(g) > order.index(upto):
            continue
        if exploded:
            vec = EXPLODE["ARCH" if p.key == "ARCH" else g]
        else:
            vec = STEP_HOVER[g] if g == upto else (0, 0, 0)
        # sideways moves go outward: which half of the sofa is this piece in?
        xs = [x for l in loops for x, *_ in l] if plane != "YZ" else [w0]
        side = -1.0 if (min(xs) + max(xs)) / 2 < CX else 1.0
        shift = (vec[0] * side, vec[1], vec[2])
        use = hi_mat if (hi_mat is not None and g == upto) else mat
        plate(f"P{p.num:02d} {p.label} {k}", loops, plane, w0, use, shift)


def export_meshes(out_dir: Path):
    """Assembled frame as OBJ and STL (mm), for viewers and marketplaces."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build_frame(material_wood())
    for ob in bpy.context.scene.objects:
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
    bpy.ops.object.convert(target="MESH")
    bpy.ops.wm.obj_export(filepath=str(out_dir / "lena-sofa.obj"),
                          global_scale=1000.0, export_materials=True)
    bpy.ops.wm.stl_export(filepath=str(out_dir / "lena-sofa.stl"), global_scale=1000.0)
    print(f"wrote {out_dir}/lena-sofa.obj, .stl (mm)")


# --------------------------------------------------------------------------
# upholstery: soft shells around the frame (sales visual)
# --------------------------------------------------------------------------

def soft_box_profile(x0, z0, x1, z1, e=18.0):
    """Closed XZ profile with doubled corners so subdivision keeps it boxy."""
    return [(x0 + e, z0), (x1 - e, z0), (x1, z0 + e), (x1, z1 - e),
            (x1 - e, z1), (x0 + e, z1), (x0, z1 - e), (x0, z0 + e)]


def arch_profile(x0, z0, x1, z1, n=16):
    """Tombstone: straight sides, round top, doubled bottom corners."""
    r = (x1 - x0) / 2
    pts = [(x0 + 15, z0), (x1 - 15, z0), (x1, z0 + 15)]
    pts += [(x0 + r + r * math.cos(math.radians(a)), z1 - r + r * math.sin(math.radians(a)))
            for a in [180.0 * i / n for i in range(n + 1)]]
    pts += [(x0, z0 + 15)]
    return pts


def sweep_y(name, prof, y0, y1, mat, edge=25.0):
    """Sweep an XZ profile along y with soft closed ends."""
    cx = sum(p[0] for p in prof) / len(prof)
    cz = sum(p[1] for p in prof) / len(prof)

    def ring(y, s=1.0):
        return [((cx + (x - cx) * s - CX) * MM, (y - CY) * MM, (cz + (z - cz) * s) * MM)
                for x, z in prof]

    ys = [y0 + edge, y0 + 2 * edge, (y0 + y1) / 2, y1 - 2 * edge, y1 - edge]
    rows = [ring(y0, 0.0), ring(y0, 0.82)] + [ring(y) for y in ys] + [ring(y1, 0.82), ring(y1, 0.0)]
    return grid_mesh(name, rows, mat)


def build_upholstery(mat, base_mat):
    foam = 25.0
    for side, (x0, x1) in (("L", (0.0, G.ARM_W)), ("R", (G.W - G.ARM_W, G.W))):
        r = (x1 - x0) / 2 + foam
        prof = [(x0 - foam, 25.0), (x1 + foam, 25.0), (x1 + foam, 45.0), (x1 + foam, G.ARM_TOP)]
        prof += [((x0 + x1) / 2 + r * math.cos(math.radians(a)), G.ARM_TOP + r * math.sin(math.radians(a)))
                 for a in [180.0 * i / 14 for i in range(1, 14)]]
        prof += [(x0 - foam, G.ARM_TOP), (x0 - foam, 45.0)]
        sweep_y(f"arm-{side}", prof, -foam, G.D + foam, mat, edge=40.0)
    # seat base wrap and the back shell behind the arches
    sweep_y("seat-base", soft_box_profile(G.SEAT_X0, 25.0, G.SEAT_X1, G.SEAT_TOP + 5),
            -foam, G.D + foam, mat, edge=30.0)
    sweep_y("back-shell", soft_box_profile(G.SEAT_X0, G.SEAT_TOP, G.SEAT_X1, G.POST_TOP + 30),
            G.POST_Y - 10, G.D + foam, mat, edge=30.0)
    # two seat cushions
    for k, (x0, x1) in enumerate(((G.SEAT_X0 + 4, G.SPLIT_X - 4), (G.SPLIT_X + 4, G.SEAT_X1 - 4))):
        sweep_y(f"seat-{k}", soft_box_profile(x0, G.SEAT_TOP, x1, G.SEAT_TOP + 135, 30.0),
                -foam - 10, G.POST_Y + 20, mat, edge=45.0)
    # the four Lena back cushions, one per arch
    for k in range(G.BAYS):
        a, b = G.bay_x(k)
        sweep_y(f"back-{k}", arch_profile(a - 6, G.SEAT_TOP + 130, b + 6, G.ARCH_TOP + 45),
                G.ARCH_Y - 190, G.ARCH_Y + G.T + 6, mat, edge=45.0)
    # dark shadow plinth so the sofa reads as sitting on low feet
    bpy.ops.mesh.primitive_cube_add(size=1)
    pl = bpy.context.object
    pl.scale = ((G.W - 120) * MM, (G.D - 120) * MM, 25 * MM)
    pl.location = (0, 0, 12.5 * MM)
    pl.data.materials.append(base_mat)


def material_plinth():
    m = bpy.data.materials.new("plinth")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.08, 0.07, 0.06, 1)
    b.inputs["Roughness"].default_value = 0.6
    return m


# extra camera angles: mode -> (build, azim, elev, dist, target_z)
SHEET_VIEWS = {"frame-back": ("frame", 128.0, 24.0, 4.0, 0.36),
               "top": ("frame", -60.0, 62.0, 4.4, 0.25),
               "front": ("upholstered", -90.0, 8.0, 4.4, 0.40)}


def render(mode: str, sheet: bool = False):
    samples, size = (96, 1400) if not sheet else (64, 1200)
    sc = reset(samples, size)
    sc.render.resolution_y = int(size * 0.72)
    floor_and_lights()
    if sheet:
        sc.render.film_transparent = True
        sc.render.image_settings.color_mode = "RGBA"
        next(o for o in sc.objects if o.type == "MESH").hide_render = True
    build = SHEET_VIEWS.get(mode, (mode,))[0]
    if mode.startswith("step-"):
        key = mode[5:].upper()
        build_frame(material_wood(), upto=key, hi_mat=material_highlight())
        camera(-58.0, 24.0, 4.3, 0.40)
    elif mode in SHEET_VIEWS:
        if build == "frame":
            build_frame(material_wood())
        else:
            build_upholstery(material_boucle(), material_plinth())
        camera(*SHEET_VIEWS[mode][1:])
    elif build == "frame":
        build_frame(material_wood())
        camera(-58.0, 22.0, 3.9, 0.38)
    elif build == "exploded":
        build_frame(material_wood(), exploded=True)
        camera(-62.0, 30.0, 6.4, 0.60)
    else:
        build_upholstery(material_boucle(), material_plinth())
        camera(-58.0, 15.0, 4.0, 0.40)
    out = (HERE / "out" / "sheets" / f"{mode}.png") if sheet else \
        (HERE / "out" / f"lena-sofa-{mode}.png")
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
