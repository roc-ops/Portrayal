// ONE FACE OF A RACK, drawn from data: the rails with this rack's holes, and
// every item on it. The Rack Builder draws both faces with it; the showcase's
// build2dElevation is an adapter over it, so the two can never disagree about
// what a rail or a device looks like.
//
// What a pane shows of an item (feedback round 3 §2 - there is no more
// "ghost"; every device shows a real panel on both faces):
//   mounted  - on this face: its outward panel, plus rack ears when `ears`
//   through  - on the other face: its far panel, whether or not it reaches
//   missing  - no compiled drawing for that panel: an outline saying so
//
// Every device goes through configuredFace, with its own swaps and fields.

import {RU, RAIL_W, OPENING, HOLE_DY, HOLE_SQUARE, HOLE_ROUND, SIDES} from '../rails.js';
import {earHoles} from './ear-holes.js';
import {configuredFace, earPlanFor, zeroUModuleEnds, setDist} from './face.js';
import {dom} from './dom.js';
import {paintFace, paintMaps} from './settable.js';
import {uLabel, zeroUOf, zeroUBottomMm} from '../model.js';
import {isRackMount} from '../export-data.js';
import {itemBox, itemsWithU} from '../fit.js';
import {faceOfAt, sideOfAt, STANDOFF, zeroUEntries} from '../zero-u.js';
import {createView} from './view.js';

// Which of the device's own panels faces `pane`. On its own face that is its
// front, unless it is turned; on the other face, the reverse.
export const panelFor = (item, pane) => (((item.face === pane) !== !!item.turned) ? 'front' : 'rear');

// RAIL COLOURS. The showcase draws its rails from the site's theme tokens, so
// they follow light and dark mode. The Rack Builder draws them as metal:
// fixed colours that stay silver in either theme, taken from site/rack3d.js's
// own rail, hole, ear and screw materials so 2D and 3D agree.
const THEMED = {rail: 'var(--pt-surface-2)', railLine: 'var(--pt-line)', hole: 'var(--pt-ground)',
                num: 'var(--pt-ink-muted)', ear: 'var(--pt-ink-muted)', earOpacity: 0.35,
                earLine: 'var(--pt-ink-muted)', screw: 'var(--pt-ink-muted)', screwLine: 'var(--pt-ink)'};
const METAL = {rail: '#B9BFC6', railLine: '#8D949C', hole: '#15181B', num: '#2B3036',
               ear: '#A8AEB5', earOpacity: 1, earLine: '#6F767E', screw: '#8D949C', screwLine: '#3A4047'};

function drawRails(svgEl, out, frame, baseRU, totalH, C = THEMED) {
  const X = x => x + OPENING / 2;
  const round = frame.holes?.style === 'tapped' || frame.holes?.style === 'round';   // (round: unthreaded, rack file version 4)
  for (const s of SIDES) {
    out.append(svgEl('rect', {x: X(Math.min(s.inner, s.outer)), y: 0, width: RAIL_W, height: totalH,
      'data-rail': s.side, fill: C.rail, stroke: C.railLine, 'stroke-width': 1}));
  }
  for (let i = 0; i < frame.heightRU; i++) {
    const u = baseRU + i;
    const yBottom = totalH - i * RU;
    for (const s of SIDES) {
      const x0 = X(Math.min(s.inner, s.outer));
      out.append(svgEl('line', {x1: x0, y1: yBottom - RU, x2: x0 + RAIL_W, y2: yBottom - RU,
        stroke: C.railLine, 'stroke-width': 0.8}));
      for (const dy of HOLE_DY) {
        const hole = {fill: C.hole, stroke: C.railLine, 'stroke-width': 0.5,
                      'data-rail-hole': s.side};
        out.append(round
          ? svgEl('circle', {cx: X(s.hole), cy: yBottom - dy, r: HOLE_ROUND / 2, ...hole})
          : svgEl('rect', {x: X(s.hole) - HOLE_SQUARE / 2, y: yBottom - dy - HOLE_SQUARE / 2,
                           width: HOLE_SQUARE, height: HOLE_SQUARE, rx: 0.6, ...hole}));
      }
      const t = svgEl('text', {x: X(s.number), y: yBottom - RU / 2 + 4,
        'text-anchor': 'middle', 'font-family': 'IBM Plex Mono, monospace',
        'font-size': 11, 'font-weight': 500, fill: C.num, 'data-rail-num': s.side});
      t.textContent = String(uLabel(frame, u));
      out.append(t);
    }
  }
}

// The selection ring is drawn, not styled: CSS outline does not render on
// an SVG group.
export const ring = (svgEl, top, ruH) => svgEl('rect', {x: -3, y: top - 1.5, width: OPENING + 6, height: ruH * RU + 3,
  rx: 3, fill: 'none', stroke: 'var(--pt-brass)', 'stroke-width': 2.5, class: 'rk-sel-ring',
  'pointer-events': 'none'});

