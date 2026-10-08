// A cable passes THROUGH a D-ring along its run, not to a point inside it
// (roc-ops/Portrayal#930). Lengths are checked against figures worked by hand
// from the rack's own measure (route.js): x from the centre line, y up, z out
// of the front rail plane.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import * as R from '../../../kit/rack/route.js';
import {throughRings, routed2d} from '../../../kit/rack/route-path.js';
import {routePoints3d} from '../../../kit/rack/cable-geometry.js';
import {RU, OPENING, RAIL_W} from '../../../kit/rack/rails.js';

const SIZES = {sw: {ru: 1, d: 515}, pp: {ru: 1, d: 100}, lacer: {ru: 1, d: 110, mount: 'rack-face', shell: 'sheet'}};
const chassisOf = ref => SIZES[ref] || null;
const add = (rack, ref, ru, extra = {}) => M.withItem(rack, {ref, cfg: 'x', ru, label: ref, ...extra}).rack;
// sw at U20 (i1), a lacer on it (i2), a patch panel at U30 (i3).
const rackOf = () => add(add(add(M.newRack(), 'sw', 20), 'lacer', 20, {on: 'i1', unit: 1}), 'pp', 30);
const ctxOf = (rings, ports, portY = {}) => ({chassisOf,
  guidesOf: id => (id === 'i2' ? rings.map(g => ({kind: 'ring', face: 'front', ...g})) : []),
  portX: end => ports[end.item] ?? null,
  portY: end => portY[end.item] ?? null});
const cableOf = (route = null) => ({id: 'c1', media: 'cat6', a: {item: 'i1', path: 'p', view: 'front'},
  b: {item: 'i3', path: 'q', view: 'front'}, ...(route ? {route, routeEdited: true} : {route: []})});

const LANE = OPENING / 2 + RAIL_W + R.LANE_GAP / 2;   // |x| of a lane
const Y20 = 19.5 * RU;                                // the U middle of U20
const Y20r = Math.round(Y20 * 10) / 10;               // as inspect rounds it, to 0.1 mm
const Z = 55;                                         // the lacer's guides: half its 110 depth out
const near = (got, want, what) => assert.ok(Math.abs(got - want) < 1e-9, `${what}: ${got}, want ${want}`);
const lengthMm = (r, c, ctx) => (R.routedLength(r, c, ctx).measured - 2 * R.END_ALLOWANCE_M) * 1000;

test('throughRings: a ring centre becomes its entry and exit, half its depth either side, in travel order', () => {
  const got = throughRings([[0, 0], [100, 0], [200, 0]], [null, {run: 'x', depth: 10}, null]);
  assert.deepEqual(got.points, [[0, 0], [95, 0], [105, 0], [200, 0]]);
  assert.deepEqual(got.passes.map(p => p.sense), [1]);
  const back = throughRings([[200, 0], [100, 0], [0, 0]], [null, {run: 'x', depth: 10}, null]);
  assert.deepEqual(back.points, [[200, 0], [105, 0], [95, 0], [0, 0]]);
});

