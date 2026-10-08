// normalise() over documents that reach every branch of it, printed as one JSON
// line for test_marks_schema_js.py to validate against marks.schema.json.
import {normalise} from '../../../kit/marks.js';

const cases = {
  empty: {},
  minimal: {v: 1, device: 'as7946-30xb', marks: [{select: '#psu-0'}]},
  full: {v: 1, device: 'as7946-30xb', config: 'dc', view: 'rear', legend: {title: 'PSUs'},
         crop: {x: 1.5, y: 2, w: 30, h: 12},
         marks: [{id: 'm1', select: "[data-path='psu-0']", color: '#ff2d95', state: 'on', label: 'PSU 0', lamp: '#00FF00'},
                 {select: '.led', state: 'off'}],
         swaps: {'port-4': 'generic/qsfp-lc@1', 'slot-1': null},
         fields: {'port-4-occupant': {'latch-color': 'red', label: null}}},
  junk: {v: 9, legend: false, crop: {x: 0, y: 0, w: -1, h: 2}, marks: [null, 'x', {select: 3, lamp: 'red'}],
         swaps: [], fields: {'__proto__': {a: 'b'}, p: 'not an object'}},
  arrayLegend: {legend: []},
};
console.log(JSON.stringify(Object.fromEntries(Object.entries(cases).map(([k, d]) => [k, normalise(d)]))));
