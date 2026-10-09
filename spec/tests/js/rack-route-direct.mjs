// A patch along one manager, and the gutter chosen from both ends (#949,
// docs/cable-lay-design.md section 4.1, "Local patches" and "Opposite ways";
// pulled forward from step 5 of section 10). Every route and length here was
// measured on these fixtures and is asserted exactly, so a rule that found
// nothing cannot pass.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as R from '../../../kit/rack/route.js';
import * as M from '../../../kit/rack/model.js';
import * as Q from '../../../kit/rack/queries.js';
import * as S from '../../../kit/rack/solids.js';
import * as F from './route-direct-fixture.mjs';

const ring = n => ({item: 'i4', via: `guide-${n}`});
const mm = l => Math.round(l.measured * 10000) / 10;

// Per cable of the owner's rack: the rings it runs through, its measured
// length in mm (the path plus 0.15 m at each end) and its stock length in m.
// Before this change every one ran out to the right lane and back, measuring
// 0.67 to 1.04 m (stock 1 or 1.5 m). c1, c2 and c5 to c8 have no ring between
// their ports and take the nearest ring they pass: c1-c7 ring 4, and c8 ring
// 5, which holds it (it reaches just past its panel port into the ring).
const OWNER = {
  c1: [[4], 449.2, 0.5], c2: [[4], 433.7, 0.5], c3: [[4], 438.3, 0.5], c4: [[4], 432.8, 0.5],
  c5: [[4], 453.5, 0.5], c6: [[4], 452.2, 0.5], c7: [[4], 479.3, 0.5], c8: [[5], 447.4, 0.5],
  c9: [[3], 495.2, 0.5], c10: [[3], 494.0, 0.5], c11: [[3], 494.3, 0.5], c12: [[3], 495.8, 0.5],
  c13: [[4], 477.4, 0.5], c14: [[4], 478.4, 0.5], c15: [[4], 463.1, 0.5], c16: [[4], 464.9, 0.5],
};

test('the owner\'s rack: each cord runs along the lacer through a ring, with no lane', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  const got = Object.fromEntries(r.cables.map(c => {
    const route = R.autoRoute(r, c, ctx), l = R.routedLength(r, c, ctx);
    return [c.id, [route, mm(l), l.value]];
  }));
  const want = Object.fromEntries(Object.entries(OWNER).map(([id, [rings, len, stock]]) => [id, [rings.map(ring), len, stock]]));
  assert.deepEqual(got, want);
  // nothing reaches a gutter
  assert.equal(r.cables.flatMap(c => R.autoRoute(r, c, ctx)).filter(w => w.lane).length, 0);
  // no route is direct, and every one fits the 0.5 m stock
  assert.equal(r.cables.filter(c => !R.autoRoute(r, c, ctx).length).length, 0);
  assert.ok(r.cables.every(c => R.routedLength(r, c, ctx).value === 0.5));
  // every ring taken is passed; only c8's holds a cord that does not turn in it
  for (const c of r.cables) {
    const p = R.routePath(r, c, ctx);
    assert.equal(p.rings.length, OWNER[c.id][0].length, c.id);
    for (const g of p.rings) assert.deepEqual([g.passed, g.held === true], [true, c.id === 'c8'], `${c.id} ${g.via}`);
  }
});

test('the owner\'s rack: no ring is entered and left by one face, and no route crosses a body', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  assert.deepEqual(R.ringFindings(r, ctx), []);
  assert.deepEqual(R.bodyFindings(r, ctx), []);
  for (const c of r.cables) {
    const p = R.routePath(r, c, ctx);
    assert.deepEqual(p.crossings, [], c.id);
    assert.deepEqual(p.detours, [], c.id);
  }
  // the solids are there to cross: the three envelopes and the lacer's fifteen plates
  const s = S.solidsOf(r, ctx);
  assert.equal(s.length, 3 + 15);
  assert.deepEqual(s.filter(x => x.part === 'envelope').map(x => x.item), ['i1', 'i2', 'i3']);
});

test('c8: no ring between its ports; ring 5, just past its panel port, holds it with no finding; a hook still warns', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  const c8 = r.cables.find(c => c.id === 'c8');
  // ports at 147.3 (LEAF-A port 56, lower row) and 195.81 (bay 4 lc6), the
  // middle 171.6: ring 5 (205.8) is 34.2 from it, ring 4 (110.4) 61.2. Ring
  // 5's near face (202.4) is 6.59 past lc6, within its depth (6.8) and the
  // OM4 cord's 3 mm: the cord reaches into it to be held, and passes
  assert.deepEqual(R.autoRoute(r, c8, ctx), [ring(5)]);
  assert.deepEqual(R.ringMarks(r, c8, ctx), [{run: 'x', depth: 6.8, sense: 1, back: false}]);
  assert.deepEqual(R.ringFindings({...r, cables: [c8]}, ctx), []);
  const [g] = R.routePath(r, c8, ctx).rings;
  assert.deepEqual([g.via, g.passed, g.held], ['guide-5', true, true]);
  // a hand route the same way gets the same answer
  assert.deepEqual(R.ringFindings({...r, cables: [{...c8, route: [ring(5)], routeEdited: true}]}, ctx), []);
  // a real hook still warns: through ring 4, 33.5 mm behind LEAF-A port 56
  // past its near face, the cord goes well past and comes back
  assert.deepEqual(R.ringFindings({...r, cables: [{...c8, route: [ring(4)], routeEdited: true}]}, ctx)
    .map(f => [f.cable, f.via]), [['c8', 'guide-4']]);
  // c7, from the upper row at the same x to lc5 (182.86): ring 5 is nearer
  // the middle (165.1), but its near face is 19.5 past lc5, a hook; ring 4
  // passes, and is taken
  const c7 = r.cables.find(c => c.id === 'c7');
  assert.deepEqual(R.autoRoute(r, c7, ctx), [ring(4)]);
  assert.deepEqual(R.ringFindings({...r, cables: [{...c7, route: [ring(5)], routeEdited: true}]}, ctx).map(f => f.via), ['guide-5']);
  // either side of the bound, on the owner's rack: lc6 moved so ring 5's near
  // face is 9.8 past it (6.8 + 3) is held; 9.9 past is a hook
  for (const [x, want] of [[202.4 - 9.8, []], [202.4 - 9.9, ['guide-5']]]) {
    const moved = {...ctx, portX: e => (e.item === 'i2' && e.path === c8.b.path ? x : ctx.portX(e))};
    const hand = {...c8, route: [ring(5)], routeEdited: true};
    assert.deepEqual(R.ringFindings({...r, cables: [hand]}, moved).map(f => f.via), want, `lc6 at ${x}`);
  }
});

