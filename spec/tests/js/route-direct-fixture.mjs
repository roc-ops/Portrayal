// The owner's second cable-lay rack (#949), kept in a file of its own so a
// probe can load the rack the test does. Not a test file.
//
// Two AS7326-56X leaves, at U42 and U40, either side of an FHD-1UFCE panel at
// U41 with an FHD-CMP5DR lacer hosted on it; sixteen OM4 cords from leaf
// ports 49 to 56 to panel bays 2 to 4. Items, cables and frame as the owner
// saved them, less their hand routes, their lengths and their bundles, so
// every route here is the automatic one.
//
// The port positions are what the Rack Builder's route context reads from
// the compiled faces (portrayal-site rack/route-context.js): the centre of
// each port box on the front view, less half the view's width, so x is in
// rack coordinates; and y down from the top of the face, which portY turns
// into height above the floor. Leaf ports from as7326-56x.ac-f2b.front, panel
// ports from fhd-1ufce.populated.front (the module seated there is the OS2
// cassette of the same family; its ports stand where the OM4's do).
import {RU} from '../../../kit/rack/rails.js';
import {CAT, RINGS} from './cable-solids-fixture.mjs';

export {RINGS};

// rack.json entries: the two boxes are their envelopes (no `solids`), the
// lacer the catalogue entry the solids test uses.
export const SIZES = {
  'as7326-56x': {ru: 1, w: 438.4, h: 43.5, d: 536.0, kind: 'switch'},
  'fhd-1ufce': {ru: 1, w: 448.0, h: 44.0, d: 432.8, kind: 'patch panel'},
  'fhd-cmp5dr': CAT['fhd-cmp5dr'],
};
export const chassisOf = ref => SIZES[ref] || null;

const leaf = (id, label, ru) => ({id, ref: 'as7326-56x', cfg: 'ac-f2b', label, ru, face: 'front', turned: false, swaps: {}, fields: {}});
export const rack = () => ({
  id: 'r1', name: 'Rack 2',
  frame: {kind: 'four-post', heightRU: 42, numbering: 'bottom-up', holes: {style: 'square', thread: null},
    railDepth: 740, usableDepth: 1000, ref: null},
  items: [
    leaf('i1', 'LEAF-A', 42),
    {id: 'i2', ref: 'fhd-1ufce', cfg: 'populated', label: 'PP-01', ru: 41, face: 'front', turned: false, swaps: {}, fields: {}},
    leaf('i3', 'LEAF-B', 40),
    {id: 'i4', ref: 'fhd-cmp5dr', cfg: 'base', label: 'CM-01', ru: 41, face: 'front', turned: false, swaps: {}, fields: {},
      on: 'i2', unit: 1},
  ],
  zeroU: [],
  cables: CABLES.map(([id, a, ap, bp]) => ({id, a: {item: a, path: ap, view: 'front'}, b: {item: 'i2', path: bp, view: 'front'},
    media: 'om4', purpose: 'uplink', label: '', route: []})),
});

// [cable, leaf, leaf port, panel port], as the owner cabled them
export const CABLES = [
  ['c1', 'i1', 'port-49', 'bay-3/module/lc5'], ['c2', 'i1', 'port-50', 'bay-3/module/lc6'],
  ['c3', 'i1', 'port-51', 'bay-4/module/lc1'], ['c4', 'i1', 'port-52', 'bay-4/module/lc2'],
  ['c5', 'i1', 'port-53', 'bay-4/module/lc3'], ['c6', 'i1', 'port-54', 'bay-4/module/lc4'],
  ['c7', 'i1', 'port-55', 'bay-4/module/lc5'], ['c8', 'i1', 'port-56', 'bay-4/module/lc6'],
  ['c9', 'i3', 'port-49', 'bay-2/module/lc3'], ['c10', 'i3', 'port-50', 'bay-2/module/lc4'],
  ['c11', 'i3', 'port-51', 'bay-2/module/lc5'], ['c12', 'i3', 'port-52', 'bay-2/module/lc6'],
  ['c13', 'i3', 'port-53', 'bay-3/module/lc1'], ['c14', 'i3', 'port-54', 'bay-3/module/lc2'],
  ['c15', 'i3', 'port-55', 'bay-3/module/lc3'], ['c16', 'i3', 'port-56', 'bay-3/module/lc4'],
];

// x (rack) and y (down from the top of the face) of each port's centre, mm
const LEAF = {
  'port-49': [88.3, 16.79], 'port-50': [88.3, 34.79], 'port-51': [107.3, 16.79], 'port-52': [107.3, 34.79],
  'port-53': [128.3, 16.79], 'port-54': [128.3, 34.79], 'port-55': [147.3, 16.79], 'port-56': [147.3, 34.79],
};
const BAYS = {2: [-87.06, -74.11, -61.16, -48.03, -35.08, -22.13],
  3: [21.91, 34.86, 47.81, 60.94, 73.89, 86.84],
  4: [130.88, 143.83, 156.78, 169.91, 182.86, 195.81]};
const PANEL = Object.fromEntries(Object.entries(BAYS).flatMap(([b, xs]) =>
  xs.map((x, i) => [`bay-${b}/module/lc${i + 1}`, [x, 22.01]])));
const FACE_H = {'as7326-56x': 43.5, 'fhd-1ufce': 44.0};

const portOf = (r, end) => {
  const it = r.items.find(i => i.id === end.item);
  const p = (it?.ref === 'as7326-56x' ? LEAF : it?.ref === 'fhd-1ufce' ? PANEL : {})[end.path];
  return p ? {it, x: p[0], y: p[1], faceH: FACE_H[it.ref]} : null;
};

// The route context, as the page builds it (route-context.js routeFacts).
export const ctxOf = r => ({chassisOf,
  guidesOf: id => (id === 'i4' ? RINGS : []),
  portX: end => portOf(r, end)?.x ?? null,
  portY: end => {
    const p = portOf(r, end);
    return p ? p.it.ru * RU - ((RU - p.faceH) / 2 + p.y) : null;
  }});
