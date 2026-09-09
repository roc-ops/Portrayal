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

You need Python 3.12 with `pyyaml` and `jsonschema`, a POSIX shell, and a
browser. Everything else is optional and only for intake (converting vendor PDFs
into figures), which the modelling guide covers.

```sh
git clone https://github.com/roc-ops/Portrayal.git
cd Portrayal
python3 -m pip install pyyaml jsonschema pytest pillow numpy
./build.sh                       # lint, then compile every device into library/dist/
python3 tools/serve.py 8931      # then open http://localhost:8931/library/dist/
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

Open the render in the browser beside your reference at the same scale and say
what you see. This sentence goes in the pull request: which figure you compared
against, at what scale, what agreed, what did not, and what you did about it.
"Looks right" is not the sentence; "front over the datasheet elevation at
2.2 px/mm, port pitch and PSU cut-out agree, the status lamp sits 0.6 mm low
and is recorded as estimated" is.

### 5. Run the gates

In this order, because the second one asks a question the third one erases:

```sh
./build.sh --device <model>                               # lint clean
python3 spec/tools/portrayal/devicelock.py --library library   # read what it says
```

The lock check compares your device to `library/devices.lock.json` as
committed and says what version bump the change needs: a patch for wording and
provenance, a minor for something added, a major for geometry or ids that
moved. Bump `version:` in `device.yaml` accordingly, run the check again until
it reports zero findings, and only then:

```sh
python3 spec/tools/portrayal/devicelock.py --library library --update
./publish.sh --no-images                                  # build + DCIM exports
python3 -m pytest spec/tests -q                           # after publish; it skips without dist/
```

Commit the regenerated `library/devices.lock.json` and `library/exports/`
with your change. CI fails on a stale export.

### 6. Open the pull request

One device per pull request. The
[template](.github/PULL_REQUEST_TEMPLATE.md) asks for the sources, the
maturity you claim, the matched-scale comparison sentence, and the gates you
ran. A reviewer reads that before the diff.

CodeRabbit reviews every pull request first. Fix what is real, reply to what is
not with why, and the maintainer merges once the review is quiet and the
`gates` check is green. Anything under `library/exports/` or `library/dist/` is
generated; a review comment on one of those files is fixed in the source it
came from.

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
