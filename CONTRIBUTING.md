# Contributing to Portrayal

Most contributions are a device: a YAML manifest that places components on the
faces of a piece of hardware, compiled into an SVG where every port, lamp, PSU
and bay is addressable. This page is the path from "I have a switch I want in
the library" to a merged pull request. It is written to fit in an afternoon for
a device whose components already exist, and to tell you early when yours will
take longer.

If you are here to change the compiler, the schemas or the kit instead, the same
gates apply; skip to [The gates](#the-gates).

## Before you start

You need Python 3.12, a POSIX shell and a browser. **macOS or Linux**: the build
gates are shell scripts, and `build.sh` runs one renderer per device under
`xargs -P`. Everything else is optional and only for intake (converting vendor
PDFs into figures), which the modelling guide covers.

```sh
git clone https://github.com/roc-ops/Portrayal.git
cd Portrayal
python3 -m venv .venv && . .venv/bin/activate   # a Homebrew or distro Python refuses a bare pip install
python3 -m pip install -e ".[test]"
./build.sh                       # lint, then compile every device into library/dist/
python3 tools/serve.py 8931      # then open http://localhost:8931/kit/index.html
```

**The editable install is not optional.** The tools are a package - `portrayal` -
and they import each other by name; before that they inserted their own directory
onto `sys.path` in fourteen spellings across 94 files. `pip install -e .` is what
makes `import portrayal` resolve, for `python -m portrayal lint` and for the
`python3 spec/tools/portrayal/....py` paths the rest of this file gives alike.
The extras are `[test]`, `[render]` (rasterising DCIM images), `[intake]` and
`[bench]`.

`spec/tools/` is five directories and the split is what the gates run:

| | |
|---|---|
| `portrayal/` | the compiler - everything `build.sh`, `publish.sh` and CI reach, and nothing else |
| `dev/` | modelling probes, converters and one-offs; `python3 spec/tools/dev/<tool>.py --help` |
| `bench/` | measurement benchmarks, `pip install -e ".[bench]"` |
| `sweeps/` | corrective migrations, each paired with the lint rule that finds its work |
| `intake/` | vendor PDF, CAD and photo conversion, `pip install -e ".[intake]"` |

The dependency runs one way: the others may import the compiler and it imports
none of them, which a test asserts by walking the imports.

If you prefer a driver to a path, `python -m portrayal` wraps the gates:

```sh
python -m portrayal lint         # the library against the schemas
python -m portrayal lock         # what version bump your change needs
python -m portrayal build        # or `publish`, which adds the DCIM exports
python -m portrayal test
```

`./build.sh` is the check that your environment works. It lints the whole
library first and refuses to render anything if lint fails, so a clean build
means the tools and the data agree.

## The afternoon path

### 1. Claim the device

Open a [device request](https://github.com/roc-ops/Portrayal/issues/new?template=device-request.yml)
naming the vendor and model and saying you are modelling it. This is how two
people avoid building the same switch in the same week. Check
`library/devices/<vendor>/` first; if the model exists, you are improving it, not
adding it, and the request becomes a
[modelling defect](https://github.com/roc-ops/Portrayal/issues/new?template=modelling-defect.yml).

### 2. Stage the sources, outside the repository

Find the datasheet and the hardware installation guide, and any vendor gallery
images. Put them under `working/intake/<vendor>/<line>/`, which is gitignored,
and record each file and its URL in a `SOURCES.md` there. **Nothing vendor-made
is ever committed**: no PDF, CAD, stencil, photograph or figure. The manifest
carries the facts you read and cites where you read them; the documents stay on
your machine. If you have the hardware, the
[field-capture guide](docs/field-capture.md) says how to photograph and measure
it so the figures are usable.

### 3. Model it

The modelling guide is [`docs/modelling-a-device.md`](docs/modelling-a-device.md),
with [`docs/modelling-pitfalls.md`](docs/modelling-pitfalls.md) for when a figure
or a rule misbehaves. It walks the order the panel is
manufactured in: chassis and faces, then the holes punched in them, then the
printing, then the components seated in the holes; with a check at each stage.
The short version of what you will write:

- `chassis` dimensions and six `views`, each sized. A face with nothing on it
  says so in an `empty:` sentence rather than being left blank.
- `placements` of components from `library/components/` (`std/` for standard
  apertures, `common/` for parts shared across vendors, `<vendor>/` for the
  rest) and `bays` for anything field-replaceable, with what each bay `accepts`.
- `groups` that say what the ports, PSUs and fans are *for*, and `attrs` for
  the facts a DCIM wants.
- `provenance` for every figure: where it came from and how sure you are, using
  the vocabulary `datasheet`, `drawing`, `measured`, `photo-measured`,
  `registry`, `borrowed`, `estimated`, `known-wrong`. An `estimated` value is
  fine; an unlabelled one is not.
- `maturity`: `draft` while you work, `modelled` once every face is sourced,
  `verified` only when nothing in the assembly is estimated, components
  included. The linter holds you to the level you claim.
- `gaps`: what you could not find, with the reason. A gap you declare is a
  known unknown; one you leave silent looks like a finding.

### Reading what lint says

A clean tree reports a few thousand warnings. **That is the backlog, not your
change**, and its size is not the number to read. `library/lint-baseline.json`
records it, counted per file per rule, and every run ends with one of two lines:

```
LINT: no change against the baseline - every warning here was already in library/lint-baseline.json
LINT: 3 warnings NEW since the baseline (`--new-only` prints just the new ones; ...)
      +2   [L61] library/devices/acme/box/device.yaml
```

So the question "did I break something" is answered by the last line rather than
by running lint twice and diffing. `--new-only` prints just those warnings.

When you fix some, or add a device that legitimately brings its own, re-record:

```sh
python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library --update-baseline
```

and commit the result with your change. A baseline that has drifted from the tree
is worse than none - it reports phantom fixes and hides real additions - so a
test fails when the two disagree.

**A baseline is not a waiver.** It says "already true", not "decided". Where a
device genuinely will not satisfy a rule and somebody has worked out why, the
device says so and the reason is required:

```yaml
lint:
  waive:
    L44: >-
      the field is 100% buried in 2D and that is correct ... it is what punches
      the rear panel in 3D, which is what you see when a PEM is pulled.
```

Waived warnings are still counted and are printed with their reason under their
own heading - separated, never hidden. Reach for this only when the answer is
argued; the backlog belongs in the baseline where it stays visible.

### Which file you author

**`device.yaml`, unless the device already has a `layout.yaml` beside it.**

A face of 64 ports is four hundred lines that say the same thing sixty-four
times, so `spec/tools/portrayal/expand.py` can generate the placements, cutouts,
numerals and lamps of a regular block from a compact `layout.yaml` - about forty
lines for a face. Where a device has one, **the layout is the source and
`device.yaml` is generated**: edit the layout, re-run

```sh
python3 spec/tools/portrayal/expand.py library/devices/<vendor>/<model>/layout.yaml     --library library --schemas spec/schemas
```

and commit both. Editing the generated file instead is the one thing that breaks
this: `spec/tests/test_layout_in_step.py` re-expands every layout and fails if it
disagrees with the device beside it, because before that test existed both of the
library's layouts had silently drifted months behind - one still carrying a
registry figure the library removed, and one missing a key the schema had since
made required.

Thirty-five devices use one today, most of the Edgecore line. Adding a layout
to a device that has none is worthwhile where the face is regular and worth
nothing where it is not: expand.py passes longhand items through untouched
precisely so that an irregular block stays written out by hand.

Reuse before you build. Search `library/components/` for the part before
drawing it; a QSFP28 cage, an RJ45 jack or a C14 inlet almost certainly exists.
A new component needs a `contract.yaml` and a skin SVG drawn in millimetres;
the guide covers both, and the
[components README](library/components/README.md) says which namespace it goes
in and how it is named.

### 4. Look at it

```sh
./build.sh --device <model>      # lint this device, render it, refresh the indexes
```

Open `http://localhost:8931/kit/index.html?device=<model>` beside your reference
at the same scale and say what you see. That page is the explorer: pick the
device, switch faces, and click a part to see what it is and where it came from.
It reads `library/dist/`, so `./build.sh --device <model>` above is what puts
your change in it. This sentence goes in the pull request: which figure you compared
against, at what scale, what agreed, what did not, and what you did about it.
"Looks right" is not the sentence; "front over the datasheet elevation at
2.2 px/mm, port pitch and PSU cut-out agree, the status lamp sits 0.6 mm low,
recorded as estimated" is.

### 5. Run the gates

In this order, because the second one asks a question the third one erases:

```sh
./build.sh --device <model>                               # lint clean
python3 spec/tools/portrayal/devicelock.py --library library   # read what it says
```

The lock check compares your device to its own
`library/devices/<vendor>/<model>/device.lock.json` as committed and says what
version bump the change needs: a patch for wording and
provenance, a minor for something added, a major for geometry or ids that
moved. Bump `version:` in `device.yaml` accordingly, run the check again until
it reports zero findings, and only then:

```sh
python3 spec/tools/portrayal/devicelock.py --library library --update
./publish.sh --no-images                                  # build + DCIM exports
python3 -m pytest spec/tests -q                           # after publish; it skips without dist/
```

**Expect skips, and know which kind.** Most of the suite reads the build in
`library/dist/`, so on a tree that has not been built it skips several hundred
tests rather than failing them: run `./build.sh` (or `./publish.sh`) first. A
handful also skip on a built tree, because the reference images they compare
against are not in this repository. A skip count in the hundreds means no build,
not a clean suite.

To run every library-wide sweep against **one** device - the equivalent of
`./build.sh --device` for the suite:

```sh
python3 -m pytest spec/tests -q -k juniper/mx204
```

The sweeps are parametrised over the library with the device's slug as the test
id (`libdata.each_device()`), so a failure names the device in the id and the
rule in the message rather than handing you a list of slugs and a test name.

Commit the regenerated `device.lock.json` and `library/exports/` with your
change. CI fails on a stale export.

`--update` rewrites **only the devices whose fingerprint moved** - usually the
one you edited, plus any that seat a component you bumped - so `git status` is
the list of what changed rather than one 906 KB file you have to take on trust.
The one-file view is a build output at `library/dist/devices.lock.json`, for a
consumer outside the checkout; it is derived, so it cannot drift.

### 6. Open the pull request

One device per pull request. The
[template](.github/PULL_REQUEST_TEMPLATE.md) asks for the sources, the
maturity you claim, the matched-scale comparison sentence, the gates you ran,
and the merge danger. A reviewer reads that before the diff.

#### Merge danger

Most changes here are **two-way doors**: if one turns out wrong, a revert puts
things back and nobody outside the repository has to do anything. A new device
in its own directory is the usual case. Those merge on green gates.

A few are **one-way doors**. Something outside the repository has already
acted on the change by the time anyone notices it was wrong, so a revert does
not undo it. The pull request says which it is, and a one-way door waits for
the maintainer to read it. It is one-way if any of these is true:

- **The lock asks for a major bump** on any device or component. A major means
  an address somebody may hold has gone: a placement id, a bay, a ref.
- **A component is renamed or removed,** or a bay stops accepting a ref. A
  rename with no change to the drawing still costs a major on every device
  that seats the part.
- **A committed export is renamed or removed,** or a port name or interface
  type in one changes. A DCIM that has already imported the old document keeps
  the old data; [`CHANGELOG.md`](CHANGELOG.md) marks these as breaking for
  data already imported.
- **The manifest format, a schema key or a lint code is removed, renamed or
  changes meaning.** [`docs/format-stability.md`](docs/format-stability.md)
  has the rules.
- **The change publishes something:** a kit release, a tag. A published
  version cannot be withdrawn from whoever installed it.
- **It changes how changes are checked or merged:** a workflow, the merge
  script, a repository setting.

Beside the door, say the **blast radius**: who notices if it is wrong. One
device, every device that seats a part, DCIM data already imported, kit
consumers, CI only.

#### Review

A change is reviewed against
[`docs/review-standards.md`](docs/review-standards.md) before it merges. The
standards are the judgements no gate can make, and they are read at review,
not while building. The reviewer fixes what it finds and commits the fix; a
comment is for a question only the author or the maintainer can answer.

The maintainer merges once the `gates` check is green. Anything under
`library/exports/` or `library/dist/` is generated; a review comment on one of
those files is fixed in the source it came from.

How the maintainer merges, and why it is a script, is in
[`docs/maintainers.md`](docs/maintainers.md).

## The gates

Every pull request, device or not, passes the same checks: `lint`, `publish`
(build + exports), the `devicelock` check, `pytest`, and "exports are current".
CI runs them in that order because its lock check only has to confirm that the
lock you committed matches the tree. Locally the lock step comes earlier, as
step 5 shows: the check must see the lock *before* you regenerate it, or the
bump it would have asked for is lost, and publish comes *after* the bumps
because a version change alters the exports. Both orders end in the same
state, and CI verifies that they did.

## Commits

One sentence that says what is true after the change, optionally prefixed with
a scope: `mx204: the rear fans are three bays, not one placement`. The body
says why, when why is not obvious. Sign off every commit (`git commit -s`): the
project accepts contributions under the
[Developer Certificate of Origin](https://developercertificate.org/), and the
sign-off is your statement that you may submit the work under Apache-2.0. There
is no CLA.

## What will not be merged

- Vendor material in any form, including a figure "just for reference".
- A figure with no provenance, or a `verified` device with an `estimated`
  value anywhere in its assembly.
- Serial numbers, MAC addresses, IP addresses, hostnames or SNMP communities in
  a dump or a note. Dumps are committed sanitised, with those fields emptied.
- A pull request that touches a generated file by hand.

## Where to ask

Open an issue. There is a form for a device request, a modelling defect and a
tooling bug; anything else can be a blank issue. Design questions about the
format itself are welcome; look at the open issues under milestone
"2 · Format reconciliation" first, since the question may already be there.
