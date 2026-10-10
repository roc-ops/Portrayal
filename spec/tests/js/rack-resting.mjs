// Trays and resting (#949, docs/cable-lay-design.md sections 2 and 3, step 3
// of section 10). A supported cable lies on its support, lifted by its
// radius; only a free span sags, by the drape of its family and no tighter
// than its bend radius allows, and never below a surface under it; on the
// held face of a tray a cable runs at the plate less its radius, sags between
// two tie slots it uses and never below the strap line. Every figure here is
// worked from the FHD-CMP5DR as the catalogue places it (the tray's `trays`
// entry in cable-solids-catalogue.json, a copy of the build's rack.json), and
// each check asserts it measured something, so a rule that found nothing
// cannot pass.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as R from '../../../kit/rack/route.js';
import * as S from '../../../kit/rack/solids.js';
import * as Q from '../../../kit/rack/queries.js';
import * as Rest from '../../../kit/rack/resting.js';
import {RU} from '../../../kit/rack/rails.js';
import * as F from './route-direct-fixture.mjs';
import * as G from './cable-solids-fixture.mjs';

const EPS = 1e-6;
const r15 = 1.5;                                   // an OM4 cord's radius
// the lacer of the owner's rack (i4) at U41, as placed
const BOTTOM = 40 * RU;                            // the bottom of U41
const TOP = BOTTOM + 3.0, UNDER = BOTTOM + 1.5;    // the floor's top and its underside
const SILL = BOTTOM + 3.0 + 5.6;                   // each ring's lowest inside edge
const near = (a, b, what, tol = 1e-6) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a}, want ${b}`);

// Every point of a path, and the points between them every `step` mm along
// each leg: what a check of the whole cable, and not only its corners, reads.
function along(points, step = 2) {
  const out = [];
  for (let k = 1; k < points.length; k++) {
    const p = points[k - 1], q = points[k];
    const n = Math.max(1, Math.ceil(Math.hypot(q.x - p.x, q.y - p.y, q.z - p.z) / step));
    for (let j = 0; j < n; j++) out.push({x: p.x + (q.x - p.x) * j / n, y: p.y + (q.y - p.y) * j / n, z: p.z + (q.z - p.z) * j / n});
  }
  out.push(points.at(-1));
  return out;
}
const over = (p, f) => p.x > f.x0 + EPS && p.x < f.x1 - EPS && p.z > f.z0 + EPS && p.z < f.z1 - EPS;

// ── the tray, as the catalogue places it ─────────────────────────────────

test('the FHD-CMP5DR\'s tray, placed: its floor 3 mm up the unit, its ties, and five ring openings on its sill', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  const [t, ...more] = S.traysOf(r, ctx);
  assert.equal(more.length, 0);
  assert.deepEqual([t.item, t.via, t.run, t.flipped, t.lip], ['i4', 'tray', 'x', false, 0]);
  near(t.top, TOP, 'top'); near(t.under, UNDER, 'under'); near(t.thickness, 1.5, 'thickness');
  // the strip, 48.8 to 110 out of the rail, across the 448.4 between the ears; and the two arms
  assert.equal(t.floors.length, 3);
  const strip = t.floors.find(f => f.x1 - f.x0 > 400);
  for (const [k, v] of Object.entries({x0: -224.2, x1: 224.2, z0: 48.8, z1: 110})) near(strip[k], v, k);
  // sixteen tie slots; the eight long along the run hold a cable that runs
  // along it, in pairs across it, 89.7 to 98 out of the rail
  assert.equal(t.ties.length, 16);
  const across = t.ties.filter(s => s.x1 - s.x0 > s.z1 - s.z0);
  assert.equal(across.length, 8);
  near(Math.min(...across.map(s => s.z0)), 89.7, 'strapped width, rail side');
  near(Math.max(...across.map(s => s.z1)), 98, 'strapped width, front side');
  // the rings stand on the strip: each opening 6.8 along the run, 72.2 to
  // 104.2 out of the rail, from the sill up the 29.5 of its opening
  assert.deepEqual(t.rings.map(o => o.via), ['guide-1', 'guide-2', 'guide-3', 'guide-4', 'guide-5']);
  for (const o of t.rings) {
    near(o.box.y0, SILL, `${o.via} sill`); near(o.box.y1 - o.box.y0, 29.5, `${o.via} opening`);
    near(o.box.z0, 72.2, `${o.via} rail side`); near(o.box.z1, 104.2, `${o.via} front side`);
    near(o.box.x1 - o.box.x0, 6.8, `${o.via} depth`);
  }
  // each ring where the drawing puts it, as the page reads it (route-direct-fixture RINGS)
  for (const [k, o] of t.rings.entries()) near((o.box.x0 + o.box.x1) / 2, F.RINGS[k].x, o.via, 0.05);
});

test('a tray is a pathway: rack.json lists it by id, a route names it, and it resolves', () => {
  assert.deepEqual(R.pathwaysOf(F.chassisOf('fhd-cmp5dr')), ['guide-1', 'guide-2', 'guide-3', 'guide-4', 'guide-5', 'tray']);
  const r = F.rack(), ctx = F.ctxOf(r);
  const c = {...r.cables[0], route: [{item: 'i4', via: 'tray'}], routeEdited: true};
  assert.deepEqual(R.resolveRoute(r, c, ctx), {waypoints: [{item: 'i4', via: 'tray'}], gone: [], auto: false});
  assert.ok(R.trayOf(r, {item: 'i4', via: 'tray'}, ctx));
  assert.equal(R.trayOf(r, {item: 'i4', via: 'nope'}, ctx), null);
  // a tray is not a ring: the shape of the route does not change
  assert.equal(R.routePath(r, c, ctx).rings.length, 0);
});

// ── the owner's rack: its cords rest on the floor and the sills ───────────

test('the owner\'s rack: every cord lies through its ring on the sill, lifted by its radius', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  let checked = 0;
  for (const c of r.cables) {
    const p = R.routePath(r, c, ctx);
    assert.equal(p.rings.length, 1, c.id);
    for (const at of ['entry', 'exit']) {
      const q = p.points.find(x => x.at === at);
      near(q.y, SILL + r15, `${c.id} ${at} y`);
      // at the side of the opening nearer the rail, a cord on its own
      near(q.z, 72.2 + r15, `${c.id} ${at} z`);
      checked++;
    }
    assert.deepEqual(p.rests.filter(x => x.kind === 'ring'), [{kind: 'ring', item: 'i4', via: p.rings[0].via}], c.id);
  }
  assert.equal(checked, 32);
});

test('the owner\'s rack: no point of any cord lies below a support it is over', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  const [t] = S.traysOf(r, ctx), solids = S.solidsOf(r, ctx);
  let overFloor = 0, onFloor = 0, inRing = 0;
  for (const c of r.cables) {
    const p = R.routePath(r, c, ctx);
    for (const q of along(p.points)) {
      // over the floor: on it or above it, or under the plate, never in it
      if (t.floors.some(f => over(q, f))) {
        overFloor++;
        assert.ok(q.y >= TOP + r15 - 1e-6 || q.y <= UNDER - r15 + 1e-6, `${c.id} at ${JSON.stringify(q)}`);
        if (Math.abs(q.y - (TOP + r15)) < 1e-6) onFloor++;
      }
      // inside a ring's band, above the plate: on its sill or above it
      for (const o of t.rings) {
        if (q.y > TOP && q.x > o.box.x0 + EPS && q.x < o.box.x1 - EPS && q.z > o.box.z0 + EPS && q.z < o.box.z1 - EPS) {
          inRing++;
          assert.ok(q.y >= o.box.y0 + r15 - 1e-6, `${c.id} below ${o.via}'s sill at ${JSON.stringify(q)}`);
        }
      }
    }
    // and no leg enters a body
    for (let k = 1; k < p.points.length; k++) assert.deepEqual(S.legCrossings(p.points[k - 1], p.points[k], solids, {diameter: 3}), [], c.id);
  }
  // it looked: the cords pass over the floor, some come to rest on it, and
  // every one is inside a ring's band
  assert.ok(overFloor > 500, `over the floor: ${overFloor}`);
  assert.ok(onFloor > 20, `on the floor: ${onFloor}`);
  assert.ok(inRing >= 16, `in a ring: ${inRing}`);
});

