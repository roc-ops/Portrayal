// spec/tests/js/rack-fit-command.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import {COMMANDS, GONE, apply} from '../../../kit/rack/commands.js';
import {ctx, chassisOf} from './slot-fixtures.mjs';

const run = (rack, args, c = ctx) => COMMANDS.fit.run(rack, args, c);
const CFG = {leaf: 'base', pp: 'loaded', mgr: 'base'};
const add = (rack, ref, ru, extra = {}) => M.withItem(rack, {ref, cfg: CFG[ref], ru, label: ref, ...extra}).rack;
const end = (item, path = 'port-1', view = 'front') => ({item, path, view});
const cable = (id, a, b, extra = {}) => ({id, a, b, media: '', purpose: '', label: '', route: [], ...extra});
const LEAF = add(M.newRack(), 'leaf', 10, {label: 'leaf-1', swaps: {'psu-1': 'acme/psu-dc@1'}});

test('fit: seat a part, empty a slot, and put back what the configuration builds', () => {
  const a = run(LEAF, {id: 'i1', path: 'port-2', ref: 'acme/lr@1'});
  assert.deepEqual(a.rack.items[0].swaps, {'psu-1': 'acme/psu-dc@1', 'port-2': 'acme/lr@1'});
  assert.equal(a.summary, 'Fitted LR optic in port-2 on leaf-1.');
  const b = run(LEAF, {id: 'i1', path: 'port-1', ref: null});
  assert.deepEqual(b.rack.items[0].swaps, {'psu-1': 'acme/psu-dc@1', 'port-1': null});
  assert.equal(b.summary, 'Emptied port-1 on leaf-1.');
  const c = run(LEAF, {id: 'i1', path: 'psu-1', ref: 'default'});
  assert.deepEqual(c.rack.items[0].swaps, {});
  assert.equal(c.summary, 'Fitted AC power supply in psu-1 on leaf-1.');
  assert.equal(run(LEAF, {id: 'i1', path: 'port-2', ref: 'default'}).rack, LEAF);
  assert.deepEqual(run(LEAF, {id: 'i9', path: 'port-1', ref: null}), {error: GONE});
});

test('fit: a nested bay, after its carrier', () => {
  const pp = add(M.newRack(), 'pp', 5, {label: 'pp-1'});
  const r = apply(pp, [{op: 'fit', id: 'i1', path: 'bay-2', ref: 'acme/carrier@1'},
                       {op: 'fit', id: 'i1', path: 'bay-2/module/sub-1', ref: 'acme/lc6@1'}], ctx);
  assert.deepEqual(r.rack.items[0].swaps, {'bay-2': 'acme/carrier@1', 'bay-2/module/sub-1': 'acme/lc6@1'});
  assert.equal(r.summary, 'Fitted Carrier in bay-2 on pp-1. Fitted LC cassette in bay-2/module/sub-1 on pp-1.');
});

test('fit: an unknown path lists the slots there; a part the slot does not take lists what it does', () => {
  assert.deepEqual(run(LEAF, {id: 'i1', path: 'port-9', ref: 'acme/sr@1'}),
    {error: 'port-9 is not a bay or cage on leaf-1. It has: psus: psu-1; sfp: port-1, port-2.'});
  assert.deepEqual(run(add(M.newRack(), 'pp', 5, {label: 'pp-1'}), {id: 'i1', path: 'bay-1/module/lc9', ref: 'acme/lc-plug@1'}),
    {error: 'bay-1/module/lc9 is not a bay or cage on pp-1. It has: lc-duplex: bay-1/module/lc1, bay-1/module/lc2.'});
  assert.deepEqual(run(LEAF, {id: 'i1', path: 'port-1', ref: 'acme/psu-ac@1'}),
    {error: 'port-1 does not take acme/psu-ac@1. It takes: acme/sr@1, acme/lr@1, acme/dac@1.'});
});

test('fit: a long list of parts is cut at eight', () => {
  const many = Array.from({length: 11}, (_, k) => `acme/x${k}@1`);
  const slotsOf = ref => (ref === 'leaf' ? {...ctx.slotsOf('leaf'), cages: {front: [{id: 'port-1', group: 'sfp', accepts: many, default: null}]}} : null);
  assert.deepEqual(run(LEAF, {id: 'i1', path: 'port-1', ref: 'acme/sr@1'}, {...ctx, slotsOf}),
    {error: `port-1 does not take acme/sr@1. It takes: ${many.slice(0, 8).join(', ')} and 3 more.`});
});

