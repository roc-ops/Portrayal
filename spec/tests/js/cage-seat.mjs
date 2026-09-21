// An optic seated by the kit must be the optic the build seats.
//
// `swap.js` repeats one formula from render.py - `seat_at`, as `occupantAt` -
// and assembles the occupant's attributes from three published sources. Both
// are held to a REAL build here: test_cage_seat_js.py renders a fitted copy of
// a device, reads what render.py actually wrote on every occupant, and hands it
// to this script with the bare build's `cages[]` and the components.json
// entries. Checking the formula against itself would prove nothing.
//
// Cases, chosen by argv[2]:
//   parity   - stdin JSON; per port, the kit's transform and attribute set
//   children - stdin JSON; per port, every descendant seatOccupant builds
//   overrides - applyOccupantOverrides on a fake DOM
//   rename   - `segment = ''` names an occupant's children as the build does
//   race     - two swaps in flight on one cage or bay
//
// jsdom is not a dependency here, so the DOM is the smallest one swap.js
// actually uses (fake-dom.mjs, the idiom of nested-bays.mjs).
const m = await import('../../../kit/swap.js');
const mode = process.argv[2];

// ---------------------------------------------------------------- fake DOM
import {Node, DOC, build, install} from './fake-dom.mjs';
install();

// ---------------------------------------------------------------- parity
if (mode === 'parity') {
  let raw = '';
  for await (const chunk of process.stdin) raw += chunk;
  const {ports} = JSON.parse(raw);
  const out = ports.map(({port, cage, ref, comp, skinRoot}) => {
    const tf = m.occupantTransform(cage, comp);
    const t = /^translate\(([^,]+),([^)]+)\)(?: rotate\(([^ ]+) ([^ ]+) ([^)]+)\))?$/.exec(tf);
    return {
      port,
      transformText: tf,
      transform: t ? {tx: +t[1], ty: +t[2],
                      rotate: t[3] ? [+t[3], +t[4], +t[5]] : null} : null,
      attrs: m.occupantAttrs(cage, ref, comp, skinRoot),
    };
  });
  console.log(JSON.stringify(out));
}

// ---------------------------------------------------------------- children
// seatOccupant on the real compiled skin (in fake-dom JSON form), and every
// descendant of what it builds - the kit's side of the children comparison.
if (mode === 'children') {
  let raw = '';
  for await (const chunk of process.stdin) raw += chunk;
  const {ports} = JSON.parse(raw);
  const empty = n => n.tagName === 'style' && !n.children.length;
  const out = ports.map(({port, cage, ref, comp, skin}) => {
    const g = m.seatOccupant(DOC, cage, ref, comp, skin);
    return {port, children: [...g.descendants()].filter(n => !empty(n))
      .map(n => ({t: n.tagName, a: Object.fromEntries(n.attributes.map(x => [x.name, x.value]))}))};
  });
  console.log(JSON.stringify(out));
}

