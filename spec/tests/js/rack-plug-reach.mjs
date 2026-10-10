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
// THE DRESSING ALLOWANCE (temporary, until #949 step 4 holds slack in a
// tray): 0.1 m an end on top of the table, for every media, by decision and
// with no maker's source. It is not in END_ALLOWANCE; endAllowance(cable)
// and a path's `allowance` carry the two together, what a length adds an end.
const DRESSING = 0.1;
test('the end allowance is the plug inside the port and the maker\'s short tolerance, per media, and 0.1 m of dressing for now', () => {
  assert.deepEqual(R.END_ALLOWANCE, {os2: 0.0131, om3: 0.0131, om4: 0.0131, om5: 0.0131,
    cat6: 0.0095 + 0.025, cat6a: 0.0095 + 0.025, dac: 0.025, aoc: 0.0524});
  const r = F.rack(), ctx = F.ctxOf(r), c1 = r.cables[0];
  const per = media => {
    const p = R.routePath(r, {...c1, media}, ctx);
    return [p.allowance, Math.round((R.pathLength(p).measured - len(p.points) / 1000) * 1e6) / 1e6];
  };
  assert.deepEqual(per('om4'), [0.1131, 0.2262]);
  assert.deepEqual(per('cat6'), [0.1345, 0.269]);
  assert.deepEqual(per('dac'), [0.125, 0.25]);
  assert.deepEqual(per('aoc'), [0.1524, 0.3048]);
  // each is its table figure and the dressing allowance, the same for all
  for (const [media, table] of Object.entries(R.END_ALLOWANCE)) {
    assert.ok(Math.abs(R.endAllowance({media}) - (table + DRESSING)) < 1e-12, media);
    assert.ok(Math.abs(per(media)[0] - R.endAllowance({media})) < 1e-12, media);
  }
  // the table itself carries none of it: no figure reaches 0.1 m
  assert.ok(Object.values(R.END_ALLOWANCE).every(v => v < DRESSING));
  // no media, or one named like something every object has: the copper figure
  for (const media of [undefined, 'constructor', '__proto__', 'nope']) assert.equal(per(media)[0], 0.1345, String(media));
  assert.equal(R.endAllowance(null), 0.1345);
  // a path built by hand, with no allowance, takes the same
  const p = R.routePath(r, c1, ctx);
  assert.ok(Math.abs(R.pathLength({points: p.points}).measured - (len(p.points) / 1000 + 0.269)) < 1e-12);
});

