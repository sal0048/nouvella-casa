"""3D checks on the exact solids: clashes, every mortise filled, load path,
assembly sequence (each piece slides in vertically), overall size."""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[0] / "curved-sofa"))

from build123d import Compound, Location

import export_step as E
import pebble_geometry as G

TOUCH = 0.01
RESULTS = []


def check(sec, ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    RESULTS.append((sec, bool(ok), msg))


def overlap(a, b, pad=0.0):
    return (a.min.X - pad < b.max.X and b.min.X - pad < a.max.X and a.min.Y - pad < b.max.Y
            and b.min.Y - pad < a.max.Y and a.min.Z - pad < b.max.Z and b.min.Z - pad < a.max.Z)


def main():
    inst = G.instances()
    items = E.assembly()
    boxes = [s.bounding_box() for s in items]

    sec = "[3D-1] interference"
    print(f"\n{sec}")
    pairs = [(i, j) for i, j in itertools.combinations(range(len(items)), 2) if overlap(boxes[i], boxes[j])]
    clashes = [(items[i].label, items[j].label) for i, j in pairs if (items[i] & items[j]).volume > 1e-3]
    check(sec, not clashes, f"{len(pairs)} neighbouring pairs, {len(clashes)} interpenetrate"
          + (f": {clashes[:3]}" if clashes else ""))

    sec = "[3D-2] every mortise holds a tab"
    print(f"\n{sec}")
    holes, empty = 0, []
    for n, (p, k, o, u, v, c) in enumerate(inst):
        for h in p.loops[1:]:
            if len(h) != 8:
                continue
            holes += 1
            plug = E.solid([h], E.frame_plane(o, u, v, c))
            pb = plug.bounding_box()
            if not any(m != n and overlap(pb, boxes[m]) and (plug & items[m]).volume > 1.0
                       for m in range(len(items))):
                empty.append(items[n].label)
    check(sec, not empty, f"{holes - len(empty)}/{holes} mortises filled" + (f"; empty in {empty[:4]}" if empty else ""))

    sec = "[3D-3] load path"
    print(f"\n{sec}")
    by = lambda s: [it for it in items if s in it.label]
    near = lambda a, b, d=G.F / 2 + TOUCH: a.distance_to(b) <= d
    for m in G.MODULES:
        base, seat = by(f"BASE-RING-{m.key}")[0], by(f"SEAT-RING-{m.key}")[0]
        ribs = by(f"RIB-{m.key}")
        bad = [r.label for r in ribs if not (near(r, base) and near(r, seat))]
        check(sec, not bad, f"module {m.key}: {len(ribs) - len(bad)}/{len(ribs)} body ribs bear on both rings")
    seats = by("SEAT-RING")
    for p in G.PEBBLES:
        plate = by(f"PEBBLE-{p.key}-PLATE")[0]
        ribs, spine = by(f"PEBBLE-{p.key}-RIB"), by(f"PEBBLE-{p.key}-SPINE")[0]
        ok = any(plate.distance_to(s) <= TOUCH for s in seats)
        ok &= all(near(r, plate, TOUCH) and near(r, spine) for r in ribs) and near(spine, plate, TOUCH)
        check(sec, ok, f"pebble {p.key}: plate on the seat ring, {len(ribs)} ribs + spine on the plate, egg-crate engaged")

    sec = "[3D-4] assembly sequence: every piece comes down vertically"
    print(f"\n{sec}")
    order = {g: i for i, g in enumerate(G.GROUP_ORDER)}
    seq = sorted(range(len(items)), key=lambda n: order[inst[n][0].group])
    placed, blocked = [], []
    for n in seq:
        s = items[n]
        for off in [o + 0.5 for o in range(0, 40, 2)] + list(range(50, 801, 50)):
            moved = s.moved(Location((0, 0, off)))
            mb = moved.bounding_box()
            hit = [items[m].label for m in placed if overlap(mb, boxes[m]) and (moved & items[m]).volume > 1e-3]
            if hit:
                blocked.append(f"{s.label} at +{off:g} hits {hit[0]}")
                break
        placed.append(n)
    check(sec, not blocked, f"{len(placed)} pieces lowered in order {' > '.join(G.GROUP_ORDER)}, "
          f"{len(blocked)} blocked" + (f": {blocked[:3]}" if blocked else ""))

    sec = "[3D-5] overall size"
    print(f"\n{sec}")
    bb = Compound(children=items).bounding_box()
    check(sec, bb.min.Z > -1e-6, f"frame {bb.size.X:.0f} x {bb.size.Y:.0f} x {bb.size.Z:.0f} mm on z = 0")
    print(f"\n3D FAILURES: {sum(not r[1] for r in RESULTS)}")
    return RESULTS


if __name__ == "__main__":
    raise SystemExit(1 if any(not r[1] for r in main()) else 0)
