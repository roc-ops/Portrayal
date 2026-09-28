// pickerEntries (kit/devsel.js): a NOS vendor's listings become picker entries
// under that vendor (#709). Pure - no DOM - so it runs under plain node and
// prints one JSON line for test_picker_entries_js.py to read.
import { readFileSync, existsSync } from 'node:fs';
import { pickerEntries, deviceLabel } from '../../../kit/devsel.js';

const devices = [
  {name: 'as7726-32x', ns: 'edgecore', manufacturer: 'Edgecore', model: 'AS7726-32X',
   portfolio: {series: 'DCS204'}, search: 'trident'},
  {name: 's9700-53dx', ns: 'ufispace', manufacturer: 'UfiSpace', model: 'S9700-53DX',
   portfolio: {}, search: 'jericho'},
];
const listings = {
  'arrcus/as7726-32x': {hardware: 'edgecore/as7726-32x', ns: 'arrcus', manufacturer: 'Arrcus',
                        nos: 'arcos', portfolio: {line: 'Switching (XGS)'}},
  'drivenets/s9700-53dx': {hardware: 'ufispace/s9700-53dx', ns: 'drivenets',
                           manufacturer: 'DriveNets', nos: 'dnos', model: 'NCP-40C',
                           portfolio: {line: 'Network Cloud'}},
  'sonic/gone': {hardware: 'edgecore/not-in-this-build', ns: 'sonic', manufacturer: 'SONiC'},
};
const e = pickerEntries(devices, listings);
const pick = k => e.find(x => x._key === k);
const out = {
  keys: e.map(x => x._key),
  arrcus: {name: pick('arrcus/as7726-32x').name, manufacturer: pick('arrcus/as7726-32x').manufacturer,
           label: deviceLabel(pick('arrcus/as7726-32x')), line: pick('arrcus/as7726-32x').portfolio.line,
           listing: pick('arrcus/as7726-32x')._listing,
           finds: ['arrcus', 'arcos', 'trident', 'xgs'].map(w => pick('arrcus/as7726-32x').search.toLowerCase().includes(w))},
  drivenets: {label: deviceLabel(pick('drivenets/s9700-53dx')), model: pick('drivenets/s9700-53dx').model},
  hardware: {label: deviceLabel(pick('as7726-32x')), listing: pick('as7726-32x')._listing,
             manufacturer: pick('as7726-32x').manufacturer},
  bare: pickerEntries(devices).length,
};
// the real build, when there is one: every listing whose hardware is in the
// index becomes an entry, and every entry key is unique
const dist = new URL('../../../library/dist/', import.meta.url);
if (existsSync(new URL('listings.json', dist))) {
  const D = JSON.parse(readFileSync(new URL('devices.json', dist))).devices;
  const L = JSON.parse(readFileSync(new URL('listings.json', dist))).listings;
  const all = pickerEntries(D, L);
  const hw = new Set(D.map(d => `${d.ns}/${d.name}`));
  out.dist = {listings: Object.values(L).filter(l => hw.has(l.hardware)).length,
              entries: all.filter(x => x._listing).length,
              unique: new Set(all.map(x => x._key)).size === all.length};
}
console.log(JSON.stringify(out));
