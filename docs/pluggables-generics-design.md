# Pluggables A: `generic/` transceivers

Status: design agreed with Jason, 2026-09-18. Part of [pluggables-design.md](pluggables-design.md),
which holds the shared decisions; this document is the one that goes to planning first.

## Goal

One drawn transceiver per form factor and face, sourced from the MSA that governs its
envelope, carrying no rate and no vendor fact, seating in every cage of its family
through the mating mechanism the library already has. A vendor optic is a wrapper
around one of these. When this lands, the two `common/` generics are retired, the
five device configurations that ship seated optics are bare, and a partner can add an
optic with one contract and no drawing.

## What exists and is kept

- `mates:` / `interface:` / `connection-points.mate` and L12. Every SFP-family cage
  presents `interface: sfp`, every QSFP-family cage `qsfp`, and vendor cages forward the
  aperture's mate point (#54, `manifest.presented_interface`). Nothing in A changes this.
- `configurations.<n>.occupants:` and its expansion to `mate-to` placements
  (`render.py`, `test_occupants.py`). Kept as the seating mechanism; not used by any
  shipped device after A.
- `std/lc-bore@3` as the LC face. Both existing transceivers compose it; the generics
  compose it too.
- The doctrine in both existing generics' `provenance.power`: a generic states
  `power-absent: not-applicable` because a wattage on a shape that stands for every
  module of its kind would be a fiction dressed as a fact. Carried over verbatim in
  spirit; the figure belongs on the wrapper.
- `fields:` and `data-fill-from` / `data-from` (#177: a colour is a field, not a second
  drawing). The latch colour and label are fields.

## What is new

### 1. The `generic/` namespace

One entry under `namespaces:` in `spec/schemas/vendors.yaml`:

> `generic`: representative of a class under a spec. The envelope is a published
> standard - it is what makes the part seat everywhere its family does - and the
> appearance stands for every product of its kind rather than any one of them. A
> vendor's product wraps a generic and adds its facts; a vendor's outlier draws its
> own. Transceivers and connectors first; DIMMs, PCIe cards and CPUs belong here when
> they arrive. Nothing already in `common/` moves here in the work that creates it.

L55's namespace check reads that map; no lint change is needed for the namespace itself.

### 2. Module envelopes in `standards.yaml`

Four entries, in the registry's existing shape (`registry`, `w`, `h`, `radius`,
`confidence`, `depth`, `depth-confidence`, `depth-notes`, `notes`), so L9 holds each
generic's drawn size to its standard exactly as it holds a cage's:

| key | registry line | where the numbers come from |
|---|---|---|
| `sfp-module` | SFF-8432 Rev 5.2a | Fig 4-1 IPF Module and Table 4-3 Dimension Table - width, height, overall length, and the latch/bail datums |
| `qsfp-module` | SFF-8661 Rev 2.5 | Fig 5-1 Basic Views - 18.35 x 8.5 envelope and the length datums |
| `qsfp-dd-module` | QSFP-DD/QSFP-DD800/QSFP112 HW Rev 6.3 | section 7.3, Fig 47 (Type 1) - Type 2/2A/2B differ behind the bezel and are not separate generics |
| `osfp-module` | OSFP MSA (fetch) | the module outline figure in that spec |

The numbers are transcribed from those figures during the build, into the registry
first and the contracts second, so a contract cannot carry a figure the registry does
not. No number is written in this design that has not been read off the page.

XFP (INF-8077i) and CFP/CFP2 (CFP MSA hardware specs) are the same shape of work and
are a second batch after these four; they are not in day one because no device in the
library needs them populated and their specs are not yet held.

`osfp-module` was scoped out of this plan's execution - the OSFP MSA was never fetched
and no built part depends on it (`generic/osfp-mpo12` is gated on the MPO receptacle
regardless); it is the first item of the second batch.

### 3. The generics

Named form x face. A generic's name never carries a rate.

