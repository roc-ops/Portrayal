// spec/tests/js/rack-two-slot.mjs
// A CARD TWO SLOTS WIDE (docs/pcie-two-slot-bays-design.md): it seats in a
// bay whose `span` names the bay beside it, covers that bay, and is refused
// while the bay it would cover holds anything. Fitted the way a person fits
// one - two one-slot cards first, then the two-slot card into a taken pair
// and a free one - through the rack's `fit`, a reload's acceptSwaps, the slot
// tree, and the drawing's own seat.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import {COMMANDS} from '../../../kit/rack/commands.js';
import {slotEnv, slotTree, resolverFor} from '../../../kit/rack/slots.js';
import {acceptSwaps, spanBox, bayTransform, markSpan, applyOverrides} from '../../../kit/swap.js';
import {install, build} from './fake-dom.mjs';

const NIC = 'acme/nic@1', GPU = 'acme/gpu@1', FILL = 'acme/filler@1';
const PITCH = 20.32;
// five full-height slots on the CEM pitch; each but the last spans the next
const slot = i => ({at: [0, +(PITCH * (i - 1)).toFixed(2)], size: {w: 120.02, h: 21.59},
                    accepts: i < 5 ? [NIC, GPU, FILL] : [NIC, FILL], default: FILL,
                    ...(i < 5 ? {span: [`s${i + 1}`]} : {})});
const COMPONENTS = {
  'acme/riser@1': {class: 'riser', description: 'Riser - five slots',
                   bays: Object.fromEntries([1, 2, 3, 4, 5].map(i => [`s${i}`, slot(i)]))},
  [NIC]: {class: 'expansion-card', description: 'NIC - one slot', size: {w: 120.02, h: 21.59}},
  [GPU]: {class: 'expansion-card', description: 'GPU - two slots', size: {w: 120.02, h: 41.91}, 'slot-width': 2},
  [FILL]: {class: 'filler', description: 'Filler', size: {w: 120.02, h: 21.59}},
};
const compByRef = ref => {
  const k = ref == null ? null : String(ref).split(':')[0];
  return k && Object.hasOwn(COMPONENTS, k) ? COMPONENTS[k] : null;
};
const SLOTS = {srv: {default: 'base',
  bays: {rear: [{id: 'riser-1', accepts: ['acme/riser@1'], default: 'acme/riser@1', at: [0, 0], size: {w: 130, h: 110}}]},
  cages: {rear: []},
  configs: [{name: 'base', description: 'One riser', airflow: 'front-to-back', bays: {}, occupants: {}}]}};
const SIZES = {srv: {ru: 2, h: 87, d: 700, model: 'Srv-2', manufacturer: 'Acme', configs: ['base'], default: 'base',
                     family: null, kind: 'server'}};
const ctx = {chassisOf: ref => SIZES[ref] || null, slotsOf: ref => SLOTS[ref] || null, compByRef};
const fit = (rack, path, ref) => COMMANDS.fit.run(rack, {id: 'i1', path: `riser-1/module/${path}`, ref}, ctx);
const swapsOf = r => r.rack.items[0].swaps;
const SRV = M.withItem(M.newRack(), {ref: 'srv', cfg: 'base', ru: 10, label: 'srv-1'}).rack;
const P = s => `riser-1/module/${s}`;

test('two one-slot cards, then a two-slot card refused by a taken neighbour and seated in a free pair', () => {
  const a = fit(SRV, 's1', NIC);
  const b = fit(a.rack, 's2', NIC);
  assert.deepEqual(swapsOf(b), {[P('s1')]: NIC, [P('s2')]: NIC});
  // s1 holds a NIC; the two-slot card into s1 would cover s2, which holds the other
  assert.deepEqual(fit(b.rack, 's1', GPU),
    {error: `${P('s1')} cannot take ${GPU}: it covers ${P('s2')}, which holds ${NIC}. Empty s2 first.`});
  // s3 and s4 are free of cards, but s4 still holds the filler it ships with
  assert.deepEqual(fit(b.rack, 's3', GPU),
    {error: `${P('s3')} cannot take ${GPU}: it covers ${P('s4')}, which holds ${FILL}. Empty s4 first.`});
  // empty s4, and the pair is free
  const c = fit(b.rack, 's4', null);
  const d = fit(c.rack, 's3', GPU);
  assert.ok(!d.error, d.error);
  assert.deepEqual(swapsOf(d), {[P('s1')]: NIC, [P('s2')]: NIC, [P('s4')]: null, [P('s3')]: GPU});
  // nothing goes into the bay the card covers, a default included
  assert.deepEqual(fit(d.rack, 's4', NIC),
    {error: `${P('s4')} is covered by ${GPU} in ${P('s3')}. Empty s3 first.`});
  assert.deepEqual(fit(d.rack, 's4', 'default'),
    {error: `${P('s4')} is covered by ${GPU} in ${P('s3')}. Empty s3 first.`});
});

