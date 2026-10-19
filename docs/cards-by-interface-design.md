# Cards by interface: a slot that seats by form, not by list

Status: proposed. The mechanism was decided 2026-10-18 (#120, #43): PCIe, OCP
and EDSFF slots seat cards by `interface:` on the slot and `mates:` on the card,
as an optic seats in a cage (lint L12), and not by `accepts:` lists that name
every card. The choice among #120's options A to D for a card that is also a
product is **not** decided; this note lays them out and proposes one.

This note changes nothing. The build it describes is one-way, and the one-way
items are listed in "What moves when it is built".

## Goal

A riser slot in the library lists the cards it takes. Counted on `main`, 54
component bays in 30 components name a PCIe bracket, a part that composes one,
or a vendor blank. Between them they carry 1,061 `accepts` entries. 49 of those
bays carry a card list of 1,056 entries in all (44 distinct bracket-bearing
parts, two of them Dell fillers); five take a filler alone. Seven devices seat
those risers: `dell/r660`, `dell/r740xd`, `hpe/dl160-gen10` and four Supermicro
`sys-111e-*` / `sys-511e-wr` boxes. No device bay names a card directly.

#120 expected one card. It is now 37 modelled cards (36 NVIDIA ConnectX and
`ufispace/n3100-4c@1`, a module since the commit that retired the device), each
named by hand in every riser that takes it. Riser 1A's slot 1 alone lists 24
refs. The list is the failure #43 named: it asserts something no vendor
published, and a card that is not in it cannot be seated. The DCIM export cuts
the same list at the 200 characters a bay description allows (`fit_items`), so a
person installing a card reads 9 of slot 1's 24 names and 13 of slot 3's 23.

## What is on `main`

- **A device bay may state `interface` instead of, or beside, `accepts`**
  (`device.schema.json`, `anyOf`). **A component bay may not.** The component
  schema's `bays` still requires `at`, `size` and `accepts` and forbids other
  keys, and the riser slots are component bays. Nothing reads a bay's
  `interface` but the schema and the device lock, which hashes it "so the first
  bay to state one is not stated in silence".
- **L12 holds a `mate-to` or an `occupants:` seat to its host's interface**
  (`lint._mate_check`, `manifest.mates_of`). A seat in a bay is not an L12 case
  today: L8 holds a configuration's `bays:` to the bay's `accepts`, and L6 holds a
  `default` to it.
- **L11 requires a `mate` connection point** on any part that states `mates`
  (`lint.lint_component_mating`). A card that fills a bay has no such point: its
  bay places it by `at`.
- **`std/pcie-bracket-fh`, `-lp` and `-fh-2slot`** are in `standards.yaml`, with
  PCI Express CEM 5.0 figures 11-5, 11-9 and 11-13.
- **Two-slot cards** (`docs/pcie-two-slot-bays-design.md`): `slot-width` on a
  card, `span` on a component bay, L185 and L186.
- **The N3100-4C and the ConnectX cards are already modules** (option A of #120,
  carried out 37 times). The N3100-4C composes `std/pcie-bracket-fh@2` behind a
  punched plate, so the composition #119 held back has been built.
