# Failure by omission

**Status: the first sweep is done (#254). The method is meant to be re-run.**

Everything else in this repository guards against saying something **false**.
Lint has ninety-odd rules, the lock will not let a device change quietly, the
provenance vocabulary refuses to let an estimate wear a measurement's clothes,
and the gates run all of it on every push.

None of that guards against saying **nothing at all**, because nothing is not a
claim and there is no rule for it to break.

## The two that started this

Both turned up on one day in September 2026, both by accident, and both had been
true for as long as the code around them existed:

- **The DCIM export decided a placement was an interface when its id began with
  `port-`.** The UfiSpace S9710-76D's ports are `fab-N` and `svc-N`, so its
  export carried **zero interfaces for a 76-port router**. With twelve other
  devices, 271 ports.
- **The interface type table had no row for 800G, 200G, 50G or 10GBASE-T.** 773
  more placements had a family and a speed and nothing to land on.

592 interfaces missing from the committed exports. No rule fired, no test
failed, nothing printed. They were simply absent - and an absent port reads
exactly like a port that does not exist.

Both were found by a person reading an output and asking *is that number right?*
That does not scale, and a new contributor cannot do it at all: they have no idea
what the number should be.

## The shape

> A tool reports success by not reporting anything.

It has now been seen seven times in this repository, which is why it has a page:

| Where | What went quiet |
|---|---|
| `dcim_export` id prefix | 271 ports on 13 devices (#251) |
| `dcim_export` type table | 773 placements with no row (#251) |
| `dcim_export` family test | `"sfp" in "osfp"` - 192 ports read as the wrong cage |
| `dcim_export` PART_IFACE | 24 CFP/CFP2/CXP ports, found by this sweep |
| `dcim_export` PART_POWER | a DC supply's inlet, found by this sweep |
| `lint` PLUGGABLE_CAGES | `sfp56` - two devices L40 never asked, found by this sweep |
| `expand.py --check` | a generator nobody ran (#168) |
| `dcim_export --modules` | 55 module types overwritten by model collision (#267) |
| `cage_type` fallback | 1215 cage placements typed by a table default, seven cards wrong (#294) |
| `size-confidence` | 502 of 526 parts state a size and not where it came from; 97 deny it in prose a search reads as `measured` (#261) |

## The method

Three steps, and the second is the one people skip.

**1. Name the classifiers.** Every table keyed by a string, every selector that
matches on a name or a substring, every `continue` and `return None` in a tool
that produces committed output. In `dcim_export` that was eleven tables and one
substring chain; in `lint`, the rule vocabularies.

**2. Run them over the real corpus and count the fall-through.** Not read the
code - *run* it. A classifier's fall-through rate is a number, and the number is
the finding. This sweep's first census was wrong twice and the corpus said so
both times: once because the mirror of `build_module` left out the fibre exit and
accused four MPO adapters that export perfectly well, and once because it counted
parts composed *inside* other parts, accusing three shells that are never placed
on a card at all.

**3. Triage against the library, not against intuition.** Most fall-through is
correct. A reset button is not an interface and a heatsink is not a port. The
finding is the *minority* that should have classified - so every candidate gets
checked against what the library itself says.

That check is the whole discipline, and it is what keeps the sweep from inventing
data. Three of this sweep's candidates did not survive it:

- **`common/db9-receptacle`, 55 placements.** Looked like a missing console-port
  row; upstream even has `de-9`. All 55 are `alarm-out` - a dry-contact relay,
  not RS-232. Adding the row would have filed 15 alarm contacts as console ports.
- **`dell/rj45-port-14g`, four jacks exporting nothing.** Looked like a missing
  Ethernet row. Dell's own master is named `2x10gb-bt-2x1gb`: two of the four are
  10GBASE-T and the model does not say which. The exporter is right to refuse it;
  the **model** is what is incomplete (#287).
- **`common/sc-apc` on a PON port.** Upstream separates `xg-pon` (10G/2.5G) from
  `xgs-pon` (10G/10G), and the connector ref cannot say which: the same SC/APC
  ferrule serves both. Typing the ref would pick one. (The one device that places
  it now states `pon: xgs-pon` on the port, so a device-level row could; the
  ref-keyed register cannot.)

And it is not only candidates that fail step three. A *rule* can too, and the
same check catches it. Three parts in a row turned out to be thin wrappers over a
connector the exporter already classifies - `common/smb-jack` is "a gold nut
around a std/smb core" in its own words - which makes "a wrapper inherits its
core's type" look like the general fix. Run against the corpus it is wrong on
half the cases it would touch: `common/rj45-ganged-eth` composes
`std/rj45-ganged`, which the console table maps to `rj-45`, so inheriting would
file **every Ethernet jack in the library as a console port**. `common/usb-a`
composed what was then a console row and is a storage port (a USB jack is now
a console only when its placement says so). `casa/c40g-ac-inlet-panel` composes
four inlets and would inherit one. The rule was replaced by three named rows.

## What replaced the silence

Not a fix - fixes are one-shot and this shape keeps coming back. Two instruments:

**A register.** `NOT_A_DCIM_PORT` in `dcim_export.py` names every part the
library calls `class: port` or `class: inlet` that never, on any of its
placements, reaches either export - each with the reason it has none. Ten of
those reasons are "upstream has no type for this", which is a perfectly good
reason and a completely different one from "nobody noticed".

**A test that holds the register from both ends.** `test_silent_drops.py` fails
when a silent port-class part is not named, *and* when a named one has started
exporting. The second half matters more than it looks: it is what stops the
register decaying into a list of things that were once true, which is the failure
mode of every hand-maintained exception list. Run against the exporter as it
stood before this page existed, it names `std/cfp`, `std/cfp2` and `std/cxp`.

And `export_modules` now prints what it could not classify, by name. Most of that
list is furniture. The point is that a name in a log is something a person can be
surprised by, and an absence is not.

## What this sweep did not cover

Said plainly, because a half-swept audit that reads as a whole one is its own
kind of silence:

- **The device pass has no census line.** `publish.sh` runs one process per
  device, so there is no single place that sees them all; `test_silent_drops.py`
  covers both passes, the printed line covers only modules.
- **`render.py` was not swept.** Its omissions are visible - a part that does not
  draw is a hole in a picture - which is a different failure mode from a silent
  one, and Gate 5 already asks a person to look.
- **The intake tools** - `visio_*`, `ocr_pages`, `measure`, `facts*` - were not
  swept. Their output is read by a person at the time, before anything is
  committed.
- **`lint`'s own vocabularies were spot-checked, not swept.** `PLUGGABLE_CAGES`
  is now held against the media the library uses; `MEDIA_FAMILY` was read and is
  safe by construction (a miss answers for itself). The rest were not.

Anyone extending this should start at step 1 on whichever of those is next, and
should expect step 2 to prove them wrong at least once.
