// A lead enters the first ring along its way that it has room to turn into
// (#1026, docs/cable-lay-design.md section 3.5): the choice is by room, not
// by distance. The rack is of the shape the issue was measured on
// (ring-room-shape.mjs): 2U switches, each with an FHD-CMP5DR lacer hosted
// on it, a vertical manager at each front upright, 400G AOC fabric links
// with a 64.8 mm plug and a 30 mm bend radius. Every count was measured on
// these racks and is asserted exactly, and each check asserts it looked at
// something.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as R from '../../../kit/rack/route.js';
import * as S from '../../../kit/rack/solids.js';
import {cornersOf} from '../../../kit/rack/route-path.js';
import {shape, measure, portOf} from './ring-room-shape.mjs';

const r1 = v => Math.round(v * 10) / 10;
const ring = (item, n) => ({item, via: `guide-${n}`});
// the rings a route takes on one manager, in order
const ringsOn = (route, item) => route.filter(w => w.item === item).map(w => Number(w.via.slice(6)));
const cableOf = (rack, id) => rack.cables.find(c => c.id === id);

// ── the shape ────────────────────────────────────────────────────────────

test('the shape: a lacer on the top unit stands its rings 73.7 mm out, their sill 7 and 20 mm under the two rows of ports it serves', () => {
  const {rack, ctx} = shape({count: 43});
  assert.equal(rack.cables.length, 43);
  // EDGE-0 at U35 and U36, its lacer m3 on U36
  const [t] = S.traysOf(rack, ctx).filter(x => x.item === 'm3');
  const sill = t.rings[0].box.y0, rows = [ctx.portY({item: 'i3', path: 'fab-0'}), ctx.portY({item: 'i3', path: 'fab-1'})];
  assert.deepEqual(rows.map(y => r1(y - sill)), [19.8, 6.8]);
  // a cable on its own lies at the rail side of the opening, its radius in
  assert.equal(t.rings[0].box.z0 + 1.5, 73.7);
  assert.equal(R.PLUG_REACH.aoc, 64.8);
  // so an AOC's plug ends 8.9 mm short of the line it must turn onto
  assert.equal(r1(73.7 - R.PLUG_REACH.aoc), 8.9);
});

// ── the rule ─────────────────────────────────────────────────────────────

test('a ring too close to turn into is passed over, and the next ring with room is taken', () => {
  const {rack, ctx} = shape({count: 43});
  // c9 leaves EDGE-0's fab-8, 6.3 mm short of ring 2's near face: the lead
  // would turn twice on 20 mm. Ring 1 stands 92 mm further along
  const c9 = cableOf(rack, 'c9');
  assert.equal(r1(portOf('edge', 'fab-8')[0]), -104.7);
  const route = R.autoRoute(rack, c9, ctx);
  assert.deepEqual(ringsOn(route, 'm3'), [1]);
  assert.deepEqual(route[0], ring('m3', 1));
  // and it has its room there: no corner between that port and ring 1 is short
  const path = R.routePath(rack, c9, ctx);
  assert.deepEqual(path.bends.filter(f => f.between.some(w => w.end === 'a')), []);
  assert.deepEqual(path.crossings, []);
  // through ring 2 by hand, as the route was before: the two turns share
  // 20.8 mm and have room for an 11.2 mm bend, one finding
  const hand = {...c9, route: [ring('m3', 2), ...route], routeEdited: true};
  const was = R.routePath({...rack, cables: [hand]}, hand, ctx).bends.filter(f => f.between.some(w => w.end === 'a'));
  assert.deepEqual(was.map(f => [f.point, f.room_mm, f.apart_mm, f.turns.map(t => t.point)]), [['reach', 11.2, 20.8, ['reach', 'approach']]]);
});

