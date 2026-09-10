// A frontier can hold a carrier and something seated inside it, and the deeper
// one has to wait.
//
// THE FACE ARRIVES ALREADY NESTED. render.py seats every configured `default:`
// at build time, so a compiled drawing holds its nesting before any override is
// applied - 248 level-2 bay groups across 52 files in the dist today.
// `nestedBays` walks `[data-class="bay"]` and level-limits nothing, so one call
// hands back every level at once.
//
// Applied together, a deeper bay's `at` was read off the carrier the shallower
// one is about to replace, and `seen` then guarantees it is never re-derived: the
// occupant lands where the OLD carrier's bay was. spec/tests/js/nested-bay-depth
// .mjs cannot catch that - its stub reveals exactly one level per pass, which is
// not how a real face behaves, and the artificial shape is precisely where this
// bug lives.
//
// So this fixture models the real thing: three levels present from the first
// call, and seating that actually swaps the carrier, so the level-3 descriptor
// genuinely depends on when it was derived. The observable is `bayTransform`'s
// output on the seated wrapper - `translate(x,y)` from the bay's `at` - which is
// the number that goes wrong.
const NODES = [];
const created = [];

function node(attrs) {
  const el = {
    _attrs: attrs,
    getAttribute: k => (k in attrs ? attrs[k] : null),
    remove() { const i = NODES.indexOf(el); if (i >= 0) NODES.splice(i, 1); },
    querySelector: sel => {
      const m = /^\[id="(.*)"\]$/.exec(sel);
      return m ? NODES.find(n => n.getAttribute('id') === m[1]) || null : null;
    },
    appendChild: child => NODES.push(child),
  };
  return el;
}

// a face compiled with all three levels already seated
function reset() {
  NODES.length = 0;
  created.length = 0;
  NODES.push(
    node({id: 'slot-1', 'data-path': 'slot-1', 'data-class': 'bay'}),
    node({id: 'slot-1--module', 'data-path': 'slot-1/module',
          'data-ref': 'so/carrier-a@1:1.0.0'}),
    node({id: 'slot-1--module--ppm-1', 'data-path': 'slot-1/module/ppm-1',
          'data-class': 'bay'}),
    // a sibling whose id is a string-prefix of ppm-1's: it must NOT be mistaken
    // for a descendant, which is what the `+ '/'` in the filter is for
    node({id: 'slot-1--module--ppm-10', 'data-path': 'slot-1/module/ppm-10',
          'data-class': 'bay'}),
    node({id: 'slot-1--module--ppm-1--module',
          'data-path': 'slot-1/module/ppm-1/module',
          'data-ref': 'so/carrier-b@1:1.0.0'}),
    node({id: 'slot-1--module--ppm-1--module--optic-1',
          'data-path': 'slot-1/module/ppm-1/module/optic-1', 'data-class': 'bay'}),
  );
}

// carrier-b and carrier-b2 put `optic-1` in DIFFERENT places. That difference is
// the whole experiment: which one the level-3 bay resolves against says whether
// it was derived before or after its carrier was replaced.
const INDEX = {
  'so/carrier-a@1': {name: 'carrier-a',
    bays: {'ppm-1': {at: [10, 10], accepts: ['so/carrier-b@1']},
           'ppm-10': {at: [40, 10], accepts: ['so/carrier-b@1']}}},
  'so/carrier-b@1': {name: 'carrier-b', bays: {'optic-1': {at: [1, 1], accepts: ['so/leaf@1']}}},
  'so/carrier-b2@1': {name: 'carrier-b2', bays: {'optic-1': {at: [7, 3], accepts: ['so/leaf@1']}}},
  'so/leaf@1': {name: 'leaf', bays: {}},
};

globalThis.CSS = {escape: s => s};
globalThis.DOMParser = class {
  parseFromString() {
    return {getElementById: () => null, documentElement: {childNodes: []}};
  }
};

const ownerDocument = {
  createElementNS: () => {
    const attrs = {};
    const el = {
      _attrs: attrs,
      setAttribute: (k, v) => { attrs[k] = v; },
      getAttribute: k => (k in attrs ? attrs[k] : null),
      hasAttribute: k => k in attrs,
      appendChild: () => {},
      querySelectorAll: () => [],
      remove() { const i = NODES.indexOf(el); if (i >= 0) NODES.splice(i, 1); },
      querySelector: () => null,
    };
    created.push(el);
    return el;
  },
  importNode: n => n,
};

const root = {
  ownerDocument,
  querySelectorAll: sel => {
    if (sel !== '[data-class="bay"]') throw new Error('unexpected selector ' + sel);
    return NODES.filter(n => n.getAttribute('data-class') === 'bay');
  },
  querySelector: sel => {
    const m = /^\[data-path="(.*)"\]$/.exec(sel);
    if (!m) throw new Error('unexpected selector ' + sel);
    return NODES.find(n => n.getAttribute('data-path') === m[1]) || null;
  },
};

const m = await import('../../../kit/swap.js');

const deviceBays = [{id: 'slot-1', at: [0, 0], accepts: ['so/carrier-a@1']}];
// replace what is in ppm-1, AND seat something in the bay that carrier declares,
// AND touch the prefix sibling so that deferring it is observable
const OVERRIDES = {
  'slot-1/module/ppm-1': 'so/carrier-b2@1',
  'slot-1/module/ppm-10': 'so/leaf@1',
  'slot-1/module/ppm-1/module/optic-1': 'so/leaf@1',
};

const run = (maxDepth) => m.applyAllOverrides(
  root, deviceBays, OVERRIDES,
  async ref => ({comp: INDEX[ref], text: ''}),
  ref => INDEX[ref] || null, maxDepth);

const wrapper = p => created.find(e => e.getAttribute('data-path') === p);

reset();
const applied = await run(undefined);
// read before the next reset clears them
const ppm1 = wrapper('slot-1/module/ppm-1/module')?.getAttribute('data-ref') ?? null;
const opticTransform =
  wrapper('slot-1/module/ppm-1/module/optic-1/module')?.getAttribute('transform') ?? null;

// THE PREFIX GUARD, MADE OBSERVABLE. ppm-1 and ppm-10 are the same level and
// must go in the SAME pass. Drop the `+ '/'` and ppm-10 reads as a descendant of
// ppm-1, so it is deferred a pass - harmless in a deep walk, and a dropped
// override the moment the walk is bounded. At maxDepth 1 there is no next pass:
// two applied means the levels were read right, one means ppm-10 was mistaken
// for something nested inside its sibling.
reset();
const boundedApplied = await run(1);

console.log(JSON.stringify({
  applied,
  // the level-2 carrier really was swapped
  ppm1,
  // THE NUMBER THAT GOES WRONG: carrier-b2 puts optic-1 at [7,3];
  // carrier-b, the one replaced in the pass before, put it at [1,1]
  opticTransform,
  // ppm-1 and ppm-10 are siblings, so one bounded pass must catch both
  boundedApplied,
}));
