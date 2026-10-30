// One guard for every table that holds a row per cable media, so that the next media cannot be added to some of
// them and not the others: each media of cable-rules.js MEDIA is in each table below. A table keyed by family
// (DRAPE, the export's FAMILY) holds the family of each media.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import * as C from '../../../kit/rack/cable-rules.js';
import * as R from '../../../kit/rack/route.js';
import * as Rest from '../../../kit/rack/resting.js';
import * as G from '../../../kit/rack/cable-geometry.js';
import * as D from '../../../kit/rack/dcim-rules.js';

const NEW = ['stack', 'usb', 'console'];
const has = (table, key) => Object.hasOwn(table, key);
const keysOf = (file, name) => {
  const text = readFileSync(new URL(`../../../kit/rack/${file}`, import.meta.url), 'utf8');
  const body = new RegExp(`const ${name} = \\{([^}]*)\\}`).exec(text)?.[1];
  assert.ok(body, `${file} has no \`const ${name} = {...}\``);
  return [...body.matchAll(/(\w+):/g)].map(m => m[1]);
};

test('the three new media are in MEDIA, after the ones that were there', () => {
  assert.deepEqual(C.MEDIA.slice(-3), NEW);
});

test('every media has a row in every table of the kit that is keyed by media', () => {
  const tables = {MEDIA_LABELS: C.MEDIA_LABELS, PLUG_REACH: R.PLUG_REACH, END_ALLOWANCE_BY_MEDIA: R.END_ALLOWANCE_BY_MEDIA,
    DIAMETERS: R.DIAMETERS, PLUG_SPLIT: R.PLUG_SPLIT, 'resting FAMILY': Rest.FAMILY, 'resting BEND': Rest.BEND, COLORS: G.COLORS};
  for (const [name, table] of Object.entries(tables))
    assert.deepEqual(C.MEDIA.filter(m => !has(table, m)), [], `${name} lacks a media`);
});

test('every media\'s family has a row in every table of the kit that is keyed by family', () => {
  const families = [...new Set(C.MEDIA.map(m => C.mediaKind(m).family))];
  assert.deepEqual(families.filter(f => !has(Rest.DRAPE, f)), [], 'resting DRAPE lacks a family');
  assert.deepEqual(families.filter(f => !keysOf('export-data.js', 'FAMILY').includes(f)), [], 'the export FAMILY lacks a family');
  // resting's FAMILY is the media's family, as mediaKind says it
  for (const m of C.MEDIA) assert.equal(Rest.FAMILY[m], C.mediaKind(m).family, m);
});

test('every media is offered for the ends that are its own, and is said by name in a mismatch', () => {
  for (const m of C.MEDIA) {
    const kind = C.mediaKind(m), other = {family: kind.family === 'fiber' ? 'copper' : 'fiber', mode: null};
    // the media offered for two ends of its own kind is of that kind
    assert.deepEqual(C.mediaKind(C.proposeMedia(kind, kind)), kind, `proposeMedia for ${m}`);
    // a mismatch names the family of each end by a word, never `undefined`
    const said = C.mismatch(m, kind, other).concat(C.mismatch(m, other, kind));
    assert.ok(said.length > 0 && said.every(s => !/undefined|null/.test(s)), `${m}: ${said.join(' ')}`);
  }
});

test('the DCIM cables file has a row for each data media and a blank, with its note, for each new one', () => {
  // power has its own sentence in the file's notes and ground is never filed (docs/cable-ends-design.md section 7)
  assert.deepEqual(C.MEDIA.filter(m => !['power', 'ground'].includes(m) && !has(D.CABLE_TYPE, m)), []);
  for (const m of NEW) {
    assert.equal(D.CABLE_TYPE[m], '', `${m}: a value is written only from the DCIM's own choice list, at the pin the kit cites`);
    assert.equal(D.cableType(m), '', m);
    assert.match(D.CABLE_TYPE_NOTES[m], /the DCIM cable-type choices were not read/, m);
  }
  // the eight that were there are as they were
  assert.deepEqual(['os2', 'om3', 'om4', 'om5', 'cat6', 'cat6a', 'dac', 'aoc'].map(D.cableType),
    ['smf-os2', 'mmf-om3', 'mmf-om4', 'mmf-om5', 'cat6', 'cat6a', 'dac-passive', 'aoc']);
});
