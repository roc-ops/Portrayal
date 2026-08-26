// A GIF89a encoder, in one file, with no dependencies.
//
// It exists for one reason: a blinking lamp. An exported SVG carries its
// @keyframes correctly and only a browser holding that file as a DOCUMENT will
// run them - an <img>, Word, PowerPoint and Inkscape all show one frozen frame.
// A GIF animates in every one of those places, so it is the only format that can
// SHOW a reader that a lamp is blinking rather than assert it in a caption.
//
// It is a picture of a drawing and not the drawing. Nothing here is addressable:
// no data-path, no data-states, no selectable text, no resolution but the one it
// was baked at. That is why it sits beside the SVG rather than replacing it, and
// why marks.js still rings every behaving lamp in the static exports - the GIF is
// for the audience that will watch it, the ring is for the reader who will print
// it.
//
// Written by hand rather than pulled in, because library/ is served as static
// files with no bundler, and a 250-line encoder is cheaper than a build step.
//
// Two decisions worth knowing before reading:
//
//   ONE GLOBAL PALETTE, built from every frame at once. A per-frame palette
//   would track each frame's colours more closely and would also make the lamp
//   shift hue between phases, because median cut would spend its 256 entries
//   differently on a frame with a green lamp than on one without.
//
//   FRAMES AFTER THE FIRST ARE CROPPED to the rectangle that actually changed.
//   The whole point of this file is a faceplate where two 2mm lamps move and
//   several million pixels do not, so the second frame is a few hundred bytes
//   rather than a second copy of the switch.

/**
 * @param spec.width   px
 * @param spec.height  px
 * @param spec.frames  Array<Uint8ClampedArray> - RGBA, width*height*4 each,
 *                     in the order they should play
 * @param spec.delay   ms between frames
 * @returns {Uint8Array} a complete image/gif file
 */
export function encodeGif({width, height, frames, delay = 500}) {
  if (!frames.length) throw new Error('a GIF needs at least one frame');
  const {palette, lookup} = quantise(frames);
  // The colour table is 2^n entries whatever the palette came out as; the spare
  // slots are black and are never referenced.
  const bits = Math.max(1, Math.ceil(Math.log2(Math.max(2, palette.length))));
  const tableSize = 1 << bits;
  const minCodeSize = Math.max(2, bits);

  const out = new Bytes();
  out.str('GIF89a');
  out.u16(width); out.u16(height);
  out.u8(0xf0 | (bits - 1));       // global table present, 8-bit colour, size
  out.u8(0);                       // background index
  out.u8(0);                       // pixel aspect ratio: none stated
  for (let i = 0; i < tableSize; i++) {
    const c = palette[i] || [0, 0, 0];
    out.u8(c[0]); out.u8(c[1]); out.u8(c[2]);
  }

  // Loop forever. A blink that plays once and stops is a static export with
  // extra steps.
  if (frames.length > 1) {
    out.str('\x21\xff\x0b');
    out.str('NETSCAPE2.0');
    out.u8(3); out.u8(1); out.u16(0); out.u8(0);
  }

  // GIF delays are in hundredths of a second, and every renderer clamps a delay
  // under ~2 to 10. Half a second is nowhere near that, but round rather than
  // truncate so a period that does not divide by 10 keeps its length.
  const cs = Math.max(2, Math.round(delay / 10));
  let previous = null;
  for (const rgba of frames) {
    const box = previous ? changed(previous, rgba, width, height)
                         : {x: 0, y: 0, w: width, h: height};
    previous = rgba;
    if (!box) continue;            // nothing moved; do not emit an empty frame

    const indices = new Uint8Array(box.w * box.h);
    let n = 0;
    for (let y = box.y; y < box.y + box.h; y++)
      for (let x = box.x; x < box.x + box.w; x++)
        indices[n++] = lookup[key555(rgba, (y * width + x) * 4)];

    if (frames.length > 1) {
      out.str('\x21\xf9\x04');
      // Disposal 1, "leave it there": every frame after the first paints only
      // its own rectangle over what is already on the canvas, and the loop back
      // to the full-size first frame is what clears the accumulated patches.
      out.u8(1 << 2);
      out.u16(cs);
      out.u8(0);                   // no transparent index
      out.u8(0);
    }
    out.u8(0x2c);                  // image descriptor
    out.u16(box.x); out.u16(box.y); out.u16(box.w); out.u16(box.h);
    out.u8(0);                     // no local table, not interlaced
    out.u8(minCodeSize);
    blocks(out, lzw(minCodeSize, indices));
    out.u8(0);                     // end of the sub-block chain
  }
  out.u8(0x3b);                    // trailer
  return out.bytes();
}

