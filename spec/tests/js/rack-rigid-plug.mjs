// A rigid plug is not a leg (#985, docs/cable-lay-design.md section 1.5). A
// DAC's or an AOC's whole 64.8 mm reach cannot bend (Amphenol C-NDAAFR-0099:
// 45 MIN required to bend the cable, measured from the diecast rear and
// including the boot), so a corner at the end of the reach has no room, and
// the cable runs on straight to a lead point before its first turn. LC, copper
// and power plugs are "not split yet" and are measured as they always were.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as R from '../../../kit/rack/route.js';
import {cornersOf} from '../../../kit/rack/route-path.js';
import * as M from '../../../kit/rack/model.js';
import * as F from './route-direct-fixture.mjs';

const mm = p => Math.round(R.pathLength(p).measured * 1e4) / 10;
const P = (x, y, z, extra = {}) => ({x, y, z, ...extra});

test('the split: a DAC and an AOC are all rigid, the others are not split yet, and no figure is a boot radius', () => {
  assert.deepEqual(Object.keys(R.PLUG_SPLIT).sort(), Object.keys(R.PLUG_REACH).sort());
  assert.deepEqual(R.PLUG_SPLIT.dac, {rigid: 64.8, boot: 0});
  assert.deepEqual(R.PLUG_SPLIT.aoc, {rigid: 64.8, boot: 0});
  for (const media of ['os2', 'om3', 'om4', 'om5', 'cat6', 'cat6a', 'power']) assert.equal(R.PLUG_SPLIT[media], null, media);
  // a split plug's rigid length and its boot are its reach
  for (const [media, s] of Object.entries(R.PLUG_SPLIT)) if (s) assert.equal(s.rigid + s.boot, R.PLUG_REACH[media], media);
  // no boot bend radius is written: a split has the two lengths and nothing else
  for (const s of Object.values(R.PLUG_SPLIT)) if (s) assert.deepEqual(Object.keys(s), ['rigid', 'boot']);
});

test('cornersOf: a leg is a leg from where the rigid part of a plug ends', () => {
  const need = c => c.map(k => [k.k, k.angle_deg, k.legs_mm, k.room_mm]);
  // a port, its reach point, and a right angle at the reach point to a point 100 on
  const whole = [P(0, 0, 0), P(0, 0, 64.8), P(100, 0, 64.8)];
  assert.deepEqual(need(cornersOf(whole, {share: 'need'})), [[1, 90, [64.8, 100], 64.8]]);
  const rigid = [P(0, 0, 0), P(0, 0, 64.8, {rigid_mm: 64.8}), P(100, 0, 64.8)];
  assert.deepEqual(need(cornersOf(rigid, {share: 'need'})), [[1, 90, [0, 100], 0]]);
  assert.deepEqual(need(cornersOf(rigid)), [[1, 90, [0, 100], 0]]);
  // run on to a lead point and the corner is there, with the run for its leg in
  const led = [P(0, 0, 0), P(0, 0, 64.8, {rigid_mm: 64.8}), P(0, 0, 94.8), P(100, 0, 94.8)];
  assert.deepEqual(need(cornersOf(led, {share: 'need'})), [[2, 90, [30, 100], 30]]);
  // the same at the far end, where the reach point is the one before the port
  const far = [P(100, 0, 94.8), P(0, 0, 94.8), P(0, 0, 64.8, {rigid_mm: 64.8}), P(0, 0, 0)];
  assert.deepEqual(need(cornersOf(far, {share: 'need'})), [[1, 90, [100, 30], 30]]);
  assert.deepEqual(need(cornersOf([P(200, 0, 64.8), P(100, 0, 64.8), P(0, 0, 64.8, {rigid_mm: 64.8}), P(0, 0, 0)], {share: 'need'})), [[2, 90, [200, 0], 0]]);
  // a partly rigid plug: the leg starts where its rigid part ends
  const part = [P(0, 0, 0), P(0, 0, 64.8, {rigid_mm: 40}), P(100, 0, 64.8)];
  assert.deepEqual(need(cornersOf(part, {share: 'need'})), [[1, 90, [24.8, 100], 24.8]]);
  // only the point next to a port is read: in the middle of a list it is a point
  const middle = [P(-50, 0, 0), P(0, 0, 0), P(0, 0, 64.8, {rigid_mm: 64.8}), P(100, 0, 64.8), P(100, 0, 200)];
  assert.deepEqual(cornersOf(middle, {share: 'need'}), cornersOf(middle.map(q => ({...q, rigid_mm: undefined})), {share: 'need'}));
  // a point with no `rigid_mm` is measured as ever
  assert.deepEqual(cornersOf(whole), cornersOf(whole.map(q => ({...q, rigid_mm: 0}))));
});

