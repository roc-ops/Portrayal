// spec/tests/js/rack-dc-checks.mjs
// THE CHECKS OF docs/dc-power-design.md section 6, on a cable whose ends are DC
// ports or poles: warnings only, each said where both sides state what it
// reads, and the three facts a check can miss said once as notes. The ends'
// facts are the `dc` key of dc-ports-fixture.mjs's catalogue; the pure checks
// are also given hand-made ends.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import * as Q from '../../../kit/rack/queries.js';
import * as CR from '../../../kit/rack/cable-rules.js';
import {apply, COMMANDS} from '../../../kit/rack/commands.js';
import {ctx, CABLE_TYPES, SLOTS} from './dc-ports-fixture.mjs';
import * as PE from './power-ends-fixture.mjs';

// ── ends made by hand ────────────────────────────────────────────────────
const pole = (role, path) => ({role, path: path ?? `x/${role}`});
const dc = (roles, rest = {}) => ({path: 'x/in', end: 'port', direction: 'input', voltage: {nominal: -48}, 'rating-a': null, awg: null, side: null,
  poles: roles.map((r, i) => pole(r, `x/in-${i}`)), ...rest});
const src = (roles, rest = {}) => dc(roles, {path: 'y/out', direction: 'output', poles: roles.map((r, i) => pole(r, `y/out-${i}`)), ...rest});
const info = d => ({family: 'power', mode: 'dc', role: d.direction === 'output' ? 'outlet' : 'inlet', dc: d});
const checks = (a, b, type) => CR.dcFeedChecks(info(a), info(b), type === undefined ? {} : {type});
const crossed = list => list.filter(w => /crossed/.test(w));
const TYPE2 = {conductors: [{role: 'unstated', awg: 14}, {role: 'unstated', awg: 14}], 'ampacity-a': 15, unverified: true};

// ── 1: the pairs (the match with dc.yaml is test_kit_dc_matches.py) ──────
test('the kit holds the pairs and the roles it compares by', () => {
  assert.deepEqual([...CR.DC_ROLES].sort(), ['batt', 'gnd', 'neg', 'pos', 'rtn', 'unstated']);
  assert.equal(CR.DC_MATCHES.filter(m => m.when === 'negative-voltage').length, 2);
});

// ── 2: polarity ──────────────────────────────────────────────────────────
test('polarity: RTN / BATT to RTN / BATT says nothing; to BATT / RTN each conductor is crossed', () => {
  assert.deepEqual(checks(src(['rtn', 'batt']), dc(['rtn', 'batt'])).warnings, []);
  assert.deepEqual(crossed(checks(src(['rtn', 'batt']), dc(['batt', 'rtn'])).warnings),
    ['A is RTN where B is BATT: the feed is crossed.', 'A is BATT where B is RTN: the feed is crossed.']);
  // the same pole by pole, with the other pairs of the registry
  assert.deepEqual(crossed(checks(src(['pos', 'neg']), dc(['pos', 'neg'], {voltage: {nominal: 24}}), undefined).warnings), []);
  assert.deepEqual(crossed(checks(src(['pos', 'neg'], {voltage: {nominal: 24}}), dc(['neg', 'pos'], {voltage: {nominal: 24}})).warnings),
    ['A is POS where B is NEG: the feed is crossed.', 'A is NEG where B is POS: the feed is crossed.']);
});

test('polarity: the first sentence of the list is the polarity one, in mismatch too', () => {
  const a = info(src(['rtn', 'batt'])), b = info(dc(['batt', 'rtn']));
  const said = CR.mismatch('power', a, b);
  assert.equal(said[0], 'A is RTN where B is BATT: the feed is crossed.');
  assert.deepEqual(said.slice(0, 2), CR.dcFeedChecks(a, b).warnings.slice(0, 2));
  const other = CR.mismatch('power', {...a, mode: 'ac'}, b);
  assert.ok(other.indexOf('The ends differ: A is AC power, B is DC power.') > 0, 'the existing sentences follow');
});

