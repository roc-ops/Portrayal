# Optic types: where a vendor-neutral optic type lives

Status: **proposed, 2026-10-28. A decision is needed before the first optic
wrapper. Nothing here is built.** This is a design note only. It makes no
schema, lint, component or export change. Writing the note first was decided
2026-10-28, and the owner makes the choice when this note is merged. Every
choice that would be one-way once built says so.

This is the optic half of #897 (named cable and optic types). The cable half
began as #919, and `spec/schemas/cable-types.yaml` is on `main`. Facts about
the library and the kit are read from `main` at a1982880c.

## 1. The question

A type such as "SFP+ 10GBASE-LR" carries the physical and optical facts that
every maker's part of that type shares: the form factor, the connector, the
PMD and what the PMD implies. Where in the library does that type live?

| home | what it is |
|---|---|
| **(a)** | a vendor-neutral wrapper namespace: one contract per type, wrapping a `generic/` transceiver |
| **(b)** | a new contract kind: one file per type, a fourth `kind` beside `component`, `module` and `kit` |
| **(c)** | listings for parts, the way `spec/schemas/listing.schema.json` lists devices today |
| **(d)** | an `optic-types` table beside `spec/schemas/cable-types.yaml`, compiled into `library/dist/optic-types.json` |

For each home, section 4 answers the same six questions:

1. what it costs to lint and lock, and how that cost scales;
2. how L99 changes;
3. how a rack file names the type;
4. what the bill-of-materials export reads;
5. how one maker's part number relates to the type;
6. what the DCIM exports emit.

**The scale.** A reseller's or a maker's compatibility list holds a few hundred
neutral types against thousands of maker-coded part numbers. Each cost below is
counted against those two numbers: about 10² types and about 10³ to 10⁴ codes.
These are orders of magnitude to compare the homes by, not a count of any
list; none is held.

## 2. What holds today

- **A generic carries no rate.** `docs/pluggables-design.md`, decisions 1 and
  5, say so: `generic/sfp-lc` is "SFP, SFP+ and SFP28 alike". A vendor's
  `kind: module` wraps it through `parts:` and carries `model`, the rate,
  `speed`, `reach`, `wavelength` and `power-draw-max-w` in its own `attrs`
  ("The vendor wrapper, once").
- **L99 holds the line by namespace.** `GENERIC_FORBIDDEN_ATTRS`
  (`spec/tools/portrayal/lint.py:2211`) is `speed`, `reach`, `wavelength`,
  `mode`, both power draws and `cable-kind`. `GENERIC_RATE_TOKENS` refuses a
  generic whose name carries a rate (`sfp28`, `10g`, `10gbase-…`, `10km`).
  `lint_component_generic` (`lint.py:2220`) applies both rules only to a
  transceiver whose namespace is exactly `generic`, because "a vendor optic is
  SUPPOSED to carry these attrs".
- **No vendor optical transceiver exists yet.** DAC and AOC ends have wrappers.
  `molex/sfp-plus-passive-dac@1` is a `kind: module` wrapping
  `generic/sfp-cable@1`. It sets `attrs.model: '74752'` and passes
  `latch-color` to the part. Its skin is an empty SVG, because "`skins`
  defaults to ["default"] and the renderer expects one". A wrapper is
  therefore two files: a contract and an empty skin.
- **A reserved namespace has no manufacturer.** `spec/schemas/vendors.yaml`
  lists `common`, `std` and `generic` under `namespaces:`: "A part in either has
  no manufacturer and a DCIM cannot order it." `module_keys`
  (`spec/tools/portrayal/dcim_export.py:3419`) answers `("", "<ns>/<name>")`
  for such a contract. `module_key` says that contract "is written nowhere".
- **A module type is emitted only for `kind: module`** (`pluggables-design.md`,
  "The vendor wrapper, once"; the `kind == "module"` tests in
  `dcim_export.py`, from `_chassis_seated` at 3430 on). It is named by its
  `part-numbers` keys, else by `attrs.model`.
- **The bill of materials reads one code.** `partNumbers`
  (`kit/rack/export-data.js:822`) takes the keys of `part-numbers`, else
  `attrs.model`, `part`, `part-number` or `vendor-sku`. `bomRows`
  (`export-data.js:1151`) writes `model: p.model || p.ref`. A seated part with
  no code is therefore listed by its ref.
