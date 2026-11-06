// spec/tests/js/rack-cable-colour.mjs
// THE COLOUR A CABLE IS DRAWN IN (#1028): its own, else the jacket colour its
// two seated ends agree on, else its named type's, else its media's. Each
// rule, the validation, the command key, the round trip through a file, what
// each export carries, and that nothing here changes a colour a rack was
// drawn in before, or lays a cable again.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, readdirSync} from 'node:fs';
import * as M from '../../../kit/rack/model.js';
import * as C from '../../../kit/rack/cable-rules.js';
import * as G from '../../../kit/rack/cable-geometry.js';
import * as P from '../../../kit/rack/ports.js';
import * as T from '../../../kit/rack/cable-types.js';
import * as R from '../../../kit/rack/route.js';
import * as X from '../../../kit/rack/export-data.js';
import * as D from '../../../kit/rack/dcim-rules.js';
import * as Q from '../../../kit/rack/queries.js';
import {COMMANDS, apply} from '../../../kit/rack/commands.js';
import {validate} from '../../../kit/rack/validate.js';
import {rackDiagram, CABLE_COLOURS} from '../../../kit/drawio.js';
import * as F from './cable-solids-fixture.mjs';
import {speedRack} from './speed-fixture.mjs';
import {sampleRack} from './bend-room-sample.mjs';
import {loadTree, outputsOf} from './speed-goldens.mjs';

// ── a catalogue of its own ──────────────────────────────────────────────
// A switch of four cages, and four cable ends: the generic end, which only
// DECLARES a jacket colour (a field with a default), two makers' ends that
// compose it and state one, and one that states it two parts down.
const BLACK = '#1c1c1c', AQUA = '#49eaf8', PURPLE = '#6b3fa0';
// What an AOC with no colour stated is drawn in (#1028): a deeper teal of the
// OM3 and OM4 aqua family (rack-aoc-colour.mjs holds how far it is from them).
const AOC_NOW = '#08788a';
const ENDS = ['generic/qsfp-cable@1', 'maker/aoc@1', 'maker/aec@1', 'maker/deep@1', 'maker/optic@1'];
const SLOTS = {sw: {default: 'base', bays: {front: [], rear: []},
  cages: {front: [1, 2, 3, 4].map(n => ({id: `port-${n}`, interface: 'qsfp', media: 'qsfp', accepts: ENDS, default: null})), rear: []},
  configs: [{name: 'base', bays: {}, occupants: {}}, {name: 'built', bays: {}, occupants: {'port-1': 'maker/aoc@1'}}]}};
const COMPONENTS = {
  'generic/qsfp-cable@1': {class: 'transceiver', attrs: {face: 'cable'},
    fields: {'jacket-color': {label: 'Jacket colour', type: 'text', default: BLACK}}},
  'maker/aoc@1': {class: 'transceiver', attrs: {'cable-kind': 'aoc'},
    parts: [{ref: 'generic/qsfp-cable@1', id: 'body', attrs: {'cable-od': 3.0, 'jacket-color': AQUA}}]},
  'maker/aec@1': {class: 'transceiver', attrs: {'cable-kind': 'aec'},
    parts: [{ref: 'generic/qsfp-cable@1', id: 'body', attrs: {'jacket-color': PURPLE}}]},
  'maker/deep@1': {class: 'transceiver', attrs: {'cable-kind': 'aoc'}, parts: [{ref: 'maker/aoc@1', id: 'inner'}]},
  'maker/optic@1': {class: 'transceiver', attrs: {media: 'fiber', mode: 'multimode', face: 'lc-duplex'}},
};
const compByRef = ref => { const k = ref == null ? null : String(ref).split(':')[0]; return k && Object.hasOwn(COMPONENTS, k) ? COMPONENTS[k] : null; };
const parts = {slotsOf: ref => (Object.hasOwn(SLOTS, ref) ? SLOTS[ref] : null), compByRef};
const chassisOf = ref => (ref === 'sw' ? {ru: 1, h: 43.6, d: 400, model: 'SW-4', default: 'base'} : null);
const ctx = {chassisOf, ...parts};
const end = (item, path = 'port-1', view = 'front') => ({item, path, view});

// Two switches, and one cable from port-1 of each. `a` and `b` are what is
// seated in each port-1 (null for an empty cage); `fields` are the item's.
function pair({a = null, b = null, fa = {}, fb = {}, media = 'aoc', cable = {}} = {}) {
  let r = M.newRack({name: 'Colour'});
  r = M.withItem(r, {ref: 'sw', cfg: 'base', ru: 1, label: 'sw-a', swaps: a ? {'port-1': a} : {}, fields: fa}).rack;
  r = M.withItem(r, {ref: 'sw', cfg: 'base', ru: 3, label: 'sw-b', swaps: b ? {'port-1': b} : {}, fields: fb}).rack;
  return C.withCable(r, {a: end('i1'), b: end('i2'), media, ...cable}).rack;
}
const readers = (rack, extra = {}) => ({jacketOf: P.jacketsFor(rack, {parts}), ...extra});
const drawn = (rack, extra) => C.cableColorOf(rack.cables[0], readers(rack, extra));

// ── what a colour is ────────────────────────────────────────────────────
test('a colour is # and three or six hex digits, kept as six in lower case; nothing else is one', () => {
  assert.equal(G.hexColor('#2BB3C8'), '#2bb3c8');
  assert.equal(G.hexColor('#abc'), '#aabbcc');
  assert.equal(G.hexColor('  #ABC '), '#aabbcc');
  for (const bad of ['red', 'aqua', '2bb3c8', '#2bb3c', '#2bb3c8ff', '#abcd', 'rgb(1,2,3)', 'url(#x)', '#gggggg', '', ' ', null, undefined, 0, 255, {}, [], true])
    assert.equal(G.hexColor(bad), null, JSON.stringify(bad));
});

test('parseColor: empty is no colour of its own, a hex colour is that colour, and anything else is refused with a sentence', () => {
  assert.deepEqual(C.parseColor(''), {ok: true, color: null});
  assert.deepEqual(C.parseColor('  '), {ok: true, color: null});
  assert.deepEqual(C.parseColor(null), {ok: true, color: null});
  assert.deepEqual(C.parseColor(undefined), {ok: true, color: null});
  assert.deepEqual(C.parseColor('#E8C547'), {ok: true, color: '#e8c547'});
  assert.deepEqual(C.parseColor('#0f0'), {ok: true, color: '#00ff00'});
  const sentence = 'A cable color is # and three or six hex digits, such as #2bb3c8, or empty for none of its own.';
  assert.equal(C.COLOR_REFUSED, sentence);
  for (const bad of ['red', 'black', '#12', 'e8c547', 7, {}, false]) assert.deepEqual(C.parseColor(bad), {ok: false, reason: sentence}, JSON.stringify(bad));
});

