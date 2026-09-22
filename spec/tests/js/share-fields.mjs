// The m1. share link carries fields (#483): slot 8, {path: {key: value|null}},
// the shape of the shell's state.cfgFields. Pure functions - marks.js's codec
// has always been pure, so no DOM here.
const marks = await import('../../../kit/marks.js');

const out = {};

// KNOWN-GOOD strings produced by kit/marks.js BEFORE `fields` existed (the codec
// as of commit bf85de83). A document without fields must still encode to exactly
// these bytes, and these links must still decode - with no fields.
const KNOWN = [
  // swapped, marked, legend, lamp colour
  ['m1.WzEsInM5NTEwLTI4ZGMOZGMOZnJvbnQiLDEsW1siAXBvcnQtNAcOI2UwMA4OdXBsaW5rLUEODiMwMGZmMDAiXV0sMCx7InBvcnQtNCI6ImdlbmVyaWMvc2ZwLWxjQDEOc2xvdC0wIjpudWxsfV0',
   {device: 's9510-28dc', config: 'dc', view: 'front', legend: true,
    marks: [{select: "[data-path='port-4']", color: '#e00', label: 'uplink-A', lamp: '#00ff00'}],
    swaps: {'port-4': 'generic/sfp-lc@1', 'slot-0': null}}],
  // un-swapped, cropped, no legend
  ['m1.WzEsInM5NTEwLTI4ZGMOZGMOZnJvbnQiLDAsW1siAXBvcnQtNAcOI2UwMCJdXSxbMSwyLDMwLDQwXV0',
   {device: 's9510-28dc', config: 'dc', view: 'front', legend: false,
    marks: [{select: "[data-path='port-4']", color: '#e00'}], crop: {x: 1, y: 2, w: 30, h: 40}}],
];
out.unfieldedIdentical = KNOWN.map(([s, doc]) => marks.encode(doc) === s);
out.emptyFieldsIdentical = KNOWN.map(([s, doc]) => marks.encode({...doc, fields: {}}) === s);
out.junkFieldsIdentical = KNOWN.map(([s, doc]) =>
  marks.encode({...doc, fields: {'port-4': {n: 3}, '': {label: 'x'}, 'port-9': 'nope'}}) === s);
out.oldLinkFields = KNOWN.map(([s]) => marks.decode(s)?.fields);
out.oldLinkSwaps = KNOWN.map(([s]) => marks.decode(s)?.swaps);

// round trip, with swaps
const FIELDS = {
  'port-4-occupant': {'latch-color': '#c22f2f', label: 'uplink-A'},
  'psu-1/module': {watts: '750W', label: null},
  'port-9-occupant': {label: ''},
};
const withSwaps = {...KNOWN[0][1], fields: FIELDS};
const s1 = marks.encode(withSwaps);
out.roundTrip = marks.decode(s1)?.fields;
out.roundTripSwaps = marks.decode(s1)?.swaps;
out.roundTripRest = JSON.stringify({...marks.decode(s1), fields: undefined})
                 === JSON.stringify({...marks.decode(KNOWN[0][0]), fields: undefined});
out.reencoded = marks.encode(marks.decode(s1)) === s1;
out.orderFree = marks.encode({...withSwaps, fields: Object.fromEntries(
  Object.entries(FIELDS).reverse().map(([p, v]) => [p, Object.fromEntries(Object.entries(v).reverse())]))}) === s1;

// a fields-only document: slot 7 is the empty value decode already accepts
const onlyFields = {...KNOWN[1][1], fields: {'port-4-occupant': {'latch-color': '#2255aa'}}};
const s2 = marks.encode(onlyFields);
out.fieldsOnlyBack = marks.decode(s2)?.fields;
out.fieldsOnlySwaps = marks.decode(s2)?.swaps;
out.fieldsOnlyRest = JSON.stringify({...marks.decode(s2), fields: undefined})
                  === JSON.stringify({...marks.decode(KNOWN[1][0]), fields: undefined});
// the raw slots: the token table only rewrites selector prefixes and '","', and
// neither occurs in these two slots' own text
const raw = new TextDecoder().decode(Uint8Array.from(
  atob(s2.slice(3).replace(/-/g, '+').replace(/_/g, '/')), c => c.charCodeAt(0)));
out.fieldsOnlyTail = raw.endsWith(',[1,2,30,40],0,{"port-4-occupant":{"latch-color":"#2255aa"}}]');

// garbage dropped, entry by entry
out.normaliseDefault = marks.normalise({}).fields;
out.normaliseJunk = [
  marks.normalise({fields: 'x'}).fields,
  marks.normalise({fields: [1, 2]}).fields,
  marks.normalise({fields: {a: 'not-an-object', b: [1], c: null}}).fields,
  marks.normalise({fields: {
    '': {label: 'no path'}, '__proto__': {label: 'evil'},
    'p': {label: 'kept', n: 3, o: {x: 1}, t: true, cleared: null, '': 'no key',
          empty: '', ctl: 'a' + String.fromCharCode(1) + 'b'},
    'q': {n: 3}}}).fields,
];
out.protoClean = ({}).label === undefined;
// a raw JSON document takes the same road
out.rawJson = marks.decode(JSON.stringify({device: 'x', fields: {p: {label: 'L', n: 1}}}))?.fields;

console.log(JSON.stringify(out));