- **A rack file seats a part by ref.** An item's `swaps` is "slot path to part
  ref" (`spec/schemas/rack.schema.json`). A cable's optional `type` names a
  row of `cable-types.json`. `cableTypeOf` (`kit/rack/cable-types.js:44`)
  falls back to the cable's `media` when a type id is not in the table, so a
  file naming a newer type still opens. `rack.schema.json` does not yet
  declare a cable `type`; the optic key, once named, should be declared there
  as well.
- **A vocabulary table has one build step.** `cable_types_index.py` checks
  `cable-types.yaml` and refuses a row with an unknown key or an unsourced
  figure. It writes `library/dist/cable-types.json`. The table carries its own
  `version`: a new type or a corrected value is a minor change, and a removed
  type or a changed id is a major one. `format` changes only when a key is
  removed or renamed.
- **A listing is for a device.** A listing "points at ONE hardware device and
  draws nothing of its own". It lives at `devices/<vendor>/<id>/listing.yaml`
  with its own `listing.lock.json`, and L56 (`lint.py:8000`) refuses a
  `hardware` that is not a `kind: device`. A reseller listing may carry only
  `model`, `aliases`, `portfolio` and `source`.

## 3. The worked example

Juniper's *MX104 Universal Routing Platform Hardware Guide* (2022), section
"Built-in 10-Gigabit Ethernet MIC", under "Cables and connectors":

> Fiber-optic 10-gigabit small form-factor pluggable (SFP+) transceivers:
> Connector: Duplex LC/PC (Rx and Tx)
> …
> 10GBASE-LR (model numbers EX-SFP-10GE-LR and SFPP-10GE-LR)

The guide's converted text is held locally and is not in this repository.
Here is what that sentence supports, and nothing more:

| fact | value | from |
|---|---|---|
| form factor | SFP+ | "small form-factor pluggable (SFP+)" |
| connector | duplex LC, PC polish | "Duplex LC/PC (Rx and Tx)" |
| PMD | 10GBASE-LR | the list entry |
| speed | 10 Gb/s | "10-gigabit" |
| maker codes for that PMD | EX-SFP-10GE-LR, SFPP-10GE-LR | the list entry |
| reach, wavelength, fibre mode | **not stated** | the guide sends optical figures to Juniper's compatibility tool; the IEEE 802.3 clause is not held |
| latch colour | **not stated** | SFF-8432's colour code (cited in `generic/sfp-lc@1`'s `bail-colour` provenance) needs the fibre mode, which the guide does not state |
| power | **not stated** | |

The guide does not say whether the two codes are one product. So the first
wrapper is **`juniper/ex-sfp-10ge-lr`** alone, a `kind: module` wrapping
`generic/sfp-lc@1`. The 10 km and 1310 nm commonly quoted for 10GBASE-LR are
left out until a held document states them, as #897 asks.

Under every home, the wrapper itself is the same:

```yaml
# library/components/juniper/ex-sfp-10ge-lr/v1/contract.yaml (after the decision)
format: 1
kind: module
name: ex-sfp-10ge-lr
class: transceiver
behaviour: occupies
mates: sfp
size: {w: 13.55, h: 8.55, d: 47.50}
size-confidence: {w: borrowed, h: borrowed, d: borrowed}
attrs: {model: EX-SFP-10GE-LR, rate: sfp-plus, speed: 10g, power-absent: not-published}
parts:
  - {ref: generic/sfp-lc@1, id: body, at: [0, 0], attrs: {label: EX-SFP-10GE-LR}}
connection-points:
  mate: {at: [6.775, 4.275], direction: front}
```

The homes differ in where "SFP+ 10GBASE-LR" lives, and in how this contract
points at it.

## 4. The four homes

### (a) A vendor-neutral wrapper namespace

A new reserved namespace, `optic/` for example, holds one wrapper per type:
`optic/sfp-plus-10gbase-lr@1`, wrapping `generic/sfp-lc@1` and carrying
`rate`, `speed` and the PMD's optical facts. A maker's part either wraps that
wrapper or wraps the generic directly.

