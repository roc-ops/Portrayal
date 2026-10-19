// spec/tests/js/rack-speed.mjs
// The rack kit made fast on a large rack (kit 0.25.0) WITHOUT A NUMBER
// CHANGED: every answer it gives is the one it gave before, a lay kept is
// the lay that would be made, and a rack of a real one's size is read within
// a budget.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {performance} from 'node:perf_hooks';
import * as M from '../../../kit/rack/model.js';
import * as R from '../../../kit/rack/route.js';
import * as F from './cable-solids-fixture.mjs';
import {loadTree, outputsOf, digestsOf, differences, GOLDENS} from './speed-goldens.mjs';
import {speedRack, moveCable, moveDevice} from './speed-fixture.mjs';

const K = await loadTree();
const WANT = JSON.parse(readFileSync(GOLDENS, 'utf8'));

// ── the invariant ────────────────────────────────────────────────────────
// speed-goldens.json holds a digest of every answer the kit gave, for every
// rack of speed-goldens.mjs, recorded from the kit as it was before 0.25.0
// (kit 0.24.0, c3313dbb), each number to seven places so that the file
// holds on any machine; the two kits were compared by every digit on one
// (speed-goldens.mjs, `--exact`). A change that is meant to move a number
// records them again (speed-goldens.mjs says how).
// RECORDED AGAIN FOR KIT 0.27.0 (#1026, #987), which is meant to move
// numbers: a lead's ring is chosen by room, a detour round a tray is laid
// another way, a patch's ring is chosen by its lay, a span has a point at
// the edge of what it lies on, and two turns on one leg are one finding. Of
// the 91 racks 75 have an answer that moves (1,580 of the 3,094 answers:
// paths, lengths and what is read off them, the schedule, the BOM, the
// spare and the DCIM cables files among them); the other 16 are as they
// were. So the file is this kit's own answers
// now, and holds the next change to them.
// RECORDED AGAIN FOR KIT 0.28.0 (#1034), which moves `straps` and
// `bundle-exports` on the racks that have a bundle and no other answer: each
// strap gained its `point`, `dir` and `on`, the straps and each export
// record gained `straight` and `few`, a trunk is measured along its members'
// paths, and a place half way between two tenths of a millimetre always
// rounds up (bundles.js mm1).
// RECORDED AGAIN FOR #985, which moves the answers of a DAC's or an AOC's
// cord wherever the page gives no number for its reach (a plug that cannot
// bend, PLUG_SPLIT): the generated racks of bend-room-sample (`sample-N`), and
// only they, since every other rack here is LC, or gives the reach as a number
// as speed-fixture does. 1,259 of the 3,094 answers moved.
test('every answer for every rack is the one recorded', async () => {
  const {digests, count} = await digestsOf(K);
  assert.deepEqual(differences(digests, WANT.digests), []);
  // and it is not a comparison of nothing with nothing
  assert.deepEqual(count, WANT.count);
  assert.ok(count.racks >= 91 && count.cables >= 3900 && count.answers >= 3000, JSON.stringify(count));
  assert.ok(Object.values(WANT.digests).every(kinds => Object.keys(kinds).length >= 30));
});

// A page makes a context anew for every draw and every tool call, so the
// answers are read here with a new context for each group of them: what is
// kept from one context must be what the next would work out. On the
// fixtures, the rack files, one generated rack in five and every rack of
// speed-fixture, to keep this file's time down; the test above reads all.
test('a context made anew for each group of answers gives the same answers', async () => {
  const only = name => !/^sample-/.test(name) || Number(name.slice(7)) % 5 === 0;
  const {digests, count} = await digestsOf(K, {fresh: true, only});
  const want = Object.fromEntries(Object.entries(WANT.digests).filter(([name]) => only(name)));
  assert.deepEqual(differences(digests, want), []);
  assert.ok(count.racks >= 40 && count.cables >= 1800, JSON.stringify(count));
});

