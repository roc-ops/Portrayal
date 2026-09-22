// The explorer's half of an optic on a seated card (#484): which cage a path
// or a click names, what replacing or emptying the card does to the swaps
// keyed under it, and the 3D per-face pass seating a card's cage. Everything
// here is swap.js - the DOM-free rules shell.js and viewer3d.js call - run on
// the fake DOM the other seating scripts use.
//
// Cases, chosen by argv[2]:
//   cage-at  - cageAt on a device cage, a card cage, a click inside an optic
//              and on a cage's own parts, and on what is no cage
//   prune    - pruneCarrier on the explorer's state slice
//   face     - applyFaceOverrides, the per-face pass viewer3d runs
//   race     - a card replaced while an optic swap on it is still loading
const m = await import('../../../kit/swap.js');
const mode = process.argv[2];

import {Node, install} from './fake-dom.mjs';
install();

const OPTIC = {
  'generic/sfp-lc@1': {name: 'sfp-lc', version: '1.0.0',
                       size: {w: 13.55, h: 8.55, d: 47.5}, mate: [6.775, 4.275]},
};
const cardCage = (id, y) => ({
  id, at: [5, y], mate: [12.6, y + 5], rotate: 90, lift: 0, interface: 'sfp',
  media: null, accepts: ['generic/sfp-lc@1'], 'occupant-attrs': {}, mirror: false,
  'group-states': false});
const CARD = {name: 'card', version: '1.2.0', size: {w: 30, h: 300},
              cages: [cardCage('xg0', 70), cardCage('xg1', 85)]};
const COMP = {...OPTIC, 'casa/card@1': CARD};
const compByRef = ref => COMP[ref] || null;

const opticSkin = name => JSON.stringify({a: {}, c: [
  {a: {id: name, 'data-path': name, 'data-class': 'transceiver',
       'data-behaviour': 'occupies'}, c: [
    {a: {id: `${name}--tx`, 'data-path': `${name}/tx`}},
  ]},
]});
// the card's standalone skin, as components/ carries it: its own namespace,
// cages drawn, no optic in them (a component declares no occupants)
const cardSkin = JSON.stringify({a: {}, c: [
  {a: {id: 'card', 'data-path': 'card', 'data-class': 'supervisor'}, c: [
    {a: {id: 'card--plate'}},
    ...CARD.cages.map(c => ({a: {id: `card--${c.id}`, 'data-path': `card/${c.id}`,
                                 'data-class': 'port'}, c: [
      {a: {id: `card--${c.id}--opening`, 'data-path': `card/${c.id}/opening`}}]})),
  ]},
]});
const loadSkin = async ref => ref === 'casa/card@1' ? {comp: CARD, text: cardSkin}
  : OPTIC[ref] ? {comp: OPTIC[ref], text: opticSkin(OPTIC[ref].name)} : null;

const builtOptic = (host, id, pathBase) => new Node({
  id, 'data-path': `${pathBase}-occupant`, 'data-behaviour': 'occupies',
  'data-for': host, 'data-ref': 'generic/sfp-lc@1:1.0.0'}, [
  new Node({id: `${id}--tx`, 'data-path': `${pathBase}-occupant/tx`}),
]);
// a built face: a device cage with the build's optic beside it, and the card
// in front-6 with an optic the configuration seated in xg1, last in the card
const face = () => new Node({}, [
  new Node({id: 'port-4', 'data-path': 'port-4', 'data-class': 'port'}, [
    new Node({id: 'port-4--opening', 'data-path': 'port-4/opening'})]),
  builtOptic('port-4', 'port-4-occupant', 'port-4'),
  new Node({id: 'port-4-led', 'data-path': 'port-4-led', 'data-class': 'led',
            'data-for': 'port-4'}),
  new Node({id: 'front-6', 'data-path': 'front-6', 'data-class': 'bay'}, [
    new Node({id: 'front-6--module', 'data-path': 'front-6/module', 'data-ref': 'casa/card@1:1.2.0',
              'data-behaviour': 'fills', 'data-for': 'front-6',
              transform: 'translate(10,20)'}, [
      new Node({id: 'front-6--module--plate', 'data-path': 'front-6/module/plate'}),
      ...CARD.cages.map(c => new Node({id: `front-6--module--${c.id}`,
                                       'data-path': `front-6/module/${c.id}`, 'data-class': 'port'}, [
        new Node({id: `front-6--module--${c.id}--opening`,
                  'data-path': `front-6/module/${c.id}/opening`})])),
      new Node({id: 'front-6--module--xg1-led', 'data-path': 'front-6/module/xg1-led',
                'data-class': 'led', 'data-for': 'front-6/module/xg1'}),
      builtOptic('front-6/module/xg1', 'front-6--module--xg1-occupant', 'front-6/module/xg1'),
    ]),
  ]),
]);
const deviceCages = [{id: 'port-4', mate: [10, 5], rotate: null, lift: 0,
                      accepts: ['generic/sfp-lc@1'], 'occupant-attrs': {},
                      mirror: false, 'group-states': false}];