// ── the order ───────────────────────────────────────────────────────────
test('rule 1: the colour stated on the cable is drawn, whatever its ends, its type and its media say', () => {
  const l = {media: 'aoc', color: '#FF8800', jackets: [AQUA, AQUA], typeColor: PURPLE};
  assert.deepEqual(G.cableColor(l), {color: '#ff8800', from: 'cable'});
  assert.equal(G.colorOf(l), '#ff8800');
  // through a rack: two aqua ends, and the cable says orange
  const rack = pair({a: 'maker/aoc@1', b: 'maker/aoc@1', cable: {color: '#f80'}});
  assert.equal(rack.cables[0].color, '#ff8800');
  assert.deepEqual(drawn(rack, {typeColorOf: () => PURPLE}), {color: '#ff8800', from: 'cable'});
});

test('rule 2: with no colour of its own, two seated ends that state the same jacket colour give it', () => {
  assert.deepEqual(G.cableColor({media: 'aoc', jackets: [AQUA, '#49EAF8'], typeColor: PURPLE}), {color: AQUA, from: 'ends'});
  assert.deepEqual(drawn(pair({a: 'maker/aoc@1', b: 'maker/aoc@1'})), {color: AQUA, from: 'ends'});
  // a colour stated two parts down is still the part's own statement
  assert.deepEqual(drawn(pair({a: 'maker/deep@1', b: 'maker/aoc@1'})), {color: AQUA, from: 'ends'});
  // #abc and #aabbcc are one colour
  assert.equal(G.agreedJacket(['#ABC', '#aabbcc']), '#aabbcc');
});

test('rule 2 needs both ends: one seated end and one bare end is no agreement, and nor are two ends that differ', () => {
  const AOC = AOC_NOW;                                      // the media's
  assert.deepEqual(drawn(pair({a: 'maker/aoc@1', b: null})), {color: AOC, from: 'media'});
  assert.deepEqual(drawn(pair({a: null, b: 'maker/aoc@1'})), {color: AOC, from: 'media'});
  assert.deepEqual(drawn(pair({a: 'maker/aoc@1', b: 'maker/aec@1'})), {color: AOC, from: 'media'});
  // an end that has a part with no jacket at all (an optic) states none
  assert.deepEqual(drawn(pair({a: 'maker/aoc@1', b: 'maker/optic@1'})), {color: AOC, from: 'media'});
  for (const j of [[AQUA, null], [null, AQUA], [AQUA, PURPLE], [null, null], [AQUA], [AQUA, AQUA, AQUA], 'x', null, [AQUA, 'aqua']])
    assert.equal(G.agreedJacket(j), null, JSON.stringify(j));
  // and where the ends differ, the type decides before the media does
  assert.deepEqual(drawn(pair({a: 'maker/aoc@1', b: 'maker/aec@1'}), {typeColorOf: () => '#00ff00'}), {color: '#00ff00', from: 'type'});
});

test('a default is not a statement: two generic ends at their declared default do not turn the cable black', () => {
  const rack = pair({a: 'generic/qsfp-cable@1', b: 'generic/qsfp-cable@1', media: 'dac'});
  assert.equal(P.seatedJacket(rack.items[0], end('i1'), parts), null);
  assert.deepEqual(drawn(rack), {color: '#15171a', from: 'media'});
  // with every media, so that no cable between two generic ends is drawn in the default of the field
  for (const media of C.MEDIA) {
    const got = drawn(pair({a: 'generic/qsfp-cable@1', b: 'generic/qsfp-cable@1', media}));
    assert.equal(got.from, 'media', media);
    // a power cord is black by its media's own default (#1052 and #1053), which is no default read from the field
    if (media !== 'power') assert.notEqual(got.color, BLACK, media);
    else assert.equal(got.color, G.COLORS.power, media);
  }
  // the links of the plan carry nothing for them either
  assert.deepEqual(Object.keys(C.cablePlan(rack, readers(rack)).links[0]), ['id', 'media', 'purpose', 'from', 'to']);
});

test('a jacket colour set on the rack is a statement, the default\'s own colour included', () => {
  const set = v => ({'port-1-occupant': {'jacket-color': v}});
  // somebody chose black on both ends: that is said, and the cable is black
  const black = pair({a: 'generic/qsfp-cable@1', b: 'generic/qsfp-cable@1', fa: set(BLACK), fb: set(BLACK)});
  assert.deepEqual(drawn(black), {color: BLACK, from: 'ends'});
  // one end set, the other at its default: one statement, no agreement
  assert.equal(drawn(pair({a: 'generic/qsfp-cable@1', b: 'generic/qsfp-cable@1', fa: set('#ff0000')})).from, 'media');
  // the rack's word is ahead of the part's own
  const over = pair({a: 'maker/aoc@1', b: 'generic/qsfp-cable@1', fa: set('#FF0000'), fb: set('#f00')});
  assert.deepEqual(drawn(over), {color: '#ff0000', from: 'ends'});
  // a value that is no colour states nothing, and does not fall back to the part's aqua
  const named = pair({a: 'maker/aoc@1', b: 'maker/aoc@1', fa: set('red')});
  assert.equal(P.seatedJacket(named.items[0], end('i1'), parts), null);
  assert.equal(drawn(named).from, 'media');
  // an empty value is a field put back to its default
  assert.equal(P.seatedJacket(pair({a: 'maker/aoc@1', fa: set('')}).items[0], end('i1'), parts), AQUA);
});

test('the field command sets an end\'s jacket, and the cable follows it', () => {
  let rack = pair({a: 'generic/qsfp-cable@1', b: 'generic/qsfp-cable@1'});
  assert.equal(drawn(rack).from, 'media');
  for (const id of ['i1', 'i2']) rack = COMMANDS.field.run(rack, {id, path: 'port-1-occupant', key: 'jacket-color', value: '#ff00ff'}, ctx).rack;
  assert.deepEqual(drawn(rack), {color: '#ff00ff', from: 'ends'});
  rack = COMMANDS.field.run(rack, {id: 'i2', path: 'port-1-occupant', key: 'jacket-color', value: null}, ctx).rack;
  assert.deepEqual(drawn(rack), {color: AOC_NOW, from: 'media'});
});