test('a free span that would sag below the floor lands on it and is supported there', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  // c1, from the upper leaf at 88.3 through ring 4 back to the panel: from
  // the ring's exit it would hang below the floor, so it lands on it
  const lands = r.cables.map(c => [c.id, R.routePath(r, c, ctx)])
    .filter(([, p]) => p.rests.some(x => x.kind === 'tray'));
  assert.ok(lands.length >= 8, lands.map(x => x[0]).join());
  for (const [id, p] of lands) {
    assert.deepEqual(p.rests.find(x => x.kind === 'tray'), {kind: 'tray', item: 'i4', via: 'tray', face: 'top', role: 'resting'}, id);
    assert.ok(p.points.some(q => q.at === 'rest' && Math.abs(q.y - (TOP + r15)) < 1e-6), `${id} lies on the floor`);
  }
});

// ── a route along the tray ─────────────────────────────────────────────

test('a route through the tray: on the floor at its radius, through each ring between on the sill', async () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  // from the upper leaf's port 49 (88.3) along the tray to bay 2 lc3 (-61.16)
  const c = {...r.cables[0], b: {item: 'i2', path: 'bay-2/module/lc3', view: 'front'}, route: [{item: 'i4', via: 'tray'}], routeEdited: true};
  const p = R.routePath(r, c, ctx);
  const tray = p.points.filter(q => q.at === 'tray');
  // on the floor at each end, through ring 3 (at 0) on its sill between
  assert.deepEqual(tray.map(q => Math.round(q.x * 10) / 10), [88.3, 3.4, -3.4, -61.2]);
  near(tray[0].y, TOP + r15, 'enters on the floor'); near(tray.at(-1).y, TOP + r15, 'leaves on the floor');
  near(tray[1].y, SILL + r15, 'ring 3, entering'); near(tray[2].y, SILL + r15, 'ring 3, leaving');
  assert.ok(tray.every(q => Math.abs(q.z - (72.2 + r15)) < 1e-9));
  assert.deepEqual(p.rests, [{kind: 'tray', item: 'i4', via: 'tray', face: 'top', role: 'resting'}]);
  assert.deepEqual(p.crossings, []);
  // inspect says what it lies on
  const info = await Q.inspect({...r, cables: [c]}, c.id, {chassisOf: F.chassisOf, route: ctx});
  assert.deepEqual(info.route.rests, [{kind: 'tray', item: 'i4', via: 'tray', face: 'top', role: 'resting'}]);
  assert.equal(info.route.text, 'CM-01 tray');
});

