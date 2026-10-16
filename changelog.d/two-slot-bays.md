### Added
- **A card two slots wide seats across two bays**, as a dual-slot GPU sits in
  a riser (`docs/pcie-two-slot-bays-design.md`). A component contract may say
  `slot-width: 2`, and a component's bay `span: [<sibling>]`: the bays a card
  wider than one slot covers when it is seated there. The card seats only in
  a bay that spans enough siblings, and only while each of them holds nothing
  once the configuration and the defaults resolve, so a configuration that
  seats one also empties the bay it covers (`riser-1/slot-2: ""`). The card is
  drawn in the box its bays make together, the covered bay's group carries
  `data-covered-by` the card's bay, and the build refuses a card over a full
  bay. Both keys are optional, so `format` stays 1. `components.json` gains
  `slot-width` on a part wider than one slot and `span` on a bay that has one.
- **`std/pcie-bracket-fh-2slot@1`**, the two-slot full-height bracket of PCIe
  CEM 5.0 figure 11-13 (120.07 x 41.91), and a `pcie-bracket-fh-2slot`
  standards entry. It is the default bracket for a two-slot card that has no
  outline of its own.
- **Lint L185 and L186.** L185: a bay's `span` names other bays of the same
  component, the same size and turn, following one another on the card's
  component side; a bay that accepts a two-slot part spans enough bays; a part
  that composes a two-slot part is two slots wide itself. L186: a two-slot
  card and a bay it covers are never both filled, by a configuration or by
  what a carrier ships. Both are errors.
- **`dell/riser-1a-14g@2` 2.2.0**: slot 1 spans slot 2, the opening with no
  connector behind it, and accepts the two-slot bracket. **`dell/r740xd`
  28.0.0** gains the example configuration `sff24-rc4-1a2a3a-two-slot`, the
  bracket seated across riser 1's slots 1 and 2, and a gap saying that Dell's
  GPU support for the chassis was not read.
- **A DCIM module bay that spans says so** in its description, before its
  accept list (`Spans slot-2 for a card 2 slots wide. Accepts: ...`), and a
  module type wider than one slot lists `slot-width` with its other facts.
  Neither DCIM can give one module two bays, so the covered bay stays empty
  there.

### Changed
- **`@portrayal/kit` is 0.50.0.** `swap.js` gains `slotWidth`, `spanCovers`,
  `spanBox`, `withSpan`, `spanWhy`, `coveredBy` and `markSpan`;
  `bayTransform` places a two-slot card by its span box; `acceptSwaps`
  refuses both claims on one pair and returns `why` by key. The rack's `fit`
  says which bay to empty, `slotTree` gives `covers` and `covered-by`, and the
  explorer's inspector disables what a span rules out. A rack file does not
  change.
