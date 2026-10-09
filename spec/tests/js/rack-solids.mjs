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
import {RU} from '../../../kit/rack/rails.js';
import * as F from './cable-solids-fixture.mjs';

const raw = path => path.points.filter(p => p.at !== 'detour');
const before = (rack, c, ctx) => S.pathCrossings(raw(R.routePath(rack, c, ctx)), S.solidsOf(rack, ctx),
  {diameter: R.cableDiameter(c, ctx)});
const tag = x => `${x.solid.item}:${x.solid.part}`;

// The owner's rack, with a switch far below (U5) whose cable is routed by hand
// through ring 2 of the lacer.
function owner() {
  const r = F.add(F.ownerRack(), 'sw', 5, {label: 'sw-low'});
  const c6 = F.cable('c6', F.end('i5', 'p100'), F.end('i2', 'bay3'), 'om4',
    {route: [{item: 'i3', via: 'guide-2'}], routeEdited: true});
  return {rack: {...r, cables: [...F.OWNER_CABLES, c6]}, ctx: F.ctxOf({ports: {i5: {p100: -100}}})};
}

test('the solids of the owner\'s rack: four envelopes and the lacer\'s seventeen plates, placed', () => {
  const {rack, ctx} = owner();
  const s = S.solidsOf(rack, ctx);
  assert.equal(s.length, 4 + 17);
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
  // From the switch below, the automatic route leaves ring 1 for the lane at
  // U11 past the end of the tray, through its web; the hand route from U5
  // rises through the tray floor to ring 2. From the switch above, nothing.
  assert.deepEqual(got, {c1: ['i3:web-a/plate'], c2: ['i3:web-a/plate'], c3: ['i3:web-a/plate'],
    c4: [], c5: [], c6: ['i3:tray/floor']});
  const crossing = Object.values(got).filter(x => x.length).length;
  assert.equal(crossing, 4);
  // after the detours: no finding at all
  assert.deepEqual(R.bodyFindings(rack, ctx), []);
  for (const c of rack.cables) {
    const p = R.routePath(rack, c, ctx);
    assert.deepEqual(p.crossings, [], c.id);
    // each detour is two points, counted in the length and only where it crossed
    assert.equal(p.detours.length, got[c.id].length, c.id);
    assert.equal(p.points.filter(x => x.at === 'detour').length, 2 * got[c.id].length, c.id);
    const grew = R.pathLength(p).measured - R.pathLength({points: raw(p)}).measured;
    assert.ok(got[c.id].length ? grew > 0.005 : grew === 0, `${c.id} grew ${grew}`);
  }
  // the floor detour of c6 goes over the near edge: up behind the strip, in
  // the 48.8 mm the arms leave open, clear by its radius and CLEAR
  const [d6] = R.routePath(rack, rack.cables[5], ctx).detours;
  assert.deepEqual(d6.between, [{end: 'a'}, {item: 'i3', via: 'guide-2'}]);
  assert.deepEqual(d6.points.map(p => Math.round(p.z * 10) / 10), [48.8 - 1.5 - S.CLEAR, 48.8 - 1.5 - S.CLEAR]);
  // a detour point is not stored: the cable's route is as written
  assert.deepEqual(rack.cables[5].route, [{item: 'i3', via: 'guide-2'}]);
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

// ── a vertical duct ───────────────────────────────────────────────────────
function ducted() {
  const {rack, ctx} = owner();
  return {rack: {...rack, zeroU: [{id: 'z1', ref: 'cmv-sfd45u5w', cfg: 'base', at: 'left-front', offsetMm: 0}]}, ctx};
}

test('a vertical duct is its walls and back, and an automatic route through its lane finds nothing', () => {
  const {rack, ctx} = ducted();
  const duct = S.solidsOf(rack, ctx).filter(x => x.item === 'z1');
  assert.deepEqual(duct.map(x => x.part), ['base/floor', 'base--seam', 'wall-left/root', 'wall-right/root']);
  // its back is behind the rail plane, its walls stand forward of it, and its
  // channel is where the lane runs: the lane point (z 0) is inside it, clear of both
  const lane = R.laneXAt(rack, 'left-front', 11, ctx.chassisOf);
  const back = duct[0].box;
  assert.ok(back.z1 < 0 && back.x0 < lane && lane < back.x1, JSON.stringify(back));
  let through = 0;
  for (const c of rack.cables.filter(c => c.routeEdited !== true)) {
    const p = R.routePath(rack, c, ctx);
    const inDuct = p.points.filter(q => q.at === 'lane' && Math.abs(q.x - lane) < 1e-9);
    through += inDuct.length ? 1 : 0;
    // into the channel through its open front: no detour, nothing crossed
    assert.deepEqual(before(rack, c, ctx).filter(x => x.solid.item === 'z1'), [], c.id);
    assert.deepEqual(p.crossings, [], c.id);
  }
  assert.equal(through, 5);
  // and a leg straight back through its base, away from a pass-through, is found
  const y = 30 * RU;
  const hit = S.legCrossings({x: lane, y, z: 0}, {x: lane, y, z: -300}, duct, {diameter: 6});
  assert.deepEqual(hit.map(h => h.solid.part), ['base/floor']);
});

// ── a closed enclosure with cable space ────────────────────────────────────
// The synthetic FHD enclosure of test_rack_solids.py: 448 x 44 x 432.8, shell
// walls 1 mm, one 40 x 24 grommet in the rear wall at device x 50 to 90 (rack
// x -174 to -134) and y 10 to 34.
function enclosure(grommet = null) {
  let r = F.add(F.add({...F.ownerRack(), items: []}, 'sw', 9, {label: 'sw-9'}), 'fhd-encl', 10, {label: 'encl'});
  r = F.add(r, 'rear', 10, {face: 'rear', label: 'rear-10'});
  const ctx = F.ctxOf({ports: {i1: {r: -154}, i2: {f: 100, g: -154}, i3: {p: 100, q: -154}}});
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
  // from the rear of the switch below up into the enclosure, to its grommet:
  // through the floor, then out by the grommet
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

// ── a leg the rules cannot clear ───────────────────────────────────────────
// A zero-U PDU standing on a lane is its envelope (section 1.1), and the lane
// beside that upright runs through it: a lane point inside a solid cannot be
// gone round, so the route is left as drawn and reported.
function pdu() {
  const {rack, ctx} = owner();
  return {rack: {...rack, zeroU: [{id: 'z2', ref: 'pdu', cfg: 'base', at: 'left-front', offsetMm: 0}]}, ctx};
}

test('what the rules cannot clear is a finding, with its sentence, in inspect, describe and the schedule', async () => {
  const {rack, ctx} = pdu();
  const f = R.bodyFindings(rack, ctx, id => ({i1: 'sw-dn', i2: 'fhd-panel', i3: 'lacer', i4: 'sw-up', z2: 'pdu-1'}[id] ?? id));
  // every automatic route runs the left-front lane, which runs through the
  // PDU, on each of its three legs there; the hand-routed c6 does not. From
  // the switch below, the leg past the web can no longer be taken round it
  // either: the detour would end in the lane, inside the PDU.
  assert.deepEqual([...new Set(f.map(x => x.cable))], ['c1', 'c2', 'c3', 'c4', 'c5']);
  assert.ok(f.every(x => x.kind === 'crosses-body'));
  const by = {};
  for (const x of f) by[`${x.item}:${x.part}`] = (by[`${x.item}:${x.part}`] ?? 0) + 1;
  assert.deepEqual(by, {'z2:envelope': 15, 'i3:web-a/plate': 3});
  const c1 = f.filter(x => x.cable === 'c1');
  assert.deepEqual(c1.map(x => [x.item, x.between]), [
    ['i3', [{item: 'i3', via: 'guide-1'}, {lane: 'left-front', ru: 11}]],
    ['z2', [{item: 'i3', via: 'guide-1'}, {lane: 'left-front', ru: 11}]],
    ['z2', [{lane: 'left-front', ru: 11}, {lane: 'left-front', ru: 12}]],
    ['z2', [{lane: 'left-front', ru: 12}, {item: 'i3', via: 'guide-1'}]]]);
  assert.equal(c1[1].text, 'c1 passes through pdu-1 between lacer ring 1 and left-front U11: '
    + 'route it round pdu-1, or through a ring or a pass-through it fits.');
  assert.equal(c1[0].text, 'c1 passes through lacer web a between lacer ring 1 and left-front U11: '
    + 'route it round lacer, or through a ring or a pass-through it fits.');
  assert.equal(c1[1].at.length, 3);
  // the route output of inspect: `crosses`
  const route = {...ctx};
  const info = await Q.inspect(rack, 'c1', {chassisOf: ctx.chassisOf, route});
  assert.deepEqual(info.route.crosses.map(x => [x.item, x.part]),
    [['i3', 'web-a/plate'], ['z2', 'envelope'], ['z2', 'envelope'], ['z2', 'envelope']]);
  assert.deepEqual(info.route.crosses[1].between, c1[1].between);
  assert.deepEqual(info.route.crosses[1].at, c1[1].at);
  // describe: one line of totals
  const text = Q.describe(rack, {chassisOf: ctx.chassisOf, route});
  assert.match(text, /^Findings: 5 cables cross a body\.$/m);
  // the cable schedule's notes
  const {rows} = cableScheduleRows(rack, new Map(), rack.items, null, {bodies: f});
  assert.ok(rows.find(x => x.id === 'c1').notes.includes(c1[0].text));
  assert.ok(!rows.find(x => x.id === 'c6').notes.includes('passes through'));
});

test('a leg through the tray floor that cannot be gone round is told to go over its front edge onto its resting face', () => {
  const {rack, ctx} = pdu();
  // by hand from the switch far below, up the lane inside the PDU, then
  // straight to ring 1: that leg starts inside the PDU, so no detour clears
  // it, and it rises through the floor of the tray as well
  const c7 = F.cable('c7', F.end('i5', 'p100'), F.end('i2', 'bay2'), 'om4',
    {route: [{lane: 'left-front', ru: 5}, {item: 'i3', via: 'guide-1'}], routeEdited: true});
  const only = {...rack, cables: [c7]};
  const f = R.bodyFindings(only, ctx, id => ({i2: 'fhd-panel', i3: 'lacer', i5: 'sw-low', z2: 'pdu-1'}[id] ?? id));
  assert.deepEqual(f.map(x => [x.item, x.part]), [['z2', 'envelope'], ['z2', 'envelope'], ['i3', 'tray/floor']]);
  assert.equal(f[2].text, 'c7 passes through lacer tray between left-front U5 and lacer ring 1: '
    + 'route it over the front edge of the tray onto its resting face, or through a ring.');
  assert.equal(S.partText('shell/rear'), 'rear wall');
  assert.equal(S.partText('envelope'), '');
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
