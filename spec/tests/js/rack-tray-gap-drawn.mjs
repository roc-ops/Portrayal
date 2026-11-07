// A RISE THROUGH A TRAY'S GAP, AS THE PAGE DRAWS IT (P-0218, after #1185). The
// site's cable-lay demo rack (spec/tests/fixtures/cable-lay/, copied from
// portrayal-site tests/rack/fixtures/cable-lay-rack.json at a6421f79, with the
// context the Rack Builder gives it) routes leaf-B's cords c9 to c12 up through
// the gap behind the FHD-CMP5DR's strip since #1185. The tube leaves its plug
// straight and turns onto the rise with one arc of its bend radius that starts
// at the plug's reach point (drawn-cord.mjs); from 32.5 mm out of the rail, with
// the strip's front 48.8 out and the cord's radius and CLEAR to keep from it,
// there are 9.8 mm to turn up in, and the arc is 25. So the drawn bends are
// 6.1 to 12.5 mm and the centre line runs up through the plate, and the kit,
// which takes the reach point as an ordinary corner with the whole plug as its
// leg, reports no bend.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as R from '../../../kit/rack/route.js';
import * as S from '../../../kit/rack/solids.js';
import * as L from './cable-lay-fixture.mjs';
import {drawn, inside} from './drawn-cord.mjs';

const r1 = v => Math.round(v * 10) / 10;
const NEED = 25, RADIUS = 1.5;
const solids = S.solidsOf(L.RACK, L.ctx), bodies = solids.map(s => s.box);
const floors = solids.filter(s => /\/floor$/.test(s.part));
// a face looks +z (every device here is on the front rails), so a plug leaves along +z
const OUT = {a: {x: 0, y: 0, z: 1}, b: {x: 0, y: 0, z: 1}};
const laid = Object.fromEntries(L.RACK.cables.map(c => {
  const path = R.routePath(L.RACK, c, L.ctx);
  return [c.id, {path, drawn: drawn(path, NEED, bodies, OUT),
    rose: path.detours.some(d => d.points.every(q => q.z > 0 && q.z < 48.8)),
    found: R.bendFindingsOf(L.RACK, c, L.ctx, id => id, path)}];
}));

test('the rack is the site\'s, and c9 to c12 no longer rise through the gap: round the front edge, onto 1 m stock', () => {
  assert.equal(L.RACK.cables.length, 16);
  assert.equal(S.gapsOf(L.RACK, L.ctx).length, 1);
  assert.equal(floors.length, 3);
  // (the gap is the 48.8 mm behind the strip, and the plate 1.5 thick)
  assert.deepEqual(floors.map(f => r1(f.box.y1 - f.box.y0)), [1.5, 1.5, 1.5]);
  // CHANGED from "c9 to c12 rise through the gap on main (488.6 to 501.5 mm, 0.5 m stock)":
  // drawable geometry, owner's option A, 2026-10-22. The plug reaches 32.5 mm and the rise
  // would stand at 42.3 from the rail, 9.8 mm for a bend of 25: not drawable, so the route
  // goes round the front edge, longer (610.9, 611.3, 615.8 and 623.3 mm) and onto 1 m stock.
  assert.ok(Object.values(laid).every(x => !x.rose), 'no cord rises through the gap');
  const lens = ['c9', 'c10', 'c11', 'c12'].map(id => r1(R.pathLength(laid[id].path).measured * 1000));
  assert.deepEqual(lens, [610.9, 611.3, 615.8, 623.3]);
  for (const k of [8, 9, 10, 11]) assert.equal(R.routedLength(L.RACK, L.RACK.cables[k], L.ctx).value, 1);
});

test('a cord whose plug leaves the room for the bend still rises through the gap, clear of the plate, the rise a bend radius beyond its plug', () => {
  // (the same rack, the plugs 10 mm out: the rise stands 32.3 mm beyond the reach point, the 25 and more)
  const ctx = {...L.ctx, plugReachOf: () => 10};
  const rising = L.RACK.cables.map(c => {
    const path = R.routePath(L.RACK, c, ctx);
    return {id: c.id, path, drawn: drawn(path, NEED, bodies, OUT),
      rose: path.detours.some(d => d.points.every(q => q.z > 0 && q.z < 48.8))};
  }).filter(x => x.rose);
  assert.ok(rising.length > 0, 'a cord rises');
  for (const x of rising) {
    // the rise stands the bend radius (25) or more beyond the plug's reach point (10): the rule
    // taken (solids.js gapWays). (How tight the slanted rise's own corners are drawn, where two
    // legs share, is the kit's bend check's as before: not asserted here.)
    const rise = x.path.detours.find(d => d.points.every(q => q.z > 0 && q.z < 48.8));
    assert.ok(rise.points.every(q => q.z - 10 >= NEED - 1e-6), `${x.id}: ${JSON.stringify(rise.points)}`);
    assert.ok(!x.drawn.curve.some(q => floors.some(f => inside(q, f.box, RADIUS))), x.id);
  }
});

test('no cord\'s centre line, drawn, enters a tray\'s floor plate (its thickness and the cord\'s radius)', () => {
  const into = [];
  for (const [id, x] of Object.entries(laid)) {
    const hit = x.drawn.curve.filter(q => floors.some(f => inside(q, f.box, RADIUS)));
    if (hit.length) into.push(`${id}: ${hit.length} samples`);
  }
  assert.deepEqual(into, []);
});

test('every drawn bend of a cord that rises through the gap is the cord\'s bend radius, or the kit reports a bend for it', () => {
  const rising = Object.entries(laid).filter(([, x]) => x.rose);
  assert.ok(rising.length > 0 || Object.values(laid).every(x => !x.rose), 'a cord that rose was found, or none does');
  const bad = [];
  for (const [id, x] of rising) {
    const least = Math.min(...x.drawn.corners.map(c => c.drawn_mm));
    if (least < NEED - 0.05 && x.found.length === 0) bad.push(`${id}: drawn to ${least} mm, no bend reported`);
  }
  assert.deepEqual(bad, []);
});

test('the kit\'s bend check sees a bend the cord is drawn short of: none is drawn short in silence', () => {
  const silent = [];
  for (const [id, x] of Object.entries(laid)) {
    if (!x.rose) continue;
    const short = x.drawn.corners.filter(c => !c.full);
    if (short.length && x.path.bends.length === 0) silent.push(`${id}: ${short.map(c => c.drawn_mm).join(', ')} mm`);
  }
  assert.deepEqual(silent, []);
});