- **The build already derives a slot's list from `mates`** for cages
  (`render._slot_dict`: "`accepts` is every candidate whose `mates:` is the
  interface"), and the kit reads only the published lists.

## The interface keys

The three facts #43 separated stay separate: the **mechanical form** is the
registry key, the **mating** is `interface`/`mates`, and the **electrical** detail
(generation, lane width) stays in `attrs`, in the bay's `slot:` block
(`connector`, `lanes`, `height`, `length`, `generation`) and in a card's
`pcie-connector`, `pcie-height` and `pcie-generation`. A gen3 card seats in a
gen4 slot, so a key that carried the generation would refuse hardware that fits.

Every figure below is the one the entry in `standards.yaml` already cites. This
note measures nothing and reads no standard that the registry does not cite.

| Key | Means | Registry entry it points at | Source | Status |
|---|---|---|---|---|
| `pcie-fh` | a slot whose opening takes a full-height add-in card bracket | `pcie-bracket-fh` | PCI Express CEM 5.0, figure 11-5 "Standard Add-in Card I/O Bracket", page 172 | proposed |
| `pcie-lp` | a slot whose opening takes a low-profile bracket | `pcie-bracket-lp` | CEM 5.0, figure 11-9 "Low Profile I/O Bracket", page 177 | proposed |
| (none) | a two-slot card | `pcie-bracket-fh-2slot` | CEM 5.0, figure 11-13, page 181 | not a key: it mates `pcie-fh` and states `slot-width: 2` |
| `ocp3-sff` | OCP NIC 3.0, small form factor | none | none held | question |
| `ocp3-lff` | OCP NIC 3.0, large form factor | none | none held | question |
| `e3s` | EDSFF E3.S, single thickness | `drive-e3s` | SFF-TA-1008 Rev 3.0a, table 5-1: 76 wide, 112.75 long, 7.5 thick | proposed, later slice |
| `e3s-2t`, `e3l`, `e3l-2t` | the other E3 device sizes | none | table 5-1 is cited for E3.S only; the registry text names E3.S 2T at 16.8 thick and holds no entry | question |

Reasons:

- **Two PCIe keys, by bracket height.** The library already models a card's
  full-height and low-profile variants as two parts (`mcx4111a-fh`,
  `mcx4111a-lp`), and the two brackets are two registry entries with different
  outlines, so they are two forms. Length is not keyed: riser 1A's full-length
  slot 1 and half-length slot 3 take lists that differ only by the two-slot
  bracket (24 refs and 23), and `slot.length` already records the difference.
- **Spelled `pcie-fh`, not `pcie-bracket-fh`.** The standards key names the
  bracket, a part. The interface names the slot it plugs into, as `sfp` names a
  cage and not the optic. The registry entry's `standard:` links the two, so a
  lint can check that a card mating `pcie-fh` composes a part that conforms to
  `pcie-bracket-fh`. See open question 2 for the alternative.
- **Registered in `connectors.yaml`**, beside the entries that already point at
  `standards.yaml` by `standard:`, with a `note` that the DCIM export reads. That
  file's header says a part presenting one of its interfaces is a slot, and
  `cover` entries already show it holding a non-connector (#822 is the open
  question of a separate registry). `standards.yaml` keeps the figures and
  gains no key.
- **No dots.** `connectors.yaml` spells `din-1-0-2-3` with hyphens because an
  interface may not contain a dot, so E3.S is `e3s` and M.2 would be `m2`.
- **OCP NIC 3.0.** The library holds no OCP specification. The six Dell cards
  carry `attrs.form-factor: ocp3-sff`, a spelling of the library's own, and their
  bracket (71.8 x 15.1) and board (76 x 115) are measured on a vendor service
  model, which is the vendor's bracket and not the OCP form factor. The R660 has
  one OCP bay. The keys are left as a question until the specification is held.
  Nothing is invented from the vendor datasheets that call a card "TSFF".
- **EDSFF.** `std/drive-e3s@1` conforms to a held entry, so `e3s` has a source.
  The R660's 16 distinct E3.S bay ids (30 bay entries, in its two front views; a 31st, `e3s-filler-14`, takes a
  filler only) accept Dell's carrier, Dell's blank and the bare drive. The
  carrier is a vendor part and the drive is everybody's, so the open relation is
  drive-in-carrier, and the chassis bay stays a vendor list. That is why `e3s`
  waits for a later slice.
- **Not proposed:** M.2, U.2/U.3, mini-PCIe. No held source gives a form-factor
  figure for them (#43 noted the SFF drive standards were not yet in the registry;
  only `drive-e3s` is there now).

## How a card seats

**The card** states `mates: pcie-fh` at the top of its contract. A part that
composes a registered bracket states the same key, and a lint holds the two
together, as L185 holds `slot-width` to the width of what a part composes. A
two-slot card also states `slot-width: 2`.

**The slot** states `interface: pcie-fh` on the bay. The component schema gains
the key and the same `anyOf` the device schema has: `accepts` or `interface`, and
both are allowed.

**One predicate, asked everywhere.** `manifest.py` gains, beside `mates_of`:

```text
takes(bay, ref)  = ref in bay.accepts
                   or (bay.interface in mates_of(contract(ref))
                       and wide-enough(bay, contract(ref)))
offers(bay, lib) = bay.accepts + every library part p with takes(bay, p), sorted
```

