// The 3D module view reads a component preview as a face of the part's own
// w x h from an origin of 0 0 (kit/relief.js buildFaceRelief). A part with
// `head:` publishes a preview whose viewBox also holds its overhangs
// (components_index.preview_box), so the comp face crops it back: `toSizeBox`.
import {readFileSync} from 'node:fs';
globalThis.location = { search: '' };
const {toSizeBox} = await import('../../../kit/relief.js');
const root = t => /<svg\b[^>]*>/.exec(t)[0];
const attr = (tag, a) => (new RegExp(`\\s${a}="([^"]*)"`).exec(tag) || [])[1];
const out = {};
for (const [key, file, w, h] of JSON.parse(process.argv[2])) {
  const text = readFileSync(file, 'utf8');
  const got = toSizeBox(text, w, h);
  const tag = root(got);
  out[key] = {viewBox: attr(tag, 'viewBox'), width: attr(tag, 'width'),
              height: attr(tag, 'height'), unchanged: got === text,
              bodySame: got.slice(got.indexOf(tag) + tag.length) ===
                        text.slice(text.indexOf(root(text)) + root(text).length)};
}
console.log(JSON.stringify(out));
