import test from 'node:test';
import assert from 'node:assert/strict';
import {createHistory} from '../../../kit/rack/history.js';

test('undo and redo walk the steps in order; a new step clears redo', () => {
  const h = createHistory();
  h.record('a', 'b', 'one'); h.record('b', 'c', 'two');
  assert.deepEqual([h.canUndo, h.undoSummary, h.canRedo], [true, 'two', false]);
  assert.equal(h.undo().before, 'b');
  assert.equal(h.redoSummary, 'two');
  assert.equal(h.undo().before, 'a');
  assert.equal(h.undo(), null);
  assert.equal(h.redo().after, 'b');
  h.record('b', 'x', 'three');
  assert.equal(h.canRedo, false);
});

test('the oldest step goes past the cap; clear empties both ways', () => {
  const h = createHistory({cap: 2});
  h.record(1, 2, 'a'); h.record(2, 3, 'b'); h.record(3, 4, 'c');
  assert.equal(h.undo().summary, 'c');
  assert.equal(h.undo().summary, 'b');
  assert.equal(h.undo(), null);
  h.clear();
  assert.deepEqual([h.canUndo, h.canRedo], [false, false]);
});
