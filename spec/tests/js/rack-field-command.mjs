// spec/tests/js/rack-field-command.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import {COMMANDS, GONE} from '../../../kit/rack/commands.js';
import {ctx, chassisOf} from './slot-fixtures.mjs';

const run = (rack, args, c = ctx) => COMMANDS.field.run(rack, args, c);
const PP = M.withItem(M.newRack(), {ref: 'pp', cfg: 'loaded', ru: 5, label: 'pp-1', fields: {'bay-1/module': {other: 'x'}}}).rack;

test('field: set one key, merged into the part\'s own; set it again; reset it', () => {
  const a = run(PP, {id: 'i1', path: 'bay-1/module', key: 'latch-color', value: 'green'});
  assert.deepEqual(a.rack.items[0].fields, {'bay-1/module': {other: 'x', 'latch-color': 'green'}});
  assert.equal(a.summary, 'Set latch-color on bay-1/module of pp-1 to green.');
  assert.equal(run(a.rack, {id: 'i1', path: 'bay-1/module', key: 'latch-color', value: 'green'}).rack, a.rack);
  const b = run(a.rack, {id: 'i1', path: 'bay-1/module', key: 'latch-color', value: null});
  assert.deepEqual(b.rack.items[0].fields, {'bay-1/module': {other: 'x'}});
  assert.equal(b.summary, 'Reset latch-color on bay-1/module of pp-1.');
  assert.deepEqual(run(PP, {id: 'i9', path: 'bay-1/module', key: 'latch-color', value: 'green'}), {error: GONE});
});

test('field: a part with no such key lists its keys; a value it refuses lists its choices', () => {
  assert.deepEqual(run(PP, {id: 'i1', path: 'bay-1/module', key: 'colour', value: 'green'}),
    {error: 'LC cassette has no field colour. Its fields: latch-color.'});
  assert.deepEqual(run(PP, {id: 'i1', path: 'bay-1/module', key: 'latch-color', value: 'red'}),
    {error: 'latch-color on LC cassette takes one of: blue, green, beige.'});
  assert.deepEqual(run(PP, {id: 'i1', path: 'bay-2/module', key: 'latch-color', value: 'blue'}),
    {error: 'Blank plate has no field latch-color. Its fields: none.'});
});

test('field: a slot path is answered with the part path, and an empty slot says so', () => {
  assert.deepEqual(run(PP, {id: 'i1', path: 'bay-1', key: 'latch-color', value: 'green'}),
    {error: 'bay-1 is a bay; the part in it is bay-1/module.'});
  const leaf = M.withItem(M.newRack(), {ref: 'leaf', cfg: 'base', ru: 5, label: 'leaf-1'}).rack;
  assert.deepEqual(run(leaf, {id: 'i1', path: 'port-2-occupant', key: 'label', value: 'x'}),
    {error: 'Nothing is seated at port-2-occupant on leaf-1.'});
  assert.equal(run(leaf, {id: 'i1', path: 'port-1-occupant', key: 'label', value: 'uplink 1'}).rack.items[0].fields['port-1-occupant'].label, 'uplink 1');
});

test('field: without the parts it merges and checks nothing', () => {
  const a = run(PP, {id: 'i1', path: 'bay-1/module', key: 'anything', value: 7}, {chassisOf});
  assert.deepEqual(a.rack.items[0].fields['bay-1/module'], {other: 'x', anything: '7'});
});

test('field: a change to nothing returns the very same rack', () => {
  // resetting a key the part does not hold, and setting the value it already holds
  assert.equal(run(PP, {id: 'i1', path: 'bay-1/module', key: 'latch-color', value: null}).rack, PP);
  assert.equal(run(PP, {id: 'i1', path: 'bay-1/module', key: 'other', value: 'x'}, {chassisOf}).rack, PP);
  assert.equal(run(PP, {id: 'i1', path: 'bay-2/module', key: 'anything', value: null}, {chassisOf}).rack, PP);
  // a number is stored as a string, so the same number again is no change
  const a = run(PP, {id: 'i1', path: 'bay-1/module', key: 'anything', value: 7}, {chassisOf});
  assert.equal(run(a.rack, {id: 'i1', path: 'bay-1/module', key: 'anything', value: '7'}, {chassisOf}).rack, a.rack);
});