test('a ring with room is taken though it is the nearest: the rule passes over nothing it need not', () => {
  const {rack, ctx} = shape({count: 43});
  let taken = 0, passed = 0;
  for (const c of rack.cables) {
    const route = R.autoRoute(rack, c, ctx);
    for (const [e, m] of [[c.a, 'm3']]) {
      if (e.item !== 'i3' || !/^fab-/.test(e.path)) continue;
      const x = ctx.portX(e), side = x <= 0 ? -1 : 1;
      // the rings on its way out, nearest first, as `through` lists them
      const out = [-205.8, -110.4, 0, 110.4, 205.8].map((cx, i) => [i + 1, cx]).filter(([, cx]) => (side < 0 ? cx <= x + 3.4 : cx >= x - 3.4))
        .sort((p, q) => Math.abs(p[1] - x) - Math.abs(q[1] - x));
      const got = ringsOn(route, m);
      if (!got.length || route.find(w => w.lane).lane.startsWith(side < 0 ? 'right' : 'left')) continue;
      // what it takes is the rings on its way from some ring outward, in order
      const from = out.findIndex(([n]) => n === got[0]);
      assert.ok(from >= 0, c.id);
      assert.deepEqual(got, out.slice(from).map(([n]) => n), c.id);
      if (from === 0) taken++; else passed++;
    }
  }
  // of EDGE-0's fabric leads that take a ring on the side their port is on,
  // most take the nearest
  assert.deepEqual([taken, passed], [24, 4]);
});

test('where no ring leaves room the nearest stands, and the finding says the manager is too close and what would help', () => {
  const {rack, ctx, nameOf} = shape({count: 43});
  // c1 leaves fab-0, 16.8 mm short of ring 1's near face, and ring 1 is the
  // last ring on its way
  const c1 = cableOf(rack, 'c1');
  assert.deepEqual(ringsOn(R.autoRoute(rack, c1, ctx), 'm3'), [1]);
  const found = R.bendFindingsOf(rack, c1, ctx, nameOf).filter(f => f.between.some(w => w.end === 'a'));
  assert.equal(found.length, 1);
  const [f] = found;
  assert.deepEqual(f.tooClose, {manager: 'm3', device: 'i3'});
  // the sentence is the bend and no more; what would help is a field of its own
  assert.equal(f.text, 'c1 turns twice within 22.8 mm between its port on EDGE-0 and Lacer EDGE-0 ring 1 (67.1 and 63.2 degrees), '
    + 'with room for a 17.9 mm bend; the cable (aoc) needs 30 mm, 12.1 mm short.');
  assert.equal(f.advice, 'Lacer EDGE-0 stands too close to the port of c1 on EDGE-0 for the cable to turn into any ring on its way: '
    + 'set EDGE-0 back from the rail, mount the manager on another unit of EDGE-0, or leave EDGE-0 without a manager.');
  assert.ok(f.text.length < 200 && !/too close/.test(f.text));
  // rack-wide the findings are the same ones
  assert.deepEqual(R.bendFindings(rack, ctx, nameOf).filter(f => f.cable === 'c1').map(f => f.text), R.bendFindingsOf(rack, c1, ctx, nameOf).map(f => f.text));
  // the path's own `bends` are as they were: the sentence is the finding's
  assert.ok(R.routePath(rack, c1, ctx).bends.every(f => !('tooClose' in f)));
  // a finding that is not a lead's says nothing of the manager, and a cable
  // with no finding has none to say it in
  const all = R.bendFindings(rack, ctx, nameOf);
  assert.ok(all.some(f => f.tooClose) && all.every(f => !f.tooClose || f.between.some(w => w.end)));
});

test('the advice fits the device: one of a single unit has no other unit to mount the manager on', () => {
  const {rack, ctx, nameOf} = shape({count: 43});
  const c1 = cableOf(rack, 'c1');
  // the same rack with EDGE-0 a device of one unit
  const one = {...ctx, chassisOf: ref => (ref === 'edge' ? {...ctx.chassisOf(ref), ru: 1, h: 43.6} : ctx.chassisOf(ref)),
    portY: e => (e.item === 'i3' ? 34 * 44.45 + 24 : ctx.portY(e))};
  const flat = {...rack, items: rack.items.map(i => (i.id === 'm3' ? {...i, ru: 35, unit: 1} : i))};
  const f1 = R.bendFindingsOf(flat, c1, one, nameOf).find(f => f.tooClose);
  assert.ok(f1, 'the lead is still too close');
  assert.ok(f1.advice.endsWith('set EDGE-0 back from the rail or leave EDGE-0 without a manager.'), f1.advice);
});

