// The gap behind a tray's floor, a way up or down beside its front edge
// (#966, docs/cable-lay-design.md section 1.3, rule 1). The router finds the
// gap from the floor boxes a tray publishes, takes it or the front-edge detour
// by length after the installed bend radius, and only by itself: no saved key
// points at a gap. Every figure was measured on these fixtures; the lengths
// "on main" are what the kit gave before the gap was built (origin/main at
// 713499fab), and each check asserts it found something, so a check that
// found nothing cannot pass.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, readdirSync} from 'node:fs';
import * as R from '../../../kit/rack/route.js';
import * as S from '../../../kit/rack/solids.js';
import * as M from '../../../kit/rack/model.js';
import {apply} from '../../../kit/rack/commands.js';
import {cornersOf} from '../../../kit/rack/route-path.js';
import * as F from './cable-solids-fixture.mjs';

const r1 = v => Math.round(v * 10) / 10;
const mm = p => r1(R.pathLength(p).measured * 1000);
// the reference rack of #949, an FHD-CMP5DR above a panel, a switch above and a switch below
const owner = () => ({rack: {...F.ownerRack(), cables: F.OWNER_CABLES}, ctx: F.ctxOf()});
// THE GAP IS TAKEN ONLY WHERE THE CORD CAN BE DRAWN THROUGH IT (P-0218-2, owner's option A,
// 2026-10-22): out of a plug, the cord goes straight to the reach point and then turns onto the
// rise with a bend of at least its radius (25), all clear of the strip's front edge. The gap is
// 48.8 deep and the rise stands 6.5 (radius and CLEAR) short of the strip, at 42.3 from the
// rail: so a reach of 17.3 mm or less leaves the 25 to bend in. The LC plug's 27.6 does not,
// and c2 (#1185) goes round the front edge. These tests of the gap's other rules (what it is
// held to, who may use it) need a cord that does rise, so they give the cords a plug of
// SHORT mm, which can.
const SHORT = 10;
const shortPlug = (extra = {}) => F.ctxOf({...extra, ctx: {plugReachOf: () => SHORT, ...(extra.ctx || {})}});
const shortOwner = () => ({rack: {...F.ownerRack(), cables: F.OWNER_CABLES}, ctx: shortPlug()});
const ids = list => Object.fromEntries(list.map(c => [c.id, c]));
const pts = d => d.points.map(q => [r1(q.x), r1(q.y), r1(q.z)]);

test('a tray\'s gap is found from the floors it publishes: the strip\'s back edge to the rail, between its arms', () => {
  const {rack, ctx} = owner();
  const [g] = S.gapsOf(rack, ctx);
  // named for the tray it belongs to, and its width: the FHD-CMP5DR's strip
  // starts 48.8 from the rail (61.2 deep of the 110), and the arms, 15.4 to
  // 48.8 out, stand at its ends: 10.5 wide, 17.3 in from the 483
  assert.deepEqual({item: g.item, via: g.via, away: g.away, width: g.width, edge: g.edge},
    {item: 'i3', via: 'tray', away: 1, width: 48.8, edge: 48.8});
  assert.deepEqual([g.x0, g.x1, g.z0, g.z1].map(r1), [-213.7, 213.7, 0, 48.8]);
  assert.equal(S.gapsOf(rack, ctx).length, 1);
  // it is the plan the floor leaves, so a part whose floor reaches the rail has none, as does
  // one that publishes no floor
  const none = ref => ({...F.chassisOf(ref), ...(ref === 'fhd-cmp5dr' ? {trays: undefined} : {})});
  assert.deepEqual(S.gapsOf(rack, {...ctx, chassisOf: none}), []);
  const closed = {...F.SIZES, 'fhd-cmp5dr': F.closed()};
  assert.deepEqual(S.gapsOf(rack, {...ctx, chassisOf: ref => closed[ref] ?? null}), []);
  // a rear-mounted tray has the mirror: the strip's back edge less than the rail
  let rear = F.add({...F.ownerRack(), items: []}, 'panel', 12, {face: 'rear'});
  rear = F.add(rear, 'fhd-cmp5dr', 12, {on: 'i1', unit: 1, face: 'rear'});
  const [h] = S.gapsOf(rear, F.ctxOf());
  assert.deepEqual([h.away, h.width, h.z0, h.z1, h.edge].map(r1), [-1, 48.8, -788.8, -740, -788.8]);
});

