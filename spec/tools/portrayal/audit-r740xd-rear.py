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
    ns, rest = ref.split('/')
    name = rest.split('@')[0]
    for v in ('v1', 'v2', 'v3'):
        p = ROOT / 'components' / ns / name / v / 'contract.yaml'
        if p.exists():
            return yaml.safe_load(p.read_text())
    raise SystemExit(f'no contract for {ref}')


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
rows = sorted(v['at'][1] for v in riser['bays'].values())
pitch = (rows[-1] - rows[0]) / (len(rows) - 1)
checks.append(('PCIe bracket pitch 20.32', f'{pitch:.2f}', abs(pitch - 20.32) < 0.01))

ndc = comp('dell/ndc-4x-rj45-14g@1')
lx = sorted(v['at'][0] for k, v in ndc['elements'].items()
            if k.startswith('lamp-link'))
jp = (lx[-1] - lx[0]) / 3
checks.append(('NDC jack pitch 22.2', f'{jp:.2f}', abs(jp - 22.2) < 0.05))

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
