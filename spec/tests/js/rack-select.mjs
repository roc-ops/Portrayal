// spec/tests/js/rack-select.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import {selectCables, NO_FACTS} from '../../../kit/rack/queries.js';
import {GONE} from '../../../kit/rack/commands.js';

const end = (item, path = 'port-1', view = 'front') => ({item, path, view});
const cable = (id, a, b, extra = {}) => ({id, a, b, media: '', purpose: '', label: '', route: [], ...extra});
let R = M.newRack();
for (const ru of [10, 20]) R = M.withItem(R, {ref: 'leaf', cfg: 'base', ru, label: `leaf-${ru}`}).rack;
R = {...R, cables: [
  cable('c1', end('i1'), end('i2'), {purpose: 'uplink', media: 'om4'}),
  cable('c2', end('i1', 'port-2-occupant/tx'), end('i2', 'port-2'), {purpose: 'uplink', media: 'os2'}),
  cable('c3', end('i1', 'port-1', 'rear'), end('i9', 'port-1'), {purpose: 'management', media: 'cat6a'})]};
const facts = async () => ({ends: new Map([['i9|front|port-1', {reason: 'the device was removed'}]])});

test('selectCables: by item, by port on either panel or one, and a port spelled through its optic', async () => {
  assert.deepEqual(await selectCables(R, {item: 'i1'}), {ids: ['c1', 'c2', 'c3']});
  assert.deepEqual(await selectCables(R, {item: 'i1', path: 'port-1'}), {ids: ['c1', 'c3']});
  assert.deepEqual(await selectCables(R, {item: 'i1', path: 'port-1', view: 'rear'}), {ids: ['c3']});
  assert.deepEqual(await selectCables(R, {item: 'i1', path: 'port-2'}), {ids: ['c2']});
  assert.deepEqual(await selectCables(R, {item: 'i2', path: 'port-2-occupant'}), {ids: ['c2']});
});

test('selectCables: by purpose, by media, and both narrowing together', async () => {
  assert.deepEqual(await selectCables(R, {purpose: 'uplink'}), {ids: ['c1', 'c2']});
  assert.deepEqual(await selectCables(R, {media: 'cat6a'}), {ids: ['c3']});
  assert.deepEqual(await selectCables(R, {item: 'i2', purpose: 'uplink', media: 'os2'}), {ids: ['c2']});
});

test('selectCables: loose ends need the cable facts', async () => {
  assert.deepEqual(await selectCables(R, {loose: true}, {cableFacts: facts}), {ids: ['c3']});
  assert.deepEqual(await selectCables(R, {loose: true}), {error: NO_FACTS});
});

test('selectCables: an empty result is not an error; a removed device with loose cables still answers', async () => {
  assert.deepEqual(await selectCables(R, {purpose: 'storage'}), {ids: []});
  assert.deepEqual(await selectCables(R, {item: 'i2', path: 'port-48'}), {ids: []});
  assert.deepEqual(await selectCables(R, {item: 'i9'}), {ids: ['c3']});
});

test('selectCables: a purpose or media of null, empty or not a string is refused, not a match for every cable', async () => {
  for (const s of [{media: null}, {purpose: null}, {media: ''}, {purpose: 3}, {media: ['om4']}, {item: null}, {item: 'i1', path: null}]) {
    const got = await selectCables(R, s);
    assert.ok(got.error && !got.ids, JSON.stringify(s));
  }
  assert.deepEqual(await selectCables(R, {media: null}), {error: "A selector's media is a name; leave it out rather than send null."});
  assert.deepEqual(await selectCables(R, {item: 'i7'}), {error: GONE});
});

test('selectCables: a selector it cannot read is refused with a sentence', async () => {
  assert.deepEqual(await selectCables(R, {}), {error: 'A selector names an item, loose: true, a purpose, a media or a bundle.'});
  assert.deepEqual(await selectCables(R, null), {error: 'A selector names an item, loose: true, a purpose, a media or a bundle.'});
  assert.deepEqual(await selectCables(R, {label: 'A1'}), {error: 'A selector does not take label.'});
  assert.deepEqual(await selectCables(R, {path: 'port-1'}), {error: 'A selector with a path needs its item.'});
  assert.deepEqual(await selectCables(R, {loose: false}), {error: 'A selector takes loose: true, or leaves it out.'});
});

test('selectCables: loose with unchecked ends says so', async () => {
  const partial = async () => ({unchecked: true, ends: new Map([['i9|front|port-1', {reason: 'the device was removed'}]])});
  assert.deepEqual(await selectCables(R, {loose: true}, {cableFacts: partial}), {ids: ['c3'], unchecked: true});
});
