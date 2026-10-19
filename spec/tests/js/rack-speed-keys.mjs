// spec/tests/js/rack-speed-keys.mjs
// What the kit keeps of a lay (kit 0.25.0, route.js WHAT IS KEPT OF A LAY) is
// found again by a key, and a key that leaves something out gives an old
// answer with nothing to say so. Each test here changes ONE thing a lay
// reads and nothing else, with everything kept from before the change, and
// holds the answers to those of a copy of the rack in which every object is
// new: it fails if that one thing is taken out of the key. Then the check a
// page can turn on (`ctx.checkKept`), the list of solids, a leg through a
// pass-through and a span that hangs past a tray's edge.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import * as M from '../../../kit/rack/model.js';
import * as R from '../../../kit/rack/route.js';
import * as S from '../../../kit/rack/solids.js';
import * as Rest from '../../../kit/rack/resting.js';
import * as F from './cable-solids-fixture.mjs';
import {speedRack, moveDevice, edgeSpans} from './speed-fixture.mjs';

const paths = (r, c) => r.cables.map(x => JSON.stringify(R.routePath(r, x, c)));
const lengths = (r, c) => r.cables.map(x => JSON.stringify(R.routedLength(r, x, c)));
// how many of two lists of texts differ
const differ = (a, b) => a.filter((t, i) => t !== b[i]).length;

test('the media is part of what a lay is kept under: a cord made OS2 from OM4 says so', () => {
  // OM4 and OS2 share a diameter, a bend radius, a drape, a reach and what
  // is inside the port: nothing of the lay differs but the media it carries
  const made = speedRack(M, F, {cables: 60, seed: 21}), rack = made.rack;
  paths(rack, made.ctxOf(rack));
  const om4 = rack.cables.filter(c => c.media === 'om4' && R.routePath(rack, c, made.ctxOf(rack)));
  assert.ok(om4.length >= 2, 'the rack has OM4 cords with a path');
  const next = {...rack, cables: rack.cables.map(c => (om4.includes(c) ? {...c, media: 'os2'} : c))};
  const kept = paths(next, made.ctxOf(next)), fresh = paths(structuredClone(next), made.ctxOf(next));
  assert.deepEqual(kept, fresh);
  for (const c of next.cables.filter(x => om4.some(o => o.id === x.id))) assert.equal(R.routePath(next, c, made.ctxOf(next)).media, 'os2');
});

test('the drape is part of what a lay is kept under: a context that answers another family hangs the spans its way', () => {
  // the same rack and cables; only what `ctx.typeOf` answers changes, and
  // with it how far a free span sags
  const made = speedRack(M, F, {cables: 60, seed: 22}), rack = made.rack;
  const stiff = r => ({...made.ctxOf(r), typeOf: () => ({family: 'dac'})});
  const before = paths(rack, made.ctxOf(rack));
  const kept = paths(rack, stiff(rack)), fresh = paths(structuredClone(rack), stiff(rack));
  assert.deepEqual(kept, fresh);
  // and it is a change: some span hangs otherwise
  assert.ok(differ(before, fresh) >= 3, `${differ(before, fresh)} paths differ by the drape`);
});

test('the trays are part of the world a lay is kept in: a tray that stands higher, with no solid moved, is landed on higher', () => {
  // the lacer's catalogue entry with its tray's floor 6 mm up and every solid
  // where it was: only the surfaces a span can land on change
  const made = speedRack(M, F, {cables: 60, seed: 23}), rack = made.rack;
  const lacer = made.chassisOf('fhd-cmp5dr');
  const raised = {...lacer, trays: lacer.trays.map(t => ({...t, top: t.top + 6}))};
  const up = r => { const c = made.ctxOf(r); return {...c, chassisOf: ref => (ref === 'fhd-cmp5dr' ? raised : c.chassisOf(ref))}; };
  assert.deepEqual(S.solidsOf(rack, up(rack)), S.solidsOf(rack, made.ctxOf(rack)));
  const before = paths(rack, made.ctxOf(rack));
  const kept = paths(rack, up(rack)), fresh = paths(structuredClone(rack), up(rack));
  assert.deepEqual(kept, fresh);
  assert.ok(differ(before, fresh) >= 1, `${differ(before, fresh)} paths differ by the tray`);
});

