// spec/tests/js/rack-commands.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import {COMMANDS, GONE, CABLE_GONE, NOT_ADDED, CLEARED} from '../../../kit/rack/commands.js';

const SIZES = {'as7726-32x': {ru: 1, h: 43.5, d: 515, model: 'AS7726-32X', default: 'ac-f2b'},
               'r740xd': {ru: 2, h: 86.8, d: 737.5, model: 'R740xd', default: 'sff24'},
               'fhd-cmp5dr': {ru: 1, h: 44, d: 110, mount: 'rack-face', model: 'FHD-CMP5DR', default: 'base'},
               'tm-280': {ru: 1, h: 43.6, d: 140.5, model: 'TM-280', default: 'base'}};
const ctx = {chassisOf: ref => SIZES[ref] || null};
const run = (op, rack, args) => COMMANDS[op].run(rack, args, ctx);
const add = (rack, ref, ru, extra = {}) => M.withItem(rack, {ref, cfg: 'x', ru, label: extra.label ?? ref, ...extra}).rack;
const end = (item, path = 'port-1', view = 'front') => ({item, path, view});

test('place: a device goes in, named by its model, and says where', () => {
  const r = run('place', M.newRack(), {ref: 'r740xd', face: 'front', ru: 10});
  assert.equal(r.rack.items[0].label, 'R740xd');
  assert.equal(r.rack.items[0].cfg, 'sff24');
  assert.deepEqual(r.created, {id: 'i1'});
  assert.equal(r.summary, 'Placed R740xd at U10 on the front.');
});

test('place: a refusal is fits() sentence; an unknown device says so', () => {
  const r = add(M.newRack(), 'r740xd', 10, {label: 'srv'});
  assert.deepEqual(run('place', r, {ref: 'as7726-32x', face: 'front', ru: 11}), {error: 'Taken by srv on the front.'});
  assert.deepEqual(run('place', r, {ref: 'nope', face: 'front', ru: 1}), {error: 'No size is known for nope.'});
});

test('place: a cable manager on a device attaches to it', () => {
  const r = add(M.newRack(), 'r740xd', 10, {label: 'srv'});
  const m = run('place', r, {ref: 'fhd-cmp5dr', face: 'front', ru: 11});
  assert.deepEqual([m.rack.items[1].on, m.rack.items[1].unit], ['i1', 2]);
});

test('move: GONE, a refusal, a no-op, and a move', () => {
  let r = add(M.newRack(), 'as7726-32x', 10, {label: 'leaf'});
  r = add(r, 'as7726-32x', 20, {label: 'spine'});
  assert.deepEqual(run('move', r, {id: 'i9', ru: 1}), {error: GONE});
  assert.deepEqual(run('move', r, {id: 'i1', ru: 20}), {error: 'Taken by spine on the front.'});
  assert.equal(run('move', r, {id: 'i1', ru: 10}).rack, r);
  const m = run('move', r, {id: 'i1', ru: 12, face: 'rear'});
  assert.equal(m.summary, 'Moved leaf to U12 on the rear.');
});

test('patch: changes what it names; clears-changes note; same value is a no-op', () => {
  const r = add(M.newRack(), 'as7726-32x', 10, {label: 'leaf', swaps: {'port-1': 'x'}});
  assert.equal(run('patch', r, {id: 'i1', label: 'leaf'}).rack, r);
  const p = run('patch', r, {id: 'i1', cfg: 'other', swaps: {}, fields: {}});
  assert.deepEqual(p.findings, [{kind: 'note', text: CLEARED}]);
  assert.equal(p.rack.items[0].cfg, 'other');
  assert.deepEqual(run('patch', r, {id: 'i7', label: 'x'}), {error: GONE});
});

