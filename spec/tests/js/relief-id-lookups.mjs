// cablePoints finds the feature a point sits on by id, in the marker's own
// parent. It used to ask the parent's selector engine for every marker; it now
// reads one id map per parent. The answer must not change, so this runs the
// module as it is and again with that one lookup put back, over compiled faces
// of the library, and compares everything they return and say.
//
// There is no DOM here and no jsdom, so a face is read by a small parser into
// the few things cablePoints touches: tagName, attributes, dataset,
// parentElement, closest, querySelector(All) for `[a]`, `[a="v"]` and a list of
// them. extractRelief needs a browser's layout and is not run here; its lookup
// is the same map, and the browser run that compares it is in the pull request.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, readdirSync, mkdtempSync, writeFileSync, copyFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join, resolve, dirname} from 'node:path';
import {pathToFileURL, fileURLToPath} from 'node:url';

globalThis.location = {search: ''};
globalThis.fetch = async () => ({ok: true, text: async () => '<svg/>'});

const KIT = resolve(dirname(fileURLToPath(import.meta.url)), '../../../kit');
const DIST = resolve(KIT, '../library/dist');

// ---------------------------------------------------------------- the module
// "before" is relief.js with the host lookup written as it was
const src = readFileSync(join(KIT, 'relief.js'), 'utf8');
const NEW = 'host && host.querySelector ? featureOn(host, on) : null';
const OLD = 'host && host.querySelector ? host.querySelector(`[id="${on.replace(/"/g, \'\\\\"\')}"]`) : null';
assert.ok(src.includes(NEW), 'the lookup this test swaps out moved');
const dir = mkdtempSync(join(tmpdir(), 'relief-old-'));
for (const f of ['fields.js', 'states.js', 'displays.js', 'dist.js']) copyFileSync(join(KIT, f), join(dir, f));
writeFileSync(join(dir, 'relief.js'), src.replace(NEW, OLD));
const now = await import(pathToFileURL(join(KIT, 'relief.js')));
const before = await import(pathToFileURL(join(dir, 'relief.js')));

// ------------------------------------------------------------------ the DOM
const ENT = {'&quot;': '"', '&apos;': "'", '&lt;': '<', '&gt;': '>', '&amp;': '&'};
const unent = s => s.replace(/&(quot|apos|lt|gt|amp);/g, m => ENT[m]);
const camel = k => k.replace(/-([a-z])/g, (_, c) => c.toUpperCase());

class El {
  constructor(tagName, attrs, parentElement) {
    this.tagName = tagName;
    this.attrs = attrs;
    this.parentElement = parentElement;
    this.children = [];
    const get = (_, name) => {
      if (typeof name !== 'string') return undefined;
      const k = Object.keys(this.attrs).find(a => a.startsWith('data-') && camel(a.slice(5)) === name);
      return k === undefined ? undefined : this.attrs[k];
    };
    this.dataset = new Proxy({}, {get});
  }
  get id() { return this.attrs.id ?? ''; }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  hasAttribute(k) { return k in this.attrs; }
  *descendants() { for (const c of this.children) { yield c; yield* c.descendants(); } }
  querySelectorAll(sel) {
    const alts = sel.split(',').map(s => s.trim()).map(matcher);
    return [...this.descendants()].filter(n => alts.some(a => a(n)));
  }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
  closest(sel) {
    const m = matcher(sel);
    for (let n = this; n; n = n.parentElement) if (m(n)) return n;
    return null;
  }
}

