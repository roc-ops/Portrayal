// spec/tests/js/rack-strap-path.mjs
// STRAPS ARE MEASURED AND PLACED ON THE CABLES (#1034). A bundle's trunk is a
// list of waypoints, and its members do not run straight from one to the
// next: a cord goes through a ring by its opening, hangs between a ring and a
// lane, and goes round a body by a detour point. The trunk's length, the
// count of its straps and the place of each are read off the members' routed
// paths (bundles.js, the trunk's own line), never off the straight line
// between two waypoints.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import * as R from '../../../kit/rack/route.js';
import * as B from '../../../kit/rack/bundles.js';
import * as X from '../../../kit/rack/export-data.js';
import * as Q from '../../../kit/rack/queries.js';
import * as F from './cable-solids-fixture.mjs';
import * as HOPS from './bundle-hops-fixture.mjs';
import {rearToFront} from './strap-path-fixture.mjs';
import {apply} from '../../../kit/rack/commands.js';
import {withCable} from '../../../kit/rack/cable-rules.js';
import {loadTree, racksOf} from './speed-goldens.mjs';

const dist = (p, q) => Math.hypot(p.x - q.x, p.y - q.y, p.z - q.z);
// how far a point is from a line of points
function offLine(p, P) {
  let near = Infinity;
  for (let k = 1; k < P.length; k++) {
    const a = P[k - 1], b = P[k], d = {x: b.x - a.x, y: b.y - a.y, z: b.z - a.z}, L2 = d.x * d.x + d.y * d.y + d.z * d.z;
    const t = L2 > 0 ? Math.max(0, Math.min(1, ((p.x - a.x) * d.x + (p.y - a.y) * d.y + (p.z - a.z) * d.z) / L2)) : 0;
    near = Math.min(near, dist(p, {x: a.x + t * d.x, y: a.y + t * d.y, z: a.z + t * d.z}));
  }
  return near;
}
// Every strap of every bundle of a rack against its members' paths: how many
// straps were read, and the farthest any is from the path of a member (of
// the member it names, where it names one).
function strapsOnPaths(rack, ctx) {
  const pathOf = new Map(rack.cables.map(c => [c.id, R.routePath(rack, c, ctx)?.points ?? null]));
  let read = 0, far = 0, named = 0;
  for (const b of M.bundlesOf(rack)) {
    const s = B.straps(rack, b, {route: ctx});
    for (const x of s?.straps ?? []) {
      assert.ok(x.point && [x.point.x, x.point.y, x.point.z].every(Number.isFinite), `${b.id}: a strap at ${x.along_mm} mm has no point of its own`);
      const members = b.members.map(m => m.cable).filter(id => pathOf.get(id));
      assert.ok(members.length >= 2, `${b.id}: its members have paths`);
      if (x.on != null) { assert.ok(members.includes(x.on), `${b.id}: ${x.on} is a member`); named++; }
      const off = Math.min(...(x.on != null ? [x.on] : members).map(id => offLine(x.point, pathOf.get(id))));
      far = Math.max(far, off);
      read++;
    }
  }
  return {read, far, named};
}

const made = rearToFront(M, F), RACK = made.rack;
const ctxOf = (r = RACK, extra) => made.ctxOf(r, extra);
const bundle = id => RACK.bundles.find(b => b.id === id);
const got = (id, r = RACK, ctx = ctxOf(r)) => B.straps(r, r.bundles.find(b => b.id === id), {route: ctx});

test('the rack is the one meant: 96 cords in eight bundles, and the rear ones cross a duct between their two lanes through its top window', () => {
  const ctx = ctxOf();
  assert.equal(RACK.cables.length, 96);
  assert.deepEqual(RACK.bundles.map(b => b.members.length), [12, 12, 12, 12, 12, 12, 12, 12]);
  const paths = RACK.cables.map(c => R.routePath(RACK, c, ctx));
  assert.ok(paths.every(Boolean), 'every cord has a path');
  // c61, of the bundle to the lacer under switch 1: rear lane, one detour point, front lane. The duct's
  // back has windows (P-0016), and the cord crosses it through the nearest, the top one (2018 to 2034 mm
  // up the duct); before, the window could not be used and the cord went over the duct by two detour
  // points, 1151 mm from one lane point to the other where the straight line is 754 mm
  const P = paths[60].points, at = P.map(p => p.at);
  const i = at.indexOf('lane'), j = at.lastIndexOf('lane');
  assert.deepEqual(at.slice(i, j + 1), ['lane', 'detour', 'lane']);
  assert.ok(P[i + 1].y > 2018.2 && P[i + 1].y < 2034, `the detour point stands in the top window: ${P[i + 1].y}`);
  assert.deepEqual(paths[60].crossings, []);
  // and it is a detour, though a shorter one: the point is well off the straight line
  assert.ok(offLine(P[i + 1], [P[i], P[j]]) > 100);
});

test('every strap of the 96-cord rack is on a member\'s routed path, to within a millimetre', () => {
  const {read, far, named} = strapsOnPaths(RACK, ctxOf());
  // 32 spacing and 24 breakout straps; the anchors are counted by slot, rack-wide, and are not of a bundle here
  assert.equal(read, 54);
  assert.equal(named, 54,'each names the cable whose path it is on');
  assert.ok(far < 1, `the farthest strap is ${far.toFixed(2)} mm off its cable`);
});

