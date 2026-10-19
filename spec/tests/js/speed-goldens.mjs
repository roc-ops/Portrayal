// EVERY ANSWER THE RACK KIT GIVES FOR A SET OF RACKS, as digests, so that a
// change meant only to make the kit faster can be held to changing no number
// (rack-speed.mjs compares this tree against speed-goldens.json). Not a test
// file. Run on its own it records the digests of a tree:
//
//   node spec/tests/js/speed-goldens.mjs --kit <dir> --write      # record
//   node spec/tests/js/speed-goldens.mjs [--kit <dir>] [--exact] [--dump <rack> <kind>]
//
// `<dir>` is a copy of a revision that holds its `kit` and its
// `spec/tests/js` fixtures, for example
//   git archive <rev> kit spec/tests/js | tar -x -C <dir>
// `--write` puts the digests in speed-goldens.json beside this file; without
// it they are compared with that file and each difference is listed. `--dump`
// prints one answer whole, to compare two trees with a diff.
//
// WHY DIGESTS, and not the answers or a second kit: the answers are some
// 46 MB of JSON, and a second copy of the kit in the repository would be read
// by every check that reads the first. A digest of each answer says which
// rack and which answer changed, and `--dump` on both trees says how.
// TO SEVEN PLACES. A digest is of an answer with every number in it rounded
// to seven decimal places (of a millimetre, a metre or a degree, whichever
// it is in), so that a machine whose sine or cosine differs in its last bit
// gives the same digest: the kit's own answers are rounded to a tenth of a
// millimetre or a centimetre where they are read, and a path's points are
// not. `--exact` digests every number whole, by all its digits, and prints
// the digests instead of comparing them with the file: two trees are held
// to exactly the same numbers by running it on each, on one machine, and
// comparing what is printed. That is how the kit before 0.25.0 and after it
// were compared, and the file here was then recorded from the kit before.
// A CHANGE THAT IS MEANT TO MOVE A NUMBER records them again, from its own
// tree, and the difference in speed-goldens.json is then part of what is
// reviewed: which racks and which answers it moved.
//
// THE RACKS (`racksOf`): the two reference fixtures of #949 (cable-solids-fixture,
// route-direct-fixture), the bundle fixtures (bundle-hops-fixture), every
// rack file under spec/tests/fixtures/racks, the sixty generated racks of
// bend-room-sample (1,803 cables), and the generated racks of speed-fixture
// at 50, 150 and 300 cables, with and without lacers, ducts, bundles and
// every port listed, and each after one cable moved and one switch moved.
// THE ANSWERS (`outputsOf`), for each rack: every cable's path whole, its
// resolved route, ring marks, routed length and spare; the ring, body, bend
// and cover findings with their sentences; fill and capacity; the lengths
// saved; each bundle's layout, checks, straps and length, the anchors and
// strap texts; the slack of each cable, its findings and lines; the schedule
// rows, the cable BOM rows and notes, the lay and fill notes, both DCIM cable
// files; `describe`, whole and by section; and `inspect` of every cable and
// bundle.
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {readFileSync, readdirSync, writeFileSync} from 'node:fs';
import {sampleRack} from './bend-room-sample.mjs';
import {speedRack, moveCable, moveDevice} from './speed-fixture.mjs';

const HERE = resolve(new URL('../../..', import.meta.url).pathname);
export const GOLDENS = new URL('./speed-goldens.json', import.meta.url);

// A tree's kit and fixtures.
export async function loadTree(root = HERE) {
  const kit = name => import(pathToFileURL(`${root}/kit/rack/${name}.js`));
  const fix = name => import(pathToFileURL(`${root}/spec/tests/js/${name}.mjs`));
  const [M, R, B, S, Q, X, D, F, O, H] = await Promise.all([kit('model'), kit('route'), kit('bundles'), kit('slack'), kit('queries'),
    kit('export-data'), kit('dcim-rules'), fix('cable-solids-fixture'), fix('route-direct-fixture'), fix('bundle-hops-fixture')]);
  return {root, M, R, B, S, Q, X, D, F, O, H};
}

