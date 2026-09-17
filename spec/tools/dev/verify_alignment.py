"""What lines up with what, on a face, derived rather than asserted.

A FACEPLATE IS MOSTLY ALIGNMENT. Ports sit on shared baselines, repeated parts
sit on constant pitches, and a chassis that got one of those wrong looks almost
right - which is exactly the failure a drawing does not advertise. This reads the
standard parts a view resolves to and reports the alignment STRUCTURE it finds:
which edges are shared, and which runs are evenly spaced.

IT ASSERTS NOTHING ABOUT A PARTICULAR MACHINE, which is what makes it usable on a
device nobody has modelled yet. It does not know that this server's iDRAC, serial
and VGA share a baseline; it reports that three parts share a bottom edge at
y=80.00, and a human checks that against the document that says so. The output is
a short list of claims to spot-check, not a pass mark.

WHY THIS AND NOT PIXELS. Every number here comes from contracts and the registry.
Measuring the render instead would test the renderer, and measuring a photograph
would test the camera; neither tests whether the model says what the document
says. A tolerance is still needed - parts are placed to two decimals and shared
edges rarely come out bit-identical - so `--tol` is explicit and small.

Usage:  verify_alignment.py <vendor>/<model> <view> [--tol 0.15]
"""
import argparse
import collections

import yaml

# A PLAIN IMPORT, because the file it wants is no longer called
# `render_standards.py`. A hyphen is not an identifier, so this reached for
# `importlib.util.spec_from_file_location` to load a sibling by path - fifteen
# lines standing in for one, and invisible to every tool that reads imports
# (#178).
from portrayal_dev import render_standards as rstd
def families(vals, tol):
    """Group near-equal coordinates, reporting each cluster's spread.

    Clustering rather than exact match because a shared edge assembled from
    three different offsets lands within a hair of itself, not on it - and a
    check that only accepts bit-identical numbers would report no alignments at
    all on a face that is in fact fully aligned.
    """
    out = []
    for key, name in sorted(vals):
        if out and key - out[-1][0][-1] <= tol:
            out[-1][0].append(key)
            out[-1][1].append(name)
        else:
            out.append(([key], [name]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('device')
    ap.add_argument('view')
    ap.add_argument('--tol', type=float, default=0.15)
    ap.add_argument('--config', default=None)
    a = ap.parse_args()

    dev = yaml.safe_load(
        (rstd.ROOT / 'devices' / a.device / 'device.yaml').read_text())
    view, found = rstd.collect(dev, a.view, a.config)
    if not found:
        raise SystemExit('no standard parts resolve on this view')

    edges = collections.defaultdict(list)
    for f in found:
        (x, y), (w, h) = f['at'], f['size']
        # a rotated part's footprint is its size turned, which is the only place
        # rotation can change an alignment
        if (f['rot'] or 0) % 180 == 90:
            w, h = h, w
        n = f['path']
        edges['left'].append((round(x, 3), n))
        edges['right'].append((round(x + w, 3), n))
        edges['top'].append((round(y, 3), n))
        edges['bottom'].append((round(y + h, 3), n))
        edges['centre-x'].append((round(x + w / 2, 3), n))
        edges['centre-y'].append((round(y + h / 2, 3), n))

    print(f'=== {a.device} / {a.view} - {len(found)} standard parts, '
          f'tolerance {a.tol} mm ===\n')
    print('SHARED EDGES  (two or more parts on one line)')
    any_shared = False
    for kind in ('left', 'right', 'top', 'bottom', 'centre-x', 'centre-y'):
        for keys, names in families(edges[kind], a.tol):
            if len(names) < 2:
                continue
            any_shared = True
            spread = max(keys) - min(keys)
            print(f'  {kind:<9} {sum(keys) / len(keys):8.2f}  '
                  f'{len(names)} parts, spread {spread:.2f}')
            for nm in names:
                print(f'                       {nm}')
    if not any_shared:
        print('  none - which on a faceplate is itself a finding')

    print('\nEVEN RUNS  (three or more of one part on a constant pitch)')
    # GROUPED BY PARENT, NOT BY PART TYPE. Pooling every instance of a ref
    # across the whole face mixes three risers into one "run" and reports the
    # gaps BETWEEN risers as pitch errors - seven brackets came out UNEVEN when
    # each riser's three are perfectly even and it is the gap to the next riser
    # that is different, which is not a pitch at all. A run is a repetition
    # inside one container.
    runs = collections.defaultdict(list)
    for f in found:
        parent = f['path'].rsplit('/', 1)[0] if '/' in f['path'] else '(face)'
        runs[(parent, f['ref'])].append(f)
    found_run = False
    for (parent, ref), items in sorted(runs.items()):
        for axis, idx in (('x', 0), ('y', 1)):
            vals = sorted(f['at'][idx] for f in items)
            if len(vals) < 3:
                continue
            gaps = [round(b - a_, 3) for a_, b in zip(vals, vals[1:])]
            if all(g < a.tol for g in gaps):
                continue                       # stacked, not a run
            stray = [g for g in gaps if abs(g - gaps[0]) > a.tol]
            found_run = True
            print(f'  {parent}: {len(vals)} x {ref} along {axis}, '
                  f'pitch {gaps[0]:.2f}, '
                  + ('even' if not stray else
                     f'UNEVEN - {len(stray)} gap(s) differ: {gaps}'))
    if not found_run:
        print('  none')


if __name__ == '__main__':
    main()
