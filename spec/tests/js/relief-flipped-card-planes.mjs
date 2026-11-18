// A card's plane on a flipped face (the underside: flipLX and flipLY), drawn with a
// stand-in canvas that holds pixels. A flipped face is rasterised mirrored in both axes.
// So the plane the viewer shows must be the half turn of the plane an unflipped face gives.
// Three faults broke that, each beside the facet clear:
//   a. the restyle re-cut (`recutPlane`) was cut upright, not turned with the first cut;
//   b. an off-centre card's art (`cropFace`) was cut at its drawing rect from the mirrored canvas;
//   c. a `shape` punch (a cavity, a seated module) replayed at drawing coordinates (`replayOnCrop`).
// The face is 100 x 140 mm at 4 px/mm and the card is 25 x 100 mm.
// The card has a blue fill and a light band at card y 40 to 70, whose footprint is cleared.
// It has a red 7 mm mark at its top left.
// buildFaceRelief needs a DOM and WebGL, so the functions it calls are run here.
import {createHash} from 'node:crypto';

globalThis.location = {search: ''};
globalThis.fetch = async () => ({ok: true, text: async () => '<svg/>'});
globalThis.CSS = {escape: s => s};

// ── a canvas that holds pixels, and an image that paints the rects of an svg ──────────
const blobs = new Map();
globalThis.Blob = class { constructor(parts) { this.text = parts.join(''); } };
globalThis.URL.createObjectURL = b => { const u = `blob:${blobs.size + 1}`; blobs.set(u, b.text); return u; };
globalThis.URL.revokeObjectURL = () => {};
globalThis.Image = class {
  set src(u) { this.svg = blobs.get(u); setTimeout(() => this.onload(), 0); }
};
const hex = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
// the svg painted at w x h pixels: its `rect` elements in order, over its viewBox
function paintSvg(svg, w, h) {
  const out = new Uint8ClampedArray(w * h * 4);
  const [vx, vy, vw, vh] = /viewBox="([^"]+)"/.exec(svg)[1].split(/\s+/).map(Number);
  const rects = [...svg.matchAll(/<rect\b([^>]*)>/g)].map(r => {
    const a = k => Number(new RegExp(`\\b${k}="([^"]+)"`).exec(r[1])[1]);
    return {x: a('x'), y: a('y'), w: a('width'), h: a('height'), c: hex(/fill="([^"]+)"/.exec(r[1])[1])};
  });
  for (let j = 0; j < h; j++) {
    for (let i = 0; i < w; i++) {
      const mx = vx + (i + 0.5) * vw / w, my = vy + (j + 0.5) * vh / h;
      for (const r of rects) {
        if (mx >= r.x && mx < r.x + r.w && my >= r.y && my < r.y + r.h) out.set([...r.c, 255], (j * w + i) * 4);
      }
    }
  }
  return out;
}
class Cv {
  constructor() { this.width = 0; this.height = 0; this._px = null; this._ctx = null; }
  get px() { return this._px ||= new Uint8ClampedArray(this.width * this.height * 4); }
  getContext() { return this._ctx ||= new Ctx(this); }
}
class Ctx {
  constructor(cv) { this.cv = cv; this.t = [1, 0, 0, 1, 0, 0]; this.globalCompositeOperation = 'source-over'; }
  translate(x, y) { const [a, , , d, e, f] = this.t; this.t = [a, 0, 0, d, e + x * a, f + y * d]; }
  scale(sx, sy) { const [a, , , d, e, f] = this.t; this.t = [a * sx, 0, 0, d * sy, e, f]; }
  setTransform(a, b, c, d, e, f) { this.t = [a, b, c, d, e, f]; }
  // the canvas pixel a drawn pixel lands on, or -1
  cell(x, y) {
    const [a, , , d, e, f] = this.t;
    const X = Math.min(a * x + e, a * (x + 1) + e), Y = Math.min(d * y + f, d * (y + 1) + f);
    return X < 0 || Y < 0 || X >= this.cv.width || Y >= this.cv.height ? -1 : (Y * this.cv.width + X) * 4;
  }
  clearRect(x, y, w, h) {
    for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) {
      const di = this.cell(x + i, y + j);
      if (di >= 0) this.cv.px.fill(0, di, di + 4);
    }
  }
  drawImage(src, ...a) {
    const isCv = src instanceof Cv;
    let sx = 0, sy = 0, dx, dy, dw, dh;
    if (a.length === 2) { [dx, dy] = a; dw = src.width; dh = src.height; }
    else if (a.length === 4) { [dx, dy, dw, dh] = a; }
    else { [sx, sy, dw, dh, dx, dy] = a; }
    const buf = isCv ? src.px : paintSvg(src.svg, dw, dh);
    const sw = isCv ? src.width : dw;
    const d = this.cv.px;
    for (let j = 0; j < dh; j++) for (let i = 0; i < dw; i++) {
      if (isCv && (sx + i >= src.width || sy + j >= src.height || sx + i < 0 || sy + j < 0)) continue;
      const si = ((sy + j) * sw + sx + i) * 4, di = this.cell(dx + i, dy + j);
      if (di < 0) continue;
      const sa = buf[si + 3] / 255, da = d[di + 3] / 255, op = this.globalCompositeOperation;
      if (op === 'source-over') {
        if (sa === 0) continue;
        const oa = sa + da * (1 - sa);
        for (let c = 0; c < 3; c++) d[di + c] = (buf[si + c] * sa + d[di + c] * da * (1 - sa)) / oa;
        d[di + 3] = oa * 255;
      } else {
        const na = op === 'destination-out' ? da * (1 - sa) : da * sa;
        d[di + 3] = na * 255;
        if (na === 0) d.fill(0, di, di + 4);
      }
    }
  }
}
globalThis.document = {createElement: () => new Cv()};
globalThis.performance ??= {now: () => Date.now()};

