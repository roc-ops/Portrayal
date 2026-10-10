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
// Before kit 0.12.0 every one ran out to the right lane and back, measuring
// 0.67 to 1.04 m (stock 1 or 1.5 m). c1, c2 and c5 to c8 have no ring between
// their ports and take the nearest ring they pass: c1-c7 ring 4, and c8 ring
// 5, just past its panel port (it held the cord, reaching just into it, until
// the cord rested on the ring's sill, below; now it passes it).
// THE PLUG'S REACH (#960, kit 0.13.0): each path now starts and ends 27.6 mm
// out of the face, where an OM4 cord leaves its LC plug and boot. Measured
// from the port faces they were 0.433-0.496 m, all 0.5 m stock; seven of
// them (c7, and c9-c14 from the lower leaf) now passed the 0.5 m break.
// RESTING (#949 step 3): each cord now lies through its ring on the ring's
// sill (5.6 mm above the tray floor, which is 3.0 above the bottom of the
// unit), at the side of the opening nearer the rail (72.2 mm out of the
// rail's 110, not the coarse 55 of half the lacer's depth), and each free
// span hangs by its drape. The upper leaf's cords grow 34 to 42 mm, from
// 0.444-0.506 m; the lower leaf's rise from below to a ring now lower and
// further out, so each is taken round the tray's front edge (one detour) and
// grows 125 to 144 mm, from 0.486-0.524 m. Thirteen now pass the 0.5 m break.
// THE RING IS SOLID (#968): each cord comes to its ring along the run from an
// approach point 6.5 mm (its radius and CLEAR) past the band, at the sill,
// and leaves to another past the far face, so no stretch of it runs inside
// the tube's radius of a leg, the bar or the seat. The upper leaf's cords
// grow 10 to 38 mm: those whose ring is past their port along the run (c1,
// c2, c5-c7) went down into it through its rear leg, and now go over the
// ring and down its far side to the approach point; c3, c4 and c8, which
// come down on the near side, add the approach only. The lower leaf's grow
// 2 to 6 mm: the detour round the tray's front edge ends at the approach
// point, not the ring's face. c2 and c3 pass the 0.5 m break (0.487 -> 0.525,
// 0.493 -> 0.504); fifteen of sixteen now do.
const OWNER = {
  c1: [[4], 534.3, 1], c2: [[4], 525.1, 1], c3: [[4], 503.9, 1], c4: [[4], 496, 0.5],
  c5: [[4], 538.8, 1], c6: [[4], 544.1, 1], c7: [[4], 568.8, 1], c8: [[5], 514, 1],
  c9: [[3], 664.3, 1], c10: [[3], 663.1, 1], c11: [[3], 665, 1], c12: [[3], 665.8, 1],
  c13: [[4], 631.9, 1], c14: [[4], 638.6, 1], c15: [[4], 620.7, 1], c16: [[4], 626.4, 1],
};
const LOWER = ['c9', 'c10', 'c11', 'c12', 'c13', 'c14', 'c15', 'c16'];

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
  // no route is direct, and fifteen pass the 0.5 m stock break (thirteen
  // before #968; c2 and c3 joined them)
  assert.equal(r.cables.filter(c => !R.autoRoute(r, c, ctx).length).length, 0);
  assert.deepEqual(r.cables.filter(c => R.routedLength(r, c, ctx).value > 0.5).map(c => c.id),
    ['c1', 'c2', 'c3', 'c5', 'c6', 'c7', 'c8', ...LOWER]);
  // every ring taken is passed. None now holds a cord that does not turn in
  // it: c8's panel port stands 12.1 mm above ring 5's sill and 10 mm short
  // of its centre, steeper than 45 degrees, so the cord comes down into the
  // ring rather than reaching along into it (route-path.js)
  for (const c of r.cables) {
    const p = R.routePath(r, c, ctx);
    assert.equal(p.rings.length, OWNER[c.id][0].length, c.id);
    for (const g of p.rings) assert.deepEqual([g.passed, g.held === true], [true, false], `${c.id} ${g.via}`);
  }
});

test('the owner\'s rack: no ring is entered and left by one face, and no route crosses a body', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  assert.deepEqual(R.ringFindings(r, ctx), []);
  assert.deepEqual(R.bodyFindings(r, ctx), []);
  for (const c of r.cables) {
    const p = R.routePath(r, c, ctx);
    assert.deepEqual(p.crossings, [], c.id);
    // the upper leaf's cords come down onto the tray; those whose ring stands
    // past their port along the run go over the ring first (#968), 6.5 mm
    // over its top (1822, the top of U41, 44 above its floor), and come down
    // its far side to the approach point; the lower leaf's go round the tray's
    // front edge first, from their reach point to the approach point
    const ap = p.points.find(q => q.at === 'approach');
    assert.ok(p.detours.length <= 1, c.id);
    if (p.detours.length) assert.deepEqual(p.detours[0].between[0], {end: 'a'}, c.id);
    if (!LOWER.includes(c.id)) {
      assert.equal(p.detours.length, ['c1', 'c2', 'c5', 'c6', 'c7'].includes(c.id) ? 1 : 0, c.id);
      for (const d of p.detours) assert.deepEqual(d.points.map(q => [q.x, q.y, q.z]), [[ap.x, 1822 + 1.5 + 6.5, ap.z]], c.id);
      continue;
    }
    assert.equal(p.detours.length, 1, c.id);
    assert.ok(p.detours[0].points.every(q => q.z > 110), `${c.id}: in front of the tray's front edge`);
    // and it ends straight in front of the approach point, not the ring
    assert.equal(p.detours[0].points.at(-1).x, ap.x, c.id);
  }
  // the solids are there to cross: the three envelopes, the lacer's fifteen
  // plates and its five rings, five parts each (#968)
  const s = S.solidsOf(r, ctx);
  assert.equal(s.length, 3 + 15 + 25);
  assert.deepEqual(s.filter(x => x.part === 'envelope').map(x => x.item), ['i1', 'i2', 'i3']);
});

