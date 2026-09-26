// data-r-from: a numeric field sets a circle's radius, at runtime as at build
// (docs/pluggables-cables-design.md section 4). Run through kit/fields.js on
// the fake DOM (fake-dom.mjs); spec/tests/test_r_from_binding.py holds the
// answers to render.py's.
import { build, install } from './fake-dom.mjs';

install();
const F = await import('../../../kit/fields.js');

const part = () => build({a: {id: 'p'}, c: [
  {t: 'circle', a: {id: 'stub', r: '2.4', 'data-r-from': 'cable-od'}},
  // a composed child's group, the way the build nests one inside its host
  {a: {id: 'child', 'data-path': 'p/boot'}, c: [
    {t: 'circle', a: {id: 'inner', r: '2.4', 'data-r-from': 'cable-od'}},
  ]},
]});
const find = (root, id) => [root, ...root.descendants()].find(n => n.getAttribute('id') === id);

const out = {};

const g = part();
const c = find(g, 'stub');
const seq = [];
F.paintFields(g, {'cable-od': 9}); seq.push(c.getAttribute('r'));
F.paintFields(g, {'cable-od': ''}); seq.push(c.getAttribute('r'));
F.paintFields(g, {'cable-od': 'thick'}); seq.push(c.getAttribute('r'));
out.seq = seq;

// every value the build test feeds, each on a fresh part; the Python test
// passes its own CASES list as JSON, so the two sides read one list
const CASES = process.argv[2] ? JSON.parse(process.argv[2])
  : [9.0, '3.0', '', 'thick', null, '0', '1.2.3', 'inf', '-4', ' 6.9 '];
out.cases = CASES.map(v => {
  const h = part();
  F.paintFields(h, {'cable-od': v});
  return [v, find(h, 'stub').getAttribute('r')];
});

const n = part();
F.paintFields(n, {'cable-od': '6.9'});
out.nested = find(n, 'inner').getAttribute('r');
F.unpaintFields(n);
out.unpainted = find(n, 'inner').getAttribute('r');
out.stashLeft = find(n, 'inner').hasAttribute('data-portrayal-r');

console.log(JSON.stringify(out));
