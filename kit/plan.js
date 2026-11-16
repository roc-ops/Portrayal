// The plan outline cut against the section, in JavaScript: what is left of the body.
//
// This is spec/tools/portrayal/plan.py written again. The two are ONE function in two languages and
// read the same two files, spec/tests/fixtures/plan_outline/sweep-cases.json (answers worked by hand)
// and body-cases.json (what plan.py computes for two made-up boxes), so they cannot disagree:
// test_plan_js.py runs this module against every case in both. Change one and the other, or a case,
// fails. Nothing here reads the DOM or three; node runs it.
//
// THE FRAME is the top face's: x along the width from the left, y down the drawing with the REAR at
// the top, so a section depth `sx` from the front is `y = depth - sx`.
//
// THE SWEEP. Every region here is a union of polygons, and the maths is one x-sweep:
//   1. The abscissae are the x of every vertex taken in, plus the x where two of their edges cross.
//      Between two consecutive abscissae no edge begins, ends or crosses another, so the edges that
//      span the slab keep their order and every chord between a pair of them is a trapezoid.
//   2. THE MERGE RULE: sorted; the smallest is kept, and any value within MERGE (0.001 mm) of the
//      last one kept is dropped, so a cluster is its smallest member.
//   3. In a slab each polygon gives the y intervals between its edges taken in pairs from the top. A
//      group of polygons is the union of those intervals; groups are intersected, and others taken away.
//   4. THE ROUNDING RULE: a coordinate is computed in floating point and written to 6 decimals.
//
// A piece is [xl, xr, lo_left, lo_right, hi_left, hi_right]: the trapezoid between two abscissae, `lo`
// the edge nearer the top of the drawing. As a polygon it is clockwise with y down from (xl, lo_left),
// a point dropped where two coincide.
//
// THE SNAP. A plan vertex within SNAP (0.5 mm) of a side of the box, or of a wall of the section at
// the band's own heights, is moved onto it before anything is cut, one coordinate at a time to the
// nearest such line.

// millimetres
export const MERGE = 0.001;
export const SNAP = 0.5;
export const TOL = 0.01;
export const DECIMALS = 6;
const EPS = 1e-9;

// round(v, 6) as Python writes it: the nearest 6-decimal value, and no negative zero
const r = v => { const n = Number(v.toFixed(DECIMALS)); return n === 0 ? 0 : n; };

// the order Python gives two lists: element by element, a shorter prefix first
function cmp(a, b) {
  const n = Math.min(a.length, b.length);
  for (let i = 0; i < n; i++) {
    const x = a[i], y = b[i];
    const c = Array.isArray(x) ? cmp(x, y) : (x < y ? -1 : x > y ? 1 : 0);
    if (c) return c;
  }
  return a.length - b.length;
}

// ---- the sweep -----------------------------------------------------------------------------------

export function mergeAbscissae(xs) {
  const out = [];
  for (const x of [...xs].sort((a, b) => a - b)) {
    if (!out.length || x - out[out.length - 1] > MERGE) out.push(x);
  }
  return out;
}

// the edges of the polygons that are not vertical, [x0, y0, x1, y1] with x0 < x1
function edgesOf(polys) {
  const out = [];
  for (const poly of polys) {
    const n = poly.length;
    for (let i = 0; i < n; i++) {
      const [ax, ay] = poly[i], [bx, by] = poly[(i + 1) % n];
      if (Math.abs(bx - ax) <= EPS) continue;
      out.push(ax < bx ? [ax, ay, bx, by] : [bx, by, ax, ay]);
    }
  }
  return out;
}

const yAt = (e, x) => e[1] + (e[3] - e[1]) * (x - e[0]) / (e[2] - e[0]);

