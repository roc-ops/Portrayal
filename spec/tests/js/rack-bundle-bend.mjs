// spec/tests/js/rack-bundle-bend.mjs
// A bundle's bend radius against its trunk (#922, docs/cable-bundles-design.md
// section 5.2): the worst member present at each corner and at each pathway
// that states a radius, unknown types unchecked and never passed.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import * as B from '../../../kit/rack/bundles.js';
import {laneX} from '../../../kit/rack/route.js';
import {bendLookup} from '../../../kit/rack/cable-types.js';
import {apply} from '../../../kit/rack/commands.js';
import {describe, inspect} from '../../../kit/rack/queries.js';
import {withCable} from '../../../kit/rack/cable-rules.js';

// The installed radii #919 publishes for these types: Cat 6 at 4 x its 6 mm,
// OM4 and OS2 a fixed 25 mm (TIA-568), a passive DAC 23 mm.
const src = ['s'];
const TYPES = {
  cat6: {od_mm: 6.0, min_bend_radius: {installed: {xOD: 4, basis: 'standard', sources: src}}},
  om4: {od_mm: 3.0, min_bend_radius: {installed: {mm: 25, basis: 'standard', sources: src}}},
  os2: {od_mm: 3.0, min_bend_radius: {installed: {mm: 25, basis: 'standard', sources: src}}},
  dac: {od_mm: 5.0, min_bend_radius: {installed: {mm: 23, basis: 'convention', sources: src}}},
};
const bendOf = bendLookup(TYPES);

const RINGS = ['guide-1', 'guide-2'];
// A tray on each device. Its d of 0 puts its rings on the rail plane, with the
// lanes, so a leg from a ring to the lane runs along x alone.
const SIZES = {sw: {ru: 1, d: 515, model: 'SW'}, pp: {ru: 1, d: 100, model: 'PP'},
  tray: {ru: 1, d: 0, mount: 'rack-face', model: 'TRAY', guides: {front: RINGS}, default: 'x'}};
const chassisOf = ref => SIZES[ref] || null;
const LANE = laneX('left');
// mgr-1's ring 1 stands 24.5 mm in from the left-front lane: the corner where
// the trunk turns up the lane has room for a 24.5 mm bend. mgr-2's stands
// 66.425 mm in (x -205), a gentle corner.
const TIGHT = 24.5, GENTLE = -205 - LANE;
const routeCtx = (rack, extra = {}) => ({chassisOf, portX: () => -150,
  guidesOf: id => {
    const it = rack.items.find(i => i.id === id);
    if (it?.ref !== 'tray') return [];
    const x0 = it.label === 'mgr-1' ? LANE + TIGHT : LANE + GENTLE;
    return RINGS.map((via, k) => ({via, kind: 'ring', face: 'front', x: x0 + k * 100, box: {x: 0, y: 0, w: 40, h: 30},
                                   aperture: null, ...(extra.radius?.[`${it.label}:${via}`] ? {radius: extra.radius[`${it.label}:${via}`]} : {})}));
  }});

const end = (item, path) => ({item, path, view: 'front'});
const RT = (...ws) => ws.map(w => (Array.isArray(w) ? {lane: w[0], ru: w[1]} : {item: w.split(':')[0], via: w.split(':')[1]}));
const TRUNK = RT('i2:guide-1', ['left-front', 10], ['left-front', 30], 'i4:guide-1');
function rackWith(media, route = TRUNK) {
  let r = M.newRack({name: 'Rack 1'});
  r = M.withItem(r, {ref: 'sw', cfg: 'x', ru: 10, label: 'sw-1'}).rack;
  r = M.withItem(r, {ref: 'tray', cfg: 'x', ru: 10, label: 'mgr-1', on: 'i1', unit: 1}).rack;
  r = M.withItem(r, {ref: 'pp', cfg: 'x', ru: 30, label: 'pp-1'}).rack;
  r = M.withItem(r, {ref: 'tray', cfg: 'x', ru: 30, label: 'mgr-2', on: 'i3', unit: 1}).rack;
  media.forEach((m, k) => {
    r = withCable(r, {a: end('i1', `p${k + 1}`), b: end('i3', `q${k + 1}`), media: m}).rack;
    r = {...r, cables: r.cables.map(c => (c.id === `c${k + 1}` ? {...c, route, routeEdited: true} : c))};
  });
  return apply(r, {op: 'bundle.create', cables: r.cables.map(c => c.id), route}, {chassisOf}).rack;
}
const check = (r, ctx = {}) => B.bundleCheck(r, r.bundles[0], {route: routeCtx(r, ctx), bendOf, ...ctx});

