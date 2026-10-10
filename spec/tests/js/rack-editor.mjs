import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import {createRackEditor} from '../../../kit/rack/editor.js';

const SIZES = {'as7726-32x': {ru: 1, h: 43.5, d: 515, model: 'AS7726-32X', default: 'ac-f2b'},
               'fhd-cmp5dr': {ru: 1, h: 44, d: 110, mount: 'rack-face', model: 'FHD-CMP5DR', default: 'base'}};
const chassisOf = ref => SIZES[ref] || null;
const P = ru => ({op: 'place', ref: 'as7726-32x', face: 'front', ru});
const fresh = () => { const ed = createRackEditor({doc: M.newDoc(), chassisOf}); const evs = []; ed.on('change', e => evs.push(e)); return {ed, evs}; };

test('apply records a step, emits once, and carries its origin through undo and redo', () => {
  const {ed, evs} = fresh();
  ed.apply(P(10), {origin: 'agent'});
  assert.equal(ed.rack().items.length, 1);
  assert.deepEqual(evs.map(e => [e.cause, e.origin, e.step]), [['apply', 'agent', true]]);
  assert.equal(ed.undoSummary, 'Placed AS7726-32X at U10 on the front.');
  assert.deepEqual(ed.undo(), {summary: 'Placed AS7726-32X at U10 on the front.'});
  assert.equal(ed.rack().items.length, 0);
  ed.redo();
  assert.equal(ed.rack().items.length, 1);
  assert.deepEqual(evs.map(e => [e.cause, e.origin]), [['apply', 'agent'], ['undo', 'agent'], ['redo', 'agent']]);
});

test('an error or a no-op records, emits and changes nothing', () => {
  const {ed, evs} = fresh();
  const before = ed.getDoc();
  assert.ok(ed.apply([P(10), P(10)]).error);
  assert.ok(ed.apply({op: 'rename', name: 'Rack 1'}).noop);
  assert.equal(ed.getDoc(), before);
  assert.deepEqual([evs.length, ed.canUndo], [0, false]);
});

test('preview is apply without the commit', () => {
  const {ed, evs} = fresh();
  const r = ed.preview(P(10));
  assert.equal(r.rack.items.length, 1);
  assert.deepEqual([ed.rack().items.length, evs.length, ed.canUndo], [0, 0, false]);
});

test('dcim is not a step, and undo and redo keep the settings as they are now', () => {
  const {ed, evs} = fresh();
  ed.apply(P(10));
  ed.apply({op: 'dcim', site: 'dc1'});
  assert.equal(evs.at(-1).step, false);
  assert.equal(ed.undoSummary, 'Placed AS7726-32X at U10 on the front.');
  ed.undo();
  assert.deepEqual([ed.rack().items.length, ed.rack().dcim], [0, {site: 'dc1'}]);
  ed.redo();
  assert.deepEqual([ed.rack().items.length, ed.rack().dcim], [1, {site: 'dc1'}]);
});

test('loadDoc settles managers, returns the repairs, and clears history', () => {
  const {ed, evs} = fresh();
  ed.apply(P(10));
  const doc = M.newDoc();
  doc.racks[0].items = [{id: 'i1', ref: 'fhd-cmp5dr', cfg: 'base', label: 'mgr', ru: 5, face: 'front', turned: false, swaps: {}, fields: {}, on: 'i9', unit: 1}];
  const {findings} = ed.loadDoc(doc);
  assert.equal(findings.length, 1);
  assert.match(findings[0].text, /the device it was on is not in this rack/);
  assert.equal('on' in ed.rack().items[0], false);
  assert.deepEqual([ed.canUndo, ed.canRedo, evs.at(-1).cause], [false, false, 'load']);
});

test('replaceRack is one step with its summary', () => {
  const {ed} = fresh();
  ed.replaceRack({...ed.rack(), name: 'X'}, 'Dropped demarc.');
  assert.deepEqual([ed.rack().name, ed.undoSummary], ['X', 'Dropped demarc.']);
});

test('a system command is refused unless the system sends it', () => {
  const {ed, evs} = fresh();
  assert.deepEqual(ed.apply([P(10), {op: 'lengths.routed', routeCtx: {}}], {origin: 'agent'}),
                   {error: "lengths.routed is a system command, sent only by the caller with origin 'system'.", index: 1});
  assert.deepEqual([ed.rack().items.length, evs.length], [0, 0]);
  assert.equal(ed.apply({op: 'lengths.routed', routeCtx: {}}, {origin: 'system'}).noop, true);
});

test('a listener that throws neither undoes the edit nor stops the others', () => {
  const {ed, evs} = fresh();
  const errors = [], was = console.error;
  console.error = (...a) => errors.push(a);
  ed.on('change', () => { throw new Error('boom'); });
  const later = [];
  ed.on('change', e => later.push(e.cause));
  let res;
  try { res = ed.apply(P(10)); } finally { console.error = was; }
  assert.equal(res.step, true);
  assert.equal(ed.rack().items.length, 1);
  assert.deepEqual([evs.length, later, errors.length], [1, ['apply'], 1]);
});

test('a per-call ctx reaches the commands for apply and preview, and is not kept', async () => {
  const {COMMANDS} = await import('../../../kit/rack/commands.js');
  const seen = [];
  COMMANDS['test.spy'] = {run: (rack, _a, ctx) => { seen.push(ctx); return {rack: {...rack, name: `${rack.name}+`}, summary: 'Spied.', findings: []}; },
                          args: {type: 'object', additionalProperties: false, properties: {rack: {type: 'string'}}}};
  try {
    const {ed} = fresh();
    const slotsOf = () => null;
    ed.apply({op: 'test.spy'}, {origin: 'agent', ctx: {slotsOf}});
    ed.preview({op: 'test.spy'}, {ctx: {slotsOf, extra: 1}});
    ed.apply({op: 'test.spy'});
    ed.preview({op: 'test.spy'});
    assert.deepEqual(seen.map(c => [typeof c.chassisOf, typeof c.slotsOf, c.extra ?? null]),
      [['function', 'function', null], ['function', 'function', 1], ['function', 'undefined', null], ['function', 'undefined', null]]);
  } finally { delete COMMANDS['test.spy']; }
});
