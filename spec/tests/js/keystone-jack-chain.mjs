// spec/tests/js/keystone-jack-chain.mjs
// SPIKE FOR #1069 (step 1): A KEYSTONE JACK IN A CLIP CAGE ON A FAPM6 IN AN
// FHD-1UBE BAY, AND A CABLE LANDED ON ITS RJ45 PORT. Four levels down:
//   enclosure bay-1 > fs/fhd-fapm6@1 > cage clip1 > jack occupant > port rj45
//   path: bay-1/module/clip1-occupant/rj45
//
// REAL: components.json (every contract in the library) and fhd-1ube.configs.json,
// built by the wrapper. STAND-INS, named as such, because the parts #1069 asks
// for do not exist and this spike adds none to library/:
//   - the FAPM6 entry gains six cages `clip1`..`clip6`, interface `keystone`,
//     which is what the build would publish once common/keystone-clip has an
//     `interface: keystone` (#1069 step 2);
//   - JACK stands for fs/keystone-rj45-cat6@1, `behaviour: occupies`,
//     `mates: keystone`, composing one std/rj45@2 port `rj45` (#1069 step 3);
//   - BLANK stands for fs/keystone-blank@1, which composes nothing.
//
// Six openings: jacks in clip1, clip3, clip5; a blank in clip2; clip4 and clip6
// left empty.
//
// A test that passes today is a plain test. One that fails today is `todo`,
// with the line of kit/rack/ports.js (or slots.js) where the walk stops; its
// diagnostics print what the call returned. Run by test_keystone_jack_chain_js.py.
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
const comps = new Map(read('components.json').components.map(c => [`${c.ns}/${c.name}@${String(c.major).replace(/^v/, '')}`, c]));

const FAPM6 = 'fs/fhd-fapm6@1', CLIP = 'common/keystone-clip@2';
const JACK = 'fs/keystone-rj45-cat6@1', BLANK = 'fs/keystone-blank@1';
const CLIPS = [1, 2, 3, 4, 5, 6].map(n => `clip${n}`);

// ── the stand-ins (#1069), laid over the real catalogue ────────────────────
const real = comps.get(FAPM6), clip = comps.get(CLIP);
assert.deepEqual(real.parts.map(q => q.id), CLIPS, 'the real FAPM6 is six clips');
assert.equal(real.cages, undefined, 'the real FAPM6 publishes no cage (#1069: the clip has no interface)');
const cage = q => ({id: q.id, interface: 'keystone', kind: 'cage', accepts: [JACK, BLANK], default: null, bores: [], at: q.at,
                    mate: [q.at[0] + clip.mate[0], q.at[1] + clip.mate[1]], media: null, lift: 0, mirror: false, rotate: null,
                    turns: null, tilt: null, 'group-states': false, 'occupant-attrs': {}});
const standIn = {
  [FAPM6]: {...real, cages: real.parts.map(cage)},
  [JACK]: {ns: 'fs', name: 'keystone-rj45-cat6', major: 'v1', kind: 'component', class: 'adapter', behaviour: 'occupies',
           mates: 'keystone', attrs: {model: 'KEYSTONE-RJ45-CAT6', media: 'rj45'}, bays: {},
           parts: [{id: 'rj45', ref: 'std/rj45@2', at: [0.35, 0.85]}],
           // what the build publishes for a composed part that declares an interface (as fs/fhd-fapm6-rj45@1's p1)
           cages: [{id: 'rj45', interface: 'rj45', kind: 'connector', accepts: ['generic/rj45-plug@1'], default: null, bores: [],
                    at: [0.35, 0.85], mate: [8.25, 7.45], media: null, lift: 0, mirror: false, rotate: null, turns: null, tilt: null,
                    'group-states': false, 'occupant-attrs': {}}]},
  [BLANK]: {ns: 'fs', name: 'keystone-blank', major: 'v1', kind: 'component', class: 'mechanical', behaviour: 'occupies',
            mates: 'keystone', attrs: {model: 'KEYSTONE-BLANK'}, bays: {}, parts: []},
};
const compByRef = ref => (ref == null ? null : standIn[String(ref).split(':')[0]] ?? comps.get(String(ref).split(':')[0]) ?? null);

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
const JACKS = ['clip1', 'clip3', 'clip5'], NOT_JACKS = ['clip2', 'clip4', 'clip6'];
const SW_END = end('mgmt', 'front', 'i2');
const json = v => JSON.stringify(v);