test('what the configuration builds in a cage states its jacket as what a swap seats does', () => {
  let r = M.newRack();
  r = M.withItem(r, {ref: 'sw', cfg: 'built', ru: 1, label: 'a'}).rack;
  r = M.withItem(r, {ref: 'sw', cfg: 'built', ru: 3, label: 'b'}).rack;
  r = C.withCable(r, {a: end('i1'), b: end('i2'), media: 'aoc'}).rack;
  assert.deepEqual(drawn(r), {color: AQUA, from: 'ends'});
  // a path into the seated part is its port all the same
  assert.equal(P.seatedJacket(r.items[0], end('i1', 'port-1-occupant/body'), parts), AQUA);
});

test('a reader made for a rack reads what each device seats once, however many of its ports are cabled', () => {
  let rack = pair({a: 'maker/aoc@1', b: 'maker/aoc@1'});
  for (const n of [2, 3, 4]) rack = C.withCable(M.updateItem(M.updateItem(rack, 'i1', {swaps: {...rack.items[0].swaps, [`port-${n}`]: 'maker/aoc@1'}}),
    'i2', {swaps: {...rack.items[1].swaps, [`port-${n}`]: n === 4 ? 'maker/aec@1' : 'maker/aoc@1'}}), {a: end('i1', `port-${n}`), b: end('i2', `port-${n}`), media: 'aoc'}).rack;
  let asked = 0;
  const counted = {slotsOf: ref => { asked++; return parts.slotsOf(ref); }, compByRef};
  const jacketOf = P.jacketsFor(rack, {parts: counted});
  const colours = C.cablePlan(rack, {jacketOf}).links.map(l => G.cableColor(l));
  assert.deepEqual(colours.map(c => c.from), ['ends', 'ends', 'ends', 'media']);
  assert.equal(asked, 2, 'eight ends on two devices');
  // and the answers are those of reading each end on its own
  for (const c of rack.cables) for (const e of [c.a, c.b])
    assert.equal(jacketOf(e), P.seatedJacket(rack.items.find(i => i.id === e.item), e, parts));
});

test('an end is not read without the catalogue, on a removed device, an empty cage or an element id', () => {
  const rack = pair({a: 'maker/aoc@1', b: 'maker/aoc@1'});
  assert.equal(P.seatedJacket(rack.items[0], end('i1'), null), null);
  assert.equal(P.seatedJacket(rack.items[0], end('i1'), {slotsOf: () => null, compByRef}), null);
  assert.equal(P.seatedJacket(null, end('i9'), parts), null);
  assert.equal(P.seatedJacket(rack.items[0], end('i1', 'port-2'), parts), null);
  assert.equal(P.seatedJacket(rack.items[0], end('i1', 'port-1--occupant'), parts), null);
  assert.equal(P.jacketAt(rack, end('gone'), {parts}), null);
  // and with no reader at all a cable is its media's, as before
  assert.deepEqual(C.cableColorOf(rack.cables[0]), {color: AOC_NOW, from: 'media'});
});

test('what a page read of an end stands over the catalogue: a colour, or null for an end it found bare', () => {
  const rack = pair({a: 'maker/aoc@1', b: 'maker/aoc@1'});
  const key = e => C.endKey(e);
  const seen = j => new Map([[key(end('i1')), {info: null, reason: null, jacket: j}]]);
  assert.equal(P.jacketAt(rack, end('i1'), {ends: seen('#ABCDEF'), parts}), '#abcdef');
  assert.equal(P.jacketAt(rack, end('i1'), {ends: seen(null), parts}), null);
  assert.equal(P.jacketAt(rack, end('i1'), {ends: seen('aqua'), parts}), null);
  // an entry with no `jacket` key says nothing of it, and the catalogue answers
  assert.equal(P.jacketAt(rack, end('i1'), {ends: new Map([[key(end('i1')), {info: null, reason: null}]]), parts}), AQUA);
  // a page with no catalogue at all can still pass both ends
  const both = new Map([[key(end('i1')), {jacket: PURPLE}], [key(end('i2')), {jacket: '#6B3FA0'}]]);
  assert.deepEqual(C.cableColorOf(rack.cables[0], {jacketOf: P.jacketsFor(rack, {ends: both})}), {color: PURPLE, from: 'ends'});
});

test('rule 3: a named type\'s colour, where the table states one; a bare media type is never asked', () => {
  const types = {aoc: {id: 'aoc', media: 'aoc', jacket: {color: '#ff0000'}}, 'aoc-maker': {id: 'aoc-maker', media: 'aoc', jacket: {color: '#49EAF8'}},
                 'aoc-plain': {id: 'aoc-plain', media: 'aoc'}, 'aoc-odd': {id: 'aoc-odd', media: 'aoc', jacket: {color: 'aqua'}},
                 'aoc-flat': {id: 'aoc-flat', media: 'aoc', jacket: '#49eaf8'}};
  const typeColorOf = T.jacketLookup(types);
  const of = cable => C.cableColorOf({a: end('i1'), b: end('i2'), ...cable}, {typeColorOf});
  assert.deepEqual(of({media: 'aoc', type: 'aoc-maker'}), {color: AQUA, from: 'type'});
  assert.deepEqual(of({media: 'aoc', type: 'aoc-plain'}), {color: AOC_NOW, from: 'media'});
  assert.deepEqual(of({media: 'aoc', type: 'aoc-odd'}), {color: AOC_NOW, from: 'media'});
  assert.deepEqual(of({media: 'aoc', type: 'aoc-flat'}), {color: AOC_NOW, from: 'media'});
  assert.deepEqual(of({media: 'aoc', type: 'not-in-the-table'}), {color: AOC_NOW, from: 'media'});
  // the media's own type is not read for a cable that names no type: `COLORS` decides
  assert.deepEqual(of({media: 'aoc'}), {color: AOC_NOW, from: 'media'});
  assert.deepEqual(of({media: 'aoc', type: 'constructor'}), {color: AOC_NOW, from: 'media'});
  // agreeing ends are ahead of the type
  assert.deepEqual(G.cableColor({media: 'aoc', jackets: [PURPLE, PURPLE], typeColor: AQUA}), {color: PURPLE, from: 'ends'});
});

// ── no default changed ──────────────────────────────────────────────────
// The colours of main at dc96952ac, written out by hand, but for the AOC's,
// which #1028 made aqua.
const MAIN = {os2: '#e8c547', om3: '#2bb3c8', om4: '#2bb3c8', om5: '#9acd32', cat6: '#5aa7ff', cat6a: '#5aa7ff',
              dac: '#15171a', aoc: AOC_NOW, unset: '#9aa3ad', power: '#1c1c1c', ground: '#3f9b4b',
              // stack, usb and console: estimated shades, no source is held; each is its own colour
              stack: '#d9702a', usb: '#8e6bd1', console: '#c9588a'};
