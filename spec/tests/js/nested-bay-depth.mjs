// The override walk follows the frontier down, however deep it goes.
//
// `applyAllOverrides` seats what it knows, looks again, and repeats while
// looking still finds something new. It cannot know the nested bays up front:
// which ones exist is a property of the carrier CURRENTLY seated.
//
// WHAT THIS FIXTURE MODELS, NARROWLY: nesting that an override CREATES. Seat a
// carrier that declares bays of its own and those bays did not exist in the
// document a moment ago, so they appear a level at a time - which is what the
// `revealed` counter below stands in for.
// It does NOT model nesting the face ALREADY HAS, and an earlier version of this
// comment wrongly claimed the two behave alike. render.py seats every configured
// `default:` at build time, so most nesting is present from the first call and a
// single frontier holds several levels at once. That case, and the stale
// geometry it used to cause, is nested-bay-frontier.mjs.
//
// NOTHING IN THE LIBRARY IS THREE LEVELS DEEP TODAY - all 670 `accepts` entries
// across the 84 nested bays resolve, and not one names a component that itself
// declares bays - so this fixture is hand-built. That is the point: a fix for a
// depth the library cannot yet reach would otherwise ship untested, and the
// first three-level carrier someone models would find out the hard way.
//
// WHAT THIS COVERS AND WHAT IT DOES NOT. It covers the WALK: that the loop goes
// past two levels, that a bay already applied is not revisited, that it stops on
// its own when a pass reveals nothing new, and that `maxDepth` bounds a drawing
// that never stops revealing. The SEATING itself - `seatModule`, `rename`,
// `bayTransform` - needs a real DOM and is covered by swap-url-refs.mjs and by
// the compiled-output tests; here `loadSkin` returns null, which makes
// `applyOverrides` count the bay and seat nothing, so no DOMParser is needed.
function el(attrs) {
  return {_attrs: attrs, getAttribute: k => (k in attrs ? attrs[k] : null)};
}

globalThis.CSS = {escape: s => s};

// Three levels. Each becomes visible only after the one above it is seated,
// which is what the `revealed` counter stands in for: `nestedBays` walks the
// document, and the document grows as modules land in it.
const LEVELS = [
  [el({id: 'slot-1', 'data-path': 'slot-1', 'data-class': 'bay'}),
   el({id: 'slot-1--module--ppm-1', 'data-path': 'slot-1/module/ppm-1',
       'data-class': 'bay'}),
   el({id: 'slot-1--module', 'data-path': 'slot-1/module',
       'data-ref': 'so/carrier-a@1:1.0.0'})],
  [el({id: 'slot-1--module--ppm-1--module--optic-1',
       'data-path': 'slot-1/module/ppm-1/module/optic-1', 'data-class': 'bay'}),
   el({id: 'slot-1--module--ppm-1--module',
       'data-path': 'slot-1/module/ppm-1/module', 'data-ref': 'so/carrier-b@1:1.0.0'})],
  [el({id: 'slot-1--module--ppm-1--module--optic-1--module--tap',
       'data-path': 'slot-1/module/ppm-1/module/optic-1/module/tap',
       'data-class': 'bay'}),
   el({id: 'slot-1--module--ppm-1--module--optic-1--module',
       'data-path': 'slot-1/module/ppm-1/module/optic-1/module',
       'data-ref': 'so/carrier-c@1:1.0.0'})],
];

const INDEX = {
  'so/carrier-a@1': {bays: {'ppm-1': {at: [0, 0], size: {w: 1, h: 1}, accepts: ['so/carrier-b@1']}}},
  'so/carrier-b@1': {bays: {'optic-1': {at: [0, 0], size: {w: 1, h: 1}, accepts: ['so/carrier-c@1']}}},
  'so/carrier-c@1': {bays: {'tap': {at: [0, 0], size: {w: 1, h: 1}, accepts: ['so/leaf@1']}}},
};

let revealed = 0;                  // how many levels have been "seated" so far
const nodes = () => LEVELS.slice(0, revealed).flat();

const root = {
  querySelectorAll: sel => {
    if (sel !== '[data-class="bay"]') throw new Error('unexpected selector ' + sel);
    // a pass over the document reveals the next level, the way seating does
    const seen = nodes().filter(n => n.getAttribute('data-class') === 'bay');
    if (revealed < LEVELS.length) revealed++;
    return seen;
  },
  querySelector: sel => {
    const m = /^\[data-path="(.*)"\]$/.exec(sel);
    if (!m) throw new Error('unexpected selector ' + sel);
    const n = nodes().find(x => x.getAttribute('data-path') === m[1]);
    return n ? {...n, querySelector: () => null, appendChild: () => {}} : null;
  },
};

const m = await import('../../../kit/swap.js');

const deviceBays = [{id: 'slot-1', at: [0, 0], size: {w: 1, h: 1}, accepts: ['so/carrier-a@1']}];
const OVERRIDES = {
  'slot-1': 'so/carrier-a@1',
  'slot-1/module/ppm-1': 'so/carrier-b@1',
  'slot-1/module/ppm-1/module/optic-1': 'so/carrier-c@1',
  'slot-1/module/ppm-1/module/optic-1/module/tap': 'so/leaf@1',
};

revealed = 1;                      // the device bay's own occupant is already in
const {applied, dropped} = await m.applyAllOverrides(
  root, deviceBays, OVERRIDES, async () => null, ref => INDEX[ref] || null);

// and again with the walk bounded to one nested pass, to show the bound bites
revealed = 1;
const boundedRun = await m.applyAllOverrides(
  root, deviceBays, OVERRIDES, async () => null, ref => INDEX[ref] || null, 1);
const bounded = boundedRun.applied;

console.log(JSON.stringify({applied, bounded, levels: LEVELS.length,
                           dropped, boundedDropped: boundedRun.dropped}));