// ── the held face ────────────────────────────────────────────────────────

test('on the held face: at the plate less its radius under each strap, sagging between two, never below the strap line', () => {
  const r = F.rack(), base = F.ctxOf(r);
  const ctx = {...base, trayFaceOf: (cable, w) => (w.item === 'i4' && w.via === 'tray' ? 'underside' : null)};
  // from the lower leaf's port 49 (88.3) under the tray to bay 2 lc3 (-61.16)
  const c = {...r.cables[8], b: {item: 'i2', path: 'bay-2/module/lc3', view: 'front'}, route: [{item: 'i4', via: 'tray'}], routeEdited: true};
  const p = R.routePath(r, c, ctx);
  const held = p.points.filter(q => q.at === 'tray');
  const line = UNDER - r15, strap = UNDER - 2 * r15;
  // the straps it passes: the pairs whose slots run along the tray, between
  // 88.3 and -61.16: the second (x -66.45 to -43.95) and the third (44.0 to 66.5)
  const [t] = S.traysOf(r, ctx);
  const used = p.rests.find(x => x.kind === 'tray');
  assert.deepEqual([used.face, used.role], ['underside', 'held']);
  assert.ok(used.ties.length === 4, JSON.stringify(used.ties));
  const xs = used.ties.map(i => t.ties[i]).map(s => [Math.round(s.x0 * 100) / 100, Math.round(s.x1 * 100) / 100]);
  assert.deepEqual([...new Set(xs.map(x => x.join()))].sort(), ['-66.45,-43.95', '43.95,66.45']);
  // under each strap, at the plate less its radius, in the strapped width at its rail side
  const under = held.filter(q => Math.abs(q.y - line) < 1e-9);
  assert.ok(under.length >= 4, `${under.length} points under a strap`);
  assert.ok(held.every(q => Math.abs(q.z - (89.7 + r15)) < 1e-9), 'at the rail side of the strapped width');
  // between the two straps it sags, a little and never below the strap line
  const between = held.filter(q => q.x > -43.95 + EPS && q.x < 43.95 - EPS);
  assert.ok(between.length > 2);
  const low = Math.min(...between.map(q => q.y));
  assert.ok(low < line - 0.1, `it sags: lowest ${low}, strapped at ${line}`);
  assert.ok(low >= strap - 1e-9, `never below the strap line: ${low} < ${strap}`);
  // and no point of the cable is in the plate or below the strap line under it
  for (const q of along(held, 0.5)) assert.ok(q.y <= line + 1e-9 && q.y >= strap - 1e-9, JSON.stringify(q));
  // it crosses no solid: it reaches the held face from below
  assert.deepEqual(p.crossings, []);
});

