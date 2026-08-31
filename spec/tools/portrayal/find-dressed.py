"""What does the library already have that composes this standard, and dressed how?

THE SECOND STAGE OF A FACE IS DRESSING, NOT DRAWING. Once the governed parts sit
where the document puts them, what is left is the trim around them - a bezel, a
pair of standoffs, two lamps by the latch - and almost none of that is unique to
one machine. There are only so many ways to dress an RJ45. So the question at
this stage is never "how do I draw it" but "which of these do we already have",
and that question deserves a command rather than a memory.

WHAT IT REPORTS, for every component that reaches the named standard through
`parts:`:

    the size it adds around the governed core, in mm on each side, which is
    what a bezel IS - if a part is the same size as the standard it composes,
    it is a wrapper that adds no trim
    its lamps, by name, because "two LEDs up by the latch" is the distinguishing
    feature of most dressed jacks and is invisible in a size
    its other elements and its skins

WHAT IT DOES NOT DO is choose. Two dressed RJ45s differing in where their lamps
sit are both correct parts, and which one matches the machine in front of you is
a question for the picture. This narrows the field to the candidates and prints
what separates them.

Usage:  find-dressed.py std/rj45          all dressed variants of one standard
        find-dressed.py --all             every standard that has any
"""
import argparse
import pathlib

import yaml

ROOT = pathlib.Path('library/components')


def contracts():
    for p in sorted(ROOT.glob('*/*/v*/contract.yaml')):
        try:
            d = yaml.safe_load(p.read_text())
        except Exception:
            continue
        if d:
            yield p, d


def reaches(d, target, seen=()):
    """Does this component compose `target`, directly or through a wrapper?"""
    for part in (d.get('parts') or []):
        ref = part.get('ref', '')
        base = ref.split('@')[0]
        if base == target:
            return part
        if base in seen:
            continue
        ns, name = base.split('/', 1)
        for v in ('v1', 'v2', 'v3'):
            f = ROOT / ns / name / v / 'contract.yaml'
            if f.exists():
                inner = reaches(yaml.safe_load(f.read_text()), target,
                                seen + (base,))
                if inner:
                    return part
                break
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('standard', nargs='?')
    ap.add_argument('--all', action='store_true')
    a = ap.parse_args()

    index = {}
    for p, d in contracts():
        for part in (d.get('parts') or []):
            base = part.get('ref', '').split('@')[0]
            if base.startswith('std/'):
                index.setdefault(base, []).append((p, d))

    if a.all or not a.standard:
        print('standards that something already dresses:\n')
        for std, users in sorted(index.items()):
            names = ', '.join(f"{q.parts[-4]}/{q.parts[-3]}" for q, _ in users)
            print(f'  {std:<24} {len(users):2d}  {names}')
        print('\nrun again with one of these to see how each is dressed')
        return

    target = a.standard if '/' in a.standard else f'std/{a.standard}'
    base = yaml.safe_load(
        (ROOT / target.split("/")[1].join(['std/', '']).replace('std/', 'std/')
         ).parent.joinpath()) if False else None
    ns, nm = target.split('/', 1)
    core = None
    for v in ('v1', 'v2', 'v3'):
        f = ROOT / ns / nm / v / 'contract.yaml'
        if f.exists():
            core = yaml.safe_load(f.read_text())
            break
    if core is None:
        raise SystemExit(f'no such standard part: {target}')
    cw, ch = core['size']['w'], core['size']['h']
    print(f'{target}  {cw} x {ch}\n')

    users = index.get(target, [])
    if not users:
        print('  NOTHING DRESSES IT YET. That is a part to build, not a '
              'problem with the face.')
        return
    for p, d in sorted(users, key=lambda t: str(t[0])):
        name = f'{p.parts[-4]}/{p.parts[-3]}@{p.parts[-2][1:]}'
        w, h = d['size']['w'], d['size']['h']
        part = reaches(d, target) or {}
        at = part.get('at', [0, 0])
        els = d.get('elements') or {}
        lamps = [k for k, v in els.items() if (v or {}).get('class') == 'led']
        other = [k for k in els if k not in lamps]
        print(f'  {name}')
        print(f'      size {w} x {h}   adds '
              f'{at[0]:+.2f} left, {w - cw - at[0]:+.2f} right, '
              f'{at[1]:+.2f} above, {h - ch - at[1]:+.2f} below')
        print(f'      lamps: {", ".join(lamps) if lamps else "none"}')
        if other:
            print(f'      other: {", ".join(other)}')
        print(f'      skins: {", ".join(d.get("skins") or [])}')
        desc = " ".join((d.get('description') or '').split())
        print(f'      {desc[:150]}\n')


if __name__ == '__main__':
    main()
