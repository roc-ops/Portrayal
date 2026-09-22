// A colour field is painted at runtime, not only at build time (#481).
//
// kit/fields.js is the rule both runtime paths apply - shell.js's setFields on
// the 2D drawing, relief.js's applyNodeFields on the documents the 3D scene
// rasterises. It is exercised here on the fake DOM (fake-dom.mjs), through the
// real modules: the helper directly, and relief.js's registry on top of it.
import { build, toSpec, install } from './fake-dom.mjs';

install();
// relief.js reads `location` at module scope for its ?tex flag
globalThis.location = { search: '' };

const F = await import('../../../kit/fields.js');
const R = await import('../../../kit/relief.js');

// an optic seated in a cage, drawn the way generic/sfp-lc's skin compiles
const optic = () => build({a: {id: 'port-4-occupant', 'data-path': 'port-4-occupant'}, c: [
  {t: 'rect', a: {id: 'body', fill: '#6e747c'}},
  {t: 'rect', a: {id: 'bail', fill: '#6f6f6f', stroke: '#444444',
                  'data-fill-from': 'latch-color'}},
  {t: 'rect', a: {id: 'ring', fill: 'none', stroke: '#8c1f1f',
                  'data-stroke-from': 'ring-color'}},
  {t: 'rect', a: {id: 'bare', 'data-fill-from': 'shell'}},          // drawn with no fill
  {t: 'text', a: {id: 'label', 'data-from': 'label'}},
]});
const find = (root, id) => [root, ...root.descendants()].find(n => n.getAttribute('id') === id);
const look = (root, id) => ({...find(root, id)._attrs});

const out = {};

// ----------------------------------------------------------- the helper
const g = optic();
F.paintFields(g, {'latch-color': '#c22f2f', label: 'uplink-A'});
out.set = {bail: look(g, 'bail'), label: find(g, 'label').textContent,
           group: g.getAttribute('data-latch-color')};

F.paintFields(g, {'latch-color': ' #2255aa '});
out.changed = look(g, 'bail');

F.paintFields(g, {'latch-color': ''});
out.cleared = look(g, 'bail');

F.paintFields(g, {'latch-color': '#c22f2f'});
F.paintFields(g, {'latch-color': null});
out.nulled = look(g, 'bail');

F.paintFields(g, {'ring-color': '#3d7bd6'});
out.stroke = look(g, 'ring');
F.paintFields(g, {'ring-color': ''});
out.strokeCleared = look(g, 'ring');

F.paintFields(g, {shell: '#101010'});
out.bareSet = look(g, 'bare');
F.paintFields(g, {shell: ''});
out.bareCleared = look(g, 'bare');

// text fields still do what they did: a value prints, empty hides
F.paintFields(g, {label: ''});
out.labelHidden = [find(g, 'label').textContent, find(g, 'label').getAttribute('display')];
F.paintFields(g, {label: 'uplink-B'});
out.labelShown = [find(g, 'label').textContent, find(g, 'label').getAttribute('display')];

// a key that matches no node changes nothing but its own data- attribute
const n = optic();
const before = JSON.stringify(toSpec(n));
F.paintFields(n, {'no-such-key': '#ff0000'});
n.removeAttribute('data-no-such-key');
out.noMatch = JSON.stringify(toSpec(n)) === before;

// unpaintFields puts every changed colour back and leaves no stash behind
const u = optic();
F.paintFields(u, {'latch-color': '#c22f2f', 'ring-color': '#3d7bd6', shell: '#101010'});
F.unpaintFields(u);
out.unpainted = [look(u, 'bail'), look(u, 'ring'), look(u, 'bare')];

// ----------------------------------------------------------- the 3D registry
// The document is repainted from its OWN LAST OUTPUT (viewer3d's LOD records
// keep the restyled text), so the drawn colour has to survive serialising, and a
// part dropped from the map has to go back to grey.
const scope = R.createReliefScope();
const face = () => build({c: [toSpec(optic()),
  {a: {'data-projection': '', 'data-of': 'port-4-occupant'}, c: [
    {t: 'rect', a: {id: 'bail-plan', fill: '#6f6f6f', 'data-fill-from': 'latch-color'}}]}]});
let doc = face();
R.setNodeFields({'port-4-occupant': {'latch-color': '#c22f2f', label: 'uplink-A'}}, scope);
R.applyNodeFields(doc, scope);
out.relief = {bail: look(doc, 'bail'), plan: look(doc, 'bail-plan'),
              label: find(doc, 'label').textContent};

doc = build(JSON.parse(JSON.stringify(toSpec(doc))));      // through text and back
R.setNodeFields({'port-4-occupant': {'latch-color': '#2255aa'}}, scope);
R.applyNodeFields(doc, scope);
out.reliefChanged = look(doc, 'bail');

doc = build(JSON.parse(JSON.stringify(toSpec(doc))));
R.setNodeFields({}, scope);                                  // the part left the map
R.applyNodeFields(doc, scope);
out.reliefDropped = [look(doc, 'bail'), look(doc, 'bail-plan')];

// an optic seated in a module keeps its own value for a key the module also sets
const nested = build({c: [{a: {'data-path': 'slot-1/module'}, c: [
  {t: 'rect', a: {id: 'handle', fill: '#6f6f6f', 'data-fill-from': 'latch-color'}},
  {a: {'data-path': 'slot-1/module/port-2'}, c: [
    {t: 'rect', a: {id: 'inner', fill: '#6f6f6f', 'data-fill-from': 'latch-color'}}]}]}]});
R.setNodeFields({'slot-1/module/port-2': {'latch-color': '#2255aa'},
                 'slot-1/module': {'latch-color': '#c22f2f'}}, scope);
R.applyNodeFields(nested, scope);
out.nested = [look(nested, 'handle').fill, look(nested, 'inner').fill];

// ----------------------------------------------------------- the 3D side colour
// recolourBody is the repaint half of a derived side colour. A canvas stub whose
// pixels are all one colour stands in for the repainted raster.
const canvasOf = (r, g, b) => ({width: 8, height: 8, getContext: () => ({
  getImageData: () => ({data: Uint8ClampedArray.from({length: 8 * 8 * 4},
    (_, i) => [r, g, b, 255][i % 4])})})});
const mat = () => ({seen: null, color: {set(c) { this.owner.seen = c; }}});
const mats = [mat(), mat()];
for (const m of mats) m.color.owner = m;
out.recolour = R.recolourBody(true, mats, canvasOf(194, 47, 47));
out.recolourSeen = mats.map(m => m.seen);
const kept = [mat()]; kept[0].color.owner = kept[0];
out.recolourStated = [R.recolourBody(false, kept, canvasOf(194, 47, 47)), kept[0].seen];
out.recolourNone = R.recolourBody(true, [], canvasOf(1, 2, 3));

console.log(JSON.stringify(out));
