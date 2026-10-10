// Room for a cable's bends (#973, docs/cable-lay-design.md section 3.4). A
// routed path is laid so that no corner of it has less room than the cable's
// installed bend radius, by the kit's own measure (route-path.js cornersOf),
// and what the rack leaves no room for is a finding and not a silence. Every
// count here was measured on these fixtures and is asserted exactly, and each
// check asserts it measured something, so a rule that found nothing cannot
// pass.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as R from '../../../kit/rack/route.js';
import * as S from '../../../kit/rack/solids.js';
import * as M from '../../../kit/rack/model.js';
import * as Rest from '../../../kit/rack/resting.js';
import * as B from '../../../kit/rack/bundles.js';
import {cornersOf, STRAIGHT_DEG} from '../../../kit/rack/route-path.js';
import * as F from './route-direct-fixture.mjs';
import {tightCorners, byCause} from './bend-corners-probe.mjs';

const P = (x, y, z = 0) => ({x, y, z});
const gap = (p, q) => Math.hypot(p.x - q.x, p.y - q.y, p.z - q.z);
const r1 = v => Math.round(v * 10) / 10;

// ── the measure ──────────────────────────────────────────────────────────

test('cornersOf is one function, in route-path.js, and bundles.js still exports it', () => {
  assert.equal(B.cornersOf, cornersOf);
  assert.equal(B.STRAIGHT_DEG, STRAIGHT_DEG);
});

test('a leg between two corners is shared by halves, or by what each turn needs of it', () => {
  // a right angle, then 47.7 mm on, a turn of 15 degrees: the plug's end to a
  // ring's line on the owner's rack. A 25 mm bend uses 25 tan 45 = 25 mm of
  // the leg at the right angle and 25 tan 7.5 = 3.3 at the other: 28.3 of
  // 47.7. By halves the right angle has 23.8 and is short; by need both have
  // 47.7 / (tan 45 + tan 7.5) = 42.2
  const t = 15 * Math.PI / 180;
  const pts = [P(0, 0), P(200, 0), P(200, 47.7), P(200 + 200 * Math.sin(t), 47.7 + 200 * Math.cos(t))];
  assert.deepEqual(cornersOf(pts).map(c => [c.angle_deg, c.room_mm]), [[90, 23.8], [15, 181.2]]);
  assert.deepEqual(cornersOf(pts, {share: 'half'}), cornersOf(pts));
  assert.deepEqual(cornersOf(pts, {share: 'need'}).map(c => [c.angle_deg, c.room_mm]), [[90, 42.2], [15, 42.2]]);
  // two right angles on one leg take half each either way
  const u = [P(0, 0), P(100, 0), P(100, 50), P(0, 50)];
  assert.deepEqual(cornersOf(u, {share: 'need'}).map(c => c.room_mm), [25, 25]);
  assert.deepEqual(cornersOf(u).map(c => c.room_mm), [25, 25]);
  // a leg to an end is all the corner's, as before
  assert.deepEqual(cornersOf([P(0, 0), P(30, 0), P(30, 80)], {share: 'need'}).map(c => c.room_mm), [30]);
  // a corner that doubles back has no room, and takes half of each leg from
  // its neighbours, not all of it
  const back = [P(0, 0), P(100, 0), P(100, 60), P(100, 0.001), P(200, 0)];
  const got = cornersOf(back, {share: 'need'});
  assert.equal(got[1].room_mm, 0);
  assert.equal(got[0].room_mm, 30);
});

test('by need is never stricter than by halves: what has room for a radius by halves has it by need', () => {
  // 400 polylines of six points from a fixed sequence; for each radius, every
  // polyline that passes by halves passes by need, and some pass only by need
  let seed = 7;
  const rnd = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; };
  let both = 0, onlyNeed = 0;
  for (let n = 0; n < 400; n++) {
    const pts = Array.from({length: 6}, () => P(rnd() * 300, rnd() * 300, rnd() * 100));
    for (const R0 of [10, 25, 40]) {
      const half = cornersOf(pts).every(c => c.room_mm >= R0), need = cornersOf(pts, {share: 'need'}).every(c => c.room_mm >= R0 - 0.1);
      assert.ok(!half || need, `polyline ${n} at ${R0}`);
      if (half) both++; else if (need) onlyNeed++;
    }
  }
  assert.ok(both > 50 && onlyNeed > 10, `${both} by both, ${onlyNeed} by need alone`);
});

// ── the owner's rack ─────────────────────────────────────────────────────

