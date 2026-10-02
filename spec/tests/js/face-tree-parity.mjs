// The Explorer's tree over real compiled faces, for test_face_elements_parity.py.
// argv[2] is a JSON file: {name: drawing}, each drawing the fake-dom tree
// ({t, a, c}) the Python side read out of a face in library/dist. Prints
// {name: [[key, parentKey|null], ...]} in the order faceTree lists the rows -
// the same `faceTree` shell.js buildTree returns, run on the same elements.
import {readFileSync} from 'node:fs';
import {build} from './fake-dom.mjs';
const {faceTree} = await import('../../../kit/swap.js');

const faces = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const out = {};
for (const [name, spec] of Object.entries(faces)) {
  const rows = [];
  (function walk(nodes, up) {
    for (const n of nodes) { rows.push([n.path, up]); walk(n.kids, n.path); }
  })(faceTree(build(spec)), null);
  out[name] = rows;
}
console.log(JSON.stringify(out));