test('every fixture with a bundle: each strap is on a member\'s routed path, to within a millimetre', async () => {
  const K = await loadTree();
  let racks = 0, straps = 0, worst = 0;
  for (const r of racksOf(K)) {
    if (!K.M.bundlesOf(r.rack).some(b => b.members.length >= 2)) continue;
    // with the check of what is kept on: every path the straps read is laid again from nothing and compared
    const {read, far} = strapsOnPaths(r.rack, {...r.ctxOf(r.rack), checkKept: true});
    assert.ok(far < 1, `${r.name}: the farthest strap is ${far.toFixed(2)} mm off a member's path`);
    racks++; straps += read; worst = Math.max(worst, far);
  }
  // and it is not a comparison of nothing with nothing
  assert.ok(racks >= 12 && straps >= 140, `${racks} racks, ${straps} straps, worst ${worst}`);
});

test('a place half way between two tenths of a millimetre rounds up, whatever rack it is on', async () => {
  // eleven units of a lane are 488.95 mm. A sum of lengths comes out a hair
  // under or over that, and it read 489 on one rack and 488.9 on another.
  const K = await loadTree(), all = racksOf(K);
  const ends = ['hops-bundled', 'speed-300'].map(name => {
    const r = all.find(x => x.name === name), ctx = r.ctxOf(r.rack);
    return K.M.bundlesOf(r.rack).map(b => B.straps(r.rack, b, {route: ctx}).runs.map(run => run[1] - run[0])).flat();
  });
  assert.ok(ends[0].includes(444.5) && ends[1].includes(489), JSON.stringify(ends));
  assert.ok(!ends.flat().some(v => Math.abs(v - 488.9) < 1e-9 || Math.abs(v - 444.4) < 1e-9), JSON.stringify(ends));
});

test('a trunk is as long as the path of it, and its straps are counted along that', () => {
  const ctx = ctxOf(), bc = {route: ctx};
  // b6 crosses the duct between its lanes through a window (it went over the
  // duct, 1736.6 mm, before P-0016). The straight lines from waypoint to
  // waypoint come to 1257 mm, all of it ridden: five straps at one every
  // 12 in. The cords run 1510.3 mm, which takes five as well, the last of
  // them closer to the end.
  const pts = B.layoutOf(RACK, bundle('b6'), bc).trunk.map(w => R.pointOf(RACK, w, ctx));
  const straight = pts.slice(1).reduce((m, p, k) => m + dist(pts[k], p), 0);
  assert.equal(Math.round(straight), 1257);
  const s = got('b6');
  assert.deepEqual(s.runs, [[0, 1510.3]]);
  assert.deepEqual(s.kinds, {spacing: 5, breakout: 4, anchor: 0});
  assert.equal(s.kinds.spacing, Math.ceil(1510.3 / 304.8));
  assert.equal(Math.ceil(1257 / 304.8), 5);
  assert.deepEqual(s.straps.map(x => [x.kind, x.along_mm]),
    [['breakout', 25], ['spacing', 151], ['spacing', 453.1], ['spacing', 755.1], ['spacing', 1057.2],
     ['breakout', 1286.7], ['spacing', 1359.3], ['breakout', 1434.8], ['breakout', 1485.3]]);
  assert.deepEqual(B.trunkLength(RACK, bundle('b6'), bc), {metres: 1.51});
  assert.equal(s.straight, false);
  // b5 has no body in its way: its cords still hang between a ring and a lane, so it is longer than its straight lines too
  assert.deepEqual(got('b5').runs, [[0, 1284.2]]);
  assert.deepEqual(got('b5').kinds, {spacing: 5, breakout: 4, anchor: 0});
  // the rack: what it buys, the BOM's strap line, and a bundle's line on the sheet and the schedule
  assert.deepEqual(B.strapTotals(RACK, bc), {spacing: 30, breakout: 24, anchor: 20, total: 74, widths: {19: 74}});
  const ex = X.bundleExports(RACK, bc);
  assert.deepEqual(ex.map(e => [e.id, e.length_m, e.straps, e.straight]),
    [['b1', 0.5, 4, false], ['b2', 0.73, 5, false], ['b3', 0.74, 5, false], ['b4', 0.51, 4, false],
     ['b5', 1.28, 9, false], ['b6', 1.51, 9, false], ['b7', 1.51, 9, false], ['b8', 1.28, 9, false]]);
  assert.equal(X.strapBomRows(ex, {anchors: B.anchorsOf(RACK, bc)})[0].description,
    '30 along 8 bundles, one every 12 in; 24 where a cable joins or leaves a bundle; 20 at tray tie slots; 74 of 19 mm wide; length to suit');
  assert.equal(X.bundleNote(ex[5]),
    'rear 2 (b6): 12 cables (c61-c72), 1.51 m, 9 straps (5 every 12 in, 4 where a cable leaves); 12 mm across, limit 29.5 mm at LACER-REAR ring 4; bend not checked.');
});

