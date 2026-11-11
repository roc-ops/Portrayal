// A `swap=` that names a part the library no longer holds (#1752). The explorer
// left it out and said nothing; the loader now reports which entries it
// dropped and what replaced the part, to a page that listens or reads the
// answer, and a page that does neither behaves as before.
import test from 'node:test';
import assert from 'node:assert/strict';
import { install } from './fake-shell-dom.mjs';

const SIG = 'sha256:' + '0'.repeat(64);
install({
  'devices.json': () => JSON.stringify({devices: [{name: 'a', ns: 'v'}]}),
  'components.json': () => JSON.stringify({components: [
    {ns: 'v', name: 'card', major: 'v2', skins: ['default'],
     supersedes: [{ref: 'v/card@1', signature: SIG, from: '0123abc'}]},
    {ns: 'v', name: 'blank', major: 'v1', skins: ['default']}]}),
  'a.configs.json': () => JSON.stringify({
    device: 'a', model: 'A', default: 'ac', views: ['front'],
    bays: {front: [{id: 'slot-1', accepts: ['v/card@2', 'v/blank@1'], default: 'v/blank@1'}]}, cages: {},
    configs: [{name: 'ac', files: {front: 'a.ac.front.svg'}}]}),
  'a.ac.front.svg': () => JSON.stringify({src: 'front', parts: []}),
});
globalThis.location.search = '?device=a&view=front&swap=slot-1~v/card@1,ghost~v/blank@1';
const warned = [];
console.warn = (...a) => warned.push(a);

const { createShell } = await import('../../../kit/shell.js');
const shell = createShell({dist: 'http://kit.test/dist'});
const heard = [];
shell.on('dropped', rows => heard.push(rows));
await shell.ready;

test('the entries left out are reported to a page that listens, with what replaced the part', () => {
  assert.deepEqual(heard.flat(), [
    {path: 'ghost', ref: 'v/blank@1', why: 'refused'},
    {path: 'slot-1', ref: 'v/card@1', why: 'gone', replacedBy: 'v/card@2'}]);
});

test('the boot still warns of the ignored keys, and now says which part is gone', () => {
  assert.deepEqual(warned.find(w => String(w[0]).includes('swaps naming nothing'))?.[2]?.sort(), ['ghost', 'slot-1']);
  assert.ok(warned.some(w => /v\/card@1 \(slot-1\) is no longer in the library; v\/card@1 is now v\/card@2/.test(String(w[1]))));
});

test('nothing is seated: the state holds no swap', () => {
  assert.deepEqual(JSON.parse(JSON.stringify(shell.state.cfgBays)), {});
});

test('applySwaps answers with the report, and `ignored` as before', async () => {
  const r = await shell.applySwaps({'slot-1': 'v/card@2'});
  assert.deepEqual(r.ignored, []);
  assert.deepEqual(r.dropped, []);
});