// ---------------------------------------------------------------- overrides
if (mode === 'overrides') {
  const COMP = {
    'generic/sfp-lc@1': {name: 'sfp-lc', version: '1.0.0',
                         size: {w: 13.55, h: 8.55, d: 47.5}, mate: [6.775, 4.275]},
    'generic/sfp-lc-simplex@1': {name: 'sfp-lc-simplex', version: '1.0.0',
                                 size: {w: 13.55, h: 8.55, d: 47.5}, mate: [6.775, 4.275]},
  };
  const skin = name => JSON.stringify({a: {}, c: [
    {a: {id: name, 'data-path': name, 'data-class': 'transceiver',
         'data-behaviour': 'occupies', 'data-media': 'fiber'}, c: [
      {a: {id: `${name}--body`}},
      {a: {id: `${name}--tx`, 'data-path': `${name}/tx`}},
    ]},
  ]});
  const loadSkin = async ref => COMP[ref]
    ? {comp: COMP[ref], text: skin(COMP[ref].name)} : null;
  const cage = id => ({id, mate: [10, 5], rotate: null, lift: 0,
                       'occupant-attrs': {'data-group': 'sfp28', 'data-media': 'sfp28'}});
  const cages = ['port-4', 'port-5', 'port-6', 'port-7', 'port-8', 'port-9', 'port-10']
    .map(cage);
  // a cage whose aperture stands off the face: the kit cannot seat into it
  // without also shifting every child's absolute out, so it refuses
  cages[4].lift = 3;
  // a mirrored cage, which the build refuses to seat at all
  cages[5].mirror = true;
  // a cage whose group carries lamp states the build would apply to the optic
  cages[6]['group-states'] = true;

  const face = () => {
    const root = new Node({}, [
      ...cages.map(c => new Node({id: c.id, 'data-path': c.id, 'data-class': 'port'})),
      new Node({id: 'led-port-4', 'data-path': 'led-port-4', 'data-class': 'led',
                'data-for': 'port-4'}),
      // what the build seated, at the END of the drawing, as render.py puts it
      ...cages.map(c => new Node({id: `${c.id}-occupant`, 'data-path': `${c.id}-occupant`,
                                  'data-behaviour': 'occupies', 'data-for': c.id,
                                  'data-ref': 'generic/sfp-lc@1:1.0.0'})),
    ]);
    return root;
  };
  const occ = (root, id) => root.querySelectorAll(
    `[data-for="${id}"][data-behaviour="occupies"]`);

  const root = face();
  const before = Object.fromEntries(cages.map(c => [c.id, occ(root, c.id).length]));
  const {applied, refused, failed} = await m.applyOccupantOverrides(root, cages, {
    'port-4': 'generic/sfp-lc-simplex@1',     // replaced
    'port-5': null,                           // emptied
    'port-6': 'nobody/nothing@9',             // unknown: failed, keeps its optic
    // port-7 absent: untouched
    'port-8': 'generic/sfp-lc@1',             // lifted: refused, left empty
    'port-9': 'generic/sfp-lc@1',             // mirrored: refused, left empty
    'port-10': 'generic/sfp-lc@1',            // group states: refused, left empty
  }, loadSkin);
  const after = Object.fromEntries(cages.map(c => [c.id, occ(root, c.id).map(n => ({
    ref: n.getAttribute('data-ref'), id: n.getAttribute('id'),
    path: n.getAttribute('data-path'), transform: n.getAttribute('transform'),
    media: n.getAttribute('data-media'), group: n.getAttribute('data-group'),
    children: n.children.map(k => [k.getAttribute('id'), k.getAttribute('data-path')]),
    // the next sibling of the host is where it went
    besideHost: root.children[root.children.indexOf(n) - 1]?.getAttribute('id'),
  }))]));
  // a second swap replaces the first swap's occupant, not stacks beside it
  const second = await m.applyOccupantOverrides(root, cages, {'port-4': 'generic/sfp-lc@1'}, loadSkin);
  const again = occ(root, 'port-4').map(n => n.getAttribute('data-ref'));
  console.log(JSON.stringify({
    applied, refused, failed, before, after, again, second,
    // seatOccupant itself will not produce a half-seated optic
    seatRefused: [4, 5, 6].map(i => m.seatOccupant(DOC, cages[i], 'generic/sfp-lc@1',
                                                   COMP['generic/sfp-lc@1'], skin('sfp-lc'))),
    reasons: cages.map(m.refusalReason),
    // what the failed cage still holds, as a caller records it
    heldAfterFailure: m.occupantRef(root, 'port-6'),
    heldWhenEmpty: m.occupantRef(root, 'port-5'),
    // emptying a refused cage is not a refusal
    emptyRefused: await m.applyOccupantOverrides(root, cages, {'port-9': null}, loadSkin),
    led: root.querySelectorAll('[data-for="port-4"]')
      .filter(n => n.getAttribute('data-class') === 'led').length,
  }));
}

// ---------------------------------------------------------------- rename
if (mode === 'rename') {
  const mk = () => new Node({}, [
    new Node({id: 'sfp-lc', 'data-path': 'sfp-lc'}),
    new Node({id: 'sfp-lc--tx', 'data-path': 'sfp-lc/tx'}),
    new Node({id: 'sfp-lc--w0'}),
    new Node({'clip-path': 'url(#sfp-lc--w0)'}),
  ]);
  const read = w => w.children.map(n => [n.getAttribute('id'), n.getAttribute('data-path'),
                                         n.getAttribute('clip-path')]);
  const bare = mk();
  m.rename(bare, 'sfp-lc', 'port-4-occupant', 'port-4-occupant', '');
  const dflt = mk();
  m.rename(dflt, 'sfp-lc', 'front-0');
  console.log(JSON.stringify({bare: read(bare), dflt: read(dflt)}));
}

