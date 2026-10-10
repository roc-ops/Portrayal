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
  assert.deepEqual(R.PLUG_REACH, {os2: 27.6, om3: 27.6, om4: 27.6, om5: 27.6, cat6: 39.4, cat6a: 39.4, dac: 64.8, aoc: 64.8});
  // the reach of end a, read off routePath: its reach point's distance out
  // of the face, or 0 when it has none
  const r = F.rack(), base = F.ctxOf(r), c1 = r.cables[0];
  const reachOf = (cable, extra = {}) => {
    const [a, q] = R.routePath(r, cable, {...base, ...extra}).points;
    return q.at === 'reach' ? Math.round((q.z - a.z) * 1000) / 1000 : 0;
  };
  assert.equal(reachOf(c1), 27.6);
  assert.equal(reachOf({...c1, media: 'cat6a'}), 39.4);
  assert.equal(reachOf({...c1, media: 'dac'}), 64.8);
  // no media, or one named like something every object has: the copper figure
  for (const media of [undefined, 'constructor', '__proto__', 'nope']) assert.equal(reachOf({...c1, media}), 39.4, String(media));
  // the page's own figure wins, 0 included; one it cannot give falls back
  assert.equal(reachOf(c1, {plugReachOf: () => 47.6}), 47.6);
  assert.equal(reachOf(c1, {plugReachOf: () => 0}), 0);
  for (const bad of [null, undefined, -1, NaN, Infinity, '30'])
    assert.equal(reachOf(c1, {plugReachOf: () => bad}), 27.6, String(bad));
  assert.equal(reachOf(c1, {plugReachOf: () => { throw new Error('no face'); }}), 27.6);
  // it is asked per end, with the cable
  const asked = [];
  R.routePath(r, c1, {...base, plugReachOf: (end, cable) => { asked.push([end.item, cable.id]); return 1; }});
  assert.deepEqual(asked, [['i1', 'c1'], ['i2', 'c1']]);
  // the helpers that compute it are not part of the kit's API
  assert.equal(R.plugReach, undefined);
  assert.equal(R.reachPoint, undefined);
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
  // (and the free spans hang between them, #949 step 3)
  const none = {...ctx, plugReachOf: () => 0};
  assert.deepEqual(R.routePath(r, front, none).points.map(p => p.at).filter(a => a !== 'rest'), ['a', 'lane', 'lane', 'lane', 'b']);
});

// THE END ALLOWANCE (#962): what a path from port face to port face leaves
// out, by media, in metres an end. The plug inside the port and half the
// maker's minus tolerance, worked by hand: LC 25.6 - 12.5 = 13.1 inside, the
// FS fibre cords +x/-0; RJ45 22.48 - 13.0 = 9.48, taken as 9.5, plus half of
// 1 per cent of 5 m; a DAC's heads come with the cord (FS measures L between
// them), so half of +/-5 cm; an AOC's QSFP head 52.4 inside, +x/-0.
test('the end allowance is the plug inside the port and the maker\'s short tolerance, per media', () => {
  assert.deepEqual(R.END_ALLOWANCE, {os2: 0.0131, om3: 0.0131, om4: 0.0131, om5: 0.0131,
    cat6: 0.0095 + 0.025, cat6a: 0.0095 + 0.025, dac: 0.025, aoc: 0.0524});
  const r = F.rack(), ctx = F.ctxOf(r), c1 = r.cables[0];
  const per = media => {
    const p = R.routePath(r, {...c1, media}, ctx);
    return [p.allowance, Math.round((R.pathLength(p).measured - len(p.points) / 1000) * 1e6) / 1e6];
  };
  assert.deepEqual(per('om4'), [0.0131, 0.0262]);
  assert.deepEqual(per('cat6'), [0.0345, 0.069]);
  assert.deepEqual(per('dac'), [0.025, 0.05]);
  assert.deepEqual(per('aoc'), [0.0524, 0.1048]);
  // no media, or one named like something every object has: the copper figure
  for (const media of [undefined, 'constructor', '__proto__', 'nope']) assert.equal(per(media)[0], 0.0345, String(media));
  // a path built by hand, with no allowance, takes the same
  const p = R.routePath(r, c1, ctx);
  assert.ok(Math.abs(R.pathLength({points: p.points}).measured - (len(p.points) / 1000 + 0.069)) < 1e-12);
});