const mainColor = l => (l.media === 'copper' ? (l.purpose === 'management' ? '#9aa3ad' : '#5aa7ff') : (Object.hasOwn(MAIN, l.media) ? MAIN[l.media] : '#e8c547'));

test('rule 4, and no default changed: every media is the colour it was', () => {
  for (const media of C.MEDIA) assert.equal(G.colorOf({media}), MAIN[media], media);
  assert.deepEqual(C.MEDIA.map(m => MAIN[m]).length, 13);
  assert.deepEqual(C.MEDIA.filter(m => !Object.hasOwn(MAIN, m)), [], 'a media with no recorded colour');
  // the three new media are drawn in colours no other media has, so a stack, a USB and a console lead read apart on a plan
  const others = Object.entries(MAIN).filter(([k]) => !['stack', 'usb', 'console'].includes(k)).map(([, v]) => v);
  for (const m of ['stack', 'usb', 'console']) assert.ok(!others.includes(MAIN[m]) && new Set(['stack', 'usb', 'console'].map(k => MAIN[k])).size === 3, m);
  assert.equal(G.colorOf({media: 'aoc'}), AOC_NOW, 'an AOC is the teal of the multimode family');
  assert.equal(G.colorOf({media: 'unset'}), '#9aa3ad');
  assert.equal(G.colorOf({media: 'copper', purpose: 'server'}), '#5aa7ff');
  assert.equal(G.colorOf({media: 'copper', purpose: 'management'}), '#9aa3ad');
  assert.equal(G.colorOf({media: 'copper', purpose: 'toString'}), '#5aa7ff');
  for (const odd of ['', 'os1', 'toString', 'constructor', '__proto__', 'copper2']) assert.equal(G.colorOf({media: odd}), '#e8c547', odd);
  assert.deepEqual(G.cableColor({media: 'om5'}), {color: '#9acd32', from: 'media'});
  // the hero's jackets, and its plugs
  assert.deepEqual(G.JACKETS, {mm: '#2bb3c8', sm: '#e8c547', dac: '#15171a', cu: '#5aa7ff'});
  assert.deepEqual(['mm', 'sm', 'dac', 'cu', 'aoc', undefined].map(G.colorOfJacket), ['#2bb3c8', '#e8c547', '#15171a', '#5aa7ff', '#e8c547', '#e8c547']);
  assert.deepEqual(G.PLUGS, {sm: '#2a6fd4', mm: '#2bb3c8'});
  // a value on the link that is no colour is never drawn, and never black
  for (const bad of ['red', '#12', 7, null, {}]) assert.equal(G.colorOf({media: 'aoc', color: bad, typeColor: bad, jackets: [bad, bad]}), AOC_NOW, JSON.stringify(bad));
});

test('one table decides a media\'s colour: `COLORS`; a jacket of the hero\'s table moves no cable', () => {
  // every colour `JACKETS` names is an entry of `COLORS`
  const flat = [...Object.values(G.COLORS).filter(v => typeof v === 'string'), ...Object.values(G.COLORS.copper)];
  for (const [k, v] of Object.entries(G.JACKETS)) assert.ok(flat.includes(v), k);
  const rack = pair({media: 'om4'});
  const before = [G.colorOf({media: 'om4'}), G.colorOf(C.cablePlan(rack).links[0]), G.colorOf({media: 'aoc'})];
  const {mm, sm} = G.JACKETS, aoc = G.COLORS.aoc;
  try {
    // the other table says something else of every jacket: nothing drawn by its media moves
    G.JACKETS.mm = '#000000'; G.JACKETS.sm = '#000000'; G.JACKETS.aoc = '#2bb3c8';
    assert.deepEqual([G.colorOf({media: 'om4'}), G.colorOf(C.cablePlan(rack).links[0]), G.colorOf({media: 'aoc'})], before);
    // and `COLORS` is the one that is read
    G.COLORS.aoc = '#010203';
    assert.equal(G.colorOf({media: 'aoc'}), '#010203');
    assert.equal(G.colorOf(C.cablePlan(pair({media: 'aoc'})).links[0]), '#010203');
  } finally { G.JACKETS.mm = mm; G.JACKETS.sm = sm; delete G.JACKETS.aoc; G.COLORS.aoc = aoc; }
  assert.equal(G.colorOf({media: 'aoc'}), AOC_NOW);
});

// Every rack the recorded answers are read from (speed-goldens.mjs racksOf):
// the fixtures, the rack files, sixty generated racks and the speed racks.
test('no existing rack changes colour: every cable of every fixture is drawn as main drew it, and its link has main\'s keys', async () => {
  const K = await loadTree();
  const {racksOf} = await import('./speed-goldens.mjs');
  let racks = 0, cables = 0;
  const seen = new Set();
  for (const {name, rack} of racksOf(K)) {
    racks++;
    const plan = C.cablePlan(rack), plan3d = C.cablePlan3d(rack);
    assert.equal(plan.links.length, (rack.cables || []).length, name);
    (rack.cables || []).forEach((c, i) => {
      cables++;
      assert.ok(!('color' in c) && !('colorAsWritten' in c), `${name} ${c.id} states no color`);
      const want = mainColor({media: c.media || 'unset', purpose: c.purpose || ''});
      seen.add(want);
      for (const l of [plan.links[i], plan3d.links[i]]) {
        assert.deepEqual(Object.keys(l), ['id', 'media', 'purpose', 'from', 'to'], `${name} ${c.id}`);
        assert.equal(G.colorOf(l), want, `${name} ${c.id}`);
      }
      assert.deepEqual(C.cableColorOf(c), {color: want, from: 'media'}, `${name} ${c.id}`);
    });
  }
  assert.ok(racks >= 91 && cables >= 3900, `${racks} racks, ${cables} cables`);
  assert.ok(seen.size >= 5, `${seen.size} colours were compared`);
});

test('a rack file with no color key loads and saves as it did: no cable gains one', () => {
  const dir = new URL('../fixtures/racks/', import.meta.url);
  let cables = 0;
  for (const f of readdirSync(dir).filter(n => n.endsWith('.json'))) {
    const doc = M.parseDoc(JSON.parse(readFileSync(new URL(f, dir), 'utf8')));
    const text = M.serialize(doc);
    assert.ok(!/"color(AsWritten)?"/.test(text), f);
    assert.equal(M.serialize(M.parseDoc(text)), text, f);
    for (const r of doc.racks) cables += r.cables.length;
  }
  assert.ok(cables >= 5, `${cables} cables read`);
  // a version-4 cable as a kit before this one wrote it, key for key
  const old = {id: 'c1', a: end('i1'), b: end('i2'), media: 'aoc', purpose: 'uplink', label: 'A1', route: []};
  const doc = M.parseDoc({format: 'portrayal-rack', version: 4, racks: [{frame: {}, items: [], cables: [old]}]});
  assert.deepEqual(doc.racks[0].cables[0], old);
});

