// kit/rack/bundle-route.js
// A BUNDLE'S TRUNK AND ITS MEMBERS' ROUTES, as lists of waypoints (#921,
// docs/cable-bundles-design.md section 4). Pure, and it reads no drawing: the
// callers in route.js and bundles.js resolve the waypoints first, and hand in
// what needs a measure (which trunk end is nearer a port) as a function.
//
// ELEMENTS. A route is cut into elements so two routes can be compared: a
// pathway waypoint ({item, via}) is one element; a run along a lane is a node
// at every U it passes and a segment between each two, so two cables going up
// left-front, one from U20 and one from U22, both to U30, share the nodes and
// segments from U22 to U30. Cutting at every U is the same as cutting at every
// U where some member's run starts or stops: an interval is shared exactly
// when each of its unit segments is shared by the same cables.

import {isWaypoint, uLabel} from './model.js';

const key = w => (w.lane ? `n|${w.lane}|${w.ru}` : `p|${w.item}|${w.via}`);
export const waypointKey = w => (isWaypoint(w) ? key(w) : null);

// The elements of a list of waypoints, in order, each {key, kind, ...}: kind
// 'p' (a pathway: item, via), 'n' (a lane node: lane, u) or 's' (a lane
// segment between u and u + 1: lane, u). Consecutive lane waypoints on one
// lane are a run; a lane waypoint after anything else is a node of its own.
// Each element also says where it is on the list: `seg`, the waypoint it is at
// or the one its run starts from, and `t`, how far along to the next (0 to 1).
export function elementsOf(waypoints) {
  const out = [];
  const push = e => { if (out.at(-1)?.key !== e.key) out.push(e); };
  waypoints.forEach((w, k) => {
    if (!w.lane) { push({key: key(w), kind: 'p', item: w.item, via: w.via, seg: k, t: 0}); return; }
    const prev = out.at(-1);
    if (k > 0 && prev?.kind === 'n' && prev.lane === w.lane && prev.u !== w.ru) {
      const from = prev.u, step = w.ru > from ? 1 : -1, span = Math.abs(w.ru - from);
      for (let u = from; u !== w.ru; u += step) {
        const lo = Math.min(u, u + step), done = Math.abs(u + step - from);
        push({key: `s|${w.lane}|${lo}`, kind: 's', lane: w.lane, u: lo, seg: k - 1, t: (done - 0.5) / span});
        if (u + step === w.ru) push({key: key(w), kind: 'n', lane: w.lane, u: w.ru, seg: k, t: 0});
        else push({key: `n|${w.lane}|${u + step}`, kind: 'n', lane: w.lane, u: u + step, seg: k - 1, t: done / span});
      }
    } else push({key: key(w), kind: 'n', lane: w.lane, u: w.ru, seg: k, t: 0});
  });
  return out;
}

// Elements back to waypoints: each pathway, and each lane node where a run
// starts, stops, turns or jumps. A node strictly between two on one lane, in
// one direction, adds nothing to the line and is left out.
export function waypointsOf(elements) {
  const nodes = elements.filter(e => e.kind !== 's')
    .map(e => (e.kind === 'p' ? {item: e.item, via: e.via} : {lane: e.lane, ru: e.u}));
  return nodes.filter((w, k) => {
    const p = nodes[k - 1], n = nodes[k + 1];
    return !(w.lane && p?.lane === w.lane && n?.lane === w.lane && (p.ru - w.ru) * (w.ru - n.ru) > 0);
  });
}

const viaText = v => (/^guide-(\d+)$/.test(v) ? `ring ${v.slice(6)}` : v);
// An element as a person reads it: "mgr-1 ring 3", "left-front U20".
export function elementText(e, nameOf = id => id, frame = null) {
  const u = n => (frame ? uLabel(frame, n) : n);
  if (e.kind === 'p') return `${nameOf(e.item)} ${viaText(e.via)}`;
  if (e.kind === 'n') return `${e.lane} U${u(e.u)}`;
  return `${e.lane} U${u(e.u)}-U${u(e.u + 1)}`;
}
// "c1", "c1 and c2", "c1, c2 and c3".
export const andList = xs => (xs.length < 2 ? xs.join('') : `${xs.slice(0, -1).join(', ')} and ${xs.at(-1)}`);

