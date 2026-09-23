// Which removable parts get a body and an ejectable group of their own - the
// decision kit/relief.js's extractRelief makes for every fills/occupies
// instance, factored out as `bodyRole` so it can be held here (#484).
globalThis.location = { search: '' };
const {bodyRole, opticBody, fruFor} = await import('../../../kit/relief.js');
const cases = {
  deviceOptic: ['port-4-occupant', 'occupies'],
  deviceChained: ['port-5-occupant-occupant', 'occupies'],
  bayModule: ['front-6/module', 'fills'],
  cardOptic: ['front-6/module/xg0-occupant', 'occupies'],
  cardChained: ['front-6/module/xg0-occupant-occupant', 'occupies'],
  cardPart: ['front-6/module/xg0', 'fills'],
  nestedBayModule: ['slot-1/module/ppm-1/module', 'fills'],
  deepCardOptic: ['slot-1/module/ppm-1/module/p0-occupant', 'occupies'],
  legacyClass: ['psu-1/module', null],
  empty: ['', 'occupies'],
  nul: [null, 'fills'],
};
const out = Object.fromEntries(Object.entries(cases).map(([k, [p, b]]) => [k, bodyRole(p, b)]));
// B3 Task 10c: an occupant two segments down is its own part too - a cap in
// a bore of an adapter placed on the device, or on a back's bulkhead read as
// a lone drawing - and on a module's BACK no occupant is a FRU
out.boreCap = bodyRole('xc01/1-occupant', 'occupies');
out.loneBackCap = bodyRole('fhd-2mtp12-lc-rear/mtp1-occupant', 'occupies');
out.backCap = bodyRole('fhd-2mtp12-lc-rear/mtp1-occupant', 'occupies', {back: true});
out.backBayModule = bodyRole('front-6/module', 'fills', {back: true});
// the body a seated optic with no `body:` block gets: its face outline, run
// back to its own depth (the skin root's data-depth, the contract's size.d)
out.body = {
  sfp: opticBody({behaviour: 'occupies', body: null, depth: 47.5, w: 8.55, h: 13.55}),
  qsfp: opticBody({behaviour: 'occupies', body: null, depth: 52.4, w: 18.35, h: 8.5}),
  qsfpdd: opticBody({behaviour: 'occupies', body: null, depth: 58.26, w: 18.35, h: 8.5}),
  declared: opticBody({behaviour: 'occupies', body: {depth: 70}, depth: 47.5, w: 8, h: 13}),
  module: opticBody({behaviour: 'fills', body: null, depth: 60, w: 30, h: 300}),
  legacy: opticBody({behaviour: null, body: null, depth: 60, w: 30, h: 300}),
  noDepth: opticBody({behaviour: 'occupies', body: null, depth: null, w: 8, h: 13}),
  zeroSize: opticBody({behaviour: 'occupies', body: null, depth: 47.5, w: 0, h: 13}),
  nothing: opticBody(),
};
// which FRU group a selection marker rides with: the longest FRU prefix
const keys = new Set(['front-6', 'front-6/module/xg0-occupant', 'port-4-occupant', 'psu-1']);
const has = k => keys.has(k);
out.fruFor = {
  cardOptic: fruFor('front-6/module/xg0-occupant', has),
  cardOpticPart: fruFor('front-6/module/xg0-occupant/tx', has),
  cardCage: fruFor('front-6/module/xg0', has),
  card: fruFor('front-6/module', has),
  bay: fruFor('front-6', has),
  prefixNotSegment: fruFor('front-60/module', has),
  deviceOptic: fruFor('port-4-occupant/tx', has),
  module: fruFor('psu-1/module/status', has),
  none: fruFor('chassis/label', has),
  empty: fruFor('', has),
};
console.log(JSON.stringify(out));