test('which end sorts first is part of which lay is kept: a port named to sort before the other end, where it stands, turns the choice', () => {
  // cords between two ports of one switch; the context reads `a-port-N` and
  // `z-port-N` where `port-N` stands, so naming end b one or the other
  // changes which end sorts first and nothing else of either lay
  const made = speedRack(M, F, {cables: 150, seed: 24}), rack = made.rack;
  const bare = e => ({...e, path: String(e.path).replace(/^[az]-/, '')});
  const ctxOf = r => { const c = made.ctxOf(r); return {...c, portX: e => c.portX(bare(e)), portY: e => c.portY(bare(e)), portBoxesOf: undefined}; };
  const same = rack.cables.filter(c => c.a.item === c.b.item);
  assert.ok(same.length >= 8, 'cords between two ports of one switch');
  const named = letter => ({...rack, cables: rack.cables.map(c => (same.includes(c) ? {...c, b: {...c.b, path: `${letter}-${c.b.path}`}} : c))});
  const last = named('z'), first = named('a');
  const before = paths(last, ctxOf(last));
  const kept = paths(first, ctxOf(first)), fresh = paths(structuredClone(first), ctxOf(first));
  assert.deepEqual(kept, fresh);
  // and it is a change beyond the name: some cord is laid from its other end
  const unnamed = t => t.replace(/[az]-port-/g, 'port-');
  assert.ok(differ(before.map(unnamed), fresh.map(unnamed)) >= 1, 'a path differs by which end sorts first');
});

// ── the check a page can turn on ─────────────────────────────────────────
test('ctx.checkKept: a rack, a cable, an end or an item changed in place throws; a rack and a context made anew do not', () => {
  const made = speedRack(M, F, {cables: 40, seed: 25});
  const checked = r => ({...made.ctxOf(r), checkKept: true});
  const all = (r, c) => r.cables.map(x => R.routePath(r, x, c));
  const fresh = () => structuredClone(made.rack);
  // as it should be used: nothing thrown, read after read, edit after edit
  let rack = fresh();
  const ctx = checked(rack);
  assert.doesNotThrow(() => { all(rack, ctx); all(rack, ctx); });
  const moved = moveDevice(rack, made.switches[6]);
  assert.doesNotThrow(() => all(moved, checked(moved)));
  // a cable's media changed in place, the same context
  const c = rack.cables.find(x => x.media === 'aoc');
  c.media = 'cat6a';
  assert.throws(() => R.routePath(rack, c, ctx), /changed in place.*ctx\.checkKept/);
  // an end repointed in place
  rack = fresh();
  let cx = checked(rack);
  all(rack, cx);
  rack.cables[0].b.path = rack.cables[1].b.path;
  assert.throws(() => R.routePath(rack, rack.cables[0], cx), /ctx\.checkKept/);
  // an item moved in place
  rack = fresh(); cx = checked(rack);
  all(rack, cx);
  for (const it of rack.items) if (it.id === made.switches[6] || it.on === made.switches[6]) it.ru -= 1;
  assert.throws(() => all(rack, cx), /ctx\.checkKept/);
  // a context that answers otherwise than it did, changed in place
  rack = fresh();
  let reach = 65;
  const live = {...made.ctxOf(rack), plugReachOf: () => reach, checkKept: true};
  all(rack, live);
  reach = 20;
  assert.throws(() => all(rack, live), /ctx\.checkKept/);
  // without the check the same misuse gives the old path and says nothing
  rack = fresh();
  const plain = made.ctxOf(rack), was = JSON.stringify(all(rack, plain));
  rack.cables.find(x => x.media === 'aoc').media = 'cat6a';
  assert.equal(JSON.stringify(all(rack, plain)), was);
});

