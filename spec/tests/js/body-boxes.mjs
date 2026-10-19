// A body in pieces resolves to the same list the one-box body does, so both
// builders draw either form through one function. Pure arithmetic, so node.
globalThis.location = { search: '' };
globalThis.fetch = async () => ({ ok: true, text: async () => '<svg/>' });
const m = await import('../../../kit/relief.js');

const one = m.bodyBoxes({depth: 195.5, color: '#222'}, 86.3, 39.1);
const fp = m.bodyBoxes({depth: 60, footprint: {at: [2, 3], size: [40, 30]}}, 50, 40);
const riser = m.bodyBoxes({depth: 184.8, color: '#4a5057', boxes: [
  {id: 'pcb', at: [-0.75, -1.4], size: [1.6, 77.0], from: 13.9, depth: 170.9, color: '#1f5138'},
  {id: 'c', at: [0.85, -0.58], size: [11.3, 10.8], from: 47.9, depth: 91.0},
]}, 107.59, 62.0);
// the box is in the module's frame; the module sits at (13.95, 4) and its
// drawn bbox starts 13.41 further left, which is what put the PCB outside
const plain = m.localToFace({a: 1, b: 0, c: 0, d: 1, e: 13.95, f: 4.0}, {x: -0.75, y: -1.4, w: 1.6, h: 77});
const mirrored = m.localToFace({a: -1, b: 0, c: 0, d: 1, e: 13.95 + 107.59, f: 4.0}, {x: -0.75, y: -1.4, w: 1.6, h: 77});
// a round piece and a painted one carry what they said, and nothing else does
const pieces = m.bodyBoxes({depth: 250, boxes: [
  {id: 'ring', at: [10, 4], size: [60, 6], from: 100, depth: 60, shape: 'ring', axis: 'y', wall: 2},
  {id: 'post', at: [0, 0], size: [8, 8], from: 0, depth: 5, shape: 'cylinder', axis: 'z'},
  {id: 'tray', at: [118, 2], size: [195, 9], from: 85, depth: 93.6, shows: ['plan']},
  {id: 'plainbox', at: [0, 0], size: [1, 1], depth: 1, shape: 'box'},
]}, 431, 22);
// the patch of a 431 x 250 plan a tray at x 118..313, 85..178.6 behind the face stands under:
// drawing x runs right to left (431 - 313 = 118 .. 313), drawing y is the depth
const tray = pieces[2];
const planCrop = m.pieceArtCrop(tray, 'plan', 431, 431, 250);
// and of a 100 x 21 rear, a block at face x 4..16, y 1..10: drawing x 84..96
const rearCrop = m.pieceArtCrop({x: 4, y: 1, w: 12, h: 9, z0: 31, z1: 37}, 'rear', 100, 100, 21);
// sample a crop: u, v on the piece -> x, y in mm on the drawing (canvas v is up)
const at = (c, u, v, dw, dh) => [
  +((c.offset[0] + u * c.repeat[0]) * dw).toFixed(3),
  +((1 - (c.offset[1] + v * c.repeat[1])) * dh).toFixed(3)];
// a piece keeps its shape and its art only where the host's frame is the part's own
const straight = [m.pieceIsStraight(null), m.pieceIsStraight({a: 1, b: 0, c: 0, d: 1, e: 5, f: 5}),
  m.pieceIsStraight({a: -1, b: 0, c: 0, d: -1, e: 0, f: 0}),      // rotate 180
  m.pieceIsStraight({a: 0, b: 1, c: -1, d: 0, e: 0, f: 0}),       // rotate 90
  m.pieceIsStraight({a: -1, b: 0, c: 0, d: 1, e: 0, f: 0}),       // mirrored
  m.pieceIsStraight({a: 1, b: 0, c: 0, d: 1, e: 0, f: 0}, {deg: 8})];
