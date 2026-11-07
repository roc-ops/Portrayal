// A device with one view is unchanged by naming views (#1002): its `pulled`
// event is `{paths}` and nothing more, a path names a part by itself, and the
// calls a host made before views existed work as they did.
import test from 'node:test';
import assert from 'node:assert/strict';
import { install } from './fake-shell-dom.mjs';

install({
  'devices.json': () => JSON.stringify({devices: [{name: 'box', ns: 'fixture', model: 'BOX'}]}),
  'components.json': () => JSON.stringify({components: []}),
  'box.configs.json': () => JSON.stringify({
    device: 'box', model: 'BOX', default: 'base', views: ['front'], bays: {}, cages: {},
    configs: [{name: 'base', files: {front: 'f.svg'}}]}),
  'f.svg': () => JSON.stringify({src: 'front', parts: [
    {attrs: {'data-path': 'dimm-0', 'data-under': 'lid'}},
    {attrs: {'data-path': 'lid', 'data-class': 'cover', 'data-behaviour': 'mounts'}}]}),
});
globalThis.location.search = '?device=box';

const { createShell } = await import('../../../kit/shell.js');
const shell = createShell({dist: 'http://kit.test/dist'});
await shell.ready;
shell.refreshTree();

const plain = o => JSON.parse(JSON.stringify(o));
const events = [];
shell.on('pulled', e => events.push(plain(e)));
const lid = () => shell.state.svg.querySelectorAll('[data-path="lid"]')[0];
const rowOf = id => [...shell.el.tree.querySelectorAll('.node')].find(r => r.dataset.path === id);

test('the event of a one-view device carries paths and no views', () => {
  shell.select('dimm-0', true);
  assert.deepEqual(events.at(-1), {paths: ['lid']});
  assert.equal(lid().hasAttribute('data-portrayal-pulled'), true);
  assert.equal(rowOf('lid').classList.contains('pulled'), true);
  assert.deepEqual(shell.pulledPaths(), ['lid']);
  assert.deepEqual(shell.pulledViews(), [null]);
  shell.select(null, true);
  assert.deepEqual(events.at(-1), {paths: []});
});

test('setPulled with no view works as it did, and its rows carry no view', () => {
  shell.setPulled(['lid'], true);
  assert.deepEqual(events.at(-1), {paths: ['lid']});
  assert.equal(rowOf('lid').dataset.view, undefined);
  shell.setPulled(['lid'], false);
  assert.deepEqual(events.at(-1), {paths: []});
});
