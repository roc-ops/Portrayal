// Shared relief pipeline.
//
// Face art is an SVG whose nodes carry data-cavity / data-z-* attributes saying
// which parts of the faceplate are recessed, raised, domed or vented. This module
// turns that into something a viewer can build geometry from, and rasterises the
// art at a chosen density.
//
// It lives here rather than in 3d.html because rack.html needs exactly the same
// reading of a face, and two copies would drift. Dependencies are injected once
// rather than threaded through every signature, so the function bodies are the
// same code that has been running in the device viewer.

import { paintFields, unpaintFields } from './fields.js';

let THREE, renderer, PXMM, FRU_PATHS;

// A BODY THAT IS NOT ONE BOX. A module's `body` is a box the size of its face
// (or its `footprint`) and `depth` deep; a riser is a plate with a 1.6 mm PCB
// standing behind it and three connectors on the PCB, and a box that size hid
// the chassis interior while a box cut to the plate left the PCB behind when
// the riser was ejected. `body.boxes` lists the pieces instead, each in the
// face's own frame, starting `from` mm behind the plane. This resolves either
// form to a list the two builders (the FRU in a chassis, the part alone) draw
// the same way; it is pure, so it is checked under node.
// A rect in a module's own frame, mapped through the module's placement (its
// translate, and its reflection when `mirror: true`) into face mm. Corners
// through the matrix, then the min/max, so a mirrored module's box comes out
// on the mirrored side with a positive width.
export function localToFace(m, r) {
  if (!m) return {x: r.x, y: r.y, w: r.w, h: r.h};
  const pt = (x, y) => ({x: m.a * x + m.c * y + m.e, y: m.b * x + m.d * y + m.f});
  const p = pt(r.x, r.y), q = pt(r.x + r.w, r.y + r.h);
  return {x: Math.min(p.x, q.x), y: Math.min(p.y, q.y), w: Math.abs(q.x - p.x), h: Math.abs(q.y - p.y)};
}

// WHERE A TURNED MODULE'S BODY STANDS: its footprint through the module's own
// frame (`toFace`, local mm -> face mm), and the turn that frame carries, as a
// three.js z rotation - the face's y runs down and the scene's up, so a
// clockwise turn on the drawing is a negative one here. `null` for a frame with
// no turn, or a mirrored one, whose body is placed from its drawn box as it
// always was. Pure, so it is checked under node.
//
// ONLY A DECLARED FOOTPRINT. A body with none fills its face, and bodyBoxMesh
// sizes that from the DRAWN box - already turned - so sending it through the
// frame turned it twice: an ASR 9001's MPA blanks, seated rotate 90, stood 34.5
// wide and 161.8 tall in a 2RU chassis. The drawn box is already where such a
// body stands, so it keeps the drawn-box path.
export function bodyPose(m, body) {
  const fp = body && body.footprint;
  if (!fp || !m || m.a * m.d - m.b * m.c <= 0 || (Math.abs(m.b) < 1e-9 && m.a > 0)) return null;
  const r = localToFace(m, {x: fp.at[0], y: fp.at[1], w: fp.size[0], h: fp.size[1]});
  return {r, turn: -Math.atan2(m.b, m.a)};
}

// WHICH RAISED SURFACE DOES A LIFTED CAVITY BELONG TO. Exported because it is
// the whole of a rule that is easy to state and easy to get subtly wrong, and a
// pure function of two rectangles and two depths is worth testing without a
// browser.
//
// A cavity punches a raised surface when it is lifted onto that surface's top:
// its footprint lies within the surface, and its lift matches the surface's own
// protrusion. Requiring the MATCH rather than merely `lift <= out` is what stops
// a shallow cavity on the faceplate from punching a tall bezel that happens to
// pass over it - two features at different depths in the same footprint are a
// real arrangement, not an error to be papered over.
// the selector for "this node carries relief of its own"
export const RAISED = '[data-z-out],[data-z-cyl],[data-z-bar],[data-z-uhandle],[data-z-dome]';

// WHAT A CAVITY BUILDS, from what render.py flagged on it. A pocket builds four
// walls, a textured floor and a closed back, clamped INTO - 2 short of the far
// face. A see-through passage (a rear hole, `seeThrough`) keeps its walls and
// drops floor and back, so the far end is open. An open bay's mouth (`hollow`)
// is a 6 mm collar meeting that passage. AN OPEN-FRAME MOUTH BUILDS NOTHING: its
// slot shares one interior with every other slot on the face - guide rails and
// a mid-plane, nothing between them - so a collar would stand a wall between
// neighbours the hardware does not have. The face is still punched; that is
// the hole, and the box's lining (openFrameFaces) is what is seen through it.
export function cavityShell(c, INTO) {
  if (c.openFrame) return {walls: false, floor: false, back: false, depth: 0};
  const open = !!(c.seeThrough || c.hollow);
  const depth = c.hollow ? Math.min(c.d, 6) : Math.min(c.d, INTO - 2);
  return {walls: true, floor: !open, back: !open, depth};
}

// WHICH FACES DECLARED AN OPEN FRAME (render.py sets `data-open-frame` on the
// root of a view whose `open-frame` is true). {face: svg text or null} in, the
// face names out. viewer3d lines the inside of the box when any face is one, so
// looking through an empty slot shows the chassis's interior and not nothing.
export function openFrameFaces(texts) {
  return Object.entries(texts || {})
    .filter(([, t]) => typeof t === 'string'
      && /^\s*<svg\b[^>]*\sdata-open-frame="1"/.test(t.replace(/<\?xml[^>]*>/, '')))
    .map(([face]) => face);
}

export function cavitySeatsOn(c, o, eps = 0.01) {
  return !!c.lift && Math.abs(c.lift - o.out) < eps
    && c.x >= o.x - eps && c.y >= o.y - eps
    && c.x + c.w <= o.x + o.w + eps && c.y + c.h <= o.y + o.h + eps;
}

// TILTED FACETS (docs/superpowers/specs/2026-09-24-tilted-facets-design.md). A part
// `on` a facet is drawn foreshortened in the face art; here it is built at its TRUE
// size, flat, and then carried onto the facet plane by one matrix. Face mm, y down,
// z out. Pure, so it is checked under node.
function _tiltBasis(deg, facing) {
  const a = deg * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
  // u: where a step along the tilted axis goes; n: the part's outward normal.
  // n must equal ex × ey, where ex and ey are the matrix's first two columns.
  if (facing === 'up')    return {axis: 'y', u: [0,  c,  s], n: [0, -s, c]};
  if (facing === 'down')  return {axis: 'y', u: [0,  c, -s], n: [0,  s, c]};
  if (facing === 'left')  return {axis: 'x', u: [ c, 0,  s], n: [-s, 0, c]};
  return                         {axis: 'x', u: [ c, 0, -s], n: [ s, 0, c]};   // right
}
export function tiltFrame({deg, facing, anchor: [ax, ay], z0 = 0}) {
  const {axis, u, n} = _tiltBasis(deg, facing);
  // the untilted axis is unchanged
  const ex = axis === 'y' ? [1, 0, 0] : u;
  const ey = axis === 'y' ? u : [0, 1, 0];
  // p' = A + ex*(x-ax) + ey*(y-ay) + n*z   ->   column-major 4x4
  const tx = ax - ex[0] * ax - ey[0] * ay;
  const ty = ay - ex[1] * ax - ey[1] * ay;
  const tz = z0 - ex[2] * ax - ey[2] * ay;
  return [ex[0], ex[1], ex[2], 0,  ey[0], ey[1], ey[2], 0,  n[0], n[1], n[2], 0,  tx, ty, tz, 1];
}
export function unproject(rect, {deg, facing, anchor: [ax, ay]}) {
  const c = Math.cos(deg * Math.PI / 180);
  if (facing === 'up' || facing === 'down')
    return {...rect, y: ay + (rect.y - ay) / c, h: rect.h / c};
  return {...rect, x: ax + (rect.x - ax) / c, w: rect.w / c};
}
export function facetZ(r, {deg, facing}, lift, [px, py]) {
  const t = Math.tan(deg * Math.PI / 180);
  const d = facing === 'up' ? py - r.y : facing === 'down' ? r.y + r.h - py
          : facing === 'left' ? px - r.x : r.x + r.w - px;
  return (lift || 0) + Math.max(0, d) * t;
}
// THE HEIGHT OF THE RAISED SOLID at a face point: the tallest `out` whose box
// holds it, a profiled one read off its piecewise-linear profiles (offsets
// from the box's own edges; the lesser of the two, as the builder draws it).
// Outs are absolute, so this is a height off the face.
// `none` is the height where nothing stands: 0, the plate, unless the caller
// is asking about a solid below it (a sunk facet's skirt; skirtIsInterior).
export function outHeightAt(outs, x, y, eps = 0.01, none = 0) {
  const lerp = (pts, t) => {
    if (t <= pts[0][0]) return pts[0][1];
    for (let i = 1; i < pts.length; i++)
      if (t <= pts[i][0]) {
        const [a0, z0] = pts[i - 1], [a1, z1] = pts[i];
        return a1 === a0 ? z1 : z0 + (z1 - z0) * (t - a0) / (a1 - a0);
      }
    return pts[pts.length - 1][1];
  };
  let h = none;
  for (const o of outs) {
    if (x < o.x - eps || x > o.x + o.w + eps || y < o.y - eps || y > o.y + o.h + eps) continue;
    const zx = o.profile && o.profile.length >= 2 ? lerp(o.profile, x - o.x) : Infinity;
    const zy = o.profileY && o.profileY.length >= 2 ? lerp(o.profileY, y - o.y) : Infinity;
    const z = Math.min(zx, zy);
    const v = Number.isFinite(z) ? z : typeof o.out === 'number' ? o.out : 0;
    if (v > h) h = v;
  }
  return h;
}
// THE NEIGHBOURS A PROFILED OUT'S SKIRT MAY BE INSIDE OF. Facet to facet
// only - a sawtooth's face and its return - and only a neighbour that is
// certainly solid down to this out's base: the same owner (a FRU pulled or a
// cover hidden takes its solid with it), no outline (its box is not its
// shape), and a base no higher than this one's (a lifted neighbour leaves the
// band beneath it open). A face with no facets gets none, so every skirt is
// built exactly as before.
export function skirtNeighbours(o, outs) {
  if (!o.facet || o.tilt) return [];
  const base = o.lift || 0;
  return outs.filter(e => e !== o && e.facet && !e.tilt && e.owner === o.owner && !e.rings
                          && (e.lift || 0) <= base + 0.01);
}
// IS THE SKIRT SEGMENT p-q INSIDE THE SOLID? Only a segment on the out's own
// box edge can be; the probe steps just past that edge and reads the tallest
// neighbour there (outHeightAt). `p`/`q` and `depthAt` are in the out's local
// mm; `others` is skirtNeighbours(o, outs).
// WHERE NO NEIGHBOUR STANDS the probe reads the plate, 0 - except beside a
// SUNK facet (recessed facets: lift < 0), where it depends on where the probe
// lands (emptyHeightAt): open pocket inside the pocket's box, plate outside.
function _skirtProbe(o, p, q) {
  const eps = 1e-4, mx = (p[0] + q[0]) / 2, my = (p[1] + q[1]) / 2;
  const dx = p[0] === q[0] ? (p[0] <= 0 ? -eps : p[0] >= o.w ? eps : 0) : 0;
  const dy = p[1] === q[1] ? (p[1] <= 0 ? -eps : p[1] >= o.h ? eps : 0) : 0;
  return !dx && !dy ? null : [o.x + mx + dx, o.y + my + dy];
}
// THE HEIGHT OF WHAT IS BESIDE A SUNK FACET WHERE NO NEIGHBOUR STANDS, at face
// point (x, y). `o.pocket` is the recess it stands in ({x, y, w, h, floor,
// mouth}; the build sets it, see pocketOf): inside that box it is open
// pocket, solid only from the floor down; outside it - a tooth spanning its
// pocket's width puts its sides there - it is the plate, solid up to the
// pocket's mouth. With no pocket known, the plate (0). Proud: always 0.
export function emptyHeightAt(o, x, y) {
  if (!(o.facet && (o.lift || 0) < 0)) return 0;
  const k = o.pocket;
  if (!k) return 0;
  return x > k.x && x < k.x + k.w && y > k.y && y < k.y + k.h ? k.floor : k.mouth;
}
export function skirtIsInterior(o, others, p, q, depthAt) {
  if (!others.length) return false;
  const pr = _skirtProbe(o, p, q);
  if (!pr) return false;
  const top = Math.max(depthAt(...p), depthAt(...q));
  return outHeightAt(others, pr[0], pr[1], 0, emptyHeightAt(o, ...pr)) >= top - 0.01;
}
// THE SKIRT OF A PROFILED OUT: the grid's perimeter, each point dropped from
// the surface (`depthAt`) to the out's own base, `o.lift`. `ring` is the
// perimeter in local mm; `pts` pairs [x, y, top], [x, y, base] per ring
// point; `idx` indexes `pts`, two triangles per built segment, a segment
// inside the solid (skirtIsInterior against `others`) left out. `segs` lists
// the built segments, {k: ring index, base}.
//
// A SUNK FACET skirts each segment down only to the solid beside it: the
// tallest neighbour, or what emptyHeightAt finds there. In open pocket that
// is its own base; beside a tooth that spans its pocket, the plate, so no
// skirt is built in the plane of the pocket's walls, and a segment that
// rises through the mouth skirts only above it. Each such segment has its
// own vertices (the quad clipped at its base, fanned). Every other out keeps
// the layout above exactly.
export function profileSkirt(o, xs, ys, depthAt, others = []) {
  const nx = xs.length, ny = ys.length;
  const ring = [];
  for (let i = 0; i < nx; i++) ring.push([xs[i], ys[0]]);
  for (let j = 1; j < ny; j++) ring.push([xs[nx - 1], ys[j]]);
  for (let i = nx - 2; i >= 0; i--) ring.push([xs[i], ys[ny - 1]]);
  for (let j = ny - 2; j > 0; j--) ring.push([xs[0], ys[j]]);
  const pts = [], idx = [], segs = [];
  if (!(o.facet && (o.lift || 0) < 0)) {
    for (const [x, y] of ring) pts.push([x, y, depthAt(x, y)], [x, y, o.lift]);
    for (let k = 0; k < ring.length; k++) {
      if (skirtIsInterior(o, others, ring[k], ring[(k + 1) % ring.length], depthAt)) continue;
      const a = 2 * k, b = a + 1, c = 2 * ((k + 1) % ring.length), d = c + 1;
      idx.push(a, b, c, b, d, c);
      segs.push({k, base: o.lift});
    }
    return {ring, pts, idx, segs};
  }
  for (let k = 0; k < ring.length; k++) {
    const p = ring[k], q = ring[(k + 1) % ring.length];
    const zp = depthAt(...p), zq = depthAt(...q);
    const pr = _skirtProbe(o, p, q);
    const beside = pr ? outHeightAt(others, pr[0], pr[1], 0, emptyHeightAt(o, ...pr)) : -Infinity;
    const base = Math.max(o.lift, beside);
    if (Math.max(zp, zq) <= base + 0.01) continue;
    // the quad p-top, q-top, q-base, p-base, kept where z >= base
    const quad = [[p[0], p[1], zp], [q[0], q[1], zq], [q[0], q[1], o.lift], [p[0], p[1], o.lift]];
    const poly = [];
    for (let i = 0; i < 4; i++) {
      const a = quad[i], b = quad[(i + 1) % 4], ia = a[2] >= base, ib = b[2] >= base;
      if (ia) poly.push(a);
      if (ia !== ib) {
        const t = (base - a[2]) / (b[2] - a[2]);
        poly.push([a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]), base]);
      }
    }
    if (poly.length < 3) continue;
    const i0 = pts.length;
    pts.push(...poly);
    for (let i = 1; i + 1 < poly.length; i++) idx.push(i0, i0 + i, i0 + i + 1);
    segs.push({k, base});
  }
  return {ring, pts, idx, segs};
}
// WHICH FACET A NODE STANDS ON: the nearest `[data-tilt-on]` group at or above
// it (render.py writes it on a part `on` a facet and on every occupant seated in
// one). `host` is that group; its projected box supplies the tilt's anchor.
// `facing` is as written - in the frame of the component declaring the facet.
export function tiltOf(el) {
  for (let n = el; n && n.getAttribute; n = n.parentNode) {
    const on = n.getAttribute('data-tilt-on');
    if (on) return {deg: +n.getAttribute('data-tilt'), facing: n.getAttribute('data-tilt-facing'),
                    on, host: n};
  }
  return null;
}
// A FACING IN THE DECLARING COMPONENT'S FRAME, TURNED INTO THE FACE'S. A card
// seated at rotate 90 has its `up` facet looking right on the face, and every
// face-mm calculation here (unproject, tiltFrame, facetZ) reads the face's axes.
// `m` is the component-to-face matrix {a, b, c, d}; a mirror swaps left/right.
export function faceFacing(m, facing) {
  const v = {up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0]}[facing];
  if (!v || !m) return facing;
  const x = m.a * v[0] + m.c * v[1], y = m.b * v[0] + m.d * v[1];
  return Math.abs(x) > Math.abs(y) ? (x > 0 ? 'right' : 'left') : (y > 0 ? 'down' : 'up');
}
// THE TILT OF A NODE ON ONE PARSED FACE, shared by the build, the lamp animator
// and the viewer's halo so that all three put a tilted thing in the same frame.
// `mmRect`, `liftOf` and `ctmOf` (a node's component-to-face matrix) are the
// caller's measuring tools; only getAttribute/parentNode/querySelector are read
// here, so it runs on the node test DOM too.
//   tiltRec(tiltOf(el)) -> {tilt: {deg, facing, on, anchor, z0}, base} | null
// `facing` is in the face's frame. `base` is the lift the node's own lift is
// measured from: everything above the outermost group on the facet, which is
// already in the facet's height.
export function tiltTools(svg, {mmRect, liftOf, ctmOf}) {
  const facets = new Map(), hostRects = new Map();
  const attr = (n, k) => (n && n.getAttribute ? n.getAttribute(k) : null);
  // The root lift is read off the derived profile, because that is the surface
  // the builder draws, and a part must stand on what is drawn.
  const facetInfo = id => {
    if (facets.has(id)) return facets.get(id);
    const node = svg.querySelector(`[id="${CSS.escape(id)}"]`);
    let info = null;
    if (node && attr(node, 'data-facet-deg')) {
      const m = ctmOf(node);
      const prof = (attr(node, 'data-z-profile-y') || attr(node, 'data-z-profile') || '').split(',')
        .map(p => +p.split(':')[1]).filter(Number.isFinite);
      info = {node, m, rect: mmRect(node), deg: +attr(node, 'data-facet-deg'),
              facing: faceFacing(m, attr(node, 'data-facet-facing')),
              lift: prof.length ? Math.min(...prof) : 0};
    }
    facets.set(id, info);
    return info;
  };
  const tiltBase = (t, hops = 0) => {
    let n = t.host;
    while (attr(n.parentNode, 'data-tilt-on') === t.on) n = n.parentNode;
    // A MATE-TO SEAT IS DRAWN OUTSIDE ITS HOST'S CARD, and its own lift is the
    // host's whole chain (render.py's `host-lift`, which folds in a sunk
    // card's -floor). Measured from its own parent it stood the card's lift
    // off the facet - or, in a well, sank into it. Two shapes of `data-for`:
    //  - a host tilted on the same facet (a boot on a tilted optic): take
    //    that host's base;
    //  - the untilted wrapper card render.py names for a device-level
    //    `mate-to` (`data-for="card"`), which carries the forwarded cage on
    //    this facet: the cage's base is the card's own lift, so take that.
    // A nested seat's host shares its parent, so nothing changes for it.
    const fr = (attr(n, 'data-for') || '').split(/\s+/)[0];
    const h = fr && hops < 8 && svg.querySelector(`[data-path="${CSS.escape(fr)}"]`);
    const ht = h && tiltOf(h);
    if (ht && ht.on === t.on && ht.host !== n) return tiltBase(ht, hops + 1);
    if (h && !(ht && ht.on === t.on) && h.querySelector(`[data-tilt-on="${CSS.escape(t.on)}"]`))
      return liftOf(h);
    const p = n.parentNode;
    return p && p !== svg && p.getAttribute ? liftOf(p) : 0;
  };
  const tiltRec = t => {
    if (!t) return null;
    const f = facetInfo(t.on);
    if (!f) { console.warn('relief: tilted part names no facet node', t.on); return null; }
    if (!hostRects.has(t.host)) hostRects.set(t.host, mmRect(t.host));
    const hr = hostRects.get(t.host);
    const facing = t.facing ? faceFacing(f.m, t.facing) : f.facing, anchor = [hr.x, hr.y];
    const z0 = facetZ(f.rect, {deg: t.deg, facing}, f.lift, anchor);
    return {tilt: {deg: t.deg, facing, on: t.on, anchor, z0}, base: tiltBase(t)};
  };
  return {facetInfo, tiltRec};
}
// A FACET HIDES THE FLAT FACE BEHIND IT, so its whole front-view footprint is
// cleared from the face canvas and from every module plane that replays the
// face's punches (a card's). Left in, the card plane cut across every tilted
// cage well and showed as a strip along the facet's root edge.
export function facetPunch(o) {
  return {kind: 'rect', x: o.x, y: o.y, w: o.w, h: o.h, facet: o.facet.id};
}
// a `rect` punch in pixels of a canvas whose origin is (ox, oy) face mm
export function punchRectPx(p, ox, oy, pxmm) {
  return [Math.round((p.x - ox) * pxmm), Math.round((p.y - oy) * pxmm),
          Math.round(p.w * pxmm), Math.round(p.h * pxmm)];
}
// A SUNK FACET STANDS ON THE FLOOR OF ITS POCKET (recessed facets, the
// addendum to the tilted-facets spec), and that floor is a textured plane
// across the whole recess, with the cavity's closed back 0.25 behind it:
// left in, they cut across the cage wells of every part on the facet, as the
// card plane did in v1 (facetPunch).
//
// A facet is SUNK IN cavity `c` when its root is below the cavity's own mouth
// (its lift under c's), the cavity holds its front-view footprint to L117's
// 0.5 mm, and it belongs to the cavity's part: the same owner, or one under
// it (a device well round a whole card is not that card's pocket). A facet
// rooted at or above the mouth - every facet before recessed facets - is
// never sunk, so none of this runs for those drawings.
function _ownedBy(o, c) {
  return o.owner === c.owner || (!!c.owner && !!o.owner && o.owner.startsWith(`${c.owner}/`));
}
export function sunkIn(o, c, tol = 0.5) {
  const pc = c.proj || c;
  return !!o.facet && !o.tilt && (o.lift || 0) < (c.lift || 0) - 0.01 && _ownedBy(o, c)
    && o.x >= pc.x - tol && o.y >= pc.y - tol
    && o.x + o.w <= pc.x + pc.w + tol && o.y + o.h <= pc.y + pc.h + tol;
}
// THE POCKET A SUNK FACET STANDS IN, as emptyHeightAt reads it: the smallest
// untilted cavity with a floor it is sunk in, {x, y, w, h, floor, mouth}, the
// floor at the cavity's lift less its built depth (`depthOf`). null if none.
export function pocketOf(o, cavities, depthOf = c => c.d) {
  let best = null;
  for (const c of cavities) {
    if (c.tilt || c.hollow || c.seeThrough || !sunkIn(o, c)) continue;
    if (!best || c.w * c.h < best.w * best.h) best = c;
  }
  return best && {x: best.x, y: best.y, w: best.w, h: best.h,
                  floor: (best.lift || 0) - depthOf(best), mouth: best.lift || 0};
}
// WHERE A TILTED WELL CROSSES THE SLAB zlo..zhi (face mm): its true box, x/y
// as built and z from its lift back `d`, carried by tiltFrame; each of the
// twelve edges clipped to the slab, and the xy bounds of what is left. null
// when the well does not reach the slab.
function _wellSection(w, d, zlo, zhi) {
  const M = tiltFrame(w.tilt), l = w.lift || 0;
  const ap = ([x, y, z]) => [M[0] * x + M[4] * y + M[8] * z + M[12],
                             M[1] * x + M[5] * y + M[9] * z + M[13],
                             M[2] * x + M[6] * y + M[10] * z + M[14]];
  const V = [];
  for (const x of [w.x, w.x + w.w]) for (const y of [w.y, w.y + w.h]) for (const z of [l - d, l])
    V.push(ap([x, y, z]));
  const hit = [];
  for (let a = 0; a < 8; a++) for (const bit of [1, 2, 4]) {
    if (a & bit) continue;
    const P = V[a], Q = V[a | bit], dz = Q[2] - P[2];
    let ta = 0, tb = 1;
    if (Math.abs(dz) < 1e-12) { if (P[2] < zlo || P[2] > zhi) continue; }
    else {
      const t1 = (zlo - P[2]) / dz, t2 = (zhi - P[2]) / dz;
      ta = Math.max(0, Math.min(t1, t2)); tb = Math.min(1, Math.max(t1, t2));
      if (ta > tb) continue;
    }
    for (const t of [ta, tb]) hit.push([P[0] + t * (Q[0] - P[0]), P[1] + t * (Q[1] - P[1])]);
  }
  if (!hit.length) return null;
  const xs = hit.map(p => p[0]), ys = hit.map(p => p[1]);
  const x0 = Math.min(...xs), y0 = Math.min(...ys);
  return {x: x0, y: y0, w: Math.max(...xs) - x0, h: Math.max(...ys) - y0};
}
// SO THE FLOOR AND THE BACK ARE CLEARED
//  - under the footprint of each facet sunk in `c`, and
//  - where each tilted cavity on such a facet (`cavities`, its `tilt.on`
//    naming the facet) crosses the slab between the back (`backZ`) and the
//    floor (`floorZ`). A well runs back along the facet normal, so it meets
//    the floor down-slope of its facet - past the footprint whenever the
//    pocket is deeper than the lift, or no return or next tooth follows.
// `depthOf` is a well's built depth. Returns `rect` punches in face mm,
// clipped to the cavity; a well clear carries `well: true`. Nothing is
// clipped from a well itself.
export function facetFloorClears(c, outs, {cavities = [], depthOf = w => w.d, tol = 0.5,
                                            floorZ = (c.lift || 0) - depthOf(c) + 0.1,
                                            backZ = (c.lift || 0) - depthOf(c) - 0.15} = {}) {
  if (c.tilt) return [];
  const pc = c.proj || c, res = [], ids = new Set();
  const clip = (r, extra) => {
    const x0 = Math.max(r.x, pc.x), y0 = Math.max(r.y, pc.y);
    const x1 = Math.min(r.x + r.w, pc.x + pc.w), y1 = Math.min(r.y + r.h, pc.y + pc.h);
    if (x1 > x0 && y1 > y0) res.push({kind: 'rect', x: x0, y: y0, w: x1 - x0, h: y1 - y0, ...extra});
  };
  for (const o of outs) {
    if (!sunkIn(o, c, tol)) continue;
    ids.add(o.facet.id);
    clip(o, {facet: o.facet.id});
  }
  for (const w of cavities) {
    if (!w.tilt || !ids.has(w.tilt.on)) continue;
    const s = _wellSection(w, depthOf(w), Math.min(backZ, floorZ), Math.max(backZ, floorZ));
    if (s) clip(s, {facet: w.tilt.on, well: true});
  }
  return res;
}
// THE FLOOR RASTER IS CUT FROM UNFLIPPED ART, while a flipped face (flipLX /
// flipLY) places geometry mirrored: a clear is mirrored within the cavity's
// front-view rect `pc` on each flipped axis, so it lands under the tooth.
export function mirrorClears(clears, pc, flipX, flipY) {
  if (!flipX && !flipY) return clears;
  return clears.map(p => ({...p,
    x: flipX ? pc.x + pc.x + pc.w - p.x - p.w : p.x,
    y: flipY ? pc.y + pc.y + pc.h - p.y - p.h : p.y}));
}
// clear `rect` punches from a canvas whose origin is (ox, oy) face mm
export function clearFloor(cvs, clears, ox, oy, pxmm) {
  if (!clears || !clears.length) return cvs;
  const ctx = cvs.getContext('2d');
  for (const p of clears) ctx.clearRect(...punchRectPx(p, ox, oy, pxmm));
  return cvs;
}
// THE GROUP THAT CARRIES A TILT (see buildFaceRelief). Its matrix is
// M_face * tiltFrame(t) * M_face^-1, M_face being the LX/LY map of a face `fw`
// x `fh` mm, mirror included. One per parent and facet anchor. Under a group
// already tilted with the same key the parent itself is returned; under one
// with a different key only the difference is applied, so a child still
// rides with its host. `userData.tilt` names the tilt for anything placed
// later (a halo, a lamp); the matrices live in a side table, not userData,
// which the GLB export serialises.
const TILT_META = new WeakMap(), TILT_KIDS = new WeakMap();
export function tiltGroupIn(parent, t, {fw, fh, flipLX = false, flipLY = false}) {
  const key = `${t.on}|${t.anchor.join(',')}`;
  let anc = parent;
  while (anc && !TILT_META.has(anc)) anc = anc.parent;
  const up = anc && TILT_META.get(anc);
  if (up && up.key === key) return parent;
  if (!TILT_KIDS.has(parent)) TILT_KIDS.set(parent, new Map());
  const kids = TILT_KIDS.get(parent);
  if (kids.has(key)) return kids.get(key);
  const sx = flipLX ? -1 : 1, sy = flipLY ? -1 : 1;
  const toL = new THREE.Matrix4().set(sx, 0, 0, -sx * fw / 2,  0, -sy, 0, sy * fh / 2,
                                      0, 0, 1, 0,  0, 0, 0, 1);
  const fromL = new THREE.Matrix4().set(sx, 0, 0, fw / 2,  0, -sy, 0, fh / 2,
                                        0, 0, 1, 0,  0, 0, 0, 1);
  const G = toL.multiply(new THREE.Matrix4().fromArray(tiltFrame(t))).multiply(fromL);
  const g = new THREE.Group();
  g.matrix.copy(up ? up.G.clone().invert().multiply(G) : G);
  g.matrixAutoUpdate = false;
  g.userData.tilt = {...t, anchor: [...t.anchor]};
  TILT_META.set(g, {key, G});
  kids.set(key, g);
  parent.add(g);
  return g;
}

