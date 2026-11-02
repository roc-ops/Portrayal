// A placed part's seat is ONE slot of its face when the device index lists it and
// the drawing yields it too (test_placed_part_seats.py runs this).
//
// The build lists the seats of a part placed straight on a device face in the
// device's `cages[view]`, each under `<placement>/<part>` (render.py
// nested_seat_entries), and the explorer reads the same seats off the drawing
// (nestedSlots, through the `data-ref` of the placed part). faceCages joins the
// two lists; a seat in both must come out once, as the drawing gives it: that
// entry carries the carrier, its group and its depth, which a swap seats through.
//
// Cases, chosen by argv[2]:
//   once  - faceCages and cageAt on a face with a placed part of two seats
//   alone - a seat only the index lists is kept, and a seat only the drawing
//           yields is found
import {Node, install} from './fake-dom.mjs';

const m = await import('../../../kit/swap.js');
install();

const mode = process.argv[2];
const seat = (id, x) => ({
  id, at: [x, 2], mate: [x + 1.7, 3.7], rotate: null, lift: 3.5, interface: 'terminal-stud',
  kind: 'connector', media: null, accepts: ['generic/ring-lug@1'], 'occupant-attrs': {},
  mirror: false, 'group-states': false});
const STUDS = {name: 'studs', version: '1.0.0', size: {w: 20, h: 8},
               cages: [seat('stud-a', 2), seat('stud-b', 10)]};
const compByRef = ref => ({'test/studs@1': STUDS})[ref] || null;

// the device index lists what the build published: no carrier, no depth
const listed = id => ({...seat(id.split('/')[1], 0), id, group: 'power'});
const port = {id: 'port-1', mate: [4, 4], rotate: null, lift: 0, accepts: ['generic/sfp-lc@1'],
              'occupant-attrs': {}, mirror: false, 'group-states': false};

const drawn = (...ids) => ids.map(c => new Node({
  id: `studs--${c}`, 'data-path': `studs/${c}`, 'data-class': 'port'}, [
  new Node({id: `studs--${c}--opening`, 'data-path': `studs/${c}/opening`})]));
const face = (...ids) => new Node({}, [
  new Node({id: 'port-1', 'data-path': 'port-1', 'data-class': 'port'}),
  new Node({id: 'studs', 'data-path': 'studs', 'data-ref': 'test/studs@1:1.0.0',
            'data-class': 'port'}, drawn(...ids)),
]);
const ids = list => list.map(e => e.id);

if (mode === 'once') {
  const root = face('stud-a', 'stud-b');
  const device = [port, listed('studs/stud-a'), listed('studs/stud-b')];
  const every = m.faceCages(root, device, compByRef);
  const offered = m.faceCages(root, device, compByRef, {offered: true});
  const at = m.cageAt(root, 'studs/stud-b', device, compByRef);
  console.log(JSON.stringify({
    every: ids(every), offered: ids(offered),
    // the entry kept is the drawing's: it names the part it is a seat of
    carriers: every.filter(e => e.id.startsWith('studs/')).map(e => e.carrier),
    modulePaths: every.filter(e => e.id.startsWith('studs/')).map(e => e.modulePath),
    keptDevice: every.find(e => e.id === 'port-1') === port,
    at: at && {id: at.id, carrier: at.carrier},
    // what was handed in is not changed
    deviceAfter: ids(device),
  }));
}

if (mode === 'alone') {
  // the index lists a third seat the drawing does not draw: it stays, as the device's
  const wide = [port, listed('studs/stud-a'), listed('studs/stud-b'), listed('studs/stud-c')];
  const half = m.faceCages(face('stud-a', 'stud-b'), wide, compByRef);
  // an older index lists no seat of the placed part: the drawing still yields both
  const bare = m.faceCages(face('stud-a', 'stud-b'), [port], compByRef);
  // no face, no drawing: the device's own list, untouched
  const none = m.faceCages(null, wide, compByRef);
  console.log(JSON.stringify({
    half: ids(half), halfCarriers: half.map(e => e.carrier ?? null),
    bare: ids(bare), none: ids(none)}));
}
