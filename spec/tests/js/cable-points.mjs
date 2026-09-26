// The arithmetic a cabling library depends on, without a DOM, plus the DOM
// wrapper checked against a hand-built fake element tree - not jsdom, which
// is not a dependency of this repo.
//
// relief.js reads `location` at module scope and falls through to fetch, so
// both are stubbed the way cavity-seats-on.mjs does it - the real module is
// exercised rather than its text asserted on.
globalThis.location = { search: '' };
globalThis.fetch = async () => ({ ok: true, text: async () => '<svg id="FETCHED"/>' });

const m = await import('../../../kit/relief.js');

// ---------------------------------------------------------------------------
// resolveCablePoint - pure, no DOM at all.
//
// The `ancestors` array is ordered OUTERMOST-LAST, matching a parentElement
// walk from the marker up to the svg. There is no `out` term: a `cable`
// point is `direction: rear`, landing on the part's own reference plane, so
// the ancestor lift sum places it exactly and `z` IS that sum. An ancestor
// may still carry a stray `out` key (as `stack` does below) - it must be
// ignored, not summed and not read from the outermost entry.

const marker = {name: 'cable', at: [6.75, 4.25], dir: 'rear'};

// a plug in a bore on a transceiver: 10.0 of bore lift. The `out` keys here
// must not affect the sum: `data-z-out` is an ABSOLUTE distance from the
// panel while lifts are relative and summed, so an ancestor's `out` cannot be
// folded into this walk whatever it says. Ancestors carrying one are real -
// nine markers in the built library sit under one (see relief.js) - which is
// why they are modelled here rather than assumed away.
const stack = [{lift: 0}, {lift: 10.0, out: 0}, {lift: 0, out: 14.3}];

const pure = {
  // no ancestors carry anything: the point is where it was declared
  bare: m.resolveCablePoint(marker, []),
  // one lifted ancestor
  lifted: m.resolveCablePoint(marker, [{lift: 10.0}]),
  // the full stack sums every lift on the way up - stray `out` keys ignored
  stacked: m.resolveCablePoint(marker, stack),
  // a missing direction is null, not undefined and not a throw
  noDir: m.resolveCablePoint({name: 'cable', at: [1, 2]}, []),
  // junk lifts are zero, not NaN - a NaN z silently removes a cable from 3D
  junk: m.resolveCablePoint(marker, [{lift: 'x'}, {}, {lift: null}]),
  // AN UNREADABLE POINT IS NULL, NOT THE ORIGIN. [0, 0] is a plausible
  // position on any part and wrong by however big the part is, so a consumer
  // could not tell it from a real answer. These four are the shapes a
  // hand-edited or truncated drawing produces.
  noAt: m.resolveCablePoint({name: 'cable'}, [{lift: 2}]),
  emptyAt: m.resolveCablePoint({name: 'cable', at: null}, []),
  junkAt: m.resolveCablePoint({name: 'cable', at: ['x', '2']}, []),
  shortAt: m.resolveCablePoint({name: 'cable', at: ['1']}, []),
  // a string pair is still a point: dataset values arrive as strings
  stringAt: m.resolveCablePoint({name: 'cable', at: ['1.5', '2.5']}, []),
  // A POINT ON A FEATURE (pluggables D): the boot of the seated LC chain,
  // group lift 22.5, body built to data-z-out 37.6. `rear` is ABSOLUTE, so z
  // is 37.6 - not 22.5 (short by the boot) and not 60.1 (the lift summed in).
  onRear: m.resolveCablePoint({...marker, rear: '37.6'}, [{lift: 22.5}]),
  // an unreadable `rear` keeps the part's face, like a junk lift keeps 0
  junkRear: m.resolveCablePoint({...marker, rear: 'x'}, [{lift: 22.5}]),
  // A POINT ON A CYLINDER: a cyl has no `out`, and its rear is its far end,
  // lift + cyl. The lift is SUMMED like any other - the ancestors' and the
  // feature's own (`cylLift`, from the feature up to the marker's parent) -
  // and the cyl runs from there. A stub at lift 34.8, 30 long: 64.8.
  onCyl: m.resolveCablePoint({...marker, cyl: '30', cylLift: '34.8'}, []),
  // the same stub on a part whose group stands 10 off: the feature's own
  // lift is 24.8 (render.py's _inset_feature takes the group's 10 off it)
  onCylLifted: m.resolveCablePoint({...marker, cyl: '30', cylLift: '24.8'}, [{lift: 10}]),
  // an unreadable cyl keeps the part's face, like an unreadable rear
  junkCyl: m.resolveCablePoint({...marker, cyl: 'x', cylLift: '34.8'}, [{lift: 10}]),
  // BOTH ON ONE MARKER, `out` WINS: an absolute rear is the feature's front
  // face as built, so a stray cyl beside it is not added on
  outOverCyl: m.resolveCablePoint({...marker, rear: '37.6', cyl: '30', cylLift: '1'}, []),
};

