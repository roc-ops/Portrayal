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
console.log(JSON.stringify({one, fp, riser, plain, mirrored, pieces,
  planNear: at(planCrop, 0, 0, 431, 250), planFar: at(planCrop, 1, 1, 431, 250),
  rearTopLeft: at(rearCrop, 0, 1, 100, 21), rearBottomRight: at(rearCrop, 1, 0, 100, 21)}));
