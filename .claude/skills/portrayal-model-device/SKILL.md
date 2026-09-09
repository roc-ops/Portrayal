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

## What is specific to working as an agent here

These are not in the docs because they are about the working tree rather than
the hardware.

- **`git add -A` is a snapshot of every agent's work, not yours.** With other
  agents writing devices in the same tree, a broad add swept an unverified
  device into a commit whose message named a different one, so the log asserted
  a file had been reviewed when it had not. Stage the explicit paths you
  verified (`git add library/devices/<vendor>/<model>`), and if you catch one
  late, amend the message to name what the commit actually holds.
- **A commit is atomic; the working tree is not.** With more than one agent in
  the repo, a test run is a photograph of whatever was half-written when it
  started. An agent saw four failures seconds after its own lint run came back
  clean, because another agent was writing files underneath it. Re-run before
  believing a failure you cannot explain, and never commit a fix for one until
  you have seen it twice. Paired edits (a contract and its skin) belong in one
  write, or behind a check that both landed.
- **Use a worktree.** `git worktree add .claude/worktrees/<name>` keeps your
  device's half-written state out of everyone else's lint run. The directory is
  gitignored.
- **A check you propose must be run against the real corpus before it is
  believed.** A rule to catch `borrowed` confidence claiming an ancestry that
  does not exist was proposed twice and run by nobody; when run, it passed five
  of the six false claims it existed to catch, because it searched prose and the
  clearest false claim's only use of the word was inside its own denial. Test
  the structure (resolve the reference, read the origin's declared token), never
  the sentence. Searching prose measures the searcher's expectations.
- **Do not run Python from `/tmp`.** A stray `bisect.py` there shadows the
  standard library and every import breaks in a way that looks like your code.
  Use the session's scratchpad directory.
- **Before writing "renders flat", compile and count.** `render.py` emits
  `data-depth` for every composed aperture regardless of the parent's `relief`
  block. Compile the component through `instance_group` and count `data-depth`
  in the output; this has been reasoned about wrongly three times in a day in
  both directions.
