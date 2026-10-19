// A rack of the shape #1026 was measured on, for spec/tests/js/rack-ring-room.mjs
// and for the figures of docs/cable-lay-design.md section 3.5, so that they
// can be counted again. Not a test file: run on its own it prints the table
// for this tree, and beside another tree of the kit when one is given:
//
//   node spec/tests/js/ring-room-shape.mjs [--base <dir>] [--cables 43]
//
// `<dir>` is a copy of another revision that holds its `kit/rack` and its
// `spec/tests/js` fixtures, for example
//   git archive <rev> kit/rack spec/tests/js | tar -x -C <dir>
// The other tree lays THIS file's racks with its own kit.
//
// THE SHAPE. A four-post rack of 42 units with a vertical cable manager at
// each front upright, and thirteen switches of two units each, every one
// with an FHD-CMP5DR lacer hosted on it (on its top unit, on its bottom
// unit, or not at all) and set back from the rail by the same amount:
//   - two control switches, at U41 and U39;
//   - six edge routers, at U35, U33, U31, U19, U17 and U15, each with forty
//     fabric ports in two rows, both in its top unit;
//   - five fabric switches, at U29 to U21, each with sixty-four ports in
//     four rows, two in each unit.
// 275 cables: every edge router has eight fabric links to each fabric
// switch (240, AOC), and every edge router and fabric switch has two
// control links (AOC) and one management link (Cat 6) to the control
// switches, which have two links (AOC) between them.
// The rows and columns are where the library draws the ports of the
// UfiSpace S9710-76D, S9725-64E and S9601-102XC, to a tenth of a millimetre
// for the rows and evenly spaced across for the columns; the switches are
// plain boxes of those sizes, so each is its envelope. The lacer is the
// catalogue's (cable-solids-fixture.mjs), with its tray and its rings; the
// vertical manager is a duct of the size of the FS CMV-SFD42U9W, written
// by hand with no parts of its own. Nothing here is random.
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import {RU} from '../../../kit/rack/rails.js';
import {PLUG_REACH} from '../../../kit/rack/route.js';
import {CAT, RINGS} from './cable-solids-fixture.mjs';

export const SIZES = {
  edge: {ru: 2, w: 436, h: 87.7, d: 762, kind: 'router'},
  fabric: {ru: 2, w: 436, h: 87.7, d: 762, kind: 'router'},
  control: {ru: 2, w: 436, h: 87.7, d: 609.6, kind: 'router'},
  'fhd-cmp5dr': CAT['fhd-cmp5dr'],
  duct: {ru: 42, w: 88.9, h: 1866.9, d: 152.6, mount: 'rack-side', kind: 'cable manager', guides: {front: ['duct']}},
};
export const chassisOf = ref => SIZES[ref] || null;

// Where a port is on its device: [x from the centre line, mm above the
// bottom of the device's two units].
const even = (first, last, n, col) => first + (last - first) * col / (n - 1);
const pair = (n, rows) => rows[n % 2];
export function portOf(ref, path) {
  const [, name, num] = /^([a-z-]+?)-?(\d+)?$/.exec(path) || [];
  const n = Number(num);
  if (ref === 'edge') {
    if (name === 'fab') return [even(-185.6, 198.8, 20, Math.floor(n / 2)), pair(n, [72.5, 59.5])];
    if (name === 'sfp') return [-168.4, pair(n, [31.6, 16.7])];
    if (name === 'mgmt') return [-190.6, 35.9];
  }
  if (ref === 'fabric') {
    if (name === 'port') return [even(-148.1, 196.6, 16, Math.floor((n % 32) / 2)), pair(n, n < 32 ? [65.6, 51.0] : [30.6, 16.1])];
    if (name === 'ctl') return [-169.5, pair(n, [49.7, 32.4])];
    if (name === 'mgmt') return [-190.7, 34.8];
  }
  if (ref === 'control') {
    if (name === 'port') return [even(-167.2, 202.6, 26, Math.floor((n % 52) / 2)), pair(n, n < 52 ? [67.2, 51.8] : [37.2, 22.0])];
  }
  return null;
}

