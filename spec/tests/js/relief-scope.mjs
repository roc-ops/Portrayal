// An override is an opinion, not a fact, and a module-level map has one seat.
//
// Two viewers showing the same rack with different occupants could not both be
// right: whichever swapped last won for both, and `clearSvgOverrides()` took no
// argument, so one viewer starting a build emptied the other's swaps. A
// downstream consumer ran two iframes - two documents, two WebGL contexts - to
// get two copies of this module.
//
// relief.js reads `location` at module scope for the ?tex flag, and svgSource
// falls through to fetch when nothing is overridden. Both are stubbed so the
// real module can be exercised under node rather than asserting on its text.
globalThis.location = { search: '' };
// `ok` matters now: svgSource memoises a miss as '' rather than handing back
// a 404 page's body as if it were a drawing, so a stub Response needs it.
globalThis.fetch = async () => ({ ok: true, text: async () => '<svg id="FETCHED"/>' });

const m = await import('../../../kit/relief.js');

const url = 'face.svg';
const a = m.createReliefScope();
const b = m.createReliefScope();

m.setSvgOverride(url, '<svg id="A"/>', a);
m.setSvgOverride(url, '<svg id="B"/>', b);

const out = {
  bothCorrect: [await m.svgSource(url, a), await m.svgSource(url, b)],
};

// one viewer's teardown must not reach into another's state
m.clearSvgOverrides(a);
out.bSurvivesATeardown = await m.svgSource(url, b);
out.aFallsBackToFetch = await m.svgSource(url, a);

// lamps are per-document too, for the same reason
m.setNodeStates({ 'port-1': 'state-on' }, a);
m.setNodeStates({ 'port-1': 'state-fault' }, b);
out.statesA = [...m.nodeStates(a)];
out.statesB = [...m.nodeStates(b)];

// a caller that passes no scope gets the default one, which is what every
// existing caller does - the demo pages were not changed for this
m.setSvgOverride(url, '<svg id="DEFAULT"/>');
out.defaultIsItsOwnScope = [await m.svgSource(url), await m.svgSource(url, b)];
out.defaultStatesUntouched = [...m.nodeStates()];

// THE RASTER DENSITY AND THE FRU SET were still module-level after the first
// pass at this, and the closing note on roc-ops/Portrayal#31 said so: two viewers at different
// pxmm would fight over PXMM. configureRelief now writes them onto the scope it
// is given, so a second viewer configuring cannot reclaim the first's.
const hi = m.createReliefScope();
const lo = m.createReliefScope();
const fruHi = new Set(['psu-0']);
const fruLo = new Set(['fan-0']);
m.configureRelief({ THREE: null, renderer: null, PXMM: 8, FRU_PATHS: fruHi }, hi);
m.configureRelief({ THREE: null, renderer: null, PXMM: 4, FRU_PATHS: fruLo }, lo);

// crop is the one that took the density off the module rather than the caller
const src = { width: 80, height: 80, getContext: () => ({ drawImage() {} }) };
globalThis.document = { createElement: () => ({ width: 0, height: 0,
                                                getContext: () => ({ drawImage() {} }) }) };
out.cropHonoursItsDensity = [m.crop(src, { x: 0, y: 0, w: 10, h: 10 }, 8).width,
                             m.crop(src, { x: 0, y: 0, w: 10, h: 10 }, 4).width];
// the last configureRelief call must not have moved the other scope's density
out.densitiesStaySeparate = [hi.pxmm, lo.pxmm];
out.fruSetsStaySeparate = [[...hi.fruPaths], [...lo.fruPaths]];

console.log(JSON.stringify(out));

// WHAT A VIEWER HAS TAKEN OFF is per-viewer too. The hiding itself needs a DOM
// and a WebGL context, so it is verified in a browser rather than here - pulling
// the C40G's psu-cover takes the face from 3920 distinct colours to 3866, puts
// it back at 3920 exactly, and survives a configuration rebuild at 3864, the two
// missing colours being the cover's relief, which a rebuild drops at extraction
// where a repaint can only hide the paint. What is checked HERE is that one
// viewer taking a cover off does not take it off another's, which is the same
// seat-per-holder question the overrides above answer.
m.setPulled(['psu-1'], a);
m.setPulled(['psu-2', 'fan-0'], b);
out.pullIsPerViewer = [[...m.pulledPaths(a)].sort(), [...m.pulledPaths(b)].sort()];

m.clearPulled(a);
out.clearingOneLeavesTheOther = [[...m.pulledPaths(a)], [...m.pulledPaths(b)].sort()];

// a scope nobody has pulled from is empty, not undefined
out.defaultPullIsEmpty = [...m.pulledPaths()];

// A CAGE SWAP GOES THROUGH THE SAME PER-SCOPE MAP AS A BAY SWAP, and this
// runs the cage path itself rather than the bay case under another name.
// `applyBayOverrides` (viewer3d.js) takes a face's text from svgSource in its
// OWN scope, seats the cage override with `applyOccupantOverrides`, and hands
// the rewritten text back to `setSvgOverride` in that scope. Exactly that is
// done here for viewer A choosing a simplex optic for port-4; viewer B, which
// chose nothing, must still read the build's optic off the same URL. Two
// viewers choosing different optics for the same port fighting over one map
// is the #302 lesson for bays, and a cage swap depends on the same seat.
// The face is the fake DOM's JSON form (fake-dom.mjs); nothing else about
// relief.js reads it.
const {install} = await import('./fake-dom.mjs');
install();
const swap = await import('../../../kit/swap.js');
const cageUrl = 'dev.default.front.svg';
const builtFace = JSON.stringify({t: 'svg', a: {}, c: [
  {a: {id: 'port-4', 'data-path': 'port-4', 'data-class': 'port'}},
  {a: {id: 'port-4-occupant', 'data-path': 'port-4-occupant', 'data-for': 'port-4',
       'data-behaviour': 'occupies', 'data-ref': 'generic/sfp-lc@1:1.0.0'}},
]});
const simplex = {name: 'sfp-lc-simplex', version: '1.0.0',
                 size: {w: 13.55, h: 8.55, d: 47.5}, mate: [6.775, 4.275]};
const loadSkin = async ref => ref === 'generic/sfp-lc-simplex@1' ? {comp: simplex,
  text: JSON.stringify({a: {}, c: [{a: {id: 'sfp-lc-simplex', 'data-path': 'sfp-lc-simplex',
                                        'data-behaviour': 'occupies'}}]})} : null;
m.clearSvgCache();
globalThis.fetch = async u => ({ ok: true,
  text: async () => u === cageUrl ? builtFace : '<svg id="FETCHED"/>' });
const cages = [{id: 'port-4', mate: [10, 5], rotate: null, lift: 0, mirror: false,
                'group-states': false, 'occupant-attrs': {}}];
const doc = new DOMParser().parseFromString(await m.svgSource(cageUrl, a), 'image/svg+xml');
const {applied} = await swap.applyOccupantOverrides(
  doc.documentElement, cages, {'port-4': 'generic/sfp-lc-simplex@1'}, loadSkin);
m.setSvgOverride(cageUrl, new XMLSerializer().serializeToString(doc), a);
const seatedIn = async scope => swap.occupantRef(
  new DOMParser().parseFromString(await m.svgSource(cageUrl, scope), 'image/svg+xml')
    .documentElement, 'port-4');
out.cageSwapApplied = applied;
out.cageSwapStaysInItsScope = [await seatedIn(a), await seatedIn(b)];

console.log(JSON.stringify(out));