test('set back 50 mm, the same leads have room: the rule reads where the device and the manager stand', () => {
  const far = shape({count: 43, setback: 50});
  const c1 = cableOf(far.rack, 'c1'), c9 = cableOf(far.rack, 'c9');
  assert.deepEqual(R.bendFindingsOf(far.rack, c1, far.ctx, far.nameOf), []);
  // and c9's plug now ends 59 mm behind the rings' line: ring 2 has room, and is taken
  assert.deepEqual(ringsOn(R.autoRoute(far.rack, c9, far.ctx), 'm3'), [2, 1]);
  assert.deepEqual(R.bendFindingsOf(far.rack, c9, far.ctx, far.nameOf), []);
});

test('a hand route is never overridden: a ring it names is gone through, room or none, and the finding gives no advice', () => {
  const {rack, ctx, nameOf} = shape({count: 43});
  const c9 = cableOf(rack, 'c9'), auto = R.autoRoute(rack, c9, ctx);
  const hand = {...c9, route: [ring('m3', 2), ...auto], routeEdited: true}, r = {...rack, cables: [hand]};
  assert.deepEqual(R.resolveRoute(r, hand, ctx).waypoints, hand.route);
  const path = R.routePath(r, hand, ctx);
  assert.deepEqual(path.rings.slice(0, 2).map(g => [g.via, g.passed]), [['guide-2', true], ['guide-1', true]]);
  const found = R.bendFindingsOf(r, hand, ctx, nameOf);
  assert.ok(found.length >= 1);
  assert.ok(found.every(f => !f.tooClose && !('advice' in f)));
});

test('what cannot be measured is not passed over: a port not found, and a cable no lay is opened out for', () => {
  const {rack, ctx} = shape({count: 43});
  const c9 = cableOf(rack, 'c9');
  // a cable that needs more than any ring leaves: none has room, the nearest stands
  const stiff = {...ctx, bendOf: () => 1e6};
  assert.deepEqual(ringsOn(R.autoRoute(rack, c9, stiff), 'm3'), [2, 1]);
  // a port the drawing does not place: the side is the left, and every ring on it is taken
  const lost = {...ctx, portX: e => (e.item === 'i3' ? null : ctx.portX(e))};
  assert.deepEqual(ringsOn(R.autoRoute(rack, c9, lost), 'm3'), [3, 2, 1]);
});

test('the choice is the same however often it is asked for, and from either end of the cable', () => {
  const {rack, ctx} = shape({count: 43});
  let rings = 0;
  for (const c of rack.cables) {
    const a = R.autoRoute(rack, c, ctx);
    assert.deepEqual(R.autoRoute(rack, c, ctx), a, c.id);
    const back = R.autoRoute(rack, {...c, a: c.b, b: c.a}, ctx);
    assert.deepEqual(back, a.toReversed(), c.id);
    rings += a.filter(w => w.item).length;
  }
  assert.ok(rings > 60, `${rings} rings`);
});

test('the measure the rule uses is the path\'s own: a lead it gives a ring has no corner short on the way to it', () => {
  // every lead of the 43 that was given a ring with room is laid with room
  const {rack, ctx, nameOf} = shape({count: 43});
  let leads = 0;
  for (const c of rack.cables) {
    const found = R.bendFindingsOf(rack, c, ctx, nameOf);
    for (const f of found) if (f.between.some(w => w.end) && f.between.some(w => w.item)) { assert.ok(f.tooClose, f.text); leads++; }
    assert.ok(cornersOf(R.routePath(rack, c, ctx).points, {share: 'need'}).length > 0, c.id);
  }
  assert.ok(leads > 10, `${leads} findings at a lead`);
});

// ── round a tray ─────────────────────────────────────────────────────────
// The fabric switches have ports in their bottom unit, under a lacer hosted
// on the top unit: c164 to c203 and c204 to c243 are the fabric links of
// EDGE-4 and EDGE-5, whose far ends are those ports.

