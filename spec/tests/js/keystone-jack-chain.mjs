// spec/tests/js/keystone-jack-chain.mjs
// A KEYSTONE JACK IN A CLIP CAGE ON A FHD-FAPM6 IN AN FHD-1UBE BAY, AND A CABLE
// LANDED ON ITS RJ45 PORT. Four levels down:
//   enclosure bay-1 > the FAPM6 > cage clip1 > the jack seated in it > port rj45
//   path: bay-1/module/clip1-occupant/rj45
//
// All real: components.json (every contract in the library) and
// fhd-1ube.configs.json, built by the wrapper. Six openings: jacks in clip1,
// clip3, clip5; a blank in clip2; clip4 and clip6 left empty.
//
// Run by test_keystone_jack_chain_js.py.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as M from '../../../kit/rack/model.js';
import * as P from '../../../kit/rack/ports.js';
import * as Q from '../../../kit/rack/queries.js';
import {slotEnv, slotTree, resolverFor, holdsAt} from '../../../kit/rack/slots.js';
import {apply} from '../../../kit/rack/commands.js';

const DIST = process.env.PORTRAYAL_DIST;
assert.ok(DIST, 'PORTRAYAL_DIST names the directory holding components.json and fhd-1ube.configs.json');
const read = name => JSON.parse(fs.readFileSync(`${DIST}/${name}`, 'utf8'));
const refOf = c => `${c.ns}/${c.name}@${String(c.major).replace(/^v/, '')}`;
const comps = new Map(read('components.json').components.map(c => [refOf(c), c]));

const FAPM6 = 'fs/fhd-fapm6@1';
// the inserts are the parts that mate the opening's interface, found and not named
const INSERTS = [...comps.values()].filter(c => c.mates === 'keystone');
const JACK = refOf(INSERTS.find(c => (c.parts || []).some(q => q.id === 'rj45')));
const BLANK = refOf(INSERTS.find(c => !(c.parts || []).length));
const CLIPS = [1, 2, 3, 4, 5, 6].map(n => `clip${n}`);
const compByRef = ref => (ref == null ? null : comps.get(String(ref).split(':')[0]) ?? null);

// ── the FHD-1UBE, real ─────────────────────────────────────────────────────
const cfg = read('fhd-1ube.configs.json');
const slots = {default: cfg.default, 'pdu-class': cfg['pdu-class'], bays: cfg.bays, cages: cfg.cages, configs: cfg.configs};
const chassisOf = ref => ({'fhd-1ube': {ru: 1, w: 448, h: 44, d: 227, model: 'FHD-1UBE', manufacturer: 'FS', kind: 'patch panel', configs: ['base'], default: 'base'},
                           sw: {ru: 1, w: 438, h: 43.6, d: 400, model: 'SW', manufacturer: 'Acme', kind: 'switch', configs: ['base'], default: 'base'}})[ref] ?? null;
const SW = {default: 'base', 'pdu-class': null, bays: {front: [], rear: []}, cages: {front: [], rear: []},
            configs: [{name: 'base', description: '', airflow: 'front-to-back', bays: {}, occupants: {}}]};
const ctx = {chassisOf, slotsOf: ref => ({'fhd-1ube': slots, sw: SW})[ref] ?? null, compByRef};

const BAY = 'bay-1';
const SWAPS = {[BAY]: FAPM6, [`${BAY}/module/clip1`]: JACK, [`${BAY}/module/clip2`]: BLANK,
               [`${BAY}/module/clip3`]: JACK, [`${BAY}/module/clip5`]: JACK};
const add = (rack, ref, ru, extra) => M.withItem(rack, {ref, cfg: 'base', ru, label: ref, ...extra}).rack;
const RACK = add(add(M.newRack(), 'fhd-1ube', 30, {label: 'pp-1', swaps: SWAPS}), 'sw', 20, {label: 'sw-1'});
const pp = RACK.items.find(i => i.ref === 'fhd-1ube');
const end = (path, view = 'front', item = 'i1') => ({item, path, view});
const at = c => `${BAY}/module/${c}`;                 // the cage
const port = c => `${BAY}/module/${c}-occupant/rj45`; // the port of what it holds
const JACKS = ['clip1', 'clip3', 'clip5'], BLANKED = ['clip2'], EMPTY = ['clip4', 'clip6'], NOT_JACKS = [...BLANKED, ...EMPTY];
const SW_END = end('mgmt', 'front', 'i2');
const json = v => JSON.stringify(v);

