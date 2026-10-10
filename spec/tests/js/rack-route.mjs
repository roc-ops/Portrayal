import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import * as R from '../../../kit/rack/route.js';
import {RU, OPENING, RAIL_W} from '../../../kit/rack/rails.js';

const SIZES = {'sw': {ru: 1, d: 515}, 'pp': {ru: 1, d: 100},
  'fhd-cmp5dr': {ru: 1, d: 110, mount: 'rack-face', shell: 'sheet'},
  'cmh-sfd1u': {ru: 1, d: 80}};
const chassisOf = ref => SIZES[ref] || null;
const add = (rack, ref, ru, extra = {}) => M.withItem(rack, {ref, cfg: 'x', ru, label: extra.label ?? ref, ...extra}).rack;
// Rings of an FHD-CMP5DR, x in rack coordinates (as its front view places them).
const RINGS = [-205, -110, 0, 110, 205].map((x, i) => ({via: `guide-${i + 1}`, kind: 'ring', face: 'front', x}));
const ctxFor = (rack, ports, extra = {}) => ({chassisOf,
  guidesOf: id => {
    const it = rack.items.find(i => i.id === id);
    if (it?.ref === 'fhd-cmp5dr') return RINGS.map(r => ({...r, face: it.face}));
    if (it?.ref === 'cmh-sfd1u') return [{via: 'duct', kind: 'duct', face: it.face, x: 0}];
    return extra[id] ?? [];
  },
  portX: end => ports[`${end.item}|${end.path}`] ?? 0});
const cable = (a, b, extra = {}) => ({id: 'c1', a: {view: 'front', ...a}, b: {view: 'front', ...b}, route: [], ...extra});

test('a port left of center leaves through the nearest ring, then every ring out to the left', () => {
  let r = add(M.newRack(), 'sw', 20, {label: 'sw'});
  r = add(r, 'fhd-cmp5dr', 20, {on: 'i1', unit: 1});
  r = add(r, 'pp', 30);
  const ctx = ctxFor(r, {'i1|p1': -100, 'i3|q1': -150});
  assert.deepEqual(R.autoRoute(r, cable({item: 'i1', path: 'p1'}, {item: 'i3', path: 'q1'}), ctx), [
    {item: 'i2', via: 'guide-2'}, {item: 'i2', via: 'guide-1'},
    {lane: 'left-front', ru: 20}, {lane: 'left-front', ru: 30}]);
});

test('a port right of center goes right; a port at the center goes left', () => {
  let r = add(M.newRack(), 'sw', 20);
  r = add(r, 'fhd-cmp5dr', 20, {on: 'i1', unit: 1});
  r = add(r, 'pp', 30);
  // Under ring 4 (110, within half its depth): through it, then ring 5.
  const right = R.autoRoute(r, cable({item: 'i1', path: 'p'}, {item: 'i3', path: 'q'}), ctxFor(r, {'i1|p': 112, 'i3|q': 120}));
  assert.deepEqual(right.slice(0, 2), [{item: 'i2', via: 'guide-4'}, {item: 'i2', via: 'guide-5'}]);
  assert.equal(right[2].lane, 'right-front');
  // Past ring 4 on the way out: ring 4 is behind the port, and the cable
  // would enter and leave it by one face (#930), so it goes on from ring 5.
  const past = R.autoRoute(r, cable({item: 'i1', path: 'p'}, {item: 'i3', path: 'q'}), ctxFor(r, {'i1|p': 120, 'i3|q': 120}));
  assert.deepEqual(past.slice(0, 2), [{item: 'i2', via: 'guide-5'}, {lane: 'right-front', ru: 20}]);
  const mid = R.autoRoute(r, cable({item: 'i1', path: 'p'}, {item: 'i3', path: 'q'}), ctxFor(r, {'i1|p': 0, 'i3|q': 0}));
  assert.deepEqual(mid[0], {item: 'i2', via: 'guide-3'});
  assert.equal(mid.find(w => w.lane).lane, 'left-front');
});

test('a 1U duct directly above is the manager when the device has none', () => {
  let r = add(M.newRack(), 'sw', 20);
  r = add(r, 'cmh-sfd1u', 21);
  r = add(r, 'pp', 30);
  const route = R.autoRoute(r, cable({item: 'i1', path: 'p'}, {item: 'i3', path: 'q'}), ctxFor(r, {'i1|p': -50, 'i3|q': -50}));
  assert.deepEqual(route[0], {item: 'i2', via: 'duct'});
});