// ---------------------------------------------------------------------------
// cablePoints - the DOM wrapper, against a hand-built fake tree.
//
// jsdom is not a dependency here, so the fake is the smallest thing
// cablePoints actually uses: dataset, parentElement, closest('[data-path]')
// and querySelectorAll('[data-cp="cable"]') on the root - the same idiom
// nested-bays.mjs uses for swap.js's querySelectorAll/closest.
//
// A real instance group (render.py's instance_group) sets data-path on
// ITSELF, and a connection-point marker is appended as its direct child - so
// `mk.closest('[data-path]')` always finds the marker's own parent, which is
// the OCCUPANT's own path. `cablePoints` keeps a marker unless a STRICTLY
// DEEPER marker shares its chain ("shadowed" in relief.js) - a plug's
// "cage-1/plug" is shadowed by a boot's "cage-1/plug/boot", but
// "sfp-lc/tx" and "sfp-lc/rx" (siblings, neither a prefix of the other)
// shadow nothing and both survive. This replaced an earlier union-find
// clustering that computed the TRANSITIVE CLOSURE of the same-chain
// relation, which is not transitive: a wrapper with its own marker plus two
// marked children fused all three into one point (connector H below), a
// shape nothing in the library can build yet but spec B2's plugs and boots
// can. The cases below are built specifically so at least one of them tells
// the two rules apart - proving the fix is doing real work, not just
// passing under either one.
function el(attrs, parent) {
  const dataset = {};
  for (const [k, v] of Object.entries(attrs)) {
    const camel = k.replace(/^data-/, '').replace(/-([a-z])/g, (_, c) => c.toUpperCase());
    dataset[camel] = v;
  }
  const node = {
    dataset,
    parentElement: parent,
    closest(sel) {
      if (sel !== '[data-path]') throw new Error('unexpected selector ' + sel);
      for (let n = node; n; n = n.parentElement) {
        if (n.dataset && 'path' in n.dataset) return n;
      }
      return null;
    },
  };
  // only the connectors that declare `data-cp-on` get a findable child; the
  // rest keep the smallest fake, so an unexpected lookup still throws
  node.querySelector = sel => {
    const hit = (node.children || []).find(c => sel === `[id="${c.id}"]`);
    if (!node.children) throw new Error('unexpected querySelector ' + sel);
    return hit || null;
  };
  return node;
}

// WHAT THE MODULE SAYS OUT LOUD, CAPTURED. cablePoints warns on an unreadable
// `data-cp-at` and on a `data-for` cycle; both are cases where the sensible
// return value is an absence, and an absence is exactly what a test cannot
// tell from a bug. Collected here so the assertions can name them.
const warnings = [];
const realWarn = console.warn;
console.warn = (...a) => { warnings.push(a.join(' ')); };

const svg = {}; // the walk boundary: parentElement chains stop when they hit this

// connector A: a bare part on the panel, one marker, no boot - the plain case
const connectorA = el({'data-path': 'cage-a', 'data-z-lift': '2.5'}, svg);
const markerA1 = el({'data-cp': 'cable', 'data-cp-at': '1 2', 'data-cp-dir': 'front'}, connectorA);

// connector B: a different connector entirely, and its marker declares no
// direction - dir must come back null, not undefined
const connectorB = el({'data-path': 'cage-b'}, svg);
const markerB1 = el({'data-cp': 'cable', 'data-cp-at': '5 6'}, connectorB);