// A MISSING FACE'S OUTLINE follows the theme on screen. On paper (the
// exported sheet, fixed ink on white) it is fixed too, like the metal rails:
// a sheet exported from a dark page must not carry dark-theme paint.
const OUTLINE = {fill: 'var(--pt-surface-2)', ink: 'var(--pt-ink-muted)'};
const OUTLINE_PAPER = {fill: '#E4E7EA', ink: '#5B636B'};

function outline(svgEl, top, ruH, text, attrs, C = OUTLINE) {
  const g = svgEl('g', attrs);
  g.append(svgEl('rect', {x: 0.5, y: top + 0.5, width: OPENING - 1, height: ruH * RU - 1, rx: 2,
    fill: C.fill, 'fill-opacity': 0.35, stroke: C.ink,
    'stroke-width': 1, 'stroke-dasharray': '4 3'}));
  const t = svgEl('text', {x: OPENING / 2, y: top + ruH * RU / 2 + 4, 'text-anchor': 'middle',
    'font-size': 11, 'font-family': 'IBM Plex Mono, monospace', fill: C.ink});
  t.textContent = text;
  g.append(t);
  return g;
}

// RACK EARS (feedback round 3 §2): an L-bracket flange over each rail at a
// mounted device's height, drawn AFTER the device group so it overlaps its
// edges like a real ear. Geometry matches rack3d.js's rackEars and the rails
// in rails.js - the flange runs from the device's own edge (the opening's
// side, x=0 or x=OPENING) out across the rail to just past the hole column
// (SIDES[].hole), and a screw head sits at the first and last hole (HOLE_DY)
// of every U the device covers.
//
// Fix round 1: the flange in the rail's own surface-2/line colours was
// nearly invisible against the rail itself. It reads as metal now - a
// muted-ink flange (not full ink, so it stays a shade behind the device's
// own panel) with a darker screw head and a short slot line.
const EAR_OVERHANG = 3; // mm the flange runs past the hole centre, so the screw head sits inside it
const SCREW_SLOT = 1.6; // mm half-length of each screw head's slot line

// `plan` is the kit's generic-ear plan (face.js earPlanFor), or null where
// the device's ears are its own - built into a face as wide as the rack, or
// stated `behind`. A null plan draws NO flange, only the screw heads: the
// device is still bolted to the rail at every U, as the BOM counts it.
//
// THE FLANGE STARTS AT THE FACE'S OWN EDGE (#168), `face` = [left, right] in
// pane x, as the plan's flange does (ears2d.js: from the face's side out to
// the 482.6 mm rack face) and as rack3d.js's flange does (from W/2 out). It
// started at the opening's edge, so every device narrower than the 450.85 mm
// opening - 186 of the 187 that take a generic ear - showed a strip of rail
// between its body and each ear: 9.75 mm on the 431.35 mm XCU10, 115 mm on a
// half-width box. Without a face (a missing drawing) it keeps the opening.
//
// THE EAR IS AS TALL AS THE SPAN ITS ITEM FILLS (the kit's fit.js itemBox:
// `lo` and `hi`), and is fixed at the rail holes that span holds (ear-holes.js,
// over the kit's holesIn). `span` = {top, bottom} in pane y and `holes`, the
// pane y of each hole: one for a half-unit panel, in the half it is in.
function drawEars(svgEl, out, item, span, C = THEMED, plan = null, face = [0, OPENING]) {
  const color = plan?.color || null;
  const X = x => x + OPENING / 2;
  const {top, bottom, holes: screwYs} = span;
  const g = svgEl('g', {class: 'rk-ears', 'data-ears-for': item.id, 'data-item-id': item.id,
                        'data-ears': plan ? 'generic' : 'built-in',
                        ...(color ? {'data-ear-color': color} : {}), 'pointer-events': 'all'});
  for (const s of SIDES) {
    const holeX = X(s.hole);
    const x0 = s.side === 'left' ? holeX - EAR_OVERHANG : face[1];
    const x1 = s.side === 'left' ? face[0] : holeX + EAR_OVERHANG;
    if (plan) g.append(svgEl('rect', {x: x0, y: top, width: x1 - x0, height: bottom - top,
      fill: color || C.ear, 'fill-opacity': C.earOpacity, stroke: C.earLine, 'stroke-width': 1}));
    for (const cy of screwYs) {
      g.append(svgEl('circle', {cx: holeX, cy, r: HOLE_ROUND / 2,
        fill: C.screw, stroke: C.screwLine, 'stroke-width': 0.6}));
      g.append(svgEl('line', {x1: holeX - SCREW_SLOT, y1: cy, x2: holeX + SCREW_SLOT, y2: cy,
        stroke: C.screwLine, 'stroke-width': 0.5}));
    }
  }
  out.append(g);
}