test('the reach is in the length once, as path, and the end allowance is the OM4 cord\'s', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  // how much the reach adds is the taut path's: a cord too stiff to sag
  // (bendOf: no span can take the bend), so a span's hang, which the reach
  // also moves (#949 step 3), is not counted as the plug's
  const rigid = {...ctx, bendOf: () => 1e12}, zero = {...rigid, plugReachOf: () => 0};
  for (const c of r.cables) {
    const p = R.routePath(r, c, ctx);
    // the measured length is the kit's points and the end allowance, no
    // more: 13.1 mm an end for an OM4 cord, the LC plug inside its port
    // (#962; 0.15 m an end before)
    assert.equal(p.allowance, 0.0131, c.id);
    assert.ok(Math.abs(R.pathLength(p).measured - (len(p.points) / 1000 + 2 * 0.0131)) < 1e-12, c.id);
    // the port to its reach point: the plug's 27.6, straight out
    const [a, ra] = p.points, [rb, b] = p.points.slice(-2);
    assert.deepEqual([ra.at, ra.end, ra.z - a.z, ra.x - a.x, ra.y - a.y], ['reach', 'a', 27.6, 0, 0], c.id);
    assert.deepEqual([rb.at, rb.end, rb.z - b.z, rb.x - b.x, rb.y - b.y], ['reach', 'b', 27.6, 0, 0], c.id);
    // it grows by at most the two plugs, and by more than nothing (1.8 to
    // 20.1 mm here since the cords rest on the ring sills, #949 step 3; 11 to
    // 28 before)
    const grew = R.routedLength(r, c, rigid).measured - R.routedLength(r, c, zero).measured;
    assert.ok(grew > 0.001 && grew <= 2 * 0.0276 + 1e-12, `${c.id} grew ${grew}`);
  }
});

// The lower leaf's cords with an optic in each leaf port: out of the plug,
// 47.6 in front of the leaf, a straight rise to the ring would cross the
// tray floor, so each goes up in front of its front edge and back in. Their
// lengths, the path plus the end allowance at each end, in mm; from the port faces they were
// 494.0-495.8 (c9-c12) and 463.1-478.4 (c13-c16), all 0.5 m stock. Since the
// cords rest (#949 step 3: on each ring's sill, at the side of its opening
// nearer the rail) they were 664.3-670.0 and 629.4-648.9; and since the ring
// is lower and further out, the default plug goes round the edge as well, to
// the same detour points, so the optic's longer plug only moves the reach
// point along the leg it would run anyway and the lengths are the default's.
// Since each ring is solid (#968) the detour ends straight in front of the
// ring's approach point, 6.5 mm past its band, not its face, and the cord
// comes in to it from there: 1.9 to 6.1 mm longer (662.3, 659.7, 662.3,
// 661, 627, 632.5, 617.6 and 620.8 before).
// THE END ALLOWANCE (#962): 13.1 mm an end for an OM4 cord, not 150, so each
// is 273.8 mm shorter (664.3, 663.1, 665, 665.8, 631.9, 638.6, 620.7 and
// 626.4 before), and each fits a 0.5 m cord (1 m before).
const OVER_THE_EDGE = {c9: 390.5, c10: 389.3, c11: 391.2, c12: 392, c13: 358.1, c14: 364.8, c15: 346.9, c16: 352.6};