test('remove: keep or remove its cables, with today\'s sentences', () => {
  let r = add(add(M.newRack(), 'as7726-32x', 10, {label: 'leaf'}), 'as7726-32x', 20, {label: 'spine'});
  r = {...r, cables: [{id: 'c1', a: end('i1'), b: end('i2'), media: '', purpose: '', label: '', route: []},
                      {id: 'c2', a: end('i1', 'port-2'), b: end('i2', 'port-2'), media: '', purpose: '', label: '', route: []}]};
  const keep = run('remove', r, {id: 'i1', cables: 'keep'});
  assert.equal(keep.summary, 'Removed leaf. Its 2 cables are loose ends.');
  assert.equal(keep.rack.cables.length, 2);
  const gone = run('remove', r, {id: 'i1', cables: 'remove'});
  assert.equal(gone.summary, 'Removed leaf and its 2 cables.');
  assert.equal(gone.rack.cables.length, 0);
  assert.equal(run('remove', add(M.newRack(), 'tm-280', 1, {label: 'pp'}), {id: 'i1'}).summary, 'Removed pp.');
});

test('remove: a host\'s managers stay, and the sentence says so', () => {
  let r = add(M.newRack(), 'as7726-32x', 10, {label: 'leaf'});
  r = add(r, 'fhd-cmp5dr', 10, {label: 'mgr', on: 'i1', unit: 1});
  assert.equal(run('remove', r, {id: 'i1'}).summary, 'Removed leaf. Its cable manager mgr stays on the rack.');
});

test('attach and detach', () => {
  let r = add(M.newRack(), 'as7726-32x', 10, {label: 'leaf'});
  r = add(r, 'fhd-cmp5dr', 10, {label: 'mgr'});
  r = add(r, 'fhd-cmp5dr', 30, {label: 'alone'});
  const a = run('attach', r, {id: 'i2'});
  assert.equal(a.summary, 'Attached mgr to leaf.');
  assert.deepEqual(run('attach', r, {id: 'i3'}), {error: 'alone is not over a device.'});
  assert.deepEqual(run('attach', r, {id: 'i1'}), {error: 'leaf is not a cable manager.'});
  const d = run('detach', a.rack, {id: 'i2'});
  assert.equal(d.summary, 'Detached mgr.');
  assert.equal('on' in d.rack.items[1], false);
  assert.equal(run('detach', d.rack, {id: 'i2'}).rack, d.rack);
});

test('frame: a shrink packs down, trims, and says so; holes merge; an echo is a no-op', () => {
  let r = add(add(M.newRack(), 'as7726-32x', 40, {label: 'a'}), 'as7726-32x', 1, {label: 'b'});
  r = {...r, cables: [{id: 'c1', a: end('i2'), b: end('i1'), media: '', purpose: '', label: '', route: []}]};
  const s = run('frame', r, {heightRU: 1});
  // b (U1) is the bottom cluster and goes; a (U40) packs down to U1.
  const text = 'Moved 1 device down and removed 1 from the bottom to fit 1U: b. 1 cable is kept as a loose end.';
  assert.equal(s.summary, text);
  assert.deepEqual(s.findings, [{kind: 'note', text}]);
  const t = run('frame', r, {holes: {style: 'tapped'}});
  assert.equal(t.rack.frame.holes.style, 'tapped');
  assert.equal(run('frame', r, {kind: 'four-post'}).rack, r);
});

test('rename and dcim', () => {
  const r = M.newRack();
  assert.equal(run('rename', r, {name: 'Core A'}).summary, 'Renamed the rack to Core A.');
  assert.deepEqual(run('rename', r, {name: '  '}), {error: 'A rack needs a name.'});
  assert.equal(run('rename', r, {name: r.name}).rack, r);
  assert.deepEqual(run('dcim', r, {site: 'dc1'}).rack.dcim, {site: 'dc1'});
  assert.equal(run('dcim', r, {site: ''}).rack, r);
});

