// An optic the kit seats in a cage ON A CARD must be the optic the build seats.
//
// The build (render.py `_seat_nested_occupants`, #484 R2) draws such an optic
// INSIDE the card's group, positioned by the card-frame mate points. The kit
// reads the card's cages off the drawing (`nestedCages`) and seats through the
// same `applyOccupantOverrides` a device cage uses. test_nested_cage_seat_js.py
// renders fitted copies, hands this script the REAL built face (fake-dom JSON),
// the components.json entries and the compiled skins, and compares what comes
// back with what render.py wrote. Checking the kit against itself would prove
// nothing.
//
// Cases, chosen by argv[2]:
//   parity    - stdin JSON; nestedCages + applyOccupantOverrides on the built
//               face with its optics stripped, and per key what the kit seated: parent, transform,
//               attributes, children, and how many optics the cage holds
//   overrides - applyOccupantOverrides on a nested key, on a fake DOM
//   race      - two swaps in flight on one nested cage
const m = await import('../../../kit/swap.js');
const mode = process.argv[2];

import {Node, DOC, build, install} from './fake-dom.mjs';
install();

const attrsOf = n => Object.fromEntries(n.attributes.map(x => [x.name, x.value]));
const occupantsOf = (root, key) =>
  root.querySelectorAll(`[data-for="${key}"][data-behaviour="occupies"]`);

// ---------------------------------------------------------------- parity
if (mode === 'parity') {
  let raw = '';
  for await (const chunk of process.stdin) raw += chunk;
  const {devices} = JSON.parse(raw);
  const out = [];
  for (const {device, face, comps, skins, overrides} of devices) {
    const root = build(face);
    const compByRef = ref => comps[ref] || null;
    const cages = m.nestedCages(root, compByRef);
    const loadSkin = async ref => comps[ref] && skins[ref]
      ? {comp: comps[ref], text: skins[ref]} : null;
    const before = Object.fromEntries(Object.keys(overrides)
      .map(k => [k, occupantsOf(root, k).length]));
    const res = await m.applyOccupantOverrides(root, cages, overrides, loadSkin);
    const empty = n => n.tagName === 'style' && !n.children.length;
    const seated = {};
    for (const key of Object.keys(overrides)) {
      const occ = occupantsOf(root, key);
      const [g] = occ;
      const cage = cages.find(c => c.id === key);
      seated[key] = {
        count: occ.length,
        parent: g?.parentNode?.getAttribute('data-path') ?? null,
        lastChild: g ? g.parentNode.children.at(-1) === g : null,
        transform: g?.getAttribute('transform') ?? null,
        attrs: g ? attrsOf(g) : null,
        children: g ? [...g.descendants()].filter(n => !empty(n))
          .map(n => ({t: n.tagName, a: attrsOf(n)})) : null,
        entry: cage ? {id: cage.id, cage: cage.cage, modulePath: cage.modulePath,
                       moduleId: cage.moduleId, carrier: cage.carrier,
                       moduleIsElement: cage.module instanceof Node,
                       mate: cage.mate, rotate: cage.rotate, lift: cage.lift,
                       mirror: cage.mirror} : null,
      };
    }
    out.push({device, before, result: res, cageIds: cages.map(c => c.id), seated});
  }
  console.log(JSON.stringify(out));
}

// ---------------------------------------------------------------- fake cards
// A face with a card in `front-6` (a flat bay) and one in `front-7` (a bay 3
// mm down, as draw_bay writes a sunk bay's data-z-lift) - the same component
// in both, so the only difference between them is the depth.
const OPTIC = {
  'generic/sfp-lc@1': {name: 'sfp-lc', version: '1.0.0',
                       size: {w: 13.55, h: 8.55, d: 47.5}, mate: [6.775, 4.275]},
  'generic/sfp-lc-simplex@2': {name: 'sfp-lc-simplex', version: '2.0.0',
                               size: {w: 13.55, h: 8.55, d: 47.5}, mate: [6.775, 4.275]},
};
const cardCage = (id, y, extra = {}) => ({
  id, at: [5, y], mate: [12.6, y + 5], rotate: 90, lift: 0, interface: 'sfp',
  media: null, accepts: ['generic/sfp-lc@1', 'generic/sfp-lc-simplex@2'],
  'occupant-attrs': {}, mirror: false, 'group-states': false, ...extra});
