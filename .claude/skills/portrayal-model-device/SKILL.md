---
name: portrayal-model-device
description: Use when modelling a hardware device for Portrayal from reference material (datasheets, install guides, drawings, photos) - building or revising a device.yaml and any components it needs, through to the pull request. Walks the manufacturing order with a verification gate at each stage, then the steps that finish a contribution.
---

# Modelling a device for Portrayal

The method lives in the repository's documentation, written for a person and
equally binding on an agent:

- **`docs/modelling-a-device.md`** - the sources and their roles, the four
  stages in manufacturing order (panel, cutouts, silkscreen, components) with a
  gate at each, the ears-and-kits step that follows the panel, the
  power-figure rules, the two audits of Gate 5, and the
  canonical shape of `device.yaml`. Read it in full before starting a device.
- **`docs/modelling-pitfalls.md`** - what has gone wrong before. Read it when
  a figure, a measurement or a lint warning is not behaving as you expect.
- **`CONTRIBUTING.md`** - the commands, how to read what lint says, the
  preflight checks, and the lock check that must run before `--update`.
- **`docs/device-template.yaml`** - the file to copy for a new device, with a
  comment on every key.
- **`library/components/README.md`** - namespaces, naming, the smallest
  complete contract, and what a skin must contain.
- **`docs/rack-mounting-design.md`** - for a rack device: ear positions,
  `chassis.kits`, and the `kind: kit` contract a rail kit is written as.
- **`docs/field-capture.md`** - when you hold the hardware: how to photograph
  and measure it so the figures are usable.
- **`docs/deliberately-empty-faces.md`** - why `empty:` is a claim about a
  face, and what it must say.
- **`docs/listing-a-nos.md`** - to list a box under a NOS vendor (ArcOS, OcNOS,
  DNOS, SONiC) without copying the hardware.

The output is a pull request that is ready for review, and it holds:

- `library/devices/<vendor>/<model>/device.yaml` at the `maturity` its sources
  earn (the next section), linting with no new warning;
- the sentence Gate 5 asks for: *I put the render beside the reference at
  matched scale, and here is what it showed.* A model that cannot produce that
  sentence is not finished, and when you delegate a device you require the
  sentence back, because "lint clean, six views" is exactly what an interrupted
  attempt leaves behind;
- everything the Submit stage produces: the lock, the exports, the changelog
  fragment, signed-off commits and the filled pull request template.

A `device.yaml` that lints is the middle of the work, not the end of it.

## What to claim: the maturity levels

`maturity` is a claim about the sources, and lint holds you to the level you
write (L15). Claim the lowest level that is true.

| level | what earns it | the check |
|---|---|---|
| `draft` | Anything still being drawn, including a face with no source yet. A draft is a fine thing to submit, and welcome. | The unsourced faces and parts are declared in `gaps:`. |
| `modelled` | Every face is sourced: each figure has provenance, and each face is drawn or says it has nothing on it. | L15 is clean at this level, and every face either has content or an `empty:` sentence. |
| `verified` | No `estimated` value anywhere in the assembly, components included. | L15 is clean at this level, and no placed component's contract carries an `estimated` size. |

**`empty:` is only for a face with nothing on it.** It is a claim that you
searched and the face carries no printing, part or opening
([deliberately-empty-faces.md](../../../docs/deliberately-empty-faces.md)). A
face that carries something you have not drawn yet is a **gap**, not an empty
face:

```yaml
gaps:
- what: rear-panel
  scope: [rear]
  reason: needs-drawing
  note: <what the face carries, and that no dimensioned figure of it is held>
  wanted: <the drawing or photograph that would let it be drawn>
```

and the device stays `draft` until the gap is closed. Check: for each face
written `empty:`, the guide or photograph names nothing on that face (read its
overview figure and its port and connector tables, not the front alone); for
each face a gap names, `maturity` is `draft`.

## The gates, and what each one proves

You do not start a stage until the gate before it has passed. The guide has
the detail; this is the order and the question each gate answers.

| gate | after | the question | how you answer it |
|---|---|---|---|
| 1 | the panel | Can this figure be measured at all, and is the panel the right shape? | Compare the figure's pixel aspect with the datasheet width and height, then overlay your panel rendered `--without silkscreen`. |
| 1b | the ears and the kits (a `rack` device only) | Does the device ship in the position marked `default`, and is every kit it takes listed with the newest range? | Lint: L125 and L160 to L165 clean, and L155 to L159 for a kit you wrote. Put the `default` position beside the rack-mounting figure, and each kit range beside the newest source that gives it. |
| 2 | the cutouts | Is every hole there, on the right pitch? | Overlay again and count. L39 checks fit, overlap and empty openings. |
| 3 | the silkscreen | Is every printed legend present, spelled as printed, beside what it names? | Render with silkscreen and compare. L14 passes. |
| 4 | the components | Does the whole file hold together? | Lint clean (below) with `./build.sh --device <model>`; render with and without silkscreen; open the viewer and read the tree; set the `maturity` the sources earn and lint again; read the capability level and its `blocked:` reason. |
| 4b | the build | Does every connector the change adds have a mate, or a sentence saying none can exist? | `part_conformance.py --scan --refs <model>` finds nothing without a record (a mate, an `unmated:` sentence, or a row in `library/conformance-exceptions.yaml`), and `spec/tests/test_port_usable_records.py` passes. Only C19 to C22 and their records; state the scan's counts in the pull request. |
| 5 | everything | Is it the device, and is it finished? | Walk the callouts and the spec table by name, walk the L27 and L29 warnings, then put the render beside the reference at matched scale, for every face that has one. |
| Submit | the branch | Can a maintainer merge it on green? | The eight steps below, each with its check. |

