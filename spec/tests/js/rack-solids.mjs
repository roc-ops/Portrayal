// Solid bodies, detours and the crosses-body finding (#949,
// docs/cable-lay-design.md section 1). Every count asserted here was measured
// on these fixtures and is asserted exactly, so a check that found nothing
// cannot pass.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as R from '../../../kit/rack/route.js';
import * as S from '../../../kit/rack/solids.js';
import * as Q from '../../../kit/rack/queries.js';
import {cableScheduleRows} from '../../../kit/rack/export-data.js';
import {RU, OPENING, RAIL_W} from '../../../kit/rack/rails.js';
import * as M from '../../../kit/rack/model.js';
import * as F from './cable-solids-fixture.mjs';

const raw = path => path.points.filter(p => p.at !== 'detour');
const diameterOf = c => R.DIAMETERS[c.media];
// what a path's legs cross, without the detours: the route as it was drawn
// before solids
const before = (rack, c, ctx) => {
  const pts = raw(R.routePath(rack, c, ctx)), s = S.solidsOf(rack, ctx), out = [];
  for (let k = 1; k < pts.length; k++) out.push(...S.legCrossings(pts[k - 1], pts[k], s, {diameter: diameterOf(c)}));
  return out;
};
const tag = x => `${x.solid.item}:${x.solid.part}`;

// The owner's rack, with a switch far below (U5) whose cable is routed by hand
// through ring 2 of the lacer. Since the automatic route runs a patch along
// one manager (#949, section 4.1), c1 to c5 run along the lacer and never
// reach a lane; c7 to c11 take the same five a ends to the switch at U5,
// which has no manager, so they run out through the lacer to the left lane
// as c1 to c5 did before.
function owner() {
  const r = F.add(F.ownerRack(), 'sw', 5, {label: 'sw-low'});
  const c6 = F.cable('c6', F.end('i5', 'p100'), F.end('i2', 'bay3'), 'om4',
    {route: [{item: 'i3', via: 'guide-2'}], routeEdited: true});
  const lane = F.OWNER_CABLES.map((c, i) => F.cable(`c${7 + i}`, c.a, F.end('i5', 'p100'), c.media));
  return {rack: {...r, cables: [...F.OWNER_CABLES, c6, ...lane]}, ctx: F.ctxOf({ports: {i5: {p100: -100}}})};
}

test('the solids of the owner\'s rack: four envelopes and the lacer\'s fifteen plates, placed', () => {
  const {rack, ctx} = owner();
  const s = S.solidsOf(rack, ctx);
  assert.equal(s.length, 4 + 15);
  assert.deepEqual(s.filter(x => x.part === 'envelope').map(x => x.item), ['i1', 'i2', 'i4', 'i5']);
  // the strip of the tray floor: 3 mm up U12, the sheet (1.5) thick, from 48.8
  // to 110 out of the front rail plane, across the 448.4 between the ears
  const strip = s.find(x => x.item === 'i3' && x.part === 'tray/floor' && x.box.x1 - x.box.x0 > 400).box;
  const near = (a, b) => Math.abs(a - b) < 1e-9;
  assert.ok(near(strip.y0, 11 * RU + 1.5) && near(strip.y1, 11 * RU + 3), JSON.stringify(strip));
  assert.ok(near(strip.z0, 48.8) && near(strip.z1, 110) && near(strip.x0, -224.2) && near(strip.x1, 224.2));
  // a box device is its envelope, behind the front rail plane
  const panel = s.find(x => x.item === 'i2').box;
  assert.deepEqual([panel.x0, panel.x1, panel.z0, panel.z1], [-224, 224, -227, 0]);
});

