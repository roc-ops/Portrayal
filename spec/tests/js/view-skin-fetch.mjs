// A rack whose devices share a skin fetches that skin once (kit/rack/view/face.js
// loadSkin), a failed fetch is asked again, and findComp answers from a Map.
// Moved whole from portrayal-site's tests/rack/skin-fetch.test.mjs (5dbbd41bd3).
import assert from 'node:assert/strict';
import {test, finish} from './view-cases.mjs';

// (kit/dist.js resolves a url against the page's location)
globalThis.location = new URL('http://localhost/rack.html');
const calls = [];
let failSkin = 0;
globalThis.fetch = async url => {
  const u = String(url);
  calls.push(u);
  if (u.endsWith('components.json')) {
    const body = {components: [
      {ns: 'a', name: 'sfp', major: 'v1', skins: ['default']},
      {ns: 'a', name: 'sfp', major: 'v1', skins: ['other']},
      {ns: 'b', name: 'card', major: 'v2', skins: ['x']},
      {ns: 'c', name: 'late', major: 'v3', skins: ['x']},
    ]};
    return {ok: true, json: async () => body};
  }
  if (failSkin > 0) { failSkin--; throw new Error('network'); }
  return {ok: true, text: async () => `<svg id="${u}"/>`};
};

const {loadSkin, findComp, components} = await import('../../../kit/rack/view/face.js');

test('devices sharing a skin fetch it once', async () => {
  const rs = await Promise.all(Array.from({length: 40}, () => loadSkin('a/sfp@1:slot')));
  assert.equal(calls.filter(u => u.includes('--sfp--')).length, 1);
  assert.ok(rs.every(r => r.text === rs[0].text && r.comp.skins[0] === 'default'));
  await loadSkin('b/card@2');
  assert.equal(calls.filter(u => u.includes('--card--')).length, 1);
  assert.equal(await loadSkin('nope/none@1'), null);
});

test('a failed skin fetch is not kept', async () => {
  failSkin = 1;
  await assert.rejects(loadSkin('c/late@3'), /network/);
  const r = await loadSkin('c/late@3');
  assert.match(r.text, /--late--/);
  assert.equal(calls.filter(u => u.includes('--late--')).length, 2);
});

test('findComp finds the first match by ref key', async () => {
  const list = await components();
  assert.equal(findComp(list, 'a/sfp@1:port').skins[0], 'default');
  assert.equal(findComp(list, 'b/card@2').ns, 'b');
  assert.equal(findComp(list, 'z/z@9'), undefined);
  // a list spliced in place is looked in as it now is
  const [gone] = list.splice(list.findIndex(c => c.ns === 'b'), 1);
  assert.equal(findComp(list, 'b/card@2'), undefined);
  list.push(gone);
  assert.equal(findComp(list, 'b/card@2'), gone);
});

await finish();