test('polarity: batt to neg holds on a negative end, is crossed on a positive one, and is neither where no voltage is stated', () => {
  const feed = src(['batt', 'rtn']);
  assert.deepEqual(crossed(checks(feed, dc(['neg', 'pos'], {voltage: {nominal: -48}})).warnings), []);
  assert.deepEqual(crossed(checks(feed, dc(['neg', 'pos'], {voltage: {nominal: 24}})).warnings),
    ['A is BATT where B is NEG: the feed is crossed.', 'A is RTN where B is POS: the feed is crossed.']);
  const none = checks(feed, dc(['neg', 'pos'], {voltage: null}));
  assert.deepEqual(crossed(none.warnings), []);
  assert.deepEqual(none.warnings, [], 'and nothing else is said as a warning');
  assert.deepEqual(none.notes, ['x/in states no voltage; the feed\'s voltage is not checked.'], 'the missing voltage is a note');
});

test('polarity: a single conductor from a BATT pole to a RTN pole is crossed, and to a BATT pole is not', () => {
  const one = (role, i, rest = {}) => dc(['batt', 'rtn'], {end: 'pole', pole: i, role, ...rest});
  assert.deepEqual(crossed(checks(src(['batt', 'rtn'], {end: 'pole', pole: 0, role: 'batt'}), one('rtn', 1)).warnings), ['A is BATT where B is RTN: the feed is crossed.']);
  assert.deepEqual(crossed(checks(src(['batt', 'rtn'], {end: 'pole', pole: 0, role: 'batt'}), one('batt', 0)).warnings), []);
  // a port to a pole compares conductor 0 with the pole, and says nothing of the conductor the pole has no end for
  assert.deepEqual(crossed(checks(src(['batt', 'rtn']), one('rtn', 1)).warnings), ['A is BATT where B is RTN: the feed is crossed.']);
});

test('polarity: a ground pole is no pole of a feed and is compared with nothing', () => {
  assert.deepEqual(checks(src(['batt', 'gnd']), dc(['batt', 'rtn'])).warnings, []);
});

// ── 3: the stand-in ──────────────────────────────────────────────────────
test('an unstated pole is never called crossed, and the note of it is said once per pole', () => {
  const a = src(['unstated', 'unstated']), b = dc(['rtn', 'batt']);
  const got = checks(a, b);
  assert.deepEqual(got.warnings, []);
  assert.deepEqual(got.notes.filter(n => /Polarity/.test(n)), ['Polarity of y/out-0 is not stated; checked by position.', 'Polarity of y/out-1 is not stated; checked by position.']);
  // on either side, and the stated pole opposite one is not warned about
  const both = checks(dc(['unstated', 'batt'], {direction: 'output', path: 'y/out'}), dc(['unstated', 'rtn']));
  assert.deepEqual(crossed(both.warnings), ['A is BATT where B is RTN: the feed is crossed.'], 'the stated pair is still compared');
  assert.deepEqual(both.notes.filter(n => /Polarity/.test(n)), ['Polarity of x/in-0 is not stated; checked by position.']);
});

// ── 4: voltage ───────────────────────────────────────────────────────────
test('voltage: signs that differ, and a source outside the load\'s range', () => {
  const rb = ['batt', 'rtn'];
  assert.deepEqual(checks(src(rb), dc(rb, {voltage: {nominal: 24}})).warnings, ['-48 V into a +24 V input.']);
  assert.deepEqual(checks(src(rb), dc(rb, {voltage: {nominal: -48, range: [-40.5, -57]}})).warnings, []);
  assert.deepEqual(checks(src(rb, {voltage: {nominal: -24}}), dc(rb, {voltage: {nominal: -48, range: [-40.5, -57]}})).warnings,
    ['Source nominal -24 V is outside the load\'s -40.5 to -57.']);
  assert.deepEqual(checks(src(rb, {voltage: {nominal: -60}}), dc(rb, {voltage: {nominal: -48, range: [-40.5, -57]}})).warnings,
    ['Source nominal -60 V is outside the load\'s -40.5 to -57.']);
  // a load that states no range is not judged against one
  assert.deepEqual(checks(src(rb, {voltage: {nominal: -24}}), dc(rb)).warnings, []);
});

