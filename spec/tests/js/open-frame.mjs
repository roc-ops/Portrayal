// An open-frame face (spec/tests/test_open_frame.py): relief.js decides what a
// cavity builds from what render.py flagged on it. A pocket builds walls, a floor
// and a back; an open bay's mouth (`hollow`) a 6 mm collar and nothing else; an
// OPEN-FRAME mouth nothing at all - no per-slot walls, because the slots of an
// open-frame chassis share one interior. openFrameFaces reads which of a
// device's faces declared an open frame, which is what tells viewer3d to line
// the box's inside.
globalThis.location = { search: '' };
globalThis.fetch = async () => ({ ok: true, text: async () => '<svg/>' });
globalThis.CSS = {escape: s => s};
const m = await import('../../../kit/relief.js');
const INTO = 300;
const out = {};
out.pocket = m.cavityShell({d: 330}, INTO);
out.shallowPocket = m.cavityShell({d: 12}, INTO);
out.hollow = m.cavityShell({d: 330, hollow: true}, INTO);
out.seeThrough = m.cavityShell({d: 431.8, seeThrough: true}, INTO);
out.openFrame = m.cavityShell({d: 330, hollow: true, openFrame: true}, INTO);
out.faces = m.openFrameFaces({
  front: '<svg xmlns="http://www.w3.org/2000/svg" data-open-frame="1"><rect/></svg>',
  rear: '<svg xmlns="http://www.w3.org/2000/svg" data-open-frame="1"/>',
  top: '<svg xmlns="http://www.w3.org/2000/svg"/>',
  left: null,
});
out.noFaces = m.openFrameFaces({front: '<svg xmlns="http://www.w3.org/2000/svg"/>'});
console.log(JSON.stringify(out));