test('owner\'s fixture: today\'s routes cross the lacer\'s plates; with the detours none does', () => {
  const {rack, ctx} = owner();
  const got = Object.fromEntries(rack.cables.map(c => [c.id, before(rack, c, ctx).map(tag)]));
  // From the switch below to the panel, the automatic route runs along the
  // lacer and crosses nothing; from the switch below to the one at U5 it
  // leaves ring 1 for the lane at U11 past the end of the tray, through its
  // web; the hand route from U5 rises through the tray floor to ring 2. From
  // the switch above, nothing.
  assert.deepEqual(got, {c1: [], c2: [], c3: [], c4: [], c5: [], c6: ['i3:tray/floor'],
    c7: ['i3:web-a/plate'], c8: ['i3:web-a/plate'], c9: ['i3:web-a/plate'], c10: [], c11: []});
  assert.equal(Object.values(got).filter(x => x.length).length, 4);
  // after the detours: no finding at all
  assert.deepEqual(R.bodyFindings(rack, ctx), []);
  for (const c of rack.cables) {
    const p = R.routePath(rack, c, ctx);
    assert.deepEqual(p.crossings, [], c.id);
    // one detour where it crossed, counted in the length; none elsewhere
    assert.equal(p.detours.length, got[c.id].length, c.id);
    const grew = R.pathLength(p).measured - R.pathLength({points: raw(p)}).measured;
    assert.ok(got[c.id].length ? grew > 0.005 : grew === 0, `${c.id} grew ${grew}`);
  }
  // the floor detour of c6 goes over the FRONT edge of the tray (section 1.3
  // rule 1): from its plug's reach point (#960) up and out in front of the
  // strip, clear by its radius and CLEAR, and back in to ring 2. The point
  // level with the port is pulled taut: the reach point already stands
  // 27.6 out, and sees the corner at ring height past the edge.
  const [d6] = R.routePath(rack, rack.cables[5], ctx).detours;
  assert.deepEqual(d6.between, [{end: 'a'}, {item: 'i3', via: 'guide-2'}]);
  assert.deepEqual(d6.points.map(p => Math.round(p.z * 10) / 10), [110 + 1.5 + S.CLEAR]);
  // a detour point is not stored: the cable's route is as written
  assert.deepEqual(rack.cables[5].route, [{item: 'i3', via: 'guide-2'}]);
});

test('a tray on the rear rails is gone round by its front edge too, which faces the rear', () => {
  let r = F.add({...F.ownerRack(), items: []}, 'panel', 12, {face: 'rear'});
  r = F.add(r, 'fhd-cmp5dr', 12, {on: 'i1', unit: 1, face: 'rear'});
  r = F.add(r, 'sw', 5, {face: 'rear'});
  const c = F.cable('c1', F.end('i3', 'p'), F.end('i1', 'q'), 'om4', {route: [{item: 'i2', via: 'guide-2'}], routeEdited: true});
  const ctx = F.ctxOf({guides: {i2: F.RINGS.map(g => ({...g, face: 'rear'}))}, ports: {i3: {p: 100}, i1: {q: 30}}});
  ctx.guidesOf = id => (id === 'i2' ? F.RINGS.map(g => ({...g, face: 'rear'})) : []);
  const p = R.routePath({...r, cables: [c]}, c, ctx);
  assert.deepEqual(p.crossings, []);
  const [d] = p.detours;
  // the rear rail plane is at -740, the tray stands 110 behind it; from the
  // plug's reach point, 27.6 behind the rear face (#960), one corner past the edge
  assert.deepEqual(d.points.map(q => Math.round(q.z * 10) / 10), [-740 - 110 - 1.5 - S.CLEAR]);
});

test('a cable lying against the plate is not crossing it; a leg through it is, on either face', () => {
  const {rack, ctx} = owner();
  const s = S.solidsOf(rack, ctx);
  const top = 11 * RU + 3, under = 11 * RU + 1.5, r = 1.5;
  const legs = {
    // the centre line one radius above the floor, along the strip
    'lying on the resting face': [{x: -150, y: top + r, z: 80}, {x: 150, y: top + r, z: 80}],
    // one radius below it, strapped up to it
    'lying against the held face': [{x: -150, y: under - r, z: 80}, {x: 150, y: under - r, z: 80}],
    // exactly on the face: not inside
    'on the face': [{x: -150, y: top, z: 80}, {x: 150, y: top, z: 80}],
    // from one face to the other inside the footprint
    'top to underside': [{x: 0, y: top + r, z: 80}, {x: 0, y: under - r, z: 80}],
    'underside to top, slanting': [{x: -100, y: under - 20, z: 60}, {x: -60, y: top + 20, z: 100}],
  };
  const found = Object.fromEntries(Object.entries(legs).map(([k, [a, b]]) =>
    [k, S.legCrossings(a, b, s, {diameter: 2 * r}).map(x => `${x.solid.item}:${x.solid.part}`)]));
  assert.deepEqual(found, {'lying on the resting face': [], 'lying against the held face': [], 'on the face': [],
    'top to underside': ['i3:tray/floor'], 'underside to top, slanting': ['i3:tray/floor']});
});