// the x where two edges cross strictly inside both
function crossings(edges) {
  const xs = [];
  const order = [...edges].sort(cmp);
  for (let i = 0; i < order.length; i++) {
    const a = order[i];
    for (let j = i + 1; j < order.length; j++) {
      const b = order[j];
      if (b[0] >= a[2]) break;
      const ma = (a[3] - a[1]) / (a[2] - a[0]), mb = (b[3] - b[1]) / (b[2] - b[0]);
      if (Math.abs(ma - mb) <= EPS) continue;          // parallel: they never cross
      const x = (b[1] - mb * b[0] - a[1] + ma * a[0]) / (ma - mb);
      if (Math.max(a[0], b[0]) + EPS < x && x < Math.min(a[2], b[2]) - EPS) xs.push(x);
    }
  }
  return xs;
}

// the y intervals of one polygon at xm: its edges that span it, paired from the top
function chords(polygonEdges, xm) {
  const spans = polygonEdges.filter(e => e[0] <= xm && xm < e[2])
    .map(e => [yAt(e, xm), e]).sort((p, q) => p[0] - q[0]).map(p => p[1]);
  const out = [];
  for (let i = 0; i + 1 < spans.length; i += 2) out.push([spans[i], spans[i + 1]]);
  return out;
}

function unionOf(intervals, xm) {
  const out = [];
  const sorted = intervals.map(iv => [yAt(iv[0], xm), iv]).sort((p, q) => p[0] - q[0]).map(p => p[1]);
  for (const [lo, hi] of sorted) {
    if (out.length && yAt(lo, xm) <= yAt(out[out.length - 1][1], xm) + EPS) {
      if (yAt(hi, xm) > yAt(out[out.length - 1][1], xm)) out[out.length - 1] = [out[out.length - 1][0], hi];
    } else out.push([lo, hi]);
  }
  return out;
}

function meet(a, b, xm) {
  const out = [];
  for (const [loA, hiA] of a) for (const [loB, hiB] of b) {
    const lo = yAt(loA, xm) >= yAt(loB, xm) ? loA : loB;
    const hi = yAt(hiA, xm) <= yAt(hiB, xm) ? hiA : hiB;
    if (yAt(hi, xm) - yAt(lo, xm) > EPS) out.push([lo, hi]);
  }
  return out;
}

function minusOf(a, b, xm) {
  const out = [];
  for (const [lo, hi] of a) {
    let cur = lo;
    for (const [loB, hiB] of b) {
      if (yAt(hiB, xm) <= yAt(cur, xm) + EPS || yAt(loB, xm) >= yAt(hi, xm) - EPS) continue;
      if (yAt(loB, xm) > yAt(cur, xm) + EPS) out.push([cur, loB]);
      cur = yAt(hiB, xm) > yAt(cur, xm) ? hiB : cur;
    }
    if (yAt(hi, xm) - yAt(cur, xm) > EPS) out.push([cur, hi]);
  }
  return out;
}

// The pieces of the region that lies in every group of `groups` and in none of `minus`. A group is a
// list of polygons ([[x, y], ...]) and stands for their union. `xRange`, a pair, keeps only the part
// between those x. Returns the pieces, left to right.
export function sweep(groups, minus = [], xRange = null) {
  const every = [...groups, ...minus].flat();
  let edges = edgesOf(every);
  if (xRange) edges = edges.filter(e => e[2] > xRange[0] && e[0] < xRange[1]);
  let xs = [...edges.map(e => e[0]), ...edges.map(e => e[2]), ...every.flatMap(p => p.map(q => q[0])), ...crossings(edges)];
  if (xRange) xs = [...xs.filter(x => xRange[0] < x && x < xRange[1]), xRange[0], xRange[1]];
  xs = mergeAbscissae(xs);
  const perGroup = groups.map(g => g.map(p => edgesOf([p])));
  const perMinus = minus.map(g => g.map(p => edgesOf([p])));
  const pieces = [];
  for (let i = 0; i + 1 < xs.length; i++) {
    const xl = xs[i], xr = xs[i + 1], xm = (xl + xr) / 2;
    let region = null;
    for (const g of perGroup) {
      const iv = unionOf(g.flatMap(pe => chords(pe, xm)), xm);
      region = region === null ? iv : meet(region, iv, xm);
      if (!region.length) break;
    }
    if (!region || !region.length) continue;
    for (const g of perMinus) region = minusOf(region, unionOf(g.flatMap(pe => chords(pe, xm)), xm), xm);
    for (const [lo, hi] of region) {
      pieces.push([r(xl), r(xr), r(yAt(lo, xl)), r(yAt(lo, xr)), r(yAt(hi, xl)), r(yAt(hi, xr))]);
    }
  }
  return pieces;
}