test('the owner\'s rack: no corner of any cord is short of its 25 mm (86 were, before #973)', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  // by the measure a path is judged by, a leg shared by need: none, of any cause
  assert.deepEqual(tightCorners(r, ctx, 'need'), []);
  assert.deepEqual(r.cables.flatMap(c => R.routePath(r, c, ctx).bends), []);
  assert.deepEqual(R.bendFindings(r, ctx), []);
  // it looked: the sixteen paths have 98 corners between them, and the
  // tightest has 25 mm
  const all = r.cables.flatMap(c => cornersOf(R.routePath(r, c, ctx).points, {share: 'need'}));
  assert.equal(all.length, 98);
  assert.equal(Math.min(...all.map(c => c.room_mm)), 25);
  // by halves, the only measure there was before, 86 corners were short: 22
  // at a rest sample, 32 at a ring's approach, 13 at a detour and 19 at a
  // plug's end beside a rest sample. 24 are still short by halves, none at
  // a rest sample or a detour: each is a turn that shares a leg with a
  // slighter one, which takes half of it and needs a fraction
  assert.deepEqual(byCause(tightCorners(r, ctx, 'half')), {rest: 0, approach: 16, detour: 0, other: 8});
  // and nothing was bought with a body: no path crosses one
  assert.deepEqual(R.bodyFindings(r, ctx), []);
  assert.deepEqual(R.ringFindings(r, ctx), []);
});

test('a path is the same however often it is asked for, and from either end', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  let read = 0;
  for (const c of r.cables) {
    const a = R.routePath(r, c, ctx), b = R.routePath(r, c, ctx);
    assert.deepEqual(a, b, c.id);
    // written the other way round, the same points in the other order
    const back = R.routePath(r, {...c, a: c.b, b: c.a}, ctx);
    assert.ok(Math.abs(R.pathLength(a).measured - R.pathLength(back).measured) < 1e-9, c.id);
    assert.equal(back.points.length, a.points.length, c.id);
    a.points.forEach((p, k) => assert.ok(gap(p, back.points.at(-1 - k)) < 1e-6, `${c.id} point ${k}`));
    read += a.points.length;
  }
  assert.ok(read > 150, `${read} points`);
});

// ── where a turn gets its room ───────────────────────────────────────────

test('an approach point stands the cable\'s own bend radius from the band where the route turns there', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  const c9 = r.cables.find(c => c.id === 'c9');
  const offs = (cable, cx) => {
    const p = R.routePath(r, cable, cx).points, k = p.findIndex(q => q.at === 'entry');
    return [Math.abs(p[k - 1].x - p[k].x), Math.abs(p[k + 2].x - p[k + 1].x)].map(r1);
  };
  // c9 turns onto ring 3's run from a detour and off it to its panel port:
  // 25 mm each side for an OM4 cord (6.5, its radius and CLEAR, before)
  assert.deepEqual(offs(c9, ctx), [25, 25]);
  // the radius is the cable's own: its media's, or the page's for its type
  assert.deepEqual(offs({...c9, media: 'cat6a'}, ctx), [30, 30]);
  assert.deepEqual(offs(c9, {...ctx, bendOf: () => 18}), [18, 18]);
  // a pass that does not turn keeps the radius and CLEAR: LEAF-B's port 49
  // out through rings 3, 2 and 1 to the left lane. Ring 2 has ring 3 before
  // it and ring 1 after it on one line, so its two approach points stand
  // 6.5 mm from its band; ring 3 turns in from the detour and ring 1 out to
  // the lane, 25 mm each, and their other sides 6.5
  const far = M.withItem(r, {ref: 'fhd-1ufce', cfg: 'populated', ru: 20, label: 'PP-02'}).rack;
  const c17 = {id: 'c17', a: {item: 'i3', path: 'port-49', view: 'front'}, b: {item: 'i5', path: 'far', view: 'front'}, media: 'om4', route: []};
  const base = F.ctxOf(far), cx = {...base, portX: e => (e.item === 'i5' ? -150 : base.portX(e)), portY: e => (e.item === 'i5' ? 19.5 * 44.45 : base.portY(e))};
  const p = R.routePath({...far, cables: [c17]}, c17, cx);
  const by = {};
  p.points.forEach((q, k) => { if (q.at === 'entry') by[q.via] = [Math.abs(p.points[k - 1].x - q.x), Math.abs(p.points[k + 2].x - p.points[k + 1].x)].map(r1); });
  assert.deepEqual(by, {'guide-3': [25, 6.5], 'guide-2': [6.5, 6.5], 'guide-1': [6.5, 25]});
  assert.deepEqual(p.bends, []);
  assert.deepEqual(p.crossings, []);
});

