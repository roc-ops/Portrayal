// A `fields=` entry for a part the opening view does not draw (#818). The
// explorer opens on `view=` alone, and a part carries its ref only on a face
// that draws it, so a rating set on a rear supply and carried in a link that
// opens on the front named nothing held, was ignored and fell out of the
// location. It is judged on the faces that draw it and kept, and painted on
// the rear when the reader goes there.
import test from 'node:test';
import assert from 'node:assert/strict';
import { install } from './fake-shell-dom.mjs';

const face = (src, parts = []) => JSON.stringify({src, parts});
install({
  'devices.json': () => JSON.stringify({devices: [{name: 'a', ns: 'v'}]}),
  'components.json': () => JSON.stringify({components: [
    {ns: 'v', name: 'psu', major: 'v1', skins: ['default'],
     fields: {watts: {type: 'choice', options: ['550W', '750W'], default: '550W'}}}]}),
  'a.configs.json': () => JSON.stringify({
    device: 'a', model: 'A', default: 'ac', views: ['front', 'rear'], bays: {}, cages: {},
    configs: [{name: 'ac', files: {front: 'a.ac.front.svg', rear: 'a.ac.rear.svg'}}]}),
  'a.ac.front.svg': () => face('front'),
  'a.ac.rear.svg': () => face('rear', [{path: 'psu-1/module', ref: 'v/psu@1'}]),
});
globalThis.location.search = '?device=a&view=front&fields='
  + ['psu-1%2Fmodule~watts~750W', 'ghost%2Fmodule~watts~750W', 'psu-2%2Fmodule~watts~9W'].join(',');
const warned = [];
console.warn = (...a) => warned.push(a);

const { createShell } = await import('../../../kit/shell.js');
const shell = createShell({dist: 'http://kit.test/dist'});
await shell.ready;

test('the link opens on the face it names', () => {
  assert.equal(shell.state.view, 'front');
  assert.equal(shell.state.svg.getAttribute('data-src'), 'front');
});

test('a field on a part drawn only on another face is kept', () => {
  assert.deepEqual(JSON.parse(JSON.stringify(shell.state.cfgFields)),
                   {'psu-1/module': {watts: '750W'}});
});

test('an entry naming nothing drawn anywhere is still ignored, and said so', () => {
  const ignored = warned.find(w => String(w[0]).includes('fields naming nothing'))?.[2];
  assert.deepEqual(ignored?.sort(), ['ghost/module~watts', 'psu-2/module~watts']);
});

test('the kept value is painted when the face that draws the part is mounted', async () => {
  shell.state.view = 'rear';
  await shell.loadStage();
  const psu = shell.state.svg.querySelector('[data-path="psu-1/module"][data-ref]');
  assert.equal(psu.getAttribute('data-watts'), '750W');
});
