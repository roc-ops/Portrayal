// Slots on a seated occupant (P3 as amended 2026-09-24), run against REAL
// compiled faces of the nokia/nfxs-d-ba. test_chained_slots_js.py renders a
// tmp copy with configurations that put generic/qsfp-lc@1 in each FANT-H's
// `qsfp-2` and, in one of them, a generic/lc-plug@2 in each optic's `tx` and
// `rx` - the cabled 100G uplink - and hands this script the faces (fake-dom
// form), the index and the skins. What the kit does to a face here is
// compared, in Python, with what render.py drew for the configuration that
// asks for the same thing.
//
// Modes, by argv[2]:
//   scenarios - stdin JSON {components, faces, skins, cages, bays, configs};
//               one JSON object out, a key per scenario. A scenario that
//               throws records {error} under its key and the rest still run.
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
// the test's own reading of what a slot holds: `data-for` it, at
// `<slot>-occupant` - not the kit's (a plug carries no data-behaviour)
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
const out = {};
async function scenario(name, fn) {
  try { out[name] = await fn(); } catch (e) { out[name] = {error: String(e && e.stack || e)}; }
}

const OPTIC = 'generic/qsfp-lc@1', PLUG = 'generic/lc-plug@2', CAP = 'common/lc-dust-cap@1';
const FANT = 'nokia/fant-h-bb@2';
const NTS = ['nt-a', 'nt-b'];
const cage = nt => `${nt}/module/qsfp-2`;
const bore = (nt, b) => `${nt}/module/qsfp-2-occupant/${b}`;
const KEYS = NTS.flatMap(nt => [cage(nt), bore(nt, 'tx'), bore(nt, 'rx')]);
const dev = 'nfxs-d-ba';
const cages = input.cages[dev] || [];
const allCages = Object.values(input.allCages[dev] || {}).flat();
const bays = input.bays[dev] || [];
const cfgOf = name => input.configs[dev].find(c => c.name === name);
const slotsOn = root => m.faceCages(root, cages, compByRef);
// A SECOND OPTIC WITH THE SAME BORES, for the cases where the replacement is a
// different part: the qsfp-lc contract and skin under another ref. The kit
// knows a carrier by its ref (cardOf), so this is what a different optic is to
// it - and the library has no second QSFP optic that publishes tx and rx.
const TWIN = 'generic/qsfp-lc-twin@1';
const twinBy = ref => String(ref).split(':')[0] === TWIN ? compByRef(OPTIC) : compByRef(ref);
const twinSkin = async ref => String(ref).split(':')[0] === TWIN ? loadSkin(OPTIC) : loadSkin(ref);
const plain = e => e && {id: e.id, key: e.key, kind: e.kind, accepts: e.accepts, default: e.default,
                         lift: e.lift, 'seat-depth': e['seat-depth'], rotate: e.rotate,
                         modulePath: e.modulePath, moduleId: e.moduleId, carrier: e.carrier};

// ------------------------------------------------------------ the census
await scenario('census', async () => {
  const withOptic = face('optics');
  const bare = face('duplex');
  const ids = root => slotsOn(root).map(s => s.id).filter(id => id.includes('qsfp-2'));
  return {
    optics: ids(withOptic),
    bare: ids(bare),
    tx: plain(slotsOn(withOptic).find(s => s.id === bore('nt-a', 'tx'))),
    offered: m.faceCages(withOptic, cages, compByRef, {offered: true}).map(s => s.id)
      .filter(id => id.includes('qsfp-2')),
  };
});

// ---------------------------------------------- plugs into a built optic
// the explorer's own path: one slot at a time (applyOccupantOverrides), the
// entry read off the face the way shell.js's cagesOnFace reads it
await scenario('plugs', async () => {
  const root = face('optics');
  const res = {};
  for (const nt of NTS) for (const b of ['tx', 'rx']) {
    const key = bore(nt, b);
    const entry = slotsOn(root).find(s => s.id === key);
    if (!entry) return {error: `no slot ${key}`};
    res[key] = await m.applyOccupantOverrides(root, [entry], {[key]: PLUG}, loadSkin);
  }
  const again = await m.applyOccupantOverrides(root, [slotsOn(root).find(s => s.id === bore('nt-a', 'tx'))],
                                              {[bore('nt-a', 'tx')]: PLUG}, loadSkin);
  return {res, again, seated: Object.fromEntries(NTS.flatMap(nt => ['tx', 'rx'].map(b => [bore(nt, b), seated(root, bore(nt, b))])))};
});

// ------------------------------- what a click names, and what it offers
await scenario('click', async () => {
  const root = face('ring');
  const hit = p => m.cageAt(root, p, cages, compByRef)?.id ?? null;
  const plug = m.cageAt(root, `${bore('nt-a', 'tx')}-occupant`, cages, compByRef);
  return {
    plug: plug?.id ?? null,
    bore: hit(bore('nt-a', 'tx')),
    optic: hit(`${cage('nt-a')}-occupant`),
    options: plug ? m.slotOptions(plug, m.occupantRef(root, plug)) : null,
  };
});

// ------------- the plugs alone, into the optics the build seated (3D)
await scenario('seatFacePlugs', async () => {
  const root = face('optics');
  const map = Object.fromEntries(KEYS.filter(k => k.includes('-occupant/')).map(k => [k, PLUG]));
  const r = await m.seatFace(root, {bays: input.faceBays[dev] || [], cages}, map, loadSkin, compByRef);
  return {res: {applied: r.applied, refused: r.refused, failed: r.failed, dropped: r.dropped},
          seated: Object.fromEntries(KEYS.map(k => [k, seated(root, k)]))};
});

