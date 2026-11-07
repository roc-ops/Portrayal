// The view reads the library it is given and nothing shared (kit/rack/view/face.js,
// faces.js): each loader takes the library as `distAt`, a function from a path in
// a build to its URL, and what it remembers is kept per library. Two libraries
// are built here with flatDist, served by a stub fetch that answers by URL and
// keeps a log. Nothing needs a DOM parser, so the cases that draw a face with
// two libraries are on the page, spec/tests/browser/rack-view-2d.html.
import assert from 'node:assert/strict';
import {test, finish} from './view-cases.mjs';

// (kit/dist.js resolves a url against the page's location)
globalThis.location = new URL('http://localhost/rack.html');
const files = new Map();
const log = [];
globalThis.fetch = async url => {
  const u = String(url);
  log.push(u);
  if (!files.has(u)) return {ok: false, status: 404};
  const body = files.get(u);
  return {ok: true, status: 200, json: async () => JSON.parse(body), text: async () => body};
};
// A library: the files it serves, by path, under a base of its own.
const serve = (base, served) => { for (const [path, body] of Object.entries(served)) files.set(base + path, typeof body === 'string' ? body : JSON.stringify(body)); };
const asked = base => log.filter(u => u.startsWith(base));

const {flatDist, layeredDist, faceFile} = await import('../../../kit/dist.js');
const {components, loadSkin, configuredFace, earPlanFor} = await import('../../../kit/rack/view/face.js');
const {faceUrl} = await import('../../../kit/rack/view/faces.js');
const {genericEars} = await import('../../../kit/relief.js');

const part = skin => ({components: [{ns: 'a', name: 'sfp', major: 'v1', skins: [skin]}]});

test('components(distAt) returns each library\'s own list, fetched once per library', async () => {
  const [A, B] = ['http://lib.test/c1a/', 'http://lib.test/c1b/'];
  serve(A, {'components.json': part('default')});
  serve(B, {'components.json': part('matte')});
  const [a, b] = [flatDist(A), flatDist(B)];
  const first = await components(a), second = await components(b), third = await components(a);
  assert.equal(first[0].skins[0], 'default');
  assert.equal(second[0].skins[0], 'matte');
  assert.equal(third, first);
  assert.deepEqual([asked(A).length, asked(B).length], [1, 1]);
  assert.equal(log.filter(u => u.includes('assets/dist')).length, 0);
});

test('loadSkin(ref, distAt) reads each library\'s own skin, started together', async () => {
  const [A, B] = ['http://lib.test/s2a/', 'http://lib.test/s2b/'];
  serve(A, {'components.json': part('default'), 'components/a--sfp--v1--default.svg': '<svg id="A"/>'});
  serve(B, {'components.json': part('matte'), 'components/a--sfp--v1--matte.svg': '<svg id="B"/>'});
  const [ra, rb] = await Promise.all([loadSkin('a/sfp@1', flatDist(A)), loadSkin('a/sfp@1', flatDist(B))]);
  assert.equal(ra.text, '<svg id="A"/>');
  assert.equal(rb.text, '<svg id="B"/>');
  assert.equal(ra.comp.skins[0], 'default');
  assert.equal(rb.comp.skins[0], 'matte');
  assert.ok(log.includes(`${A}components/a--sfp--v1--default.svg`));
  assert.ok(log.includes(`${B}components/a--sfp--v1--matte.svg`));
});

test('faceUrl(distAt, ref, config, view) is distAt(file), for a distAt that is no prefix', async () => {
  const at = path => `https://cdn.test/${path.split('.')[0]}/${path}`;
  const index = {device: 'x3', default: 'c1', configs: [{name: 'c1', files: {front: 'x3.shared.front.svg'}}]};
  serve('https://cdn.test/x3/', {'x3.configs.json': index});
  const url = await faceUrl(at, 'x3', 'c1', 'front');
  assert.equal(url, at(faceFile(index, 'c1', 'front')));
  assert.equal(url, 'https://cdn.test/x3/x3.shared.front.svg');
  // a device the library has no index for falls back to the name it would have had
  assert.equal(await faceUrl(at, 'nodev', 'c1', 'rear'), 'https://cdn.test/nodev/nodev.c1.rear.svg');
});

test('earPlanFor(ref, cfg, distAt) is each library\'s own, without a DOM', async () => {
  const chassis = w => ({h: 44.45, w, d: 300});
  const lib = (base, w) => {
    serve(base, {'x.configs.json': {device: 'x', default: 'c1', chassis: chassis(w), configs: [{name: 'c1', files: {front: 'x.c1.front.svg'}}]},
                 'x.c1.front.svg': `<svg viewBox="0 0 ${w} 44.45"/>`});
    return flatDist(base);
  };
  const a = lib('http://lib.test/e4a/', 430), b = lib('http://lib.test/e4b/', 400);
  const first = await earPlanFor('x', 'c1', a), second = await earPlanFor('x', 'c1', b), third = await earPlanFor('x', 'c1', a);
  assert.deepEqual(first, genericEars(chassis(430), 430));
  assert.deepEqual(second, genericEars(chassis(400), 400));
  assert.deepEqual([first.w, first.flange], [430, 26.3]);
  assert.deepEqual([second.w, second.flange], [400, 41.3]);
  assert.deepEqual(third, first);
});

test('configuredFace(args, domDoc, distAt) asks each library for its own face, once', async () => {
  const [A, B] = ['http://lib.test/f5a/', 'http://lib.test/f5b/'];
  for (const base of [A, B]) serve(base, {'y.configs.json': {device: 'y', default: 'c1', configs: [{name: 'c1', files: {front: 'y.c1.front.svg'}}]}});
  const [a, b] = [flatDist(A), flatDist(B)];
  const args = {ref: 'y', cfg: 'c1', view: 'front'};
  const round = () => Promise.all([configuredFace(args, null, a), configuredFace(args, null, b)]);
  assert.deepEqual(await round(), [null, null]);
  for (const base of [A, B]) {
    assert.ok(log.includes(`${base}y.configs.json`), `${base} configs.json`);
    assert.equal(asked(base).filter(u => u.endsWith('y.c1.front.svg')).length, 1, `${base} face file`);
  }
  assert.equal(log.filter(u => u.includes('assets/dist')).length, 0);
  const before = log.length;
  assert.deepEqual(await round(), [null, null]);
  assert.equal(log.length, before, 'a second round asks for nothing');
});

test('a layered library is read whole: its parts, a skin and a face from the later root', async () => {
  const [A, B] = ['http://lib.test/l6a/', 'http://lib.test/l6b/'];
  serve(A, {'devices.json': {devices: [{name: 'x6'}]}, 'components.json': part('default')});
  serve(B, {'devices.json': {devices: [{name: 'y6'}]},
            'components.json': {components: [{ns: 'b', name: 'card', major: 'v2', skins: ['only']}]},
            'components/b--card--v2--only.svg': '<svg id="B-card"/>',
            'y6.configs.json': {device: 'y6', default: 'c1', configs: [{name: 'c1', files: {front: 'y6.shared.front.svg'}}]}});
  const at = layeredDist([A, B]);
  const url = faceUrl(at, 'y6', 'c1', 'front');          // asked before the library knows its roots
  assert.deepEqual((await components(at)).map(c => c.ns), ['a', 'b']);
  assert.equal((await loadSkin('b/card@2', at)).text, '<svg id="B-card"/>');
  assert.equal(await url, `${B}y6.shared.front.svg`);
});

await finish();
