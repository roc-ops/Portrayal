// What kit/swap.js does to a bay's `seen-through` mark, on the bay's own drawing
// as render.py wrote it (stdin JSON: {bay, svg, ref}). Seating a part hides the
// mark with `display`, emptying the bay shows it again, an unknown ref leaves the
// bay open and the mark shown.
import {build, install} from './fake-dom.mjs';
const m = await import('../../../kit/swap.js');
install();

let raw = '';
for await (const chunk of process.stdin) raw += chunk;
const {bay, svg, ref} = JSON.parse(raw);

const root = build({t: 'svg', a: {}, c: [JSON.parse(JSON.stringify(svg))]});
const mark = () => root.querySelector('[data-class="seen-through"]').getAttribute('display');
const comp = {name: 'part', version: '1.0.0', size: {w: 10, h: 10, d: 10}};
const loadSkin = async r => r === ref ? {comp, text: JSON.stringify({a: {}, c: [{a: {id: 'x'}}]})} : null;
const bays = [{id: bay, at: [0, 0], size: {w: 100, h: 21}}];

const out = {before: mark()};
await m.applyOverrides(root, bays, {[bay]: ref}, loadSkin);
out.seated = mark();
await m.applyOverrides(root, bays, {[bay]: ''}, loadSkin);
out.emptied = mark();
await m.applyOverrides(root, bays, {[bay]: 'nobody/unknown@1'}, loadSkin);
out.unknown = mark();
console.log(JSON.stringify(out));