test('inspect of a bundle gives the routed length and the count along it', async () => {
  const f = await Q.inspect(RACK, 'b6', {chassisOf: made.chassisOf, route: ctxOf()});
  assert.deepEqual(f.length, {metres: 1.51});
  assert.deepEqual(f.straps.kinds, {spacing: 5, breakout: 4, anchor: 0});
  assert.equal('straight' in f.straps, false);
});

test('a strap carries its own point, the way the trunk runs there and the cable it is on; segment and t still say where on the trunk', () => {
  const ctx = ctxOf(), s = got('b6', RACK, ctx), b = bundle('b6');
  const P = R.routePath(RACK, RACK.cables.find(c => c.id === 'c61'), ctx).points;
  const i = P.findIndex(p => p.at === 'lane'), j = P.findLastIndex(p => p.at === 'lane'), way = P.slice(i, j + 1);
  assert.equal(way.length, 3);
  for (const x of s.straps) {
    assert.deepEqual(Object.keys(x), ['kind', 'segment', 't', 'along_mm', 'point', 'dir', 'on', 'width_mm']);
    assert.ok(Math.abs(Math.hypot(x.dir.x, x.dir.y, x.dir.z) - 1) < 1e-3, 'a unit vector');
    assert.ok(Number.isInteger(x.segment) && x.t >= 0 && x.t <= 1);
  }
  // the trunk's second segment is the rear lane to the front lane: its straps
  // are on the legs of the detour, each running the way its leg runs
  const between = s.straps.filter(x => x.segment === 1);
  assert.equal(between.length, 3);
  const legs = way.slice(1).map((q, k) => { const p = way[k], d = dist(p, q);
    return {from: way.slice(1, k + 1).reduce((m, v, n) => m + dist(way[n], v), 0), p, d, dir: {x: (q.x - p.x) / d, y: (q.y - p.y) / d, z: (q.z - p.z) / d}}; });
  const whole = legs.at(-1).from + legs.at(-1).d;
  let at0 = null;
  for (const x of between) {
    const leg = legs.find(v => Math.abs(v.dir.x - x.dir.x) + Math.abs(v.dir.y - x.dir.y) + Math.abs(v.dir.z - x.dir.z) < 1e-3);
    assert.ok(leg, `the strap at ${x.along_mm} mm runs along a leg of the detour`);
    // `t` is the share of the segment's routed length: the same start of the segment for every strap of it
    const from = x.along_mm - x.t * whole;
    at0 ??= from;
    assert.ok(Math.abs(from - at0) < 0.2, 'every strap of the segment gives the same start for it');
    // and its point is that far along the cord from the rear lane point
    const along = leg.from + dist(leg.p, x.point);
    assert.ok(Math.abs(along - x.t * whole) < 0.2, `${along} mm along, t ${x.t}`);
  }
  // the trunk starts at the middle of its first ring, between where the cord enters and leaves it: the
  // breakout strap 25 mm along is 25 mm from there, on the cord's way out of the ring
  const [entry, exit] = [P.find(p => p.at === 'entry'), P.find(p => p.at === 'exit')];
  const middle = {x: (entry.x + exit.x) / 2, y: (entry.y + exit.y) / 2, z: (entry.z + exit.z) / 2};
  assert.equal(s.straps[0].along_mm, 25);
  assert.ok(Math.abs(dist(s.straps[0].point, middle) - 25) < 0.02, `${dist(s.straps[0].point, middle)} mm from the ring's middle`);
  assert.deepEqual(s.straps[0].dir, {x: -1, y: 0, z: 0});
  // none of them is on the straight line a reader of segment and t alone would draw
  assert.ok(between.every(x => offLine(x.point, [way[0], way.at(-1)]) > 20));
  assert.ok(b.members.some(m => m.cable === s.straps[0].on));
});

test('the way a strap runs is the trunk\'s, also where its cable is written from the other end', () => {
  // eleven cords up one lane, the trunk written from U31 up to U42; flipped, every cord is written from its top end
  for (const flip of [false, true]) {
    const r = HOPS.bundled({flip}), ctx = HOPS.ctxFor(r), s = B.straps(r, r.bundles[0], {route: ctx});
    assert.equal(s.count, 10);
    const c = r.cables.find(x => x.id === s.straps[0].on), P = R.routePath(r, c, ctx).points;
    const lanes = P.filter(p => p.at === 'lane');
    // the cable runs down the lane where it is written from its top end, and the trunk still runs up
    assert.equal(Math.sign(lanes.at(-1).y - lanes[0].y), flip ? -1 : 1, 'which way the cable is written');
    for (const x of s.straps) assert.deepEqual(x.dir, {x: 0, y: 1, z: 0});
    assert.ok(s.straps.every((x, k) => k === 0 || x.point.y > s.straps[k - 1].point.y), 'further along is further up');
  }
});