test('on the FHD-CMP5DR c2 does NOT rise through the gap: its LC plug leaves no room to draw the bend there', () => {
  // CHANGED from #1185's "c2 rises through the gap" (480 mm): drawable geometry, owner's option
  // A, 2026-10-22. c2 is the switch below's port 100 to the panel, through ring 2: out of its
  // plug (27.6 out of the rail plane, 14.7 short of the 42.3 the rise would stand at, where
  // 25 is needed for the bend), so it goes round the front edge, as it did before #1185.
  const {rack, ctx} = owner();
  const c = ids(rack.cables);
  const p = R.routePath(rack, c.c2, ctx);
  const [d] = p.detours;
  assert.equal(p.detours.length, 1);
  assert.deepEqual(d.between, [{end: 'a'}, {item: 'i3', via: 'guide-3'}]);
  assert.deepEqual(pts(d), [[-100, 466.7, 123.7], [-28.4, 499.3, 123.7]]);
  assert.ok(d.points.every(q => q.z > 110), JSON.stringify(d.points));
  assert.deepEqual([p.bends, p.crossings], [[], []]);
  // #1185 had it at 483.6 mm through the gap; round the front edge it is 610.6 mm, 127.0 longer
  assert.equal(mm(p), 610.6);
  assert.equal(r1(610.6 - 483.6), 127);
  assert.equal(R.routedLength(rack, c.c2, ctx).value, 1);
  // and no cord of this rack rises: c1 and c3 stay round the front edge, c4 and c5 come from
  // above and meet no floor
  const rose = rack.cables.filter(x => R.routePath(rack, x, ctx).detours.some(e => e.points.every(q => q.z < 48.8))).map(x => x.id);
  assert.deepEqual(rose, []);
});

test('on the FHD-CMP5DR a cord whose plug leaves the room for the bend rises through the gap, and is shorter than round the front edge', () => {
  // (#1185's c2 test, on a plug 10 mm out, where 32.3 mm are left to bend in: SHORT, above)
  const {rack, ctx} = shortOwner();
  const c = ids(rack.cables);
  const p = R.routePath(rack, c.c2, ctx);
  // out of its plug (10 out of the rail plane), up behind the strip's back edge at 48.8 and across the
  // strip to the ring's approach point. The point stands the cord's radius and CLEAR (6.5) short of the edge
  const [d] = p.detours;
  assert.equal(p.detours.length, 1);
  assert.deepEqual(d.between, [{end: 'a'}, {item: 'i3', via: 'guide-3'}]);
  assert.deepEqual(pts(d), [[-61, 498.7, 42.3]]);
  assert.ok(d.points.every(q => q.z > 0 && q.z < 48.8 - 1.5 - S.CLEAR + 1e-9), JSON.stringify(d.points));
  assert.deepEqual([p.bends, p.crossings], [[], []]);
  // the rise stands 32.3 out of the reach point, the 25 of the bend and more
  assert.ok(d.points[0].z - SHORT >= 25);
  assert.equal(mm(p), 479.8);
  assert.equal(R.routedLength(rack, c.c2, ctx).value, 0.5);
  // the reach is the line: a plug that stands 17.4 out (0.1 mm short of the 25) does not
  const near = shortPlug({ctx: {plugReachOf: () => 17.4}});
  assert.ok(R.routePath(rack, c.c2, near).detours[0].points.every(q => q.z > 110));
  const far = shortPlug({ctx: {plugReachOf: () => 17.3}});
  assert.ok(R.routePath(rack, c.c2, far).detours[0].points.every(q => q.z < 48.8));
});

