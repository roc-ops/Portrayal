// A position set through the shell (docs/adjustable-positions-design.md
// sections 4 and 5): `setFields` at the carrier's path moves the members on
// every face, keeps the one spelling, and refuses what is not a position with
// its sentence; a `fields=` entry in a link is judged against the device's
// adjustments, which no component declares; a reset puts the drawing back.
import test from 'node:test';
import assert from 'node:assert/strict';
import { install } from './fake-shell-dom.mjs';

const DECL = {axis: 'z', carrier: 'panel', range: [20, 180], default: 60,
              stops: {front: 20, middle: 100, rear: 180}, label: 'Panel setback',
              datum: 'the front face of the panel'};
const ADJ = at => JSON.stringify({'panel-setback': {...DECL, at}});
const M = (by, a = {}) => ({'data-moves-with': 'panel-setback', 'data-moves-by': by, ...a});
const chassis = {attrs: {'data-path': 'chassis', 'data-model': 'SLIDER'}};
const face = (src, parts) => JSON.stringify({src, attrs: {'data-adjustments': ADJ(60)},
                                             parts: [chassis, ...parts]});
install({
  'devices.json': () => JSON.stringify({devices: [{name: 'slider', ns: 'fixture', model: 'SLIDER'}]}),
  'components.json': () => JSON.stringify({components: [
    {ns: 'fixture', name: 'slide-well', major: 'v1', skins: ['default']},
    {ns: 'fixture', name: 'slide-stud', major: 'v1', skins: ['default'],
     fields: {finish: {type: 'choice', options: ['zinc', 'black'], default: 'zinc'}}}]}),
  'slider.configs.json': () => JSON.stringify({
    device: 'slider', model: 'SLIDER', default: 'base', views: ['front', 'top', 'right'],
    bays: {}, cages: {},
    configs: [{name: 'base', files: {front: 'f.svg', top: 't.svg', right: 'r.svg'}}]}),
  'f.svg': () => face('front', [
    {attrs: {id: 'panel', 'data-path': 'panel', 'data-ref': 'fixture/slide-well@1:1.0.0',
             'data-depth': '60', transform: 'translate(10,0)', ...M('0 0 1')}},
    {attrs: {id: 'rail', 'data-path': 'rail', 'data-z-lift': '-60', ...M('0 0 1')}}]),
  't.svg': () => face('top', [
    {attrs: {id: 'panel', x: '10', y: '138.5', ...M('0 -1 0')}},
    {attrs: {id: 'rail', x: '20', y: '140', ...M('0 -1 0')}},
    {attrs: {id: 'side-left', x: '0', y: '0'}}]),
  'r.svg': () => face('right', [
    {attrs: {id: 'stud', 'data-path': 'stud', 'data-ref': 'fixture/slide-stud@1:1.0.0',
             transform: 'translate(63,17)', ...M('1 0 0')}}]),
});
// a link that opens on the plan, where the carrier is not drawn: a stop name,
// a field of a component beside it, and three entries that are not positions
globalThis.location.search = '?device=slider&view=top&fields=' + [
  'panel~panel-setback~rear', 'stud~finish~black', 'stud~panel-setback~100',
  'rail~panel-setback~100', 'panel~depth~5'].join(',');
const warned = [];
console.warn = (...a) => warned.push(a);

const { createShell } = await import('../../../kit/shell.js');
const { encodeFields, decodeFields } = await import('../../../kit/fields.js');
const shell = createShell({dist: 'http://kit.test/dist'});
await shell.ready;
await shell.loadFaces();

const plain = o => JSON.parse(JSON.stringify(o));
const on = (view, id) => (shell.state.faces?.[view] || shell.state.svg)
  .querySelectorAll('[id="' + id + '"]')[0];
const tf = (view, id) => on(view, id).getAttribute('transform');

test('a link sets a position, and the number is what is kept', () => {
  assert.deepEqual(plain(shell.state.cfgFields),
                   {panel: {'panel-setback': '180'}, stud: {finish: 'black'}});
  // and it goes back into a link as one string
  assert.equal(encodeFields(shell.state.cfgFields), 'panel~panel-setback~180,stud~finish~black');
  assert.deepEqual(decodeFields(encodeFields(shell.state.cfgFields)), plain(shell.state.cfgFields));
});

test('an entry that names a position anywhere but at its carrier is ignored', () => {
  const ignored = warned.find(w => String(w[0]).includes('fields naming nothing'))?.[2];
  assert.deepEqual(ignored?.sort(), ['panel~depth', 'rail~panel-setback', 'stud~panel-setback']);
});

