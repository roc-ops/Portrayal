// Switch positions: a choice field MOVES or SHOWS a node, at runtime as at
// build (docs/switch-positions-design.md). Run through kit/fields.js on the
// fake DOM; spec/tests/test_switch_positions.py holds the answers to render.py's.
import { build, install } from './fake-dom.mjs';

install();
globalThis.location = {search: ''};   // relief.js reads its own flags off the location
const F = await import('../../../kit/fields.js');

const part = () => build({a: {id: 'p'}, c: [
  {t: 'rect', a: {id: 'slider', x: '1.1', y: '6', width: '2', height: '2.8',
                  'data-move-from': 'sw-1', 'data-move': 'on: 0 -3.2'}},
  {t: 'rect', a: {id: 'drawn-moved', x: '0', y: '0', width: '1', height: '1', transform: 'translate(1 1)',
                  'data-move-from': 'sw-1', 'data-move': 'on: 0.5 0'}},
  {t: 'rect', a: {id: 'rocker', x: '0', y: '0', width: '4', height: '2',
                  'data-move-from': 'sw-1', 'data-move': 'on: 0 0 180'}},
  {t: 'rect', a: {id: 'placed-rocker', x: '0', y: '0', width: '4', height: '2', transform: 'translate(10 0)',
                  'data-move-from': 'sw-1', 'data-move': 'on: 1 0 180'}},
  {t: 'rect', a: {id: 'flag-on', x: '0', y: '0', width: '1', height: '1',
                  'data-show-from': 'state', 'data-show': 'on'}},
  {t: 'rect', a: {id: 'flag-off', x: '0', y: '0', width: '1', height: '1', display: 'none',
                  'data-show-from': 'state', 'data-show': 'off tripped'}},
  {t: 'text', a: {id: 'label', 'data-from': 'note', 'data-show-from': 'state', 'data-show': 'tripped',
                  display: 'none'}},
]});
const find = (root, id) => [root, ...root.descendants()].find(n => n.getAttribute('id') === id);
const snap = g => Object.fromEntries(['slider', 'drawn-moved', 'rocker', 'placed-rocker', 'flag-on', 'flag-off', 'label']
  .map(id => [id, {transform: find(g, id).getAttribute('transform'), display: find(g, id).getAttribute('display')}]));

// the Python test passes its list of value maps as JSON, so the two sides read one list
const CASES = JSON.parse(process.argv[2] || '[]');
const out = {cases: CASES.map(vals => { const g = part(); F.paintFields(g, vals); return snap(g); })};

// paint, then unpaint: everything back as drawn, no stash left
const g = part();
F.paintFields(g, {'sw-1': 'on', state: 'tripped'});
out.painted = snap(g);
F.unpaintFields(g);
out.unpainted = snap(g);
out.stashLeft = [g, ...g.descendants()].some(n =>
  n.hasAttribute('data-portrayal-transform') || n.hasAttribute('data-portrayal-display'));
// set, then set back to the default: as drawn
const h = part();
F.paintFields(h, {'sw-1': 'on'}); F.paintFields(h, {'sw-1': 'off'});
out.backToDefault = snap(h);
// A NODE THE BUILD MOVED for a configuration, as render.py writes it: the kit
// sets it back to the default, and an empty value leaves it as built
const built = () => build({a: {id: 'q'}, c: [
  {t: 'rect', a: {id: 'slider', x: '1.1', y: '6', width: '2', height: '2.8', transform: 'translate(0 -3.2)',
                  'data-move-base': '', 'data-move-from': 'sw-1', 'data-move': 'on: 0 -3.2'}},
  {t: 'rect', a: {id: 'drawn-moved', x: '0', y: '0', width: '1', height: '1',
                  transform: 'translate(0.5 0) translate(1 1)', 'data-move-base': 'translate(1 1)',
                  'data-move-from': 'sw-1', 'data-move': 'on: 0.5 0'}},
]});
const tfs = g => ['slider', 'drawn-moved'].map(id => find(g, id).getAttribute('transform'));
const b1 = built(); F.paintFields(b1, {'sw-1': 'off'}); out.builtOff = tfs(b1);
F.unpaintFields(b1); out.builtUnpainted = tfs(b1);
const b2 = built(); F.paintFields(b2, {'sw-1': ''}); out.builtEmpty = tfs(b2);
const b3 = built(); F.paintFields(b3, {'sw-1': 'on'}); out.builtOn = tfs(b3);
out.parse = F.parseMoves('on: 0 -3.2, off: 1 2 90');
try { F.parseMoves('on: up'); out.badParse = 'accepted'; } catch (e) { out.badParse = 'threw'; }
out.badNumber = ['on: . 0', 'on: 1.2.3 0', 'on: 0 0 .'].map(s => {
  try { F.parseMoves(s); return 'accepted'; } catch (e) { return 'threw'; } });
// THE MARK A PART CARRIES FOR ITS POSITION FIELDS (#874): taken before a hidden
// SHOW node is removed, so the viewer's rebuild check still sees the field
const R = await import('../../../kit/relief.js');
const face = build({a: {id: 'face'}, c: [
  {a: {id: 'brk', 'data-path': 'breaker-a1'}, c: [
    {t: 'rect', a: {id: 'flag-trip', display: 'none', 'data-show-from': 'state', 'data-show': 'tripped'}},
    {t: 'rect', a: {id: 'handle', 'data-move-from': 'state', 'data-move': 'off: 0 2'}},
  ]},
  {a: {id: 'dip', 'data-path': 'dip-a'}, c: [
    {t: 'rect', a: {id: 's1', 'data-move-from': 'sw-1', 'data-move': 'down: 0 1.5'}},
    {t: 'rect', a: {id: 's2', 'data-move-from': 'sw-2', 'data-move': 'down: 0 1.5'}},
  ]},
  {a: {id: 'plain', 'data-path': 'psu-1'}, c: [{t: 'text', a: {'data-from': 'watts'}}]},
]});
R.markPositionFields(face);
for (const el of [...face.querySelectorAll('[data-show-from][display="none"]')]) el.remove();
out.marks = Object.fromEntries(['brk', 'dip', 'plain'].map(id =>
  [id, find(face, id).getAttribute('data-position-fields')]));
out.flagGone = !find(face, 'flag-trip');
console.log(JSON.stringify(out));