test('a cord that must clear its plug goes round the tray\'s front edge, and is measured that way', () => {
  const r = F.rack(), ctx = optics(F.ctxOf(r));
  const got = Object.fromEntries(r.cables.map(c => [c.id, R.routePath(r, c, ctx)]));
  const lower = Object.keys(OVER_THE_EDGE);
  assert.deepEqual(Object.fromEntries(lower.map(id => [id, mm(R.pathLength(got[id]))])), OVER_THE_EDGE);
  assert.ok(lower.every(id => R.pathLength(got[id]).value === 0.5));
  for (const id of lower) {
    const p = got[id];
    // one detour, from the leaf end's reach point to its first ring, over
    // the strip's front edge (110 out), clear by the cord's radius and CLEAR
    assert.equal(p.detours.length, 1, id);
    const ring = ['c9', 'c10', 'c11', 'c12'].includes(id) ? 'guide-3' : 'guide-4';
    assert.deepEqual(p.detours[0].between, [{end: 'a'}, {item: 'i4', via: ring}], id);
    assert.ok(p.detours[0].points.every(q => Math.abs(q.z - (110 + 1.5 + S.CLEAR)) < 1e-9), id);
    assert.deepEqual(p.crossings, [], id);
    // the same leg from the leaf's face, not its plug, goes round too: a
    // straight rise from the face to a ring on its sill, 73.7 out, meets the
    // floor's back edge at 48.8 below the plate (before the cords rested on
    // the sill it did not, and only the plug put it over the floor)
    const face = R.routePath(r, r.cables.find(c => c.id === id), {...ctx, plugReachOf: () => 0});
    assert.equal(face.detours.length, 1, id);
    assert.deepEqual(face.crossings, [], id);
  }
  // the upper leaf's cords drop onto the tray from above; since each ring is
  // solid (#968), those whose ring stands past their port along the run go
  // over it first, and the rest need no detour
  for (const id of ['c3', 'c4', 'c8']) assert.deepEqual(got[id].detours, [], id);
  for (const id of ['c1', 'c2', 'c5', 'c6', 'c7']) assert.equal(got[id].detours.length, 1, id);
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
// where the kit turns at its face). This checks the kit's own consistency:
// the path a drawing would build from the kit's points and rules. It does
// not run or check the site's drawing, which still starts its bend further
// out (the site follow-up of section 1.5).
// SINCE THE CORDS REST (#949 step 3) the comparison is of the taut path, a
// cord too stiff to sag: a drawing that hangs its spans by the kit's points
// follows them, which the first check holds. SINCE EACH RING IS SOLID (#968)
// a drawing takes a ring the kit rests the cord in by its two approach
// points, straight through the opening between them, where it took the
// ring's centre: a leg to the centre of a solid ring meets its legs, and
// going round them is not the way through the opening.
test('the drawn path and the measured length agree within a few mm', () => {
  const r = F.rack();
  for (const [name, loose] of [['default', F.ctxOf(r)], ['optics', optics(F.ctxOf(r))]]) {
    // the kit's points, sag and all: nothing left for a drawing to go round
    for (const c of r.cables) {
      const p = R.routePath(r, c, loose), solids = S.solidsOf(r, loose);
      for (let k = 1; k < p.points.length; k++)
        assert.deepEqual(S.detour(p.points[k - 1], p.points[k], solids, {diameter: 3}), [], `${name} ${c.id} hung leg ${k}`);
    }
    const ctx = {...loose, bendOf: () => 1e12};
    const solids = S.solidsOf(r, ctx);
    let detoured = 0;
    for (const c of r.cables) {
      const p = R.routePath(r, c, ctx);
      // the kit's points: nothing left for a drawing to go round
      for (let k = 1; k < p.points.length; k++)
        assert.deepEqual(S.detour(p.points[k - 1], p.points[k], solids, {diameter: 3}), [], `${name} ${c.id} leg ${k}`);
      // built the drawing's way: each ring the cord rests in by its two
      // approach points, any other waypoint by its centre, each ring passed
      // by its mark
      const A = p.points[1], B = p.points.at(-2);
      const approach = p.points.filter(q => q.at === 'approach');
      const marks = R.ringMarks(r, c, ctx);
      const legs = [A], mk = [null];
      R.resolveRoute(r, c, ctx).waypoints.forEach((w, i) => {
        const ap = approach.filter(q => !w.lane && q.item === w.item && q.via === w.via);
        if (ap.length === 2) { legs.push(...ap); mk.push(null, null); } else { legs.push(R.pointOf(r, w, ctx)); mk.push(marks[i]); }
      });
      legs.push(B); mk.push(null);
      const pts = [], pm = [];
      legs.forEach((q, k) => {
        const round = k ? S.detour(legs[k - 1], q, solids, {diameter: 3}) : [];
        if (round.length) detoured++;
        for (const d of round) { pts.push(d); pm.push(null); }
        pts.push(q);
        pm.push(mk[k]);
      });
      const drawn = len(throughRings(pts, pm).points) + Math.abs(A.z - p.points[0].z) + Math.abs(B.z - p.points.at(-1).z);
      const measured = (R.pathLength(p).measured - 2 * p.allowance) * 1000;
      assert.ok(Math.abs(drawn - measured) <= 4, `${name} ${c.id}: drawn ${drawn}, measured ${measured}`);
    }
    // the lower cords go round the edge, in the drawing too: one leg of each
    // (before the cords rested on the sill, only with the optics' longer plug);
    // and since each ring is solid (#968) the five upper cords whose ring is
    // past their port go over it
    assert.equal(detoured, 8 + 5, name);
  }
});