// ── the list of solids ───────────────────────────────────────────────────
// A leg against a list of solids, as solids.js read it before the list was
// laid out flat: every solid in turn, its box grown by the cable's radius
// for a ring's part or a zero-U part, the stretch strictly inside it, and
// left out where that stretch lies in a hole the cable fits.
// P-0016: a hole is judged on the stretch inside the TRUE plate, not the grown
// one, which ends up to a radius outside a hole cut through the plate.
function reference(a, b, solids, diameter) {
  const out = [], AX = ['x', 'y', 'z'], EPS = 1e-6;
  const stretch = (box) => {
    let t0 = 0, t1 = 1;
    for (const k of AX) {
      const lo = box[`${k}0`] + EPS, hi = box[`${k}1`] - EPS;
      if (!(hi > lo)) return null;
      const p = a[k], dv = b[k] - a[k];
      if (Math.abs(dv) < 1e-12) { if (p <= lo || p >= hi) return null; continue; }
      let u = (lo - p) / dv, v = (hi - p) / dv;
      if (u > v) [u, v] = [v, u];
      t0 = Math.max(t0, u); t1 = Math.min(t1, v);
      if (t1 - t0 <= 1e-9) return null;
    }
    return [t0, t1];
  };
  for (const s of solids) {
    let box = s.box;
    const grown = (/^ring\/[^/]+\/./.test(String(s.part ?? '')) || s.zeroU === true) && diameter > 0;
    if (grown) {
      const r = diameter / 2;
      box = {x0: box.x0 - r, x1: box.x1 + r, y0: box.y0 - r, y1: box.y1 + r, z0: box.z0 - r, z1: box.z1 + r};
    }
    const span = stretch(box);
    if (!span) continue;
    const [t0, t1] = span;
    const at = t => ({x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t, z: a.z + (b.z - a.z) * t});
    const p = at(t0), q = at(t1);
    const own = grown ? stretch(s.box) : null;
    const [hp, hq] = own ? [at(own[0]), at(own[1])] : [p, q];
    const within = (pt, h) => AX.every(k => pt[k] >= h[`${k}0`] - EPS && pt[k] <= h[`${k}1`] + EPS);
    // #992: a zero-U part's hole is taken less the radius across the hole (the
    // plate's thinnest axis is the way through, and is left as it is)
    const way = AX.slice().sort((m, n) => (s.box[`${m}1`] - s.box[`${m}0`]) - (s.box[`${n}1`] - s.box[`${n}0`]))[0];
    const less = h => {
      if (!(s.zeroU === true && diameter > 0)) return h.box;
      const r = diameter / 2, o = {...h.box};
      for (const k of AX.filter(k => k !== way)) {
        const mid = (o[`${k}0`] + o[`${k}1`]) / 2;
        o[`${k}0`] = Math.min(o[`${k}0`] + r, mid); o[`${k}1`] = Math.max(o[`${k}1`] - r, mid);
      }
      return o;
    };
    if ((s.holes || []).some(h => within(hp, less(h)) && within(hq, less(h)) && diameter <= Math.min(...h.size) + 1e-9)) continue;
    out.push({solid: s, t0, t1, at: p});
  }
  return out.sort((x, y) => x.t0 - y.t0);
}
const said = hits => hits.map(h => [h.solid.item, h.solid.part, h.t0, h.t1, h.at]);
// the reference rack of #949 with a duct at the left front upright: its floor has eight pass-throughs
function ducted() {
  const rack = {...F.ownerRack(), zeroU: [{id: 'z1', ref: 'cmv-sfd45u5w', cfg: 'base', at: 'left-front', offsetMm: 0}]};
  const ctx = F.ctxOf(), solids = S.solidsOf(rack, ctx);
  return {rack, ctx, solids, floor: solids.find(s => s.item === 'z1' && s.holes.length)};
}