test('a tie slot is never an opening: a leg through one crosses the floor', () => {
  const {rack, ctx} = owner();
  // slot 1a, 22.5 x 3 at tray x 54.85, 95 back on the plan: rack x -169.35
  // to -146.85, 12 to 15 out from the front edge. A 3 mm cord down its middle.
  const x = -158, z = 110 - 13.5;
  const hit = S.legCrossings({x, y: 11 * RU + 20, z}, {x, y: 11 * RU - 20, z}, S.solidsOf(rack, ctx), {diameter: 3});
  assert.deepEqual(hit.map(h => h.solid.part), ['tray/floor']);
});

// ── ducts ──────────────────────────────────────────────────────────────────
function ducted() {
  const {rack, ctx} = owner();
  return {rack: {...rack, zeroU: [{id: 'z1', ref: 'cmv-sfd45u5w', cfg: 'base', at: 'left-front', offsetMm: 0}]}, ctx};
}

test('a vertical duct is its walls and back, and an automatic route through its lane finds nothing', () => {
  const {rack, ctx} = ducted();
  const duct = S.solidsOf(rack, ctx).filter(x => x.item === 'z1');
  assert.deepEqual(duct.map(x => x.part), ['base/floor', 'wall-left/root', 'wall-right/root']);
  // its back is behind the rail plane, and its channel is where the lane
  // runs: the lane point (z 0) is inside it, clear of the back and the walls
  const lane = R.laneXAt(rack, 'left-front', 11, ctx.chassisOf);
  const back = duct[0].box;
  assert.ok(back.z1 < 0 && back.x0 < lane && lane < back.x1, JSON.stringify(back));
  let through = 0;
  for (const c of rack.cables.filter(c => c.routeEdited !== true)) {
    const p = R.routePath(rack, c, ctx);
    through += p.points.some(q => q.at === 'lane' && Math.abs(q.x - lane) < 1e-9) ? 1 : 0;
    // into the channel through its open front: nothing of the duct crossed
    assert.deepEqual(before(rack, c, ctx).filter(x => x.solid.item === 'z1'), [], c.id);
    assert.deepEqual(p.crossings, [], c.id);
  }
  assert.equal(through, 5);
  // and a leg straight back through its base, away from a pass-through, is found
  const y = 30 * RU;
  const hit = S.legCrossings({x: lane, y, z: 0}, {x: lane, y, z: -300}, duct, {diameter: 6});
  assert.deepEqual(hit.map(h => h.solid.part), ['base/floor']);
});

test('a duct whose fingers are its own body (CMV-5U3W): a route through its channel goes straight through', () => {
  // the 5U finger duct on the left rail beside the panel, U12 to U16
  const r = F.add(F.ownerRack(), 'cmv-5u3w', 12, {side: 'left', label: 'duct'});
  const s = S.solidsOf(r, F.ctxOf()).filter(x => x.item === 'i5');
  // only its flange, behind the channel: its spine, bars and finger tips
  // stand inside the duct's footprint and are left open
  assert.deepEqual(s.map(x => x.part), ['flange/floor']);
  const flange = s[0].box;
  const x = flange.x0 + 7.3;            // the middle of the 14.6 channel
  const ctx = F.ctxOf({guides: {i5: [{via: 'duct', kind: 'duct', face: 'front', run: 'y', x}]}});
  const c = F.cable('c1', F.end('i4', 'p150'), F.end('i2', 'bay2'), 'om4',
    {route: [{item: 'i5', via: 'duct'}], routeEdited: true});
  const p = R.routePath({...r, cables: [c]}, c, ctx);
  const at = p.points.find(q => q.at === 'pathway');
  assert.ok(at.z > flange.z1, `the duct point stands in front of its flange: ${at.z} > ${flange.z1}`);
  assert.deepEqual(p.crossings, []);
  assert.deepEqual(p.detours.filter(d => d.between.some(w => w.item === 'i5')), []);
});

