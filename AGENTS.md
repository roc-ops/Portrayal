# Working on Portrayal as an AI agent

This file is for coding agents of any kind. Everything it points at is ordinary
documentation that a person follows the same way.

## Read these first

- [`docs/modelling-a-device.md`](docs/modelling-a-device.md): how a device is
  modelled, in manufacturing order, with a gate at each stage. Read it in full
  before you start a device.
- [`docs/modelling-pitfalls.md`](docs/modelling-pitfalls.md): what has gone
  wrong before. Read it when a figure, a measurement or a lint warning does not
  behave as you expect.
- [`CONTRIBUTING.md`](CONTRIBUTING.md): the commands, in the order CI runs them,
  including the lock check that has to run before `--update`.
- [`library/components/README.md`](library/components/README.md): namespaces,
  naming, and what a component contract and its skin must contain.
- [`docs/listing-a-nos.md`](docs/listing-a-nos.md): listing a box under a NOS
  vendor (ArcOS, OcNOS, DNOS, SONiC) without copying the hardware.

Read this one when you review, not while you build:

- [`docs/review-standards.md`](docs/review-standards.md): the judgements no
  gate can make, for the second pass over a finished change.

## The skills are documents

`.claude/skills/*/SKILL.md` are written for Claude Code, but they are plain
Markdown instructions and you can follow them by hand.
`portrayal-model-device` points at the documents above.
`portrayal-vendor-intake` stages a vendor's datasheets and guides and converts
the PDFs with docling. It assumes the conversion runs on a separate machine
with a GPU; running docling locally works too, only more slowly.
`portrayal-review` reviews a change against its sources and the review
standards, and fixes what it finds. `portrayal-pr` writes the pull request
body, including its merge danger. `portrayal-retro` reads what recent work got
wrong and proposes checks, standards and test redesigns; it changes nothing
itself.

## The gates

```sh
./build.sh --device <model>                                   # lint, then render one device
python3 spec/tools/portrayal/devicelock.py --library library   # the version bump a change needs
./publish.sh --no-images                                       # the build plus the DCIM exports
python3 -m pytest spec/tests -q -n auto                        # after a build; it reads library/dist
python3 spec/tools/portrayal/preflight.py --json               # seconds, no build; before asking for review
```

Preflight checks the diff against `origin/main` for what review rounds keep
finding: stale exports, an unallowed skip reason, private paths, a missing
changelog fragment, lock and lint findings, and `kit` tests. Every FAIL line
names the command that fixes it. A WARN line is advice and does not fail: the
`prose` check warns on a new or changed sentence over 25 words in a
description or an `attrs` string. CONTRIBUTING.md has the table.

Run them from the checkout you changed. `build.sh` and `publish.sh` make the
tools import this checkout's `portrayal`. When you call a tool directly, put
`spec/tools` on `PYTHONPATH` first, or an editable install elsewhere on the
machine answers instead.
