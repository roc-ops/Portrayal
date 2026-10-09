// The plug's reach (#960, docs/cable-lay-design.md section 1.5): a route's
// first and last legs start where the cable leaves its plug, the port face
// plus the plug's depth out of it, so a cable that must clear its plug before
// it turns is measured that way, round a tray's front edge included. Every
// length here was measured on these fixtures and is asserted exactly.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as R from '../../../kit/rack/route.js';
import * as S from '../../../kit/rack/solids.js';
import * as M from '../../../kit/rack/model.js';
import {throughRings} from '../../../kit/rack/route-path.js';
import * as F from './route-direct-fixture.mjs';

const mm = l => Math.round(l.measured * 10000) / 10;
const len = pts => pts.reduce((s, q, k) => (k ? s + Math.hypot(q.x - pts[k - 1].x, q.y - pts[k - 1].y, q.z - pts[k - 1].z) : 0), 0);
// The owner's rack with a QSFP-LC optic in each leaf port: the cord's LC plug
// seats in the optic, which stands 20.0 out of its cage (generic/qsfp-lc@2),
// so its boot ends 47.6 out of the leaf's face; the panel ends take the
// default. What a page passes as `plugReachOf` from the seated plug.
const QSFP_LC = 20.0 + R.PLUG_REACH.om4;
const optics = ctx => ({...ctx, plugReachOf: e => (e.item === 'i2' ? null : QSFP_LC)});

test('the defaults are the library\'s plug and boot, per media', () => {
  assert.deepEqual(R.PLUG_REACH, {os2: 27.6, om3: 27.6, om4: 27.6, om5: 27.6, cat6: 39.4, cat6a: 39.4, dac: 68.7, aoc: 68.7});
  const e = {item: 'i1', path: 'p', view: 'front'};
  assert.equal(R.plugReach({media: 'om4'}, e, {}), 27.6);
  assert.equal(R.plugReach({media: 'cat6a'}, e, {}), 39.4);
  assert.equal(R.plugReach({media: 'dac'}, e, null), 68.7);
  // no media, or one named like something every object has: the copper figure
  for (const media of [undefined, 'constructor', '__proto__', 'nope']) assert.equal(R.plugReach({media}, e, {}), 39.4, String(media));
  // the page's own figure wins, 0 included; one it cannot give falls back
  assert.equal(R.plugReach({media: 'om4'}, e, {plugReachOf: () => 47.6}), 47.6);
  assert.equal(R.plugReach({media: 'om4'}, e, {plugReachOf: () => 0}), 0);
  for (const bad of [null, undefined, -1, NaN, Infinity, '30'])
    assert.equal(R.plugReach({media: 'om4'}, e, {plugReachOf: () => bad}), 27.6, String(bad));
  assert.equal(R.plugReach({media: 'om4'}, e, {plugReachOf: () => { throw new Error('no face'); }}), 27.6);
  // it is asked per end, with the cable
  const asked = [];
  R.plugReach({id: 'c', media: 'om4'}, e, {plugReachOf: (end, cable) => { asked.push([end.item, cable.id]); return 1; }});
  assert.deepEqual(asked, [['i1', 'c']]);
});