// ── a closed enclosure ─────────────────────────────────────────────────────
// fhd-encl in the fixture catalogue is written by hand: 448 x 44 x 432.8,
// shell walls 1 mm, a patch plate at the front, one 40 x 24 grommet in the
// rear wall at device x 50 to 90 (rack x -174 to -134) and y 10 to 34. The
// library derives no such entry yet (step 6 of the note); this holds the
// kit's reading of walls and holes, which the sheet parts' pass-throughs use.
function enclosure(grommet = null) {
  let r = F.add(F.add({...F.ownerRack(), items: []}, 'sw', 9, {label: 'sw-9'}), 'fhd-encl', 10, {label: 'encl'});
  r = F.add(r, 'rear', 10, {face: 'rear', label: 'rear-10'});
  const ctx = F.ctxOf();
  if (grommet) {
    const encl = structuredClone(F.CAT['fhd-encl']);
    encl.solids[4].holes[0].size = grommet;
    const base = ctx.chassisOf;
    ctx.chassisOf = ref => (ref === 'fhd-encl' ? encl : base(ref));
  }
  return {rack: r, ctx};
}
const U10 = 9.5 * RU, U9 = 8.5 * RU;

test('a closed enclosure: through its floor or its rear wall is found, through its grommet it is not', () => {
  const {rack, ctx} = enclosure();
  const s = S.solidsOf(rack, ctx);
  assert.deepEqual(s.filter(x => x.item === 'i2').map(x => x.part),
    ['shell/top', 'shell/bottom', 'shell/left', 'shell/right', 'shell/rear', 'plate']);
  const parts = (a, b, d = 3) => S.legCrossings(a, b, s, {diameter: d}).map(x => x.solid.part);
  // from below up into the enclosure, to its grommet: through the floor
  assert.deepEqual(parts({x: -154, y: U9, z: -300}, {x: -154, y: U10, z: -432.8}), ['shell/bottom']);
  // from behind, straight in through the rear wall to the front: the wall,
  // then the patch plate from inside
  assert.deepEqual(parts({x: 100, y: U10, z: -600}, {x: 100, y: U10, z: 0}), ['shell/rear', 'plate']);
  // the same line through the grommet: the wall is not crossed
  assert.deepEqual(parts({x: -154, y: U10, z: -600}, {x: -154, y: U10, z: -300}), []);
  // a cable fatter than the grommet's smaller side (24 mm) does cross the wall
  assert.deepEqual(parts({x: -154, y: U10, z: -600}, {x: -154, y: U10, z: -300}, 25), ['shell/rear']);
});

test('a grommet too small for the cable is no opening; one it fits is (the fit rule, mutated both ways)', () => {
  const leg = [{x: -154, y: U10, z: -600}, {x: -154, y: U10, z: -300}];
  for (const [size, d, want] of [[[40, 24], 6, 0], [[40, 5.9], 6, 1], [[6, 40], 6, 0], [[5.99, 40], 6, 1]]) {
    const {rack, ctx} = enclosure(size);
    const got = S.legCrossings(...leg, S.solidsOf(rack, ctx), {diameter: d}).length;
    assert.equal(got, want, `grommet ${size} for a ${d} mm cable`);
  }
});

// ── a zero-U PDU over the gutter ───────────────────────────────────────────
function pdu(at = 'left-front') {
  const {rack, ctx} = owner();
  return {rack: {...rack, zeroU: [{id: 'z2', ref: 'pdu', cfg: 'base', at, offsetMm: 0}]}, ctx};
}