// ── the file ────────────────────────────────────────────────────────────
const SCHEMA = JSON.parse(readFileSync(new URL('../../schemas/rack.schema.json', import.meta.url)));
const docOf = cables => ({format: 'portrayal-rack', version: 4, racks: [{frame: {}, items: [{id: 'i1', ref: 'sw', ru: 1}, {id: 'i2', ref: 'sw', ru: 3}], cables}]});
const cab = extra => ({id: 'c1', a: end('i1'), b: end('i2'), media: 'aoc', purpose: '', label: '', route: [], ...extra});

test('a cable\'s color goes through a save and a load, and the schema describes it', () => {
  const doc = M.parseDoc(docOf([cab({color: '#49eaf8'})]));
  assert.equal(doc.racks[0].cables[0].color, '#49eaf8');
  assert.equal(doc.version, 4, 'the key needs no new version: a reader keeps a cable key it does not know');
  const text = M.serialize(doc), again = M.parseDoc(text);
  assert.deepEqual(again, doc);
  assert.equal(M.serialize(again), text);
  assert.deepEqual(validate(SCHEMA, JSON.parse(text)), []);
  assert.equal(SCHEMA.$defs.cable.properties.color.type, 'string');
  assert.ok(!SCHEMA.$defs.cable.required.includes('color'), 'the key is optional');
  // the schema refuses what the reader would not keep as a colour
  for (const bad of ['red', '#ABCDEF', '#abc', 'abcdef', 7]) {
    const d = JSON.parse(text); d.racks[0].cables[0].color = bad;
    assert.deepEqual(validate(SCHEMA, d).map(e => `${e.keyword} at /${e.path.join('/')}`),
      [`${typeof bad === 'string' ? 'pattern' : 'type'} at /racks/0/cables/0/color`], JSON.stringify(bad));
  }
});

test('the reader keeps a colour as six lower-case digits, and moves a value that is none aside, whole', () => {
  const read = color => M.parseDoc(docOf([cab({color})])).racks[0].cables[0];
  assert.equal(read('#ABC').color, '#aabbcc');
  assert.equal(read('#2BB3C8').color, '#2bb3c8');
  for (const bad of ['red', '', 7, {r: 1}, ['#fff'], false]) {
    const c = read(bad);
    assert.ok(!('color' in c), JSON.stringify(bad));
    assert.deepEqual(c.colorAsWritten, bad, JSON.stringify(bad));
    assert.deepEqual(C.cableColorOf(c), {color: AOC_NOW, from: 'media'}, 'drawn by its media, never black');
    assert.deepEqual(validate(SCHEMA, JSON.parse(M.serialize(M.parseDoc(docOf([cab({color: bad})]))))), []);
  }
  assert.ok(!('color' in read(null)) && !('colorAsWritten' in read(null)));
  assert.ok(!('color' in read(undefined)) && !('colorAsWritten' in read(undefined)));
  // and what was moved aside survives the next save and load
  const once = M.parseDoc(docOf([cab({color: 'red'})]));
  assert.deepEqual(M.parseDoc(M.serialize(once)), once);
});

// ── the commands ────────────────────────────────────────────────────────
test('cable.add takes a color; cable.update sets it, changes it and clears it; a value that is none is refused', () => {
  const bare = {...pair(), cables: []};
  const run = (op, rack, args) => COMMANDS[op].run(rack, args, ctx);
  const added = run('cable.add', bare, {a: end('i1'), b: end('i2'), media: 'aoc', color: '#49EAF8'});
  assert.equal(added.rack.cables[0].color, '#49eaf8');
  assert.ok(!('color' in run('cable.add', bare, {a: end('i1'), b: end('i2'), media: 'aoc'}).rack.cables[0]));
  assert.ok(!('color' in run('cable.add', bare, {a: end('i1'), b: end('i2'), color: null}).rack.cables[0]));
  assert.deepEqual(run('cable.add', bare, {a: end('i1'), b: end('i2'), color: 'aqua'}), {error: C.COLOR_REFUSED});

  const id = added.rack.cables[0].id;
  const changed = run('cable.update', added.rack, {id, color: '#f80'});
  assert.equal(changed.rack.cables[0].color, '#ff8800');
  assert.equal(changed.summary, `Edited cable ${id}.`);
  // the same colour again, however it is written, changes nothing
  assert.equal(run('cable.update', changed.rack, {id, color: '#FF8800'}).rack, changed.rack);
  assert.equal(run('cable.update', changed.rack, {id, color: '#f80'}).rack, changed.rack);
  // cleared by null and by an empty text, and then its media decides again
  for (const none of [null, '', '  ']) {
    const cleared = run('cable.update', changed.rack, {id, color: none});
    assert.ok(!('color' in cleared.rack.cables[0]), JSON.stringify(none));
    assert.deepEqual(C.cableColorOf(cleared.rack.cables[0]), {color: AOC_NOW, from: 'media'});
  }
  // clearing what is not set changes nothing: the very same rack
  const plain = run('cable.add', bare, {a: end('i1'), b: end('i2')}).rack;
  assert.equal(run('cable.update', plain, {id: 'c1', color: null}).rack, plain);
  // refused, and the rack is left as it was
  for (const bad of ['red', '#12', 'rgb(0,0,0)']) assert.deepEqual(run('cable.update', changed.rack, {id, color: bad}), {error: C.COLOR_REFUSED}, bad);
  // everything else about the cable stays
  const {color: _c, ...rest} = changed.rack.cables[0], {color: _d, ...was} = added.rack.cables[0];
  assert.deepEqual(rest, was);
});

