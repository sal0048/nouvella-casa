"""3D assembly checks on the exact solids (build123d).

* no two parts interpenetrate (every tab clears its mortise);
* every rib actually bears on what should carry it (contact, not floating);
* every back rib passes up through its band slot.
Returns a list of (section, passed, message) like verify.py.
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))  # shared code, lower priority

import chair_geometry as C
import export_step as E

TOUCH = 0.01          # mm: closer than this counts as bearing contact
RESULTS = []


def check(section, ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    RESULTS.append((section, bool(ok), msg))


def main() -> list:
    items = E.assembly()
    by = {s.label: s for s in items}
    boxes = [s.bounding_box() for s in items]

    def overlap(a, b):
        return (a.min.X < b.max.X and b.min.X < a.max.X and a.min.Y < b.max.Y
                and b.min.Y < a.max.Y and a.min.Z < b.max.Z and b.min.Z < a.max.Z)

    sec = "[3D-1] interference"
    print(f"\n{sec}")
    pairs = [(i, j) for i, j in itertools.combinations(range(len(items)), 2)
             if overlap(boxes[i], boxes[j])]
    clashes = [(items[i].label, items[j].label) for i, j in pairs
               if (items[i] & items[j]).volume > 1e-3]
    check(sec, not clashes, f"{len(pairs)} neighbouring pairs, {len(clashes)} interpenetrate")

    sec = "[3D-2] load path: every rib bears on what carries it"
    print(f"\n{sec}")
    base = next(s for s in items if "BASE-RING" in s.label)
    seat = next(s for s in items if "SEAT-RING" in s.label)
    bands = [s for s in items if "BACK-BAND" in s.label]
    body = [s for s in items if "BODY-RIB" in s.label]
    back = [s for s in items if "BACK-RIB" in s.label]
    loose = [s.label for s in body
             if s.distance_to(base) > TOUCH or s.distance_to(seat) > TOUCH]
    check(sec, not loose, f"{len(body) - len(loose)}/{len(body)} body ribs touch both rings")
    loose = [s.label for s in back
             if s.distance_to(seat) > TOUCH or min(s.distance_to(b) for b in bands) > TOUCH]
    check(sec, not loose, f"{len(back) - len(loose)}/{len(back)} back ribs touch the seat "
                          f"ring and a band")
    loose = [s.label for s in bands if min(s.distance_to(r) for r in back) > TOUCH]
    check(sec, not loose, f"{len(bands) - len(loose)}/{len(bands)} bands rest on back ribs")

    sec = "[3D-3] overall size"
    print(f"\n{sec}")
    from build123d import Compound
    bb = Compound(children=items).bounding_box()
    check(sec, bb.min.Z > -1e-6 and abs(bb.max.Z - C.BACK_TOP) < 1e-6,
          f"frame {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, "
          f"standing on z = 0")
    print(f"\n3D FAILURES: {sum(not r[1] for r in RESULTS)}")
    return RESULTS


if __name__ == "__main__":
    raise SystemExit(1 if any(not r[1] for r in main()) else 0)