test('a zero-U PDU standing in the gutter pushes the lane outboard of it, and routes beside it find nothing', () => {
  const {rack, ctx} = pdu();
  // the PDU (56 wide) stands against the upright's outer face; the lane runs
  // in a gutter as wide as the usual one just outboard of it, at the units it spans
  const out = -(OPENING / 2 + RAIL_W + 56 + R.LANE_GAP / 2);
  assert.equal(R.laneXAt(rack, 'left-front', 11, ctx.chassisOf), out);
  // it spans U1-U30 (1700 mm, ru 30): outboard at its top unit, the gutter above it
  assert.equal(R.laneXAt(rack, 'left-front', 1, ctx.chassisOf), out);
  assert.equal(R.laneXAt(rack, 'left-front', 30, ctx.chassisOf), out);
  assert.equal(R.laneXAt(rack, 'left-front', 31, ctx.chassisOf), R.laneX('left'));
  assert.equal(R.laneXAt(rack, 'right-front', 11, ctx.chassisOf), R.laneX('right'));
  // the PDU is its envelope, and the lane points are clear of it
  const box = S.solidsOf(rack, ctx).find(x => x.item === 'z2').box;
  assert.ok(out < box.x0, `${out} < ${box.x0}`);
  let beside = 0;
  for (const c of rack.cables) {
    const p = R.routePath(rack, c, ctx);
    beside += p.points.some(q => q.at === 'lane' && q.x === out) ? 1 : 0;
    assert.deepEqual(p.crossings, [], c.id);
  }
  assert.equal(beside, 5);
  assert.deepEqual(R.bodyFindings(rack, ctx), []);
  // a rear PDU on a four-post pushes the rear lane only
  const rear = pdu('left-rear');
  assert.equal(R.laneXAt(rear.rack, 'left-rear', 11, rear.ctx.chassisOf), out);
  assert.equal(R.laneXAt(rear.rack, 'left-front', 11, rear.ctx.chassisOf), R.laneX('left'));
});

test('a cable to the lane beside a rear PDU goes round it on the rack side, never over its outlet face', () => {
  // a four-post: the switch's rear ports at the rear rail plane (-740), a
  // zero-U PDU on the left-rear upright, its outlet face looking out of the
  // back of the rack
  let r = F.add({...F.ownerRack(), items: []}, 'rear', 10, {face: 'rear', label: 'rear-10'});
  r = F.add(r, 'rear', 20, {face: 'rear', label: 'rear-20'});
  r = {...r, zeroU: [{id: 'z2', ref: 'pdu', cfg: 'base', at: 'left-rear', offsetMm: 0}]};
  const ctx = F.ctxOf({ports: {i1: {p: -200}, i2: {q: -180}}});
  const c = F.cable('c1', F.end('i1', 'p', 'front'), F.end('i2', 'q', 'front'), 'cat6');
  const rack = {...r, cables: [c]};
  const box = S.solidsOf(rack, ctx).find(x => x.item === 'z2').box;
  // centred on the 34 mm post behind the rear rail: its outlet face is behind
  // the rail plane, outside the frame
  assert.ok(box.z0 < -740 && box.z1 > -740, JSON.stringify(box));
  const p = R.routePath(rack, c, ctx);
  assert.deepEqual(p.crossings, []);
  // both ports run to the lane outboard of the PDU, each round it once
  assert.equal(p.detours.length, 2);
  assert.ok(p.points.some(q => q.at === 'lane' && q.x < box.x0));
  // and no point of the path lies over its outlet face. A plug in a rear
  // port reaches past the PDU's outlet plane (cat6, 39.4 behind the rail,
  // #960), so the cable starts behind it: inboard of the PDU, beside it, and
  // never across its face
  const over = p.points.filter(q => q.z < box.z0 - 1e-9 && q.x > box.x0 - 1e-9 && q.x < box.x1 + 1e-9);
  assert.deepEqual(over, [], JSON.stringify(over));
  const behind = p.points.filter(q => q.z < box.z0 - 1e-9);
  assert.deepEqual(behind.map(q => [q.at, q.z]), [['reach', -779.4], ['detour', -779.4], ['detour', -779.4], ['reach', -779.4]]);
  // it goes round on the rack side instead, in front of the PDU
  assert.ok(p.detours.every(d => d.points.some(q => q.z > box.z1)), JSON.stringify(p.detours));
});

