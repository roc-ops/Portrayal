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

// A TILT-CARRYING MODULE, swapped into a bay. render.py writes
// `data-tilt-on="<facet's own id>"` on a part that stands `on` a tilted
// facet, and on an occupant seated in such a part - it's an id reference,
// same shape as `data-cp-on`, and has to follow the facet's id into the
// bay's namespace or relief.js's `tiltOf` finds nothing at the old name.
const tiltNodes = [
  el({id: 'fwlt-b', 'data-path': 'fwlt-b'}),
  el({id: 'fwlt-b--facet-0'}),                                  // the facet itself
  el({id: 'fwlt-b--port-1', 'data-tilt-on': 'fwlt-b--facet-0'}), // a part standing on it
  // an occupant seated in that part inherits the tilt reference too
  el({id: 'fwlt-b--port-1-occupant', 'data-tilt-on': 'fwlt-b--facet-0'}),
  // a token naming something outside this component is left alone
  el({'data-tilt-on': 'other-component--facet-0'}),
];
m.rename({querySelectorAll: () => tiltNodes}, 'fwlt-b', 'bay-3', 'bay-3', 'module');
const tiltIds = tiltNodes.map(n => n.getAttribute('id')).filter(Boolean);
const tiltOns = tiltNodes.map(n => n.getAttribute('data-tilt-on')).filter(Boolean);

// AN OCCUPANT HAS NO `module` SEGMENT (`segment = ''`), same case
// `data-cp-on` already covers above - a tilted optic seated straight into a
// slot, not composed inside a swapped-in module.
const tiltOccupant = [
  el({id: 'sfp-tilt', 'data-path': 'sfp-tilt'}),
  el({id: 'sfp-tilt--facet-0'}),
  el({id: 'sfp-tilt--tab', 'data-tilt-on': 'sfp-tilt--facet-0'}),
];
m.rename({querySelectorAll: () => tiltOccupant}, 'sfp-tilt', 'port-9-occupant',
         'port-9-occupant', '');
const tiltOccupantIds = tiltOccupant.map(n => n.getAttribute('id')).filter(Boolean);
const tiltOccupantOns = tiltOccupant.map(n => n.getAttribute('data-tilt-on')).filter(Boolean);

// A NESTED BAY: idBase and pathBase diverge (slot-1's own bay nested inside a
// swapped module). `data-tilt-on` is renamed by the ID rule (idBase), never
// the path rule, exactly as `data-cp-on` is.
const tiltNested = [
  el({id: 'fwlt-b', 'data-path': 'fwlt-b'}),
  el({id: 'fwlt-b--facet-0'}),
  el({id: 'fwlt-b--port-1', 'data-tilt-on': 'fwlt-b--facet-0'}),
];
m.rename({querySelectorAll: () => tiltNested}, 'fwlt-b',
         'bay-3--module--slot-1', 'bay-3/module/slot-1', 'module');
const tiltNestedIds = tiltNested.map(n => n.getAttribute('id')).filter(Boolean);
const tiltNestedOns = tiltNested.map(n => n.getAttribute('data-tilt-on')).filter(Boolean);

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
  tiltIds,
  tiltOns,
  tiltOccupantIds,
  tiltOccupantOns,
  tiltNestedIds,
  tiltNestedOns,
}));
