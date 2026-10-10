// spec/tests/js/rack-route-check.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import {COMMANDS} from '../../../kit/rack/commands.js';
import {pathwaysOf, routedLength} from '../../../kit/rack/route.js';
import {inspect} from '../../../kit/rack/queries.js';
import {chassisOf} from './slot-fixtures.mjs';

const add = (rack, ref, ru, label) => M.withItem(rack, {ref, cfg: 'base', ru, label}).rack;
const end = (item, path = 'port-1') => ({item, path, view: 'front'});
const rackWith = () => {
  let r = add(add(add(M.newRack(), 'leaf', 20, 'leaf-1'), 'mgr', 19, 'cm-1'), 'leaf', 10, 'leaf-2');
  return {...r, cables: [{id: 'c1', a: end('i1'), b: end('i3'), media: 'om4', purpose: '', label: '', route: []}]};
};
const route = (rack, waypoints, ctx = {chassisOf}) => COMMANDS['cable.route'].run(rack, {id: 'c1', route: waypoints}, ctx);

// The same route context Task 4's cable test uses: no rings, every port 100 mm left of centre.
const ROUTE_CTX = {chassisOf, guidesOf: () => [], portX: () => -100};

test('pathwaysOf lists guides and passes across views, sorted and unique', () => {
  assert.deepEqual(pathwaysOf(chassisOf('mgr')), ['guide-1', 'guide-2', 'window-1']);
  assert.deepEqual(pathwaysOf(null), []);
});

test('cable.route accepts real pathways and gutters', () => {
  const r = rackWith();
  const s = route(r, [{item: 'i2', via: 'guide-2'}, {lane: 'left-front', ru: 15}]);
  assert.equal(s.error, undefined);
  assert.deepEqual(s.rack.cables[0].route, [{item: 'i2', via: 'guide-2'}, {lane: 'left-front', ru: 15}]);
});

test('cable.route refuses made-up names and says what exists', () => {
  const r = rackWith();
  assert.deepEqual(route(r, [{item: 'i2', via: '?'}]),
    {error: 'Waypoint 1: cm-1 has no ring, duct, pass-through or tray called ?. It has: guide-1, guide-2, window-1.'});
  assert.deepEqual(route(r, [{item: 'i9', via: 'guide-1'}]), {error: 'Waypoint 1 names i9, which is not in the rack.'});
  assert.match(route(r, [{lane: 'left-front', ru: 3}, {lane: '?', ru: 9}]).error,
    /^Waypoint 2: there is no gutter called \?\. This rack has: left-front, right-front, left-rear, right-rear\.$/);
  assert.deepEqual(route(r, [{lane: 'left-front', ru: 99}]), {error: 'Waypoint 1: ru 99 is not on this 42U rack, whose ru runs 1-42 from the bottom.'});
});

test('cable.route refuses a pathway on a device with none, and checks nothing without a catalogue', () => {
  const r = rackWith();
  const noGuides = ref => ({...chassisOf(ref), guides: undefined, passes: undefined});
  assert.deepEqual(route(r, [{item: 'i2', via: 'guide-1'}], {chassisOf: noGuides}),
    {error: 'Waypoint 1: cm-1 has no rings, ducts, pass-throughs or trays.'});
  assert.equal(route(r, [{item: 'i2', via: 'anything'}], {}).error, undefined);
});

test('a refused route changes nothing, and a repeat of the same route is the very same rack', () => {
  const r = rackWith();
  const before = structuredClone(r);
  assert.equal(route(r, [{item: 'i2', via: '?'}]).rack, undefined);
  assert.deepEqual(r, before);
  const once = route(r, [{lane: 'left-front', ru: 15}]).rack;
  assert.equal(route(once, [{lane: 'left-front', ru: 15}]).rack, once);
  assert.deepEqual(r, before);
});

test('inspect gives a cable its slack: its own length less the routed length', async () => {
  const base = rackWith();
  const withLength = length => ({...base, cables: [{...base.cables[0], length}]});
  const measured = rack => Math.round(routedLength(rack, rack.cables[0], ROUTE_CTX).measured * 100) / 100;
  const slack = async rack => (await inspect(rack, 'c1', {chassisOf, route: ROUTE_CTX})).slack;
  const m = measured(base);
  // 1.09 m from the port faces; 1.15 from each plug's reach (#960); 1.27
  // with each span out to the lane hanging by the drape of fibre (#949 step
  // 3); 1.00 (0.9962) with #962's end allowance, 13.1 mm an end for this OM4
  // cord where it was 0.15 m
  assert.equal(m, 1);
  assert.deepEqual(await slack(withLength({value: 2, unit: 'm', source: 'entered'})), {metres: 1});
  assert.deepEqual(await slack(withLength({value: 10, unit: 'ft', source: 'entered'})), {metres: Math.round((3.048 - m) * 100) / 100});
  assert.equal(await slack(withLength({value: 2, unit: 'm', source: 'routed'})), null);
  assert.equal(await slack(base), null);
  assert.equal((await inspect(withLength({value: 2, unit: 'm', source: 'entered'}), 'c1', {chassisOf})).slack, null);
});

test('cable.route judges only waypoints the cable does not already store', () => {
  const stale = [{item: 'i9', via: 'x'}, {lane: 'left-front', ru: 99}, {lane: 'left-front', ru: 5}];
  const base = rackWith();
  const r = {...base, cables: [{...base.cables[0], route: stale, routeEdited: true}]};
  const s = route(r, [{lane: 'left-front', ru: 5}, {lane: 'left-front', ru: 99}, {item: 'i9', via: 'x'}]);
  assert.equal(s.error, undefined);
  assert.equal(route(r, [{item: 'i9', via: 'x'}, {lane: 'left-front', ru: 5}]).error, undefined);
  assert.deepEqual(route(r, [...stale, {item: 'i2', via: '?'}]),
    {error: 'Waypoint 4: cm-1 has no ring, duct, pass-through or tray called ?. It has: guide-1, guide-2, window-1.'});
});

test('cable.route reads a configured face from guidesOf, and skips a configured item without it', () => {
  const r = rackWith();
  const guidesOf = () => [{via: 'extra-ring'}, {via: 'guide-1'}];
  assert.equal(route(r, [{item: 'i2', via: 'extra-ring'}], {chassisOf, guidesOf}).error, undefined);
  assert.deepEqual(route(r, [{item: 'i2', via: '?'}], {chassisOf, guidesOf}),
    {error: 'Waypoint 1: cm-1 has no ring, duct, pass-through or tray called ?. It has: extra-ring, guide-1.'});
  const odd = {...r, items: r.items.map(i => (i.id === 'i2' ? {...i, swaps: {'bay-1': 'x'}} : i))};
  assert.equal(route(odd, [{item: 'i2', via: '?'}]).error, undefined);
  const other = {...r, items: r.items.map(i => (i.id === 'i1' ? {...i, cfg: 'dc'} : i))};
  assert.equal(route(other, [{item: 'i1', via: '?'}]).error, undefined);
});

test('inspect gives no slack for a unit it cannot convert', async () => {
  const base = rackWith();
  const r = {...base, cables: [{...base.cables[0], length: {value: 30, unit: 'cm', source: 'entered'}}]};
  assert.equal((await inspect(r, 'c1', {chassisOf, route: ROUTE_CTX})).slack, null);
});