test('a short jumper with no manager has no route', () => {
  let r = add(M.newRack(), 'sw', 20);
  r = add(r, 'pp', 22);
  assert.deepEqual(R.autoRoute(r, cable({item: 'i1', path: 'p'}, {item: 'i2', path: 'q'}), ctxFor(r, {})), []);
});

test('a rack with no managers: lanes only, and nothing throws', () => {
  let r = add(M.newRack(), 'sw', 5);
  r = add(r, 'pp', 30);
  assert.deepEqual(R.autoRoute(r, cable({item: 'i1', path: 'p'}, {item: 'i2', path: 'q'}), ctxFor(r, {'i1|p': 10, 'i2|q': -10})),
    [{lane: 'right-front', ru: 5}, {lane: 'right-front', ru: 30}]);
});

test('the same face, different sides: the shorter side is taken, whichever end is a (#949)', () => {
  let r = add(M.newRack(), 'sw', 20);
  r = add(r, 'fhd-cmp5dr', 20, {on: 'i1', unit: 1});
  r = add(r, 'pp', 30);
  r = add(r, 'fhd-cmp5dr', 30, {on: 'i3', unit: 1});
  const ctx = ctxFor(r, {'i1|p': -100, 'i3|q': 150});
  const c = cable({item: 'i1', path: 'p'}, {item: 'i3', path: 'q'});
  // a at -100, b at 150: by the right, a crosses three rings and b one; by
  // the left (end a's side, which was the rule) a crosses two and b four
  const right = [{item: 'i2', via: 'guide-3'}, {item: 'i2', via: 'guide-4'}, {item: 'i2', via: 'guide-5'},
    {lane: 'right-front', ru: 20}, {lane: 'right-front', ru: 30}, {item: 'i4', via: 'guide-5'}];
  const left = [{item: 'i2', via: 'guide-2'}, {item: 'i2', via: 'guide-1'}, {lane: 'left-front', ru: 20},
    {lane: 'left-front', ru: 30}, {item: 'i4', via: 'guide-1'}, {item: 'i4', via: 'guide-2'},
    {item: 'i4', via: 'guide-3'}, {item: 'i4', via: 'guide-4'}];
  assert.deepEqual(R.autoRoute(r, c, ctx), right);
  const mm = route => Math.round(R.routedLength(r, {...c, route, routeEdited: true}, ctx).measured * 10000) / 10;
  // (1318.5 and 1459.8 from the port faces, before the plug's reach, #960;
  // 1361.8 and 1472.9 taut, before each free span hung by its drape, #949
  // step 3: the right still the shorter; 1387.4 and 1502.7 before #962's
  // end allowance, 34.5 mm an end for a cable with no media, not 150: 231
  // shorter each)
  assert.deepEqual([mm(right), mm(left)], [1156.4, 1271.7]);
  // the same cable written the other way round takes the same side
  const back = cable({item: 'i3', path: 'q'}, {item: 'i1', path: 'p'});
  assert.deepEqual(R.autoRoute(r, back, ctx), right.toReversed());
  // a tie keeps end a's side: ports at -100 and 100 are as far from either gutter
  const tie = ctxFor(r, {'i1|p': -100, 'i3|q': 100});
  assert.equal(R.autoRoute(r, c, tie).find(w => w.lane).lane, 'left-front');
  assert.equal(R.autoRoute(r, back, tie).find(w => w.lane).lane, 'right-front');
});

test('opposite faces: front lane to rear lane on the A side, joined at the higher U', () => {
  let r = add(M.newRack(), 'sw', 20);
  r = add(r, 'pp', 30, {face: 'rear'});
  const route = R.autoRoute(r, cable({item: 'i1', path: 'p'}, {item: 'i2', path: 'q'}), ctxFor(r, {'i1|p': -100, 'i2|q': 100}));
  assert.deepEqual(route, [{lane: 'left-front', ru: 20}, {lane: 'left-front', ru: 30}, {lane: 'left-rear', ru: 30}]);
});

test('a rear-face end measures its side as seen from the front', () => {
  let r = add(M.newRack(), 'sw', 20, {face: 'rear'});
  r = add(r, 'pp', 30, {face: 'rear'});
  // x is already rack coordinates (front view): -100 is the rack's left.
  const route = R.autoRoute(r, cable({item: 'i1', path: 'p'}, {item: 'i2', path: 'q'}), ctxFor(r, {'i1|p': -100, 'i2|q': -100}));
  assert.equal(route[0].lane, 'left-rear');
});

