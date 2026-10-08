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
  // The port is 50 mm right of the ring, level with it in the face: it stands
  // on the ring's right, as does the lane. (The lacer standing 55 mm out of
  // the face is not an approach angle, and does not make it neither side.)
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
  // The point before (out of the port, x -150) is under the ring, not beyond
  // its entry face: no lead in, so no hook; the corner is at the face.
  assert.ok(!pts.some(p => p.x > -145 && p.y === 30 && p.z === 55), 'no lead in past the point before');
  // No hook: along the run, x only rises from the point under the ring to the
  // entry face (-145), and only falls from there to the lane.
  const xs = pts.map(p => p.x), e = xs.indexOf(-145);
  assert.ok(e > 0 && xs.slice(0, e + 1).every((x, k) => k === 0 || x >= xs[k - 1] - 1e-9)
    && xs.slice(e).every((x, k, l) => k === 0 || x <= l[k - 1] + 1e-9), `x along the path: ${xs.join(' ')}`);
  assert.equal(Math.max(...xs), -145);
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

test('no hook in 2D: a ring approached at 90 degrees gets no lead past the point before, nor past the point after', () => {
  const ring = {run: 'x', depth: 10};
  // down onto the ring's centre at x 100, through it to the left, then down again at x -50
  const {points} = throughRings([[100, 40], [100, 0], [-50, 0], [-50, -200]], [null, ring, null, null], {lead: 30});
  const xs = points.map(p => p[0]);
  assert.equal(Math.max(...xs), 105, `x: ${xs.join(' ')}`);       // the entry face, never beyond it
  assert.equal(Math.min(...xs), -50, `x: ${xs.join(' ')}`);
  // the exit side has room: a lead point, 30 out along the run
  assert.ok(points.some(p => p[0] === 65 && p[1] === 0));
  const d = routed2d([[100, 40], [100, 0], [-50, 0], [-50, -200]], 30, [null, ring, null, null]);
  for (const x of d.match(/[MLQ ](-?[\d.]+) /g).map(t => +t.slice(1))) assert.ok(x <= 105 && x >= -50, d);
  // and the mirror: a point after the exit that is under it (in band) gets no lead out
  const m = throughRings([[0, 0], [100, 0], [100, -40]], [null, ring, null], {lead: 30}).points;
  assert.deepEqual(m.map(p => p[0]), [0, 65, 95, 105, 100]);
});

test('two rings close together: their leads are clamped and never cross', () => {
  const ring = {run: 'x', depth: 10};
  // centres 14 apart: 4 mm between the first exit (105) and the second entry (109)
  const {points} = throughRings([[0, 0], [100, 0], [114, 0], [300, 0]], [null, ring, ring, null], {lead: 30});
  const xs = points.map(p => p[0]);
  assert.ok(xs.every((x, k) => k === 0 || x >= xs[k - 1]), `x: ${xs.join(' ')}`);
  // (unclamped, the 30 mm leads would reach 135 and 79, back across each other)
  assert.ok(xs.includes(105) && xs.includes(109) && xs.filter(x => x > 105 && x < 109).length === 2, `x: ${xs.join(' ')}`);
});

test('a point beside the ring but far off its line IN THE FACE is on neither side; the stand-off out of the face does not count', () => {
  const ring = {run: 'x', depth: 10};
  // 6 mm along the run, 80 mm below: it comes up into the ring; the next point is on the same side
  const got = throughRings([[106, -80], [100, 0], [300, 0]], [null, ring, null]);
  assert.deepEqual(got.back, []);
  assert.deepEqual(got.points, [[106, -80], [95, 0], [105, 0], [300, 0]]);
  // the same 80 mm as the stand-off, z, out of the face: it stands on the right, as the next does
  const out = throughRings([{x: 106, y: 0, z: 0}, {x: 100, y: 0, z: 80}, {x: 300, y: 0, z: 80}], [null, ring, null]);
  assert.deepEqual(out.back.map(b => [b.index, b.sense]), [[1, -1]]);
});

