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

console.log(JSON.stringify(out));
