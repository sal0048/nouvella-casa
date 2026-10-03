"""3D assembly checks on the exact solids (build123d).

* no two pieces interpenetrate (every tab clears its mortise, every
  cross-halving clears its partner);
* every mortise is filled by a tab (no orphan holes, no missing tabs);
* load path: each piece bears on what should carry it (contact, not floating);
* overall size.
Returns a list of (section, passed, message) like verify.py.
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))  # shared code, lower priority

from build123d import Compound, Location

import export_step as E
import lena_geometry as G

TOUCH = 0.01          # mm: closer than this counts as bearing contact
RESULTS = []

# assembly order and the direction each piece travels to reach its place
X = (1, 0, 0)
NX, NZ = (-1, 0, 0), (0, 0, -1)
SEQUENCE = [
    ("P01 RIB-A 1/2", NZ),                  # stand rib 1
    ("P03 BACK-ARCH 1/4", X), ("P03 BACK-ARCH 2/4", NX),   # arches into its posts
    ("P02 RIB-B 1/1", NX), ("P03 BACK-ARCH 3/4", NX),
    ("P01 RIB-A 2/2", NX), ("P03 BACK-ARCH 4/4", NX),
    ("P04 RAIL-FRONT 1/1", NZ), ("P05 RAIL-MID 1/1", NZ), ("P06 RAIL-BACK 1/1", NZ),
    ("P07 ARM-INNER-L 1/1", X), ("P08 ARM-INNER-R 1/1", NX),
    ("P09 ARM-SPACER 1/6", X), ("P09 ARM-SPACER 2/6", X), ("P09 ARM-SPACER 3/6", X),
    ("P09 ARM-SPACER 4/6", NX), ("P09 ARM-SPACER 5/6", NX), ("P09 ARM-SPACER 6/6", NX),
    ("P10 ARM-OUTER 1/2", X), ("P10 ARM-OUTER 2/2", NX),
    ("P11 SEAT-DECK 1/2", NZ), ("P11 SEAT-DECK 2/2", NZ),
]
# how far back along its path each piece is tested: fine through the joints,
# then coarse out to well clear of the frame
OFFSETS = [o + 0.5 for o in range(0, 40, 2)] + list(range(50, 501, 25))


def check(section, ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    RESULTS.append((section, bool(ok), msg))


def main() -> list:
    inst = G.instances()
    items = E.assembly()
    boxes = [s.bounding_box() for s in items]

    def overlap(a, b, pad=0.0):
        return (a.min.X - pad < b.max.X and b.min.X - pad < a.max.X and
                a.min.Y - pad < b.max.Y and b.min.Y - pad < a.max.Y and
                a.min.Z - pad < b.max.Z and b.min.Z - pad < a.max.Z)

    sec = "[3D-1] interference"
    print(f"\n{sec}")
    pairs = [(i, j) for i, j in itertools.combinations(range(len(items)), 2)
             if overlap(boxes[i], boxes[j])]
    clashes = [(items[i].label, items[j].label) for i, j in pairs
               if (items[i] & items[j]).volume > 1e-3]
    check(sec, not clashes, f"{len(pairs)} neighbouring pairs, {len(clashes)} interpenetrate"
          + (f": {clashes[:3]}" if clashes else ""))

    sec = "[3D-2] every mortise holds a tab"
    print(f"\n{sec}")
    holes, empty = 0, []
    for n, (p, k, plane, w0, loops) in enumerate(inst):
        for h in loops[1:]:
            if len(h) != 8:
                continue                      # lightening hole, meant to stay empty
            holes += 1
            plug = E.solid([h], E.PLANES[plane](w0))
            pb = plug.bounding_box()
            filled = any(m != n and overlap(pb, boxes[m]) and (plug & items[m]).volume > 1.0
                         for m in range(len(items)))
            if not filled:
                empty.append(f"{items[n].label} hole @{pb.center().X:.0f},"
                             f"{pb.center().Y:.0f},{pb.center().Z:.0f}")
    check(sec, not empty, f"{holes - len(empty)}/{holes} mortises filled"
          + (f"; empty: {empty[:4]}" if empty else ""))

    sec = "[3D-3] load path"
    print(f"\n{sec}")
    by = lambda s: [it for it in items if s in it.label]

    def touch(a, b):
        return a.distance_to(b) <= TOUCH

    def engaged(a, b):
        """tab inside the other part's mortise: within the slot clearance"""
        return a.distance_to(b) <= G.F / 2 + TOUCH

    floor = [s for s in items if s.bounding_box().min.Z < 1e-6]
    names = sorted({s.label.split()[1] for s in floor})
    check(sec, {"ARM-OUTER", "ARM-INNER-L", "ARM-INNER-R", "RIB-A", "RIB-B"} <= set(names),
          f"on the floor: {', '.join(names)}")
    arms = by("ARM-OUTER") + by("ARM-INNER")
    bad = [s.label for s in by("ARM-SPACER") if sum(touch(s, a) for a in arms) != 2]
    check(sec, not bad, f"{6 - len(bad)}/6 spacers bear on both panels of their arm")
    ribs, inner = by("RIB-"), by("ARM-INNER")
    bad = [s.label for s in by("RAIL-")
           if not all(touch(s, r) for r in ribs + inner)]
    check(sec, not bad, f"{3 - len(bad)}/3 rails sit in all 3 ribs and both arm panels")
    rails = by("RAIL-")
    bad = [s.label for s in by("SEAT-DECK")
           if sum(touch(s, r) for r in ribs) < 2 or not all(touch(s, r) for r in rails)]
    check(sec, not bad, f"{2 - len(bad)}/2 decks bear on 2 ribs and all 3 rails")
    posts = ribs + inner
    bad = [s.label for s in by("BACK-ARCH") if sum(engaged(s, q) for q in posts) != 2]
    check(sec, not bad, f"{4 - len(bad)}/4 arches tabbed into the posts either side")

    sec = "[3D-4] assembly sequence: every piece slides home along one axis"
    print(f"\n{sec}")
    lab = {s.label: s for s in items}
    placed, blocked = [], []
    for name, d in SEQUENCE:
        s = lab[name]
        for off in OFFSETS:
            moved = s.moved(Location((-d[0] * off, -d[1] * off, -d[2] * off)))
            mb = moved.bounding_box()
            hit = [o.label for o in placed if overlap(mb, o.bounding_box())
                   and (moved & o).volume > 1e-3]
            if hit:
                blocked.append(f"{name} at {off:g} mm hits {hit[0]}")
                break
        placed.append(s)
    check(sec, not blocked and len(placed) == len(items),
          f"{len(placed)} pieces in order, {len(blocked)} blocked on the way in"
          + (f": {blocked[:3]}" if blocked else ""))

    sec = "[3D-5] overall size"
    print(f"\n{sec}")
    bb = Compound(children=items).bounding_box()
    check(sec, bb.min.Z > -1e-6 and abs(bb.size.X - G.W) < 1e-6 and abs(bb.size.Y - G.D) < 1e-6
          and abs(bb.max.Z - G.ARCH_TOP) < 1e-6,
          f"frame {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, standing on z = 0")
    print(f"\n3D FAILURES: {sum(not r[1] for r in RESULTS)}")
    return RESULTS


if __name__ == "__main__":
    raise SystemExit(1 if any(not r[1] for r in main()) else 0)
