import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import * as G from '../../../kit/rack/managers.js';

const SIZES = {'as7726-32x': {ru: 1, h: 43.5, d: 515}, 'r740xd': {ru: 2, h: 86.8, d: 737.5},
               'fhd-cmp5dr': {ru: 1, h: 44, d: 110, mount: 'rack-face', shell: 'sheet'},
               'tm-280': {ru: 1, h: 43.6, d: 140.5}, 'deep-1u': {ru: 1, h: 44, d: 760}};
const chassisOf = ref => SIZES[ref] || null;
const add = (rack, ref, ru, extra = {}) => M.withItem(rack, {ref, cfg: 'x', ru, label: extra.label ?? ref, ...extra}).rack;

test('placement: on a device on that face it attaches; elsewhere it stands alone', () => {
  const r = add(M.newRack(), 'r740xd', 10, {label: 'srv'});
  assert.deepEqual(G.placement(r, {face: 'front', ru: 11}, chassisOf), {face: 'front', ru: 11, on: 'i1', unit: 2});
  assert.deepEqual(G.placement(r, {face: 'rear', ru: 11}, chassisOf), {face: 'rear', ru: 11});
  assert.deepEqual(G.placement(r, {face: 'front', ru: 12}, chassisOf), {face: 'front', ru: 12});
});

test('placement never hosts a manager on another manager', () => {
  const r = add(M.newRack(), 'fhd-cmp5dr', 10);
  assert.equal(G.hostAt(r, 'front', 10, chassisOf), null);
});

test('moveItem: a host carries its managers, both of a 2U host by one U', () => {
  let r = add(M.newRack(), 'r740xd', 10, {label: 'srv'});
  r = add(r, 'fhd-cmp5dr', 10, {on: 'i1', unit: 1});
  r = add(r, 'fhd-cmp5dr', 11, {on: 'i1', unit: 2});
  const m = G.moveItem(r, 'i1', {ru: 11}, chassisOf);
  assert.equal(m.ok, true);
  assert.deepEqual(m.rack.items.map(i => i.ru), [11, 11, 12]);
});

test('moveItem: a host is refused when a manager of its would collide, and nothing changes', () => {
  let r = add(M.newRack(), 'as7726-32x', 10, {label: 'leaf'});
  r = add(r, 'fhd-cmp5dr', 10, {on: 'i1', unit: 1, label: 'mgr-a'});
  r = add(r, 'fhd-cmp5dr', 20, {label: 'mgr-b'});
  const m = G.moveItem(r, 'i1', {ru: 20}, chassisOf);
  assert.deepEqual(m, {ok: false, reason: 'mgr-a moves with it: Taken by mgr-b on the front.'});
});

test('moveItem: a manager dropped on a device attaches, and dropped on empty space detaches', () => {
  let r = add(M.newRack(), 'as7726-32x', 10);
  r = add(r, 'fhd-cmp5dr', 30);
  const on = G.moveItem(r, 'i2', {ru: 10, face: 'front'}, chassisOf);
  assert.deepEqual([on.rack.items[1].on, on.rack.items[1].unit], ['i1', 1]);
  const off = G.moveItem(on.rack, 'i2', {ru: 5}, chassisOf);
  assert.equal('on' in off.rack.items[1], false);
});

