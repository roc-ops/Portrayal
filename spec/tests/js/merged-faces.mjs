// The faces the explorer's merged tree lists but does not mount. In 3D the
// tree has one section per face; the mounted face is seated by the shell's
// reseat(), and the rest are parsed straight from the build - so they must be
// given the swap state too, or a bay the reader filled reads "open" on every
// face but one. The pass is swap.js's `seatFace`; the map it is handed is the
// state's delta against the build (`swapOverrides`), read as the shell reads it.
//
// The fixture is the fhd-1ufce shape: four cassette bays on the front, open in
// the `base` configuration, and a rear with no bays at all - only the holes
// that show a seated cassette's back (`data-rear-of`).
//
// Cases, chosen by argv[2]:
//   swapped  - the base build, two bays filled by the reader (the repro)
//   emptied  - a build that seated a cassette, taken out by the reader
//   again    - a face seated once, handed a later swap of the same bay
//   none     - no swaps: nothing on either face is touched
const m = await import('../../../kit/swap.js');
const mode = process.argv[2];

import {Node, install} from './fake-dom.mjs';
install();

const A = 'fs/cas-a@2', B = 'fs/cas-b@1';
const COMP = {
  [A]: {name: 'cas-a', size: {w: 108.97, h: 35.05}, faces: {rear: 'fs/cas-a-rear@1'}},
  [B]: {name: 'cas-b', size: {w: 108.97, h: 35.05}, faces: {rear: 'fs/cas-b-rear@1'}},
  'fs/cas-a-rear@1': {name: 'cas-a-rear', size: {w: 108.97, h: 35.05}},
  'fs/cas-b-rear@1': {name: 'cas-b-rear', size: {w: 108.97, h: 35.05}},
};
const compByRef = ref => COMP[ref.split(':')[0]] || null;
const skin = name => JSON.stringify({a: {}, c: [
  {a: {id: name, 'data-path': name, 'data-class': 'cassette'}, c: [
    {a: {id: `${name}--port-1`, 'data-path': `${name}/port-1`, 'data-class': 'port'}},
  ]},
]});
const loadSkin = async ref => {
  const c = compByRef(ref);
  return c ? {comp: c, text: skin(c.name)} : null;
};

const bay = (id, x) => ({id, at: [x, 4.475], size: {w: 108.97, h: 35.05}, rotate: null,
                         accepts: [A, B], default: null});
const BAYS = [bay('bay-1', 6.06), bay('bay-2', 115.03), bay('bay-3', 224), bay('bay-4', 333)];

// the front as the build draws it; `seated` names the bays it filled
const front = (seated = {}) => new Node({}, BAYS.map(b => new Node(
  {id: b.id, 'data-path': b.id, 'data-class': 'bay'},
  seated[b.id] ? [new Node({id: `${b.id}--module`, 'data-path': `${b.id}/module`,
                            'data-ref': `${seated[b.id]}:1.0.0`, 'data-behaviour': 'fills'})]
               : [])));
// the rear: no bays, one hole per front bay, holding the back the build seated
const rear = (seated = {}) => new Node({}, BAYS.map((b, i) => new Node(
  {id: `cutout--back-${i + 1}`, 'data-path': `cutout:back-${i + 1}`, 'data-class': 'cutout',
   'data-rear-of': b.id, 'data-rear-at': `${337.955 - 109 * i},6.5`},
  seated[b.id] ? [new Node({id: `${b.id}-rear`, 'data-projection': '1',
                            'data-of': `${b.id}/module`})] : [])));

// what each face says about each bay - what the merged tree reads. A build
// writes `ref:version` and a swap the bare ref; the ref is what is compared.
const inFront = root => Object.fromEntries(BAYS.map(b => [b.id,
  root.querySelector(`[data-path="${b.id}/module"]`)?.getAttribute('data-ref')?.split(':')[0]
    ?? null]));
const inRear = root => Object.fromEntries(BAYS.map(b => {
  const hole = root.querySelector(`[data-rear-of="${b.id}"]`);
  const backs = hole.querySelectorAll(':scope > [data-projection]');
  return [b.id, backs.length ? backs.map(p =>
    p.querySelector(`[data-of="${b.id}/module/port-1"]`) ? 'with-port' : 'bare') : null];
}));

// the shell's state, and the delta it hands a face (index.html's swapOverrides)
const delta = (cfg, cfgBays) => m.swapOverrides({cfg, bays: BAYS, cages: [], cfgBays,
                                                 cfgOccupants: {}, compByRef});
const seat = (root, view, overrides) =>
  m.seatFace(root, {bays: view === 'front' ? BAYS : [], cages: []}, overrides, loadSkin, compByRef);

const out = {};
if (mode === 'swapped') {
  const cfg = {name: 'base', bays: {}};
  const map = delta(cfg, {...m.builtBays(cfg), 'bay-1': A, 'bay-2': B});
  const f = front(), r = rear();
  const fr = await seat(f, 'front', map), rr = await seat(r, 'rear', map);
  Object.assign(out, {map, front: inFront(f), rear: inRear(r),
                      frontApplied: fr.applied, rearApplied: rr.applied, rearHoles: rr.rear});
}
if (mode === 'emptied') {
  const cfg = {name: 'populated', bays: {'bay-1': A, 'bay-3': B}};
  const map = delta(cfg, {...m.builtBays(cfg), 'bay-1': null});
  const f = front({'bay-1': A, 'bay-3': B}), r = rear({'bay-1': A, 'bay-3': B});
  await seat(f, 'front', map); await seat(r, 'rear', map);
  Object.assign(out, {map, front: inFront(f), rear: inRear(r)});
}
if (mode === 'again') {
  const f = front(), r = rear();
  await seat(f, 'front', {'bay-1': A}); await seat(r, 'rear', {'bay-1': A});
  // the one-key pass the shell makes when the reader swaps again later
  await seat(f, 'front', {'bay-1': B}); await seat(r, 'rear', {'bay-1': B});
  Object.assign(out, {front: inFront(f), rear: inRear(r),
                      modules: f.querySelectorAll('[data-path="bay-1/module"]').length});
}
if (mode === 'none') {
  const cfg = {name: 'populated', bays: {'bay-1': A}};
  const map = delta(cfg, m.builtBays(cfg));
  const f = front({'bay-1': A}), r = rear({'bay-1': A});
  const fr = await seat(f, 'front', map), rr = await seat(r, 'rear', map);
  Object.assign(out, {map, front: inFront(f), rear: inRear(r),
                      applied: fr.applied + rr.applied});
}
console.log(JSON.stringify(out));
