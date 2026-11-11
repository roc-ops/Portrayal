# XENPAK and CPAK: deliberately deferred

Status: deferred, decided 2026-11-11. Nothing is built, and this note changes
no component, schema, lint rule or device. It is the record #61 asks for.

#61 lists four optical form factors that have no aperture: OSFP, SFP-DD,
XENPAK and CPAK. OSFP and SFP-DD now exist as `std/osfp` and `std/sfp-dd`
(`docs/pluggables-osfp-xfp-design.md` and `docs/pluggables-sfp-dd-design.md`
describe the parts built on them). Its "Done when" accepts, for the four, that
they "either exist or are recorded as deliberately deferred". XENPAK and CPAK
are recorded here as deferred. Until now only the pull request that added
`std/rj11` said so, in its "What stays" table and for that pull request alone,
and `docs/rj45-family-design.md` ("Out of scope") lists them as outside that
work.

## Where the two stand on `main`

| | XENPAK | CPAK |
|---|---|---|
| a registry entry in `spec/schemas/standards.yaml` | none | none |
| a connector key in `spec/schemas/connectors.yaml` | none | none |
| a rung in `spec/schemas/pluggables.yaml` | none | none |
| a `std/` component | none | none |
| a source document held | none | none with a dimension (below) |
| modelled parts that name it | none | three line cards, below |

XENPAK appears in no contract, skin, device, test or schema. `git grep -i
xenpak` finds one line, the "Out of scope" paragraph of
`docs/rj45-family-design.md`.

## What each needs before it is modelled

Both need the same four steps that OSFP, XFP and the CFP family went through
(`docs/pluggables-osfp-xfp-design.md`, `docs/pluggables-cfp-cxp-design.md`):
a held source for the host opening and for the module envelope; entries for
them in `standards.yaml`; a connector key and a `pluggables.yaml` rung, so a
cage can state what it seats; and a `std/` part that draws the opening. The
sources are what is missing.

**XENPAK.** The governing document is the XENPAK MSA, a legacy specification
that XFP and X2 superseded; #61 records its availability as unknown. No file
named for it, and no text that mentions it, is in the intake this library is
modelled from. What would let it be modelled: the XENPAK MSA's mechanical
specification, with the module outline and the host opening, held and cited by
title and page. A second condition is #61's own: take it up when a device that
has XENPAK ports is modelled. No device in the library has one.

**CPAK.** Cisco's pluggable for its 100 Gigabit Ethernet line cards; #61
records it as proprietary with no public MSA. What would let it be modelled: a
Cisco mechanical drawing of the module and of the faceplate opening, or a
measurement of one. The Cisco ASR 9000 Series 4-port and 8-port 100 Gigabit
Ethernet Line Cards data sheet (C78-733790) names the CPAK interfaces and
gives the card's dimensions; it gives no CPAK dimension. Nothing else held does.

### The modelled parts that name a CPAK port

Three line cards draw CPAK cages. Each cage is a `class: cutout` element of
13.92 x 37.01 mm, transcribed from Cisco's ASR 9000 stencil master. The
cutouts compose no `std/` part, state no interface and conform to nothing, and
each contract's `provenance.aperture` says so. Each contract carries one L26
warning for it, recorded in `library/lint-baseline.json`.

| component | version | CPAK cutouts |
|---|---|---|
| `cisco/a9k-4x100ge-se` | 1.0.2 | `cpak-0` to `cpak-3` |
| `cisco/a9k-8x100ge-se` | 1.0.2 | `cpak-0` to `cpak-7` |
| `cisco/a9k-8x100g-lb-se` | 1.0.2 | `cpak-0` to `cpak-7` |

The ASR 9006, 9010, 9904, 9912 and 9922 reference these cards. The stencil
master is a drawing of the faceplate, not a Cisco statement of the CPAK
opening, so its figure is not a source for a `std/` part.

Two other families mention CPAK without a CPAK port. The MPA adapters
`cisco/a9k-mpa-1x100ge` and `cisco/a9k-mpa-2x100ge`, and the 400 Gigabit
carriers `cisco/a9k-mod400-se` and `-tr`, quote Cisco's supported-adapter list
that spells "CFP2-DCO and CPAK". The adapters model CFP2 cutouts and state
`media: CFP2`. The A9K-8X100GE-X cards and the QSFP28 `cisco/a9k-4x100ge`
say in their contracts that they are not CPAK cards.

## Where the code and the notes disagree

These are recorded here and not changed by this note.

- The docstring of `lint_component_aperture` (rule L26) in
  `spec/tools/portrayal/lint.py` (near line 1786) says the CPAK, CFP and CFP2 specifications "withhold the
  figure by design". That is true of CPAK. `standards.yaml` now holds `cfp`
  and `cfp2` openings from the CFP MSA drawings, and `std/cfp` and `std/cfp2`
  exist.
- The `aperture` provenance of the two MPA contracts still says the CFP2 figure
  is withheld, and their CFP2 cutouts are 15.23 x 37.13 mm against the 14.30 of
  `std/cfp2`. Composing the part is a separate piece of work.
- The `aperture` provenance of the three CPAK line cards names CFP MSA
  membership among the ways to close the gap. #61 says a CPAK figure would come
  from a Cisco drawing or a measurement.

## What this leaves open on #61

This note closes #61's XENPAK and CPAK rows as deferred. The issue stays open
for: the size of `std/qsfp-dd`, which rests on a source the registry marks
unverified; `common/sc-apc`, which waits for TIA-604-3; and the citation of
`std/micro-usb`.

## When to take this up again

- A device that has XENPAK ports is to be modelled, and the XENPAK MSA's
  mechanical specification is held.
- A Cisco drawing of the CPAK module and faceplate opening is held. Then the
  three line cards compose the new part, which asks each card for a version
  bump and each of the five chassis for the bump the lock reports; trial it
  with `devicelock.py` before promising a size.

When either happens, replace this note's row for that form factor with a link
to the design note that builds it.
