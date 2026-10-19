// Abandoning a load in kit/shell.js (#998). A load whose fetch never settles
// is given up with `abandonLoad()`, which ends it as a newer load would
// (#929): no state written, no drawing mounted, no `load`, and its promise
// rejects as superseded. `loadstart` announces every load so a host can start
// its timer on it. Each case holds one response on the wire, abandons, and
// releases it afterwards.
import test from 'node:test';
import assert from 'node:assert/strict';
import { install, gate } from './fake-shell-dom.mjs';

const held = {};                 // url suffix -> gate; a fetch for it waits on the gate
const asked = key => held[key]?.asked;
const hold = key => { held[key] = {...gate(), asked: false}; return held[key]; };
const face = (src, parts = []) => JSON.stringify({src, parts});
const meta = (name, configs) => JSON.stringify({
  device: name, model: name.toUpperCase(), default: configs[0], views: ['front', 'rear'],
  bays: {}, cages: {},
  configs: configs.map(c => ({name: c, files: {front: `${name}.${c}.front.svg`, rear: `${name}.${c}.rear.svg`}})),
});
// a held route is answered when its gate opens; one that is not held at once
const routes = {
  'devices.json': () => JSON.stringify({devices: [
    {name: 'a', ns: 'v'}, {name: 'b', ns: 'v'}, {name: 'c', ns: 'v'}]}),
  'components.json': () => JSON.stringify({components: [
    {ns: 'v', name: 'psu', major: 'v1', skins: ['default'],
     fields: {watts: {type: 'choice', options: ['550W', '750W'], default: '550W'}}}]}),
};
const serve = (key, body) => {
  routes[key] = async () => {
    if (held[key]) { held[key].asked = true; await held[key].p; }
    return body;
  };
};
serve('a.configs.json', meta('a', ['ac']));
serve('b.configs.json', meta('b', ['base']));
serve('c.configs.json', meta('c', ['base']));
serve('a.ac.front.svg', face('a.ac.front'));
serve('a.ac.rear.svg', face('a.ac.rear', [{path: 'psu-1/module', ref: 'v/psu@1'}]));
for (const d of ['b', 'c']) for (const v of ['front', 'rear']) serve(`${d}.base.${v}.svg`, face(`${d}.base.${v}`));
install(routes);

// the start-up link: a field on a part only the rear draws, so the shell
// fetches the rear faces after the load, and that fetch is held here
globalThis.location.search = '?device=a&view=front&fields=' + 'psu-1%2Fmodule~watts~750W';
const { createShell, isSuperseded } = await import('../../../kit/shell.js');

const starts = [];
const loads = [];
const devices = [];
const shell = createShell({dist: 'http://kit.test/dist'});
shell.on('loadstart', info => starts.push(info));
shell.on('load', svg => loads.push(svg.getAttribute('data-src')));
shell.on('device', name => devices.push(name));

const tick = () => new Promise(r => setTimeout(r, 0));
const until = async ok => { for (let i = 0; i < 200 && !ok(); i++) await tick(); };

// boot: let the load finish, wait for the held rear face to be asked for, abandon
hold('a.ac.rear.svg');
await until(() => asked('a.ac.rear.svg'));
const bootAsked = asked('a.ac.rear.svg');
const bootStarts = starts.slice();
const bootLoads = loads.slice();
shell.abandonLoad();
held['a.ac.rear.svg'].open();
await shell.ready;
await tick();
delete held['a.ac.rear.svg'];

const drawn = () => shell.el.svgHost.children.map(c => c.getAttribute('data-src'));
const where = () => [shell.state.device, shell.state.cfg, shell.state.view];
const outcome = p => p.then(() => 'loaded', err => (isSuperseded(err) ? 'superseded' : `failed: ${err}`));
// what a load writes outside the state: the tree and the breadcrumb
const touched = {tree: 0, crumb: 0};
for (const [name, node] of [['tree', shell.el.tree], ['crumb', shell.el.crumb]]) {
  Object.defineProperty(node, 'innerHTML', {get: () => '', set: () => { touched[name]++; }});
  for (const m of ['appendChild', 'replaceChildren']) {
    const real = node[m].bind(node);
    node[m] = (...a) => { touched[name]++; return real(...a); };
  }
}
const quiet = async () => {
  for (const k of Object.keys(held)) delete held[k];
  await shell.loadDevice('a', {config: 'ac', view: 'front'});
  starts.length = 0; loads.length = 0; devices.length = 0;
  touched.tree = touched.crumb = 0;
};

test('the start-up load announces itself once', () => {
  assert.equal(bootStarts.length, 1);
  assert.deepEqual(bootStarts[0], {kind: 'device', device: 'a', config: null, view: 'front', module: null});
});

