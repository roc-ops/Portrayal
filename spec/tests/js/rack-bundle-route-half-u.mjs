// A lane run that starts or ends at a half unit (kit/rack/bundle-route.js).
//
// elementsOf once stepped a run by one unit and compared with !==, so a run
// ending at 16.5 never ended and grew without bound. Every call that could
// loop therefore runs in a child process with a hard time and memory limit:
// on a tree that still loops, the test FAILS in seconds instead of hanging
// the suite (test_rack_kit_js.py runs this file with no timeout of its own).
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

const URL_OF = f => new URL(`../../../kit/rack/${f}`, import.meta.url).href;
const L = 'left-front';

// Run `body` (module code, printing one JSON line) in a child that is killed
// after 5 s and holds at most 64 MB: a hang or an out-of-memory exit is a
// failed assertion here, never a stuck run.
function guarded(body) {
  const r = spawnSync(process.execPath, ['--max-old-space-size=64', '--input-type=module', '-e', body],
    {timeout: 5000, killSignal: 'SIGKILL', encoding: 'utf8'});
  assert.equal(r.signal, null, `the call did not end in 5 s (signal ${r.signal})`);
  assert.equal(r.status, 0, `the call failed: ${r.stderr.slice(0, 300)}`);
  return JSON.parse(r.stdout);
}
const lane = (...rus) => rus.map(ru => ({lane: L, ru}));
// An element as [key, kind, u, hi, seg, t]; `hi` is only on a partial segment.
// (the waypoints go in as code, not JSON, which has no Infinity or NaN)
const code = ws => `[${ws.map(w => `{lane: '${w.lane}', ru: ${w.ru}}`).join(', ')}]`;
const rows = waypoints => guarded(`
  import {elementsOf} from '${URL_OF('bundle-route.js')}';
  console.log(JSON.stringify(elementsOf(${code(waypoints)}).map(e => [e.key, e.kind, e.u, e.hi ?? null, e.seg, e.t])));`);
// JSON has no NaN or Infinity: both come back as null, in the expectation too.
const wire = x => JSON.parse(JSON.stringify(x));
const n = (u, seg, t) => [`n|${L}|${u}`, 'n', u, null, seg, t];
const s = (u, seg, t) => [`s|${L}|${u}`, 's', u, null, seg, t];            // a whole segment, u to u + 1
const part = (lo, hi, seg, t) => [`s|${L}|${lo}|${hi}`, 's', lo, hi, seg, t]; // a partial one, lo to hi

// The cut points of a run are its two ends and every whole unit between them.
// A segment between two cut points is whole (key s|lane|lo) only when it is
// exactly one unit from a whole unit; any other carries both ends in its key.
// t is the middle of a segment, and a node's place, as a share of the run.

test('a run that ends at a half unit ends: 15 to 16.5', () => {
  assert.deepEqual(rows(lane(15, 16.5)), wire([
    n(15, 0, 0), s(15, 0, 0.5 / 1.5), n(16, 0, 1 / 1.5), part(16, 16.5, 0, 1.25 / 1.5), n(16.5, 1, 0)]));
});

test('a run that starts at a half unit: 16.5 to 18', () => {
  assert.deepEqual(rows(lane(16.5, 18)), wire([
    n(16.5, 0, 0), part(16.5, 17, 0, 0.25 / 1.5), n(17, 0, 0.5 / 1.5), s(17, 0, 1 / 1.5), n(18, 1, 0)]));
});

test('a run with both ends at a half unit: 15.5 to 17.5', () => {
  assert.deepEqual(rows(lane(15.5, 17.5)), wire([
    n(15.5, 0, 0), part(15.5, 16, 0, 0.125), n(16, 0, 0.25), s(16, 0, 0.5), n(17, 0, 0.75),
    part(17, 17.5, 0, 0.875), n(17.5, 1, 0)]));
});