test('voltage: with no output end the signs only, and a port that states none is a note and no warning', () => {
  const rb = ['batt', 'rtn'];
  assert.deepEqual(checks(dc(rb, {voltage: {nominal: -48}}), dc(rb, {voltage: {nominal: 24}})).warnings, ['The ends differ in sign: A is -48 V, B is +24 V.']);
  assert.deepEqual(checks(dc(rb, {voltage: {nominal: -24, range: [-40, -57]}}), dc(rb, {voltage: {nominal: -48, range: [-40.5, -57]}})).warnings, []);
  const miss = checks(src(rb, {voltage: null}), dc(rb, {voltage: null}));
  assert.deepEqual(miss.warnings, []);
  assert.deepEqual(miss.notes.filter(n => /voltage/.test(n)),
    ['y/out states no voltage; the feed\'s voltage is not checked.', 'x/in states no voltage; the feed\'s voltage is not checked.']);
  // a range alone is no nominal
  assert.deepEqual(checks(src(rb), dc(rb, {voltage: {range: [-40, -57]}})).warnings, []);
});

// ── 5: conductors against poles ──────────────────────────────────────────
test('conductors: the type\'s count against the end\'s poles, and its gauge against the end\'s awg', () => {
  const rb = ['batt', 'rtn'];
  const three = checks(src(rb), dc(['batt', 'rtn', 'gnd']), TYPE2);
  assert.deepEqual(three.warnings.filter(w => /conductor/.test(w)), ['A two-conductor feed to a three-pole port (end B).']);
  const pole1 = checks(src(rb), dc(rb, {end: 'pole', pole: 1, role: 'rtn'}), TYPE2);
  assert.deepEqual(pole1.warnings.filter(w => /conductor/.test(w)), ['A two-conductor feed to one pole (end B).']);
  assert.deepEqual(checks(src(rb), dc(rb), TYPE2).warnings, [], 'two conductors to two poles, awg not stated at the end');
  assert.deepEqual(checks(src(rb), dc(rb, {awg: [12]}), TYPE2).warnings, ['14 AWG where the end takes 12 (end B).']);
  assert.deepEqual(checks(src(rb), dc(rb, {awg: [10, 12, 14]}), TYPE2).warnings, []);
  assert.deepEqual(checks(src(rb, {awg: [12]}), dc(rb, {awg: [12]}), TYPE2).warnings.filter(w => /AWG/.test(w)),
    ['14 AWG where the end takes 12 (end A).', '14 AWG where the end takes 12 (end B).']);
});

test('conductors: with no type there is no warning and one note; a type that states no conductors reads as none', () => {
  const rb = ['batt', 'rtn'];
  const NOTE = 'The cable names no DC feed type; its conductors are not checked against the poles.';
  assert.deepEqual(checks(src(rb), dc(rb), null).notes, [NOTE]);
  assert.deepEqual(checks(src(rb), dc(rb), {media: 'power'}).notes, [NOTE]);
  assert.deepEqual(checks(src(rb), dc(rb), null).warnings, []);
  assert.deepEqual(checks(src(rb), dc(rb)).notes, [], 'a type that was not read is not said to be missing');
  assert.deepEqual(checks(src(rb), dc(rb), TYPE2).notes, []);
  // a side that is no half of an A/B pair is not a missing fact
  assert.deepEqual(checks(src(rb, {side: null}), dc(rb, {side: null}), TYPE2).notes, []);
});

// ── 6: A and B kept to their sides ───────────────────────────────────────
test('sides: a feed from side A to a B terminal; quiet where either is not stated', () => {
  const rb = ['batt', 'rtn'];
  assert.deepEqual(checks(src(rb, {side: 'a'}), dc(rb, {side: 'b'})).warnings, ['Feed A lands on a B terminal.']);
  assert.deepEqual(checks(src(rb, {side: 'a'}), dc(rb, {side: 'a'})).warnings, []);
  assert.deepEqual(checks(src(rb, {side: 'a'}), dc(rb, {side: null})).warnings, []);
  assert.deepEqual(checks(src(rb, {side: null}), dc(rb, {side: 'b'})).warnings, []);
});