test('the mirror: a front PDU, on a four-post and on a two-post, is gone round behind it, never in front of its outlet face', () => {
  for (const [kind, at] of [['four-post', 'left-front'], ['two-post', 'left']]) {
    // two switches on the front rails, a zero-U PDU on the left upright
    // looking out of the front of the rack, and a cable between their front
    // ports by the left lane
    let r = F.add({...M.newRack({kind}), items: []}, 'sw', 10, {label: 'sw-10'});
    r = F.add(r, 'sw', 20, {label: 'sw-20'});
    r = {...r, zeroU: [{id: 'z2', ref: 'pdu', cfg: 'base', at, offsetMm: 0}]};
    const ctx = F.ctxOf({ports: {i1: {p: -200}, i2: {q: -180}}});
    const c = F.cable('c1', F.end('i1', 'p'), F.end('i2', 'q'), 'cat6');
    const rack = {...r, cables: [c]};
    const box = S.solidsOf(rack, ctx).find(x => x.item === 'z2').box;
    // centred on the 34 mm post behind the front rail: its outlet face is in
    // front of the rail plane
    assert.ok(box.z1 > 0 && box.z0 < 0, `${kind}: ${JSON.stringify(box)}`);
    const p = R.routePath(rack, c, ctx);
    assert.deepEqual(p.crossings, [], kind);
    assert.equal(p.detours.length, 2, kind);
    assert.ok(p.points.some(q => q.at === 'lane' && q.x < box.x0), kind);
    // no point of the path lies over its outlet face: the plugs reach past
    // its outlet plane (cat6, 39.4 out, #960), so the cable starts in front
    // of it, inboard of the PDU, and goes round behind it from there
    const over = p.points.filter(q => q.z > box.z1 + 1e-9 && q.x > box.x0 - 1e-9 && q.x < box.x1 + 1e-9);
    assert.deepEqual(over, [], `${kind}: ${JSON.stringify(over)}`);
    const ahead = p.points.filter(q => q.z > box.z1 + 1e-9);
    assert.deepEqual(ahead.map(q => q.at), ['reach', 'detour', 'detour', 'reach'], kind);
    assert.ok(ahead.every(q => q.z === 39.4 && q.x > box.x1), kind);
    // it goes round behind the PDU, the side facing into the rack
    assert.ok(p.detours.every(d => d.points.some(q => q.z < box.z0)), `${kind}: ${JSON.stringify(p.detours)}`);
  }
});

// ── what the rules cannot clear ────────────────────────────────────────────
// Contrived: a deep shelf standing out of the rails over the lacer's own
// unit, so ring 1, where every automatic route here goes, is inside it. A leg
// that ends inside a body cannot be taken round it; the route is left as
// drawn and reported.
function shelved() {
  const {rack, ctx} = owner();
  return {rack: F.add(rack, 'shelf', 12, {label: 'shelf'}), ctx};
}
const names = id => ({i1: 'sw-dn', i2: 'fhd-panel', i3: 'lacer', i4: 'sw-up', i5: 'sw-low', i6: 'shelf'}[id] ?? id);

