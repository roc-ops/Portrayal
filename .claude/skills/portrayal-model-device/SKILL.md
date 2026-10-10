---
name: portrayal-model-device
description: Use when modelling a hardware device for Portrayal from reference material (datasheets, install guides, drawings, photos) - building or revising a device.yaml and any components it needs. Walks the manufacturing order with a verification gate at each stage.
---

# Modelling a device for Portrayal

The method lives in the repository's documentation, written for a person and
equally binding on an agent:

- **`docs/modelling-a-device.md`** - the sources and their roles, the four
  stages in manufacturing order (panel, cutouts, silkscreen, components) with a
  gate at each, the power-figure rules, the two audits of Gate 5, and the
  canonical shape of `device.yaml`. Read it in full before starting a device.
- **`docs/modelling-pitfalls.md`** - what has gone wrong before. Read it when
  a figure, a measurement or a lint warning is not behaving as you expect.
- **`CONTRIBUTING.md`** - the commands, in the order CI runs them, including
  the lock check that must run before `--update`.
- **`library/components/README.md`** - namespaces, naming, the smallest
  complete contract, and what a skin must contain.

The output is `library/devices/<vendor>/<model>/device.yaml` linting clean at
`maturity: modelled`, plus the sentence Gate 5 asks for: *I put the render
beside the reference at matched scale, and here is what it showed.* A model
that cannot produce that sentence is not finished, and when you delegate a
device you require the sentence back, because "lint clean, six views" is exactly
what an interrupted attempt leaves behind.

## The gates, and what each one proves

You do not start a stage until the gate before it has passed. The guide has
the detail; this is the order and the question each gate answers.

| gate | after | the question | how you answer it |
|---|---|---|---|
| 1 | the panel | Can this figure be measured at all, and is the panel the right shape? | Compare the figure's pixel aspect with the datasheet width and height, then overlay your panel rendered `--without silkscreen`. |
| 2 | the cutouts | Is every hole there, on the right pitch? | Overlay again and count. L39 checks fit, overlap and empty openings. |
| 3 | the silkscreen | Is every printed legend present, spelled as printed, beside what it names? | Render with silkscreen and compare. L14 passes. |
| 4 | the components | Does the whole file hold together? | `./build.sh --device <model>` clean at `maturity: modelled`; read the tree and the capability level. |
| 5 | everything | Is it the device, and is it finished? | Walk the callouts and the spec table by name, then put the render beside the reference at matched scale, for every face that has one. |

## How the method is written

The guide and the pitfalls page hold three kinds of text, and each is read
differently.

- **A rule with its check.** This is nearly all of it. The rule is stated as a
  mechanism that holds on any hardware (a rotated placement pivots on its own
  centre before rotation, so recompute `at` and look at the render). You do not
  need to have met the device that taught it.
- **A measured table, kept with its sources.** The figure-aspect calibration
  and the per-ambient power figures name the vendor and the part because the
  number is only usable if it can be traced. Do not strip the names from these.
- **An example marked *Illustration*.** A few rules would read as over-caution
  without the case behind them. The rule comes first and the case after it, and
  the rule stands if you skip the case.

When you add a lesson, write it in the first form: say what the mechanism is
and how to check for it, and leave the device out. Name a device only if the
entry is a measurement, or if the rule is not believable without the case, and
then mark it. A lesson that only makes sense to someone who knows the product
is not finished.

## What is specific to working as an agent here

These are not in the docs because they are about the working tree rather than
the hardware. Each is a rule and the check that holds it.

- **Stage the paths you verified, never the whole tree.** Other agents may be
  writing devices in the same checkout, and `git add -A` commits their
  unverified work under your message. Use `git add
  library/devices/<vendor>/<model>` and the components you touched. Check:
  `git show --stat HEAD` lists only what the message names. If it does not and
  the commit is not pushed, amend the message to say what the commit holds.
- **Use a worktree.** `git worktree add .claude/worktrees/<name>` keeps your
  half-written device out of every other lint run, and theirs out of yours. The
  directory is gitignored.
- **A failure you cannot explain is re-run before it is believed.** A commit is
  atomic and a shared working tree is not, so a test run can photograph another
  writer's half-finished file. Check: the failure appears twice, on a tree
  `git status` shows as yours alone, before you commit a fix for it. Write
  paired edits (a contract and its skin) together, or check that both landed.
- **A check you propose is run against the real library before anyone
  believes it.** Test the structure (resolve the reference, read the declared
  token), never the sentence: a search over prose passes a false claim whose
  only use of the word is inside its own denial. Check: say what the rule finds
  on the library today, and plant one fault it must catch. This is also a line
  in [`docs/review-standards.md`](../../../docs/review-standards.md).
- **Run scripts from a directory that holds only your files.** In a shared
  temporary directory, a stray file named like a standard-library module
  shadows it, and every import fails in a way that looks like your code. Use
  the session's scratch directory. Check, when imports break for no reason:
  `python3 -c "import bisect; print(bisect.__file__)"` names the standard
  library.
- **A claim about how something renders is counted, not reasoned.** The
  pitfalls page, under Relief and 3D, has the case that prompted this: whether
  a part "renders flat" is answered by compiling it and counting `data-depth`.
