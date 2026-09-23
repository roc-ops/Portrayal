// The explorer's slots on a FRONT face, in 2D (B3 Task 10a), run against
// REAL compiled faces. test_nested_slots_js.py renders tmp copies of the
// fs/fhd-1ufce and the smartoptics/dcp-r-34d-cs with extra configurations,
// builds components.json and the component skins in tmp too, and hands this
// script the faces (fake-dom form), the index and the skins. What the kit
// does to a face here is compared, in Python, with what render.py drew for
// the configuration that asks for the same thing.
//
// Modes, by argv[2]:
//   scenarios - stdin JSON {components, faces, skins, cages, bays, configs};
//               one JSON object out, a key per scenario. A scenario that
//               throws records {error} under its key and the rest still run,
//               so each Python test fails for its own reason.
// SWAP_MODULE names the swap.js to load; by default the kit's own.
import {pathToFileURL} from 'node:url';
import {build, install} from './fake-dom.mjs';

const m = await import(process.env.SWAP_MODULE
  ? pathToFileURL(process.env.SWAP_MODULE).href : '../../../kit/swap.js');
install();

let raw = '';
for await (const chunk of process.stdin) raw += chunk;
const input = JSON.parse(raw);
const COMPS = new Map(input.components.map(c => [`${c.ns}/${c.name}@${c.major.slice(1)}`, c]));
const compByRef = ref => COMPS.get(String(ref).split(':')[0]) || null;
const loadSkin = async ref => {
  const comp = compByRef(ref);
  const text = input.skins[String(ref).split(':')[0]];
  return comp && text ? {comp, text} : null;
};
const face = name => build(input.faces[name]);
const attrsOf = n => Object.fromEntries(n.attributes.map(x => [x.name, x.value]));
const byPath = (root, p) => root.querySelector(`[data-path="${p}"]`);
// what the build seated for a slot: `data-for` it, at `<slot>-occupant` - the
// test's own reading, not the kit's (a plug carries no data-behaviour)
const occupantsAt = (root, key) => root.querySelectorAll(`[data-for="${key}"]`)
  .filter(n => (n.getAttribute('data-path') || '').endsWith('-occupant'));
