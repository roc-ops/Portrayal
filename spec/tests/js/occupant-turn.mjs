// The kit's half of a turned occupant (#829), without a face: the `turn=`
// parameter, its gate, a configuration's own turns, the delta an untouched
// page writes, which turn a seat takes, the transform it is drawn at, the
// views a turn names and the held faces it reaches. test_occupant_turn_js.py
// reads the one JSON object this prints.
import {install} from './fake-dom.mjs';

const m = await import('../../../kit/swap.js');
install();

const out = {};
const tryOr = (f, fallback = 'threw') => { try { return f(); } catch (e) { return fallback; } };

// --- the URL ------------------------------------------------------------------
const state = {'ground-stud-1': 180, 'ground-studs-rear/stud-tr': 90, 'a~b,c': 270, zero: 0};
const enc = m.encodeTurns(state);
out.encoded = enc;
out.roundTrip = m.decodeTurns(enc);
out.encodedTwice = m.encodeTurns(m.decodeTurns(enc)) === enc;
const junk = ['', '~', '~90', 'x~', 'x~ninety', 'x~-90', 'x~90.5', 'x~90~1', '%E0%A4%A~90',
              '__proto__~90', 'constructor~90', 'x~9999', ',,,', 'a~90,,b~180', null, 42, {}];
out.junk = junk.map(s => tryOr(() => m.decodeTurns(s)));
out.encodedNothing = [m.encodeTurns({}), m.encodeTurns(null), m.encodeTurns({x: null}),
                      m.encodeTurns({x: 'up'})];
// a swap string and a turn string live side by side; neither decodes the other
out.swapUntouched = m.decodeSwaps('ground-stud-1~generic%2Fring-lug%401');
out.turnInSwap = m.decodeSwaps('ground-stud-1~generic%2Fring-lug%401~180');
out.search = m.searchWith('?device=mx150&swap=a~b', {turn: m.encodeTurns({'ground-stud-1': 180})});

// --- the gate -----------------------------------------------------------------
const stud = {id: 'ground-stud-1', interface: 'terminal-stud', turns: [0, 90, 180, 270],
              accepts: ['generic/ring-lug@1'], rotate: null, mate: [34, 6.5], lift: 8};
const pole = {id: 'pole', interface: 'terminal-stud', turns: null, accepts: ['generic/ring-lug@1']};
const sfp = {id: 'port-1', interface: 'sfp', turns: null, accepts: ['generic/sfp-lc@1']};
const casa = {name: 'c40g-ground-studs', ns: 'casa', major: 'v1',
              cages: [{id: 'stud-tr', interface: 'terminal-stud', turns: [0, 90, 180, 270]}]};
const compByRef = r => (String(r).startsWith('casa/c40g-ground-studs@1') ? casa : null);
out.accept = m.acceptTurns({'ground-stud-1': 90, pole: 90, 'port-1': 180, nowhere: 90,
                            'ground-stud-2': 0, 'ground-studs-rear/stud-tr': 270,
                            'ground-studs-rear/stud-xx': 90, 'ground-stud-1-occupant': 90},
                           {cages: [stud, pole, sfp], compByRef,
                            placementRef: p => (p === 'ground-studs-rear' ? 'casa/c40g-ground-studs@1' : null)});
out.acceptAngle = m.acceptTurns({'ground-stud-1': 45}, {cages: [stud]});

// --- a configuration's turns, and the delta ---------------------------------------
const cfg = {occupants: {'ground-stud-1': {ref: 'generic/ring-lug@1', turn: 90},
                         'ground-stud-0': 'generic/ring-lug@1',
                         'ground-studs-rear/stud-bl': {ref: 'generic/ring-lug@1', turn: 270},
                         'port-1': {ref: 'generic/sfp-lc@1'}}};
const built = m.builtTurns(cfg, [stud]);
out.built = built;
// with the device's own bays and the index, as the shell asks: a stud composed
// in a placed part is no bay, so its path takes no `module` step
out.builtCtx = m.builtTurns(cfg, [stud], {bays: [], compByRef,
  placementRef: p => (p === 'ground-studs-rear' ? 'casa/c40g-ground-studs@1' : null)});
out.untouched = m.encodeTurns(m.turnOverrides({cfgTurns: {...built}, built}));
out.touched = m.turnOverrides({cfgTurns: {...built, 'ground-stud-1': 180, 'ground-stud-0': 0}, built});
out.noCfg = [m.builtTurns(null), m.builtTurns({}), m.builtTurns({occupants: 'x'})];

