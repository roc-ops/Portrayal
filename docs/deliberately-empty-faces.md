# A face with no source: the design says one thing and the implementation another

Written 2026-08-26, out of the ASR 9000 family reaching capability 2 on all seven chassis with
exactly one face short on each. Not a Cisco quirk - see the evidence section.

## The situation

Seven modular chassis. Front, rear, top, left and right all carry sourced content. The bottom
carries none, on every one of them, and cannot be made to without inventing a face.

## The evidence that this is not one vendor being unhelpful

**There is no bottom view of any ASR 9000 chassis anywhere in the 78-document intake.** Every
figure caption in all 65 PDFs was searched for "Bottom View", "underside" and "bottom of the
chassis". Zero hits. This is an exhaustive search over captions returning nothing, not a failure
to find something.

That is a fact about how a rack chassis gets documented rather than about Cisco. A face that sits
on rails, is never serviced, has no connectors, no indicators and no user-replaceable parts gets
no figure - because there is nothing a technician would ever need to see there. Expect the same on
any rack-mount device from any vendor, and expect it MORE the larger the chassis, since a 44 RU
box is never lifted to look underneath.

By contrast every other face earns documentation for a reason: the front and rear because parts go
in them, the top because the footprint drawing has to dimension something, the sides because rack
rails bolt to them and airflow crosses them.

## The mismatch

The capability-levels design (the intent behind `spec/tools/portrayal/capability.py`) defines level 3 as

    "all six of front/rear/top/bottom/left/right present, sized, AND MUTUALLY CONSISTENT"

and says the consistency check "is the valuable half of level 3, and it is not 'six views exist'".
It does not ask for content.

The implementation does. `assess()` builds `drawable` from views that have a size AND pass
`_has_content`, and level 3 inherits that set. But `_has_content` was written for LEVEL 1 - its
docstring is about "something is drawn on this face beyond the bare rectangle" and level 1's
failure message is "no view has both a size and anything on it". That is the right test for "is
this a drawing". It is the wrong test for "does this describe a box", which is what level 3 is
about and what 3D needs.

**So the implementation is stricter than the written design, and for this case the design is
right.** A chassis whose six faces are all correctly SIZED already describes the box correctly;
the 3D view and the rack elevation are the right shape today.

## Why it must NOT simply be relaxed

A sized-but-empty face is ambiguous, and that ambiguity is the whole risk:

- **"this face is genuinely plain metal, and I checked"**, or
- **"nobody has modelled this face yet"**.

Silently accepting both lets an UNMODELLED face reach level 3 and puts a plausible wrong box in
the 3D view - which is precisely the failure capability levels exist to prevent. Dropping the
content test would trade a visible, honest failure for an invisible, dishonest pass.

## What was rejected, and why it is worth recording

Adding a `regions` entry naming the bottom plate WOULD satisfy the predicate today - regions count
as content. It was rejected. A region that says "bottom plate, no features documented" passes the
check by annotating that we have nothing, which is the same species as prose-in-attrs, invented
captions, and every other statement this project has spent the session removing. **A check passed
by describing an absence is worse than a check failed honestly**, because the failure is visible
and the annotation is not.

## THE STRONGEST ARGUMENT, and it only became visible once the family was finished

It is better than either argument above.

**Level 3 is currently being reached on these chassis THROUGH A SINGLE DERIVED LINE THAT HAPPENS
TO BE LEGITIMATE.** Seven of the eight Cisco chassis earn their bottom face from one 3.9 mm strip
marking the rack mounting plane. That line is real - a dimensioned plane that necessarily
intersects the face - and it deserves to count. But it is the only thing on that face, and the
level therefore turns on whether the vendor happened to dimension a mounting plane in a top-down
figure.

**So the level is measuring whether a lucky feature exists, not whether the face is modelled.**
Two symptoms show it is luck rather than structure:

- **The feature is not consistently placed.** 0.0 mm from the front on the ASR 9001, 62.2 on the
  9904, 145.5 on the 9006, two of them on the 9906. There is no property of a chassis that
  predicts it.
- **THE BEST-DOCUMENTED CHASSIS IN THE FAMILY IS THE ONE THAT FAILS.** The ASR 9910 has Figure 12,
  a proper dimensioned three-view mechanical drawing - Top, Front and Side - which is more than
  any of its seven siblings has. It is stuck at level 2 because that figure spends its dimensions
  on the OUTSIDE of the box and none on where the box mounts. Four separate routes were tried and
  recorded; all four fail. A chassis with a worse drawing that happens to dimension its mounting
  plane scores higher.

That is the clearest possible statement of the problem: **the metric ranks the 9910 below chassis
it is better documented than.** A declaration mechanism would let a face say what it is directly,
and the 9910 would then be able to say "this face is undocumented and here is the evidence I
looked" - which is a different and more useful answer than "level 2".

## The proposed shape

**A view may DECLARE itself deliberately empty, with provenance saying why, and that declaration
satisfies level 3's face test where silence does not. Empty-by-verification counts;
empty-by-omission does not.**

That is the same three-state honesty the design note already applies to `capability.unknown` -
untestable is not the same answer as failed - and the same discipline as the gaps register:
declare the unknown so it cannot be mistaken for either a finding or an oversight.

Sketch, not a proposal for syntax:

    bottom:
      size: {w: 447.0, h: 668.0}
      empty: 'no bottom view exists in any of the 78 documents held; searched every
              figure caption in 65 PDFs. The face sits on rack rails and is never serviced.'

with `_has_content` unchanged for level 1 - a declared-empty face is still not a DRAWING - and
level 3 accepting `content OR declared-empty`.

## The ruling that came back, verbatim, because it decides this class of question

  ANNOTATING AN ABSENCE is illegitimate - a region whose entire content is "there is nothing here"
  passes a content check by describing the lack of content.

  DERIVED GEOMETRY is legitimate - a real plane, dimensioned in a real figure, that necessarily
  intersects this face.

**The test: does removing this make the drawing LESS TRUE?** Remove an absence-note and nothing is
lost. Remove the mounting line and you lose a real fact about where the chassis meets the rack.

That is what settled the rack mounting strip in favour and `underside - no feature documented`
against, and it is a cleaner discriminator than anything in this note's first draft.

## Interim, in force now

Accept level 2 for the Cisco family. Every affected chassis carries a
`bottom-face-is-undocumented-family-wide` gap stating the search, the reason no region was added,
and the fact that the face is correctly sized. Nothing is invented. The 3D box is the right shape
and the capability number honestly reports that one face is undescribed.

`capability.py` is not changed by this note. It is core, and this is a design decision rather
than a bug fix.