test('a leg from above straight onto the held face crosses the plate: lying against it excuses only the cable that lies there', () => {
  const r = F.rack(), base = F.ctxOf(r);
  const ctx = {...base, trayFaceOf: () => 'underside'};
  const solids = S.solidsOf(r, ctx);
  // from the upper leaf, pinned under the tray
  const c = {...r.cables[0], b: {item: 'i2', path: 'bay-2/module/lc3', view: 'front'}, route: [{item: 'i4', via: 'tray'}], routeEdited: true};
  const p = R.routePath(r, c, ctx);
  const reach = p.points[1], first = p.points.find(q => q.at === 'tray');
  near(first.y, UNDER - r15, 'on the held face');
  // the straight leg from the plug above to the held face passes through the floor
  const straight = S.legCrossings(reach, first, solids, {diameter: 3});
  assert.deepEqual(straight.map(x => `${x.solid.item}:${x.solid.part}`), ['i4:tray/floor']);
  // the kit does not lay it so: it goes round the front edge first (section
  // 1.3, rule 1), and what it lays crosses nothing
  assert.ok(p.detours.length >= 1);
  assert.ok(p.detours[0].points.some(q => q.z > 110 + r15), 'round the front edge');
  assert.deepEqual(p.crossings, []);
  // a cable lying on the held face itself is no crossing: along the plate, a radius below it
  assert.deepEqual(S.legCrossings({x: -150, y: UNDER - r15, z: 91.2}, {x: 150, y: UNDER - r15, z: 91.2}, solids, {diameter: 3}), []);
});

test('a held face is offered only with tie slots: without them the cable lies on the face that looks up', () => {
  const noTies = {...F.chassisOf('fhd-cmp5dr'), trays: F.chassisOf('fhd-cmp5dr').trays.map(t => ({...t, ties: []}))};
  const r = F.rack(), base = F.ctxOf(r);
  const ctx = {...base, chassisOf: ref => (ref === 'fhd-cmp5dr' ? noTies : base.chassisOf(ref)), trayFaceOf: () => 'underside'};
  const c = {...r.cables[8], route: [{item: 'i4', via: 'tray'}], routeEdited: true};
  const p = R.routePath(r, c, ctx);
  assert.deepEqual(p.rests.find(x => x.kind === 'tray'), {kind: 'tray', item: 'i4', via: 'tray', face: 'top', role: 'resting'});
  assert.ok(p.points.filter(q => q.at === 'tray').every(q => q.y > TOP));
});

// ── drape and the bend radius ────────────────────────────────────────────

test('DRAPE: fibre and AOC limp, twisted pair half, DAC and power stiff; the family is the media\'s', () => {
  assert.deepEqual(Rest.DRAPE, {fiber: 1, aoc: 1, copper: 0.5, dac: 0.35, power: 0.35});
  assert.deepEqual(['om4', 'os2', 'cat6', 'cat6a', 'dac', 'aoc', 'power', undefined, 'constructor'].map(m => Rest.familyOf({media: m})),
    ['fiber', 'fiber', 'copper', 'copper', 'dac', 'aoc', 'power', 'copper', 'copper']);
  assert.equal(Rest.drapeOf({media: 'power'}), 0.35);
  // the cable types table, when the page gives its lookup: the cable's own type first, else its media
  const typeOf = id => ({'power-c19': {family: 'power'}, 'x-fibre': {family: 'fiber'}, cat6: {family: 'copper'}}[id] ?? null);
  assert.equal(Rest.familyOf({type: 'power-c19', media: 'cat6'}, {typeOf}), 'power');
  assert.equal(Rest.familyOf({type: 'nope', media: 'cat6'}, {typeOf}), 'copper');
  assert.equal(Rest.familyOf({type: 'x-fibre'}, {typeOf}), 'fiber');
  assert.equal(Rest.familyOf({media: 'dac'}, {typeOf: () => { throw new Error('x'); }}), 'dac');
  assert.equal(Rest.familyOf({media: 'dac'}, {typeOf: () => ({family: 'nonsense'})}), 'dac');
  // the bend radius: the page's, else the table's installed figure by media
  assert.equal(Rest.bendOf({media: 'om4'}, {}), 25);
  assert.equal(Rest.bendOf({media: 'cat6a'}, {}), 30);
  assert.equal(Rest.bendOf({media: 'power'}, {}), 42.6);
  assert.equal(Rest.bendOf({media: 'om4'}, {bendOf: () => 40}), 40);
  for (const bad of [null, 0, -5, NaN, '30']) assert.equal(Rest.bendOf({media: 'dac'}, {bendOf: () => bad}), 23, String(bad));
  assert.equal(Rest.bendOf({media: 'dac'}, {bendOf: () => { throw new Error('x'); }}), 23);
});

