# Two-slot cards: a bay that a card can span

Status: decided 2026-10-14, built with this note. The decision is option A,
in the maintainer's words: "for the two slot bay I think we want to go with
option A", "because I think that's how it works in the real world".

Option A: a bay can be spanned. A card seated in it covers the next bay too, the
way a dual-slot GPU sits in a riser: it plugs into its own slot and its cooler
covers the opening beside it. Option B was a separate dual-slot bay drawn over
each pair on a GPU riser. It was not chosen.

## Goal

Every riser bay in the library is one slot: 120.02 x 21.59 on the 20.32 pitch.
A card two slots wide (PCIe CEM 5.0 figure 11-11) fits no bay, so every
dual-slot card is `unplaced`. A GPU batch is about 25 two-slot cards out of 30.
This note says how a two-slot card seats, and what each consumer shows.

## The rulings

### R1. Both sides declare: the card says how wide it is, the bay says what it can join

- **The card** carries `slot-width: 2` at the top of its contract. The key is
  optional, and a part that does not carry it is one slot wide. Its width is a
  fact about the hardware, the same in every chassis, so it belongs on the card.
  `std/pcie-bracket-fh-2slot@1` carries it. So does a card that composes that
  bracket, and lint holds the two together (R6).
- **The bay** carries `span: [slot-2]`: the sibling bays, in order, that a card
  wider than one slot covers when it is seated here. Which neighbour that is
  depends on the riser's geometry: which way the card's component side faces,
  and whether the opening beside it is free metal. The riser knows that and
  the card does not.

Neither side alone is enough. A width on the card alone does not say which
neighbour. A wider bay alone (option B) is a second opening for the same metal.
A bay may list more than one id, which leaves room for a three-slot card
(figure 11-12). A card `n` slots wide covers the first `n - 1` ids.

`span` is on a component's bays only: a riser's, or a carrier's. No device in
the library draws a PCIe slot on its own face, so a device bay does not take
`span` until one does.

### R2. Which way it spans, and what blocks it

**The span runs toward the card's component side.** That is the bay's own `+y`,
turned by the bay's `rotate`. Every full-height bracket in the library is drawn
with its keyed flange, the PCB side, at the top of its box
(`std/pcie-bracket-fh@2`, "handedness"). Figure 11-11 puts the 34.80 component
height on the other side, so a two-slot card's cooler hangs below its own slot
in the bracket's frame. A riser bay at `rotate: 180`, like riser 3 on the Dell
14G, spans upward on the face.

Three things block a span:

| | when it is caught | what says so |
|---|---|---|
| **No neighbour.** The bay names fewer than `n - 1` ids in `span`, or it has no `span`. | statically | Lint L185: a bay that accepts a part `n` slots wide names at least `n - 1` bays in `span`. The kit never offers the card there, because it is not in the bay's `accepts`. The build refuses it too. |
| **The neighbour is in another riser.** | never possible | `span` names ids in the same `bays:` map. A bay in another riser is not a sibling, so lint refuses the id as unknown. Two risers are two modules and can be swapped independently, so a card across them would describe hardware that comes apart. |
| **The neighbour holds something.** | per configuration, and per swap in the kit | The build raises an error. Lint L186 reports it for a configuration and for what the parts ship. The kit refuses the seat and says which bay to empty. |

**"Holds something" is read after defaults resolve,** as the duplex bores are
(`docs/pluggables-caps-design.md`, "The duplex host"). A riser bay usually
ships a filler, and a real filler bracket has to come out before a two-slot
card goes in. So a configuration that seats a two-slot card also empties the
bay it covers:

```yaml
bays:
  riser-1: dell/riser-1a-14g@2
  riser-1/slot-1: std/pcie-bracket-fh-2slot@1
  riser-1/slot-2: ""
```

The exclusion runs both ways. While `slot-1` holds a two-slot card, nothing can
be seated in `slot-2`. While `slot-2` holds something, a two-slot card cannot
seat in `slot-1`. The covered bay's `accepts` are not consulted, because a
covered bay holds nothing. Riser 1A's `slot-2` takes only a filler, and it can
still be covered.

Lint L185 also holds the geometry of a span. Each id names a different bay of
the same size, `rotate` and `mirror`. The bays follow one another along the
component side, each starting where the last one's slot pitch puts it, with no
gap wider than a bay and no step sideways. `rotate: 90` and `270` are refused
for now, because no riser in the library turns its slots a quarter.

### R3. Where the card is drawn: in the box its bays make together

A one-slot occupant hangs on its bay: the build puts its top-left on the bay's
`at`, and the kit puts its centre on the bay's centre. The two agree when the
occupant is the bay's size. A two-slot card in one bay's box would hang half
outside on the wrong side. So a spanning card is seated in the **span box**:
the bounding box of the bay and the bays it covers. Its size is
`w x (h + pitch)`, 120.02 x 41.91 on a CEM riser, which is the figure 11-13
bracket's 41.91. The build and the kit both use that box and nothing else.
`manifest.span_box` (which the build and lint import) and `swap.js` `spanBox`
compute it, and `spec/tests/test_two_slot_bays.py` holds the two to the same
numbers on riser 1A.

The bay's `rotate` turns the card inside that box. So a riser bay at 180 puts
the keyed flange at the bottom of the pair, which is the bottom of the bay it
plugs into.

### R4. What the slot tree, `fit` and the faces show

- **The faces.** The card's group is in the bay it plugs into
  (`riser-1/module/slot-1/module`), and only there. The covered bay's group
  stays, empty, and carries `data-covered-by="riser-1/module/slot-1"`.
  The covered bay keeps its opening rect, but the spanning bay's group is
  moved after the covered ones, so the card paints over that opening. The 3D
  scene is built from the same face text (`viewer3d.js` through `swap.js`).
  The card's body boxes stand where its face does, so they cover both
  openings without anything of their own.