function matcher(s) {
  const parts = [...s.matchAll(/\[([\w-]+)(?:="((?:[^"\\]|\\.)*)")?\]/g)];
  if (!parts.length || parts.map(p => p[0]).join('') !== s) throw new Error('selector ' + s);
  return n => parts.every(([, k, v]) =>
    v === undefined ? n.hasAttribute(k) : n.getAttribute(k) === v.replace(/\\(.)/g, '$1'));
}

const TOKEN = /<!--[\s\S]*?-->|<\?[\s\S]*?\?>|<!\[CDATA\[[\s\S]*?\]\]>|<!DOCTYPE[^>]*>|<\/([^\s>]+)\s*>|<([^\s\/>]+)((?:\s+[^\s=\/>]+(?:\s*=\s*(?:"[^"]*"|'[^']*'))?)*)\s*(\/?)>/g;
const ATTR = /([^\s=\/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'))?/g;

function parse(text) {
  let root = null, cur = null;
  for (const m of text.matchAll(TOKEN)) {
    if (m[1] !== undefined) { cur = cur && cur.parentElement; continue; }
    if (m[2] === undefined) continue;
    const attrs = {};
    for (const a of m[3].matchAll(ATTR)) attrs[a[1]] = unent(a[2] ?? a[3] ?? '');
    const el = new El(m[2], attrs, cur);
    if (cur) cur.children.push(el); else root = el;
    if (!m[4]) cur = el;
  }
  return root;
}

// ------------------------------------------------------------------ faces
// every compiled face of a device: <dist>/<model>.<configuration>.<view>.svg
function faces(model) {
  return readdirSync(DIST).filter(f => f.startsWith(model + '.') && f.endsWith('.svg'))
    .sort().map(f => join(DIST, f));
}

// the parts of the cable-manager and GPU work, and two large switches
const DEVICES = ['cmh-sfd1u', 'cmh-uhd-sfdabs1u', 'cmh-uhd-sfdabs2u', 'cmh-uhd-sfdabs3u', 'cmh-hd-sfdabs3u',
      'cmh-hd-sfdabs4u', 'cmv-sfd42u9w', 'cmv-sfd45u5w', 'cmv-sfds45u5w', 'cmv-dfd45u5w',
      'cmv-5u3w', 'fs-cfs-1u', 'fhd-cmp5dr',
      'r660', 'r740xd', 'sys-111e-fdwtr', 'sys-111e-fwtr',
      's7801-54xs', 'as7326-56x', 'as5912-54x'];

// what a run returns and says, with each element named by where it sits
function run(mod, svg) {
  const at = new Map([svg, ...svg.descendants()].map((n, i) => [n, i]));
  const warned = [];
  const warn = console.warn;
  console.warn = (...a) => warned.push(a.join(' '));
  let points;
  try { points = mod.cablePoints(svg); } finally { console.warn = warn; }
  return {points: points.map(p => ({...p, el: at.get(p.el)})), warned};
}

function same(svg, what) {
  const a = run(before, svg), b = run(now, svg);
  assert.deepStrictEqual(b, a, what);
  return b;
}

// A face carries no cable marker of its own: a plug does, and a plug is seated
// on a port as a group of its own, which the build draws beside the face's
// other top-level groups. So each top-level path of a face gets one real plug
// skin seated on it, `data-for` its port, as a seated occupant is. The skins
// repeat their ids from port to port, which is the case the scope is for.
const PLUGS = ['generic--lc-duplex-plug--v2', 'generic--mpo12-plug--v1', 'generic--rj45-plug--v1',
               'generic--qsfp-dd-cable--v1', 'generic--c13-plug--v1', 'generic--lc-plug--v2',
               'common--lc-boot--v1', 'generic--sfp-cable--v1']
  .map(n => parse(readFileSync(join(DIST, 'components', `${n}--default.svg`), 'utf8')));

function adopt(el, parent) {
  const c = new El(el.tagName, {...el.attrs}, parent);
  parent.children.push(c);
  for (const k of el.children) adopt(k, c);
  return c;
}

function seatPlugs(svg) {
  const ports = svg.children.filter(c => c.attrs['data-path'] && !c.attrs['data-projection']);
  ports.forEach((port, i) => {
    const path = port.attrs['data-path'] + '-occupant';
    const seat = new El('g', {id: path, 'data-path': path, 'data-for': port.attrs['data-path'],
                              'data-z-lift': String(i % 3 * 2.5)}, svg);
    svg.children.push(seat);
    for (const k of PLUGS[i % PLUGS.length].children) adopt(k, seat);
  });
  return ports.length;
}

let ranFaces = 0, withCpOn = 0, points = 0, seated = 0, mostPorts = 0;
for (const model of DEVICES) {
  test(`${model}: every face gives the same cable points, bare and with plugs seated`, () => {
    const files = faces(model);
    assert.ok(files.length, `no compiled face for ${model}: build first`);
    for (const f of files) {
      same(parse(readFileSync(f, 'utf8')), f);
      const svg = parse(readFileSync(f, 'utf8'));
      const n = seatPlugs(svg);
      const out = same(svg, `${f} with ${n} plugs`);
      ranFaces++;
      seated += n;
      mostPorts = Math.max(mostPorts, n);
      points += out.points.length;
      if (svg.querySelector('[data-cp-on]')) withCpOn++;
    }
  });
}

test('the spread is not empty', () => {
  assert.ok(ranFaces >= DEVICES.length, `only ${ranFaces} faces ran`);
  assert.ok(points > 500, `only ${points} cable points compared`);
  assert.ok(mostPorts >= 53, `the largest face seated only ${mostPorts} plugs`);
  assert.ok(withCpOn > 0, 'no face carried a data-cp-on, so the lookup was never run');
});

// ---------------------------------------------------- an id twice in one scope
// The scope is the marker's own parent. Plant a feature twice inside it, once
// with the copy after and once with the copy before; the first in document
// order must win in both, and a copy outside the parent must not be seen.
function planted(where) {
  const svg = parse(`<svg>
    <g id="far"><g id="f" data-z-out="99"/></g>
    <g id="host">${where === 'after'
      ? '<g id="f" data-z-out="10"/><g id="f" data-z-out="20"/>'
      : '<g id="f" data-z-out="10"/><g><g id="f" data-z-out="20"/></g>'}
      <g id="cp" data-path="p" data-cp="cable" data-cp-at="1 2" data-cp-on="f"/>
      <g id="cq" data-path="q" data-cp="cable" data-cp-at="3 4" data-cp-on="f"/>
    </g></svg>`);
  return svg;
}
for (const where of ['after', 'nested']) {
  test(`an id twice inside one parent: the first in document order (${where})`, () => {
    const out = same(planted(where), where);
    // the first marker in the host asks the selector, the second reads the map
    assert.deepEqual(out.points.map(p => p.z), [10, 10]);
    assert.deepEqual(out.warned, []);
  });
}

test('a copy of the id outside the marker\'s parent is not seen', () => {
  const svg = parse(`<svg><g data-path="a"><g id="f" data-z-out="7"/></g>
    <g data-path="b"><g id="x"/><g data-path="b" data-cp="cable" data-cp-at="1 2" data-cp-on="f"/></g></svg>`);
  const out = same(svg, 'scoped');
  assert.equal(out.points[0].z, 0, 'the lookup left the parent');
  assert.ok(out.warned.some(w => w.includes('declares its cable point on "f"')), out.warned);
});

test('an id the parent does not hold gives the same warning and fallback', () => {
  const svg = parse(`<svg><g data-path="a"><g id="g"/><g data-path="a" data-cp="cable" data-cp-at="1 2" data-cp-on="nope"/></g></svg>`);
  const out = same(svg, 'missing');
  assert.equal(out.warned.length, 1);
});

test('a feature on a cylinder, an id with a quote, and one with a backslash', () => {
  const svg = parse(`<svg><g data-path="a" data-z-lift="3">
    <g id='q"x' data-z-cyl="30" data-z-lift="4"/><g id="b\\s" data-z-out="5"/>
    <g data-path="a" data-cp="cable" data-cp-at="1 2" data-cp-on='q"x'/>
    <g data-path="b" data-cp="cable" data-cp-at="1 2" data-cp-on="b\\s"/></g></svg>`);
  const out = same(svg, 'odd ids');
  assert.equal(out.points.find(p => p.path === 'a').z, 37);
});