test('a cord too thick for the gap keeps the front-edge detour; one that fits does not', () => {
  const {rack, ctx} = owner();
  const solids = S.solidsOf(rack, ctx), gaps = S.gapsOf(rack, ctx);
  // from the switch below (U5) to a point over the strip, clear of the rings: a long rise
  const a = {x: -55, y: 200, z: 27.6}, b = {x: -55, y: 600, z: 100};
  const way = (diameter, g = gaps) => S.detour(a, b, solids, {diameter, lanes: [], room: 50, gaps: g});
  // a 3 mm cord, a 20 and a 40, and one exactly the gap's 48.8, rise behind the strip
  for (const d of [3, 20, 40, 48.8]) {
    const [q] = way(d);
    assert.ok(q.z > 0 && q.z < 48.8, `${d} mm: ${JSON.stringify(q)}`);
  }
  assert.deepEqual(way(3).map(q => [q.x, r1(q.y), r1(q.z)]), [[-55, 498.7, 42.3]]);
  // 0.1 mm more is wider than the gap: round the front edge, as without gaps
  const wide = way(48.9);
  assert.deepEqual(wide.map(q => [q.x, q.y, r1(q.z)]), [[-55, 600, 150]]);
  assert.ok(wide[0].z > 110);
  assert.deepEqual(wide, way(48.9, []));
  assert.equal(wide.gap, undefined);
  // and the same cord at 3 mm with no gaps offered is round the front edge too
  assert.deepEqual(way(3, []).map(q => [q.x, q.y, r1(q.z)]), [[-55, 600, 150]]);
});

test('a bundle fits the gap by its diameter, as a cable does: a wide one keeps the front-edge detour', () => {
  // (on a short plug: the cords rise only where the bend can be drawn, P-0218-2, owner's option A, 2026-10-22)
  const {rack: base} = shortOwner();
  const c2 = base.cables[1];
  // twelve-millimetre cords, the cord c2 and n-1 more like it, bundled
  const bundled = n => {
    const extra = Array.from({length: n - 1}, (_, k) => ({...c2, id: `x${k}`}));
    return {...base, cables: [...base.cables, ...extra],
      bundles: [{id: 'b1', number: 1, label: 'B', members: [c2, ...extra].map(c => ({cable: c.id})), route: []}]};
  };
  const ctx = shortPlug({ctx: {diameterOf: () => 12}});
  const run = rack => R.routePath(rack, rack.cables[1], ctx);
  // alone, a 12 mm cord rises through the gap
  const alone = run(base);
  assert.deepEqual(pts(alone.detours[0]), [[-64.6, 503.2, 37.8]]);
  // eight in a bundle are 37.9 mm across (sqrt(8 x 144 / 0.8)), which fits the gap's 48.8; but
  // CHANGED (drawable geometry, owner's option A, 2026-10-22): the rise would stand 24.8 from
  // the rail, 14.8 mm out of a 10 mm plug, short of the 25 to bend in, so the bundle goes round
  // the front edge. #1185 had it through the gap, at [-53.4, 503.8, 24.8]
  assert.equal(r1(Math.sqrt(8 * 144 / 0.8)), 37.9);
  const eight = run(bundled(8));
  assert.ok(eight.detours[0].points.every(q => q.z > 110), JSON.stringify(eight.detours));
  // (a plug on the rail plane has the room: the fit by diameter is the router's, with no plug in the way)
  const rail = (x, y) => ({x, y, z: 0});
  const open = S.detour(rail(-55, 200), {x: -55, y: 600, z: 100}, S.solidsOf(base, ctx), {diameter: 37.9, lanes: [], room: 50, gaps: S.gapsOf(base, ctx)});
  assert.ok(open.every(q => q.z < 48.8), JSON.stringify(open));
  // fourteen are 50.2 mm: wider than the gap, so the bundle goes round the front edge
  assert.equal(r1(Math.sqrt(14 * 144 / 0.8)), 50.2);
  const wide = run(bundled(14));
  assert.deepEqual(wide.detours.map(pts), [[[-100, 466.7, 128.2], [-28.4, 503.8, 128.2]]]);
  assert.ok(wide.detours[0].points.every(q => q.z > 110));
  assert.deepEqual([wide.bends, wide.crossings], [[], []]);
});

