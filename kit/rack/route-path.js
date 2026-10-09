// Pure geometry for a routed cable (kept out of cables.js so node can import it).
// A ROUTED CABLE: straight runs between its waypoints, each
// corner rounded by r, so it reads as dressed cable rather than a hang.
// `rings`, when given, is parallel to `pts`: null, or a ring's mark at each
// point that is a ring's centre - route.js ringMarks gives them, with the
// decision routePath made, turned to the drawing's axes by orientMarks (an
// elevation's y is down; the rear pane's x is mirrored too) - so the cable
// passes through it straight, the way it was measured, and its corners are
// rounded outside it (throughRings).
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
// {run: 'x'|'y'|'z', depth, sense?, back?} where pts[k] is a ring's centre,
// and null elsewhere. A run the point has no axis for (z on a 2D point)
// leaves the point as it is: seen end-on, a ring is where the cable is.
//
// THE DECISION, ONCE. Which way a cable goes through a ring, and whether it
// goes through at all, is decided once, in the rack's own frame, by
// route.js routePath, and handed on as `sense` (+1 or -1 along the run) and
// `back` (true: it would enter and leave by one face). A mark that carries
// them is obeyed, so a drawing, whose points sit in its own frame (a lead out
// of the connector, an elevation with no z), draws what was measured and
// counted. `sense` is along the axes of the points given: a drawing whose
// axis runs against the rack's (an SVG's y down, the mirrored rear pane's x)
// turns its marks first (route.js orientMarks). A mark without them is
// decided here, by the same rule:
//
// Which way through: the side the point before stands on; else the side the
// point after goes to; else toward + on the run. A point stands on NEITHER
// side when it is within half the ring's depth of the centre along the run,
// or when it is further off the run's line IN THE FACE than it is along the
// run (steeper than 45 degrees: a port well below the ring, a little to one
// side, comes up into it). In the face means the stand-off out of it, z, is
// not counted for a ring that runs along x or y: how far a lacer stands out
// of its host is not an approach angle, and every frame agrees on x and y.
// Points before and after both standing on the SAME side mean the cable
// would enter and leave by one face: that ring is not drawn through. The
// cable is taken to that face only, and its index is in `back`.
//
// HELD, NOT HOOKED (#949, the owner's decision of 2026-10-09). A cable that
// only reaches a short way past its PORT into a ring just beyond it is held
// by the ring, not hooked back through it: it passes, toward the ring and away
// from both neighbours, and turns back beyond its far face. It applies only
// when the nearer of the two neighbours along the run is a port, which the
// mark says (`portBefore`, `portAfter`; neither given, no exemption): a cable
// that turns back at a ring just past another ring's exit or a lane point is a
// hook, however close the rings stand. Short means the ring's near face is no
// further past that port, along the run, than the ring's own depth plus the
// cable's diameter (`diameter` on the mark, 0 when not given), the diameter
// counted at most up to the ring's depth: the ring stands right at the port,
// with one cable's lay before it. The cap keeps the bound at twice the ring's
// depth whatever the cable: a fat, stiff cable bends wider, so a longer reach
// past its port is more of a hook, not less. Measured to the far face, the
// overshoot is at most twice the depth plus that diameter. A ring further off
// is a hook-back, and stays in `back`. The pass carries `held: true`.
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
// {index, entry, exit, sense} (entry and exit the points in `points`); and
// per ring not passed, {index, sense, face}. A ring that holds a cable
// reaching just into it (above) is a pass with `held: true`.
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
// The axes across a run, in the face: for a ring along x or y, the other of
// the two (the stand-off out of the face, z, is not an approach); along z,
// both.
const inFace = a => (a === 'z' ? ['x', 'y'] : a === 'x' ? ['y'] : ['x']);

export function throughRings(pts, rings = [], {lead = 0} = {}) {
  const out = [], passes = [], back = [];
  // which side of the ring centred at o a point q stands on: -1, +1, or 0
  // (within half its depth along the run, or steeper than 45 degrees off it)
  const side = (q, o, a, half) => {
    const v = get(q, a) - get(o, a);
    const across = Math.hypot(...inFace(a).filter(b => has(q, b) && has(o, b)).map(b => get(q, b) - get(o, b)));
    if (Math.abs(v) <= half + EPS || Math.abs(v) < across) return 0;
    return v > 0 ? 1 : -1;
  };
  pts.forEach((p, k) => {
    const g = rings?.[k];
    const a = g?.run ?? 'x';
    if (!g || !(g.depth > 0) || !(a in AXIS) || !has(p, a)) { out.push(copy(p)); return; }
    const c = get(p, a), half = g.depth / 2;
    const prev = out.length ? out[out.length - 1] : null, next = pts[k + 1] ?? null;
    const given = g.sense === 1 || g.sense === -1;
    const before = given ? 0 : prev ? side(prev, p, a, half) : 0, after = given ? 0 : next ? side(next, p, a, half) : 0;
    // a ring just past the nearer neighbour holds the cable (above)
    let held = false;
    if (!given && before && before === after) {
      // the nearer neighbour along the run, and whether it is a port
      const dp = Math.abs(get(prev, a) - c), dn = Math.abs(get(next, a) - c);
      const [reach, port] = dp <= dn ? [dp, g.portBefore === true] : [dn, g.portAfter === true];
      const d = Math.min(g.diameter > 0 ? g.diameter : 0, g.depth);
      held = port && reach - half <= g.depth + d + EPS;
    }
    if (!held && (given ? g.back === true : before && before === after)) {
      const s = given ? g.sense : -before;
      const face = along(p, a, c - s * half);
      out.push(face);
      back.push({index: k, sense: s, face});
      return;
    }
    const sense = given ? g.sense : before ? -before : after || 1;
    const entry = along(p, a, c - sense * half), exit = along(p, a, c + sense * half);
    passes.push({index: k, sense, entry, exit, run: a, ...(held ? {held: true} : {})});
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
  return {points: out, passes: passes.map(({index, sense, entry, exit, held}) => ({index, sense, entry, exit, ...(held ? {held} : {})})), back};
}
