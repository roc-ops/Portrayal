// HOW A CORD IS DRAWN, as a test reads it. The Rack Builder draws a routed cord
// from the kit's path points (portrayal-site site/rack/bend3d.js kitRoute): the
// tube leaves its plug straight along the face's normal, turns onto the first
// point it can reach with one arc of the cord's bend radius that starts at the
// plug's reach point (the lead, at most two radii long), and rounds every other
// corner with an arc of that radius, tighter where the legs either side cannot
// hold it (each leg is shared, and half of it is each corner's at least) or
// where the arc would meet a solid body (the corner's share is halved until it
// clears). This module is that rule on plain numbers, so that the kit's tests
// can ask of a path what the page will draw: the centre line of the tube
// (`curve`) and the radius each corner is drawn at (`corners`). It is a model of
// the drawing for the tests, not something the kit measures with.
const EPS = 1e-6, STRAIGHT = 0.25 * Math.PI / 180;
const sub = (p, q) => ({x: p.x - q.x, y: p.y - q.y, z: p.z - q.z});
const add = (p, q, k = 1) => ({x: p.x + q.x * k, y: p.y + q.y * k, z: p.z + q.z * k});
const dot = (p, q) => p.x * q.x + p.y * q.y + p.z * q.z;
const len = p => Math.hypot(p.x, p.y, p.z);
const unit = p => { const l = len(p) || 1; return {x: p.x / l, y: p.y / l, z: p.z / l}; };
const round1 = v => Math.round(v * 10) / 10;

// the corner a lead turns at, out of the plug (bend3d.js leadOut)
function leadOut(s, n, q, R, most) {
  if (!(R > 0)) return 0;
  const d = sub(q, s), u = dot(d, n), w = len(sub(d, {x: n.x * u, y: n.y * u, z: n.z * u}));
  if (w < 1e-6 && u > 0) return 0;
  const A = u, B = R - w, rho = Math.hypot(A, B);
  if (rho < R) return most;
  const phi = Math.atan2(A, B), off = Math.acos(Math.min(1, R / rho));
  const ahead = th => (u - R * Math.sin(th)) * Math.cos(th) + (w - R * (1 - Math.cos(th))) * Math.sin(th) > 0;
  const norm = th => Math.atan2(Math.sin(th), Math.cos(th));
  const theta = [norm(phi - off), norm(phi + off)].filter(th => th >= -1e-9 && th < Math.PI && ahead(Math.max(0, th))).sort((x, y) => x - y)[0];
  if (theta == null) return most;
  if (!(theta > STRAIGHT)) return 0;
  return Math.min(most, R * Math.tan(theta / 2));
}

// the corners of a polyline at radius R, each leg shared (bend3d.js fitCorners); `cap` is a corner's tangent length when a body took it
function fit(pts, R, cap = new Map()) {
  const P = [];
  for (const p of pts) if (!P.length || len(sub(p, P.at(-1))) > EPS) P.push(p);
  const L = P.slice(1).map((p, j) => len(sub(p, P[j])));
  const turn = P.map((q, k) => (k === 0 || k === P.length - 1 ? 0
    : Math.acos(Math.max(-1, Math.min(1, dot(unit(sub(q, P[k - 1])), unit(sub(P[k + 1], q))))))));
  const want = turn.map(th => (th < STRAIGHT ? 0 : th >= Math.PI - STRAIGHT ? Infinity : R * Math.tan(th / 2)));
  const share = (j, other) => Math.max(L[j] / 2, L[j] - want[other]);
  const corners = [];
  for (let k = 1; k < P.length - 1; k++) {
    if (turn[k] < STRAIGHT) continue;
    const room = Math.min(share(k - 1, k - 1), share(k, k + 1)), capped = cap.get(k) ?? Infinity;
    const t = Math.min(want[k], room, capped);
    const drawn = want[k] === Infinity ? 0 : t / Math.tan(turn[k] / 2);
    corners.push({k, at: P[k], theta: turn[k], t: want[k] === Infinity ? 0 : t, drawn_mm: round1(drawn), full: drawn >= R - 0.05});
  }
  return {P, corners};
}