test('fit: without slots it merges and checks nothing; a missing parts list is refused', () => {
  const r = run(LEAF, {id: 'i1', path: 'port-48', ref: 'x'}, {chassisOf});
  assert.deepEqual(r.rack.items[0].swaps, {'psu-1': 'acme/psu-dc@1', 'port-48': 'x'});
  // partName falls back to the ref when the part has no description to read
  assert.equal(r.summary, 'Fitted x in port-48 on leaf-1.');
  assert.deepEqual(run(LEAF, {id: 'i1', path: 'port-1', ref: null}, {...ctx, slotsOf: () => null}),
    {error: 'The parts list for leaf could not be loaded.'});
});

test('fit: a different cassette keeps the cables on ports it lacks as loose ends, and says so', () => {
  let r = add(add(M.newRack(), 'pp', 5, {label: 'pp-1'}), 'leaf', 10, {label: 'leaf-1'});
  r = {...r, cables: [cable('c1', end('i1', 'bay-1/module/lc1'), end('i2')), cable('c2', end('i1', 'bay-1/module/lc2/1'), end('i2', 'port-2'))]};
  const f = run(r, {id: 'i1', path: 'bay-1', ref: 'acme/mpo2@1'});
  assert.equal(f.rack.cables.length, 2);
  assert.deepEqual(f.findings, [{kind: 'note', text: 'Kept the cables on bay-1/module/lc1, bay-1/module/lc2/1 as loose ends (c1, c2): these ports are not on MPO cassette.'}]);
  const e = run(r, {id: 'i1', path: 'bay-1', ref: null});
  assert.deepEqual(e.findings, [{kind: 'note', text: 'Kept the cables on bay-1/module/lc1, bay-1/module/lc2/1 as loose ends (c1, c2): bay-1 is empty.'}]);
});

test('fit: what was seated in a part, and its fields, go with it', () => {
  const r = add(M.newRack(), 'pp', 5, {label: 'pp-1', swaps: {'bay-1/module/lc1': 'acme/lc-plug@1', 'bay-2': 'acme/lc6@1'},
    fields: {'bay-1/module': {'latch-color': 'green'}, 'bay-1/module/lc1-occupant': {x: '1'}, 'bay-2/module': {'latch-color': 'beige'}}});
  const f = run(r, {id: 'i1', path: 'bay-1', ref: 'acme/mpo2@1'});
  assert.deepEqual(f.rack.items[0].swaps, {'bay-1': 'acme/mpo2@1', 'bay-2': 'acme/lc6@1'});
  assert.deepEqual(f.rack.items[0].fields, {'bay-2/module': {'latch-color': 'beige'}});
});

test('fit: an optic that does not suit the cable on its port is a finding', () => {
  let r = add(add(M.newRack(), 'leaf', 10, {label: 'leaf-1'}), 'leaf', 20, {label: 'leaf-2'});
  r = {...r, cables: [cable('c3', end('i1', 'port-2'), end('i2', 'port-2'), {media: 'om4'})]};
  assert.deepEqual(run(r, {id: 'i1', path: 'port-2', ref: 'acme/lr@1'}).findings,
    [{kind: 'note', text: 'c3 now runs OM4 multimode fiber into LR optic.'}]);
  assert.deepEqual(run(r, {id: 'i1', path: 'port-2', ref: 'acme/sr@1'}).findings, []);
});

test('fit: the other swaps are kept', () => {
  const r = run(LEAF, {id: 'i1', path: 'port-2', ref: 'acme/dac@1'});
  assert.equal(r.rack.items[0].swaps['psu-1'], 'acme/psu-dc@1');
});

test('fit: a slot on the part the configuration built, with no swap naming that part', () => {
  const pp = add(M.newRack(), 'pp', 5, {label: 'pp-1'});
  const r = run(pp, {id: 'i1', path: 'bay-1/module/lc1', ref: 'acme/lc-plug@1'});
  assert.deepEqual(r.rack.items[0].swaps, {'bay-1/module/lc1': 'acme/lc-plug@1'});
  assert.equal(r.summary, 'Fitted LC plug in bay-1/module/lc1 on pp-1.');
});

