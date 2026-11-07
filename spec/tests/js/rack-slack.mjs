// spec/tests/js/rack-slack.mjs
// LENGTHS AND THE SLACK RECORD (docs/rack-file-v4-design.md section 3, build
// part 7): the lengths named (path, need, stock, spare, end play, to store),
// the stock break, the short tolerance with its floor, the `slack` key read,
// resolved and said in words, `cable.slack` and its refusals, and the two
// schedule columns. Nothing here draws or places spare.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import * as R from '../../../kit/rack/route.js';
import * as SL from '../../../kit/rack/slack.js';
import * as Q from '../../../kit/rack/queries.js';
import * as X from '../../../kit/rack/export-data.js';
import {apply, COMMANDS} from '../../../kit/rack/commands.js';
import * as F from './route-direct-fixture.mjs';

const mm = v => Math.round(v * 1e4) / 10;
const near = (a, b, what, tol = 1e-9) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a}, want ${b}`);
// A cord laid along the tray of the lacer (i4), which states a place for slack
function trayRack(extra = {}, cableExtra = {}) {
  const r = F.rack();
  const c = {...r.cables[0], b: {item: 'i2', path: 'bay-2/module/lc3', view: 'front'}, route: [{item: 'i4', via: 'tray'}], routeEdited: true,
             length: {value: 1, unit: 'm', source: 'routed', need: 0.36}, ...cableExtra};
  return {r: {...r, cables: [c, ...r.cables.slice(1)], ...extra}, c};
}
const TRAY = {item: 'i4', via: 'tray'};

// ── the lengths ──────────────────────────────────────────────────────────

test('the reference rack: every stock size before and after; only a cord within 10 mm over a break changes, each named', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  // before version 4: the first size at or over the need and the end play, to a nanometre
  const before = m => R.STOCK_M.find(s => s >= m - 1e-9);
  const moved = [];
  for (const c of r.cables) {
    const l = R.routedLength(r, c, ctx), was = before(l.measured);
    if (was !== l.value) {
      moved.push([c.id, was, l.value, mm(l.measured - l.value)]);
      // it drops one size, and was within the tolerance over it
      assert.ok(l.value < was && l.measured > l.value && l.measured <= l.value + R.BREAK_TOL_M + 1e-9, c.id);
    } else assert.ok(l.measured <= l.value + 1e-9 || l.measured > l.value + R.BREAK_TOL_M, c.id);
  }
  // c3 was 2.7 mm over a 0.5 m cord with full end play, and c7 5.8 mm
  assert.deepEqual(moved, [['c3', 1, 0.5, 2.7], ['c7', 1, 0.5, 5.8]]);
  assert.equal(r.cables.length, 16);
});

test('for every cable the need and the spare are the stock, and the end play and what is to store are the spare', () => {
  const r = F.rack(), ctx = F.ctxOf(r);
  let n = 0;
  for (const c of r.cables) {
    const s = R.spareOf(r, c, ctx), p = R.routePath(r, c, ctx), l = R.pathLength(p);
    near(s.need_m + s.spare_m, s.stock_m, `${c.id} need and spare`);
    near(s.end_play_m + s.to_store_m, s.spare_m, `${c.id} end play and to store`);
    assert.equal(s.stock_m, l.value);
    near(s.need_m, l.need, c.id);
    near(s.need_m, R.needOf(p, c, s.stock_m), c.id);
    assert.equal(s.pinned, false);
    assert.ok(s.end_play_m <= 2 * R.END_PLAY_M + 1e-12 && s.to_store_m >= 0);
    n++;
  }
  assert.equal(n, 16);
  // c12, the reference cord of the note (need 423 mm, a 1 m cord, 577 mm
  // spare: 200 of end play and 377 to store). Under #966 it rose through the
  // tray's gap (need 298 mm, a 0.5 m cord with 2 mm to store); CHANGED, drawable
  // geometry, owner's option A, 2026-10-22, P-0218-2: it goes round the front edge
  const ref = R.spareOf(r, r.cables.find(c => c.id === 'c12'), ctx);
  assert.deepEqual([mm(ref.need_m), ref.stock_m, mm(ref.spare_m), mm(ref.end_play_m), mm(ref.to_store_m)], [423.4, 1, 576.6, 200, 376.6]);
  // c13, which still goes round the front edge, is the 1 m cord of the note's kind
  const far = R.spareOf(r, r.cables.find(c => c.id === 'c13'), ctx);
  assert.equal(far.stock_m, 1);
  assert.ok(far.to_store_m > 0.3);
  // a cord whose spare is less than the end play keeps what it has at the ends and stores none
  const c3 = R.spareOf(r, r.cables.find(c => c.id === 'c3'), ctx);
  assert.deepEqual([c3.stock_m, mm(c3.spare_m), mm(c3.end_play_m), c3.to_store_m], [0.5, 197.3, 197.3, 0]);
  // a pinned length is the stock, whatever the route would choose; one too short has a negative spare
  const pin = len => R.spareOf(r, {...r.cables[0], length: len}, ctx);
  assert.deepEqual([pin({value: 3, unit: 'm', source: 'entered'}).stock_m, pin({value: 3, unit: 'm', source: 'entered'}).pinned], [3, true]);
  assert.ok(pin({value: 0.2, unit: 'm', source: 'entered'}).spare_m < 0);
  near(pin({value: 10, unit: 'ft', source: 'entered'}).stock_m, 3.048, 'feet');
  assert.equal(pin({value: 2, unit: 'yd', source: 'entered'}), null);
  assert.equal(R.spareOf(r, {...r.cables[0], length: undefined, lengthAsWritten: 'long'}, ctx), null);
  // without a path there is none: it never reads a saved number
  assert.equal(R.spareOf(r, {...r.cables[0], a: {item: 'i9', path: 'x', view: 'front'}}, ctx), null);
});

test('a copper cord at each stock size: the need is unchanged to 5 m, and 20 mm more at 7 m', () => {
  const cu = {media: 'cat6'};
  assert.deepEqual(R.STOCK_M.map(s => Math.round(R.shortTolerance(cu, s) * 1000)), [50, 50, 50, 50, 50, 50, 70, 100, 150, 200, 300]);
  // to 5 m that is the 25 mm an end the table held; a cable with no media, or one unknown, is the same
  for (const c of [{}, null, {media: 'nope'}, {media: 'cat6a'}]) assert.deepEqual([1, 5, 7, 30].map(s => R.shortTolerance(c, s)), [0.05, 0.05, 0.07, 0.3]);
  // DAC keeps its stated 50 mm at every length; fibre and AOC have none
  assert.deepEqual([1, 5, 7].map(s => R.shortTolerance({media: 'dac'}, s)), [0.05, 0.05, 0.05]);
  for (const media of ['os2', 'om3', 'om4', 'om5', 'aoc']) assert.equal(R.shortTolerance({media}, 30), 0, media);
  // a path of each length: the need over the path, per stock size chosen
  const path = (metres, media) => ({points: [{x: 0, y: 0, z: 0}, {x: 0, y: metres * 1000, z: 0}], allowance: R.endAllowance({media}), media});
  const over = (metres, media) => { const l = R.pathLength(path(metres, media)); return [l.value, Math.round((l.need - metres) * 1000)]; };
  assert.deepEqual([0.2, 0.7, 1.2, 1.7, 2.7, 4.7].map(m => over(m, 'cat6')), [[0.5, 69], [1, 69], [1.5, 69], [2, 69], [3, 69], [5, 69]]);
  assert.deepEqual(over(6.5, 'cat6'), [7, 89], 'at 7 m the tolerance is 70 mm: 20 mm more');
  assert.deepEqual(over(9.5, 'cat6'), [10, 119]);
  // the size is solved with the tolerance: 6.72 m of path needs 6.789 at 7 m (0.07) and does not fit with end play; at 10 m it does
  assert.deepEqual(over(6.72, 'cat6'), [7, 89]);
  assert.deepEqual(over(6.73, 'cat6'), [10, 119]);
  assert.deepEqual(over(6.73, 'om4'), [7, 26], 'a fibre cord of the same path is a 7 m cord');
});

// ── the loader ───────────────────────────────────────────────────────────

const docWith = slack => ({format: 'portrayal-rack', version: 4, id: 'd', racks: [{id: 'r1', name: 'R', frame: {kind: 'four-post', heightRU: 42},
  items: [], zeroU: [], cables: [{id: 'c1', a: {item: 'i1', path: 'p', view: 'front'}, b: {item: 'i2', path: 'q', view: 'front'},
    media: 'os2', purpose: '', label: '', route: [], ...(slack === undefined ? {} : {slack})}]}]});
const read = slack => M.parseDoc(docWith(slack)).racks[0].cables[0];

test('the loader keeps the usable slack entries, and what was written when any is not', () => {
  const good = [{item: 'i4', via: 'tray', form: 'coil'}, {end: 'a', value: 0.1, unit: 'm'}, {item: 'i5', via: 'spool-1', form: 'spool', value: 2}];
  assert.deepEqual(read(good), {...docWith(good).racks[0].cables[0]});
  assert.equal('slackAsWritten' in read(good), false);
  // each fault: the usable part stays, and the list as written is held beside it
  const cases = [
    ['a bad form', [{item: 'i4', via: 'tray', form: 'knot'}, {end: 'b'}], [{end: 'b'}]],
    ['a negative value', [{end: 'a', value: -1}, {item: 'i4', via: 'tray'}], [{item: 'i4', via: 'tray'}]],
    ['two entries with no value', [{item: 'i4', via: 'tray'}, {end: 'a'}, {end: 'b', value: 0.2}], [{item: 'i4', via: 'tray'}, {end: 'b', value: 0.2}]],
    ['an unknown end', [{end: 'c'}, {end: 'a', value: 0.1}], [{end: 'a', value: 0.1}]],
    ['a value of 0, a unit that is no text, an entry that is no object', [{end: 'a', value: 0}, {end: 'a', value: 1, unit: 5}, 'tray', null], []],
    ['a tray with no via', [{item: 'i4'}, {item: '', via: 'tray'}], []],
  ];
  for (const [what, written, kept] of cases) {
    const c = read(written);
    assert.deepEqual(c.slack, kept, what);
    assert.deepEqual(c.slackAsWritten, written, what);
    // saved and opened again it is unchanged
    const doc = M.parseDoc(docWith(written));
    assert.deepEqual(M.parseDoc(M.serialize(doc)), doc, what);
    assert.deepEqual(JSON.parse(M.serialize(doc)).racks[0].cables[0].slackAsWritten, written, what);
  }
  // a slack that is no list moves there whole, and the cable has no slack key: nothing has been said
  for (const odd of ['tray', {item: 'i4', via: 'tray'}, 5, null]) {
    const c = read(odd);
    assert.equal('slack' in c, false, JSON.stringify(odd));
    assert.deepEqual(c.slackAsWritten, odd);
    assert.deepEqual(M.parseDoc(M.serialize(M.parseDoc(docWith(odd)))).racks[0].cables[0], c);
  }
  // no key and an empty list are two things, and both survive
  assert.equal('slack' in read(undefined), false);
  assert.deepEqual(read([]).slack, []);
  assert.equal('slackAsWritten' in read([]), false);
});

// ── the text of the list (section 3.6), a case a row ─────────────────────

test('stored: each row of the table says its text', () => {
  const said = (slack, cableExtra = {}, rackExtra = {}, ctxExtra = {}) => {
    const {r, c} = trayRack(rackExtra, {...(slack === undefined ? {} : {slack}), ...cableExtra});
    const ctx = {...F.ctxOf(r), ...ctxExtra};
    return SL.storedText(r, c, SL.slackOf(r, c, ctx));
  };
  // (the cord has 0.44 m to store and 0.2 m of end play)
  assert.equal(said([TRAY]), 'CM-01 tray, coil, 0.44 m; 0.2 m at the ends', 'an entry naming a tray');
  assert.equal(said([{...TRAY, form: 'serpentine'}]), 'CM-01 tray, serpentine, 0.44 m; 0.2 m at the ends');
  assert.equal(said([{end: 'a'}]), '0.44 m at the A end; 0.2 m at the ends', 'an end entry');
  assert.equal(said([{...TRAY, value: 0.3}]), 'CM-01 tray, coil, 0.3 m; 0.14 m not placed; 0.2 m at the ends', 'values that add up to less');
  assert.equal(said([{...TRAY, value: 0.3}, {end: 'b'}]), 'CM-01 tray, coil, 0.3 m; 0.14 m at the B end; 0.2 m at the ends', 'the rest goes to the entry with no value');
  assert.equal(said(undefined), '0.44 m not placed; 0.2 m at the ends', 'no slack key');
  assert.equal(said([]), '0.44 m not placed, by choice; 0.2 m at the ends', 'an empty list');
  // values that add up to more: the size grows to hold them, so a routed cord is never over; a pinned one is
  const pinned = {length: {value: 1, unit: 'm', source: 'entered'}};
  assert.equal(said([{...TRAY, value: 1.5}], pinned), 'CM-01 tray, coil, 1.5 m; 0.2 m at the ends', 'values that add up to more');
  // nothing to store: the spare is all end play (a 0.6 m cord pinned: 0.24 m of spare, 0.04 to store; 0.5 m: 0.14)
  assert.equal(said(undefined, {length: {value: 0.5, unit: 'm', source: 'entered'}}), '0.14 m at the ends', 'nothing to store');
  // an entry on a tray the cable no longer rests on, or on its held face
  // (off the tray the cord is shorter: a 0.5 m cord, with nothing to store)
  assert.equal(said([{item: 'i4', via: 'tray'}], {route: [], routeEdited: false}), 'CM-01 tray, coil, 0 m, not on its route; 0.2 m at the ends');
  assert.equal(said([{item: 'i4', via: 'tray'}], {route: [], routeEdited: false, length: {value: 1, unit: 'm', source: 'entered'}}),
    'CM-01 tray, coil, 0.5 m, not on its route; 0.2 m at the ends');
  assert.equal(said([TRAY], {}, {}, {trayFaceOf: (cable, w) => (w.via === 'tray' ? 'underside' : null)}).replace(/0\.\d+ m, on/, 'N m, on'),
    'CM-01 tray, coil, N m, on the held face; 0.2 m at the ends');
  // a pinned stock length under the need: blank
  assert.equal(said([TRAY], {length: {value: 0.2, unit: 'm', source: 'entered'}}), '');
  // no length, a length kept as written, or no path: blank
  assert.equal(said([TRAY], {length: undefined}), '');
  assert.equal(said([TRAY], {length: undefined, lengthAsWritten: {value: 'x'}}), '');
  assert.equal(said([TRAY], {a: {item: 'i9', path: 'p', view: 'front'}}), '');
});

test('a member riding a bundle trunk through the tray reads in its bundle', () => {
  const {r, c} = trayRack({}, {slack: [TRAY]});
  // a second cord along the tray, and the two bundled through it
  const c2 = {...r.cables[1], b: {item: 'i2', path: 'bay-2/module/lc4', view: 'front'}, route: [TRAY], routeEdited: true,
              length: {value: 1, unit: 'm', source: 'routed'}};
  const rr = {...r, cables: [c, c2, ...r.cables.slice(2)], bundles: [{id: 'b1', number: 2, label: '', members: [{cable: c.id}, {cable: c2.id}], route: [TRAY]}]};
  const ctx = F.ctxOf(rr);
  const s = SL.slackOf(rr, c, ctx);
  assert.equal(s.entries[0].ok, false);
  assert.equal(s.entries[0].why, 'c1 rides Bundle 2 through CM-01 tray: store its spare after it leaves the bundle.');
  assert.match(SL.storedText(rr, c, s), /^CM-01 tray, coil, 0\.\d+ m, in Bundle 2; 0\.2 m at the ends$/);
});

// ── the findings ─────────────────────────────────────────────────────────

test('the findings: spare with no place, a pinned length too short, more stored than there is, and an entry off the route', () => {
  const bare = F.rack(), ctx = F.ctxOf(bare);
  // a cable with no length has nothing bought, so nothing spare: no finding and no line
  assert.deepEqual([SL.slackFindings(bare, ctx), SL.spareLine(bare, ctx)], [[], '']);
  const r = R.withRoutedLengths(bare, ctx);
  const f = SL.slackFindings(r, ctx);
  // every cord of the rack with more than 0.3 m to store and no slack key
  // (c9 to c12 and c15 were cords of 0.5 m with under 0.3 m to store while they
  // rose through the tray's gap, #966; CHANGED, drawable geometry, owner's
  // option A, 2026-10-22, P-0218-2: they go round the front edge and are 1 m cords)
  assert.deepEqual(f.map(x => x.kind), Array(12).fill('spare-unplaced'));
  assert.deepEqual(f.map(x => x.cable), ['c1', 'c5', 'c6', 'c8', 'c9', 'c10', 'c11', 'c12', 'c13', 'c14', 'c15', 'c16']);
  assert.equal(f.find(x => x.cable === 'c13').text, 'c13 has 0.35 m to store and no place for it.');
  // an empty list is a choice, and gives none; nor does a place
  const chosen = {...r, cables: r.cables.map(c => ({...c, slack: c.id === 'c12' ? [{end: 'a'}] : []}))};
  assert.deepEqual(SL.slackFindings(chosen, ctx), []);
  // the line for the rack counts every cord with spare and no place said, c4 with its 9 mm too
  // (8.08 m until #987: c8, through ring 4, needs 72 mm less of its 1 m cord;
  // 6.35 m and 12 cords while five cords rose through the tray's gap (#966), their
  // spare mostly gone with the size of the cord; CHANGED, drawable geometry, owner's
  // option A, 2026-10-22, P-0218-2: they go round the front edge again)
  assert.equal(SL.spareLine(r, ctx), 'Spare: 8.15 m; 13 cords not placed.');
  assert.equal(SL.spareLine(chosen, ctx), 'Spare: 8.15 m; 0 cords not placed.');
  // a pinned length under the need
  // (0.3 m while c12 went through the tray's gap, #966; 0.42 m round the front edge, as now)
  const short = {...r, cables: [{...r.cables[11], length: {value: 0.2, unit: 'm', source: 'entered'}}]};
  assert.deepEqual(SL.slackFindings(short, ctx), [{kind: 'spare-short', cable: 'c12', text: 'c12 is 0.2 m and needs 0.42 m.'}]);
  // values past what there is to store, on a pinned cord
  const {r: tr, c} = trayRack({}, {length: {value: 1, unit: 'm', source: 'entered'}, slack: [{...TRAY, value: 1.5}]});
  assert.deepEqual(SL.slackFindings({...tr, cables: [c]}, F.ctxOf(tr), id => tr.items.find(i => i.id === id).label),
    [{kind: 'spare-over', cable: 'c1', text: 'c1 stores 1.5 m in CM-01 tray and has 0.44 m to store.'}]);
  // within the stock break tolerance, 10 mm, it is no finding: 0.44 m to store and 0.445 stated
  const close = {...c, slack: [{...TRAY, value: 0.445}]};
  assert.deepEqual(SL.slackFindings({...tr, cables: [close]}, F.ctxOf(tr)), []);
  assert.equal(SL.slackFindings({...tr, cables: [{...c, slack: [{...TRAY, value: 0.46}]}]}, F.ctxOf(tr)).length, 1);
  // an entry kept on a tray the cable does not rest on
  const off = {...r, cables: [{...r.cables[11], slack: [TRAY]}]};
  assert.deepEqual(SL.slackFindings(off, ctx), [{kind: 'spare-off-route', cable: 'c12', text: 'CM-01 tray is not on the route of c12.'}]);
});

// ── cable.slack ──────────────────────────────────────────────────────────

test('cable.slack records a place, and each refusal of the design has its sentence', () => {
  const {r, c} = trayRack();
  const ctx = {chassisOf: F.chassisOf, route: F.ctxOf(r)};
  const run = (rack, cmd, cx = ctx) => apply(rack, cmd, cx);
  const ok = run(r, {op: 'cable.slack', id: 'c1', at: TRAY});
  assert.equal(ok.error, undefined);
  assert.equal(ok.summary, 'Stored the spare of c1 in CM-01 tray.');
  assert.deepEqual(ok.rack.cables[0].slack, [{item: 'i4', via: 'tray'}]);
  assert.equal(run(ok.rack, {op: 'cable.slack', id: 'c1', at: TRAY}).noop, true);
  // a value, a form, an end; the same place is replaced, another is added
  const more = run(ok.rack, [{op: 'cable.slack', id: 'c1', at: TRAY, value: 0.3, form: 'serpentine'}, {op: 'cable.slack', id: 'c1', at: {end: 'b'}}]);
  assert.deepEqual(more.rack.cables[0].slack, [{item: 'i4', via: 'tray', form: 'serpentine', value: 0.3, unit: 'm'}, {end: 'b'}]);
  assert.equal(more.summary, 'Stored 0.3 m of the spare of c1 in CM-01 tray. Stored the spare of c1 at its B end.');
  // only one place takes the rest
  assert.equal(run(more.rack, {op: 'cable.slack', id: 'c1', at: {end: 'a'}}).error,
    'c1 already has an entry that takes the rest of its spare: give this one a value.');
  // the refusals of section 3.5
  // a place that can never hold it says where the spare can go (P-0017)
  assert.equal(run(r, {op: 'cable.slack', id: 'c12', at: TRAY}).error, 'CM-01 tray is not on the route of c12. '
    + 'The route of c12 has no tray or duct that holds spare, so its spare can go only at an end ({end: a} or {end: b}).');
  const held = {chassisOf: F.chassisOf, route: {...F.ctxOf(r), trayFaceOf: (cable, w) => (w.via === 'tray' ? 'underside' : null)}};
  assert.equal(run(r, {op: 'cable.slack', id: 'c1', at: TRAY}, held).error, 'c1 lies on the held face of CM-01 tray; slack is stored on the resting face.');
  const noSlack = {chassisOf: F.chassisOf, route: {...F.ctxOf(r), chassisOf: ref => {
    const k = F.chassisOf(ref);
    return k?.trays ? {...k, trays: k.trays.map(({slack: _s, ...t}) => t)} : k;
  }}};
  assert.equal(run(r, {op: 'cable.slack', id: 'c1', at: TRAY}, noSlack).error, 'CM-01 tray states no place for spare cable.');
  assert.equal(run(r, {op: 'cable.slack', id: 'c1', at: TRAY, form: 'spool'}).error, 'CM-01 tray states no spool.');
  // no turn can lie on the floor: Cat6A, 30 mm radius and 7.5 mm across, 67.5 mm against a floor 61.2 mm deep
  const cat = {...r, cables: [{...c, media: 'cat6a'}]};
  const fat = {chassisOf: F.chassisOf, route: {...F.ctxOf(cat), diameterOf: () => 7.5}};
  assert.equal(run(cat, {op: 'cable.slack', id: 'c1', at: TRAY}, fat).error, 'A turn of c1 is 67.5 mm across, and the floor of CM-01 tray is 61.2 mm deep.');
  // a member riding a bundle through it
  const c2 = {...r.cables[1], b: {item: 'i2', path: 'bay-2/module/lc4', view: 'front'}, route: [TRAY], routeEdited: true};
  const b = {...r, cables: [c, c2], bundles: [{id: 'b1', number: 2, label: '', members: [{cable: 'c1'}, {cable: 'c2'}], route: [TRAY]}]};
  assert.equal(run(b, {op: 'cable.slack', id: 'c1', at: TRAY}, {chassisOf: F.chassisOf, route: F.ctxOf(b)}).error,
    'c1 rides Bundle 2 through CM-01 tray: store its spare after it leaves the bundle.');
  // the shape of `at`, and what is not there
  assert.equal(run(r, {op: 'cable.slack', id: 'c1', at: {}}).error, 'cable.slack needs at as {item, via}, a duct or a tray, or {end}, a or b.');
  assert.equal(run(r, {op: 'cable.slack', id: 'c1', at: {item: 'i9', via: 'tray'}}).error,
    'i9 is not in the rack. The spare of c1 can go in CM-01 tray, or at an end ({end: a} or {end: b}).');
  assert.equal(run(r, {op: 'cable.slack', id: 'c99', at: TRAY}).error, 'That cable is no longer in the rack.');
  assert.equal(run(r, {op: 'cable.slack', id: 'c1', at: {end: 'a'}, form: 'coil'}).error, 'Spare left at an end has no form.');
  assert.deepEqual(run(r, {op: 'cable.slack', id: 'c1', at: TRAY, value: 0}), {error: 'cable.slack needs value, a number above 0.', index: 0});
  // with no routes known the place is recorded as given
  assert.equal(run(r, {op: 'cable.slack', id: 'c12', at: TRAY}, {chassisOf: F.chassisOf}).error, undefined);
  // clear: one place, then all; the key goes with the last, so nothing is said again
  const one = run(more.rack, {op: 'cable.slack.clear', id: 'c1', at: {end: 'b'}});
  assert.deepEqual(one.rack.cables[0].slack, [{item: 'i4', via: 'tray', form: 'serpentine', value: 0.3, unit: 'm'}]);
  const none = run(one.rack, {op: 'cable.slack.clear', id: 'c1'});
  assert.equal('slack' in none.rack.cables[0], false);
  assert.equal(run(none.rack, {op: 'cable.slack.clear', id: 'c1'}).noop, true);
  assert.equal('slack' in run(one.rack, {op: 'cable.slack.clear', id: 'c1', at: TRAY}).rack.cables[0], false);
  assert.deepEqual(Object.keys(COMMANDS['cable.slack'].args.properties).sort(), ['at', 'form', 'id', 'rack', 'unit', 'value']);
});

test('a route edit that takes the tray off the route keeps the entry and says so', () => {
  const {r} = trayRack({}, {slack: [TRAY]});
  const ctx = {chassisOf: F.chassisOf, route: F.ctxOf(r)};
  const reset = apply(r, {op: 'cable.route.reset', id: 'c1'}, ctx);
  assert.deepEqual(reset.rack.cables[0].slack, [TRAY], 'the entry is kept');
  const s = SL.slackOf(reset.rack, reset.rack.cables[0], F.ctxOf(reset.rack));
  assert.deepEqual([s.entries[0].ok, s.entries[0].why], [false, 'CM-01 tray is not on the route of c1.']);
});

// ── what a slack entry does not do ───────────────────────────────────────

test('routePath returns the same points with and without a slack entry, and a stated value is inside the stock size', () => {
  const {r, c} = trayRack();
  const ctx = F.ctxOf(r);
  const bare = R.routePath(r, c, ctx);
  for (const slack of [[TRAY], [{end: 'a', value: 0.2}], [], [{...TRAY, form: 'serpentine', value: 1.4}]]) {
    const withSlack = {...c, slack};
    assert.deepEqual(R.routePath({...r, cables: [withSlack]}, withSlack, ctx).points, bare.points, JSON.stringify(slack));
  }
  // need 0.36 m: a 1 m cord; with 0.5 m stated, 0.36 + 0.2 + 0.5 is past 1.01, so 1.5 m
  assert.equal(R.routedLength(r, c, ctx).value, 1);
  assert.equal(R.routedLength(r, {...c, slack: [{...TRAY, value: 0.44}]}, ctx).value, 1);
  assert.equal(R.routedLength(r, {...c, slack: [{...TRAY, value: 0.5}]}, ctx).value, 1.5);
  assert.equal(R.routedLength(r, {...c, slack: [{end: 'a', value: 1, unit: 'ft'}, {...TRAY, value: 0.3}]}, ctx).value, 1.5);
  // and the length the page keeps current holds it: need beside the size, and no `measured`
  const kept = R.withRoutedLengths({...r, cables: [{...c, slack: [{...TRAY, value: 0.5}]}]}, ctx).cables[0];
  assert.deepEqual(kept.length, {value: 1.5, unit: 'm', source: 'routed', need: 0.36});
  // an entered length is never touched
  const entered = {...c, length: {value: 3, unit: 'm', source: 'entered'}};
  assert.equal(R.withRoutedLengths({...r, cables: [entered]}, ctx).cables[0], entered);
});

// ── inspect, describe and the schedule ───────────────────────────────────

test('inspect tells no slack key from an empty list, and shows what is stored', async () => {
  const look = async slack => {
    const {r} = trayRack({}, slack === undefined ? {} : {slack});
    return Q.inspect(r, 'c1', {chassisOf: F.chassisOf, route: F.ctxOf(r)});
  };
  const none = await look(undefined), empty = await look([]), tray = await look([{...TRAY, value: 0.3}, {end: 'a'}]);
  assert.deepEqual(none.slack, {metres: 0.64, at_ends_m: 0.2, said: false, stored: [], unplaced_m: 0.44});
  assert.deepEqual(empty.slack, {metres: 0.64, at_ends_m: 0.2, said: true, stored: [], unplaced_m: 0.44});
  assert.deepEqual(tray.slack, {metres: 0.64, at_ends_m: 0.2, said: true, unplaced_m: 0,
    stored: [{item: 'i4', via: 'tray', form: 'coil', metres: 0.3, ok: true}, {end: 'a', metres: 0.14}]});
  assert.equal(none.length.need, 0.36);
  assert.deepEqual(none.spare_findings, [{kind: 'spare-unplaced', text: 'c1 has 0.44 m to store and no place for it.'}]);
  assert.equal('spare_findings' in empty, false);
  // describe carries one line for the rack, and none without the routes
  const r = R.withRoutedLengths(F.rack(), F.ctxOf(F.rack()));
  const lines = Q.describe(r, {chassisOf: F.chassisOf, route: F.ctxOf(r)}).split('\n');
  assert.ok(lines.includes('Spare: 8.15 m; 13 cords not placed.'), lines.slice(0, 4).join(' | '));
  assert.ok(!Q.describe(r, {chassisOf: F.chassisOf}).includes('Spare:'));
});

test('the cable schedule ends with spare and stored, and one note line for the rack', () => {
  assert.deepEqual(X.CABLE_COLUMNS.slice(-4), ['notes', 'spare', 'stored', 'straps']);
  const {r} = trayRack({}, {slack: [TRAY]});
  const ctx = F.ctxOf(r);
  const ends = new Map();
  const {rows, notes, columns} = X.cableScheduleRows(r, ends, r.items, null, {spare: SL.spareExports(r, ctx)});
  assert.deepEqual([rows[0].spare, rows[0].stored], [0.64, 'CM-01 tray, coil, 0.44 m; 0.2 m at the ends']);
  // a cable with no length is blank in both
  assert.deepEqual([rows[1].spare, rows[1].stored], ['', '']);
  assert.ok(notes.some(n => /^Spare: \d+(\.\d+)? m; \d+ cords? not placed\.$/.test(n)), notes.join(' | '));
  // the CSV: the two cells last, after the notes
  const csv = X.toCsv(columns, rows.slice(0, 1));
  assert.match(csv.split('\r\n')[0], /,status,notes,spare,stored,straps$/);
  assert.match(csv.split('\r\n')[1], /,0\.64,"CM-01 tray, coil, 0\.44 m; 0\.2 m at the ends",$/);
  // without `spare` the columns are there and blank, so the header is one
  const plain = X.cableScheduleRows(r, ends, r.items);
  assert.deepEqual([plain.columns, plain.rows[0].spare, plain.rows[0].stored], [X.CABLE_COLUMNS, '', '']);
});

test('a media named like something every object has is a media the tables do not know', async () => {
  const {mediaKind} = await import('../../../kit/rack/cable-rules.js');
  const r = F.rack(), ctx = F.ctxOf(r);
  for (const media of ['constructor', '__proto__', 'toString', 'hasOwnProperty']) {
    const c = {...r.cables[0], media};
    const p = R.routePath(r, c, ctx);
    assert.ok(p.points.every(q => [q.x, q.y, q.z].every(Number.isFinite)), `${media}: every point is a number`);
    const l = R.routedLength(r, c, ctx), plain = R.routedLength(r, {...c, media: ''}, ctx);
    // it routes and measures as a cable with no media does, and its length is never null in a saved file
    assert.deepEqual([l.value, Math.round(l.measured * 1e6)], [plain.value, Math.round(plain.measured * 1e6)], media);
    const kept = R.withRoutedLengths({...r, cables: [c]}, ctx).cables[0].length;
    assert.ok(kept.value > 0 && kept.need > 0, JSON.stringify(kept));
    assert.deepEqual(mediaKind(media), {family: null, mode: null});
  }
});