// ── 7: a protector against the load ──────────────────────────────────────
test('protector: a breaker below the load\'s current, and above the cable\'s ampacity; quiet where one is not stated', () => {
  const rb = ['batt', 'rtn'];
  assert.deepEqual(checks(src(rb, {'rating-a': 30}), dc(rb, {'rating-a': 40})).warnings, ['30 A breaker on a 40 A load.']);
  assert.deepEqual(checks(src(rb, {'rating-a': 40}), dc(rb, {'rating-a': 40})).warnings, []);
  assert.deepEqual(checks(src(rb, {'rating-a': null}), dc(rb, {'rating-a': 40})).warnings, []);
  assert.deepEqual(checks(src(rb, {'rating-a': 30}), dc(rb, {'rating-a': null})).warnings, []);
  assert.deepEqual(checks(src(rb, {'rating-a': 60}), dc(rb), TYPE2).warnings, ['60 A breaker on a 14 AWG feed (ampacity 15 A, an estimate).']);
  assert.deepEqual(checks(src(rb, {'rating-a': 15}), dc(rb), TYPE2).warnings, []);
  assert.deepEqual(checks(src(rb, {'rating-a': 60}), dc(rb), {...TYPE2, 'ampacity-a': undefined}).warnings, [], 'no ampacity, no warning');
  assert.deepEqual(checks(src(rb, {'rating-a': 60}), dc(rb), null).warnings, [], 'no type, no warning');
});

// ── 8: direction ─────────────────────────────────────────────────────────
test('direction: two outputs give the existing sentence, once', () => {
  const rb = ['batt', 'rtn'];
  const said = CR.mismatch('power', info(src(rb)), info(src(rb)));
  assert.equal(said.filter(s => /Both ends are/.test(s)).length, 1);
  assert.equal(said.filter(s => /outlets/.test(s)).length, 1);
  assert.deepEqual(CR.mismatch('power', info(dc(rb)), info(dc(rb))), ['Both ends are inlets: a power cable runs from an outlet to an inlet.']);
  assert.deepEqual(checks(src(rb), src(rb)).warnings, []);
});

// ── 9: a cable with no DC end says what it said ──────────────────────────
test('mismatch with three arguments says what it said before for a cable with no DC end', () => {
  const fiber = {family: 'fiber', mode: 'single-mode'};
  assert.deepEqual(CR.mismatch('cat6a', fiber, {family: 'copper', mode: null}),
    ['The ends differ: A is fiber, B is copper.', 'Cat 6A copper does not suit end A, which is fiber.']);
  const ac = {family: 'power', mode: 'ac', role: 'inlet'};
  assert.deepEqual(CR.mismatch('power', ac, ac), ['Both ends are inlets: a power cable runs from an outlet to an inlet.']);
  assert.deepEqual(CR.mismatch('power', ac, {family: 'power', mode: 'dc', role: 'outlet'}), ['The ends differ: A is AC power, B is DC power.']);
  assert.deepEqual(CR.mismatch('power', ac, {...ac, role: 'outlet', note: 'the plug is in question'}), ['End B: the plug is in question.']);
  assert.deepEqual(CR.mismatch('os2', null, null), []);
  assert.deepEqual(CR.dcFeedChecks(ac, {family: 'power', mode: 'dc', role: 'outlet'}, {type: null}), {warnings: [], notes: []}, 'one DC family end is not a DC end');
  assert.deepEqual(CR.dcFeedChecks(null, null), {warnings: [], notes: []});
});

// ── the catalogue's feeds: the commands, the queries ─────────────────────
const add = (rack, ref, ru, label) => M.withItem(rack, {ref, cfg: 'base', ru, label}).rack;
const end = (item, path, view = 'rear') => ({item, path, view});
// fuse-1 (i1), load-1 (i2), plus-1 (i3), tri-1 (i4), dc-1 (i5), pdu-1 (i6)
let RACK = M.newRack();
for (const [ref, ru, label] of [['fuse', 40, 'fuse-1'], ['load', 35, 'load-1'], ['plus', 30, 'plus-1'], ['tri', 25, 'tri-1'], ['dc', 20, 'dc-1'], ['pdu', 15, 'pdu-1']])
  RACK = add(RACK, ref, ru, label);
