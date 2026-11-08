// spec/tests/js/rack-dual-wide-mic.mjs
// A DUAL-WIDE MIC fills both MIC windows of a line card: the carrier's first
// window `span`s the second, which lies beside it along the face rather than
// below it (docs/pcie-two-slot-bays-design.md). Swapped in and out the way a
// person does it through the rack's `fit`, a reload's acceptSwaps, the slot
// tree and the drawing's own seat: refused while the second window holds a
// MIC, seated once it is empty, and the second window comes back on the way
// out.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import {COMMANDS} from '../../../kit/rack/commands.js';
import {slotEnv, slotTree, resolverFor} from '../../../kit/rack/slots.js';
import {acceptSwaps, spanBox, bayTransform} from '../../../kit/swap.js';

const CARD = 'acme/mpc@1', WIDE = 'acme/mic-wide@1', ONE = 'acme/mic-one@1', BLANK = 'acme/blank@1';
// the windows of the MX line cards: 168.8 x 29.2, a 0.5 seam apart along x
const window = (x, extra = {}) => ({at: [x, 0.15], size: {w: 168.8, h: 29.2},
  accepts: [ONE, BLANK, ...(extra.span ? [WIDE] : [])], default: BLANK, ...extra});
const COMPONENTS = {
  [CARD]: {class: 'line-card', description: 'Line card - two MIC windows',
           bays: {mic0: window(37.7, {span: ['mic1']}), mic1: window(207.0)}},
  [WIDE]: {class: 'line-card', description: 'MIC - dual-wide', size: {w: 338.1, h: 29.2}, 'slot-width': 2},
  [ONE]: {class: 'line-card', description: 'MIC - single-wide', size: {w: 168.8, h: 29.2}},
  [BLANK]: {class: 'filler', description: 'Blank MIC', size: {w: 168.8, h: 29.2}},
};
const compByRef = ref => {
  const k = ref == null ? null : String(ref).split(':')[0];
  return k && Object.hasOwn(COMPONENTS, k) ? COMPONENTS[k] : null;
};
const SLOTS = {box: {default: 'base',
  bays: {front: [{id: 'fpc0', accepts: [CARD], default: CARD, at: [0, 0], size: {w: 413.5, h: 29.5}}]},
  cages: {front: []},
  configs: [{name: 'base', description: 'One card', airflow: 'front-to-back', bays: {}, occupants: {}}]}};
const SIZES = {box: {ru: 2, h: 87, d: 700, model: 'Box-2', manufacturer: 'Acme', configs: ['base'], default: 'base',
                     family: null, kind: 'router'}};
const ctx = {chassisOf: ref => SIZES[ref] || null, slotsOf: ref => SLOTS[ref] || null, compByRef};
const fit = (rack, path, ref) => COMMANDS.fit.run(rack, {id: 'i1', path: `fpc0/module/${path}`, ref}, ctx);
const swapsOf = r => r.rack.items[0].swaps;
const BOX = M.withItem(M.newRack(), {ref: 'box', cfg: 'base', ru: 10, label: 'box-1'}).rack;
const P = s => `fpc0/module/${s}`;

test('into mic0 is refused while mic1 holds a MIC, seated once mic1 is empty', () => {
  assert.deepEqual(fit(BOX, 'mic0', WIDE),
    {error: `${P('mic0')} cannot take ${WIDE}: it covers ${P('mic1')}, which holds ${BLANK}. Empty mic1 first.`});
  const a = fit(BOX, 'mic1', ONE);
  assert.deepEqual(fit(a.rack, 'mic1', null).error, undefined);
  const b = fit(fit(BOX, 'mic1', null).rack, 'mic0', WIDE);
  assert.ok(!b.error, b.error);
  assert.deepEqual(swapsOf(b), {[P('mic1')]: null, [P('mic0')]: WIDE});
});

test('mic1 takes nothing while the dual-wide MIC covers it, a default included', () => {
  const d = fit(fit(BOX, 'mic1', null).rack, 'mic0', WIDE);
  const covered = {error: `${P('mic1')} is covered by ${WIDE} in ${P('mic0')}. Empty mic0 first.`};
  assert.deepEqual(fit(d.rack, 'mic1', ONE), covered);
  assert.deepEqual(fit(d.rack, 'mic1', 'default'), covered);
});

test('out of mic0 gives mic1 back: a single-wide MIC or an empty window, then mic1 takes a MIC again', () => {
  const d = fit(fit(BOX, 'mic1', null).rack, 'mic0', WIDE);
  const out = fit(d.rack, 'mic0', ONE);
  assert.ok(!out.error, out.error);
  assert.equal(swapsOf(out)[P('mic0')], ONE);
  const back = fit(out.rack, 'mic1', ONE);
  assert.ok(!back.error, back.error);
  assert.equal(swapsOf(back)[P('mic1')], ONE);
  const empty = fit(d.rack, 'mic0', null);
  assert.ok(!empty.error, empty.error);
  assert.ok(!fit(empty.rack, 'mic1', BLANK).error);
});

test('mic1 takes no dual-wide MIC: it has no window beside it', () => {
  assert.match(fit(BOX, 'mic1', WIDE).error, /^fpc0\/module\/mic1 does not take acme\/mic-wide@1\./);
});

test('a reload refuses both claims, and says why', () => {
  const env = slotEnv(BOX.items[0], SLOTS.box, compByRef);
  const r = acceptSwaps({[P('mic0')]: WIDE, [P('mic1')]: ONE}, env);
  assert.deepEqual(r.accepted, {});
  assert.deepEqual(r.ignored.sort(), [P('mic0'), P('mic1')]);
  assert.match(r.why[P('mic0')], /covers fpc0\/module\/mic1, which holds acme\/mic-one@1/);
  assert.match(r.why[P('mic1')], /is covered by acme\/mic-wide@1 in fpc0\/module\/mic0/);
  const ok = acceptSwaps({[P('mic0')]: WIDE, [P('mic1')]: null}, env);
  assert.deepEqual(ok.accepted, {[P('mic0')]: WIDE, [P('mic1')]: null});
  assert.equal(ok.why, undefined);
});

test('the slot tree says mic0 covers mic1', () => {
  const env = slotEnv(BOX.items[0], SLOTS.box, compByRef);
  const t = slotTree(env, {[P('mic0')]: WIDE, [P('mic1')]: null});
  const at = p => t.bays.find(b => b.path === p);
  assert.deepEqual(at(P('mic0')).covers, [P('mic1')]);
  assert.equal(at(P('mic1'))['covered-by'], P('mic0'));
  assert.equal(at(P('mic1')).holds, null);
});

test('the MIC is drawn in the box the two windows make, one plate with the seam under it', () => {
  const env = slotEnv(BOX.items[0], SLOTS.box, compByRef);
  const bay = resolverFor(env, {}).entryAt(P('mic0'));
  const box = spanBox(bay, COMPONENTS[WIDE]);
  assert.deepEqual(box.at, [37.7, 0.15]);
  assert.ok(Math.abs(box.size.w - 338.1) < 1e-6 && box.size.h === 29.2, JSON.stringify(box));
  assert.equal(spanBox(bay, COMPONENTS[ONE]), null, 'a single-wide MIC keeps its own window');
  assert.equal(bayTransform(bay, COMPONENTS[WIDE]), 'translate(206.75,14.75) translate(-169.05,-14.6)');
});