test('the members stand at the position on every face, the one on screen included', () => {
  assert.equal(shell.state.view, 'top');
  assert.equal(tf('top', 'panel'), 'translate(0 -120)');
  assert.equal(tf('top', 'rail'), 'translate(0 -120)');
  assert.equal(tf('top', 'side-left'), null);
  assert.equal(tf('right', 'stud'), 'translate(120 0) translate(63,17)');
  // from the front the motion is depth: the well's floor, and what stands on it
  assert.equal(tf('front', 'panel'), 'translate(10,0)');
  assert.equal(on('front', 'panel').getAttribute('data-depth'), '180');
  assert.equal(on('front', 'rail').getAttribute('data-z-lift'), '-180');
  // the value is on the carrier, as every field is
  assert.equal(on('front', 'panel').getAttribute('data-panel-setback'), '180');
});

test('setFields takes a number or a stop name and keeps one spelling', () => {
  const events = [];
  shell.on('fields', e => events.push(plain(e)));
  assert.deepEqual(shell.setFields('panel', {'panel-setback': ' 120.04 '}), {refused: []});
  assert.equal(shell.state.cfgFields.panel['panel-setback'], '120');
  assert.equal(tf('top', 'panel'), 'translate(0 -60)');
  assert.equal(tf('right', 'stud'), 'translate(60 0) translate(63,17)');
  assert.deepEqual(events.at(-1).fields, {'panel-setback': '120'});
  shell.setFields('panel', {'panel-setback': 'front'});
  assert.equal(shell.state.cfgFields.panel['panel-setback'], '20');
  assert.equal(tf('top', 'panel'), 'translate(0 40)');
  assert.equal(on('front', 'panel').getAttribute('data-depth'), '20');
});

for (const [value, reason] of [
  ['300', 'panel-setback on SLIDER takes 20 to 180 mm. 300 is outside it.'],
  ['back', 'panel-setback on SLIDER takes a number in mm, or one of: front, middle, rear.'],
]) test(`setFields refuses ${value} with its sentence, and the drawing stays`, () => {
  shell.setFields('panel', {'panel-setback': '100'});
  const before = [tf('top', 'panel'), on('front', 'panel').getAttribute('data-depth')];
  let fired = 0;
  const off = shell.on('fields', () => fired++);
  warned.length = 0;
  const got = shell.setFields('panel', {'panel-setback': value});
  assert.deepEqual(got, {refused: [{path: 'panel', key: 'panel-setback', value, reason}]});
  assert.equal(shell.state.cfgFields.panel['panel-setback'], '100');
  assert.deepEqual([tf('top', 'panel'), on('front', 'panel').getAttribute('data-depth')], before);
  assert.equal(fired, 0);
  assert.ok(warned.some(w => String(w[0]).includes(reason)));
  if (typeof off === 'function') off();
});

test('a refused position does not take the other fields of the call with it', () => {
  // `stud` is no carrier: its fields are judged as they always were
  shell.setFields('stud', {finish: 'zinc', 'panel-setback': '999'});
  assert.equal(shell.state.cfgFields.stud.finish, 'zinc');
  assert.equal(shell.state.cfgFields.stud['panel-setback'], '999');   // not a position there: a plain key
  assert.equal(tf('right', 'stud'), 'translate(40 0) translate(63,17)');   // still at 100
  shell.setFields('stud', null);
});

test('resetting the position puts every face back as built', () => {
  shell.setFields('panel', {'panel-setback': '180'});
  shell.resetField('panel', 'panel-setback');
  assert.equal(shell.state.cfgFields.panel, undefined);
  assert.equal(tf('top', 'panel'), null);
  assert.equal(tf('top', 'rail'), null);
  assert.equal(tf('right', 'stud'), 'translate(63,17)');
  assert.equal(on('front', 'panel').getAttribute('data-depth'), '60');
  assert.equal(on('front', 'rail').getAttribute('data-z-lift'), '-60');
  for (const view of ['front', 'top', 'right'])
    for (const n of shell.state.faces[view].descendants())
      assert.ok(!Object.keys(n.attrs).some(k => k.startsWith('data-portrayal-adjust')), view);
});

test('clearing the fields of the carrier puts it back too', () => {
  shell.setFields('panel', {'panel-setback': '20'});
  assert.equal(tf('top', 'panel'), 'translate(0 40)');
  shell.setFields('panel', null);
  assert.equal(tf('top', 'panel'), null);
  assert.equal(on('front', 'panel').getAttribute('data-depth'), '60');
});

test('a face fetched after the position was set is drawn at it', async () => {
  shell.setFields('panel', {'panel-setback': '180'});
  shell.state.view = 'right';
  await shell.loadStage();
  const stud = shell.state.svg.querySelectorAll('[id="stud"]')[0];
  assert.equal(stud.getAttribute('transform'), 'translate(120 0) translate(63,17)');
});