test('an edited route through a ring behind the port: a finding when level with it, none when it comes up steeply or from under it', () => {
  const r = rackOf();
  const rings = [-205, -110, 0, 110, 205].map((x, i) => ({via: `guide-${i + 1}`, x}));
  const c = cableOf([{item: 'i2', via: 'guide-4'}, {item: 'i2', via: 'guide-5'}, {lane: 'right-front', ru: 20}, {lane: 'right-front', ru: 30}]);
  const at = (x, below = 0) => R.routePath(r, c, ctxOf(rings, {i1: x, i3: 120}, below ? {i1: Y20 - below} : {}));
  // level, 10 mm right of ring 4 (5 past its face), going right: it would double back
  assert.deepEqual(at(120).findings.map(f => f.via), ['guide-4']);
  assert.deepEqual(at(120, 8).findings.map(f => f.via), ['guide-4']);       // 10 along, 8 below: still beside it
  // 30 mm below: steeper than 45 degrees, it comes up into the ring
  assert.deepEqual(at(120, 30).findings, []);
  assert.deepEqual(at(120, 30).rings.map(g => [g.via, g.passed, g.sense]), [['guide-4', true, 1], ['guide-5', true, 1]]);
  // within half the ring's depth of its centre: under it
  assert.deepEqual(at(112).findings, []);
});

test('the drawings obey routePath: 2D and 3D draw each ring as routePath decided, over a grid of ports', () => {
  const r = rackOf();
  const rings = [-205, -150, -110, 0, 110, 205].map((x, i) => ({via: `guide-${i + 1}`, x}));
  const route = lane => [{item: 'i2', via: 'guide-2'}, {item: 'i2', via: 'guide-4'}, {lane, ru: 20}, {lane, ru: 30}];
  let disagreedUnmarked = 0, n = 0;
  for (const lane of ['left-front', 'right-front']) for (const x of [-230, -160, -150, -147, -140, -120, -110, -100, -60, -10, 0, 10, 50, 120])
    for (const below of [0, 8, 30, 60]) {
      const ctx = ctxOf(rings, {i1: x, i3: lane.startsWith('left') ? -100 : 100}, {i1: Y20 - below});
      const c = cableOf(route(lane));
      const path = R.routePath(r, c, ctx), marks = R.ringMarks(r, c, ctx);
      const decided = path.rings.map(g => [g.passed, g.sense]);
      const centres = R.resolveRoute(r, c, ctx).waypoints.map(w => R.pointOf(r, w, ctx));
      const a = path.points[0], b = path.points[path.points.length - 1];
      // 2D: the front elevation, y down, no z; and the rear pane, mirrored in x as well
      const flat = p => [p.x, -p.y], rear = p => [-p.x, -p.y];
      const two = throughRings([flat(a), ...centres.map(flat), flat(b)], [null, ...R.orientMarks(marks, {y: -1}), null], {lead: 4});
      const back2 = throughRings([rear(a), ...centres.map(rear), rear(b)], [null, ...R.orientMarks(marks, {x: -1, y: -1}), null], {lead: 4});
      // 3D: out of each connector 40 mm first, the rings at their stand-off,
      // and this cable spread 6 mm up at each ring it shares (scene3d's SPREAD)
      const lift = p => ({x: p.x, y: p.y + 6, z: p.z});
      const outA = {x: a.x, y: a.y, z: a.z + 40}, outB = {x: b.x, y: b.y, z: b.z + 40};
      const three = throughRings([outA, ...centres.map(lift), outB], [null, ...marks, null], {lead: 30});
      // each frame draws routePath's decisions, in its own axes; mirrored back to
      // the rack's, its points are the 3D frame's along the run
      for (const [got, sx] of [[two, 1], [back2, -1], [three, 1]]) {
        const drawn = [...got.passes.map(p => [p.index, true, p.sense * sx]), ...got.back.map(p => [p.index, false, p.sense * sx])]
          .sort((u, v) => u[0] - v[0]).map(([, passed, sense]) => [passed, sense]);
        assert.deepEqual(drawn, decided, `port ${x}, ${below} below, ${lane}`);
      }
      const runX = (pts, f) => pts.map(f);
      assert.deepEqual(runX(throughRings([rear(a), ...centres.map(rear), rear(b)], [null, ...R.orientMarks(marks, {x: -1, y: -1}), null]).points, p => -p[0]),
        runX(throughRings([flat(a), ...centres.map(flat), flat(b)], [null, ...R.orientMarks(marks, {y: -1}), null]).points, p => p[0]),
        `rear pane mirrors the front: port ${x}, ${below} below, ${lane}`);
      // drawn from the other end (a cross-face cable's tag side): the same path, reversed
      const pts2 = [flat(a), ...centres.map(flat), flat(b)];
      const fwd = throughRings(pts2, [null, ...marks, null]).points;
      const rev = throughRings([...pts2].reverse(), R.reverseMarks([null, ...marks, null])).points;
      assert.deepEqual(rev, [...fwd].reverse(), `reversed: port ${x}, ${below} below, ${lane}`);
      // routed2d and routePoints3d take the same marks
      assert.ok(!/NaN/.test(routed2d([flat(a), ...centres.map(flat), flat(b)], 4, [null, ...marks, null])));
      // without the decisions, the 3D frame would not always agree with it
      const free = throughRings([outA, ...centres.map(lift), outB], [null, ...marks.map(m => m && {run: m.run, depth: m.depth}), null]);
      const undecided = [...free.passes.map(p => [p.index, true, p.sense]), ...free.back.map(p => [p.index, false, p.sense])]
        .sort((u, v) => u[0] - v[0]).map(([, passed, sense]) => [passed, sense]);
      if (JSON.stringify(undecided) !== JSON.stringify(decided)) disagreedUnmarked++;
      n++;
    }
  assert.ok(n > 100);
  assert.ok(disagreedUnmarked > 0, 'the grid reaches cases where a frame left to itself decides otherwise');
});