// A context for a rack file that names real devices: each a box of its
// units, each port placed by its name, so every cable has a path.
function plainCtx(rack) {
  const RUS = {'asr-9006': 10};
  const chassisOf = ref => ({ru: RUS[ref] ?? 1, w: 440, h: (RUS[ref] ?? 1) * 44.45 - 0.9, d: 400, model: String(ref).toUpperCase()});
  const hash = s => { let h = 2166136261; for (const ch of String(s)) h = Math.imul(h ^ ch.codePointAt(0), 16777619); return h >>> 0; };
  return () => Object.freeze({chassisOf, guidesOf: () => [], portX: e => (rack.items.some(i => i.id === e.item) ? (hash(`${e.item}|${e.path}`) % 4000) / 10 - 200 : null)});
}

// Every rack: [{name, rack, ctxOf, chassisOf}], `ctxOf(rack)` a context made anew.
export function racksOf(K) {
  const {M, F, O, H} = K, out = [];
  const add = (name, rack, ctxOf, chassisOf) => out.push({name, rack, ctxOf, chassisOf});
  add('owner', {...F.ownerRack(), cables: F.OWNER_CABLES}, () => F.ctxOf(), F.chassisOf);
  add('owner-direct', O.rack(), r => O.ctxOf(r), O.chassisOf);
  for (const [name, r] of [['hops', H.rack()], ['hops-flip', H.rack({flip: true})], ['hops-managed', H.managed()],
    ['hops-patched', H.patched()], ['hops-patched-3', H.patched({gap: 3, shift: 2})], ['hops-bundled', H.bundled()], ['hops-bundled-flip', H.bundled({flip: true})]]) {
    add(name, r, x => H.ctxFor(x), H.chassisOf);
    add(`${name}-ports`, r, x => H.ctxFor(x, {portBoxesOf: id => H.portsOf(x, id)}), H.chassisOf);
  }
  const dir = new URL('../fixtures/racks/', import.meta.url);
  for (const f of readdirSync(dir).filter(n => n.endsWith('.json')).sort()) {
    const doc = M.parseDoc(JSON.parse(readFileSync(new URL(f, dir), 'utf8')));
    (doc.racks || []).forEach((r, k) => { const c = plainCtx(r); add(`file-${f}-${k}`, r, c, c().chassisOf); });
  }
  for (let seed = 1; seed <= 60; seed++) { const s = sampleRack(M, F, seed); add(`sample-${seed}`, s.rack, () => ({...s.ctx}), s.ctx.chassisOf); }
  const speed = (name, opts) => { const s = speedRack(M, F, opts); add(name, s.rack, s.ctxOf, s.chassisOf); return s; };
  speed('speed-50', {cables: 50, bundles: 2});
  speed('speed-150', {cables: 150, bundles: 4});
  const big = speed('speed-300', {cables: 300, bundles: 4});
  add('speed-300-cable-moved', moveCable(big.rack, 'c1'), big.ctxOf, big.chassisOf);
  add('speed-300-switch-moved', moveDevice(big.rack, big.switches[6]), big.ctxOf, big.chassisOf);
  speed('speed-bare', {cables: 120, seed: 2, lacers: false, managers: false});
  speed('speed-no-ducts', {cables: 120, seed: 3, managers: false, bundles: 3});
  speed('speed-no-lacers', {cables: 120, seed: 4, lacers: false});
  speed('speed-cabled-ports', {cables: 120, seed: 5, portBoxes: false, bundles: 3});
  speed('speed-20-switches', {devices: 20, cables: 200, seed: 6, bundles: 3});
  return out;
}

const plain = (k, v) => (v instanceof Map ? {map: [...v]} : v instanceof Set ? {set: [...v]} : typeof v === 'number' && !Number.isFinite(v) ? String(v) : v);
// An answer as text: every number whole (`textOf`), or to seven places.
export const textOf = v => JSON.stringify(v, plain) ?? 'undefined';
const PLACES = 1e7;
const rounded = (k, v) => (typeof v === 'number' && Number.isFinite(v) ? Math.round(v * PLACES) / PLACES : plain(k, v));
export const roundedText = v => JSON.stringify(v, rounded) ?? 'undefined';
export const digest = s => createHash('sha256').update(s).digest('hex').slice(0, 12);