| part | face | notes |
|---|---|---|
| `generic/sfp-lc` | LC duplex | migrates `common/sfp-lc-duplex` |
| `generic/sfp-lc-simplex` | one LC (bidi) | |
| `generic/sfp-sc` | SC simplex | gated: needs `std/sc-bore`, which has no free dimensions - see section 4 |
| `generic/sfp-rj45` | RJ45 | gated: no free document dimensions the RJ45 opening cut into a copper SFP's face, and every panel jack in the library (12.7 x 11.0 and larger) is taller than the 8.55 envelope the part conforms to - an outline the envelope excludes is worse than a missing part; a 10GBASE-T SFP+ mechanical drawing would settle it |
| `generic/qsfp-lc` | LC duplex | migrates `common/qsfp-transceiver`'s `lc` skin |
| `generic/qsfp-mpo12` | MPO-12, one row, pinned | gated: needs a dimensioned MPO receptacle |
| `generic/qsfp-dd-lc` | LC duplex | |
| `generic/qsfp-dd-mpo12` | MPO-12, one row, pinned | gated as above |
| `generic/qsfp-dd-mpo16` | MPO-16, one row, pinned | gated as above; a different key, so a different part |
| `generic/qsfp-dd-mpo24` | MPO-12 two row, pinned | gated as above; same key as mpo12, own part for the ferrule |
| `generic/osfp-mpo12` | MPO-12, pinned | gated as above, plus the OSFP fetch |

The face names are the QSFP-DD spec's own (HW 6.3 section 6.2, fourteen media
dependent interfaces): `lc` (duplex LC), `mpo12`, `mpo16`, `mpo24` (the spec's
"MPO-12 two row"), `dual-mpo12`, `dual-lc` (dual duplex LC), `dual-cs`, `quad-sn`,
`dual-sn`, `quad-mdc`, `dual-mdc`, and BiDi variants of MPO-12, SN and MDC. Only the
first three are day one; the rest are named here so nobody invents a second spelling
when a 400G-DR4 or an 800G-SR8 arrives. SN, MDC and CS are connectors the library
does not have yet and get their own bores when they come.

An MPO-8 is not a part: the QSFP+ receptacle figure (INF-8074 Fig 21a) marks four
of its twelve positions "unused", so an SR4 is `generic/qsfp-mpo12` with
`optical.unused` on the wrapper saying which four and why. See the umbrella's
"what is one part and what is two".

Contract shape, common to all:

```yaml
format: 1
kind: component
name: sfp-lc
version: 1.0.0
class: transceiver
behaviour: occupies
mates: sfp
conforms: sfp-module
profile: networking
size: {w: <registry>, h: <registry>, d: <registry>}
attrs: {power-absent: not-applicable, form-factor: sfp, face: lc-duplex}
fields:
  latch-color: {label: latch colour, type: text, default: '#1f7a3a'}
  label:       {label: module label, type: text, default: ''}
parts:
  - {ref: std/lc-bore@3, id: tx, at: [..], rotate: 180, lift: <protrusion>}
  - {ref: std/lc-bore@3, id: rx, at: [..], rotate: 180, lift: <protrusion>}
relief:
  features:
    - {node: body, out: <protrusion>, confidence: drawing, source: 'SFF-8432 ...'}
    - {node: latch, lift: <protrusion>, out: <..>, confidence: drawing, source: '...'}
connection-points:
  mate: {at: [w/2, h/2], direction: front}
  optical-tx: {at: [..], direction: front}
  optical-rx: {at: [..], direction: front}
skins: [default]
```

Three things the shape enforces:

- **Every generic protrudes from day one** (umbrella decision 9). The protrusion is
  the module's overall length less the cage's bezel-to-connector depth, both from the
  MSAs - the subtraction `common/sfp-lc-duplex` already documents, with a better source
  on each side. Where an MSA gives the latch or bail its own reach, that is a second
  feature; where it does not, the feature says `estimated` and why.
  Every generic draws the MSA's MAXIMUM protrusion - designator A's 10.0 recommended
  maximum for SFP, the 20 MAX nose for QSFP and QSFP-DD - rather than a typical
  module's, because the maximum is the figure the standards publish and a typical
  figure would be an estimate.
- **The face's optical axis is not the module centreline** and is not sourced by any
  MSA. SFF-8436 and the QSFP-DD spec both defer the LC receptacle to TIA-604-10, which
  is paywalled. The generics inherit the current bores' position tokens and the
  provenance says so in the same words the existing parts use.
- **No rate, reach, wavelength or wattage.** Enforced by lint, below.
- **An MPO face declares `optical.positions` and `optical.gender: pinned`.** Positions
  because a module composing the face must never restate the count (the schema's own
  rule); gender because both module specs say the receptacle carries the alignment
  pins, and B's plugs are the other half of that fact.

### 4. `std/sc-bore`