test('a plug that ends behind a tray\'s back edge comes up behind the plate, by one point on its back plane', () => {
  const far = shape({setback: 50});
  const c = cableOf(far.rack, 'c164'), path = R.routePath(far.rack, c, far.ctx);
  // FAB-0's port-32, 23.6 mm under the tray of its lacer (m6); set back 50
  // mm, its plug ends 14.8 mm out of the rail, 34 mm behind the floor's back edge
  const [t] = S.traysOf(far.rack, far.ctx).filter(x => x.item === 'm6');
  const floor = t.floors.reduce((m, f) => ((f.x1 - f.x0) > (m.x1 - m.x0) ? f : m));
  const reach = path.points.find(q => q.at === 'reach' && q.end === 'b'), ap = path.points.findLast(q => q.at === 'approach');
  assert.deepEqual([r1(floor.z0), r1(reach.z), r1(t.top - reach.y)], [48.8, 14.8, 16.5]);
  // one detour, of one point: the back edge less the cable's radius and
  // CLEAR, as far above the plate, and between the two along the run
  const clear = 1.5 + S.CLEAR;
  assert.deepEqual(path.detours.map(d => d.between), [[ring('m6', 1), {end: 'b'}]]);
  const [q] = path.detours[0].points;
  assert.equal(path.detours[0].points.length, 1);
  assert.deepEqual([r1(q.z), r1(q.y)], [r1(floor.z0 - clear), r1(t.top + clear)]);
  assert.ok(q.x > ap.x && q.x < reach.x, `${q.x} between ${ap.x} and ${reach.x}`);
  // and it has its room: round the front edge the same cord turned twice on
  // 53.3 mm, with room for a 26.6 mm bend
  assert.deepEqual(path.bends, []);
  assert.deepEqual(path.crossings, []);
  // with no setback the plug ends under the floor, in front of its back
  // edge, and the way round is the front edge as before
  const near = shape({});
  const front = R.routePath(near.rack, cableOf(near.rack, 'c164'), near.ctx).detours.at(-1);
  assert.ok(front.points.length && front.points.every(o => o.z > floor.z1), JSON.stringify(front.points));
});

test('the back edge is offered only to an end that stands behind it, and only where it is asked for', () => {
  const {rack, ctx} = shape({});
  const solids = S.solidsOf(rack, ctx).filter(x => x.item === 'm6');
  const above = {x: -170, y: 1299.4, z: 73.7}, opts = {diameter: 3, room: 60};
  // under the floor, in front of its back edge: `rear` changes nothing
  const under = {x: -148, y: 1275, z: 64.8};
  assert.deepEqual(S.detour(above, under, solids, {...opts, rear: true}), S.detour(above, under, solids, opts));
  // behind the back edge: round the front edge as it stands, and by one point with `rear`
  const behind = {x: -148, y: 1275, z: 14.8};
  const front = S.detour(above, behind, solids, opts), back = S.detour(above, behind, solids, {...opts, rear: true});
  assert.ok(front.length >= 2 && front.every(q => q.z > 110), JSON.stringify(front));
  assert.equal(back.length, 1);
  assert.deepEqual([r1(back[0].z), back[0].x > -170 && back[0].x < -148], [42.3, true]);
  // either way round, nothing is crossed
  for (const way of [front, back]) {
    const chain = [above, ...way, behind];
    for (let k = 1; k < chain.length; k++) assert.deepEqual(S.legCrossings(chain[k - 1], chain[k], solids, {diameter: 3}), []);
  }
});

