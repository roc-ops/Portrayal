// The cable-lay rack of the site's demo (portrayal-site tests/rack/fixtures/
// cable-lay-rack.json, copied to spec/tests/fixtures/cable-lay/ with its source
// named), with the routing context the site gives it: where each end's port is,
// how far its plug stands out, the lacer's five rings and the cable types'
// diameter and bend radius. Not a test file.
import {readFileSync} from 'node:fs';
import * as F from './cable-solids-fixture.mjs';

const read = name => JSON.parse(readFileSync(new URL(`../fixtures/cable-lay/${name}`, import.meta.url), 'utf8'));
export const RACK = read('cable-lay-rack.json');
const ENDS = read('cable-lay-ports.json').ends;

// rack.json's entries for the three parts (the lacer's is the catalogue's, with its derived plates)
export const SIZES = {
  'as7326-56x': {manufacturer: 'Edgecore', model: 'AS7326-56X', ru: 1, w: 438.4, h: 43.5, d: 536},
  'fhd-1ufce': {manufacturer: 'FS.com', model: 'FHD-1UFCE', ru: 1, w: 448, h: 44, d: 432.8},
  'fhd-cmp5dr': F.CAT['fhd-cmp5dr'],
};
export const chassisOf = ref => SIZES[ref] ?? null;

// cable-types.yaml, OM4: 3.0 mm across, a minimum installed bend radius of 25 mm
export const TYPES = {om4: {od_mm: 3, bend_mm: 25}};
export const diameterOf = c => TYPES[c?.media]?.od_mm ?? null;
export const bendOf = c => TYPES[c?.media]?.bend_mm ?? null;

const end = e => ENDS[`${e.item}|${e.path}`] ?? null;
export const ctx = Object.freeze({
  chassisOf,
  guidesOf: id => (id === 'i4' ? F.RINGS : []),
  portX: e => end(e)?.x ?? null,
  portY: e => end(e)?.y ?? null,
  plugReachOf: e => end(e)?.reach ?? null,
  diameterOf, bendOf,
});
