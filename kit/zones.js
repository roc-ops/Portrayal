// Finding the things a cable can be drawn to in a compiled face: its ports, and
// the bays that hold the cards whose ports they are, each with its box in the
// drawing's own millimetres and the model's words about it.
//
// The draw.io and OmniGraffle exports are both built on this, and so is
// anything else that has to put a connectable shape over a picture of a face.
// It reads the compiled SVG and nothing else.

import { toSvg } from './marks.js';

// ── reading the compiled drawing ─────────────────────────────────────────
// A real transform stack, because the compiled output is not only translates.
// A C40G mounts its supervisors on their side -
//   transform="translate(214.75,118.645) rotate(90) translate(-15.235,-172.75)"
// - and reading just the first translate put twelve of its ports 80 mm below
// the chassis. 65 rotates and 8 scales across the current faces.
//
// Matrices are SVG's [a b c d e f]: x' = a·x + c·y + e, y' = b·x + d·y + f.
const I = [1, 0, 0, 1, 0, 0];
const mul = (m, n) => [
  m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1],
  m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3],
  m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5],
];
const apply = (m, x, y) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];

function parseTransform(str) {
  let m = I;
  if (!str) return m;
  const re = /(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)/g;
  let t;
  while ((t = re.exec(str))) {
    const n = t[2].split(/[\s,]+/).map(Number).filter(Number.isFinite);
    const rad = d => d * Math.PI / 180;
    switch (t[1]) {
      case 'matrix':    if (n.length >= 6) m = mul(m, n.slice(0, 6)); break;
      case 'translate': m = mul(m, [1, 0, 0, 1, n[0] || 0, n[1] || 0]); break;
      case 'scale':     m = mul(m, [n[0] ?? 1, 0, 0, n[1] ?? n[0] ?? 1, 0, 0]); break;
      case 'skewX':     m = mul(m, [1, 0, Math.tan(rad(n[0] || 0)), 1, 0, 0]); break;
      case 'skewY':     m = mul(m, [1, Math.tan(rad(n[0] || 0)), 0, 1, 0, 0]); break;
      case 'rotate': {
        const c = Math.cos(rad(n[0] || 0)), s2 = Math.sin(rad(n[0] || 0));
        const R = [c, s2, -s2, c, 0, 0];
        // rotate(a cx cy) is translate(cx cy) rotate(a) translate(-cx -cy)
        m = (n.length >= 3)
          ? mul(mul(mul(m, [1, 0, 0, 1, n[1], n[2]]), R), [1, 0, 0, 1, -n[1], -n[2]])
          : mul(m, R);
        break;
      }
    }
  }
  return m;
}

// THE REAL OUTLINE, NOT THE RECTANGLES INSIDE IT. The walk in readSvg measures
// rects and circles and nothing else, because a path has no box until something
// lays it out. That was right for an SFP cage, which is one rect, and wrong for
// every jack drawn as a housing: an RJ45 is mostly path with one small latch
// rect in it, so on the S9510-28DC the TOD, BITS and console jacks came out as
// 7.6 x 2.3 mm strips across the top of a 15.8 x 13.2 mm jack - 8% of it - and
// a line could not be landed on them in draw.io or in OmniGraffle. The coax
// timing inputs fared little better, at about 55%. A port whose art is ALL path
// had no box at all and was dropped.
//
// The browser can measure a whole group, so where there is a browser it does,
// with the same CTM arithmetic relief.js uses and all four corners so a rotated
// card still gets its full box. Where there is no document - a test runner, a
// worker - the walked box stands, which is what every export had before.
function layoutZones(text, zones) {
  if (typeof document === 'undefined' || !zones.length) return;
  const div = document.createElement('div');
  div.style.cssText = 'position:absolute;left:-10000px;top:0;width:1000px;visibility:hidden';
  div.innerHTML = text;
  document.body.append(div);
  try {
    const svg = div.querySelector('svg');
    const rootCtm = svg && svg.getScreenCTM();
    if (!rootCtm) return;
    const inv = rootCtm.inverse();
    for (const z of zones) {
      const el = svg.querySelector(`[id="${CSS.escape(z.id)}"]`);
      if (!el || typeof el.getBBox !== 'function') continue;
      let b;
      try { b = el.getBBox(); } catch (e) { continue; }
      if (!(b.width > 0 && b.height > 0)) continue;
      const m = inv.multiply(el.getScreenCTM());
      let x = Infinity, y = Infinity, x1 = -Infinity, y1 = -Infinity;
      for (const [px, py] of [[b.x, b.y], [b.x + b.width, b.y],
                              [b.x + b.width, b.y + b.height], [b.x, b.y + b.height]]) {
        const ax = m.a * px + m.c * py + m.e, ay = m.b * px + m.d * py + m.f;
        x = Math.min(x, ax); y = Math.min(y, ay); x1 = Math.max(x1, ax); y1 = Math.max(y1, ay);
      }
      Object.assign(z, {x, y, x1, y1});
    }
  } finally { div.remove(); }
}

