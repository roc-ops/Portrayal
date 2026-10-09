// The kit's half of the generic rack ear (spec/tests/test_generic_ears.py):
// relief.js genericEars, over the chassis cases the Python test hands it on
// stdin, so the 3D scene and ears.py draw the same bracket.
globalThis.location = { search: '' };
globalThis.fetch = async () => ({ ok: true, text: async () => '<svg/>' });
globalThis.CSS = {escape: s => s};
const m = await import('../../../kit/relief.js');
let text = '';
for await (const chunk of process.stdin) text += chunk;
const cases = JSON.parse(text);
console.log(JSON.stringify(cases.map(c => m.genericEars(c.chassis, c.faceW))));