const SEPARATELY = 'Bundle them separately, or give the bundle a route.';

// ── the trunk, worked out from the members' own routes (section 4.1) ─────
// `members` is [{id, waypoints}] in the order the cables were named, each
// cable's own route as resolveRoute gives it with no bundle in play. Returns
// {route} (the trunk as waypoints) or {error}, a refusal in words.
export function deriveTrunk(members, {nameOf = id => id, frame = null} = {}) {
  const txt = e => elementText(e, nameOf, frame);
  const seqs = members.map(m => {
    const seen = new Set();
    return {id: m.id, els: elementsOf(m.waypoints).filter(e => !seen.has(e.key) && seen.add(e.key))};
  });
  const count = new Map(), el = new Map();
  for (const s of seqs) for (const e of s.els) { count.set(e.key, (count.get(e.key) || 0) + 1); el.set(e.key, e); }
  const shared = k => count.get(k) >= 2;
  for (const s of seqs) s.sh = s.els.map((e, i) => ({k: e.key, i})).filter(x => shared(x.k));
  const uses = (s, k) => s.sh.some(x => x.k === k);

  // Joins: shared elements next to each other on some member's route,
  // counting only its shared elements; direct when nothing lies between them.
  const joinKey = (x, y) => (x < y ? `${x}\u0000${y}` : `${y}\u0000${x}`);
  const joins = new Map(), detours = [];
  for (const s of seqs) for (let j = 1; j < s.sh.length; j++) {
    const [p, q] = [s.sh[j - 1], s.sh[j]];
    if (q.i - p.i === 1) {
      const jk = joinKey(p.k, q.k);
      const J = joins.get(jk) || {x: p.k, y: q.k, by: []};
      J.by.push(s.id);
      joins.set(jk, J);
    } else detours.push({s, x: p.k, y: q.k});
  }
  // Components of the shared elements under the direct joins.
  const parent = new Map([...count.keys()].filter(shared).map(k => [k, k]));
  const find = k => { while (parent.get(k) !== k) k = parent.get(k); return k; };
  for (const J of joins.values()) parent.set(find(J.x), find(J.y));

  // A DETOUR is parting and meeting again: refused when the two elements are
  // joined some other way. When nothing else joins them, it is a run no cable
  // takes, refused below as groups that share nothing.
  for (const {s, x, y} of detours) {
    if (find(x) !== find(y)) continue;
    let others = seqs.filter(o => o !== s && uses(o, x) && uses(o, y)).map(o => o.id);
    if (!others.length) others = seqs.filter(o => o !== s && (uses(o, x) || uses(o, y))).map(o => o.id);
    return {error: `${s.id} parts from ${andList(others)} at ${txt(el.get(x))} and meets them again at ${txt(el.get(y))}. ${SEPARATELY}`};
  }

  const adj = new Map([...parent.keys()].map(k => [k, new Set()]));
  for (const J of joins.values()) { adj.get(J.x).add(J.y); adj.get(J.y).add(J.x); }
  // Path order, which does not depend on the order the cables were named: the
  // longest shared run first, a tie to the lowest cable id.
  const byId = (a, b) => a.id.localeCompare(b.id, 'en', {numeric: true});
  const ref = [...seqs].sort((a, b) => b.sh.length - a.sh.length || byId(a, b))[0];
  const pos = k => { const i = ref?.sh.findIndex(x => x.k === k); return i >= 0 ? i : Infinity; };

  // A LOOP is parting and meeting again without a detour. The join on a loop
  // with the fewest members is the one blamed.
  const bridges = bridgesOf(adj);
  const onLoop = [...joins.values()].filter(J => !bridges.has(joinKey(J.x, J.y)));
  if (onLoop.length) {
    const J = onLoop.sort((a, b) => a.by.length - b.by.length || Math.min(pos(a.x), pos(a.y)) - Math.min(pos(b.x), pos(b.y)))[0];
    const blamed = seqs.filter(s => J.by.includes(s.id));
    const s0 = blamed[0], ix = s0.sh.find(x => x.k === J.x).i, iy = s0.sh.find(x => x.k === J.y).i;
    const [x, y] = ix < iy ? [J.x, J.y] : [J.y, J.x];
    let others = seqs.filter(o => !J.by.includes(o.id) && uses(o, x) && uses(o, y)).map(o => o.id);
    if (!others.length) others = seqs.filter(o => !J.by.includes(o.id) && o.sh.some(z => find(z.k) === find(x))).map(o => o.id);
    const who = blamed.map(s => s.id);
    return {error: `${andList(who)} part${who.length === 1 ? 's' : ''} from ${andList(others)} at ${txt(el.get(x))} and meet${who.length === 1 ? 's' : ''} them again at ${txt(el.get(y))}. ${SEPARATELY}`};
  }

  // A FORK: an element joined to three or more others.
  const fork = [...adj.keys()].filter(k => adj.get(k).size >= 3).sort((a, b) => pos(a) - pos(b))[0];
  if (fork != null) {
    const lead = seqs.find(s => uses(s, fork) && s.sh.length >= 2);
    const at = lead.sh.findIndex(x => x.k === fork);
    const incoming = at > 0 ? lead.sh[at - 1].k : null;
    const branch = from => {
      const seen = new Set([fork, from]), todo = [from];
      while (todo.length) for (const n of adj.get(todo.pop())) if (!seen.has(n)) { seen.add(n); todo.push(n); }
      seen.delete(fork);
      return seen;
    };
    const named = from => {
      const e = el.get(from);
      if (e.kind !== 's') return txt(e);
      const beyond = [...adj.get(from)].find(n => n !== fork);
      return txt(beyond ? el.get(beyond) : e);
    };
    const parts = [...adj.get(fork)].filter(n => n !== incoming).sort((a, b) => pos(a) - pos(b)).map(n => {
      const set = branch(n), who = seqs.filter(s => s.sh.some(x => set.has(x.k))).map(s => s.id);
      return `${andList(who)} go${who.length === 1 ? 'es' : ''} on to ${named(n)}`;
    });
    return {error: `Bundle members part after ${txt(el.get(fork))}: ${parts.join('; ')}. ${SEPARATELY}`};
  }

  // GROUPS THAT SHARE NOTHING are two bundles.
  const roots = [...new Set([...adj.keys()].map(find))];
  if (roots.length > 1) {
    const groups = roots.map(r => {
      const who = seqs.filter(s => s.sh.some(x => find(x.k) === r));
      const first = who[0].sh.find(x => find(x.k) === r).k;
      return {who: who.map(s => s.id), first, at: seqs.indexOf(who[0])};
    }).sort((a, b) => a.at - b.at);
    // A cable in two groups runs with the others at both, and only detours join
    // them: they run together there and apart between, so nothing joins them.
    const all = groups.flatMap(g => g.who);
    if (new Set(all).size < all.length) {
      const who = seqs.map(s => s.id).filter(id => all.includes(id));
      return {error: `${andList(who)} run together at ${andList(groups.map(g => txt(el.get(g.first))))}, but apart between them. ${SEPARATELY}`};
    }
    const said = groups.map(g => `${andList(g.who)} share ${txt(el.get(g.first))}`);
    return {error: `${said.slice(0, -1).join(', ')}, and ${said.at(-1)}, but the ${groups.length === 2 ? 'two groups share' : 'groups share'} nothing. ${SEPARATELY}`};
  }
  const lonely = seqs.find(s => !s.sh.length);
  if (lonely) return {error: `${lonely.id} runs with none of the others. Leave it out, or give the bundle a route.`};

  // ONE SIMPLE PATH, oriented the way the first cable named that meets two or
  // more of its elements runs, from its a end to its b end.
  const start = [...adj.keys()].find(k => adj.get(k).size <= 1);
  const path = [start];
  for (let prev = null, cur = start; ;) {
    const next = [...adj.get(cur)].find(n => n !== prev);
    if (next == null) break;
    path.push(next); prev = cur; cur = next;
  }
  const orient = seqs.find(s => s.sh.length >= 2);
  if (orient) {
    const at = k => path.indexOf(k);
    if (at(orient.sh[1].k) < at(orient.sh[0].k)) path.reverse();
  }
  return {route: waypointsOf(path.map(k => el.get(k)))};
}