test('what the rules cannot clear is a finding, with its sentence, in inspect, describe and the schedule', async () => {
  const {rack, ctx} = shelved();
  const f = R.bodyFindings(rack, ctx, names);
  assert.ok(f.every(x => x.kind === 'crosses-body'));
  const by = {};
  for (const x of f) by[x.cable] = (by[x.cable] ?? 0) + 1;
  // every leg that starts or ends at a ring inside the shelf; from the
  // switch below to the one at U5, the leg past the web that can no longer
  // be taken round it; and the plug of each panel port (c1 to c6), which
  // reaches out of the panel into the shelf (#960)
  assert.deepEqual(by, {c1: 8, c2: 4, c3: 4, c4: 4, c5: 4, c6: 5, c7: 4, c8: 6, c9: 4, c10: 3, c11: 5});
  assert.equal(f.length, 51);
  assert.equal(f.filter(x => x.item === 'i6').length, 51 - 3 - 1);
  const c7 = f.filter(x => x.cable === 'c7');
  assert.deepEqual(c7.slice(0, 4).map(x => [x.item, x.part, x.between]), [
    ['i6', 'envelope', [{end: 'a'}, {item: 'i3', via: 'guide-1'}]],
    ['i6', 'envelope', [{item: 'i3', via: 'guide-1'}, {item: 'i3', via: 'guide-1'}]],
    ['i6', 'envelope', [{item: 'i3', via: 'guide-1'}, {lane: 'left-front', ru: 11}]],
    ['i3', 'web-a/plate', [{item: 'i3', via: 'guide-1'}, {lane: 'left-front', ru: 11}]]]);
  assert.equal(c7[2].text, 'c7 passes through shelf between lacer ring 1 and left-front U11: '
    + 'route it round shelf, or through a ring or a pass-through it fits.');
  assert.equal(c7[1].text, 'c7 passes through shelf at lacer ring 1: '
    + 'route it round shelf, or through a ring or a pass-through it fits.');
  assert.equal(c7[0].text.slice(0, 50), 'c7 passes through shelf between its port on sw-dn ');
  assert.equal(c7[1].at.length, 3);
  // the route output of inspect: `crosses`
  const route = {...ctx};
  const info = await Q.inspect(rack, 'c7', {chassisOf: ctx.chassisOf, route});
  assert.deepEqual(info.route.crosses.map(x => [x.item, x.part]), c7.map(x => [x.item, x.part]));
  assert.deepEqual(info.route.crosses[2].between, c7[2].between);
  assert.deepEqual(info.route.crosses[2].at, c7[2].at);
  // describe: one line of totals
  const text = Q.describe(rack, {chassisOf: ctx.chassisOf, route});
  assert.match(text, /^Findings: 11 cables cross a body\.$/m);
  // the cable schedule's notes
  const {rows} = cableScheduleRows(rack, new Map(), rack.items, null, {bodies: f});
  assert.ok(rows.find(x => x.id === 'c7').notes.includes(c7[2].text));
  // and without the shelf, nothing
  const {rack: clean} = owner();
  assert.ok(!Q.describe(clean, {chassisOf: ctx.chassisOf, route}).includes('Findings:'));
});

test('a leg through the tray floor that cannot be gone round is told to go over its front edge', () => {
  const {rack, ctx} = shelved();
  const f = R.bodyFindings(rack, ctx, names).filter(x => x.cable === 'c6');
  // from U5 up to ring 2, inside the shelf: through the shelf and the floor
  assert.deepEqual(f.map(x => [x.item, x.part]), [['i6', 'envelope'], ['i3', 'tray/floor'], ['i6', 'envelope'], ['i6', 'envelope'],
    ['i6', 'envelope']]);
  // the last: its plug in the panel port, reaching into the shelf (#960)
  assert.deepEqual(f[4].between, [{end: 'b'}, {end: 'b'}]);
  assert.equal(f[4].text, 'c6 passes through shelf at its port on fhd-panel: '
    + 'route it round shelf, or through a ring or a pass-through it fits.');
  assert.equal(f[1].text, 'c6 passes through lacer tray between its port on sw-low and lacer ring 2: '
    + 'route it over the front edge of the tray, or through a ring.');
});