// ── the corners of a polyline ────────────────────────────────────────────

test('cornersOf: a right angle with 120 mm to the next corner each side has room for 60 mm', () => {
  const P = (x, y, z = 0) => ({x, y, z});
  const cs = B.cornersOf([P(0, 0), P(120, 0), P(120, 120), P(240, 120)]);
  assert.deepEqual(cs, [{k: 1, angle_deg: 90, legs_mm: [120, 120], room_mm: 60},
                        {k: 2, angle_deg: 90, legs_mm: [120, 120], room_mm: 60}]);
  // one corner, legs to the ends: all of each leg, the shorter one wins
  assert.deepEqual(B.cornersOf([P(0, 0), P(40, 0), P(40, 300)]).map(c => c.room_mm), [40]);
  // 120 degrees: tan 60 = 1.732
  assert.deepEqual(B.cornersOf([P(0, 0), P(100, 0), P(150, Math.sqrt(3) * 50)]).map(c => [c.angle_deg, c.room_mm]), [[60, 173.2]]);
  assert.deepEqual(B.cornersOf([P(0, 0), P(100, 0), P(50, Math.sqrt(3) * 50)]).map(c => [c.angle_deg, c.room_mm]), [[120, 57.7]]);
});

test('cornersOf: rings in line are one leg; small turns add up to a corner; a fold has no room', () => {
  const P = (x, y, z = 0) => ({x, y, z});
  // three points in line, then a turn: one corner, its leg through the straight passes
  assert.deepEqual(B.cornersOf([P(0, 0), P(100, 0), P(200, 0), P(200, 50)]).map(c => [c.k, c.legs_mm]), [[2, [200, 50]]]);
  // turns of 0.6 degrees each against the previous segment: each is a straight
  // pass against its segment, but against the leg they add up past 1 degree
  const pts = [P(0, 0)];
  let a = 0, p = P(0, 0);
  for (let k = 0; k < 6; k++) { a += 0.6 * Math.PI / 180; p = P(p.x + 100 * Math.cos(a), p.y + 100 * Math.sin(a)); pts.push(p); }
  assert.ok(B.cornersOf(pts).length >= 1, 'small turns never made a corner');
  // a turn of 0.57 degrees is a straight pass, not a corner
  assert.deepEqual(B.cornersOf([P(0, 0), P(100, 0), P(200, 1)]), []);
  // a point on top of the one before is skipped, not a turn of 0 or 180
  assert.deepEqual(B.cornersOf([P(0, 0), P(100, 0), P(100, 0), P(200, 0)]), []);
  // doubling back: no room at all
  assert.deepEqual(B.cornersOf([P(0, 0), P(0, 300), P(0, 100)]).map(c => [c.angle_deg, c.room_mm]), [[180, 0]]);
});

// ── the bundle against its corners ───────────────────────────────────────

