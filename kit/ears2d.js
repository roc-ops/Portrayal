// THE GENERIC RACK EAR IN 2D (#909), drawn by the page over a published face.
//
// A published face has no ears: the library draws a device between its ear
// folds, and render.py draws the generic L-bracket only under `--with ears`,
// which no published build is made with. A page that offers the ears as a
// choice - the Explorer and Annotate off by default, the Rack Builder on -
// draws them here instead, over the face it already holds, from the plan
// relief.js `genericEars` makes out of configs.json: the plan the 3D viewer
// builds its brackets from, and the plan spec/tools/portrayal/ears.py makes in
// Python. `earRects` is ears.py's `rects` and `earShapes` is render.py's
// `_generic_ears`, line for line, so the overlay is the drawing `--with ears`
// would have published; spec/tests/test_ears_overlay.py renders a device both
// ways and compares every attribute.
//
// WHAT THE OVERLAY IS NOT. It is not a part: no `data-path`, no `data-class`,
// and `pointer-events="none"`, so it is never picked, selected, listed in a
// tree or offered as a port or bay to a diagram export. It IS what is on
// screen, so an export of the live drawing (zones.js `readDrawing`, and so
// `toDrawio` and `toGraffle`) carries it as picture, with the viewBox grown to
// hold it - exports capture the state the reader set, as they do a seated
// optic or a lit lamp.
//
// ONE THING THIS CANNOT SEE, as genericEars cannot: whether the device places
// `common/rack-ear@1` of its own. Those ears are drawn only under the same
// `ears` tag, so a published face never holds them, and a generic pair here is
// the only pair on screen.

import { genericEars, faceDeclared, EAR } from './relief.js';

const SVG_NS = 'http://www.w3.org/2000/svg';
export const IDS = ['ear-left', 'ear-right'];

// Python's formatting, so a coordinate here is the string render.py writes.
// `round(v, 4)` and `.3f` round an exact tie to even, and JavaScript rounds it
// up; a tie is possible only where the value is an odd sixteenth (three
// places) or thirty-second (four), so only those take the even branch.
const tieEven = (v, k, frac) => {
  const m = v * k, f = Math.floor(m);
  if (m - f === 0.5 && Number.isInteger(v * frac)) return (f % 2 === 0 ? f : f + 1) / k;
  return null;
};
const round4 = v => tieEven(v, 1e4, 32) ?? Math.round(v * 1e4) / 1e4;
const fix3 = v => (tieEven(v, 1e3, 16) ?? v).toFixed(3);
// `:g`, six significant figures
export const fmtG = v => {
  const n = Number(Number(v).toPrecision(6));
  return Object.is(n, -0) ? '-0' : String(n);
};

/** render.py `_slot_path`: a stadium, semicircular ends on the short axis. */
export function slotPath(x, y, w, h) {
  if (w >= h) {
    const r = h / 2;
    return `M${fix3(x + r)} ${fix3(y)} H${fix3(x + w - r)} `
         + `A${fix3(r)} ${fix3(r)} 0 0 1 ${fix3(x + w - r)} ${fix3(y + h)} `
         + `H${fix3(x + r)} A${fix3(r)} ${fix3(r)} 0 0 1 ${fix3(x + r)} ${fix3(y)} Z`;
  }
  const r = w / 2;
  return `M${fix3(x + w)} ${fix3(y + r)} V${fix3(y + h - r)} `
       + `A${fix3(r)} ${fix3(r)} 0 0 1 ${fix3(x)} ${fix3(y + h - r)} `
       + `V${fix3(y + r)} A${fix3(r)} ${fix3(r)} 0 0 1 ${fix3(x + w)} ${fix3(y + r)} Z`;
}

/**
 * ears.py `rects`: the ear's outlines on one face, in that face's own
 * coordinates, as `[side, kind, x, y, w, h]`; `kind` is `flange`, `slot`,
 * `leg` or `edge`. `vw` and `vh` are the face's DECLARED size (`faceSize`).
 * Front and rear show each flange face-on beyond the body's sides; the sides
 * show the leg on the body and the flange edge-on; the top and the underside
 * show both edge-on. The rear and the underside are seen mirrored, so the
 * device's left ear is at the right of those drawings. Any other view (an
 * alternative front such as `front-lff-12`) gets nothing, as in render.py.
 */