// ── what is kept is what would be made ───────────────────────────────────
// A rack is edited step by step, as a page's commands edit one (a new rack
// that shares what it did not touch), and after each step every answer is
// read twice: from the rack as it is, with whatever the kit kept from the
// steps before, and from a copy of it in which every object is new, so that
// nothing kept applies. The two must be the same text, every number whole.
test('after each edit, the answers with what was kept are the answers of a rack read for the first time', async () => {
  const made = speedRack(M, F, {cables: 80, bundles: 3, seed: 7});
  const answers = r => outputsOf(K, {rack: r, ctxOf: made.ctxOf, chassisOf: made.chassisOf}, {fresh: true, exact: true});
  const cable = (r, id, fn) => ({...r, cables: r.cables.map(c => (c.id === id ? fn(c) : c))});
  const first = made.rack;
  const steps = [
    ['as generated', r => r],
    ['a cable moved to another port', r => moveCable(r, 'c3')],
    ['a cable relabelled', r => cable(r, 'c4', c => ({...c, label: 'uplink A'}))],
    ['a cable of another media', r => cable(r, 'c6', c => ({...c, media: c.media === 'cat6a' ? 'om4' : 'cat6a'}))],
    ['a cable given a length', r => cable(r, 'c8', c => ({...c, length: {value: 7, unit: 'm', source: 'entered'}}))],
    ['a cable routed by hand', r => cable(r, 'c9', c => ({...c, routeEdited: true, route: [{lane: 'right-front', ru: 40}, {lane: 'right-front', ru: 20}]}))],
    ['a switch moved down a unit', r => moveDevice(r, made.switches[6])],
    ['a cable removed', r => ({...r, cables: r.cables.filter(c => c.id !== 'c10')})],
    ['a cable written end for end', r => cable(r, 'c12', c => ({...c, a: c.b, b: c.a}))],
    ['a lacer removed', r => ({...r, items: r.items.filter(i => i.id !== made.lacerOf[made.switches[2]])})],
    ['a bundle let go', r => ({...r, bundles: (r.bundles || []).slice(1)})],
    ['the rails moved apart', r => ({...r, frame: {...r.frame, railDepth: 800}})],
    ['a duct removed', r => ({...r, zeroU: r.zeroU.slice(1)})],
    ['undone, to the rack as generated', () => first],
  ];
  let rack = first, read = 0;
  for (const [name, step] of steps) {
    rack = step(rack);
    const kept = await answers(rack), fresh = await answers(structuredClone(rack));
    for (const kind of Object.keys(fresh)) assert.equal(kept[kind], fresh[kind], `${name}: ${kind}`);
    assert.ok(Object.keys(kept).length >= 30 && JSON.parse(kept.paths).filter(Boolean).length >= 70, name);
    read++;
  }
  assert.equal(read, steps.length);
});

test('a path handed out is the caller\'s own: changing it changes no later answer', () => {
  const made = speedRack(M, F, {cables: 20, seed: 9}), rack = made.rack, ctx = made.ctxOf(rack);
  const c = rack.cables[0], before = JSON.stringify(R.routePath(rack, c, ctx));
  const p = R.routePath(rack, c, ctx);
  p.points.length = 1; p.points[0].x = 1e6; p.bends.push({short_mm: 99}); p.rings.forEach(g => { g.sense = 0; }); p.marks.fill('x');
  const route = R.resolveRoute(rack, c, ctx);
  route.waypoints.length = 0;
  for (const f of R.bendFindings(rack, ctx)) { f.between.length = 0; f.at[0] = 1e6; }
  for (const f of R.coverFindings(rack, ctx)) { f.between.length = 0; f.ports.length = 0; }
  assert.equal(JSON.stringify(R.routePath(rack, c, ctx)), before);
  assert.equal(JSON.stringify(R.routePath(rack, c, made.ctxOf(rack))), before);
  assert.ok(R.resolveRoute(rack, c, ctx).waypoints.length > 0);
  assert.notEqual(R.routePath(rack, c, ctx), R.routePath(rack, c, ctx));
});