test('a tight corner: Cat 6 alone fits it, and one OM4 fibre makes the bundle as strict as fibre', () => {
  const copper = check(rackWith(['cat6', 'cat6', 'cat6']));
  assert.deepEqual(copper.warnings, []);
  assert.deepEqual(copper.bend.violations, []);
  assert.deepEqual([copper.bend.radius_mm, copper.bend.by], [24, 'c1']);
  const [tight, gentle] = copper.bend.points;
  assert.deepEqual(tight, {kind: 'corner', at: 'left-front U10', waypoint: {lane: 'left-front', ru: 10}, angle_deg: 90,
    legs_mm: [24.5, 889], room_mm: 24.5, source: 'legs', estimated: true, need_mm: 24, by: 'c1',
    members: ['c1', 'c2', 'c3'], unchecked: [], ok: true, short_mm: 0});
  assert.deepEqual([gentle.at, gentle.room_mm, gentle.ok], ['left-front U30', 66.4, true]);

  const mixed = check(rackWith(['cat6', 'om4', 'cat6']));
  assert.deepEqual([mixed.bend.radius_mm, mixed.bend.by], [25, 'c2']);
  assert.deepEqual(mixed.warnings, [
    'Bundle 1 turns at left-front U10 with room for a 24.5 mm bend; c2 (om4) needs 25 mm, 0.5 mm short.']);
  assert.equal(mixed.bend.violations.length, 1);
  assert.deepEqual(mixed.bend.violations[0], {kind: 'corner', at: 'left-front U10', waypoint: {lane: 'left-front', ru: 10},
    angle_deg: 90, legs_mm: [24.5, 889], room_mm: 24.5, source: 'legs', estimated: true, need_mm: 25, by: 'c2',
    members: ['c1', 'c2', 'c3'], unchecked: [], ok: false, short_mm: 0.5});
  // the gentle corner at the other end passes with the fibre in it
  assert.deepEqual(mixed.bend.points.map(p => [p.at, p.ok]), [['left-front U10', false], ['left-front U30', true]]);
});

test('a bundle command and inspect carry the bend warning; describe counts it', async () => {
  let r = rackWith(['cat6', 'os2']);
  const ctx = {route: routeCtx(r), bendOf};
  const res = apply(r, {op: 'bundle.update', id: 'b1', label: 'uplinks'}, {chassisOf, ...ctx});
  assert.ok(!res.error);
  assert.deepEqual(res.findings, [{kind: 'warning',
    text: 'uplinks turns at left-front U10 with room for a 24.5 mm bend; c2 (os2) needs 25 mm, 0.5 mm short.'}]);
  r = res.rack;
  const f = await inspect(r, 'b1', {chassisOf, ...ctx});
  assert.deepEqual(Object.keys(f.bend).sort(), ['by', 'points', 'radius_mm', 'unchecked', 'violations']);
  assert.deepEqual([f.bend.radius_mm, f.bend.by, f.bend.violations.length], [25, 'c2', 1]);
  assert.deepEqual(f.warnings, [res.findings[0].text]);
  const said = describe(r, {chassisOf, ...ctx});
  assert.ok(said.includes('b1 uplinks: 2 cables (c1-c2), about 8 mm, straps every 12 in, 1 warning.'), said);
  // without the routes nothing is measured, and bend is null rather than a pass
  assert.equal((await inspect(r, 'b1', {chassisOf, bendOf})).bend, null);
});

test('a member at its own join or peel point makes its own turn there and does not count in the bend', () => {
  let r = rackWith(['cat6', 'cat6', 'om4']);
  // c3 (OM4) leaves at left-front U10 for its a end: from there it rides up
  // the lane, so the tight corner at U10 is its own turn, not the bundle's
  r = apply(r, {op: 'bundle.peel', id: 'b1', cable: 'c3', at: {lane: 'left-front', ru: 10}, end: 'a'}, {chassisOf}).rack;
  const c = check(r);
  assert.deepEqual(c.warnings, []);
  const tight = c.bend.points.find(p => p.at === 'left-front U10');
  assert.deepEqual([tight.members, tight.need_mm, tight.ok], [['c1', 'c2'], 24, true]);
  // it still counts at the gentle corner, which it rides through
  assert.deepEqual(c.bend.points.find(p => p.at === 'left-front U30').by, 'c3');
});