GATED AT EXECUTION, 2026-09-18. The library has no SC face - `common/sc-apc` is a 24
x 26 mm moulded PON bay - and no free document dimensions the SC simplex keyed
opening a `std/sc-bore` would need. Searched: SENKO DS-SC-000006 (plug; no front
view, unlike the LC plug datasheet the LC bore was built from), DS-SC-000010 and
DS-SC-000011 (adapters; housing and panel cutout only), FS SC/UPC simplex adapter and
Molex 106167 (the same), TE catalogue 1307895 pp. 49-52 (the 13.0-13.5 x 18.0
SC-footprint panel cutout for adapters, not the keyed opening), and OKF (nothing).
TIA-604-3 / IEC 61754-4 are paywalled. So the SC face waits for a drawing exactly as
the MPO faces do, `generic/sfp-sc` is not in this plan, and
`working/intake/fiber-connectors/sc/COVERAGE.md` records the search. What would
settle it: a TE customer drawing of an SC simplex adapter or connector with a front
view, or the standard.

### 5. One lint rule

**L99 - a generic stays generic.** A contract under `generic/` with `class: transceiver`
is an error if its `attrs` carry any of `speed`, `reach`, `wavelength`, `mode`,
`power-draw-max-w` or `power-draw-typical-w`, or if its `name` matches a rate token
(`sfp28`, `qsfp56`, `10g` ...). This is the defect `common/sfp-lc-duplex` has today,
made impossible to repeat, and it is what keeps decision 5 true after the people who
took it have moved on. Warning-free on a clean library; tested with a fixture.

### 6. The wrapper idiom, documented

`library/components/README.md` gains a section: how to add an optic. It shows the
wrapper from the umbrella, says which attrs belong on it (`model`, `media`, `speed`,
`reach`, `wavelength`, `power-draw-max-w`, and `latch-color` / `label` passed to the
part), says that `mates:` on the wrapper must equal the generic's, and says what an
outlier does instead. That section is the whole contribution surface for an optics
partner.

### 7. Migration

1. Build `generic/sfp-lc` and `generic/qsfp-lc` from the two `common/` parts' sourced
   figures (the SFP's drawing-plus-STEP 13.5 x 8.5, the QSFP's toleranced 18.35 x 8.5 x
   83.2) cross-checked against SFF-8432 and SFF-8661, keeping every provenance sentence
   that still holds and dropping the SFP's baked-in `mode`, `reach`, `speed`.
2. Strip `occupants:` from the five UfiSpace configurations (`s9600-32x breakout`,
   `s9600-28dx`, `s9600-64x`, `s9510-28dc`, `s9501-28smt` `dc-populated`). The
   configurations stay - `breakout` is a real software state - and their descriptions
   stop saying "fitted with 25G optics".
3. Move `test_occupants.py` and `test_mate_forwarding.py` onto a fixture device under
   `spec/tests/fixtures/` that seats a `generic/` part, so the mechanism stays tested
   without a shipped device carrying an optic.
4. Leave `common/sfp-lc-duplex@1`, `common/qsfp-transceiver@1` and
   `common/qsfp-drawing@1` in place. L89 asks any unreached major to say why; the two
   transceivers gain an `unplaced:` sentence pointing at their `generic/` successors,
   and are deleted in a later sweep once nothing references them. `qsfp-drawing` is a
   reference sheet and already says so.
5. Correct `library/components/README.md`'s claim that the viewer textures a box from
   `body-*.svg`; nothing reads them (D decides whether anything should).

### 8. What the DCIM export does

Nothing new. An occupant does not change the interface export - the NetBox interface
is the cage - and `dcim_export.py` already skips `std/lc-bore` as "the bore of a
transceiver, not a port". `std/sc-bore` joins that skip list.

## Order of work

1. Fetch the OSFP MSA into `working/intake/optic/msa/` beside a `SOURCES.md`; read
   SFF-8432 Table 4-3 and SFF-8661 Fig 5-1 out of OKF.
2. `standards.yaml`: the four module entries.
3. `vendors.yaml`: the `generic` namespace. L99 and its fixture test.
4. `generic/sfp-lc` and `generic/qsfp-lc` by migration; render each beside its MSA
   figure at matched scale (Gate 5).
5. `sfp-lc-simplex`, `qsfp-dd-lc`.
6. Strip the five configs; fixture; README section and README correction.
7. Gates: lock, lint, build, publish, catalogue, suite. One PR per numbered step where
   a step touches shipped devices.

MPO faces and OSFP follow when their dimensions are in hand; they are tracked, not
blocked on.

## Open questions

- Whether `generic/sfp-rj45` composes the RJ45 aperture as a face or draws the copper
  jack's opening itself. Composing keeps one source of truth for the opening; the
  decision waits for the first drawing of a copper SFP's face.
- The MPO receptacle dimension. The QSFP-DD spec's Figs 28-30 draw the three MPO
  receptacles and do not dimension them; a public MPO adapter datasheet (SENKO, US
  Conec) probably does, and the MPO-16 one needs its own since the key differs.