`_mate_check` says why: "a second copy would be one bad afternoon away from
disagreeing with the first". The lines in the build tools that read a bay's
`accepts` (counted by a search for `get("accepts")` and `["accepts"]` in
`spec/tools/portrayal`: lint about 14 to 16, `dcim_export` 9, `devicelock` 4,
`render` 3, `components_index` 2, `redirects` 2, and one each in `manifest`,
`devices_index` and `components_catalogue`), and the helper scripts that take
`accepts[0]` or list it (`render_standards.py`, `audit_standards.py`,
`dc_inventory.py`, `benchgt.py`; list order matters to the first), read `offers`
instead, and the build publishes `offers`
as `accepts` in `components.json` and `<device>.configs.json`, beside a new
`interface`. The kit reads only those published lists, as it does for cages, so it
does not change and a saved rack still seats.

**A slot that keeps `accepts` beside its `interface`: the union.** A part is
taken if the list names it or it mates the interface. The list is the vendor's
own statement and each ref in it is a positive claim, which is how a Dell filler
stays in riser 1A (a blank is vendor-specific and does not mate the open form).
An intersection would make `interface` a decoration the list overrides, and
would silence the check, the failure this repository keeps meeting. The device
lock already reads it as a union: "stating one where there was none only admits
more". A new warning reports an `accepts` entry that also mates the interface,
so a migrated bay does not keep the list it came to replace.

**A slot with no `interface`** stays a closed list. Riser 1A's slot 2 has no
connector behind it and takes a filler only; it keeps `accepts` and no
`interface`, which says "blanked" as it does now.

**`default`** must be taken (L6, L8 and the nested-bay check ask `takes`).

**L11** asks a `mate` point of a part that `occupies`, and not of one that
`fills` a bay. The schema's description of `mates` ("Requires a `mate`
connection-point") says the same.

**An x8 card in an x16 slot, and an open-ended slot.** The key carries no lane
count, so an up-plug is admitted with no statement. The opposite, an x16 card in
an x8 connector, is not refused by the key. The facts are data on both sides
(`slot.connector`, `attrs.pcie-connector`), and a warning that reads the two, as
L75 reads `slot` against its prose, is possible without a new key. Open-ended
connectors have no field and no held source. The gap is not new: the two HPE bays
whose `slot.connector` is x8 (slot 2 of the primary and of the FlexibleLOM riser)
each list 17 low-profile cards today, 11 of them x16. This slice says nothing more and the
question stays open (open question 5).

## With `slot-width` and `span`

`slot-width` (the card) and `span` (the bay) are unchanged keys, and L186
(exclusion) is unchanged. The meeting point is the third clause of L185, "a bay
that accepts a part `n` slots wide names at least `n - 1` bays in `span`".

For an explicit `accepts` entry, the clause stands. For an `interface` bay it
cannot become "a bay whose interface a wide part mates spans enough": adding a
two-slot card to the library would then fail the lint of every riser, including
riser 1A's slot 3, which has no bay below it and can never span. A card
author would break a riser file they never touched.

**The proposal: width is part of the seat predicate, as the rate ceiling is for
a cage** (`render._cage_accepts`). A card `slot-width: n` is taken by an
interface bay only if the bay's `span` names at least `n - 1` bays. So
`std/pcie-bracket-fh-2slot@1`, mating `pcie-fh`, is offered in riser 1A's slot 1
(`span: [slot-2]`) and not in slot 3, the same two answers the lists give today.
A configuration that seats it in slot 3 fails L8 on the same predicate, and the
build refuses it as it does now. The covered bay's `accepts` and `interface`
are not consulted, as in R2 of the two-slot note. L185's geometry clauses and its
composer clause are unchanged.

## The product-and-module question (#120's options A to D)

What the options now cost:

| | What it is | What has changed since #120 |
|---|---|---|
| **A** | the card is a component and loses the product fields | **Carried out 37 times.** The N3100-4C and 36 ConnectX cards are modules. The DCIM carries a NIC as a module type in the host's slot, and these export as module types. #1161 (open, draft) lets a component state `part-numbers`, which was the field a ConnectX card needs most: one model, many orderable codes. |
| **B** | a bay accepts a device | unchanged: a device carries `chassis` and six views, and a bay is a hole in another device's face, so two chassis would be compared |
| **C** | a new kind or a flag | unchanged: the largest spec change, and it must say what a seated device's views mean inside the host's |
| **D** | model it twice | unchanged: two files for one object, which drift. The module already composes the bracket, so the duplication is the product record alone |