test('one ring: the cable enters on the side of the port, passes straight along x, and the length is hand-worked', () => {
  const r = rackOf();
  const ctx = ctxOf([{via: 'guide-1', x: -150, aperture: {w: 32, h: 29.5}}], {i1: -100, i3: -100});
  const c = cableOf([{item: 'i2', via: 'guide-1'}, {lane: 'left-front', ru: 20}, {lane: 'left-front', ru: 30}]);
  const path = R.routePath(r, c, ctx);
  const [a, entry, exit, l1, l2, b] = path.points;
  assert.deepEqual([a.at, entry.at, exit.at, l1.at, l2.at, b.at], ['a', 'entry', 'exit', 'lane', 'lane', 'b']);
  // the default depth, estimated: the ring states none
  assert.deepEqual(path.rings.map(g => [g.depth, g.estimated, g.sense]), [[R.RING_DEPTH, true, -1]]);
  assert.deepEqual([entry.x, exit.x], [-150 + R.RING_DEPTH / 2, -150 - R.RING_DEPTH / 2]);
  assert.deepEqual([entry.y, entry.z], [exit.y, exit.z]);
  // a(-100, Y20, 0) -> entry(-145, Y20, 55) -> exit(-155) -> lane(-LANE, Y20, 0) -> up 10U -> b(-100, Y30, 0)
  const h = R.RING_DEPTH / 2;
  const want = Math.hypot(50 - h, Z) + R.RING_DEPTH + Math.hypot(LANE - 150 - h, Z) + 10 * RU + (LANE - 100);
  near(lengthMm(r, c, ctx), want, 'one ring');
  // and the ring states its depth: that is used, and not estimated
  const stated = ctxOf([{via: 'guide-1', x: -150, depth: 6.8}], {i1: -100, i3: -100});
  assert.deepEqual(R.routePath(r, c, stated).rings.map(g => [g.depth, g.estimated]), [[6.8, false]]);
  near(lengthMm(r, c, stated), Math.hypot(50 - 3.4, Z) + 6.8 + Math.hypot(LANE - 153.4, Z) + 10 * RU + (LANE - 100), 'stated depth');
});

test('collinear rings: one straight pass through all of them', () => {
  const r = rackOf();
  const rings = [-205, -110, 0].map((x, i) => ({via: `guide-${i + 1}`, x}));
  const ctx = ctxOf(rings, {i1: 50, i3: -100});
  const c = cableOf([{item: 'i2', via: 'guide-3'}, {item: 'i2', via: 'guide-2'}, {item: 'i2', via: 'guide-1'},
    {lane: 'left-front', ru: 20}, {lane: 'left-front', ru: 30}]);
  const path = R.routePath(r, c, ctx);
  const inRings = path.points.slice(1, 7);
  assert.deepEqual(inRings.map(p => p.at), ['entry', 'exit', 'entry', 'exit', 'entry', 'exit']);
  // one line: the same y and z all the way, x falling from the first entry to the last exit
  assert.ok(inRings.every(p => p.y === Y20 && p.z === Z));
  const xs = inRings.map(p => p.x), h = R.RING_DEPTH / 2;
  assert.deepEqual(xs, [h, -h, -110 + h, -110 - h, -205 + h, -205 - h]);
  assert.ok(xs.every((x, k) => k === 0 || x < xs[k - 1]), 'never turns back');
  assert.deepEqual(path.findings, []);
  // a(50, Y20, 0) -> first entry -> straight to the last exit -> lane -> up -> b(-100, Y30, 0)
  const want = Math.hypot(50 - h, Z) + (205 + 2 * h) + Math.hypot(LANE - 205 - h, Z) + 10 * RU + (LANE - 100);
  near(lengthMm(r, c, ctx), want, 'collinear rings');
});

test('a ring approached at 90 degrees: the bend is at its face, outside, and it is straight inside', () => {
  const r = rackOf();
  // The port is directly below the ring's centre, 30 mm lower: it stands on
  // neither side, so the ring is entered from the side away from the lane.
  const ctx = ctxOf([{via: 'guide-1', x: -150}], {i1: -150, i3: -100}, {i1: Y20 - 30});
  const c = cableOf([{item: 'i2', via: 'guide-1'}, {lane: 'left-front', ru: 20}, {lane: 'left-front', ru: 30}]);
  const path = R.routePath(r, c, ctx), h = R.RING_DEPTH / 2;
  const [a, entry, exit] = path.points;
  assert.deepEqual([entry.x, exit.x], [-150 + h, -150 - h]);
  // nothing between entry and exit but the straight run along x
  // (the port below it stands in the same x band, but not in the ring)
  assert.ok(path.points.every(p => p.at === 'a' || !(p.x < -150 + h && p.x > -150 - h)));
  assert.deepEqual([exit.y - entry.y, exit.z - entry.z], [0, 0]);
  // the turn is at the entry: the cable rises from the port to it, then runs along x
  assert.ok(entry.y - a.y === 30 && entry.z - a.z === Z);
  const want = Math.hypot(h, 30, Z) + R.RING_DEPTH + Math.hypot(LANE - 150 - h, Z) + 10 * RU + (LANE - 100);
  near(lengthMm(r, c, ctx), want, '90 degree approach');
  // The old point-in-the-ring measure was shorter: the length grows by a few mm.
  const old = Math.hypot(30, Z) + Math.hypot(LANE - 150, Z) + 10 * RU + (LANE - 100);
  assert.ok(want > old && want - old < R.RING_DEPTH);
});

