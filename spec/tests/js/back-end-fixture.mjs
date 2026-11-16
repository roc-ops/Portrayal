// A patch panel mounted on the REAR rails whose adapters sit in holders in a
// drawer, and a switch on the front rails: the catalogue as `loadSlots` hands
// it to the rack kit (configs.json and components.json, cut to what the rules
// read), and the ports as a page reads them off the drawings. Not a test file.
//
// The shapes are the library's: a holder (class adapter-panel) seated in a bay
// of a drawer (class mechanical) that sits in the panel's own bay, each adapter
// of the holder an end on its face (`sc01`) and an end on its back (`b01`) of
// one sleeve, paired in the holder's fibre map (`optical.ends`). The back is
// drawn by no panel: a holder in a drawer is no bay of the device.
//
//   pnl  config `base`  the holder has its fibre map: b01 is twin to sc01
//   pnl  config `bare`  the holder has none: b01 has no twin
//   sw   two cages for LC optics
import {RU} from '../../../kit/rack/rails.js';
import * as M from '../../../kit/rack/model.js';

const comp = (ref, rest) => { const [ns, tail] = ref.split('/'), [name, major] = tail.split('@'); return {ns, name, major: `v${major}`, ...rest}; };
const plain = {kind: 'component', cages: [], bays: {}, parts: []};
export const ADAPTER = 'acme/sc-adapter@1', HOLDER = 'acme/holder@1', BARE = 'acme/holder-bare@1', DRAWER = 'acme/drawer@1';
const adapter = id => ({id, ref: ADAPTER});
const ends = n => Object.fromEntries(Array.from({length: n}, (_, i) => {
  const id = String(i + 1).padStart(2, '0');
  return [[`sc${id}.1`, {label: String(i + 1), to: `rear:b${id}.1`}], [`rear:b${id}.1`, {label: String(i + 1), to: `sc${id}.1`}]];
}).flat());
export const COMPONENTS = [
  comp(ADAPTER, {...plain, class: 'port', attrs: {connector: 'sc', media: 'fiber'}}),
  comp(HOLDER, {...plain, class: 'adapter-panel', kind: 'module', attrs: {media: 'fiber', model: 'HOLDER'}, faces: {rear: 'acme/holder-rear@1'},
    parts: [adapter('sc01'), adapter('sc02')], optical: {ends: ends(2)}}),
  comp('acme/holder-rear@1', {...plain, class: 'adapter-panel', attrs: {media: 'fiber'}, parts: [adapter('b01'), adapter('b02')]}),
  // the same holder with no fibre map: nothing says which front end a back end is the other end of
  comp(BARE, {...plain, class: 'adapter-panel', kind: 'module', attrs: {media: 'fiber', model: 'HOLDER-BARE'}, faces: {rear: 'acme/holder-bare-rear@1'},
    parts: [adapter('sc01')]}),
  comp('acme/holder-bare-rear@1', {...plain, class: 'adapter-panel', attrs: {media: 'fiber'}, parts: [adapter('b01')]}),
  comp(DRAWER, {...plain, class: 'mechanical', kind: 'module', attrs: {model: 'DRAWER'}, bays: {'slot-1': {accepts: [HOLDER, BARE], default: HOLDER}}}),
  comp('generic/sfp-lc@1', {...plain, class: 'transceiver', kind: 'module', attrs: {media: 'fiber', face: 'lc-duplex', mode: 'single-mode'}}),
];
const byRef = new Map(COMPONENTS.map(c => [`${c.ns}/${c.name}@${c.major.slice(1)}`, c]));
const config = (name, holder) => ({name, description: '', airflow: 'passive', bays: {'drawer/slot-1': holder}, occupants: {}});
export const SLOTS = {
  pnl: {default: 'base', 'pdu-class': null,
        bays: {front: [{id: 'drawer', group: 'drawer', accepts: [DRAWER], default: DRAWER}], rear: []}, cages: {front: [], rear: []},
        configs: [config('base', HOLDER), config('bare', BARE)]},
  sw: {default: 'base', 'pdu-class': null, bays: {front: [], rear: []},
       cages: {front: [1, 2].map(n => ({id: `port-${n}`, kind: 'cage', group: 'sfp', interface: 'sfp', media: 'sfp', accepts: ['generic/sfp-lc@1'], default: null})), rear: []},
       configs: [{name: 'base', description: '', airflow: 'front-to-back', bays: {}, occupants: {}}]},
};
// rack.json entries: the panel is 284 deep, as the library's drawer panel is
export const SIZES = {
  pnl: {ru: 1, w: 482.6, h: 44, d: 284, model: 'PNL', manufacturer: 'Acme', kind: 'patch panel', configs: ['base', 'bare'], default: 'base'},
  sw: {ru: 1, w: 438, h: 43.6, d: 400, model: 'SW', manufacturer: 'Acme', kind: 'switch', configs: ['base'], default: 'base'},
};
export const chassisOf = ref => SIZES[ref] || null;
export const ctx = {chassisOf, slotsOf: ref => SLOTS[ref] ?? null, compByRef: ref => (ref == null ? null : byRef.get(String(ref).split(':')[0]) ?? null)};

export const SLOT = 'drawer/module/slot-1/module';
export const end = (item, path, view = 'front') => ({item, path, view});
// the switch (i1) at U20 on the front rails with an optic in each cage, the panel (i2) at U30 and the one with no fibre map (i3) at U34, both on the rear rails
const withSwitch = M.withItem(M.newRack(), {ref: 'sw', cfg: 'base', ru: 20, label: 'SW-1', swaps: {'port-1': 'generic/sfp-lc@1', 'port-2': 'generic/sfp-lc@1'}}).rack;
const withPanel = M.withItem(withSwitch, {ref: 'pnl', cfg: 'base', ru: 30, face: 'rear', label: 'PNL-1'}).rack;
export const BASE = M.withItem(withPanel, {ref: 'pnl', cfg: 'bare', ru: 34, face: 'rear', label: 'PNL-2'}).rack;
export const withCables = (rack, ...cables) => ({...rack, cables: cables.map(([id, a, b, extra = {}]) => ({id, a, b, media: 'os2', purpose: '', label: '', route: [], ...extra}))});

// x from the centre line, and the height of the face the port is seen on: what the route context reads off the compiled faces
const X = {'sw|port-1': 50, 'sw|port-2': 150, [`pnl|${SLOT}/sc01`]: -250, [`pnl|${SLOT}/sc02`]: 100};
const FACE_H = {sw: 43.6, pnl: 44};
const portOf = (rack, e) => {
  const it = rack.items.find(i => i.id === e.item), x = it ? X[`${it.ref}|${e.path}`] : undefined;
  // the drawings place the faces' ends; nothing places a back end
  return x != null && e.view === 'front' ? {it, x} : null;
};
export const routeCtx = rack => ({...ctx, guidesOf: () => [],
  portX: e => portOf(rack, e)?.x ?? null,
  portY: e => { const p = portOf(rack, e); return p ? p.it.ru * RU - ((RU - FACE_H[p.it.ref]) / 2 + 10) : null; }});