test('settleManagers: a missing host detaches; a stale ru follows the host; a non-manager loses on', () => {
  const rack = {...M.newRack(), items: [
    {id: 'i1', ref: 'as7726-32x', cfg: 'x', label: 'leaf', ru: 12, face: 'front', turned: false, swaps: {}, fields: {}},
    {id: 'i2', ref: 'fhd-cmp5dr', cfg: 'x', label: 'mgr-1', ru: 9, face: 'front', turned: false, swaps: {}, fields: {}, on: 'i1', unit: 1},
    {id: 'i3', ref: 'fhd-cmp5dr', cfg: 'x', label: 'mgr-2', ru: 30, face: 'front', turned: false, swaps: {}, fields: {}, on: 'i9', unit: 1},
    {id: 'i4', ref: 'r740xd', cfg: 'x', label: 'srv', ru: 1, face: 'front', turned: false, swaps: {}, fields: {}, on: 'i1', unit: 1}]};
  const {rack: s, notices} = G.settleManagers(rack, chassisOf);
  assert.equal(s.items[1].ru, 12);
  assert.equal('on' in s.items[2], false);
  assert.equal('on' in s.items[3], false);
  assert.deepEqual(notices, [
    'mgr-1 was out of step with leaf, so it moved to U12 with it.',
    'mgr-2: the device it was on is not in this rack, so it stays at U30 on its own.',
    'srv is not a cable manager, so it is not on another device.']);
});

test('moveItem: a host flipped to the other face is not refused by its own managers (two-post)', () => {
  let r = add(M.newRack({kind: 'two-post'}), 'tm-280', 5, {label: 'tm'});
  r = add(r, 'fhd-cmp5dr', 5, {on: 'i1', unit: 1, label: 'mgr'});
  const m = G.moveItem(r, 'i1', {face: 'rear'}, chassisOf);
  assert.equal(m.ok, true);
  assert.deepEqual(m.rack.items.map(i => i.face), ['rear', 'rear']);
});

test('moveItem: a 760 mm host flipped to the rear carries its manager (four-post)', () => {
  let r = add(M.newRack(), 'deep-1u', 5, {label: 'deep'});
  r = add(r, 'fhd-cmp5dr', 5, {on: 'i1', unit: 1, label: 'mgr'});
  const m = G.moveItem(r, 'i1', {face: 'rear'}, chassisOf);
  assert.equal(m.ok, true);
  assert.deepEqual(m.rack.items.map(i => i.face), ['rear', 'rear']);
});

test('moveItem: a flip is still refused when a manager of its would collide', () => {
  let r = add(M.newRack(), 'as7726-32x', 10, {label: 'leaf'});
  r = add(r, 'fhd-cmp5dr', 10, {on: 'i1', unit: 1, label: 'mgr-a'});
  r = add(r, 'fhd-cmp5dr', 10, {face: 'rear', label: 'mgr-b'});
  assert.deepEqual(G.moveItem(r, 'i1', {face: 'rear'}, chassisOf),
    {ok: false, reason: 'mgr-a moves with it: Taken by mgr-b on the rear.'});
});

test('settleManagers: an item whose chassis is unknown is left untouched, with no notice', () => {
  const rack = {...M.newRack(), items: [
    {id: 'i1', ref: 'as7726-32x', cfg: 'x', label: 'leaf', ru: 12, face: 'front', turned: false, swaps: {}, fields: {}},
    {id: 'i2', ref: 'gone-part', cfg: 'x', label: 'mystery', ru: 12, face: 'front', turned: false, swaps: {}, fields: {}, on: 'i1', unit: 1}]};
  const {rack: s, notices} = G.settleManagers(rack, chassisOf);
  assert.deepEqual(s.items[1], rack.items[1]);
  assert.deepEqual(notices, []);
});

test('settleManagers: a host on the other face says so, not that it is missing', () => {
  const rack = {...M.newRack(), items: [
    {id: 'i1', ref: 'as7726-32x', cfg: 'x', label: 'leaf', ru: 12, face: 'rear', turned: false, swaps: {}, fields: {}},
    {id: 'i2', ref: 'fhd-cmp5dr', cfg: 'x', label: 'mgr', ru: 12, face: 'front', turned: false, swaps: {}, fields: {}, on: 'i1', unit: 1}]};
  const {rack: s, notices} = G.settleManagers(rack, chassisOf);
  assert.equal('on' in s.items[1], false);
  assert.deepEqual(notices, ['mgr: leaf is on the rear, so it stays at U12 on its own.']);
});
