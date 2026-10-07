// Switch positions: a choice field MOVES or SHOWS a node, at runtime as at
// build (docs/switch-positions-design.md). Run through kit/fields.js on the
// fake DOM; spec/tests/test_switch_positions.py holds the answers to render.py's.
import { build, install } from './fake-dom.mjs';

install();
const F = await import('../../../kit/fields.js');

const part = () => build({a: {id: 'p'}, c: [
  {t: 'rect', a: {id: 'slider', x: '1.1', y: '6', width: '2', height: '2.8',
                  'data-move-from': 'sw-1', 'data-move': 'on: 0 -3.2'}},
  {t: 'rect', a: {id: 'drawn-moved', x: '0', y: '0', width: '1', height: '1', transform: 'translate(1 1)',
                  'data-move-from': 'sw-1', 'data-move': 'on: 0.5 0'}},
  {t: 'rect', a: {id: 'rocker', x: '0', y: '0', width: '4', height: '2',
                  'data-move-from': 'sw-1', 'data-move': 'on: 0 0 180'}},
  {t: 'rect', a: {id: 'flag-on', x: '0', y: '0', width: '1', height: '1',
                  'data-show-from': 'state', 'data-show': 'on'}},
  {t: 'rect', a: {id: 'flag-off', x: '0', y: '0', width: '1', height: '1', display: 'none',
                  'data-show-from': 'state', 'data-show': 'off tripped'}},
  {t: 'text', a: {id: 'label', 'data-from': 'note', 'data-show-from': 'state', 'data-show': 'tripped',
                  display: 'none'}},
]});
const find = (root, id) => [root, ...root.descendants()].find(n => n.getAttribute('id') === id);
const snap = g => Object.fromEntries(['slider', 'drawn-moved', 'rocker', 'flag-on', 'flag-off', 'label']
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
out.parse = F.parseMoves('on: 0 -3.2, off: 1 2 90');
try { F.parseMoves('on: up'); out.badParse = 'accepted'; } catch (e) { out.badParse = 'threw'; }
console.log(JSON.stringify(out));
