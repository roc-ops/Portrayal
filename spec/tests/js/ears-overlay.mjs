// The kit's 2D ear overlay (kit/ears2d.js), run over faces render.py drew
// WITHOUT ears; spec/tests/test_ears_overlay.py compares what it draws with
// the same faces drawn `--with ears`.
//
// stdin: {cases: [{name, meta: {chassis}, front: <the front's SVG text>,
//                  view, root: <the face's root, fake-dom form>}]}
// stdout: per case {plan, n, drawn: <root after drawEars, fake-dom form>,
//                   cleared: <root attributes after clearEars>}
// The plan is made the way a page makes it: configs.json's chassis and the
// front's declared width, read off the front's text.
import {build, install, toSpec} from './fake-dom.mjs';

globalThis.location = {search: ''};
install();
const E = await import('../../../kit/ears2d.js');
let raw = '';
for await (const chunk of process.stdin) raw += chunk;
const out = {};
for (const c of JSON.parse(raw).cases) {
  try {
    const plan = E.earPlan(c.meta, E.frontWidthOfText(c.front));
    const svg = build(c.root);
    const n = E.drawEars(svg, plan, c.view);
    const drawn = toSpec(svg);
    // drawn twice is drawn once: the second call replaces the first
    const again = E.drawEars(svg, plan, c.view);
    const twice = svg.querySelectorAll('[data-overlay="ears"]').length;
    E.clearEars(svg);
    out[c.name] = {plan, n, again, twice, drawn, cleared: toSpec(svg)};
  } catch (e) {
    out[c.name] = {error: String(e && e.stack || e)};
  }
}
console.log(JSON.stringify(out));
