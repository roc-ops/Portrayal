// kit/rack/coil.js
// THE CELLS OF A TRAY, AND A COIL OF SPARE CABLE IN ONE (docs/cable-spare-design.md
// sections 3.1 to 3.3). A cell is the floor between two rings; a coil is turns of
// the cable stacked in a cell, joined to the cord's lay line by two legs. These
// are pure functions of the tray traysOf publishes and of a cable's bend radius
// and diameter. Nothing here changes a path, a need, a stock size or a finding:
// the legs and the turns are the spare the cable stores, so a drawn coil adds
// nothing to what a cord needs.
import {FILL_LIMIT} from './route.js';

const EPS = 1e-9;
// the length of a rounded rectangle w by h with corner radius r
const perimeter = (w, h, r) => 2 * (w + h) - (8 - 2 * Math.PI) * r;
const round1 = v => Math.round(v * 10) / 10;

// THE CELLS OF ONE TRAY, from its largest floor (the strip) cut by the rings
// that stand on it: {item, via, run, top, opening, across: {c0, c1, depth},
// cells: [{i, a0, a1, width}]} in rack mm. `a` runs along the tray, `c` across
// it; `opening` is the lowest ring opening, the height a stack may reach, and 0
// where the tray has no ring to give one.
export function cellsOf(tray) {
  const x = tray.run === 'x', k = x ? ['x0', 'x1', 'z0', 'z1'] : ['z0', 'z1', 'x0', 'x1'];
  const area = f => (f.x1 - f.x0) * (f.z1 - f.z0);
  const strip = tray.floors.reduce((m, f) => (area(f) > area(m) ? f : m));
  const a0 = strip[k[0]], a1 = strip[k[1]];
  const bands = (tray.rings || []).filter(r => r.run === tray.run).map(r => [r.box[k[0]], r.box[k[1]]])
    .filter(([lo, hi]) => hi > a0 + EPS && lo < a1 - EPS).sort((p, q) => p[0] - q[0]);
  const cells = [];
  let at = a0;
  for (const [lo, hi] of bands) { cells.push({a0: at, a1: Math.max(at, lo)}); at = Math.max(at, hi); }
  cells.push({a0: at, a1: a1});
  const opening = (tray.rings || []).length ? Math.min(...tray.rings.map(r => r.box.y1 - r.box.y0)) : 0;
  return {item: tray.item, via: tray.via, run: x ? 'x' : 'z', top: tray.top, opening,
    across: {c0: strip[k[2]], c1: strip[k[3]], depth: strip[k[3]] - strip[k[2]]},
    cells: cells.map((c, i) => ({i, ...c, width: c.a1 - c.a0}))};
}

// THE TURNS A CELL TAKES FOR A CABLE `{bend, diameter}`, or null when none: a
// turn runs on the cable's centre line, a rounded rectangle whose corners are
// the bend radius, so it needs the cell and the floor to be at least twice the
// radius across on the centre line. {min_mm, max_mm, w, h, across_mm, r, d}:
// the shortest turn (a circle) and the longest (the whole centre-line box), the
// box's sides, and its depth across the tray.
export function turnLimits(g, cell, cable) {
  const r = cable.bend, d = cable.diameter;
  if (!(r > 0 && d > 0)) return null;
  const w = cell.width - d, h = g.across.depth - d;
  if (w < 2 * r - EPS || h < 2 * r - EPS) return null;
  return {min_mm: perimeter(2 * r, 2 * r, r), max_mm: perimeter(w, h, r), w, h, across_mm: round1(h), r, d};
}

// HOW MANY TURNS MAY STACK: the opening of the lowest ring, times `fraction`
// (FILL_LIMIT by default, the fill rule, an estimate and not a measurement of
// any tray), in whole turns of the cable's diameter.
export const stackOf = (g, cable, fraction = FILL_LIMIT) => Math.floor(fraction * g.opening / cable.diameter + EPS);

// WHAT A TRAY HOLDS at a stack: {cells, turns, min_m, max_m}, the cells that
// take a turn, their turns, and the cord those turns hold when each is the
// shortest and when each is the longest the cell takes.
export function capacityOf(g, cable, stack) {
  let cells = 0, turns = 0, min = 0, max = 0;
  for (const c of g.cells) {
    const lim = turnLimits(g, c, cable);
    if (!lim) continue;
    cells++; turns += stack; min += stack * lim.min_mm; max += stack * lim.max_mm;
  }
  return {cells, turns, min_m: min / 1000, max_m: max / 1000};
}

