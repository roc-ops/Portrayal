# Pluggables C: slotting in the kit

Status: design agreed 2026-09-18. Part of [pluggables-design.md](pluggables-design.md).
Depends on A for parts to offer. Written now so it survives; refined when A lands.

## Goal

In the explorer and the annotate tab - one inspector serves both - a pluggable cage
is swappable the way a bay is: pick from a list, the drawing and the 3D scene update.
The list is not written by anyone. It is everything in the library that mates the
cage's interface and fits the ladder, so a generic and a partner's optic sit in the
same list the moment the partner's part lints. Portrayal ships no populated device;
this is the mechanism a downstream tool uses to populate one.

## What exists and is kept

- `swap.js`: seating an occupant into a BAY, in one place, used identically by the
  live 2D DOM (`shell.js`) and the fetched face text the 3D scene is built from
  (`viewer3d.js`). The two-callers-one-home rule is kept; a second seat path is added
  beside the first, not a second module.
- `<device>.configs.json` `bays[view][]` - `id, at, size, accepts, default, group,
  rel-pos, rotate` - which `shell.js` reads into `state.meta.bays` and offers as a
  select. Cages get the same shape.
- `interface:` on cages, `mates:` on occupants, mate-forwarding through vendor cages,
  and L12. The accept list is DERIVED from these, never declared on a cage.

## The ladder registry

`spec/schemas/pluggables.yaml`:

```yaml
format: 1
families:
  sfp:
    interface: sfp
    rates: [sfp, sfp-plus, sfp28, sfp56]           # ascending; a cage at rate N takes N and below
    source: 'SFF-8432 envelope; one cage interface, rate is electrical'
  qsfp:
    interface: qsfp
    rates: [qsfp, qsfp28, qsfp56, qsfp112]
    source: 'SFF-8661 envelope; SFF-8663 cage governs qsfp28 and qsfp56; QSFP-DD HW 6.3 section 9 - QSFP112 cage is backward compatible to QSFP28/QSFP+'
  qsfp-dd:
    interface: qsfp-dd
    rates: [qsfp-dd, qsfp-dd800]
    also-accepts: [qsfp]                           # every rate of the qsfp family
    source: 'QSFP-DD HW 6.3 section 1 - QSFP-DD/QSFP-DD800 cages are compatible with 4-lane QSFP28/QSFP112'
  osfp: {interface: osfp, rates: [osfp]}
  xfp:  {interface: xfp,  rates: [xfp]}
  cfp:  {interface: cfp,  rates: [cfp]}
  cfp2: {interface: cfp2, rates: [cfp2]}
```

Rate names are the port groups' existing `media` vocabulary (`PLUGGABLE_CAGES` in
lint), so a cage's ceiling is a value every port group already declares. A media
value that names no family, or a family whose `interface` matches no cage in the
library, is a lint error against the registry - the registry can be wrong and must
be caught by the corpus, not trusted.

What the registry does NOT say: whether a host lights a given lane arrangement.
Breakout and lane modes are firmware and vendor-specific, stay `port-modes-<media>`
prose on the device (L40), and are never consulted for slotting. The registry says
what fits and links; a downstream tool that needs to know what a port will do
consults the device.

## Build side

`configs.json` gains `cages[view][]`, one entry per placement whose part presents a
pluggable interface (directly or through a wrapper):

```json
{"id": "port-7", "at": [72.86, 27.77], "interface": "sfp", "media": "sfp28",
 "group": "sfp-plus", "rel-pos": 7, "rotate": null,
 "accepts": ["generic/sfp-lc@1", "generic/sfp-lc-simplex@2",
             "cisco/sfp-10g-lr@1", "..."],
 "occupant": null}
```

`accepts` is computed at build time from the components index: every part with
`behaviour: occupies` whose `mates` equals the cage's presented interface, and whose
own rate (its `rate` attr, or none for a generic; L102 refuses a rung written as `media`) is at or below the cage's `media`
on the family's ladder, plus the `also-accepts` families. Vendor-blind by
construction.

`media` is the port's declared media, read from the placement first and then from
its port group - L18's precedence, and the corpus declares it in both places.

`occupant` is the configured occupant if the manifest seats one, which after A no
shipped device does - and it is **the default configuration's** occupant, because a
`cages[]` entry is a view-static fact while `occupants:` is declared per
configuration. Each configuration's own map is published beside its `bays`, as
`configs[].occupants`, and a consumer holding a particular configuration reads that
rather than `cages[].occupant`, exactly as it already reads `configs[].bays` rather
than a bay's view-level `default`.

Sorted generics first, then vendors alphabetically, so the list reads the same on
every device.

