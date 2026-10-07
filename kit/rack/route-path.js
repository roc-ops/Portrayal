// Pure geometry for a routed cable (kept out of cables.js so node can import it).
// A ROUTED CABLE (routing spec §7): straight runs between its waypoints, each
// corner rounded by r, so it reads as dressed cable rather than a hang.
export function routed2d(pts, r = 4) {
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