Device-only keys, from the two schemas on `main`: `adjustments`, `aliases`,
`chassis`, `datasheet`, `gaps`, `interfaces`, `lint`, `manufacturer`, `maturity`,
`model`, `part-numbers`, `portfolio`, `references` and `views`. A component
already carries `groups`, `configurations`, `faces`, `provenance` and `attrs`.
With #1161, `part-numbers` leaves the list. `manufacturer` comes from the
namespace and `model` from `attrs.model`. What a card cannot state is `portfolio`,
`maturity`, `gaps`, `datasheet` and `references`, and `provenance` carries the
sources and the unknowns in prose.

**Recommendation (a proposal, to be accepted or not): A, with #1161.** It is built, it is
what the DCIM models, and it needs only the interface mechanism to stop the
enumeration. B and C answer a question about views inside a host that nothing
asks yet. D duplicates. If a card's catalogue facts (portfolio, maturity) are
wanted later, the repository's own precedent is the listing: a small record that
points at one piece of hardware and carries only what differs
(`docs/listing-a-nos.md`). A listing may name only a device today (L56), so that
would be a new optional use of an existing idea and is additive. Nothing in this
note depends on it.

## What moves when it is built

Counts are from `main` at the time of writing. "Before public" says whether the
change may be made while the package is at 0.x (`docs/format-stability.md`:
current format only, every breaking change announced in `CHANGELOG.md`).

| # | Item | Count | One-way? | Before public |
|---|---|---|---|---|
| 1 | Component bay gains optional `interface`; `accepts` no longer required when it is stated | `component.schema.json`, 1 key | yes: contracts will state it | allowed; an optional key does not raise `format` |
| 2 | Interface spellings `pcie-fh`, `pcie-lp` in `connectors.yaml` | 2 keys | yes: outside contracts will write them, and a rename breaks them | allowed now only |
| 3 | `mates` on a part that fills a bay, with no `mate` point (L11) | 1 rule | yes: the meaning of `mates` widens | allowed |
| 4 | Both `accepts` and `interface`: union | 1 rule | yes: intersection later would drop seatings | allowed |
| 5 | Width is part of the seat predicate; L185 clause 3 narrows to explicit lists | 1 rule | yes | allowed |
| 6 | Published `accepts` in `components.json` and `configs.json` becomes derived, and `interface` is published | same key, new source | yes: a list is no longer authored, and a project library that adds a card changes a public riser's list | allowed; additive, so `contract` does not rise |
| 7 | Cards and brackets gain `mates` | 42 contracts (36 ConnectX, N3100-4C, `common/pcie-card-fh`, `-lp`, three `std/` brackets) | yes, with item 2 | allowed; a minor each |
| 8 | Riser bays state `interface` and drop the card entries | 49 bays in the carriers that list cards; 1,056 entries; the 5 filler-only bays stay | yes: CONTRIBUTING calls "a bay stops accepting a ref" one-way. The authored list shrinks, but what the bay takes does not (`offers` is a superset of the old list), so the note relies on that reading; if the lock reads the authored list and asks a major, the item is one-way on that rule too | allowed; confirm with `devicelock.py` |
| 9 | DCIM bay descriptions | 30 module types in each of NetBox and Nautobot, 60 files | a description of an imported bay template | allowed; bay names and positions do not change, so not marked BREAKING (open question 9) |
| 10 | Lint | one new code, never reused; L11, L6, L8, L89, L123, L33 read through the predicate; a warning for a redundant `accepts` entry; `docs/lint-rules.md` | yes: codes are never renumbered | allowed |
| 11 | Device locks | 7 devices; `devicelock._children` and `_composed` must follow `offers`, or a card edit stops reaching the lock of a device whose configurations draw it | expected to ask nothing for devices; the component versions are about 72 bumps (30 risers and 42 cards, a minor each by the usual rule) | confirm by running `devicelock.py` against `main`'s lock before `--update` |
| 12 | L89 and the catalogue's "seated by" | 42 cards; at most 31 are named by no device or configuration and would read as unplaced | no | allowed |
| 13 | Kit, rack file, saved racks | kit unchanged and no version change; the rack file is unchanged; a swap is a ref and the published list still contains it | no | not checked against saved racks (none are held in the repository, as far as `git` shows) |
| 14 | `docs/format-stability.md`, `CHANGELOG.md` fragment, `docs/lint-rules.md` | 3 files | no | required |

