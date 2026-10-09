// The fixture racks of spec/tests/js/rack-solids.mjs, kept in a file of their
// own so a probe can load the racks the test does. Not a test file.
import {readFileSync} from 'node:fs';
import * as M from '../../../kit/rack/model.js';

// rack.json entries: two copied from a build of the library, one from a
// synthetic enclosure; test_rack_solids.py holds all three to what
// rack_index.py derives today.
export const CAT = JSON.parse(readFileSync(new URL('./cable-solids-catalogue.json', import.meta.url))).devices;

// The owner's fixture of #949: an FHD panel with an FHD-CMP5DR lacer on it at
// U12, a switch above at U13 and a switch below at U11. The panel and the
// switches are plain box devices, so each is its envelope; the lacer is the
// catalogue's, with its derived plates.
export const SIZES = {
  sw: {ru: 1, w: 440, h: 44, d: 300},
  panel: {ru: 1, w: 448, h: 44, d: 227},
  'fhd-cmp5dr': CAT['fhd-cmp5dr'],
  'cmv-sfd45u5w': CAT['cmv-sfd45u5w'],
  'fhd-encl': CAT['fhd-encl'],
  pdu: {ru: 30, w: 56, h: 1700, d: 60, mount: 'rack-side'},
  rear: {ru: 1, w: 440, h: 44, d: 100},
};
export const chassisOf = ref => SIZES[ref] || null;
const add = (rack, ref, ru, extra = {}) => M.withItem(rack, {ref, cfg: 'base', ru, label: ref, ...extra}).rack;

// The five rings of the FHD-CMP5DR, centred 35.7, 131.1, 241.5, 351.9 and
// 447.3 mm along its 483 (its provenance), so in rack x 241.5 less.
export const RINGS = [35.7, 131.1, 241.5, 351.9, 447.3].map((c, i) => ({
  via: `guide-${i + 1}`, kind: 'ring', face: 'front', run: 'x', depth: 6.8,
  x: Math.round((c - 241.5) * 100) / 100, aperture: {w: 32, h: 29.5}}));

// i1 switch below (U11), i2 panel (U12), i3 lacer on the panel, i4 switch above (U13)
export function ownerRack() {
  let r = add(M.newRack(), 'sw', 11, {label: 'sw-dn'});
  r = add(r, 'panel', 12, {label: 'fhd-panel'});
  r = add(r, 'fhd-cmp5dr', 12, {on: 'i2', unit: 1, label: 'lacer'});
  r = add(r, 'sw', 13, {label: 'sw-up'});
  return r;
}
// ports: x by item and port path
export const PORTS = {
  i1: {p140: -140, p100: -100, p120: -120},
  i2: {bay2: -60, bay3: 30, bay4: 120, bay2b: -50},
  i4: {p150: -150, p100: -100},
};
export const ctxOf = (extra = {}) => ({chassisOf,
  guidesOf: id => (id === 'i3' ? RINGS : extra.guides?.[id] ?? []),
  portX: end => extra.ports?.[end.item]?.[end.path] ?? PORTS[end.item]?.[end.path] ?? null,
  portY: end => extra.portY?.[end.item] ?? null,
  ...(extra.ctx || {})});
const end = (item, path, view = 'front') => ({item, path, view});
export const cable = (id, a, b, media = 'om4', extra = {}) => ({id, media, a, b, route: [], ...extra});
// cables from the switch below and above to bays 2 to 4 of the panel
export const OWNER_CABLES = [
  cable('c1', end('i1', 'p140'), end('i2', 'bay4')),
  cable('c2', end('i1', 'p100'), end('i2', 'bay3')),
  cable('c3', end('i1', 'p120'), end('i2', 'bay2b')),
  cable('c4', end('i4', 'p150'), end('i2', 'bay2')),
  cable('c5', end('i4', 'p100'), end('i2', 'bay3'), 'cat6'),
];
export {end, add};