// ── the chain is seated in the catalogue ───────────────────────────────────
test('the real FHD-1UBE bay-1 accepts the FAPM6', () => {
  const bay = cfg.bays.front.find(b => b.id === BAY);
  assert.ok(bay.accepts.includes(FAPM6), `${BAY} accepts ${FAPM6}`);
});

test('the FAPM6 publishes six keystone cages that take the blank and the jack, empty as FS ships them', () => {
  const c = comps.get(FAPM6);
  assert.deepEqual(c.cages.map(g => g.id), CLIPS);
  for (const g of c.cages) {
    assert.equal(g.interface, 'keystone');
    assert.equal(g.default, null);
    assert.deepEqual([...g.accepts].sort(), [BLANK, JACK].sort());
  }
});

test('slotTree lists the FAPM6 in the bay and its six clip cages, each with what it holds', () => {
  const env = slotEnv(pp, slots, compByRef), tree = slotTree(env, pp.swaps);
  assert.equal(tree.bays.find(b => b.path === BAY).holds, FAPM6);
  const cages = tree.cages.filter(g => g.path.startsWith(`${BAY}/module/`) && !g.path.includes('-occupant'));
  assert.deepEqual(cages.map(g => g.path), CLIPS.map(at));
  assert.deepEqual(cages.map(g => g.holds), [JACK, BLANK, JACK, null, JACK, null]);
  assert.ok(cages.every(g => g.interface === 'keystone'));
});

test('the resolver reaches the jack and its rj45 slot four levels down', () => {
  const env = slotEnv(pp, slots, compByRef), R = resolverFor(env, pp.swaps);
  assert.equal(R.refAt(`${BAY}/module`), FAPM6);
  assert.equal(R.entryAt(at('clip1')).interface, 'keystone');
  assert.equal(R.refAt(`${at('clip1')}-occupant`), JACK);
  assert.equal(R.refAt(port('clip1')), 'std/rj45@2');
  const slot = R.entryAt(port('clip1'));
  assert.equal(slot?.interface, 'rj45');
  assert.equal(slot.kind, 'connector');
  assert.equal(R.entryAt(port('clip4')), null, 'nothing seated in clip4, so no slot under it');
  assert.equal(holdsAt(env, pp.swaps, at('clip4'), {...R.entryAt(at('clip4')), isCage: true}), null);
});

// ── seatedPort ─────────────────────────────────────────────────────────────
test('seatedPort finds the jack\'s port', () => {
  for (const c of JACKS) {
    const got = P.seatedPort(pp, end(port(c)), ctx);
    assert.equal(got?.port, true, `${c}: ${json(got)}`);
    assert.equal(got.holder?.ref, FAPM6);
    assert.equal(got.info?.family, 'copper');
    assert.equal(got.onView, 'front');
  }
});

test('seatedPort says a clip with a blank in it has no port, and names the blank', () => {
  const got = P.seatedPort(pp, end(port('clip2')), ctx);
  assert.equal(got?.port, false);
  assert.equal(got.part, undefined, 'not "a part is here that takes no cable": the blank has no port to name');
  assert.equal(got.holder?.path, at('clip2'));
  assert.equal(got.holder?.ref, BLANK);
});

test('seatedPort says an empty clip is empty', () => {
  for (const c of EMPTY) {
    const got = P.seatedPort(pp, end(port(c)), ctx);
    assert.equal(got?.port, false, c);
    assert.deepEqual(got.holder, {path: at(c), part: null, ref: null}, c);
  }
});

test('seatedPort answers for a jack on the other panel', () => {
  const got = P.seatedPort(pp, end(port('clip1'), 'rear'), ctx);
  assert.equal(got?.port, false);
  assert.equal(got.onView, 'front');
});