// ── a leg that meets two bodies ────────────────────────────────────────────
test('a way round one body that meets a second is itself gone round, and the result is pulled taut', () => {
  const box = (x0, x1, y0, y1, z0, z1, part) => ({item: part, part, box: {x0, x1, y0, y1, z0, z1}, away: 1});
  const A = box(40, 60, -10, 10, -10, 10, 'A');
  // every plane round A but one is blocked: z below by C, y both ways by D and
  // E; the plane above, z 15, is crossed by B, a small post that can itself be
  // gone round
  const B = box(20, 30, -5, 5, 12, 18, 'B');
  const C = box(-50, 150, -100, 100, -40, -12, 'C');
  const D = box(-50, 150, 12, 40, -11, 11, 'D');
  const E = box(-50, 150, -40, -12, -11, 11, 'E');
  const a = {x: 0, y: 0, z: 0}, b = {x: 100, y: 0, z: 0};
  const pts = S.detour(a, b, [A, B, C, D, E], {diameter: 0});
  assert.ok(Array.isArray(pts), JSON.stringify(pts));
  // over A by the one plane left, z 15, and over B on the way: B's top (18)
  // and CLEAR at the start, A's top (10) and CLEAR at the end, pulled taut
  assert.deepEqual(pts, [{x: 0, y: 0, z: 18 + S.CLEAR}, {x: 100, y: 0, z: 10 + S.CLEAR}]);
  const all = [a, ...pts, b];
  for (let k = 1; k < all.length; k++) assert.deepEqual(S.legCrossings(all[k - 1], all[k], [A, B, C, D, E]), [], `leg ${k}`);
  // pulled taut: no point can be dropped
  for (let k = 1; k < all.length - 1; k++)
    assert.ok(S.legCrossings(all[k - 1], all[k + 1], [A, B, C, D, E]).length, `point ${k} could be dropped`);
  // and an end inside a body cannot be cleared at all
  assert.equal(S.detour({x: 50, y: 0, z: 0}, b, [A]), null);
});

test('a part with no width or no depth, or a sheet part from a catalogue without solids, is not solid', () => {
  const {rack, ctx} = owner();
  const old = {...ctx, chassisOf: ref => (ref === 'fhd-cmp5dr' ? {...F.CAT['fhd-cmp5dr'], solids: undefined}
    : ref === 'sw' ? {ru: 1} : ctx.chassisOf(ref))};
  assert.deepEqual(S.solidsOf(rack, old).map(x => `${x.item}:${x.part}`), ['i2:envelope']);
  // and then routes are as they were before solids: no detour, no finding
  for (const c of rack.cables) assert.deepEqual(R.routePath(rack, c, old).detours, [], c.id);
  // a zero-U part that carries a lane, from such a catalogue, is a pathway
  // still, never its envelope, sheet or not: the lane runs through it, so its
  // envelope would hold every route
  const d = ducted();
  for (const shell of ['sheet', undefined]) {
    const oldDuct = {...d.ctx, chassisOf: ref => (ref === 'cmv-sfd45u5w' ? {...F.CAT[ref], solids: undefined, shell}
      : d.ctx.chassisOf(ref))};
    assert.deepEqual(S.solidsOf(d.rack, oldDuct).filter(x => x.item === 'z1'), [], String(shell));
    assert.deepEqual(R.bodyFindings(d.rack, oldDuct), [], String(shell));
  }
});

test('a turned device and a rear one are placed as the 3D scene places them', () => {
  const r = F.add(F.add({...F.ownerRack(), items: []}, 'panel', 20, {turned: true}), 'panel', 22, {face: 'rear'});
  const s = S.solidsOf(r, F.ctxOf());
  const z = s.map(x => [x.box.z0, x.box.z1]);
  assert.deepEqual(z, [[-227, 0], [-740, -740 + 227]]);
  // and a rack-face part on the rear rails stands out behind them
  const r2 = F.add({...F.ownerRack(), items: []}, 'fhd-cmp5dr', 20, {face: 'rear'});
  const strip = S.solidsOf(r2, F.ctxOf()).find(x => x.part === 'tray/floor' && x.box.x1 - x.box.x0 > 400).box;
  assert.ok(Math.abs(strip.z0 - (-740 - 110)) < 1e-9 && Math.abs(strip.z1 - (-740 - 48.8)) < 1e-9, JSON.stringify(strip));
});
