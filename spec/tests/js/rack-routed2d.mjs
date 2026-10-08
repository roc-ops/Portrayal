import test from 'node:test';
import assert from 'node:assert/strict';
import {routed2d} from '../../../kit/rack/route-path.js';

test('routed2d: two points are one straight line', () => {
  assert.equal(routed2d([[0, 0], [10, 0]]), 'M0 0 L10 0');
});

test('routed2d: a corner is rounded by r, cut back along both legs', () => {
  assert.equal(routed2d([[0, 0], [10, 0], [10, 10]], 4), 'M0 0 L6 0 Q10 0 10 4 L10 10');
});

test('routed2d: a corner never cuts back more than half its leg', () => {
  assert.equal(routed2d([[0, 0], [2, 0], [2, 10]], 4), 'M0 0 L1 0 Q2 0 2 4 L2 10');
});

test('routed2d: a zero-length segment gives no NaN', () => {
  const d = routed2d([[0, 0], [0, 0], [10, 0]]);
  assert.ok(!/NaN/.test(d), d);
  assert.ok(d.startsWith('M0 0') && d.endsWith('L10 0'), d);
});
