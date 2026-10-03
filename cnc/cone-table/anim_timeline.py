"""Frame timeline of the assembly video, shared by render_assembly.py
(Blender) and make_video.py (captions)."""

FPS = 24
DROP = 14                      # frames for a part to drop into place
# (part, first frame) - order of assembly
STEPS = [("FORMER-BASE", 6), ("CORE-1A", 44), ("CORE-1B", 64),
         ("FORMER-JOINT-LO", 96), ("FORMER-JOINT-UP", 132),
         ("CORE-2A", 168), ("CORE-2B", 188), ("FORMER-TOP", 222)]
WRAP0, WRAP1 = 258, 350        # shell wraps around the skeleton
END = 430
