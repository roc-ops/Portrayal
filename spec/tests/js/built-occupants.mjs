// What a configuration seats, read ONE way - swap.js's `builtOccupants` - and
// which entries of the explorer's state are swaps (`swapOverrides`). The
// schema allows an `occupants:` value to be a mapping `{ref, id, attrs, skin}`
// and a key to name an occupant (the chained form); the explorer read both as
// flat ref strings, and an untouched page wrote a `swap=` for a boot.
//
// Pure functions only - no DOM.
const m = await import('../../../kit/swap.js');

const cages = [
  {id: 'port-4', accepts: ['generic/sfp-lc@1', 'generic/sfp-lc-simplex@1']},
  {id: 'port-5', accepts: ['generic/sfp-lc@1']},
  {id: 'port-6', accepts: ['generic/sfp-lc@1']},
];
const bays = [{id: 'slot-0', default: 'x/card@1', accepts: ['x/card@1', 'x/other@1']},
              {id: 'slot-1', accepts: ['x/card@1']}];
const cfg = {
  name: 'fitted',
  bays: {'slot-1': 'x/card@1'},
  occupants: {
    'port-4': {ref: 'generic/sfp-lc@1', id: 'uplink-optic', attrs: {speed: '10g'}},
    'port-5': 'generic/rj45-plug@1',             // the plug ...
    'port-5-occupant': 'generic/boot@1',         // ... and the boot chained on it
    'uplink-optic': 'generic/boot@1',            // chained on port-4's custom id
    'nowhere': 'generic/sfp-lc@1',               // names no cage at all
  },
};
const out = {};
out.built = m.builtOccupants(cfg, cages);
out.noOccupants = [m.builtOccupants({}, cages), m.builtOccupants(null, cages),
                   m.builtOccupants({occupants: 'junk'}, cages)];
// a chained key that happens to collide with a cage id is still a tier, not a cage
out.collision = m.builtOccupants({occupants: {'port-4': 'a', 'port-4-occupant': 'b'}},
                                 [...cages, {id: 'port-4-occupant'}]);

// THE UNTOUCHED PAGE: the state as syncCfgBays builds it, compared with the build
const untouched = {cfg, bays, cages, cfgBays: m.builtBays(cfg),
                   cfgOccupants: m.builtOccupants(cfg, cages)};
out.untouched = m.swapOverrides(untouched);
out.untouchedSwap = m.encodeSwaps(out.untouched);
out.untouchedSearch = m.searchWith('?device=d&config=fitted',
                                   {device: 'd', config: 'fitted', swap: out.untouchedSwap});

// swapping AWAY from the mapping-form optic and BACK to it is no swap
const away = {...untouched, cfgOccupants: {...untouched.cfgOccupants, 'port-4': 'generic/sfp-lc-simplex@1'}};
out.away = m.swapOverrides(away);
const back = {...untouched, cfgOccupants: {...untouched.cfgOccupants, 'port-4': 'generic/sfp-lc@1'}};
out.back = m.swapOverrides(back);
// emptying the mapping-form optic is a swap; a cage the config never named, filled, is one
out.emptied = m.swapOverrides({...untouched, cfgOccupants: {...untouched.cfgOccupants, 'port-4': null}});
out.filled = m.swapOverrides({...untouched, cfgOccupants: {...untouched.cfgOccupants, 'port-6': 'generic/sfp-lc@1'}});
// bays: the configuration's entry, else the bay default
out.bays = [
  m.swapOverrides({...untouched, cfgBays: {'slot-0': 'x/card@1', 'slot-1': 'x/card@1'}}),
  m.swapOverrides({...untouched, cfgBays: {'slot-0': 'x/other@1'}}),
  m.swapOverrides({...untouched, cfgBays: {'slot-1': null}}),
];

// A NESTED BAY THE CONFIGURATION SEATS: the manifest keys it without the
// `/module` step (`slot-1/ppm-1`), the drawing - and so the state and every
// bay id - with it. The dcp-2 ila-node shape: the carrier's default holds a
// dummy cover, the configuration seats a real PPM.
const nBays = [{id: 'slot-1', default: 'x/carrier@1', accepts: ['x/carrier@1']}];
const nCfg = {name: 'ila-node', bays: {'slot-1/ppm-1': 'x/ppm-1510@1'}};
out.nestedBuilt = m.builtBays(nCfg);
const nUntouched = {cfg: nCfg, bays: nBays, cages: [], cfgBays: m.builtBays(nCfg), cfgOccupants: {}};
out.nestedUntouched = m.swapOverrides(nUntouched);
out.nestedUntouchedSwap = m.encodeSwaps(out.nestedUntouched);
// the drawing's key seated as built is no swap; a different module there is one
out.nestedAsBuilt = m.swapOverrides({...nUntouched, cfgBays: {'slot-1/module/ppm-1': 'x/ppm-1510@1'}});
out.nestedSwapped = m.swapOverrides({...nUntouched, cfgBays: {'slot-1/module/ppm-1': 'x/cover@1'}});
out.noBays = [m.builtBays({}), m.builtBays(null), m.builtBays({bays: 'junk'})];
console.log(JSON.stringify(out));