const occupantsOf = (root, key) =>
  root.querySelectorAll(`[data-for="${key}"][data-behaviour="occupies"]`);

if (mode === 'cage-at') {
  const root = face();
  const at = p => m.cageAt(root, p, deviceCages, compByRef)?.id ?? null;
  console.log(JSON.stringify({
    device: at('port-4'),
    deviceOptic: at('port-4-occupant'),
    deviceOpticPart: at('port-4-occupant/tx'),
    deviceOpening: at('port-4/opening'),
    deviceLed: at('port-4-led'),
    card: at('front-6/module/xg0'),
    cardOpening: at('front-6/module/xg0/opening'),
    cardOptic: at('front-6/module/xg1-occupant'),
    cardOpticPart: at('front-6/module/xg1-occupant/tx'),
    cardLed: at('front-6/module/xg1-led'),
    cardPlate: at('front-6/module/plate'),
    cardItself: at('front-6/module'),
    bay: at('front-6'),
    nothing: at('nowhere'),
    nul: at(null),
    noFace: m.cageAt(null, 'port-4', deviceCages, compByRef)?.id ?? null,
    // the entry is nestedCages', accepts and all - what the select offers
    accepts: m.cageAt(root, 'front-6/module/xg0', deviceCages, compByRef)?.accepts,
    faceCages: m.faceCages(root, deviceCages, compByRef).map(c => c.id),
    faceCagesNoFace: m.faceCages(null, deviceCages, compByRef).map(c => c.id),
  }));
}

if (mode === 'prune') {
  const slice = () => ({
    cfgBays: {'front-6': 'casa/card@1', 'front-7': 'casa/card@1',
              'front-6/module/sub-1': 'x/leaf@1'},
    cfgOccupants: {'port-4': 'generic/sfp-lc@1', 'front-6/module/xg0': 'generic/sfp-lc@1',
                   'front-6/module/xg1': null, 'front-7/module/xg0': 'generic/sfp-lc@1',
                   // a prefix of front-6 that is NOT under it
                   'front-60/module/xg0': 'generic/sfp-lc@1'},
    touched: new Set(['front-6', 'front-6/module/xg0', 'front-6/module/xg1',
                      'front-6/module/sub-1', 'front-7/module/xg0', 'port-4']),
    refused: {'front-6/module/xg0': 'generic/sfp-lc@1'},
    failed: {'front-6/module/xg1': 'generic/sfp-lc@1', 'port-4': 'generic/sfp-lc@1'},
  });
  const plain = s => ({...s, touched: [...s.touched].sort()});
  const before = slice();
  const dropped = m.pruneCarrier(before, 'front-6');
  // the built card seated again: fresh from its component, so the optics the
  // build put in it are gone and the state says so
  const rebuilt = m.pruneCarrier(slice(), 'front-6',
    {'front-6/module/xg0': 'generic/sfp-lc@1', 'front-6/module/xg1': 'generic/sfp-lc@1',
     'front-6/module/xg9': null, 'front-7/module/xg0': 'generic/sfp-lc@1'});
  // what that state writes: the config seats the card in front-6 with optics
  // in xg0 and xg1; the user swapped front-6 away, then back to the built card
  const cfg = {name: 'fitted', bays: {'front-6': 'casa/card@1'},
               occupants: {'front-6/xg0': 'generic/sfp-lc@1', 'front-6/xg1': 'generic/sfp-lc@1'}};
  const bays = [{id: 'front-6', accepts: ['casa/card@1', 'casa/blank@1']}];
  const base = {cfgBays: m.builtBays(cfg), cfgOccupants: m.builtOccupants(cfg, []),
                touched: new Set(), refused: {}, failed: {}};
  const emptied = m.pruneCarrier(base, 'front-6');
  emptied.cfgBays['front-6'] = null; emptied.touched.add('front-6');
  const back = m.pruneCarrier(emptied, 'front-6', m.builtOccupants(cfg, []));
  back.cfgBays['front-6'] = 'casa/card@1';
  const delta = s => m.swapOverrides({cfg, bays, cages: [], cfgBays: s.cfgBays,
                                      cfgOccupants: s.cfgOccupants});
  console.log(JSON.stringify({
    dropped: plain(dropped), rebuilt: plain(rebuilt),
    // pure: the slice it was handed is not changed
    inputKept: before.cfgOccupants['front-6/module/xg0'] === 'generic/sfp-lc@1'
      && before.touched.has('front-6/module/xg0') && 'front-6/module/sub-1' in before.cfgBays,
    emptiedDelta: delta(emptied), emptiedSwap: m.encodeSwaps(delta(emptied)),
    backDelta: delta(back), backSwap: m.encodeSwaps(delta(back)),
    garbage: plain(m.pruneCarrier({}, 'front-6')),
  }));
}