test('a cord whose port stands behind the approach point is led square to it', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  // c1: LEAF-A port 49 at x 88.3, ring 4 (107 to 113.8) entered from its far
  // face, so the approach point stands at 138.8, 50.5 mm past the port along
  // the run. Straight to it the cord would turn back on itself there, 123
  // degrees; led square it runs level with its plug's end to a lead point
  // beside the approach point, and down and out to it: two right angles
  const p = R.routePath(r, r.cables[0], ctx).points;
  const k = p.findIndex(q => q.at === 'lead');
  assert.deepEqual([p[k].item, p[k].via, p[k].end], ['i4', 'guide-4', undefined]);
  assert.deepEqual([p[k - 1].at, p[k + 1].at === 'rest' ? p[k + 2].at : p[k + 1].at], ['reach', 'approach']);
  const ap = p.find(q => q.at === 'approach');
  assert.deepEqual([p[k].x, p[k].y, p[k].z].map(r1), [r1(ap.x), r1(p[k - 1].y), r1(p[k - 1].z)]);
  assert.equal(r1(ap.x), 138.8);
  const taut = p.filter(q => q.at !== 'rest');
  const at = cornersOf(taut, {share: 'need'}).filter(c => ['reach', 'lead', 'approach'].includes(taut[c.k].at)).slice(0, 3);
  assert.deepEqual(at.map(c => [taut[c.k].at, c.angle_deg]), [['reach', 90], ['lead', 90], ['approach', 90]]);
  assert.ok(at.every(c => c.room_mm >= 25), JSON.stringify(at));
});

test('a detour leaves each end\'s move to its plane room for two bends', () => {
  // a plate 100 wide, a leg from 20 below it to 30 above it across its
  // middle: over its near edge, 6.5 mm clear of it as before; with room, the
  // plane stands that far from the end it would otherwise be nearer to
  const plate = {item: 'p', part: 'tray/floor', away: 1, box: {x0: -50, x1: 50, y0: 0, y1: 2, z0: 0, z1: 100}, holes: []};
  const a = {x: 0, y: -20, z: 70}, b = {x: 10, y: 30, z: 70};
  const plain = S.detour(a, b, [plate], {diameter: 3});
  assert.deepEqual(plain.map(q => [q.x, q.y, q.z]), [[0, -20, 106.5], [10, 30, 106.5]]);
  const roomy = S.detour(a, b, [plate], {diameter: 3, room: 50});
  assert.deepEqual(roomy.map(q => [q.x, q.y, q.z]), [[0, -20, 120], [10, 30, 120]]);
  // an end already that far from the plane leaves it where it was
  const far = S.detour({...a, z: 40}, {...b, z: 40}, [plate], {diameter: 3, room: 50});
  assert.deepEqual(far.map(q => q.z), [106.5, 106.5]);
  // and where the room cannot be had (a second plate stands where the plane
  // would move to), the way is the one without it: the route still exists
  const wall = {item: 'w', part: 'body', box: {x0: -50, x1: 50, y0: -40, y1: 60, z0: 112, z1: 140}, holes: []};
  const kept = S.detour(a, b, [plate, wall], {diameter: 3, room: 50});
  assert.deepEqual(kept.map(q => q.z), [106.5, 106.5]);
});

// ── a hang ───────────────────────────────────────────────────────────────

test('a free span\'s samples are evenly spaced along its arc, and none is a near-duplicate', () => {
  // 300 mm level, fibre: the catenary sags 110 mm, steep at its ends. By the
  // chord its samples were 15 mm apart across the face and 31 to 15 along
  // the cable; along the arc they are the same distance apart, to a hundredth
  const p = P(0, 100), q = P(300, 100);
  const pts = [p, ...Rest.hang(p, q, {drape: 1, bend: 25}).points, q];
  const legs = pts.slice(1).map((x, k) => gap(pts[k], x));
  assert.ok(legs.length > 15, `${legs.length} legs`);
  assert.ok(Math.max(...legs) - Math.min(...legs) < 0.05, `${Math.min(...legs)} to ${Math.max(...legs)}`);
  // where a span lands, every point is a bend's own and none within 1 mm of
  // the next (two were 0.25 mm apart on c8)
  const floor = [{x0: -10, x1: 400, z0: -10, z1: 10, y: 92 - 1.5}];
  const laid = [p, ...Rest.hang(p, q, {r: 1.5, drape: 1, bend: 25, surfaces: floor}).points, q];
  assert.ok(laid.length >= 6);
  assert.ok(Math.min(...laid.slice(1).map((x, k) => gap(laid[k], x))) >= 1);
  assert.ok(cornersOf(laid, {share: 'need'}).every(c => c.room_mm >= 25), JSON.stringify(cornersOf(laid, {share: 'need'})));
});

