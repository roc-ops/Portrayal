// spec/tests/js/rack-ids-in-use.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import {COMMANDS} from '../../../kit/rack/commands.js';

const SIZES = {sw: {ru: 1, h: 43.5, d: 400, model: 'SW', default: 'base'},
               mgr: {ru: 1, h: 43.5, d: 100, model: 'MGR', default: 'base'},
               other: {ru: 1, h: 43.5, d: 400, model: 'OTHER', default: 'base'}};
const ctx = {chassisOf: ref => SIZES[ref] || null};
const run = (op, rack, args) => COMMANDS[op].run(rack, args, ctx);

const item = (id, ref, ru, extra = {}) => ({id, ref, cfg: 'base', label: ref, ru, face: 'front', turned: false,
  swaps: {}, fields: {}, ...extra});
const cable = (id, a, b, route = []) => ({id, a: {item: a, path: 'p', view: 'front'}, b: {item: b, path: 'p', view: 'front'},
  media: '', purpose: '', label: '', route});
// A rack as a saved file holds it, read back by the loader.
const fileRack = (items, cables = []) => M.parseDoc({format: M.FORMAT, version: M.VERSION, id: 'doc-1',
  racks: [{id: 'r1', name: 'Rack 1', frame: M.defaultFrame(), items, zeroU: [], cables}]}).racks[0];
const routed = via => cable('c1', 'i1', 'i2', [{item: 'i3', via}]);
const placed = rack => run('place', rack, {ref: 'other', face: 'front', ru: 30}).created.id;

test('remove the highest id while a cable route names it: the next device does not take it', () => {
  const rack = fileRack([item('i1', 'sw', 1), item('i2', 'sw', 2), item('i3', 'mgr', 3)], [routed('ring-1')]);
  const gone = run('remove', rack, {id: 'i3'});
  assert.equal(gone.rack.items.some(i => i.id === 'i3'), false);
  const next = run('place', gone.rack, {ref: 'other', face: 'front', ru: 30});
  assert.notEqual(next.created.id, 'i3', 'a route through the removed device must not name the new one');
  assert.deepEqual(next.rack.cables[0].route.map(w => w.item), ['i3']);
});

test('a route waypoint on a device below the highest id is never handed out either', () => {
  const rack = fileRack([item('i1', 'sw', 1), item('i2', 'mgr', 2), item('i3', 'sw', 3)],
    [cable('c1', 'i1', 'i3', [{item: 'i2', via: 'ring-1'}])]);
  const gone = run('remove', rack, {id: 'i2'}).rack;
  assert.ok(M.itemIdsInUse(gone).some(x => x.id === 'i2'), 'the route still counts i2');
  assert.notEqual(placed(gone), 'i2');
});

test('a holder an item names is never handed out once it is gone', () => {
  const rack = fileRack([item('i1', 'sw', 1), item('i2', 'sw', 2, {heldBy: {item: 'i3'}})]);
  assert.equal(rack.items.some(i => i.id === 'i3'), false);
  assert.notEqual(placed(rack), 'i3');
});

test('a rack that names no id beyond its own items hands out one past the highest', () => {
  const rack = fileRack([item('i1', 'sw', 1), item('i2', 'sw', 2)], [cable('c1', 'i1', 'i2')]);
  assert.equal(placed(rack), 'i3');
});