test('the reach point is out of the face the port is seen from: +z at the front, -z at the rear', () => {
  const SIZES = {sw: {ru: 1, d: 300}};
  const ctx = {chassisOf: ref => SIZES[ref] || null, guidesOf: () => [], portX: () => -100, portY: () => null};
  let r = M.withItem(M.newRack(), {ref: 'sw', cfg: 'x', ru: 10, label: 'f'}).rack;
  r = M.withItem(r, {ref: 'sw', cfg: 'x', ru: 20, label: 'b', face: 'rear'}).rack;
  const at = (rack, c) => R.routePath(rack, c, ctx).points.filter(p => p.at === 'a' || p.at === 'b' || p.at === 'reach')
    .map(p => [p.at, p.end ?? null, p.z + 0]);   // + 0: a two-post's rear plane is -0
  const front = {id: 'c1', media: 'cat6', a: {item: 'i1', path: 'p', view: 'front'}, b: {item: 'i2', path: 'p', view: 'front'}, route: []};
  // a: the front switch, on the front rail plane; b: the rear one, at -740
  assert.deepEqual(at(r, front), [['a', null, 0], ['reach', 'a', 39.4], ['reach', 'b', -740 - 39.4], ['b', null, -740]]);
  // a port on a device's far panel is seen from the other face: the front
  // switch's rear panel (300 back) looks to the rear, the rear switch's rear
  // panel (its far one, 300 in front of the rear rails) looks to the front
  const far = {...front, a: {...front.a, view: 'rear'}, b: {...front.b, view: 'rear'}};
  assert.deepEqual(at(r, far), [['a', null, -300], ['reach', 'a', -300 - 39.4], ['reach', 'b', -440 + 39.4], ['b', null, -440]]);
  // on a two-post both rail planes are z 0: the rear reach is still behind it
  let t = M.withItem(M.newRack({kind: 'two-post'}), {ref: 'sw', cfg: 'x', ru: 10, label: 'f'}).rack;
  t = M.withItem(t, {ref: 'sw', cfg: 'x', ru: 20, label: 'b', face: 'rear'}).rack;
  assert.deepEqual(at(t, front), [['a', null, 0], ['reach', 'a', 39.4], ['reach', 'b', -39.4], ['b', null, 0]]);
  // a plug of no reach adds no point: the path is as it was from the faces
  const none = {...ctx, plugReachOf: () => 0};
  assert.deepEqual(R.routePath(r, front, none).points.map(p => p.at), ['a', 'lane', 'lane', 'lane', 'b']);
});

test('the reach is in the length once, as path, and the end allowance is unchanged', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  const zero = {...ctx, plugReachOf: () => 0};
  for (const c of r.cables) {
    const p = R.routePath(r, c, ctx);
    // the measured length is the kit's points and 0.15 m an end, no more
    assert.ok(Math.abs(R.pathLength(p).measured - (len(p.points) / 1000 + 2 * R.END_ALLOWANCE_M)) < 1e-12, c.id);
    // the port to its reach point: the plug's 27.6, straight out
    const [a, ra] = p.points, [rb, b] = p.points.slice(-2);
    assert.deepEqual([ra.at, ra.end, ra.z - a.z, ra.x - a.x, ra.y - a.y], ['reach', 'a', 27.6, 0, 0], c.id);
    assert.deepEqual([rb.at, rb.end, rb.z - b.z, rb.x - b.x, rb.y - b.y], ['reach', 'b', 27.6, 0, 0], c.id);
    // it grows by at most the two plugs, and by more than nothing
    const grew = R.routedLength(r, c, ctx).measured - R.routedLength(r, c, zero).measured;
    assert.ok(grew > 0.01 && grew <= 2 * 0.0276 + 1e-12, `${c.id} grew ${grew}`);
  }
});

// The lower leaf's cords with an optic in each leaf port: out of the plug,
// 47.6 in front of the leaf, a straight rise to the ring would cross the
// tray floor, so each goes up in front of its front edge and back in. Their
// lengths, the path plus 0.15 m an end, in mm; from the port faces they were
// 494.0-495.8 (c9-c12) and 463.1-478.4 (c13-c16), all 0.5 m stock.
const OVER_THE_EDGE = {c9: 670.0, c10: 667.3, c11: 665.4, c12: 664.3, c13: 643.9, c14: 648.9, c15: 629.4, c16: 632.5};