test('the same straps whatever order the cables and the members are written in', () => {
  // half of b6 in Cat 6, so that its members do not all lie alike: a thicker cord stands further off a ring's sill and hangs otherwise
  const mixed = {...RACK, cables: RACK.cables.map((c, k) => (k >= 60 && k < 72 && k % 2 ? {...c, media: 'cat6'} : c))};
  const turn = r => ({...r, cables: [...r.cables].reverse(),
    bundles: r.bundles.map(b => ({...b, members: [...b.members].reverse()}))});
  const shuffle = r => ({...r, cables: r.cables.map((c, k, all) => all[(k * 37 + 11) % all.length]),
    bundles: r.bundles.map(b => ({...b, members: b.members.map((m, k, all) => all[(k * 5 + 3) % all.length])}))});
  for (const rack of [RACK, mixed]) {
    const want = rack.bundles.map(b => got(b.id, rack));
    for (const other of [turn(rack), shuffle(rack)]) {
      assert.equal(other.cables.length, 96);
      assert.deepEqual(new Set(other.cables.map(c => c.id)).size, 96);
      assert.deepEqual(other.bundles.map(b => got(b.id, other)), want);
      assert.deepEqual(other.bundles.map(b => B.trunkLength(other, b, {route: ctxOf(other)})), rack.bundles.map(b => B.trunkLength(rack, b, {route: ctxOf(rack)})));
    }
  }
  // the members of the mixed bundle do differ, and its straps are not all on one kind's path
  assert.notDeepEqual(got('b6', mixed).runs, got('b6').runs);
});

// ── which member, where they differ ──────────────────────────────────────
// A strap goes round the whole pack, so the trunk is taken from the member in
// the middle by length on each piece: one cord that hangs otherwise than the
// rest sets neither the length, nor the count, nor the place.
const DUCT_SIZES = {sw: {ru: 1, d: 515, model: 'SW'}, pp: {ru: 1, d: 100, model: 'PP'},
  mgr: {ru: 1, d: 110, mount: 'rack-face', model: 'MGR', guides: {front: ['guide-1', 'guide-2', 'guide-3']}, default: 'x'}};
// Two ducts 762 mm apart on one manager (or the ducts of `at`, by x), a cord of each media given
// through them, all in one bundle. `portX` places the ports; -150 for every one without it.
function ducts(media, {at = {'guide-1': 0, 'guide-2': 762}, portX = () => -150} = {}) {
  const chassisOf = ref => DUCT_SIZES[ref] || null;
  const way = Object.keys(at).map(via => ({item: 'i2', via}));
  let r = M.newRack({name: 'Rack 1'});
  r = M.withItem(r, {ref: 'sw', cfg: 'x', ru: 10, label: 'sw-1'}).rack;
  r = M.withItem(r, {ref: 'mgr', cfg: 'x', ru: 10, label: 'mgr-1', on: 'i1', unit: 1}).rack;
  r = M.withItem(r, {ref: 'pp', cfg: 'x', ru: 30, label: 'pp-1'}).rack;
  media.forEach((m, k) => {
    r = withCable(r, {a: {item: 'i1', path: `p${k + 1}`, view: 'front'}, b: {item: 'i3', path: `q${k + 1}`, view: 'front'}, media: m}).rack;
    r = {...r, cables: r.cables.map(c => (c.id === `c${k + 1}` ? {...c, route: way, routeEdited: true} : c))};
  });
  r = apply(r, {op: 'bundle.create', cables: media.map((m, k) => `c${k + 1}`), route: way}, {chassisOf}).rack;
  // (a plug's reach is given as a number, so a DAC's and an AOC's are measured
  // whole, as every plug was before #985: the cords here differ by how they
  // hang, not by a plug that cannot bend)
  const ctx = {chassisOf, portX, plugReachOf: (e, c) => R.PLUG_REACH[c?.media] ?? null,
    guidesOf: id => (id === 'i2' ? Object.entries(at).map(([via, x]) => ({via, kind: 'duct', face: 'front', x, box: {w: 40, h: 30}})) : [])};
  return {rack: r, ctx};
}
// What a bundle's straps come to, and how far the farthest strap is from each member's path.
function measured(rack, ctx, b = rack.bundles[0]) {
  const s = B.straps(rack, b, {route: ctx});
  const off = Object.fromEntries(b.members.map(m => {
    const P = R.routePath(rack, rack.cables.find(c => c.id === m.cable), ctx)?.points;
    return [m.cable, P ? Math.max(...s.straps.map(x => offLine(x.point, P))) : null];
  }));
  return {run: s.runs[0][1], kinds: s.kinds, on: [...new Set(s.straps.map(x => x.on))], off, length: B.trunkLength(rack, b, {route: ctx}).metres, straps: s};
}

