// What the 3D explorer is handed, run against REAL compiled drawings (B3
// Task 10c). test_explorer_3d_js.py renders tmp copies of fs/fhd-1ufce and
// smartoptics/dcp-r-34d-cs with configurations that ask the build for what
// the explorer is asked to do, builds components.json and the component
// skins in tmp, and hands this script the drawings (fake-dom form), the index
// and the skins. What the kit makes of them is compared, in Python, with what
// render.py drew.
//
// Modes, by argv[2]:
//   roles  - stdin JSON {sets: {name: {back, nodes: [{ref, behaviour, for,
//            path, cls}]}}}; relief.js's bodyBehaviour and bodyRole for every
//            instance of a real drawing, and the FRU keys extractRelief makes.
//   eject  - stdin JSON {cases: [{name, body, bodyDepth, depth, occupies,
//            feats, base, into}]}; reliefExtent and ejectTravel.
//   faces  - stdin JSON {components, skins, cases: [{name, face, bays,
//            cages, map}]}; seatViews over each case's faces, as viewer3d
//            rewrites them before any relief is cut, with each face's result.
//   backs  - stdin JSON {components, skins, cases: [{name, back, bay,
//            moduleRef, map}]}; seatBack into a module's own back drawing,
//            as viewer3d hands relief.js the back it builds in 3D.
// SWAP_MODULE / RELIEF_MODULE name the swap.js / relief.js to load; by
// default the kit's own. A
// scenario that throws records {error} and the rest still run.
import {pathToFileURL} from 'node:url';
import {build, install, toSpec} from './fake-dom.mjs';

globalThis.location = {search: ''};
const mode = process.argv[2];
let raw = '';
for await (const chunk of process.stdin) raw += chunk;
const input = JSON.parse(raw);
const out = {};
const run = async (name, fn) => {
  try { out[name] = await fn(); }
  catch (e) { out[name] = {error: String(e && e.stack || e)}; }
};

if (mode === 'roles' || mode === 'eject') {
  const R = await import(process.env.RELIEF_MODULE
    ? pathToFileURL(process.env.RELIEF_MODULE).href : '../../../kit/relief.js');
  // THE KIT BEFORE THE FIX, kept only as the stand-in when relief.js has
  // none of these, so a RED run records what the old kit did rather than a
  // missing function: fills / occupies / a legacy class were collected (no
  // plug), and every part travelled 1.5 x (body, body-depth or 60) + 25 and
  // left that deep a box.
  const bodyBehaviour = R.bodyBehaviour || (n => !n.ref ? null
    : ['fills', 'occupies'].includes(n.behaviour) ? n.behaviour
    : (!n.behaviour && ['psu', 'fan', 'tab', 'power', 'cooling'].includes(n.cls)) ? 'class' : null);
  const reliefExtent = R.reliefExtent || (() => 0);
  const ejectTravel = R.ejectTravel || (({body, bodyDepth, into}) => {
    const d = body ? body.depth : (bodyDepth || 60);
    return {pull: Math.min((body && body.travel) || d * 1.5 + 25, Math.max(into - 10, d + 10)), leavesBay: true, bayDepth: d};
  });
  if (mode === 'roles') {
    for (const [name, {back, nodes}] of Object.entries(input.sets)) {
      await run(name, async () => {
        // bodyBehaviour decides what is collected at all (a plug included),
        // bodyRole what it is built as - extractRelief's two questions
        const roles = nodes.map(n => {
          const behaviour = bodyBehaviour(n);
          return {path: n.path, raw: n.behaviour ?? null, for: n.for ?? null, behaviour,
                  role: behaviour ? R.bodyRole(n.path, behaviour, {back}) : null};
        });
        // extractRelief's collection: one FRU per key, the first instance wins
        const frus = [];
        for (const r of roles)
          if (r.role?.fru && !frus.includes(r.role.fru)) frus.push(r.role.fru);
        return {roles, frus};
      });
    }
  } else {
    // how far a pulled part travels, and whether it leaves a box: reliefExtent
    // over the part's own features, then ejectTravel
    for (const c of input.cases) {
      await run(c.name, async () => {
        const extent = reliefExtent(c.feats, c.base);
        return {extent, travel: ejectTravel({body: c.body, bodyDepth: c.bodyDepth, depth: c.depth,
                                               occupies: c.occupies, extent, into: c.into})};
      });
    }
  }
} else {
  install();
  const m = await import(process.env.SWAP_MODULE
    ? pathToFileURL(process.env.SWAP_MODULE).href : '../../../kit/swap.js');
  const COMPS = new Map(input.components.map(c => [`${c.ns}/${c.name}@${c.major.slice(1)}`, c]));
  const compByRef = ref => COMPS.get(String(ref).split(':')[0]) || null;
  const loadSkin = async ref => {
    const comp = compByRef(ref);
    const text = input.skins[String(ref).split(':')[0]];
    return comp && text ? {comp, text} : null;
  };
  const plain = r => r && Object.fromEntries(Object.entries(r)
    .filter(([k]) => ['applied', 'dropped', 'refused', 'failed', 'rear'].includes(k)));
  // THE PASS viewer3d RAN BEFORE seatViews, kept only as the stand-in for a
  // kit that has none, so a RED run records the real differences rather than
  // a missing function: the faces viewsToRewrite names through
  // applyFaceOverrides, then every face's rear holes through
  // applyRearOverrides, which re-seats only the bays the map swapped.
  const oldSeatViews = async (roots, devIndex, map) => {
    const out_ = {};
    for (const view of m.viewsToRewrite(devIndex, map))
      if (roots[view]) out_[view] = await m.applyFaceOverrides(roots[view],
        {bays: devIndex.bays?.[view] || [], cages: devIndex.cages?.[view] || []}, map, loadSkin, compByRef);
    for (const [view, root] of Object.entries(roots)) {
      const n = await m.applyRearOverrides(root, map, loadSkin, compByRef);
      out_[view] = {...(out_[view] || {applied: 0, refused: [], failed: []}),
                    rear: {applied: n?.applied ?? n}};
    }
    return out_;
  };
  if (mode === 'faces') {
    for (const c of input.cases) {
      await run(c.name, async () => {
        const roots = Object.fromEntries(Object.entries(c.faces).map(([v, f]) => [v, build(f)]));
        const res = await (m.seatViews || oldSeatViews)(roots, {bays: c.bays, cages: c.cages}, c.map,
                                                        loadSkin, compByRef);
        return {res: Object.fromEntries(Object.entries(res).map(([v, r]) => [v, plain(r)])),
                faces: Object.fromEntries(Object.entries(roots).map(([v, r]) => [v, toSpec(r)]))};
      });
    }
  } else if (mode === 'backs') {
    for (const c of input.cases) {
      await run(c.name, async () => {
        const root = build(c.back);
        // before seatBack, the kit never touched a module's own back drawing
        if (!m.seatBack) return {res: {applied: 0, refused: [], failed: []}, back: toSpec(root)};
        const res = await m.seatBack(root, {bay: c.bay, moduleRef: c.moduleRef}, c.map,
                                     loadSkin, compByRef);
        return {res: plain(res), back: toSpec(root)};
      });
    }
  }
}
console.log(JSON.stringify(out));