// a piece as a clockwise polygon, a point dropped where two coincide
export function polygon(piece) {
  const [xl, xr, a, b, c, d] = piece;
  const out = [];
  for (const p of [[xl, a], [xr, b], [xr, d], [xl, c]]) {
    const last = out[out.length - 1];
    if (!last || Math.abs(last[0] - p[0]) > EPS || Math.abs(last[1] - p[1]) > EPS) out.push(p);
  }
  if (out.length > 1 && Math.abs(out[0][0] - out[out.length - 1][0]) <= EPS
      && Math.abs(out[0][1] - out[out.length - 1][1]) <= EPS) out.pop();
  return out;
}

export function area(piece) {
  const [xl, xr, a, b, c, d] = piece;
  return (xr - xl) * ((c - a) + (d - b)) / 2;
}

// ---- the outline of a union ----------------------------------------------------------------------

// the intervals of `a` that `b` does not cover; both sorted lists of [lo, hi]
function gaps(a, b) {
  const out = [];
  for (const [lo, hi] of a) {
    let cur = lo;
    for (const [loB, hiB] of b) {
      if (hiB <= cur + EPS || loB >= hi - EPS) continue;
      if (loB > cur + EPS) out.push([cur, loB]);
      cur = Math.max(cur, hiB);
    }
    if (hi - cur > EPS) out.push([cur, hi]);
  }
  return out;
}

// a point dropped where it lies on the straight run between its neighbours
function simplify(loop) {
  const out = [...loop];
  let changed = true;
  while (changed && out.length > 3) {
    changed = false;
    for (let i = 0; i < out.length; i++) {
      const a = out[(i + out.length - 1) % out.length], b = out[i], c = out[(i + 1) % out.length];
      const cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]);
      const ahead = (b[0] - a[0]) * (c[0] - b[0]) + (b[1] - a[1]) * (c[1] - b[1]);
      if (Math.abs(cross) <= 1e-5 * Math.hypot(c[0] - a[0], c[1] - a[1]) && ahead >= 0) {
        out.splice(i, 1);
        changed = true;
        break;
      }
    }
  }
  return out;
}

// the loop starting at its smallest x, then smallest y, so one outline has one spelling
function rotate(loop) {
  let best = 0;
  for (let k = 1; k < loop.length; k++) {
    if (loop[k][0] < loop[best][0] || (loop[k][0] === loop[best][0] && loop[k][1] < loop[best][1])) best = k;
  }
  return [...loop.slice(best), ...loop.slice(0, best)];
}

// The boundary of the region the pieces of one sweep fill, as closed loops of [x, y], clockwise with y
// down for an outer boundary and the other way round for a hole. The loops start at their smallest x,
// then y, carry no point on a straight run and are listed by their first point.
export function loops(pieces) {
  const edges = [];                              // [start, end] directed, interior on the right
  const byLeft = new Map(), byRight = new Map();
  const push = (m, k, v) => { if (!m.has(k)) m.set(k, []); m.get(k).push(v); };
  for (const [xl, xr, a, b, c, d] of pieces) {
    edges.push([[xl, a], [xr, b]]);
    edges.push([[xr, d], [xl, c]]);
    push(byLeft, xl, [a, c]);
    push(byRight, xr, [b, d]);
  }
  const xsAll = [...new Set([...byLeft.keys(), ...byRight.keys()])].sort((p, q) => p - q);
  for (const x of xsAll) {
    const left = (byRight.get(x) || []).slice().sort(cmp);       // intervals of pieces ending at x
    const right = (byLeft.get(x) || []).slice().sort(cmp);       // intervals of pieces starting at x
    for (const [lo, hi] of gaps(left, right)) edges.push([[x, lo], [x, hi]]);       // a wall facing right: down
    for (const [lo, hi] of gaps(right, left)) edges.push([[x, hi], [x, lo]]);       // a wall facing left: up
  }
  const key = pt => `${pt[0].toFixed(5)},${pt[1].toFixed(5)}`;
  const starts = new Map();
  for (const e of edges) if (key(e[0]) !== key(e[1])) push(starts, key(e[0]), e);
  const used = new Set(), out = [];
  for (const e of edges) {
    if (key(e[0]) === key(e[1]) || used.has(e)) continue;
    const loop = [];
    let cur = e;
    while (cur && !used.has(cur)) {
      used.add(cur);
      loop.push(cur[0]);
      const nxt = (starts.get(key(cur[1])) || []).filter(n => !used.has(n));
      cur = nxt.length ? nxt[0] : null;
    }
    if (loop.length >= 3) out.push(rotate(simplify(loop.map(([x, y]) => [r(x), r(y)]))));
  }
  return out.sort(cmp);
}

