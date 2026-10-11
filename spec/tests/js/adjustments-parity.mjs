// The kit's move against the build's (docs/adjustable-positions-design.md
// sections 5 and 6). spec/tests/test_adjustments_build.py hands this the faces
// of the fixture as the build drew them at its default, each as a fake-DOM
// tree, and a fields map; it moves them with kit/fields.js and prints, for
// every node with an id, the attributes a move can change. The Python side
// compares them with the same faces as the build drew them moved.
import { readFileSync } from 'node:fs';
import { build, install } from './fake-dom.mjs';

install();
globalThis.location = {search: ''};
const F = await import('../../../kit/fields.js');

const {faces, fields} = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const KEYS = ['transform', 'x', 'y', 'data-depth', 'data-z-lift', 'data-z-out',
              'data-z-profile', 'data-z-profile-y'];
const out = {};
for (const [view, spec] of Object.entries(faces)) {
  const root = build(spec);
  const drew = F.paintAdjustments(root, fields);
  out[view] = {drew, nodes: Object.fromEntries([root, ...root.descendants()]
    .filter(n => n.getAttribute('id'))
    .map(n => [n.getAttribute('id'),
               Object.fromEntries(KEYS.filter(k => n.hasAttribute(k)).map(k => [k, n.getAttribute(k)]))]))};
}
console.log(JSON.stringify(out));