test('one limp cord among stiff ones sets neither the length, nor the count, nor the place of a strap', () => {
  // four DACs between the ducts: 788.8 mm of cord, three straps
  const dacs = ducts(['dac', 'dac', 'dac', 'dac']), all = measured(dacs.rack, dacs.ctx);
  assert.deepEqual([all.run, all.kinds.spacing, all.length], [788.8, 3, 0.79]);
  // one of them an AOC, which hangs lower and longer: the same length, the same three straps, each on a DAC
  const aoc = ducts(['dac', 'dac', 'dac', 'aoc']), one = measured(aoc.rack, aoc.ctx);
  assert.deepEqual([one.run, one.kinds, one.length], [all.run, all.kinds, all.length]);
  assert.deepEqual(one.on, ['c2']);
  assert.ok(one.off.c1 < 0.02 && one.off.c2 < 0.02 && one.off.c3 < 0.02, 'every strap is on the three DACs');
  assert.ok(one.off.c4 > 50, `the AOC hangs elsewhere, ${one.off.c4.toFixed(1)} mm off at the farthest strap`);
  // fibre with one Cat 6 among it: as the fibre alone
  const fibre = ducts(['os2', 'os2', 'os2', 'os2']), f0 = measured(fibre.rack, fibre.ctx);
  const cat = ducts(['os2', 'os2', 'os2', 'cat6']), f1 = measured(cat.rack, cat.ctx);
  assert.deepEqual([f0.run, f0.kinds.spacing], [762, 3]);
  assert.deepEqual([f1.run, f1.kinds, f1.on], [f0.run, f0.kinds, ['c2']]);
  assert.ok(f1.off.c1 < 0.02 && f1.off.c2 < 0.02 && f1.off.c3 < 0.02 && f1.off.c4 > 50);
  // and the other way about: Cat 6 with one fibre cord among it is measured as Cat 6, 815 mm
  const most = ducts(['cat6', 'cat6', 'cat6', 'os2']), f2 = measured(most.rack, most.ctx);
  assert.deepEqual([f2.run, f2.on], [815, ['c1']]);
  assert.ok(f2.off.c4 > 50);
  // wherever the odd one is written, and whatever its id
  for (const media of [['aoc', 'dac', 'dac', 'dac'], ['dac', 'aoc', 'dac', 'dac'], ['dac', 'dac', 'aoc', 'dac']]) {
    const x = ducts(media), m = measured(x.rack, x.ctx), odd = `c${media.indexOf('aoc') + 1}`;
    assert.deepEqual([m.run, m.kinds], [all.run, all.kinds], media.join());
    assert.ok(!m.on.includes(odd) && m.off[odd] > 50, media.join());
  }
});

test('on the 96-cord rack, one Cat 6A cord among eleven fibre moves nothing, and no strap is on it', () => {
  const plain = got('b6');
  for (const odd of ['c61', 'c63', 'c66', 'c72']) {
    const r = {...RACK, cables: RACK.cables.map(c => (c.id === odd ? {...c, media: 'cat6a'} : c))};
    const s = got('b6', r);
    assert.deepEqual([s.runs, s.kinds, s.straps.map(x => x.along_mm)], [plain.runs, plain.kinds, plain.straps.map(x => x.along_mm)], odd);
    // (c66 is the middle cord on the run through the duct's window, which the cords lie along alike since
    // P-0016, so a strap there may name it; the others are never the middle there)
    if (odd !== 'c66') assert.ok(s.straps.every(x => x.on !== odd), `${odd} is named by no strap`);
    // each strap is where it was, to a hundredth of a millimetre: on the fibre
    s.straps.forEach((x, k) => assert.ok(dist(x.point, plain.straps[k].point) < 0.02, `${odd}: the strap at ${x.along_mm} mm`));
  }
});

test('a strap names a member that rides there, the middle one of them, and the name changes where cords leave', () => {
  // b6: twelve ride to the first ring under the switch, eight on to the second, four to the third
  const b = bundle('b6'), ctx = ctxOf(), s = got('b6', RACK, ctx), L = B.layoutOf(RACK, b, {route: ctx});
  const riders = x => L.members.filter(m => { const [lo, hi] = [m.ji, m.li].sort((p, q) => p - q);
    const at = L.T.findLastIndex((e, i) => e.kind !== 's' && e.seg <= x.segment && (e.seg < x.segment || e.t <= x.t + 1e-9) && i >= 0);
    return lo <= at && hi > at; }).map(m => m.cable);
  assert.deepEqual(s.straps.map(x => [x.along_mm, x.on, riders(x).length]),
    [[25, 'c66', 12], [151, 'c66', 12], [453.1, 'c66', 12], [755.1, 'c66', 12], [1057.2, 'c66', 12], [1286.7, 'c66', 12],
     [1359.3, 'c68', 8], [1434.8, 'c70', 4], [1485.3, 'c70', 4]]);
  // of members that lie alike, the middle one by id, the earlier of two middles: c66 of c61-c72, c68 of c65-c72, c70 of c69-c72
  for (const x of s.straps) { const r = riders(x); assert.ok(r.includes(x.on)); assert.equal(x.on, r[Math.floor((r.length - 1) / 2)]); }
  // where they leave: three places, the last riders four, then eight, then twelve
  assert.deepEqual(L.members.map(m => Math.max(m.ji, m.li) - Math.min(m.ji, m.li)).filter((v, k, a) => a.indexOf(v) === k).length, 3);
});

