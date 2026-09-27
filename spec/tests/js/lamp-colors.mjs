// A lamp in the host's colour, in the documents the 3D scene rasterises (#664).
//
// relief.js keeps a per-viewer registry of lamp colours beside the states and
// fields, and applyNodeLampColors writes each as an inline --led-color on the
// lamp - the route a state takes, repaint and never re-shape. lamps.js's unlit
// copy (withBase) has to take the colour out again, or a blink's off half would
// show it. Exercised on the fake DOM through the real modules.
import { register } from 'node:module';
import { build, install } from './fake-dom.mjs';

// lamps.js imports `three` for the meshes it builds, which nothing here builds:
// it is only used inside functions, so an empty module stands in for it and the
// real withBase runs unchanged.
register('data:text/javascript,' + encodeURIComponent(
  "export async function resolve(s, c, next) {"
  + " return s === 'three' ? {url: 'data:text/javascript,export {}', shortCircuit: true}"
  + " : next(s, c); }"));

install();
// relief.js reads `location` at module scope for its ?tex flag
globalThis.location = { search: '' };

const R = await import('../../../kit/relief.js');
const L = await import('../../../kit/lamps.js');

const face = () => build({a: {id: 'face'}, c: [
  {t: 'g', a: {'data-path': 'led-sys', id: 'led-sys'}, c: [
    {t: 'circle', a: {id: 'lens', fill: 'var(--led-color, #3a3f44)'}}]},
  {t: 'g', a: {'data-path': 'led-fan', id: 'led-fan', style: 'opacity:0.9'}, c: [
    {t: 'circle', a: {id: 'lens2', fill: 'var(--led-color, #3a3f44)'}}]},
  {t: 'g', a: {'data-path': 'led-psu', id: 'led-psu'}},
]});
const node = (root, path) => root.querySelectorAll(`[data-path="${path}"]`)[0];
const look = (root, path) => ({...node(root, path)._attrs});
const out = {};

const scope = R.createReliefScope();

// set: two lamps, one of which already carries a style of its own
out.rejected = R.setNodeLampColors({'led-sys': '#FF00FF', 'led-fan': '#2bb3c8',
                                    'led-psu': 'red; background:url(x)'}, scope);
out.registry = Object.fromEntries(R.nodeLampColors(scope));
const a = face();
R.applyNodeLampColors(a, scope);
out.set = {sys: look(a, 'led-sys'), fan: look(a, 'led-fan'), psu: look(a, 'led-psu')};

// change one, drop the other: the dropped one's own style comes back exactly
R.setNodeLampColors({'led-sys': '#00ff00'}, scope);
R.applyNodeLampColors(a, scope);
out.changed = {sys: look(a, 'led-sys'), fan: look(a, 'led-fan')};

// clear: nothing of ours is left on any node
R.setNodeLampColors({}, scope);
R.applyNodeLampColors(a, scope);
out.cleared = {sys: look(a, 'led-sys'), fan: look(a, 'led-fan')};

// OFF STAYS OFF: a lamp registered state-off keeps its drawing, as in 2D
R.setNodeStates({'led-sys': 'state-off'}, scope);
R.setNodeLampColors({'led-sys': '#ff00ff', 'led-fan': '#2bb3c8'}, scope);
const b = face();
R.applyNodeLampColors(b, scope);
out.off = {sys: look(b, 'led-sys'), fan: look(b, 'led-fan')};
R.setNodeStates({}, scope);

// two viewers, two opinions
const other = R.createReliefScope();
out.otherScope = Object.fromEntries(R.nodeLampColors(other));

// THE UNLIT COPY: withBase strips the state classes AND the host's colour, and
// nothing else in the style
const lit = `<svg><!--art--><g class="state-on" style="opacity:0.9;${R.LAMP_MARK}--led-color:#ff00ff/*portrayal-lamp-end*/"><circle/></g></svg>`;
out.stripped = R.withoutLampColors(lit);
out.base = L.withBase(lit);

// A DOME CUT BELOW THE LAMP'S GROUP (nodeTools' scopeWrap): the wrapper that
// rebuilds the group around the dome's art took its class, so its state rule
// applied, and not the host's colour - the face showed magenta round a dome
// in the stylesheet's own colour. The wrapper carries the marked colour now.
// Layout the fake DOM does not have is stubbed; scopeWrap reads attributes only.
const { Node } = await import('./fake-dom.mjs');
if (!Object.getOwnPropertyDescriptor(Node.prototype, 'parentElement'))
  Object.defineProperty(Node.prototype, 'parentElement', {get() { return this.parentNode; }});
const lampFace = () => build({t: 'svg', a: {id: 'svg'}, c: [
  {t: 'g', a: {'data-path': 'led-sys', id: 'led-sys', class: 'state-ok'}, c: [
    {t: 'circle', a: {id: 'dome', 'data-path': 'led-sys/lamp', 'data-z-dome': '0.3',
                      fill: 'var(--led-color, #3a3f44)'}}]}]});
const s2 = R.createReliefScope();
R.setNodeStates({'led-sys': 'state-ok'}, s2);
R.setNodeLampColors({'led-sys': '#ff00ff'}, s2);
const svg = lampFace();
svg.getScreenCTM = () => ({inverse: () => ({})});
// nodeTools gathers the drawing's <style> and <defs>, which this one has none
// of; the fake DOM has no tag selectors, so that one query answers empty
const qsa = svg.querySelectorAll.bind(svg);
svg.querySelectorAll = sel => (sel === 'style, defs' ? [] : qsa(sel));
R.applyNodeLampColors(svg, s2);
const dome = svg.querySelectorAll('[data-path="led-sys/lamp"]')[0];
out.wrapped = R.nodeTools(svg).scopeWrap(dome, '<circle/>');
R.setNodeLampColors({}, s2);
R.applyNodeLampColors(svg, s2);
out.wrappedCleared = R.nodeTools(svg).scopeWrap(dome, '<circle/>');

// a 3D mark's colour goes into a three.js material, which reads #rgb and
// #rrggbb only: the alpha forms are cut down, anything else is null (#667)
out.markHex = Object.fromEntries(['#F0a', '#f0a8', '#FF00AA', '#ff00aa80', 'red', '#ff00a', '', null]
  .map(c => [String(c), R.markHex(c)]));

console.log(JSON.stringify(out));