const A1 = end('i1', 'output-a1/output'), A2 = end('i1', 'output-a2/output'), B1 = end('i1', 'output-b1/output'), N1 = end('i1', 'output-n1/output');
const L0 = end('i2', 'psu-0/module/input'), L1 = end('i2', 'psu-1/module/input');
const L0_BATT = end('i2', 'psu-0/module/terminal-48v'), L1_BATT = end('i2', 'psu-1/module/terminal-48v'), L1_RTN = end('i2', 'psu-1/module/terminal-rtn');
const PLUS0 = end('i3', 'psu-0/module/input'), PLUS1 = end('i3', 'psu-1/module/input'), PLUS2 = end('i3', 'psu-2/module/input');
const TRI0 = end('i4', 'psu-0/module/input'), DCQ = end('i5', 'psu-2/module/input');
const OUT = end('i6', 'outlet-front-1', 'front'), OUT2 = end('i6', 'outlet-front-2', 'front');
const withTypes = {...ctx, cableTypes: CABLE_TYPES};
const full = rack => ({...withTypes, cableFacts: PE.oldPage(), drawnAt: PE.drawnAt(rack)});
const run = (rack, cmds, c = withTypes) => apply(rack, cmds, c);
const texts = (res, kind) => res.findings.filter(f => f.kind === kind).map(f => f.text);
// a rack file may hold a cable's `type`; the commands do not set one
const typed = (rack, type) => ({...rack, cables: rack.cables.map(c => ({...c, type}))});
const cabled = (rack, ...cables) => { const r = run(rack, cables.map(c => ({op: 'cable.add', media: 'power', ...c}))); assert.equal(r.error, undefined); return r.rack; };

test('cable.add says which DC port or pole each end landed on, and returns the checks, polarity first', () => {
  const one = run(RACK, [{op: 'cable.add', a: A1, b: L0, media: 'power'}]);
  assert.equal(one.summary, 'Added cable c1: end A on the DC port output-a1/output, end B on the DC port psu-0/module/input.');
  assert.deepEqual(one.findings, [{kind: 'warning', text: '30 A breaker on a 40 A load.'},
    {kind: 'note', text: 'The cable names no DC feed type; its conductors are not checked against the poles.'}]);
  const pole = run(RACK, [{op: 'cable.add', a: B1, b: L1_BATT, media: 'power'}]);
  assert.equal(pole.summary, 'Added cable c1: end A on the DC port output-b1/output, end B on the BATT pole of psu-1/module/input.');
  assert.deepEqual(pole.findings.map(f => f.kind), ['note'], 'one BATT conductor to a BATT pole: nothing to warn of');
  // a feed to a +24 V supply: each conductor crossed, and the polarity first of everything said
  const wrong = run(RACK, [{op: 'cable.add', a: A2, b: PLUS0, media: 'power'}]);
  assert.deepEqual(texts(wrong, 'warning'), ['A is BATT where B is POS: the feed is crossed.', 'A is RTN where B is NEG: the feed is crossed.', '-48 V into a +24 V input.']);
  assert.equal(wrong.findings[0].kind, 'warning');
  assert.equal(wrong.findings.at(-1).kind, 'note', 'the notes follow the warnings');
});

test('cable.add reads the cable types table when ctx gives it, and a cable with no DC end is as it was', () => {
  const rack = typed(cabled(RACK, {a: B1, b: L0}), 'dc-feed-2x14awg');
  const big = run(rack, [{op: 'cable.update', id: 'c1', b: L1}]);
  assert.equal(big.error, undefined);
  assert.deepEqual(texts(big, 'warning'), ['14 AWG where the end takes 12 (end B).', '60 A breaker on a 14 AWG feed (ampacity 15 A, an estimate).']);
  assert.equal(big.findings.some(f => f.kind === 'note'), false, 'a named DC type needs neither the type note nor polarity notes');
  // the same table is not read when ctx does not give it
  assert.deepEqual(texts(run(rack, [{op: 'cable.update', id: 'c1', b: L1}], ctx), 'warning'), []);
  // no DC end: today's summary, word for word, and none of the findings
  const plain = run(RACK, [{op: 'cable.add', a: OUT, b: OUT2, media: 'power'}]);
  assert.equal(plain.summary, 'Added cable c1.');
  assert.deepEqual(plain.findings, []);
  assert.equal(run(RACK, [{op: 'cable.add', a: OUT, b: OUT2}], ctx).summary, 'Added cable c1.');
  assert.equal(run(RACK, [{op: 'cable.add', a: OUT, b: OUT2}], {chassisOf: ctx.chassisOf}).summary, 'Added cable c1.', 'and without the catalogue');
});