test('the reach is in the length once, as path, and the end allowance is the OM4 cord\'s', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  for (const c of r.cables) {
    const p = R.routePath(r, c, ctx);
    // the measured length is the kit's points and the end allowance, no
    // more: 113.1 mm an end for an OM4 cord, the 13.1 of LC plug inside its
    // port and the temporary 100 of dressing (#962; 0.15 m an end before)
    assert.equal(p.allowance, 0.1131, c.id);
    assert.ok(Math.abs(R.pathLength(p).measured - (len(p.points) / 1000 + 2 * 0.1131)) < 1e-12, c.id);
    // the port to its reach point: the plug's 27.6, straight out
    const [a, ra] = p.points, [rb, b] = p.points.slice(-2);
    assert.deepEqual([ra.at, ra.end, ra.z - a.z, ra.x - a.x, ra.y - a.y], ['reach', 'a', 27.6, 0, 0], c.id);
    assert.deepEqual([rb.at, rb.end, rb.z - b.z, rb.x - b.x, rb.y - b.y], ['reach', 'b', 27.6, 0, 0], c.id);
    // and the reach is nowhere else in the path: each plug is one leg of it,
    // and one point (a cord that runs on straight out of its plug for a
    // turn's room, #973, adds a lead point after it, which this rack's
    // default plugs do not need at the leaf)
    assert.equal(p.points.filter(q => q.at === 'reach').length, 2, c.id);
  }
  // Until #973 this test also held each length to grow by no more than the
  // two plugs over the same route measured from the port faces. That no
  // longer compares like with like: where a cord turns is now placed for its
  // bend radius from where its plug ends (an approach point two radii past
  // the reach point along the run, a lead point square to it), so a plug of
  // no reach is a different route, 1 mm shorter to 136 mm longer here.
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
// THE END ALLOWANCE (#962): 113.1 mm an end for an OM4 cord (13.1 of plug in
// the port and the temporary 100 of dressing), not 150, so each is 73.8 mm
// shorter (664.3, 663.1, 665, 665.8, 631.9, 638.6, 620.7 and 626.4 before),
// and each is still a 1 m cord.
// ROOM FOR THE BENDS (#973): the detour's plane stands two bend radii (50
// mm) in front of the ring's line, 123.7 out, where it stood the cord's
// radius and CLEAR past the tray's edge, 116.5 out: the leg back in to the
// approach point is shared by two right angles, and 42.8 mm left each 21.4
// of the 25 it needs. The approach point stands the bend radius from the
// band; not for c13 to c16, whose leaf port stands 8 to 34 mm from there
// along the run: the leg between the detour's two turns (up 27 or 45 mm in
// front of the edge) is as long as the port and the approach point are
// apart, and needs 50, so the point stands 42.3 or 21.5 mm to the side of
// the port (for c16 the side nearer the ring, 12 mm from its band). Each
// cord is 20.6 to 101.3 mm longer (590.5, 589.3, 591.2, 592, 558.1, 564.8,
// 546.9 and 552.6 before), and still a 1 m cord.
const OVER_THE_EDGE = {c9: 611.1, c10: 613.2, c11: 616.1, c12: 623.4, c13: 645.7, c14: 617.4, c15: 648.2, c16: 575.8};

test('a cord that must clear its plug goes round the tray\'s front edge, and is measured that way', () => {
  const r = F.rack(), ctx = optics(F.ctxOf(r));
  const got = Object.fromEntries(r.cables.map(c => [c.id, R.routePath(r, c, ctx)]));
  const lower = Object.keys(OVER_THE_EDGE);
  assert.deepEqual(Object.fromEntries(lower.map(id => [id, mm(R.pathLength(got[id]))])), OVER_THE_EDGE);
  assert.ok(lower.every(id => R.pathLength(got[id]).value === 1));
  for (const id of lower) {
    const p = got[id];
    // one detour, from the leaf end's reach point to its first ring, over
    // the strip's front edge (110 out): clear of it by more than the cord's
    // radius and CLEAR, two bend radii in front of the ring's line (73.7 out)
    assert.equal(p.detours.length, 1, id);
    const ring = ['c9', 'c10', 'c11', 'c12'].includes(id) ? 'guide-3' : 'guide-4';
    assert.deepEqual(p.detours[0].between, [{end: 'a'}, {item: 'i4', via: ring}], id);
    assert.ok(p.detours[0].points.every(q => Math.abs(q.z - (73.7 + 2 * 25)) < 1e-9), id);
    assert.ok(73.7 + 2 * 25 > 110 + 1.5 + S.CLEAR);
    assert.deepEqual(p.crossings, [], id);
    assert.deepEqual(p.bends, [], id);
    // the same leg from the leaf's face, not its plug, goes round too: a
    // straight rise from the face to a ring on its sill, 73.7 out, meets the
    // floor's back edge at 48.8 below the plate (before the cords rested on
    // the sill it did not, and only the plug put it over the floor)
    const face = R.routePath(r, r.cables.find(c => c.id === id), {...ctx, plugReachOf: () => 0});
    assert.equal(face.detours.length, 1, id);
    assert.deepEqual(face.crossings, [], id);
  }
  // the upper leaf's cords drop onto the tray from above. Since each ring is
  // solid (#968), those whose ring stands past their port along the run went
  // over it by a detour; since #973 the approach point stands clear of the
  // ring, and each of them (and c4, whose longer plug here ends beside the
  // approach point) is led square to it instead: along the run, level with
  // its plug's end, to a lead point beside the approach point, then down
  for (const id of ['c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7']) assert.deepEqual(got[id].detours, [], id);
  const led = id => got[id].points.filter(q => q.at === 'lead').map(q => [q.item, q.via]);
  for (const id of ['c1', 'c2', 'c4', 'c5', 'c6', 'c7']) assert.deepEqual(led(id), [['i4', 'guide-4']], id);
  assert.deepEqual(led('c3'), []);
  // c8 leaves ring 5 and comes straight back to a panel port 13.4 mm short
  // of it: round the front of the tray, and straight in to its plug
  assert.deepEqual(got.c8.detours.map(d => d.between), [[{item: 'i4', via: 'guide-5'}, {end: 'b'}]]);
  assert.deepEqual(got.c8.points.filter(q => q.at === 'lead').map(q => q.end), ['b']);
  assert.deepEqual(R.bodyFindings(r, ctx), []);
  assert.deepEqual(R.ringFindings(r, ctx), []);
  assert.deepEqual(R.bendFindings(r, ctx), []);
});

// THE DRAWING AND THE MEASURE AGREE. A drawing that draws the kit's own
// points (as the site does: each tube through routePath's points) finds
// nothing to add to them: taking each leg round the bodies again, with the
// drawn tube's width, adds no point. And the path is the kit's stops and its
// own rule, nothing a drawing cannot follow: between each two points that
// are not a detour's or a hang's, solids.js detour, asked for the room the
// kit asks (twice the bend radius), gives exactly the kit's detour points.
// This checks the kit's own consistency; it does not run or check the site's
// drawing.
// UNTIL #973 the second check rebuilt each path from the reach points and
// the rings' approach points alone, and held its length to the measure within
// 4 mm. A path is no longer those points and plain detours: an approach point
// stands where its turn has room, a cord can be led square to it or run on
// out of its plug, and a detour's plane stands out for its two bends, each
// decided by the bend radius. A drawing takes the kit's points for them.
test('the drawn path is the measured one: nothing to go round again, and each detour is the kit\'s rule', () => {
  const r = F.rack();
  for (const [name, ctx] of [['default', F.ctxOf(r)], ['optics', optics(F.ctxOf(r))]]) {
    const solids = S.solidsOf(r, ctx);
    let detoured = 0, legs = 0;
    for (const c of r.cables) {
      const p = R.routePath(r, c, ctx);
      // the kit's points, sag and all: nothing left for a drawing to go round
      for (let k = 1; k < p.points.length; k++)
        assert.deepEqual(S.detour(p.points[k - 1], p.points[k], solids, {diameter: 3}), [], `${name} ${c.id} leg ${k}`);
      // the stops, and the detours the rule gives between them
      const taut = p.points.filter(q => q.at !== 'rest'), stops = taut.filter(q => q.at !== 'detour');
      const built = [stops[0]];
      for (let k = 1; k < stops.length; k++) {
        const round = S.detour(stops[k - 1], stops[k], solids, {diameter: 3, room: 2 * 25});
        if (round.length) detoured++;
        legs++;
        built.push(...round, stops[k]);
      }
      const xyz = pts => pts.map(q => [q.x, q.y, q.z].map(v => Math.round(v * 1000) / 1000));
      assert.deepEqual(xyz(built), xyz(taut), `${name} ${c.id}`);
      assert.equal(p.detours.reduce((n, d) => n + d.points.length, 0), taut.length - stops.length, `${name} ${c.id}`);
    }
    // it looked: the lower leaf's eight go round the tray's front edge, and
    // c8 round its front on the way back to its panel port
    assert.equal(detoured, 8 + 1, name);
    assert.ok(legs > 100, `${name}: ${legs} legs`);
  }
});