| question | answer |
|---|---|
| cost to lint and lock | One contract and one empty skin per type: about 10² contracts, each run through every component rule and versioned on its own. A maker's code is a further contract and skin, so a full compatibility list would be 10³ to 10⁴ more. |
| L99 | Changes. The new namespace is reserved like `generic/`, so L99 must say what it may carry: the PMD's facts yes, `model` and the power draws no, and a rate in the name *required* rather than refused. That is a second rule set beside the generic one, keyed on another namespace. |
| rack file | `swaps: {"<cage>": "optic/sfp-plus-10gbase-lr@1"}`. It opens in any library that ships the namespace, as `generic/` ships today. A library older than the type cannot resolve the ref, and nothing today falls back to the generic. |
| bill of materials | The neutral wrapper has no code. `partNumbers` finds none, so the line is the ref. Putting the type's label in `attrs.model` would print a part number nobody sells. |
| a maker's part number | Its own wrapper, `juniper/ex-sfp-10ge-lr`, whose `parts:` names `optic/sfp-plus-10gbase-lr@1`. That is a module wrapping a module wrapping a generic: one more level than any optic has today. Codes the library does not model have no home. |
| DCIM | A reserved namespace has no manufacturer, so a `kind: module` there is written nowhere (`module_keys`). The maker's wrapper is the module type, as today. A neutral module type would need a made-up manufacturer, which is a DCIM entry nobody can order. |

**Worked example.** `optic/sfp-plus-10gbase-lr@1` carries `rate: sfp-plus`,
`speed: 10g` and the connector from the guide. It omits reach and wavelength
because no held source states them. `juniper/ex-sfp-10ge-lr@1` then wraps it
and adds `model: EX-SFP-10GE-LR`.

### (b) A new contract kind