test('a member of no known type is unchecked, never passed', () => {
  // one unknown: the others are checked, and it is named
  const some = check(rackWith(['cat6', '', 'cat6']));
  assert.deepEqual(some.bend.unchecked, ['c2']);
  assert.deepEqual(some.bend.points.map(p => [p.ok, p.unchecked]), [[true, ['c2']], [true, ['c2']]]);
  assert.ok(some.notes.includes("Bundle 1's bend is not checked for c2, which has no cable type with a bend radius."), some.notes);
  // every one unknown: no point is said to pass, and none fails
  const none = check(rackWith(['', '']));
  assert.deepEqual(none.bend.points.map(p => p.ok), [null, null]);
  assert.deepEqual([none.bend.radius_mm, none.bend.by, none.bend.violations, none.warnings], [null, null, [], []]);
  assert.ok(none.notes.includes("Bundle 1's bend is not checked: c1 and c2 have no cable type with a bend radius."), none.notes);
  // an unknown fibre at the tight corner hides nothing: the Cat 6 pass is
  // what is reported, with the fibre named as unchecked there
  const hidden = check(rackWith(['cat6', 'om9']));
  assert.deepEqual(hidden.bend.points[0].unchecked, ['c2']);
  assert.equal(hidden.bend.points[0].need_mm, 24);
  // no type table loaded: every member unchecked, said once
  const r = rackWith(['cat6', 'om4']);
  const bare = B.bundleCheck(r, r.bundles[0], {route: routeCtx(r)});
  assert.deepEqual([bare.bend.unchecked, bare.bend.violations, bare.warnings], [['c1', 'c2'], [], []]);
  assert.ok(bare.notes.includes("Bundle 1's bend is not checked: the cable types are not loaded."), bare.notes);
  // a type table that throws counts as no radius, never an error
  const thrown = B.bundleCheck(r, r.bundles[0], {route: routeCtx(r), bendOf: () => { throw new Error('x'); }});
  assert.deepEqual(thrown.bend.unchecked, ['c1', 'c2']);
});

test('a pathway that states a radius holds the bundle to it, straight through it too', () => {
  // a 20 mm radius stated on mgr-2 ring 1, passed straight on the way to
  // ring 2: the Cat 6 needs 24
  const on = RT('i2:guide-1', ['left-front', 10], ['left-front', 30], 'i4:guide-1', 'i4:guide-2');
  const c = check(rackWith(['cat6', 'dac'], on), {radius: {'mgr-2:guide-1': 20}});
  const p = c.bend.points.find(x => x.kind === 'pathway');
  assert.deepEqual(p, {kind: 'pathway', at: 'mgr-2 ring 1', waypoint: {item: 'i4', via: 'guide-1'}, room_mm: 20, source: 'guide',
    estimated: false, need_mm: 24, by: 'c1', members: ['c1', 'c2'], unchecked: [], ok: false, short_mm: 4});
  assert.ok(c.warnings.includes('Bundle 1 passes mgr-2 ring 1, which holds it to a 20 mm bend; c1 (cat6) needs 24 mm, 4 mm short.'), c.warnings);
  // the same pathway with no stated radius is a straight pass: no point there
  assert.deepEqual(check(rackWith(['cat6', 'dac'], on)).bend.points.map(x => x.at), ['left-front U10', 'left-front U30']);
});

test('a trunk that doubles back is always reported, unless a pathway there states the bend it keeps', () => {
  // up the lane, out along mgr-2 to ring 2, and back to ring 1: a fold at ring 2
  const fold = RT(['left-front', 10], ['left-front', 30], 'i4:guide-2', 'i4:guide-1');
  const c = check(rackWith(['dac', 'dac'], fold));
  assert.deepEqual(c.warnings, ['Bundle 1 doubles back at mgr-2 ring 2, with no room for a bend; c1 (dac) needs 23 mm.']);
  assert.deepEqual(c.bend.violations.map(v => [v.angle_deg, v.room_mm, v.short_mm]), [[180, 0, 23]]);
  // a guide that states an 80 mm radius there is what the corner has
  const g = check(rackWith(['dac', 'dac'], fold), {radius: {'mgr-2:guide-2': 80}});
  assert.deepEqual(g.warnings, []);
  assert.deepEqual(g.bend.points.filter(x => x.at === 'mgr-2 ring 2').map(x => [x.kind, x.room_mm, x.source, x.ok]),
                   [['pathway', 80, 'guide', true]]);
});