test('a hang is laid only where it leaves every corner its room, and is offered shallower before it is refused', () => {
  const p = P(0, 100), q = P(120, 100);
  const head = [P(0, 100, -200), p], tail = [q, P(120, 100, -200)];
  const fits = need => pts => cornersOf([...head.slice(0, 1), p, ...pts, ...tail], {share: 'need'}).every(c => c.room_mm >= need - 1e-9);
  const depth = pts => (pts.length ? 100 - Math.min(...pts.map(x => x.y)) : 0);
  // with nothing to say otherwise the full hang is laid, as before
  const full = Rest.hang(p, q, {drape: 1, bend: 25}).points;
  assert.ok(depth(full) > 40, `${depth(full)}`);
  // held at each end by a leg at right angles to it: the turn there needs 25
  // mm of the span, so its samples stand further apart, or it sags less
  const some = Rest.hang(p, q, {drape: 1, bend: 25, fits: fits(25)}).points;
  assert.ok(some.length >= 1 && some.length < full.length, `${some.length} of ${full.length}`);
  assert.ok(fits(25)(some));
  // and with no room for any hang at all (a radius the legs cannot take) it
  // is straight
  assert.deepEqual(Rest.hang(p, q, {drape: 1, bend: 25, fits: () => false}), {points: [], lands: []});
});

// ── what stays tight ─────────────────────────────────────────────────────

test('a bend the rack leaves no room for is found, and the route still exists', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  // c9 as an AOC from the leaf below: its head ends 64.8 mm out of the port,
  // and to reach ring 3 it goes out past the tray's front edge and back in
  // to the approach point, 60 mm (two radii of 30) in front of the ring's
  // line. Pulled taut it turns 138.3 degrees at the edge, and that turn and
  // the right angle at the approach point need 30 (tan 69.2 + tan 45) = 109
  // mm of the 60 between them: each has room for 16.5 mm
  const aoc = {...r.cables.find(c => c.id === 'c9'), media: 'aoc'};
  const rack = {...r, cables: [aoc]};
  const p = R.routePath(rack, aoc, ctx);
  assert.ok(p.points.length > 8);
  assert.deepEqual(p.crossings, []);
  assert.ok(R.pathLength(p).measured > 0.5);
  assert.deepEqual(p.bends.map(b => [b.point, b.angle_deg, b.legs_mm[1], b.room_mm, b.short_mm]),
    [['detour', 138.3, 60, 16.5, 13.5], ['approach', 90, 66.8, 16.5, 13.5]]);
  for (const b of p.bends) {
    assert.deepEqual([b.kind, b.cable, b.need_mm, b.between], ['tight-bend', 'c9', 30, [{end: 'a'}, {item: 'i4', via: 'guide-3'}]]);
    assert.equal(b.at.length, 3);
  }
  // each is a corner of the path, with the room the kit's measure gives it
  const corners = cornersOf(p.points, {share: 'need'});
  assert.ok(corners.length > 4);
  assert.deepEqual(p.bends.map(b => [b.angle_deg, b.room_mm]), corners.filter(c => c.room_mm < 30).map(c => [c.angle_deg, c.room_mm]));
  const f = R.bendFindings(rack, ctx, id => ({i2: 'PP-01', i3: 'LEAF-B', i4: 'CM-01'}[id] ?? id));
  assert.deepEqual(f.map(x => x.text), [
    'c9 turns 138.3 degrees between its port on LEAF-B and CM-01 ring 3 with room for a 16.5 mm bend; the cable (aoc) needs 30 mm, 13.5 mm short.',
    'c9 turns 90 degrees between its port on LEAF-B and CM-01 ring 3 with room for a 16.5 mm bend; the cable (aoc) needs 30 mm, 13.5 mm short.']);
  // the same cord as OM4 has room everywhere; and held to a radius no lacer
  // gives, 80 mm, the turns it makes are found, each against that radius
  assert.deepEqual(R.bendFindings(r, ctx).filter(x => x.cable === 'c9'), []);
  const stiff = R.bendFindings(r, {...ctx, bendOf: () => 80}).filter(x => x.cable === 'c9');
  assert.deepEqual(stiff.map(x => x.room_mm), [13.9, 10.1, 10.1, 28.8, 28.8]);
  assert.ok(stiff.every(x => x.need_mm === 80 && x.short_mm === r1(80 - x.room_mm)));
});

test('a cable stiffer than a lay is opened out for is laid as one of 100 mm, and judged by its own radius', () => {
  const r = F.rack(), base = F.ctxOf(r), ctx = {...base, bendOf: () => 1e9};
  let read = 0;
  for (const c of r.cables) {
    const p = R.routePath(r, c, ctx);
    assert.ok(p.points.every(q => Math.abs(q.x) < 600 && q.z < 400 && q.z > -50), c.id);
    assert.ok(R.pathLength(p).measured < 1.5, `${c.id}: ${R.pathLength(p).measured}`);
    assert.ok(p.bends.length >= 1 && p.bends.every(b => b.need_mm === 1e9), c.id);
    assert.deepEqual(p.crossings, [], c.id);
    read++;
  }
  assert.equal(read, 16);
});