test('a tray with no gap behind it keeps today\'s route, to the millimetre', () => {
  const {rack, ctx} = owner();
  const closed = {...F.SIZES, 'fhd-cmp5dr': F.closed()};
  const shut = {...ctx, chassisOf: ref => closed[ref] ?? null};
  assert.deepEqual(S.gapsOf(rack, shut), []);
  // as on main, with the same catalogue: round the front edge, 123.7 out
  const got = Object.fromEntries(rack.cables.map(c => [c.id, mm(R.routePath(rack, c, shut))]));
  assert.deepEqual(got, {c1: 851.8, c2: 610.6, c3: 614.8, c4: 467.3, c5: 539.8});
  const p = R.routePath(rack, rack.cables[1], shut);
  assert.deepEqual(p.detours.map(pts), [[[-100, 466.7, 123.7], [-28.4, 499.3, 123.7]]]);
  assert.ok(p.detours[0].points.every(q => q.z > 110));
  // the rear rails: the front edge faces the rear, and the gap is its mirror
  let r = F.add({...F.ownerRack(), items: []}, 'panel', 12, {face: 'rear'});
  r = F.add(r, 'fhd-cmp5dr', 12, {on: 'i1', unit: 1, face: 'rear'});
  r = F.add(r, 'sw', 5, {face: 'rear'});
  const cord = F.cable('c1', F.end('i3', 'p'), F.end('i1', 'q'), 'om4', {route: [{item: 'i2', via: 'guide-2'}], routeEdited: true});
  const rctx = F.ctxOf({guides: {i2: F.RINGS.map(g => ({...g, face: 'rear'}))}, ports: {i3: {p: 100}, i1: {q: 30}}});
  rctx.guidesOf = id => (id === 'i2' ? F.RINGS.map(g => ({...g, face: 'rear'})) : []);
  const shutRear = {...rctx, chassisOf: ref => closed[ref] ?? null};
  const q = R.routePath({...r, cables: [cord]}, cord, shutRear);
  assert.deepEqual(q.detours[0].points.map(x => r1(x.z)), [-740 - 73.7 - 2.5 * 25]);
});

test('the turn in the gap keeps its bend radius: through it only where its corners have their room', () => {
  // (on a short plug, as c2's own is too long to be drawn through the gap: P-0218-2, owner's option A, 2026-10-22)
  const {rack, ctx} = shortOwner();
  const p = R.routePath(rack, rack.cables[1], ctx);
  const need = 25;
  // no corner of the cord, the two turns of the rise among them, is short of 25 mm
  const turns = cornersOf(p.points, {share: 'need'});
  const at = p.points.findIndex(q => q.at === 'detour');
  const here = turns.filter(c => c.k >= at - 1 && c.k <= at + 1);
  assert.ok(here.length >= 2, JSON.stringify(here));
  for (const c of turns) assert.ok(c.room_mm >= need - 1e-9, `corner ${c.k}: ${c.room_mm}`);
  assert.deepEqual(p.bends, []);
  // at the detour itself, the least room is 25.0 mm and more
  assert.ok(Math.min(...here.map(c => c.room_mm)) >= need);
  // a cord of a larger radius has the same gap and does not fit its turn there: the same rise, asked
  // for a bend radius of 60 mm (room is twice it), goes round the front edge
  const solids = S.solidsOf(rack, ctx), gaps = S.gapsOf(rack, ctx);
  const a = {x: -100, y: 466.725, z: 27.6}, b = {x: -28.4, y: 499.275, z: 73.7};
  const through = room => S.detour(a, b, solids, {diameter: 3, lanes: [], room, gaps});
  assert.ok(through(50).every(q => q.z < 48.8), JSON.stringify(through(50)));
  assert.ok(through(120).every(q => q.z > 110), JSON.stringify(through(120)));
  // and without a bend radius to hold it to (room 0), the gap is not offered at all
  assert.ok(through(0).every(q => q.z > 110), JSON.stringify(through(0)));
});

test('a lay that rises through the gap and leaves a corner short is the front edge; and a cord that does not meet a tray is as it was', () => {
  const {rack, ctx} = owner();
  const c = ids(rack.cables);
  // c1 and c3 would rise through the gap and leave the leg across the strip short of the
  // room its two turns need: they go round the front edge, to the millimetre as on main
  for (const [id, len] of [['c1', 851.8], ['c3', 614.8]]) {
    const p = R.routePath(rack, c[id], ctx);
    assert.equal(mm(p), len, id);
    assert.ok(p.detours[0].points.every(q => q.z > 110), id);
    assert.deepEqual(p.bends, [], id);
  }
  // the cords from the switch above meet no tray: no detour, and as on main
  for (const [id, len] of [['c4', 467.3], ['c5', 539.8]]) {
    const p = R.routePath(rack, c[id], ctx);
    assert.equal(mm(p), len, id);
    assert.deepEqual(p.detours, [], id);
  }
});

