// A nested bay follows its carrier the way a card's cage does (#484's rule,
// one level over). What the explorer's state holds in a bay inside a seated
// module is compared against the build only while the module above it is
// still the build's; a carrier the state has swapped is a fresh seat of its
// component, so what the build put in its bays is no answer there. And putting
// the BUILD's own carrier back is a fresh seat too: its bays hold the
// component's defaults, not what the configuration had seated in them.
//
// Driven the way the explorer drives it: the state reset from a configuration
// (builtBays / builtOccupants), a carrier swap pruned as shell.js's dropUnder
// prunes it (pruneCarrier, with freshBaysUnder when the ref going in is the
// build's), and the delta read as index.html reads it (swapOverrides) - that
// delta is both `swap=` and the 3D override map, so a key missing from it is
// a swap the 3D scene never sees.
//
// Cases, chosen by argv[2]:
//   reseat   - swap the built carrier away and back: the build's nested module
//              must not survive in 3D
//   swapped  - under a swapped carrier, pick what the configuration had put
//              in the old carrier's nested bay, or empty it
//   order    - a nested key that precedes its carrier in the state map
const m = await import('../../../kit/swap.js');
const mode = process.argv[2];

const A22 = 'smartoptics/dcp-f-a22@2';
const X404 = 'smartoptics/dcp-404@1';
const PPM = 'smartoptics/ppm-ad1-1510@2';
const DUMMY = 'smartoptics/ppm-dummy@1';
const ppmBay = y => ({at: [147.3, y], size: {w: 55.4, h: 19.5},
                      accepts: [PPM, DUMMY], default: DUMMY});
// two carriers that both declare a `ppm-1`, so a key survives the swap in
// name - which is exactly what made the old carrier's answer look like the new
// one's
const INDEX = {
  [A22]: {bays: {'ppm-1': ppmBay(2.5), 'ppm-2': ppmBay(22)}},
  [X404]: {bays: {'ppm-1': ppmBay(2.5)}},
  [PPM]: {}, [DUMMY]: {},
};
const compByRef = ref => {
  if (!/^[^/]+\/[^@]+@\d+$/.test(ref)) throw new Error(`not ns/name@major: ${ref}`);
  return INDEX[ref] || null;
};

// the dcp-2 ila-node shape: the A22 in slot 1 with a real PPM in ppm-1
const cfg = {name: 'ila-node', bays: {'slot-1': A22, 'slot-1/ppm-1': PPM}};
const bays = [{id: 'slot-1', accepts: [A22, X404], default: A22}];
const NESTED = 'slot-1/module/ppm-1';

const reset = () => ({cfgBays: m.builtBays(cfg), cfgOccupants: m.builtOccupants(cfg, []),
                      touched: new Set(), refused: {}, failed: {}});
// shell.js's dropUnder + the write seat() makes after it
const swapCarrier = (state, ref) => {
  const builtRef = m.builtBays(cfg)['slot-1'] ?? null;
  const again = ref && ref === builtRef;
  const next = m.pruneCarrier(state, 'slot-1',
    again ? m.builtOccupants(cfg, []) : {},
    again ? m.freshBaysUnder(cfg, 'slot-1', ref, compByRef) : {});
  next.cfgBays['slot-1'] = ref;
  next.touched.add('slot-1');
  return next;
};
const pick = (state, key, ref) => {
  state.cfgBays[key] = ref;
  state.touched.add(key);
  return state;
};
const delta = (state, withIndex = true) => m.swapOverrides({
  cfg, bays, cages: [], cfgBays: state.cfgBays, cfgOccupants: state.cfgOccupants,
  ...(withIndex ? {compByRef} : {})});

if (mode === 'reseat') {
  const away = swapCarrier(reset(), X404);
  const back = swapCarrier(away, A22);
  console.log(JSON.stringify({
    untouched: delta(reset()),
    away: delta(away),
    back: delta(back),
    backSwap: m.encodeSwaps(delta(back)),
    // what the inspector's select reads: the fresh default, as the face shows
    backState: back.cfgBays[NESTED] ?? null,
    backTouched: back.touched.has(NESTED),
    // the helper alone: only the configuration's nested bays under the
    // carrier, each at what a fresh seat of `ref` holds there
    fresh: m.freshBaysUnder(cfg, 'slot-1', A22, compByRef),
    freshElsewhere: m.freshBaysUnder(cfg, 'slot-2', A22, compByRef),
    freshUnknown: m.freshBaysUnder(cfg, 'slot-1', 'nobody/nothing@9', compByRef),
    freshBadRef: m.freshBaysUnder(cfg, 'slot-1', 'garbage', compByRef),
    freshNoCfg: m.freshBaysUnder(null, 'slot-1', A22, compByRef),
  }));
}

if (mode === 'swapped') {
  const under = () => swapCarrier(reset(), X404);
  console.log(JSON.stringify({
    // the configuration's PPM, chosen in the new carrier's ppm-1
    chosen: delta(pick(under(), NESTED, PPM)),
    // without the index the carrier-swapped rule still holds
    chosenNoIndex: delta(pick(under(), NESTED, PPM), false),
    // the new carrier's own default: what its fresh seat already shows
    fresh: delta(pick(under(), NESTED, DUMMY)),
    // emptied: the fresh seat holds its default, so an empty bay is a swap
    emptied: delta(pick(under(), NESTED, null)),
    // on the BUILT carrier: a nested bay the configuration does not name
    // is built at the component's default, so emptying it is a swap
    unnamedEmptied: delta(pick(reset(), 'slot-1/module/ppm-2', null)),
    unnamedDefault: delta(pick(reset(), 'slot-1/module/ppm-2', DUMMY)),
  }));
}

if (mode === 'order') {
  const state = {cfgBays: {[NESTED]: PPM, 'slot-1': X404}, cfgOccupants: {}};
  console.log(JSON.stringify({delta: delta(state)}));
}