**Lint clean means no warning that is new.** A clean tree reports thousands of
warnings, so the number is not the test. The last line of the run is: it reads
`LINT: no change against the baseline` when nothing you did added one, and
`LINT: <n> warnings NEW since the baseline` when something did. Fix a new
warning, or, where the device will not satisfy a rule and you can argue why,
waive it under `lint: waive:` with the reason, which is required. Re-record
`library/lint-baseline.json` with `--update-baseline` only for warnings you
fixed or ones a new device legitimately brings, and commit it with the change.
A warning on a stock component you did not edit was there
before you. Check: the last line, and `--new-only` prints only what is yours.

**If the device has a `layout.yaml`, it is the source.** Edit the layout and
re-run `spec/tools/portrayal/expand.py`; never edit the generated
`device.yaml` beside it. Check: `spec/tests/test_layout_in_step.py` re-expands
every layout and fails if the device disagrees. A device with no layout is
authored in `device.yaml`.

The step behind gate 1b comes after the panel and before the cutouts. Three
of its rules are the ones most often broken, each with its check:

- **`at` is written only when a figure or a drawing gives it.** A position the
  guide only names keeps its name and has no number. Check: each `at` cites
  its figure in provenance.
- **A kit is referenced, never copied, and never placed.** Search the library
  for the kit before writing a `kind: kit` contract. Check: L161 passes, and
  L5 and L10 pass.
- **Ears are not drawn and `common/rack-ear@1` is not placed on a new device.**
  A generic ear is drawn from `chassis.ears` only when a viewer asks. Check:
  the default build shows no ears.

## Submit: the steps after Gate 5

A device that passes Gate 5 is not yet a contribution. Maintainers merge on
green gates, and each step below is one a gate or a reviewer would otherwise
send back. Run them in this order, from the checkout you changed. The first
three put the branch in the state the others measure.

| # | step | rule | check |
|---|---|---|---|
| 1 | Up to date | Bring the branch up to the project's main (`origin/main`; `upstream/main` in a fork) before the lock, because the lock is measured against main's. | `git fetch`, then `git merge-base --is-ancestor origin/main HEAD` exits 0. |
| 2 | The lock | Run `python3 spec/tools/portrayal/devicelock.py --library library` first and read what it asks. Bump `version:` in `device.yaml` as it says (patch, minor, major), and repeat until it reports zero findings. Only then run it again with `--update`, which writes `device.lock.json`. | The first run ends `devicelock: 0 finding(s)`; after `--update`, `git status` shows the lock of the device you edited, plus any device that seats a component you bumped. |
| 3 | The exports | Run `./publish.sh --no-images` (the flag comes first) and commit what it regenerates under `library/exports/`. A generated file is never edited by hand; fix the source it came from and run it again. | After the commit, `git status --short library/exports` is empty, and preflight's `exports` check passes. |
| 4 | The changelog | A new file under `changelog.d/`, named for the topic, with its entry under `### Added`, `### Changed`, `### Removed` or `### Fixed`. `CHANGELOG.md` is not edited, and neither is the kit version: that is bumped when the kit is published. | `python3 spec/tools/portrayal/changelog.py --check` prints `<n> changelog fragment(s), all well formed`. |
| 5 | The tests | Run `python3 -m pytest spec/tests -q -n auto` after the publish, because most of the suite reads `library/dist/` and skips without it. | The run passes, and `-rs` gives a reason for each skip; hundreds of skips mean no build, not a clean suite. |
| 6 | Preflight | Run `python3 spec/tools/portrayal/preflight.py --json` and fix every FAIL line with the command it names. Two checks, `prose` and `conformance`, are advice: they print PASS or WARN and a WARN does not fail. Shorten a new sentence of more than 25 words in a `description` or an `attrs` string; run the tests, which write `library/dist/part-conformance.json`, for `conformance`. | The exit status is 0 and no check reads FAIL. |
| 7 | The sign-off | Every commit carries a `Signed-off-by:` line (`git commit -s`). Only the human contributor can agree to the [Developer Certificate of Origin](https://developercertificate.org/): it is their statement that they may submit the work under Apache-2.0. So an assistant asks the contributor to read it and to say they agree, and adds the line only after they have. | `git log origin/main..HEAD --no-merges --grep='^Signed-off-by:' --invert-grep --format='%h %s'` prints nothing. |
| 8 | The description | Fill in every section of `.github/PULL_REQUEST_TEMPLATE.md`, heading for heading and in its order, and show the draft to the contributor before it is saved. The `portrayal-pr` skill says how to write each section. | The body's headings are the template's headings, in order, and none is empty. |

Steps 2 to 6 can send you back to an earlier step: a version bump changes the
exports, and an export fix changes the diff the lock is read against. After the
last edit, run 2 to 6 once more in order. Preflight is not a gate and does not
replace steps 2 to 5; CI still builds, publishes and runs the suite.

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
  unverified work under your message. Name what the change produced, by path:
  the device folder, each component you touched, the regenerated
  `device.lock.json`, the `library/exports/` files that moved and one
  `changelog.d/` fragment. Check: `git show --stat HEAD` lists only what the
  message names, and `git status --short` is empty afterwards. If the commit
  holds more and is not pushed, amend the message to say what it holds.
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