test('c8: no ring between its ports; ring 5, just past its panel port, passes it with no finding; a hook still warns', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  const c8 = r.cables.find(c => c.id === 'c8');
  // ports at 147.3 (LEAF-A port 56, lower row) and 195.81 (bay 4 lc6), the
  // middle 171.6: ring 5 (205.8) is 34.2 from it, ring 4 (110.4) 61.2. Ring
  // 5's near face (202.4) is 6.59 past lc6, within its depth (6.8) and the
  // OM4 cord's 3 mm: the cord reaches into it to be held, and passes
  assert.deepEqual(R.autoRoute(r, c8, ctx), [ring(5)]);
  assert.deepEqual(R.ringMarks(r, c8, ctx), [{run: 'x', depth: 6.8, sense: 1, back: false}]);
  assert.deepEqual(R.ringFindings({...r, cables: [c8]}, ctx), []);
  // passed; not `held` since #949 step 3: the cord rests on ring 5's sill,
  // 12.1 mm below lc6's reach point, which is then steeper than 45 degrees
  // off the run and comes down into the ring (the bound below is level)
  const [g] = R.routePath(r, c8, ctx).rings;
  assert.deepEqual([g.via, g.passed, g.held], ['guide-5', true, undefined]);
  // a hand route the same way gets the same answer
  assert.deepEqual(R.ringFindings({...r, cables: [{...c8, route: [ring(5)], routeEdited: true}]}, ctx), []);
  // a real hook still warns: through ring 3, 144 mm behind LEAF-A port 56
  // past its near face, the cord goes well past and comes back. (Ring 4,
  // 33.5 mm behind, warned until the cord rested on its sill, 43.5 mm below
  // that port: from there the port is steeper than 45 degrees off the run.)
  assert.deepEqual(R.ringFindings({...r, cables: [{...c8, route: [ring(3)], routeEdited: true}]}, ctx)
    .map(f => [f.cable, f.via]), [['c8', 'guide-3']]);
  // c7, from the upper row at the same x to lc5 (182.86): ring 4 passes, and
  // is taken; ring 2, far behind both ports, is a hook
  const c7 = r.cables.find(c => c.id === 'c7');
  assert.deepEqual(R.autoRoute(r, c7, ctx), [ring(4)]);
  assert.deepEqual(R.ringFindings({...r, cables: [{...c7, route: [ring(2)], routeEdited: true}]}, ctx).map(f => f.via), ['guide-2']);
  // either side of the bound, on the owner's rack: lc6 moved so ring 5's near
  // face is 9.8 past it (6.8 + 3) is held; 9.9 past is a hook
  for (const [x, want] of [[202.4 - 9.8, []], [202.4 - 9.9, ['guide-5']]]) {
    const moved = {...ctx, portX: e => (e.item === 'i2' && e.path === c8.b.path ? x : ctx.portX(e))};
    const hand = {...c8, route: [ring(5)], routeEdited: true};
    assert.deepEqual(R.ringFindings({...r, cables: [hand]}, moved).map(f => f.via), want, `lc6 at ${x}`);
  }
});

test('a cross-connect on the panel with no ring it can pass takes the nearest anyway, and the finding says so', () => {
  // bay 3 lc2 (34.86) to lc5 (73.89), both on PP-01 behind the lacer: no ring
  // between (ring 3 at 0, ring 4 at 110.4), the middle 54.4 is 54.4 from ring
  // 3 and 56.0 from ring 4. Level with both ports, neither is passed, and
  // neither is held: ring 3's near face is 31.5 past lc2. Never direct, so
  // ring 3, and the automatic route carries a doubles-back finding.
  const r0 = F.rack();
  const x = {id: 'x1', a: {item: 'i2', path: 'bay-3/module/lc2', view: 'front'}, b: {item: 'i2', path: 'bay-3/module/lc5', view: 'front'},
    media: 'om4', route: []};
  const r = {...r0, cables: [x]}, ctx = F.ctxOf(r);
  assert.deepEqual(R.autoRoute(r, x, ctx), [ring(3)]);
  assert.deepEqual(R.ringFindings(r, ctx).map(f => [f.cable, f.via]), [['x1', 'guide-3']]);
  const [g] = R.routePath(r, x, ctx).rings;
  assert.deepEqual([g.passed, g.held], [false, undefined]);
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
  assert.deepEqual(info.routed, {metres: 0.63, stock: 1});
  assert.equal(info.route.rings.length, 1);
  assert.equal(info.route.rings[0].passed, true);
  assert.equal(info.route.crosses, undefined);
  // and the length a page keeps current is this one
  const kept = R.withRoutedLengths(r, ctx);
  assert.deepEqual(kept.cables.find(c => c.id === 'c13').length, {value: 1, unit: 'm', source: 'routed', measured: 0.63});
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
  // (1781.4 and 1932.6 from the port faces, before the plug's reach, #960;
  // 1828.6 and 1970 before the cord rested, #949 step 3: it now goes round
  // the tray's front edge into its first ring, lies on the sill of each ring
  // and on the floor between them, and hangs from the lane to the far port;
  // 1967.2 and 2171.1 before each ring was solid, #968: it now comes to and
  // leaves each ring from an approach point past its band, and its detour
  // round the tray's front edge ends there, not at the first ring's face)
  assert.deepEqual([len(left), len(right)], [1986.9, 2193.8]);
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