test('an even split of two kinds goes to the kind that hangs less, and half the pack is then off every strap', () => {
  // two DACs and two AOCs: the earlier of the two middles by length is a DAC, so it is measured as four DACs are
  const four = ducts(['dac', 'dac', 'dac', 'dac']), all = measured(four.rack, four.ctx);
  for (const media of [['dac', 'dac', 'aoc', 'aoc'], ['aoc', 'aoc', 'dac', 'dac'], ['aoc', 'dac', 'aoc', 'dac']]) {
    const x = ducts(media), m = measured(x.rack, x.ctx);
    assert.deepEqual([m.run, m.kinds], [all.run, all.kinds], media.join());
    media.forEach((kind, k) => {
      const off = m.off[`c${k + 1}`];
      assert.ok(kind === 'dac' ? off < 0.02 : off > 50, `${media.join()}: c${k + 1} (${kind}) is ${off.toFixed(1)} mm off at the farthest strap`);
    });
    assert.equal(m.straps.few, false);
  }
  // one of each: the DAC
  const two = ducts(['aoc', 'dac']), m = measured(two.rack, two.ctx);
  assert.deepEqual([m.run, m.on], [all.run, ['c2']]);
  assert.ok(m.off.c1 > 50);
});

test('a readable minority sets the trunk, and that is said', async () => {
  // three DACs whose ports are not found and one AOC whose are: the AOC is all there is to measure
  const x = ducts(['dac', 'dac', 'dac', 'aoc'], {portX: e => (/4$/.test(e.path) ? -150 : null)}), m = measured(x.rack, x.ctx);
  assert.deepEqual([m.run, m.kinds.spacing, m.on, m.off.c1], [946.8, 4, ['c4'], null]);
  const said = 'Bundle 1 is measured in part on fewer than half of the cables that ride there, since no path could be read for the others (a port not found on its drawing), so its length and its straps are an estimate.';
  assert.equal(m.straps.few, true);
  assert.equal(m.straps.straight, false);
  assert.deepEqual(m.straps.notes, [said]);
  assert.deepEqual(B.trunkLength(x.rack, x.rack.bundles[0], {route: x.ctx}), {metres: 0.95, few: true});
  const [e] = X.bundleExports(x.rack, {route: x.ctx});
  // the export record keeps the two estimates apart: a minority's figure can be over, a straight line is the shortest
  assert.deepEqual([e.few, e.straight], [true, false]);
  assert.ok(e.notes.includes(said));
  const f = await Q.inspect(x.rack, 'b1', {chassisOf: x.ctx.chassisOf, route: x.ctx});
  assert.ok(f.notes.includes(said) && f.straps.few === true && f.length.few === true);
  // half of them readable is no minority: two DACs with a path and two without are measured as DACs, and nothing is said
  const half = ducts(['dac', 'dac', 'dac', 'dac'], {portX: e => (/[34]$/.test(e.path) ? -150 : null)}), h = measured(half.rack, half.ctx);
  assert.deepEqual([h.run, h.straps.few, h.straps.notes], [788.8, false, []]);
  // also where the readable half is the other kind: two DACs unread and two AOCs read are measured on the AOCs, with no note
  const other = ducts(['dac', 'dac', 'aoc', 'aoc'], {portX: e => (/[34]$/.test(e.path) ? -150 : null)}), o = measured(other.rack, other.ctx);
  assert.deepEqual([o.run, o.kinds.spacing, o.straps.few, o.straps.straight, o.straps.notes], [946.8, 4, false, false, []]);
  assert.deepEqual([X.bundleExports(other.rack, {route: other.ctx})[0].few, X.bundleExports(other.rack, {route: other.ctx})[0].straight], [false, false]);
});

test('a member is counted only on the stretch it rides, though its own path passes more of the trunk', () => {
  // three ducts, four cords through all of them; c1 is made to join at the second duct, so it rides the second stretch only
  const x = ducts(['om4', 'om4', 'om4', 'om4'], {at: {'guide-1': 0, 'guide-2': 400, 'guide-3': 800}});
  const {rack: r0, ctx} = x;
  const peeled = apply(r0, {op: 'bundle.peel', id: 'b1', cable: 'c1', at: {item: 'i2', via: 'guide-2'}, end: 'a'}, {chassisOf: ctx.chassisOf, route: ctx}).rack;
  const b = peeled.bundles[0], L = B.layoutOf(peeled, b, {route: ctx});
  assert.deepEqual(L.members.map(m => [m.cable, m.ji, m.li]), [['c1', 1, 2], ['c2', 0, 2], ['c3', 0, 2], ['c4', 0, 2]]);
  // its own path still passes the first duct: it comes from its port through it
  const P = R.routePath(peeled, peeled.cables[0], ctx).points;
  assert.ok(P.some(p => p.via === 'guide-1') && P.some(p => p.via === 'guide-2'));
  // on the first stretch three ride (c2, c3, c4) and the middle one is c3; were c1 counted there it would be c2
  const s = B.straps(peeled, b, {route: ctx});
  // (a strap exactly at the second duct is of the stretch that starts there)
  const first = s.straps.filter(q => q.segment === 0 && q.t < 1), second = s.straps.filter(q => q.segment === 1 || q.t === 1);
  assert.ok(first.length >= 2 && second.length >= 2);
  assert.deepEqual([...new Set(first.map(q => q.on))], ['c3']);
  // on the second all four ride, and the earlier of the two middles is c2
  assert.deepEqual([...new Set(second.map(q => q.on))], ['c2']);
});

