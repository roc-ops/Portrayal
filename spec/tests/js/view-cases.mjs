// The runner the view tests share (spec/tests/test_rack_view_js.py reads it): a
// script registers its cases with test(), awaits finish(), and prints ONE JSON
// line, {case name: "ok" or the failure's message}. The wrapper fails on any
// case that is not "ok" and names it.
const cases = [];
export const test = (name, fn) => { cases.push([name, fn]); };
export async function finish() {
  const out = {};
  for (const [name, fn] of cases) {
    try { await fn(); out[name] = 'ok'; } catch (err) { out[name] = String(err?.message ?? err); }
  }
  console.log(JSON.stringify(out));
}