const end = (item, path) => ({item, path, view: 'front'});
// The thirteen switches, top down: [id, ref, label, U].
export const SWITCHES = [
  ['i1', 'control', 'CTL-A', 41], ['i2', 'control', 'CTL-B', 39],
  ['i3', 'edge', 'EDGE-0', 35], ['i4', 'edge', 'EDGE-1', 33], ['i5', 'edge', 'EDGE-2', 31],
  ['i6', 'fabric', 'FAB-0', 29], ['i7', 'fabric', 'FAB-1', 27], ['i8', 'fabric', 'FAB-2', 25], ['i9', 'fabric', 'FAB-3', 23], ['i10', 'fabric', 'FAB-4', 21],
  ['i11', 'edge', 'EDGE-3', 19], ['i12', 'edge', 'EDGE-4', 17], ['i13', 'edge', 'EDGE-5', 15],
];
const EDGES = SWITCHES.filter(s => s[1] === 'edge'), FABRICS = SWITCHES.filter(s => s[1] === 'fabric');

// The 275 cables, in order: the fabric links edge by edge, then the control
// and management links switch by switch, then the two between the control
// switches. The first 43 are EDGE-0's forty fabric links and its three to
// the control switches.
function cables() {
  const out = [], add = (a, b, media) => out.push({id: `c${out.length + 1}`, a, b, media, route: []});
  const links = (id, ref, k) => {
    const [up, mgmt] = ref === 'edge' ? ['sfp', 'mgmt'] : ['ctl', 'mgmt'];
    add(end(id, `${up}-0`), end('i1', `port-${k}`), 'aoc');
    add(end(id, `${up}-1`), end('i2', `port-${k}`), 'aoc');
    add(end(id, mgmt), end(k % 2 ? 'i1' : 'i2', `port-${60 + k}`), 'cat6');
  };
  const fabric = e => { for (let k = 0; k < 40; k++) add(end(EDGES[e][0], `fab-${k}`), end(FABRICS[Math.floor(k / 8)][0], `port-${e * 8 + k % 8}`), 'aoc'); };
  fabric(0);
  links(EDGES[0][0], 'edge', 0);
  for (let e = 1; e < EDGES.length; e++) fabric(e);
  [...EDGES.slice(1), ...FABRICS].forEach(([id, ref], k) => links(id, ref, k + 1));
  add(end('i1', 'port-96'), end('i2', 'port-96'), 'aoc');
  add(end('i1', 'port-97'), end('i2', 'port-97'), 'aoc');
  return out;
}

// The rack and its route context: `lacer` 'top', 'bottom' or 'none' (the
// unit of each switch its lacer is hosted on), `setback` mm (every switch),
// `count` how many of the 275 cables to keep, from the first.
// `rigid` true measures a DAC's or an AOC's plug as the kit does by default
// (#985: its 64.8 mm cannot bend, so a turn at its end has no leg in it); false,
// the default here, gives the reach as a number (`plugReachOf`), which the kit
// measures as a leg whole, as every plug was measured before #985. The figures
// of docs/cable-lay-design.md section 3.5 and the tests that count them are of
// that; the change of #985 is counted with `rigid: true`.
export function shape({lacer = 'top', setback = 0, count = 275, rigid = false} = {}) {
  const items = SWITCHES.map(([id, ref, label, ru]) => ({id, ref, cfg: 'base', label, ru, face: 'front', turned: false, swaps: {}, fields: {},
    ...(setback ? {setback} : {})}));
  if (lacer !== 'none') SWITCHES.forEach(([id, , label, ru], k) => {
    const unit = lacer === 'top' ? 2 : 1;
    items.push({id: `m${k + 1}`, ref: 'fhd-cmp5dr', cfg: 'base', label: `Lacer ${label}`, ru: ru + unit - 1, face: 'front', turned: false, swaps: {}, fields: {}, on: id, unit});
  });
  const rack = {id: 'r1', name: 'Ring room',
    frame: {kind: 'four-post', heightRU: 42, numbering: 'bottom-up', holes: {style: 'square', thread: null}, railDepth: 740, usableDepth: 1000, ref: null},
    items,
    zeroU: [{id: 'z1', ref: 'duct', cfg: 'base', label: 'Duct L', at: 'left-front', offsetMm: 0}, {id: 'z2', ref: 'duct', cfg: 'base', label: 'Duct R', at: 'right-front', offsetMm: 0}],
    cables: cables().slice(0, count)};
  const port = e => { const it = rack.items.find(i => i.id === e.item); const p = it && portOf(it.ref, e.path); return p ? {it, p} : null; };
  const byId = new Map(rack.cables.map(c => [c.id, c]));
  const ctx = Object.freeze({chassisOf,
    ...(rigid ? {} : {plugReachOf: (e, c) => PLUG_REACH[(c ?? byId.get(e?.cable))?.media] ?? null}),
    guidesOf: id => (rack.items.find(i => i.id === id)?.ref === 'fhd-cmp5dr' ? RINGS : []),
    portX: e => port(e)?.p[0] ?? null,
    // above the floor of U1: the bottom of the device's lowest unit, the gap a
    // body of 87.7 mm leaves in two units, and the port's height on the face
    portY: e => { const q = port(e); return q ? (q.it.ru - 1) * RU + (2 * RU - 87.7) / 2 + q.p[1] : null; }});
  return {rack, ctx, nameOf: id => rack.items.find(i => i.id === id)?.label ?? id};
}