const CARD = {name: 'card', version: '1.2.0', size: {w: 30, h: 300},
              cages: [cardCage('xg0', 70), cardCage('xg1', 85), cardCage('xg2', 100),
                      cardCage('xg3', 115), cardCage('xg4', 130),
                      // a composed cage on a raised shelf: its published lift
                      // already carries the part's own (component_cages)
                      cardCage('c1', 145, {lift: 44}),
                      // raised by exactly what front-7 sinks: a sum of 0 there
                      cardCage('c2', 160, {lift: 3})]};
const COMP = {...OPTIC, 'casa/card@1': CARD};
const skin = name => JSON.stringify({a: {}, c: [
  {a: {id: name, 'data-path': name, 'data-class': 'transceiver',
       'data-behaviour': 'occupies', 'data-media': 'fiber'}, c: [
    {a: {id: `${name}--body`}},
    {a: {id: `${name}--tx`, 'data-path': `${name}/tx`}},
  ]},
]});
const loadSkin = async ref => OPTIC[ref] ? {comp: OPTIC[ref], text: skin(OPTIC[ref].name)} : null;
const builtOptic = (bay, cage) => new Node({
  id: `${bay}--module--${cage}-occupant`, 'data-path': `${bay}/module/${cage}-occupant`,
  'data-behaviour': 'occupies', 'data-for': `${bay}/module/${cage}`,
  'data-ref': 'generic/sfp-lc@1:1.0.0'});
const card = (bay, bayAttrs = {}) => new Node({id: bay, 'data-path': bay, 'data-class': 'bay',
                                               ...bayAttrs}, [
  new Node({id: `${bay}--module`, 'data-path': `${bay}/module`, 'data-ref': 'casa/card@1:1.2.0',
            transform: 'translate(10,20)'}, [
    new Node({id: `${bay}--module--plate`}),
    ...CARD.cages.map(c => new Node({id: `${bay}--module--${c.id}`,
                                     'data-path': `${bay}/module/${c.id}`, 'data-class': 'port'}, [
      // the cage node is a composed child, as on the SMM-8x10G
      new Node({id: `${bay}--module--${c.id}--cage`, 'data-path': `${bay}/module/${c.id}/cage`}),
    ])),
    // an LED data-for a cage is not its occupant
    new Node({id: `${bay}--module--xg1-led`, 'data-path': `${bay}/module/xg1-led`,
              'data-class': 'led', 'data-for': `${bay}/module/xg1`}),
    // what the build seated on the card, last, as render.py appends it
    builtOptic(bay, 'xg1'), builtOptic(bay, 'xg2'), builtOptic(bay, 'xg3'),
  ]),
]);
const face = () => new Node({}, [
  // a device cage beside the cards: the same call seats both kinds
  new Node({id: 'port-4', 'data-path': 'port-4', 'data-class': 'port'}),
  card('front-6'),
  card('front-7', {'data-z-lift': '-3'}),
]);
const summary = (root, key) => occupantsOf(root, key).map(n => ({
  ref: n.getAttribute('data-ref'), id: n.getAttribute('id'), path: n.getAttribute('data-path'),
  parent: n.parentNode.getAttribute('data-path'),
  last: n.parentNode.children.at(-1) === n,
  transform: n.getAttribute('transform'),
  children: n.children.map(k => [k.getAttribute('id'), k.getAttribute('data-path')]),
}));

