import test from 'node:test';
import assert from 'node:assert/strict';

// jdist resolves a url against location.href and fetches it: stand both in.
globalThis.location = {href: 'https://page.test/', search: ''};
const asked = [];
let body = {format: 1, devices: {}};
globalThis.fetch = async url => { asked.push(url); return {ok: true, json: async () => body}; };

const {loadCatalog, chassisLookup, catalogEntries} = await import('../../../kit/rack/catalog.js');
const {clearDistCache} = await import('../../../kit/dist.js');

const DEVICES = {
  'tm-280': {manufacturer: 'BATM', model: 'TM-280', ru: 1},
  'as7726-32x': {manufacturer: 'Edgecore', model: '7726-32X', ru: 1},
  'asr-9006': {manufacturer: 'Cisco', model: 'ASR 9006', ru: 10},
  'asr-9001': {manufacturer: 'Cisco', model: 'ASR 9001', ru: 2}};

test('loadCatalog(base) fetches <base>/rack.json, a trailing slash or not', async () => {
  clearDistCache(); asked.length = 0; body = {format: 1, devices: DEVICES};
  await loadCatalog('/d');
  assert.deepEqual(asked, ['https://page.test/d/rack.json']);
  clearDistCache(); asked.length = 0;
  await loadCatalog('/d/');
  assert.deepEqual(asked, ['https://page.test/d/rack.json']);
});

test('a function dist is called with rack.json and its URL is fetched', async () => {
  clearDistCache(); asked.length = 0;
  const calls = [];
  await loadCatalog(path => { calls.push(path); return `https://cdn.test/index@1/${path}`; });
  assert.deepEqual(calls, ['rack.json']);
  assert.deepEqual(asked, ['https://cdn.test/index@1/rack.json']);
});

test('a format other than 1 is refused with the sentence that says so', async () => {
  clearDistCache(); body = {format: 2, devices: {}};
  await assert.rejects(loadCatalog('/d'), {message: 'rack.json: format 2; this kit reads format 1'});
  clearDistCache(); body = {devices: {}};
  await assert.rejects(loadCatalog('/d'), {message: 'rack.json: format undefined; this kit reads format 1'});
});

test('entries are sorted by manufacturer, then model; chassisOf finds a device or null', async () => {
  clearDistCache(); body = {format: 1, devices: DEVICES};
  const c = await loadCatalog('/d');
  assert.deepEqual(c.entries.map(e => e.name), ['tm-280', 'asr-9001', 'asr-9006', 'as7726-32x']);
  assert.equal(c.chassisOf('asr-9006').ru, 10);
  assert.equal(c.chassisOf('nope'), null);
  assert.equal(c.chassisOf('constructor'), null);
  assert.equal(c.chassisOf('__proto__'), null);
  assert.equal(chassisLookup(DEVICES)('tm-280'), DEVICES['tm-280']);
  assert.equal(catalogEntries({}).length, 0);
});

test('a catalogue with no devices key loads empty', async () => {
  clearDistCache(); body = {format: 1};
  const c = await loadCatalog('/d');
  assert.deepEqual(c.devices, {});
  assert.deepEqual(c.entries, []);
});