test('spareOf takes the path it is handed, and reads the one kept without', () => {
  const made = speedRack(M, F, {cables: 20, seed: 9});
  const rack = R.withRoutedLengths(made.rack, made.ctxOf(made.rack)), ctx = made.ctxOf(rack);
  for (const c of rack.cables) assert.deepEqual(R.spareOf(rack, c, ctx, R.routePath(rack, c, ctx)), R.spareOf(rack, c, ctx));
  assert.equal(R.spareOf(rack, rack.cables[0], ctx, null), null);
  assert.ok(rack.cables.some(c => R.spareOf(rack, c, ctx)?.need_m > 0));
});

// ── the run-outs (#1038) ─────────────────────────────────────────────────
// A run-out is tried at a lead end only where a way round in that lead goes
// round a body that is no tray's floor (a ring's part, or its web, #1026): a
// floor is gone round and a run-out does not clear it. Counted on the first
// read of the rack of the budgets below, by the kit's own counter, not by the
// clock: the run-outs were tried at 1,202 lead ends (1,070 of them with a
// floor in the lead), three trial lays each, and taken at 34.
test('at 300 cables: run-outs are tried at 87 lead ends, not 1,202, and the 34 taken before are taken', () => {
  const made = speedRack(M, F, {cables: 300, bundles: 4, seed: 11}), rack = made.rack, ctx = made.ctxOf(rack);
  R.RUN_OUTS.tried = R.RUN_OUTS.taken = 0;
  for (const c of rack.cables) R.routePath(rack, c, ctx);
  assert.deepEqual({...R.RUN_OUTS}, {tried: 87, taken: 34});
});

// ── the budgets ──────────────────────────────────────────────────────────
// A rack of thirteen two-unit switches, a lacer on each, two ducts and 300
// cords (speed-fixture.mjs), every path read (routePath over every cable).
// THE FIGURES ARE CEILINGS WITH HEADROOM, not what it takes: on the machine
// they were chosen on (twelve cores, node 22, other work running) a first
// read took 0.6 s, where the kit before 0.25.0 took 35 s, a second read
// 3 ms, a read in a context made anew 26 ms and a read after one cable
// moved 26 ms. A first read may take FIRST_MS, some sixteen times what it
// took; the others are held to a fraction of that budget (a second read a
// twentieth, a new context and one cable moved a fifth each), and a read
// after one cable moved also to half of what the first read took in this
// run, which is what says the other 299 cables were not laid again.
// HELD AFTER #1038 (run-outs tried only where a body that is no floor stands
// in a lead): FIRST_MS was 10000 and is 6000, SECOND 0.05 and is 0.03, ANEW
// and EDITED 0.2 and are 0.1. On a shared machine at a load of 14 a first
// read took 3 s (2.9 s with the run-outs gated, 3.3 s without), so the
// ceiling is twice that, and some nine times a quiet machine's.
const FIRST_MS = 6000, SECOND = 0.03, ANEW = 0.1, EDITED = 0.1;
test('at 300 cables: a first read within its budget, and a second, a new context and one cable moved within a fraction of it', () => {
  const made = speedRack(M, F, {cables: 300, bundles: 4, seed: 11}), rack = made.rack;
  assert.equal(rack.cables.length, 300);
  const all = (r, c) => r.cables.map(x => R.routePath(r, x, c));
  const ms = fn => { const t = performance.now(); const v = fn(); return [performance.now() - t, v]; };
  const ctx = made.ctxOf(rack);
  const [first, paths] = ms(() => all(rack, ctx));
  assert.ok(paths.every(Boolean), 'every cable has a path');
  const [second] = ms(() => all(rack, ctx));
  const [anew] = ms(() => all(rack, made.ctxOf(rack)));
  // the better of two, each a different cable moved, so that one pause does not fail it
  const moved = ['c1', 'c2'].map(id => { const r = moveCable(rack, id); return ms(() => all(r, made.ctxOf(r)))[0]; });
  const edited = Math.min(...moved);
  const said = `first ${Math.round(first)} ms, second ${second.toFixed(1)} ms, new context ${Math.round(anew)} ms, one cable moved ${Math.round(edited)} ms`;
  assert.ok(first < FIRST_MS, said);
  assert.ok(second < SECOND * FIRST_MS, said);
  assert.ok(anew < ANEW * FIRST_MS, said);
  assert.ok(edited < EDITED * FIRST_MS, said);
  assert.ok(edited < first / 2, said);
});