// Two leaves twenty units apart, ports on the centre line, no manager: out of
// each plug, to a lane, up it, and in. At 25 mm the cord has room everywhere
// once each plug runs on to a lead point.
function twoLeaves() {
  let r = M.withItem(M.newRack(), {ref: 'leaf', cfg: 'x', ru: 10, label: 'a'}).rack;
  r = M.withItem(r, {ref: 'leaf', cfg: 'x', ru: 30, label: 'b'}).rack;
  const cord = media => ({id: 'c1', a: {item: 'i1', path: 'p', view: 'front'}, b: {item: 'i2', path: 'p', view: 'front'}, media, route: []});
  const ctx = extra => ({chassisOf: () => ({ru: 1, w: 440, h: 44, d: 400}), guidesOf: () => [], portX: () => 0, bendOf: () => 25, ...extra});
  return {r, cord, ctx};
}
const asPoints = p => p.points.filter(q => q.at !== 'rest').map(q => [q.at, q.end ?? null, q.rigid_mm ?? null, Math.round(q.z * 10) / 10]);

test('a corner at a DAC\'s or an AOC\'s plug does not use the rigid reach as a leg: the cord runs on to a lead point and turns there', () => {
  const {r, cord, ctx} = twoLeaves();
  for (const [media, rigidLen, given] of [['dac', 1948.9, 1851.2], ['aoc', 2088.8, 1988.5]]) {
    const c = cord(media), p = R.routePath(r, c, ctx());
    // each end: the port, the reach point (flagged rigid), a lead point 1.5 radii on, and then the lane
    assert.deepEqual(asPoints(p), [['a', null, null, 0], ['reach', 'a', 64.8, 64.8], ['lead', 'a', null, 102.3], ['lane', null, null, 0], ['lane', null, null, 0],
      ['lead', 'b', null, 102.3], ['reach', 'b', 64.8, 64.8], ['b', null, null, 0]], media);
    // no corner is at the reach point, and the first is at the lead with the run for its leg in
    const cs = cornersOf(p.points, {share: 'need'});
    assert.ok(cs.every(k => p.points[k.k].at !== 'reach'), media);
    assert.deepEqual([p.points[cs[0].k].at, cs[0].legs_mm[0]], ['lead', 37.5], media);
    assert.deepEqual(p.bends, [], media);
    assert.equal(mm(p), rigidLen, media);
    // the route a page gives the reach for (a number says nothing of the rigid part) is measured as before: its turn is at the reach point
    const before = R.routePath(r, c, ctx({plugReachOf: () => R.PLUG_REACH[media]}));
    assert.deepEqual(asPoints(before), [['a', null, null, 0], ['reach', 'a', null, 64.8], ['lane', null, null, 0], ['lane', null, null, 0], ['reach', 'b', null, 64.8], ['b', null, null, 0]], media);
    assert.equal(mm(before), given, media);
    assert.ok(mm(p) > mm(before), media);
    // the cord written the other way round is the same lay turned round
    const back = R.routePath(r, {...c, a: c.b, b: c.a}, ctx());
    assert.deepEqual(asPoints(back), asPoints(p), media);
  }
});

test('a cord with no room for a lead point to be laid is found, not hidden: the corner at the rigid reach point has no room', () => {
  // the rule has nothing to turn at: held to a radius no run-out is offered
  // for (more than the lay is opened out for, 100 mm), the plug's end is a
  // corner with no room at all, and it is in `bends`
  const {r, cord, ctx} = twoLeaves();
  const p = R.routePath(r, cord('dac'), ctx({bendOf: () => 150}));
  assert.ok(p.bends.some(b => b.point === 'reach' && b.room_mm === 0 && b.short_mm === 150), JSON.stringify(p.bends.map(b => [b.point, b.room_mm])));
});

