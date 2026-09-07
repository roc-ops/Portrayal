# What a bay's size means, what a component's size means, and why a card can exceed its slot

Written for the Cisco ASR 9000 family after a fit check compared every bay against every component
it accepts and returned 266 mismatches. Four were real. The other 262 were one convention that had
never been written down, and this file is that convention.

## The two numbers

**A COMPONENT'S `size` IS ITS ENVELOPE — the plate PLUS its ejector levers.** That is what Cisco
publishes and what the components in `library/components/cisco/` carry.

**A BAY'S `size` IS THE SAME ENVELOPE**, so that a bay and its occupant can be compared at all.
It is NOT the cage opening.

## Why a bay is legitimately larger than the hole it sits in

Two Cisco statements about the same card family fix this, and the difference between them is the
whole answer:

    Table A-10, OL-17500-09     14 in     = 355.60 mm    no qualifier
    4th-generation data sheets  15.58 in  = 395.70 mm    "includes ejector bracket/lever"
                                            ---------
                                             40.10 mm    the ejectors, ~20 mm each end

And the measured cages:

    ASR 9010  354.95     ASR 9912  357.35     ASR 9922  358.20
    ASR 9906  364.32     ASR 9910  365.62

**The PLATE fits the opening — 355.60 against the 9010's measured 354.95, agreeing to 0.65 mm —
and the EJECTORS sit outside it.** So a bay declared at 395.70 in a cage measuring 354.95 is
correct, not an error, and a fit check that does not know this reports it 262 times.

## What that means for reading a mismatch

A component larger than its bay is one of three things and they need separating:

1. **A STALE NUMBER.** One side was corrected and the other was not. The ASR 9922's sixteen power
   bays sat at 95.85 for hours after the module was corrected to 99.62, because the sweep that
   fixed the 9006 and 9010 matched on a row of three and the 9922's are a 4x4 grid. **This is the
   kind the check exists to find**, and it is invisible to lint.
2. **A SCOPE DIFFERENCE.** Envelope against plate, over-ejector against seating. Not an error;
   record which scope each number is and move on.
3. **A GENUINE CONTRADICTION.** The number cannot be reconciled with a dimension that is
   independently confirmed. Then the bay does NOT move — see below.

## The rule that decides case 3: a bay never exceeds the measured pitch

**A bay may be larger than the cage opening (ejectors) but must NEVER be larger than the slot
pitch**, because the pitch is what physically separates one card from the next. Widening past it
makes adjacent bays overlap, which is exactly what L13 reports.

This bit twice in one sitting. Widening the ASR 9906 and 9910 line card bays to 44.20 to admit the
RSP4-S produced 25 L13 overlaps, because their measured pitches are 43.42 and 43.78. The RSP4-S
does not fit those chassis at its published thickness, and inflating the geometry to pretend
otherwise would have put the error into the drawing.

## The one unresolved conflict in this family, recorded rather than absorbed

Every CONTROL card is published ~428 mm long and ~46 mm thick:

    RSP-880 / RSP880-LT   46.0 x 428.5      ASR9922-RP   46.0 x 428.5
    RP3                   41.4 x 428.2      RSP4-S       44.2 x 403.4

Against measured pitches of 43.42 to 44.33 and cages of 354.95 to 365.62, **neither dimension
reconciles even after allowing the full 40.10 mm of ejector** — a 428.5 plate would still be
33.45 mm too long for a cage two unrelated sources agree on.

Four different control cards all landing ~33 mm over is not four independent errors; it is one
systematic difference in what Cisco measures for a control card. **That consistency is evidence
FOR the reading, not against it.** So the accepts keep those cards where Cisco names them, the
bays stay at what the cage and the reconcilable envelopes allow, and each affected chassis carries
a `sources-disagree` gap naming both axes.

## Using a fit check

The audit used a small script that compared every bay's size against every component in its
`accepts` list. It is not in the repository, and any replacement should be honest about the same
three limits, because they matter: **it ignores bay `rotate`, it cannot tell an envelope
from an opening, and it allows either orientation to satisfy a fit** — so it will pass a card that
is the right size the wrong way round.

It is a smoke detector, not a measurement. Treat every mismatch as a question, sort it into the
three cases above, and expect most of them to be case 2 until this note is contradicted.

Cisco family as of writing: 52 mismatches remain across 121 bays, and every one is the control-card
conflict above.


---

# RECONCILING A BAY AND A MODULE SILENCES THE ONLY CHECK THAT CAN SEE THEM

The most important thing in this note, added after most of the reconciling had already been done.
Learned by fixing a PEM fit by growing its bays, committing it, and then reversing it.

**A fit check compares a bay to a component and NEITHER of them to the world.** It is satisfied by
both being wrong together exactly as easily as by both being right. So:

> Every mismatch resolved by moving one side removes the SIGNAL without adding any TRUTH, and once
> resolved nothing will ever flag it again.

That makes a resolved mismatch strictly worse than an open one, unless the resolution came from
outside the pair. The open one was visible.

## The test to apply before touching either number

**Did this number come from a third thing?** Not from the bay, not from the component:

- a measured cage extent, a slot pitch, a printed label;
- a published dimension with its scope stated;
- a NEIGHBOUR - what sits above, below, or on the opposite face.

If yes, it is a measurement and the fit going quiet is earned. **If no, it is a judgement, and it
must be recorded as one**, because nothing downstream will ever ask again.

## What that meant here, honestly

Auditing every distinct bay dimension across the five ASR 9000 chassis after this was pointed out:

    sourced        43.70, 46.00, 76.20, 99.62, 139.12, 395.70, 447.09, 41.07, 42.85, 44.45
    RECONCILED     42.67, 403.10, 403.40, 406.40, 492.10

**Five of fifteen were grown to meet a component.** Each is now listed in a
`bay-extents-reconciled-rather-than-measured` gap on the chassis carrying it, naming the value,
the bay count and the card it was grown to meet. The ejector arithmetic - 355.60 against 395.70,
40.10 mm - justifies the SHAPE of those numbers without justifying any particular one of them, and
the gap says so.

## And check the neighbour's own provenance before anchoring to it

The first attempt at that fix mounted a real edge flush against a number that turned out to be a pitch
divided out of a DIFFERENT chassis and then accumulated six times. **"It is in the file" is not the
same as "it was measured"**, and an accumulated pitch is the softest thing available to anchor to.
Before resolving a bay against a neighbour, read how that neighbour's own number was arrived at.

The corollary, which bit here too: several chassis in this family carry cage provenance generated
from ONE template across five files. Where that happened, five files agreeing is one source wearing
five hats, and it looks exactly like corroboration.
