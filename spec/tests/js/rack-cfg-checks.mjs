// spec/tests/js/rack-cfg-checks.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import {COMMANDS, CLEARED} from '../../../kit/rack/commands.js';
import {ctx, chassisOf} from './slot-fixtures.mjs';

const run = (op, rack, args, c = ctx) => COMMANDS[op].run(rack, args, c);
const LEAF = M.withItem(M.newRack(), {ref: 'leaf', cfg: 'base', ru: 10, label: 'leaf-1',
  swaps: {'port-2': 'acme/lr@1'}, fields: {'port-2-occupant': {label: 'x'}}}).rack;

test('place: a configuration the device does not list is refused when the slots are loaded', () => {
  assert.deepEqual(run('place', M.newRack(), {ref: 'leaf', cfg: 'ac', face: 'front', ru: 5}),
    {error: 'Leaf-48 has no configuration ac. It has: base, dc.'});
  assert.equal(run('place', M.newRack(), {ref: 'leaf', cfg: 'dc', face: 'front', ru: 5}).rack.items[0].cfg, 'dc');
  assert.equal(run('place', M.newRack(), {ref: 'leaf', cfg: 'ac', face: 'front', ru: 5}, {chassisOf}).rack.items[0].cfg, 'ac');
  assert.deepEqual(run('place', M.newRack(), {ref: 'leaf', cfg: 'dc', face: 'front', ru: 5}, {...ctx, slotsOf: () => null}),
    {error: 'The parts list for leaf could not be loaded.'});
  assert.equal(run('place', M.newRack(), {ref: 'leaf', face: 'front', ru: 5}, {...ctx, slotsOf: () => null}).rack.items[0].cfg, 'base');
});

test('patch {cfg}: a configuration the device does not list is refused when the slots are loaded', () => {
  assert.deepEqual(run('patch', LEAF, {id: 'i1', cfg: 'ac'}), {error: 'leaf-1 has no configuration ac. It has: base, dc.'});
});

test('patch {cfg} alone clears the swaps and fields, and says so', () => {
  const p = run('patch', LEAF, {id: 'i1', cfg: 'dc'}, {chassisOf});
  assert.deepEqual([p.rack.items[0].cfg, p.rack.items[0].swaps, p.rack.items[0].fields], ['dc', {}, {}]);
  assert.deepEqual(p.findings, [{kind: 'note', text: CLEARED}]);
  const kept = run('patch', LEAF, {id: 'i1', cfg: 'dc', swaps: {'port-1': null}}, {chassisOf});
  assert.deepEqual([kept.rack.items[0].swaps, kept.rack.items[0].fields], [{'port-1': null}, {}]);
  assert.equal(run('patch', LEAF, {id: 'i1', cfg: 'base'}, {chassisOf}).rack, LEAF);
});

test("patch {cfg}: a file's empty cfg is the default, so naming the default changes nothing", () => {
  const blank = M.withItem(M.newRack(), {ref: 'leaf', cfg: '', ru: 10, label: 'leaf-1', swaps: {'port-2': 'acme/lr@1'}}).rack;
  assert.equal(run('patch', blank, {id: 'i1', cfg: 'base'}).rack, blank);
  assert.equal(run('patch', blank, {id: 'i1', cfg: 'base'}, {chassisOf}).rack, blank);
  const moved = run('patch', blank, {id: 'i1', cfg: 'dc'});
  assert.deepEqual([moved.rack.items[0].cfg, moved.rack.items[0].swaps], ['dc', {}]);
});

test('patch {swaps} still replaces the map, but leaves out what the slots refuse', () => {
  const p = run('patch', LEAF, {id: 'i1', swaps: {'port-1': 'acme/dac@1', 'port-48': 'x', 'port-2': 'acme/psu-ac@1'}});
  assert.deepEqual(p.rack.items[0].swaps, {'port-1': 'acme/dac@1'});
  assert.deepEqual(p.findings, [{kind: 'note', text: 'Left out port-2, port-48: not a slot on leaf-1, or a part that slot does not take.'}]);
  const raw = run('patch', LEAF, {id: 'i1', swaps: {'port-48': 'x'}}, {chassisOf});
  assert.deepEqual(raw.rack.items[0].swaps, {'port-48': 'x'});
});