// a corner's arc, a circular arc between its tangent points `t` from the corner, sampled: the points of the arc alone
function arcOf(P, c, step = 0.5) {
  const u = unit(sub(c.at, P[c.k - 1])), v = unit(sub(P[c.k + 1], c.at));
  const a = add(c.at, u, -c.t), b = add(c.at, v, c.t);
  if (!(c.t > EPS)) return {a, b, arc: []};
  const r = c.t / Math.tan(c.theta / 2), m = unit({x: u.x * -1 + v.x, y: u.y * -1 + v.y, z: u.z * -1 + v.z});
  // the centre is on the bisector, toward the inside of the turn, r / cos(theta / 2) from the corner
  const ctr = add(c.at, m, r / Math.cos(c.theta / 2));
  const ea = unit(sub(a, ctr)), eb = unit(sub(b, ctr));
  const ang = Math.acos(Math.max(-1, Math.min(1, dot(ea, eb)))), n = Math.max(2, Math.ceil(r * ang / step)), w = Math.sin(ang);
  const arc = [];
  for (let i = 1; i < n; i++) {
    const s = i / n, k1 = w > 1e-9 ? Math.sin((1 - s) * ang) / w : 1 - s, k2 = w > 1e-9 ? Math.sin(s * ang) / w : s;
    arc.push({x: ctr.x + r * (ea.x * k1 + eb.x * k2), y: ctr.y + r * (ea.y * k1 + eb.y * k2), z: ctr.z + r * (ea.z * k1 + eb.z * k2)});
  }
  return {a, b, arc};
}
// the centre line: the legs and each corner's arc, sampled
function sample(P, corners, step = 0.5) {
  const out = [P[0]];
  const line = q => { const p = out.at(-1), n = Math.max(1, Math.ceil(len(sub(q, p)) / step)); for (let i = 1; i <= n; i++) out.push(add(p, sub(q, p), i / n)); };
  for (const c of corners) {
    const {a, b, arc} = arcOf(P, c, step);
    line(a);
    out.push(...arc);
    line(b);
  }
  line(P.at(-1));
  return out;
}

// whether a point is inside a box, solid or grown (boxes: {x0, x1, y0, y1, z0, z1})
export const inside = (q, b, by = 0) => q.x > b.x0 - by + 0.05 && q.x < b.x1 + by - 0.05 && q.y > b.y0 - by + 0.05 && q.y < b.y1 + by - 0.05 && q.z > b.z0 - by + 0.05 && q.z < b.z1 + by - 0.05;

// A cord's drawn curve. `path` is the kit's routePath, `R` its bend radius, `bodies` the boxes its arcs are kept out of
// (the solids of the rack, not grown), `normals` the way each end's plug points ({a: n, b: n}, a unit vector out of the face).
export function drawn(path, R, bodies = [], normals) {
  const pts = path.points;
  const a = pts.find(q => q.at === 'a'), b = pts.find(q => q.at === 'b');
  let inner = pts.filter(q => q.at !== 'a' && q.at !== 'b' && q.at !== 'reach');
  const ra = pts.find(q => q.at === 'reach' && q.end === 'a') ?? pts.find(q => q.at === 'reach'), rb = pts.findLast(q => q.at === 'reach');
  const na = normals.a, nb = normals.b, most = 2 * R;
  const reachable = (s, n, q) => { const d = sub(q, s), u = dot(d, n); return Math.hypot(u, R - len(sub(d, {x: n.x * u, y: n.y * u, z: n.z * u}))) >= R; };
  while (inner.length > 1 && inner[0].at === 'rest' && !reachable(ra, na, inner[0])) inner = inner.slice(1);
  while (inner.length > 1 && inner.at(-1).at === 'rest' && !reachable(rb, nb, inner.at(-1))) inner = inner.slice(0, -1);
  const crowded = (s, n, list) => {
    if (list.length < 2 || list[0].at !== 'rest') return false;
    const l = leadOut(s, n, list[0], R, most), v = add(s, n, l);
    const d1 = sub(list[0], v), L = len(d1), d2 = sub(list[1], list[0]);
    if (L <= EPS || len(d2) <= EPS) return true;
    const th = Math.acos(Math.max(-1, Math.min(1, dot(unit(d1), unit(d2)))));
    return l + (th < STRAIGHT ? 0 : R * Math.tan(Math.min(th, Math.PI - STRAIGHT) / 2)) > L + 1e-6;
  };
  while (crowded(ra, na, inner)) inner = inner.slice(1);
  while (crowded(rb, nb, [...inner].reverse())) inner = inner.slice(0, -1);
  const qa = inner[0] ?? rb, qb = inner.at(-1) ?? ra;
  const la = leadOut(ra, na, qa, R, most), lb = leadOut(rb, nb, qb, R, most);
  const chain = [ra, ...(la > EPS ? [add(ra, na, la)] : []), ...inner, ...(lb > EPS ? [add(rb, nb, lb)] : []), rb];
  // straighten: a point on the line through its neighbours is dropped
  const P = [];
  for (const q of chain) {
    if (P.length && len(sub(P.at(-1), q)) <= EPS) continue;
    if (P.length >= 2) {
      const d1 = unit(sub(P.at(-1), P.at(-2))), d2 = unit(sub(q, P.at(-1)));
      if (Math.acos(Math.max(-1, Math.min(1, dot(d1, d2)))) < STRAIGHT) P.pop();
    }
    P.push(q);
  }
  // the arcs kept out of the bodies: a corner whose arc meets one has its share halved (bend3d.js clearCurve)
  const cap = new Map();
  let fitted = fit(P, R, cap);
  for (let n = 0; n < 10; n++) {
    let moved = false;
    for (const c of fitted.corners) {
      if (!(c.t > 1e-6)) continue;
      if (arcOf(fitted.P, c, 0.25).arc.some(q => bodies.some(box => inside(q, box)))) { cap.set(c.k, c.t / 2 < 0.5 ? 0 : c.t / 2); moved = true; }
    }
    if (!moved) break;
    fitted = fit(P, R, cap);
  }
  return {points: fitted.P, corners: fitted.corners, curve: sample(fitted.P, fitted.corners), a, b};
}