const demoted = m.plainPiece(pieces[0]);
// THE FOUR SIDES. A card's shroud: face x 28.41..126.31, y 14.4..40, 0.9..140.93
// behind the face, on a 120.02 face 268.6 deep. Each side drawing's viewBox has
// its own origin (`at`), and a crop is sampled at the four corners of the side
// as three's BoxGeometry lays its uv out: +x and -x faces run u toward the back
// and toward the front, +y has v toward the back, -y v toward the front.
const shroud = {x: 28.41, y: 14.4, w: 97.9, h: 25.6, z0: 0.9, z1: 140.93};
const side = (which, dw, dh, vbAt) => m.pieceArtCrop(shroud, which, 120.02, dw, dh, {at: vbAt, depth: 268.6});
const sideAt = (c, u, v, dw, dh, [ax, ay]) => {
  const [x, y] = at(c, u, v, dw, dh);
  return [+(x + ax).toFixed(3), +(y + ay).toFixed(3)];
};
const right = side('right', 267.7, 38.23, [0.9, 1.77]);
const left = side('left', 267.7, 25.6, [0, 14.4]);
const top = side('top', 120, 268.6, [10, 0]);
const bottom = side('bottom', 97.9, 267.7, [-6.29, 0]);
const sides = {
  // u 0 v 1 on +x is the front top corner: drawing x = z0, y = the box's top
  rightFrontTop: sideAt(right, 0, 1, 267.7, 38.23, [0.9, 1.77]),
  rightBackBottom: sideAt(right, 1, 0, 267.7, 38.23, [0.9, 1.77]),
  // u 0 on -x is the back: drawing x = 268.6 - z1
  leftBackTop: sideAt(left, 0, 1, 267.7, 25.6, [0, 14.4]),
  // u 0 v 0 on +y is face x 28.41 at the front: drawing y = 268.6 - z0
  topFrontLeft: sideAt(top, 0, 0, 120, 268.6, [10, 0]),
  // u 0 v 0 on -y is face x 28.41 at the back: drawing x = 120.02 - 28.41
  bottomBackLeft: sideAt(bottom, 0, 0, 97.9, 267.7, [-6.29, 0]),
  bottomFrontRight: sideAt(bottom, 1, 1, 97.9, 267.7, [-6.29, 0]),
};
// A FITTED PIECE stands while the part shows a node for one of its options
const ext = {id: 'ext', when: {extender: ['straight']}};
const fitted = [m.pieceFitted({id: 'plain'}, undefined),
  m.pieceFitted(ext, undefined), m.pieceFitted(ext, {extender: ['long-offset']}),
  m.pieceFitted(ext, {extender: ['straight']}), m.pieceFitted(ext, {other: ['straight']})];
// and what a drawing shows, by part: a hidden node (or one inside a hidden
// group) shows nothing, and a part alone is keyed by its own path
const {build} = await import('./fake-dom.mjs');
const doc = build({a: {}, c: [
  {a: {'data-path': 'card'}, c: [
    {a: {'data-show-from': 'extender', 'data-show': 'straight'}},
    {a: {'data-show-from': 'extender', 'data-show': 'long-offset', display: 'none'}}]},
  {a: {'data-path': 'riser/module/slot-1/module'}, c: [
    {a: {display: 'none'}, c: [{a: {'data-show-from': 'extender', 'data-show': 'straight'}}]},
    {a: {'data-show-from': 'extender', 'data-show': 'long-offset'}}]},
  {a: {'data-projection': '1', 'data-path': 'x'}, c: [{a: {'data-show-from': 'k', 'data-show': 'a'}}]}]});
const shown = m.shownOptions(doc);
const keptWhen = m.plainPiece(m.bodyBoxes({depth: 10, boxes: [
  {id: 'e', at: [0, 0], size: [1, 1], depth: 1, when: {extender: ['straight']}, shows: ['right']}]}, 1, 1)[0]);
console.log(JSON.stringify({one, fp, riser, plain, mirrored, pieces, straight, demoted,
  planNear: at(planCrop, 0, 0, 431, 250), planFar: at(planCrop, 1, 1, 431, 250),
  rearTopLeft: at(rearCrop, 0, 1, 100, 21), rearBottomRight: at(rearCrop, 1, 0, 100, 21),
  sides, fitted, keptWhen, shown}));