// Every answer for one rack, as text by kind. `fresh` makes a context anew
// for each group of answers, as a page does for each draw and tool call;
// otherwise one context serves them all. `exact` writes every number whole;
// otherwise to seven places.
export async function outputsOf(K, {rack: rack0, ctxOf, chassisOf}, {fresh = false, exact = false} = {}) {
  const {M, R, B, S, Q, X, D} = K, out = {}, write = exact ? textOf : roundedText;
  const put = (kind, fn) => { try { out[kind] = write(fn()); } catch (e) { out[kind] = `throws: ${e?.message}`; } };
  const one = ctxOf(rack0);
  const ctxFor = r => (fresh || r !== rack0 ? ctxOf(r) : one);
  const each = (r, fn) => (r.cables || []).map(c => fn(c));
  const label = r => id => r.items.find(i => i.id === id)?.label ?? (r.zeroU || []).find(z => z.id === id)?.label ?? id;
  {
    const r = rack0, c0 = ctxFor(r);
    put('paths', () => each(r, c => R.routePath(r, c, c0)));
    put('routes', () => each(r, c => R.resolveRoute(r, c, c0)));
    put('marks', () => each(r, c => R.ringMarks(r, c, c0)));
    put('lengths', () => each(r, c => R.routedLength(r, c, c0)));
    put('spare', () => each(r, c => R.spareOf(r, c, c0)));
    const c1 = ctxFor(r);
    put('ring-findings', () => R.ringFindings(r, c1, label(r)));
    put('body-findings', () => R.bodyFindings(r, c1, label(r)));
    put('bend-findings', () => R.bendFindings(r, c1, label(r)));
    put('cover-findings', () => R.coverFindings(r, c1, label(r)));
    put('fill', () => R.fill(r, c1));
    put('capacity', () => R.capacityOver(r, c1));
  }
  let rack = rack0;
  try { rack = R.withRoutedLengths(rack0, ctxFor(rack0)); } catch { rack = rack0; }
  put('saved', () => each(rack, c => c.length ?? null));
  const ctx = ctxOf(rack), bc = {route: ctx};
  put('saved-paths', () => each(rack, c => R.routePath(rack, c, ctx)));
  put('saved-spare', () => each(rack, c => R.spareOf(rack, c, ctx)));
  const bundles = M.bundlesOf(rack);
  put('bundle-layouts', () => bundles.map(b => B.layoutOf(rack, b, bc)));
  put('bundle-checks', () => B.bundleChecks(rack, bc));
  put('straps', () => bundles.map(b => B.straps(rack, b, bc)));
  put('anchors', () => B.anchorsOf(rack, bc));
  put('strap-texts', () => B.strapTexts(rack, bc));
  put('strap-totals', () => B.strapTotals(rack, bc));
  put('trunk-lengths', () => bundles.map(b => B.trunkLength(rack, b, bc)));
  const sc = ctxFor(rack);
  put('slack', () => each(rack, c => S.slackOf(rack, c, sc)));
  put('slack-findings', () => S.slackFindings(rack, sc, label(rack)));
  put('spare-lines', () => [S.spareLine(rack, sc), S.spareBomLine(rack, sc)]);
  put('spare-exports', () => S.spareExports(rack, sc));
  const xc = ctxFor(rack), name = label(rack);
  const facts = () => ({spare: S.spareExports(rack, xc), bodies: R.bodyFindings(rack, xc, name), bends: R.bendFindings(rack, xc, name),
    covers: R.coverFindings(rack, xc, name), bundles: X.bundleExports(rack, {route: xc}), straps: B.strapTexts(rack, {route: xc})});
  const routes = () => new Map(each(rack, c => [c.id, R.resolveRoute(rack, c, xc)]));
  put('bundle-exports', () => X.bundleExports(rack, {route: xc}));
  put('schedule', () => X.cableScheduleRows(rack, new Map(), rack.items, routes(), facts()));
  put('bom', () => [X.cableBomRows(rack), X.cableBomNotes(rack, new Map(), {spare: S.spareExports(rack, xc)}), X.strapBomRows(X.bundleExports(rack, {route: xc}))]);
  put('lay-notes', () => X.layNotes(rack, {bends: R.bendFindings(rack, xc, name), covers: R.coverFindings(rack, xc, name)}));
  put('fill-notes', () => X.fillNotes(rack, {fill: R.fill(rack, xc), over: R.capacityOver(rack, xc), routes: routes(), ctx: xc}, name));
  const names = X.uniqueNames(rack.items), kept = new Set(rack.items.map(i => i.id));
  const landed = new Map((rack.cables || []).flatMap(c => [c.a, c.b]).map(e => [`${e.item}|${e.view}|${e.path}`, {info: null, reason: null}]));
  for (const target of ['netbox', 'nautobot'])
    put(`dcim-${target}`, () => D.cableImportRows({rack, target, names, kept, ends: landed, resolve: e => ({ok: true, name: e.path, type: 'dcim.interface'})}));
  const qc = () => ({chassisOf, route: ctxFor(rack)});
  put('describe', () => [Q.describe(rack, qc()), ...['items', 'zeroU', 'cables', 'bundles'].map(section => Q.describe(rack, qc(), {section, limit: 50}))]);
  const ic = qc(), seen = [];
  for (const x of [...(rack.cables || []), ...bundles]) { try { seen.push(await Q.inspect(rack, x.id, ic)); } catch (e) { seen.push(`throws: ${e?.message}`); } }
  out.inspect = write(seen);
  return out;
}

