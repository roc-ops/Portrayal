# Pluggables C: slotting in the kit

Status: design agreed with Jason, 2026-09-18. Part of [pluggables-design.md](pluggables-design.md).
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
 "accepts": ["generic/sfp-lc@1", "generic/sfp-lc-simplex@1",
             "cisco/sfp-10g-lr@1", "..."],
 "occupant": null}
```

`accepts` is computed at build time from the components index: every part with
`behaviour: occupies` whose `mates` equals the cage's presented interface, and whose
own rate (its `media` attr, or none for a generic) is at or below the cage's `media`
on the family's ladder, plus the `also-accepts` families. Vendor-blind by
construction. `occupant` is the configured occupant if the manifest seats one, which
after A no shipped device does.

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
- Whether a cage inside a seated module (an SFP on a line card in a bay) is offered.
  It should be - the nested-bay work (#nested-bays) already resolves paths through a
  seated module - but it is the case most likely to have a lift bug and gets its own
  test.