test('a run down to or from a half unit: 18 to 16.5 and 17.5 to 15', () => {
  // downward, a segment is named by its lower end, as a whole one always was
  assert.deepEqual(rows(lane(18, 16.5)), wire([
    n(18, 0, 0), s(17, 0, 0.5 / 1.5), n(17, 0, 1 / 1.5), part(16.5, 17, 0, 1.25 / 1.5), n(16.5, 1, 0)]));
  assert.deepEqual(rows(lane(17.5, 15)), wire([
    n(17.5, 0, 0), part(17, 17.5, 0, 0.25 / 2.5), n(17, 0, 0.5 / 2.5), s(16, 0, 1 / 2.5), n(16, 0, 1.5 / 2.5),
    s(15, 0, 2 / 2.5), n(15, 1, 0)]));
});

test('a run inside one unit is one partial segment, the same going up or down', () => {
  assert.deepEqual(rows(lane(16, 16.5)), wire([n(16, 0, 0), part(16, 16.5, 0, 0.5), n(16.5, 1, 0)]));
  assert.deepEqual(rows(lane(16.5, 16)), wire([n(16.5, 0, 0), part(16, 16.5, 0, 0.5), n(16, 1, 0)]));
});

test('no run returns one node', () => {
  assert.deepEqual(rows(lane(16.5, 16.5)), wire([n(16.5, 0, 0)]));
  assert.deepEqual(rows(lane(15, 15)), wire([n(15, 0, 0)]));
});

test('a run to an end that is no number returns and never loops', () => {
  // an end that is not a finite number is a node of its own, with no steps to it
  assert.deepEqual(rows(lane(15, Infinity)), wire([n(15, 0, 0), n(Infinity, 1, 0)]));
  assert.deepEqual(rows(lane(-Infinity, 15)), wire([n(-Infinity, 0, 0), n(15, 1, 0)]));
  assert.deepEqual(rows(lane(15, NaN)), wire([n(15, 0, 0), n(NaN, 1, 0)]));
  assert.deepEqual(rows(lane(15, 1e300)), wire([n(15, 0, 0), n(1e300, 1, 0)]));
});

test('whole-unit runs keep their keys and their t, with no hi', () => {
  const up = rows(lane(20, 30));
  assert.equal(up.length, 21);
  up.forEach((row, i) => {
    const j = Math.floor(i / 2);
    assert.equal(row[0], i % 2 ? `s|${L}|${20 + j}` : `n|${L}|${20 + j}`);
    assert.equal(row[3], null);
    assert.equal(row[5], i === 20 ? 0 : i % 2 ? (j + 0.5) / 10 : j / 10);   // 0.05, 0.1, ... as before the change
  });
  assert.deepEqual(up.slice(0, 4), [n(20, 0, 0), s(20, 0, 0.05), n(21, 0, 0.1), s(21, 0, 0.15)]);
  assert.deepEqual(up.at(-1), n(30, 1, 0));
  assert.deepEqual(rows(lane(22, 30)).slice(0, 3), [n(22, 0, 0), s(22, 0, 0.0625), n(23, 0, 0.125)]);
  assert.deepEqual(rows(lane(22, 20)), [n(22, 0, 0), s(21, 0, 0.25), n(21, 0, 0.5), s(20, 0, 0.75), n(20, 1, 0)]);
});

test('a partial segment prints with both its ends; a whole one as it did', () => {
  const out = guarded(`
    import {elementsOf, elementText} from '${URL_OF('bundle-route.js')}';
    const els = elementsOf(${JSON.stringify(lane(15, 16.5))});
    const up = {heightRU: 42, numbering: 'bottom-up'}, down = {heightRU: 42, numbering: 'top-down'};
    console.log(JSON.stringify([els.map(e => elementText(e)), els.map(e => elementText(e, id => id, up)), els.map(e => elementText(e, id => id, down))]));`);
  assert.deepEqual(out[0], ['left-front U15', 'left-front U15-U16', 'left-front U16', 'left-front U16-U16.5', 'left-front U16.5']);
  assert.deepEqual(out[1], out[0]);
  // top-down, a half unit is named as the frame names every unit
  assert.deepEqual(out[2], ['left-front U28', 'left-front U28-U27', 'left-front U27', 'left-front U27-U26.5', 'left-front U26.5']);
});