test('a free span sags by its drape, no tighter than its bend radius over its drape, and a stiff one lands further along', () => {
  const p = {x: 0, y: 100, z: 0}, q = {x: 300, y: 100, z: 0};
  const depth = (drape, bend) => 100 - Math.min(...Rest.hang(p, q, {drape, bend}).points.map(x => x.y));
  // fibre (25 mm): the drawing's catenary, 20 + 0.3 x 300, where the bend allows it
  near(depth(1, 25), 110, 'fibre', 0.5);
  // stiffer families sag less
  assert.ok(depth(1, 25) > depth(0.5, 24) && depth(0.5, 24) > depth(0.35, 23));
  // the bend radius bounds it: a short span sags far less than the catenary
  const short = {x: 60, y: 100, z: 0};
  const d60 = 100 - Math.min(...Rest.hang(p, short, {drape: 1, bend: 25}).points.map(x => x.y));
  assert.ok(d60 < 20 + 0.3 * 60 && d60 > 0, `${d60}`);
  near(Rest.sagOf(60, 1, 25), d60, 'the bound', 0.05);
  // no bend on a sagging span is tighter than the radius over the drape:
  // the radius through three neighbouring points of its curve
  for (const [drape, bend] of [[1, 25], [0.5, 24], [0.35, 23]]) {
    const R0 = bend / drape;
    for (const end of [short, q]) {
      const pts = [p, ...Rest.hang(p, end, {drape, bend}).points, end];
      for (let k = 2; k < pts.length - 2; k++) {
        const [a, b, c] = [pts[k - 1], pts[k], pts[k + 1]];
        const ab = Math.hypot(b.x - a.x, b.y - a.y), bc = Math.hypot(c.x - b.x, c.y - b.y), ca = Math.hypot(a.x - c.x, a.y - c.y);
        const area = Math.abs((b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y)) / 2;
        if (area > 1e-9) assert.ok(ab * bc * ca / (4 * area) >= R0 - 0.5, `drape ${drape}: radius ${ab * bc * ca / (4 * area)} < ${R0}`);
      }
    }
  }
  // over a floor 8 mm below both ends, each lands; the stiff one further along
  const floor = [{x0: -10, x1: 400, z0: -10, z1: 10, y: 92 - r15}];
  const landsAt = (drape, bend) => {
    const pts = Rest.hang(p, q, {r: r15, drape, bend, surfaces: floor}).points;
    return pts.find(x => Math.abs(x.y - 92) < 1e-6)?.x;
  };
  const limp = landsAt(1, 25), stiff = landsAt(0.35, 23);
  assert.ok(limp > 0 && stiff > limp, `limp ${limp}, stiff ${stiff}`);
  // and never below the floor anywhere
  for (const [drape, bend] of [[1, 25], [0.35, 23]])
    assert.ok(Rest.hang(p, q, {r: r15, drape, bend, surfaces: floor}).points.every(x => x.y >= 92 - 1e-9));
});

