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
//   queue    - swap.js's `faceQueue`, the shell's bookkeeping for the held
//              faces: a swap made while faces load, entries a face already
//              holds, jobs asked for on faces no longer held, a failed job
const m = await import('../../../kit/swap.js');
const mode = process.argv[2];

import {Node, install} from './fake-dom.mjs';
install();

const A = 'fs/cas-a@2', B = 'fs/cas-b@1';
const COMP = {
  // A's body is an FHD cassette's, B's an FHD adapter panel's: two backs that
  // land in two places in the same hole
  [A]: {name: 'cas-a', size: {w: 108.97, h: 35.05}, faces: {rear: 'fs/cas-a-rear@1'},
        body: {footprint: {at: [4.985, 2.025], size: [99.0, 31.0]}}},
  [B]: {name: 'cas-b', size: {w: 108.97, h: 35.05}, faces: {rear: 'fs/cas-b-rear@1'},
        body: {footprint: {at: [10.485, 0.125], size: [88.0, 34.8]}}},
  'fs/cas-a-rear@1': {name: 'cas-a-rear', size: {w: 99.0, h: 31.0}},
  'fs/cas-b-rear@1': {name: 'cas-b-rear', size: {w: 88.0, h: 34.8}},
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
   'data-rear-of': b.id, 'data-rear-bay': `${[332.97, 224, 115.03, 6.06][i]},4.475,108.97,35.05`},
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
                      frontApplied: fr.applied, rearApplied: rr.applied, rearHoles: rr.rear.applied});
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
if (mode === 'queue') {
  const tick = () => new Promise(r => setTimeout(r, 0));
  // the shell's seat, counted: which face was handed which entries
  const calls = [];
  const skinAsks = [];
  const counted = async ref => { skinAsks.push(ref); return loadSkin(ref); };
  const q = m.faceQueue({loadSkin: counted, seat: async (face, view, map, skin) => {
    calls.push([view, Object.keys(map).sort()]);
    return m.seatFace(face, {bays: view === 'front' ? BAYS : [], cages: []}, map, skin, compByRef);
  }});
  const cfg = {name: 'base', bays: {}};
  // the reader's state: one cassette in two bays, so a face needs its skin
  // (and the rear its back) twice in one job
  let cfgBays = {'bay-1': A, 'bay-3': A};
  const held = {};
  let gate;                                      // the front's text is slow to arrive
  const slow = new Promise(r => { gate = r; });
  const opts = live => ({
    live, has: v => !!held[v], delta: () => delta(cfg, cfgBays),
    fetch: async v => { if (v === 'front') await slow; return v === 'front' ? front() : rear(); },
    store: (v, f) => !held[v] && !!(held[v] = f),
  });
  const heldFaces = live => ({live, held: () => Object.entries(held)});
  const loading = q.load(['front', 'rear'], opts(() => true));
  await tick();
  // a swap made while the front is still loading: bay-2 filled
  cfgBays = {...cfgBays, 'bay-2': B};
  const during = q.swap({'bay-2': B}, heldFaces(() => true));
  gate();
  out.loaded = await loading;
  out.during = await during;
  out.afterLoad = {front: inFront(held.front), rear: inRear(held.rear)};
  // the faces were seated with the delta once their text arrived, which
  // already held bay-2, so the swap queued behind them seated nothing again
  out.callsAfterLoad = calls.map(c => c.join(':'));
  // each skin asked for once per job, however many faces need it
  out.skinAsks = [...skinAsks].sort();
  calls.length = 0;
  out.same = await q.swap({'bay-1': A}, heldFaces(() => true));
  out.sameCalls = calls.length;
  out.changed = await q.swap({'bay-1': B}, heldFaces(() => true));
  out.changedCalls = calls.map(c => c.join(':'));
  out.afterChange = {front: inFront(held.front), rear: inRear(held.rear)};
  // asked for on faces no longer held: nothing is seated or stored
  calls.length = 0;
  out.staleSwap = await q.swap({'bay-3': A}, heldFaces(() => false));
  const other = {};
  out.staleLoad = await q.load(['top'], {...opts(() => false), has: v => !!other[v],
                                         store: (v, f) => !!(other[v] = f)});
  out.staleCalls = calls.length;
  out.staleStored = Object.keys(other);
  // a job that fails does not stop the one behind it
  const bad = m.faceQueue({loadSkin, seat: async () => { throw new Error('boom'); }});
  const first = bad.swap({'bay-1': A}, heldFaces(() => true)).then(() => 'ok', e => e.message);
  const second = bad.swap({}, heldFaces(() => true)).then(n => n, e => e.message);
  out.failed = [await first, await second];
  // a face the queue never seated takes every entry
  const fresh = front();
  held.front = fresh;
  calls.length = 0;
  await q.swap({'bay-1': B}, {live: () => true, held: () => [['front', fresh]]});
  out.unrecorded = calls.map(c => c.join(':'));
}
if (mode === 'positions') {
  // each module's back where ITS body stands, mirrored in the hole - and the
  // hole's `data-rear-at` rewritten to say so, or cleared when emptied
  const r = rear();
  const hole = () => r.querySelector('[data-rear-of="bay-1"]');
  const back = () => hole().querySelector(':scope > [data-projection]');
  out.positions = {};
  for (const [k, ref] of [['a', A], ['b', B]]) {
    await seat(r, 'rear', {'bay-1': ref});
    out.positions[k] = {transform: back().getAttribute('transform'),
                        at: hole().getAttribute('data-rear-at')};
  }
  await seat(r, 'rear', {'bay-1': null});
  out.positions.emptied = hole().getAttribute('data-rear-at');
}
console.log(JSON.stringify(out));
