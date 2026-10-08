// spec/tests/js/rack-inspect.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import {inspect} from '../../../kit/rack/queries.js';
import {GONE, CABLE_GONE} from '../../../kit/rack/commands.js';
import {ctx, chassisOf} from './slot-fixtures.mjs';

const CFG = {leaf: 'base', pp: 'loaded', mgr: 'base'};
const add = (rack, ref, ru, extra = {}) => M.withItem(rack, {ref, cfg: CFG[ref], ru, label: ref, ...extra}).rack;
const end = (item, path = 'port-1', view = 'front') => ({item, path, view});
const cable = (id, a, b, extra = {}) => ({id, a, b, media: '', purpose: '', label: '', route: [], ...extra});

test('inspect: an item without slots says they were not loaded, and still lists its cables', async () => {
  let r = add(add(M.newRack(), 'leaf', 10, {label: 'leaf-1'}), 'leaf', 20, {label: 'leaf-2'});
  r = {...r, cables: [cable('c1', end('i1'), end('i2', 'port-2'))]};
  const got = await inspect(r, 'i1', {chassisOf});
  assert.deepEqual(got, {kind: 'item', id: 'i1', ref: 'leaf', model: 'Leaf-48', manufacturer: 'Acme', label: 'leaf-1', cfg: 'base',
    configs: [{name: 'base', description: '', airflow: null}, {name: 'dc', description: '', airflow: null}],
    ru: 10, u: 1, face: 'front', turned: false, on: null, unit: null, managers: [], slots: 'not loaded',
    cables: [{id: 'c1', end: 'a', path: 'port-1', view: 'front', other: 'i2/port-2'}]});
});

test('inspect: an item with slots lists its bays, cages and fields, with what each holds', async () => {
  const r = add(M.newRack(), 'leaf', 10, {label: 'leaf-1', swaps: {'port-2': 'acme/lr@1'}, fields: {'port-1-occupant': {'pull-tab': 'blue'}}});
  const got = await inspect(r, 'i1', ctx);
  assert.equal('slots' in got, false);
  assert.deepEqual(got.configs[0], {name: 'base', description: 'AC power', airflow: 'front-to-back'});
  assert.deepEqual(got.bays, [{path: 'psu-1', view: 'rear', group: 'psus', holds: 'acme/psu-ac@1', default: 'acme/psu-ac@1',
    accepts: [{ref: 'acme/psu-ac@1', name: 'AC power supply', kind: 'psu'}, {ref: 'acme/psu-dc@1', name: 'DC power supply', kind: 'psu'}]}]);
  // port-1 holds what the configuration builds; port-2 the item's own swap
  assert.deepEqual(got.cages.map(g => [g.path, g.view, g.interface, g.holds, g.default]),
    [['port-1', 'front', 'sfp', 'acme/sr@1', null], ['port-2', 'front', 'sfp', 'acme/lr@1', null]]);
  assert.deepEqual(got.cages[0].accepts.map(a => a.ref), ['acme/sr@1', 'acme/lr@1', 'acme/dac@1']);
  assert.deepEqual(got.fields, [
    {path: 'port-1-occupant', key: 'pull-tab', type: 'choice', value: 'blue', default: 'black', choices: ['blue', 'black']},
    {path: 'port-1-occupant', key: 'label', type: 'text', value: '', default: ''}]);
});

test('inspect: a bay lists the slots on what it holds, and a swapped carrier holds its defaults', async () => {
  const r = add(M.newRack(), 'pp', 5, {label: 'pp-1', swaps: {'bay-2': 'acme/carrier@1'}});
  const got = await inspect(r, 'i1', ctx);
  assert.deepEqual(got.bays.map(b => [b.path, b.holds]),
    [['bay-1', 'acme/lc6@1'], ['bay-2', 'acme/carrier@1'], ['bay-2/module/sub-1', null]]);
  assert.deepEqual(got.cages.map(g => [g.path, g.interface]), [['bay-1/module/lc1', 'lc-duplex'], ['bay-1/module/lc2', 'lc-duplex']]);
  assert.deepEqual(got.fields.map(f => [f.path, f.key, f.value]), [['bay-1/module', 'latch-color', 'blue']]);
});

test('inspect: a device whose parts list did not load reads as not loaded', async () => {
  const r = add(M.newRack(), 'leaf', 10);
  const got = await inspect(r, 'i1', {...ctx, slotsOf: () => null});
  assert.equal(got.slots, 'not loaded');
});

test('inspect: an id that is not in the rack', async () => {
  assert.deepEqual(await inspect(M.newRack(), 'i4', ctx), {error: GONE});
  assert.deepEqual(await inspect(M.newRack(), 'c4', ctx), {error: CABLE_GONE});
});

test('inspect: an item whose configuration the parts list no longer has reads as the default one', async () => {
  const r = add(M.newRack(), 'leaf', 10, {cfg: 'gone'});
  const got = await inspect(r, 'i1', ctx);
  assert.equal(got.cfg, 'gone');
  assert.deepEqual(got.cages.map(g => [g.path, g.holds]), [['port-1', 'acme/sr@1'], ['port-2', null]]);
});
