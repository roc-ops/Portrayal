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
// walk from the marker up to the svg.

const marker = {name: 'cable', at: [6.75, 4.25], dir: 'rear'};

// a plug in a bore on a transceiver: 10.0 of bore lift, 14.3 of body out
const stack = [{lift: 0}, {lift: 10.0, out: 0}, {lift: 0, out: 14.3}];

const pure = {
  // no ancestors carry anything: the point is where it was declared
  bare: m.resolveCablePoint(marker, []),
  // one lifted ancestor
  lifted: m.resolveCablePoint(marker, [{lift: 10.0}]),
  // the full stack sums every lift on the way up
  stacked: m.resolveCablePoint(marker, stack),
  // a missing direction is null, not undefined and not a throw
  noDir: m.resolveCablePoint({name: 'cable', at: [1, 2]}, []),
  // junk lifts are zero, not NaN - a NaN z silently removes a cable from 3D
  junk: m.resolveCablePoint(marker, [{lift: 'x'}, {}, {lift: null}]),
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
// the OCCUPANT's own path ("cage-1/plug"), never the connector's. A boot
// mated onto a plug is a further-nested occupant with its OWN, longer path
// ("cage-1/plug/boot"). Grouping on the full closest path would therefore
// never collapse a plug's marker and its boot's marker into one connector -
// so cablePoints groups on the LEADING path segment instead, which both
// share. This fake tree exists specifically to prove that collapse happens
// for the right reason, and not because every marker was faked to report the
// same owner.
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

// connector C: a plug seated in the cage, and a boot seated on the plug.
// Both declare a `cable` point; the boot's extra 5mm of lift puts it further
// out, so it must be the one that survives.
const connectorC = el({'data-path': 'cage-c', 'data-z-out': '10'}, svg);
const plugC = el({'data-path': 'cage-c/plug'}, connectorC);
const markerPlug = el({'data-cp': 'cable', 'data-cp-at': '3 3', 'data-cp-dir': 'rear'}, plugC);
const bootC = el({'data-path': 'cage-c/plug/boot', 'data-z-lift': '5'}, plugC);
const markerBoot = el({'data-cp': 'cable', 'data-cp-at': '3 3.2', 'data-cp-dir': 'rear'}, bootC);

const markers = [markerA1, markerB1, markerPlug, markerBoot];
svg.querySelectorAll = sel => {
  if (sel !== '[data-cp="cable"]') throw new Error('unexpected selector ' + sel);
  return markers;
};

// a drawing with no cable markers at all
const emptyRoot = {querySelectorAll: sel => {
  if (sel !== '[data-cp="cable"]') throw new Error('unexpected selector ' + sel);
  return [];
}};

console.log(JSON.stringify({
  ...pure,
  points: m.cablePoints(svg),
  empty: m.cablePoints(emptyRoot),
}));