// ---------------------------------------------------------------- race
// TWO SWAPS IN FLIGHT ON ONE TARGET. A focused select fires `change` on every
// arrow key, and a view change re-seats while a swap is still loading, so two
// applies on one cage (or one bay) overlap whenever the skin fetch is slow.
// The loads here resolve BY HAND, in whichever order a case needs.
if (mode === 'race') {
  const COMP = {
    'generic/a@1': {name: 'a', version: '1.0.0', size: {w: 10, h: 8, d: 40}, mate: [5, 4]},
    'generic/b@1': {name: 'b', version: '1.0.0', size: {w: 10, h: 8, d: 40}, mate: [5, 4]},
  };
  const skin = name => JSON.stringify({a: {}, c: [
    {a: {id: name, 'data-path': name, 'data-behaviour': 'occupies'}, c: [{a: {id: `${name}--tx`}}]},
  ]});
  const pending = [];
  const loadSkin = ref => new Promise(res => pending.push(
    () => res(COMP[ref] ? {comp: COMP[ref], text: skin(COMP[ref].name)} : null)));
  const settle = () => new Promise(r => setTimeout(r, 0));
  const cage = {id: 'port-4', mate: [10, 5], rotate: null, lift: 0, mirror: false,
                'group-states': false, 'occupant-attrs': {}};
  const bay = {id: 'slot-0', at: [0, 0], size: {w: 10, h: 8}, accepts: []};
  const face = () => new Node({}, [
    new Node({id: 'port-4', 'data-path': 'port-4', 'data-class': 'port'}),
    new Node({id: 'slot-0', 'data-path': 'slot-0', 'data-class': 'bay'}, [
      new Node({id: 'slot-0--module', 'data-path': 'slot-0/module', 'data-ref': 'built:1'})]),
    new Node({id: 'port-4-occupant', 'data-path': 'port-4-occupant', 'data-for': 'port-4',
              'data-behaviour': 'occupies', 'data-ref': 'built:1'}),
  ]);
  const optics = root => root.querySelectorAll('[data-for="port-4"][data-behaviour="occupies"]')
    .map(n => n.getAttribute('data-ref'));
  const modules = root => root.querySelectorAll('[id="slot-0--module"]')
    .map(n => n.getAttribute('data-ref'));
  const claims = m.seatClaims ? m.seatClaims() : () => () => true;
  const out = {};

  // 1. a cage, loads resolving in request order, no claims at all (viewer3d's call)
  {
    const root = face();
    pending.length = 0;
    const a = m.applyOccupantOverrides(root, [cage], {'port-4': 'generic/a@1'}, loadSkin);
    const b = m.applyOccupantOverrides(root, [cage], {'port-4': 'generic/b@1'}, loadSkin);
    await settle(); pending[0](); pending[1]();
    await Promise.all([a, b]);
    out.cageInOrder = optics(root);
  }
  // 2. a cage, the LATER request's load resolving FIRST, with claims
  {
    const root = face();
    pending.length = 0;
    const a = m.applyOccupantOverrides(root, [cage], {'port-4': 'generic/a@1'}, loadSkin,
                                       claims('port-4'));
    const b = m.applyOccupantOverrides(root, [cage], {'port-4': 'generic/b@1'}, loadSkin,
                                       claims('port-4'));
    await settle(); pending[1](); await settle(); pending[0]();
    const [ra, rb] = await Promise.all([a, b]);
    out.cageOutOfOrder = optics(root);
    out.cageResults = [ra, rb];
  }
  // 3. a cage emptied while an earlier swap is still loading
  {
    const root = face();
    pending.length = 0;
    const a = m.applyOccupantOverrides(root, [cage], {'port-4': 'generic/a@1'}, loadSkin,
                                       claims('port-4'));
    const b = m.applyOccupantOverrides(root, [cage], {'port-4': null}, loadSkin,
                                       claims('port-4'));
    await settle(); pending[0]();
    await Promise.all([a, b]);
    out.cageEmptiedWhileLoading = optics(root);
  }
  // 4. a bay, the same out-of-order pair - one mechanism for both kinds
  {
    const root = face();
    pending.length = 0;
    const a = m.applyOverrides(root, [bay], {'slot-0': 'generic/a@1'}, loadSkin, claims('slot-0'));
    const b = m.applyOverrides(root, [bay], {'slot-0': 'generic/b@1'}, loadSkin, claims('slot-0'));
    await settle(); pending[1](); await settle(); pending[0]();
    await Promise.all([a, b]);
    out.bayOutOfOrder = modules(root);
  }
  // 5. the claims themselves: a newer claim retires an older one, per key
  {
    const c = m.seatClaims ? m.seatClaims() : () => () => true;
    const k1 = c('port-4'), other = c('slot-0'), k2 = c('port-4');
    out.claims = [k1(), k2(), other()];
  }
  console.log(JSON.stringify(out));
}
