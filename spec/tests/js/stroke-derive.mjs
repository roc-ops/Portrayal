// An outline derived from its fill (#482): kit/fields.js's `strokeShade` for a
// list of colours given on argv (JSON), and `data-stroke-derive` applied at
// runtime on the fake DOM. The Python side of the parity check is render.py's
// `stroke_shade`; spec/tests/test_stroke_derive.py compares the two.
import { build, install } from './fake-dom.mjs';

install();
const F = await import('../../../kit/fields.js');

const inputs = JSON.parse(process.argv[2] || '[]');
const out = {shades: inputs.map(c => F.strokeShade(c))};

const part = () => build({a: {'data-path': 'port-4-occupant'}, c: [
  {t: 'rect', a: {id: 'bail', fill: '#6f6f6f', stroke: '#444444',
                  'data-fill-from': 'latch-color', 'data-stroke-derive': 'latch-color'}}]});
const bail = g => ({...g.children[0]._attrs});
const g = part();
F.paintFields(g, {'latch-color': '#c22f2f'});
out.set = bail(g);
F.paintFields(g, {'latch-color': '#2255AA'});
out.changed = bail(g);
F.paintFields(g, {'latch-color': 'red'});          // a fill, but no shade
out.noShade = bail(g);
F.paintFields(g, {'latch-color': '#c22f2f'});
F.paintFields(g, {'latch-color': ''});
out.cleared = bail(g);

console.log(JSON.stringify(out));