test('a link whose faces are being fetched, abandoned, does not apply its fields', () => {
  assert.ok(bootAsked, 'the rear face was never asked for: the case did not reach the fields');
  assert.deepEqual(bootLoads, ['a.ac.front'], 'the start-up load itself had completed');
  assert.deepEqual(JSON.parse(JSON.stringify(shell.state.cfgFields)), {});
  assert.deepEqual(starts, bootStarts, 'abandoning started no load');
  assert.deepEqual(drawn(), ['a.ac.front']);
});

test('a device manifest that arrives after abandonLoad changes nothing', async () => {
  await quiet();
  const before = {where: where(), svg: shell.state.svg, meta: shell.state.meta};
  hold('c.configs.json');
  const late = outcome(shell.loadDevice('c'));
  await until(() => asked('c.configs.json'));
  assert.equal(starts.length, 1);
  assert.deepEqual(starts[0], {kind: 'device', device: 'c', config: null, view: null, module: null});
  shell.abandonLoad();
  held['c.configs.json'].open();
  assert.equal(await late, 'superseded');
  await tick();
  assert.deepEqual(where(), before.where);
  assert.equal(shell.state.svg, before.svg);
  assert.equal(shell.state.meta, before.meta);
  assert.deepEqual(drawn(), ['a.ac.front'], 'the drawing the page had is still the only one');
  assert.deepEqual(loads, []);
  assert.deepEqual(devices, []);
  assert.deepEqual(touched, {tree: 0, crumb: 0});
});

test('a face that arrives after abandonLoad is not mounted', async () => {
  await quiet();
  hold('b.base.front.svg');
  const late = outcome(shell.loadDevice('b'));
  await until(() => asked('b.base.front.svg'));
  shell.abandonLoad();
  held['b.base.front.svg'].open();
  assert.equal(await late, 'superseded');
  await tick();
  assert.deepEqual(drawn(), [], 'the stage was emptied when the load began and nothing was mounted over it');
  assert.deepEqual(loads, []);
  assert.deepEqual(touched, {tree: 0, crumb: 0});
});

test('a load the shell started from its own select can be abandoned', async () => {
  await quiet();
  const before = {device: shell.state.device, cfg: shell.state.cfg, svg: shell.state.svg};
  hold('a.ac.rear.svg');
  shell.el.view.onchange({target: {value: 'rear'}});
  await until(() => asked('a.ac.rear.svg'));
  assert.equal(starts.length, 1);
  assert.deepEqual(starts[0], {kind: 'stage', device: 'a', config: 'ac', view: 'rear', module: null});
  shell.abandonLoad();
  held['a.ac.rear.svg'].open();
  await tick(); await tick();
  assert.deepEqual(drawn(), [], 'blank: the stage was emptied by the load and nothing replaced it');
  assert.deepEqual(loads, []);
  assert.deepEqual(touched, {tree: 0, crumb: 0});
  assert.equal(shell.state.device, before.device);
  assert.equal(shell.state.cfg, before.cfg);
  assert.equal(shell.state.view, 'rear', 'the select has written its own choice, as it does before any load');
  assert.equal(shell.state.svg, before.svg, 'the drawing state names is the one before the load');
});

test('the start event fires once for each load', async () => {
  await quiet();
  await shell.loadDevice('b', {config: 'base', view: 'rear'});
  assert.deepEqual(starts, [{kind: 'device', device: 'b', config: 'base', view: 'rear', module: null}]);
  starts.length = 0;
  shell.el.view.onchange({target: {value: 'front'}});
  await until(() => loads.length);
  assert.deepEqual(starts, [{kind: 'stage', device: 'b', config: 'base', view: 'front', module: null}]);
  starts.length = 0;
  await shell.loadStage();
  assert.equal(starts.length, 1);
});

test('abandoning with no load in flight does nothing, and a later load runs', async () => {
  await quiet();
  const before = {where: where(), svg: shell.state.svg};
  assert.doesNotThrow(() => shell.abandonLoad());
  assert.doesNotThrow(() => shell.abandonLoad());
  assert.deepEqual(where(), before.where);
  assert.equal(shell.state.svg, before.svg);
  assert.deepEqual(drawn(), ['a.ac.front']);
  assert.deepEqual(starts, []);
  assert.equal(await outcome(shell.loadDevice('b')), 'loaded');
  assert.deepEqual(where(), ['b', 'base', 'front']);
  assert.deepEqual(drawn(), ['b.base.front']);
  assert.deepEqual(loads, ['b.base.front']);
});
