// spec/tests/js/rack-apply.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import {apply} from '../../../kit/rack/commands.js';

const SIZES = {'as7726-32x': {ru: 1, h: 43.5, d: 515, model: 'AS7726-32X', default: 'ac-f2b'}};
const ctx = {chassisOf: ref => SIZES[ref] || null};
const P = (ru, extra = {}) => ({op: 'place', ref: 'as7726-32x', face: 'front', ru, ...extra});

test('a batch applies whole, and @names reach later commands', () => {
  const r = apply(M.newRack(), [P(10, {as: 'leaf'}), P(20, {as: 'spine'}),
    {op: 'cable.add', a: {item: '@leaf', path: 'port-1', view: 'front'}, b: {item: '@spine', path: 'port-1', view: 'front'}, as: 'up'},
    {op: 'patch', id: '@leaf', label: '@spine'}], ctx);
  assert.equal(r.rack.items.length, 2);
  assert.deepEqual(r.rack.cables[0].a.item, 'i1');
  assert.equal(r.rack.items[0].label, '@spine');          // not an id: kept as written
  assert.deepEqual(r.created, {leaf: 'i1', spine: 'i2', up: 'c1', ids: ['i1', 'i2', 'c1']});
  assert.equal(r.step, true);
  assert.equal(r.noop, false);
});

test('a failing command leaves the rack untouched and says which', () => {
  const rack = M.newRack();
  const r = apply(rack, [P(10), P(11), P(10)], ctx);
  assert.deepEqual(r, {error: 'Taken by AS7726-32X on the front.', index: 2});
});

test('names: unbound, bound twice, and the rack argument', () => {
  const rack = M.newRack();
  assert.deepEqual(apply(rack, [{op: 'move', id: '@x', ru: 2}], ctx), {error: 'Nothing earlier in this batch is called x.', index: 0});
  assert.deepEqual(apply(rack, [P(1, {as: 'a'}), P(2, {as: 'a'})], ctx), {error: 'Two commands in this batch are called a.', index: 1});
  assert.deepEqual(apply(rack, [P(1, {rack: 'r2'})], ctx), {error: 'Only rack r1 can be edited here.', index: 0});
  assert.equal(apply(rack, [P(1, {rack: 'r1'})], ctx).rack.items.length, 1);
});

test('unknown commands and bad arguments are refused in words', () => {
  const rack = M.newRack();
  assert.deepEqual(apply(rack, {op: 'plce'}, ctx), {error: "There is no command called 'plce'.", index: 0});
  assert.deepEqual(apply(rack, {op: 'place', ref: 'as7726-32x', face: 'front'}, ctx),
                   {error: 'place needs ru, a whole number from 1.', index: 0});
  assert.deepEqual(apply(rack, P(1, {face: 'side'}), ctx), {error: 'place needs face, one of front, rear.', index: 0});
  assert.deepEqual(apply(rack, P(1, {colour: 'red'}), ctx), {error: 'place does not take colour.', index: 0});
  assert.deepEqual(apply(rack, 'place', ctx), {error: 'A command is an object with an op.', index: 0});
});

test('a batch of no-ops is a no-op; a dcim-only batch is not a step', () => {
  const rack = M.newRack();
  const n = apply(rack, [{op: 'rename', name: rack.name}], ctx);
  assert.equal(n.noop, true);
  assert.equal(n.rack, rack);
  const d = apply(rack, {op: 'dcim', site: 'dc1'}, ctx);
  assert.deepEqual([d.noop, d.step], [false, false]);
});

test('the step summary names only what is a step', () => {
  const r = apply(M.newRack(), [{op: 'dcim', site: 'dc1'}, {op: 'rename', name: 'Core'}], ctx);
  assert.equal(r.summary, 'Renamed the rack to Core.');
  assert.equal(r.step, true);
});

test('cable.route arguments: a waypoint is an object, both halves of one shape', () => {
  const rack = {...M.newRack(), cables: [{id: 'c1', a: {item: 'i1', path: 'p', view: 'front'}, b: {item: 'i2', path: 'p', view: 'front'},
                                         media: '', purpose: '', label: '', route: []}]};
  const R = route => apply(rack, {op: 'cable.route', id: 'c1', route}, ctx);
  assert.deepEqual(R([null]), {error: 'cable.route needs route.0, an object.', index: 0});
  assert.deepEqual(R([{item: 'i1'}]), {error: 'cable.route needs route.0.via, some text.', index: 0});
  assert.deepEqual(R([{lane: 'left-front'}]), {error: 'cable.route needs route.0.ru, a whole number.', index: 0});
  assert.deepEqual(R([{lane: 'left-front', ru: 2, x: 1}]), {error: 'cable.route does not take route.0.x.', index: 0});
  assert.equal(R([{lane: 'left-front', ru: 2}]).rack.cables[0].route.length, 1);
});

test('frame height is at most 100U', () => {
  assert.deepEqual(apply(M.newRack(), {op: 'frame', heightRU: 101}, ctx), {error: 'frame needs heightRU, a whole number from 1 to 100.', index: 0});
  assert.equal(apply(M.newRack(), {op: 'frame', heightRU: 100}, ctx).rack.frame.heightRU, 100);
});