// A DEPTH THAT VARIES ACROSS A NODE, INSIDE THE NODE'S OWN OUTLINE. `profile`
// and `profile-y` built their height field over the bounding box, so a sloped
// moulding could only be a rectangle; the MaiaEdge PBC-2000's centre pane has
// ends that ARE its windows' ends - chamfer, vertical, chamfer - and a box
// either ran into the windows or stopped short of the chamfer corners.
//
// The region is ear-clipped ONCE, and each triangle is then cut by the grid
// cells it crosses (Sutherland-Hodgman - triangle and cell are both convex, so
// the cut is exact) and every vertex stood at depthAt(x, y). Grid lines sit on
// the profiles' knots, so a knee is still a knee. Clipping the concave outline
// by the cells first was tried and was wrong: it left edges along the cell
// boundaries that enclosed part of a window next to its corner. The skirt
// drops every outline point from the surface to `lift`, so the walls follow the
// outline too. Coordinates are node-local mm.
//
// HOLES ARE CUT, because the bezel turned out to be the whole face: one sloped
// plate with the two octagonal windows through it. Each hole is bridged into
// its shell by a zero-width cut straight up from its topmost point - the
// keyhole earcut uses - so the region is one simple polygon again. The walls of
// holes come back apart from the outer wall (`holeSkirt`), because on the
// hardware they are a different colour: a window's edge is the amber bead. A
// hole that cannot be bridged (nothing of the shell above it) is not cut, and
// gets no wall either.
//
// `regions` is [{shell, holes: [ring...]}], rings as [[x, y]...].
export function shapedHeightField(regions, xs, ys, depthAt, lift = 0) {
  const clip = (poly, keep, cut) => {
    const out = [];
    for (let i = 0; i < poly.length; i++) {
      const a = poly[i], b = poly[(i + 1) % poly.length];
      const ia = keep(a), ib = keep(b);
      if (ia) out.push(a);
      if (ia !== ib) out.push(cut(a, b));
    }
    return out;
  };
  const atX = (x) => (a, b) => [x, a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0])];
  const atY = (y) => (a, b) => [a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]), y];
  const signed = r => {
    let s = 0;
    for (let i = 0, j = r.length - 1; i < r.length; j = i++)
      s += (r[j][0] - r[i][0]) * (r[j][1] + r[i][1]);
    return s / 2;
  };
  const tidy = poly => {
    const out = [];
    for (const p of poly) {
      const q = out[out.length - 1];
      if (!q || Math.abs(q[0] - p[0]) > 1e-9 || Math.abs(q[1] - p[1]) > 1e-9) out.push(p);
    }
    while (out.length > 1 && Math.abs(out[0][0] - out[out.length - 1][0]) < 1e-9
           && Math.abs(out[0][1] - out[out.length - 1][1]) < 1e-9) out.pop();
    return out;
  };
  const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const earclip = (poly) => {
    // counter-clockwise in a y-down frame is clockwise on paper; normalise so
    // every convex corner has a positive cross product
    const P = signed(poly) < 0 ? poly.slice().reverse() : poly.slice();
    const idx = P.map((_, i) => i), tris = [];
    let guard = 0;
    while (idx.length > 3 && guard++ < 10000) {
      let found = false;
      for (let k = 0; k < idx.length; k++) {
        const i0 = idx[(k + idx.length - 1) % idx.length], i1 = idx[k], i2 = idx[(k + 1) % idx.length];
        const [a, b, c] = [P[i0], P[i1], P[i2]];
        const cr = cross(a, b, c);
        if (cr < -1e-12) continue;                    // reflex corner
        if (Math.abs(cr) <= 1e-12) { idx.splice(k, 1); found = true; break; }  // collinear: drop it
        let blocked = false;
        for (const j of idx) {
          if (j === i0 || j === i1 || j === i2) continue;
          const p = P[j];
          if (cross(a, b, p) > 1e-12 && cross(b, c, p) > 1e-12 && cross(c, a, p) > 1e-12) { blocked = true; break; }
        }
        if (blocked) continue;
        tris.push([a, b, c]);
        idx.splice(k, 1);
        found = true;
        break;
      }
      if (!found) break;
    }
    if (idx.length === 3) tris.push(idx.map(i => P[i]));
    return tris;
  };

  const orient = (r, ccw) => (signed(r) < 0) === ccw ? r.slice() : r.slice().reverse();
  const bridge = (shell, holes, cut) => {
    let outer = orient(tidy(shell), true);
    const hs = holes.map((h, n) => ({h: orient(tidy(h), false), n}))
      .sort((a, b) => Math.min(...a.h.map(p => p[1])) - Math.min(...b.h.map(p => p[1])));
    for (const {h, n} of hs) {
      let hi = 0;
      for (let k = 1; k < h.length; k++) if (h[k][1] < h[hi][1]) hi = k;
      const [hx, hy] = h[hi];
      let best = -1, by = -Infinity;
      for (let k = 0; k < outer.length; k++) {
        const a = outer[k], b = outer[(k + 1) % outer.length];
        const lo = Math.min(a[0], b[0]), up = Math.max(a[0], b[0]);
        if (!(hx >= lo && hx < up)) continue;
        const y = a[1] + (b[1] - a[1]) * (hx - a[0]) / (b[0] - a[0]);
        if (y < hy && y > by) { by = y; best = k; }
      }
      if (best < 0) continue;            // no edge above it: not inside this shell
      cut.add(n);
      const p = [hx, by];
      const loop = h.slice(hi).concat(h.slice(0, hi), [h[hi]]);
      outer = outer.slice(0, best + 1).concat([p], loop, [p], outer.slice(best + 1));
    }
    return outer;
  };

  // Douglas-Peucker: the outline arrives sampled every 0.25 mm, and the ear
  // clipper below is quadratic in it. Walls keep every sample; only the
  // triangulation works from the simplified ring.
  const simplify = (r, eps = 0.02) => {
    if (r.length < 4) return r.slice();
    const keep = new Array(r.length).fill(false);
    const seg = (p, a, b) => {
      const dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy);
      return L < 1e-12 ? Math.hypot(p[0] - a[0], p[1] - a[1])
                       : Math.abs(dy * p[0] - dx * p[1] + b[0] * a[1] - b[1] * a[0]) / L;
    };
    const stack = [[0, r.length - 1]];
    keep[0] = keep[r.length - 1] = true;
    // split the closed ring at its far point so the open run has two ends
    let far = 0, fd = -1;
    for (let k = 1; k < r.length; k++) {
      const d = Math.hypot(r[k][0] - r[0][0], r[k][1] - r[0][1]);
      if (d > fd) { fd = d; far = k; }
    }
    keep[far] = true;
    stack.length = 0; stack.push([0, far], [far, r.length - 1]);
    while (stack.length) {
      const [i0, i1] = stack.pop();
      let bi = -1, bd = eps;
      for (let k = i0 + 1; k < i1; k++) {
        const d = seg(r[k], r[i0], r[i1]);
        if (d > bd) { bd = d; bi = k; }
      }
      if (bi >= 0) { keep[bi] = true; stack.push([i0, bi], [bi, i1]); }
    }
    return r.filter((_, k) => keep[k]);
  };
  const cutTriangle = (tri, x0, x1, y0, y1) => {
    let p = tri;
    p = clip(p, q => q[0] >= x0, atX(x0));
    if (p.length) p = clip(p, q => q[0] <= x1, atX(x1));
    if (p.length) p = clip(p, q => q[1] >= y0, atY(y0));
    if (p.length) p = clip(p, q => q[1] <= y1, atY(y1));
    return tidy(p);
  };

  const pos = [], idx = [], cutHoles = [];
  const put = (x, y) => { pos.push(x, y, depthAt(x, y)); return pos.length / 3 - 1; };
  for (const {shell: rawShell, holes = []} of regions) {
    const cut = new Set();
    // TRIANGULATE THE WHOLE REGION FIRST, THEN CUT EACH TRIANGLE BY THE GRID.
    // Clipping a concave outline against a cell leaves edges running along the
    // cell boundary, and next to a window's corner those enclosed part of the
    // window. A triangle is convex, so cutting it by a cell is exact; the grid
    // is still what puts a vertex on every profile knot.
    const shell = simplify(rawShell);
    const region = holes.length ? bridge(shell, holes.map(h => simplify(h)), cut) : shell;
    cutHoles.push(...holes.filter((_, n) => cut.has(n)));
    for (const tri of earclip(tidy(region))) {
      const bx0 = Math.min(tri[0][0], tri[1][0], tri[2][0]), bx1 = Math.max(tri[0][0], tri[1][0], tri[2][0]);
      const by0 = Math.min(tri[0][1], tri[1][1], tri[2][1]), by1 = Math.max(tri[0][1], tri[1][1], tri[2][1]);
      for (let j = 0; j + 1 < ys.length; j++) {
        if (ys[j + 1] <= by0 || ys[j] >= by1) continue;
        for (let i = 0; i + 1 < xs.length; i++) {
          if (xs[i + 1] <= bx0 || xs[i] >= bx1) continue;
          const p = cutTriangle(tri, xs[i], xs[i + 1], ys[j], ys[j + 1]);
          if (p.length < 3 || Math.abs(signed(p)) < 1e-9) continue;
          for (let k = 1; k + 1 < p.length; k++) {      // convex: a fan will do
            if (Math.abs(cross(p[0], p[k], p[k + 1])) < 1e-9) continue;
            idx.push(put(...p[0]), put(...p[k]), put(...p[k + 1]));
          }
        }
      }
    }
  }
  const wall = rings => {
    const spos = [], sidx = [];
    for (const ring of rings) {
      const base = spos.length / 6;
      for (const [x, y] of ring) spos.push(x, y, depthAt(x, y), x, y, lift);
      for (let k = 0; k < ring.length; k++) {
        const a = 2 * (base + k), b = a + 1;
        const c = 2 * (base + (k + 1) % ring.length), d = c + 1;
        sidx.push(a, b, c, b, d, c);
      }
    }
    return {pos: spos, idx: sidx};
  };
  return {top: {pos, idx},
          skirt: wall(regions.map(r => r.shell)),
          holeSkirt: wall(cutHoles)};
}

export function bodyBoxes(body, faceW, faceH) {
  const color = body.color || '#3a3f44';
  if (body.boxes && body.boxes.length) {
    return body.boxes.map((b, i) => ({
      id: b.id || `box-${i}`, x: b.at[0], y: b.at[1], w: b.size[0], h: b.size[1],
      z0: b.from || 0, z1: (b.from || 0) + b.depth, color: b.color || color}));
  }
  const fp = body.footprint || {at: [0, 0], size: [faceW, faceH]};
  return [{id: 'body', x: fp.at[0], y: fp.at[1], w: fp.size[0], h: fp.size[1],
           z0: 0, z1: body.depth, color}];
}

// WHERE A CABLE LANDS, in the chassis frame. Exported as two halves on
// purpose: the SUM is pure and is tested under bare node, the QUERY needs a
// document and is exercised by a hand-built fake tree plus (for the real
// compiled output) the Task 4 tests. jsdom is not a dependency here.
//
// `ancestors` runs OUTERMOST-LAST: index 0 is the marker's own parent, and
// each later entry is one step further out, ending at whatever sits just
// inside the svg - the same walk `nodeTools.liftOf` does, spelled out on
// plain objects so it can be checked without a document. Every entry
// contributes its own `lift` to the sum, and `z` is that sum - unless the
// marker carries `rear`, the absolute far face of the feature it sits on,
// which then IS `z` (see below).
//
// NO `out` TERM, DELIBERATELY, AND THE REASON IS THE SEMANTICS AND NOT A
// SURVEY. `lift` and `out` are read differently by this module and always
// have been: a lift is RELATIVE and is summed up the ancestor chain, while
// `data-z-out` is an ABSOLUTE distance from the panel (the rule
// _inset_feature's docstring in render.py is built on, and the one whose
// violation produced the dcp-f-a22 white spikes). An absolute figure cannot
// be summed into a relative walk and cannot be added to one: an ancestor's
// `out` already counts from the panel, so folding it in here would place the
// point at panel + lift + out, a distance nothing measures.
//
// An earlier version of this function did read an outermost ancestor's `out`,
// and an earlier version of THIS COMMENT defended dropping it by claiming
// that no ancestor of a `cable` marker in any real drawing carries
// data-z-out. That claim was laundered from a single drawing. Swept over
// every built drawing in library/dist, 9 of the 23,629 connection-point
// markers sit under an ancestor that DOES carry one - all nine in
// dcp-2.ila-node.front.svg, under `slot-1--module--body-square` at
// data-z-out "44.0". The argument above does not depend on how many there
// are, which is the point: it would hold at zero and it holds at nine.
//
// THAT DIFFERENT MECHANISM NOW EXISTS, AND IT REPLACES RATHER THAN SUMS
// (pluggables D). Plugs and boots declare relief, and a boot is 15.1 or 26.4
// long: the ancestor walk put a boot's cable at the boot's FRONT face, where
// it meets the plug, when the cable leaves from its REAR. The seated chain
// generic/sfp-lc-simplex@2 -> generic/lc-plug@2 -> common/lc-boot@1 makes the
// arithmetic concrete: the boot's group carries data-z-lift 22.5 (the optic's
// 10.0 plus the plug body's 12.5), the lift walk gave z 22.5, and the boot's
// body is built from 22.5 to its data-z-out of 37.6 - 15.1 short. So a point
// can now name the relief feature it sits on (the contract's `on:`, which
// render.py emits on the marker as `data-cp-on`, the feature node's compiled
// id), and `rear` is that node's data-z-out. `rear` is ABSOLUTE, the same
// number relief.js builds the feature's far face at, so when it is present
// it IS `z` - it is never added to the lift, which is what the paragraphs
// above forbid. `lift` still comes back as the part's own face. A point with
// no `on:`, or whose feature is missing or unreadable, keeps z = lift.
//
// A CYLINDER HAS NO data-z-out, AND ITS REAR IS ITS FAR END. A `cyl` feature
// (a round stub a cable leaves from) is built by relief.js from its node's
// summed lift to that plus data-z-cyl, so its rear is RELATIVE, not absolute:
// `cylLift` is the feature node's own lift, summed from the feature up to the
// marker's parent (cablePoints walks it), and z = the ancestors' lift +
// cylLift + cyl - the same sum liftOf makes, with the cyl added. `rear`, when
// present, still wins: an `out` feature resolves exactly as it did. An
// unreadable cyl keeps z = lift, like an unreadable rear.
//
// A LIFT THAT DOES NOT PARSE IS ZERO; A POINT THAT DOES NOT PARSE IS NULL,
// and the asymmetry is deliberate. A junk lift has a safe reading - the
// feature is not displaced - and a NaN there would silently delete the cable
// from 3D, which is the worse failure. A junk or absent `at` has no safe
// reading: coercing it to [0, 0] lands the cable at the part's ORIGIN, a
// position that looks entirely plausible on a drawing and is wrong by however
// large the part is. So it comes back `null`, which the first consumer to do
// arithmetic on it fails on immediately, at the point of use, with the
// marker in hand.
export function resolveCablePoint(marker, ancestors = []) {
  const num = v => (Number.isFinite(+v) ? +v : 0);
  const lift = ancestors.reduce((z, a) => z + num(a && a.lift), 0);
  const raw = marker.at || [];
  const ok = raw.length === 2 && raw.every(v => v !== '' && v !== null && Number.isFinite(+v));
  const given = v => v !== undefined && v !== null && v !== '' && Number.isFinite(+v);
  const rear = marker.rear;
  const z = given(rear) ? +rear
    : given(marker.cyl) ? lift + num(marker.cylLift) + +marker.cyl
    : lift;
  return {
    name: marker.name,
    at: ok ? [+raw[0], +raw[1]] : null,
    dir: marker.dir ?? null,
    lift, z,
  };
}

