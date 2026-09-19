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
  return node;
}

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

const markers = [
  markerA1, markerB1, markerPlug, markerBoot,
  markerTx, markerRx, markerSfp1, markerSfp10,
  markerPlugG, markerBootG,
  markerWrap, markerWrapA, markerWrapB,
  markerJ,
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

console.log(JSON.stringify({
  ...pure,
  points: strip(m.cablePoints(svg)),
  empty: m.cablePoints(emptyRoot),
}));