test('fit: a swap from an older file that its slot refuses does not block another slot, and is kept', () => {
  const old = add(M.newRack(), 'leaf', 10, {label: 'leaf-1', swaps: {'port-1': 'junk'}});
  const r = run(old, {id: 'i1', path: 'port-2', ref: 'acme/sr@1'});
  assert.deepEqual(r.rack.items[0].swaps, {'port-1': 'junk', 'port-2': 'acme/sr@1'});
});

test('fit: a batch is one undo step, swaps and fields alike', async () => {
  const {createRackEditor} = await import('../../../kit/rack/editor.js');
  const doc = M.newDoc();
  doc.racks[0] = add(doc.racks[0], 'pp', 5, {label: 'pp-1', fields: {'bay-1/module': {'latch-color': 'green'}}});
  const ed = createRackEditor({doc, chassisOf});
  const res = ed.apply([{op: 'fit', id: 'i1', path: 'bay-1', ref: 'acme/mpo2@1'}, {op: 'fit', id: 'i1', path: 'bay-2', ref: 'acme/lc6@1'}],
                       {origin: 'agent', ctx});
  assert.equal(res.step, true);
  assert.deepEqual(ed.rack().items[0].fields, {});
  ed.undo();
  assert.deepEqual([ed.rack().items[0].swaps, ed.rack().items[0].fields], [{}, {'bay-1/module': {'latch-color': 'green'}}]);
});

test('fit: seating what a slot already holds is a no-op that leaves what sits inside it', () => {
  const pp = add(M.newRack(), 'pp', 5, {label: 'pp-1', swaps: {'bay-2': 'acme/carrier@1', 'bay-2/module/sub-1': 'acme/lc6@1'},
    fields: {'bay-2/module': {x: '1'}}});
  const r1 = run(pp, {id: 'i1', path: 'bay-2', ref: 'acme/carrier@1'});
  assert.equal(r1.rack, pp);
  assert.deepEqual(pp.items[0].swaps['bay-2/module/sub-1'], 'acme/lc6@1');
  assert.deepEqual(pp.items[0].fields, {'bay-2/module': {x: '1'}});
  const lf = add(M.newRack(), 'leaf', 10, {label: 'leaf-1', swaps: {'port-1': 'acme/sr@1', 'port-1-occupant': 'acme/x@1'},
    fields: {'port-1-occupant': {label: 'a'}}});
  assert.equal(run(lf, {id: 'i1', path: 'port-1', ref: 'acme/sr@1'}).rack, lf);
  // the configuration's own default, and an empty slot left empty
  assert.equal(run(LEAF, {id: 'i1', path: 'port-1', ref: 'acme/sr@1'}).rack, LEAF);
  assert.equal(run(LEAF, {id: 'i1', path: 'port-2', ref: null}).rack, LEAF);
  assert.equal(run(LEAF, {id: 'i1', path: 'port-2', ref: 'default'}).rack, LEAF);
  // without slots, the same part under its own key
  const bare = {chassisOf};
  assert.equal(run(lf, {id: 'i1', path: 'port-1', ref: 'acme/sr@1'}, bare).rack, lf);
});

test('fit: a different part in a cage keeps the sibling cages\' swaps and fields, and the input untouched', () => {
  const lf = add(M.newRack(), 'leaf', 10, {label: 'leaf-1',
    swaps: {'port-1-occupant': 'a', 'port-10-occupant': 'b'}, fields: {'port-1-occupant': {l: '1'}, 'port-10-occupant': {l: '2'}}});
  const snap = JSON.parse(JSON.stringify(lf.items[0]));
  const r = run(lf, {id: 'i1', path: 'port-1', ref: 'acme/lr@1'});
  assert.equal(r.rack.items[0].swaps['port-10-occupant'], 'b');
  assert.deepEqual(r.rack.items[0].fields, {'port-10-occupant': {l: '2'}});
  assert.deepEqual(JSON.parse(JSON.stringify(lf.items[0])), snap);
});

test('fit: an end stored with -occupant under a swapped cassette that has the port gives no cut note', () => {
  let r = add(add(M.newRack(), 'pp', 5, {label: 'pp-1', swaps: {'bay-1': 'acme/mpo2@1'}}), 'leaf', 10, {label: 'leaf-1'});
  r = {...r, cables: [cable('c1', end('i1', 'bay-1/module/lc1-occupant'), end('i2'))]};
  const f = run(r, {id: 'i1', path: 'bay-1', ref: 'acme/lc6@1'});
  assert.deepEqual(f.findings, []);
});
