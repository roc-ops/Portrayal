// What a configuration seats, read ONE way - swap.js's `builtOccupants` - and
// which entries of the explorer's state are swaps (`swapOverrides`). The
// schema allows an `occupants:` value to be a mapping `{ref, id, attrs, skin}`
// and a key to name an occupant (the chained form); the explorer read both as
// flat ref strings, and an untouched page wrote a `swap=` for a boot.
//
// Pure functions only - no DOM.
const m = await import('../../../kit/swap.js');

const cages = [
  {id: 'port-4', accepts: ['generic/sfp-lc@1', 'generic/sfp-lc-simplex@2']},
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
const away = {...untouched, cfgOccupants: {...untouched.cfgOccupants, 'port-4': 'generic/sfp-lc-simplex@2'}};
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

// AN OPTIC THE CONFIGURATION SEATS IN A CARD'S CAGE (#484): the manifest keys
// it without the `/module` step (`front-6/xg0`), the drawing - and so the
// explorer's state, the swap map and the 3D overrides - with it. The c100g
// shape: the card is configured, and so are optics in two of its cages, one
// of them in the mapping form with a custom id, each with a tier chained on.
const cBays = [{id: 'front-6', default: 'casa/blank@1', accepts: ['casa/blank@1', 'casa/smm@1']}];
const cCfg = {name: 'fitted', bays: {'front-6': 'casa/smm@1'}, occupants: {
  'front-6/xg0': 'generic/sfp-lc@1',
  'front-6/xg0-occupant': 'generic/boot@1',          // chained on xg0's optic
  'front-6/cg0': {ref: 'generic/qsfp-lc@1', id: 'uplink'},
  'front-6/uplink': 'generic/boot@1',                // chained on the custom id
  'port-4': 'generic/sfp-lc@1',
}};
out.cardBuilt = m.builtOccupants(cCfg, cages);
const cUntouched = {cfg: cCfg, bays: cBays, cages, cfgBays: m.builtBays(cCfg),
                    cfgOccupants: m.builtOccupants(cCfg, cages)};
out.cardUntouched = m.swapOverrides(cUntouched);
out.cardUntouchedSearch = m.searchWith('?device=c100g&config=fitted',
  {device: 'c100g', config: 'fitted', swap: m.encodeSwaps(out.cardUntouched)});
// the built optic, chosen away and back, is no swap; emptied, it is one.
// EACH CHOICE GOES THROUGH WHAT THE SHELL'S dropOnSlot DOES FIRST (#611): the
// state under the slot is pruned (pruneCarrier) - since the chained tier is
// a slot, that includes the boot the build put on the old optic - and put
// back as built only when the choice IS what the build seated there.
const withCard = occ => {
  let st = {cfgBays: cUntouched.cfgBays, cfgOccupants: cUntouched.cfgOccupants};
  for (const [key, ref] of Object.entries(occ)) {
    const builtRef = cUntouched.cfgOccupants[key] ?? null;
    st = m.pruneCarrier(st, key, ref && ref === builtRef ? cUntouched.cfgOccupants : {});
    st = {...st, cfgOccupants: {...st.cfgOccupants, [key]: ref}};
  }
  return m.swapOverrides({...cUntouched, cfgBays: st.cfgBays, cfgOccupants: st.cfgOccupants});
};
// and without that step, a boot left in the state on an optic it was not
// built on IS asked for - so it is measured, and reported, as a swap
out.cardAwayUnpruned = m.swapOverrides({...cUntouched,
  cfgOccupants: {...cUntouched.cfgOccupants, 'front-6/module/xg0': 'generic/sfp-lc-simplex@2'}});
out.cardAway = withCard({'front-6/module/xg0': 'generic/sfp-lc-simplex@2'});
out.cardBack = withCard({'front-6/module/xg0': 'generic/sfp-lc@1'});
out.cardEmptied = withCard({'front-6/module/xg0': null});
out.cardFilled = withCard({'front-6/module/xg1': 'generic/sfp-lc@1'});
// ON A CARD THE STATE HAS SWAPPED, the build's optics are not there: a fresh
// card is seated from its component, whose cages hold nothing. So an optic
// chosen there IS a swap even when it names what the build put in the old
// card's cage of the same id - or 3D, handed only the card, shows it empty.
out.cardOnSwappedCarrier = m.swapOverrides({...cUntouched,
  cfgBays: {'front-6': 'casa/smm-b@1'},
  cfgOccupants: {'front-6/module/xg0': 'generic/sfp-lc@1'}});
console.log(JSON.stringify(out));