test('ringMarks: with no port found there is no decision, only the ring', () => {
  const r = rackOf();
  const ctx = ctxOf([{via: 'guide-1', x: -150}], {i3: -100});
  const c = cableOf([{item: 'i2', via: 'guide-1'}, {lane: 'left-front', ru: 20}]);
  assert.deepEqual(R.ringMarks(r, c, ctx), [{run: 'x', depth: R.RING_DEPTH}, null]);
  const ok = ctxOf([{via: 'guide-1', x: -150}], {i1: -100, i3: -100});
  assert.deepEqual(R.ringMarks(r, c, ok), [{run: 'x', depth: R.RING_DEPTH, sense: -1, back: false}, null]);
});

test('the automatic route takes only rings that run along the tray', () => {
  const r = rackOf();
  const rings = [{via: 'guide-1', x: -205}, {via: 'up', x: -150, run: 'y'}, {via: 'guide-2', x: -110}];
  const ctx = ctxOf(rings, {i1: -100, i3: -100});
  assert.deepEqual(R.autoRoute(r, cableOf(), ctx).filter(w => w.via).map(w => w.via), ['guide-2', 'guide-1']);
});

test('the automatic route never doubles back at either end, a lacer on each device', () => {
  // sw at U20 and pp at U30, each with a lacer: B's rings are met in reverse, from the lane to its port
  let r = add(add(add(add(M.newRack(), 'sw', 20), 'lacer', 20, {on: 'i1', unit: 1}), 'pp', 30), 'lacer', 30, {on: 'i3', unit: 1});
  const rings = [-205, -110, 0, 110, 205].map((x, i) => ({kind: 'ring', face: 'front', via: `guide-${i + 1}`, x}));
  for (const xa of [-230, -112, -3, 0, 3, 108, 230]) for (const xb of [-230, -150, -112, -3, 0, 3, 100, 112, 230]) {
    const ctx = {chassisOf, guidesOf: id => (id === 'i2' || id === 'i4' ? rings : []),
      portX: end => (end.item === 'i1' ? xa : xb), portY: () => null};
    const c = {...cableOf(), route: []};
    const route = R.autoRoute(r, c, ctx);
    assert.ok(route.some(w => w.item === 'i4') || xb === 230 || xb === -230, `B's lacer used: ${xa} ${xb}`);
    assert.deepEqual(R.routePath(r, c, ctx).findings, [], `ports at ${xa} and ${xb}`);
  }
});

