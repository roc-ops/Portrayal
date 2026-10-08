// Pure geometry for a routed cable (kept out of cables.js so node can import it).
// A ROUTED CABLE: straight runs between its waypoints, each
// corner rounded by r, so it reads as dressed cable rather than a hang.
// `rings`, when given, is parallel to `pts`: a ring's {run, depth} at each
// point that is a ring's centre (throughRings), so the cable passes through
// it straight and its corners are rounded outside it.
export function routed2d(pts, r = 4, rings = null) {
  if (rings) pts = throughRings(pts, rings, {lead: r}).points;
  let d = `M${pts[0][0]} ${pts[0][1]}`;
  for (let k = 1; k < pts.length - 1; k++) {
    const [p, q, s] = [pts[k - 1], pts[k], pts[k + 1]];
    const cut = (a, b) => { const L = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1, t = Math.min(r, L / 2) / L;
      return [b[0] + (a[0] - b[0]) * t, b[1] + (a[1] - b[1]) * t]; };
    const i = cut(p, q), o = cut(s, q);
    d += ` L${i[0]} ${i[1]} Q${q[0]} ${q[1]} ${o[0]} ${o[1]}`;
  }
  const z = pts[pts.length - 1];
  return `${d} L${z[0]} ${z[1]}`;
}

// ── through a ring (roc-ops/Portrayal#930) ───────────────────────────────
// A D-ring holds a cable that passes THROUGH it along its run, not one that
// turns at a point inside it. So a ring's centre becomes two points: where the
// cable enters, half the ring's depth along the run on the side nearer the
// point before it, and where it leaves, as far the other side. Between them
// the cable is straight and parallel to the run; any bend is outside.
//
// A point is [x, y] or [x, y, z] (the 2D drawing), or {x, y, z} (rack
// coordinates, or a three.js vector, which is cloned). `rings[k]` is
// {run: 'x'|'y'|'z', depth} where pts[k] is a ring's centre, and null
// elsewhere. A run the point has no axis for (z on a 2D point) leaves the
// point as it is: seen end-on, a ring is where the cable is.
//
// Which way through: the side the point before stands on; else the side the
// point after goes to; else toward + on the run. A point stands on NEITHER
// side when it is within half the ring's depth of the centre along the run,
// or when it is further from the run's line than it is along it (steeper
// than 45 degrees: a port below the ring, a little to one side, comes up
// into it, it does not run along to it). Points before and after both
// standing on the SAME side mean the cable would enter and leave by one face:
// that ring is not drawn through. The cable is taken to its near face only,
// and its index is in `back`, for the caller to report.
//
// `lead` (mm, default 0) adds a point on the run outside each face, so a
// drawing that rounds its corners rounds them there and not inside the ring.
// It is never further out than half the neighbour's own distance beyond that
// face along the run, so it never hooks back past the neighbour and two rings
// in a row never cross their leads; a neighbour at or inside the face's
// plane (a port under the ring) gets none, and the corner is at the face. A
// length is measured with lead 0.
//
// Returns {points, passes, back}: the points in order; per ring passed,
// {index, entry, exit, sense} (sense +1 or -1 along the run, entry and exit
// the points in `points`); and the indexes of the rings not passed.
const AXIS = {x: 0, y: 1, z: 2};
const has = (p, a) => (Array.isArray(p) ? AXIS[a] < p.length : typeof p?.[a] === 'number');
const get = (p, a) => (Array.isArray(p) ? p[AXIS[a]] : p[a]);
const copy = p => (Array.isArray(p) ? p.slice() : typeof p.clone === 'function' ? p.clone() : {...p});
const along = (p, a, v) => { const q = copy(p); if (Array.isArray(q)) q[AXIS[a]] = v; else q[a] = v; return q; };
const gap = (p, q) => {
  const ks = Array.isArray(p) ? p.map((_, i) => i) : ['x', 'y', 'z'];
  return Math.hypot(...ks.map(k => (p[k] ?? 0) - (q[k] ?? 0)));
};
const EPS = 1e-9;

export function throughRings(pts, rings = [], {lead = 0} = {}) {
  const out = [], passes = [], back = [];
  // which side of the ring centred at o a point q stands on: -1, +1, or 0
  // (within half its depth along the run, or steeper than 45 degrees off it)
  const side = (q, o, a, half) => {
    const v = get(q, a) - get(o, a), across = Math.sqrt(Math.max(0, gap(q, o) ** 2 - v * v));
    if (Math.abs(v) <= half + EPS || Math.abs(v) < across) return 0;
    return v > 0 ? 1 : -1;
  };
  pts.forEach((p, k) => {
    const g = rings?.[k];
    const a = g?.run ?? 'x';
    if (!g || !(g.depth > 0) || !(a in AXIS) || !has(p, a)) { out.push(copy(p)); return; }
    const c = get(p, a), half = g.depth / 2;
    const prev = out.length ? out[out.length - 1] : null, next = pts[k + 1] ?? null;
    const before = prev ? side(prev, p, a, half) : 0, after = next ? side(next, p, a, half) : 0;
    if (before && before === after) {
      out.push(along(p, a, c + before * half));
      back.push(k);
      return;
    }
    const sense = before ? -before : after || 1;
    const entry = along(p, a, c - sense * half), exit = along(p, a, c + sense * half);
    passes.push({index: k, sense, entry, exit, run: a});
    out.push(entry, exit);
  });
  if (lead > 0) {
    // A lead point on the run, outside each face: at most half the
    // neighbour's distance beyond that face ALONG THE RUN, so it never passes
    // the neighbour (no hook) and two rings in a row never cross their leads.
    for (const pass of passes) {
      const {entry, exit, sense, run} = pass;
      const i = out.indexOf(entry), j = out.indexOf(exit);
      const prev = out[i - 1], next = out[j + 1];
      if (next) {
        const l = Math.min(lead, Math.max(0, sense * (get(next, run) - get(exit, run))) / 2);
        if (l > EPS) out.splice(j + 1, 0, along(exit, run, get(exit, run) + sense * l));
      }
      if (prev) {
        const l = Math.min(lead, Math.max(0, sense * (get(entry, run) - get(prev, run))) / 2);
        if (l > EPS) out.splice(i, 0, along(entry, run, get(entry, run) - sense * l));
      }
    }
  }
  return {points: out, passes: passes.map(({index, sense, entry, exit}) => ({index, sense, entry, exit})), back};
}