const m = await import('../../../kit/relief.js');

// ── the fixture ──────────────────────────────────────────────────────────────────────
const PX = 4, FW = 100, FH = 140, CW = 25, CH = 100;
const GREY = '#1b1d20', BLUE = '#2f6fd0', LIGHT = '#9ec3ff', RED = '#e03030';
const rect = (x, y, w, h, c) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${c}"/>`;
const svg = (w, h, body) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}">${body}</svg>`;
const cardArt = (x, y) => rect(x, y, CW, CH, BLUE) + rect(x, y + 40, CW, 30, LIGHT) + rect(x + 1, y + 1, 7, 7, RED);
// the face carries an orange strip on its authored top edge and a green one on its left edge
const faceText = (x, y) => svg(FW, FH, rect(0, 0, FW, FH, GREY) + rect(0, 0, FW, 6, '#d09020') +
                                       rect(0, 0, 6, 60, '#20c070') + cardArt(x, y));
const cardText = svg(CW, CH, cardArt(0, 0));
// a pocket of an L shape, 10 x 8 mm, at card x 3, y 80
const L = svg(10, 8, rect(0, 0, 10, 3, '#000000') + rect(0, 3, 3, 5, '#000000'));
const POCKET = {x: 3, y: 80, w: 10, h: 8};

