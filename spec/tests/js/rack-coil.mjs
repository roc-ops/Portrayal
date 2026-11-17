// spec/tests/js/rack-coil.mjs
// THE CELLS OF A TRAY AND THE COIL A SPARE MAKES IN ONE (docs/cable-spare-design.md
// sections 3.1 to 3.3 and 5): the cells between a tray's rings, the turn a cell
// takes for a cable, how many turns it holds at a stack, and a coil of a stored
// length with its legs. Geometry only: nothing here changes a path, a need, a
// stock size, an export or a finding.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as R from '../../../kit/rack/route.js';
import * as S from '../../../kit/rack/solids.js';
import * as SL from '../../../kit/rack/slack.js';
import {BEND} from '../../../kit/rack/resting.js';
import * as C from '../../../kit/rack/coil.js';
import * as F from './route-direct-fixture.mjs';

const near = (a, b, what, tol = 0.05) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a}, want ${b}`);
const OM4 = {bend: 25, diameter: 3};
const lacer = () => { const r = F.rack(), ctx = F.ctxOf(r); return {r, ctx, tray: S.traysOf(r, ctx).find(t => t.item === 'i4')}; };
// the cord of the slack tests: laid along the lacer, with its spare stored there
function stored(entry = {item: 'i4', via: 'tray'}) {
  const r = F.rack();
  const c = {...r.cables[0], b: {item: 'i2', path: 'bay-2/module/lc3', view: 'front'}, route: [{item: 'i4', via: 'tray'}], routeEdited: true,
             length: {value: 1, unit: 'm', source: 'routed', need: 0.36}, slack: [entry]};
  const rack = {...r, cables: [c, ...r.cables.slice(1)]};
  return {rack, c, ctx: F.ctxOf(rack)};
}

test('the lacer has six cells between its five rings; they add to the floor, and the two at the ends take no turn', () => {
  const {tray} = lacer(), g = C.cellsOf(tray);
  assert.equal(g.run, 'x');
  assert.deepEqual(g.cells.map(c => Math.round(c.width * 10) / 10), [15, 88.6, 103.6, 103.6, 88.6, 15]);
  near(g.cells.reduce((s, c) => s + c.width, 0) + 5 * 6.8, 448.4, 'cells and bands make the floor');
  near(g.across.depth, 61.2, 'floor depth');
  assert.deepEqual(g.cells.map(c => !!C.turnLimits(g, c, OM4)), [false, true, true, true, true, false]);
});

test('the shortest turn of an OM4 cord is 157.1 mm and the longest a cell takes is 244.7 or 274.7 mm', () => {
  const g = C.cellsOf(lacer().tray);
  const t = i => C.turnLimits(g, g.cells[i], OM4);
  near(t(1).min_mm, 157.1, 'shortest');
  near(t(1).max_mm, 244.7, 'longest in an 88.6 cell');
  near(t(2).max_mm, 274.7, 'longest in a 103.6 cell');
  // the floor holds a turn at 25 mm only from 75.3 to 83.5 from the rail: the lay line (73.7) is inside it
  assert.equal(C.turnLimits(g, g.cells[2], {bend: 25, diameter: 3}).across_mm, 58.2);
});

test('a cable that cannot turn on a 61.2 mm floor has no turn: Cat6A, AOC and power; fibre, DAC and Cat6 do', () => {
  const g = C.cellsOf(lacer().tray), cell = g.cells[2];
  const has = m => !!C.turnLimits(g, cell, {bend: BEND[m], diameter: R.DIAMETERS[m]});
  for (const m of ['om4', 'os2', 'dac', 'cat6']) assert.equal(has(m), true, m);
  for (const m of ['cat6a', 'aoc', 'power']) assert.equal(has(m), false, m);
});

test('stack: three turns high at the fill limit and nine to the full ring opening; twelve turns hold 1.89 to 3.12 m', () => {
  const g = C.cellsOf(lacer().tray);
  assert.equal(C.stackOf(g, OM4), 3);
  assert.equal(C.stackOf(g, OM4, 1), 9);
  const cap = C.capacityOf(g, OM4, 3);
  assert.equal(cap.turns, 12);
  near(cap.min_m, 1.885, 'least stored', 0.002);
  near(cap.max_m, 3.116, 'most stored', 0.002);
  const full = C.capacityOf(g, OM4, 9);
  assert.equal(full.turns, 36);
  near(full.min_m, 5.655, 'least at nine', 0.005);
  near(full.max_m, 9.349, 'most at nine', 0.005);
});

test('a coil is solved to its length: whole turns between the shortest and the longest, and what no whole turn takes is left', () => {
  const g = C.cellsOf(lacer().tray), cell = g.cells[2], lim = C.turnLimits(g, cell, OM4);
  // 3 m of stored cord, less nothing: 19 turns of 157.9 mm ... the fewest layers that fit the cell
  const k = C.solveTurns(lim, 3000);
  assert.equal(k.layers, Math.ceil(3000 / lim.max_mm));
  near(k.layers * k.turn_mm, 3000, 'drawn length', 1e-6);
  assert.ok(k.turn_mm >= lim.min_mm - 1e-9 && k.turn_mm <= lim.max_mm + 1e-9);
  assert.equal(k.left_mm, 0);
  // under one shortest turn: not drawn
  const small = C.solveTurns(lim, 150);
  assert.equal(small.layers, 0);
  assert.equal(small.left_mm, 150);
  // between the longest turn and two shortest ones no whole number of turns fits: one longest turn is drawn, the rest is left
  const gap = C.solveTurns(lim, 290);
  assert.equal(gap.layers, 1);
  near(gap.turn_mm, lim.max_mm, 'longest', 1e-9);
  near(gap.left_mm, 290 - lim.max_mm, 'left', 1e-9);
});

test('spareCoils: a cord with a tray entry gets one coil in the nearest cell; its legs and turns and what is left add to what is stored', () => {
  const {rack, c, ctx} = stored();
  const [k] = SL.spareCoils(rack, c, ctx);
  assert.ok(k, 'a coil');
  assert.equal(k.item, 'i4');
  assert.equal(k.cell, 2, 'the cell nearest the middle of the lacer that takes a turn, the lower index of the two equally near');
  assert.ok(k.layers >= 1);
  near((k.drawn_mm + k.legs_mm + k.left_mm) / 1000, k.metres, 'drawn, legs and left are the stored length', 1e-6);
  assert.equal(k.legs.length, 2);
  // the lay line (73.7) is inside the turn's footprint: the cord and the coil cross in plan, and the coil stands a diameter above it
  assert.equal(k.crosses_lay, true);
  near(k.legs[0][0].z, 73.7, 'a leg leaves the lay line');
  near(k.layers_at[0].y - k.legs[0][0].y, 3, 'first turn one diameter above the through cord', 1e-6);
});

test('spareCoils changes nothing it is given: the path points, the spare and the marks are the same with and without it', () => {
  const {rack, c, ctx} = stored();
  const before = JSON.stringify([R.routePath(rack, c, ctx).points, R.spareOf(rack, c, ctx), SL.spareMarks(rack, c, ctx), SL.slackOf(rack, c, ctx)]);
  SL.spareCoils(rack, c, ctx);
  assert.equal(JSON.stringify([R.routePath(rack, c, ctx).points, R.spareOf(rack, c, ctx), SL.spareMarks(rack, c, ctx), SL.slackOf(rack, c, ctx)]), before);
});

test('spareCoils gives none for a cord with no entry, for "slack: []", for an end, for a cord that cannot turn, or without the routes', () => {
  const {rack, c, ctx} = stored();
  assert.deepEqual(SL.spareCoils(rack, {...c, slack: undefined}, ctx), []);
  assert.deepEqual(SL.spareCoils(rack, {...c, slack: []}, ctx), []);
  assert.deepEqual(SL.spareCoils(rack, {...c, slack: [{end: 'a'}]}, ctx), []);
  assert.deepEqual(SL.spareCoils(rack, c, undefined), []);
  const wide = stored({item: 'i4', via: 'tray'});
  assert.deepEqual(SL.spareCoils(wide.rack, {...wide.c, media: 'power'}, wide.ctx), []);
});

test('spareCoils warns above the stack limit and does not refuse: the layers are drawn as they fall', () => {
  const {rack, c, ctx} = stored({item: 'i4', via: 'tray', value: 3, unit: 'm'});
  const big = {...c, length: {value: 5, unit: 'm', source: 'entered'}};
  const [k] = SL.spareCoils({...rack, cables: [big, ...rack.cables.slice(1)]}, big, ctx);
  assert.ok(k.layers > k.stack_limit, `${k.layers} layers against ${k.stack_limit}`);
  assert.equal(k.over_stack, true);
});