/** `layout: false` keeps the rect-and-circle walk alone - the old answer, kept
 *  so the two can be compared, and used wherever there is no document. */
export function readSvg(text, {layout = true} = {}) {
  const doc = new DOMParser().parseFromString(text, 'image/svg+xml');
  const root = doc.documentElement;
  if (root.querySelector('parsererror')) throw new Error('unparseable SVG');
  const vb = (root.getAttribute('viewBox') || '0 0 0 0').split(/\s+/).map(Number);
  const zones = [];
  const num = (el, a, d = 0) => {
    const v = parseFloat(el.getAttribute(a));
    return Number.isFinite(v) ? v : d;
  };
  // A rotated rectangle's bounds are the bounds of its transformed corners.
  const grow = (z, ctm, x, y, w, h) => {
    if (!z) return;
    for (const [px, py] of [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]) {
      const [ax, ay] = apply(ctm, px, py);
      z.x = Math.min(z.x, ax); z.y = Math.min(z.y, ay);
      z.x1 = Math.max(z.x1, ax); z.y1 = Math.max(z.y1, ay);
    }
  };
  (function walk(el, ctm, zone) {
    ctm = mul(ctm, parseTransform(el.getAttribute?.('transform')));
    const tag = el.tagName;
    // What a thing IS comes from the model, not from the shape of its id.
    // Guessing by name found 1 port on an ASR 9001 (whose ports are named tod,
    // svc-lan, sync-0) and none at all on a C100G, whose 44 ports live on
    // seated modules and are named front-6--module--xg0.
    const cls = el.getAttribute?.('data-class');
    let {port, bay} = zone;
    // Outermost wins WITHIN a class, not across classes. A cage inside a port
    // is part of that port - not a second thing to plug into - but a port on a
    // card seated in a bay is very much its own port: that is where the 44
    // ports of a C100G live, named front-6--module--xg0, and nesting them
    // under their bay loses every one of them.
    if (tag === 'g' && el.id) {
      // The model's own words about the thing, carried through. A miniature
      // symbol needs to know which bay a port belongs to and what kind of port
      // it is; geometry alone cannot say either.
      const meta = {
        path: el.getAttribute('data-path') || el.id,
        group: el.getAttribute('data-group') || null,
        media: el.getAttribute('data-media') || null,
        speed: el.getAttribute('data-speed') || null,
        model: el.getAttribute('data-model') || null,
      };
      if (cls === 'port' && !port) {
        port = {id: el.id, cls, ...meta,
                x: Infinity, y: Infinity, x1: -Infinity, y1: -Infinity};
        zones.push(port);
      } else if (cls === 'bay' && !bay) {
        bay = {id: el.id, cls, ...meta,
               x: Infinity, y: Infinity, x1: -Infinity, y1: -Infinity};
        zones.push(bay);
      }
    }
    const z = port || bay;
    if (tag === 'rect') {
      const x = num(el, 'x'), y = num(el, 'y');
      const w = num(el, 'width'), h = num(el, 'height');
      grow(port, ctm, x, y, w, h); if (bay !== port) grow(bay, ctm, x, y, w, h);
    } else if (tag === 'circle') {
      const r = num(el, 'r');
      const x = num(el, 'cx') - r, y = num(el, 'cy') - r;
      grow(port, ctm, x, y, 2 * r, 2 * r); if (bay !== port) grow(bay, ctm, x, y, 2 * r, 2 * r);
    } else if (tag === 'path' || tag === 'line' || tag === 'polygon') {
      // No bbox without laying it out; a port is never only a path, so its
      // rects carry it. Noted so the count stays honest if that changes.
      if (z) z.hasPath = true;
    }
    for (const c of el.children) walk(c, ctm, {port, bay});
  })(root, I, {port: null, bay: null});
  if (layout) layoutZones(text, zones);
  const sized = zones
    .filter(z => Number.isFinite(z.x))
    .map(z => ({id: z.id, cls: z.cls, path: z.path, group: z.group,
                media: z.media, speed: z.speed, model: z.model,
                x: z.x, y: z.y, w: z.x1 - z.x, h: z.y1 - z.y}));
  return {vb, zones: sized};
}