test('a cord that must clear its plug goes round the tray\'s front edge, and is measured that way', () => {
  const r = F.rack(), ctx = optics(F.ctxOf(r));
  const got = Object.fromEntries(r.cables.map(c => [c.id, R.routePath(r, c, ctx)]));
  const lower = Object.keys(OVER_THE_EDGE);
  assert.deepEqual(Object.fromEntries(lower.map(id => [id, mm(R.pathLength(got[id]))])), OVER_THE_EDGE);
  assert.ok(lower.every(id => R.pathLength(got[id]).value === 1));
  for (const id of lower) {
    const p = got[id];
    // one detour, from the leaf end's reach point to its first ring, over
    // the strip's front edge (110 out), clear by the cord's radius and CLEAR
    assert.equal(p.detours.length, 1, id);
    const ring = ['c9', 'c10', 'c11', 'c12'].includes(id) ? 'guide-3' : 'guide-4';
    assert.deepEqual(p.detours[0].between, [{end: 'a'}, {item: 'i4', via: ring}], id);
    assert.ok(p.detours[0].points.every(q => Math.abs(q.z - (110 + 1.5 + S.CLEAR)) < 1e-9), id);
    assert.deepEqual(p.crossings, [], id);
    // the same leg from the leaf's face, not its plug, needs no detour: the
    // plug is what puts it over the floor
    const face = R.routePath(r, r.cables.find(c => c.id === id), {...ctx, plugReachOf: () => 0});
    assert.deepEqual(face.detours, [], id);
  }
  // the upper leaf's cords drop onto the tray from above and need none
  for (const id of ['c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8']) assert.deepEqual(got[id].detours, [], id);
  assert.deepEqual(R.bodyFindings(r, ctx), []);
  assert.deepEqual(R.ringFindings(r, ctx), []);
});

// THE DRAWING AND THE MEASURE AGREE. A drawing that starts each tube at the
// kit's reach point (the site's clearLegs: each drawn leg taken round the same
// bodies by solids.js detour, with the drawn tube's width) finds nothing to
// add to the kit's own points, and one built the drawing's way - from the
// reach points through the waypoints' centres, each leg taken round the
// bodies, then each ring passed by its mark - is as long as the kit measures,
// the plugs added, within a few mm (the drawing turns at a ring's centre
// where the kit turns at its face).
test('the drawn path and the measured length agree within a few mm', () => {
  const r = F.rack();
  for (const [name, ctx] of [['default', F.ctxOf(r)], ['optics', optics(F.ctxOf(r))]]) {
    const solids = S.solidsOf(r, ctx);
    let detoured = 0;
    for (const c of r.cables) {
      const p = R.routePath(r, c, ctx);
      // the kit's points: nothing left for a drawing to go round
      for (let k = 1; k < p.points.length; k++)
        assert.deepEqual(S.detour(p.points[k - 1], p.points[k], solids, {diameter: 3}), [], `${name} ${c.id} leg ${k}`);
      // built the drawing's way
      const A = p.points[1], B = p.points.at(-2);
      const centres = R.resolveRoute(r, c, ctx).waypoints.map(w => R.pointOf(r, w, ctx));
      const marks = R.ringMarks(r, c, ctx);
      const legs = [A, ...centres, B], pts = [], mk = [];
      legs.forEach((q, k) => {
        const round = k ? S.detour(legs[k - 1], q, solids, {diameter: 3}) : [];
        if (round.length) detoured++;
        for (const d of round) { pts.push(d); mk.push(null); }
        pts.push(q);
        mk.push(k === 0 || k === legs.length - 1 ? null : marks[k - 1]);
      });
      const drawn = len(throughRings(pts, mk).points) + (A.z - p.points[0].z) + (B.z - p.points.at(-1).z);
      const measured = (R.pathLength(p).measured - 2 * R.END_ALLOWANCE_M) * 1000;
      assert.ok(Math.abs(drawn - measured) <= 4, `${name} ${c.id}: drawn ${drawn}, measured ${measured}`);
    }
    // the optics case does go round the edge, in the drawing too: one leg of each lower cord
    assert.equal(detoured, name === 'optics' ? 8 : 0, name);
  }
});