test('a way round a tray\'s front edge keeps the point where it turns back in, where pulled taut it would take a turn\'s room', () => {
  const {rack, ctx} = shape({});
  // c167's far end is FAB-0's port-35, 31 mm under the tray and 77 mm along
  // from ring 1's face: out past the front edge, across and back in
  const c = cableOf(rack, 'c167'), path = R.routePath(rack, c, ctx);
  const d = path.detours.at(-1), ap = path.points.findLast(q => q.at === 'approach'), reach = path.points.find(q => q.at === 'reach' && q.end === 'b');
  assert.deepEqual(d.between, [ring('m6', 1), {end: 'b'}]);
  // two points, both two bend radii in front of the rings' line: straight
  // out from the approach point, and straight out from the plug
  assert.deepEqual(d.points.map(q => [r1(q.x), r1(q.y), r1(q.z)]), [[r1(ap.x), r1(ap.y), 133.7], [r1(reach.x), r1(reach.y), 133.7]]);
  assert.deepEqual(path.bends.filter(f => f.between.some(w => w.end === 'b')), []);
  // pulled taut, as it was, the second point goes and the first turns 139
  // degrees on the 60 mm it shares with the right angle before it
  const solids = S.solidsOf(rack, ctx), opts = {diameter: 3, room: 60};
  const taut = S.detour(ap, reach, solids, opts), loose = S.detour(ap, reach, solids, {...opts, loose: true});
  assert.deepEqual([taut.length, loose.length], [1, 2]);
  const turns = pts => cornersOf([{...ap, x: ap.x - 60}, ap, ...pts, reach, {...reach, z: 0}], {share: 'need'}).map(k => [k.angle_deg, k.room_mm]);
  assert.deepEqual(turns(taut), [[90, 16.4], [138.6, 16.4], [41.4, 30.4]]);
  assert.ok(turns(loose).every(([, room]) => room >= 30), JSON.stringify(turns(loose)));
  // and only a way round a plate is kept so: over a ring's leg, `loose` or
  // not, a way is pulled taut (c182's, below)
  const lead = cableOf(rack, 'c182'), lp = R.routePath(rack, lead, ctx);
  const from = lp.points.find(q => q.at === 'reach' && q.end === 'a'), to = lp.points.find(q => q.at === 'approach');
  assert.equal(S.detour(from, to, solids, opts).length, 1);
  assert.deepEqual(S.detour(from, to, solids, {...opts, loose: true}), S.detour(from, to, solids, opts));
});

test('a lead is not taken up over a ring that stands in its way: the nearest stands, and says the manager is too close', () => {
  const {rack, ctx, nameOf} = shape({});
  // c182 leaves EDGE-4's fab-18, 3.5 mm left of the centre line and so just
  // past ring 3 on its way left; ring 3's rear leg stands 1.6 mm in front of
  // its plug's end. The detour rules take a leg over the ring, and that hump
  // can have all its room; no lead is dressed so
  const c = cableOf(rack, 'c182');
  assert.deepEqual(ringsOn(R.autoRoute(rack, c, ctx), 'm12'), [2, 1]);
  const found = R.bendFindingsOf(rack, c, ctx, nameOf).filter(f => f.between.some(w => w.end === 'a'));
  assert.ok(found.length >= 1 && found.every(f => f.tooClose?.manager === 'm12'), JSON.stringify(found.map(f => f.text)));
});

// ── two turns on one leg ─────────────────────────────────────────────────

