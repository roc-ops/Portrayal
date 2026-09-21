// What `over()` in shell.js counts as lying OVER a part, as the pure predicate
// it now calls. A seated optic is `data-behaviour="occupies"` +
// `data-for="<port>"`, and reading every `[data-behaviour][data-for]` as a
// cover made selecting a port - which swapCage does after every swap - take
// the port's own optic for a lid and pull it.
const {liesOver} = await import('../../../kit/swap.js');
const el = a => ({getAttribute: k => (k in a ? a[k] : null)});

const optic = el({'data-path': 'port-4-occupant', 'data-behaviour': 'occupies', 'data-for': 'port-4'});
const cover = el({'data-path': 'psu-cover', 'data-behaviour': 'mounts', 'data-for': 'psu-1 psu-2 psu-3 psu-4'});
const filler = el({'data-path': 'blank', 'data-behaviour': 'fills', 'data-for': 'slot-3'});
const lamp = el({'data-path': 'led-4', 'data-for': 'port-4'});
const self = el({'data-path': 'port-4', 'data-behaviour': 'mounts', 'data-for': 'port-4'});

console.log(JSON.stringify({
  opticOverItsPort: liesOver(optic, 'port-4'),
  coverOverPsu1: liesOver(cover, 'psu-1'),
  coverOverPsu4: liesOver(cover, 'psu-4'),
  coverOverOther: liesOver(cover, 'psu-5'),
  fillerOverSlot: liesOver(filler, 'slot-3'),
  lampNoBehaviour: liesOver(lamp, 'port-4'),
  notItself: liesOver(self, 'port-4'),
  nullSafe: [liesOver(null, 'x'), liesOver(cover, null)],
}));