test('through apply, as a page\'s tools call it: set, clear, a refusal that names the color, and a value of the wrong kind', () => {
  const rack = {...pair(), cables: []};
  const ok = apply(rack, [{op: 'cable.add', a: end('i1'), b: end('i2'), media: 'dac', color: '#abc', as: 'x'},
                          {op: 'cable.update', id: '@x', color: '#123456'}], ctx);
  assert.equal(ok.error, undefined, JSON.stringify(ok.error));
  assert.equal(ok.rack.cables[0].color, '#123456');
  const off = apply(ok.rack, {op: 'cable.update', id: 'c1', color: null}, ctx);
  assert.ok(!('color' in off.rack.cables[0]));
  assert.equal(off.step, true, 'clearing a colour is an undo step');
  assert.deepEqual(apply(ok.rack, {op: 'cable.update', id: 'c1', color: 'teal'}, ctx), {error: C.COLOR_REFUSED, index: 0});
  // a number is refused by the arguments, before the command runs
  assert.deepEqual(apply(ok.rack, {op: 'cable.update', id: 'c1', color: 5}, ctx), {error: 'cable.update needs color, some text.', index: 0});
  // the table an agent reads names the key on both commands
  for (const op of ['cable.add', 'cable.update']) assert.deepEqual(COMMANDS[op].args.properties.color.type, ['string', 'null'], op);
});

test('a colour named at all replaces one the loader moved aside', () => {
  const rack = M.parseDoc(docOf([cab({color: 'red'})])).racks[0];
  const set = COMMANDS['cable.update'].run(rack, {id: 'c1', color: '#ff0000'}, ctx).rack.cables[0];
  assert.deepEqual([set.color, 'colorAsWritten' in set], ['#ff0000', false]);
  const cleared = COMMANDS['cable.update'].run(rack, {id: 'c1', color: null}, ctx).rack.cables[0];
  assert.deepEqual(['color' in cleared, 'colorAsWritten' in cleared], [false, false]);
  // a patch that does not name the colour leaves it
  assert.equal(COMMANDS['cable.update'].run(rack, {id: 'c1', label: 'x'}, ctx).rack.cables[0].colorAsWritten, 'red');
});

// ── what draws and lists it ─────────────────────────────────────────────
test('the plans carry what decides a colour, and only what says something; colorOf of a link is the colour to draw', () => {
  const own = pair({a: 'maker/aoc@1', b: 'maker/aoc@1', cable: {color: '#ff8800'}});
  const ends = pair({a: 'maker/aoc@1', b: 'maker/aoc@1'});
  const differ = pair({a: 'maker/aoc@1', b: 'maker/aec@1'});
  const none = pair();
  for (const plan of [C.cablePlan, C.cablePlan3d]) {
    const link = (rack, extra) => plan(rack, readers(rack, extra)).links[0];
    assert.deepEqual([link(own).color, link(own).jackets, G.colorOf(link(own))], ['#ff8800', undefined, '#ff8800']);
    assert.deepEqual([link(ends).jackets, G.colorOf(link(ends))], [[AQUA, AQUA], AQUA]);
    assert.deepEqual([link(differ).jackets, G.colorOf(link(differ))], [[AQUA, PURPLE], AOC_NOW]);
    assert.deepEqual(Object.keys(link(none)), ['id', 'media', 'purpose', 'from', 'to']);
    assert.deepEqual([link(none, {typeColorOf: () => '#0F0'}).typeColor, G.colorOf(link(none, {typeColorOf: () => '#0F0'}))], ['#00ff00', '#00ff00']);
    // with no reader, a link carries the cable's own colour and nothing else
    assert.deepEqual([plan(own).links[0].color, plan(ends).links[0].jackets], ['#ff8800', undefined]);
  }
  // 2D and 3D agree, cable for cable
  for (const rack of [own, ends, differ, none])
    assert.equal(G.colorOf(C.cablePlan(rack, readers(rack)).links[0]), G.colorOf(C.cablePlan3d(rack, readers(rack)).links[0]));
});

test('the 3D scene is told when a colour changes: sameCables3d for the cable\'s own, colorsKey for one from its ends', () => {
  const rack = pair({a: 'generic/qsfp-cable@1', b: 'generic/qsfp-cable@1'});
  const tinted = C.updateCable(rack, 'c1', {color: '#ff8800'});
  assert.equal(C.sameCables3d(rack, tinted), false);
  assert.equal(C.sameCables3d(tinted, C.updateCable(tinted, 'c1', {color: '#FF8800'})), true);
  assert.equal(C.sameCables3d(tinted, C.updateCable(tinted, 'c1', {color: null})), false);
  assert.equal(C.sameCables3d(rack, C.updateCable(rack, 'c1', {label: 'x'})), true);
  // a jacket set on both ends changes no cable, so the cables read the same; the key of the colours does not
  let set = rack;
  for (const id of ['i1', 'i2']) set = COMMANDS.field.run(set, {id, path: 'port-1-occupant', key: 'jacket-color', value: '#00ff00'}, ctx).rack;
  assert.equal(C.sameCables3d(rack, set), true);
  assert.equal(C.colorsKey(rack, readers(rack)), `c1=${AOC_NOW}`);
  assert.equal(C.colorsKey(set, readers(set)), 'c1=#00ff00');
  assert.equal(C.colorsKey(tinted), 'c1=#ff8800');
});

test('a bundle\'s band is its members\' one colour, and no colour at all when they differ', () => {
  assert.deepEqual(G.bundleColor(['#2bb3c8', '#2BB3C8', '#2bb3c8']), {color: '#2bb3c8', mixed: false});
  assert.deepEqual(G.bundleColor(['#2bb3c8', '#e8c547']), {color: null, mixed: true});
  assert.deepEqual(G.bundleColor([]), {color: null, mixed: false});
  assert.deepEqual(G.bundleColor(undefined), {color: null, mixed: false});
  assert.deepEqual(G.bundleColor(['#abc']), {color: '#aabbcc', mixed: false});
  // from a rack: two OM4 cords and one given its own colour
  let rack = pair({media: 'om4'});
  rack = C.withCable(rack, {a: end('i1', 'port-2'), b: end('i2', 'port-2'), media: 'om4'}).rack;
  const colors = r => r.cables.map(c => C.cableColorOf(c).color);
  assert.deepEqual(G.bundleColor(colors(rack)), {color: '#2bb3c8', mixed: false});
  assert.deepEqual(G.bundleColor(colors(C.updateCable(rack, 'c2', {color: '#ff0000'}))), {color: null, mixed: true});
});

const dev = (id, u) => ({id, name: id, u, ru: 1, faces: {front: {svg: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"/>',
  vb: [0, 0, 10, 10], ports: [{id: 'port-1', path: 'port-1', cls: 'port', x: 1, y: 1, w: 2, h: 2}]}}});
const strokeOf = (rows, cableStyle) => /id="cable-c1"><mxCell style="([^"]*)"/.exec(rackDiagram(
  [{label: 'R', faces: ['front'], racks: [{label: 'R', units: 4, mounted: [dev('i1', 1), dev('i2', 3)]}]}], {cables: rows, cableStyle}))?.[1];
