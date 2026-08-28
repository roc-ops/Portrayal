// buildFaceRelief asked whether a view existed with a HEAD and then fetched the
// same URL again, so every face cost two round trips and the second proved
// nothing the first had not. Measured on a six-device rack: 66 requests of which
// 30 were duplicates. This exercises the replacement - svgSource memoises the
// miss, so one request answers both questions and a repeat asks nothing.
//
// relief.js reads `location` at module scope for the ?tex flag; stubbed so the
// real module runs under node rather than asserting on its text.
globalThis.location = { search: '' };

const calls = [];
globalThis.fetch = async (url, opts = {}) => {
  calls.push({ url, method: opts.method || 'GET' });
  if (url === 'present.svg')
    return { ok: true, text: async () => '<svg id="PRESENT"/>' };
  return { ok: false, status: 404, text: async () => '<html>404 Not Found</html>' };
};

const m = await import('../../../library/viewer/relief.js');
const scope = m.createReliefScope();

const present = await m.svgSource('present.svg', scope);
const missing = await m.svgSource('missing.svg', scope);

// asking twice more must cost nothing
await m.svgSource('present.svg', scope);
await m.svgSource('missing.svg', scope);

console.log(JSON.stringify({
  present,
  // a 404 body is NOT handed back as if it were a drawing
  missing,
  missingIsFalsy: !missing,
  // every existing caller degrades on '' rather than throwing
  matchAllSurvives: [...missing.matchAll(/x/g)].length,
  requests: calls.length,
  methods: [...new Set(calls.map(c => c.method))],
  urls: calls.map(c => c.url).sort(),
}));