test('two turns that share a leg too short for both are one finding, and it says it is two turns', async () => {
  const Q = await import('../../../kit/rack/queries.js');
  const X = await import('../../../kit/rack/export-data.js');
  const {rack, ctx, nameOf} = shape({count: 43});
  const c1 = cableOf(rack, 'c1'), path = R.routePath(rack, c1, ctx);
  // c1 jogs from its plug's end to ring 1's approach point: 67.1 degrees
  // one way and 63.2 the other, 22.8 mm apart. It was two findings, each
  // with room for 17.9 mm and 12.1 short
  assert.equal(path.bends.length, 1);
  const [f] = path.bends;
  assert.deepEqual([f.point, f.angle_deg, f.apart_mm, f.room_mm, f.short_mm, f.legs_mm], ['reach', 67.1, 22.8, 17.9, 12.1, [64.8, 43.3]]);
  assert.deepEqual(f.turns.map(t => [t.point, t.angle_deg]), [['reach', 67.1], ['approach', 63.2]]);
  // it is where the leg between the two turns is: the middle of it
  assert.deepEqual(f.at, [0, 1, 2].map(i => r1((f.turns[0].at[i] + f.turns[1].at[i]) / 2)));
  // both turns are corners of the path, short by the same leg
  const corners = cornersOf(path.points, {share: 'need'}).filter(k => k.room_mm < 30);
  assert.deepEqual(corners.map(k => [k.angle_deg, k.room_mm]), [[67.1, 17.9], [63.2, 17.9]]);
  assert.equal(corners[0].legs_mm[1], f.apart_mm);
  // the same cable written the other way round: the same finding, read from its end
  const back = R.routePath(rack, {...c1, a: c1.b, b: c1.a}, ctx).bends;
  assert.deepEqual(back.map(b => [b.point, b.apart_mm, b.room_mm, b.turns.map(t => t.angle_deg), b.at]), [['approach', 22.8, 17.9, [63.2, 67.1], f.at]]);
  // a turn that is short for another leg than the one it shares stays a finding of its own
  const all = rack.cables.flatMap(c => R.routePath(rack, c, ctx).bends);
  assert.ok(all.some(b => b.turns) && all.some(b => !b.turns), JSON.stringify(all.map(b => !!b.turns)));
  for (const b of all) assert.ok(!b.turns || b.turns.length === 2);
  // what a reader is told agrees: inspect lists the one finding with its
  // two turns, describe counts the cable once, and a schedule's note is the
  // finding's own sentence
  const qctx = {chassisOf: ctx.chassisOf, route: ctx};
  const seen = (await Q.inspect(rack, 'c1', qctx)).route.bends;
  assert.equal(seen.length, 1);
  assert.deepEqual([seen[0].apart_mm, seen[0].turns.length, seen[0].tooClose], [22.8, 2, {manager: 'm3', device: 'i3'}]);
  assert.match(seen[0].advice, /^Lacer EDGE-0 stands too close to the port of c1 on EDGE-0 /);
  assert.match(seen[0].text, /^c1 turns twice within 22\.8 mm between its port on EDGE-0 and .* ring 1 \(67\.1 and 63\.2 degrees\), with room for a 17\.9 mm bend/);
  const withBend = rack.cables.filter(c => R.routePath(rack, c, ctx).bends.length).length;
  assert.match(Q.describe(rack, qctx), new RegExp(`Findings: ${withBend} cables have a tight bend \\(the worst `));
  const found = R.bendFindings(rack, ctx, nameOf);
  // (and the advice after it, once)
  const mine = found.filter(x => x.cable === 'c1');
  assert.deepEqual(X.layNotesOf('c1', {bends: found}), [mine[0].text, mine[0].advice]);
});

// ── what is kept ─────────────────────────────────────────────────────────

test('the ring chosen reads nothing that what is kept leaves out: every path laid again from nothing is the path kept', () => {
  // `checkKept` on a context lays every path read again from a copy of the
  // rack, the cable and the context, and throws on a difference. The choice
  // of ring is part of the route a lay is kept under, and is itself kept by
  // what it read (leadRoom), so a context made anew, and a rack edited as a
  // command edits one, must give what a first read gives
  let reads = 0;
  for (const o of [{count: 43}, {count: 43, setback: 50}, {count: 43, lacer: 'bottom'}]) {
    const {rack, ctx} = shape(o);
    const first = {...ctx, checkKept: true};
    for (const cx of [first, first, {...ctx, checkKept: true}]) {
      for (const c of rack.cables) { R.routePath(rack, c, cx); reads++; }
      R.bendFindings(rack, cx);
    }
    // two cables exchange ports on one switch: a new rack sharing the rest
    const [c1, c9] = [cableOf(rack, 'c1'), cableOf(rack, 'c9')];
    const moved = {...rack, cables: rack.cables.map(c => (c === c1 ? {...c, a: {...c9.a}} : c === c9 ? {...c, a: {...c1.a}} : c))};
    const cx = {...ctx, checkKept: true};
    for (const c of moved.cables) { R.routePath(moved, c, cx); reads++; }
    // and the answer does follow the edit: c1 now leaves fab-8, and passes
    // ring 2 where the lacer is on that unit and nothing is set back
    assert.deepEqual(ringsOn(R.autoRoute(moved, cableOf(moved, 'c1'), cx), 'm3'), o.setback || o.lacer ? [2, 1] : [1], JSON.stringify(o));
  }
  assert.equal(reads, 3 * 4 * 43);
});

