---
name: blender-local
description: How to run Blender in this environment - headless bpy (Blender 5.0.1) in /root/.venvs/blender, no GUI and no blender-mcp server. Read this before using any blender-* or reference/mesh skill (from roble3/cc-blender-skill) that mentions mcp__blender__* tools, and whenever a task needs Blender modeling, materials, lighting, rendering, animation or export.
---

# Blender in this container

Blender runs as the **bpy Python module** (Blender 5.0.1), not as the desktop app.
There is no `blender-mcp` add-on server, so the `mcp__blender__*` tools named in the
cc-blender-skill skills do not exist here. Their knowledge applies unchanged; only
the execution path differs.

| Skill says | Do this instead |
| --- | --- |
| `mcp__blender__execute_blender_code` | write a script, run `/root/.venvs/blender/bin/python script.py` |
| `mcp__blender__get_scene_info` / `get_object_info` | print `bpy.data.objects`, `ob.location`, `ob.dimensions`, `ob.data.materials` from the script |
| `mcp__blender__get_viewport_screenshot` | render a still (`bpy.ops.render.render(write_still=True)`, Cycles CPU, low samples) and Read the PNG |
| `download_polyhaven_asset` / `download_sketchfab_model` | not available; build the asset or ask the user for the file |
| Keeping state between calls | there is none: each script starts from `read_factory_settings(use_empty=True)`, or save/load a `.blend` with `bpy.ops.wm.save_as_mainfile` / `open_mainfile` |

Notes
- `import bpy` must come before `import bmesh` / `mathutils`.
- Engines: Cycles CPU works headless (use denoising, 8-64 samples); EEVEE and
  Workbench need a GPU context and are not reliable here.
- The venv has numpy<2 (bpy requirement), shapely and ezdxf; the system python has
  build123d / cadgen (numpy>=2). Pass data between them as STL/OBJ/JSON files.
- Working examples in this repo: `cnc/round-armchair/render_blender.py`,
  `cnc/cone-table/render_blender.py`, `render_exploded.py`, `render_assembly.py`.
- Rebuild the venv with `scripts/setup-tools.sh --blender`.
- Helper scripts inside these skills (`scripts/*.py`) are plain Python (OpenCV,
  NumPy, SciPy, Pillow): run them with the system `python3`.