test('a leg through a pass-through of a part beside the rack: through it where the cable fits, across the plate where it does not', () => {
  const {solids, floor} = ducted();
  assert.ok(solids.length >= 12, 'a list long enough to be laid out flat');
  assert.equal(floor.holes.length, 8);
  let through = 0, across = 0, n = 0;
  const thin = Math.min(floor.box.x1 - floor.box.x0, floor.box.z1 - floor.box.z0) < 3 ? (floor.box.x1 - floor.box.x0 < 3 ? 'x' : 'z') : 'y';
  for (const h of floor.holes) {
    const mid = {x: (h.box.x0 + h.box.x1) / 2, y: (h.box.y0 + h.box.y1) / 2, z: (h.box.z0 + h.box.z1) / 2};
    const w = Math.min(...h.size);
    // down the middle of the hole, off its middle, just inside its edge, just outside it, and aslant
    for (const [du, dv, slant] of [[0, 0, 0], [w / 4, 0, 0], [0, w / 2 - 2, 0], [0, w / 2 + 2, 0], [0, 0, 3], [w, 0, 0]])
      for (const d of [3, 6, w - 0.5, w + 0.5, 0]) {
        const across2 = ['x', 'y', 'z'].filter(k => k !== thin);
        const a = {...mid, [thin]: mid[thin] - 40, [across2[0]]: mid[across2[0]] + du, [across2[1]]: mid[across2[1]] + dv};
        const b = {...a, [thin]: mid[thin] + 40, [across2[0]]: a[across2[0]] + slant};
        for (const [p, q] of [[a, b], [b, a]]) {
          const got = S.legCrossings(p, q, solids, {diameter: d}), want = reference(p, q, solids, d);
          assert.deepEqual(said(got), said(want));
          assert.ok(got.every((x, i) => x.solid === want[i].solid));
          n++;
          if (got.some(x => x.solid === floor)) across++; else through++;
        }
      }
  }
  assert.ok(through >= 100 && across >= 40, `${n} legs: ${through} through a hole, ${across} across the plate`);
});

test('legs of every kind against the solids of a rack are crossed as each solid in turn would be', () => {
  const made = speedRack(M, F, {cables: 10, seed: 26}), solids = S.solidsOf(made.rack, made.ctxOf(made.rack));
  let a = 12345;
  const rnd = () => { a = (Math.imul(a, 1664525) + 1013904223) >>> 0; return a / 4294967296; };
  const pt = () => ({x: -320 + 640 * rnd(), y: 600 + 1400 * rnd(), z: -800 + 950 * rnd()});
  let hits = 0;
  for (let k = 0; k < 4000; k++) {
    const p = pt(), q = k % 3 ? pt() : {...p, [['x', 'y', 'z'][k % 5 % 3]]: pt().x};
    const d = [0, 3, 6, 7.5][k % 4];
    const got = S.legCrossings(p, q, solids, {diameter: d}), want = reference(p, q, solids, d);
    assert.deepEqual(said(got), said(want));
    hits += got.length;
  }
  assert.ok(hits > 2000, `${hits} crossings compared`);
});

test('a list of solids is laid out again when it is another list, another length, or has another first or last solid', () => {
  const {solids} = ducted();
  const list = solids.map(s => ({...s}));
  const far = {item: 'far', part: 'body', box: {x0: 900, x1: 950, y0: 0, y1: 50, z0: 0, z1: 50}, holes: []};
  const p = {x: 925, y: 25, z: -10}, q = {x: 925, y: 25, z: 60};
  assert.deepEqual(S.legCrossings(p, q, list), []);
  // the last solid replaced in place: seen
  const lastWas = list[list.length - 1];
  list[list.length - 1] = far;
  assert.deepEqual(S.legCrossings(p, q, list).map(h => h.solid.item), ['far']);
  list[list.length - 1] = lastWas;
  assert.deepEqual(S.legCrossings(p, q, list), []);
  // one more solid: seen
  list.push(far);
  assert.deepEqual(S.legCrossings(p, q, list).map(h => h.solid.item), ['far']);
  // the first solid's box replaced: seen
  list.pop();
  list[0] = {...list[0]};
  list[0].box = far.box;
  assert.equal(S.legCrossings(p, q, list).length, 1);
  // another list with other solids, as a caller is to hand in: seen
  assert.deepEqual(S.legCrossings(p, q, [...solids.slice(0, 5), far, ...solids.slice(5)]).map(h => h.solid.item), ['far']);
});

// ── a span past a tray's edge ────────────────────────────────────────────
// The spans of speed-fixture.mjs edgeSpans, as the kit hangs them (recorded
// into speed-edge-spans.json, to a millionth of a millimetre): the points of
// each, and what it lands on. Recorded from kit 0.24.0 (c3313dbb), and again
// for 0.27.0 (#987): 39 of the 45 are as they were, and six have one or two
// more points and no point gone, each where the span passes the edge of a
// surface it lies on, at the height a cable lies on it (resting.js
// overEdges); five of those name that surface among what they land on.
const EDGE_SPANS = JSON.parse(readFileSync(new URL('./speed-edge-spans.json', import.meta.url), 'utf8'));
test('a span that hangs past the edge of a tray lands, clears and drops as it did', () => {
  const got = edgeSpans(F, S, Rest);
  assert.equal(got.length, 45);
  assert.ok(got.filter(([, lands]) => lands.length).length >= 5 && got.filter(([pts, lands]) => pts.length && !lands.length).length >= 5,
    'some land on the tray and some hang clear of it');
  assert.deepEqual(got, EDGE_SPANS);
});