// U at a given SVG y coordinate, the inverse of drawElevation's own layout
// (y=0 is the top rail; a U's bottom sits at totalH - (u - baseRU) * RU).
// The pure half of drag support (spec round 2 §1): the drag controller in
// drag.js maps a pointer's screen position into this space, this then maps
// that into a U.
export function uAtY(frame, y, baseRU = 1) {
  const totalH = frame.heightRU * RU;
  const i = Math.floor((totalH - y) / RU);
  return Math.min(baseRU + frame.heightRU - 1, Math.max(baseRU, baseRU + i));
}
// THE HALF UNIT at a given SVG y: a position as the rack file holds one (rack
// file version 4: `ru` in steps of 0.5, 12 the bottom of U12 and 12.5 its
// middle). What a drag of a device that may start on a half asks, and a click
// on a unit one half of which is taken.
export function halfAtY(frame, y) {
  const totalH = frame.heightRU * RU;
  const i = Math.floor((totalH - y) / (RU / 2));
  return Math.min(frame.heightRU + 0.5, Math.max(1, 1 + i / 2));
}

// ZERO-U PARTS (the kit's rack/zero-u.js): a duct standing beside an upright, drawn
// as it stands, portrait, outside the rail. `zeroU` entries are {id, ref, cfg,
// label, at, ru, w, h}: w and h the part's chassis width and drawn height in mm,
// ru its bottom U. A two-post's uprights are seen from both panes (its front
// view from the front, its rear view from the rear, mirrored across); a
// four-post's upright is on one face, and only that pane draws the part, by
// its working (front) face. Every pane is widened and raised for every part
// whichever pane draws it, so the two panes keep one box and one U scale.
const zeroUShown = (z, view) => { const f = faceOfAt(z.at); return f == null || f === view; };
const zeroUPanel = (z, view) => (faceOfAt(z.at) == null ? view : 'front');
// Its centre across the pane: rack x is right as seen from the front; the rear pane mirrors it.
const zeroUPaneX = (z, view) => {
  const s = sideOfAt(z.at) === 'left' ? -1 : 1, xr = s * (OPENING / 2 + RAIL_W + STANDOFF + (z.w || 0) / 2);
  return view === 'rear' ? OPENING / 2 - xr : OPENING / 2 + xr;
};
// A ZERO-U PART STANDS WHERE ITS MILLIMETRES SAY (kit 0.30.0, #1030): the
// kit's solid, and so the routes round it, read `offsetMm`, and `ru` is only
// the nearest unit. zeroUDrawn adds that bottom (`mm`) to the kit's entries;
// an entry without one stands on its unit.
export function zeroUDrawn(rack, chassisOf) {
  const mm = new Map(zeroUOf(rack).map(z => [z.id, zeroUBottomMm(z)]));
  return zeroUEntries(rack, chassisOf).map(e => ({...e, mm: mm.get(e.id)}));
}
// (the ring round a selected part, `bottom` its bottom edge in pane y: drawn by drawElevation and by a view's select)
const zeroURing = (svgEl, z, view, bottom, w, h) => svgEl('rect', {x: zeroUPaneX(z, view) - w / 2 - 3, y: bottom - h - 1.5, width: w + 6, height: h + 3,
  rx: 3, fill: 'none', stroke: 'var(--pt-brass)', 'stroke-width': 2.5, class: 'rk-sel-ring', 'pointer-events': 'none'});
const zeroURise = (z, baseRU) => (Number.isFinite(z.mm) ? z.mm - (baseRU - 1) * RU : (z.ru - baseRU) * RU);
function zeroUBox(zeroU, frame, baseRU, g) {
  const totalH = frame.heightRU * RU;
  const wide = Math.max(0, ...zeroU.map(z => STANDOFF + (z.w || 0) + 4));
  const top = Math.min(-18, ...zeroU.map(z => totalH - zeroURise(z, baseRU) - (z.h || 0) - 6));
  const side = Math.max(g, wide);
  return {x: -RAIL_W - side, y: top, w: OPENING + RAIL_W * 2 + side * 2, h: totalH + 12 - top};
}
// A NARROW RACK-FACE PART on one rail stands over that rail's holes, not
// across the opening; on the right rail it is the left-hand drawing turned end
// over end (upstream design 3, as built). `side` is as seen from its own face.
const SIDED = new Set(['left', 'right']);
function sidedTransform(it, view, w, h, y) {
  const left = (it.side === 'left') === (it.face === view);
  const cx = OPENING / 2 + (left ? SIDES[0].hole : SIDES[1].hole);
  const x = cx - w / 2;
  const turn = it.side === 'right' ? ` rotate(180 ${w / 2} ${h / 2})` : '';
  return `translate(${x} ${y})${turn}`;
}

