// The same id on two views is two parts (#1002). A DIN rail panel's `left` and
// `right` views each place `screw-upper` and `screw-lower`, and each side
// bracket is `under` both. Selecting the right bracket must take the RIGHT
// screws off - in the drawing, in the tree's rows, and in the `pulled` event a
// 3D scene hides by - and leave the left view's screws, rows and event entries
// alone. A host that names no view keeps the behaviour it had.
//
// The shell is mounted over the stand-in page (fake-shell-dom.mjs) with the
// merged tree on, as 3D draws it: one section per view, so the id is listed twice.
import test from 'node:test';
import assert from 'node:assert/strict';
import { install } from './fake-shell-dom.mjs';

const under = 'screw-upper screw-lower';
const screw = id => ({attrs: {'data-path': id, 'data-class': 'screw', 'data-behaviour': 'mounts'}});
const face = (src, parts) => JSON.stringify({src, parts});
install({
  'devices.json': () => JSON.stringify({devices: [{name: 'rail', ns: 'fixture', model: 'RAIL'}]}),
  'components.json': () => JSON.stringify({components: []}),
  'rail.configs.json': () => JSON.stringify({
    device: 'rail', model: 'RAIL', default: 'base', views: ['front', 'left', 'right'],
    bays: {}, cages: {},
    configs: [{name: 'base', files: {front: 'f.svg', left: 'l.svg', right: 'r.svg'}}]}),
  'f.svg': () => face('front', [{attrs: {'data-path': 'chassis'}}]),
  'l.svg': () => face('left', [
    {attrs: {'data-path': 'side-left', 'data-class': 'side-bracket', 'data-under': under}},
    screw('screw-upper'), screw('screw-lower')]),
  'r.svg': () => face('right', [
    {attrs: {'data-path': 'side-right', 'data-class': 'side-bracket', 'data-under': under}},
    screw('screw-upper'), screw('screw-lower')]),
});
globalThis.location.search = '?device=rail&view=left';

const { createShell } = await import('../../../kit/shell.js');
const shell = createShell({dist: 'http://kit.test/dist'});
await shell.ready;
shell.state.merge = true;
await shell.loadFaces();
shell.refreshTree();

const plain = o => JSON.parse(JSON.stringify(o));
const events = [];
shell.on('pulled', e => events.push(plain(e)));
const part = (view, id) => shell.state.faces[view].querySelectorAll(`[data-path="${id}"]`)[0];
const off = (view, id) => part(view, id).hasAttribute('data-portrayal-pulled');
const rows = id => [...shell.el.tree.querySelectorAll('.node')].filter(r => r.dataset.path === id);
const rowOff = (view, id) => rows(id).find(r => r.dataset.view === view).classList.contains('pulled');
const reset = () => { shell.select(null, true); shell.setPulled(['screw-upper', 'screw-lower'], false, 'left');
                      shell.setPulled(['screw-upper', 'screw-lower'], false, 'right'); events.length = 0; };

test('the merged tree lists the id once for each view that places it', () => {
  assert.deepEqual(rows('screw-upper').map(r => r.dataset.view).sort(), ['left', 'right']);
  assert.deepEqual(rows('side-right').map(r => r.dataset.view), ['right']);
});

test('selecting the right bracket takes the right screws off and leaves the left', () => {
  reset();
  shell.select('side-right', true, 'right');
  for (const id of ['screw-upper', 'screw-lower']) {
    assert.equal(off('right', id), true, `right ${id}`);
    assert.equal(off('left', id), false, `left ${id}`);
    assert.equal(rowOff('right', id), true, `right ${id} row`);
    assert.equal(rowOff('left', id), false, `left ${id} row`);
  }
  assert.deepEqual(shell.pulledPaths('right'), ['screw-upper', 'screw-lower']);
  assert.deepEqual(shell.pulledPaths('left'), []);
});

test('the pulled event carries the view beside each path, and the paths stay bare ids', () => {
  reset();
  shell.select('side-right', true, 'right');
  const last = events.at(-1);
  assert.deepEqual(last.paths, ['screw-upper', 'screw-lower']);
  assert.deepEqual(last.views, ['right', 'right']);
  assert.deepEqual(shell.pulledViews(), ['right', 'right']);
  assert.deepEqual(shell.pulledPaths(), ['screw-upper', 'screw-lower']);
});

test('moving the selection to the left bracket puts the right screws back and takes the left off', () => {
  reset();
  shell.select('side-right', true, 'right');
  shell.select('side-left', true, 'left');
  for (const id of ['screw-upper', 'screw-lower']) {
    assert.equal(off('left', id), true, `left ${id}`);
    assert.equal(off('right', id), false, `right ${id}`);
    assert.equal(rowOff('left', id), true);
    assert.equal(rowOff('right', id), false);
  }
  assert.deepEqual(events.at(-1).views, ['left', 'left']);
  shell.select(null, true);
  assert.equal(off('left', 'screw-upper') || off('right', 'screw-upper'), false);
  assert.deepEqual(plain(events.at(-1)).paths, []);
});

test('a part on one view highlights one row, not the row under every view', () => {
  reset();
  shell.select('screw-upper', true, 'right');
  const lit = [...shell.el.tree.querySelectorAll('.node')].filter(r => r.classList.contains('sel'));
  assert.equal(lit.length, 1);
  assert.equal(lit[0].dataset.view, 'right');
  assert.equal(lit[0].dataset.path, 'screw-upper');
  // and the same part again, on the other view, moves the highlight rather than adding one
  shell.select('screw-upper', true, 'left');
  const again = [...shell.el.tree.querySelectorAll('.node')].filter(r => r.classList.contains('sel'));
  assert.deepEqual(again.map(r => r.dataset.view), ['left']);
});

test('a host that names no view keeps what it had', () => {
  reset();
  // a path only one view places is that view's, named or not
  shell.select('side-right', false);
  assert.equal(off('right', 'screw-upper'), true);
  assert.equal(off('left', 'screw-upper'), false);
  reset();
  // setPulled with no view takes the first face that draws the path, as it always did
  shell.setPulled(['screw-upper'], true);
  assert.equal(off('left', 'screw-upper'), true);
  assert.equal(off('right', 'screw-upper'), false);
  assert.deepEqual(events.at(-1).paths, ['screw-upper']);
  shell.setPulled(['screw-upper'], false);
  assert.equal(off('left', 'screw-upper'), false);
  assert.deepEqual(events.at(-1).paths, []);
});

test('setPulled takes one view for every path, or a list beside the paths', () => {
  reset();
  shell.setPulled(['screw-upper', 'screw-lower'], true, ['left', 'right']);
  assert.equal(off('left', 'screw-upper'), true);
  assert.equal(off('right', 'screw-lower'), true);
  assert.equal(off('right', 'screw-upper'), false);
  assert.equal(off('left', 'screw-lower'), false);
  assert.deepEqual(events.at(-1), {paths: ['screw-upper', 'screw-lower'], views: ['left', 'right']});
  // a view that does not draw the path leaves it alone
  reset();
  shell.setPulled(['side-left'], true, 'right');
  assert.equal(events.length, 0);
});

test('over names the covers of the part on its own view', () => {
  assert.deepEqual(shell.over('side-right', 'right'), ['screw-upper', 'screw-lower']);
  assert.deepEqual(shell.over('side-right'), ['screw-upper', 'screw-lower']);
});
