globalThis.location = { search: '' };
globalThis.fetch = async () => ({ ok: true, text: async () => '<svg/>' });
const m = await import('../../../kit/relief.js');
const apply = (e, [x, y, z]) => [e[0]*x + e[4]*y + e[8]*z + e[12],
                                 e[1]*x + e[5]*y + e[9]*z + e[13],
                                 e[2]*x + e[6]*y + e[10]*z + e[14]];
const r = v => v.map(n => Math.round(n * 1000) / 1000);

// Test all four facings
const testFacing = (deg, facing, anchor, z0) => {
  const mat = m.tiltFrame({deg, facing, anchor, z0});

  // Extract columns (column-major order in a 4x4)
  const col0 = [mat[0], mat[1], mat[2]];
  const col1 = [mat[4], mat[5], mat[6]];
  const col2 = [mat[8], mat[9], mat[10]];

  // Orthonormality checks
  const dot = (a, b) => a[0]*b[0] + a[1]*b[1] + a[2]*b[2];
  const mag = (v) => Math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2]);

  // Apply to three points: anchor at z=0, axis step at z=0, and local z component
  const anchorPt = r(apply(mat, [anchor[0], anchor[1], 0]));
  const axisStep = r(apply(mat, [anchor[0] + (facing === 'up' || facing === 'down' ? 0 : 10),
                                  anchor[1] + (facing === 'up' || facing === 'down' ? 10 : 0),
                                  0]));
  const localZ = r(apply(mat, [anchor[0], anchor[1], 1]));

  return {
    anchorPt,
    axisStep,
    localZ,
    col0Mag: Math.round(mag(col0) * 1000) / 1000,
    col1Mag: Math.round(mag(col1) * 1000) / 1000,
    col2Mag: Math.round(mag(col2) * 1000) / 1000,
    dot01: Math.round(dot(col0, col1) * 1000) / 1000,
    dot02: Math.round(dot(col0, col2) * 1000) / 1000,
    dot12: Math.round(dot(col1, col2) * 1000) / 1000,
  };
};

const anchor = [10, 50];
const deg30 = 30, deg45 = 45;

const out = {
  up: testFacing(deg30, 'up', anchor, 2),
  down: testFacing(deg30, 'down', anchor, 0),
  left: testFacing(deg45, 'left', anchor, 0),
  right: testFacing(deg45, 'right', anchor, 0),
  unprojUp: m.unproject({x: 12, y: 50 + 8.660254, w: 5, h: 8.660254},
                        {deg: 30, facing: 'up', anchor}),
  facetZUp: Math.round(m.facetZ({x: 0, y: 40, w: 25, h: 30}, {deg: 30, facing: 'up'}, 0, [5, 70]) * 1000) / 1000,
  facetZLeft: Math.round(m.facetZ({x: 0, y: 40, w: 25, h: 30}, {deg: 45, facing: 'left'}, 0, [25, 50]) * 1000) / 1000,
  facetZRight: Math.round(m.facetZ({x: 0, y: 40, w: 25, h: 30}, {deg: 45, facing: 'right'}, 0, [0, 50]) * 1000) / 1000,
};
console.log(JSON.stringify(out));