export function loopArea2(loop) {
  let s = 0;
  for (let i = 0; i < loop.length; i++) {
    const [x0, y0] = loop[i], [x1, y1] = loop[(i + 1) % loop.length];
    s += x0 * y1 - x1 * y0;
  }
  return s;
}

// The outline of the union of `polys` as loops, cut to the rectangle `clip` = [x0, y0, x1, y1] when given.
export function unionLoops(polys, clip = null) {
  if (!polys.length) return [];
  if (!clip) return loops(sweep([polys]));
  const [x0, y0, x1, y1] = clip;
  return loops(sweep([polys, [[[x0, y0], [x1, y0], [x1, y1], [x0, y1]]]], [], [x0, x1]));
}

// ---- the snap ------------------------------------------------------------------------------------

// The rows of a rectilinear region as [y0, y1, [[x0, x1], ...]] for each strip between consecutive
// vertex heights, with the x intervals that are solid in it (the vertical edges, paired left to
// right). `loopsList` is a list of closed loops, section.py `_bands` for the polygon alone.
export function sectionRows(loopsList) {
  const ys = [...new Set(loopsList.flat().map(p => p[1]))].sort((a, b) => a - b);
  const verticals = [];
  for (const lp of loopsList) {
    for (let i = 0; i < lp.length; i++) {
      const a = lp[i], b = lp[(i + 1) % lp.length];
      if (a[0] === b[0]) verticals.push([a[0], Math.min(a[1], b[1]), Math.max(a[1], b[1])]);
    }
  }
  const out = [];
  for (let i = 0; i + 1 < ys.length; i++) {
    const mid = (ys[i] + ys[i + 1]) / 2;
    const xs = verticals.filter(([, lo, hi]) => lo < mid && mid < hi).map(v => v[0]).sort((a, b) => a - b);
    const iv = [];
    for (let k = 0; k + 1 < xs.length; k += 2) iv.push([xs[k], xs[k + 1]]);
    out.push([ys[i], ys[i + 1], iv]);
  }
  return out;
}

// The section's rows as [y0, y1, [[lo, hi], ...]]: heights, and the depth intervals that are solid
// there in the plan's frame (depth - sx), top of the drawing first. `loopsList` is the section polygon
// or, for a body cut back to its core, the loops of that body.
export function rows(section, depth) {
  const lps = Array.isArray(section[0]) && Array.isArray(section[0][0]) ? section : [section];
  return sectionRows(lps).map(([y0, y1, iv]) => [y0, y1, iv.map(([a, b]) => [depth - b, depth - a]).sort(cmp)]);
}

function rowEdges(rws, depth, lo, hi) {
  const ys = new Set();
  for (const [y0, y1, iv] of rws) {
    if (Math.min(y1, hi) - Math.max(y0, lo) > EPS) for (const [a, b] of iv) { ys.add(a); ys.add(b); }
  }
  return [...ys].sort((a, b) => a - b);
}