// THE PANE'S BOX, before any room for cables: the rails, a gutter each side
// (the lane gap when cables are routed) and, with parts beside the rack, room
// for them. The side panes take its top and height (side-elevation.js), so a
// U is at one height in every pane.
export function elevationBox(frame, zeroU = [], baseRU = 1, laneGap = 0) {
  const g = Math.max(6, laneGap), totalH = frame.heightRU * RU;
  return zeroU.length ? zeroUBox(zeroU, frame, baseRU, g) : {x: -RAIL_W - g, y: -18, w: OPENING + RAIL_W * 2 + g * 2, h: totalH + 30};
}

// THE SURFACE THE DEVICES ARE MOUNTED ON (docs/rack-views-design.md §2.5). The
// rack-specific code of a pane is behind these three, so that a surface of
// another kind plugs in without a change to the handle: `frame2d` draws the
// rails, holes and unit numbers, `placeOf` says where an item is (`lo` and
// `hi`, mm above the bottom of the rails) and `ears` the rail holes its ears
// are fixed at. Only the rack is a surface now (mountRack2d refuses another).
export const rackSurface = {
  kind: 'rack',
  frame2d: drawRails,
  // WHERE THE BODY IS: the kit's (fit.js itemBox), when the caller has the
  // catalogue (`chassisOf`: the Rack Builder and its sheet). Without it (the
  // showcase) the span is the item's units, `ruH`.
  placeOf: (it, {frame, chassisOf, ruH}) => (typeof chassisOf === 'function' && chassisOf(it.ref) ? itemBox({frame}, it, chassisOf)
    : {lo: (it.ru - 1) * RU, hi: (it.ru - 1 + ruH) * RU}),
  ears: box => earHoles(box.lo, box.hi),
};

