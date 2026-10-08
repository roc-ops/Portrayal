import test from 'node:test';
import assert from 'node:assert/strict';

// jdist resolves a url against location.href and fetches it: stand both in.
globalThis.location = {href: 'https://page.test/', search: ''};
const asked = [];
let body = {format: 1, types: {}};
globalThis.fetch = async url => { asked.push(url); return {ok: true, json: async () => body}; };

const T = await import('../../../kit/rack/cable-types.js');
const {clearDistCache} = await import('../../../kit/dist.js');

const src = ['s'];
const TYPES = {
  om4: {id: 'om4', media: 'om4', od_mm: 3.0, min_bend_radius: {
    installed: {mm: 25, basis: 'standard', sources: src}, loaded: {mm: 50, basis: 'standard', sources: src}}},
  cat6: {id: 'cat6', media: 'cat6', od_mm: 6.0, min_bend_radius: {
    installed: {xOD: 4, basis: 'standard', sources: src}, loaded: {xOD: 8, basis: 'standard', sources: src}}},
  aoc: {id: 'aoc', media: 'aoc', od_mm: 3.0, min_bend_radius: {
    installed: {xOD: 10, basis: 'standard', sources: src}, loaded: null}},
  'cat6a-stp': {id: 'cat6a-stp', media: 'cat6a', od_mm: 7.5, min_bend_radius: {
    installed: {xOD: 8, basis: 'convention', sources: src}, loaded: null}},
  nood: {id: 'nood', media: 'nood', min_bend_radius: {installed: {xOD: 4, basis: 'convention', sources: src}}},
};

test('a fixed radius is its millimetres; a multiple is times the outside diameter', () => {
  assert.equal(T.radiusMm(TYPES.om4), 25);
  assert.equal(T.radiusMm(TYPES.cat6), 24);
  assert.equal(T.radiusMm(TYPES.aoc), 30);           // 10 x 3.0, not 30.000000000000004
  assert.equal(T.radiusMm(TYPES.om4, 'loaded'), 50);
  assert.equal(T.radiusMm(TYPES.cat6, 'loaded'), 48);
});

test('no radius, or a multiple of a diameter the type does not give, is null', () => {
  assert.equal(T.radiusMm(TYPES.aoc, 'loaded'), null);
  assert.equal(T.radiusMm(TYPES.nood), null);
  assert.equal(T.radiusMm(null), null);
});

test('installedRadiusMm resolves a type by id, and an unknown id is null', () => {
  assert.equal(T.installedRadiusMm(TYPES, 'cat6a-stp'), 60);
  assert.equal(T.installedRadiusMm(TYPES, 'cat5e'), null);
  assert.equal(T.installedRadiusMm(TYPES, 'constructor'), null);
  assert.equal(T.installedRadiusMm(TYPES, '__proto__'), null);
  assert.equal(T.installedRadiusMm(TYPES, undefined), null);
});

test('bendOf reads a cable by its type, else its media; none is null', () => {
  const bendOf = T.bendLookup(TYPES);
  assert.equal(bendOf({id: 'c1', media: 'om4'}), 25);
  assert.equal(bendOf({id: 'c2', media: 'cat6a', type: 'cat6a-stp'}), 60);
  assert.equal(bendOf({id: 'c3', media: ''}), null);
  assert.equal(bendOf({id: 'c4', media: 'toString'}), null);
  assert.equal(bendOf({id: 'c5'}), null);
  assert.equal(bendOf(null), null);
});

test('a type this table does not know falls back to the cable\'s media', () => {
  const bendOf = T.bendLookup(TYPES);
  assert.equal(bendOf({media: 'cat6', type: 'cat6-from-a-newer-table'}), 24);
  assert.equal(bendOf({media: 'cat6', type: 'constructor'}), 24);
  assert.equal(bendOf({media: '', type: 'nope'}), null);
  assert.equal(T.cableTypeOf(TYPES, {media: 'om4', type: 'cat6a-stp'}).id, 'cat6a-stp');
  assert.equal(T.cableTypeOf(TYPES, {media: 'om4', type: 'x'}).id, 'om4');
  assert.equal(T.diameterLookup(TYPES)({media: 'cat6', type: 'x'}), 6.0);
});

test('diameterOf reads the type\'s typical outside diameter', () => {
  const diameterOf = T.diameterLookup(TYPES);
  assert.equal(diameterOf({media: 'cat6'}), 6.0);
  assert.equal(diameterOf({media: 'nood'}), null);
  assert.equal(diameterOf({media: 'x'}), null);
});

test('loadCableTypes fetches <base>/cable-types.json and hands back the lookups', async () => {
  clearDistCache(); asked.length = 0; body = {format: 1, version: '1.0.0', sources: {s: {}}, types: TYPES};
  const ct = await T.loadCableTypes('/d/');
  assert.deepEqual(asked, ['https://page.test/d/cable-types.json']);
  assert.equal(ct.version, '1.0.0');
  assert.equal(ct.bendOf({media: 'cat6'}), 24);
  assert.equal(ct.diameterOf({media: 'om4'}), 3.0);
  assert.equal(ct.typeOf('aoc').id, 'aoc');
  assert.equal(ct.typeOf('hasOwnProperty'), null);
});

test('a format other than 1 is refused with the sentence that says so', async () => {
  clearDistCache(); body = {format: 2, types: {}};
  await assert.rejects(T.loadCableTypes('/d'), {message: 'cable-types.json: format 2; this kit reads format 1'});
});