- **The slot tree** (`kit/rack/slots.js` `slotTree`). The covered bay is
  listed with `holds: null` and `covered-by: <path>`, and the spanning bay
  with `covers: [<path>, ...]`. A reader that does not know the keys sees one
  occupied bay and one empty one, which is still true.
- **`fit`** (the rack command) refuses a two-slot card while the bay it would
  cover holds something: "riser-1/module/slot-1 cannot take X: it covers
  riser-1/module/slot-2, which holds Y. Empty slot-2 first." It also refuses
  to fill a bay that a seated card covers, a default put back included, and
  names the card. `acceptSwaps` makes the same decision for a reload and a
  patch, refuses both claims on one pair, and says why by key (`why`), so a
  shared link cannot seat both. `swap.js` `spanWhy` is the one sentence all
  of them give.
- **The explorer's inspector.** A covered bay says what covers it, and its
  select is disabled. A two-slot option in a bay whose neighbour is full is
  listed, but disabled, with the bay to empty.

### R5. The exports: one module in one bay, and the covered bay stays empty

Neither NetBox nor Nautobot can show a module that takes two bays. A module
has one `module_bay`, and nothing reserves a second. So:

- **The device and module types are unchanged in shape.** Both bays are still
  `module-bays` rows. A bay with a `span` says so in its description before
  the accept list: `Spans slot-2 for a card 2 slots wide. Accepts: ...`.
  That is the place a person installing a card will read.
- **A two-slot part's module type** says it in `comments`, beside the other
  facts the schema has no field for: `slot-width: 2 (seated, it also covers
  the bay beside its own, which stays empty)`. A `std/` bracket has no
  manufacturer and is not exported as a module type; a vendor's card is.
- **An installed card**, from a rack's export, is one row in the bay it plugs
  into. The covered bay gets no row. Today a riser's cards are nested modules,
  and the rack export already skips them with a note
  (`kit/rack/dcim-rules.js`), so nothing changes there yet. When nested
  modules are exported, the covered bay stays empty, and that is what a DCIM
  should record.

### R6. Lint

- **L185** (component): a bay's `span` names other bays of the same component,
  each the same size, `rotate` and `mirror`, in order along the component
  side. A bay that accepts a part `n` slots wide names at least `n - 1` of
  them. A part that composes a part wider than one slot declares at least
  that width itself.
- **L186** (component, device): a two-slot card and a bay it covers are never
  both filled. That holds for what a configuration seats and for the defaults
  a component ships.
- **L33 and L123 are unchanged.** L33 compares a device bay with what it
  accepts, and no device bay spans (R1). L123 holds one module to one bay
  size across the library, and a two-slot card's bay is a one-slot bay
  everywhere it is accepted, so the rule sees one size. Neither compares a
  card with its span box. A two-slot card is the size of the bays it takes,
  not of the one it plugs into, and R3's box is where that is applied.

### R7. A saved rack in an older kit

The rack file does not change: no new key, no new version. A two-slot card in
a rack is `swaps: {"riser-1/module/slot-1": <card>, "riser-1/module/slot-2": ""}`.
Every key in that map is one an older kit already reads.

- **An older kit with a library that has the card:** the swap is accepted,
  because the card is in the bay's `accepts`. The older kit does not know
  `slot-width`, so it centres the card on `slot-1` as a one-slot card. The
  card overhangs its bay by half a slot on each side, and it does not refuse a
  later fill of `slot-2`. Nothing is lost: saved again, the file is the same
  map. A newer kit reads it as it was meant.
- **An older kit with an older library:** the card is not in `accepts`, so the
  swap is ignored and named, as any unknown part is (`acceptSwaps`), and the
  bay shows its default.

That is why `slot-width` and `span` are optional keys, and why the component
contract's `format` stays 1 (`docs/format-stability.md`: "an optional key is
not a breaking change").

## The default two-slot bracket

`std/pcie-bracket-fh-2slot@1` is PCIe CEM 5.0 figure 11-13, "Detailed Two-Slot
I/O Bracket Design". It is the bracket a two-slot card is drawn with when it
has no outline of its own. A real card's bracket need not be this one: the
first photographed GPU bracket was about 36 across, against figure 11-13's
38.74 body, with 9.8 tabs against 10.20. So a card that has been
photographed draws its own outline and still declares `slot-width: 2`. A card
that has not been photographed composes this part, as a one-slot card composes
`std/pcie-bracket-fh@2`.

## Proof

- `riser-1a-14g` `slot-1` takes `span: [slot-2]`. Its `slot-2` is the opening
  with no connector behind it, so a card in `slot-1` that covers it needs
  nothing from it. `slot-3` has no bay on its component side and takes no span.
- The R740xd gains an example configuration with the figure 11-13 bracket
  seated across `slot-1` and `slot-2` on riser 1. It renders on the rear face,
  in 2D and 3D.
- The A100 (`nvidia/a100-pcie-80gb`) moves onto this after both changes have
  merged: `slot-width: 2`, and a riser bay with a `span` that accepts it. It has:
  riser 1A's `slot-1` accepts it, and the R740xd's example configuration
  `sff24-rc4-1a2a3a-a100` seats it across slots 1 and 2. Its own plate is 36
  across, which the note on the default bracket expected, so it draws its own
  outline.

## Not in this change

- `span` on a device bay (R1).
- A `common/pcie-card-plan-2slot` top view of a two-slot card.
- Power connectors and NVLink bridges. A bridge spans two CARDS, not two bays,
  and is another design.