// connector C: a plug seated in the cage, and a boot seated on the plug -
// same chain, different z. Both declare a `cable` point; the boot's extra
// 5mm of lift puts it further out, so it must be the one that survives.
const connectorC = el({'data-path': 'cage-c'}, svg);
const plugC = el({'data-path': 'cage-c/plug'}, connectorC);
const markerPlug = el({'data-cp': 'cable', 'data-cp-at': '3 3', 'data-cp-dir': 'rear'}, plugC);
const bootC = el({'data-path': 'cage-c/plug/boot', 'data-z-lift': '5'}, plugC);
const markerBoot = el({'data-cp': 'cable', 'data-cp-at': '3 3.2', 'data-cp-dir': 'rear'}, bootC);

// connector D: a component drawing's two bores, SIBLINGS under a shared
// leading segment ("sfp-lc"), neither a prefix of the other. THE CASE A
// leading-segment grouping could not pass: it collapses these into one
// point, losing the rx side of an LC duplex entirely.
const sfpLc = el({'data-path': 'sfp-lc'}, svg);
const boreTx = el({'data-path': 'sfp-lc/tx', 'data-z-lift': '3'}, sfpLc);
const markerTx = el({'data-cp': 'cable', 'data-cp-at': '0 1'}, boreTx);
const boreRx = el({'data-path': 'sfp-lc/rx', 'data-z-lift': '4'}, sfpLc);
const markerRx = el({'data-cp': 'cable', 'data-cp-at': '0 2'}, boreRx);

// connectors E/F: "sfp-1" and "sfp-10" - a bare `startsWith` (without the
// trailing "/" boundary) would wrongly read "sfp-1" as a prefix of "sfp-10"
// and merge two unrelated ports into one.
const sfp1 = el({'data-path': 'sfp-1'}, svg);
const markerSfp1 = el({'data-cp': 'cable', 'data-cp-at': '9 9'}, sfp1);
const sfp10 = el({'data-path': 'sfp-10'}, svg);
const markerSfp10 = el({'data-cp': 'cable', 'data-cp-at': '8 8'}, sfp10);

// connector G: a plug and a boot with an EXACT z tie (no extra lift on the
// boot). Under shadowing there is no tie to break - the plug's path is a
// strict prefix of the boot's, so the plug is shadowed regardless of z, and
// the boot must still be the one that survives.
const connectorG = el({'data-path': 'cage-g'}, svg);
const plugG = el({'data-path': 'cage-g/plug'}, connectorG);
const markerPlugG = el({'data-cp': 'cable', 'data-cp-at': '7 7'}, plugG);
const bootG = el({'data-path': 'cage-g/plug/boot'}, plugG);
const markerBootG = el({'data-cp': 'cable', 'data-cp-at': '7 7.1'}, bootG);

// connector H: THE BRANCHING CASE a union-find clustering could not pass. A
// wrapper carries its own `cable` marker, and TWO of its children each carry
// their own, unrelated to one another ("wrap/a" and "wrap/b" are siblings,
// neither a prefix of the other). "wrap" is shadowed by both children, but
// the children must not shadow each other - a clustering that groups
// everything sharing a chain member together fuses all three through the
// shared "wrap" and wrongly returns one point instead of two.
const wrap = el({'data-path': 'wrap'}, svg);
const markerWrap = el({'data-cp': 'cable', 'data-cp-at': '4 4'}, wrap);
const wrapA = el({'data-path': 'wrap/a'}, wrap);
const markerWrapA = el({'data-cp': 'cable', 'data-cp-at': '4 5'}, wrapA);
const wrapB = el({'data-path': 'wrap/b'}, wrap);
const markerWrapB = el({'data-cp': 'cable', 'data-cp-at': '4 6'}, wrapB);

// connector J: a marker whose point does not parse. It must still appear -
// dropping a connector is its own silent failure - but with `at: null`, so
// the first arithmetic on it fails at the point of use instead of putting a
// cable on the part's origin.
const connectorJ = el({'data-path': 'cage-j'}, svg);
const markerJ = el({'data-cp': 'cable', 'data-cp-at': 'banana'}, connectorJ);