// --- which turn a seat takes ---------------------------------------------------------
const book = {set: {'ground-stud-1': 270}, seat: {'ground-stud-1': {'generic/ring-lug@1': 180}}};
out.seatTurn = {
  chosen: m.seatTurn(stud, 'generic/ring-lug@1', book),
  def: m.seatTurn(stud, 'generic/ring-lug@1:1.0.0', {set: {}, seat: book.seat}),
  disallowed: m.seatTurn(stud, 'generic/ring-lug@1', {set: {'ground-stud-1': 45}, seat: book.seat}),
  none: m.seatTurn(stud, 'generic/ring-lug@1', null),
  pole: m.seatTurn(pole, 'generic/ring-lug@1', {set: {pole: 90}, seat: {pole: {'generic/ring-lug@1': 90}}}),
  nested: m.seatTurn({...stud, id: 'ground-studs-rear/stud-tr', key: 'ground-studs-rear/stud-tr'},
                     'generic/ring-lug@1', {seat: {'ground-studs-rear/stud-tr': {'generic/ring-lug@1': 90}}}),
};

// --- the transform it is drawn at ------------------------------------------------------
const lug = {size: {w: 5.5, h: 27.4}, mate: [2.75, 2.75]};
const turned = {...stud, rotate: 90};
out.transform = {
  t0: m.occupantTransform(stud, lug),
  t0explicit: m.occupantTransform(stud, lug, 0),
  t90: m.occupantTransform(stud, lug, 90),
  t180: m.occupantTransform(stud, lug, 180),
  host90t270: m.occupantTransform(turned, lug, 270),
  host90t0: m.occupantTransform(turned, lug, 0),
  rot: [m.seatRotate(stud, 0), m.seatRotate(stud, 90), m.seatRotate(turned, 270),
        m.seatRotate({rotate: 180}, 180), m.seatRotate({rotate: null}, -90)],
};
// the mate point lands on the cage's whatever the turn
const mateOf = (cage, t) => {
  const [x, y] = m.occupantAt(cage, lug, t);
  const cx = lug.size.w / 2, cy = lug.size.h / 2;
  const r = (m.seatRotate(cage, t) || 0) * Math.PI / 180;
  const dx = lug.mate[0] - cx, dy = lug.mate[1] - cy;
  return [x + cx + dx * Math.cos(r) - dy * Math.sin(r), y + cy + dx * Math.sin(r) + dy * Math.cos(r)];
};
out.mates = [0, 90, 180, 270].map(t => [mateOf(stud, t), mateOf(turned, t)]);
out.attrs = {
  stud: m.occupantAttrs(stud, 'generic/ring-lug@1', {version: '1.0.0'}, {}, 'x', 'x', 90)['data-seat-turn'],
  studNone: m.occupantAttrs(stud, 'generic/ring-lug@1', {version: '1.0.0'})['data-seat-turn'],
  pole: m.occupantAttrs(pole, 'generic/ring-lug@1', {version: '1.0.0'}, {}, 'x', 'x', 0)['data-seat-turn'] ?? null,
};

// --- the views a turn names ----------------------------------------------------------
const devIndex = {bays: {front: [], rear: []}, cages: {front: [sfp], rear: [stud]}};
out.views = {
  turnOnly: m.viewsToRewrite(devIndex, {}, {'ground-stud-1': 90}),
  swapOnly: m.viewsToRewrite(devIndex, {'port-1': 'generic/sfp-lc@1'}),
  both: m.viewsToRewrite(devIndex, {'port-1': null}, {'ground-stud-1': 90}).sort(),
  none: m.viewsToRewrite(devIndex, {}, {}),
};

// --- the held faces: a turn re-seats a face that holds the same ref ----------------------
const turns = {};
const seen = [];
const q = m.faceQueue({
  loadSkin: async r => r,
  seat: async (face, view, map) => { seen.push({view, map: {...map}}); return {applied: Object.keys(map).length}; },
  stamp: (k, v) => `${v ?? ''}~${turns[k] ?? ''}`,
});
const face = {};
const held = () => [['rear', face]];
await q.load(['rear'], {has: () => false, fetch: async () => face,
                        delta: () => ({'ground-stud-1': 'generic/ring-lug@1'}),
                        store: () => true, live: () => true});
const again = await q.swap({'ground-stud-1': 'generic/ring-lug@1'}, {held, live: () => true});
turns['ground-stud-1'] = 90;
const afterTurn = await q.swap({'ground-stud-1': 'generic/ring-lug@1'}, {held, live: () => true});
const sameTurn = await q.swap({'ground-stud-1': 'generic/ring-lug@1'}, {held, live: () => true});
out.queue = {again, afterTurn, sameTurn, seen: seen.length};

console.log(JSON.stringify(out));