// ── what already works: the chain is seated in the catalogue ───────────────
test('the real FHD-1UBE bay-1 accepts the FAPM6', () => {
  const bay = cfg.bays.front.find(b => b.id === BAY);
  assert.ok(bay.accepts.includes(FAPM6), `${BAY} accepts ${FAPM6}`);
});

test('slotTree lists the FAPM6 in the bay and its six clip cages, each with what it holds', () => {
  const env = slotEnv(pp, slots, compByRef), tree = slotTree(env, pp.swaps);
  assert.equal(tree.bays.find(b => b.path === BAY).holds, FAPM6);
  const cages = tree.cages.filter(g => g.path.startsWith(`${BAY}/module/`));
  assert.deepEqual(cages.map(g => g.path), CLIPS.map(at));
  assert.deepEqual(cages.map(g => g.holds), [JACK, BLANK, JACK, null, JACK, null]);
  assert.ok(cages.every(g => g.interface === 'keystone'));
  // (slots.js:103 addCage does not go on into the occupant: the jack's rj45 is in no tree list)
  assert.equal(tree.cages.some(g => g.path.includes('-occupant')), false);
});

test('the resolver reaches the jack and its rj45 slot four levels down', () => {
  const env = slotEnv(pp, slots, compByRef), R = resolverFor(env, pp.swaps);
  assert.equal(R.refAt(`${BAY}/module`), FAPM6);
  assert.equal(R.entryAt(at('clip1')).interface, 'keystone');
  assert.equal(R.refAt(`${at('clip1')}-occupant`), JACK);
  assert.equal(R.refAt(port('clip1')), 'std/rj45@2');
  const slot = R.entryAt(port('clip1'));
  assert.equal(slot.interface, 'rj45');
  assert.equal(slot.kind, 'connector');
  assert.equal(R.entryAt(port('clip4')), null, 'nothing seated in clip4, so no slot under it');
  assert.equal(holdsAt(env, pp.swaps, at('clip4'), {...R.entryAt(at('clip4')), isCage: true}), null);
});

// ── seatedPort ─────────────────────────────────────────────────────────────
test('seatedPort folds the jack\'s port into its cage: portPathOf drops everything from the first -occupant', () => {
  // cable-rules.js:27. The jack's address and the cage's are one address to seatedPort, portFree and sameEnd,
  // so an insert with two ports (the coupler) cannot be told apart by path.
  for (const c of CLIPS) assert.deepEqual(P.seatedPort(pp, end(port(c)), ctx), P.seatedPort(pp, end(at(c)), ctx), c);
});

test('seatedPort finds the jack\'s port', {todo: 'ports.js:122 portPathOf has cut the path to bay-1/module/clip1 before the walk starts, and :143 portIn (:38) then walks the FAPM6\'s composed parts only: clip1 is mechanical and the occupant is never entered. Falls to :153-164, which answers {port: false, part: "KEYSTONE-CLIP"}'}, t => {
  const got = P.seatedPort(pp, end(port('clip1')), ctx);
  t.diagnostic(`seatedPort(${port('clip1')}) -> ${json(got)}`);
  assert.equal(got?.port, true);
  assert.equal(got.holder?.ref, FAPM6);
  assert.equal(got.info?.family, 'copper');
});

test('seatedPort says a clip with a blank or nothing in it has no port', {todo: 'ports.js:162-164 answers {port: false, part: "KEYSTONE-CLIP"} for the cage alone, the same whatever the cage holds (jack, blank or nothing); it never asks what holdsAt says is seated'}, t => {
  for (const c of NOT_JACKS) {
    const got = P.seatedPort(pp, end(port(c)), ctx);
    t.diagnostic(`seatedPort(${port(c)}) -> ${json(got)}`);
    assert.equal(got?.port, false, c);
    assert.equal(got.part, undefined, `${c}: not "a part is here"`);
  }
});

