// A drawing bigger than its face is laid out on the face (#865).
//
// A part beyond the rack face - the CMH-6DR1U's end rings, 43 mm past each
// ear - grows the drawing's viewBox, and its origin goes negative. relief.js
// takes every coordinate in the drawing's own user units, so x 0 is the
// face's left edge whatever the viewBox says; read as the plane, the wider
// viewBox put the face's centre half the overhang off. render.py states the
// face on the root (`data-face-w`/`-h`) whenever the two differ, and the face
// is cropped back to it, as a module preview with a head already is.
globalThis.location = { search: '' };
globalThis.fetch = async () => ({ ok: true, text: async () => '<svg/>' });
globalThis.CSS = {escape: s => s};
const m = await import('../../../kit/relief.js');

const RINGED = '<svg xmlns="http://www.w3.org/2000/svg" width="568.6mm" height="44mm" ' +
  'viewBox="-43 0 568.6 44" data-device="cmh-6dr1u" data-face-w="482.6" data-face-h="44">' +
  '<rect x="0" y="0" width="482.6" height="44"/></svg>';
const PLAIN = '<svg xmlns="http://www.w3.org/2000/svg" width="434mm" height="86.8mm" ' +
  'viewBox="0 0 434 86.8"><rect/></svg>';

const out = {};
out.ringed = m.faceDeclared(RINGED);
out.plain = m.faceDeclared(PLAIN);
out.none = m.faceDeclared('');
out.cropped = /<svg\b[^>]*>/.exec(m.toSizeBox(RINGED, ...out.ringed))[0];
// LX, as relief.js lays a part out: x + w/2 - fw/2. The left ring's centre is
// at x 0 (from -43 to 43); on the face it is the face's left edge.
const LX = (x, w, fw) => x + w / 2 - fw / 2;
out.ringCentreOnFace = LX(-43, 86, out.ringed[0]);
out.ringCentreOnDrawing = LX(-43, 86, 568.6);
console.log(JSON.stringify(out));