const empty = n => n.tagName === 'style' && !n.children.length;
function seated(root, key) {
  const occ = occupantsAt(root, key);
  const [g] = occ;
  return {
    count: occ.length,
    parent: g?.parentNode?.getAttribute('data-path') ?? null,
    transform: g?.getAttribute('transform') ?? null,
    attrs: g ? attrsOf(g) : null,
    children: g ? [...g.descendants()].filter(n => !empty(n)).map(n => ({t: n.tagName, a: attrsOf(n)})) : null,
    reason: null,
  };
}
// Task 9's entry shape, built by the test itself for a carrier at any path -
// only as the reference nestedSlots is compared with, and as the stand-in
// when the kit has no nestedSlots at all (so the stacking and re-keying
// scenarios record a real RED rather than a missing function)
function helperSlots(root, deviceCages = []) {
  const out = [];
  for (const mod of root.querySelectorAll('[data-ref]')) {
    const carrierPath = mod.getAttribute('data-path');
    if (!carrierPath) continue;
    let inside = false;
    for (let n = mod; n && typeof n.getAttribute === 'function'; n = n.parentNode)
      if (n.getAttribute('data-for') != null
          && !['mounts', 'fills'].includes(n.getAttribute('data-behaviour'))) { inside = true; break; }
    if (inside) continue;
    const ref = (mod.getAttribute('data-ref') || '').split(':')[0];
    let depth = 0;
    for (let n = mod; n && typeof n.getAttribute === 'function'; n = n.parentNode)
      depth += +(n.getAttribute('data-z-lift') || 0) || 0;
    const mirrored = /scale\(\s*-/.test(mod.getAttribute('transform') || '');
    for (const c of compByRef(ref)?.cages || []) {
      const id = `${carrierPath}/${c.id}`;
      if (!byPath(root, id)) continue;
      out.push({...c, id, key: id.replace(/\/module(?=\/|$)/g, ''), cage: c.id,
                lift: (+c.lift || 0) + depth, 'seat-depth': depth,
                mirror: !!c.mirror || mirrored, module: mod, modulePath: carrierPath,
                moduleId: mod.getAttribute('id') || '', carrier: ref});
    }
  }
  // a slot on a part that is itself a slot is one of its bores, or it is the
  // wrapper's own publication of the aperture its host already presents
  const all = [...deviceCages, ...out];
  return out.filter(e => {
    const host = all.find(h => h.id === e.modulePath);
    return !host || (host.bores || []).includes(e.cage);
  });
}
const allSlots = (root, deviceCages = []) => m.nestedSlots
  ? [...deviceCages, ...m.nestedSlots(root, compByRef, {deviceCages, all: true})]
  : [...deviceCages, ...helperSlots(root, deviceCages)];
const offered = (root, deviceCages = []) => m.nestedSlots
  ? m.faceCages(root, deviceCages, compByRef, {offered: true}).map(c => c.id)
  : null;
const plain = e => e && {id: e.id, key: e.key, kind: e.kind, accepts: e.accepts, default: e.default,
                         bores: e.bores, lift: e.lift, 'seat-depth': e['seat-depth'], rotate: e.rotate,
                         mate: e.mate, mirror: e.mirror, modulePath: e.modulePath,
                         moduleId: e.moduleId, carrier: e.carrier};
async function swap(root, deviceCages, key, ref) {
  const entry = allSlots(root, deviceCages).find(c => c.id === key);
  if (!entry) return {error: `no slot ${key}`};
  return m.applyOccupantOverrides(root, [entry], {[key]: ref}, loadSkin);
}

const PLUG = 'generic/lc-duplex-plug@2', SIMPLEX = 'generic/lc-plug@2';
const DCAP = 'common/lc-duplex-dust-cap@2', CAP = 'common/lc-dust-cap@1';
const CASS12 = 'fs/fhd-2mtp12-lc-os2-a@3', CASS6 = 'fs/fhd-1mtp6lcd-os2-a@3';
const out = {};
async function scenario(name, fn) {
  try { out[name] = await fn(); } catch (e) { out[name] = {error: String(e && e.stack || e)}; }
}
const fhdCages = input.cages['fhd-1ufce'] || [];
const dcpCages = input.cages['dcp-r-34d-cs'] || [];

// ------------------------------------------------------------ the census
await scenario('census', async () => {
  const root = face('fhd:populated');
  const slots = m.nestedSlots(root, compByRef, {deviceCages: fhdCages, all: true});
  const free = m.nestedSlots(root, compByRef, {deviceCages: fhdCages});
  const helper = helperSlots(root, fhdCages);
  const dcp = face('dcp:default');
  return {
    all: slots.map(s => s.id), offered: free.map(s => s.id),
    lc1: plain(slots.find(s => s.id === 'bay-1/module/lc1')),
    tx: plain(slots.find(s => s.id === 'bay-1/module/lc1/tx')),
    helperSame: JSON.stringify(helper.map(plain)) === JSON.stringify(slots.map(plain)),
    alias: JSON.stringify(m.nestedCages(root, compByRef).map(plain))
         === JSON.stringify(free.map(plain)),
    dcpAll: m.nestedSlots(dcp, compByRef, {deviceCages: dcpCages, all: true}).map(s => s.id),
    dcpOffered: m.faceCages(dcp, dcpCages, compByRef, {offered: true}).map(s => s.id),
    dcpHelperSame: JSON.stringify(helperSlots(dcp, dcpCages).map(plain))
      === JSON.stringify(m.nestedSlots(dcp, compByRef, {deviceCages: dcpCages, all: true}).map(plain)),
  };
});

// ------------------------------------------------ swap, again, and back
await scenario('fhdPlug', async () => {
  const root = face('fhd:populated');
  const key = 'bay-1/module/lc1';
  const first = await swap(root, fhdCages, key, PLUG);
  const plug = seated(root, key);
  const offeredWithPlug = offered(root, fhdCages);
  // P3, made to bite: an index in which the duplex plug publishes a boot
  // slot on each half (the real one publishes none) - still no slot is read
  // inside the seated plug
  const boots = {...compByRef(PLUG), cages: ['a', 'b'].map(id => ({
    id, kind: 'connector', accepts: ['common/lc-boot@1'], default: null, bores: [],
    mate: [0, 0], lift: 0, rotate: null, mirror: false, 'group-states': false}))};
  const withBoots = ref => String(ref).split(':')[0] === PLUG ? boots : compByRef(ref);
  const insidePlug = m.nestedSlots(root, withBoots, {deviceCages: fhdCages, all: true})
    .map(e => e.id).filter(id => id.includes('-occupant'));
  const plugParts = root.querySelectorAll('[data-ref]')
    .filter(n => (n.getAttribute('data-path') || '').startsWith(`${key}-occupant/`)).length;
  const toCap = await swap(root, fhdCages, key, DCAP);
  const afterCap = occupantsAt(root, key).map(n => n.getAttribute('data-ref'));
  await swap(root, fhdCages, key, PLUG);
  await swap(root, fhdCages, key, PLUG);
  const afterTwoPlugs = occupantsAt(root, key).map(n => n.getAttribute('data-ref'));
  const occRef = m.occupantRef(root, allSlots(root, fhdCages).find(c => c.id === key));
  const emptied = await swap(root, fhdCages, key, null);
  return {first, plug, toCap, afterCap, afterTwoPlugs, emptied, left: occupantsAt(root, key).length,
          offeredWithPlug, occRef, insidePlug, plugParts};
});

// what a click on a seated plug names, and the select it offers
await scenario('clickPlug', async () => {
  const root = face('fhd:populated');
  const key = 'bay-1/module/lc1';
  await swap(root, fhdCages, key, PLUG);
  const hit = m.cageAt(root, `${key}-occupant/a`, fhdCages, compByRef);
  const bore = m.cageAt(root, `${key}/tx`, fhdCages, compByRef);
  return {plugPart: hit?.id ?? null, bore: bore?.id ?? null,
          options: hit && m.slotOptions ? m.slotOptions(hit, PLUG) : null};
});

// ------------------------------------------- empty, then a simplex plug
await scenario('fhdSimplex', async () => {
  const root = face('fhd:populated');
  const before = offered(root, fhdCages).filter(id => id.startsWith('bay-1/module/lc1'));
  await swap(root, fhdCages, 'bay-1/module/lc1', null);
  const emptied = offered(root, fhdCages).filter(id => id.startsWith('bay-1/module/lc1'));
  const res = await swap(root, fhdCages, 'bay-1/module/lc1/tx', SIMPLEX);
  const after = offered(root, fhdCages).filter(id => id.startsWith('bay-1/module/lc1'));
  const again = await swap(root, fhdCages, 'bay-1/module/lc1/tx', SIMPLEX);
  return {before, emptied, after, res, again, tx: seated(root, 'bay-1/module/lc1/tx'),
          lc1: occupantsAt(root, 'bay-1/module/lc1').length};
});

// ------------------------------------------- the DCP-R: a lifted bore
await scenario('dcpBore', async () => {
  const root = face('dcp:default');
  const before = offered(root, dcpCages).filter(id => id.startsWith('xc01'));
  const res = await swap(root, dcpCages, 'xc01/tx', SIMPLEX);
  const tx = seated(root, 'xc01/tx');
  const again = await swap(root, dcpCages, 'xc01/tx', CAP);
  const back = occupantsAt(root, 'xc01/tx').map(n => n.getAttribute('data-ref'));
  await swap(root, dcpCages, 'xc01/tx', SIMPLEX);
  return {before, res, tx, again, back, final: occupantsAt(root, 'xc01/tx').length};
});

await scenario('dcpDuplex', async () => {
  const root = face('dcp:default');
  await swap(root, dcpCages, 'xc01/tx', null);
  const oneEmpty = offered(root, dcpCages).filter(id => id.startsWith('xc01'));
  await swap(root, dcpCages, 'xc01/rx', null);
  const bothEmpty = offered(root, dcpCages).filter(id => id.startsWith('xc01'));
  const res = await swap(root, dcpCages, 'xc01', PLUG);
  const after = offered(root, dcpCages).filter(id => id.startsWith('xc01'));
  return {oneEmpty, bothEmpty, res, after, xc01: seated(root, 'xc01'),
          click: m.cageAt(root, 'xc01-occupant/b', dcpCages, compByRef)?.id ?? null};
});

// -------------------------------- a module swapped in, and its keys
await scenario('rekey', async () => {
  const root = face('fhd:populated');
  const bay = input.bays['fhd-1ufce'].find(b => b.id === 'bay-2');
  await m.applyOverrides(root, [bay], {'bay-2': CASS12}, loadSkin);
  const mod = byPath(root, 'bay-2/module');
  const rows = [mod, ...mod.descendants()].filter(n => n.getAttribute('data-path') || n.getAttribute('data-for'))
    .map(n => [n.getAttribute('data-path'), n.getAttribute('data-for'), n.getAttribute('id')]);
  const caps = {};
  for (let i = 1; i <= 12; i++) {
    const key = `bay-2/module/lc${String(i).padStart(2, '0')}`;
    caps[key] = seated(root, key);
  }
  const slots = m.nestedSlots ? m.nestedSlots(root, compByRef, {deviceCages: fhdCages}) : helperSlots(root);
  const under = slots.filter(s => s.id.startsWith('bay-2/module/'));
  // and a swap on the swapped module takes its shipped cap out
  const res = await swap(root, fhdCages, 'bay-2/module/lc01', PLUG);
  return {rows, caps, offered: under.map(s => s.id), keys: under.map(s => s.key),
          res, lc01: occupantsAt(root, 'bay-2/module/lc01').map(n => n.getAttribute('data-ref')),
          // by the occupant's PATH, which rename always rewrote: the shipped
          // cap is still there if the swap could not find it by its key
          lc01Paths: root.querySelectorAll('[data-path="bay-2/module/lc01-occupant"]')
            .map(n => n.getAttribute('data-ref')),
          plug: seated(root, 'bay-2/module/lc01')};
});

// ---------------------------------------------- the shuttered cassette
await scenario('shuttered', async () => {
  const root = face('fhd:shut');
  const slots = m.nestedSlots(root, compByRef, {deviceCages: fhdCages});
  const mine = slots.filter(s => s.id.startsWith('bay-3/module/'));
  const lc01 = mine.find(s => s.id === 'bay-3/module/lc01');
  const filled = mine.filter(s => m.occupantsOf(root, s).length).map(s => s.id);
  const res = await swap(root, fhdCages, 'bay-3/module/lc01/tx', SIMPLEX);
  return {n: mine.length, ids: mine.map(s => s.id).slice(0, 3), filled,
          defaults: [...new Set(mine.map(s => s.default ?? null))],
          options: m.slotOptions(lc01, ''), boreOptions: m.slotOptions(mine.find(s => s.id === 'bay-3/module/lc01/tx'), ''),
          res, tx: seated(root, 'bay-3/module/lc01/tx'),
          after: m.faceCages(root, fhdCages, compByRef, {offered: true}).map(s => s.id)
            .filter(id => id.startsWith('bay-3/module/lc01'))};
});

// what the select offers, with the shipped default marked
await scenario('options', async () => {
  const root = face('fhd:populated');
  const lc1 = m.nestedSlots(root, compByRef, {deviceCages: fhdCages}).find(s => s.id === 'bay-1/module/lc1');
  return {capped: m.slotOptions(lc1, DCAP), plugged: m.slotOptions(lc1, PLUG), none: m.slotOptions(lc1, '')};
});

// ---------------------- the drawing and the index agree on every slot
await scenario('resolver', async () => {
  const faces = [['fhd:populated', fhdCages, 'fhd-1ufce', 'populated'],
                 ['fhd:shut', fhdCages, 'fhd-1ufce', 'shut'],
                 ['dcp:default', dcpCages, 'dcp-r-34d-cs', 'default']];
  const res = {};
  for (const [name, cages, dev, cfgName] of faces) {
    const root = face(name);
    const cfg = input.configs[dev].find(c => c.name === cfgName);
    const cb = m.builtBays(cfg);
    const R = m.slotResolver({bays: input.bays[dev], cages, compByRef,
                              bayRef: (p, bay) => Object.prototype.hasOwnProperty.call(cb, p) ? cb[p] : bay.default ?? null,
                              placementRef: p => (byPath(root, p)?.getAttribute('data-ref') || '').split(':')[0] || null});
    const slots = m.nestedSlots(root, compByRef, {deviceCages: cages, all: true});
    const diff = [];
    for (const s of slots) {
      const r = R.entryAt(s.id);
      const pick = e => e && JSON.stringify([e.accepts, e.default ?? null, e.bores, e.kind, e.mate, e.rotate]);
      if (!r || pick(r) !== pick(s) || r.key !== s.key) diff.push(s.id);
    }
    res[name] = {n: slots.length, diff};
  }
  return res;
});

// ------------------------------------------- the reload's gate
await scenario('accept', async () => {
  const fhdCfg = input.configs['fhd-1ufce'].find(c => c.name === 'populated');
  const cb = m.builtBays(fhdCfg);
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const fhd = {bays: input.bays['fhd-1ufce'], cages: fhdCages, compByRef,
               built: p => own(cb, p) ? cb[p] || null : undefined};
  const map = {
    'bay-1': CASS12,
    'bay-1/module/lc01': PLUG,            // on the NEW cassette in bay-1
    'bay-1/module/lc1': PLUG,             // the OLD cassette's slot: gone
    'bay-2/module/lc1/tx': SIMPLEX,       // its adapter still holds its cap
    'bay-3/module/lc1': '',               // emptied ...
    'bay-3/module/lc1/tx': SIMPLEX,       // ... so its bore is free
    'bay-4/module/lc1-occupant/a': 'common/lc-boot@1',   // P3: inside an occupant
    'bay-4/module/lc1/tx': 'common/lc-dust-cap@1',        // blocked by the shipped duplex cap
    'bay-4/module/lc2': 'generic/sfp-lc@1',               // not something the slot accepts
  };
  const a = m.acceptSwaps(map, fhd);
  const b = m.acceptSwaps(Object.fromEntries(Object.entries(map).reverse()), fhd);
  const dcpCfg = input.configs['dcp-r-34d-cs'].find(c => c.name === 'default');
  const root = face('dcp:default');
  const dcp = {bays: input.bays['dcp-r-34d-cs'], cages: dcpCages, compByRef, built: () => undefined,
               placementRef: p => (byPath(root, p)?.getAttribute('data-ref') || '').split(':')[0] || null};
  const noRef = {...dcp, placementRef: undefined};
  return {
    fhd: a, fhdOrderFree: JSON.stringify(a) === JSON.stringify(b),
    dcpBore: m.acceptSwaps({'xc01/tx': SIMPLEX}, dcp),
    dcpBoreNoRef: m.acceptSwaps({'xc01/tx': SIMPLEX}, noRef),
    dcpDuplexCapped: m.acceptSwaps({'xc01': PLUG}, dcp),
    dcpDuplexFree: m.acceptSwaps({'xc01': PLUG, 'xc01/tx': '', 'xc01/rx': ''}, dcp),
    dcpCfg: dcpCfg.name,
  };
});

// ------------------------------- the delta: swap=, and the 3D map
await scenario('delta', async () => {
  const fhdCfg = input.configs['fhd-1ufce'].find(c => c.name === 'populated');
  const base = {cfg: fhdCfg, bays: input.bays['fhd-1ufce'], cages: fhdCages, compByRef,
                cfgBays: m.builtBays(fhdCfg)};
  const d = (occ, bays = {}) => m.swapOverrides({...base, cfgBays: {...base.cfgBays, ...bays},
                                                  cfgOccupants: occ});
  const root = face('dcp:default');
  const dcpCfg = input.configs['dcp-r-34d-cs'].find(c => c.name === 'default');
  const dcp = occ => m.swapOverrides({cfg: dcpCfg, bays: input.bays['dcp-r-34d-cs'], cages: dcpCages,
                                      compByRef, cfgBays: {}, cfgOccupants: occ,
                                      placementRef: p => (byPath(root, p)?.getAttribute('data-ref') || '').split(':')[0] || null});
  const emptied = d({'bay-1/module/lc1': null});
  return {
    untouched: d({}),
    emptied, emptiedSwap: m.encodeSwaps(emptied),
    emptiedBack: m.decodeSwaps(m.encodeSwaps(emptied)),
    capBack: d({'bay-1/module/lc1': DCAP}),
    plugged: d({'bay-1/module/lc1': PLUG}),
    simplex: d({'bay-1/module/lc1': null, 'bay-1/module/lc1/tx': SIMPLEX}),
    // on a cassette the state swapped, what a fresh seat ships is no swap
    fresh: d({'bay-1/module/lc01': DCAP}, {'bay-1': CASS12}),
    freshEmptied: d({'bay-1/module/lc01': null}, {'bay-1': CASS12}),
    dcpEmptied: dcp({'xc01/tx': null}),
    dcpCap: dcp({'xc01/tx': CAP}),
    dcpDuplex: dcp({'xc01/tx': null, 'xc01/rx': null, 'xc01': PLUG}),
  };
});

// ------------------------------------------------------- pruning
await scenario('prune', async () => {
  const slice = {cfgBays: {'bay-1': CASS6, 'bay-2': CASS6},
                 cfgOccupants: {'bay-1/module/lc1': PLUG, 'bay-1/module/lc2/tx': SIMPLEX,
                                'bay-1/module/lc2': null, 'bay-2/module/lc1': null},
                 touched: new Set(['bay-1/module/lc1', 'bay-1/module/lc2/tx', 'bay-1/module/lc2',
                                   'bay-2/module/lc1']),
                 refused: {}, failed: {}};
  const p = m.pruneCarrier(slice, 'bay-1');
  const fhdCfg = input.configs['fhd-1ufce'].find(c => c.name === 'populated');
  const state = {...p, cfgBays: {...p.cfgBays, 'bay-1': CASS12}};
  const delta = m.swapOverrides({cfg: fhdCfg, bays: input.bays['fhd-1ufce'], cages: fhdCages, compByRef,
                                 cfgBays: state.cfgBays, cfgOccupants: state.cfgOccupants});
  // the BUILD's own cassette put back, on a configuration that keyed its
  // slots: a fresh seat holds what the cassette ships, so that is recorded
  const keyed = {bays: {'bay-1': CASS6}, occupants: {'bay-1/lc1': PLUG, 'bay-1/lc2': ''}};
  const built = m.builtOccupants(keyed, fhdCages, {bays: input.bays['fhd-1ufce'], compByRef});
  const R = m.slotResolver({bays: input.bays['fhd-1ufce'], cages: fhdCages, compByRef,
                            bayRef: p => p === 'bay-1' ? CASS6 : null});
  const back = m.pruneCarrier({cfgBays: {}, cfgOccupants: {}, touched: new Set(), refused: {}, failed: {}},
                              'bay-1', built, {}, k => R.entryAt(k)?.default ?? null);
  return {cfgOccupants: p.cfgOccupants, touched: [...p.touched].sort(), delta,
          swap: m.encodeSwaps(delta), built, back: back.cfgOccupants};
});

// the faces not on screen forget what they held under a carrier that left
await scenario('queue', async () => {
  const calls = [];
  const q = m.faceQueue({loadSkin: async () => null,
                         seat: async (f, view, map) => { calls.push(Object.keys(map)); return {applied: Object.keys(map).length}; }});
  const faces = [['front', {}]];
  const opts = {held: () => faces, live: () => true};
  await q.swap({'bay-1/module/lc01': PLUG}, opts);
  await q.swap({'bay-1': CASS6}, opts);
  await q.swap({'bay-1': CASS12}, opts);
  await q.swap({'bay-1/module/lc01': PLUG}, opts);
  return {calls};
});

// ----------------------------------- which views the 3D pass rewrites
await scenario('views', async () => {
  const dev = {bays: {front: []}, cages: {front: dcpCages, rear: []}};
  return {bore: m.viewsToRewrite(dev, {'xc01/tx': SIMPLEX}),
          fhd: m.viewsToRewrite({bays: {front: input.bays['fhd-1ufce'], rear: []}, cages: {}},
                                {'bay-1/module/lc1/tx': SIMPLEX})};
});

// ------------------------- a configuration's deep keys, at the drawing's path
await scenario('builtKeys', async () => {
  const cfg = {bays: {'bay-1': CASS6}, occupants: {'bay-1/lc1/tx': SIMPLEX, 'bay-1/lc1': '',
                                                   'bay-2/lc3': PLUG}};
  const dcp = {occupants: {'xc01/tx': '', 'xc01/rx': '', 'xc01': PLUG, 'port-1510/tx': SIMPLEX}};
  return {
    fhd: m.builtOccupants(cfg, fhdCages, {bays: input.bays['fhd-1ufce'], compByRef}),
    dcp: m.builtOccupants(dcp, dcpCages, {bays: input.bays['dcp-r-34d-cs'], compByRef}),
  };
});

// ------------- the faces not on screen, and 3D: seatFace with slot keys
// The per-face pass (seatFace -> applyFaceOverrides) that the merged tree's
// detached faces and the 3D scene run, handed a MIXED map in one go: a
// cassette swap and a slot on the cassette it seats, and one level of an
// adapter emptied while the other is filled.
await scenario('seatFace', async () => {
  const fhdRoot = face('fhd:populated');
  const fhdBays = input.bays['fhd-1ufce'];
  const map = {'bay-2': CASS12, 'bay-2/module/lc01': PLUG,
               'bay-1/module/lc1': '', 'bay-1/module/lc1/tx': SIMPLEX};
  const fr = await m.seatFace(fhdRoot, {bays: fhdBays, cages: fhdCages}, map, loadSkin, compByRef);
  const byPathCount = (root, p) => root.querySelectorAll(`[data-path="${p}"]`).length;
  const stale = r => r.querySelectorAll('[data-for]')
    .filter(n => /^fhd-/.test(n.getAttribute('data-for') || '')).length;
  const tx = await (async () => {
    const root = face('dcp:default');
    const res = await m.seatFace(root, {bays: [], cages: dcpCages}, {'xc01/tx': SIMPLEX}, loadSkin, compByRef);
    return {res: {applied: res.applied, refused: res.refused, failed: res.failed},
            seated: seated(root, 'xc01/tx'), paths: byPathCount(root, 'xc01/tx-occupant')};
  })();
  const duplex = await (async () => {
    const root = face('dcp:default');
    const res = await m.seatFace(root, {bays: [], cages: dcpCages},
                                 {'xc01/tx': '', 'xc01/rx': '', 'xc01': PLUG}, loadSkin, compByRef);
    return {res: {applied: res.applied, refused: res.refused, failed: res.failed},
            seated: seated(root, 'xc01'), bores: byPathCount(root, 'xc01/tx-occupant')
              + byPathCount(root, 'xc01/rx-occupant')};
  })();
  return {
    fhd: {res: {applied: fr.applied, refused: fr.refused, failed: fr.failed, dropped: fr.dropped},
          lc01: seated(fhdRoot, 'bay-2/module/lc01'),
          lc01Paths: byPathCount(fhdRoot, 'bay-2/module/lc01-occupant'),
          lc1: occupantsAt(fhdRoot, 'bay-1/module/lc1').length,
          lc1Paths: byPathCount(fhdRoot, 'bay-1/module/lc1-occupant'),
          tx: seated(fhdRoot, 'bay-1/module/lc1/tx'),
          stale: stale(fhdRoot)},
    tx, duplex,
  };
});

// ------------------- what the kit says of every candidate slot, for the
// build to answer the same question about (manifest.nested_key_host)
await scenario('agree', async () => {
  const res = {};
  const faces = [['c40g:bdm-3plus1', 'c40g', 'bdm-3plus1'], ['s9510-30xc:ac', 's9510-30xc', 'ac'],
                 ['dcp:default', 'dcp-r-34d-cs', 'default'], ['fhd:populated', 'fhd-1ufce', 'populated']];
  for (const [name, dev, cfgName] of faces) {
    if (!input.faces[name]) continue;
    const root = face(name);
    const cages = input.cages[dev] || [];
    const cfg = input.configs[dev].find(c => c.name === cfgName);
    const cb = m.builtBays(cfg);
    const R = m.slotResolver({bays: input.bays[dev], cages, compByRef,
      bayRef: (p, bay) => Object.prototype.hasOwnProperty.call(cb, p) ? cb[p] : bay.default ?? null,
      placementRef: p => (root.querySelector(`[data-path="${p}"][data-ref]`)?.getAttribute('data-ref') || '')
        .split(':')[0] || null});
    const kit = new Set(m.nestedSlots(root, compByRef, {deviceCages: cages, all: true}).map(e => e.id));
    // every slot a component publishes on a group the face draws, outside any
    // occupant - the question, before either side's rule answers it
    const cand = [];
    for (const mod of root.querySelectorAll('[data-ref]')) {
      const at = mod.getAttribute('data-path');
      if (!at) continue;
      let inside = false;
      for (let n = mod; n && typeof n.getAttribute === 'function'; n = n.parentNode)
        if (n.getAttribute('data-for') != null
            && !['mounts', 'fills'].includes(n.getAttribute('data-behaviour'))) inside = true;
      if (inside) continue;
      for (const c of compByRef((mod.getAttribute('data-ref') || '').split(':')[0])?.cages || []) {
        const id = `${at}/${c.id}`;
        if (byPath(root, id)) cand.push({id, key: m.slotKey(id), kit: kit.has(id), resolver: !!R.entryAt(id)});
      }
    }
    res[name] = cand;
  }
  return res;
});

// ------------------- a cage wrapper's own aperture is not a second slot
await scenario('wrappers', async () => {
  const res = {};
  for (const [name, dev] of [['c40g:bdm-3plus1', 'c40g'], ['s9510-30xc:ac', 's9510-30xc']]) {
    if (!input.faces[name]) continue;
    const root = face(name);
    const cages = input.cages[dev] || [];
    res[name] = {
      slots: m.nestedSlots(root, compByRef, {deviceCages: cages, all: true}).map(e => e.id),
      unguarded: m.nestedSlots(root, compByRef, {all: true}).map(e => e.id),
      oldNested: helperSlots(root, cages).filter(e => e.modulePath.endsWith('/module')).map(e => e.id),
      device: cages.map(c => c.id),
      raw: root.querySelectorAll('[data-ref]').length,
    };
  }
  return res;
});

console.log(JSON.stringify(out));