The pattern is `kind: kit` (#905), "the third kind", which has no `class` and no
`size` and is never placed. A `kind: optic-type` file names its generic and
states its facts. A maker's `kind: module` gains a key that names the type.

| question | answer |
|---|---|
| cost to lint and lock | One contract per type, about 10², with no skin because nothing is drawn. Each is versioned on its own. Every walker that switches on `kind` has to learn a fourth value: the schema's `if` blocks, lint's dispatch, the component index, `artifacts.py` and the DCIM export. Maker codes cost what they cost under (a). |
| L99 | Unchanged for `generic/`. The new kind gets its own rule: the PMD's facts are allowed, `model` and power are refused, and the named generic must be a `generic/` transceiver. |
| rack file | A type is not seatable, as a kit is not, so `swaps` still names a part. Naming a neutral type needs a new rack key, such as the generic in `swaps` and the type's ref beside it. It opens wherever the type's file ships. A missing type can fall back to the generic only if the kit is written to do so. |
| bill of materials | Reads the seated part, as today. A type's label appears only if the export learns the new kind. |
| a maker's part number | Its own `kind: module`, wrapping the generic and naming `type: <ns>/sfp-plus-10gbase-lr@1`. Unmodelled codes have no home. |
| DCIM | No module type for the type, because it is not `kind: module`. The maker's wrapper is the module type, as today. |

**Worked example.** `<ns>/sfp-plus-10gbase-lr/v1/contract.yaml` holds
`kind: optic-type`, `generic: generic/sfp-lc@1`, `rate: sfp-plus` and
`speed: 10g`. `juniper/ex-sfp-10ge-lr@1` adds `type:` pointing at it.

This is (d) with every row as its own file, plus a schema kind that every
reader of the library must learn. Per-file versions buy nothing here, because a
type has no geometry to version.

### (c) Listings for parts

Extend `listing.schema.json` so that a listing's `hardware` may be a component.
A Juniper listing of `generic/sfp-lc@1` would say "Juniper sells this shape as
EX-SFP-10GE-LR".

| question | answer |
|---|---|
| cost to lint and lock | One listing and one `listing.lock.json` per maker code: 10³ to 10⁴ pairs of files for a full compatibility list. This is the home that scales with codes, not with types. |
| L99 | Unchanged. L56 changes: `hardware` may name a component, and a component has none of the configurations, ports or entity map that L56 checks today. |
| rack file | `swaps` would have to name a listing, and listings are not parts today. A file naming a listing opens only where that listing is held. |
| bill of materials | A listing is not a component, so `partNumbers` needs a second lookup from a seated part to the listing that names it. |
| a maker's part number | The listing *is* the part number. That is what (c) does well. |
| DCIM | A part listing would need a new export path: a module type under the listing's vendor, with the generic's ports. Listings export device types today. |
| **the neutral type** | **Has no home.** A listing "draws nothing of its own" and carries only names and codes. It does not carry the PMD's facts. "SFP+ 10GBASE-LR" would still need (a), (b) or (d). |

**Worked example.** `devices/juniper/ex-sfp-10ge-lr/listing.yaml` with
`hardware: generic/sfp-lc` and `model: EX-SFP-10GE-LR`. 10GBASE-LR appears
nowhere in it, unless the listing gains fact keys and stops being a listing.

(c) answers question 5 and not the question this note asks, so it is not a
candidate on its own.

### (d) An `optic-types` table beside `cable-types.yaml`

`spec/schemas/optic-types.yaml` follows `cable-types.yaml`. It has a `sources`
table, a `types` map and its own `version`. A new `optic_types_index.py`, the
counterpart of `cable_types_index.py`, checks it and writes
`library/dist/optic-types.json`. Each row names the generic it is drawn as.

| question | answer |
|---|---|
| cost to lint and lock | One file. About 10² rows, checked by one build step, under one table `version`. An added row is a minor change, and a removed row or a changed id is a major one, as for cable types. No contract, skin or lock per type. Maker codes are not rows. |
| L99 | **Unchanged.** The table is not a contract, so no generic gains a rate. A new check (not L99) holds that a wrapper's type id resolves, that the row's `generic` is the part the wrapper wraps, and that any fact both state agrees. |
| rack file | `swaps: {"<cage>": "generic/sfp-lc@1"}` plus the type id beside it, under a key the Explorer type-picker change names (for example `optics: {"<cage>": "sfp-plus-10gbase-lr"}`). `generic/` ships in every library. An id the table does not know falls back to the generic shape, as `cableTypeOf` does for a cable's `type`. **This is the only home where a file naming a neutral type opens in any library.** |
| bill of materials | A seated maker wrapper reads `attrs.model`, as today. A seated generic with a type prints the type's `label` ("SFP+ 10GBASE-LR") as its description, with no part number invented. Neither line changes `partNumbers`. |
| a maker's part number | Its own wrapper, where a cited document models it: `juniper/ex-sfp-10ge-lr`, with `attrs.optic-type: sfp-plus-10gbase-lr`. Every other code on a compatibility list is a lookup kept outside the library. A downstream tool maps code to type id. That fits decision 2: Portrayal ships bare, and a list's code is not a sourced drawing. |
| DCIM | Nothing new. The maker's `kind: module` is the module type, as today. A generic with a type seated in a rack exports no module type, as a seated generic does today. The type's label can reach the module's description. |

**Worked example.**

```yaml
# spec/schemas/optic-types.yaml (after the decision)
format: 1
version: 1.0.0
sources:
  juniper-mx104-hw:
    title: Juniper MX104 Universal Routing Platform Hardware Guide (2022), Built-in 10-Gigabit Ethernet MIC, Cables and connectors
    url: <the guide's address, cited by the change that adds the first wrapper>
types:
  sfp-plus-10gbase-lr:
    label: SFP+ 10GBASE-LR
    generic: generic/sfp-lc@1
    rate: sfp-plus
    pmd: 10GBASE-LR
    speed: 10g
    connector: {face: lc-duplex, polish: pc}
    sources: [juniper-mx104-hw]
    # reach, wavelength, fibre mode, latch: not stated in a held source
```

`juniper/ex-sfp-10ge-lr@1` is the wrapper in section 3 with one more attr,
`optic-type: sfp-plus-10gbase-lr`. The source's url is left open here.
`cable_types_index.py` requires an https url, and the change that adds the first wrapper
cites the guide's real address.

## 5. Side by side

| | (a) namespace | (b) new kind | (c) listings | (d) table |
|---|---|---|---|---|
| files per neutral type | 2 | 1 | none (no home) | 0 (a row) |
| files per maker code modelled | 2 | 2 | 2 | 2 (its wrapper) |
| files per maker code *not* modelled | 2, or none | 2, or none | 2 | 0 (outside the library) |
| L99 | new rule set | new rule for the kind | unchanged; L56 widened | unchanged |
| opens in any library | only if the namespace ships, with no fallback | only if the kit falls back | no | yes, with fallback |
| new rack key | no | yes | yes (a listing in `swaps`) | yes |
| BOM | ref, or a false code | as today | a second lookup | as today, plus the type label |
| DCIM | unchanged, or a fake manufacturer | unchanged | a new export path | unchanged |
| precedent | `generic/` | `kind: kit` | device listings | `cable-types.yaml` |

## 6. Recommendation

**(d), the `optic-types` table.**

- **A type is vocabulary, not a part.** It has no geometry and no maker, and the
  library's own rule, in `cable-types.yaml`, is that "a cable type is
  vocabulary … not a part with geometry of its own". An optic type is the
  same kind of thing. The shape is `generic/sfp-lc@1`, and that does not
  change.
- **It costs one file for a few hundred types**, under one version, and nothing
  for the thousands of codes the library does not model.
- **Decision 5 and L99 stay as they are.** No generic learns a rate, and no
  second reserved namespace needs its own rules.
- **A rack file stays portable.** The file seats `generic/`, which every
  library holds, and the type id rides beside it with the same fallback
  `cableTypeOf` already uses.
- **Nothing in the DCIM exports moves.** The maker's wrapper stays the one
  orderable module type, which is what "The vendor wrapper, once" decided.
- **#897 asked for this.** Its proposal is "`optic-types.json` for transceiver
  types" beside `cable-types.json`, storing "the type name plus overrides".

What (d) does not do: give a maker's code a place in the library without a
wrapper. That is deliberate. A code the library models gets a wrapper from a
cited document. Any other code is mapped to its type outside the library.

**What follows, in later changes.** The `optic-types.yaml` table and its build
step, with one row. Then `juniper/ex-sfp-10ge-lr` naming that row. The check
from #897: it seats in the EX2300-24P's SFP+ cages, and the bill-of-materials
export shows its model. The rack key and the Explorer type picker come after
that.

## 7. One-way items

Each of these is one-way once it is built and published. Choosing a home is
not, until the first one ships.

| item | why it cannot be taken back cheaply |
|---|---|
| the home itself | Once a wrapper names a type in one home, moving it renames a published thing and every rack file that saved it. |
| a type's id (`sfp-plus-10gbase-lr`) | A rack file saves it. Removing or renaming one is a major change to the table, so ids are kept. |
| the form factor in the id | Keying by form factor and PMD (`sfp-plus-10gbase-lr`) rather than by PMD alone (`10gbase-lr`) decides whether an XFP 10GBASE-LR is a second row or the same one. |
| the published keys of `optic-types.json` | A removed or renamed key raises `format`, as for `cable-types.json`. |
| the wrapper's attr name (`optic-type`) | Every wrapper states it, and the check reads it. |
| the rack key that saves a seated type | A published rack-schema key, declared in `rack.schema.json`. It is named by the Explorer type-picker change, not here. |
| `juniper/ex-sfp-10ge-lr` as its own wrapper | It is the module type's name in a DCIM. Adding SFPP-10GE-LR to it later as a `part-numbers` key renames that module type (`component.schema.json`, `part-numbers`). |

## Sources

- Held in this repository: `docs/pluggables-design.md`,
  `docs/pluggables-generics-design.md`, `spec/schemas/cable-types.yaml`,
  `spec/schemas/listing.schema.json`, `spec/schemas/vendors.yaml`,
  `spec/schemas/rack.schema.json`, `spec/tools/portrayal/lint.py` (L56, L99),
  `spec/tools/portrayal/cable_types_index.py`,
  `spec/tools/portrayal/dcim_export.py`, `kit/rack/export-data.js`,
  `kit/rack/cable-types.js`, `library/components/generic/sfp-lc/v1/` and
  `library/components/molex/sfp-plus-passive-dac/v1/`.
- Held locally, not in this repository: the Juniper MX104 hardware guide's
  converted text, for the worked example only.
- Not held: SFF-8432 Rev 5.2a for this note (the generic's provenance cites
  it), the IEEE 802.3 10GBASE-LR clause and Juniper's EX-SFP-10GE-LR product
  page. The example cites only the guide's words.