test('cable.update says where a moved DC end landed and checks it the same', () => {
  const rack = cabled(RACK, {a: A2, b: L0});
  const moved = run(rack, [{op: 'cable.update', id: 'c1', b: PLUS0}]);
  assert.match(moved.summary, /^Moved end B of cable c1 to .*plus-1.*\. End B is on the DC port psu-0\/module\/input\.$/);
  assert.deepEqual(texts(moved, 'warning').slice(0, 2), ['A is BATT where B is POS: the feed is crossed.', 'A is RTN where B is NEG: the feed is crossed.']);
  const relabel = run(rack, [{op: 'cable.update', id: 'c1', label: 'feed'}]);
  assert.equal(relabel.summary, 'Edited cable feed.');
  assert.deepEqual(relabel.findings, [], 'an edit that moves no end is not checked again');
  const plain = cabled(RACK, {a: OUT, b: OUT2});
  const away = run(plain, [{op: 'cable.update', id: 'c1', b: end('i6', 'outlet-rear-1')}]);
  assert.equal(away.error, undefined);
  assert.deepEqual(away.findings, []);
  assert.doesNotMatch(away.summary, /DC/);
});

// ── 6: both supplies of a device from one side ───────────────────────────
test('both supplies of a device fed from side A: inspect, describe and the cable.add that makes it true say so', async () => {
  const first = run(RACK, [{op: 'cable.add', a: A1, b: L0, media: 'power'}]);
  assert.equal(first.findings.some(f => /fed from side/.test(f.text)), false, 'one supply fed says nothing');
  const second = run(first.rack, [{op: 'cable.add', a: A2, b: L1, media: 'power'}]);
  const SAID = 'Both supplies of load-1 are fed from side A.';
  assert.deepEqual(texts(second, 'warning'), [SAID]);
  const item = await Q.inspect(second.rack, 'i2', full(second.rack));
  assert.equal(item.feed_side.text, SAID);
  assert.deepEqual([item.feed_side.side, item.feed_side.cables], ['a', ['c1', 'c2']]);
  assert.match(Q.describe(second.rack, withTypes), /Findings: .*load-1.*side A/);
  assert.equal(Object.hasOwn(await Q.inspect(first.rack, 'i2', full(first.rack)), 'feed_side'), false, 'only when there is one');
  assert.doesNotMatch(Q.describe(first.rack, withTypes), /Findings/);
  // one of the two on side B, or on an output that states no side: nothing
  const mixed = cabled(RACK, {a: A1, b: L0}, {a: B1, b: L1});
  assert.equal(Object.hasOwn(await Q.inspect(mixed, 'i2', full(mixed)), 'feed_side'), false);
  const unsided = cabled(RACK, {a: A1, b: L0}, {a: N1, b: L1});
  assert.equal(Object.hasOwn(await Q.inspect(unsided, 'i2', full(unsided)), 'feed_side'), false);
  assert.equal(run(cabled(RACK, {a: A1, b: L0}), [{op: 'cable.add', a: N1, b: L1, media: 'power'}]).findings.some(f => /fed from side/.test(f.text)), false);
  // the same device with a supply fed by something that is no DC output: not claimed
  assert.equal(run(cabled(RACK, {a: A1, b: L0}), [{op: 'cable.add', a: OUT, b: L1, media: 'power'}]).findings.some(f => /fed from side/.test(f.text)), false);
  // and without the catalogue
  assert.deepEqual(Q.sideFindings(second.rack, {chassisOf: ctx.chassisOf}), []);
});

// ── the cable's own inspect and the free-port answer ─────────────────────
test('inspect of a DC cable says the checks first, with the type when ctx gives the table', async () => {
  const rack = cabled(RACK, {a: A2, b: PLUS0});
  const got = await Q.inspect(rack, 'c1', full(rack));
  assert.deepEqual(got.mismatch.slice(0, 3), ['A is BATT where B is POS: the feed is crossed.', 'A is RTN where B is NEG: the feed is crossed.', '-48 V into a +24 V input.']);
  const heavy = typed(cabled(RACK, {a: B1, b: L1}), 'dc-feed-2x14awg');
  const t = await Q.inspect(heavy, 'c1', full(heavy));
  assert.ok(t.mismatch.includes('60 A breaker on a 14 AWG feed (ampacity 15 A, an estimate).'));
  const noTable = await Q.inspect(heavy, 'c1', {...full(heavy), cableTypes: undefined});
  assert.equal(noTable.mismatch.some(s => /ampacity/.test(s)), false, 'a type nobody read is not judged');
  // suggestMedia says the checks that need no type
  const said = await Q.suggestMedia(RACK, A2, PLUS0, full(RACK));
  assert.equal(said.media, 'power');
  assert.equal(said.warnings[0], 'A is BATT where B is POS: the feed is crossed.');
});

