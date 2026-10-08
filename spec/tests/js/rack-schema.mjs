// spec/tests/js/rack-schema.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, readdirSync} from 'node:fs';
import {validate} from '../../../kit/rack/validate.js';
import * as M from '../../../kit/rack/model.js';

const SCHEMA = JSON.parse(readFileSync(new URL('../../schemas/rack.schema.json', import.meta.url)));
const errs = d => validate(SCHEMA, JSON.parse(M.serialize(d))).map(e => `${e.keyword} at /${e.path.join('/')}`);

test('a new document, and one with every kind of thing in it, validate', () => {
  assert.deepEqual(errs(M.newDoc()), []);
  const d = M.parseDoc({format: 'portrayal-rack', version: 2, racks: [{name: 'R', frame: {kind: 'four-post', heightRU: 42, holes: {style: 'tapped', thread: 'M6'}},
    dcim: {site: 'dc1', role: 'leaf', extra: 'kept'},
    items: [{id: 'i1', ref: 'a', cfg: 'x', ru: 1, face: 'front', swaps: {'p': 'q'}, fields: {f: 1}},
            {id: 'i2', ref: 'm', cfg: 'x', ru: 1, face: 'front', on: 'i1', unit: 1}],
    cables: [{id: 'c1', a: {item: 'i1', path: 'p1', view: 'front'}, b: {item: 'i9', path: 'p2'}, media: 'om4',
              length: {value: 3, unit: 'cm'}, route: [], note: 'kept'},
             {id: 'c2', a: {item: 'i1', path: 'p3'}, b: {item: 'i1', path: 'p4'}, length: {value: 'abc'}},
             {id: 'c3', a: {item: 'i1', path: 'p5'}, b: {item: 'i1', path: 'p6'}, routeEdited: true,
              length: {value: 2, unit: 'm', source: 'routed', measured: 1.62},
              route: [{item: 'i2', via: 'ring-1'}, {lane: 'left-front', ru: 4}, 'junk']}]}]});
  assert.deepEqual(errs(d), []);
});

test('a rack the browser checks cable validates once parseDoc has read it', () => {
  const end = (item, path) => ({item, path, view: 'front'});
  const d = M.parseDoc({format: 'portrayal-rack', version: 1, id: 'doc-cable-fixture', racks: [{
    id: 'r1', name: 'Cable test',
    frame: {kind: 'four-post', heightRU: 24, numbering: 'bottom-up', holes: {style: 'square', thread: null}, railDepth: 740, usableDepth: 1000, ref: null},
    items: [{id: 'i1', ref: 'asr-9006', cfg: 'base', label: 'core-1', ru: 2, face: 'front', turned: false, swaps: {'slot-2': 'cisco/a9k-16x100ge-tr@1'}, fields: {}},
            {id: 'i2', ref: 'as7726-32x', cfg: 'ac-f2b', label: 'leaf-1', ru: 14, face: 'front', turned: false, swaps: {}, fields: {}}],
    zeroU: [],
    cables: [{id: 'c1', a: end('i2', 'port-1'), b: end('i1', 'slot-2/module/p0'), media: 'os2', purpose: 'uplink', label: 'A1',
              length: {value: 2, unit: 'm', source: 'entered'}, route: []},
             {id: 'c2', a: end('i2', 'mgmt-eth'), b: end('i1', 'gone'), media: 'cat6a', purpose: 'management', label: '', route: []}]}]});
  assert.deepEqual(errs(d), []);
});

test('every fixture rack in spec/tests/fixtures/racks that parseDoc accepts validates', () => {
  const dir = new URL('../fixtures/racks/', import.meta.url);
  let files = [];
  try { files = readdirSync(dir).filter(f => f.endsWith('.json')); } catch { /* no fixtures dir */ }
  for (const f of files) {
    let doc;
    try { doc = M.parseDoc(readFileSync(new URL(f, dir), 'utf8')); } catch { continue; }
    assert.deepEqual(errs(doc), [], f);
  }
});

test('on without unit, a bad face and a bad version are refused', () => {
  const d = M.newDoc();
  d.racks[0].items = [{id: 'i1', ref: 'a', cfg: '', label: 'a', ru: 1, face: 'front', turned: false, swaps: {}, fields: {}, on: 'i2'}];
  assert.ok(errs(d).some(e => e.startsWith('dependentRequired')));
  d.racks[0].items[0] = {...d.racks[0].items[0], unit: 1, face: 'side'};
  assert.ok(errs(d).some(e => e.startsWith('enum')));
  assert.ok(errs({...M.newDoc(), version: 3}).some(e => e.startsWith('const')));
});

test('a waypoint is both halves of one shape', () => {
  const W = {$ref: '#/$defs/waypoint', $defs: SCHEMA.$defs};
  assert.deepEqual(validate(W, {item: 'i1', via: 'ring-1'}), []);
  assert.deepEqual(validate(W, {lane: 'left-front', ru: 4}), []);
  assert.deepEqual(validate(W, {item: 'i1'}).map(e => [e.keyword, e.missing]), [['dependentRequired', 'via']]);
  assert.deepEqual(validate(W, {ru: 4}).map(e => [e.keyword, e.missing]), [['dependentRequired', 'lane']]);
});
