# Review standards

What a review of a change to this repository checks, beyond what the gates
already check. It is read at review, by whoever reviews: a person, or an agent
following [`portrayal-review`](../.claude/skills/portrayal-review/SKILL.md).
It is deliberately not part of the modelling method. Someone building a device
is finding sources, drawing and debugging; these are the questions for the
second pass, when the work exists and can be looked at.

**Only judgement lives here.** A rule a tool could check belongs in the tool:
a lint rule, a test, the lock. If a review catches the same mechanical thing
twice, the fix is the check, not a line in this file. Everything below is
something no gate can decide, and a reviewer skips anything the gates already
enforce.

## How a review runs

A review answers two questions and reports them separately, because a change
can pass one and fail the other.

- **Sources.** Does the change say what its sources say? For a device, that is
  the documents its provenance cites and the issue it closes: what the issue
  asked for and is missing, what was added that nobody asked for, and what is
  present but wrong.
- **Standards.** Does the change follow the sections below?

The reviewer fixes what it finds and commits the fix to the branch. A comment
is for a question only the author or the maintainer can answer: a judgement
between two readings of a figure, a one-way door, a waiver. The person who
reads the pull request afterwards should be reading a finished change, not a
list of things to do.

## Every change

- **The merge danger is stated and is right.** The pull request says whether it
  is a one-way door and what it can reach; see the list in
  [`CONTRIBUTING.md`](../CONTRIBUTING.md#merge-danger). A change that calls
  itself two-way while renaming a component or an export is the case to catch.
- **A claim that can be counted was counted.** A colour read off a photograph
  comes with a pixel count; a figure with the page it came from; an interface
  type with the upstream file that defines it. A confident sentence with
  nothing behind it is what stops the next reader checking.
- **A relative is not evidence.** A convention established for one product
  family (an airflow colour, a lamp order) is not a reading of a different
  device. If the documents for this device are silent, the file says so and
  opens a gap.
- **Nothing private.** No vendor material, no person named as the decider, no
  path into an untracked directory, no reference to a tool a public reader
  cannot use.
- **No generated file was edited by hand.**

## A device or a component

- **The comparison was made, for every face that has a reference.** The pull
  request carries the sentence Gate 5 asks for, and a face with no reference
  image is named as such. Ask for the sentence before believing the file.
- **Look at every face and every module, zoomed.** Overlap is the defect a
  person catches most and a gate catches least: decor over a port, text over a
  vent, a lever over a label, a part out of its rotated cutout. Look again
  after a fix; two correct fixes can collide.
- **A rule that starts on a face reaches the end of it,** or the file says why
  it stops.
- **Physically implausible is a failed check, not a finding.** Staggered fans,
  a jack upside down, a module wider than its bay: find the second image and
  measure both before accepting it.
- **What is never drawn stays undrawn:** rack ears, cable furniture, a vendor
  logo. The exception is a part that IS one: a `rack-face` part is its ears,
  and a cable manager modelled as its own device is drawn
  ([cable-managers-design.md](cable-managers-design.md)). A logo gets a
  reserved `logo-zone`; a product name in plain text is fine.
- **A thing at component scale is a component.** A cover, door or filler drawn
  as bare decor is an unexplained box in the tree.
- **A cutout is not left empty,** and a lamp that has states draws with the
  state colour, not a fixed fill.
- **A rotated or stacked placement was rendered seated.** Stacked cages sit
  belly to belly and a turned bay is easy to get upside down; only a seated
  configuration shows it.
- **A vent is declared, not coloured.** Decor that is a hole in the sheet says
  `vent:` or `pattern: vent`; on a device with an interior well, the walls
  were looked at from inside with the cover off.
- **A relief change was looked at in 3D, in every configuration.** A slab that
  buries the detail behind it lints clean.
- **A rename is priced as a major** on every device that seats the part, and
  was worth it. A corrected attribute or provenance note is a patch.
- **A new device joins the written censuses with its own paragraph,** not with
  a waiver. A waiver records an argument the alternative lost, not a
  preference.
- **A first-of-kind module had its DCIM export read,** not just generated.

## A test

- **It fails when the thing it guards breaks,** and the author says how they
  know: the fix removed, the fault planted.
- **It asks through the interface.** It runs the tool the build runs and reads
  what that tool writes. A test that reads source text, or reaches past the
  interface to check a private detail, breaks on a rename and passes on a bug.
- **The expected value is independent.** A literal worked out by hand, never
  the same computation the code performs.
- **It measured something.** A sweep asserts how many things it walked; a skip
  gates on whether the build ran, never on whether the result was empty.
- **Its fixture is built, not borrowed.** A test pinned to what a live device
  lacks breaks the day the device gets better.
- **It is worth what it costs.** A test of five seconds or more says why a
  lint rule or a cheaper fixture could not answer the same question, and a
  whole-library lint or index is the session's shared one, not a new run.

## Tool and kit code

These are heuristics, each a possible problem to weigh, never a violation on
its own.

- **A check was run against the real library before it was believed.** A rule
  that searches prose measures what its author expected to find.
- **A lint rule is generic.** It states a property of hardware, not of one
  vendor; a rule that names a vendor is a census of that vendor's exceptions.
- **The same logic in two places** (the renderer and the indexer, the build
  and the kit) is one function wanted, or a parity test.
- **An option, parameter or hook nothing uses yet** is removed until
  something does.
- **A viewer change was exercised both ways it redraws:** a repaint and a full
  rebuild. A fix that holds on one path and not the other is common.