test('a saved rack opens, and a rack with no tray is as it was', () => {
  const dir = new URL('../fixtures/racks/', import.meta.url);
  let opened = 0, cables = 0;
  for (const f of readdirSync(dir).filter(n => n.endsWith('.json')).sort()) {
    const doc = M.parseDoc(JSON.parse(readFileSync(new URL(f, dir), 'utf8')));
    for (const rack of doc.racks || []) {
      // (real device names, each a plain box of its units: no tray in any)
      const chassisOf = ref => ({ru: 1, w: 440, h: 43.5, d: 400, model: String(ref).toUpperCase()});
      const ctx = {chassisOf, guidesOf: () => [], portX: e => (rack.items.some(i => i.id === e.item) ? (e.path.length * 7) % 300 - 150 : null)};
      assert.deepEqual(S.gapsOf(rack, ctx), [], f);
      for (const c of rack.cables || []) { R.routePath(rack, c, ctx); cables++; }
      opened++;
    }
  }
  assert.ok(opened > 0 && cables > 0, `${opened} racks, ${cables} cables`);
  // a rack whose tray publishes no floor (a catalogue older than `trays`) opens and routes as it did
  const {rack, ctx} = owner();
  const old = ref => { const c = F.chassisOf(ref); return c?.trays ? {...c, trays: undefined} : c; };
  const bare = {...ctx, chassisOf: old};
  assert.deepEqual(S.gapsOf(rack, bare), []);
  for (const c of rack.cables) assert.doesNotThrow(() => R.routePath(rack, c, bare), c.id);
});

// What main gave: the same rack with the gap closed (a floor that reaches the rail leaves none), the
// strip's front edge where it was
const asMain = ctx => {
  const closed = {...F.SIZES, 'fhd-cmp5dr': F.closed()};
  return {...ctx, chassisOf: ref => closed[ref] ?? null};
};
// whether the cord rises through the gap: it is shorter than main's route round the front edge
const rose = (rack, c, ctx) => mm(R.routePath(rack, c, asMain(ctx))) - mm(R.routePath(rack, c, ctx)) > 1;

test('a hand-edited route never uses the gap: no leg of it, those between its waypoints too, is offered one', () => {
  // (on a short plug, so that the automatic cord does rise: P-0218-2, owner's option A, 2026-10-22)
  const {rack: base, ctx} = shortOwner();
  const main = asMain(ctx);
  const ring3 = {item: 'i3', via: 'guide-3'}, ring2 = {item: 'i3', via: 'guide-2'};
  // the same cord, c2, written by hand: one waypoint, and two in either order
  const routes = [[ring3], [ring2, ring3], [ring3, ring2]];
  for (const route of routes) {
    const c = {...base.cables[1], route, routeEdited: true};
    const rack = {...base, cables: [c]};
    assert.deepEqual(R.resolveRoute(rack, c, ctx).waypoints, route);
    const p = R.routePath(rack, c, ctx), m = R.routePath(rack, c, main);
    const text = JSON.stringify(route.map(w => w.via));
    assert.deepEqual(rack.cables[0].route, route, text);
    assert.equal(rose(rack, c, ctx), false, text);
    // the route of main, point for point and to the millimetre
    assert.deepEqual(p.points, m.points, text);
    assert.deepEqual([p.detours, p.bends, p.crossings], [m.detours, m.bends, m.crossings], text);
    assert.equal(mm(p), mm(m), text);
  }
  // the front-edge detour of one waypoint is main's, 123.7 out: 610.2 mm on this plug; the automatic cord is 479.8
  const one = {...base.cables[1], route: [ring3], routeEdited: true};
  const p = R.routePath({...base, cables: [one]}, one, ctx);
  assert.equal(p.detours.length, 1);
  assert.deepEqual(p.detours[0].between, [{end: 'a'}, ring3]);
  assert.ok(p.detours[0].points.every(q => q.z > 110));
  assert.equal(mm(p), 610.2);
});