test('a bundle whose straps cannot be read is left out of the rack\'s totals, and the totals say so', () => {
  const ctx = ctxOf(), bc = {route: ctx};
  const whole = B.strapTotals(RACK, bc);
  assert.equal(whole.total, 74);
  assert.equal('unread' in whole || 'unreadBundles' in whole, false, 'nothing is said where every bundle was read');
  // one port of one cord of b6 cannot be placed: its reader throws
  const c61 = RACK.cables[60];
  const bad = ctxOf(RACK, {portX: e => { if (e.item === c61.a.item && e.path === c61.a.path) throw new Error('no drawing'); return ctx.portX(e); }});
  assert.throws(() => B.straps(RACK, bundle('b6'), {route: bad}), /no drawing/);
  const short = B.strapTotals(RACK, {route: bad});
  // b6's nine straps are not counted, nor is any tie slot its cords would be tied at: fewer, and said
  assert.ok(short.total < whole.total - 8, `${short.total} of ${whole.total}`);
  assert.equal(short.spacing, whole.spacing - 5);
  assert.equal(short.breakout, whole.breakout - 4);
  assert.equal(short.unread, 1);
  assert.deepEqual(short.unreadBundles, ['b6']);
  // the exports say it in words: no length, no count, a note, and the BOM line counts the rest
  const ex = X.bundleExports(RACK, {route: bad});
  assert.deepEqual([ex[5].length_m, ex[5].straps], [null, null]);
  assert.deepEqual(X.strapBomNotes(ex), ['rear 2: its route could not be read, so its straps are not counted.']);
  assert.equal(X.strapBomRows(ex, {anchors: B.anchorsOf(RACK, {route: bad})})[0].qty, short.total);
  // with no routes at all, every drawn bundle is unread
  const none = B.strapTotals(RACK, {});
  assert.deepEqual([none.total, none.unread, none.unreadBundles], [0, 8, RACK.bundles.map(b => b.id)]);
});

// A bundle of the cords named, renamed: the rack with `ids[k]` for the k-th of them.
function renamed(keep, ids) {
  const to = new Map(keep.map((id, k) => [id, ids[k]]));
  return {...RACK, cables: RACK.cables.filter(c => to.has(c.id) || !bundle('b6').members.some(m => m.cable === c.id))
      .map(c => (to.has(c.id) ? {...c, id: to.get(c.id)} : c)),
    bundles: RACK.bundles.map(b => (b.id === 'b6' ? {...b, members: keep.map(id => ({cable: to.get(id)}))} : b))};
}
test('two as long go to the id that sorts first by number, and by its plain text where the numbers are the same', () => {
  const on = (ids, turn = false) => { let r = renamed(['c69', 'c70'], ids);
    if (turn) r = {...r, cables: [...r.cables].reverse(), bundles: r.bundles.map(b => ({...b, members: [...b.members].reverse()}))};
    return [...new Set(got('b6', r).straps.map(x => x.on))]; };
  // two cords that lie alike: the earlier of the two middles is the first by id
  assert.deepEqual(on(['c69', 'c70']), ['c69']);
  // by number: c200 before c1000 (as c2 before c10), where plain text would put c1000 first
  assert.ok('c1000' < 'c200');
  assert.deepEqual(on(['c200', 'c1000']), ['c200']);
  assert.deepEqual(on(['c1000', 'c200']), ['c200']);
  assert.deepEqual(on(['c200', 'c1000'], true), ['c200']);
  // c0200 and c200 are the same number (as c02 and c2): the plain text settles it, whichever is written first
  assert.equal('c0200'.localeCompare('c200', 'en', {numeric: true}), 0);
  assert.deepEqual(on(['c0200', 'c200']), ['c0200']);
  assert.deepEqual(on(['c200', 'c0200']), ['c0200']);
  assert.deepEqual(on(['c200', 'c0200'], true), ['c0200']);
  assert.deepEqual(on(['c0200', 'c200'], true), ['c0200']);
});

test('an error is let out: a path found changed, and a reader of the context that throws', () => {
  // a rack changed in place, with the check of what is kept on: straps() throws as routePath does, and gives no straight-line answer
  const rack = structuredClone(RACK), ctx = ctxOf(rack, {checkKept: true}), b = rack.bundles[5];
  assert.equal(B.straps(rack, b, {route: ctx}).straight, false);
  rack.cables[60].media = 'cat6a';
  rack.cables[65].media = 'cat6a';
  assert.throws(() => R.routePath(rack, rack.cables[65], ctx), /ctx\.checkKept/);
  assert.throws(() => B.straps(rack, b, {route: ctx}), /ctx\.checkKept/);
  assert.throws(() => B.trunkLength(rack, b, {route: ctx}), /ctx\.checkKept/);
  // a reader that throws is heard of too
  const bad = ctxOf(RACK, {portY: () => { throw new Error('no drawing'); }});
  assert.throws(() => B.straps(RACK, bundle('b6'), {route: bad}), /no drawing/);
  assert.throws(() => B.trunkLength(RACK, bundle('b6'), {route: bad}), /no drawing/);
  // the readers that count for a whole rack keep their own rule: a bundle that cannot be read is not counted, never guessed
  assert.equal(X.bundleExports(RACK, {route: bad})[5].straps, null);
});

