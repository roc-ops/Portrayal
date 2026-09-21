// A skin that clips by reference must still clip once it is seated in a bay.
//
// `rename()` moved every `id` into the bay's namespace and left every
// `url(#...)` naming one pointing at the old name. SVG does not fail a dangling
// clip-path - it draws the element UNCLIPPED - so a swapped drive carrier put
// its honeycomb across the whole card and nothing reported a fault.
//
// jsdom is not a dependency here, so the DOM is the smallest one that
// `rename()` actually uses: querySelectorAll over a flat list, getAttribute,
// setAttribute, removeAttribute, and an `attributes` array.
function el(attrs) {
  const a = {...attrs};
  return {
    get attributes() {
      return Object.entries(a).map(([name, value]) => ({name, value}));
    },
    getAttribute: k => (k in a ? a[k] : null),
    setAttribute: (k, v) => { a[k] = v; },
    removeAttribute: k => { delete a[k]; },
    _attrs: a,
  };
}

const nodes = [
  el({id: 'drive-carrier-25', 'data-path': 'drive-carrier-25'}),
  el({id: 'drive-carrier-25--w0'}),                       // <clipPath>
  el({'clip-path': 'url(#drive-carrier-25--w0)',
      'data-path': 'drive-carrier-25/window-1'}),         // the group it clips
  el({fill: 'url(#drive-carrier-25--hex)'}),              // a pattern fill
  el({id: 'drive-carrier-25--hex'}),
  el({fill: 'url(#portrayal-vent)'}),                     // not ours: untouched
];
const wrap = {querySelectorAll: () => nodes};

const m = await import('../../../kit/swap.js');
m.rename(wrap, 'drive-carrier-25', 'drive-r0');

const ids = nodes.map(n => n.getAttribute('id')).filter(Boolean);
const refs = nodes
  .map(n => n.getAttribute('clip-path') || n.getAttribute('fill'))
  .filter(Boolean);

// A CAGE HAS NO NAMESPACE WORD. An optic seated in `port-4` is the top-level
// `port-4-occupant`, and rename's `segment = ''` names its children
// `port-4-occupant--w0` - the second pass has to follow that spelling too, or
// every clipped optic a swap seats draws unclipped the way the drive carrier did.
const optic = [
  el({id: 'sfp-lc', 'data-path': 'sfp-lc'}),
  el({id: 'sfp-lc--w0'}),                                 // <clipPath>
  el({'clip-path': 'url(#sfp-lc--w0)', 'data-path': 'sfp-lc/face'}),
  el({fill: 'url(#portrayal-vent)'}),
];
m.rename({querySelectorAll: () => optic}, 'sfp-lc', 'port-4-occupant',
         'port-4-occupant', '');
const cageIds = optic.map(n => n.getAttribute('id')).filter(Boolean);
const cageRefs = optic
  .map(n => n.getAttribute('clip-path') || n.getAttribute('fill'))
  .filter(Boolean);

console.log(JSON.stringify({
  ids,
  refs,
  // every url(#...) that names something must name something that exists
  dangling: refs
    .map(r => (r.match(/url\(#([^)]*)\)/) || [])[1])
    .filter(id => id && id.startsWith('drive-') && !ids.includes(id)),
  cageIds,
  cageRefs,
  cageDangling: cageRefs
    .map(r => (r.match(/url\(#([^)]*)\)/) || [])[1])
    .filter(id => id && id !== 'portrayal-vent' && !cageIds.includes(id)),
}));
