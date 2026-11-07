// kit/housing.js run on the payload a test writes to stdin: {mode, ...}.
// Prints one JSON line. No three.js and no DOM, so it runs anywhere node does.
import * as H from '../../../kit/housing.js';

const input = JSON.parse(await new Promise(res => {
  let s = ''; process.stdin.on('data', d => { s += d; }); process.stdin.on('end', () => res(s));
}));

const round = v => (typeof v === 'number' ? Math.round(v * 1e6) / 1e6
  : Array.isArray(v) ? v.map(round)
  : v && typeof v === 'object' ? Object.fromEntries(Object.entries(v).map(([k, x]) => [k, round(x)])) : v);

// the sixteen corners of the two halves in the box frame, worked out here from
// the plan and not from openBounds, so the test has its own answer to compare
function halfCorners(plan) {
  const out = [];
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) for (const sz of [-1, 1]) {
    const [a, b, c] = plan.base.size, [d, e, f] = plan.lid.size;
    out.push(plan.base.center.map((v, i) => v + [sx * a, sy * b, sz * c][i] / 2));
    out.push(H.lidPoint(plan, [sx * d / 2, sy * e / 2, sz * f / 2]));
  }
  return out;
}

const out = {};
for (const c of input.cases) {
  const plan = H.housingPlan(c.halves, c.size);
  out[c.name] = {
    plan: round(plan),
    corner: plan && c.corner ? round(H.lidPoint(plan, c.corner)) : null,
    plates: plan && c.bays ? round(['base', 'lid'].map(n => H.bayPlates(plan, n, c.bays))) : null,
    bounds: plan && c.bounds ? round(H.openBounds(plan)) : null,
    corners: plan && c.bounds ? round(halfCorners(plan)) : null,
  };
}
out.describe = input.metas.map(m => round(H.describeHalves(m)));
out.view = input.metas.map(m => H.openViewOf(m));
out.views = input.views.map(([i, state, cur]) => H.viewFor(input.metas[i], state, cur));
out.state =input.states.map(s => H.normalizeHousing(s));
console.log(JSON.stringify(out));
