// spec/tests/js/rack-only-in.mjs
// A BAY OF SOME CONFIGURATIONS ONLY (#1022): configs.json publishes `only-in`
// on a bay or cage entry as device.yaml states it, and the kit reads a slot
// whose list leaves out the item's configuration as no slot at all.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import {COMMANDS, apply} from '../../../kit/rack/commands.js';
import {slotEnv, slotTree, holdsAt} from '../../../kit/rack/slots.js';
import * as P from '../../../kit/rack/ports.js';
import {ctx, PANEL, PANEL_OM4} from './rear-ports-fixture.mjs';

void COMMANDS;
const end = (path, view = 'front') => ({item: 'i1', path, view});
const itemIn = cfg => M.withItem(M.newRack(), {ref: 'pp', cfg, ru: 30, label: 'pp-1'}).rack.items[0];
const slots = ctx.slotsOf('pp');
const envOf = item => slotEnv(item, slots, ctx.compByRef);

test('holdsAt: a bay whose only-in leaves out the configuration holds nothing, whatever its default or the swaps', () => {
  const item = itemIn('panels');
  const env = envOf(item);
  const gone = slots.bays.front.find(b => b.id === 'bay-9');
  assert.deepEqual(gone['only-in'], ['base']);
  assert.equal(holdsAt(env, {}, 'bay-9', gone), null);
  // a swap naming it is not honoured into a configuration that lacks it
  assert.equal(holdsAt(env, {'bay-9': PANEL_OM4}, 'bay-9', gone), null);
  // nor is anything beneath it
  assert.equal(holdsAt(env, {'bay-9/module/sub-1': PANEL_OM4}, 'bay-9/module/sub-1', {id: 'sub-1', default: PANEL}), null);
});

test('holdsAt: in a configuration that has the bay it gives what it gave before', () => {
  const item = itemIn('base');
  const env = envOf(item);
  const bay9 = slots.bays.front.find(b => b.id === 'bay-9');
  assert.equal(holdsAt(env, {}, 'bay-9', bay9), PANEL);
  assert.equal(holdsAt(env, {'bay-9': PANEL_OM4}, 'bay-9', bay9), PANEL_OM4);
  // a bay that states no only-in is a bay of every configuration
  const bay8 = slots.bays.front.find(b => b.id === 'bay-8');
  assert.equal(bay8['only-in'], undefined);
  for (const cfg of ['panels', 'base']) assert.equal(holdsAt(envOf(itemIn(cfg)), {}, 'bay-8', bay8), PANEL);
});

test('the slot tree lists the bays of the configuration only', () => {
  const ids = cfg => slotTree(envOf(itemIn(cfg)), {}).bays.map(b => b.path);
  assert.equal(ids('panels').includes('bay-9'), false);
  assert.equal(ids('base').includes('bay-9'), true);
  assert.equal(ids('panels').includes('bay-7'), true);
  assert.equal(ids('base').includes('bay-7'), false);
});

test('fit refuses a bay the configuration does not have, as it does any path that is no bay', () => {
  const rack = M.withItem(M.newRack(), {ref: 'pp', cfg: 'panels', ru: 30, label: 'pp-1'}).rack;
  const got = apply(rack, [{op: 'fit', id: 'i1', path: 'bay-9', ref: PANEL_OM4}], ctx);
  assert.match(JSON.stringify(got), /bay-9 is not a bay or cage/);
  const ok = apply(M.withItem(M.newRack(), {ref: 'pp', cfg: 'base', ru: 30, label: 'pp-1'}).rack, [{op: 'fit', id: 'i1', path: 'bay-9', ref: PANEL_OM4}], ctx);
  assert.deepEqual(ok.rack.items[0].swaps, {'bay-9': PANEL_OM4});
});

test('seatedPort answers for a bay left to its default in a configuration that has it', () => {
  // bay-8 states no only-in and the configuration does not list it
  assert.equal(P.seatedPort(itemIn('panels'), end('bay-8/module/lc01'), ctx).port, true);
  assert.equal(P.seatedPort(itemIn('panels'), end('bay-8/module/b01', 'rear'), ctx).port, true);
  // bay-7 is a bay of `panels` by its list
  assert.equal(P.seatedPort(itemIn('panels'), end('bay-7/module/lc01'), ctx).port, true);
  assert.equal(P.seatedPort(itemIn('base'), end('bay-9/module/lc01'), ctx).port, true);
});

test('seatedPort says nothing for a bay the configuration does not have, swapped or not', () => {
  assert.equal(P.seatedPort(itemIn('panels'), end('bay-9/module/lc01'), ctx), null);
  assert.equal(P.seatedPort(itemIn('base'), end('bay-7/module/lc01'), ctx), null);
  const swapped = {...itemIn('panels'), swaps: {'bay-9': PANEL_OM4}};
  assert.equal(P.seatedPort(swapped, end('bay-9/module/lc01'), ctx), null);
  assert.equal(P.seatedPort(swapped, end('bay-9/module/lc01'), ctx, {seen: true}), null);
});
