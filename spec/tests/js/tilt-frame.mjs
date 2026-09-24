globalThis.location = { search: '' };
globalThis.fetch = async () => ({ ok: true, text: async () => '<svg/>' });
const m = await import('../../../kit/relief.js');
const apply = (e, [x, y, z]) => [e[0]*x + e[4]*y + e[8]*z + e[12],
                                 e[1]*x + e[5]*y + e[9]*z + e[13],
                                 e[2]*x + e[6]*y + e[10]*z + e[14]];
const r = v => v.map(n => Math.round(n * 1000) / 1000);
const up = m.tiltFrame({deg: 30, facing: 'up', anchor: [10, 50], z0: 2});
const left = m.tiltFrame({deg: 45, facing: 'left', anchor: [10, 50], z0: 0});
const out = {
  anchorStays: r(apply(up, [10, 50, 0])),
  tenBelow: r(apply(up, [10, 60, 0])),          // 10 true mm down the slope
  normalOut: r(apply(up, [10, 50, 1])),         // 1 mm out of the part's face
  leftTenRight: r(apply(left, [20, 50, 0])),
  unproj: m.unproject({x: 12, y: 50 + 8.660254, w: 5, h: 8.660254},
                      {deg: 30, facing: 'up', anchor: [10, 50]}),
  facetZ: Math.round(m.facetZ({x: 0, y: 40, w: 25, h: 30}, {deg: 30, facing: 'up'}, 0, [5, 70]) * 1000) / 1000,
};
console.log(JSON.stringify(out));