// {rack name: {kind: digest}}, and how many cables and answers were read.
// `only(name)` picks the racks; every rack without it.
export async function digestsOf(K, {only = () => true, ...opts} = {}) {
  const out = {}, count = {racks: 0, cables: 0, answers: 0};
  for (const r of racksOf(K).filter(x => only(x.name))) {
    const got = await outputsOf(K, r, opts);
    out[r.name] = Object.fromEntries(Object.entries(got).map(([kind, text]) => [kind, digest(text)]));
    count.racks++; count.cables += (r.rack.cables || []).length; count.answers += Object.keys(got).length;
  }
  return {digests: out, count};
}

// The digests as the file holds them: a rack a line.
export const fileText = ({count, digests}) => `${JSON.stringify({count, digests}).replace(/\},"/g, '},\n"')}\n`;

// Each answer that differs: ["rack: kind"].
export function differences(got, want) {
  const out = [];
  for (const name of new Set([...Object.keys(got), ...Object.keys(want)]))
    for (const kind of new Set([...Object.keys(got[name] ?? {}), ...Object.keys(want[name] ?? {})]))
      if (got[name]?.[kind] !== want[name]?.[kind]) out.push(`${name}: ${kind}`);
  return out;
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) {
  const arg = name => { const i = process.argv.indexOf(name); return i > 0 ? process.argv[i + 1] : null; };
  const K = await loadTree(arg('--kit') ? resolve(arg('--kit')) : HERE);
  const at = process.argv.indexOf('--dump');
  if (at > 0) {
    const r = racksOf(K).find(x => x.name === process.argv[at + 1]);
    if (!r) throw new Error(`no rack ${process.argv[at + 1]}`);
    console.log(JSON.stringify(JSON.parse((await outputsOf(K, r, {exact: process.argv.includes('--exact')}))[process.argv[at + 2]]), null, 1));
  } else {
    const exact = process.argv.includes('--exact');
    const t = Date.now(), {digests, count} = await digestsOf(K, {fresh: process.argv.includes('--fresh'), exact});
    console.error(`${count.racks} racks, ${count.cables} cables, ${count.answers} answers, ${((Date.now() - t) / 1000).toFixed(1)} s`);
    if (exact) console.log(fileText({count, digests}));
    else if (process.argv.includes('--write')) writeFileSync(GOLDENS, fileText({count, digests}));
    else {
      const diff = differences(digests, JSON.parse(readFileSync(GOLDENS, 'utf8')).digests);
      console.log(diff.length ? diff.join('\n') : 'no difference');
      process.exitCode = diff.length ? 1 : 0;
    }
  }
}
