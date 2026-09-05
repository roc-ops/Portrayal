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
console.log(JSON.stringify({one, fp, riser}));
