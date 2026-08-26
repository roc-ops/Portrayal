// A drawing is mostly background, and the background sorts last.
//
// The S9510-28DC's export ground is a cream (220, 214, 197) - high in all three
// channels - covering more than half the pixels. medianCut sorted it last, its
// weighted-median scan never reached half because the scan skips the final
// bucket, and the split returned the whole box plus an EMPTY one. Empty boxes
// still count toward the 256 budget and every one of them takes the [0,0,0]
// palette branch, so a 1642-colour drawing encoded to four colours and lost
// every lamp in it - which is the one thing an animated export exists to show.
import { encodeGif } from '../../../library/viewer/gif.js';

const W = 200, H = 200, N = W * H;
const frame = new Uint8ClampedArray(N * 4);
for (let i = 0; i < N; i++) {
  const o = i * 4;
  if (i < N * 0.6) {                 // dominant, and highest in every channel
    frame[o] = 220; frame[o + 1] = 214; frame[o + 2] = 197;
  } else {                           // a spread of darker minority colours
    frame[o] = (i % 29) * 5; frame[o + 1] = (i % 17) * 9; frame[o + 2] = (i % 23) * 7;
  }
  frame[o + 3] = 255;
}

const bytes = encodeGif({ width: W, height: H, frames: [frame], delay: 500 });
if (String.fromCharCode(...bytes.slice(0, 6)) !== 'GIF89a') throw new Error('not a GIF');

// global colour table: header 6 + logical screen descriptor 7, size 2^(n+1)
const packed = bytes[10];
const entries = 1 << ((packed & 7) + 1);
const table = bytes.slice(13, 13 + entries * 3);
let black = 0, distinct = new Set();
for (let i = 0; i < entries; i++) {
  const r = table[i * 3], g = table[i * 3 + 1], b = table[i * 3 + 2];
  if (r === 0 && g === 0 && b === 0) black++;
  distinct.add(`${r},${g},${b}`);
}
console.log(JSON.stringify({ entries, black, distinct: distinct.size }));
