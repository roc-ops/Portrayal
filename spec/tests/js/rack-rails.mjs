import test from 'node:test';
import assert from 'node:assert/strict';
import * as R from '../../../kit/rack/rails.js';

test('square holes are EIA-310 cage-nut holes, 3/8 in', () => {
  assert.equal(R.HOLE_SQUARE, 9.5);
  assert.equal(R.HOLE_SIZE, R.HOLE_SQUARE);
});

test('a tapped hole is drawn round at about a 12-24 major diameter', () => {
  assert.equal(R.HOLE_ROUND, 5.5);
});

test('a hole sits inside its rail, clear of the U line', () => {
  for (const s of R.SIDES) {
    const inner = Math.abs(s.inner), outer = Math.abs(s.outer), hole = Math.abs(s.hole);
    assert.ok(hole - R.HOLE_SQUARE / 2 > inner, `${s.side}: hole crosses the inner edge`);
    assert.ok(hole + R.HOLE_SQUARE / 2 < outer, `${s.side}: hole crosses the outer edge`);
  }
  assert.ok(R.HOLE_DY[0] - R.HOLE_SQUARE / 2 > 0);
  assert.ok(R.HOLE_DY.at(-1) + R.HOLE_SQUARE / 2 < R.RU);
});

test('the right rail mirrors the left', () => {
  const [l, r] = R.SIDES;
  for (const k of ['inner', 'outer', 'hole', 'number']) assert.equal(l[k], -r[k]);
});
