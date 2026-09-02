"""Check the modelled rear against the fact sheet, instead of against a glance.

The fact sheet records what the documents say the rear has - an inventory in
section B.2 and a table of measured geometry in B.3. Both are checkable against
the device file, which turns "does the drawing look right" into a list that
either passes or names what is missing.

This found the rear handle: ten of eleven Table 9 items were modelled and the
eleventh had been sitting unnoticed through several review passes.
"""
import pathlib

import yaml

ROOT = pathlib.Path('library')


def comp(ref):
    """Resolve `ns/name@major` to its contract.

    THE MAJOR IN THE REF IS THE ANSWER, and this used to ignore it: it walked
    v1, v2, v3 and returned the first directory that existed, so a part with two
    majors in the library was read at whichever came first rather than at the one
    the caller asked for. It also stopped at v3, which is why the audit died on
    common/rj45-port@4 the moment that part reached its fourth major.
    The library keeps one directory per major, so `@4` is `v4` and there is
    nothing to search. The highest present is a fallback for a ref written
    without a major, not the normal path.
    """
    ns, rest = ref.split('/')
    name, _, major = rest.partition('@')
    base = ROOT / 'components' / ns / name
    want = base / f'v{major}' / 'contract.yaml' if major else None
    if want and want.exists():
        return yaml.safe_load(want.read_text())
    got = sorted(base.glob('v*/contract.yaml'),
                 key=lambda q: int(q.parent.name[1:]))
    if not got:
        raise SystemExit(f'no contract for {ref}')
    if major:
        print(f'     NOTE {ref} has no v{major}; reading {got[-1].parent.name}')
    return yaml.safe_load(got[-1].read_text())


d = yaml.safe_load((ROOT / 'devices/dell/r740xd/device.yaml').read_text())
rear = d['views']['rear']
bays = {b['id']: b for b in rear['components']['bays']}
pl = {p['id']: p for p in rear['components']['placements']}

# ---- B.2, the inventory --------------------------------------------------
TABLE9 = [('full-height PCIe slot (7)', 'riser-1'),
          ('half-height PCIe slot', 'riser-2'),
          ('rear handle', 'rear-handle'),
          ('power supply unit (2)', 'psu-1'),
          ('NIC ports on the NDC', 'ndc'),
          ('USB 3.0 (2)', 'usb-1'),
          ('VGA port', 'vga'),
          ('serial port', 'serial'),
          ('iDRAC9 dedicated port', 'idrac9'),
          ('system identification button', 'sys-id'),
          ('unnamed second circle', 'sys-status')]
have = set(bays) | set(pl)
print('B.2  ISM Table 9 item                    modelled')
miss = 0
for label, key in TABLE9:
    ok = key in have
    miss += not ok
    print(f'     {label:<36} {"yes" if ok else "NO  <-- MISSING"}')

# ---- B.3, the measured geometry ------------------------------------------
checks = []
riser = comp('dell/riser-2a-14g@1')
rows = sorted(v['at'][1] for v in (riser.get('bays') or {}).values())
if len(rows) >= 2:
    pitch = (rows[-1] - rows[0]) / (len(rows) - 1)
    checks.append(('PCIe bracket pitch 20.32', f'{pitch:.2f}',
                   abs(pitch - 20.32) < 0.01))
else:
    checks.append(('PCIe bracket pitch 20.32', 'no slot bays found', False))

# THE JACKS ARE COMPOSED PARTS NOW, AND THIS ASKED FOR LAMPS. The NDC used to
# draw its own indicators as `elements` and the four `lamp-link` positions stood
# in for the four jacks; it now composes dell/rj45-port-14g four times and has no
# `elements` at all, so this line raised KeyError and took the whole audit with
# it - including the eleven inventory rows above, which were fine.
#
# THE PORT PLACEMENTS ARE THE BETTER READING ANYWAY. A lamp is near its jack; a
# port placement IS the jack, so the pitch now comes from the thing being
# measured rather than from a proxy for it. The old shape is still accepted,
# because this tool is meant to survive the part being rearranged again.
#
# AND A MISSING MEASUREMENT IS A FAILED CHECK, NOT A TRACEBACK. That is the
# actual lesson: an audit that dies on the first part it cannot read tells you
# less than one that prints a red line and carries on to the other six.
ndc = comp('dell/ndc-4x-rj45-14g@1')
jx = sorted(q['at'][0] for q in (ndc.get('parts') or [])
            if str(q.get('id', '')).startswith('port-'))
if not jx:
    jx = sorted(v['at'][0] for k, v in (ndc.get('elements') or {}).items()
                if k.startswith('lamp-link'))
if len(jx) >= 2:
    jp = (jx[-1] - jx[0]) / (len(jx) - 1)
    checks.append((f'NDC jack pitch 22.2 (from {len(jx)})', f'{jp:.2f}',
                   abs(jp - 22.2) < 0.05))
else:
    checks.append(('NDC jack pitch 22.2', 'no jack positions found', False))

rj = comp('common/rj45-jack@2')
checks.append(('iDRAC9 RJ45 ~15.5 wide', f"{rj['size']['w']}",
               abs(rj['size']['w'] - 15.54) < 0.4))

psu = comp('dell/psu-1100w-ac-14g@1')
checks.append(('PSU 88.7 x 41.8', f"{psu['size']['w']} x {psu['size']['h']}",
               psu['size'] == {'w': 88.7, 'h': 41.8}))
checks.append(('PSU top at y 45.0', f"{bays['psu-1']['at'][1]}",
               bays['psu-1']['at'][1] == 45.0))


def bottom(pid):
    """Where a port's own aperture ends on the face - through the wrapper."""
    p = pl[pid]
    c = comp(p['ref'])
    inner = [q for q in (c.get('parts') or []) if q.get('id') == 'shell']
    if not inner:
        return p['at'][1] + c['size']['h']
    std = comp(inner[0]['ref'])
    return p['at'][1] + inner[0]['at'][1] + std['size']['h']


bs = {k: bottom(k) for k in ('idrac9', 'serial', 'vga')}
checks.append(('I/O bottoms share y = 80',
               ', '.join(f'{k} {v:.2f}' for k, v in bs.items()),
               all(abs(v - 80.0) < 0.1 for v in bs.values())))

print('\nB.3  measured-geometry claim             model                      ok')
bad = 0
for name, got, ok in checks:
    bad += not ok
    print(f'     {name:<36} {got:<26} {"yes" if ok else "NO"}')
print(f'\n{len(TABLE9)-miss}/{len(TABLE9)} inventory, '
      f'{len(checks)-bad}/{len(checks)} geometry')
