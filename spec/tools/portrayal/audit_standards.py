"""Which parts on a face come from a standard, and which were drawn by hand?

BEFORE THE SHEET METAL, THE PARTS. A faceplate is easiest to get right in the
order it is built: seat every governed part where the drawing says it goes, check
those, then draw the metal around them, then print the legends. Metal drawn first
has nothing to be right about; metal drawn last only has to meet parts already in
the right place. This script is the gate between the first stage and the second.

WHAT IT CATCHES. A connector can look correct and still be a hand drawing - the
right size, the right place, its own idea of what an RJ45 looks like. Ten of
those on one face are ten chances to disagree with each other, and none of them
improve when the registry does. The check is not "is there a component here" but
"does the art come from the governed part":

    STANDARD   the component composes a std/ part, or conforms: to a registry key
    LOCAL      it draws its own face - the size may be right and the art is its
               own, so it will not track the standard and cannot be fixed once
    NO STD     nothing in the registry covers this at all, which is a job to do
               before the face can be finished rather than a defect in it

The third is the important one and the reason this prints rather than fails: a
face that needs a part nobody has built yet is not a broken face, it is a face
waiting on a component. Go and build the standard, then come back.

Usage:  audit_standards.py <vendor>/<model> [view]
"""
import pathlib
import sys

import yaml

ROOT = pathlib.Path('library')
STANDARDS = yaml.safe_load(
    (pathlib.Path('spec/schemas/standards.yaml')).read_text()) or {}
KEYS = set(STANDARDS.get('standards', STANDARDS).keys())


def load(ref):
    """Resolve `ns/name@ver` to its contract, or None if there is no such part."""
    ns, rest = ref.split('/', 1)
    name = rest.split('@')[0]
    for v in ('v1', 'v2', 'v3', 'v4'):
        p = ROOT / 'components' / ns / name / v / 'contract.yaml'
        if p.exists():
            return yaml.safe_load(p.read_text())
    return None


def verdict(ref, seen=()):
    """STANDARD if this part is governed art, LOCAL if it draws its own face.

    Composition counts transitively: a Dell wrapper that places std/c14-inlet is
    as governed as the inlet itself, which is the whole point of wrapping.
    """
    if ref in seen:                       # a cycle is a bug, not an answer
        return 'LOCAL', 'circular reference'
    c = load(ref)
    if c is None:
        return 'MISSING', 'no contract resolves'
    if c.get('conforms') in KEYS:
        return 'STANDARD', f"conforms: {c['conforms']}"
    for part in (c.get('parts') or []):
        sub = part.get('ref', '')
        if sub.startswith('std/'):
            return 'STANDARD', f"composes {sub}"
        v, why = verdict(sub, seen + (ref,))
        if v == 'STANDARD':
            return 'STANDARD', f"composes {sub} ({why})"
    return 'LOCAL', 'draws its own face'


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__.strip().splitlines()[-1])
    dev = yaml.safe_load((ROOT / 'devices' / sys.argv[1] /
                          'device.yaml').read_text())
    views = [sys.argv[2]] if len(sys.argv) > 2 else list(dev['views'])
    tally = {}
    for vname in views:
        view = dev['views'][vname]
        rows = []
        comps = view.get('components') or {}
        for p in comps.get('placements') or []:
            rows.append((p['id'], p['ref'], 'placement'))
        for b in comps.get('bays') or []:
            for ref in (b.get('accepts') or [b.get('default')]):
                if ref:
                    rows.append((b['id'], ref, 'bay'))
        if not rows:
            continue
        print(f'\n=== {sys.argv[1]} / {vname} ===')
        print(f"    {'id':<20} {'ref':<34} {'verdict':<9} why")

        def report(pid, ref, depth=0):
            """A module that hosts bays is audited THROUGH, not just at.

            A riser draws its own plate, which is correct - nobody standardises
            vendor sheet metal - and it carries the slots that hold the parts
            that DO have a standard. Stopping at the riser reports the one thing
            here that could never be governed and hides the eight that are.
            """
            v, why = verdict(ref)
            tally[v] = tally.get(v, 0) + 1
            mark = ' ' if v == 'STANDARD' else '<-'
            pad = '  ' * depth
            print(f' {mark} {pad}{pid:<{20 - 2 * depth}} {ref:<34} {v:<9} {why}')
            c = load(ref)
            for bid, bay in ((c.get('bays') or {}) if c else {}).items():
                for sub in (bay.get('accepts') or [bay.get('default')]):
                    if sub:
                        report(bid, sub, depth + 1)

        for pid, ref, kind in rows:
            report(pid, ref)
    total = sum(tally.values())
    print(f'\n{tally.get("STANDARD", 0)}/{total} come from a standard; '
          f'{tally.get("LOCAL", 0)} draw their own face'
          + (f'; {tally["MISSING"]} unresolved' if tally.get('MISSING') else ''))


if __name__ == '__main__':
    main()