// ── the gutter, and what is chosen by laying ─────────────────────────────

test('no cable is moved to another gutter: each side is measured through its nearest rings, laid as it was before', () => {
  // c131 (lacer on the bottom unit) has its ports on opposite sides of the
  // centre line, so its gutter is chosen by measuring both. Measured through
  // the rings chosen by room, the right came out 127 mm shorter and was
  // taken, into a bend 6.8 mm short that the left never had. The gutter is
  // chosen first, by the way through the ring nearest each port and with
  // none of this kit's new offers, as it was: the left
  const {rack, ctx} = shape({lacer: 'bottom'});
  const c = cableOf(rack, 'c131'), route = R.autoRoute(rack, c, ctx);
  assert.deepEqual([...new Set(route.filter(w => w.lane).map(w => w.lane))], ['left-front']);
  assert.deepEqual(ringsOn(route, 'm11'), [1]);
  assert.deepEqual(ringsOn(route, 'm6'), [1, 2, 3, 4]);
  const path = R.routePath(rack, c, ctx);
  assert.deepEqual([path.bends, path.crossings], [[], []]);
  assert.equal(Math.round(R.pathLength(path).measured * 10000) / 10, 1675);
  // the same cable written the other way round takes the same gutter
  assert.deepEqual(R.autoRoute(rack, {...c, a: c.b, b: c.a}, ctx), route.toReversed());
});

test('a ring between a plug and the ring its lead takes is cleared run out, through its opening, not gone round', () => {
  // c168's far end is FAB-0's port-36, beside ring 2 of the lacer on the unit
  // below and 21 mm above its line; ring 2 is passed over for ring 1. The
  // straight way from ring 1 meets ring 2, and the way round it that has all
  // its room is a loop out, under the tray and back, 320 mm long. Run 15 mm
  // on out of its plug, the cable clears ring 2 through its opening
  const {rack, ctx} = shape({lacer: 'bottom'});
  const c = cableOf(rack, 'c168'), took = R.RUN_OUTS.taken, path = R.routePath(rack, c, ctx);
  // the ring is the first body in the lead, so the run-out is tried, and taken (#1038)
  assert.ok(R.RUN_OUTS.taken > took);
  assert.deepEqual(ringsOn(R.autoRoute(rack, c, ctx), 'm6'), [1]);
  assert.deepEqual(path.detours, []);
  assert.deepEqual(path.points.filter(q => q.at === 'lead').map(q => [q.end, r1(q.z)]), [['b', 79.8]]);
  assert.deepEqual([path.bends, path.crossings], [[], []]);
  // 5.8 mm shorter than through ring 2, where it turned twice on 22.8 mm
  assert.equal(Math.round(R.pathLength(path).measured * 10000) / 10, 1459.7);
});

test('the answer kept for a lead is kept with the world it was judged in: a wall put between is seen', () => {
  // the same rack, cable and ends, and a context whose lacer has a wall
  // standing between ring 2 and ring 1: what the test reads of the cable and
  // the ring is the same text, and only the world differs
  const {rack, ctx} = shape({count: 43});
  const c9 = cableOf(rack, 'c9');
  assert.deepEqual(ringsOn(R.autoRoute(rack, c9, ctx), 'm3'), [1]);
  const lacer = ctx.chassisOf('fhd-cmp5dr');
  const walled = {...lacer, solids: [...lacer.solids, {part: 'wall/plate', box: {x: 80, y: -100, z: 0, w: 2, h: 400, d: 400}}]};
  const cx = {...ctx, chassisOf: ref => (ref === 'fhd-cmp5dr' ? walled : ctx.chassisOf(ref))};
  // no way to ring 1 with room now: no ring leaves any, and the nearest stands
  assert.deepEqual(ringsOn(R.autoRoute(rack, c9, cx), 'm3'), [2, 1]);
  // and back in the first world, the first answer
  assert.deepEqual(ringsOn(R.autoRoute(rack, c9, {...ctx}), 'm3'), [1]);
});

