// How long kit/plan.js takes on the biggest plan outline the format allows: 16 bands of 128 points,
// 2048 in all. Each band is a polygon made of chords of an ellipse (a slightly smaller one for every
// band, so the bands step in from the flange), cut against the three-band box's section.
//
//   node plan-timing.mjs <kit/plan.js>      prints {points, bands, pieces, ms}
import { pathToFileURL } from 'node:url';

const P = await import(pathToFileURL(process.argv[2]).href);

const width = 600, depth = 281, height = 288;
const section = [[14, 0], [250, 0], [250, 132], [281, 132], [281, 155], [253, 155], [253, 288], [28, 288],
                 [28, 155], [0, 155], [0, 132], [14, 132]];
const bands = [];
for (let b = 0; b < 16; b++) {
  const rx = width / 2 - 2 * b, ry = depth / 2 - 1.5 * b, points = [];
  for (let i = 0; i < 128; i++) {
    const a = 2 * Math.PI * i / 128;                    // clockwise with y down
    points.push([+(width / 2 - rx * Math.cos(a)).toFixed(6), +(depth / 2 - ry * Math.sin(a)).toFixed(6)]);
  }
  bands.push({heights: [b * 18, (b + 1) * 18], points});
}
const points = bands.reduce((n, b) => n + b.points.length, 0);
const t0 = performance.now();
const got = P.planBody({width, depth, height, section, 'plan-outline': bands});
const outline = P.unionLoops(got.bands.map(b => b.points));
const ms = performance.now() - t0;
console.log(JSON.stringify({points, bands: bands.length, pieces: got.solid.reduce((n, s) => n + s.pieces.length, 0),
                            loops: outline.length, ms}));