// Every `cable` marker in a drawing, resolved to one point per CONNECTOR.
// This is the function a cabling library consumes; page code should not walk
// data-cp itself.
//
// WHAT IS AND IS NOT RESOLVED, stated plainly because the spec's phrase
// "resolved chassis-frame position and direction" promises more than this
// returns. `z` IS resolved, in millimetres off the panel: the summed ancestor
// lift, or - for a point `on:` a relief feature - that feature's data-z-out (a cyl's far end, lift + data-z-cyl). `at` IS NOT: it is the marker's OWN-FRAME point, exactly as the
// part's contract declared it, with none of the group transforms between the
// part and the svg applied. `dir` is the declared direction, unrotated.
//
// So the owning ELEMENT comes back as `el`, and finishing the job is the
// consumer's: `el.getScreenCTM()` against the svg's (nodeTools' `inv` above is
// the same idiom) maps `at` into face millimetres, and a mirrored or rotated
// placement is handled by that matrix rather than by re-deriving it here. No
// matrix API is invented for this - there is no consumer yet to design one
// against, and a wrong guess at the shape would be harder to remove than the
// absence is to fill.
//
// A connector can carry more than one `cable` marker at once - a boot mated
// onto a plug both declare one, because each is the same physical connection
// point from its own contract's point of view - and the outermost survives:
// the boot's marker when a boot is seated, the plug's when it is not.
//
// A cable lands on the OUTERMOST point of a connector. Stated structurally:
// a marker is SHADOWED when another marker sits strictly deeper on the same
// chain. Two DIFFERENT relations record "same chain", and grouping has to
// walk both:
//
//   - PATH ANCESTRY, the original rule: a part composed through a
//     contract's `parts:` (render.py builds the child's path as
//     `<parent>/<part id>`) or a module seated in a bay (`<bay>/module`)
//     gets a `data-path` that nests under its container's, one owner path a
//     prefix of the other, on a "/" boundary so "sfp-1" is never read as a
//     parent of "sfp-10".
//   - SEAT CHAINS, added here. A `mate-to` occupant is a TOP-LEVEL SIBLING
//     of its host in the compiled drawing - render.py appends it to the
//     view root, not under the host's group - so a boot seated on a plug
//     seated on a cage gets THREE UNRELATED top-level paths ("cage",
//     "cage-plug", "cage-plug-boot"), no one a prefix of another. PATH
//     ANCESTRY CANNOT SEE THIS RELATIONSHIP: it is not encoded in the path,
//     by construction, so no amount of cleverness in a prefix test finds
//     it. What DOES record it is `data-for`, which render.py sets on every
//     seated placement's group - REGARDLESS OF HOW THE SEAT WAS AUTHORED.
//     That last clause was once wishful: only the `occupants:` expansion
//     wrote `for: host`, so a HAND-WRITTEN `mate-to` (which the spec offers
//     in the same breath) carried no `data-for`, this grouping never fired
//     for it, and a plug with a boot on it came back as two points for one
//     connector. render.py now DEFAULTS `for` to the `mate-to` target at
//     resolution time, so both authorings record a host.
//
//     A DEFAULT, THOUGH, NOT AN OVERRIDE: `for:` is older than seating and
//     means "what this part belongs to", so an author who writes one on a
//     `mate-to` placement keeps it, and that value is what this function
//     walks. It need not be the host - it can name any part, in any view.
//     So do not read a seat's `data-for` as "my host"; read it as "what this
//     part says it belongs to", which for the common case IS the host.
//     Walking `data-for` to a root groups a
//     whole chain of seats the same
//     way path-prefix already groups a composed or bayed one - do not
//     "simplify" this back to path-prefix alone; that is exactly the
//     regression this function exists to prevent, and it has a live test
//     (spec/tests/js/cable-points.mjs's connector K) that fails the moment
//     it happens.
//
// Composed parts carry no `data-for` at all, so path-prefix stays as the
// fallback - it is still the only signal for that shape, and dropping it
// would un-group every `parts:`-composed and bay-nested case this module
// already passed.
//
// An earlier version of this function used a union-find over a "same
// connector" relation that was not transitive: "a/b" and "a/b/c" belong
// together, "a/b/c" and "a/b/d" do not, but union-find merges all three
// through the shared middle "a/b" - a connector that carries its own marker
// AND two marked descendants fused all three into one point. Nothing in the
// library can build that shape yet; spec B2's plugs and boots can, and this
// function has no other consumer.
const shadowed = (p, all) => all.some(q => q !== p && q.startsWith(p + '/'));

// Resolve one `data-for` value to the local owner it names, or null.
// `data-for` can carry more than one space-separated token (render.py's
// `data_for` - a silkscreen mark can annotate several things at once) and a
// cross-view token comes out leading with "/" (`/rear/psu-0`). BOTH SHAPES
// REACH A SEAT. This comment used to say a `mate-to` occupant's `data-for`
// "is never either of those - it is always exactly the bare local id of its
// host", and that stopped being true when render.py made its `mate-to`
// default yield to an author's explicit `for:`: a seated placement carrying
// its own `for:` regroups its cable chain by THAT value, which may be
// multi-token, may be cross-view, and may name something that is not its
// host at all. Intended and tested, not a loophole - so the loop below is
// load-bearing rather than defensive, and must not be "simplified" to a
// single lookup on the whole attribute. Tokens are tried in order; a
// leading-slash one names another view and is skipped, and a token this
// drawing has no marked owner for (a typo, or a genuinely cross-view
// target) is skipped too, not thrown on. See cable-points.mjs's connector O,
// which plants an owner under a literal "/rear/x" so the skip is
// observable.
function seatOwner(el, byPath) {
  const raw = (el.dataset && el.dataset.for) || '';
  for (const tok of raw.split(/\s+/).filter(Boolean)) {
    if (tok[0] === '/') continue;
    const found = byPath.get(tok);
    if (found) return found;
  }
  return null;
}

// The chain from `owner` up to its connector's root, walking `data-for` one
// hop at a time. `seen` stops it cold on a cycle - a `data-for` that names
// an owner already in the chain - rather than spinning forever; an
// unresolved `data-for` (`seatOwner` returns null) ends the chain exactly
// like a root that carries no `data-for` at all.
function seatChain(owner, byPath) {
  const chain = [];
  const seen = new Set();
  let cur = owner;
  while (cur) {
    if (seen.has(cur)) {
      // SAID OUT LOUD, LIKE THE UNREADABLE POINT BELOW. Terminating was never
      // in doubt - `seen` did that from the start - but terminating QUIETLY
      // is not the same thing: a 2-cycle makes each side shadow the other, so
      // BOTH connectors vanish from the returned list with nothing said. That
      // is the identical failure mode an unreadable `data-cp-at` gets a
      // warning for a few lines down, and it deserves the identical treatment.
      // Only a hand-edited or truncated drawing can produce it - render.py
      // refuses a `mate-to` cycle outright - which is exactly the case worth
      // naming out loud rather than diagnosing from an absence.
      console.warn(`cablePoints: data-for cycle - the seat chain from ` +
                   `${owner.dataset.path || '(no data-path)'} revisits ` +
                   `${cur.dataset.path || '(no data-path)'}; the walk stops ` +
                   `there and connectors on this chain may be dropped`);
      break;
    }
    chain.push(cur);
    seen.add(cur);
    cur = seatOwner(cur, byPath);
  }
  return chain;
}

export function cablePoints(svg) {
  const entries = [...svg.querySelectorAll('[data-cp="cable"]')].map(mk => {
    // The whole attribute, not its first two tokens: "1 2 3" is as malformed
    // as "banana", and silently keeping the 1 and the 2 is the same class of
    // plausible-looking wrong answer as defaulting to the origin.
    const coords = (mk.dataset.cpAt || '').trim().split(/\s+/);
    const marker = {name: mk.dataset.cp, at: coords.length === 2 ? coords : null,
                    dir: mk.dataset.cpDir ?? null};
    const ancestors = [];
    for (let n = mk.parentElement; n && n !== svg; n = n.parentElement) {
      ancestors.push({lift: n.dataset.zLift});
    }
    const owner = mk.closest('[data-path]');
    // THE FEATURE A POINT SITS ON is a skin node inside the same instance
    // group as the marker (render.py's `data-cp-on`), so the lookup is scoped
    // to the marker's own parent - never the whole drawing, where a projection
    // or another view could carry the same id.
    const on = mk.dataset.cpOn;
    if (on) {
      const host = mk.parentElement;
      const feat = host && host.querySelector
        ? host.querySelector(`[id="${on.replace(/"/g, '\\"')}"]`) : null;
      if (feat && feat.dataset.zOut !== undefined) marker.rear = feat.dataset.zOut;
      else if (feat && feat.dataset.zCyl !== undefined) {
        // a cyl's rear is its far end: its own lift, summed from the feature
        // up to (not including) the marker's parent, plus its length
        let own = 0;
        for (let n = feat; n && n !== host; n = n.parentElement)
          own += Number.isFinite(+n.dataset.zLift) ? +(n.dataset.zLift || 0) : 0;
        marker.cyl = feat.dataset.zCyl;
        marker.cylLift = own;
      }
      else console.warn(`cablePoints: ${owner ? owner.dataset.path : '(no data-path)'} ` +
                        `declares its cable point on ${JSON.stringify(on)}, which ` +
                        `carries no data-z-out or data-z-cyl here; z falls back to the part's face`);
    }
    const pt = {...resolveCablePoint(marker, ancestors),
                path: owner ? owner.dataset.path : '', el: mk};
    // SAID OUT LOUD, ONCE, WHERE THE OWNER IS STILL KNOWN. `at: null` is
    // enough to stop a cable landing at the origin, but on its own it
    // surfaces as a TypeError in someone else's library with no idea which
    // part produced it. The compiled drawing is machine-written, so this
    // fires only on a hand-edited or truncated one - which is precisely the
    // case worth naming.
    if (!pt.at)
      console.warn(`cablePoints: ${pt.path || '(no data-path)'} declares an ` +
                   `unreadable data-cp-at ${JSON.stringify(mk.dataset.cpAt)}; ` +
                   `its point is null rather than [0, 0]`);
    return {pt, owner};
  });

  // Only an owner that itself carries a `cable` marker can compete for a
  // connector's point, so that is the only lookup a seat chain ever needs -
  // an intermediate host with a `data-path` but no marker of its own has
  // nothing here to shadow or be shadowed by.
  const byPath = new Map();
  for (const {owner} of entries) if (owner) byPath.set(owner.dataset.path, owner);
  const chains = entries.map(({owner}) => owner ? seatChain(owner, byPath) : []);

  // O(n^2) in the number of cable markers on one drawing, same as the
  // shadow checks above - fine at real-world scale (a handful of connectors
  // per drawing), not worth optimising.
  const paths = entries.map(({pt}) => pt.path);
  // THE TWO RULES ARE INDEPENDENT AND ANDED: a marker survives only if
  // NEITHER shadows it. That is safe only because the two relations never
  // overlap on one chain - a `data-for` never points at a PATH-DESCENDANT of
  // its own owner (composed nesting and occupant `data-for` are disjoint in
  // everything render.py emits today). If that ever stopped being true - a
  // host whose `data-for` named its own composed child, say "a" pointing at
  // "a/b" - path-prefix would shadow "a" and the chain rule would shadow
  // "a/b" independently, and the connector would vanish with NEITHER rule
  // aware the other fired. No runtime check for it here: the invariant holds
  // today and a check would be dead code, but a fix that lets the two rules
  // interact would need one.
  return entries
    .filter(({pt, owner}) =>
      !shadowed(pt.path, paths) &&
      !(owner && chains.some(ch => ch.slice(1).includes(owner))))
    .map(({pt}) => pt);
}

export function configureRelief(deps, scope) {
  // THREE and the renderer are genuinely per-page and stay module-level. The
  // raster density and the FRU path set are per-VIEWER, and a second viewer
  // calling this used to reclaim them from under the first.
  ({THREE, renderer, PXMM, FRU_PATHS} = deps);
  const sc = _sc(scope);
  if (deps.PXMM != null) sc.pxmm = deps.PXMM;
  if (deps.FRU_PATHS) sc.fruPaths = deps.FRU_PATHS;
}

// Every view SVG was fetched with cache: 'no-store' from four separate call
// sites - svgCanvas (once per box face), extractRelief, and twice more in the
// page - so switching configuration re-downloaded the same six files dozens of
// times. On the demo host that was 9.4 of the 11.8 seconds a switch took. The
// URL already carries the config name, so memoising per URL is safe; a build
// tool writes new files under new names.
//
// AND THE FLAG ITSELF IS GONE NOW, for the reason dist.js already gave about the
// JSON: `no-store` kept a rebuilt dist from going stale during development, and
// the memo below does that job within a load - but it also meant the browser
// could not reuse the file across page loads, forever. Entering the 3D tab on
// one switch is 24 requests and 284 KB of face SVG, none of it revalidatable.
// The drawings are much larger than the JSON that argument was made about.
//
// If you are iterating on the build and want the next load to see new bytes,
// hard-reload. That is the tool for it, not a permanent header on every
// drawing.
const SVG_CACHE = new Map();
// A FACE CAN BE OVERRIDDEN FOR A BUILD. A runtime bay swap changes what the device
// looks like without changing any file on disk, and everything downstream here -
// svgCanvas, extractRelief, the hit index, the FRU-path scan - reads its text
// through svgSource. Registering the swapped text against the same URL is what
// lets ONE substitution reach all of them; threading a text argument through five
// signatures instead would have meant five chances to miss one, and the one that
// was missed would look like a rendering fault rather than a plumbing gap.
//
// AN OVERRIDE IS AN OPINION, NOT A FACT, and that is what separates it from the
// cache above. `SVG_CACHE` is keyed by URL and shared on purpose - the same URL
// really is the same bytes, for everybody. An override says what that URL should
// render as FOR ONE VIEWER, and a module-level map has exactly one seat.
//
// It cost a downstream consumer real work: a before/after comparison of one rack
// with two occupant sets could not be built in one page, because whichever
// viewer swapped last won for both. They ran two iframes - two documents, two
// WebGL contexts - to get two copies of this module. Worse than a race, the old
// `clearSvgOverrides()` took no argument and emptied everything, so one viewer
// starting a build silently discarded another's swaps.
//
// So a viewer may own a SCOPE: its swapped faces and its lit lamps, the two
// things here that are per-document rather than per-page. THREE, the renderer
// and the fetch cache stay module-level, because those genuinely are shared.
// Passing no scope uses the default one, which is what every existing caller
// does and what this module did before - so nothing had to change to keep working.
export function createReliefScope(deps = {}) {
  return {overrides: new Map(), states: new Map(), pulled: new Set(),
          pxmm: deps.PXMM, fruPaths: deps.FRU_PATHS};
}
const DEFAULT_SCOPE = createReliefScope();
const _sc = scope => scope || DEFAULT_SCOPE;
// A scope that was never configured falls back to the module-level injection,
// which is what every pre-scope caller relies on.
const _px = scope => _sc(scope).pxmm ?? PXMM;
const _fru = scope => _sc(scope).fruPaths ?? FRU_PATHS;

export function setSvgOverride(url, text, scope) {
  const m = _sc(scope).overrides;
  if (text == null) m.delete(url);
  else m.set(url, text);
}
export function clearSvgOverrides(scope) { _sc(scope).overrides.clear(); }
export function svgSource(url, scope) {
  const ov = _sc(scope).overrides;
  if (ov.has(url)) return Promise.resolve(ov.get(url));
  // A MISS IS MEMOISED AS THE EMPTY STRING, which does two things at once.
  //
  // It removes the HEAD probe. `buildFaceRelief` used to ask whether a view
  // existed with a HEAD and then fetch the same URL again, so every face cost
  // two round trips and the second proved nothing the first had not. Measured on
  // a six-device rack: 66 requests of which 30 were duplicates, one HEAD and one
  // GET per face per device. On localhost that is 287 ms of a 7.4 s build; over
  // a 50 ms link it is 30 serial round trips, about 1.5 s of pure latency, and
  // it scales with the devices on screen.
  //
  // It also fixes a quieter bug: this used to call `r.text()` whatever the
  // status, so a 404's HTML was handed back as if it were a drawing, to be
  // parsed as SVG and fail somewhere further away from the cause.
  //
  // EMPTY STRING RATHER THAN NULL, because every existing caller then degrades
  // instead of throwing: `''.matchAll` yields nothing, `innerHTML = ''` empties
  // the node, `parseFromString('')` raises a parsererror the caller already
  // checks for, and a Blob of '' fails the image load exactly as a 404 page did.
  if (!SVG_CACHE.has(url))
    SVG_CACHE.set(url, fetch(url).then(r => r.ok ? r.text() : ''));
  return SVG_CACHE.get(url);
}
export function clearSvgCache() { SVG_CACHE.clear(); }

// A STATE SET AT RUNTIME IS A CHANGE TO THE DOCUMENT, exactly like a bay swap,
// and it reached 3D exactly as well: not at all. The chip in the tree adds
// `state-10g` to an element in the LIVE SVG the page is showing, and everything
// in here rasterises a document FETCHED from dist/ - a different DOM that has
// never carried a state class in its life. Zero of the library's 390 compiled
// faces do; the class only ever exists in the browser. So every lamp on every
// device painted its unlit fallback in 3D while 2D showed it lit.
//
// The registry is by `data-path` rather than by id or by element, because that
// is the one name the live drawing and the compiled file agree on - the page
// knows what the user clicked by path, and both documents label the same part
// with it. Values are the classes to apply, space-separated, as the page has
// them.
//
// This is deliberately NOT a lamp feature. Nothing here knows what an LED is:
// the classes are applied to whatever elements carry those paths, and any rule
// the drawing's own stylesheet keys off them - a fill, an opacity, an animation,
// a colour on a cylinder's cap - takes effect for the same reason. `data-z-dome`
// is how these lamps happen to be modelled today, and a fix that could only see
// domes would light some of a device's indicators and not others.
// Scoped for the same reason overrides are: which lamps a viewer has lit is that
// viewer's opinion about the document, and two comparisons side by side are
// exactly the case where they differ.

/** Replace the runtime state classes, keyed by data-path. */
export function setNodeStates(map, scope) {
  const st = _sc(scope).states;
  st.clear();
  for (const [path, cls] of map instanceof Map ? map : Object.entries(map || {}))
    if (cls) st.set(path, String(cls));
}
export function clearNodeStates(scope) { _sc(scope).states.clear(); }

// WHAT A VIEWER HAS WRITTEN ON A PART. A field is a node the part declares
// (`fields` in its contract, carried in components.json) and its skin is wired
// to: a `data-from` node's text, a `data-fill-from` node's fill, a
// `data-stroke-from` node's stroke - a supply's wattage, an optic's latch
// colour. The value lands in the parsed document and on the part's group as
// `data-<key>`, and in every texture redrawn from it - the same route a lamp
// state takes. Keyed by the part's data-path; a map of key -> value per part.
// The rule itself is fields.js's, shared with the 2D drawing so the two cannot
// drift: an empty value hides a text node and puts a colour back as drawn.
export function setNodeFields(map, scope) {
  const st = _sc(scope).fields || (_sc(scope).fields = new Map());
  st.clear();
  for (const [path, vals] of map instanceof Map ? map : Object.entries(map || {}))
    if (vals && Object.keys(vals).length) st.set(path, {...vals});
}
export function nodeFields(scope) { return new Map(_sc(scope).fields || []); }
// COLOURS ARE PUT BACK FIRST, over the whole document, for the reason
// applyNodeStates clears first: the registry is the whole truth, and a part
// taken OUT of it arrives as a path that is no longer there. A repaint that
// only visited registered paths would paint a latch red and never paint it grey
// again - and the LOD records repaint from their own last output, so the red
// would be permanent. The drawn colour is stashed on the node, so this needs no
// memory of its own. Outer parts before inner ones, so an optic seated in a
// module keeps its own value for a key the module also sets.
export function applyNodeFields(root, scope) {
  if (!root) return root;
  unpaintFields(root);
  const st = _sc(scope).fields;
  if (!st || !st.size) return root;
  for (const [path, vals] of [...st].sort(([a], [b]) => a.length - b.length))
    // the part on the face that holds it, and its projections on the others
    for (const el of root.querySelectorAll(
        `[data-path="${CSS.escape(path)}"],[data-projection][data-of="${CSS.escape(path)}"]`))
      paintFields(el, vals);
  return root;
}
export function nodeStates(scope) { return new Map(_sc(scope).states); }