// ---------------------------------------------------------------- overrides
if (mode === 'overrides') {
  const root = face();
  const compByRef = ref => COMP[ref] || null;
  const cages = m.nestedCages(root, compByRef);
  const deviceCage = {id: 'port-4', mate: [10, 5], rotate: null, lift: 0,
                      'occupant-attrs': {}, mirror: false, 'group-states': false};
  const all = [deviceCage, ...cages];
  const keys = ['front-6/module/xg0', 'front-6/module/xg1', 'front-6/module/xg2',
                'front-6/module/xg3', 'front-6/module/xg4', 'front-6/module/c1',
                'front-7/module/xg0'];
  const before = Object.fromEntries(keys.map(k => [k, occupantsOf(root, k).length]));
  const res = await m.applyOccupantOverrides(root, all, {
    'port-4': 'generic/sfp-lc@1',                     // a device cage, beside
    'front-6/module/xg0': 'generic/sfp-lc@1',         // seated into an empty cage
    'front-6/module/xg1': 'generic/sfp-lc-simplex@2', // replaces the built optic
    'front-6/module/xg2': null,                       // emptied
    'front-6/module/xg3': 'nobody/nothing@9',         // unknown: failed, keeps its optic
    // xg4 absent: untouched
    'front-6/module/c1': 'generic/sfp-lc@1',          // a lifted card cage: refused
    'front-7/module/xg0': 'generic/sfp-lc@1',         // a card in a sunk bay: refused
  }, loadSkin);
  const after = Object.fromEntries(keys.map(k => [k, summary(root, k)]));
  const deviceSeat = summary(root, 'port-4');
  // the same cage again: the kit's own optic is replaced, not stacked
  const second = await m.applyOccupantOverrides(root, cages,
    {'front-6/module/xg1': 'generic/sfp-lc@1'}, loadSkin);
  // a stale entry: the card in front-6 swapped for another component after
  // nestedCages read it - its cages are not the new card's to fill
  const stale = face();
  const staleCages = m.nestedCages(stale, compByRef);
  stale.querySelector('[data-path="front-6/module"]').setAttribute('data-ref', 'casa/other@1:1.0.0');
  const staleRes = await m.applyOccupantOverrides(stale, staleCages,
    {'front-6/module/xg1': 'generic/sfp-lc@1'}, loadSkin);
  const entry = cages.find(c => c.id === 'front-6/module/xg0');
  console.log(JSON.stringify({
    before, result: res, after, deviceSeat, second,
    again: occupantsOf(root, 'front-6/module/xg1').map(n => n.getAttribute('data-ref')),
    led: root.querySelectorAll('[data-for="front-6/module/xg1"]')
      .filter(n => n.getAttribute('data-class') === 'led').length,
    ids: cages.map(c => c.id),
    lifts: Object.fromEntries(cages.map(c => [c.id, c.lift])),
    reasons: Object.fromEntries(cages.map(c => [c.id, m.refusalReason(c)])),
    entry: {cage: entry.cage, modulePath: entry.modulePath, moduleId: entry.moduleId,
            carrier: entry.carrier, moduleIsElement: entry.module instanceof Node,
            mate: entry.mate, rotate: entry.rotate},
    names: m.occupantNames(entry),
    deviceNames: m.occupantNames(deviceCage),
    held: m.occupantRef(root, 'front-6/module/xg3'),
    staleRes,
    staleHeld: occupantsOf(stale, 'front-6/module/xg1').map(n => n.getAttribute('data-ref')),
    // a mirrored card mirrors every cage on it
    mirrored: (() => {
      const r = face();
      r.querySelector('[data-path="front-6/module"]')
        .setAttribute('transform', 'translate(40,20) translate(30,0) scale(-1,1)');
      return m.nestedCages(r, compByRef).filter(c => c.modulePath === 'front-6/module')
        .map(c => m.refusalReason(c));
    })(),
    // a module whose component the index does not know has no cages
    unknownCard: m.nestedCages(face(), ref => ref === 'casa/card@1' ? null : COMP[ref]).length,
  }));
}

// ---------------------------------------------------------------- race
// Two applies on one nested cage, the LATER request's skin resolving first,
// under the same claim book a device cage uses.
if (mode === 'race') {
  const pending = [];
  const slowSkin = ref => new Promise(res => pending.push(
    () => res(OPTIC[ref] ? {comp: OPTIC[ref], text: skin(OPTIC[ref].name)} : null)));
  const settle = () => new Promise(r => setTimeout(r, 0));
  const root = face();
  const cages = m.nestedCages(root, ref => COMP[ref] || null);
  const claims = m.seatClaims();
  const key = 'front-6/module/xg1';
  const a = m.applyOccupantOverrides(root, cages, {[key]: 'generic/sfp-lc@1'}, slowSkin, claims(key));
  const b = m.applyOccupantOverrides(root, cages, {[key]: 'generic/sfp-lc-simplex@2'}, slowSkin,
                                     claims(key));
  await settle(); pending[1](); await settle(); pending[0]();
  const [ra, rb] = await Promise.all([a, b]);
  console.log(JSON.stringify({
    held: occupantsOf(root, key).map(n => n.getAttribute('data-ref')),
    results: [ra, rb],
  }));
}
