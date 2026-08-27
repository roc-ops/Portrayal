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
globalThis.fetch = async () => ({ text: async () => '<svg id="FETCHED"/>' });

const m = await import('../../../library/viewer/relief.js');

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
// pass at this, and the closing note on ndv#31 said so: two viewers at different
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
