// Overlapping loads in kit/shell.js (#929): a loadDevice or loadStage that a
// newer one overtook must write no state, mount no drawing and emit no `load`,
// and its promise must reject as superseded. Each case holds one response on
// the wire and releases it after, or before, the newer load finishes.
import test from 'node:test';
import assert from 'node:assert/strict';
import { install, gate } from './fake-shell-dom.mjs';

const held = {};                 // url suffix -> gate; a fetch for it waits on the gate
const meta = (name, configs) => JSON.stringify({
  device: name, model: name.toUpperCase(), default: configs[0], views: ['front', 'rear'],
  bays: {}, cages: {},
  configs: configs.map(c => ({name: c, files: {front: `${name}.${c}.front.svg`, rear: `${name}.${c}.rear.svg`}})),
});
const routes = {
  'devices.json': () => JSON.stringify({devices: [{name: 'a', ns: 'v'}, {name: 'b', ns: 'v'}]}),
  'components.json': () => JSON.stringify({components: []}),
  'a.configs.json': () => meta('a', ['ac', 'dc']),
  'b.configs.json': () => meta('b', ['base']),
};
// every face is its own file name, so the mounted drawing says which load drew it
for (const f of ['a.ac.front', 'a.ac.rear', 'a.dc.front', 'a.dc.rear', 'b.base.front', 'b.base.rear'])
  routes[`${f}.svg`] = async () => { if (held[`${f}.svg`]) await held[`${f}.svg`].p; return f; };
for (const f of ['a.configs.json', 'b.configs.json']) {
  const plain = routes[f];
  routes[f] = async u => { if (held[f]) await held[f].p; return plain(u); };
}
install(routes);
const { createShell, isSuperseded } = await import('../../../kit/shell.js');

const shell = createShell({dist: 'http://kit.test/dist'});
const loads = [];
shell.on('load', svg => loads.push(svg.getAttribute('data-src')));
await shell.ready;

const tick = () => new Promise(r => setTimeout(r, 0));
const drawn = () => shell.el.svgHost.children.map(c => c.getAttribute('data-src'));
const where = () => [shell.state.device, shell.state.cfg, shell.state.view];
const outcome = p => p.then(() => 'loaded', err => (isSuperseded(err) ? 'superseded' : `failed: ${err}`));
const fresh = async () => {
  for (const k of Object.keys(held)) delete held[k];
  await shell.loadDevice('a', {config: 'ac', view: 'front'});
  loads.length = 0;
};

test('the shell mounts the first device it lists', () => {
  assert.equal(shell.state.device, 'a');
  assert.deepEqual(drawn(), ['a.ac.front']);
});

test('a device manifest that arrives after a newer load changes nothing', async () => {
  await fresh();
  // held only for this load; the memo in dist.js keeps a's manifest after it
  held['b.configs.json'] = gate();
  const late = outcome(shell.loadDevice('b'));
  await tick();
  const newer = outcome(shell.loadDevice('a', {config: 'dc', view: 'rear'}));
  assert.equal(await newer, 'loaded');
  held['b.configs.json'].open();
  assert.equal(await late, 'superseded');
  await tick();
  assert.deepEqual(where(), ['a', 'dc', 'rear']);
  assert.deepEqual(drawn(), ['a.dc.rear']);
  assert.deepEqual(loads, ['a.dc.rear']);
});

test('the older load coming back first is superseded all the same', async () => {
  await fresh();
  held['a.dc.front.svg'] = gate();
  held['b.base.front.svg'] = gate();
  shell.state.cfg = 'dc';
  const older = outcome(shell.loadStage());
  await tick();
  const newer = outcome(shell.loadDevice('b'));
  await tick();
  held['a.dc.front.svg'].open();             // the older face lands first
  assert.equal(await older, 'superseded');
  assert.deepEqual(drawn(), [], 'a superseded face mounted while the newer load was out');
  held['b.base.front.svg'].open();
  assert.equal(await newer, 'loaded');
  assert.deepEqual(where(), ['b', 'base', 'front']);
  assert.deepEqual(drawn(), ['b.base.front']);
  assert.deepEqual(loads, ['b.base.front']);
});

test('a face that lands after a configuration change is not stacked on the new one', async () => {
  await fresh();
  held['a.dc.front.svg'] = gate();
  shell.state.cfg = 'dc';
  const older = outcome(shell.loadStage());
  await tick();
  shell.state.cfg = 'ac';
  const newer = outcome(shell.loadStage());
  assert.equal(await newer, 'loaded');
  held['a.dc.front.svg'].open();
  assert.equal(await older, 'superseded');
  await tick();
  assert.deepEqual(drawn(), ['a.ac.front'], 'exactly one drawing, the newer one');
  assert.equal(shell.state.svg.getAttribute('data-src'), 'a.ac.front');
  assert.deepEqual(loads, ['a.ac.front']);
});

test('a load nothing overtook resolves as before', async () => {
  await fresh();
  assert.equal(await outcome(shell.loadDevice('b')), 'loaded');
  assert.deepEqual(where(), ['b', 'base', 'front']);
  assert.deepEqual(loads, ['b.base.front']);
});
