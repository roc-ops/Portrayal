"""Draw a face with ONLY its governed parts, so their positions can be checked.

THE PARTS GO DOWN BEFORE THE METAL. A faceplate is easiest to get right in the
order it is built: seat every standard part where the document says it goes,
check those, then draw the sheet metal around them, then print the legends. This
renders the first stage on its own - no bezels, no vendor trim, no silkscreen,
no hand-drawn housings - because those are exactly the things that make a wrong
position look plausible. A bare row of connectors on an empty panel either lines
up with the drawing or visibly does not.

WHAT IT DRAWS is every `std/` part the view resolves to, at its absolute position
on the face, with its own skin verbatim. It reaches them the way the device does:
through wrappers (`parts:`) and through modules that carry bays, accumulating
offsets on the way down. A DE-9 seated as `common/db9-receptacle` appears here as
the `std/db9` inside it, 5.165 in from the wrapper's corner, because that is
where the governed aperture actually is.

WHAT IT LEAVES OUT is everything else, and the gaps are the point: each one is a
place where this face draws its own art instead of composing a standard. Run
audit-standards.py to see them named.

NOTHING HERE READS A PIXEL. Positions come from the contracts, sizes from the
registry, and the only picture involved is the one a human compares the output
against afterwards.

Usage:  render-standards.py <vendor>/<model> <view> [--out FILE]
"""
import argparse
import pathlib
import re

import yaml

ROOT = pathlib.Path('library')
SVG = 'http://www.w3.org/2000/svg'


def load(ref):
    ns, rest = ref.split('/', 1)
    name = rest.split('@')[0]
    for v in ('v1', 'v2', 'v3', 'v4'):
        p = ROOT / 'components' / ns / name / v / 'contract.yaml'
        if p.exists():
            return yaml.safe_load(p.read_text()), p.parent
    return None, None


def skin_body(d, uid):
    """A skin's contents with every id made unique, so twenty copies can coexist."""
    t = (d / 'skins' / 'default.svg').read_text()
    t = t[t.index('>', t.index('<svg')) + 1:t.rindex('</svg>')]
    t = re.sub(r'<!--.*?-->', '', t, flags=re.S)
    t = re.sub(r'id="([^"]+)"', lambda m: f'id="{uid}-{m.group(1)}"', t)
    return re.sub(r'url\(#([^)]+)\)', lambda m: f'url(#{uid}-{m.group(1)})', t)


def walk(ref, x, y, rot, path, out):
    """Collect every std/ leaf under `ref`, with absolute position.

    Offsets accumulate through wrappers and through nested bays alike, which is
    the same descent the renderer makes and the reason a part seated three
    levels down still lands where the face puts it.
    """
    c, d = load(ref)
    if c is None:
        return
    if ref.startswith('std/'):
        out.append(dict(ref=ref, at=(x, y), rot=rot, path=path,
                        size=(c['size']['w'], c['size']['h']), dir=d,
                        conforms=c.get('conforms')))
        return
    for p in (c.get('parts') or []):
        px, py = p.get('at', [0, 0])
        walk(p['ref'], x + px, y + py, p.get('rotate') or rot,
             f"{path}/{p.get('id', '?')}", out)
    for bid, bay in (c.get('bays') or {}).items():
        sub = bay.get('default') or (bay.get('accepts') or [None])[0]
        if sub:
            bx, by = seat(bay, sub)
            walk(sub, x + bx, y + by, bay.get('rotate') or rot,
                 f'{path}/{bid}', out)


def seat(bay, ref):
    """Where a bay's occupant actually lands: CENTRED, not corner-aligned.

    render.py hangs a bay's occupant by its centre - translate(centre) rotate
    translate(-w/2,-h/2) - so a part smaller than its bay sits in the middle of
    it. Reading `at` as the occupant's top-left agrees only when the two are the
    same size, which every bay on this device happened to be until a 69.85 drive
    went into a 79.4 slot and sat 4.8 mm left of where it renders.
    """
    bx, by = bay.get('at', [0, 0])
    bw, bh = bay.get('size', [None, None])
    c, _ = load(ref)
    if c is None or bw is None:
        return bx, by
    # THE UNROTATED SIZE, deliberately. The emitted transform is
    # translate(at) rotate(deg, w/2, h/2), which turns the part about its own
    # UNROTATED centre - so `at` is where the unrotated box would sit and the
    # centre lands at at + (w/2, h/2) whatever the angle. Swapping w and h here
    # for a rotated bay looks right and is not: it put a 2.5 inch drive 35 mm
    # from its bay, because the swap and the rotation then applied twice.
    pw, ph = c['size']['w'], c['size']['h']
    return bx + bw / 2 - pw / 2, by + bh / 2 - ph / 2