test('where the lay from each end differs, the one kept is by corners counted singly: a finding of two turns is two', async () => {
  // speed-fixture's rack of 150 cords: c96 laid from one end has three
  // findings, 6.1 and 13.5 mm short and a pair 14 mm short (47.6 in all, the
  // pair counted twice), and from the other end two that come to less only
  // if the pair is counted once. The lay kept is the first, as before a
  // pair was one finding
  const M = await import('../../../kit/rack/model.js'), F = await import('./cable-solids-fixture.mjs');
  const {speedRack} = await import('./speed-fixture.mjs');
  const m = speedRack(M, F, {cables: 150, bundles: 4}), ctx = m.ctxOf(m.rack);
  const c = m.rack.cables.find(x => x.id === 'c96'), path = R.routePath(m.rack, c, ctx);
  assert.deepEqual(path.bends.map(f => [f.point, f.short_mm, f.turns?.length ?? 1]), [['reach', 6.1, 1], ['approach', 13.5, 1], ['approach', 14, 2]]);
  assert.equal(Math.round(R.pathLength(path).measured * 10000) / 10, 659.2);
});

test('a patch keeps the ring it took unless another lays better, and the tightest corner is weighed before the sum', async () => {
  const M = await import('../../../kit/rack/model.js'), F = await import('./cable-solids-fixture.mjs');
  const {speedRack} = await import('./speed-fixture.mjs');
  const m = speedRack(M, F, {cables: 300}), ctx = m.ctxOf(m.rack);
  // c268 joins two ports of one switch 22 mm apart, with no ring between.
  // Through ring 2, as before, it has three corners 23.3 to 26 mm short;
  // through ring 3 one, which doubles back with no room, 30 mm short and
  // 142 mm longer. Fewer millimetres short in all, and the worse cable
  const c = m.rack.cables.find(x => x.id === 'c268'), item = R.autoRoute(m.rack, c, ctx)[0].item;
  const lay = n => { const hand = {...c, route: [ring(item, n)], routeEdited: true}, p = R.routePath({...m.rack, cables: [hand]}, hand, ctx);
    return [Math.round(R.pathLength(p).measured * 10000) / 10, Math.max(...p.bends.map(f => f.short_mm)), r1(p.bends.reduce((n2, f) => n2 + f.short_mm * (f.turns?.length ?? 1), 0)), p.findings.length]; };
  assert.deepEqual([lay(2), lay(3)], [[700.6, 26, 75.3, 1], [842.2, 30, 30, 1]]);
  assert.deepEqual(R.autoRoute(m.rack, c, ctx), [ring(item, 2)]);
});

// ── the rack, counted ────────────────────────────────────────────────────

test('the first 43 cables of the shape, lacer on the top unit: 37 corners short at no setback (69 before), none at 50 and 100 mm', () => {
  // EDGE-0's forty fabric links and its three to the control switches. With
  // the nearest ring taken every time, and a detour pulled taut, the same
  // racks had 69 corners short on 32 cables, 21 on 10 at 25 mm (not counted
  // here) and 2 on 1 at 50 mm
  const count = o => { const m = measure(R, shape({count: 43, ...o})); return [m.corners, m.cables, m.findings, m.close, m.crossings]; };
  // every finding left at no setback is a lead with no ring it has room to
  // turn into, and says so; nothing is bought with a body
  assert.deepEqual(count({setback: 0}), [37, 18, 19, 19, 0]);
  assert.deepEqual(count({setback: 50}), [0, 0, 0, 0, 0]);
  assert.deepEqual(count({setback: 100}), [0, 0, 0, 0, 0]);
  // on the bottom unit the tray is a unit below the ports it serves: 2
  // corners on 1 cable (16 on 7 before)
  assert.deepEqual(count({lacer: 'bottom'}), [2, 1, 1, 1, 0]);
  // and with no lacer nothing is short, before or after
  assert.deepEqual(count({lacer: 'none'}), [0, 0, 0, 0, 0]);
});