// ── the lane table ───────────────────────────────────────────────────────
// Where the lanes run enters a lay's inputs through each lane waypoint's
// point, and the world through one rule only: the last way round a body a leg
// crosses from front to back, by a side lane (solids.js detour, rule 3). So
// a rack is built in which that is the only way. A cord runs straight from a
// front port to a rear port of one device, with no waypoint. Between them
// stands a wall; a plate stands just where the way over it, under it and
// round each end of it would turn, so each of those ends inside a plate and
// is no way; the lanes pass outside the side plates. A duct of no solid
// stands at each left upright and carries its lane, and the context says
// how wide the two are: 40 mm, and the left lane is the near one; 600 mm,
// and the cord goes round by the right.
function walled(ductW) {
  const RU = 44.45, yp = 19.5 * RU, m = 3 + 5;               // a Cat 6 cord: its radius and the clearance a detour keeps
  // boxes in the device's own frame: x from its left edge, y from its foot, z back from its face
  const box = (x0, x1, y0, y1, z0, z1) => ({x: x0 + 241, y: y0 - 19 * RU, z: -z1, w: x1 - x0, h: y1 - y0, d: z1 - z0});
  const maze = {ru: 1, w: 482, h: 44, d: 300, solids: [
    {part: 'wall', box: box(-250, 250, yp - 100, yp + 100, -200, -100)},
    {part: 'plate-left', box: box(-250 - m - 2, -250 - m + 2, yp - 300, yp + 300, -420, 120)},
    {part: 'plate-right', box: box(250 + m - 2, 250 + m + 2, yp - 300, yp + 300, -420, 120)},
    {part: 'plate-over', box: box(-300, 300, yp + 100 + m - 2, yp + 100 + m + 2, -420, 120)},
    {part: 'plate-under', box: box(-300, 300, yp - 100 - m - 2, yp - 100 - m + 2, -420, 120)}]};
  const duct = {ru: 45, w: ductW, h: 2000, d: 100, mount: 'rack-side', guides: {front: ['duct']}};
  let rack = M.withItem(M.newRack(), {ref: 'maze', cfg: 'base', ru: 20, label: 'maze'}).rack;
  rack = {...rack, zeroU: ['left-front', 'left-rear'].map((at, k) => ({id: `z${k + 1}`, ref: 'duct', cfg: 'base', at, offsetMm: 0})),
    cables: [{id: 'c1', a: {item: 'i1', path: 'f', view: 'front'}, b: {item: 'i1', path: 'r', view: 'rear'}, media: 'cat6', route: [], routeEdited: true}]};
  const ctx = {chassisOf: ref => ({maze, duct}[ref] ?? null), guidesOf: () => [], portX: () => -100, portY: () => yp};
  return {rack, ctx};
}
// which side of the rack a path goes furthest out on, and how many bodies it crosses
const round = p => [p.crossings.length, Math.sign(p.points.reduce((s, q) => (Math.abs(q.x) > Math.abs(s) ? q.x : s), 0))];
test('where the lanes run is part of the world a lay is kept in: a duct made wider, with no solid moved, sends the cord round by the other lane', () => {
  const near = walled(40), far = walled(600), rack = near.rack, cable = rack.cables[0];
  assert.deepEqual(S.solidsOf(rack, far.ctx), S.solidsOf(rack, near.ctx));
  // it goes round by a lane, the left one, and crosses nothing
  assert.deepEqual(round(R.routePath(rack, cable, near.ctx)), [0, -1]);
  const kept = R.routePath(rack, cable, far.ctx);
  const copy = structuredClone(rack), fresh = R.routePath(copy, copy.cables[0], walled(600).ctx);
  assert.equal(JSON.stringify(kept), JSON.stringify(fresh));
  assert.deepEqual(round(kept), [0, 1]);
});