test('cable.add, cable.update, cable.remove', () => {
  const r = add(add(M.newRack(), 'as7726-32x', 10, {label: 'leaf'}), 'as7726-32x', 20, {label: 'spine'});
  const a = run('cable.add', r, {a: end('i1'), b: end('i2'), media: 'om4'});
  assert.deepEqual([a.created, a.summary], [{id: 'c1'}, 'Added cable c1.']);
  assert.deepEqual(run('cable.add', a.rack, {a: end('i1'), b: end('i2', 'port-5')}),
                   {error: 'leaf (U10) port-1 already has a cable (c1).'});
  assert.deepEqual(run('cable.add', r, {a: end('i1'), b: end('i9')}), {error: NOT_ADDED});
  assert.deepEqual(run('cable.add', r, {a: end('i1'), b: end('i1')}), {error: 'A cable needs two different ports.'});
  const u = run('cable.update', a.rack, {id: 'c1', label: 'A1', length: {value: 3}});
  assert.deepEqual(u.rack.cables[0].length, {value: 3, unit: 'm', source: 'entered'});
  assert.equal(u.summary, 'Edited cable A1.');
  assert.equal(run('cable.update', a.rack, {id: 'c1', media: 'om4'}).rack, a.rack);
  assert.deepEqual(run('cable.update', a.rack, {id: 'c9', label: 'x'}), {error: CABLE_GONE});
  assert.equal(run('cable.remove', u.rack, {id: 'c1'}).summary, 'Deleted cable A1.');
});

test('cable.route and cable.route.reset', () => {
  let r = add(add(M.newRack(), 'as7726-32x', 10), 'as7726-32x', 20);
  r = {...r, cables: [{id: 'c1', a: end('i1'), b: end('i2'), media: '', purpose: '', label: 'A1', route: []}]};
  const route = [{lane: 'left-front', ru: 15}];
  const s = run('cable.route', r, {id: 'c1', route});
  assert.deepEqual([s.rack.cables[0].route, s.rack.cables[0].routeEdited, s.summary], [route, true, 'Routed cable A1 by hand.']);
  assert.equal(run('cable.route', s.rack, {id: 'c1', route}).rack, s.rack);
  const t = run('cable.route.reset', s.rack, {id: 'c1'});
  assert.deepEqual([t.rack.cables[0].route, 'routeEdited' in t.rack.cables[0], t.summary],
                   [[], false, 'Put cable A1 back on its own route.']);
  assert.equal(run('cable.route.reset', t.rack, {id: 'c1'}).rack, t.rack);
  assert.deepEqual(run('cable.route', r, {id: 'c9', route}), {error: CABLE_GONE});
  assert.deepEqual(run('cable.route.reset', r, {id: 'c9'}), {error: CABLE_GONE});
});

test('cable.route and cable.route.reset take the summary the page gives them', () => {
  let r = add(add(M.newRack(), 'as7726-32x', 10), 'as7726-32x', 20);
  r = {...r, cables: [{id: 'c1', a: end('i1'), b: end('i2'), media: '', purpose: '', label: 'A1', route: []}]};
  const s = run('cable.route', r, {id: 'c1', route: [{lane: 'left-front', ru: 15}], summary: 'Waypoint added.'});
  assert.equal(s.summary, 'Waypoint added.');
  assert.equal(run('cable.route.reset', s.rack, {id: 'c1', summary: 'Route reset to automatic.'}).summary, 'Route reset to automatic.');
});

test('a route written by hand drops the route the loader kept as written', () => {
  let r = add(add(M.newRack(), 'as7726-32x', 10), 'as7726-32x', 20);
  r = {...r, cables: [{id: 'c1', a: end('i1'), b: end('i2'), media: '', purpose: '', label: '', route: [], routeAsWritten: 'junk'}]};
  assert.equal('routeAsWritten' in run('cable.route', r, {id: 'c1', route: []}).rack.cables[0], false);
});

test('lengths.routed is a system command that is not a step', () => {
  assert.equal(COMMANDS['lengths.routed'].step, false);
  assert.equal(COMMANDS['lengths.routed'].system, true);
  // Nothing to measure: the very rack comes back.
  const r = add(M.newRack(), 'as7726-32x', 10);
  assert.equal(run('lengths.routed', r, {routeCtx: {}}).rack, r);
});