// `document` is the one every node is made through (and whose window parses a
// drawing): the view reads no global.
export async function drawElevation({document: domDoc, surface = rackSurface, items, frame, view = 'front', baseRU = 1,
                                     hitTargets = false, selectedId = null, selectedU = null,
                                     placeholders = true, ears = false, metal = false, paper = false, laneGap = 0,
                                     zeroU = [], selectedZeroU = null, chassisOf = null}) {
  const {svgEl, importDrawingNode} = dom(domDoc);
  const win = domDoc.defaultView;
  const C = metal ? METAL : THEMED;
  const totalH = frame.heightRU * RU;
  // Lanes (cable routing spec §7): with routed cables the gutter beside each
  // rail widens to the lane gap, so a run up the side has room.
  const box = elevationBox(frame, zeroU, baseRU, laneGap);
  const out = svgEl('svg', {xmlns: 'http://www.w3.org/2000/svg', 'data-pane': view,
    viewBox: `${box.x} ${box.y} ${box.w} ${box.h}`});
  surface.frame2d(svgEl, out, frame, baseRU, totalH, C);
  let zStyled = false;
  for (const z of zeroU.filter(x => zeroUShown(x, view))) {
    const panel = zeroUPanel(z, view);
    // (`swaps`: the plugs derived at its outlets, never stored: cable-plugs.js zeroUFacts. `ends`: its outlets, for picking)
    const face = await configuredFace({ref: z.ref, cfg: z.cfg, view: panel, swaps: z.swaps || {}, fields: {}, ends: true}, domDoc);
    const bottom = totalH - zeroURise(z, baseRU);
    const attrs = {'data-zerou-id': z.id, 'data-device-name': z.label, 'data-device-ref': z.ref,
                   'data-panel': 'zerou', 'data-zerou-at': z.at, style: 'cursor: pointer',
                   ...(z.id === selectedZeroU ? {class: 'rk-selected'} : {})};
    let w = z.w || 0, h = z.h || 0, gz;
    if (face) {
      const root = new win.DOMParser().parseFromString(face.text, 'image/svg+xml').documentElement;
      const vb = (root.getAttribute('viewBox') || '').split(/\s+/).map(Number);
      w = parseFloat(root.getAttribute('width')) || vb[2] || w;
      h = parseFloat(root.getAttribute('height')) || vb[3] || h;
      gz = svgEl('g', {transform: `translate(${zeroUPaneX(z, view) - w / 2} ${bottom - h})`, ...attrs});
      for (const kid of [...root.childNodes]) {
        if (kid.nodeName === 'style') { if (zStyled) continue; zStyled = true; }
        gz.append(importDrawingNode(kid) ?? []);
      }
      // WHAT IT IS SET TO AND SHOWS (settable.js), as the item below
      paintFace(gz, z.paint);
      // The whole part takes a click: its backing rect, under its drawing.
      gz.prepend(svgEl('rect', {x: 0, y: 0, width: w, height: h, fill: 'transparent', 'data-zerou-hit': z.id}));
      // THE OUTLETS A CORD LANDS ON (kit 0.36.0, Portrayal #1068: ports.js cableEndPaths of the part), for
      // Cable mode's portAt, as a device's slots are; the end is {item: the part's id, path, view: this panel}.
      // (and, kit 0.44.0, the ports of the modules in its bays, which the kit names: face.js zeroUModuleEnds)
      const slotEnds = [...new Set([...(face.ports || []).filter(p => p.end).map(p => p.path ?? p.id),
                                    ...await zeroUModuleEnds(z, panel)])];
      if (slotEnds.length) { gz.setAttribute('data-cable-ends', slotEnds.join(' ')); gz.setAttribute('data-zerou-panel', panel); }
    } else {
      gz = svgEl('g', attrs);
      if (placeholders) {
        const x0 = zeroUPaneX(z, view) - w / 2;
        const P = paper ? OUTLINE_PAPER : OUTLINE;
        gz.append(svgEl('rect', {x: x0 + 0.5, y: bottom - h + 0.5, width: Math.max(1, w - 1), height: Math.max(1, h - 1), rx: 2,
          fill: P.fill, 'fill-opacity': 0.35, stroke: P.ink, 'stroke-width': 1, 'stroke-dasharray': '4 3'}));
        const t = svgEl('text', {x: x0 + w / 2, y: bottom - h / 2, 'text-anchor': 'middle', 'font-size': 11,
          'font-family': 'IBM Plex Mono, monospace', fill: P.ink, transform: `rotate(-90 ${x0 + w / 2} ${bottom - h / 2})`});
        t.textContent = `${z.label} · no ${panel} drawing`;
        gz.append(t);
      }
    }
    out.append(gz);
    if (z.id === selectedZeroU) out.append(zeroURing(svgEl, z, view, bottom, w, h));
  }
  // Under the devices, so a click on a device is the device's; a click on an
  // empty U lands here.
  // A UNIT ONE HALF OF WHICH IS TAKEN offers its other half, as a target of
  // its own (`data-half`, `data-u` the half position): the free half beside a
  // half-unit panel, or above the top half of a 1.5U device. A unit that is
  // empty, or full, is one target, as ever. On a two-post frame the rails are
  // shared, so a device on either face takes the half.
  if (hitTargets) {
    const takes = items.filter(it => it.mount !== 'rack-face' && (it.face === view || frame.kind === 'two-post'));
    const taken = (lo, hi) => takes.some(it => it.ru < hi && lo < it.ru + (it.u ?? 1));
    for (let i = 0; i < frame.heightRU; i++) {
      const u = baseRU + i, lower = taken(u, u + 0.5), upper = taken(u + 0.5, u + 1);
      const rect = (ru, y, h, half) => out.append(svgEl('rect', {x: 0, y, width: OPENING, height: h,
        fill: 'transparent', 'data-u': String(ru), 'data-face': view, ...(half ? {'data-half': half} : {}),
        class: ru === selectedU ? 'rk-u rk-u-selected' : 'rk-u'}));
      if (lower === upper) rect(u, totalH - (i + 1) * RU, RU, null);
      else if (lower) rect(u + 0.5, totalH - (i + 1) * RU, RU / 2, 'upper');
      else rect(u, totalH - (i + 0.5) * RU, RU / 2, 'lower');
    }
  }
  let styled = false;
  // Fix round 1: a selection ring is queued here and appended only after
  // every item is drawn, not right after its own item - otherwise a ring
  // drawn for a `through` item (through panels go first, by precedence
  // below) could sit under a `mounted` item's panel drawn later at the same
  // U (a four-post pair sharing it).
  const rings = [];
  // Precedence (round 3 §2): draw every item's `through` panel before any
  // `mounted` one, so a four-post pair sharing a U shows the item actually
  // mounted on this face on top - by data-panel, not by item order.
  // MANAGERS LAST (spec section 6): a rack-face part bolts over its host, so it
  // is drawn after every device. On the other face it shows only where no
  // device spans its U - behind a device it is out of sight.
  const isFace = it => it.mount === 'rack-face';
  const spans = (o, u) => o.ru < u + 1 && u < o.ru + (o.u ?? 1);   // half-open, as the kit's spanOf is
  const shown = items.filter(it => !(isFace(it) && it.face !== view
                                     && items.some(o => !isFace(o) && spans(o, it.ru))));
  const rank = it => (it.face === view ? 1 : 0) + (isFace(it) ? 2 : 0);
  const order = [...shown].sort((a, b) => rank(a) - rank(b));
  for (const it of order) {
    const common = {'data-item-id': it.id, 'data-device-name': it.label, 'data-device-ref': it.ref,
                    ...(it.id === selectedId ? {class: 'rk-selected'} : {})};
    const through = it.face !== view;
    const topOf = ruH => totalH - (it.ru - baseRU + ruH) * RU;
    const panel = panelFor(it, view);
    const face = await configuredFace({ref: it.ref, cfg: it.cfg, view: panel,
                                       swaps: it.swaps || {}, fields: it.fields || {}, ends: true}, domDoc);
    // One height for this item, computed before the `!face` branch: `it.u`
    // when it is known (every real caller sets it via fit.js's itemsWithU, in
    // halves since rack file version 4), falling back to the compiled
    // drawing's own height only when it is not.
    let ruH = it.u ?? 1;
    // ROLLED A QUARTER TURN (rack file version 4), an item is an outline, as
    // the kit fits and routes it and says when the file opens: how it mounts
    // that way is not described yet, so its drawing is not stood on its side
    // by guesswork, nor drawn upright in a span that is its width.
    const quarter = it.roll === 90 || it.roll === 270;
    if (quarter && face && placeholders) {
      out.append(outline(svgEl, topOf(ruH), ruH, `${it.label} · rolled a quarter turn`,
                         {...common, 'data-panel': through ? 'through' : 'mounted', 'data-rolled': String(it.roll)}, paper ? OUTLINE_PAPER : OUTLINE));
      if (it.id === selectedId) rings.push([topOf(ruH), ruH]);
      continue;
    }
    if (!face) {
      if (placeholders) {
        out.append(outline(svgEl, topOf(ruH), ruH, `${it.label} · no ${panel} drawing`,
                           {...common, 'data-panel': 'missing', ...(isFace(it) ? {'pointer-events': 'none'} : {})}, paper ? OUTLINE_PAPER : OUTLINE));
        if (it.id === selectedId) rings.push([topOf(ruH), ruH]);
      }
      continue;
    }
    const root = new win.DOMParser().parseFromString(face.text, 'image/svg+xml').documentElement;
    const vb = (root.getAttribute('viewBox') || '').split(/\s+/).map(Number);
    const w = parseFloat(root.getAttribute('width')) || vb[2];
    const h = parseFloat(root.getAttribute('height')) || vb[3];
    if (it.u == null) ruH = Math.max(1, Math.round(h / RU));
    // WHERE THE BODY IS: the kit's (fit.js itemBox), when the caller has the
    // catalogue (`chassisOf`: the Rack Builder and its sheet). `lo` and `hi`
    // are the edges of the span the item fills, in mm above the bottom of the
    // rails, and the drawing is centred between them, always: a half-unit
    // panel at U12 is in the lower half of U12, and one at 12.5 in its upper
    // half. Without the catalogue (the showcase) the span is the item's units.
    // (the rack surface's `placeOf`)
    const box = surface.placeOf(it, {frame, chassisOf, ruH});
    const paneY = mm => totalH + (baseRU - 1) * RU - mm;
    const y = paneY((box.lo + box.hi) / 2) - h / 2;
    // THE FACE IS CENTRED, NOT THE DRAWING (#168). A drawing bigger than its
    // face (#865: `data-face-w`/`-h`, the face at 0,0 in it, its viewBox grown
    // round what stands off it) was centred by its whole width and ignored
    // its viewBox origin, which put the 482.6 mm CMH-6DR1U 43 mm left of the
    // rails. Its children keep their own coordinates here, so the face's
    // origin is 0 when declared and the viewBox origin when not.
    const fw = parseFloat(root.getAttribute('data-face-w')), fh = parseFloat(root.getAttribute('data-face-h'));
    const declared = fw > 0 && fh > 0;
    const [faceW, faceH] = declared ? [fw, fh] : [w, h];
    const [ox, oy] = declared ? [0, 0] : [Number.isFinite(vb[0]) ? vb[0] : 0, Number.isFinite(vb[1]) ? vb[1] : 0];
    const fx = (OPENING - faceW) / 2, fy = paneY((box.lo + box.hi) / 2) - faceH / 2;
    const g = svgEl('g', {transform: isFace(it) && SIDED.has(it.side) ? sidedTransform(it, view, w, h, y) : `translate(${fx - ox} ${fy - oy})`, ...common,
                          ...(isFace(it) && SIDED.has(it.side) ? {'data-side': it.side} : {}),
                          'data-panel': through ? 'through' : 'mounted'});
    // THE SLOTS A CABLE LANDS ON besides the ports (a power inlet or outlet, a
    // ground stud: kit ports.js cableEndPaths), for portAt to take a click on.
    const slotEnds = (face.ports || []).filter(p => p.end).map(p => p.path ?? p.id);
    if (slotEnds.length) g.setAttribute('data-cable-ends', slotEnds.join(' '));
    // Ids are NOT rewritten per device. The compiled drawings carry no <defs>,
    // no url(#...) and no href="#...", so there is nothing to collide - and
    // renaming them would break swap.js, which finds a seated module by the
    // canonical id the compiler gave it. One <style> is enough: every
    // compiled drawing carries the same stylesheet.
    for (const kid of [...root.childNodes]) {
      if (kid.nodeName === 'style') { if (styled) continue; styled = true; }
      g.append(importDrawingNode(kid) ?? []);
    }
    // WHAT IT IS SET TO AND SHOWS (settable.js): the lamps and digits the rack
    // sets and the text or picture a display holds, painted into this
    // device's own drawing, as the fields are (the item's `paint`, which the
    // page reads for the rack as it is: none for a rack that sets nothing)
    paintFace(g, it.paint);
    out.append(g);
    // A manager is mostly air: a click on its tray or ears is meant for the
    // host behind it, or the empty U on the far face. This holds on either
    // face. Its rings (data-kind="ring"; any data-ref component too, for
    // future parts) and the gutter mark still take clicks (spec section 7).
    if (isFace(it)) {
      g.setAttribute('pointer-events', 'none');
      for (const part of g.querySelectorAll('[data-kind="ring"], [data-ref]')) {
        part.setAttribute('pointer-events', 'visiblePainted');
      }
    }
    // Ears only on the face the item is actually mounted on, and only after
    // its own group, so they overlap its edges like a real ear.
    // (a desktop, wall or DIN-rail device has none: the Rack Builder marks it
    // with `mount`, which the showcase's items never carry)
    // GENERIC EARS ONLY WHERE THE KIT'S PLAN GIVES ONE (Portrayal #909): a
    // face as wide as the rack face has its ears built in and draws them
    // itself (a blanking panel, a shelf, a full-width patch panel), so a
    // second pair over them would hide the real ones: such a device gets its
    // screw heads only. In the plan's colour, silver unless the device states
    // `chassis.ears.color`.
    if (!through && ears && isRackMount(it)) drawEars(svgEl, out, it, {top: paneY(box.hi), bottom: paneY(box.lo), holes: surface.ears(box).map(paneY)},
                                                      C, await earPlanFor(it.ref, it.cfg), [fx, fx + faceW]);
    if (it.id === selectedId) rings.push([topOf(ruH), ruH]);
  }
  // A U carrying a manager says so in the gutter: the manager itself is mostly
  // see-through. The marker is also how a click reaches it.
  for (const it of shown.filter(i => isFace(i) && i.face === view)) {
    const y0 = totalH - (it.ru - baseRU + 1) * RU;
    const mark = svgEl('g', {'data-manager-mark': it.id, 'data-item-id': it.id,
      'data-device-name': it.label, style: 'cursor: pointer'});
    mark.append(svgEl('rect', {x: -RAIL_W - 6, y: y0, width: RAIL_W + 6, height: RU, fill: 'transparent'}),
      svgEl('path', {d: `M ${-RAIL_W - 5} ${y0 + 4} l 4 ${RU / 2 - 4} l -4 ${RU / 2 - 4} z`,
        fill: 'var(--pt-brass)'}));
    out.append(mark);
  }
  for (const [top, ruH] of rings) out.append(ring(svgEl, top, ruH));
  return out;
}

