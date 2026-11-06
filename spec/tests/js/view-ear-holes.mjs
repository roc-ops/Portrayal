// WHICH RAIL HOLES AN EAR IS SCREWED AT (kit/rack/view/ear-holes.js). Where a body
// is in the units its item fills is the kit's (rack/fit.js itemBox), and so are
// the rail holes an ear can use (rack/rails.js holesIn); ear-holes.js holds the
// one small rule over them. The two cases of portrayal-site's
// tests/rack/half-unit.test.mjs (5dbbd41bd3) that read it, moved with it; the
// others read the page and the 3D scene, which stay in the site. Reads the real
// build (library/dist) for the catalogue.
import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
import {test, finish} from './view-cases.mjs';
import {earHoles} from '../../../kit/rack/view/ear-holes.js';
import {RU, HOLE_DY, holesIn} from '../../../kit/rack/rails.js';
import * as F from '../../../kit/rack/fit.js';
import {newRack} from '../../../kit/rack/model.js';

const DIST = new URL('../../../library/dist/', import.meta.url);
assert.ok(existsSync(new URL('rack.json', DIST)), 'no library/dist: run ./build.sh first (the suite reads the build)');
const devices = JSON.parse(readFileSync(new URL('rack.json', DIST), 'utf8')).devices;
const chassisOf = ref => devices[ref] ?? null;
const item = (id, ref, ru, extra = {}) => ({id, ref, cfg: 'base', label: id, ru, face: 'front', turned: false, swaps: {}, fields: {}, ...extra});
const near = (a, b, what) => assert.ok(Math.abs(a - b) < 1e-9, `${what}: ${a}, expected ${b}`);

test('two half-unit panels in one unit: each centred in its own half, one hole each, and the unit\'s two outer holes between them', () => {
  const rack = {...newRack(), items: [item('lo', 'xcu', 12), item('hi', 'xcu', 12.5)]};
  const [a, b] = rack.items.map(i => F.itemBox(rack, i, chassisOf));
  near(a.lo, 11 * RU, 'lower half starts at the bottom of U12');
  near(a.hi, 11.5 * RU, 'and ends at its middle');
  near(b.lo, 11.5 * RU, 'upper half starts at the middle');
  near(b.hi, 12 * RU, 'and ends at the top of U12');
  for (const box of [a, b]) {
    near((box.y0 + box.y1) / 2, (box.lo + box.hi) / 2, 'the body is centred in its half');
    near(box.h, 22.2, 'at the catalogue height');
    assert.ok(box.y0 >= box.lo && box.y1 <= box.hi, 'inside its half');
  }
  assert.ok(a.y1 <= b.y0, 'the two bodies do not overlap');
  const ha = earHoles(a.lo, a.hi), hb = earHoles(b.lo, b.hi);
  assert.equal(ha.length, 1);
  assert.equal(hb.length, 1);
  near(ha[0], 11 * RU + HOLE_DY[0], 'the lower half meets the unit\'s first hole');
  near(hb[0], 11 * RU + HOLE_DY[2], 'the upper half meets its last');
  // both fit, and a third is refused in either half with the kit's "Taken by"
  for (const i of rack.items) assert.deepEqual(F.fits(rack, i, chassisOf, {ignoreId: i.id}), {ok: true});
  assert.equal(F.fits(rack, {ref: 'xcu', face: 'front', ru: 12.5}, chassisOf).reason, 'Taken by hi on the front.');
  assert.equal(F.fits(rack, {ref: 'xcu', face: 'front', ru: 12}, chassisOf).reason, 'Taken by lo on the front.');
  // the two take one unit between them, as the page's summary counts
  assert.equal(F.itemsWithU(rack, chassisOf).reduce((n, i) => n + i.u, 0), 1);
});

test('an ear\'s screws: two a unit for whole units, one for a half, the middle hole empty where both others are in', () => {
  const ys = (lo, hi) => earHoles(lo * RU, hi * RU).map(y => Math.round(y * 100) / 100);
  assert.deepEqual(ys(0, 1), [6.35, 38.1]);
  assert.deepEqual(ys(0, 2), [6.35, 38.1, 50.8, 82.55]);
  assert.deepEqual(ys(0, 0.5), [6.35]);
  assert.deepEqual(ys(0.5, 1), [38.1]);
  assert.deepEqual(ys(0, 1.5), [6.35, 38.1, 50.8]);        // a 1.5U device at a whole unit: 3 an ear, the 6 the BOM counts
  assert.deepEqual(ys(0.5, 2), [38.1, 50.8, 82.55]);       // and started on a half
  // every screw is a hole the kit gives that span, and over the whole catalogue an ear has 2 x units of them
  for (const [name, c] of Object.entries(devices)) {
    const u = F.unitsOf(c);
    for (const ru of Number.isInteger(u) ? [1, 7] : [1, 7, 7.5]) {
      const box = F.itemBox(null, item('x', name, ru), chassisOf), got = earHoles(box.lo, box.hi);
      assert.equal(got.length, 2 * u, `${name} at ${ru}: ${got.length} screws an ear for ${u}U`);
      for (const y of got) assert.ok(holesIn(box.lo, box.hi).includes(y), `${name}: ${y} is not a hole of its span`);
    }
  }
});

await finish();
