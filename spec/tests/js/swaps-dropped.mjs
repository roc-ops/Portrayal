// spec/tests/js/swaps-dropped.mjs
// A swap map that names a part the library no longer holds: the loader says
// which entries it left out, why, and what the library says replaced the part
// (`supersedes`, read by kit/redirects.js). Pure: no DOM, no fetch.
import test from 'node:test';
import assert from 'node:assert/strict';
import {acceptSwaps} from '../../../kit/swap.js';
import {redirectsOf, droppedSwaps, droppedText} from '../../../kit/redirects.js';

const SIG = 'sha256:' + '0'.repeat(64);
const entry = (name, major, supersedes = []) => ({ns: 'so', name, major: `v${major}`, supersedes});

// the catalogue: card@2 replaces the removed card@1; blank@1 and leaf@1 are live
const LIST = [entry('card', 2, [{ref: 'so/card@1', signature: SIG, from: '0123abc'}]), entry('blank', 1), entry('leaf', 1)];
const COMPS = {'so/card@2': {bays: {'sub-1': {accepts: ['so/leaf@1']}}}, 'so/blank@1': {bays: {}}, 'so/leaf@1': {bays: {}}};
const compByRef = ref => COMPS[ref];
const redirects = redirectsOf(LIST);
const bays = [{id: 'slot-1', accepts: ['so/card@2', 'so/blank@1'], default: 'so/blank@1'},
              {id: 'slot-2', accepts: ['so/card@2', 'so/blank@1'], default: 'so/blank@1'}];
const ctx = {compByRef, redirects};
const run = map => {
  const {ignored} = acceptSwaps(map, {bays, compByRef, built: id => bays.find(b => b.id === id)?.default});
  return droppedSwaps(map, ignored, ctx);
};

test('a ref the library no longer holds is named, with the part that replaced it', () => {
  assert.deepEqual(run({'slot-1': 'so/card@1'}), [{path: 'slot-1', ref: 'so/card@1', why: 'gone', replacedBy: 'so/card@2'}]);
});

test('a ref gone and replaced by nothing is named without a replacement', () => {
  const r = run({'slot-2': 'so/old@3'});
  assert.deepEqual(r, [{path: 'slot-2', ref: 'so/old@3', why: 'gone'}]);
  assert.ok(!('replacedBy' in r[0]));
});

test('an entry under a dropped carrier is named as sitting under it', () => {
  assert.deepEqual(run({'slot-1': 'so/card@1', 'slot-1/module/sub-1': 'so/leaf@1'}), [
    {path: 'slot-1', ref: 'so/card@1', why: 'gone', replacedBy: 'so/card@2'},
    {path: 'slot-1/module/sub-1', ref: 'so/leaf@1', why: 'under', carrier: 'slot-1'}]);
});

test('a part the library holds that the slot does not take is refused, not gone', () => {
  assert.deepEqual(run({'slot-1': 'so/leaf@1', 'nope': 'so/blank@1'}), [
    {path: 'nope', ref: 'so/blank@1', why: 'refused'}, {path: 'slot-1', ref: 'so/leaf@1', why: 'refused'}]);   // in the loader's key order
});

test('an entry the loader took, or one that empties a slot, is never named', () => {
  assert.deepEqual(run({'slot-1': 'so/card@2', 'slot-2': ''}), []);
  assert.deepEqual(droppedSwaps({'slot-2': ''}, ['slot-2'], ctx), []);
});

test('with no catalogue read, nothing is called gone', () => {
  const bare = droppedSwaps({'slot-1': 'so/card@1'}, ['slot-1'], {compByRef, redirects: redirectsOf([])});
  assert.deepEqual(bare, [{path: 'slot-1', ref: 'so/card@1', why: 'refused'}]);
  assert.deepEqual(droppedSwaps({'slot-1': 'so/card@1'}, ['slot-1'], {}), [{path: 'slot-1', ref: 'so/card@1', why: 'refused'}]);
});

test('garbage never throws', () => {
  assert.deepEqual(droppedSwaps(null, ['a'], ctx), []);
  assert.deepEqual(droppedSwaps({a: 'x'}, null, ctx), []);
  assert.deepEqual(droppedSwaps({a: 7}, ['a'], {compByRef: () => { throw new Error('bad ref'); }, redirects}), []);
});

test('the sentence names each gone ref once, with where it was and what replaced it', () => {
  const said = droppedText(run({'slot-1': 'so/card@1', 'slot-2': 'so/old@3', 'slot-1/module/sub-1': 'so/leaf@1'}));
  assert.match(said, /so\/card@1 \(slot-1\) is no longer in the library; so\/card@1 is now so\/card@2/);
  assert.match(said, /so\/old@3 \(slot-2\) is no longer in the library/);
  assert.doesNotMatch(said, /leaf/);
  assert.equal(droppedText([]), '');
  assert.equal(droppedText(run({'slot-1': 'so/leaf@1'})), '', 'a refused entry is not a part the library lost');
});
