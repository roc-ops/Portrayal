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

const ROUTE = {chassisOf, guidesOf: () => [], portX: () => -100};

test('inspect: a cable, with its routed length from a route context', async () => {
  let r = add(add(M.newRack(), 'leaf', 10, {label: 'leaf-1'}), 'leaf', 20, {label: 'leaf-2'});
  r = add(r, 'mgr', 20, {label: 'ring', on: 'i2', unit: 1});
  r = {...r, cables: [cable('c1', end('i1'), end('i2'), {media: 'om4', purpose: 'uplink', label: 'A1', length: {value: 2, unit: 'm', source: 'entered'}})]};
  const got = await inspect(r, 'c1', {chassisOf, route: ROUTE});
  assert.deepEqual(got, {kind: 'cable', id: 'c1',
    a: {item: 'i1', path: 'port-1', view: 'front', name: 'leaf-1 (U10) port-1'},
    b: {item: 'i2', path: 'port-1', view: 'front', name: 'leaf-2 (U20) port-1'},
    media: 'om4', purpose: 'uplink', label: 'A1', length: {value: 2, unit: 'm', source: 'entered'},
    routed: {metres: 1.09, stock: 1.5}, slack: {metres: 0.91},
    route: {edited: false, waypoints: [{lane: 'left-front', ru: 10}, {lane: 'left-front', ru: 20}], text: 'left-front U10-U20'},
    lanes: ['left-front', 'right-front', 'left-rear', 'right-rear'],
    passes: {i3: ['guide-1', 'guide-2', 'window-1']},
    loose: null, mismatch: null});
});

test('inspect: a hand-made route without a route context, and loose ends and media from the cable facts', async () => {
  let r = add(add(M.newRack(), 'leaf', 10, {label: 'leaf-1'}), 'pp', 20, {label: 'pp-1'});
  const route = [{lane: 'right-front', ru: 12}, {lane: 'right-front', ru: 18}];
  r = {...r, cables: [cable('c1', end('i1'), end('i2', 'bay-1/module/lc1'), {media: 'os2', route, routeEdited: true})]};
  const copper = {family: 'copper', mode: null};
  const cableFacts = async (_rack, ends) => {
    assert.deepEqual(ends, [end('i1'), end('i2', 'bay-1/module/lc1')]);
    return {ends: new Map([['i1|front|port-1', {info: copper, reason: null}],
                           ['i2|front|bay-1/module/lc1', {info: null, reason: 'bay-1/module/lc1 holds no optic'}]])};
  };
  const got = await inspect(r, 'c1', {chassisOf, cableFacts});
  assert.equal(got.routed, null);
  assert.deepEqual(got.route, {edited: true, waypoints: route, text: 'right-front U12-U18'});
  assert.deepEqual(got.passes, {i2: ['guide-1']});
  assert.deepEqual(got.loose, [{end: 'b', reason: 'bay-1/module/lc1 holds no optic'}]);
  assert.deepEqual(got.mismatch, ['OS2 single-mode fiber does not suit end A, which is copper.']);
});

test('inspect: a route context that throws leaves the cable unmeasured', async () => {
  let r = add(add(M.newRack(), 'leaf', 10), 'leaf', 20);
  r = {...r, cables: [cable('c1', end('i1'), end('i2'))]};
  const got = await inspect(r, 'c1', {chassisOf, route: {...ROUTE, portX: () => { throw new Error('no drawing'); }}});
  assert.equal(got.routed, null);
  assert.deepEqual(got.route.waypoints, []);
});

test('inspect: a cable-facts reader that rejects leaves the ends unchecked, not an error', async () => {
  let r = add(add(M.newRack(), 'leaf', 10), 'leaf', 20);
  r = {...r, cables: [cable('c1', end('i1'), end('i2'))]};
  const got = await inspect(r, 'c1', {chassisOf, cableFacts: async () => { throw new Error('no drawing'); }});
  assert.equal(got.kind, 'cable');
  assert.equal(got.unchecked, true);
  assert.equal(got.loose, null);
  assert.equal(got.mismatch, null);
  const fine = await inspect(r, 'c1', {chassisOf, cableFacts: async () => ({ends: new Map()})});
  assert.equal('unchecked' in fine, false);
});