test('the site-facing outputs: ring marks, inspect and the route text read the route along the lacer', async () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  const c13 = r.cables.find(c => c.id === 'c13');
  // LEAF-B port 53 (x 128.3) to panel bay 3 lc1 (x 21.91): through ring 4 leftward
  assert.deepEqual(R.ringMarks(r, c13, ctx), [{run: 'x', depth: 6.8, sense: -1, back: false}]);
  assert.deepEqual(R.ringMarks(r, r.cables.find(c => c.id === 'c3'), ctx), [{run: 'x', depth: 6.8, sense: 1, back: false}]);
  const info = await Q.inspect(r, 'c13', {chassisOf: F.chassisOf, route: ctx});
  assert.equal(info.route.text, 'CM-01 ring 4');
  assert.deepEqual(info.route.waypoints, [ring(4)]);
  assert.deepEqual(info.routed, {metres: 0.48, stock: 0.5});
  assert.equal(info.route.rings.length, 1);
  assert.equal(info.route.rings[0].passed, true);
  assert.equal(info.route.crosses, undefined);
  // and the length a page keeps current is this one
  const kept = R.withRoutedLengths(r, ctx);
  assert.deepEqual(kept.cables.find(c => c.id === 'c13').length, {value: 0.5, unit: 'm', source: 'routed', measured: 0.48});
});

// ── a cable whose ends use different managers ─────────────────────────────
// The owner's rack with a second panel far below (U20, i5), no manager on it
// or beside it: a cable from LEAF-B leaves through the lacer, the other end
// through nothing, so the route takes a gutter.
function withFarPanel(bx) {
  const r0 = F.rack();
  const r = M.withItem(r0, {ref: 'fhd-1ufce', cfg: 'populated', ru: 20, label: 'PP-02'}).rack;
  const c = {id: 'c17', a: {item: 'i3', path: 'port-49', view: 'front'}, b: {item: 'i5', path: 'far', view: 'front'},
    media: 'om4', route: []};
  const base = F.ctxOf(r);
  const ctx = {...base, portX: e => (e.item === 'i5' ? bx : base.portX(e)),
    portY: e => (e.item === 'i5' ? 19.5 * 44.45 : base.portY(e))};
  return {r: {...r, cables: [c]}, c, ctx};
}

test('ends on two managers still take the lane; on opposite sides, the shorter side, chosen from both ends', () => {
  // a at LEAF-B port 49 (x 88.3, right of centre), b at x -150 (left)
  const {r, c, ctx} = withFarPanel(-150);
  const route = R.autoRoute(r, c, ctx);
  // the left: out through rings 3, 2 and 1 to the left lane, down to U20;
  // end a's side, the right, was the rule, and measures longer
  const left = [ring(3), ring(2), ring(1), {lane: 'left-front', ru: 40}, {lane: 'left-front', ru: 20}];
  const right = [ring(4), ring(5), {lane: 'right-front', ru: 40}, {lane: 'right-front', ru: 20}];
  assert.deepEqual(route, left);
  const len = rt => mm(R.routedLength(r, {...c, route: rt, routeEdited: true}, ctx));
  assert.deepEqual([len(left), len(right)], [1781.4, 1932.6]);
  // written the other way round, the same side
  const back = {...c, a: c.b, b: c.a};
  assert.deepEqual(R.autoRoute(r, back, ctx), left.toReversed());
});

test('ends on two managers, both ports on one side: that side, without measuring', () => {
  const {r, c, ctx} = withFarPanel(150);
  assert.deepEqual(R.autoRoute(r, c, ctx), [ring(4), ring(5), {lane: 'right-front', ru: 40}, {lane: 'right-front', ru: 20}]);
  // both on the left: the left, though end a's port is the one nearer the right
  const l = withFarPanel(-150);
  const ctx2 = {...l.ctx, portX: e => (e.item === 'i3' ? -10 : l.ctx.portX(e))};
  assert.equal(R.autoRoute(l.r, l.c, ctx2).find(w => w.lane).lane, 'left-front');
});

test('a port not found keeps end a\'s side and does not throw', () => {
  const {r, c, ctx} = withFarPanel(-150);
  const blind = {...ctx, portX: e => (e.item === 'i5' ? null : ctx.portX(e))};
  // the far port defaults to the centre (left), a is on the right: opposite
  // sides, but nothing can be measured, so end a's side
  assert.equal(R.autoRoute(r, c, blind).find(w => w.lane).lane, 'right-front');
});