test('the cage\'s own address still answers for the clip, whatever it holds', () => {
  for (const c of CLIPS) assert.equal(P.seatedPort(pp, end(at(c)), ctx)?.port, false, c);
});

// ── cableEndPaths ──────────────────────────────────────────────────────────
test('cableEndPaths gives the jack\'s port a path and the blank and the empty clips none', () => {
  const paths = P.cableEndPaths(pp, 'front', ctx).filter(p => p.startsWith(`${BAY}/`)).sort();
  assert.deepEqual(paths, JACKS.map(port));
});

test('cableEndPaths offers nothing under a jack on the panel it is not on', () => {
  assert.deepEqual(P.cableEndPaths(pp, 'rear', ctx).filter(p => p.startsWith(`${BAY}/`)), []);
});

// ── landing the cable ──────────────────────────────────────────────────────
test('a cable from a switch to the jack is added', () => {
  const res = apply(RACK, [{op: 'cable.add', a: SW_END, b: end(port('clip1')), media: 'cat6'}], ctx);
  assert.equal(res.error, undefined);
  assert.equal(res.rack.cables.length, 1);
});

test('a cable end on the jack lands as a copper port', () => {
  const page = {facts: {item: true, drawing: true, port: false, cage: false, occupied: false, holder: null}, info: null, reason: 'no port'};
  const settled = P.settleEnd(RACK, end(port('clip1')), page, ctx);
  assert.equal(settled?.facts?.port, true);
  assert.equal(settled.info?.family, 'copper');
});

test('a cable end on a blank is refused when it is added, and says so', () => {
  const res = apply(RACK, [{op: 'cable.add', a: SW_END, b: end(port('clip2')), media: 'cat6'}], ctx);
  assert.match(res.error ?? '', /has no port rj45/);
  assert.match(res.error, /clip2/);
});

test('a cable already on a jack is not a second cable on the same jack', () => {
  const one = apply(RACK, [{op: 'cable.add', a: SW_END, b: end(port('clip1')), media: 'cat6'}], ctx);
  assert.equal(one.error, undefined);
  const two = apply(one.rack, [{op: 'cable.add', a: end('mgmt', 'front', 'i2'), b: end(port('clip1')), media: 'cat6'}], ctx);
  assert.ok(two.error, 'one cable per port');
});

// ── the agent's free-port answer for the six openings ──────────────────────
// A page's reader hands in each port it drew, by path or as the drawing's element id
// (`bay-1--module--clip1-occupant--rj45`, cable-rules.js isElementId).
const elementId = p => p.split('/').join('--');
const reader = spell => async (item, view) => (view === 'front' ? JACKS.map(c => ({cls: 'port', path: spell(port(c)), media: 'rj45'})) : []);
const freeFront = async (portsOf, rack = RACK) => (await Q.freePorts(rack, 'i1', {...ctx, portsOf})).filter(f => f.view === 'front').map(f => f.path).sort();

test('free ports, from a reader that hands in the jacks\' paths, are the three jacks', async () => {
  assert.deepEqual(await freeFront(reader(p => p)), JACKS.map(port));
});

test('free ports, from a reader that hands in the jacks\' element ids, are the three jacks', async () => {
  assert.deepEqual(await freeFront(reader(elementId)), JACKS.map(port));
});

test('free ports offer nothing for the blank and the empty clips', async () => {
  const got = await freeFront(reader(p => p));
  for (const c of NOT_JACKS) assert.equal(got.some(p => p.includes(`/${c}`)), false, c);
});

test('free ports, with no reader, list no data port (queries.js lists the catalogue\'s power and ground ends only)', async () => {
  assert.deepEqual(await freeFront(async () => []), []);
});

test('a jack with a cable on it is no longer free', async () => {
  const one = apply(RACK, [{op: 'cable.add', a: SW_END, b: end(port('clip3')), media: 'cat6'}], ctx);
  assert.deepEqual(await freeFront(reader(p => p), one.rack), ['clip1', 'clip5'].map(port));
});
