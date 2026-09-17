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


# A GUARD. #179 named this file for not having one - it audits ONE device's rear
# face and did the whole audit on import, which `dev/` being importable turns
# from a curiosity into a hazard. A module-level `if` opens no scope, so the
# script path is unchanged.
if __name__ == "__main__":
    import argparse
    # No options: this audits ONE device's rear face against one appendix of one
    # ISM, which is what #179 meant by "device-specific". `--help` exists so that
    # a reader running it by accident is told that before it prints a table.
    argparse.ArgumentParser(
        description=__doc__.strip().splitlines()[0],
        epilog="Takes no arguments: it reads library/devices/dell/r740xd "
               "and Table 9 of that machine's ISM.").parse_args()
    d = yaml.safe_load((ROOT / 'devices/dell/r740xd/device.yaml').read_text())
    rear = d['views']['rear']
    bays = {b['id']: b for b in rear['components']['bays']}
    pl = {p['id']: p for p in rear['components']['placements']}
    cut = {c['id']: c for c in rear['panel']['cutouts']}

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

    # THE SIZE CAME FROM A FIGURE AND NOW COMES FROM THE CAD. 88.7 x 41.8 was
    # photo-measured off ISM figure 8 at 7.2 px/mm; Dell's own service model,
    # descended past the named assembly to the mesh child that is 195.5 deep, gives
    # 86.3 x 39.1 and puts the body's left edge at face x 251.34 against the 251.30
    # this device seats it at. A measurement in software beats a reading off a
    # figure, so the expectation moves with it.
    psu = comp('dell/psu-1100w-ac-14g@1')
    checks.append(('PSU 86.3 x 39.1 (vendor CAD)',
                   f"{psu['size']['w']} x {psu['size']['h']}",
                   psu['size'] == {'w': 86.3, 'h': 39.1}))
    # THE POSITION IS NOT SETTLED AND THIS NO LONGER PRETENDS IT IS. y 45.0 was
    # argued off ISM figure 9 in the same breath as a height of 41.8, and that
    # height is now disproven; y 46.20 is what the device carries and its only
    # corroboration is a comment that cites the seating back. So the check that can
    # be made is the one that does not need the answer: the bay reserves exactly
    # what the module measures. See the device's psu-top-edge-unsettled gap.
    checks.append(('PSU bay fits the module',
                   f"bay {bays['psu-1']['size']['w']} x {bays['psu-1']['size']['h']}"
                   f" at y {bays['psu-1']['at'][1]}",
                   bays['psu-1']['size'] == psu['size']))


    def bottom(pid):
        """Where a port's APERTURE ends on the face - the hole, not the bezel.

        THIS USED TO COMPARE A BEZEL WITH TWO APERTURES. serial and vga each compose
        a `shell` and it reached that; idrac9 composes none at that id, so it fell
        back to the whole part - which for an RJ45 is the bezel, and a bezel is
        deliberately bigger than its hole. It read 80.95 against 80.50 and called
        the row misaligned when nothing was.
        The cutout is the hole in the sheet metal and every one of the three has
        one, so it is the measurement they can all be held to. The device says as
        much where it places this port: "THE HOLE FOLLOWS THE COMPOSED APERTURE,
        NOT THE BEZEL'S CENTRE".
        """
        k = cut.get(pid)
        if k:
            return k['at'][1] + k['size'][1]
        p = pl[pid]
        c = comp(p['ref'])
        inner = [q for q in (c.get('parts') or []) if q.get('id') == 'shell']
        if not inner:
            return p['at'][1] + c['size']['h']
        return p['at'][1] + inner[0]['at'][1] + comp(inner[0]['ref'])['size']['h']


    # AND THE 80.0 WAS NEVER SOURCED. No fact sheet for this device is held; the
    # number was written into this tool. What the row is FOR is that the three
    # openings finish flush with one another, which is a relative claim the drawing
    # can be held to and which survives the panel being re-measured. The absolute is
    # printed so a reader can still challenge it.
    bs = {k: bottom(k) for k in ('idrac9', 'serial', 'vga')}
    spread = max(bs.values()) - min(bs.values())
    checks.append(('I/O apertures finish flush (<0.1)',
                   ', '.join(f'{k} {v:.2f}' for k, v in bs.items()) +
                   f'  spread {spread:.2f}',
                   spread < 0.1))

    print('\nB.3  measured-geometry claim             model                      ok')
    bad = 0
    for name, got, ok in checks:
        bad += not ok
        print(f'     {name:<36} {got:<26} {"yes" if ok else "NO"}')
    print(f'\n{len(TABLE9)-miss}/{len(TABLE9)} inventory, '
          f'{len(checks)-bad}/{len(checks)} geometry')