// The polygon with each coordinate moved onto the nearest target within SNAP, a point that repeats
// its neighbour then dropped. Returns {points, snaps}, a snap being [index, axis, from, to] for each
// move of more than TOL (the ones lint names).
export function snapPolygon(points, targetsX, targetsY) {
  const out = [], snaps = [];
  points.forEach(([x, y], i) => {
    const now = [];
    for (const [axis, v0, targets] of [['x', x, targetsX], ['y', y, targetsY]]) {
      let v = v0, near = null;
      for (const t of targets) if (near === null || Math.abs(t - v0) < Math.abs(near - v0)) near = t;
      if (near !== null && Math.abs(near - v0) <= SNAP + EPS) {
        if (Math.abs(near - v0) > TOL) snaps.push([i, axis, v0, near]);
        v = near;
      }
      now.push(v);
    }
    out.push(now);
  });
  const kept = out.filter((p, i) => { const q = out[(i + out.length - 1) % out.length]; return p[0] !== q[0] || p[1] !== q[1]; });
  return {points: kept, snaps};
}

// `plan` (the bands, [{heights, points}]) with every polygon snapped onto the box's sides and the
// walls of the section `rws` (rows, as `rows` returns them) at the band's own heights. Returns
// {bands, snaps}, a snap being [band, index, axis, from, to].
export function snapped(plan, rws, width, depth) {
  const bands = [], snaps = [];
  plan.forEach((b, i) => {
    const [lo, hi] = b.heights;
    const ty = [...new Set([0, depth, ...rowEdges(rws, depth, lo, hi)])].sort((p, q) => p - q);
    const got = snapPolygon(b.points, [0, width], ty);
    bands.push({heights: b.heights, points: got.points});
    for (const s of got.snaps) snaps.push([i, ...s]);
  });
  return {bands, snaps};
}

// ---- the body that is left -----------------------------------------------------------------------

const rectPolys = (intervals, width) => intervals.map(([a, b]) => [[0, a], [width, a], [width, b], [0, b]]);

// A band's heights with an edge within TOL of a row's edge taken to be on it.
export function bandHeights(heights, rws) {
  const edges = [...new Set(rws.flatMap(([y0, y1]) => [y0, y1]))].sort((a, b) => a - b);
  return heights.map(h => {
    let near = null;
    for (const e of edges) if (near === null || Math.abs(e - h) < Math.abs(near - h)) near = e;
    return near !== null && Math.abs(near - h) <= TOL ? near : h;
  });
}

// What the plan leaves of the section's body: for each band and each row it covers,
// {band, heights: [h0, h1], intervals, pieces} where the pieces are the band's polygon cut to the
// row's depth intervals. `plan` is already snapped; `rws` the rows.
export function bodyOf(plan, rws, width) {
  const out = [];
  plan.forEach((b, i) => {
    const heights = bandHeights(b.heights, rws);
    for (const [y0, y1, iv] of rws) {
      const h0 = Math.max(heights[0], y0), h1 = Math.min(heights[1], y1);
      if (h1 - h0 > EPS) {
        out.push({band: i, heights: [h0, h1], intervals: iv, pieces: sweep([[b.points], rectPolys(iv, width)])});
      }
    }
  });
  return out;
}

// A chassis' plan outline, cut once: {width, height, depth, section, bands, snaps, rows, solid}.
// `chassis` states `width`, `height`, `depth`, `section` and `plan-outline` (the bands as written).
export function planBody(chassis) {
  const width = Number(chassis.width), height = Number(chassis.height), depth = Number(chassis.depth);
  const section = chassis.section.map(p => [Number(p[0]), Number(p[1])]);
  const raw = chassis['plan-outline'].map(b => ({
    heights: [Number(b.heights[0]), Number(b.heights[1])],
    points: b.points.map(p => [Number(p[0]), Number(p[1])]),
  }));
  const rws = rows(section, depth);
  const {bands, snaps} = snapped(raw, rws, width, depth);
  return {width, height, depth, section, bands, snaps, rows: rws, solid: bodyOf(bands, rws, width)};
}