test('two-post: lanes are left and right, and opposite faces share one', () => {
  let r = add(M.newRack({kind: 'two-post'}), 'sw', 20);
  r = add(r, 'pp', 30, {face: 'rear'});
  assert.deepEqual(R.lanesOf(r.frame), ['left', 'right']);
  const route = R.autoRoute(r, cable({item: 'i1', path: 'p'}, {item: 'i2', path: 'q'}), ctxFor(r, {'i1|p': -100}));
  assert.deepEqual(route, [{lane: 'left', ru: 20}, {lane: 'left', ru: 30}]);
});

test('resolveRoute: edited routes are kept; a gone waypoint is reported, not dropped', () => {
  let r = add(M.newRack(), 'sw', 20);
  r = add(r, 'pp', 30);
  const c = cable({item: 'i1', path: 'p'}, {item: 'i2', path: 'q'},
    {routeEdited: true, route: [{item: 'i9', via: 'guide-1'}, {lane: 'left-front', ru: 25}, {lane: 'nowhere', ru: 3}]});
  const got = R.resolveRoute(r, c, ctxFor(r, {}));
  assert.deepEqual(got, {waypoints: [{lane: 'left-front', ru: 25}],
    gone: [{item: 'i9', via: 'guide-1'}, {lane: 'nowhere', ru: 3}], auto: false});
  const auto = R.resolveRoute(r, {...c, routeEdited: undefined}, ctxFor(r, {}));
  assert.equal(auto.auto, true);
});

test('routeText reads as the schedule prints it', () => {
  assert.equal(R.routeText([{item: 'i2', via: 'guide-3'}, {item: 'i2', via: 'guide-1'}, {lane: 'left-front', ru: 12},
    {lane: 'left-front', ru: 24}, {item: 'i5', via: 'duct'}], id => ({i2: 'mgr-1', i5: 'pp-duct'}[id] ?? id)),
    'mgr-1 ring 3 > mgr-1 ring 1 > left-front U12-U24 > pp-duct duct');
});

test('a manager hosted on the adjacent device above is the manager', () => {
  let r = add(M.newRack(), 'sw', 20);
  r = add(r, 'pp', 21);
  r = add(r, 'fhd-cmp5dr', 21, {on: 'i2', unit: 1});
  r = add(r, 'pp', 30);
  const route = R.autoRoute(r, cable({item: 'i1', path: 'p'}, {item: 'i4', path: 'q'}), ctxFor(r, {'i1|p': -100, 'i4|q': -100}));
  assert.deepEqual(route.slice(0, 2), [{item: 'i3', via: 'guide-2'}, {item: 'i3', via: 'guide-1'}]);
});

test('managers both above and below: the one above is used', () => {
  let r = add(M.newRack(), 'cmh-sfd1u', 19);
  r = add(r, 'sw', 20);
  r = add(r, 'cmh-sfd1u', 21);
  r = add(r, 'pp', 30);
  const route = R.autoRoute(r, cable({item: 'i2', path: 'p'}, {item: 'i4', path: 'q'}), ctxFor(r, {}));
  assert.deepEqual(route[0], {item: 'i3', via: 'duct'});
});

test('two ends beside one duct manager run in the duct, with no lane (#949)', () => {
  let r = add(M.newRack(), 'sw', 20);
  r = add(r, 'cmh-sfd1u', 21);
  r = add(r, 'pp', 22);
  const route = R.autoRoute(r, cable({item: 'i1', path: 'p'}, {item: 'i3', path: 'q'}), ctxFor(r, {'i1|p': -50, 'i3|q': 120}));
  assert.deepEqual(route, [{item: 'i2', via: 'duct'}]);
});

test('two ends on one ring manager run through the rings between them, in order from end a, else the nearest (#949)', () => {
  let r = add(M.newRack(), 'sw', 20);
  r = add(r, 'fhd-cmp5dr', 20, {on: 'i1', unit: 1});
  r = add(r, 'pp', 21);
  const c = cable({item: 'i3', path: 'q'}, {item: 'i1', path: 'p'});
  // a at 150 on the panel above, b at -150 on the switch: rings 4, 3 and 2, leftward
  assert.deepEqual(R.autoRoute(r, c, ctxFor(r, {'i1|p': -150, 'i3|q': 150})),
    [{item: 'i2', via: 'guide-4'}, {item: 'i2', via: 'guide-3'}, {item: 'i2', via: 'guide-2'}]);
  // a ring at a port's own x is between
  assert.deepEqual(R.autoRoute(r, c, ctxFor(r, {'i1|p': 0, 'i3|q': 110})), [{item: 'i2', via: 'guide-4'}, {item: 'i2', via: 'guide-3'}]);
  // no ring between (1 to 109): never direct, but the ring nearest the middle
  // (55), rings 3 and 4 being as near, the one on end a's side
  assert.deepEqual(R.autoRoute(r, c, ctxFor(r, {'i1|p': 1, 'i3|q': 109})), [{item: 'i2', via: 'guide-4'}]);
  const swapped = cable({item: 'i1', path: 'p'}, {item: 'i3', path: 'q'});
  assert.deepEqual(R.autoRoute(r, swapped, ctxFor(r, {'i1|p': 1, 'i3|q': 109})), [{item: 'i2', via: 'guide-3'}]);
  // and not a tie: 20 to 60, the middle 40, ring 3
  assert.deepEqual(R.autoRoute(r, c, ctxFor(r, {'i1|p': 20, 'i3|q': 60})), [{item: 'i2', via: 'guide-3'}]);
  // the middle, not end a: a at 15 is nearer ring 3, but the middle (60) is nearer ring 4
  assert.deepEqual(R.autoRoute(r, swapped, ctxFor(r, {'i1|p': 15, 'i3|q': 105})), [{item: 'i2', via: 'guide-4'}]);
});