test('an LC, a copper or a power plug is not split yet: its whole reach is a leg, exactly as before', () => {
  const {r, cord, ctx} = twoLeaves();
  for (const [media, len] of [['om4', 1850], ['os2', 1850], ['cat6', 1833.1], ['cat6a', 1833.1], ['power', 1916]]) {
    const p = R.routePath(r, cord(media), ctx());
    assert.ok(p.points.every(q => !('rigid_mm' in q)), media);
    // the same route as when the page gives the reach, which is measured whole
    const given = R.routePath(r, cord(media), ctx({plugReachOf: () => R.PLUG_REACH[media]}));
    assert.deepEqual(p.points, given.points, media);
    assert.equal(mm(p), len, media);
    assert.deepEqual(p.bends, [], media);
  }
  // a cable with no media, or one named like something every object has
  for (const media of [undefined, 'constructor', '__proto__', 'nope']) {
    const p = R.routePath(r, cord(media), ctx());
    assert.ok(p.points.every(q => !('rigid_mm' in q)), String(media));
    assert.equal(mm(p), 1833.1, String(media));
  }
});

test('the reference rack\'s c9 as an AOC (rack-bend-room.mjs pins it whole): rigid, the turn at its far plug end has no room', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  const aoc = {...r.cables.find(c => c.id === 'c9'), media: 'aoc'}, rack = {...r, cables: [aoc]};
  const p = R.routePath(rack, aoc, ctx);
  assert.deepEqual(p.bends.map(b => [b.point, b.room_mm, b.short_mm]), [['reach', 0, 30]]);
  assert.equal(mm(p), 723);
  // given as a number it is measured whole, as rack-bend-room.mjs has it, with no finding
  assert.deepEqual(R.routePath(rack, aoc, {...ctx, plugReachOf: () => R.PLUG_REACH.aoc}).bends, []);
  // all sixteen cords as AOCs: 33 findings
  assert.equal(r.cables.reduce((n, c) => { const a = {...c, media: 'aoc'}; return n + R.routePath({...r, cables: [a]}, a, ctx).bends.length; }, 0), 33);
});

test('the issue\'s count of corners that depend on the plug being a leg, on the reference rack\'s sixteen cords', () => {
  // forcing a rigid plug of the LC reach on each cord's reach points: corners
  // that have the room they need only because the plug is a leg. 24 on the
  // sixteen cords today (the issue counted 23 when it was written)
  const r = F.rack(), ctx = F.ctxOf(r);
  let depend = 0;
  const cables = new Set();
  for (const c of r.cables) {
    const p = R.routePath(r, c, ctx), need = 25;
    const whole = cornersOf(p.points, {share: 'need'});
    const rigid = cornersOf(p.points.map(q => (q.at === 'reach' ? {...q, rigid_mm: R.PLUG_REACH.om4} : q)), {share: 'need'});
    for (const k of rigid) if (k.room_mm < need && whole.find(x => x.k === k.k)?.room_mm >= need) { depend++; cables.add(c.id); }
  }
  assert.deepEqual([depend, cables.size], [24, 16]);
});

test('the reference rack of #949 is unchanged: its sixteen LC cords, their corners and the five that turn 90 degrees where the plug ends', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  const LENGTHS = {c1: 514.2, c2: 499.8, c3: 502.7, c4: 491.4, c5: 522, c6: 515, c7: 505.8, c8: 547, c9: 611.2, c10: 613.2, c11: 616.1, c12: 623.4,
    c13: 645.5, c14: 616.9, c15: 648, c16: 576.3};
  let corners = 0, atPlug = 0;
  for (const c of r.cables) {
    assert.equal(c.media, 'om4', c.id);
    const p = R.routePath(r, c, ctx);
    assert.equal(mm(p), LENGTHS[c.id], c.id);
    assert.deepEqual(p.bends, [], c.id);
    assert.ok(p.points.every(q => !('rigid_mm' in q)), c.id);
    const cs = cornersOf(p.points, {share: 'need'});
    corners += cs.length;
    atPlug += cs.filter(k => p.points[k.k].at === 'reach' && Math.abs(k.angle_deg - 90) <= 0.5).length;
  }
  assert.deepEqual([r.cables.length, corners, atPlug], [16, 98, 5]);
});
