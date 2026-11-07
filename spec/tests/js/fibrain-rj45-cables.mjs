// spec/tests/js/fibrain-rj45-cables.mjs
// THE FIBRAIN HD RJ45 MODULES SEATED IN THEIR HOLDERS IN THE 1U FRAME (#1041), against
// the rack kit, built from the real components.json, rack.json and xpu.configs.json
// under PORTRAYAL_DIST (library/dist).
//
// Held here: a module seats in each of the six positions of a holder seated in a slot
// of the frame (the example build `copper-mixed`, and by a swap in a bare frame), the
// kit answers `seatedPort` for its jack as a copper port on the front, a cable from a
// switch's RJ45 port to it is accepted and routes, and a made-up position, the rear
// face and an empty position are refused or offer no port.
//
// Run by test_fibrain_rj45_holders.py, which names the build in PORTRAYAL_DIST.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as M from '../../../kit/rack/model.js';
import * as R from '../../../kit/rack/route.js';
import * as P from '../../../kit/rack/ports.js';
import {apply} from '../../../kit/rack/commands.js';
import {redirectsOf} from '../../../kit/redirects.js';

const DIST = process.env.PORTRAYAL_DIST;
assert.ok(DIST, 'PORTRAYAL_DIST names the build directory (library/dist)');
const read = name => JSON.parse(fs.readFileSync(`${DIST}/${name}`, 'utf8'));
const components = read('components.json').components;
const comps = new Map(components.map(c => [`${c.ns}/${c.name}@${String(c.major).replace(/^v/, '')}`, c]));
const compByRef = ref => (ref == null ? null : comps.get(String(ref).split(':')[0]) ?? null);
const redirects = redirectsOf(components);
const devices = read('rack.json').devices;
const cfgFile = read('xpu.configs.json');
const slots = {default: cfgFile.default, 'pdu-class': cfgFile['pdu-class'], bays: cfgFile.bays, cages: cfgFile.cages, configs: cfgFile.configs};
const SW = {default: 'base', 'pdu-class': null, bays: {front: [], rear: []}, cages: {front: [], rear: []},
            configs: [{name: 'base', description: '', airflow: 'front-to-back', bays: {}, occupants: {}}]};
const SWSIZE = {ru: 1, w: 438, h: 43.6, d: 400, model: 'SW', manufacturer: 'Acme', kind: 'switch', configs: ['base'], default: 'base'};
const chassisOf = ref => (ref === 'sw' ? SWSIZE : devices[ref] ?? null);
const ctx = {chassisOf, slotsOf: ref => (ref === 'sw' ? SW : ref === 'xpu' ? slots : null), compByRef, redirects};

const MODULES = ['xe100', 'xe110', 'xe200', 'xe210', 'xq100', 'xq110', 'xq200', 'xq210', 'xr100', 'xr110', 'xr200', 'xr210'].map(m => `fibrain/${m}@1`);
const add = (rack, ref, ru, extra) => M.withItem(rack, {ref, cfg: 'base', ru, label: ref, ...extra}).rack;
const SEATED = add(add(M.newRack(), 'xpu', 30, {cfg: 'copper-mixed', label: 'frame'}), 'sw', 20, {label: 'sw-1'});
const frame = SEATED.items.find(i => i.ref === 'xpu');
const swItem = SEATED.items.find(i => i.ref === 'sw');
const end = (item, path, view = 'front') => ({item: item.id, path, view});
const JACK = (slot, pos) => `slot-${slot}/module/pos-${pos}/module/jack`;

const SLOTS = [1, 2, 3, 4, 5, 6, 7, 8];
const HOLDERS = {'copper-mixed': null, 'xpu00-copper': 'fibrain/xmu00@1', 'xps00-copper': 'fibrain/xms00@1'};

test('the copper examples seat a holder in all eight slots with six modules each, as the manifest says', () => {
  for (const name of Object.keys(HOLDERS)) {
    const cfg = cfgFile.configs.find(c => c.name === name);
    assert.ok(cfg, `${name} is a configuration of the frame`);
    const seated = Object.entries(cfg.bays).filter(([k]) => k.includes('/'));
    assert.equal(seated.length, 48, name);
    for (const [, ref] of seated) assert.ok(MODULES.includes(ref), ref);
    for (const s of SLOTS) {
      const want = HOLDERS[name] ?? (s % 2 ? 'fibrain/xms00@1' : 'fibrain/xmu00@1');
      assert.equal(cfg.bays[`slot-${s}`], want, `${name} slot-${s}`);
    }
  }
});

test('the orderable frames and the base ship empty', () => {
  for (const name of ['base', 'xpu00', 'xps00']) {
    const cfg = cfgFile.configs.find(c => c.name === name);
    assert.ok(cfg, name);
    assert.deepEqual(Object.keys(cfg.bays ?? {}), [], name);
  }
});