// What a tree's kit finds on one of these racks: {findings, corners, cables,
// close, crossings, lengths}: the tight-bend findings, the corners they are
// of (a finding of two turns is two; before #1026 every corner was a
// finding), the cables that have one, how many of the findings say the
// manager is too close, the legs through a body, and each cable's routed
// length as [metres measured, stock size].
export function measure(R, {rack, ctx, nameOf}) {
  let findings = 0, corners = 0, close = 0, crossings = 0;
  const cables = new Set(), lengths = {};
  for (const c of rack.cables) {
    const path = R.routePath(rack, c, ctx);
    if (!path) continue;
    const found = R.bendFindingsOf(rack, c, ctx, nameOf, path);
    findings += found.length;
    corners += found.reduce((n, f) => n + (f.turns?.length ?? 1), 0);
    close += found.filter(f => f.tooClose).length;
    if (found.length) cables.add(c.id);
    crossings += path.crossings.length;
    const l = R.pathLength(path);
    lengths[c.id] = [l.measured, l.value];
  }
  return {findings, corners, cables: cables.size, close, crossings, lengths};
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) {
  const arg = name => { const i = process.argv.indexOf(name); return i > 0 ? process.argv[i + 1] : null; };
  const here = resolve(new URL('../../..', import.meta.url).pathname), baseDir = arg('--base') && resolve(arg('--base'));
  const count = Number(arg('--cables') ?? 275);
  const load = async root => import(pathToFileURL(`${root}/kit/rack/route.js`));
  const This = await load(here), Base = baseDir ? await load(baseDir) : null;
  console.log(`${count} cables; corners short of room / cables that have one${Base ? ', base then this tree' : ''}`);
  const moved = [];
  let up = 0, down = 0, same = 0;
  for (const lacer of ['top', 'bottom', 'none']) for (const setback of [0, 25, 50, 100]) {
    const t = measure(This, shape({lacer, setback, count})), b = Base && measure(Base, shape({lacer, setback, count}));
    console.log(`  lacer ${lacer.padEnd(6)} setback ${String(setback).padStart(3)}: ${b ? `${b.corners}/${b.cables} -> ` : ''}${t.corners}/${t.cables}`
      + ` (${t.findings} findings, ${t.close} of them saying the manager is too close); legs through a body ${b ? `${b.crossings} -> ` : ''}${t.crossings}`);
    if (!b) continue;
    for (const [id, [m, v]] of Object.entries(t.lengths)) {
      const [m0, v0] = b.lengths[id], d = (m - m0) * 1000;
      if (Math.abs(d) > 0.05) moved.push(d); else same++;
      if (v > v0) up++; else if (v < v0) down++;
    }
  }
  if (Base) {
    moved.sort((x, y) => x - y);
    console.log(`  routed lengths, all twelve racks: ${moved.length} of ${moved.length + same} move`
      + (moved.length ? `, ${moved[0].toFixed(1)} to ${moved.at(-1).toFixed(1)} mm, median ${moved[Math.floor(moved.length / 2)].toFixed(1)}; ${moved.filter(d => d < 0).length} shorter` : '')
      + `; stock sizes ${up} up, ${down} down`);
  }
}