// A LAMP COLOUR THE HOST CHOOSES (#664). In 2D a mark's `lamp` is any hex,
// written on the lamp as an inline `--led-color` - how a reader paints a lamp
// whose vendor never published a colour table. In 3D a lamp is part of a
// face texture, so the colour has to be in the TEXT a texture is painted
// from: the route a state takes, repaint and never re-shape. Inline, so it
// wins over the drawing's `#id.state-*` rules as it does in 2D.
//
// HEX ONLY, and validated here, because it lands in a CSS value slot: the
// rule is marks.js's HEX_RE, repeated (and held equal by a test) so relief
// does not import the 2D marks module.
//
// OFF STAYS OFF, as in 2D (`mark.state !== 'off'`): a lamp whose registered
// state is `state-off` keeps its drawing, so a custom colour never lights a
// lamp that is out.
export const LAMP_HEX = /^#(?:[0-9a-f]{3}|[0-9a-f]{4}|[0-9a-f]{6}|[0-9a-f]{8})$/i;
// The declaration is written between two CSS comments so an unlit copy of the
// art (lamps.js withBase) can take exactly it out again and nothing else.
export const LAMP_MARK = '/*portrayal-lamp*/';
const LAMP_END = '/*portrayal-lamp-end*/';
const LAMP_DECL = new RegExp(`${LAMP_MARK.replace(/[*/]/g, '\\$&')}[^/]*${LAMP_END.replace(/[*/]/g, '\\$&')}`, 'g');
/** Strip the host's lamp colours from a fragment of text (an unlit copy). */
export function withoutLampColors(text) { return String(text).replace(LAMP_DECL, ''); }

/** Replace the host's lamp colours, keyed by data-path. Returns the rejected paths. */
export function setNodeLampColors(map, scope) {
  const st = _sc(scope).lampColors || (_sc(scope).lampColors = new Map());
  st.clear();
  const rejected = [];
  for (const [path, colour] of map instanceof Map ? map : Object.entries(map || {})) {
    if (!colour) continue;
    if (LAMP_HEX.test(String(colour))) st.set(String(path), String(colour).toLowerCase());
    else rejected.push(String(path));
  }
  return rejected;
}
export function nodeLampColors(scope) { return new Map(_sc(scope).lampColors || []); }

/** Paint the registered lamp colours onto a parsed document, clearing first. */
export function applyNodeLampColors(root, scope) {
  if (!root) return root;
  // put back what this painted, over the whole document: a colour taken out
  // of the registry arrives as a path that is no longer there
  for (const el of root.querySelectorAll('[data-portrayal-lamp]')) {
    const was = el.getAttribute('data-portrayal-lamp-style');
    if (was) el.setAttribute('style', was); else el.removeAttribute('style');
    el.removeAttribute('data-portrayal-lamp');
    el.removeAttribute('data-portrayal-lamp-style');
  }
  const st = _sc(scope).lampColors;
  if (!st || !st.size) return root;
  const states = _sc(scope).states;
  for (const [path, colour] of st) {
    if (/(^|\s)state-off(\s|$)/.test(states.get(path) || '')) continue;
    for (const el of root.querySelectorAll(`[data-path="${CSS.escape(path)}"]`)) {
      const was = el.getAttribute('style') || '';
      el.setAttribute('data-portrayal-lamp', colour);
      if (was) el.setAttribute('data-portrayal-lamp-style', was);
      el.setAttribute('style', `${was}${was && !/;\s*$/.test(was) ? ';' : ''}`
                               + `${LAMP_MARK}--led-color:${colour}${LAMP_END}`);
    }
  }
  return root;
}

// WHAT A VIEWER HAS TAKEN OFF. A cover hides what is behind it, which is the
// whole reason it is on the device and the whole reason someone wants it off. In
// 2D that is a CSS rule; in 3D the face is a rasterised canvas, so the part is
// baked into a texture and an attribute set after the bake changes nothing. That
// is why pulling had no effect in 3D at all.
//
// So it is applied to the TEXT a texture is painted from, which puts it on the
// same path a lamp state already takes - repaint, never re-shape.
//
// display="none" AND NOT REMOVAL, because a repaint has to be able to put the
// part back. `applyNodeStates` gets away with clearing state classes because it
// can always re-add them; an element that has been deleted from the fragment a
// texture is redrawn from is gone for the session. The marker attribute is what
// distinguishes a part this viewer hid from one the author authored hidden.
//
// NESTED PARTS COME WITH IT. Pulling a supply takes its lamps and its ports,
// because they are on it - a tree row pointing at geometry that is no longer
// drawn is exactly the dangling selection this was reported for.
export function setPulled(paths, scope) {
  const s = _sc(scope).pulled;
  s.clear();
  for (const p of paths || []) if (p) s.add(String(p));
}
export function clearPulled(scope) { _sc(scope).pulled.clear(); }
export function pulledPaths(scope) { return new Set(_sc(scope).pulled); }

/** Is `path` the pulled part itself, or something sitting on it? */
function _isPulled(path, pulled) {
  if (!path) return false;
  for (const p of pulled) if (path === p || path.startsWith(p + "/")) return true;
  return false;
}

/** Hide what this viewer has taken off, in a parsed document. */
export function applyPulled(root, scope) {
  if (!root) return root;
  for (const el of root.querySelectorAll("[data-portrayal-pulled]")) {
    el.removeAttribute("data-portrayal-pulled");
    el.removeAttribute("display");
  }
  const pulled = _sc(scope).pulled;
  if (!pulled.size) return root;
  for (const el of root.querySelectorAll("[data-path]"))
    if (_isPulled(el.getAttribute("data-path"), pulled)) {
      el.setAttribute("data-portrayal-pulled", "");
      el.setAttribute("display", "none");
    }
  // a part's projections on other faces go with it
  for (const el of root.querySelectorAll("[data-projection][data-of]"))
    if (_isPulled(el.getAttribute("data-of"), pulled)) {
      el.setAttribute("data-portrayal-pulled", "");
      el.setAttribute("display", "none");
    }
  return root;
}

// Applied by CLEARING FIRST, over the whole document rather than over the paths
// in the registry. Turning a state off is a state change like any other, and it
// arrives as a path that is no longer in the map - so a version that only
// visited registered paths would light lamps correctly and never put one out.
/** Put the registered classes onto the matching elements of a parsed document. */
export function applyNodeStates(root, scope) {
  if (!root) return root;
  for (const el of root.querySelectorAll('[data-path][class]'))
    for (const c of [...el.classList]) if (c.startsWith('state-')) el.classList.remove(c);
  for (const [path, cls] of _sc(scope).states)
    for (const el of root.querySelectorAll(`[data-path="${CSS.escape(path)}"]`))
      el.classList.add(...cls.split(/\s+/).filter(Boolean));
  return root;
}

// Re-apply the registry to an already-serialised fragment. A state change repaints
// and never re-shapes, so a texture can be redrawn from the text it was built
// from without re-extracting any geometry - which is the whole reason clicking a
// state chip does not cost a rebuild.
export function restyleText(text, scope) {
  if (!text) return text;
  const div = document.createElement('div');
  div.innerHTML = text;
  applyNodeStates(div, scope);
  applyNodeFields(div, scope);
  applyNodeLampColors(div, scope);
  applyPulled(div, scope);
  return div.innerHTML;
}

// A flat drawing outlines the faceplate and rounds its corners so the sheet
// metal reads as a part on a page. On a box, the outline of a face IS the box's
// edge, and both devices cost us something in 3D: the 0.5mm stroke sits half
// inside each face, so where two textured faces meet - front to side, rear to
// side - you get 0.5mm of near-black that reads as a gap you can see through,
// and rx="1.2" makes the four corners genuinely transparent under alphaTest, so
// at each box vertex you really can. Top edges escaped notice only because the
// lid art paints a bright line along them that swamps the seam. Square and
// de-stroke the faceplate before it becomes a texture; the geometry draws the
// edge.
export function squareFaceplate(text) {
  return text.replace(/<rect\b[^>]*\bid="chassis-faceplate"[^>]*>/,
    m => m.replace(/\s(?:rx|ry|stroke|stroke-width)="[^"]*"/g, ''));
}

// The root viewBox, width and height set to the box 0 0 w h (mm), when they
// say anything else; the drawing inside is untouched.
export function toSizeBox(text, w, h) {
  return text.replace(/<svg\b[^>]*>/, tag => {
    const vb = /\sviewBox="([^"]*)"/.exec(tag);
    const n = vb ? vb[1].trim().split(/[\s,]+/).map(Number) : null;
    if (n && n.length === 4 && n[0] === 0 && n[1] === 0 && n[2] === w && n[3] === h) return tag;
    return tag.replace(/\sviewBox="[^"]*"/, ` viewBox="0 0 ${w} ${h}"`)
              .replace(/\swidth="[^"]*"/, ` width="${w}mm"`)
              .replace(/\sheight="[^"]*"/, ` height="${h}mm"`);
  });
}

export async function svgCanvas(url, wmm, hmm, flipX = false, flipYax = false, scope) {
  const text = await svgSource(url, scope);
  const img = new Image();
  const blobUrl = URL.createObjectURL(new Blob([text], {type: 'image/svg+xml'}));
  await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = blobUrl; });
  const cv = document.createElement('canvas');
  const px = _px(scope);
  cv.width = Math.round(wmm * px); cv.height = Math.round(hmm * px);
  const ctx = cv.getContext('2d');
  if (flipX) { ctx.translate(cv.width, 0); ctx.scale(-1, 1); }
  if (flipYax) { ctx.translate(0, cv.height); ctx.scale(1, -1); }
  ctx.drawImage(img, 0, 0, cv.width, cv.height);
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  URL.revokeObjectURL(blobUrl);
  cv._svgText = text;      // kept for adaptive re-rasterisation (see LOD below)
  return cv;
}
// A face canvas is inevitably non-power-of-two (a 548x44mm side is 2192x176 at
// 4px/mm). WebGL2 mipmaps NPOT textures natively, so rescaling to POT buys
// nothing - and it costs: a 2192x176 side squashed to 2048x128 is 1.07x
// horizontally but 1.38x vertically, and that anisotropic resample distorts fine
// repeating detail (the AS5912's 488x5mm vent strips) into something that beats
// against the pixel grid and crawls under motion. Feed the native raster instead.
// ?tex=plain drops mipmaps and anisotropy. Edge artefacts at a corner seen
// nearly edge-on are a sampler question, and samplers differ by GPU and browser
// in ways this machine cannot reproduce - so make the suspect switchable rather
// than argue about it. A corner line that survives ?tex=plain is not sampling.
const TEX_MODE = new URLSearchParams(location.search).get('tex') || '';
export function canvasTex(cv) {
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  if (TEX_MODE === 'plain') {
    tex.anisotropy = 1;
    tex.generateMipmaps = false;
    tex.minFilter = THREE.LinearFilter;
  } else {
    tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
    tex.generateMipmaps = true;
    tex.minFilter = THREE.LinearMipmapLinearFilter;
  }
  tex.needsUpdate = true;
  return tex;
}
// Swap the art on a material that is already in the scene, disposing what it
// replaces. Textures are GPU allocations, and a state chip is a control a user
// will click repeatedly; leaking one per click is how a viewer that felt fine in
// review runs a machine out of memory in a demo.
export function remap(mat, cv) {
  const old = mat.map;
  const tex = canvasTex(cv);
  if (old) { tex.repeat.copy(old.repeat); tex.offset.copy(old.offset); }
  mat.map = tex;
  mat.needsUpdate = true;
  if (old) old.dispose();
}

// crop a mm-rect out of a face canvas (no mirroring: the rear floor plane's
// 180-degree rotation and the box rear-face UVs already reverse X to match)
export function crop(cv, r, pxmm = PXMM) {
  const c = document.createElement('canvas');
  c.width = Math.max(1, Math.round(r.w * pxmm)); c.height = Math.max(1, Math.round(r.h * pxmm));
  const ctx = c.getContext('2d');
  ctx.drawImage(cv, Math.round(r.x * pxmm), Math.round(r.y * pxmm), c.width, c.height, 0, 0, c.width, c.height);
  return c;
}

// WHICH INSTANCES COME OUT, and as what: the behaviour extractRelief builds a
// removable part's body by, from the instance's own marks - `fills` and
// `occupies` as the part says, a legacy body class (psu, fan, tab, power,
// cooling) with no behaviour at all as `class`, and null for anything that
// does not come out (a label, a screw, a part without `data-ref`).
//
// AN OCCUPANT OCCUPIES, WHATEVER IT DECLARES (B3 Task 10c). A plug is
// `class: port` with no behaviour, deliberately (test_behaviour.py holds a
// port to none, and each plug's provenance records why), so it was never
// collected and never pulled, while the cap it replaces was. The kit already
// knows an occupant by its seat: `data-for` its slot, at the build's
// `<slot>-occupant` name (swap.js isOccupantOf, projectedOccupant). That is
// the reading here, so a plug is pulled by its own path exactly as a cap is.
// A projection is flat and is never read (extractRelief's `q`).
export const BODY_CLASSES = ['psu', 'fan', 'tab', 'power', 'cooling'];
export function bodyBehaviour({ref, behaviour, for: host, path, cls} = {}) {
  if (!ref) return null;
  if (behaviour === 'fills' || behaviour === 'occupies') return behaviour;
  if (host && /-occupant$/.test(String(path || ''))) return 'occupies';
  if (!behaviour && BODY_CLASSES.includes(cls)) return 'class';
  return null;
}

// HOW FAR A PART STANDS OFF ITS OWN SEAT, from its relief: the furthest a
// feature of it reaches, less the lift it is seated at. `out` is absolute
// from the panel and every other length runs from its node's own summed lift,
// so each is measured from `base`, the part group's summed lift.
//   feats [{out, cyl, bar, uhandle, lift}] -> mm (0 for a flat part)
export function reliefExtent(feats = [], base = 0) {
  const num = v => (v === undefined || v === null || v === '' || !Number.isFinite(+v)) ? null : +v;
  let top = 0;
  for (const f of feats) {
    if (num(f.out) !== null) top = Math.max(top, num(f.out) - base);
    for (const k of ['cyl', 'bar', 'uhandle'])
      if (num(f[k]) !== null) top = Math.max(top, (num(f.lift) || 0) - base + num(f[k]));
  }
  return top;
}

// HOW FAR A PULLED PART TRAVELS, AND WHETHER IT LEAVES A HOLE.
// A part that says how deep it is - a `body:` block, a `data-body-depth`, or
// an optic's own `data-depth` - travels as it always did: a captive part its
// declared travel, anything else 1.5 x its depth + 25 (60 when a drawing
// predates depths entirely), never further than the face looks less 10, and
// it leaves a dark bay box that deep behind it.
// An OCCUPANT THAT DECLARES NO DEPTH - a dust cap, a plug - has no body
// behind the face to clear: it is the relief it draws. It travels its own
// extent (reliefExtent) plus EJECT_MARGIN and leaves no box, so the port it
// came out of shows as the build draws it - bore, sleeve and ferrule. With
// the depth fallback every cap slid 115 mm and left a 60 mm box in its port
// (B3 Task 10c).
export const EJECT_MARGIN = 10;
export function ejectTravel({body = null, bodyDepth = null, depth = null, occupies = false,
                             extent = 0, into = Infinity} = {}) {
  if (occupies && !body && !bodyDepth && !depth)
    return {pull: Math.min((+extent || 0) + EJECT_MARGIN, into - 10), leavesBay: false, bayDepth: 0};
  const d = body ? body.depth : (bodyDepth || 60);
  const captive = body && body.travel;
  return {pull: Math.min(captive || d * 1.5 + 25, into - 10), leavesBay: true, bayDepth: d};
}

// WHAT A REMOVABLE PART'S BODY IS BUILT AS, from its path and behaviour - the
// decision extractRelief makes for every `fills` / `occupies` instance:
//   {fru}           its own ejectable group, keyed `fru`: a module in a chassis
//                   bay (`front-6/module` -> `front-6`), an optic on a device
//                   cage (`port-4-occupant`);
//   {fru, nested}   an OCCUPANT anywhere below the top - an optic seated on a
//                   card (`front-6/module/xg0-occupant`, #484), a dust cap in
//                   a bore of an adapter on the device (`xc01/1-occupant`) or
//                   on a cassette (`bay-1/module/lc1-occupant`): a FRU of its
//                   own, keyed by its full path, whose group sits inside its
//                   host's when the host is one (the card's, or the optic a
//                   tier is chained on) - pulled on its own, and still gone
//                   with its carrier;
//   {sub}           a module in a module's bay: not a FRU, it comes out with
//                   its carrier `sub`, and is built only from `body.boxes`;
//   null            nothing to build - no path, or, on a module's BACK
//                   (`back`), an occupant: the back is drawn inside its
//                   module's FRU, in the back component's own namespace
//                   (`fhd-2mtp12-lc-rear/mtp1-occupant`), so what it holds is
//                   its art and rides out with the module.
// Deeper than two segments used to mean {sub} for everything, and a generic
// optic declares no boxes, so a card's optic had no body and no pull at all.
// And TWO segments used to mean the first, whatever moved: a Smartoptics
// adapter's two bore caps (`xc01/1-occupant`, `xc01/2-occupant`) came out
// as one FRU named for the adapter, taking the adapter's own art with them,
// and a cassette back's cap as a FRU named for the back - the whole back
// ejected as a "cap" (B3 Tasks 8 and 10c).
export function bodyRole(path, behaviour, {back = false} = {}) {
  const segs = String(path || '').split('/');
  if (!segs[0]) return null;
  if (behaviour === 'occupies' && back) return null;
  if (behaviour === 'occupies' && segs.length > 1) return {fru: segs.join('/'), nested: true};
  if (segs.length <= 2) return {fru: segs[0]};
  return {sub: segs[0]};
}

// WHICH FRU A PATH RIDES WITH: the longest `/`-boundary prefix of `path`
// that is a FRU key (`fruKeys` has(), a Set or an object's key test). A
// card's optic is a FRU inside the card's (bodyRole), so the first segment
// alone - the card's bay - would leave a marker on the optic behind when
// only the optic is pulled. null when nothing on the path is a FRU.
export function fruFor(path, has) {
  const segs = String(path || '').split('/');
  for (let n = segs.length; n > 0; n--) {
    const k = segs.slice(0, n).join('/');
    if (k && has(k)) return k;
  }
  return null;
}

// THE BODY OF A SEATED OPTIC THAT DECLARES NONE: an `occupies` part with no
// `body:` block is one box, its own face outline (`w` x `h`, the element's drawn
// box on the face) run back from the face to the module's own depth - the
// `data-depth` its skin root carries, the contract's size.d (47.5 on the SFP
// generics). It stands inside the cage's recess, which keeps its own depth,
// and it is built into the optic's FRU group so it comes out with the optic.
// Anything else - a module, a part with a `body:` block, an optic with no
// depth - gets null and is built as it always was.
//   {behaviour, body, depth, w, h} -> {w, h, depth} | null
export function opticBody({behaviour, body, depth, w, h} = {}) {
  if (behaviour !== 'occupies' || body) return null;
  const d = +depth, bw = +w, bh = +h;
  if (!(d > 0) || !(bw > 0) || !(bh > 0)) return null;
  return {w: bw, h: bh, depth: d};
}