test('endPane: face, turned, and the end view', () => {
  const rows = [['front', false, 'front', 'front'], ['front', false, 'rear', 'rear'],
    ['front', true, 'front', 'rear'], ['front', true, 'rear', 'front'],
    ['rear', false, 'front', 'rear'], ['rear', false, 'rear', 'front'],
    ['rear', true, 'front', 'front'], ['rear', true, 'rear', 'rear']];
  for (const [face, turned, view, want] of rows) {
    const r = {items: [{id: 'i1', face, turned}]};
    assert.equal(R.endPane(r, {item: 'i1', view}), want, `${face} turned=${turned} view=${view}`);
  }
});

test('stock lengths round up, then by 5 m past 30', () => {
  assert.deepEqual([0.2, 0.5, 0.51, 1.62, 2.01, 9.9, 29.1, 30.2, 41].map(R.stockLength),
    [0.5, 0.5, 1, 2, 3, 10, 30, 35, 45]);
});

test('a lane point sits in its gutter at the U middle, on its face\'s rail plane', () => {
  const r = M.newRack();
  const p = R.pointOf(r, {lane: 'left-rear', ru: 10}, ctxFor(r, {}));
  assert.deepEqual(p, {x: -(OPENING / 2 + RAIL_W + R.LANE_GAP / 2), y: 9.5 * RU, z: -r.frame.railDepth});
});

test('a routed length measures the path, adds the end allowance at each end, and rounds to stock', () => {
  let r = add(M.newRack(), 'sw', 1);
  r = add(r, 'pp', 21);
  // a cable too stiff to sag (bendOf: no span can take the bend), so the
  // path is the taut one worked below; resting is rack-resting.mjs's
  const ctx = {...ctxFor(r, {'i1|p': -100, 'i2|q': -100}), portY: () => null, bendOf: () => 1e12};
  const got = R.routedLength(r, cable({item: 'i1', path: 'p'}, {item: 'i2', path: 'q'}), ctx);
  // port -> its plug's reach, straight out of the face (a cable with no
  // media: the copper plug's, 39.4, #960) -> left lane (|dx| = lane x - 100,
  // back on the rail plane) at U1, up 20U, back to the reach point and the
  // port at U21.
  const dx = OPENING / 2 + RAIL_W + R.LANE_GAP / 2 - 100, ra = 39.4;
  const mm = 2 * (ra + Math.hypot(dx, ra)) + 20 * RU;
  // and a cable with no media's end allowance, the copper cord's 34.5 mm,
  // at each end (#962; 0.15 m before)
  assert.ok(Math.abs(got.measured - (mm / 1000 + 2 * 0.0345)) < 1e-9, `measured ${got.measured}`);
  assert.equal(got.value, R.stockLength(got.measured));
});

test('fill: Cat6 through one ring, against 40% of its opening', () => {
  let r = add(M.newRack(), 'sw', 20);
  r = add(r, 'fhd-cmp5dr', 20, {on: 'i1', unit: 1});
  r = add(r, 'pp', 30);
  const ctx = ctxFor(r, {'i1|p': -205, 'i3|q': -205});
  const g0 = ctx.guidesOf;
  ctx.guidesOf = id => g0(id).map(g => ({...g, aperture: {w: 32, h: 29.5}}));
  r = {...r, cables: Array.from({length: 14}, (_, k) => ({id: `c${k}`, media: 'cat6', route: [],
    a: {item: 'i1', path: 'p', view: 'front'}, b: {item: 'i3', path: 'q', view: 'front'}}))};
  const f = R.fill(r, ctx).find(x => x.via === 'guide-1');
  const pct = Math.round(14 * Math.PI * 9 / (0.4 * 32 * 29.5) * 100);
  assert.deepEqual([f.count, f.percent, f.over], [14, pct, true]);
});

