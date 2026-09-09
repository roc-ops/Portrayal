// A bay inside a seated module is resolved from the drawing, not the manifest.
//
// Which nested bays exist depends on what is currently populated - a dcp-2 has
// two traffic slots, and whether it also has two PPM bays depends on whether
// slot 1 holds an A22 or a DCP-404 - so they cannot be in the device manifest
// and never could be. `nestedBays` reads them off the compiled face instead.
//
// jsdom is not a dependency here, so the DOM is the smallest one the function
// actually uses: querySelectorAll over a flat list, a querySelector that
// matches `[data-path="..."]`, and getAttribute.
function el(attrs) {
  return {_attrs: attrs, getAttribute: k => (k in attrs ? attrs[k] : null)};
}

const nodes = [
  // a bay on the device itself: no `/module/` in its path
  el({id: 'slot-1', 'data-path': 'slot-1', 'data-class': 'bay'}),
  el({id: 'slot-1--module', 'data-path': 'slot-1/module',
      'data-ref': 'smartoptics/dcp-f-a22@1:1.2.0'}),
  // two bays inside what is seated in it
  el({id: 'slot-1--module--ppm-1', 'data-path': 'slot-1/module/ppm-1',
      'data-class': 'bay'}),
  el({id: 'slot-1--module--ppm-2', 'data-path': 'slot-1/module/ppm-2',
      'data-class': 'bay'}),
  // a bay in a module whose component is not in the index: skipped, not thrown
  el({id: 'slot-2--module--x', 'data-path': 'slot-2/module/x', 'data-class': 'bay'}),
  el({id: 'slot-2--module', 'data-path': 'slot-2/module',
      'data-ref': 'nobody/nothing@9:1.0.0'}),
];

const root = {
  querySelectorAll: sel => {
    if (sel !== '[data-class="bay"]') throw new Error('unexpected selector ' + sel);
    return nodes.filter(n => n.getAttribute('data-class') === 'bay');
  },
  querySelector: sel => {
    const m = /^\[data-path="(.*)"\]$/.exec(sel);
    if (!m) throw new Error('unexpected selector ' + sel);
    return nodes.find(n => n.getAttribute('data-path') === m[1]) || null;
  },
};
globalThis.CSS = {escape: s => s};

const INDEX = {
  'smartoptics/dcp-f-a22@1': {
    bays: {
      'ppm-1': {at: [147.3, 2.5], size: {w: 55.4, h: 19.5},
                accepts: ['smartoptics/ppm-ad1-1510@1', 'smartoptics/ppm-dummy@1'],
                default: 'smartoptics/ppm-dummy@1'},
      'ppm-2': {at: [147.3, 22.0], size: {w: 55.4, h: 19.5},
                accepts: ['smartoptics/ppm-ad1-1510@1', 'smartoptics/ppm-dummy@1'],
                default: 'smartoptics/ppm-dummy@1'},
    },
  },
};

const m = await import('../../../kit/swap.js');
const got = m.nestedBays(root, ref => INDEX[ref] || null);

// AFTER THE CARRIER IS REPLACED, the answer has to change. viewer3d overrides
// the device's bays first and the nested ones second, so the second pass must
// re-derive rather than reuse: 73 device bays in the library accept more than
// one bay-bearing carrier, and their nested bays differ in geometry. Reusing a
// descriptor taken before the swap seats the module at the old carrier's `at`.
const carrier = nodes.find(n => n.getAttribute('data-path') === 'slot-1/module');
carrier._attrs['data-ref'] = 'other/carrier@1:1.0.0';
INDEX['other/carrier@1'] = {
  bays: {'ppm-1': {at: [10, 20], size: {w: 5, h: 6}, accepts: ['x/y@1'], default: null}},
};
const after = m.nestedBays(root, ref => INDEX[ref] || null);

console.log(JSON.stringify({
  ids: got.map(b => b.id),
  accepts: got.map(b => b.accepts.length),
  defaults: got.map(b => b.default),
  // the descriptor has to carry what a device bay carries, or the picker and
  // the seating cannot use it
  keys: got.length ? Object.keys(got[0]).sort() : [],
  at: got.length ? got[0].at : null,
  size: got.length ? got[0].size : null,
  // the same path, re-derived after the carrier changed underneath it
  afterIds: after.map(b => b.id),
  afterAt: after.length ? after[0].at : null,
  afterAccepts: after.length ? after[0].accepts : null,
}));