// THE MEASURING TOOLS FOR ONE PARSED FACE, shared between the build and the
// lamp animator. Both need the same answers - where a node sits in face mm,
// how far off the face it starts, which part owns it, and how to render it
// standalone with the scope its rules were written in - and having two
// copies is how the second one drifts. `svg` must be attached to a document
// (getScreenCTM and getBBox read nothing from a detached tree).
export function nodeTools(svg, {back = false} = {}) {
  const q = sel => [...svg.querySelectorAll(sel)].filter(el => !el.closest('[data-projection]'));
  const inv = svg.getScreenCTM().inverse();
  const mmRect = el => {
    const b = el.getBBox();
    const m = inv.multiply(el.getScreenCTM());
    const pts = [[b.x, b.y], [b.x + b.width, b.y + b.height]]
      .map(([x, y]) => ({x: m.a * x + m.c * y + m.e, y: m.b * x + m.d * y + m.f}));
    const x0 = Math.min(pts[0].x, pts[1].x), y0 = Math.min(pts[0].y, pts[1].y);
    return {x: x0, y: y0, w: Math.abs(pts[1].x - pts[0].x), h: Math.abs(pts[1].y - pts[0].y)};
  };
  const shared = [...q('style, defs')].map(n => n.outerHTML).join('');
  // HOW FAR OFF THE FACE A FEATURE STARTS, summed up the ANCESTOR CHAIN.
  //
  // `lift` is not always written on the node that carries the feature. A composed
  // part gets its lift on the part's instance GROUP (render.py writes it there,
  // because that is the thing being positioned), while the `cyl` or `dome` that
  // has to move sits on a child of it - and `dataset` does not inherit. So an
  // MCX jack mounted on a block standing 15.9mm proud read lift 0 and drew at
  // the panel, underneath its own block.
  //
  // Sum rather than look one level up: a part on a raised block on a raised
  // bezel is a real shape, and the third case arrives the day after the second
  // is special-cased.
  //
  // THIS IS THE SECOND BUG OF EXACTLY THIS SHAPE IN ONE AFTERNOON, and the
  // pattern is worth naming because there will be a third. This module decides
  // what exists in 3D by QUERYING THE DOM FOR ATTRIBUTES, so every query is a
  // chance to miss data that is correctly present. The other case was the FRU
  // class list below, which asked for psu/fan/tab and so could not see the
  // twelve parts that spell the same classes `power` and `cooling`. In both,
  // the manifest was right, the compiled SVG was right, and the extractor threw
  // the answer away - which looks exactly like a modelling gap and is not one.
  // When something declared does not appear in 3D, suspect the selector first.
  const liftOf = el => {
    let z = 0;
    for (let n = el; n && n !== svg; n = n.parentElement) z += +(n.dataset.zLift || 0);
    return z;
  };
  // owning FRU (bay module / pull tab) of a node, for animated removal
  // WHICH PART DID THIS COME FROM - which is not the same question as "is this
  // part a FRU", and conflating the two is what made covers unpullable.
  // The answer is used for two different jobs. Grouping into an ejectable
  // subgroup is still FRU-only: a module leaves a BAY behind it, and building
  // one behind a bolted-on cover would punch a hole in the chassis. But TAGGING
  // every mesh with the part that produced it costs nothing and is what lets a
  // cover be hidden without being ejected.
  // An optic on a card (bodyRole `nested`) is a FRU of its own, so what it
  // draws is owned by it and not by the card's bay.
  // An occupant is known as bodyBehaviour knows it - a plug as well as a
  // cap - and on a module's BACK it owns nothing of its own: it is its
  // module's art, as bodyRole's `back` makes it no FRU (B3 Task 10c).
  const occupantAbove = el => {
    for (let n = el; n && n !== svg && n.dataset; n = n.parentElement)
      if (bodyBehaviour({ref: n.dataset.ref, behaviour: n.dataset.behaviour, for: n.dataset.for,
                         path: n.dataset.path, cls: n.dataset.class}) === 'occupies') return n;
    return null;
  };
  const ownerOf = el => {
    const a = el.closest('[data-path]');
    if (!a) return null;
    const o = back ? null : occupantAbove(el);
    const own = o && bodyRole(o.dataset.path, 'occupies');
    if (own && own.nested) return own.fru;
    return a.dataset.path.split('/')[0] || null;
  };
  // A NODE RENDERED ALONE LOSES THE SCOPE ITS RULES WERE WRITTEN IN, and that is
  // the third bug of the shape the `lift` note above names. `shared` carries the
  // face's whole stylesheet into every one of these standalone documents, but
  // the two forms render.py emits for a declared state colour are
  //
  //   #led-p65-a.state-10g          the element itself
  //   #led-p65-a .state-10g         a descendant of it
  //
  // and the element being rasterised here is `led-p65-a--lamp`, a CHILD of that
  // group. Reparented under a bare transform <g>, neither selector can match:
  // the ancestor simply is not in the document any more. Measured - a lamp whose
  // state is set paints rgb(34,197,94) on the face and rgb(60,65,71) in its own
  // node svg, from the same text and the same stylesheet.
  //
  // So the ancestor chain is rebuilt as empty groups carrying ONLY id and class -
  // never `transform`, since the CTM below already accounts for every one of
  // them, and re-applying them would move the art twice. data-path rides along
  // so a later restyle can tell which nodes a change reaches.
  //
  // This is not about states. Any id-scoped rule the compiled sheet carries -
  // a per-instance fill, a group override, a palette on a component - was
  // equally invisible to relief art before this, and looked like a modelling
  // gap rather than a plumbing one.
  const scopeWrap = (el, inner) => {
    for (let p = el.parentElement; p && p !== svg; p = p.parentElement) {
      // `data-ref` and `data-class` ride too: render.py's other scope for a
      // declared colour is `g[data-ref^='dell/control-panel-left-14g@']
      // .state-fault`, and a lamp wrapped in id and class alone painted its
      // generic default in its own texture while the face showed the vendor's
      // colour - same defect as the id case, one attribute over.
      const id = p.getAttribute('id'), cls = p.getAttribute('class'),
            path = p.getAttribute('data-path'), ref = p.getAttribute('data-ref'),
            dc = p.getAttribute('data-class'), lamp = p.getAttribute('data-portrayal-lamp');
      if (!id && !cls && !ref && !dc && !lamp) continue;   // a pure layout group changes no selector
      // THE HOST'S LAMP COLOUR RIDES TOO (#664), and only it: it is an inline
      // custom property on the lamp's group, and a dome or a lens cut out
      // below the group took the group's class (so its state rule applied)
      // and not the colour - the face showed the host's magenta around a
      // dome in the stylesheet's own colour. Marked as applyNodeLampColors
      // marks it, so an unlit copy strips it and a repaint replaces it.
      const lampStyle = lamp && LAMP_HEX.test(lamp)
        ? ` data-portrayal-lamp="${lamp}" style="${LAMP_MARK}--led-color:${lamp}${LAMP_END}"` : '';
      inner = `<g${id ? ` id="${id}"` : ''}${cls ? ` class="${cls}"` : ''}` +
              `${ref ? ` data-ref="${ref}"` : ''}${dc ? ` data-class="${dc}"` : ''}` +
              `${path ? ` data-path="${path}"` : ''}${lampStyle}>${inner}</g>`;
    }
    return inner;
  };
  // The `<!--art-->` marker separates the shared stylesheet from the node's
  // own art, so lamps.js can lay an unlit copy of the art under the live one.
  // `hide` is a selector for descendants that are drawn by something else: a
  // card's own art leaves out the optics seated on it, which are FRUs of their
  // own (bodyRole) and cut their own plane.
  const nodeSvg = (el, rect, hide = null) => {
    const m = inv.multiply(el.getScreenCTM());
    const clone = el.cloneNode(true);
    clone.removeAttribute('transform');   // the CTM below already includes it
    // raised descendants (collars, handles) render as their own geometry -
    // keep them out of cavity floors and plate textures
    for (const r of clone.querySelectorAll(
        '[data-z-out],[data-z-cyl],[data-z-bar],[data-z-uhandle],[data-z-dome][data-z-lift]'))
      r.style.display = 'none';
    if (hide) for (const r of clone.querySelectorAll(hide)) r.style.display = 'none';
    const live = scopeWrap(el,
        `<g transform="matrix(${m.a} ${m.b} ${m.c} ${m.d} ${m.e - rect.x} ${m.f - rect.y})">` +
        clone.outerHTML + `</g>`);
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${rect.w} ${rect.h}"` +
      ` width="${rect.w}mm" height="${rect.h}mm">${shared}<!--art-->` + live + `</svg>`;
  };
  return {inv, mmRect, shared, liftOf, ownerOf, scopeWrap, nodeSvg};
}

// standards-relief extraction: cavities (with interior features) + outward protrusions.
// Interior/plate art is re-rendered STANDALONE from its own nodes so bezel plates
// can carry arbitrary shapes (plug-outline apertures, LED holes) via alpha.
// `back` says the drawing is a module's back, built inside the module's FRU
// (buildFaceRelief's back pass): nothing on it is a FRU of its own (bodyRole).
export async function extractRelief(url, scope, {back = false} = {}) {
  const div = document.createElement('div');
  div.style.cssText = 'position:absolute;left:-10000px;top:0;width:1000px;visibility:hidden';
  div.innerHTML = await svgSource(url, scope);
  document.body.appendChild(div);
  const svg = div.querySelector('svg');
  // A PROJECTION IS FLAT. A part seated on one face may be drawn again on
  // another as `data-projection` (render.py's `plan:`), for the 2D view with
  // the lid off. Its body already stands in the scene from the face that
  // holds it, so nothing inside one is extracted here - it is texture only.
  const q = sel => [...svg.querySelectorAll(sel)].filter(el => !el.closest('[data-projection]'));
  // before anything is measured or serialised: cleanText and every nodeSvg below
  // are taken from this document, so applying the runtime states once here is
  // what puts them on the face texture and on every piece of relief at once.
  applyNodeStates(svg, scope);
  // and the fields written on parts, for the same reason: a rebuild - a config
  // switch, a swap - would otherwise draw every badge from the default text
  // while the registry still said the value was set, and a repeated setFields
  // would see nothing changed and never put it back
  applyNodeFields(svg, scope);
  // and the host's lamp colours (#664), so a rebuild paints a custom-coloured
  // lamp the colour the registry says rather than its stylesheet default
  applyNodeLampColors(svg, scope);
  // A part the viewer has taken off is REMOVED here rather than hidden, and only
  // here: this document is built to be measured and then discarded, so nothing
  // has to put it back. Left as display:none it would measure 0x0 and extrude a
  // degenerate feature instead of none at all - a cover that is off should leave
  // no geometry behind, not a flat one.
  applyPulled(svg, scope);
  for (const el of [...q("[data-portrayal-pulled]")]) el.remove();
  const {inv, mmRect, shared, liftOf, ownerOf, nodeSvg} = nodeTools(svg, {back});
  // TILTED FACETS (docs/superpowers/specs/2026-09-24-tilted-facets-design.md).
  // A node under a `[data-tilt-on]` group is measured foreshortened; it is
  // unprojected here to its true size about its part's anchor, and the builder
  // carries it onto the facet plane with tiltFrame. Nothing below runs for a
  // drawing with no facets.
  // Lifts inside a tilted part are measured from the plane the part sits on,
  // which is the facet (tiltTools' `base`).
  const {facetInfo, tiltRec} = tiltTools(svg, {mmRect, liftOf,
                                               ctmOf: n => inv.multiply(n.getScreenCTM())});
  // `proj` keeps the front-view rect: rasters, crops and punches are cut from
  // the face art at it, while geometry takes the true rect.
  const tilted = (e, t) => {
    const r = tiltRec(t);
    if (!r) return e;
    e.proj = {x: e.x, y: e.y, w: e.w, h: e.h};
    Object.assign(e, unproject(e.proj, r.tilt));
    e.tilt = r.tilt;
    if (typeof e.lift === 'number') e.lift -= r.base;
    // `out` is an absolute height; cyl, bar, dome and depth are lengths from `lift`
    if (typeof e.out === 'number') e.out -= r.base;
    return e;
  };
  // THE OUTLINE OF A NODE, in face millimetres, as closed rings.
  //
  // SAMPLED RATHER THAN PARSED. getPointAtLength walks a path at constant arc
  // length and consumes NO length crossing from one subpath to the next, so two
  // consecutive samples that jump much further than the step are a subpath
  // boundary. That finds the rings without writing a path parser, and it works
  // for curves exactly as well as for lines - which matters, because these
  // outlines are CAD contours and the next one may not be polygonal.
  //
  // A ring whose centroid falls inside another is a HOLE; one that does not is a
  // separate island. That is what makes the screw hole in the rear handle's left
  // foot a hole rather than a second lump of metal.
  //
  // A `fill="none"` path is a stroked centreline - a line, not an area - and
  // extruding it would build a ribbon where the drawing shows a bracket.
  const RING_STEP = 0.25;
  const inRing = (pt, ring) => {
    let hit = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const a = ring[i], b = ring[j];
      if ((a[1] > pt[1]) !== (b[1] > pt[1]) &&
          pt[0] < (b[0] - a[0]) * (pt[1] - a[1]) / (b[1] - a[1]) + a[0]) hit = !hit;
    }
    return hit;
  };
  const ringsOf = el => {
    const m = inv.multiply(el.getScreenCTM());
    const paths = el.tagName === 'path' ? [el] : [...el.querySelectorAll('path')];
    const rings = [];
    for (const q of paths) {
      if (q.getAttribute('fill') === 'none') continue;
      let total = 0;
      try { total = q.getTotalLength(); } catch (e) { continue; }
      if (!(total > 0)) continue;
      const n = Math.max(8, Math.min(4000, Math.ceil(total / RING_STEP)));
      const step = total / n;
      let cur = [], prev = null;
      for (let i = 0; i <= n; i++) {
        const s = q.getPointAtLength(step * i);
        const pt = [m.a * s.x + m.c * s.y + m.e, m.b * s.x + m.d * s.y + m.f];
        if (prev && Math.hypot(pt[0] - prev[0], pt[1] - prev[1]) > 4 * step) {
          if (cur.length > 2) rings.push(cur);
          cur = [];
        }
        cur.push(pt); prev = pt;
      }
      if (cur.length > 2) rings.push(cur);
    }
    if (!rings.length) return null;
    const area = r => {
      let a = 0;
      for (let i = 0, j = r.length - 1; i < r.length; j = i++)
        a += (r[j][0] + r[i][0]) * (r[j][1] - r[i][1]);
      return Math.abs(a / 2);
    };
    const cent = r => [r.reduce((s, c) => s + c[0], 0) / r.length,
                       r.reduce((s, c) => s + c[1], 0) / r.length];
    rings.sort((a, b) => area(b) - area(a));
    const out = [];
    for (const r of rings) {
      const host = out.find(o => inRing(cent(r), o.shell));
      if (host) host.holes.push(r); else out.push({shell: r, holes: []});
    }
    return out;
  };

  // FLAT ART THAT WAS LIFTED. A composed part with no relief of its own - a
  // warning triangle, a printed marking - has nothing for a lift to raise. It
  // stays in the face texture at the panel plane, and a raised plate in front of
  // it hides it completely. smartoptics/dcp-404's two hazard triangles vanished
  // this way while its lamps did not, which is what made it look like a marking
  // problem rather than a lift one: lamps are drawn by the lamp path, which owns
  // them on every face, so they were never in the face texture to be buried.
  //
  // Anything carrying `data-states` is such a lamp and is left alone here.
  const flatLifted = [...q('[data-z-lift]')]
    .filter(el => !el.matches(RAISED) && !el.hasAttribute('data-depth')
                  && !el.querySelector(`${RAISED},[data-depth],[data-states]`)
                  && !el.hasAttribute('data-states'))
    .map(el => {
      const rect = mmRect(el);
      const e = {...rect, lift: liftOf(el), owner: ownerOf(el), svgText: nodeSvg(el, rect)};
      const t = tiltOf(el);
      return t ? tilted(e, t) : e;
    });

  const cavities = [...q('[data-depth]')]
    .filter(el => !el.querySelector('[data-depth]'))
    .map(el => {
      const cavNode = el.dataset.cavity &&
        svg.querySelector(`[id="${CSS.escape(el.id + '--' + el.dataset.cavity)}"]`);
      const rect = mmRect(cavNode || el);
      const grpRect = mmRect(el);
      const features = [...el.querySelectorAll('[data-z-top],[data-z-sink]')].map(f => ({
        ...mmRect(f),
        kind: f.dataset.zTop ? 'top' : 'sink',
        val: +(f.dataset.zTop || f.dataset.zSink),
        color: f.dataset.zColor || '#0a0c0e',
        // A ROUND FEATURE IN A CAVITY USED TO BUILD AS A BOX. The cavity itself has
        // had `round` since the screw heads needed it, but the `top`/`sink` features
        // standing in one never did, so every circular recess in the library came out
        // square: an LC ferrule, a reset pinhole and - the one that surfaced it - the
        // six stud bores of the AIS800-64D's DC supply. Nothing depended on the square
        // reading; a `<circle>` is taken at its word, and `data-round` is there for a
        // node whose art is round but whose tag is not.
        round: f.dataset.round === '1' || f.tagName === 'circle',
      }));
      const e = {...rect, owner: ownerOf(el), d: +el.dataset.depth, wall: el.dataset.wall || '#a7adb4',
              wallsInside: el.dataset.walls === 'inside',
              // A HOLE A BAY IS SEEN THROUGH (render.py's `rear:`) is a passage
              // to the front of the chassis. Whatever the bay holds stands in it
              // as its own body, back painted, and leaves with it when pulled;
              // with nothing there the passage is open to the front. So no
              // floor and no back are built - a painted floor would stay behind
              // a pulled cassette, and close the slot when it was empty.
              seeThrough: !!el.dataset.rearOf || !!el.querySelector(':scope > [data-projection]'),
              // AN OPEN BAY'S MOUTH (render.py `data-see-through`): the passage
              // behind it is the rear hole's, so this builds no floor and no
              // back - only a short collar of wall where the passage, which the
              // depth clamp stops just short of the face, would leave a gap.
              hollow: el.dataset.seeThrough === '1',
              // an open-frame mouth (render.py `data-open-frame`): punched, nothing built
              openFrame: el.dataset.openFrame === '1',
              lift: liftOf(el),
              round: !!el.dataset.round, cavSvg: nodeSvg(cavNode || el, rect),
              grpRect, grpSvg: nodeSvg(el, grpRect), features};
      const t = tiltOf(el);
      if (!t) return e;
      // its features are unprojected about the same anchor; grpRect stays
      // projected, since it is only ever the raster they are cut from
      tilted(e, t);
      if (e.tilt) for (const ft of features) {
        ft.proj = {x: ft.x, y: ft.y, w: ft.w, h: ft.h};
        Object.assign(ft, unproject(ft.proj, e.tilt));
      }
      return e;
    });
  // pressed grooves: shallow standalone cavities whose own art is the floor.
  // `lift` is not optional here even though a groove is always pressed into the
  // face and always reads 0: every consumer of a cavity does arithmetic on it,
  // and `undefined - d / 2` is NaN, which Three.js does not reject - it culls the
  // mesh. Omitting it punched the faceplate and then silently deleted the walls
  // and floor that were supposed to close the hole, so the chassis had seven
  // full-length slits you could see the background through.
  for (const el of q('[data-groove]')) {
    const rect = mmRect(el);
    const e = {...rect, owner: ownerOf(el), d: +el.dataset.groove, wall: '#25282c', round: false,
               lift: liftOf(el),
               cavSvg: nodeSvg(el, rect), grpRect: rect,
               grpSvg: nodeSvg(el, rect), features: []};
    const t = tiltOf(el);
    cavities.push(t ? tilted(e, t) : e);
  }
  // A CARD'S OPTICS ARE NOT THE CARD'S ART: each is a FRU of its own
  // (bodyRole), so the card's plane is cut without them.
  const OWN_FRU = '[data-behaviour="occupies"][data-ref],[data-ref][data-for][data-path$="-occupant"]';
  const outs = [...q('[data-z-out],[data-z-cyl],[data-z-bar],[data-z-uhandle]')].map(el => {
    const rect = mmRect(el);
    const e = {...rect, owner: ownerOf(el), out: el.dataset.zOut && +el.dataset.zOut,
            cyl: el.dataset.zCyl && +el.dataset.zCyl,
            bar: el.dataset.zBar && +el.dataset.zBar,
            uhandle: el.dataset.zUhandle && +el.dataset.zUhandle,
            dia: el.dataset.zDia && +el.dataset.zDia,
            lift: liftOf(el),
            knurl: !!el.dataset.zKnurl,
            thread: el.dataset.zThread && +el.dataset.zThread,
            color: el.dataset.zColor || null,
            holeColor: el.dataset.zHoleColor || null,
            rings: el.dataset.zShape ? ringsOf(el) : null,
            profile: el.dataset.zProfile
              ? el.dataset.zProfile.split(',').map(p => p.split(':').map(Number)) : null,
            profileY: el.dataset.zProfileY
              ? el.dataset.zProfileY.split(',').map(p => p.split(':').map(Number)) : null,
            svgText: nodeSvg(el, rect)};
    const t = tiltOf(el);
    if (t) {
      tilted(e, t);
      // an outline is unprojected point by point, like its box
      if (e.tilt && e.rings) {
        const un = r => r.map(([x, y]) => { const u = unproject({x, y, w: 0, h: 0}, e.tilt); return [u.x, u.y]; });
        e.rings = e.rings.map(g => ({shell: un(g.shell), holes: g.holes.map(un)}));
      }
    }
    const f = el.dataset.facetDeg && facetInfo(el.id);
    if (f) {
      // THE WEDGE, REBUILT IN THE FACE'S FRAME. render.py's profile runs along
      // the declaring component's axis, which is the face's only when the
      // component is not turned. Root edge at the facet's lift, proud edge at
      // lift + extent x tan, per `facing`.
      const tn = Math.tan(f.deg * Math.PI / 180), lo = f.lift;
      const alongY = f.facing === 'up' || f.facing === 'down', along = alongY ? e.h : e.w;
      const hi = lo + along * tn;
      const wedge = f.facing === 'up' || f.facing === 'left' ? [[0, lo], [along, hi]] : [[0, hi], [along, lo]];
      if (alongY) { e.profileY = wedge; e.profile = null; }
      else { e.profile = wedge; e.profileY = null; }
      e.out = hi;
      e.facet = {deg: f.deg, facing: f.facing, id: el.id};
      // THE PARTS ON IT paint its surface: they are siblings of the facet node,
      // so its own art does not hold them, and the face raster does not hold
      // the facet (every raised node is hidden from it). Outermost groups only;
      // optics are FRUs and bring their own plane.
      e.parts = q(`[data-tilt-on="${CSS.escape(el.id)}"]`)
        .filter(h => !h.parentElement.closest(`[data-tilt-on="${CSS.escape(el.id)}"]`)
                     && !h.matches(OWN_FRU))
        .map(h => { const r = mmRect(h); return {...r, svgText: nodeSvg(h, r, OWN_FRU)}; });
    }
    return e;
  });
  const domes = [...q('[data-z-dome]')].map(el => {
    const rect = mmRect(el);
    // a lamp on a raised indicator bezel domes from THAT surface, not the panel
    const e = {...rect, owner: ownerOf(el), dome: +el.dataset.zDome, lift: liftOf(el),
               svgText: nodeSvg(el, rect)};
    const t = tiltOf(el);
    return t ? tilted(e, t) : e;
  });
  const vents = [...q('[data-vent],[data-z-vent]')].map(el => {
    const rect = mmRect(el);
    return {...rect, owner: ownerOf(el), depth: +(el.dataset.vent || el.dataset.zVent),
            svgText: nodeSvg(el, rect)};
  });
  // component instances only (data-ref) - contract elements can share a class
  // name (pull-tab has an element called "tab"), which would shadow the module
  const frus = [];
  // WHICH CLASSES GET A BODY. A component is field-replaceable because of what it
  // IS, and this list is the renderer's view of that. It was psu/fan/tab, which
  // silently excluded two whole classes that behave identically:
  //   power    - power ENTRY modules and trays. NOT a mislabelled psu: a PEM is a
  //              conduit that neither draws nor supplies, and collapsing the two
  //              would lose a distinction the power model depends on. 5 parts.
  //   cooling  - casa/ and cisco/ call a fan `cooling` where edgecore/, ufispace/
  //              and common/ call the same object `fan`. 7 parts against 3. That
  //              duplication is a DATA defect, tracked as roc-ops/Portrayal#173;
  //              admitting both here is the renderer refusing to be the place it
  //              gets fixed, not an endorsement of it.
  // The visible symptom was that every Casa and Cisco fan and PEM drew as art
  // painted on the chassis plate, with no body and no ejection - and edgecore
  // "worked in 3D" for no better reason than its choice of word.
  //
  // THAT LIST IS NOW A FALLBACK. A part says how it MOVES - `data-behaviour`,
  // one of fills / occupies / mounts - and a body is owed to anything that comes
  // out, which is `fills` (into an aperture) and `occupies` (into a receptacle).
  // The class list could never say that: it was a catalogue of nouns, so every
  // new removable type meant editing it, and a TRANSCEIVER - removable, and the
  // reason the SFP bail cannot pivot yet - was simply not on it. `mounts` is
  // deliberately excluded: a rack ear, a label and a ground lug attach to the
  // box and do not withdraw from it.
  //
  // The old list stays for drawings compiled before behaviours existed. It costs
  // one selector and means a stale dist/ does not silently lose every FRU.
  // The rule itself is bodyBehaviour (above), which also admits an occupant
  // that declares no behaviour - a plug.
  // A MODULE INSIDE A MODULE HAS A BODY OF ITS OWN. A card in a riser slot is
  // not a FRU here - it comes out with its riser - but its PCB is real, and
  // it hides on its own path. Collected beside the FRUs and built into the
  // owner's ejection group.
  const subBodies = [];
  // (OWN_FRU, above: a card's optics are not the card's art)
  // THE BODY NODE'S SIDE COLOUR FIRST: on the SFP skins it stands 10 mm out
  // of the cage as a relief feature whose sides are its `data-z-color`
  // (#6e747c, the `outs` colour above), and the box behind the face is the
  // same shell - in its fill (#9aa0a8) a pulled optic read as two parts. Then
  // the fill, as computed, for a body node that states no side colour.
  const bodyFill = el => {
    const n = el.id && el.querySelector(`[id="${CSS.escape(el.id)}--body"]`);
    if (!n) return null;
    if (n.dataset.zColor) return n.dataset.zColor;
    const f = getComputedStyle(n).fill;
    return f && f !== 'none' && !f.startsWith('url(') ? f : null;
  };
  const FEATURE_SEL = '[data-z-out],[data-z-cyl],[data-z-bar],[data-z-uhandle]';
  for (const el of q('[data-ref]')) {
    const beh = bodyBehaviour({ref: el.dataset.ref, behaviour: el.dataset.behaviour,
                               for: el.dataset.for, path: el.dataset.path, cls: el.dataset.class});
    if (!beh) continue;
    const full = el.dataset.path || '';
    const role = bodyRole(full, beh, {back});
    if (!role) continue;
    const path = role.fru || role.sub;
    // a module in a chassis bay is `bay/module`; one in a module's bay is
    // `bay/module/slot/module` - the third segment is what makes it nested
    if (role.sub) {
      // the body index lives with the builder; every nested module is
      // recorded here and the builder keeps the ones that declare boxes
      const m = inv.multiply(el.getScreenCTM());
      subBodies.push({path: full, owner: path, ref: el.dataset.ref.split(':')[0], lift: liftOf(el),
                      toFace: {a: m.a, b: m.b, c: m.c, d: m.d, e: m.e, f: m.f}});
      // on a facet: its boxes are unprojected and built in the tilt frame
      const st = tiltOf(el) && tiltRec(tiltOf(el));
      if (st) { subBodies[subBodies.length - 1].tilt = st.tilt; subBodies[subBodies.length - 1].lift -= st.base; }
      continue;
    }
    if (frus.some(f => f.path === path)) continue;
    // `data-body-depth` IS THE MODULE'S OWN DEPTH and was being thrown
    // away here, so every module without a `body:` block fell back to a
    // hardcoded 60 mm bay below - 60 for a 40 mm control panel, 60 for a
    // 25 mm drive blank. On a part seated in a rack ear that hole runs
    // straight out the back of the flange.
    // A MODULE IN A BAY THAT OPENS IN A WELL IS NOT AT THE FACE. The bay
    // carries the well's floor as a negative z-lift (render.py's `in:`), and
    // the module's plane, body and bay box all sit that far down.
    const frect = mmRect(el);
    // A SHELF LEAVES NO HOLE. A bay with a `floor:` is a shelf in a well - a
    // card on its riser slot - and the dark box the kit leaves behind a pulled
    // module would stand on the card below it. Read off the bay, which is the
    // module's parent.
    const shelf = !!(el.parentElement && el.parentElement.dataset && el.parentElement.dataset.shelf);
    // an OPEN-BACKED bay leaves no box behind a pulled module either - its
    // passage is the rear hole's, and a box would close it (see `hollow`)
    const openBack = !!(el.parentElement && el.parentElement.dataset && el.parentElement.dataset.openBack);
    // a nested FRU's group goes inside its host's: the optic it is chained
    // on, else the card's bay
    const within = role.nested ? [el.dataset.for, full.split('/')[0]] : null;
    const hide = el.querySelector(OWN_FRU) ? OWN_FRU : null;
    frus.push({path, ref: el.dataset.ref.split(':')[0], within,
               // an optic's own depth, for opticBody (on anything else
               // `data-depth` is a cavity's and is not read here)
               behaviour: el.dataset.behaviour || null,
               // what it is pulled as (a plug occupies though it declares
               // nothing), and how far its relief stands off its seat -
               // the travel of an occupant that declares no depth (ejectTravel)
               occupies: beh === 'occupies',
               extent: beh === 'occupies' ? reliefExtent(
                 [el, ...el.querySelectorAll(FEATURE_SEL)].map(n => ({
                   out: n.dataset.zOut, cyl: n.dataset.zCyl, bar: n.dataset.zBar,
                   uhandle: n.dataset.zUhandle, lift: liftOf(n)})), liftOf(el)) : 0,
               depth: el.dataset.behaviour === 'occupies' ? +el.dataset.depth || null : null,
               // and its colour: its skin's own `<name>--body` node's side
               // colour, else its fill (bodyFill)
               bodyColor: el.dataset.behaviour === 'occupies' ? bodyFill(el) : null,
               cls: el.dataset.class, lift: liftOf(el), shelf, openBack,
               bodyDepth: +el.dataset.bodyDepth || null, ...frect,
               // its own art, so the plane can be cut to the module's SHAPE
               svgText: nodeSvg(el, frect, hide),
               // THE MODULE'S OWN FRAME, not its drawn box. A riser's slot
               // brackets hang 13.4 mm outboard of its plate, so the bbox
               // starts 13.4 left of the contract's origin - and a body box
               // placed from the bbox stood that far out through the chassis
               // wall. This is local mm -> face mm, mirror included, so a box
               // in the contract's frame lands where the contract says.
               toFace: (() => { const m = inv.multiply(el.getScreenCTM());
                                return {a: m.a, b: m.b, c: m.c, d: m.d, e: m.e, f: m.f}; })()});
    // AN OPTIC IN A TILTED CAGE IS TILTED WITH IT. render.py copies the tilt
    // onto the occupant; a seat without it takes its mate-to host's.
    let t = tiltOf(el);
    if (!t && el.dataset.for) {
      const h = svg.querySelector(`[data-path="${CSS.escape(el.dataset.for.split(/\s+/)[0])}"]`);
      t = h && tiltOf(h);
    }
    if (t) tilted(frus[frus.length - 1], t);
  }
  for (const el of q('[data-z-out],[data-z-cyl],[data-z-bar],[data-z-uhandle]'))
    el.style.display = 'none';
  const cleanText = svg.outerHTML;
  div.remove();
  return {cavities, outs, domes, vents, frus, subBodies, flatLifted, cleanText};
}