test('capacity, like fill, does not count a cable at a manager it only doubles back from', () => {
  SIZES.lacer.capacity = {count: 1, basis: 'test'};
  try {
    const ring = [{via: 'guide-1', x: -150}];
    const ctx = ctxOf(ring, {i1: -40, i3: -100});
    const through = cableOf([{item: 'i2', via: 'guide-1'}, {lane: 'left-front', ru: 20}, {lane: 'left-front', ru: 30}]);
    // from the port at -40 to the ring at -150 and back to the right-hand lane: a double-back
    const back = {...cableOf([{item: 'i2', via: 'guide-1'}, {lane: 'right-front', ru: 20}, {lane: 'right-front', ru: 30}]), id: 'c2'};
    const two = {...rackOf(), cables: [through, {...through, id: 'c2'}]};
    assert.deepEqual(R.capacityOver(two, ctx), [{item: 'i2', count: 2, capacity: 1}]);
    const mixed = {...rackOf(), cables: [through, back]};
    assert.deepEqual(R.routePath(mixed, back, ctx).findings.map(f => f.via), ['guide-1']);
    assert.deepEqual(R.capacityOver(mixed, ctx), []);
  } finally { delete SIZES.lacer.capacity; }
});

test('a mirrored rear pane draws the ring as decided, not hooked: orientMarks turns x', () => {
  // a rear ring: port at x -100, ring at -150, lane at the left; the rack's sense is -1
  const ring = {run: 'x', depth: 10, sense: -1, back: false};
  const lane = -(OPENING / 2 + RAIL_W + R.LANE_GAP / 2);
  // the rear pane is seen mirrored: x' = -x
  const pts = [[100, 0], [150, 0], [-lane, 0]];
  const drawn = throughRings(pts, [null, ...R.orientMarks([ring], {x: -1, y: -1}), null]).points;
  assert.deepEqual(drawn.map(p => p[0]), [100, 145, 155, -lane]);
  const xs = drawn.map(p => p[0]);
  assert.ok(xs.every((v, k) => k === 0 || v > xs[k - 1]), `no hook: ${xs.join(' ')}`);
  // unturned, the rack's sense in the mirrored pane is the hook #930 removes
  assert.deepEqual(throughRings(pts, [null, ring, null]).points.map(p => p[0]), [100, 155, 145, -lane]);
  // a doubled-back ring's face is on the side both neighbours are on, in the pane too
  const back = {run: 'x', depth: 10, sense: -1, back: true};    // rack: face at -145, the port's side
  const face = throughRings([[100, 0], [150, 0], [90, 0]], [null, ...R.orientMarks([back], {x: -1}), null]).points[1];
  assert.deepEqual(face, [145, 0]);
});

test('a ring that runs up the rack, in an elevation whose y is down: orientMarks turns y', () => {
  // a y-run ring (as the CMH-6DR1U end ring) on the lacer at x -150; the port 30 mm below it, the lane level with it
  const r = rackOf();
  const ctx = ctxOf([{via: 'end', x: -150, run: 'y'}], {i1: -150, i3: -100}, {i1: Y20 - 30});
  const c = cableOf([{item: 'i2', via: 'end'}, {lane: 'left-front', ru: 20}, {lane: 'left-front', ru: 30}]);
  const path = R.routePath(r, c, ctx), marks = R.ringMarks(r, c, ctx);
  assert.deepEqual(path.rings.map(g => [g.run, g.passed, g.sense]), [['y', true, 1]]);   // upward
  const [a, entry, exit] = path.points;
  assert.deepEqual([entry.y, exit.y], [Y20 - R.RING_DEPTH / 2, Y20 + R.RING_DEPTH / 2]);
  // the elevation: y down
  const centres = R.resolveRoute(r, c, ctx).waypoints.map(w => R.pointOf(r, w, ctx));
  const flat = p => [p.x, -p.y];
  const pts = [flat(a), ...centres.map(flat), flat(path.points[path.points.length - 1])];
  const drawn = throughRings(pts, [null, ...R.orientMarks(marks, {y: -1}), null]).points;
  assert.deepEqual(drawn.slice(1, 3).map(p => p[1]), [-entry.y, -exit.y]);
  // unturned it would enter from above and hook back down
  const hooked = throughRings(pts, [null, ...marks, null]).points;
  assert.deepEqual(hooked.slice(1, 3).map(p => p[1]), [-exit.y, -entry.y]);
  // and the 3D scene, in the rack's own axes, takes the marks unchanged
  assert.deepEqual(R.orientMarks(marks, {}), marks);
});