/** The things a cable can be drawn to: ports, and optionally the bays that hold
 *  the cards whose ports they are. Sorted so port-2 precedes port-10. */
export function portsOf(zones, {bays = false} = {}) {
  return zones
    .filter(z => z.cls === 'port' || (bays && z.cls === 'bay'))
    // Bays FIRST, then ports. A later sibling draws on top in draw.io, and a
    // bay is a big cell containing the ports of whatever is seated in it - so
    // sorting the two together by id lets a slot land above its own card's
    // ports and swallow every click meant for them.
    .sort((a, b) =>
      (a.cls === b.cls ? 0 : a.cls === 'bay' ? -1 : 1) ||
      a.id.length - b.id.length || a.id.localeCompare(b.id));
}

/**
 * Zones narrowed to a viewBox: clipped to it, and dropped where nothing is left.
 *
 * A cropped export is a viewBox over part of the face, and every port outside it
 * is still in the file - clipped by the crop's clip-path, but present. Left in,
 * those ports become connection points floating beside the picture, in the
 * diagram, over nothing.
 */
export function within(zones, vb) {
  const [vx, vy, vw, vh] = vb;
  const out = [];
  for (const z of zones) {
    const x = Math.max(z.x, vx), y = Math.max(z.y, vy);
    const x1 = Math.min(z.x + z.w, vx + vw), y1 = Math.min(z.y + z.h, vy + vh);
    if (x1 > x && y1 > y) out.push({...z, x, y, w: x1 - x, h: y1 - y});
  }
  return out;
}

/** Fetch a compiled face and read it, once per url. */
const SEEN = new Map();
export async function loadFace(url) {
  if (!SEEN.has(url)) {
    SEEN.set(url, fetch(url).then(async r => {
      if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
      const text = await r.text();
      const {vb, zones} = readSvg(text);
      return {text, vb, zones};
    }).catch(e => { SEEN.delete(url); throw e; }));
  }
  return SEEN.get(url);
}

/**
 * A LIVE drawing, as the exports want it: the self-contained SVG marks.js
 * writes, with whatever is seated, lit, highlighted or cropped in it, and the
 * ports and bays read back out of that same text.
 *
 * READ FROM THE EXPORT, NOT FROM THE STAGE. The two differ - a crop is a new
 * viewBox, a legend grows one, a seated optic is a part the compiled file never
 * had - and the connection points have to agree with the picture they sit on,
 * which is the exported one.
 *
 * The clone loses two things a host page put there and a file must not carry:
 * the root's inline style, where a shell writes its zoom and pan (an exported
 * root with a transform arrives panned off its own viewBox), and the shell's
 * `.halo` selection ring, which is painted by the shell's stylesheet and so,
 * in a file opened anywhere else, falls back to a solid black rectangle over
 * whatever was selected.
 *
 * @param svgRoot  the drawing's <svg>, live in the document
 * @param doc      a marks document, or nothing for the drawing as it stands
 * @returns {{text, vb, zones, ports}}  ports and bays, clipped to the viewBox
 */
export function readDrawing(svgRoot, doc = {}) {
  const c = svgRoot.cloneNode(true);
  c.removeAttribute('style');
  for (const h of c.querySelectorAll('.halo')) h.remove();
  const text = toSvg(c, doc);
  const {vb, zones} = readSvg(text);
  return {text, vb, zones, ports: portsOf(within(zones, vb), {bays: true})};
}