// A LENGTH SOLVED TO WHOLE TURNS: the fewest turns that none is longer than the
// cell takes, each the same length, so the drawn length is `mm` to the last
// digit. Under one shortest turn nothing is drawn. Where no whole number of
// turns fits (more than the longest turn and under two shortest ones) the
// longest turns that fit are drawn and the rest is `left_mm`.
// {layers, turn_mm, drawn_mm, left_mm}
export function solveTurns(lim, mm) {
  if (mm < lim.min_mm - EPS) return {layers: 0, turn_mm: 0, drawn_mm: 0, left_mm: Math.max(0, mm)};
  const n = Math.ceil(mm / lim.max_mm - EPS), turn = mm / n;
  if (turn >= lim.min_mm - EPS) return {layers: n, turn_mm: turn, drawn_mm: mm, left_mm: 0};
  return {layers: n - 1, turn_mm: lim.max_mm, drawn_mm: (n - 1) * lim.max_mm, left_mm: mm - (n - 1) * lim.max_mm};
}

// THE CELL NEAREST A POINT ALONG THE TRAY that takes a turn of the cable, the
// lower of two equally near; null when none does.
export function cellNear(g, cable, along) {
  let best = null, gap = Infinity;
  for (const c of g.cells) {
    if (!turnLimits(g, c, cable)) continue;
    const d = Math.abs((c.a0 + c.a1) / 2 - along);
    if (d < gap - EPS) { best = c; gap = d; }
  }
  return best;
}

// A COIL OF `metres` OF SPARE in a cell, joined to the cord's lay line. `lay` is
// a point {x, y, z} of the cord resting on the tray, in rack mm; the legs leave
// it, climb one diameter (the first turn stands over the through cords) and
// meet the first turn at the edge of the cell's centre-line box nearest the
// line; the other turns stand one diameter above each other. The legs and the
// turns and what is left add to `metres`, so the cord needs no more cable for
// the coil. {cell, layers, turn_mm, drawn_mm, legs_mm, left_mm, stack_limit,
// over_stack, crosses_lay, legs: [[from, to], [to, from]], layers_at:
// [{y, box: {x0, x1, z0, z1}, radius}]}. Over the stack limit is said and not
// refused (the turns are drawn as they fall). Nothing is drawn, and the
// whole length is `left_mm`, where the legs would leave under one turn.
export function coilIn(g, cell, cable, metres, lay) {
  const lim = turnLimits(g, cell, cable);
  if (!lim) return null;
  const x = g.run === 'x', d = cable.diameter, total = metres * 1000;
  const lay_a = (cell.a0 + cell.a1) / 2, lay_c = x ? lay.z : lay.x;
  // the edge of the centre-line box nearest the lay line, across the tray
  const lo = g.across.c0 + d / 2, hi = g.across.c1 - d / 2, edge = Math.abs(lay_c - lo) <= Math.abs(hi - lay_c) ? lo : hi, dir = edge === lo ? 1 : -1;
  const leg = Math.hypot(edge - lay_c, d);
  const limit = stackOf(g, cable);
  const none = {cell: cell.i, layers: 0, turn_mm: 0, drawn_mm: 0, legs_mm: 0, left_mm: total, stack_limit: limit, over_stack: false, crosses_lay: false, legs: [], layers_at: []};
  if (total - 2 * leg < lim.min_mm - EPS) return none;
  const k = solveTurns(lim, total - 2 * leg);
  const s = lim.max_mm > lim.min_mm ? (k.turn_mm - lim.min_mm) / (lim.max_mm - lim.min_mm) : 1;
  const w = 2 * lim.r + s * (lim.w - 2 * lim.r), h = 2 * lim.r + s * (lim.h - 2 * lim.r);
  const span = dir === 1 ? [edge, edge + h] : [edge - h, edge];
  const along = [lay_a - w / 2, lay_a + w / 2];
  const at = (a, c, y) => (x ? {x: a, y, z: c} : {x: c, y, z: a});
  const from = at(lay_a, lay_c, lay.y), to = at(lay_a, edge, lay.y + d);
  const box = x ? {x0: along[0], x1: along[1], z0: span[0], z1: span[1]} : {x0: span[0], x1: span[1], z0: along[0], z1: along[1]};
  return {cell: cell.i, layers: k.layers, turn_mm: k.turn_mm, drawn_mm: k.drawn_mm, legs_mm: 2 * leg, left_mm: k.left_mm,
    stack_limit: limit, over_stack: k.layers > limit, crosses_lay: lay_c > span[0] + EPS && lay_c < span[1] - EPS,
    legs: [[from, to], [to, from]],
    layers_at: Array.from({length: k.layers}, (_, i) => ({y: lay.y + d * (i + 1), box, radius: lim.r}))};
}