test('every seated module\'s jack is a copper port on the front, in its holder, in its slot', () => {
  let n = 0;
  for (const slot of SLOTS) for (const pos of [1, 2, 3, 4, 5, 6]) {
    const got = P.seatedPort(frame, end(frame, JACK(slot, pos)), ctx);
    assert.equal(got?.port, true, `${JACK(slot, pos)}`);
    assert.equal(got.onView, 'front');
    assert.equal(got.back, false);
    assert.equal(got.info.family, 'copper');
    assert.equal(got.holder.path, `slot-${slot}/module/pos-${pos}`);
    assert.ok(MODULES.includes(got.holder.ref), got.holder.ref);
    n++;
  }
  assert.equal(n, 48);
});

test('the kit lists the 48 jacks as cable ends of the frame\'s front', () => {
  const paths = P.cableEndPaths(frame, 'front', ctx).filter(p => p.endsWith('/jack')).sort();
  const want = SLOTS.flatMap(s => [1, 2, 3, 4, 5, 6].map(p => JACK(s, p))).sort();
  assert.deepEqual(paths, want);
});

test('a module swapped into a bare frame seats the same way, every module in every position', () => {
  for (const [holder, slot] of [['fibrain/xmu00@1', 1], ['fibrain/xms00@1', 8]]) {
    for (const ref of MODULES) for (const pos of [1, 2, 3, 4, 5, 6]) {
      const swaps = {[`slot-${slot}`]: holder, [`slot-${slot}/module/pos-${pos}`]: ref};
      const rack = add(M.newRack(), 'xpu', 30, {label: 'bare', swaps});
      const it = rack.items[0];
      const got = P.seatedPort(it, end(it, JACK(slot, pos)), ctx);
      assert.equal(got?.port, true, `${holder} ${ref} pos-${pos}`);
      assert.equal(got.info.family, 'copper');
      // the next position, with nothing seated, offers no port
      const other = pos === 6 ? 5 : pos + 1;
      assert.notEqual(P.seatedPort(it, end(it, JACK(slot, other)), ctx)?.port, true, `pos-${other} is empty`);
    }
  }
});

test('a cable from a switch RJ45 port to a seated module is accepted, lands as copper and routes', () => {
  const sw = end(swItem, 'mgmt'), jack = end(frame, JACK(1, 3));
  const res = apply(SEATED, [{op: 'cable.add', a: sw, b: jack, media: 'cat6a'}], ctx);
  assert.equal(res.error, undefined);
  const rack = res.rack, c = rack.cables[0];
  const page = {facts: {item: true, drawing: true, port: false, cage: false, occupied: false, holder: null}, info: null, reason: 'no port'};
  const settled = P.settleEnd(rack, jack, page, ctx);
  assert.equal(settled.facts.port, true);
  assert.equal(settled.info.family, 'copper');
  const rc = {chassisOf, guidesOf: () => [], portX: () => -150, bendOf: () => 1e12};
  assert.ok(R.autoRoute(rack, c, rc).length >= 1, 'a route was found');
});

test('a cable lands on the last jack of the last slot, slot-8/pos-6', () => {
  const jack = end(frame, JACK(8, 6));
  assert.equal(jack.path, 'slot-8/module/pos-6/module/jack');
  const res = apply(SEATED, [{op: 'cable.add', a: end(swItem, 'mgmt'), b: jack, media: 'cat6a'}], ctx);
  assert.equal(res.error, undefined);
  const settled = P.settleEnd(res.rack, jack, {facts: {item: true, drawing: true, port: false, cage: false, occupied: false, holder: null}, info: null, reason: 'no port'}, ctx);
  assert.equal(settled.facts.port, true);
  assert.equal(settled.info.family, 'copper');
});

test('a made-up position, an empty slot and the back of a jack are not ports', () => {
  assert.notEqual(P.seatedPort(frame, end(frame, JACK(1, 7)), ctx)?.port, true, 'pos-7');
  const bare = add(M.newRack(), 'xpu', 40, {label: 'bare'}).items[0];
  assert.notEqual(P.seatedPort(bare, end(bare, JACK(3, 1)), ctx)?.port, true, 'slot-3 of the bare frame holds nothing');
  // no IDC rear is modelled: the jack is on the front only
  assert.notEqual(P.seatedPort(frame, end(frame, JACK(1, 1), 'rear'), ctx)?.port, true, 'jack on the rear');
  // a made-up port on a module that is seated is refused when the cable is added, as the kit refuses it for any part
  const refused = apply(SEATED, [{op: 'cable.add', a: end(swItem, 'mgmt'), b: end(frame, `slot-1/module/pos-1/module/jack9`), media: 'cat6a'}], ctx);
  assert.match(refused.error ?? '', /has no port jack9/);
});