test('a route that would enter and leave a ring by one face is a finding, not drawn through, and not counted in fill', () => {
  const r = {...rackOf(), cables: [cableOf([{item: 'i2', via: 'guide-1'}, {lane: 'right-front', ru: 20}, {lane: 'right-front', ru: 30}])]};
  const ctx = ctxOf([{via: 'guide-1', x: -150, aperture: {w: 32, h: 29.5}}], {i1: -100, i3: 100});
  const path = R.routePath(r, r.cables[0], ctx);
  assert.deepEqual(path.findings, [{kind: 'doubles-back', cable: 'c1', item: 'i2', via: 'guide-1'}]);
  assert.deepEqual(path.points.map(p => p.at), ['a', 'face', 'lane', 'lane', 'b']);
  assert.equal(path.points[1].x, -150 + R.RING_DEPTH / 2);
  assert.deepEqual(R.fill(r, ctx), []);
  const [f] = R.ringFindings(r, ctx, id => (id === 'i2' ? 'lacer-1' : id));
  assert.match(f.text, /^c1 would enter and leave lacer-1 ring 1 by the same face/);
});

test('fill counts the cables that pass through a ring', () => {
  const r = {...rackOf(), cables: [cableOf([{item: 'i2', via: 'guide-1'}, {lane: 'left-front', ru: 20}, {lane: 'left-front', ru: 30}])]};
  const ctx = ctxOf([{via: 'guide-1', x: -150, aperture: {w: 32, h: 29.5}}], {i1: -100, i3: -100});
  assert.deepEqual(R.fill(r, ctx).map(e => [e.via, e.count]), [['guide-1', 1]]);
  assert.deepEqual(R.ringFindings(r, ctx), []);
});

test('the automatic route never makes a cable double back through a ring', () => {
  const r = rackOf();
  const rings = [-205, -110, 0, 110, 205].map((x, i) => ({via: `guide-${i + 1}`, x}));
  for (const x of [-230, -200, -150, -112, -100, -3, 0, 3, 100, 108, 112, 150, 230]) {
    const ctx = ctxOf(rings, {i1: x, i3: x});
    const c = {...cableOf(), route: []};
    assert.deepEqual(R.routePath(r, c, ctx).findings, [], `port at ${x}`);
  }
});

test('routed2d with rings: corners are rounded outside the ring, and it is straight inside', () => {
  const d = routed2d([[0, 0], [50, 20], [100, 20]], 4, [null, {run: 'x', depth: 10}, null]);
  // every coordinate the path names between the faces (x 45 to 55) is on the run's line, y 20
  const nums = d.match(/-?\d+(\.\d+)?/g).map(Number);
  for (let k = 0; k < nums.length; k += 2) if (nums[k] >= 45 && nums[k] <= 55) assert.equal(nums[k + 1], 20, d);
  // the bend's control point is the lead point, 4 mm before the entry face
  assert.match(d, /Q41 20 /);
  // without rings, as before
  assert.equal(routed2d([[0, 0], [10, 0], [10, 10]], 4), 'M0 0 L6 0 Q10 0 10 4 L10 10');
});

