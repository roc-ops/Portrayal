// A ring is solid, and a cord enters it through its opening (#968,
// docs/cable-lay-design.md section 3.3). The FHD-CMP5DR's snap-in rings, as
// the catalogue places them (cable-solids-catalogue.json, a copy of the
// build's rack.json): each is five boxes, its two legs, the hook over the
// slit, the bar over the opening and the seat under it. Every figure here was
// measured on these fixtures, and each check asserts it measured something,
// so a check that found nothing cannot pass.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as R from '../../../kit/rack/route.js';
import * as S from '../../../kit/rack/solids.js';
import {RU} from '../../../kit/rack/rails.js';
import * as F from './route-direct-fixture.mjs';

const r15 = 1.5;                                   // an OM4 cord's radius
const BASE = 40 * RU + 3.0;                        // the floor of U41, what each ring stands on
const near = (a, b, what, tol = 1e-6) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a}, want ${b}`);
const isRing = s => /^ring\//.test(s.part);
const dist = (p, b) => Math.hypot(Math.max(b.x0 - p.x, 0, p.x - b.x1), Math.max(b.y0 - p.y, 0, p.y - b.y1),
  Math.max(b.z0 - p.z, 0, p.z - b.z1));

// THE TUBE CHECK: every point of a path, and every point 0.5 mm apart along
// each of its legs, against every ring solid; what comes nearer one than the
// cord's radius is a clip. Returns the clips and how many samples it read.
function clips(points, rings, r = r15) {
  const out = [];
  let read = 0, closest = Infinity;
  for (let k = 1; k < points.length; k++) {
    const p = points[k - 1], q = points[k];
    const n = Math.max(1, Math.ceil(Math.hypot(q.x - p.x, q.y - p.y, q.z - p.z) / 0.5));
    for (let j = 0; j <= n; j++) {
      const t = j / n, at = {x: p.x + (q.x - p.x) * t, y: p.y + (q.y - p.y) * t, z: p.z + (q.z - p.z) * t};
      read++;
      for (const s of rings) {
        const d = dist(at, s.box);
        closest = Math.min(closest, d);
        if (d < r - 1e-6) out.push({part: s.part, leg: [p.at ?? p.via, q.at ?? q.via], d});
      }
    }
  }
  return {out, read, closest};
}

// The catalogue without its rings' solids: what the kit routed before #968.
const withoutRingSolids = ctx => ({...ctx, chassisOf: ref => {
  const c = ctx.chassisOf(ref);
  return c?.solids ? {...c, solids: c.solids.filter(s => !isRing(s))} : c;
}});

test('each ring is five solids, named, round the opening the catalogue places', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  const rings = S.solidsOf(r, ctx).filter(isRing);
  assert.equal(rings.length, 25);
  const [t] = S.traysOf(r, ctx);
  for (const o of t.rings) {
    const parts = Object.fromEntries(rings.filter(s => s.part.startsWith(`ring/${o.via}/`))
      .map(s => [s.part.split('/')[2], s.box]));
    assert.deepEqual(Object.keys(parts).sort(), ['bar', 'front-leg', 'hook', 'rear-leg', 'seat'], o.via);
    // every part is the band along the run, as thick as the opening is long
    for (const b of Object.values(parts)) { near(b.x0, o.box.x0, `${o.via} x0`); near(b.x1, o.box.x1, `${o.via} x1`); }
    // the legs close the opening across the run, 5.8 thick (guide.wall); the
    // rear leg, nearer the rail, the full 41 of the loop (guide.height)
    near(parts['rear-leg'].z1, o.box.z0, 'rear leg meets the opening'); near(parts['rear-leg'].z0, o.box.z0 - 5.8, 'rear leg wall');
    near(parts['front-leg'].z0, o.box.z1, 'front leg meets the opening'); near(parts['front-leg'].z1, o.box.z1 + 5.8, 'front leg wall');
    near(parts['rear-leg'].y0, BASE, 'rear leg foot'); near(parts['rear-leg'].y1, BASE + 41, 'rear leg top');
    // the front leg stops at the slit, 28.6, and the hook comes down to 30.8
    near(parts['front-leg'].y1, BASE + 28.6, 'front leg top'); near(parts['hook'].y0, BASE + 30.8, 'hook foot');
    near(parts['hook'].y1, BASE + 41, 'hook top');
    // the seat under the opening up to the sill, the bar over it from its top
    near(parts.seat.y0, BASE, 'seat foot'); near(parts.seat.y1, o.box.y0, 'seat is the sill');
    near(parts.bar.y0, o.box.y1, 'bar over the opening'); near(parts.bar.y1, BASE + 41, 'bar top');
    for (const k of ['seat', 'bar']) { near(parts[k].z0, o.box.z0, `${k} z0`); near(parts[k].z1, o.box.z1, `${k} z1`); }
  }
});

test('the owner\'s rack: no point of any cord comes within its radius of a ring', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  const rings = S.solidsOf(r, ctx).filter(isRing);
  assert.equal(rings.length, 25);
  let read = 0, closest = Infinity;
  for (const c of r.cables) {
    const p = R.routePath(r, c, ctx);
    const got = clips(p.points, rings);
    assert.deepEqual(got.out, [], c.id);
    read += got.read; closest = Math.min(closest, got.closest);
    assert.deepEqual(p.crossings, [], c.id);
  }
  // it looked, all along every cord; and the nearest any comes is the
  // radius itself, a cord lying on the sill against the rear leg
  assert.ok(read > 9000, `${read} samples`);
  near(closest, r15, 'nearest approach');
});

test('without the ring solids the same check finds cords in the rings', () => {
  // the check is not vacuous: with a catalogue whose rings are open, the
  // approach points alone still take thirteen cords in through the opening,
  // but c1, c2 and c7, whose ring stands past their port, come down to it
  // from behind and above and run through its rear leg and bar, as every
  // upper cord did before #968
  const r = F.rack(), ctx = F.ctxOf(r);
  const rings = S.solidsOf(r, ctx).filter(isRing);
  const open = withoutRingSolids(ctx);
  assert.equal(S.solidsOf(r, open).filter(isRing).length, 0);
  const hit = r.cables.filter(c => clips(R.routePath(r, c, open).points, rings).out.length).map(c => c.id);
  assert.deepEqual(hit, ['c1', 'c2', 'c7']);
  const parts = new Set(r.cables.flatMap(c => clips(R.routePath(r, c, open).points, rings).out.map(x => x.part.split('/')[2])));
  assert.ok(parts.has('rear-leg'), [...parts].join());
});

// THE APPROACH. Every pass through a ring whose opening is placed comes from
// a point on the run outside the band, clear of it by the cord's radius and
// CLEAR, at the opening's height and across position, and leaves to another
// past its far face; no detour ends at the ring or inside its band.
function approachFaults(p, t, r = r15) {
  const faults = [];
  let passes = 0;
  const pts = p.points;
  pts.forEach((q, k) => {
    if (q.at !== 'entry') return;
    passes++;
    const o = t.rings.find(x => x.via === q.via), run = o.run === 'z' ? 'z' : 'x';
    const exit = pts[k + 1], before = pts[k - 1], after = pts[k + 2];
    for (const [ap, face, what] of [[before, q, 'in'], [after, exit, 'out']]) {
      const ok = ap?.at === 'approach' && ap.via === q.via
        && Math.abs(Math.abs(ap[run] - face[run]) - (r + S.CLEAR)) < 1e-6
        && Math.abs(ap.y - face.y) < 1e-9 && ['x', 'z'].filter(a => a !== run).every(a => Math.abs(ap[a] - face[a]) < 1e-9)
        && (ap[run] < o.box[`${run}0`] || ap[run] > o.box[`${run}1`]);
      if (!ok) faults.push(`${q.via} ${what}`);
    }
  });
  // no detour point level with a ring (between its foot and its top, by
  // the radius) and inside its band along the run, grown by the radius: a
  // detour that ends there sends the cord into the ring's face, through a
  // leg, where it should end level with the approach point
  for (const d of p.detours) for (const q of d.points) {
    for (const o of t.rings) {
      const run = o.run === 'z' ? 'z' : 'x';
      const level = q.y > BASE - r && q.y < BASE + 41 + r;
      if (level && q[run] > o.box[`${run}0`] - r - 1e-9 && q[run] < o.box[`${run}1`] + r + 1e-9) faults.push(`detour at ${o.via}`);
    }
  }
  return {faults, passes};
}

test('every ring is entered from an approach point, and no detour ends at the ring', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  const [t] = S.traysOf(r, ctx);
  let passes = 0, detoured = 0;
  for (const c of r.cables) {
    const p = R.routePath(r, c, ctx);
    const got = approachFaults(p, t);
    assert.deepEqual(got.faults, [], c.id);
    passes += got.passes;
    detoured += p.detours.length;
    // the leg into the approach point is where a detour ends: the lower
    // leaf's round the tray's front edge, straight in front of it
    const ap = p.points.find(q => q.at === 'approach');
    for (const d of p.detours) assert.equal(d.points.at(-1).x, ap.x, c.id);
  }
  assert.equal(passes, 16);
  assert.equal(detoured, 13);
});

test('a detour that ends at the ring\'s centre, or its face, is a fault', () => {
  // the check, on c9's path with its detour moved to end straight in front
  // of ring 3's centre (0), as 0.12 drew it, and at its face (3.4), as 0.14
  // did: both fault, and the path as routed does not
  const r = F.rack(), ctx = F.ctxOf(r);
  const [t] = S.traysOf(r, ctx);
  const p = R.routePath(r, r.cables.find(c => c.id === 'c9'), ctx);
  assert.deepEqual(approachFaults(p, t).faults, []);
  for (const x of [0, 3.4]) {
    const moved = {...p, detours: p.detours.map(d => ({...d, points: d.points.map((q, i) => (i === d.points.length - 1 ? {...q, x} : q))}))};
    assert.deepEqual(approachFaults(moved, t).faults, ['detour at guide-3'], `ends at x ${x}`);
  }
  // and a pass with no approach point, the entry reached straight from the
  // detour, faults on its way in
  const bare = {...p, points: p.points.filter((q, k) => !(q.at === 'approach' && p.points[k + 1]?.at === 'entry'))};
  assert.deepEqual(approachFaults(bare, t).faults, ['guide-3 in']);
});

test('a leg that grazes a ring crosses it, and the finding names the part', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  const solids = S.solidsOf(r, ctx);
  const leg = S.solidsOf(r, ctx).find(s => s.part === 'ring/guide-3/front-leg').box;
  // a cord running along x 1 mm in front of the front leg, at its mid-height:
  // its centre line is outside the leg, its tube is not
  const y = (leg.y0 + leg.y1) / 2, z = leg.z1 + 1;
  const hit = S.legCrossings({x: -30, y, z}, {x: 30, y, z}, solids, {diameter: 3});
  assert.deepEqual(hit.map(h => h.solid.part), ['ring/guide-3/front-leg']);
  // the same leg at the radius off it touches and does not cross
  assert.deepEqual(S.legCrossings({x: -30, y, z: leg.z1 + r15}, {x: 30, y, z: leg.z1 + r15}, solids, {diameter: 3}), []);
  // and a plate is still met by the centre line: a cord lying on the floor
  // in front of the rings crosses nothing
  const top = 40 * RU + 3.0;
  assert.deepEqual(S.legCrossings({x: -150, y: top + 1, z: 60}, {x: 150, y: top + 1, z: 60}, solids, {diameter: 3}), []);
  // a leg that ends inside a ring cannot be gone round, and its finding
  // names the part: c9 with its panel end's plug reaching 107 mm out at x 0,
  // into ring 3's front leg (104.2 to 110 out, up to 28.6 over the floor)
  const c = r.cables.find(x => x.id === 'c9');
  const into = {...ctx, portX: e => (e.item === 'i2' ? 0 : ctx.portX(e)), plugReachOf: e => (e.item === 'i2' ? 107 : null)};
  const f = R.bodyFindings({...r, cables: [c]}, into).filter(x => x.part === 'ring/guide-3/front-leg');
  assert.ok(f.length >= 1, JSON.stringify(R.bodyFindings({...r, cables: [c]}, into).map(x => x.part)));
  assert.match(f[0].text, /^c9 passes through i4 ring 3 front leg (at|between) .*: route it into the ring along its run, through its opening\.$/);
});

test('a ring a route would double back at is gone to as far as its approach point', () => {
  // the cross-connect of rack-route-direct.mjs: bay 3 lc2 (34.86) to lc5
  // (73.89) on the panel behind the lacer, through ring 3 (-3.4 to 3.4),
  // which neither port is past, so it is a finding and the cord is taken to
  // the ring's face and back. The face it is taken to is ring 3's near face,
  // 3.4; the path's point stands 6.5 mm (its radius and CLEAR) further out,
  // and no point of the cord comes within its radius of the ring
  const r0 = F.rack();
  const x = {id: 'x1', a: {item: 'i2', path: 'bay-3/module/lc2', view: 'front'}, b: {item: 'i2', path: 'bay-3/module/lc5', view: 'front'},
    media: 'om4', route: []};
  const r = {...r0, cables: [x]}, ctx = F.ctxOf(r);
  const p = R.routePath(r, x, ctx);
  const [g] = p.rings;
  assert.deepEqual([g.via, g.passed], ['guide-3', false]);
  near(g.face.x, 3.4, 'the ring\'s own face');
  const face = p.points.find(q => q.at === 'face');
  near(face.x, 3.4 + r15 + S.CLEAR, 'the path stops at the approach point');
  assert.deepEqual(clips(p.points, S.solidsOf(r, ctx).filter(isRing)).out, []);
  assert.deepEqual(R.ringFindings(r, ctx).map(f => f.via), ['guide-3']);
});
