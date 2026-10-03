"""The V10 kerfed shell as it stands bent on the cone (3D, for viewing).

    from shell3d import kerfed_shell; s = kerfed_shell()

Skin (SKIN thick under the show face) as one revolved wall, plus the back
layer (DEPTH) cut by the 49 kerfs. Each kerf lies along a generatrix, so in
3D it is a slot centred on a meridian plane, at azimuth 2 pi k / N from the
seam. Bent, a kerf has closed hinge x DEPTH at the back face and is still
TOOL_D wide at the skin: the slot is drawn with the mean of the two. Formers
and core come from verify_3d.assembly(); this replaces its plain SHELL.
"""

from __future__ import annotations

import math

from build123d import Axis, Box, Location, Polyline, make_face, revolve

import table_geometry as G


def wall(r_out, r_in):
    """Revolved wall between two radius functions of z (outer face R)."""
    prof = Polyline((r_in(0.0), 0, 0.0), (r_out(0.0), 0, 0.0), (r_out(G.H_CONE), 0, G.H_CONE),
                    (r_in(G.H_CONE), 0, G.H_CONE), close=True)
    return revolve(make_face(prof), Axis.Z, 360)


def kerfed_shell():
    c = G.COS_A
    skin = wall(G.R, lambda z: G.R(z) - G.SKIN / c)
    back = wall(lambda z: G.R(z) - G.SKIN / c, lambda z: G.R(z) - G.T_SHELL / c)
    s_in = G.s_of(G.H_CONE)
    n = G.kerf_count(s_in)
    hinge = G.hinge_angle(s_in)
    w = G.TOOL_D - hinge * G.DEPTH / 2              # mean bent width of a kerf
    slots = None
    for k in range(1, n):
        phi = 360.0 * k / n
        b = Location((0, 0, 0), (0, 0, 1), phi) * Location((G.R_BOT / 2 + 20, 0, G.H_CONE / 2)) * \
            Box(G.R_BOT + 40, w, G.H_CONE + 20)
        slots = b if slots is None else slots + b
    shell = skin + (back - slots)
    shell.label = "SHELL"
    return shell