// The commonest opaque colour in a raster, which is what a part is MADE of - as
// against the one pixel at its centre, which is whatever happens to be printed
// there. Buckets to 5 bits per channel so anti-aliased edges fall in with the
// body they belong to, then returns the first EXACT colour seen in the winning
// bucket, so the answer is a colour actually present in the art rather than a
// rounded one. Subsamples on a grid: this runs once per raised node at build.
function dominantColor(cv) {
  const {width: W, height: H} = cv;
  if (!W || !H) return 'rgb(128,128,128)';
  const d = cv.getContext('2d').getImageData(0, 0, W, H).data;
  const step = Math.max(1, Math.floor(Math.min(W, H) / 48));
  const count = new Map(), exact = new Map();
  for (let y = 0; y < H; y += step)
    for (let x = 0; x < W; x += step) {
      const i = (y * W + x) * 4;
      if (d[i + 3] < 128) continue;                       // transparent
      const k = (d[i] >> 3) << 10 | (d[i + 1] >> 3) << 5 | (d[i + 2] >> 3);
      count.set(k, (count.get(k) || 0) + 1);
      if (!exact.has(k)) exact.set(k, `rgb(${d[i]},${d[i + 1]},${d[i + 2]})`);
    }
  let best = null, bestN = 0;
  for (const [k, n] of count) if (n > bestN) { bestN = n; best = k; }
  return best === null ? 'rgb(128,128,128)' : exact.get(best);
}

// THE REPAINT HALF OF A DERIVED SIDE COLOUR (#481), on its own so it can be
// checked without WebGL: when the art chose the colour (no `data-z-color`), every
// material it went into takes the dominant colour of the repainted art. It runs
// on EVERY restyle of the node, not only a field change - a lamp state or a pull
// that changes the node's art moves its sides with it, which is the same reading
// the build makes. Returns the colour set, or null when nothing was derived.
export function recolourBody(derived, mats, cv) {
  if (!derived || !mats || !mats.length) return null;
  const c = dominantColor(cv);
  for (const m of mats) m.color.set(c);
  return c;
}

export async function rasterize(svgText, wmm, hmm, pxmm = PXMM, flipX = false, flipY = false) {
  const img = new Image();
  const blobUrl = URL.createObjectURL(new Blob([svgText], {type: 'image/svg+xml'}));
  await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = blobUrl; });
  const cv = document.createElement('canvas');
  cv.width = Math.max(1, Math.round(wmm * pxmm)); cv.height = Math.max(1, Math.round(hmm * pxmm));
  const ctx = cv.getContext('2d');
  if (flipX) { ctx.translate(cv.width, 0); ctx.scale(-1, 1); }
  if (flipY) { ctx.translate(0, cv.height); ctx.scale(1, -1); }
  ctx.drawImage(img, 0, 0, cv.width, cv.height);
  URL.revokeObjectURL(blobUrl);
  return cv;
}

// six-sided FRU body: same art the component tab shows, reused inside the device

