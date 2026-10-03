"""Studio product shots of the cone for ads (blender-materials recipe 12 +
blender-lighting 'product' three-point, via the headless bpy venv).

    /root/.venvs/blender/bin/python render_studio.py [oak|walnut|all] [--preview]

Writes out/studio/cone_<finish>_4x5.png (1080x1350, Instagram/Facebook feed).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
import bmesh  # noqa: E402  (after bpy)
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))
import table_geometry as T  # noqa: E402

MM = 0.001
FINISHES = {
    # dark / light grain colours (linear), lacquer
    "oak": ((0.36, 0.20, 0.09), (0.50, 0.30, 0.15), 0.45),
    "walnut": ((0.06, 0.028, 0.013), (0.12, 0.060, 0.030), 0.40),
}
BACKDROP = (0.55, 0.45, 0.36)          # warm sand sweep


def wood(name, dark, light, rough):
    """Recipe 12 (procedural wood) with vertical grain along the cone's
    generatrices, plus a satin lacquer coat."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt, links = m.node_tree.nodes, m.node_tree.links
    b = nt["Principled BSDF"]
    tc = nt.new("ShaderNodeTexCoord")
    mp = nt.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (14.0, 14.0, 0.8)     # fine, long vertical grain
    wave = nt.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 4.0
    wave.inputs["Distortion"].default_value = 6.0
    wave.inputs["Detail"].default_value = 4.0
    noise = nt.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 60.0
    noise.inputs["Detail"].default_value = 8.0
    mix = nt.new("ShaderNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 0.6
    ramp = nt.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].color = (*light, 1)
    ramp.color_ramp.elements[0].position = 0.25   # soft grain, not stripes
    ramp.color_ramp.elements[1].position = 0.85
    links.new(tc.outputs["Object"], mp.inputs["Vector"])
    links.new(mp.outputs["Vector"], wave.inputs["Vector"])
    links.new(mp.outputs["Vector"], noise.inputs["Vector"])
    links.new(wave.outputs["Color"], mix.inputs[1])
    links.new(noise.outputs["Color"], mix.inputs[2])
    links.new(mix.outputs["Color"], ramp.inputs["Fac"])
    # broad figure: slow light/dark zones along the board, as in real veneer
    fig = nt.new("ShaderNodeTexNoise")
    fig.inputs["Scale"].default_value = 1.2
    fig.inputs["Detail"].default_value = 2.0
    fmap = nt.new("ShaderNodeMapping")
    fmap.inputs["Scale"].default_value = (3.0, 3.0, 0.5)
    fr = nt.new("ShaderNodeValToRGB")
    fr.color_ramp.elements[0].color = (0.72, 0.72, 0.72, 1)
    fr.color_ramp.elements[1].color = (1.12, 1.12, 1.12, 1)
    tone = nt.new("ShaderNodeMixRGB")
    tone.blend_type = "MULTIPLY"
    tone.inputs[0].default_value = 1.0
    links.new(tc.outputs["Object"], fmap.inputs["Vector"])
    links.new(fmap.outputs["Vector"], fig.inputs["Vector"])
    links.new(fig.outputs["Fac"], fr.inputs["Fac"])
    links.new(ramp.outputs["Color"], tone.inputs[1])
    links.new(fr.outputs["Color"], tone.inputs[2])
    links.new(tone.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = 0.35
    b.inputs["Coat Roughness"].default_value = 0.25
    return m


def plain(name, rgb, rough=0.8):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    return m


def cone_shell(n=256):
    """Closed conical wall (outer R(z), inner R_in(z)) - the finished skin."""
    me = bpy.data.meshes.new("SHELL")
    bm = bmesh.new()
    zs = (0.0, T.H_CONE)
    rings = []
    for i in range(n):
        a = 2 * math.pi * i / n
        c, s = math.cos(a), math.sin(a)
        rings.append([bm.verts.new((r * c * MM, r * s * MM, z * MM))
                      for r, z in ((T.R(zs[0]), zs[0]), (T.R(zs[1]), zs[1]),
                                   (T.R_in(zs[0]), zs[0]), (T.R_in(zs[1]), zs[1]))])
    for i in range(n):
        o0, o1, i0, i1 = rings[i]
        p0, p1, j0, j1 = rings[(i + 1) % n]
        bm.faces.new((o0, p0, p1, o1))
        bm.faces.new((i0, i1, j1, j0))
        bm.faces.new((o1, p1, j1, i1))
        bm.faces.new((o0, i0, j0, p0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new("SHELL", me)
    bpy.context.collection.objects.link(ob)
    bev = ob.modifiers.new("edge", "BEVEL")          # soften the rims a touch
    bev.width, bev.segments, bev.limit_method = 0.0015, 3, "ANGLE"
    return ob


def cap():
    """FORMER-TOP seen from above: flush disc closing the cone."""
    r = T.R_in(T.H_CONE) - T.FIT
    bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=r * MM, depth=T.T_BOARD * MM,
                                        location=(0, 0, (T.H_CONE - T.T_BOARD / 2) * MM))
    return bpy.context.object


def sweep(w=6.0, d=4.0, h=3.0, r=0.8, n=24):
    """Infinity-cove backdrop: floor curving up into a wall."""
    me = bpy.data.meshes.new("SWEEP")
    bm = bmesh.new()
    # floor from the front, quarter circle (centre y=1.2-r, z=r), then the wall
    prof = [(-d, 0.0)] + [(1.2 - r + r * math.cos(a), r + r * math.sin(a))
                          for a in (-math.pi / 2 + (math.pi / 2) * i / n for i in range(n + 1))]
    prof.append((1.2, h))
    left = [bm.verts.new((-w / 2, y, z)) for y, z in prof]
    right = [bm.verts.new((w / 2, y, z)) for y, z in prof]
    for k in range(len(prof) - 1):
        bm.faces.new((left[k], right[k], right[k + 1], left[k + 1]))
    bm.to_mesh(me)
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new("SWEEP", me)
    bpy.context.collection.objects.link(ob)
    return ob


def aim(ob, target):
    d = (Vector(target) - ob.location).normalized()
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def area(name, loc, energy, size, target, kelvin_rgb):
    bpy.ops.object.light_add(type="AREA", location=loc)
    L = bpy.context.object
    L.name = name
    L.data.energy, L.data.size = energy, size
    L.data.color = kelvin_rgb
    aim(L, target)
    return L


def shot(finish, preview=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dark, light, rough = FINISHES[finish]
    shell = cone_shell()
    shell.data.materials.append(wood(f"MAT-{finish}", dark, light, rough))
    top = cap()
    top.data.materials.append(wood("MAT-cap", tuple(c * 1.1 for c in dark),
                                   tuple(min(1, c * 1.1) for c in light), rough))
    bg = sweep()
    bg.data.materials.append(plain("MAT-sweep", BACKDROP, 0.9))

    mid = (0, 0, T.H_CONE * MM * 0.45)
    # product three-point: key 5, fill 1, rim 1.5 (neutral ~5000K)
    area("KEY", (-0.9, -1.1, 1.1), 70, 1.2, mid, (1.0, 0.96, 0.9))
    area("FILL", (1.3, -0.8, 0.5), 14, 2.0, mid, (0.95, 0.97, 1.0))
    area("RIM", (0.4, 0.9, 1.2), 30, 0.8, (0, 0, T.H_CONE * MM), (1.0, 0.95, 0.88))

    bpy.ops.object.camera_add(location=(0.55, -1.75, 0.62))
    cam = bpy.context.object
    aim(cam, (0, 0, T.H_CONE * MM * 0.42))
    cam.data.lens = 85
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = (cam.location - Vector(mid)).length
    cam.data.dof.aperture_fstop = 5.6

    sc = bpy.context.scene
    sc.camera = cam
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.88, 0.85, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.05
    sc.world = w
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 16 if preview else 128
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1080, 1350
    sc.render.resolution_percentage = 50 if preview else 100
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    out = HERE / "out" / "studio"
    out.mkdir(parents=True, exist_ok=True)
    sc.render.filepath = str(out / f"cone_{finish}_4x5{'_preview' if preview else ''}.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "all"
    for f in (FINISHES if which == "all" else [which]):
        shot(f, "--preview" in sys.argv)