def wanted(item, config):
    """`only-in` decides whether this belongs in the configuration asked for.

    THE CONFIGURATION IS NOT COSMETIC HERE. Comparing the default build against
    a figure of the 4 x 2.5 rear-drive machine puts a riser where the document
    has drive bays, and the whole right-hand third of the face reads as wrong
    when nothing is. Pick the configuration the figure is of.
    """
    only = item.get('only-in')
    return not only or (config in only)


def collect(dev, vname, config=None, fit=None):
    """`fit` overrides which accepted module a bay is drawn with.

    THE SCHEMA CANNOT SAY THIS YET. A bay declares `accepts` and one `default`,
    and `only-in` can remove the bay from a configuration entirely - but nothing
    records that rear-4-sff fits riser 2 with its one-slot variant while
    no-rear-storage fits the three-slot one. `occupants` is next door and is not
    it: that is what is PLUGGED INTO a receptacle, not which module fills a bay.
    So this is a command-line override for comparing against a figure, and the
    gap it papers over is worth fixing in the schema rather than here.
    """
    fit = fit or {}
    view = dev['views'][vname]
    comps = view.get('components') or {}
    found = []
    for p in comps.get('placements') or []:
        if wanted(p, config):
            walk(p['ref'], *p.get('at', [0, 0]), p.get('rotate'), p['id'], found)
    for b in comps.get('bays') or []:
        if not wanted(b, config):
            continue
        sub = fit.get(b['id']) or b.get('default') or (
            b.get('accepts') or [None])[0]
        if sub:
            bx, by = seat({'at': b.get('at', [0, 0]),
                           'size': [b['size']['w'], b['size']['h']],
                           'rotate': b.get('rotate')}, sub)
            walk(sub, bx, by, b.get('rotate'), b['id'], found)
    return view, found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('device')
    ap.add_argument('view')
    ap.add_argument('--out', default=None)
    ap.add_argument('--scale', type=float, default=4.0)
    ap.add_argument('--fit', action='append', default=[],
                    metavar='BAY=REF',
                    help='draw a bay with one of its other accepted modules')
    ap.add_argument('--config', default=None,
                    help='named configuration; bays with an '
                         '`only-in` that excludes it are omitted')
    a = ap.parse_args()

    dev = yaml.safe_load((ROOT / 'devices' / a.device / 'device.yaml').read_text())
    fit = dict(s.split('=', 1) for s in a.fit)
    view, found = collect(dev, a.view, a.config, fit)
    W, H = view['size']['w'], view['size']['h']

    s = [f'<svg xmlns="{SVG}" width="{W * a.scale:.0f}" '
         f'height="{H * a.scale:.0f}" viewBox="0 0 {W} {H}">',
         # the panel, drawn as an outline only: this sheet is about what sits ON
         # the face, and a painted panel hides the alignment it is there to show
         f'<rect x="0.25" y="0.25" width="{W - 0.5}" height="{H - 0.5}" '
         'fill="#f4f5f6" stroke="#9aa1a8" stroke-width="0.5"/>']
    for i, f in enumerate(found):
        x, y = f['at']
        w, h = f['size']
        tf = f'translate({x:g},{y:g})'
        if f['rot']:
            tf += f" rotate({f['rot']} {w / 2:g} {h / 2:g})"
        s.append(f'<g transform="{tf}"><title>{f["path"]} = {f["ref"]}</title>'
                 f'{skin_body(f["dir"], f"p{i}")}</g>')
    s.append('</svg>')

    out = pathlib.Path(a.out or f'{a.device.replace("/", "-")}.{a.view}.std.svg')
    if a.config:
        print(f'configuration: {a.config}')
    out.write_text('\n'.join(s) + '\n')
    print(f'{out}  {len(found)} standard part(s) on a {W} x {H} face')
    for f in sorted(found, key=lambda f: f['at'][0]):
        print(f"   {f['at'][0]:8.2f} {f['at'][1]:7.2f}  {f['ref']:<24} {f['path']}")


if __name__ == '__main__':
    main()