test('capacity: a manager over its stated count', () => {
  SIZES['fhd-cmp5dr'].capacity = {count: 2, basis: 'test'};
  let r = add(M.newRack(), 'sw', 20);
  r = add(r, 'fhd-cmp5dr', 20, {on: 'i1', unit: 1});
  r = add(r, 'pp', 30);
  r = {...r, cables: [0, 1, 2].map(k => ({id: `c${k}`, media: 'cat6', route: [],
    a: {item: 'i1', path: 'p', view: 'front'}, b: {item: 'i3', path: 'q', view: 'front'}}))};
  try {
    assert.deepEqual(R.capacityOver(r, ctxFor(r, {'i1|p': -100})), [{item: 'i2', count: 3, capacity: 2}]);
  } finally { delete SIZES['fhd-cmp5dr'].capacity; }
});

test('withRoutedLengths fills unset lengths, updates routed ones, and never touches an entered one', () => {
  let r = add(M.newRack(), 'sw', 1);
  r = add(r, 'pp', 21);
  const base = {a: {item: 'i1', path: 'p', view: 'front'}, b: {item: 'i2', path: 'q', view: 'front'}, route: []};
  r = {...r, cables: [{id: 'c1', ...base}, {id: 'c2', ...base, length: {value: 7, unit: 'ft', source: 'entered'}},
                      {id: 'c3', ...base, length: {value: 9, unit: 'm', source: 'routed', measured: 8.7}}]};
  const ctx = {...ctxFor(r, {'i1|p': -100, 'i2|q': -100}), portY: () => null};
  const out = R.withRoutedLengths(r, ctx);
  assert.equal(out.cables[0].length.source, 'routed');
  assert.deepEqual(out.cables[1].length, {value: 7, unit: 'ft', source: 'entered'});
  assert.equal(out.cables[2].length.value, out.cables[0].length.value);
  assert.equal(R.withRoutedLengths(out, ctx), out);
});

test('withRoutedLengths leaves a cable alone whose written length the page could not read', () => {
  let r = add(M.newRack(), 'sw', 1);
  r = add(r, 'pp', 21);
  const base = {a: {item: 'i1', path: 'p', view: 'front'}, b: {item: 'i2', path: 'q', view: 'front'}, route: []};
  r = {...r, cables: [{id: 'c1', ...base, lengthAsWritten: {value: 'long', unit: 'm'}}]};
  const ctx = {...ctxFor(r, {'i1|p': -100, 'i2|q': -100}), portY: () => null};
  const out = R.withRoutedLengths(r, ctx);
  assert.equal(out, r);
  assert.equal(out.cables[0].length, undefined);
});

test('a loose end (no port found) gets no routed length, and a routed length already there is kept', () => {
  let r = add(M.newRack(), 'sw', 1);
  r = add(r, 'pp', 21);
  const base = {a: {item: 'i1', path: 'p', view: 'front'}, b: {item: 'i2', path: 'q', view: 'front'}, route: []};
  r = {...r, cables: [{id: 'c1', ...base}, {id: 'c3', ...base, length: {value: 9, unit: 'm', source: 'routed', measured: 8.7}}]};
  const ctx = {...ctxFor(r, {}), portY: () => null, portX: end => (end.item === 'i2' ? null : -100)};
  assert.equal(R.portPoint(r, base.b, ctx), null);
  assert.equal(R.routedLength(r, r.cables[0], ctx), null);
  const out = R.withRoutedLengths(r, ctx);
  assert.equal(out, r);
  assert.equal(out.cables[0].length, undefined);
  assert.deepEqual(out.cables[1].length, {value: 9, unit: 'm', source: 'routed', measured: 8.7});
});

test('a rack device\'s guide on its far panel sits at its chassis depth, like a port there', () => {
  let r = add(M.newRack(), 'sw', 3);               // a front-face 515 mm device
  const g = {via: 'rear-ring', kind: 'ring', face: 'rear', x: 10};
  const ctx = ctxFor(r, {}, {i1: [g]});
  assert.equal(R.pointOf(r, {item: 'i1', via: 'rear-ring'}, ctx).z, -515);
  const own = ctxFor(r, {}, {i1: [{...g, face: 'front'}]});
  assert.equal(R.pointOf(r, {item: 'i1', via: 'rear-ring'}, own).z, 0);
});