// the plane of a card placed at (x, y) on the face, as the viewer cuts it
async function plane({x, y, flip, open, restyled, pocket = false}) {
  const cv = await m.rasterize(faceText(x, y), FW, FH, PX, flip, flip);
  const art = document.createElement('canvas');
  art.width = cv.width; art.height = cv.height;
  art.getContext('2d').drawImage(cv, 0, 0);
  const pf = {x, y, w: CW, h: CH};
  const punches = [{kind: 'rect', x, y: y + 40, w: CW, h: 30, facet: 'card--band'}];
  const face = cv.getContext('2d');
  face.clearRect(...m.punchRectPx(punches[0], 0, 0, PX));
  if (pocket) {
    const p = {kind: 'shape', svg: L, x: x + POCKET.x, y: y + POCKET.y, w: POCKET.w, h: POCKET.h};
    punches.push(p);
    face.globalCompositeOperation = 'destination-out';
    face.drawImage(await m.rasterSource(L, p.w, p.h, PX), Math.round(p.x * PX), Math.round(p.y * PX));
    face.globalCompositeOperation = 'source-over';
  }
  const crop = m.cropFace(open ? art : cv, pf, FW, FH, flip, flip, PX);
  if (open) await m.replayOnCrop(crop, punches, pf, PX, flip, flip);
  if (!restyled) return crop;
  return m.recutPlane(cardText, pf, punches, PX, flip, flip);
}

// ── what a plane reads ───────────────────────────────────────────────────────────────
const hash = cv => createHash('sha256').update(cv.px).update(`${cv.width}x${cv.height}`).digest('hex').slice(0, 24);
const mm = v => v / PX;
function read(cv) {
  const {width: w, height: h, px} = cv;
  let red = null, blue = 0, grey = 0;
  const bands = [];
  let band = null;
  for (let j = 0; j < h; j++) {
    let x0 = Infinity, x1 = -1;
    for (let i = 0; i < w; i++) {
      const k = (j * w + i) * 4, [r, g, b, a] = px.subarray(k, k + 4);
      if (a < 25) { x0 = Math.min(x0, i); x1 = Math.max(x1, i); continue; }
      if (r > 190 && g < 90 && b < 90) {
        red = red ? [Math.min(red[0], i), Math.min(red[1], j), Math.max(red[2], i), Math.max(red[3], j)] : [i, j, i, j];
      } else if (b > 150 && r < 140) blue++;
      else if (r === 0x1b && g === 0x1d && b === 0x20) grey++;
    }
    if (x1 >= 0) { band = band ? {...band, y1: j, x0: Math.min(band.x0, x0), x1: Math.max(band.x1, x1)} : {x0, x1, y0: j, y1: j}; }
    else if (band) { bands.push(band); band = null; }
  }
  if (band) bands.push(band);
  return {
    clear: bands.map(b => [mm(b.x0), mm(b.y0), mm(b.x1 + 1), mm(b.y1 + 1)]),
    mark: red && [mm(red[0]), mm(red[1]), mm(red[2] + 1), mm(red[3] + 1)],
    blueFrac: +(blue / (w * h)).toFixed(3), greyFrac: +(grey / (w * h)).toFixed(3),
    hash: hash(cv),
  };
}
// the half turn of a canvas: what a plane on a flipped face must be, set against the unflipped one
function halfTurn(cv) {
  const t = new Cv();
  t.width = cv.width; t.height = cv.height;
  const n = cv.width * cv.height;
  for (let i = 0; i < n; i++) t.px.set(cv.px.subarray(i * 4, i * 4 + 4), (n - 1 - i) * 4);
  return t;
}

// ── every case, flipped and not ──────────────────────────────────────────────────────
const out = {};
const POS = {centred: [37.5, 20], off: [10, 10]};
for (const [pos, [x, y]] of Object.entries(POS)) {
  for (const open of [false, true]) {
    for (const restyled of [false, true]) {
      for (const pocket of [false, true]) {
        const key = `${pos}-${open ? 'open' : 'closed'}-${restyled ? 'restyled' : 'first'}${pocket ? '-pocket' : ''}`;
        const flat = await plane({x, y, flip: false, open, restyled, pocket});
        const turned = await plane({x, y, flip: true, open, restyled, pocket});
        out[key] = {flipped: read(turned), flat: read(flat), isHalfTurnOfFlat: hash(halfTurn(flat)) === hash(turned)};
      }
    }
  }
}
console.log(JSON.stringify(out));