// ------------------------------------------------------------------- quantise

// 5 bits per channel. The drawings are flat vector art - a dozen real colours
// plus whatever antialiasing produced along the edges - so a 32768-bucket
// histogram is both small and a faithful summary, and it doubles as the cache
// that maps a pixel to a palette entry without a per-pixel nearest search.
const key555 = (d, i) => ((d[i] >> 3) << 10) | ((d[i + 1] >> 3) << 5) | (d[i + 2] >> 3);

function quantise(frames) {
  const count = new Uint32Array(32768);
  const sum = new Float64Array(32768 * 3);
  for (const rgba of frames)
    for (let i = 0; i < rgba.length; i += 4) {
      const k = key555(rgba, i);
      count[k]++;
      sum[k * 3] += rgba[i]; sum[k * 3 + 1] += rgba[i + 1]; sum[k * 3 + 2] += rgba[i + 2];
    }
  const used = [];
  for (let k = 0; k < 32768; k++) if (count[k]) used.push(k);

  // Fewer than 256 distinct buckets is the common case here - flat vector art on
  // a flat panel - and it is worth taking: one bucket per box means the palette
  // is the image's own colours and nothing shifts.
  const boxes = used.length > 256 ? medianCut(used, count, sum, 256)
                                  : used.map(k => [k]);

  const palette = [];
  const lookup = new Uint8Array(32768);
  boxes.forEach((box, index) => {
    let n = 0, r = 0, g = 0, b = 0;
    for (const k of box) {
      n += count[k];
      r += sum[k * 3]; g += sum[k * 3 + 1]; b += sum[k * 3 + 2];
      lookup[k] = index;
    }
    palette.push(n ? [Math.round(r / n), Math.round(g / n), Math.round(b / n)]
                   : [0, 0, 0]);
  });
  return {palette, lookup};
}

// Median cut: split the box whose pixels span the widest range in some channel,
// at the weighted median of that channel, until there are `want` boxes. Chosen
// over an octree because the failure mode matters more than the average error -
// an octree merges the least-populated leaves, and on a 4000x300 faceplate the
// least-populated colour is the 2mm lamp the whole picture is about.
function medianCut(used, count, sum, want) {
  const chan = (k, c) => (k >> (10 - c * 5)) & 31;
  const spread = box => {
    let best = -1, at = 0;
    for (let c = 0; c < 3; c++) {
      let lo = 31, hi = 0;
      for (const k of box) { const v = chan(k, c); if (v < lo) lo = v; if (v > hi) hi = v; }
      if (hi - lo > best) { best = hi - lo; at = c; }
    }
    return {range: best, channel: at};
  };
  const weight = box => box.reduce((a, k) => a + count[k], 0);

  let boxes = [used];
  while (boxes.length < want) {
    // Heckbert's two phases, and the first one is why this is not just "split
    // the biggest crowd". A blinking lamp is a few hundred saturated pixels in a
    // picture of several million grey ones; scored by population it never wins a
    // split and its colour is averaged into the chassis it sits on - the export
    // is then a drawing of a switch with no lamp on it, which is precisely the
    // failure this whole file exists to avoid. So the first half of the budget
    // goes to the widest boxes, which isolates the outliers, and only then does
    // population decide where the remaining detail goes.
    const byRange = boxes.length < want / 2;
    let pick = -1, score = 0;
    boxes.forEach((box, i) => {
      if (box.length < 2) return;
      const s = spread(box);
      if (s.range < 1) return;
      const v = byRange ? s.range : weight(box) * s.range;
      if (v > score) { score = v; pick = i; }
    });
    if (pick < 0) break;                 // nothing left that can be split
    const box = boxes[pick];
    const c = spread(box).channel;
    const sorted = box.slice().sort((a, b) => chan(a, c) - chan(b, c));
    const half = weight(sorted) / 2;
    let acc = 0, cut = 1;
    for (; cut < sorted.length; cut++) {
      acc += count[sorted[cut - 1]];
      if (acc >= half) break;
    }
    boxes.splice(pick, 1, sorted.slice(0, cut), sorted.slice(cut));
  }
  return boxes;
}

