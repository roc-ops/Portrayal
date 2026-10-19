// spec/tests/js/rack-dfd1u-crossing.mjs
// THE CMH-DFD1U'S TWO MIDDLE HOLES (P-0021). The part's joined bases carry two
// pass-through holes, declared on both faces under each duct's cover (a lid).
// rack.json therefore gives each floor the holes, and the kit lets a leg that
// runs front to rear inside a hole's span go straight through; with the holes
// closed the same cord is gone round the floor. Reads the build's rack.json,
// as the Rack Builder does.
import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
import * as R from '../../../kit/rack/route.js';
import * as S from '../../../kit/rack/solids.js';
import * as F from './cable-solids-fixture.mjs';

const BUILT = new URL('../../../library/dist/rack.json', import.meta.url);
const skip = existsSync(BUILT) ? false : 'library/dist not built - run ./build.sh';
const entry = skip ? null : JSON.parse(readFileSync(BUILT, 'utf8')).devices['cmh-dfd1u'];
const closed = entry && {...entry, solids: entry.solids.map(s => ({...s, holes: []}))};

// the reference fixture rack of #949 with the duct manager at U8, and a cord from the
// switch below to the switch above routed from its front duct to its rear
// duct, both laid at rack x `x` (the part's centre is rack x 0)
function rackWith(dev, x) {
  const sizes = {...F.SIZES, 'cmh-dfd1u': dev};
  const base = F.add(F.ownerRack(), 'cmh-dfd1u', 8, {label: 'dfd'});
  const dfd = base.items.at(-1).id;
  const c = F.cable('c1', F.end('i1', 'p140'), F.end('i4', 'p150', 'rear'), 'om4', {
    route: [{item: dfd, via: 'front-duct'}, {item: dfd, via: 'rear-duct'}], routeEdited: true});
  const guide = (via, face) => ({via, kind: 'duct', face, run: 'x', x});
  const ctx = F.ctxOf({guides: {[dfd]: [guide('front-duct', 'front'), guide('rear-duct', 'rear')]},
    ctx: {chassisOf: ref => sizes[ref] || null}});
  return {rack: {...base, cables: [c]}, ctx, dfd, c};
}
// the detours of the leg from the front duct to the rear duct
const between = (p, dfd) => p.detours.filter(d => d.between.length === 2 && d.between.every(w => w.item === dfd));
// the points from the front duct's waypoint to the rear duct's
const crossing = p => {
  const at = p.points.map((q, k) => (q.at === 'pathway' ? k : -1)).filter(k => k >= 0);
  return p.points.slice(at[0], at[1] + 1);
};
const length = pts => pts.slice(1).reduce((n, q, k) => n + Math.hypot(q.x - pts[k].x, q.y - pts[k].y, q.z - pts[k].z), 0);

test('the DFD1U\'s two floors each carry both holes, 76.4 x 24.7 at x 54.2 and 302.4', {skip}, () => {
  assert.equal(entry.solids.length, 2);
  for (const floor of entry.solids) {
    const boxes = new Set(floor.holes.map(h => `${h.box.x}:${h.box.w}:${h.box.h}`));
    assert.deepEqual([...boxes].sort(), ['302.4:76.4:24.7', '54.2:76.4:24.7']);
  }
});

test('a cord from the front duct to the rear duct laid over a hole goes straight through it, shorter than round the floor', {skip}, () => {
  const x = -124.1;                                    // the middle of the first hole, from the part's centre
  const open = rackWith(entry, x), shut = rackWith(closed, x);
  const through = R.routePath(open.rack, open.c, open.ctx), round = R.routePath(shut.rack, shut.c, shut.ctx);
  assert.deepEqual(through.crossings, []);
  assert.deepEqual(round.crossings, []);
  assert.deepEqual(between(through, open.dfd), [], 'no detour between the ducts');
  assert.ok(between(round, shut.dfd).length, 'without the holes the floor is gone round');
  const gain = length(crossing(round)) - length(crossing(through));
  assert.ok(gain > 40, `the way through is ${gain.toFixed(0)} mm shorter`);
  // and the same cord laid between the holes meets the solid and is gone round, holes or not
  const mid = rackWith(entry, 0);
  assert.ok(between(R.routePath(mid.rack, mid.c, mid.ctx), mid.dfd).length);
  // the way through is the hole's: its floors stand in the cord's way only outside it
  const floors = S.solidsOf(open.rack, open.ctx).filter(s => s.item === open.dfd);
  assert.equal(floors.length, 2);
  assert.ok(floors.every(f => f.holes.some(h => h.box.x0 < x && x < h.box.x1)));
});
