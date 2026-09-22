// Which entries of a reloaded `swap=` map the explorer takes into its state.
// Everything it takes is written back to the URL AND sent to the 3D scene,
// whose applyOverrides has no accepts check - so an entry the 2D face would
// refuse must never get this far. The rule: an entry is taken only when it
// names a bay or cage that exists AND its ref is one that bay or cage accepts
// (an empty ref is always allowed for one that exists). A nested bay exists
// only by virtue of what its carrier holds, so a nested key is resolved after
// its carrier's own entry is decided - level by level, as applyAllOverrides
// walks the frontier.
const {acceptSwaps} = await import('../../../kit/swap.js');

const COMPS = {
  'so/a22@1': {bays: {'ppm-1': {accepts: ['so/ppm-x@1', 'so/ppm-y@1'], default: 'so/ppm-x@1'},
                      'ppm-2': {accepts: ['so/ppm-x@1', 'so/deep@1']}}},
  'so/deep@1': {bays: {'sub-1': {accepts: ['so/leaf@1']}}},
  'so/blank@1': {bays: {}},
  // a card with cages of its own (components.json `cages`, #484) and one bay
  'so/card@1': {bays: {'sub-1': {accepts: ['so/leaf@1']}},
                cages: [{id: 'xg0', accepts: ['generic/sfp-lc@1']},
                        {id: 'xg1', accepts: ['generic/sfp-lc@1']}]},
};
const compByRef = ref => {
  if (!/^[^/]+\/[^@]+@\d+$/.test(ref)) throw new Error('bad ref ' + ref);   // as shell's does
  return COMPS[ref];
};
const bays = [{id: 'slot-1', accepts: ['so/a22@1', 'so/blank@1', 'so/card@1'], default: 'so/blank@1'},
              {id: 'slot-2', accepts: ['so/a22@1', 'so/blank@1'], default: 'so/blank@1'},
              {id: 'slot-3', accepts: ['so/card@1', 'so/blank@1']}];
const cages = [{id: 'port-4', accepts: ['generic/qsfp-lc@1']},
               {id: 'port-9', accepts: []}];
// slot-2 is built holding an A22; slot-1 is built blank
// (undefined = no answer, so a nested bay falls back to its own default)
// slot-3 is built holding the card
const built = id => ({'slot-2': 'so/a22@1', 'slot-3': 'so/card@1'})[id]
  ?? bays.find(b => b.id === id)?.default;
const run = map => acceptSwaps(map, {bays, cages, built, compByRef});

const out = {};
out.device = run({'slot-1': 'so/a22@1', 'port-4': 'generic/qsfp-lc@1', 'port-9': '',
                  'slot-2': null});
out.deviceRefused = run({'slot-1': 'so/ppm-x@1', 'port-4': 'generic/sfp-lc@1',
                         'port-9': 'generic/osfp@1', 'nope': 'so/a22@1'});
// a nested bay under a carrier the SAME map seats
out.nestedUnderSwap = run({'slot-1': 'so/a22@1', 'slot-1/module/ppm-1': 'so/ppm-y@1'});
// a nested bay under the BUILT carrier
out.nestedUnderBuilt = run({'slot-2/module/ppm-2': 'so/ppm-x@1'});
// the carrier holds nothing with that bay (built blank), or it was emptied
out.nestedNoCarrier = run({'slot-1/module/ppm-1': 'so/ppm-x@1'});
out.nestedCarrierEmptied = run({'slot-2': '', 'slot-2/module/ppm-1': 'so/ppm-x@1'});
// the nested bay exists but refuses the ref; and one that names nothing
out.nestedRefused = run({'slot-2/module/ppm-1': 'so/deep@1', 'slot-2/module/bogus': 'so/ppm-x@1'});
// emptying a nested bay that exists is allowed
out.nestedEmptied = run({'slot-2/module/ppm-1': ''});
// the carrier entry refused falls back to the BUILT carrier for its children
out.carrierRefused = run({'slot-2': 'so/ppm-x@1', 'slot-2/module/ppm-1': 'so/ppm-y@1'});
// three levels, the middle one only implied by the built/default occupant chain
out.deep = run({'slot-2/module/ppm-2': 'so/deep@1', 'slot-2/module/ppm-2/module/sub-1': 'so/leaf@1'});
out.deepNoMiddle = run({'slot-2/module/ppm-2/module/sub-1': 'so/leaf@1'});
// a nested default counts as seated; an explicit built-empty (null) does not
out.nestedDefault = acceptSwaps({'slot-2/module/ppm-1/module/x': 'y'}, {bays, cages, built, compByRef});
COMPS['so/ppm-x@1'] = {bays: {'x': {accepts: ['so/leaf@1']}}};
out.viaDefault = run({'slot-2/module/ppm-1/module/x': 'so/leaf@1'});
out.viaBuiltEmpty = acceptSwaps({'slot-2/module/ppm-1/module/x': 'so/leaf@1'},
  {bays, cages, compByRef, built: id => id === 'slot-2/module/ppm-1' ? null : built(id)});
// A CAGE ON A SEATED CARD (#484) exists by virtue of its carrier, exactly as
// a nested bay does, and through the same walk: under the built card, under a
// card the same map seats, and not under a carrier that holds no such card
out.cageUnderBuilt = run({'slot-3/module/xg0': 'generic/sfp-lc@1', 'slot-3/module/xg1': ''});
out.cageUnderSwap = run({'slot-1': 'so/card@1', 'slot-1/module/xg0': 'generic/sfp-lc@1'});
out.cageNoCarrier = run({'slot-1/module/xg0': 'generic/sfp-lc@1'});
out.cageCarrierEmptied = run({'slot-3': '', 'slot-3/module/xg0': 'generic/sfp-lc@1'});
out.cageCarrierReplaced = run({'slot-3': 'so/blank@1', 'slot-3/module/xg0': 'generic/sfp-lc@1'});
out.cageRefused = run({'slot-3/module/xg0': 'generic/qsfp-lc@1', 'slot-3/module/xg9': ''});
// a cage is no carrier: nothing is nested under an optic
out.underACage = run({'slot-3/module/xg0': 'generic/sfp-lc@1',
                      'slot-3/module/xg0/module/sub-1': 'so/leaf@1'});
// the card's bay beside its cages still resolves
out.cardBay = run({'slot-3/module/sub-1': 'so/leaf@1'});
// garbage never throws
out.garbage = [run(null), run({}), run({'slot-1': 'not a ref'}),
               run({'slot-1/module/': 'x'}), run({'/module/ppm-1': 'so/ppm-x@1'})];
console.log(JSON.stringify(out));
