// spec/tests/js/rack-cable-repoint.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import {COMMANDS, GONE, CABLE_GONE, apply} from '../../../kit/rack/commands.js';
import {chassisOf} from './slot-fixtures.mjs';

const ctx = {chassisOf};
const run = (rack, args) => COMMANDS['cable.update'].run(rack, args, ctx);
const end = (item, path = 'port-1', view = 'front') => ({item, path, view});
let R = M.newRack();
for (const [ru, label] of [[10, 'leaf-1'], [20, 'leaf-2']]) R = M.withItem(R, {ref: 'leaf', cfg: 'base', ru, label}).rack;
const LEN = {value: 3, unit: 'm', source: 'entered'};
R = {...R, cables: [{id: 'c1', a: end('i1'), b: end('i2'), media: 'om4', purpose: 'uplink', label: 'A1', length: LEN, route: []},
                    {id: 'c2', a: end('i1', 'port-2'), b: end('i2', 'port-2'), media: '', purpose: '', label: '', route: []}]};

test('cable.update {a}: re-points the end and keeps everything else', () => {
  const u = run(R, {id: 'c1', a: end('i1', 'bay-1/module/lc3')});
  assert.deepEqual(u.rack.cables[0], {id: 'c1', a: end('i1', 'bay-1/module/lc3'), b: end('i2'), media: 'om4', purpose: 'uplink',
    label: 'A1', length: LEN, route: []});
  assert.equal(u.summary, 'Moved end A of cable A1 to leaf-1 (U10) bay-1/module/lc3.');
  assert.deepEqual(u.findings, []);
});

test('cable.update {b}: a port with another cable is refused with its sentence; its own port is not', () => {
  assert.deepEqual(run(R, {id: 'c1', b: end('i2', 'port-2')}), {error: 'leaf-2 (U20) port-2 already has a cable (c2).'});
  assert.equal(run(R, {id: 'c1', b: end('i2')}).rack, R);
  assert.deepEqual(run(R, {id: 'c1', b: end('i1')}), {error: 'A cable needs two different ports.'});
  assert.deepEqual(run(R, {id: 'c1', b: end('i9')}), {error: GONE});
  assert.deepEqual(run(R, {id: 'c9', b: end('i2', 'port-5')}), {error: CABLE_GONE});
});

test('cable.update: a hand-made route is kept and noted', () => {
  const routed = {...R, cables: R.cables.map(c => (c.id === 'c1' ? {...c, route: [{lane: 'left-front', ru: 15}], routeEdited: true} : c))};
  const u = run(routed, {id: 'c1', b: end('i2', 'port-7'), label: 'A2'});
  assert.deepEqual(u.rack.cables[0].route, [{lane: 'left-front', ru: 15}]);
  assert.equal(u.rack.cables[0].label, 'A2');
  assert.deepEqual(u.findings, [{kind: 'note', text: "c1's route was drawn for its old end."}]);
});

test('cable.update: an end named by @name from earlier in the batch', () => {
  const r = apply(R, [{op: 'place', ref: 'leaf', face: 'front', ru: 30, as: 'new'},
                      {op: 'cable.update', id: 'c1', b: {item: '@new', path: 'port-1', view: 'front'}}], ctx);
  assert.deepEqual(r.rack.cables[0].b, end('i3'));
});

test('cable.update: re-pointing an end to where it already is changes nothing, and never touches the input', () => {
  const before = JSON.stringify(R);
  assert.equal(run(R, {id: 'c1', a: end('i1')}).rack, R);
  assert.equal(run(R, {id: 'c1', a: end('i1'), b: end('i2')}).rack, R);
  assert.equal(run(R, {id: 'c1', a: end('i1'), label: 'A1'}).rack, R);
  run(R, {id: 'c1', a: end('i1', 'port-9'), label: 'Z'});
  assert.equal(JSON.stringify(R), before);
});