// Enough of three.js's Vector3 for routePoints3d.
class V {
  constructor(x = 0, y = 0, z = 0) { Object.assign(this, {x, y, z}); }
  clone() { return new V(this.x, this.y, this.z); }
  add(v) { this.x += v.x; this.y += v.y; this.z += v.z; return this; }
  multiplyScalar(s) { this.x *= s; this.y *= s; this.z *= s; return this; }
  addScaledVector(v, s) { this.x += v.x * s; this.y += v.y * s; this.z += v.z * s; return this; }
  lerp(v, t) { this.x += (v.x - this.x) * t; this.y += (v.y - this.y) * t; this.z += (v.z - this.z) * t; return this; }
  distanceTo(v) { return Math.hypot(this.x - v.x, this.y - v.y, this.z - v.z); }
}
const THREE = {Vector3: V};

test('routePoints3d with rings: every point inside the ring is on the run, so the tube is straight there', () => {
  const A = {points: [new V(-150, 0, 0)], normal: new V(0, 0, 1), reach: 40};
  const B = {points: [new V(-260, 300, 0)], normal: new V(0, 0, 1), reach: 40};
  const wps = [new V(-150, 30, 55), new V(-260, 30, 0)];
  const pts = routePoints3d(THREE, A, B, wps, 30, [{run: 'x', depth: 10}, null]);
  // inside the ring: its 10 mm along x, and its opening around the centre (-150, 30, 55)
  const inside = pts.filter(p => p.x <= -145 + 1e-9 && p.x >= -155 - 1e-9 && Math.abs(p.y - 30) < 15 && Math.abs(p.z - 55) < 15);
  assert.ok(inside.length >= 2, 'the entry and exit are there');
  assert.ok(inside.every(p => Math.abs(p.y - 30) < 1e-9 && Math.abs(p.z - 55) < 1e-9), JSON.stringify(inside));
  // and the points either side of the faces, on the run, so the curve is tangent to it there
  // (the lead in: r, clamped to half the way from the point before)
  assert.ok(pts.some(p => p.x > -145 && p.y === 30 && p.z === 55), 'a lead point outside the entry face');
  assert.ok(pts.some(p => p.x < -155 && p.y === 30 && p.z === 55), 'a lead point outside the exit face');
  // without rings, the waypoint itself is a corner, as before
  const plain = routePoints3d(THREE, A, B, wps, 30);
  assert.ok(plain.some(p => p.x === -150 && p.y === 30 && p.z === 55));
});

test('inspect reads a cable\'s rings as routePath measured them; a doubled-back ring is not passed', async () => {
  const {inspect} = await import('../../../kit/rack/queries.js');
  const route = [{item: 'i2', via: 'guide-1'}, {lane: 'left-front', ru: 20}, {lane: 'left-front', ru: 30}];
  const r = {...rackOf(), cables: [cableOf(route)]};
  const ctx = ctxOf([{via: 'guide-1', x: -150}], {i1: -100, i3: -100});
  const got = await inspect(r, 'c1', {chassisOf, route: ctx});
  assert.deepEqual(got.route.rings, [{item: 'i2', via: 'guide-1', run: 'x', depth: R.RING_DEPTH, estimated: true, passed: true,
    sense: -1, entry: [-145, Y20r, Z], exit: [-155, Y20r, Z]}]);
  const back = {...r, cables: [cableOf([route[0], {lane: 'right-front', ru: 20}, {lane: 'right-front', ru: 30}])]};
  const got2 = await inspect(back, 'c1', {chassisOf, route: ctxOf([{via: 'guide-1', x: -150}], {i1: -100, i3: 100})});
  assert.deepEqual(got2.route.rings.map(g => [g.passed, g.face]), [[false, [-145, Y20r, Z]]]);
  // no rings on the route: no `rings` key, as before
  const plain = await inspect({...rackOf(), cables: [cableOf([{lane: 'left-front', ru: 20}])]}, 'c1', {chassisOf, route: ctx});
  assert.equal('rings' in plain.route, false);
});