// ── what deriveTrunk makes of them ───────────────────────────────────────
const trunkOf = members => guarded(`
  import {deriveTrunk} from '${URL_OF('bundle-route.js')}';
  console.log(JSON.stringify(deriveTrunk(${JSON.stringify(members)})));`);

test('two cables that end at a half unit have a trunk to it, as to a whole unit', () => {
  const half = trunkOf([{id: 'c1', waypoints: lane(10, 16.5)}, {id: 'c2', waypoints: lane(12, 16.5)}]);
  assert.deepEqual(half, {route: lane(12, 16.5)});
  const whole = trunkOf([{id: 'c1', waypoints: lane(10, 17)}, {id: 'c2', waypoints: lane(12, 17)}]);
  assert.deepEqual(whole, {route: lane(12, 17)});
});

test('a trunk stops at the last whole unit two runs share, a half unit short of where they part', () => {
  // 15 to 16.5 and 15 to 17 share up to U16; the half unit from 16 to 16.5 is
  // not seen as shared, but nothing parts and meets again: no error
  assert.deepEqual(trunkOf([{id: 'c1', waypoints: lane(15, 16.5)}, {id: 'c2', waypoints: lane(15, 17)}]), {route: lane(15, 16)});
});

test('a cable with a half-unit waypoint midway is refused in words, never looped on', () => {
  // 15 to 16.5 to 17 and 15 to 17 run the same way, but the first is cut at 16.5
  // and the second is not: they share U15 to U16 and U17 and nothing between
  const r = trunkOf([{id: 'c1', waypoints: lane(15, 16.5, 17)}, {id: 'c2', waypoints: lane(15, 17)}]);
  assert.match(r.error, /^c1 and c2 run together at .*, but apart between them\. Bundle them separately/);
});

// ── the case as it was met: a half-unit panel, two cables, bundle.create ─
test('bundle.create for two cables to a half-unit panel ends, with or without keeping the result', () => {
  const body = `
    import * as M from '${URL_OF('model.js')}';
    import {withCable} from '${URL_OF('cable-rules.js')}';
    import {apply} from '${URL_OF('commands.js')}';
    const SIZES = {sw: {ru: 1, d: 515, model: 'SW'}, half: {ru: 0.5, d: 100, model: 'HALF'}};
    const chassisOf = ref => SIZES[ref] || null;
    let r = M.newRack({name: 'Rack 1'});
    r = M.withItem(r, {ref: 'sw', cfg: 'x', ru: 10, label: 'sw-1'}).rack;
    r = M.withItem(r, {ref: 'half', cfg: 'x', ru: 16.5, label: 'half-1'}).rack;
    const routes = [[{lane: 'left-front', ru: 10}, {lane: 'left-front', ru: 16.5}], [{lane: 'left-front', ru: 12}, {lane: 'left-front', ru: 16.5}]];
    routes.forEach((route, k) => {
      r = withCable(r, {a: {item: 'i1', path: 'p' + (k + 1), view: 'front'}, b: {item: 'i2', path: 'q' + (k + 1), view: 'front'}, media: 'cat6'}).rack;
      r = {...r, cables: r.cables.map(c => (c.id === 'c' + (k + 1) ? {...c, route, routeEdited: true} : c))};
    });
    const rc = {chassisOf, guidesOf: () => [], portX: () => -150};
    const once = () => apply(r, {op: 'bundle.create', cables: ['c1', 'c2']}, {chassisOf, route: rc});
    const a = once(), b = once();
    console.log(JSON.stringify([a, b].map(x => ({error: x.error ?? null, members: x.rack?.bundles?.[0]?.members.length ?? 0, route: x.rack?.bundles?.[0]?.route ?? null}))));`;
  const [a, b] = guarded(body);
  assert.deepEqual(a, {error: null, members: 2, route: lane(12, 16.5)});
  assert.deepEqual(b, a);
});