## Kit side

- `swap.js` gains `seatOccupant(svg, cageId, ref)`: fetch the part's compiled face,
  rename its ids into the cage's namespace (the existing `rename`), and position it
  by MATE POINTS - the occupant's `mate` marker (from B's render change 2) landing on
  the cage's - not by a bay box. The bay transform is the wrong tool for a part that
  is larger than its opening on purpose.
- `shell.js` offers the select on a cage row exactly as on a bay row, reading
  `state.meta.cages`; the choice is written into the share URL and the pushed states
  the way bay swaps are, so a populated view survives a reload and reaches 3D.
- The annotate tab needs nothing of its own: it shares the inspector.
- `swap-url-refs`, `nested-bays` and the relief-scope tests gain a cage case each.

## What a populated drawing means

A swap in the kit is a per-viewer opinion, exactly as a bay swap is: it changes no
file, it is scoped to the viewer that made it, and two viewers on one page do not
share it (`relief.js` scope, #302's lesson). Exporting a populated device is a
downstream concern - the mechanism a downstream tool would use is `occupants:` in a
configuration of its own manifest, which already exists.

## Order of work

1. `pluggables.yaml` and its lint (registry agrees with the corpus).
2. Build side: `cages[]` in `configs.json`, with a test that a known SFP28 cage
   accepts the SFP generics and a known QSFP-DD cage accepts the QSFP generics, and
   that an OSFP cage accepts only OSFP.
3. `seatOccupant` in `swap.js`, with the JS test.
4. The inspector select; share-URL and state plumbing.
5. Gate 5 for a UI: a screenshot of one SFP28 port populated with `generic/sfp-lc`
   in 2D and 3D, beside the same port bare.

## Open questions

- Whether the accept list should also carry the `optics-<media>` prose the device
  holds, as a hint rather than a filter. Probably yes, as a tooltip, since it is the
  one thing the device knows that the registry does not.
- ~~Whether a cage inside a seated module (an SFP on a line card in a bay) is
  offered.~~ Answered 2026-09-22 (#484): yes. See "A cage on a seated card" below.

## A cage on a seated card (#484, decided 2026-09-22)

The 22 modular chassis have no device-level cage - every port is on a card in a
bay - so until this they could not be offered an optic at all. Five rulings:

- **R1 - cages ride on the component.** `components.json` gives each component
  its own `cages: [{id, at, mate, lift, rotate, interface, media, accepts,
  occupant-attrs, mirror, group-states}]` in the component's frame, computed by
  the same core as a device view's `cages[view][]` (`cage_entry`, called by
  `cage_entries` and `component_cages`). A module swapped in at runtime brings
  its cages with it; no per-configuration nested `cages[]` exists.
- **R2 - the build seats nested occupants.** A configuration's `occupants:` may
  key a cage on a seated module by the module-less path, the convention nested
  `bays:` keys already use: `front-6/xg0`. The build draws the optic INSIDE the
  module's instance group, at `front-6/module/xg0-occupant` (id
  `front-6--module--xg0-occupant`, `data-for="front-6/module/xg0"`), so it
  inherits the bay transform instead of solving it again. Its position, turn,
  refusals and lift come from `solve_seat`, the one seating rule the
  device-level `mate-to` resolution also calls, and chained keys
  (`front-6/xg0-occupant` for a plug, `front-6/xg0-occupant-occupant` for its
  boot) resolve to a fixed point within the card. A key that seats nothing is an
  error: a cage the module does not carry, an empty bay, a bay on no face this
  configuration draws (an unbound variant face included). Lint L12 walks the
  same key down the configuration's bays (`manifest.nested_key_host`) and holds
  the optic to the cage's interface. This is the parity reference the kit's
  seating is held to, and it lets a downstream manifest ship a populated card.
- **R3 - media on a card cage** is the part's own `attrs.media`: a component
  declares no port groups, so a card cage's `occupant-attrs` is what
  `group_side_attrs` yields for no group - empty.
- **R4 - depth.** A nested cage's effective lift is the module's own seat depth
  plus the cage's presented lift. Census of the library: 7 card cages carry a
  non-zero `lift`, all on smartoptics DCP cards (the four client cages and the
  line cage of `dcp-404`, the two SFP cages of `dcp-f-a22`), each at 44.0 - the
  raised shelf. The kit refuses them with its reason, exactly as it refuses a
  lifted device cage (no half-lift); the build seats them, lifted.
- **R5 - pruning.** Replacing or emptying a carrier drops every swap keyed under
  its path (`front-6/module/...`) from state, `swap=` and the 3D override map: an
  optic cannot outlive the card it sat in.