test('a span from a support to a surface below drops onto it in two bends of the radius, and lands level', () => {
  const floor = [{x0: -1, x1: 401, z0: -1, z1: 1, y: 100}];
  const onFloor = pts => pts.filter(x => Math.abs(x.y - 100) < 1e-9).map(x => x.x);
  // a 40 mm drop at R 25, no deeper than 2R: a bend down and a bend back,
  // each turning acos(1 - 40 / 50), landing 2R sin of that along
  const p = {x: 0, y: 140, z: 0}, q = {x: 400, y: 140, z: 0};
  const a = Rest.hang(p, q, {r: 0, drape: 1, bend: 25, surfaces: floor});
  assert.equal(a.lands.length, 1);
  const e = 50 * Math.sin(Math.acos(1 - 40 / 50));
  near(Math.min(...onFloor(a.points)), e, 'lands 2R sin(theta) along');
  near(Math.max(...onFloor(a.points)), 400 - e, 'and leaves as far before the end');
  // the two bends meet mid-drop, half-way down
  const mid = a.points.find(x => Math.abs(x.x - e / 2) < 1e-6);
  near(mid.y, 120, 'half-way down at the middle of the drop');
  // a 70 mm drop, deeper than 2R: two quarter bends and a straight fall
  // between, 25 along, from 25 below the start to 25 above the floor
  const deep = Rest.hang({x: 0, y: 170, z: 0}, {x: 400, y: 170, z: 0}, {r: 0, drape: 1, bend: 25, surfaces: floor});
  near(Math.min(...onFloor(deep.points)), 50, 'lands 2R along');
  const fall = deep.points.filter(x => Math.abs(x.x - 25) < 1e-6).map(x => Math.round(x.y * 1000) / 1000);
  assert.deepEqual(fall, [145, 125]);
});

test('a span that is a fall or a rise is straight; a sag that would enter a body is not laid', () => {
  assert.deepEqual(Rest.hang({x: 0, y: 0, z: 0}, {x: 2, y: 300, z: 1}).points, []);
  // routePath keeps the chord where a sag would cross a body the chord does not
  const box = {item: 'b', part: 'body', box: {x0: 40, x1: 60, y0: -50, y1: -2, z0: -10, z1: 10}};
  assert.equal(Rest.newCrossing({x: 0, y: 0, z: 0}, {x: 100, y: 0, z: 0}, [{x: 50, y: -10, z: 0}], [box], 0), true);
  assert.equal(Rest.newCrossing({x: 0, y: 0, z: 0}, {x: 100, y: 0, z: 0}, [{x: 50, y: -1, z: 0}], [box], 0), false);
});

test('an unrouted jumper hangs by the same rule, onto the top of a body below it rather than into it', () => {
  // two switches at U20, a shelf standing out of the rails at U19 under their
  // fronts: a short jumper between their ports hangs in front of them, and
  // lands on the shelf rather than sagging into it
  let r = G.add(G.add(G.add({...G.ownerRack(), items: []}, 'sw', 20, {label: 'a'}), 'shelf', 19, {label: 'shelf'}), 'sw', 21, {label: 'b'});
  const c = G.cable('j1', G.end('i1', 'p'), G.end('i3', 'q'));
  const ctx = {...G.ctxOf({ports: {i1: {p: -150}, i3: {q: 150}}, portY: {i1: 19 * RU + 20, i3: 20 * RU + 5}}), guidesOf: () => []};
  r = {...r, cables: [c]};
  assert.deepEqual(R.autoRoute(r, c, ctx), []);
  const p = R.routePath(r, c, ctx);
  const shelfTop = 19 * RU;
  assert.deepEqual(p.rests, [{kind: 'body', item: 'i2', part: 'envelope'}]);
  assert.ok(p.points.every(q => q.y >= shelfTop + r15 - 1e-9));
  assert.ok(p.points.some(q => Math.abs(q.y - (shelfTop + r15)) < 1e-9), 'lies on the shelf');
  assert.deepEqual(p.crossings, []);
});

// ── as mounted ───────────────────────────────────────────────────────────

test('a tray on the rear rails rests the cable on its sill at the side of the opening nearer the rear rail', () => {
  let r = G.add({...G.ownerRack(), items: []}, 'panel', 12, {face: 'rear'});
  r = G.add(r, 'fhd-cmp5dr', 12, {on: 'i1', unit: 1, face: 'rear'});
  r = G.add(r, 'sw', 13, {face: 'rear'});
  const c = G.cable('c1', G.end('i3', 'p'), G.end('i1', 'q'), 'om4', {route: [{item: 'i2', via: 'guide-2'}], routeEdited: true});
  const ctx = G.ctxOf({ports: {i3: {p: 100}, i1: {q: 30}}});
  ctx.guidesOf = id => (id === 'i2' ? G.RINGS.map(g => ({...g, face: 'rear', x: -g.x})) : []);
  const [t] = S.traysOf(r, ctx);
  // the rear rail plane is -740, the tray 110 behind it: the opening 72.2 to
  // 104.2 behind the rail, so its rail side is the higher z
  const o = t.rings.find(x => x.via === 'guide-2');
  near(o.box.z1, -740 - 72.2, 'rail side'); near(o.box.z0, -740 - 104.2, 'far side');
  const p = R.routePath({...r, cables: [c]}, c, ctx);
  const entry = p.points.find(q => q.at === 'entry');
  near(entry.y, 11 * RU + 3 + 5.6 + r15, 'on the sill');
  near(entry.z, -740 - 72.2 - r15, 'at the rail side');
  assert.deepEqual(p.crossings, []);
});