test('a bay that spans nothing does not take a two-slot card', () => {
  // s5 is the last slot: no bay beside it, so it does not accept one at all
  assert.match(fit(SRV, 's5', GPU).error, /^riser-1\/module\/s5 does not take acme\/gpu@1\./);
});

test('a reload refuses both claims on one pair, and says why', () => {
  const env = slotEnv(SRV.items[0], SLOTS.srv, compByRef);
  const r = acceptSwaps({[P('s1')]: GPU, [P('s2')]: NIC}, env);
  assert.deepEqual(r.accepted, {});
  assert.deepEqual(r.ignored.sort(), [P('s1'), P('s2')]);
  assert.match(r.why[P('s1')], /covers riser-1\/module\/s2, which holds acme\/nic@1/);
  assert.match(r.why[P('s2')], /is covered by acme\/gpu@1 in riser-1\/module\/s1/);
  const ok = acceptSwaps({[P('s1')]: GPU, [P('s2')]: null}, env);
  assert.deepEqual(ok.accepted, {[P('s1')]: GPU, [P('s2')]: null});
  assert.equal(ok.why, undefined, 'nothing refused, nothing said');
});

test('the slot tree says what covers what', () => {
  const env = slotEnv(SRV.items[0], SLOTS.srv, compByRef);
  const t = slotTree(env, {[P('s3')]: GPU, [P('s4')]: null});
  const at = p => t.bays.find(b => b.path === p);
  assert.deepEqual(at(P('s3')).covers, [P('s4')]);
  assert.equal(at(P('s4'))['covered-by'], P('s3'));
  assert.equal(at(P('s4')).holds, null);
  assert.ok(!('covers' in at(P('s1'))) && !('covered-by' in at(P('s1'))), 'a one-slot bay says neither');
});

test('the card is drawn in the box its two bays make, as manifest.span_box draws it', () => {
  const env = slotEnv(SRV.items[0], SLOTS.srv, compByRef);
  const bay = resolverFor(env, {}).entryAt(P('s3'));
  assert.deepEqual(spanBox(bay, COMPONENTS[GPU]), {at: [0, 40.64], size: {w: 120.02, h: 41.91}});
  assert.equal(spanBox(bay, COMPONENTS[NIC]), null, 'a one-slot card keeps its own bay');
  assert.equal(bayTransform(bay, COMPONENTS[GPU]), 'translate(60.01,61.595) translate(-60.01,-20.955)');
  assert.equal(bayTransform(bay, COMPONENTS[NIC]), 'translate(60.01,51.435) translate(-60.01,-10.795)');
});

test('seated on a drawing, the covered bay is marked and the card paints over it', async () => {
  install();
  const env = slotEnv(SRV.items[0], SLOTS.srv, compByRef);
  const R = resolverFor(env, {});
  const bayG = s => ({a: {id: `riser-1--module--${s}`, 'data-path': P(s), 'data-class': 'bay'}});
  const root = build({a: {}, c: [{a: {'data-path': 'riser-1', 'data-ref': 'acme/riser@1'},
                                  c: [{a: {'data-path': 'riser-1/module', 'data-ref': 'acme/riser@1'},
                                       c: ['s1', 's2', 's3', 's4', 's5'].map(bayG)}]}]});
  const skin = name => JSON.stringify({a: {id: name}, c: []});
  const loadSkin = async ref => ({comp: {...compByRef(ref), name: ref.split('/')[1].split('@')[0]},
                                  text: skin(ref.split('/')[1].split('@')[0])});
  const bay = R.entryAt(P('s3'));
  await applyOverrides(root, [bay], {[P('s3')]: GPU}, loadSkin);
  const g = p => root.querySelector(`[data-path="${p}"]`);
  assert.equal(g(P('s4')).getAttribute('data-covered-by'), P('s3'));
  const order = g(P('s3')).parentNode.children.map(n => n.getAttribute('data-path'));
  assert.deepEqual(order, [P('s1'), P('s2'), P('s4'), P('s3'), P('s5')]);
  // a one-slot card in its place uncovers s4
  await applyOverrides(root, [bay], {[P('s3')]: NIC}, loadSkin);
  assert.equal(g(P('s4')).getAttribute('data-covered-by'), null);
  markSpan(root, bay, null);
});