test('a route written by the route command is hand-edited, and never uses the gap', () => {
  // (on a short plug, so that the automatic cord does rise: P-0218-2, owner's option A, 2026-10-22)
  const {rack: base, ctx} = shortOwner();
  const before = R.routePath(base, base.cables[1], ctx);
  assert.equal(rose(base, base.cables[1], ctx), true);
  const done = apply(base, {op: 'cable.route', id: 'c2', route: [{item: 'i3', via: 'guide-3'}]}, ctx);
  assert.equal(done.error, undefined);
  const c = done.rack.cables.find(x => x.id === 'c2');
  assert.equal(c.routeEdited, true);
  const p = R.routePath(done.rack, c, ctx);
  assert.equal(rose(done.rack, c, ctx), false);
  assert.deepEqual(p.points, R.routePath(done.rack, c, asMain(ctx)).points);
  assert.equal(mm(p), 610.2);
  // and the cord is put back on its own route: it rises through the gap again
  const back = apply(done.rack, {op: 'cable.route.reset', id: 'c2'}, ctx);
  assert.equal(back.error, undefined);
  const q = R.routePath(back.rack, back.rack.cables.find(x => x.id === 'c2'), ctx);
  assert.equal(rose(back.rack, back.rack.cables.find(x => x.id === 'c2'), ctx), true);
  assert.deepEqual(q.points, before.points);
});

test('on one rack the automatic cord rises through the gap and the hand-edited one beside it goes round', () => {
  // (on a short plug, so that the automatic cord does rise: P-0218-2, owner's option A, 2026-10-22)
  const {rack: base, ctx} = shortOwner();
  const hand = {...base.cables[1], id: 'h2', a: {...base.cables[1].a, path: 'p140'}, b: {...base.cables[1].b, path: 'bay4'}, route: [{item: 'i3', via: 'guide-4'}], routeEdited: true};
  const rack = {...base, cables: [base.cables[1], hand]};
  const auto = R.routePath(rack, rack.cables[0], ctx);
  assert.equal(rose(rack, rack.cables[0], ctx), true);
  assert.equal(mm(auto), 479.8);
  const p = R.routePath(rack, hand, ctx);
  assert.equal(rose(rack, hand, ctx), false);
  assert.deepEqual(p.points, R.routePath(rack, hand, asMain(ctx)).points);
});

test('a bundle with a trunk drawn by hand, or a member routed by hand, uses no gap; one the kit routes does', () => {
  // (on a short plug, so that the automatic cord does rise: P-0218-2, owner's option A, 2026-10-22)
  const {rack: base, ctx} = shortOwner();
  const c2 = base.cables[1];
  const more = {...c2, id: 'x0'};
  const bundle = (route, members = [c2, more]) => ({id: 'b1', number: 1, label: 'B', members: members.map(c => ({cable: c.id})), route});
  const withB = (b, cables) => ({...base, cables, bundles: [b]});
  const asAuto = withB(bundle([]), [c2, more]);
  assert.equal(rose(asAuto, asAuto.cables[0], ctx), true);
  // a trunk written by hand through a ring of the tray: no member rises
  const trunked = withB(bundle([{item: 'i3', via: 'guide-3'}]), [c2, more]);
  for (const c of trunked.cables) {
    const p = R.routePath(trunked, c, ctx);
    assert.equal(rose(trunked, c, ctx), false, c.id);
    assert.deepEqual(p.points, R.routePath(trunked, c, asMain(ctx)).points, c.id);
  }
  // one member hand-edited: the bundle goes round the front edge together, the automatic member too
  const mixed = withB(bundle([]), [c2, {...more, route: [{item: 'i3', via: 'guide-3'}], routeEdited: true}]);
  for (const c of mixed.cables) {
    const p = R.routePath(mixed, c, ctx);
    assert.equal(rose(mixed, c, ctx), false, c.id);
    assert.deepEqual(p.points, R.routePath(mixed, c, asMain(ctx)).points, c.id);
  }
});

test('the gap is the router\'s own: no key of the rack file names it', () => {
  // the lay entries a cable can carry name a tray and a face, and nothing else here
  const {rack: base, ctx} = owner();
  const lay = [{item: 'i3', via: 'tray', face: 'top'}];
  const c = {...base.cables[1], lay};
  const rack = {...base, cables: [c]};
  const [g] = S.gapsOf(rack, ctx);
  // the gap is named by the tray it belongs to, which a later value of a `lay` entry could point at
  assert.deepEqual([g.item, g.via], [lay[0].item, lay[0].via]);
  assert.deepEqual(Object.keys(g).sort(), ['away', 'edge', 'item', 'via', 'width', 'x0', 'x1', 'z0', 'z1'].sort());
  // and a cable that carries a `lay` entry routes through the gap as one that does not
  assert.deepEqual(R.routePath(rack, c, ctx).points, R.routePath({...base, cables: [base.cables[1]]}, base.cables[1], ctx).points);
});