export function earRects(p, view, vw, vh) {
  const fl = p.flange, t = p.t, h = p.h;
  const top = vh - p.y - h;                         // SVG y of the ear's top edge
  const z0 = p.at, z1 = Math.max(p.at, 0) + p.leg;  // the leg, back from the front
  const zf0 = p.at - t, zf1 = p.at;                 // the flange's thickness
  const out = [];
  if (view === 'front' || view === 'rear') {
    const mirrored = view === 'rear';
    IDS.forEach((side, i) => {
      const left = (i === 0) !== mirrored;
      const x = left ? -fl : vw;
      out.push([side, 'flange', x, top, fl, h]);
      const sx = left ? (x + fl - p.slot_x) : (x + p.slot_x);
      const [sw, sh] = p.slot;
      for (const cy of p.slots) out.push([side, 'slot', sx - sw / 2, top + h - cy - sh / 2, sw, sh]);
    });
  } else if (view === 'left' || view === 'right') {
    const side = view === 'left' ? IDS[0] : IDS[1];
    const atX = view === 'left' ? z => vw - z : z => z;
    let xs = [atX(z0), atX(z1)].sort((a, b) => a - b);
    out.push([side, 'leg', xs[0], top, xs[1] - xs[0], h]);
    xs = [atX(zf0), atX(zf1)].sort((a, b) => a - b);
    out.push([side, 'edge', xs[0], top, xs[1] - xs[0], h]);
  } else if (view === 'top' || view === 'bottom') {
    const mirrored = view === 'bottom';
    IDS.forEach((side, i) => {
      const left = (i === 0) !== mirrored;
      out.push([side, 'leg', left ? -t : vw, vh - z1, t, z1 - z0]);
      out.push([side, 'edge', left ? -fl : vw, vh - zf1, fl, t]);
    });
  }
  return out;
}

/**
 * render.py `_generic_ears` as data: per ear, its shapes with the attributes
 * render.py writes, and the box each covers (which grows the viewBox).
 * @returns {{groups: [{id, shapes: [{tag, attrs}]}], boxes: [[x0, y0, x1, y1]]}}
 */
export function earShapes(plan, view, vw, vh) {
  const groups = [], boxes = [];
  if (!plan) return {groups, boxes};
  const by = {};
  for (const [side, kind, x, y, w, h] of earRects(plan, view, vw, vh)) {
    const g = by[side] ||= (groups.push({id: side, shapes: []}), groups[groups.length - 1]);
    let shape;
    if (kind === 'slot') {
      const n = g.shapes.filter(s => s.tag === 'path').length + 1;
      shape = {tag: 'path', attrs: {d: slotPath(x, y, w, h), fill: EAR.HOLE, id: `${side}--slot-${n}`}};
    } else {
      shape = {tag: 'rect', attrs: {x: fmtG(round4(x)), y: fmtG(round4(y)),
                                    width: fmtG(round4(w)), height: fmtG(round4(h)),
                                    fill: plan.color || EAR.SILVER, stroke: EAR.EDGE, 'stroke-width': '0.4',
                                    id: `${side}--${kind}`}};
    }
    g.shapes.push(shape);
    boxes.push([x, y, x + w, y + h]);
  }
  return {groups, boxes};
}

/** A viewBox `[x, y, w, h]` grown round `boxes`, as render.py grows its
 *  extents: null when nothing reaches outside it. */
export function grownViewBox(vb, boxes) {
  const e = [vb[0], vb[1], vb[0] + vb[2], vb[1] + vb[3]];
  const was = e.join(' ');
  for (const [x0, y0, x1, y1] of boxes) {
    e[0] = Math.min(e[0], x0); e[1] = Math.min(e[1], y0);
    e[2] = Math.max(e[2], x1); e[3] = Math.max(e[3], y1);
  }
  return e.join(' ') === was ? null : [e[0], e[1], e[2] - e[0], e[3] - e[1]];
}