const landed = rack => new Map(rack.cables.flatMap(c => [c.a, c.b]).map(e => [C.endKey(e), {info: null, reason: null}]));

test('draw.io: a cable whose colour is said carries it and is drawn in it; one coloured by its media is filed as before', () => {
  const rows = (rack, extra = {}) => X.drawioCables(rack, {ends: landed(rack), idOf: id => id, drawn: () => true, parts, ...extra}).cables;
  const base = {id: 'c1', a: {item: 'i1', path: 'port-1'}, b: {item: 'i2', path: 'port-1'}, media: 'aoc', purpose: '', label: ''};
  // by its media: exactly the row of main, with no `color`
  assert.deepEqual(rows(pair()), [base]);
  assert.deepEqual(rows(pair({a: 'maker/aoc@1', b: 'maker/aec@1'})), [base]);
  assert.deepEqual(rows(pair({a: 'generic/qsfp-cable@1', b: 'generic/qsfp-cable@1'})), [base]);
  // its own, its ends', its type's
  assert.equal(rows(pair({cable: {color: '#f80'}}))[0].color, '#ff8800');
  assert.equal(rows(pair({a: 'maker/aoc@1', b: 'maker/aoc@1'}))[0].color, AQUA);
  assert.equal(rows(pair(), {typeColorOf: () => PURPLE})[0].color, PURPLE);
  // without the parts lists the ends are not read, as an export that passes none had it
  assert.deepEqual(X.drawioCables(pair({a: 'maker/aoc@1', b: 'maker/aoc@1'}), {ends: landed(pair()), idOf: id => id, drawn: () => true}).cables, [base]);
  // the vendor draws it: the stated colour ahead of the media's entry, and the map's entry without one
  assert.match(strokeOf(rows(pair({cable: {color: '#f80'}})), {aoc: '#111111'}), /strokeColor=#ff8800;$/);
  assert.match(strokeOf(rows(pair()), {aoc: '#111111'}), /strokeColor=#111111;$/);
  assert.match(strokeOf(rows(pair()), undefined), new RegExp(`strokeColor=${AOC_NOW};$`), "an AOC is drawn as the kit draws it");
  assert.match(strokeOf([{...base, color: 'red'}], {aoc: '#111111'}), /strokeColor=#111111;$/, 'a value that is no colour is not drawn');
  // a page's own style function is handed the row, colour and all
  assert.equal(strokeOf(rows(pair({cable: {color: '#f80'}})), c => `strokeColor=${c.color};`), 'strokeColor=#ff8800;');
});

// ── the AOC default, and the draw.io palette that follows the kit (#1028) ──
test('an AOC with no colour stated is the multimode family\'s teal, not OM4\'s aqua, in the explorer\'s resolver', () => {
  assert.equal(G.colorOf({media: 'aoc'}), AOC_NOW);
  assert.equal(G.COLORS.aoc, AOC_NOW);
  assert.notEqual(G.colorOf({media: 'aoc'}), G.colorOf({media: 'om4'}));
  assert.equal(G.colorOf(C.cablePlan(pair({media: 'aoc'})).links[0]), AOC_NOW);
  assert.deepEqual(drawn(pair({media: 'aoc'})), {color: AOC_NOW, from: 'media'});
  // the hero's jacket for multimode, and its plug, are OM4's entry as before
  assert.equal(G.JACKETS.mm, G.COLORS.om4);
  assert.equal(G.PLUGS.mm, G.COLORS.om4);
});

test('every other COLORS entry is as it was', () => {
  assert.deepEqual({...G.COLORS, aoc: undefined}, {os2: '#e8c547', copper: {server: '#5aa7ff', management: '#9aa3ad'},
    om3: '#2bb3c8', om4: '#2bb3c8', om5: '#9acd32', cat6: '#5aa7ff', cat6a: '#5aa7ff', dac: '#15171a', aoc: undefined,
    unset: '#9aa3ad', power: '#1c1c1c', ground: '#3f9b4b', stack: '#d9702a', usb: '#8e6bd1', console: '#c9588a'});
});

// A cable as a rack plan hands it to the draw.io writer, and the same cable as
// the explorer draws it.
const edgeOf = (media, purpose = '') => ({id: 'c1', a: {item: 'i1', path: 'port-1'}, b: {item: 'i2', path: 'port-1'},
  media: X.drawioMediaKey({media, purpose}), purpose, label: ''});
const KNOWN = [...C.MEDIA, 'copper', 'os1', 'om1', 'om2', 'cat5e', 'cu', 'mm', 'sm', 'mystery', 'constructor', ''];

test('draw.io: every media the kit knows is stroked in the colour the explorer draws it', () => {
  for (const media of KNOWN) for (const purpose of media === 'copper' ? ['server', 'management', 'Management', '', 'toString'] : ['']) {
    const want = G.colorOf({media, purpose});
    assert.match(strokeOf([edgeOf(media, purpose)], undefined), new RegExp(`strokeColor=${want};$`), `${media}/${purpose}`);
  }
  // and through a rack's own plan, which is where a page gets both
  for (const media of C.MEDIA) {
    const rack = pair({media});
    const rows = X.drawioCables(rack, {ends: landed(rack), idOf: id => id, drawn: () => true, parts}).cables;
    assert.match(strokeOf(rows, undefined), new RegExp(`strokeColor=${G.colorOf(C.cablePlan(rack).links[0])};$`), media);
  }
});

test('draw.io: CABLE_COLOURS is derived from the kit, and a key it names is the colour the explorer gives that media', () => {
  assert.deepEqual(Object.keys(CABLE_COLOURS), ['dac', 'aoc', 'cu', 'mm', 'sm', 'om1', 'om2', 'om3', 'om4', 'om5',
    'os1', 'os2', 'cat5e', 'cat6', 'cat6a', 'default']);
  for (const [k, v] of Object.entries(CABLE_COLOURS)) assert.equal(v, G.colorOf({media: k}), k);
});

test('draw.io: a cable\'s own colour, and a caller\'s map, still win over the kit\'s', () => {
  const row = edgeOf('aoc');
  assert.match(strokeOf([{...row, color: '#f80'}], undefined), /strokeColor=#f80;$/);
  assert.match(strokeOf([{...row, color: '#f80'}], {aoc: '#111111'}), /strokeColor=#f80;$/);
  assert.match(strokeOf([row], {aoc: '#111111'}), /strokeColor=#111111;$/);
  assert.match(strokeOf([edgeOf('dac')], {aoc: '#111111'}), /strokeColor=#15171a;$/, 'a media the map does not name is the kit\'s');
  assert.match(strokeOf([edgeOf('copper', 'management')], {'copper-management': '#222222'}), /strokeColor=#222222;$/);
  // a map's `default` is still what an unknown media takes
  assert.match(strokeOf([edgeOf('mystery')], {default: '#333333'}), /strokeColor=#333333;$/);
  assert.match(strokeOf([edgeOf('aoc')], {default: '#333333'}), new RegExp(`strokeColor=${AOC_NOW};$`));
});

test('NetBox and Nautobot: the color column is the cable\'s own colour, six digits with no #, and blank otherwise', () => {
  const row = (rack, target) => D.cableImportRows({rack, target, names: X.uniqueNames(rack.items), kept: new Set(rack.items.map(i => i.id)),
    ends: landed(rack), parts, resolve: e => ({ok: true, name: e.path, type: 'dcim.interface'})}).rows[0];
  for (const target of ['netbox', 'nautobot']) {
    assert.equal(row(pair({cable: {color: '#49EAF8'}}), target).color, '49eaf8', target);
    assert.match(row(pair({cable: {color: '#abc'}}), target).color, /^[0-9a-f]{6}$/, 'what both validators take');
    // a colour worked out from the ends is not a recorded fact of the cable
    assert.equal(row(pair({a: 'maker/aoc@1', b: 'maker/aoc@1'}), target).color, '', target);
    assert.equal(row(pair(), target).color, '', target);
    assert.equal(D.CABLE_IMPORT_COLUMNS[target].filter(c => c === 'color').length, 1, 'the column was there already');
  }
});

test('describe and inspect show a cable\'s own colour, and say nothing of one it does not state', async () => {
  const plain = pair(), tinted = pair({cable: {color: '#ff8800'}});
  const line = r => Q.describe(r, {chassisOf}).split('\n').find(l => l.includes('c1:'));
  assert.ok(line(tinted).endsWith('aoc, #ff8800'), line(tinted));
  assert.ok(line(plain).endsWith('aoc'), line(plain));
  assert.equal((await Q.inspect(tinted, 'c1', {chassisOf})).color, '#ff8800');
  assert.ok(!('color' in await Q.inspect(plain, 'c1', {chassisOf})));
});

// ── speed: a colour is no part of a lay (#1031) ─────────────────────────
test('a colour lays nothing again: no path reads it, every path is the one kept, and checkKept stays quiet', () => {
  const made = speedRack(M, F, {cables: 60, bundles: 2, seed: 31}), rack = made.rack;
  const paths = (r, c) => r.cables.map(x => JSON.stringify(R.routePath(r, x, c)));
  const before = paths(rack, made.ctxOf(rack));
  assert.ok(before.filter(p => p !== 'null').length >= 50, 'the rack has paths');
  // every cable given a colour, by the command, as a page would
  let tinted = rack;
  for (const c of rack.cables) tinted = COMMANDS['cable.update'].run(tinted, {id: c.id, color: '#ff8800'}, {chassisOf: made.chassisOf}).rack;
  assert.ok(tinted.cables.every(c => c.color === '#ff8800'));
  // the same paths, in a context made anew, with what was kept
  assert.deepEqual(paths(tinted, made.ctxOf(tinted)), before);
  // and the kept paths are what a rack read for the first time gives
  assert.deepEqual(paths(structuredClone(tinted), made.ctxOf(tinted)), before);
  // with the check on, a kept path that was not what the rack gives now would throw
  const checked = r => ({...made.ctxOf(r), checkKept: true});
  assert.doesNotThrow(() => paths(tinted, checked(tinted)));
  let again = tinted;
  for (const c of rack.cables.slice(0, 20)) again = COMMANDS['cable.update'].run(again, {id: c.id, color: null}, {chassisOf: made.chassisOf}).rack;
  assert.deepEqual(paths(again, checked(again)), before);
  // NO LAY READS THE KEY: each cable's `color` is a getter that counts, out of
  // reach of a spread, so only code that asks for the colour by name counts.
  let reads = 0;
  const watched = {...tinted, cables: tinted.cables.map(c => {
    const {color, ...rest} = c;
    return Object.defineProperty(rest, 'color', {enumerable: false, get() { reads++; return color; }});
  })};
  const ctxW = made.ctxOf(watched);
  assert.deepEqual(paths(watched, ctxW), before);
  for (const c of watched.cables) { R.resolveRoute(watched, c, ctxW); R.routedLength(watched, c, ctxW); R.ringMarks(watched, c, ctxW); R.spareOf(watched, c, ctxW); }
  R.bendFindings(watched, ctxW); R.bodyFindings(watched, ctxW); R.coverFindings(watched, ctxW); R.fill(watched, ctxW); R.capacityOver(watched, ctxW);
  assert.equal(reads, 0, 'route.js asked for a cable\'s colour');
  // and the getter does count when the colour is asked for
  assert.equal(C.cableColorOf(watched.cables[0]).color, '#ff8800');
  assert.ok(reads > 0);
});

test('of every recorded answer, a cable\'s own colour moves only the ones that show it', async () => {
  const K = await loadTree();
  const made = speedRack(M, F, {cables: 40, bundles: 2, seed: 32});
  const tinted = {...made.rack, cables: made.rack.cables.map((c, i) => (i % 2 ? c : {...c, color: '#ff8800'}))};
  const of = r => outputsOf(K, {rack: r, ctxOf: made.ctxOf, chassisOf: made.chassisOf}, {exact: true});
  const [was, is] = [await of(made.rack), await of(tinted)];
  const moved = Object.keys(was).filter(k => was[k] !== is[k]).sort();
  // both DCIM files (the column), and what describes a cable to an agent
  assert.deepEqual(moved, ['dcim-nautobot', 'dcim-netbox', 'describe', 'inspect']);
  assert.ok(Object.keys(was).length >= 30);
});

// ── the generated racks draw as they did (a second set, with the readers on) ──
test('with the readers passed and nothing stated, a generated rack is still drawn by its media', () => {
  let cables = 0;
  for (const seed of [1, 7, 23]) {
    const s = sampleRack(M, F, seed), rack = s.rack;
    const r = {jacketOf: P.jacketsFor(rack, {ends: new Map(), parts}), typeColorOf: T.jacketLookup({})};
    for (const l of C.cablePlan(rack, r).links) { cables++; assert.equal(G.colorOf(l), mainColor(l)); assert.ok(!('jackets' in l) && !('typeColor' in l) && !('color' in l)); }
  }
  assert.ok(cables >= 60, `${cables} cables`);
});
