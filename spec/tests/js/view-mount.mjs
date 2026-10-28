// kit/rack/view/view.js and mountRack2d, with a fake document: what they refuse
// and how they let go. Nothing here draws a device (the fake DOM has no SVG
// parser): the drawing is compared on the page, spec/tests/browser/rack-view-2d.html.
import assert from 'node:assert/strict';
import {test, finish} from './view-cases.mjs';
import {joinPath, splitPath} from '../../../kit/rack/view/view.js';
import {mountRack2d} from '../../../kit/rack/view/elevation.js';
import {newDoc, newRack} from '../../../kit/rack/model.js';

// ---- paths (docs/rack-views-design.md §2.4) ----------------------------------

const KEYS = ['item:i3', 'zeroU:z1', 'cable:c7', 'bundle:b2', 'tie:a|b|c', 'tie:i1|via 2|tie-3', 'u:12', 'u:12.5'];

test('joinPath and splitPath round-trip every kind of key, with and without a part path', () => {
  for (const key of KEYS) {
    assert.deepEqual(splitPath(joinPath(key)), {key, path: null}, key);
    for (const path of ['xc04/port-3', 'port-3', 'bay-1/module/p1']) {
      assert.equal(joinPath(key, path), `${key}/${path}`);
      assert.deepEqual(splitPath(joinPath(key, path)), {key, path}, `${key}/${path}`);
    }
  }
});

test('a key with a | and a position of 12.5 keep every character', () => {
  assert.deepEqual(splitPath('tie:a|b|c/port-1'), {key: 'tie:a|b|c', path: 'port-1'});
  assert.deepEqual(splitPath('u:12.5'), {key: 'u:12.5', path: null});
});

test('a text that is no path is refused in a sentence', () => {
  assert.throws(() => splitPath('xc04/port-3'), /not a path/);
  assert.throws(() => splitPath('rack:r1'), /not a path/);
});

// ---- a fake document: elements that can be made, appended, removed and counted ----

class El {
  constructor(tag) { this.tagName = tag; this.attrs = {}; this.children = []; this.parentNode = null; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  removeAttribute(k) { delete this.attrs[k]; }
  append(...kids) { for (const k of kids) { k.parentNode = this; this.children.push(k); } }
  remove() { const p = this.parentNode; if (p) { p.children.splice(p.children.indexOf(this), 1); this.parentNode = null; } }
  querySelectorAll() { return []; }
  contains(n) { for (let x = n; x; x = x.parentNode) if (x === this) return true; return false; }
}
const fakeDocument = () => ({defaultView: {}, createElementNS: (ns, tag) => new El(tag), createElement: tag => new El(tag)});
const fakeContainer = () => {
  const c = new El('div');
  c.added = []; c.removed = [];
  c.addEventListener = (type, fn) => c.added.push([type, fn]);
  c.removeEventListener = (type, fn) => c.removed.push([type, fn]);
  return c;
};
const twoRacks = () => {
  const doc = newDoc();
  const r2 = {...newRack(), id: 'r2', name: 'Rack 2'};
  r2.frame = {...r2.frame, heightRU: 10};
  return {...doc, racks: [{...doc.racks[0], frame: {...doc.racks[0].frame, heightRU: 20}}, r2]};
};
const viewBoxHeight = c => Number(c.children[0].getAttribute('viewBox').split(' ')[3]);

test('mountRack2d wants a document, and draws racks[0] without a rackId', async () => {
  assert.throws(() => mountRack2d(fakeContainer(), {doc: newDoc()}), /needs the document/);
  const c = fakeContainer();
  const view = mountRack2d(c, {document: fakeDocument(), doc: twoRacks()});
  await view.ready;
  assert.equal(c.children.length, 1);
  assert.equal(c.children[0].getAttribute('data-pane'), 'front');
  view.dispose();
});

test('racks[1] draws when rackId names it; an unknown id is refused naming it, for ready and for update', async () => {
  const doc = twoRacks();
  const first = fakeContainer(), second = fakeContainer();
  const a = mountRack2d(first, {document: fakeDocument(), doc});
  const b = mountRack2d(second, {document: fakeDocument(), doc, rackId: 'r2'});
  await Promise.all([a.ready, b.ready]);
  assert.notEqual(viewBoxHeight(first), viewBoxHeight(second), 'the second rack is a different height');
  const lost = mountRack2d(fakeContainer(), {document: fakeDocument(), doc, rackId: 'r9'});
  await assert.rejects(lost.ready, /There is no rack r9 in this document/);
  await assert.rejects(a.update(doc, {rackId: 'r9'}), /There is no rack r9 in this document/);
  // without a rackId the view keeps the rack it has, and that rack gone from the document is named
  await b.update(doc);
  await assert.rejects(b.update({...doc, racks: [doc.racks[0]]}), /There is no rack r2 in this document/);
  // a failed update leaves the drawing it had
  assert.equal(second.children.length, 1);
  for (const v of [a, b, lost]) v.dispose();
});

test('a backboard surface is refused with a sentence, and no other kind is added', () => {
  assert.throws(() => mountRack2d(fakeContainer(), {document: fakeDocument(), doc: newDoc(), surface: {kind: 'backboard', id: 'b1'}}),
    /backboard is not a surface a view can draw yet/);
  assert.throws(() => mountRack2d(fakeContainer(), {document: fakeDocument(), doc: newDoc(), surface: {kind: 'wall', id: 'w1'}}), /There is no "wall" surface/);
  assert.throws(() => mountRack2d(fakeContainer(), {document: fakeDocument(), doc: newDoc(), rackId: 'r1', surface: {kind: 'rack', id: 'r2'}}), /different racks/);
});

test('a second call to dispose does nothing, and the first removes the drawing and the listener it added', async () => {
  const c = fakeContainer();
  const view = mountRack2d(c, {document: fakeDocument(), doc: newDoc()});
  await view.ready;
  assert.equal(c.added.length, 1);
  assert.equal(c.children.length, 1);
  view.dispose();
  assert.equal(c.children.length, 0);
  assert.deepEqual(c.removed, c.added);
  view.dispose();
  assert.equal(c.removed.length, 1, 'the second call removed nothing');
  await assert.rejects(view.update(newDoc()), /disposed/);
});

test('on("pick") returns its own remover, and an unknown event name throws', () => {
  const c = fakeContainer();
  const view = mountRack2d(c, {document: fakeDocument(), doc: newDoc()});
  const off = view.on('pick', () => {});
  assert.equal(typeof off, 'function');
  assert.throws(() => view.on('hover', () => {}), /no "hover" event/);
  off();
  view.dispose();
});

await finish();