test('the same swaps in another key order, or a length as the loader wrote it, change nothing', () => {
  const r = add(M.newRack(), 'r740xd', 10, {label: 'Srv', swaps: {x: 'a', y: 'b'}});
  assert.equal(run('patch', r, {id: 'i1', swaps: {y: 'b', x: 'a'}}).rack, r);
  let c = add(add(M.newRack(), 'as7726-32x', 10), 'as7726-32x', 20);
  c = {...c, cables: [{id: 'c1', a: end('i1'), b: end('i2'), media: '', purpose: '', label: '', route: [],
                       length: {unit: 'm', value: 3, source: 'entered'}}]};
  assert.equal(run('cable.update', c, {id: 'c1', length: {value: 3}}).rack, c);
});

test('cable.route refuses an entry that is neither a pathway nor a gutter', () => {
  let r = add(add(M.newRack(), 'as7726-32x', 10), 'as7726-32x', 20);
  r = {...r, cables: [{id: 'c1', a: end('i1'), b: end('i2'), media: '', purpose: '', label: '', route: []}]};
  assert.deepEqual(run('cable.route', r, {id: 'c1', route: [{lane: 'left-front', ru: 4}, {}]}),
                   {error: 'Waypoint 2 is neither a pathway nor a gutter.'});
  assert.deepEqual(run('cable.route', r, {id: 'c1', route: [null]}), {error: 'Waypoint 1 is neither a pathway nor a gutter.'});
  assert.deepEqual(run('cable.route', r, {id: 'c1', route: [{lane: 'left-front', ru: 1.5}]}),
                   {error: 'Waypoint 1 is neither a pathway nor a gutter.'});
});

test('a command keeps its own copy of what the caller passed', () => {
  const r = add(M.newRack(), 'r740xd', 10, {label: 'Srv'});
  const swaps = {'slot-1': 'a'}, fields = {f: {text: 'x'}};
  const p = run('patch', r, {id: 'i1', swaps, fields});
  const was = structuredClone(p.rack);
  swaps['slot-1'] = 'b'; fields.f.text = 'y';
  assert.deepEqual(p.rack, was);
  let c = add(add(M.newRack(), 'as7726-32x', 10), 'as7726-32x', 20);
  c = {...c, cables: [{id: 'c1', a: end('i1'), b: end('i2'), media: '', purpose: '', label: '', route: []}]};
  const route = [{lane: 'left-front', ru: 15}];
  const s = run('cable.route', c, {id: 'c1', route});
  route[0].ru = 99; route.push({lane: 'left-front', ru: 1});
  assert.deepEqual(s.rack.cables[0].route, [{lane: 'left-front', ru: 15}]);
  const a = {item: 'i1', path: 'port-2', view: 'front'};
  const added = run('cable.add', c, {a, b: end('i2', 'port-2')});
  a.path = 'port-9';
  assert.equal(added.rack.cables[1].a.path, 'port-2');
});

test('place and move above the top of the rack say so', () => {
  const r = add(M.newRack(), 'as7726-32x', 10, {label: 'leaf'});
  assert.deepEqual(run('place', r, {ref: 'as7726-32x', face: 'front', ru: 99}), {error: 'U99 is past the top of this 42U rack.'});
  assert.deepEqual(run('move', r, {id: 'i1', ru: 43}), {error: 'U43 is past the top of this 42U rack.'});
});

test('lengths.routed refuses a routing context it cannot measure with', () => {
  let r = add(add(M.newRack(), 'as7726-32x', 10), 'as7726-32x', 20);
  r = {...r, cables: [{id: 'c1', a: end('i1'), b: end('i2'), media: '', purpose: '', label: '', route: []}]};
  assert.deepEqual(run('lengths.routed', r, {routeCtx: {}}), {error: 'The routed lengths could not be measured.'});
});