// ---- MOUNTING ONE FACE OF ONE RACK (docs/rack-views-design.md §2) -----------
// `mountRack2d(container, {document, doc, rackId, surface, face, chassisOf, ctx,
// dist, ears, metal})` draws the pane at once and returns the handle of
// view.js. It makes every node through `document` and reads no global.

const SURFACES = {rack: rackSurface};
const noRack = id => new Error(`There is no rack ${id} in this document.`);

export function mountRack2d(container, opts = {}) {
  const {document: domDoc, face = 'front', chassisOf = () => null, ctx, ears = true, metal = true} = opts;
  if (!domDoc) throw new Error('mountRack2d needs the document to draw into: pass {document}.');
  if (face !== 'front' && face !== 'rear') throw new Error(`face is "front" or "rear", not ${JSON.stringify(face)}.`);
  const kind = opts.surface?.kind ?? 'rack';
  if (kind === 'backboard') {
    throw new Error('A backboard is not a surface a view can draw yet: only {kind: "rack"} is mounted, and how a backboard is stored is not decided (#1297).');
  }
  if (!SURFACES[kind]) throw new Error(`There is no "${kind}" surface: only {kind: "rack"} is mounted.`);
  if (opts.rackId != null && opts.surface?.id != null && opts.surface.id !== opts.rackId) {
    throw new Error(`rackId ${opts.rackId} and the surface's id ${opts.surface.id} name different racks.`);
  }
  const surface = SURFACES[kind];
  setDist(opts.dist);
  const st = {doc: null, rackId: opts.rackId ?? opts.surface?.id ?? null, svg: null, drawn: null, sel: null};
  let epoch = 0, gone = false;

  // The selection as drawElevation takes it: an item, a part beside the rack, or a unit.
  const selected = () => {
    const [k, ...rest] = (st.sel?.key ?? '').split(':'), id = rest.join(':');
    return {selectedId: k === 'item' ? id : null, selectedZeroU: k === 'zeroU' ? id : null, selectedU: k === 'u' ? Number(id) : null};
  };

  async function draw(doc, rackId) {
    const mine = ++epoch;
    const id = rackId ?? doc?.racks?.[0]?.id;
    if (id == null) throw new Error('This document has no racks.');
    const rack = (doc.racks || []).find(r => r.id === id);
    if (!rack) throw noRack(id);
    // WHAT EACH ENTRY IS SET TO AND SHOWS (settable.js); a rack that sets nothing reads no parts list
    const paint = await paintMaps(rack, ctx || {}, async () => null);
    const items = itemsWithU(rack, chassisOf).map(it => (paint.has(it.id) ? {...it, paint: paint.get(it.id)} : it));
    const zeroU = zeroUDrawn(rack, chassisOf).map(z => (paint.has(z.id) ? {...z, paint: paint.get(z.id)} : z));
    const svg = await drawElevation({document: domDoc, surface, items, frame: rack.frame, view: face, hitTargets: true,
                                     ears, metal, zeroU, chassisOf, ...selected()});
    if (mine !== epoch || gone) return;   // overtaken by a later update, or disposed
    st.svg?.remove();
    container.append(svg);
    Object.assign(st, {doc, rackId: id, svg, drawn: {items, zeroU, frame: rack.frame}});
  }

  // THE SELECTION RING, in the drawn pane and without drawing it again: what
  // drawElevation({selectedId, selectedZeroU, selectedU}) draws for the same pick.
  function paintSelection() {
    const svg = st.svg;
    if (!svg) return;
    for (const n of [...svg.querySelectorAll('.rk-sel-ring')]) n.remove();
    for (const n of [...svg.querySelectorAll('.rk-selected')]) n.removeAttribute('class');
    for (const n of [...svg.querySelectorAll('.rk-u-selected')]) n.setAttribute('class', 'rk-u');
    if (!st.sel) return;
    const {selectedId, selectedZeroU, selectedU} = selected();
    const {svgEl} = dom(domDoc);
    const {items, zeroU, frame} = st.drawn, totalH = frame.heightRU * RU;
    if (selectedId != null) {
      const groups = [...svg.querySelectorAll('[data-item-id][data-panel]')].filter(g => g.getAttribute('data-item-id') === selectedId);
      const it = items.find(i => i.id === selectedId);
      if (!it || !groups.length) return;
      for (const g of groups) g.setAttribute('class', 'rk-selected');
      svg.append(ring(svgEl, totalH - (it.ru - 1 + (it.u ?? 1)) * RU, it.u ?? 1));
    } else if (selectedZeroU != null) {
      const g = [...svg.querySelectorAll('[data-zerou-id]')].find(n => n.getAttribute('data-zerou-id') === selectedZeroU);
      const z = zeroU.find(x => x.id === selectedZeroU);
      if (!g || !z) return;
      g.setAttribute('class', 'rk-selected');
      const hit = g.querySelector('[data-zerou-hit]');
      const w = hit ? parseFloat(hit.getAttribute('width')) : z.w || 0, h = hit ? parseFloat(hit.getAttribute('height')) : z.h || 0;
      g.after(zeroURing(svgEl, z, face, totalH - zeroURise(z, 1), w, h));
    } else if (selectedU != null) {
      for (const n of svg.querySelectorAll('[data-u]')) if (n.getAttribute('data-u') === String(selectedU)) n.setAttribute('class', 'rk-u rk-u-selected');
    }
  }

  const {handle, emit} = createView({
    ready: draw(opts.doc, st.rackId),
    update: (doc, {rackId} = {}) => draw(doc, rackId ?? st.rackId),
    select(parsed) { st.sel = parsed; paintSelection(); },
    dispose() {
      gone = true; epoch++;
      container.removeEventListener('click', onClick);
      st.svg?.remove();
      st.svg = null;
    },
  });
  handle.ready.catch(() => {});   // a host that never reads `ready` is not left with an unhandled rejection

  // A CLICK on a drawn part: the item and the part of it (the nearest data-path in its drawing), a part
  // beside the rack, or an empty unit (its position, 12 or 12.5)
  function onClick(ev) {
    const t = ev.target, svg = st.svg;
    if (!svg || !t?.closest || !svg.contains(t)) return;
    const z = t.closest('[data-zerou-id]'), i = z ? null : t.closest('[data-item-id]'), u = z || i ? null : t.closest('[data-u]');
    const owner = z || i;
    if (!owner && !u) return;
    const part = owner ? t.closest('[data-path]') : null;
    emit({view: '2d', rackId: st.rackId, surface: {kind: 'rack', id: st.rackId},
          key: z ? `zeroU:${z.getAttribute('data-zerou-id')}` : i ? `item:${i.getAttribute('data-item-id')}` : `u:${u.getAttribute('data-u')}`,
          path: part && owner.contains(part) ? part.getAttribute('data-path') : null,
          face, u: u ? Number(u.getAttribute('data-u')) : null, originalEvent: ev});
  }
  container.addEventListener('click', onClick);
  return handle;
}