// ── cableEndPaths ──────────────────────────────────────────────────────────
test('cableEndPaths gives the jack\'s port a path and the blank and the empty clips none', {todo: 'ports.js:447-452 `under` descends comp.parts only, so it stops at the clip; :454 reads slotTree().bays and never its cages, and the cage\'s occupant is in neither'}, t => {
  const paths = P.cableEndPaths(pp, 'front', ctx).filter(p => p.startsWith(`${BAY}/`)).sort();
  t.diagnostic(`cableEndPaths(front) under ${BAY} -> ${json(paths)}`);
  assert.deepEqual(paths, JACKS.map(port));
});

// ── landing the cable ──────────────────────────────────────────────────────
test('a cable from a switch to the jack is added', () => {
  const res = apply(RACK, [{op: 'cable.add', a: SW_END, b: end(port('clip1')), media: 'cat6'}], ctx);
  assert.equal(res.error, undefined);
  assert.equal(res.rack.cables.length, 1);
});

test('a cable end on the jack lands as a copper port', {todo: 'settleEnd (ports.js:567, :577) takes seatedPort\'s {port: false, part} (:164) and lays it over the page\'s: the end reads "takes no plug or lug the library knows"'}, t => {
  const page = {facts: {item: true, drawing: true, port: false, cage: false, occupied: false, holder: null}, info: null, reason: 'no port'};
  const settled = P.settleEnd(RACK, end(port('clip1')), page, ctx);
  t.diagnostic(`settleEnd(${port('clip1')}) -> ${json(settled)}`);
  assert.equal(settled?.facts?.port, true);
  assert.equal(settled.info?.family, 'copper');
});

test('a cable end on a blank or an empty clip is refused when it is added', {todo: 'seatedEndReason (ports.js:198) skips an answer with `part` set (a part at the path that takes no cable is "the page\'s to call loose"), so the end is kept unchecked, jack or not'}, t => {
  for (const c of NOT_JACKS) {
    const res = apply(RACK, [{op: 'cable.add', a: SW_END, b: end(port(c)), media: 'cat6'}], ctx);
    t.diagnostic(`cable.add to ${port(c)} -> ${json(res.error ?? 'accepted')}`);
    assert.match(res.error ?? '', /has no port/, c);
  }
});

// ── the agent's free-port answer for the six openings ──────────────────────
// A page's reader hands in each port it drew, by path or as the drawing's element id
// (`bay-1--module--clip1-occupant--rj45`, cable-rules.js isElementId).
const elementId = p => p.split('/').join('--');
const reader = spell => async (item, view) => (view === 'front' ? JACKS.map(c => ({cls: 'port', path: spell(port(c)), media: 'rj45'})) : []);
const freeFront = async portsOf => (await Q.freePorts(RACK, 'i1', {...ctx, portsOf})).filter(f => f.view === 'front').map(f => f.path).sort();

test('free ports, from a reader that hands in the jacks\' paths: the three jacks, on the reader\'s word alone', async () => {
  assert.deepEqual(await freeFront(reader(p => p)), JACKS.map(port));
});

test('free ports, from a reader that hands in the jacks\' element ids, are the three jacks', {todo: 'queries.js:324 asks seatedPort about the address the id stands for and drops the id when `.port` is not true (ports.js:164 says false)'}, async t => {
  const got = await freeFront(reader(elementId));
  t.diagnostic(`freePorts(front), element ids -> ${json(got)}`);
  assert.deepEqual(got, JACKS.map(port));
});

test('free ports offer nothing for the blank and the empty clips, and nothing without a reader', async () => {
  const got = await freeFront(reader(p => p));
  for (const c of NOT_JACKS) assert.equal(got.some(p => p.includes(`/${c}`)), false, c);
  assert.deepEqual(await freeFront(async () => []), [], 'with no reader the catalogue lists no data port (queries.js:303)');
});