// connector K: a CHAIN OF SEATS, not nested paths - three elements with
// DISTINCT TOP-LEVEL data-path values ("cage", "cage-plug",
// "cage-plug-boot"), all three siblings under the root, exactly the shape a
// `mate-to` occupant produces (render.py appends it to the view root, not
// the host's group). No path is a prefix of another, so the path-prefix
// rule ALONE keeps all three - this is the case that was three points before
// the fix and must be one after it. `data-for` is what ties them together:
// the plug names "cage", the boot names "cage-plug", and the outermost (the
// boot's) is the one that must survive.
const cageRoot = el({'data-path': 'cage'}, svg);
const markerCage = el({'data-cp': 'cable', 'data-cp-at': '2 2'}, cageRoot);
const cagePlug = el({'data-path': 'cage-plug', 'data-for': 'cage'}, svg);
const markerCagePlug = el({'data-cp': 'cable', 'data-cp-at': '2 2.1'}, cagePlug);
const cagePlugBoot = el({'data-path': 'cage-plug-boot', 'data-for': 'cage-plug'}, svg);
const markerCagePlugBoot = el({'data-cp': 'cable', 'data-cp-at': '2 2.2'}, cagePlugBoot);

// connector L: a marker whose `data-for` names an element THAT DOES NOT
// EXIST anywhere in this drawing - a typo, or a genuinely cross-view target
// this drawing cannot resolve. The chain walk must stop cold rather than
// throw or loop forever, and the marker must still be reported.
const cageL = el({'data-path': 'cage-l', 'data-for': 'does-not-exist'}, svg);
const markerCageL = el({'data-cp': 'cable', 'data-cp-at': '9 1'}, cageL);

// connector M: a 2-CYCLE in data-for - two elements each naming the OTHER as
// their host. Nothing real produces this (a `mate-to` occupant's data-for
// names an already-positioned host; two elements cannot each be seated on
// the other), but `cablePoints` runs in a browser against a document this
// kit did not write, so the walk terminating is not optional - a hang here
// is a real failure mode, not a theoretical one. seatChain's `seen` guard
// stops each walk after two steps: cycle-a's chain is [cycle-a, cycle-b] and
// cycle-b's is [cycle-b, cycle-a], so EACH sees the other in the other's
// chain tail and shadows it. The sensible result asserted below is that
// BOTH drop - symmetric, contradictory data getting zero survivors, rather
// than an arbitrary pick decided by array order.
const cycleA = el({'data-path': 'cycle-a', 'data-for': 'cycle-b'}, svg);
const markerCycleA = el({'data-cp': 'cable', 'data-cp-at': '6 6'}, cycleA);
const cycleB = el({'data-path': 'cycle-b', 'data-for': 'cycle-a'}, svg);
const markerCycleB = el({'data-cp': 'cable', 'data-cp-at': '6 6.1'}, cycleB);

// connector N: SELF-REFERENCE - an element whose data-for names itself. The
// `seen` guard stops the walk after one step (the element is already in
// `seen` the instant it is revisited as its own next hop), so its chain is
// just itself and nothing shadows it, and the marker survives on its own.
// ITS RETURN VALUE is what having no data-for at all would give; its output
// is not. A self-reference is a 1-cycle, so it also trips the cycle warning
// and the reader sees one on stderr naming cycle-self - which is right: the
// attribute is malformed either way, and surviving is not the same as being
// unremarkable.
const cycleSelf = el({'data-path': 'cycle-self', 'data-for': 'cycle-self'}, svg);
const markerCycleSelf = el({'data-cp': 'cable', 'data-cp-at': '6 6.2'}, cycleSelf);

// connector O: A MULTI-TOKEN `data-for` WHOSE FIRST TOKEN IS CROSS-VIEW.
// `seatOwner` handles both shapes render.py's `data_for` can emit - several
// space-separated targets, and a device-absolute one leading with "/" - and
// until now nothing exercised either, so the loop could have been a bare
// `byPath.get(raw)` and every test would still have passed.
//
// `/rear/x` IS PLANTED AS A REAL data-path HERE ON PURPOSE. No renderer emits
// a path beginning with a slash - that is precisely why the leading slash
// makes a cross-view token unmistakable - but without an owner under that key
// the `continue` is unobservable: an unplanted "/rear/x" would miss the map
// and fall through to the next token anyway, so the guard could be deleted
// and this fixture would not notice. With it planted, dropping the guard
// chains plug-o to the WRONG owner (the first token wins) and the assertions
// below fail. The second token, `cage-o`, is the host a seat really names.
const crossView = el({'data-path': '/rear/x'}, svg);
const markerCrossView = el({'data-cp': 'cable', 'data-cp-at': '0 7'}, crossView);
const cageO = el({'data-path': 'cage-o'}, svg);
const markerCageO = el({'data-cp': 'cable', 'data-cp-at': '1 1'}, cageO);
const plugO = el({'data-path': 'plug-o', 'data-for': '/rear/x cage-o'}, svg);
const markerPlugO = el({'data-cp': 'cable', 'data-cp-at': '1 1.5'}, plugO);