if (mode === 'face') {
  const out = {};
  // a card cage alone: the built card, an optic chosen for its empty cage
  // and the built one emptied - with the device cage beside it
  {
    const root = face();
    const r = await m.applyFaceOverrides(root, {bays: [], cages: deviceCages},
      {'front-6/module/xg0': 'generic/sfp-lc@1', 'front-6/module/xg1': null,
       'port-4': 'generic/sfp-lc@1'}, loadSkin, compByRef);
    out.cageOnly = {
      result: {applied: r.applied, refused: r.refused, failed: r.failed, dropped: r.dropped},
      xg0: occupantsOf(root, 'front-6/module/xg0').map(n => n.parentNode.getAttribute('data-path')),
      xg1: occupantsOf(root, 'front-6/module/xg1').length,
      port4: occupantsOf(root, 'port-4').length,
    };
  }
  // the card replaced in the SAME map: the cage is read off the NEW card, so
  // the optic lands in it and not in the one that left
  {
    const root = face();
    const bays = [{id: 'front-6', at: [0, 0], size: {w: 30, h: 300},
                   accepts: ['casa/card@1']}];
    const r = await m.applyFaceOverrides(root, {bays, cages: deviceCages},
      {'front-6': 'casa/card@1', 'front-6/module/xg0': 'generic/sfp-lc@1'}, loadSkin, compByRef);
    const mod = root.querySelector('[data-path="front-6/module"]');
    out.carrierSwapped = {
      applied: r.applied,
      modules: root.querySelectorAll('[data-path="front-6/module"]').length,
      freshCard: mod.getAttribute('data-ref'),
      xg0: occupantsOf(root, 'front-6/module/xg0').map(n => n.parentNode === mod),
      // the build's optic went with the card it sat in
      xg1: occupantsOf(root, 'front-6/module/xg1').length,
    };
  }
  // the card emptied and its cage named anyway: nothing to seat into
  {
    const root = face();
    const bays = [{id: 'front-6', at: [0, 0], size: {w: 30, h: 300}, accepts: ['casa/card@1']}];
    const r = await m.applyFaceOverrides(root, {bays, cages: deviceCages},
      {'front-6': null, 'front-6/module/xg0': 'generic/sfp-lc@1'}, loadSkin, compByRef);
    out.carrierEmptied = {applied: r.applied,
                          xg0: occupantsOf(root, 'front-6/module/xg0').length};
  }
  console.log(JSON.stringify(out));
}

// THE CARD GOES WHILE ITS OPTIC IS LOADING. shell.js's order: seat() takes a
// claim on the nested key and awaits the optic's skin; a bay swap replaces the
// card and prunes (dropUnder), which retires every claim under the bay. The
// optic swap then resolves - and must touch neither the old card nor, by its
// claim, the state. A new swap on the new card still lands.
if (mode === 'race') {
  const pending = [];
  const slowSkin = ref => new Promise(res => pending.push(() => res(
    OPTIC[ref] ? {comp: OPTIC[ref], text: opticSkin(OPTIC[ref].name)} : null)));
  const settle = () => new Promise(r => setTimeout(r, 0));
  const root = face();
  const claims = m.seatClaims();
  const key = 'front-6/module/xg0';
  const live = claims(key);
  const optic = m.applyOccupantOverrides(root, m.nestedCages(root, compByRef),
                                         {[key]: 'generic/sfp-lc@1'}, slowSkin, live);
  await settle();
  const oldCard = root.querySelector('[data-path="front-6/module"]');
  const bays = [{id: 'front-6', at: [0, 0], size: {w: 30, h: 300}, accepts: ['casa/card@1']}];
  await m.applyOverrides(root, bays, {'front-6': 'casa/card@1'}, loadSkin, claims('front-6'));
  claims.retireUnder('front-6');              // where the shell prunes
  const other = claims('front-60/module/xg0'); // a prefix of front-6, not under it
  claims.retireUnder('front-6');
  pending[0]();
  const res = await optic;
  // read now: the new swap below takes a newer claim on the same key
  const liveAfter = live(), otherLive = other();
  const oldOptics = oldCard.children.filter(n => n.getAttribute('data-behaviour') === 'occupies'
    && n.getAttribute('data-for') === key).length;
  const newCard = root.querySelector('[data-path="front-6/module"]');
  const staleOnFace = occupantsOf(root, key).length;
  const again = await m.applyOccupantOverrides(root, m.nestedCages(root, compByRef),
                                               {[key]: 'generic/sfp-lc@1'}, loadSkin, claims(key));
  console.log(JSON.stringify({
    liveAfter, otherLive, res, oldOptics, staleOnFace,
    replaced: newCard !== oldCard,
    again, landed: occupantsOf(root, key).map(n => n.parentNode === newCard),
  }));
}