// a three-pole port and a port of unstated poles, from the catalogue
test('a three-pole port and a port of unstated poles, from the catalogue', () => {
  const moved = run(typed(cabled(RACK, {a: A1, b: L0}), 'dc-feed-2x12awg'), [{op: 'cable.update', id: 'c1', b: TRI0}]);
  assert.equal(moved.error, undefined);
  assert.deepEqual(texts(moved, 'warning'), ['A two-conductor feed to a three-pole port (end B).', '30 A breaker on a 12 AWG feed (ampacity 20 A, an estimate).']);
  const q = run(RACK, [{op: 'cable.add', a: A1, b: DCQ, media: 'power'}]);
  assert.ok(texts(q, 'note').includes('Polarity of psu-2/module/t1 is not stated; checked by position.'));
  assert.ok(texts(q, 'note').includes('psu-2/module/input states no voltage; the feed\'s voltage is not checked.'));
  assert.deepEqual(crossed(texts(q, 'warning')), []);
});

// ── 11: a terminal drawn as an element of a supply that states no DC port ─
const elemPage = () => async (rack, extra = []) => {
  const ends = new Map();
  for (const e of [...(rack.cables || []).flatMap(c => [c.a, c.b]), ...extra]) {
    const cut = e.path.lastIndexOf('/module/'), bayPath = cut < 0 ? null : e.path.slice(0, cut);
    const bay = SLOTS.elem.bays.rear.find(b => b.id === bayPath);
    const facts = {item: true, drawing: true, port: false, cage: false, occupied: false,
                   holder: bayPath ? {path: bayPath, part: ctx.compByRef(bay?.default)?.attrs?.model ?? null} : null};
    ends.set(`${e.item}|${e.view}|${e.path}`, {facts, info: {family: null, mode: null}, reason: CR.looseReason(e, facts)});
  }
  return {seats: {}, ends};
};
test('a terminal drawn on a supply that declares no DC port says so; the old sentence is kept for every other end', async () => {
  const rack = cabled(add(M.newRack(), 'elem', 20, 'elem-1'), {a: end('i1', 'psu-0/module/terminal-48v'), b: end('i1', 'card-0/module/terminal-48v')},
    {a: end('i1', 'psu-0/module/nothing'), b: end('i1', 'psu-1/module/led-art')}, {a: end('i1', 'psu-0/module/terminal-rtn'), b: end('i1', 'psu-1/module/terminal-48v')});
  const c = {...withTypes, cableFacts: elemPage()};
  const rows = (await Q.looseEnds(rack, c)).ends.map(e => `${e.cable} ${e.side}: ${e.reason}`);
  assert.deepEqual(rows, [
    'c1 a: terminal-48v is drawn on PSU-EL, which declares no DC port',
    'c1 b: card-0 holds CARD-EL, which has no port terminal-48v',        // a card is no power part
    'c2 a: psu-0 holds PSU-EL, which has no port nothing',               // a path that names no element of the part
    'c2 b: psu-1 holds PSU-ELP, which has no port led-art',              // a supply that states a DC port
    'c3 a: terminal-rtn is drawn on PSU-EL, which declares no DC port']);
});

// ── 12: the words an agent reads ─────────────────────────────────────────
test('the words an agent reads name a DC port and a pole, within the table\'s limits', () => {
  const add = COMMANDS['cable.add'], upd = COMMANDS['cable.update'];
  const path = add.args.properties.a.properties.path.description;
  assert.equal(path, 'The port, outlet or DC port, as the free ports name it (port-1, outlet-a2, psu-0/module/input); a DC pole by its own path.');
  assert.ok(path.length <= 150);
  assert.equal(upd.args.properties.a.properties.path.description, path);
  for (const d of [add.description, upd.description]) { assert.ok(d.length <= 500); assert.doesNotMatch(d, /\w\(\)|Explorer|portrayal\.dev|Rack Builder/); }
  assert.match(add.description, /DC feed lands on a DC port or on one pole of it/);
  assert.match(add.description, /summary says which/);
  assert.match(add.description, /findings carry its DC checks, polarity first/);
  assert.match(upd.description, /A moved DC end is checked the same/);
  assert.equal(Object.hasOwn(add.args.properties, 'type') || Object.hasOwn(upd.args.properties, 'type'), false, 'no type argument');
});