// connector P: THE SEATED LC CHAIN, as render.py compiles it for pluggables
// D - a plug seated in an optic (group lift 10) and a boot on the plug (group
// lift 22.5), each with a `cable` point `on:` its body, whose data-z-out is
// absolute (plug 22.5, boot 37.6). The boot survives and lands on its REAR.
// connector Q: the same plug, bare - its cable leaves the plug body's rear.
// connector R: a point `on:` a node that carries no data-z-out - it keeps its
// face and says so.
function withFeature(owner, id, zOut, attrs = {}) {
  const f = el(zOut === undefined ? attrs : {'data-z-out': zOut, ...attrs}, owner);
  f.id = id;
  owner.children = (owner.children || []).concat([f]);
  return f;
}
const plugP = el({'data-path': 'p-plug', 'data-z-lift': '10'}, svg);
withFeature(plugP, 'p-plug--body', '22.5');
const markerPlugP = el({'data-cp': 'cable', 'data-cp-at': '2.79 7.61', 'data-cp-on': 'p-plug--body'}, plugP);
const bootP = el({'data-path': 'p-plug-boot', 'data-for': 'p-plug', 'data-z-lift': '22.5'}, svg);
withFeature(bootP, 'p-plug-boot--body', '37.6');
const markerBootP = el({'data-cp': 'cable', 'data-cp-at': '3.1 3.1', 'data-cp-on': 'p-plug-boot--body'}, bootP);
const plugQ = el({'data-path': 'q-plug', 'data-z-lift': '10'}, svg);
withFeature(plugQ, 'q-plug--body', '22.5');
const markerPlugQ = el({'data-cp': 'cable', 'data-cp-at': '2.79 7.61', 'data-cp-on': 'q-plug--body'}, plugQ);
const partR = el({'data-path': 'r-part', 'data-z-lift': '4'}, svg);
withFeature(partR, 'r-part--flat');
const markerR = el({'data-cp': 'cable', 'data-cp-at': '1 1', 'data-cp-on': 'r-part--flat'}, partR);

// connector S: a point `on:` a CYLINDER - a stub at lift 24.8 in a part whose
// group stands 10 off, 30 long, so its far end is 10 + 24.8 + 30 = 64.8. The
// group's lift comes from the marker's ancestor walk and the stub's own from
// the feature node, exactly as relief.js's liftOf sums both.
const partS = el({'data-path': 's-part', 'data-z-lift': '10'}, svg);
withFeature(partS, 's-part--stub', undefined, {'data-z-lift': '24.8', 'data-z-cyl': '30'});
const markerS = el({'data-cp': 'cable', 'data-cp-at': '5 5', 'data-cp-on': 's-part--stub'}, partS);

const markers = [
  markerPlugP, markerBootP, markerPlugQ, markerR, markerS,
  markerA1, markerB1, markerPlug, markerBoot,
  markerTx, markerRx, markerSfp1, markerSfp10,
  markerPlugG, markerBootG,
  markerWrap, markerWrapA, markerWrapB,
  markerJ,
  markerCage, markerCagePlug, markerCagePlugBoot,
  markerCageL,
  markerCycleA, markerCycleB, markerCycleSelf,
  markerCrossView, markerCageO, markerPlugO,
];
svg.querySelectorAll = sel => {
  if (sel !== '[data-cp="cable"]') throw new Error('unexpected selector ' + sel);
  return markers;
};

// a drawing with no cable markers at all
const emptyRoot = {querySelectorAll: sel => {
  if (sel !== '[data-cp="cable"]') throw new Error('unexpected selector ' + sel);
  return [];
}};

// `el` is the owning element itself, so it cannot be serialised - it is
// replaced here by the one fact worth asserting across the process boundary:
// that it is the marker element this point came from.
const strip = pts => pts.map(({el: owner, ...rest}) => ({...rest, elIsMarker: markers.includes(owner)}));

const result = {
  ...pure,
  points: strip(m.cablePoints(svg)),
  empty: m.cablePoints(emptyRoot),
};
console.warn = realWarn;
console.log(JSON.stringify({...result, warnings}));