// The tightest rectangle in which two frames differ, or null if they do not.
function changed(a, b, width, height) {
  let x0 = width, y0 = height, x1 = -1, y1 = -1;
  for (let y = 0; y < height; y++) {
    const row = y * width * 4;
    for (let x = 0; x < width; x++) {
      const i = row + x * 4;
      if (a[i] === b[i] && a[i + 1] === b[i + 1] && a[i + 2] === b[i + 2] &&
          a[i + 3] === b[i + 3]) continue;
      if (x < x0) x0 = x;
      if (x > x1) x1 = x;
      if (y < y0) y0 = y;
      if (y > y1) y1 = y;
    }
  }
  return x1 < 0 ? null : {x: x0, y: y0, w: x1 - x0 + 1, h: y1 - y0 + 1};
}

// ----------------------------------------------------------------------- LZW

// Variable-width LZW, LSB-first, as GIF89a defines it. The code-size increase is
// the one part that cannot be reasoned out from first principles: it is a
// handshake with the decoder, which is always one entry behind the encoder, so
// the width grows just before the encoder creates the entry that would overflow
// it. Off by one in either direction and the file decodes to noise in some
// viewers and correctly in others, which is the worst way to be wrong.
function lzw(minCodeSize, indices) {
  const clear = 1 << minCodeSize;
  const eoi = clear + 1;
  let next = eoi + 1;
  let size = minCodeSize + 1;
  let table = new Map();
  const bits = new BitWriter();

  bits.write(clear, size);
  if (!indices.length) { bits.write(eoi, size); return bits.bytes(); }
  let code = indices[0];
  for (let i = 1; i < indices.length; i++) {
    const k = indices[i];
    const key = code * 256 + k;
    const found = table.get(key);
    if (found !== undefined) { code = found; continue; }
    bits.write(code, size);
    if (next === 4096) {
      bits.write(clear, size);
      next = eoi + 1;
      size = minCodeSize + 1;
      table = new Map();
    } else {
      if (next >= (1 << size)) size++;
      table.set(key, next++);
    }
    code = k;
  }
  bits.write(code, size);
  bits.write(eoi, size);
  return bits.bytes();
}

class BitWriter {
  constructor() { this.out = []; this.acc = 0; this.n = 0; }
  write(value, width) {
    this.acc |= value << this.n;
    this.n += width;
    while (this.n >= 8) {
      this.out.push(this.acc & 0xff);
      this.acc >>>= 8;
      this.n -= 8;
    }
  }
  bytes() {
    if (this.n > 0) { this.out.push(this.acc & 0xff); this.acc = 0; this.n = 0; }
    return this.out;
  }
}

// GIF carries its image data in sub-blocks of at most 255 bytes, each preceded
// by its own length.
function blocks(out, data) {
  for (let i = 0; i < data.length; i += 255) {
    const chunk = data.slice(i, i + 255);
    out.u8(chunk.length);
    for (const b of chunk) out.u8(b);
  }
}

// --------------------------------------------------------------------- output

class Bytes {
  constructor() { this.buf = new Uint8Array(1 << 16); this.n = 0; }
  room(k) {
    if (this.n + k <= this.buf.length) return;
    const bigger = new Uint8Array(Math.max(this.buf.length * 2, this.n + k));
    bigger.set(this.buf.subarray(0, this.n));
    this.buf = bigger;
  }
  u8(v) { this.room(1); this.buf[this.n++] = v & 0xff; }
  u16(v) { this.u8(v); this.u8(v >> 8); }
  str(s) { for (let i = 0; i < s.length; i++) this.u8(s.charCodeAt(i)); }
  bytes() { return this.buf.slice(0, this.n); }
}