// ---------- the whole map on a face that holds none of it (3D, detached)
await scenario('seatFace', async () => {
  const root = face('duplex');
  const map = Object.fromEntries(KEYS.map(k => [k, k.includes('-occupant/') ? PLUG : OPTIC]));
  const r = await m.seatFace(root, {bays: input.faceBays[dev] || [], cages}, map, loadSkin, compByRef);
  return {res: {applied: r.applied, refused: r.refused, failed: r.failed, dropped: r.dropped},
          seated: Object.fromEntries(KEYS.map(k => [k, seated(root, k)]))};
});

// ---- another optic and a plug for it, on a face whose BUILT optic holds
// plugs - the frontier's case. In one pass the plug's slot was the build's
// optic's, which the same map took out: its carrier gone, the plug was
// dropped, and `seen` kept it from ever being tried again
await scenario('replaceUnderPlugs', async () => {
  const root = face('ring');
  const map = {[cage('nt-a')]: TWIN, [bore('nt-a', 'tx')]: PLUG};
  const r = await m.seatFace(root, {bays: input.faceBays[dev] || [], cages}, map, twinSkin, twinBy);
  return {applied: r.applied, optic: occupantsAt(root, cage('nt-a')).map(n => n.getAttribute('data-ref')),
          tx: seated(root, bore('nt-a', 'tx')).count, rx: seated(root, bore('nt-a', 'rx')).count,
          ntb: seated(root, bore('nt-b', 'tx')).count};
});

// ------------------------------------------------ the gate on a reload
const gate = (cfgName, map) => {
  const cfg = cfgOf(cfgName);
  const bo = m.builtOccupants(cfg, allCages, {bays, compByRef});
  const cb = m.builtBays(cfg);
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  return m.acceptSwaps(map, {bays, cages: allCages, compByRef,
    built: p => own(cb, p) ? cb[p] || null : bays.find(b => b.id === p)?.default ?? undefined,
    builtOcc: p => own(bo, p) ? bo[p] : undefined});
};
await scenario('accept', async () => ({
  // the optic and its plugs, on a configuration that seats no optic
  both: gate('duplex', {[cage('nt-a')]: OPTIC, [bore('nt-a', 'tx')]: PLUG}),
  // a plug keyed first in the map: the host is still decided first
  reversed: gate('duplex', {[bore('nt-a', 'tx')]: PLUG, [cage('nt-a')]: OPTIC}),
  // a plug in an optic nobody seated names no slot
  noOptic: gate('duplex', {[bore('nt-a', 'tx')]: PLUG}),
  // on the build's optic, a plug is a slot; a thing it does not accept is not
  onBuilt: gate('optics', {[bore('nt-a', 'tx')]: PLUG, [bore('nt-a', 'rx')]: FANT}),
  // the optic emptied: its plugs name nothing
  emptied: gate('ring', {[cage('nt-a')]: null, [bore('nt-a', 'tx')]: PLUG}),
}));

// ------------------------------------------- the delta and the codec
await scenario('delta', async () => {
  const cfgOccOf = name => m.builtOccupants(cfgOf(name), allCages, {bays, compByRef});
  const delta = (name, occ) => m.swapOverrides({cfg: cfgOf(name), bays, cages: allCages,
    cfgBays: m.builtBays(cfgOf(name)), cfgOccupants: occ, compByRef});
  const ring = cfgOccOf('ring');
  // the explorer's own drop when the optic leaves (shell.js dropOnSlot)
  const slice = {cfgBays: {}, cfgOccupants: {...ring}, touched: new Set(), refused: {}, failed: {}};
  const pruned = m.pruneCarrier(slice, cage('nt-a'), {}, {}, () => null);
  pruned.cfgOccupants[cage('nt-a')] = null;
  // ... and when the build's optic goes back in: a fresh seat, no plugs
  const back = m.pruneCarrier(slice, cage('nt-a'), ring, {}, () => null);
  const map = {[cage('nt-a')]: OPTIC, [bore('nt-a', 'tx')]: PLUG};
  // plugs in ANOTHER optic the state seated: a fresh seat holds none, so both
  // are swaps even though the configuration plugged the same ports
  const twin = m.swapOverrides({cfg: cfgOf('ring'), bays, cages: allCages,
    cfgBays: m.builtBays(cfgOf('ring')), cfgOccupants: {...ring, [cage('nt-a')]: TWIN},
    compByRef: twinBy});
  return {
    built: ring,
    twin,
    untouched: delta('ring', ring),
    plugOut: delta('ring', {...ring, [bore('nt-a', 'rx')]: null}),
    opticOut: delta('ring', pruned.cfgOccupants),
    prunedKeys: Object.keys(pruned.cfgOccupants).sort(),
    putBack: delta('ring', back.cfgOccupants),
    onDuplex: delta('duplex', {...cfgOccOf('duplex'), ...map}),
    codec: m.decodeSwaps(m.encodeSwaps(map)),
    under: [m.underCarrier(bore('nt-a', 'tx'), cage('nt-a')), m.underCarrier(cage('nt-a'), cage('nt-a')),
            m.underCarrier(`${cage('nt-a')}0-occupant/tx`, cage('nt-a')),
            m.underCarrier('nt-a/module/qsfp-2', 'nt-a')],
    views: m.viewsToRewrite({bays: {front: []}, cages: {front: [{id: 'port-4'}], rear: [{id: 'psu'}]}},
                            {'port-4-occupant/tx': PLUG}),
  };
});

console.log(JSON.stringify(out));
