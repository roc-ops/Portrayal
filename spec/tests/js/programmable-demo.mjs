// A demo colour for a programmable-colour lamp (#1271).
//
// A lamp the model marks `programmable` carries `data-programmable="true"` on
// its own element (and the maker's name for the feature in
// `data-programmable-note`). The Explorer offers a colour box on the tree row of
// such a lamp; what it asks of kit/states.js is which elements those are, which
// colours are colours, and which of the colours it holds the 3D scene should be
// given. Exercised on the shared fake DOM through the real module;
// test_programmable_demo_colour.py reads the JSON this prints.
import { build, install } from './fake-dom.mjs';

install();

const S = await import('../../../kit/states.js');

const lamp = (path, a = {}) => ({a: {'data-path': path, 'data-class': 'led', 'data-states': 'off up', ...a}});
const root = build({t: 'svg', a: {id: 'face'}, c: [
  lamp('led-a', {'data-programmable': 'true', 'data-programmable-note': 'Etherlighting'}),
  lamp('led-b', {'data-programmable': 'true'}),
  lamp('led-c'),
  lamp('led-d', {'data-programmable': 'false'}),
  lamp('led-e', {'data-programmable': 'true', 'data-programmable-note': '  '}),
]});
const el = p => root.querySelector(`[data-path="${p}"]`);

const out = {
  of: Object.fromEntries(['led-a', 'led-b', 'led-c', 'led-d', 'led-e'].map(p => [p, S.programmableOf(el(p))])),
  none: [S.programmableOf(null), S.programmableOf(undefined), S.programmableOf({})],
  hex: Object.fromEntries(['#ff00ff', '#F0F', '#FF00FF80', 'red', 'rgb(1,2,3)', '', null, '#12345', '#gggggg']
    .map(v => [String(v), S.demoHex(v)])),
  colours: S.demoColours(root, {'led-a': '#00ff00', 'led-b': 'nope', 'led-c': '#ff0000', 'gone': '#0000ff',
                                'led-e': '#0000FF'}),
  fromMap: S.demoColours(root, new Map([['led-a', '#123456']])),
  empty: [S.demoColours(root, {}), S.demoColours(root, null), S.demoColours(null, {'led-a': '#00ff00'})],
};
console.log(JSON.stringify(out));