const viewBoxOf = svg => {
  const n = (svg.getAttribute('viewBox') || '').trim().split(/[\s,]+/).map(Number);
  return n.length === 4 && n.every(Number.isFinite) ? n : null;
};

/** The face a drawing declares, `[w, h]` in mm: `data-face-w`/`-h` where the
 *  drawing is bigger than its face (#865), else the viewBox's size. */
export function faceSize(svg) {
  const fw = parseFloat(svg.getAttribute('data-face-w'));
  const fh = parseFloat(svg.getAttribute('data-face-h'));
  if (fw > 0 && fh > 0) return [fw, fh];
  const vb = viewBoxOf(svg);
  return vb ? [vb[2], vb[3]] : null;
}

/** The front's declared width from a face's TEXT (a fetched front, when the
 *  front is not the face on screen): what the ear is sized against. */
export function frontWidthOfText(text) {
  const d = faceDeclared(text);
  if (d) return d[0];
  const vb = /<svg\b[^>]*\sviewBox="\s*[-\d.eE+]+[\s,]+[-\d.eE+]+[\s,]+([\d.eE+-]+)/.exec(text || '');
  return vb ? parseFloat(vb[1]) : null;
}

/** The plan for a device, from its configs.json and its front's declared
 *  width - null where it gets no generic ear (relief.js genericEars). */
export const earPlan = (meta, frontW) => genericEars(meta && meta.chassis, frontW);

// what the overlay changed on the root, so taking it off puts it back
const WAS = new WeakMap();
const ROOT_KEYS = ['viewBox', 'width', 'height', 'data-face-w', 'data-face-h'];

/** Take the overlay off and give the root back its own viewBox and size. */
export function clearEars(svg) {
  if (!svg) return;
  for (const g of svg.querySelectorAll('[data-overlay="ears"]')) g.remove();
  const was = WAS.get(svg);
  if (!was) return;
  WAS.delete(svg);
  for (const k of ROOT_KEYS)
    if (was[k] == null) svg.removeAttribute(k); else svg.setAttribute(k, was[k]);
}

/**
 * Draw the plan's ears over `svg`, the face `view`, replacing any drawn
 * before; with no plan this only clears. The ears go last, over the drawing,
 * in one `<g data-overlay="ears" pointer-events="none">` holding a `<g>` per
 * ear with render.py's ids, and the viewBox grows round them as render.py's
 * does - with `data-face-w`/`-h` naming the face, so a reader of the live
 * drawing still finds the face in it. Returns the number of shapes drawn.
 */
export function drawEars(svg, plan, view) {
  clearEars(svg);
  if (!svg || !plan) return 0;
  const size = faceSize(svg), vb = viewBoxOf(svg);
  if (!size || !vb) return 0;
  const {groups, boxes} = earShapes(plan, view, size[0], size[1]);
  if (!groups.length) return 0;
  const doc = svg.ownerDocument;
  const mk = (tag, attrs) => {
    const el = doc.createElementNS(SVG_NS, tag);
    for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
    return el;
  };
  const host = mk('g', {'data-overlay': 'ears', 'pointer-events': 'none', 'aria-hidden': 'true'});
  let n = 0;
  for (const g of groups) {
    const ge = mk('g', {id: g.id, 'data-generic': 'ear'});
    for (const s of g.shapes) { ge.appendChild(mk(s.tag, s.attrs)); n++; }
    host.appendChild(ge);
  }
  svg.appendChild(host);
  const grown = grownViewBox(vb, boxes);
  if (grown) {
    WAS.set(svg, Object.fromEntries(ROOT_KEYS.map(k => [k, svg.getAttribute(k)])));
    svg.setAttribute('viewBox', grown.map(fmtG).join(' '));
    svg.setAttribute('width', `${fmtG(grown[2])}mm`);
    svg.setAttribute('height', `${fmtG(grown[3])}mm`);
    svg.setAttribute('data-face-w', fmtG(size[0]));
    svg.setAttribute('data-face-h', fmtG(size[1]));
  }
  return n;
}