Items 1 to 8 and 10 are the one-way list: nine entries, with items 9 and 11 as
the consequences to watch. The rack kit's `fit` and `acceptSwaps` are item 13:
they decide by `target.accepts` of the published list, which still holds every
card, so they need no change.

The order matters for item 8: a riser may drop its card entries only after every
card it listed carries `mates`. Under the union (item 4) a half-migrated library
seats exactly what it did before.

## The first build slice

- **Files:** `spec/schemas/component.schema.json`, `spec/schemas/connectors.yaml`,
  `manifest.py` (`takes`, `offers`), `lint.py`, `render.py`, `components_index.py`,
  `devices_index.py`, `components_catalogue.py`, `devicelock.py`, `dcim_export.py`
  (`bay_row` takes the interface and its `note`), `redirects.py`, the docs in item
  14.
- **Library:** `mates` on the 42 cards and brackets, then `interface: pcie-fh` or
  `pcie-lp` on the bays of the R740xd's 14G Dell risers, dropping their card
  entries and keeping each filler in `accepts` and as `default`. The other
  carriers (Dell 16G, HPE, Supermicro) follow.
- **First devices and cards:** the R740xd, whose four example configurations
  (`-n3100-4c`, `-connectx`, `-connectx-100g`, `-two-slot`) must keep seating what
  they seat, and `ufispace/n3100-4c@1`. The two-slot bracket must still be offered
  in riser 1A's slot 1 only.
- **Tests:** a card not named in any list is seated in a slot by its `mates`; a
  card of the other height is refused; `default` and `L8` on an interface bay; a
  two-slot card is offered where the `span` is long enough and not elsewhere;
  published lists equal today's for the migrated risers (a snapshot); the module-type
  export of a migrated riser; the lock asks nothing of the seven devices.
- **Stays for later:** the other carriers, OCP and EDSFF keys, M.2 and U.2, the
  x16-in-x8 warning, and the cover-off interior view of #43.

## Open questions

1. **Which of #120's options?** A is proposed. Choosing C instead means the 37
   cards authored as modules are redone, and each module type the DCIM imported is
   replaced.
2. **Spelling and home of the keys.** `pcie-fh` and `pcie-lp` in `connectors.yaml`
   (proposed), or the standards keys `pcie-bracket-fh` and `-lp` verbatim, which
   removes a second spelling and a registry edit but makes `conforms` and `mates`
   read as one relation. The spelling is frozen when the format is public.
3. **Union or intersection** when a bay states both. Union is proposed. It fixes
   what the existing schema's "both together is fine" means.
4. **Fillers.** Kept in `accepts` as vendor parts (proposed), or made to `mate` the
   key. The second offers Dell's filler in an HPE riser.
5. **x16 card in an x8 connector, and open-ended slots.** Left to a later warning
   (proposed). It changes whether the two HPE x8 bays keep offering the 11 x16 cards each lists.
   No source for open-ended connectors is held.
6. **`mates` stated on each composing card** (proposed, 42 edits) or inherited from
   the composed bracket (no edits, but a card's key is then silent).
7. **Derived published lists** (proposed, kit untouched) or a kit that reads
   `interface` itself (kit version, and lists stay short).
8. **OCP and EDSFF.** Wait for a held OCP NIC 3.0 specification, and register `e3s`
   in a later slice from the SFF-TA-1008 entry, or register `e3s` now.
9. **Is a changed DCIM bay description "BREAKING for DCIM data already
   imported"?** Names and positions do not change; the note says no.
10. **L11.** Waive the `mate` point for a part that fills a bay (proposed), or give
    each card a `mate` point it does not use.
11. **Slice size.** All 42 cards and the R740xd risers first (proposed), or every
    carrier at once, which touches 30 riser contracts and 60 export files together.