test('traysOf: a catalogue without trays gives none, and a narrow part turned end over end holds the cable on the band now below', () => {
  const r = F.rack();
  assert.deepEqual(S.traysOf(r, {...F.ctxOf(r), chassisOf: ref => ({...F.chassisOf(ref), trays: undefined})}), []);
  assert.deepEqual(S.traysOf(r, {}), []);
  // a narrow tray on the right rail is placed turned end over end (solids.js
  // railOf), as a part rolled 180 degrees would be: its own top looks down,
  // its rings hang, and the opening's lowest inside edge is its far band
  const narrow = {ru: 1, w: 60, h: 44, d: 110, mount: 'rack-face', shell: 'sheet', thickness: 1.5,
    trays: [{id: 'tray', top: 3, thickness: 1.5, run: 'x', lip: 0,
      floor: [{x: 0, y: 1.5, z: 0, w: 60, h: 1.5, d: 61.2}], ties: [],
      rings: [{via: 'guide-1', run: 'x', box: {x: 20, y: 8.6, z: 5.8, w: 6.8, h: 29.5, d: 32}}]}]};
  let rr = G.add({...G.ownerRack(), items: []}, 'narrow', 12, {side: 'right'});
  const ctx = {chassisOf: ref => (ref === 'narrow' ? narrow : null), guidesOf: () => [], portX: () => null};
  const [t] = S.traysOf(rr, ctx);
  assert.equal(t.flipped, true);
  // turned about the middle of its 44 mm, from the bottom of U12: the plate
  // is 3 mm below its top, and the rings hang below the plate
  const top = 11 * RU + 44;
  near(t.top, top - 1.5, 'its upward face is its own underside');
  near(t.under, top - 3, 'its downward face is its own top');
  const o = t.rings[0];
  near(o.box.y1, top - 8.6, 'the near band, against the plate');
  near(o.box.y0, top - 8.6 - 29.5, 'the far band, below: where a cable rests');
});

test('a sag that would cut through a body its chord passes over is not laid: the span keeps its chord', () => {
  // a sheet part at U13 whose only plate is a 4 mm rib, 60 out of the rail,
  // 1 mm in from one end of a jumper between two ports of the switch above,
  // 90 apart and 4 above the rib: the catenary from that end would cut
  // through the rib before its first sample reached it
  const plate = {ru: 1, w: 482, h: 44.45, d: 60, mount: 'rack-face', shell: 'sheet',
    solids: [{part: 'rib', box: {x: 241 - 44, y: 30, z: 0, w: 4, h: 1.5, d: 60}}]};
  const SIZES = {sw: {ru: 1, w: 440, h: 44, d: 300}, plate};
  let r = G.add(G.add({...G.ownerRack(), items: []}, 'plate', 13), 'sw', 14);
  const top = 12 * RU + 31.5;
  const c = G.cable('j1', G.end('i2', 'p'), G.end('i2', 'q'));
  r = {...r, cables: [c]};
  const ctx = {chassisOf: ref => SIZES[ref] || null, guidesOf: () => [], portX: e => (e.path === 'p' ? -45 : 45),
    portY: () => top + 4};
  const p = R.routePath(r, c, ctx);
  assert.deepEqual(p.crossings, []);
  // the span between the two reach points is straight: no point of it hung
  assert.deepEqual(p.points.map(q => q.at), ['a', 'reach', 'reach', 'b']);
  // and what it would have laid does enter the rib
  const [ra, rb] = [p.points[1], p.points[2]];
  const hung = Rest.hang(ra, rb, {r: r15, drape: 1, bend: 25, surfaces: Rest.surfacesOf(r, ctx)}).points;
  assert.ok(hung.length > 2);
  assert.equal(Rest.newCrossing(ra, rb, hung, S.solidsOf(r, ctx), 3), true);
});
