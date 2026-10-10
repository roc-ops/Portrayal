// The corners of each cord's routed path that have less room than the cord's
// installed bend radius, counted by what made the corner (#973). Not a test
// file: rack-bend-room.mjs imports `tightCorners`, and run on its own it
// prints the count for the owner's cable-lay rack (route-direct-fixture.mjs),
// so a change to how routes are laid is measured the same way before and
// after:
//
//   node spec/tests/js/bend-corners-probe.mjs [--list]
//
// THE MEASURE is the kit's own (route-path.js cornersOf, the room the bundle
// bend check gives a corner): a point of the path is a corner when the path
// turns there by more than STRAIGHT_DEG, and its room is the largest bend its
// two legs leave it. A corner is tight when its room is less than the cord's
// installed bend radius (resting.js bendOf: the page's `ctx.bendOf`, else its
// media's). A leg between two corners is shared between them, and the count
// is given both ways: `half`, each corner taking half the leg (the bundle
// check's rule, and the only one before #973), and `need`, the leg shared by
// what each corner's turn uses of it (what routePath's `bends` reports).
//
// ON A REVISION BEFORE #973 this file does not run as it is: cornersOf was in
// bundles.js and had no `share`. The `before` figures (86 by halves, 87 by
// need) were measured by bend-room-sample.mjs --base <dir>, which lays the
// owner's rack with that revision's kit and counts its paths with this
// revision's cornersOf.
//
// THE CAUSE is read off the path's own labels (route.js routePath `at`):
//   rest      a sample of a free span as it hangs or lands;
//   approach  an approach point of a ring, its entry, its exit or its face;
//   detour    a point taken round a body;
//   other     a port, a plug's reach point, a lead point, a lane, a tray's stretch.
import {pathToFileURL} from 'node:url';
import * as R from '../../../kit/rack/route.js';
import {cornersOf} from '../../../kit/rack/route-path.js';
import {bendOf} from '../../../kit/rack/resting.js';

export const CAUSES = ['rest', 'approach', 'detour', 'other'];
const causeOf = at => (at === 'rest' ? 'rest' : at === 'detour' ? 'detour'
  : ['approach', 'entry', 'exit', 'face'].includes(at) ? 'approach' : 'other');

// Every tight corner of every cable of a rack: [{cable, k, at, cause,
// angle_deg, legs_mm, room_mm, need_mm}], `k` the index of the point.
export function tightCorners(rack, ctx, share = 'need') {
  const out = [];
  for (const c of rack.cables || []) {
    const path = R.routePath(rack, c, ctx);
    if (!path) continue;
    const need = bendOf(c, ctx);
    for (const x of cornersOf(path.points, {share})) {
      if (x.room_mm >= need - 1e-9) continue;
      const at = path.points[x.k].at;
      out.push({cable: c.id, k: x.k, at, cause: causeOf(at), angle_deg: x.angle_deg, legs_mm: x.legs_mm,
        room_mm: x.room_mm, need_mm: need});
    }
  }
  return out;
}
export const byCause = list => Object.fromEntries(CAUSES.map(k => [k, list.filter(x => x.cause === k).length]));

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) {
  const F = await import('./route-direct-fixture.mjs');
  const r = F.rack(), ctx = F.ctxOf(r);
  const list = tightCorners(r, ctx, 'need'), half = tightCorners(r, ctx, 'half');
  console.log(`corners below the installed bend radius, a leg shared by need: ${list.length}`, byCause(list));
  console.log(`corners below the installed bend radius, a leg shared by halves: ${half.length}`, byCause(half));
  const per = {};
  for (const x of list) (per[x.cable] ||= []).push(x);
  for (const c of r.cables) {
    const l = R.routedLength(r, c, ctx);
    console.log(`${c.id.padEnd(4)} ${(per[c.id] || []).length} tight; ${(l.measured * 1000).toFixed(1)} mm, stock ${l.value} m`);
    if (process.argv.includes('--list')) for (const x of per[c.id] || [])
      console.log(`     #${x.k} ${x.at} ${x.angle_deg} deg, legs ${x.legs_mm.join(' / ')}, room ${x.room_mm} of ${x.need_mm}`);
  }
}