// Build the relief geometry for one face: the recesses, raised parts, domes,
// vents and FRU sub-groups a compiled face describes. Returns nothing - it
// fills the collections the caller owns, because a device viewer wants these
// parented per instance while a rack viewer wants them built once per model.
export async function buildFaceRelief(F, ctx) {
  const {src, faceCv, faceSvg, facePunch, meshes,
         FRU_GROUPS, FRU_META, BODY_META, D, bodyBoxMesh} = ctx;
    // HOW FAR INTO THE BOX THIS FACE LOOKS, which is not the same number on every
    // face and was the device's DEPTH on all of them. Depth is right for front and
    // rear and wrong for the other four: into a top or a bottom you go the chassis
    // HEIGHT, into a side its WIDTH. Nothing caught it because the parts on those
    // faces are shallow - a ground lug does not test a depth clamp - but on a 1U
    // server, H 44 and D 700, a top-face cavity was free to sink 698 mm into a
    // 44 mm box and come out of the underside. Falls back to D so a caller that
    // has not been taught the difference behaves exactly as before.
    const INTO = ctx.deep ?? D;
    // THE ONE THAT WAS MISSED LAST TIME read through ctx and named no scope, and
    // resolved against the default while looking like a rendering fault. Read the
    // density once, here, so every raster below is this viewer's.
    const PX = _px(ctx.scope);
    // Every texture below that was rasterised from a node's OWN art records how
    // to redraw itself. That is the whole cost model for a state change: it
    // repaints and never re-shapes, so nothing here has to be measured, extruded
    // or disposed again - only the handful of canvases the change actually
    // reaches. A full rebuild of this device is 1.0-1.4 s; one lamp is one
    // 1.6 ms raster and one face.
    //
    // Registered by TEXT, not by path, and the affected test is a substring
    // search over that text. A node's svg carries its ancestors (for scope) and
    // its descendants (for their own art), so any of the three can be what the
    // state class lands on - and asking the text is the only version of the
    // question that cannot miss one of the three.
    const restyle = ctx.restyle || [];
    // `anim` - the material and its mm size - is what lets the viewer redraw
    // the same texture at several instants of a CSS animation (see lamps.js)
    const reg = (svgText, run, anim = null) => { if (svgText) restyle.push({svgText, run, anim}); };
    // `let`, because the drawing may state a different size below and a face
    // is drawn at its own size rather than at its plane's.
    let fw = F.fw(), fh = F.fh();
    // A device need not declare every view; fall back to a plain face. Asked
    // through svgSource so the answer is cached: when the view DOES exist this
    // is the same fetch extractRelief is about to want, and when it does not the
    // miss is remembered rather than re-probed on the next LOD pass.
    if (!(await svgSource(src, ctx.scope))) {
      const cv0 = document.createElement('canvas');
      cv0.width = Math.round(fw * PX); cv0.height = Math.round(fh * PX);
      const c0 = cv0.getContext('2d');
      c0.fillStyle = '#3a3f44'; c0.fillRect(0, 0, cv0.width, cv0.height);
      faceCv[F.view] = cv0;
      return;
    }
    const {cavities, outs, domes, vents, frus, subBodies = [], flatLifted = [],
           cleanText} = await extractRelief(src, ctx.scope, {back: !!ctx.back});
    // A MODULE PREVIEW IS THE PART'S SIZE BOX HERE. A part that declares
    // `head:` publishes a preview whose viewBox also holds the head and its
    // composed parts (components_index.preview_box), so the 2D module view
    // shows the overhang. Every coordinate below reads the drawing from an
    // origin of 0 0 and the face is the part's own w x h, so the 3D module
    // view crops the drawing back to that box, as it was before the preview
    // grew; the head's own relief is built from its node either way.
    const faceText = F.sizeBox ? toSizeBox(squareFaceplate(cleanText), fw, fh)
                               : squareFaceplate(cleanText);
    // THE DRAWING'S OWN SIZE WINS, because the face is not obliged to match the
    // plane it sits on. The R740xd's front is the 482.6 mm rack face - Dell
    // builds the flanges into the faceplate and puts the VGA, the power button
    // and the health lamp in them - over a 434 mm body. Taking fw from the
    // chassis squashed the artwork by 10% AND placed every feature against the
    // wrong centre, which threw the ear's ports 36 mm off the end of the box.
    // For every other face in the library the two numbers are already equal, so
    // this changes nothing that was right.
    const vb = /viewBox\s*=\s*"\s*[-\d.eE+]+\s+[-\d.eE+]+\s+([\d.eE+-]+)\s+([\d.eE+-]+)/.exec(faceText);
    if (vb) {
      const dw = parseFloat(vb[1]), dh = parseFloat(vb[2]);
      if (dw > 0 && dh > 0) { fw = dw; fh = dh; }
    }
    if (ctx.faceMM) ctx.faceMM[F.view] = [fw, fh];
    const cv = await rasterize(faceText, fw, fh, PX, !!F.flipLX, !!F.flipLY);
    // THE ART BEFORE ANY HOLE IS PUNCHED IN IT. A cavity punches `cv` with its
    // own outline, and a module whose bay opens inside that cavity - a drive in
    // the mid tray, a DIMM on the board - had its face art punched away before
    // the FRU pass came to crop it, so every such module was a dark rectangle.
    const artCv = document.createElement('canvas');
    artCv.width = cv.width; artCv.height = cv.height;
    artCv.getContext('2d').drawImage(cv, 0, 0);
    faceCv[F.view] = cv;
    faceSvg[F.view] = faceText;   // LOD re-rasterises from this; keep it squared
    facePunch[F.view] = [];
    const grp = new THREE.Group();
    grp.position.set(...F.pos());
    grp.rotation.set(...F.rot);
    // A FACE MAY BE AUTHORED MIRRORED and the underside is - a bottom view is drawn
    // as if the device were rolled towards you, so its art is flipped in both axes
    // against the face's local frame. `flipLY` was here already and no face ever set
    // it; `flipLX` is its partner, and the pair is what lets the bottom carry relief.
    const LX = (x, w) => (F.flipLX ? -1 : 1) * (x + w / 2 - fw / 2);
    const LY = (y, h) => (F.flipLY ? -1 : 1) * (fh / 2 - (y + h / 2));
    // A PART ON A FACET IS BUILT FLAT, AT ITS TRUE SIZE, IN A GROUP WHOSE
    // MATRIX IS ITS TILT FRAME (docs/superpowers/specs/2026-09-24-tilted-facets-design.md;
    // tiltGroupIn). The matrix is fixed: a FRU's pull moves its own group along
    // local z, which in here is the facet's normal.
    const tiltGroupFor = (t, parent) =>
      tiltGroupIn(parent, t, {fw, fh, flipLX: !!F.flipLX, flipLY: !!F.flipLY});
    const sideMats = c => Array.from({length: 6},
      () => new THREE.MeshLambertMaterial({color: c}));
    // each FRU gets a subgroup so its art and relief travel together when ejected
    const fruGroups = {};
    // a card's optic rides in the card's group (bodyRole `nested`): pulled on
    // its own, and gone with the card - every other FRU hangs off the face
    const hostOf = f => (f.within || []).map(p => p && fruGroups[p]).find(Boolean) || grp;
    for (const f of frus) {
      const fg = new THREE.Group();
      (f.tilt ? tiltGroupFor(f.tilt, hostOf(f)) : hostOf(f)).add(fg);
      fruGroups[f.path] = fg;
      FRU_GROUPS[f.path] = fg;
      const bd = BODY_META[f.ref];
      // a `body:` block is the best answer, the part's own size.d the next, and
      // 60 only when a drawing predates `data-body-depth` entirely; captive
      // modules declare how far they pull out, removable FRUs clear the
      // chassis, and an occupant that declares no depth clears its own relief
      // (ejectTravel)
      const travel = ejectTravel({body: bd, bodyDepth: f.bodyDepth, depth: f.depth,
                                  occupies: f.occupies, extent: f.extent, into: INTO});
      FRU_META[f.path] = {cls: f.cls, view: F.view, body: bd, captive: !!(bd && bd.travel),
                          bodyDepth: f.bodyDepth, pull: travel.pull,
                          leavesBay: travel.leavesBay, bayDepth: travel.bayDepth};
    }
    let curOwner = null, curTilt = null;
    // Tagged on the way in, so `setPulled` can hide a part's relief without the
    // part having to be a FRU. A cover's meshes stay in the shared group - they
    // are not going anywhere - and simply stop being drawn.
    // A tilted entry goes into its tilt group under the same parent.
    const addTo = obj => {
      if (curOwner) obj.userData.portrayalPath = curOwner;
      const into = curOwner && fruGroups[curOwner] ? fruGroups[curOwner] : grp;
      return (curTilt ? tiltGroupFor(curTilt, into) : into).add(obj);
    };
    // the front-view rect of an entry: where its art is cut from the face
    const projOf = e => e.proj || e;
    // an open bay's mouth is a short collar, not a pocket: walls deep enough
    // to meet the rear passage, which stops INTO - 2 short of the face
    const builtDepth = c => cavityShell(c, INTO).depth;
    for (const c of cavities) {
      // AN OPEN BAY'S MOUTH IS THE CHASSIS'S. It has no data-path of its own, so
      // ownerOf() answers with the bay's path, and a FRU group is keyed by that
      // same path - the collar went out with the cassette and a tree pull hid it.
      curOwner = c.hollow ? null : c.owner;
      curTilt = c.tilt || null;
      // a tilted cavity's art is cut at its front-view rect and stretched over
      // its true size (for every other cavity pc is c)
      const pc = projOf(c);
      const d = builtDepth(c);
      // floor + feature art comes from the cavity group rendered standalone, so
      // raised bezel plates (drawn over the cavity on the face) never leak in
      const gcv = await rasterize(c.grpSvg, c.grpRect.w, c.grpRect.h, PX);
      const floorCv = crop(gcv, {x: pc.x - c.grpRect.x, y: pc.y - c.grpRect.y, w: pc.w, h: pc.h}, PX);
      const cavCrops = [];
      const fctx = floorCv.getContext('2d');
      for (const ft of c.features) {
        const pf = projOf(ft);
        ft.faceCv = crop(gcv, {x: pf.x - c.grpRect.x, y: pf.y - c.grpRect.y, w: pf.w, h: pf.h}, PX);
        cavCrops.push(ft);
        // remove the feature art from the floor (it lives on its own box now)
        const px = [Math.round((pf.x - pc.x) * PX), Math.round((pf.y - pc.y) * PX),
                    Math.round(pf.w * PX), Math.round(pf.h * PX)];
        if (ft.kind === 'sink') fctx.clearRect(...px);
        else { fctx.fillStyle = '#0d0f11'; fctx.fillRect(...px); }
      }
      // a sunk facet stands on this floor: clear it under the facet and where
      // each well on the facet crosses the floor and the back behind it
      // (facetFloorClears; none without a negative facet lift). The floor
      // raster is unflipped, so the clears are mirrored on a flipped face.
      const sinkBack = Math.max(0, ...c.features.filter(f => f.kind === 'sink').map(f => f.val));
      const floorClears = mirrorClears(facetFloorClears(c, outs, {
        cavities, depthOf: builtDepth,
        floorZ: c.lift - (d - 0.1), backZ: c.lift - (d + sinkBack + 0.15)}), pc, !!F.flipLX, !!F.flipLY);
      clearFloor(floorCv, floorClears, pc.x, pc.y, PX);
      // shape-accurate punch: the cavity node's own art defines the hole
      if (!c.lift && !c.tilt) {   // a lifted cavity recesses from a raised part, so the
        // chassis face beneath it is already covered - punching it would leave
        // a hole straight through the faceplate. A tilted one punches the
        // facet it stands on instead (the outs loop).
        const pctx = cv.getContext('2d');
        pctx.globalCompositeOperation = 'destination-out';
        pctx.drawImage(await rasterize(c.cavSvg, c.w, c.h, PX),
                       Math.round(c.x * PX), Math.round(c.y * PX));
        pctx.globalCompositeOperation = 'source-over';
        facePunch[F.view].push({kind: 'shape', svg: c.cavSvg,
                                x: c.x, y: c.y, w: c.w, h: c.h, mouth: !!c.hollow});
      }
      // walls are double-sided: the interior is the recess, and the exterior is
      // the cage/housing body seen through neighboring vent holes. The back face
      // is a separate dark exterior; the textured floor plane sits just inside it
      // (sink pockets punch through the floor's alpha, so the back stays clear
      // of the floor by the sink allowance).
      // A WELL WHOSE SIDES ARE THE CHASSIS SHOWS THEM FROM INSIDE ONLY. The
      // double side is for a port cage, whose housing is seen through the vent
      // next to it. The R740xd's board well is 80 mm deep to the rear metal:
      // drawn double-sided, its rear wall stood a hair behind the rear panel
      // and everything looking in from that face - the C14 inlet's pins, the
      // rear drive bays - ended at a flat plane.
      const shell = cavityShell(c, INTO);
      if (!shell.walls) continue;
      const wallMat = new THREE.MeshLambertMaterial({color: c.wall,
        side: c.wallsInside ? THREE.BackSide : THREE.DoubleSide});
      const backMat = new THREE.MeshLambertMaterial({color: 0x23262b, side: THREE.DoubleSide});
      let walls;
      if (c.round) {
        walls = new THREE.Mesh(
          new THREE.CylinderGeometry(c.w / 2, c.w / 2, d, 24, 1, true), wallMat);
        walls.rotation.x = Math.PI / 2;
      } else {
        const noFace = new THREE.MeshBasicMaterial({visible: false});
        walls = new THREE.Mesh(new THREE.BoxGeometry(c.w, c.h, d),
          [wallMat, wallMat, wallMat, wallMat, noFace, noFace]);
      }
      // A NON-FINITE POSITION IS NOT A DRAWING ERROR, IT IS A DISAPPEARANCE.
      // Three.js culls a mesh whose matrix holds a NaN rather than complaining,
      // so the failure looks exactly like geometry nobody wrote - which is how
      // seven see-through slits survived in a shipped drawing. Say it out loud.
      const zc = c.lift - d / 2;
      if (!Number.isFinite(zc) || !Number.isFinite(LX(c.x, c.w)) || !Number.isFinite(LY(c.y, c.h)))
        console.error('relief: cavity has a non-finite position and will not render',
                      {owner: c.owner, x: c.x, y: c.y, d, lift: c.lift});
      walls.position.set(LX(c.x, c.w), LY(c.y, c.h), zc);
      addTo(walls);
      if (!shell.floor) continue;
      // textured floor: the aperture art, pushed to the back of the recess
      const floor = new THREE.Mesh(new THREE.PlaneGeometry(c.w, c.h),
        new THREE.MeshBasicMaterial({map: canvasTex(floorCv), transparent: true, alphaTest: 0.1, alphaToCoverage: true}));
      floor.position.set(LX(c.x, c.w), LY(c.y, c.h), c.lift - (d - 0.1));
      addTo(floor);
      // one raster feeds the floor and every raised feature standing in it, so
      // they are redrawn together from the one group svg they were cut from
      const floorMat = floor.material;
      reg(c.grpSvg, async text => {
        const g2 = await rasterize(text, c.grpRect.w, c.grpRect.h, PX);
        // the facet clear is REAPPLIED: a restyle re-cuts the floor from the art
        remap(floorMat, clearFloor(
          crop(g2, {x: pc.x - c.grpRect.x, y: pc.y - c.grpRect.y, w: pc.w, h: pc.h}, PX),
          floorClears, pc.x, pc.y, PX));
        for (const ft of cavCrops) {
          const pf = projOf(ft);
          if (ft.mat) remap(ft.mat,
            crop(g2, {x: pf.x - c.grpRect.x, y: pf.y - c.grpRect.y, w: pf.w, h: pf.h}, PX));
        }
      });
      // closed exterior back, deep enough to clear any sink pockets
      const maxSink = Math.max(0, ...c.features.filter(f => f.kind === 'sink').map(f => f.val));
      // ...and the closed back, 0.25 behind the floor, is cleared under a sunk
      // facet the same way, or it is the plane that crosses the cage wells
      if (floorClears.length) {
        const acv = document.createElement('canvas');
        acv.width = floorCv.width; acv.height = floorCv.height;
        const actx = acv.getContext('2d');
        actx.fillStyle = '#fff';
        actx.fillRect(0, 0, acv.width, acv.height);
        backMat.alphaMap = canvasTex(clearFloor(acv, floorClears, pc.x, pc.y, PX));
        backMat.alphaTest = 0.5;
      }
      const back = new THREE.Mesh(new THREE.PlaneGeometry(c.w, c.h), backMat);
      back.position.set(LX(c.x, c.w), LY(c.y, c.h), c.lift - (d + maxSink + 0.15));
      addTo(back);
      for (const ft of c.features) {
        if (ft.kind === 'top') {
          const hgt = Math.min(ft.val, d - 0.2);
          const mats = sideMats(ft.color);
          mats[4] = new THREE.MeshBasicMaterial({map: canvasTex(ft.faceCv)});
          ft.mat = mats[4];
          let m;
          if (ft.round) {
            // CylinderGeometry's materials are [side, +Y cap, -Y cap] and it stands
            // along Y, so the art goes on cap 1 and the whole thing lies down. Same
            // rotation the round cavity wall above takes, for the same reason.
            const cyl = new THREE.CylinderGeometry(ft.w / 2, ft.w / 2, hgt, 24);
            m = new THREE.Mesh(cyl, [mats[0], mats[4], mats[5]]);
            m.rotation.x = Math.PI / 2;
          } else {
            m = new THREE.Mesh(new THREE.BoxGeometry(ft.w, ft.h, hgt), mats);
          }
          m.position.set(LX(ft.x, ft.w), LY(ft.y, ft.h), c.lift - (d - hgt / 2));
          addTo(m);
        } else {   // sink: a deeper pocket beyond the floor
          const mat = new THREE.MeshLambertMaterial({color: ft.color, side: THREE.DoubleSide});
          let m;
          if (ft.round) {
            m = new THREE.Mesh(new THREE.CylinderGeometry(ft.w / 2, ft.w / 2, ft.val, 24), mat);
            m.rotation.x = Math.PI / 2;
          } else {
            m = new THREE.Mesh(new THREE.BoxGeometry(ft.w, ft.h, ft.val), mat);
          }
          m.position.set(LX(ft.x, ft.w), LY(ft.y, ft.h), -(d + ft.val / 2));
          addTo(m);
        }
      }
    }
    // Air vents stay as painted art rather than punched alpha. Punching them made
    // each honeycomb cell an alphaTest cutout, and alphaTest is a binary decision
    // taken AFTER texture filtering - at a grazing angle, with dozens of cells
    // falling in one pixel, the filtered alpha sits near the threshold and speckles.
    // Neither mipmaps nor alphaToCoverage can fix that; both act before the cut.
    // Left as colour, mipmapping averages the cells to smooth shading, which is
    // what you actually see on a real chassis from any distance.
    // Large openings (cavities, FRU bays) are punched elsewhere and do not moire,
    // being a handful of big rectangles rather than a fine repeating lattice.
    for (const v of vents) {
      // Vents are painted into the face art (see above), so the face is opaque
      // here and a box behind it can only ever show through as z-fighting. It sat
      // 0.05mm back, far finer than the depth buffer resolves, which is what was
      // speckling along the side faces. Nothing to draw.
      curOwner = v.owner;
      curTilt = null;
    }
    for (const dm of domes) { // gentle domes: node art draped on a paraboloid cap
      curOwner = dm.owner;
      curTilt = dm.tilt || null;
      // (LED lamps, bulged fan guards); apex proud, rim sunk 0.15 into the face
      const dcv = await rasterize(dm.svgText, dm.w, dm.h, PX);
      const geo = new THREE.CircleGeometry(0.5, 48);
      const pos = geo.attributes.position;
      for (let i = 0; i < pos.count; i++) {
        const rr = Math.min(1, Math.hypot(pos.getX(i), pos.getY(i)) * 2);
        pos.setZ(i, 1 - rr * rr);
      }
      geo.computeVertexNormals();
      const m = new THREE.Mesh(geo, new THREE.MeshLambertMaterial(
        {map: canvasTex(dcv), transparent: true, alphaTest: 0.1, alphaToCoverage: true}));
      m.scale.set(dm.w, dm.h, dm.dome + 0.15);
      m.position.set(LX(dm.x, dm.w), LY(dm.y, dm.h), (dm.lift || 0) - 0.15);
      addTo(m);
      reg(dm.svgText, async text => remap(m.material, await rasterize(text, dm.w, dm.h, PX)),
          {mat: m.material, w: dm.w, h: dm.h, path: dm.owner});
    }
    for (const o of outs) {   // protrusions: bezel plates, handles, studs, tubes
      curOwner = o.owner;
      curTilt = o.tilt || null;
      // the pocket a sunk facet stands in, for what its skirt stands beside
      // (profileSkirt, emptyHeightAt); a proud facet has none
      if (o.facet && (o.lift || 0) < 0) o.pocket = pocketOf(o, cavities, builtDepth);
      if (o.facet) {
        // the wedge covers its footprint: clear the flat face under it (facetPunch)
        const fp = facetPunch(o);
        cv.getContext('2d').clearRect(...punchRectPx(fp, 0, 0, PX));
        facePunch[F.view].push(fp);
      }
      // A FACET'S SURFACE CARRIES THE PARTS ON IT. Its own art is the first
      // layer and the parts' art goes over it at their front-view rects; each
      // is a text a restyle can change, so each has a slot (see `reg` below).
      const facetTexts = o.facet && o.parts && o.parts.length
        ? [o.svgText, ...o.parts.map(p => p.svgText)] : null;
      const facetArt = async cvs => {
        if (!facetTexts) return cvs;
        const fx = cvs.getContext('2d');
        for (let i = 0; i < o.parts.length; i++) {
          const p = o.parts[i];
          fx.drawImage(await rasterize(facetTexts[i + 1], p.w, p.h, PX),
                       Math.round((p.x - o.x) * PX), Math.round((p.y - o.y) * PX));
        }
        return cvs;
      };
      const ocv = await rasterize(o.svgText, o.w, o.h, PX);
      // A LIFTED CAVITY PUNCHES THE SURFACE IT WAS LIFTED ONTO. The cavity loop
      // above skips the FACE punch for a lifted cavity, on the reasoning that it
      // recesses from a raised part whose own geometry already covers the face -
      // which is right, and only half the job. Nothing then punched that raised
      // part, so the well sat at the correct depth behind an unbroken surface.
      //
      // smartoptics/dcp-404 is the case that found it: a faceplate standing 44
      // proud of its chassis with four QSFP cages lifted onto it. The cages are
      // pure cavities - no `out` of their own - so they had no raised feature to
      // be seen by and simply vanished. Its QSFP-DD neighbour appeared to work
      // and did not: what showed was its collar, an `out` that the lift raised to
      // 45, while its bay was buried exactly like the others.
      //
      // The punch is the same one the face gets - destination-out with the
      // cavity node's own art, so the hole has the cage's shape and not its
      // bounding box - and the material is already `transparent` with an
      // `alphaTest`, so erased pixels discard the fragment and the cavity behind
      // shows through.
      //
      // IT MUST BE REAPPLIED ON EVERY RESTYLE, which is why it is a function and
      // not a block. `reg` re-rasterises this node from `o.svgText` whenever a
      // descendant changes, and a lifted flat part IS such a descendant: the
      // DCP-404 composes fourteen lamps that all live inside `body`, so setting
      // any lamp state rebuilds the plate texture. Composed once inline, that
      // rebuild dropped the punch and the marks and re-buried all four cages and
      // both hazard triangles - the very symptom this fixes, undone by the first
      // state change. Found in review rather than by any test.
      //
      // A TILTED CAVITY PUNCHES THE FACET IT STANDS ON, with its front-view
      // footprint: that is where its mouth crosses the sloped surface. The lift
      // rule only compares entries in one frame - a tilted entry's lift is
      // measured from its facet, not from the face.
      const sameFrame = (a, b) => !a.tilt === !b.tilt &&
        (!a.tilt || (a.tilt.on === b.tilt.on && `${a.tilt.anchor}` === `${b.tilt.anchor}`));
      const seated = cavities.filter(c => (sameFrame(c, o) && cavitySeatsOn(c, o))
        || (o.facet && c.tilt && c.tilt.on === o.facet.id && !c.lift));
      const marks = flatLifted.filter(f => sameFrame(f, o) && cavitySeatsOn(f, o));
      // An untilted pair keeps the plain offset; anything tilted is placed by
      // front-view rects scaled into the raster, which then holds either frame.
      const put = async (octx, cvs, e, text) => {
        if (!o.tilt && !e.tilt) {
          octx.drawImage(await rasterize(text, e.w, e.h, PX),
                         Math.round((e.x - o.x) * PX), Math.round((e.y - o.y) * PX));
          return;
        }
        const po = projOf(o), pe = projOf(e);
        const kx = cvs.width / po.w, ky = cvs.height / po.h;
        octx.drawImage(await rasterize(text, pe.w, pe.h, PX),
                       Math.round((pe.x - po.x) * kx), Math.round((pe.y - po.y) * ky),
                       Math.round(pe.w * kx), Math.round(pe.h * ky));
      };
      const compose = async cvs => {
        if (!seated.length && !marks.length) return cvs;
        const octx = cvs.getContext('2d');
        octx.globalCompositeOperation = 'destination-out';
        for (const c of seated) await put(octx, cvs, c, c.cavSvg);
        octx.globalCompositeOperation = 'source-over';
        // and the flat art goes ON, after the punch, so a marking beside a cage
        // is not erased by it
        for (const f of marks) await put(octx, cvs, f, f.svgText);
        return cvs;
      };
      // THE SIDE COLOUR IS THE ART'S DOMINANT COLOUR, NOT ITS CENTRE PIXEL.
      // It used to be the one pixel at the middle of the node's box, which is fine
      // until something small sits exactly there - and on a fan tray something does.
      // The AIS800-64D's handle carries its release button at dead centre, a fixed
      // #5a2320 with no `fill-from`, so every tray took the BUTTON's colour for its
      // whole handle: the 2D art went blue in the back-to-front build and the 3D
      // tube stayed red, in both builds, because the pixel being read never changed.
      // The commonest opaque colour in the node's own art is what the part is made
      // of; a button, a legend or a screw head is by definition a minority of it.
      // Still read from the UNPUNCHED raster, so this goes before `compose`.
      //
      // AND IT IS READ AGAIN ON EVERY REPAINT, when the art is what chose it. A
      // field can recolour the node after the build - an optic's latch set red
      // from a host page - and a repaint that only redrew the face texture left
      // every side of the part, and the whole of a `bar` bail that has no face
      // texture at all, the grey it was built in (#481). So each material this
      // node's colour went into is collected in `bodyMats`, and a repaint sets
      // them from the repainted art. A `data-z-color` is a statement rather than
      // a reading and is never overridden; the thread and knurl textures, which
      // bake the colour into a canvas of their own, are not re-cut.
      const derived = !o.color;
      if (derived) o.color = dominantColor(ocv);
      const bodyMats = [];
      const bodyMat = (extra = {}) => {
        const m = new THREE.MeshLambertMaterial({color: o.color, ...extra});
        bodyMats.push(m);
        return m;
      };
      await compose(await facetArt(ocv));
      const faceTex = new THREE.MeshBasicMaterial(
        {map: canvasTex(ocv), transparent: true, alphaTest: 0.1, alphaToCoverage: true});
      if (facetTexts) {
        // every slot repaints the whole surface from the latest text of each;
        // no lamp animation is handed this material, since a frame drawn from
        // the facet's own text alone would drop the parts
        const repaint = async () => {
          const cvs = await rasterize(facetTexts[0], o.w, o.h, PX);
          recolourBody(derived, bodyMats, cvs);
          remap(faceTex, await compose(await facetArt(cvs)));
        };
        facetTexts.forEach((t, i) => reg(t, async text => { facetTexts[i] = text; await repaint(); }));
      } else reg(o.svgText,
          async text => {
            const cvs = await rasterize(text, o.w, o.h, PX);
            // unpunched, as at build: `compose` below erases the seated cavities
            recolourBody(derived, bodyMats, cvs);
            remap(faceTex, await compose(cvs));
          },
          {mat: faceTex, w: o.w, h: o.h, path: o.owner});
      if (o.uhandle !== undefined && o.uhandle !== '') {
        const far = +o.uhandle;
        const horizontal = o.w >= o.h;
        // THE NODE IS THE WHOLE HANDLE'S ART AND THE TUBE IS USUALLY THINNER THAN IT.
        // This node has to be the entire 2D handle, because the face texture hides exactly
        // the node carrying the relief attribute - put the attribute on an inner bar and the
        // flat art around it stays painted on the face UNDER the geometry, which is what a
        // reviewer saw on the AIS800-64D's trays. So where the drawn loop is taller than its
        // tube, the contract says the diameter.
        const dia = (o.dia && +o.dia) || Math.min(o.w, o.h), r = dia / 2, Rb = dia;
        const zBar = far - r, legH = Math.max(0.5, zBar - Rb);
        const uLen = Math.max(o.w, o.h);
        const u0 = horizontal ? o.x : o.y;
        const a = u0 + r, b = u0 + uLen - r;          // leg centerlines (svg coords)
        const cc = horizontal ? o.y + o.h / 2 : o.x + o.w / 2;  // cross-axis center
        const mat = bodyMat();
        const P = (u, z) => horizontal
          ? [u - fw / 2, (F.flipLY ? -1 : 1) * (fh / 2 - cc), z]
          : [cc - fw / 2, (F.flipLY ? -1 : 1) * (fh / 2 - u), z];
        for (const u of [a, b]) {                     // legs
          const leg = new THREE.Mesh(new THREE.CylinderGeometry(r, r, legH, 16), mat);
          leg.rotation.x = Math.PI / 2;
          leg.position.set(...P(u, legH / 2));
          addTo(leg);
        }
        const barLen = (b - Rb) - (a + Rb);           // crossbar between the bends
        if (barLen > 0.1) {
          const bar = new THREE.Mesh(new THREE.CylinderGeometry(r, r, barLen, 16), mat);
          if (horizontal) bar.rotation.z = Math.PI / 2;
          bar.position.set(...P((a + b) / 2, zBar));
          addTo(bar);
        }
        for (const [u, near] of [[a + Rb, a], [b - Rb, b]]) {   // continuous bends
          const holder = new THREE.Group();
          holder.position.set(...P(u, zBar - Rb));
          holder.rotation.z = horizontal ? 0 : Math.PI / 2;
          const elbow = new THREE.Mesh(new THREE.TorusGeometry(Rb, r, 12, 16, Math.PI / 2), mat);
          // low-u corner sweeps (-u -> +z), high-u corner (+u -> +z), in holder-local xy
          const legLocalU = horizontal ? near : -near;   // svg y runs opposite to local up
          const cornerLocalU = horizontal ? u : -u;
          elbow.rotation.set(Math.PI / 2, 0, legLocalU < cornerLocalU ? Math.PI / 2 : 0);
          holder.add(elbow);
          addTo(holder);
        }
      } else if (o.bar !== undefined && o.bar !== '') {
        // round tube along the node's long axis, lift..lift+bar off the face
        const len = Math.max(o.w, o.h), r = o.bar / 2;
        const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, len, 16), bodyMat());
        if (o.w >= o.h) m.rotation.z = Math.PI / 2;   // horizontal bar
        m.position.set(LX(o.x, o.w), LY(o.y, o.h), o.lift + r);
        addTo(m);
      } else if (o.cyl !== undefined && o.cyl !== '') {
        // cylinder: lift..lift+cyl, top cap carries the node art
        const r = Math.min(o.w, o.h) / 2;
        let side;
        if (o.thread) {
          // single-start helix: one diagonal per tile, tiled once around the
          // circumference and once per pitch along the axis, so the stripe meets
          // itself at the seam and reads as a continuous thread rather than rings
          const tc = document.createElement('canvas');
          tc.width = 32; tc.height = 32;
          const tx = tc.getContext('2d');
          tx.fillStyle = o.color; tx.fillRect(0, 0, 32, 32);
          tx.strokeStyle = 'rgba(0,0,0,0.42)'; tx.lineWidth = 7;
          tx.lineCap = 'butt';
          for (const dy of [-32, 0, 32]) {          // wrap copies keep it seamless
            tx.beginPath(); tx.moveTo(0, 32 + dy); tx.lineTo(32, dy); tx.stroke();
          }
          tx.strokeStyle = 'rgba(255,255,255,0.20)'; tx.lineWidth = 2.5;
          for (const dy of [-32, 0, 32]) {
            tx.beginPath(); tx.moveTo(0, 27 + dy); tx.lineTo(32, dy - 5); tx.stroke();
          }
          const ttex = canvasTex(tc);
          ttex.wrapS = ttex.wrapT = THREE.RepeatWrapping;
          ttex.repeat.set(1, Math.max(1, Math.round(o.cyl / o.thread)));
          side = new THREE.MeshLambertMaterial({map: ttex});
        } else if (o.knurl) {  // fine grip ridges wrapped around the circumference
          const kc = document.createElement('canvas');
          kc.width = 8; kc.height = 8;
          const kctx = kc.getContext('2d');
          kctx.fillStyle = o.color; kctx.fillRect(0, 0, 8, 8);
          kctx.fillStyle = 'rgba(0,0,0,0.45)'; kctx.fillRect(4, 0, 4, 8);
          const ktex = canvasTex(kc);
          ktex.wrapS = THREE.RepeatWrapping;
          ktex.repeat.set(Math.max(12, Math.round(2 * Math.PI * r / 0.5)), 1);
          ktex.magFilter = THREE.NearestFilter;
          side = new THREE.MeshLambertMaterial({map: ktex});
        } else {
          side = bodyMat();
        }
        const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, o.cyl, 24),
          [side, faceTex, side]);
        m.rotation.x = Math.PI / 2;
        m.position.set(LX(o.x, o.w), LY(o.y, o.h), o.lift + o.cyl / 2);
        addTo(m);
      } else if ((o.profile && o.profile.length >= 2) || (o.profileY && o.profileY.length >= 2)) {
        // A DEPTH THAT VARIES ACROSS THE NODE, BOTH WAYS. `profile` is [x, out]
        // from the left edge, `profile-y` is [y, out] from the top edge, and
        // the surface at any point is the LESSER of the two. The R740xd's
        // bezel is a honeycomb 20 proud whose end caps fall away to 9 at the
        // tips and whose bottom rail sits back at 15 - a section like a
        // football sliced a third through, in both directions - and a box
        // drew it as a slab with the right picture on the front. Built as a
        // height field with the node's art on it and skirts down to the face.
        const px = o.profile && o.profile.length >= 2 ? o.profile : [[0, o.out], [o.w, o.out]];
        const py = o.profileY && o.profileY.length >= 2 ? o.profileY : [[0, o.out], [o.h, o.out]];
        const interp = (pts, t) => {
          if (t <= pts[0][0]) return pts[0][1];
          for (let i = 0; i + 1 < pts.length; i++) {
            const [t0, v0] = pts[i], [t1, v1] = pts[i + 1];
            if (t <= t1) return t1 === t0 ? v1 : v0 + (v1 - v0) * (t - t0) / (t1 - t0);
          }
          return pts[pts.length - 1][1];
        };
        const depthAt = (x, y) => Math.min(interp(px, x), interp(py, y));
        // sample at every knot and every 5 mm, so a knee is a knee and a
        // straight run is straight
        const knots = (pts, len) => {
          const set = new Set([0, len]);
          for (const [t] of pts) if (t > 0 && t < len) set.add(t);
          for (let v = 5; v < len; v += 5) set.add(v);
          return [...set].sort((a, b) => a - b);
        };
        const xs = knots(px, o.w), ys = knots(py, o.h);
        if (o.rings && o.rings.length) {
          // `shape: true` beside a profile: the same surface, cut to the
          // node's outline, with its walls along the outline rather than the
          // box - see shapedHeightField
          const local = r => r.map(([x, y]) => [x - o.x, y - o.y]);
          const regions = o.rings.map(r => ({shell: local(r.shell), holes: r.holes.map(local)}));
          const g = shapedHeightField(regions, xs, ys, depthAt, o.lift);
          const toWorld = (P) => {
            const out = [];
            for (let i = 0; i < P.length; i += 3)
              out.push(LX(o.x + P[i], 0), LY(o.y + P[i + 1], 0), P[i + 2]);
            return out;
          };
          const front = new THREE.BufferGeometry();
          front.setAttribute('position', new THREE.Float32BufferAttribute(toWorld(g.top.pos), 3));
          const uvs = [];
          for (let i = 0; i < g.top.pos.length; i += 3)
            uvs.push(g.top.pos[i] / o.w, 1 - g.top.pos[i + 1] / o.h);
          front.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
          front.setIndex(g.top.idx);
          front.computeVertexNormals();
          faceTex.side = THREE.DoubleSide;
          addTo(new THREE.Mesh(front, faceTex));
          const skirt = new THREE.BufferGeometry();
          skirt.setAttribute('position', new THREE.Float32BufferAttribute(toWorld(g.skirt.pos), 3));
          skirt.setIndex(g.skirt.idx);
          skirt.computeVertexNormals();
          addTo(new THREE.Mesh(skirt, bodyMat({side: THREE.DoubleSide})));
          if (g.holeSkirt.idx.length) {
            // a window's edge is its own colour - the PBC-2000's amber bead
            const hs = new THREE.BufferGeometry();
            hs.setAttribute('position', new THREE.Float32BufferAttribute(toWorld(g.holeSkirt.pos), 3));
            hs.setIndex(g.holeSkirt.idx);
            hs.computeVertexNormals();
            addTo(new THREE.Mesh(hs, o.holeColor
              ? new THREE.MeshLambertMaterial({color: o.holeColor, side: THREE.DoubleSide})
              : bodyMat({side: THREE.DoubleSide})));
          }
        } else {
          const nx = xs.length, ny = ys.length;
          const pos = [], uvs = [], idx = [];
          for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
            pos.push(LX(o.x + xs[i], 0), LY(o.y + ys[j], 0), depthAt(xs[i], ys[j]));
            uvs.push(xs[i] / o.w, 1 - ys[j] / o.h);
          }
          for (let j = 0; j + 1 < ny; j++) for (let i = 0; i + 1 < nx; i++) {
            const a = j * nx + i, b = a + 1, c = a + nx, d = c + 1;
            idx.push(a, c, b, b, c, d);
          }
          const front = new THREE.BufferGeometry();
          front.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
          front.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
          front.setIndex(idx);
          front.computeVertexNormals();
          faceTex.side = THREE.DoubleSide;   // a mirrored face reverses the winding
          addTo(new THREE.Mesh(front, faceTex));
          // skirts: the perimeter dropped to the out's base (`o.lift`; below
          // the plate for a sunk facet), so the ends and the rails are the
          // slopes the profiles give them and not open edges (profileSkirt)
          // A SKIRT AGAINST A NEIGHBOUR AS TALL IS INSIDE THE SOLID. A sawtooth
          // is a face and its return, two nodes meeting at the tooth's apex;
          // each dropped a full-height skirt there, back to back in one plane,
          // and a cage well running down the slope crossed them and showed
          // them z-fighting inside the cage. One tooth has no wall there.
          // Facet to facet only (skirtNeighbours): without facets this is a no-op.
          const {pts, idx: si} = profileSkirt(o, xs, ys, depthAt, skirtNeighbours(o, outs));
          const sp = [];
          for (const [x, y, z] of pts) sp.push(LX(o.x + x, 0), LY(o.y + y, 0), z);
          const skirt = new THREE.BufferGeometry();
          skirt.setAttribute('position', new THREE.Float32BufferAttribute(sp, 3));
          skirt.setIndex(si);
          skirt.computeVertexNormals();
          addTo(new THREE.Mesh(skirt, bodyMat({side: THREE.DoubleSide})));
        }
      } else if (o.rings && o.rings.length) {
        // THE SHAPE, NOT THE BOX. `shape: true` on the feature. The face art was
        // always the node's own; it was the SIDES that followed the bounding box,
        // so a contoured moulding read as a cardboard box with the right picture
        // on the front. Extruding the outline gives it the sides it has.
        const depth = o.out - o.lift;
        const shapes = o.rings.map(r => {
          const s = new THREE.Shape(
            r.shell.map(([x, y]) => new THREE.Vector2(LX(x, 0), LY(y, 0))));
          for (const h of r.holes)
            s.holes.push(new THREE.Path(
              h.map(([x, y]) => new THREE.Vector2(LX(x, 0), LY(y, 0)))));
          return s;
        });
        const geo = new THREE.ExtrudeGeometry(shapes, {depth, bevelEnabled: false});
        // ExtrudeGeometry's UVs are world-space; the face texture is rasterised
        // over the node's rect, so put world coordinates back into face mm and
        // then into that rect. Inverting LX/LY rather than assuming they are the
        // identity is what keeps a flipped face right - `left` and `bottom` are
        // drawn mirrored, and a texture that ignored that would read backwards.
        const unX = wx => (F.flipLX ? -wx : wx) + fw / 2;
        const unY = wy => fh / 2 - (F.flipLY ? -wy : wy);
        const pos = geo.attributes.position, uv = geo.attributes.uv;
        for (let i = 0; i < pos.count; i++) {
          uv.setXY(i, (unX(pos.getX(i)) - o.x) / o.w,
                   1 - (unY(pos.getY(i)) - o.y) / o.h);
        }
        uv.needsUpdate = true;
        const m = new THREE.Mesh(
          geo, [faceTex, bodyMat()]);
        m.position.set(0, 0, o.lift);
        addTo(m);
      } else {
        // box: lift..out (lift defaults to 0 = sits on the face)
        const depth = o.out - o.lift;
        const mats = sideMats(o.color);
        bodyMats.push(...mats.filter((_, i) => i !== 4));
        mats[4] = faceTex;
        const m = new THREE.Mesh(new THREE.BoxGeometry(o.w, o.h, depth), mats);
        m.position.set(LX(o.x, o.w), LY(o.y, o.h), o.lift + depth / 2);
        addTo(m);
      }
    }
    curOwner = null;
    curTilt = null;
    // DEEPEST FIRST: a card's optic cuts its plane off the face before the
    // card punches its own shape out (the card's art leaves the optic out, but
    // its punch would still clear the optic's pixels). The sort is stable, so
    // every FRU of one depth - all of them, on a face with no card optic -
    // keeps the order it always had.
    const segsOf = f => f.path.split('/').length;
    frus.sort((a, b) => segsOf(b) - segsOf(a));   // the groups above are already made
    for (const f of frus) {   // move the FRU's face art into its group; leave a bay
      const fg = fruGroups[f.path];
      // AN OPEN-BACKED BAY'S MOUTH HAS ALREADY BEEN PUNCHED OUT OF `cv`, and it
      // is the size of the whole slot - so cropping `cv` gave the module an
      // empty plane: adapters floating in front of an open passage and no
      // faceplate. Cut from the pristine art instead, and re-open only the
      // module's own cavities (the mouth is the bay's hole, not the module's).
      // A TILTED MODULE (an optic in a cage on a facet) is cut from the face at
      // its front-view rect `pf`, and its plane and body take its true size,
      // inside its tilt group. For every other module pf is f.
      const pf = projOf(f);
      // A TILTED MODULE IS CUT FROM THE PRISTINE ART, like a lifted one: it
      // stands on a facet, and the facet's footprint has been cleared from `cv`.
      const faceCrop = crop(f.lift || f.openBack || f.tilt ? artCv : cv, pf, PX);
      // replay one face punch on a canvas whose origin is pf (a facet's is a rect)
      const unpunch = async (ctx2, p) => {
        if (p.kind === 'rect') { ctx2.clearRect(...punchRectPx(p, pf.x, pf.y, PX)); return; }
        ctx2.globalCompositeOperation = 'destination-out';
        ctx2.drawImage(await rasterize(p.svg, p.w, p.h, PX),
                       Math.round((p.x - pf.x) * PX), Math.round((p.y - pf.y) * PX));
        ctx2.globalCompositeOperation = 'source-over';
      };
      // A TILTED MODULE'S OWN BORES ARE PUNCHED FROM ITS PLANE HERE, not through
      // `cv`: a tilted cavity never punches the face (its facet is its surface),
      // so no face punch exists to replay, and one recorded for the purpose
      // would be replayed by every plane overlapping it, the card's included.
      // Scoped to the owner, the hole reaches exactly the plane in front of it.
      const bores = f.tilt ? cavities.filter(c => c.tilt && c.proj && c.owner === f.path) : [];
      const unbore = async ctx2 => {
        for (const c of bores) {
          ctx2.globalCompositeOperation = 'destination-out';
          ctx2.drawImage(await rasterize(c.cavSvg, c.proj.w, c.proj.h, PX),
                         Math.round((c.proj.x - pf.x) * PX), Math.round((c.proj.y - pf.y) * PX));
          ctx2.globalCompositeOperation = 'source-over';
        }
      };
      if (f.openBack && !f.lift) {
        const x0 = faceCrop.getContext('2d');
        for (const p of facePunch[F.view]) {
          if (p.mouth || !(p.x < pf.x + pf.w && p.x + p.w > pf.x && p.y < pf.y + pf.h && p.y + p.h > pf.y)) continue;
          await unpunch(x0, p);
        }
      }
      // A MODULE IS ITS SHAPE, NOT ITS BOX. The R740xd's riser 2 is two
      // full-height slots over one low-profile slot - an L - and its box
      // takes in the top-left corner of a power supply; riser 1's brackets
      // reach two millimetres past its plate into the iDRAC jack. Cropping
      // the box moved that corner and that jack-top onto the ejecting riser
      // and left a hole in the panel where they had been. So the crop is
      // masked by the module's own art, exactly as a cavity's punch is: what
      // the module paints comes with it, and what it does not stays.
      const mask = await rasterize(f.svgText, pf.w, pf.h, PX);
      // a seated optic with no `body:` gets one (opticBody, built below)
      const ob = opticBody({behaviour: f.behaviour, body: FRU_META[f.path].body,
                            depth: f.depth, w: f.w, h: f.h});
      const opticMat = ob
        ? new THREE.MeshLambertMaterial({color: f.bodyColor || dominantColor(mask)}) : null;
      const mctx = faceCrop.getContext('2d');
      mctx.globalCompositeOperation = 'destination-in';
      mctx.drawImage(mask, 0, 0, faceCrop.width, faceCrop.height);
      mctx.globalCompositeOperation = 'source-over';
      if (bores.length) await unbore(mctx);
      const zf = f.lift || 0;
      const plane = new THREE.Mesh(new THREE.PlaneGeometry(f.w, f.h),
        new THREE.MeshBasicMaterial({map: canvasTex(faceCrop), transparent: true, alphaTest: 0.1, alphaToCoverage: true}));
      plane.position.set(LX(f.x, f.w), LY(f.y, f.h), zf + 0.3);
      fg.add(plane);
      // A FIELD OR A STATE WRITTEN ON A MODULE REPAINTS ITS PLANE. The crop above
      // is a one-time cut of the face canvas, so a wattage written on a supply
      // after the build changed the face texture and left the supply's own
      // plane reading the old badge. Re-cut from the module's own art, restyled,
      // with the cavities that fall in its rect punched from it again - the
      // C14 inlet's pins live behind one. Taken before the module's own shape
      // punch is recorded below, which is the face's hole and not this plane's.
      // A LIFTED MODULE'S PLANE SITS BELOW THE FACE'S PUNCHES. Its first crop
      // came from the pristine art canvas for that reason: a DIMM on the board
      // or a drive in the tray lies inside its well's own punch, and replaying
      // that punch would cut the whole plane away. Only a module at the face
      // has cavities of its own to re-open.
      // AN OPEN BAY'S MOUTH IS NOT THE MODULE'S. It is the bay's own hole, the
      // size of the whole slot, and replaying it here cut the entire faceplate
      // out of every module seated in an open-backed bay.
      // (a tilted module, like a lifted one, replays none: its holes are `bores`)
      const punchesHere = f.lift || f.tilt ? [] : facePunch[F.view].filter(p => !p.mouth &&
        p.x < pf.x + pf.w && p.x + p.w > pf.x && p.y < pf.y + pf.h && p.y + p.h > pf.y);
      reg(f.svgText, async text => {
        const c2 = await rasterize(text, pf.w, pf.h, PX);
        const x2 = c2.getContext('2d');
        for (const p of punchesHere) await unpunch(x2, p);
        if (bores.length) await unbore(x2);
        remap(plane.material, c2);
        if (opticMat && !f.bodyColor) recolourBody(true, [opticMat], c2);
      });
      // CLEAR, never fill: an opaque patch on the chassis face would occlude
      // everything behind it (the module's own cavities, pins, bay interior)
      // and the same shape comes out of the face, not the rectangle
      const pctx = cv.getContext('2d');
      pctx.globalCompositeOperation = 'destination-out';
      pctx.drawImage(mask, Math.round(pf.x * PX), Math.round(pf.y * PX));
      pctx.globalCompositeOperation = 'source-over';
      facePunch[F.view].push({kind: 'shape', svg: f.svgText, x: pf.x, y: pf.y, w: pf.w, h: pf.h});
      const meta = FRU_META[f.path];
      // A SEATED OPTIC WITH NO `body:` (opticBody): one box behind its face, in
      // its body node's side colour (bodyFill); an optic whose skin names no body node is
      // coloured as a derived relief side is, the dominant colour of its art.
      if (ob) {
        const m = new THREE.Mesh(new THREE.BoxGeometry(ob.w, ob.h, ob.depth), opticMat);
        m.position.set(LX(f.x, f.w), LY(f.y, f.h), zf - ob.depth / 2 - 0.05);
        m.userData.portrayalPath = f.path;
        fg.add(m);
      }
      if (meta.body && meta.body.boxes) {
        // THE BODY IN PIECES, each a plain box in the FRU's group so the
        // riser's PCB and connectors come out with its plate. Side art is
        // for the one-box form; a PCB is a colour.
        for (const b of bodyBoxes(meta.body, f.w, f.h)) {
          // toFace is the drawn (foreshortened) frame; a tilted box is unprojected
          const r = f.tilt ? unproject(localToFace(f.toFace, b), f.tilt) : localToFace(f.toFace, b);
          const m = new THREE.Mesh(new THREE.BoxGeometry(r.w, r.h, b.z1 - b.z0),
            new THREE.MeshLambertMaterial({color: b.color}));
          m.position.set(LX(r.x, r.w), LY(r.y, r.h),
                         zf - b.z0 - (b.z1 - b.z0) / 2 - 0.05);
          fg.add(m);
        }
      } else if (meta.body) {   // full module body travels with the FRU
        const {mesh, fp, d} = await bodyBoxMesh(meta.body, f.w, f.h);
        // A MODULE SEATED ON ITS SIDE HAS ITS BODY ON ITS SIDE. `fp` is in
        // the module's own frame, and `f.x`/`f.w` are its DRAWN box: in a bay
        // with `rotate: 90` (fs/fhd-4ufce's on-edge slots) that box is 35.05
        // wide and the footprint 99 wide, so the body stood across the slot
        // through both neighbours. A turned module with a footprint goes
        // through its own frame (`bodyPose`) and its body, and the back hung
        // on it, turn with it; anything else is placed from its drawn box,
        // exactly as before.
        const pose = bodyPose(f.toFace, meta.body);
        const at = pose || {x: LX(f.x + fp.at[0], fp.size[0]), y: LY(f.y + fp.at[1], fp.size[1]), turn: 0};
        if (pose) at.x = LX(pose.r.x, pose.r.w), at.y = LY(pose.r.y, pose.r.h);
        mesh.position.set(at.x, at.y, zf - d / 2 - 0.05);
        mesh.rotation.z = at.turn;
        fg.add(mesh);
        // A MODULE'S BACK IS A FACE, NOT A PICTURE. `body.sides.rear` is a
        // compiled drawing - for a cassette it IS the module's rear face, the
        // same one the chassis projects through an open back - so it carries
        // relief: a flanged MTP stands off it, its opening recesses into it.
        // Painted flat as a side texture, the back of a pulled cassette read as
        // a photograph glued to a box. This runs the ordinary face pass over
        // that drawing and hangs the result on the back of the body, inside the
        // FRU group, so it comes out with the module. Turned a half turn, like
        // the chassis's own rear face: the art is drawn as seen from behind.
        // NOT FOR A LIFTED MODULE, whose face is not the panel and whose body
        // box is placed off it, and NOT FOR A BACK'S OWN BACK: `ctx.back` stops
        // the recursion at one level, so a rear drawing that itself seats a
        // module cannot walk backwards for ever.
        //
        // THE BACK THIS MODULE HOLDS NOW, not the one it ships with: a plug
        // put on a cassette's back in the explorer, or a cap taken off it, is
        // in a drawing of its own - `ctx.backSource(bay, ref, url)` is the
        // host's answer (viewer3d seats the map's keys under the bay into the
        // shipped drawing with swap.js's seatBack and hands back the URL of
        // that copy), and with no host answer the shipped drawing is built.
        const backSrc = meta.body.sides && meta.body.sides.rear;
        if (backSrc && ctx.dist && !f.lift && !ctx.back) {
          const key = `back:${f.path}`;
          const shipped = ctx.dist + backSrc;
          const src = ctx.backSource ? await ctx.backSource(f.path, f.ref, shipped) : shipped;
          const back = {view: key, fw: () => fp.size[0], fh: () => fp.size[1],
                        deep: () => d, pos: () => [0, 0, 0], rot: [0, Math.PI, 0]};
          const before = meshes.length;
          await buildFaceRelief(back, {...ctx, src, deep: d, back: true});
          if (meshes.length > before) {
            const bg = meshes.pop();
            if (at.turn) {
              // turned about the chassis's depth axis, outside the back's own
              // half turn - a group of its own, so the two do not compose
              const tg = new THREE.Group();
              tg.add(bg);
              tg.position.set(at.x, at.y, zf - d - 0.05);
              tg.rotation.z = at.turn;
              fg.add(tg);
            } else {
              bg.position.set(at.x, at.y, zf - d - 0.05);
              fg.add(bg);
            }
          }
          // and the box's own back takes the face's punched texture, so the
          // recesses the pass just built are not covered by a flat copy of
          // the same art
          if (faceCv[key] && Array.isArray(mesh.material))
            mesh.material[5] = new THREE.MeshBasicMaterial(
              {map: canvasTex(faceCv[key]), transparent: true, alphaTest: 0.1,
               alphaToCoverage: true});
        }
      }
      // empty bay: interior surfaces only, so it never occludes the module's
      // own cavities (the C14 inlet pins live inside this volume)
      // the bay is as deep as the thing that goes in it, not 60 mm
      const bd = meta.bayDepth;
      // an occupant with no depth of its own leaves its port as the build
      // draws it, with no box (ejectTravel)
      if (!meta.leavesBay) continue;
      if (f.shelf) continue;   // a shelf, not a hole: nothing is left behind
      if (f.openBack) continue;   // a passage: the rear hole's walls are its sides
      // a body in pieces is a riser, and behind an unseated riser is the
      // chassis interior, not a hole: nothing is left behind here either
      if (meta.body && meta.body.boxes) continue;
      const bay = new THREE.Mesh(new THREE.BoxGeometry(f.w + 0.6, f.h + 0.6, bd),
        new THREE.MeshLambertMaterial({color: 0x0a0c0e, side: THREE.BackSide}));
      bay.position.set(LX(f.x, f.w), LY(f.y, f.h), zf - bd / 2 - 0.2);
      // THE HOLE BELONGS TO THE BAY, NOT THE MODULE. Tagged with the bay's
      // path so it stays when the module is unseated - that is the point of
      // it - and goes when the bay itself does: the mid tray's four bays are
      // pulled with the tray, and four dark boxes were left hanging where it
      // had been, hiding the board.
      bay.userData.portrayalPath = f.path;
      // an optic's cage is on its card, so the hole behind it leaves with the card;
      // a tilted module's hole is in its tilt frame, which is its group's parent
      (f.within || f.tilt ? fruGroups[f.path].parent : grp).add(bay);
    }
    for (const s of subBodies) {
      const body = BODY_META[s.ref];
      if (!body || !body.boxes) continue;
      const into = s.tilt ? tiltGroupFor(s.tilt, fruGroups[s.owner] || grp) : fruGroups[s.owner] || grp;
      for (const b of bodyBoxes(body, 0, 0)) {
        const r = s.tilt ? unproject(localToFace(s.toFace, b), s.tilt) : localToFace(s.toFace, b);
        const m = new THREE.Mesh(new THREE.BoxGeometry(r.w, r.h, b.z1 - b.z0),
          new THREE.MeshLambertMaterial({color: b.color}));
        m.position.set(LX(r.x, r.w), LY(r.y, r.h),
                       (s.lift || 0) - b.z0 - (b.z1 - b.z0) / 2 - 0.05);
        m.userData.portrayalPath = s.path;
        into.add(m);
      }
    }
  meshes.push(grp);
}