// The joins no loop runs through, by Tarjan's bridge search over an
// undirected graph {node -> Set(neighbours)}. Keys as deriveTrunk's joinKey.
function bridgesOf(adj) {
  const disc = new Map(), low = new Map(), out = new Set();
  let t = 0;
  const visit = (u, parent) => {
    disc.set(u, t); low.set(u, t); t++;
    for (const v of adj.get(u)) {
      if (!disc.has(v)) {
        visit(v, u);
        low.set(u, Math.min(low.get(u), low.get(v)));
        if (low.get(v) > disc.get(u)) out.add(u < v ? `${u}\u0000${v}` : `${v}\u0000${u}`);
      } else if (v !== parent) low.set(u, Math.min(low.get(u), disc.get(v)));
    }
  };
  for (const u of adj.keys()) if (!disc.has(u)) visit(u, null);
  return out;
}

// ── a member's route along the trunk (section 4.2) ───────────────────────
// `own` is the member's own route and `trunk` the bundle's, both as resolved
// waypoints; `member` is {cable, a?, b?}. `aNearStart()` answers, for a member
// whose own route never meets the trunk, whether its a port is nearer the
// trunk's first waypoint than its last (true when it cannot tell).
// Returns {waypoints, join, leave, met, stale}: the route it follows; the
// trunk waypoints it joins and leaves at (null when the trunk is empty);
// `met`, whether its own route meets the trunk; and `stale`, the peel ends
// ('a', 'b') that were not used because they are not on the trunk, or are a
// pair whose a point is at or past its b point.
export function followTrunk(own, trunk, member, {aNearStart = () => true} = {}) {
  const T = elementsOf(trunk), M = elementsOf(own);
  if (!T.length) return {waypoints: own, join: null, leave: null, met: false, stale: []};
  const tAt = new Map();
  T.forEach((e, i) => { if (!tAt.has(e.key)) tAt.set(e.key, i); });
  const onTrunk = e => tAt.has(e.key);
  const meets = M.map((e, i) => ({e, i})).filter(x => x.e.kind !== 's' && onTrunk(x.e));
  const stale = [];
  const peel = end => {
    const w = member?.[end];
    if (w == null) return null;
    const k = waypointKey(w);
    if (k == null || !tAt.has(k)) { stale.push(end); return null; }
    return tAt.get(k);
  };
  let pa = peel('a'), pb = peel('b');
  const last = T.length - 1;
  const sign = n => (n > 0 ? 1 : n < 0 ? -1 : 0);
  let i0, i1, dir;
  if (meets.length) {
    i0 = tAt.get(meets[0].e.key); i1 = tAt.get(meets.at(-1).e.key);
    dir = sign(i1 - i0) || (pb != null && sign(pb - i0)) || (pa != null && sign(i0 - pa)) || 1;
  } else {
    dir = aNearStart() ? 1 : -1;
    [i0, i1] = dir > 0 ? [0, last] : [last, 0];
  }
  // A pair in the wrong order is stale; so is one peel point at or past the other
  // end of the member's run.
  if (pa != null && pb != null && (pb - pa) * dir <= 0) { stale.push('a', 'b'); pa = pb = null; }
  if (pa != null && (i1 - pa) * dir <= 0) { stale.push('a'); pa = null; }
  if (pb != null && (pb - i0) * dir <= 0) { stale.push('b'); pb = null; }
  const join = pa ?? i0, leave = pb ?? i1;
  const slice = [];
  for (let i = join; ; i += dir || 1) { slice.push(T[i]); if (i === leave) break; }
  // Its own route up to where it joins; from where it leaves, on to the next
  // element of its own route that is not on the trunk, then along it.
  const atM = i => M.findIndex(e => e.key === T[i].key);
  let before = [], after = [];
  if (meets.length) {
    const j = pa != null ? atM(pa) : -1;
    before = M.slice(0, j >= 0 ? j : meets[0].i);
    const k = pb != null ? atM(pb) : -1;
    after = M.slice((k >= 0 ? k : meets.at(-1).i) + 1);
    while (after.length && onTrunk(after[0])) after.shift();
  }
  return {waypoints: waypointsOf([...before, ...slice, ...after]), join: waypointsOf([T[join]])[0] ?? null,
          leave: waypointsOf([T[leave]])[0] ?? null, met: meets.length > 0, stale: [...new Set(stale)]};
}
