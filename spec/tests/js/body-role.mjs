// Which removable parts get a body and an ejectable group of their own - the
// decision kit/relief.js's extractRelief makes for every fills/occupies
// instance, factored out as `bodyRole` so it can be held here (#484).
globalThis.location = { search: '' };
const {bodyRole} = await import('../../../kit/relief.js');
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
console.log(JSON.stringify(Object.fromEntries(
  Object.entries(cases).map(([k, [p, b]]) => [k, bodyRole(p, b)]))));
