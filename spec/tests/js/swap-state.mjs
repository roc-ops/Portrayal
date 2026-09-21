// A swap survives a reload: the explorer's `swap=` query parameter and the
// m1. share codec both carry it, and neither may change what an un-swapped
// document or an older link reads as.
//
// Pure functions only - no DOM. `encodeSwaps`/`decodeSwaps` live in swap.js so
// the URL form is testable here; marks.js's codec has always been pure.
const swap = await import('../../../kit/swap.js');
const marks = await import('../../../kit/marks.js');

const out = {};

// ---------------------------------------------------------------- URL form
const map = {
  'slot-1/module/ppm-2': 'generic/ppm-blank@1',   // a nested bay path
  'port-4': 'generic/qsfp-lc@1',                  // a cage id
  'slot-0': null,                                 // an emptied bay
  'port-9': '',                                   // an emptied cage, spelled ''
  'weird,key~x': 'ns/odd@2',                      // separators inside a key
};
out.encoded = swap.encodeSwaps(map);
out.roundTrip = swap.decodeSwaps(out.encoded);
out.encodedAgain = swap.encodeSwaps(out.roundTrip);
// key order does not change the string (the swapKey rule: keys sorted)
out.orderFree = swap.encodeSwaps(Object.fromEntries(Object.entries(map).reverse())) === out.encoded;
out.empty = swap.encodeSwaps({});
out.garbage = [
  swap.decodeSwaps(''), swap.decodeSwaps(null), swap.decodeSwaps(undefined),
  swap.decodeSwaps(42), swap.decodeSwaps({}), swap.decodeSwaps('no-separator'),
  swap.decodeSwaps('~orphan-ref'), swap.decodeSwaps('%E0%A4%A~x'),
  swap.decodeSwaps(',,,'), swap.decodeSwaps('a~b~c'),
  swap.decodeSwaps('__proto__~evil'),
];
// one bad entry does not take the good ones with it
out.partial = swap.decodeSwaps('bad,port-4~generic%2Fqsfp-lc%401,%E0%A4%A~x');
out.protoClean = ({}).evil === undefined;

// the query string: read raw, written raw, other parameters kept
const search = swap.searchWith('?tex=flat&device=old&swap=x~y',
  {device: 's9510-28dc', config: 'dc', view: 'front', swap: out.encoded});
out.search = search;
out.searchBack = swap.decodeSwaps(swap.rawParam(search, 'swap'));
out.searchDevice = swap.rawParam(search, 'device');
out.searchTex = swap.rawParam(search, 'tex');
out.searchNoSwap = swap.searchWith('?device=a&swap=x~y', {device: 'a', swap: ''});
out.searchMissing = swap.rawParam('?device=a', 'swap');

// ---------------------------------------------------------------- m1. codec
// KNOWN-GOOD strings produced by kit/marks.js BEFORE `swaps` existed (commit
// b4e5a5a7). An un-swapped document must still encode to exactly these bytes,
// and these links must still decode - with no swaps.
const KNOWN = [
  ['m1.WzEsInM5NTEwLTI4ZGMOZGVmYXVsdA5mcm9udC0wIiwxLFtbIgFwb3J0LTQHDiNlMDAOb24OVXBsaW5rIMOpDm0xDiMwMGZmMDAPAmxlZAcOIzAwZiJdXSxbMSwyLDMwLDQwXV0',
   {device: 's9510-28dc', config: 'default', view: 'front-0', legend: true,
    crop: {x: 1, y: 2, w: 30, h: 40},
    marks: [{select: "[data-path='port-4']", color: '#e00', state: 'on',
             label: 'Uplink é', id: 'm1', lamp: '#00ff00'},
            {select: "[data-class='led']", color: '#00f'}]}],
  ['m1.WzEsInM5NTEwLTI4ZGMODnJlYXItMCIsMSxbXSwwXQ',
   {device: 's9510-28dc', config: '', view: 'rear-0', marks: []}],
];
out.unswappedIdentical = KNOWN.map(([s, doc]) => marks.encode(doc) === s);
out.unswappedEmptyMapIdentical = KNOWN.map(([s, doc]) => marks.encode({...doc, swaps: {}}) === s);
out.oldLinkSwaps = KNOWN.map(([s]) => marks.decode(s)?.swaps);
out.oldLinkMarks = KNOWN.map(([s]) => marks.decode(s)?.marks.length);

const swapped = {...KNOWN[0][1], swaps: {'port-4': 'generic/qsfp-lc@1', 'slot-0': null,
                                         'slot-1/module/ppm-2': 'generic/ppm-blank@1'}};
const s = marks.encode(swapped);
out.swappedDiffers = s !== KNOWN[0][0];
out.swappedPrefix = s.startsWith('m1.');
out.swappedBack = marks.decode(s)?.swaps;
out.swappedRest = JSON.stringify({...marks.decode(s), swaps: undefined})
               === JSON.stringify({...marks.decode(KNOWN[0][0]), swaps: undefined});
out.normaliseDefault = marks.normalise({}).swaps;
out.normaliseJunk = [marks.normalise({swaps: 'x'}).swaps, marks.normalise({swaps: [1, 2]}).swaps,
                     marks.normalise({swaps: {a: 3, b: 'ns/x@1', c: null, '': 'y'}}).swaps];

console.log(JSON.stringify(out));