test('with the check of what is kept on, the answers are the same and nothing is found changed', () => {
  const plain = RACK.bundles.map(b => got(b.id));
  const checked = ctxOf(RACK, {checkKept: true});
  assert.deepEqual(RACK.bundles.map(b => B.straps(RACK, b, {route: checked})), plain);
  assert.deepEqual(RACK.bundles.map(b => B.trunkLength(RACK, b, {route: checked})), RACK.bundles.map(b => B.trunkLength(RACK, b, {route: ctxOf()})));
  // a second read in the same context, and one in a context made anew
  assert.deepEqual(RACK.bundles.map(b => B.straps(RACK, b, {route: checked})), plain);
  assert.deepEqual(RACK.bundles.map(b => got(b.id, RACK, ctxOf())), plain);
});

test('where no member has a path, a trunk is the straight lines between its waypoints, and that is said', async () => {
  // no port is found on its drawing, so no cord has a path
  const ctx = ctxOf(RACK, {portX: () => null});
  assert.equal(R.routePath(RACK, RACK.cables[60], ctx), null);
  const b = bundle('b6'), s = B.straps(RACK, b, {route: ctx});
  const pts = B.layoutOf(RACK, b, {route: ctx}).trunk.map(w => R.pointOf(RACK, w, ctx));
  const straight = pts.slice(1).reduce((m, p, k) => m + dist(pts[k], p), 0);
  assert.deepEqual(B.trunkLength(RACK, b, {route: ctx}), {metres: Math.round(straight / 10) / 100, straight: true});
  assert.ok(s.count > 0);
  for (const x of s.straps) {
    assert.equal(x.on, null);
    const p = pts[x.segment], q = pts[x.segment + 1];
    assert.ok(dist(x.point, {x: p.x + x.t * (q.x - p.x), y: p.y + x.t * (q.y - p.y), z: p.z + x.t * (q.z - p.z)}) < 0.1, 'on the straight line, at t');
  }
  // SAID where a person reads it: the straps, the bundle's notes on the sheet and the schedule, the export record, inspect
  const said = 'rear 2 is measured along the straight line between its waypoints where no path could be read for its cables (a port not found on its drawing), so its length and its straps are an estimate.';
  assert.equal(s.straight, true);
  assert.deepEqual(s.notes, [said]);
  const ex = X.bundleExports(RACK, {route: ctx});
  assert.deepEqual([ex[5].straight, ex[5].few], [true, false]);
  assert.ok(ex[5].notes.includes(said));
  const notes = X.bundleNotes(ex), at = notes.indexOf(X.bundleNote(ex[5]));
  assert.ok(at >= 0 && notes.slice(at + 1, at + 4).includes(said), 'under the bundle\'s own line');
  const f = await Q.inspect(RACK, 'b6', {chassisOf: made.chassisOf, route: ctx});
  assert.deepEqual(f.length, {metres: 1.26, straight: true});
  assert.equal(f.straps.straight, true);
  assert.ok(f.notes.includes(said));
  // and not said of a bundle measured on its cables: a stretch nobody rides is no estimate
  const fine = X.bundleExports(RACK, {route: ctxOf()});
  assert.ok(fine.every(e => e.straight === false && e.few === false && !e.notes.some(n => /straight line|fewer than half/.test(n))));
  // nor of a trunk that runs on past where its members leave it: b1 with one more ring that no member rides to
  const longer = {...RACK, bundles: RACK.bundles.map(x => (x.id === 'b1' ? {...x, route: [...x.route, {item: x.route.at(-1).item, via: 'guide-3'}]} : x))};
  const s1 = got('b1', longer);
  assert.equal(s1.straight, false);
  assert.ok(B.trunkLength(longer, longer.bundles[0], {route: ctxOf(longer)}).metres > 0.5);
});

test('the bend check reads a bundle\'s corners from the line its straps are read from, not the chords between its waypoints (#1037)', () => {
  const ctx = ctxOf(), b6 = bundle('b6');
  // the straight lines from waypoint to waypoint: the room of the tightest corner is over 100 mm
  const L = B.layoutOf(RACK, b6, {route: ctx});
  const chords = B.cornersOf(L.trunk.map(w => R.pointOf(RACK, w, ctx)), {share: 'need'});
  assert.ok(Math.min(...chords.map(c => c.room_mm)) > 100, JSON.stringify(chords));
  // the cords turn 79.9 degrees at the mouth of the rear ring, 135.3 mm from the one before and 50 mm from
  // the next, which has 56.5 mm of room, shared with a 5.3 degree turn after it
  const check = B.bundleCheck(RACK, b6, {route: ctx, bendOf: () => 60});
  const tight = check.bend.violations.find(v => v.angle_deg === 79.9);
  assert.deepEqual([tight?.legs_mm, tight?.room_mm, tight?.short_mm], [[135.3, 50], 56.5, 3.5]);
  assert.ok(check.warnings.some(w => w.includes('with room for a 56.5 mm bend') && w.includes('3.5 mm short')), check.warnings.join('\n'));
  // a radius the tightest corner has room for passes it
  assert.deepEqual(B.bundleCheck(RACK, b6, {route: ctx, bendOf: () => 50}).bend.violations.filter(v => v.angle_deg === 79.9), []);
});
