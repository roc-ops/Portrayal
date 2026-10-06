// The pure half of the explorer's field editor (#811): the rows a form draws,
// what a typed value is worth, and the string a location carries.
import { fieldRows, fieldAccepts, encodeFields, decodeFields } from '../../../kit/fields.js';

const rating = {label: 'Rating', type: 'choice', options: [2, 3, 5, 60], default: 60, unit: 'A'};
const colour = {label: 'Latch colour', type: 'text', default: '#c22f2f', pattern: '#[0-9a-f]{6}'};
const count = {type: 'number', default: 4};

const map = {'breaker-a1/module': {rating: 30}, 'a,b~c/x': {k: 'v ~,1', gone: null}};
const enc = encodeFields(map);

console.log(JSON.stringify({
  rows: fieldRows({rating, colour, count}, {rating: '5', colour: ''}),
  none: fieldRows(undefined, {}),
  accepts: {
    option: fieldAccepts(rating, '5'), notOption: fieldAccepts(rating, '7'),
    number: fieldAccepts(count, '12'), notNumber: fieldAccepts(count, 'twelve'), emptyNumber: fieldAccepts(count, ''),
    pattern: fieldAccepts(colour, '#00ff00'), notPattern: fieldAccepts(colour, '#00ff00;x'),
    badPattern: fieldAccepts({type: 'text', pattern: '('}, 'anything'),
    undeclared: fieldAccepts(undefined, '1'),
  },
  enc,
  dec: decodeFields(enc),
  junk: decodeFields('a~b,a~b~c~d,~k~v,p~~v,__proto__~k~v,%E0~k~v,ok~k~v'),
  empty: [encodeFields({}), encodeFields(null), JSON.stringify(decodeFields('')), JSON.stringify(decodeFields(null))],
}));
