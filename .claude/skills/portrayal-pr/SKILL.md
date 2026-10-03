---
name: portrayal-pr
description: Use when writing or updating the body of a Portrayal pull request. Fills the repository's template - what changed as the smallest picture that shows it, the sources, the comparison against the reference, the gates and what the tests cost, and the merge danger.
---

# Writing a Portrayal pull request

The body follows **[`.github/PULL_REQUEST_TEMPLATE.md`](../../../.github/PULL_REQUEST_TEMPLATE.md)**,
heading for heading. A reviewer reads it before the diff, so each section says
what is true after the change and how you know. Keep prose short and skip
preamble.

## What this changes

One or two sentences, then the smallest picture that makes the change clear.
Pick one or two; most changes need no more.

- A new device or component: a shallow tree of what was added.

  ```text
  library/devices/<vendor>/<model>/
  ├── device.yaml     # front, rear, top; configurations ac, dc
  └── layout.yaml
  library/components/<vendor>/<psu>/v1/   # new: the supply both configs seat
  ```

- A change to something that exists: a `diff` of its shape, not of its lines.

  ```diff
   views.rear.bays
     psu-0   accepts: vendor/psu-ac@1
  -  psu-1   accepts: vendor/psu-ac@1
  +  psu-1   accepts: vendor/psu-ac@1, vendor/psu-dc@1
  ```

- Tool or kit logic: pseudocode or a call tree of the behaviour, as a `diff`
  when it changed.
- A flow between parts (build, index, kit): a small Mermaid sequence diagram.

Vendor photographs and figures never go in a pull request. A render of ours
does; describe the comparison in words under the heading below.

## Sources, maturity, comparison

Fill these as the template asks. The comparison is the sentence Gate 5 of
[`docs/modelling-a-device.md`](../../../docs/modelling-a-device.md) requires:
what you put beside the reference, at what scale, and what it showed, for every
face that has a reference. Name any face that has none.

For a change that is not a device, replace the comparison with **evidence**:
the test that failed before and passes now, or the output before and after.

## Gates run locally

Tick only what you ran, on this tree, after your last edit. Then add what the
tests cost. CI reports it in the job summary once the run finishes; quote the
flagged lines, or say that nothing was flagged. If you added a test of five
seconds or more, say here why a lint rule or a cheaper fixture could not
answer the same question.

## Merge danger

State the door and the blast radius. Work them out; do not guess.

```sh
python3 spec/tools/portrayal/devicelock.py --library library   # names every bump the change needs
git diff origin/main...HEAD --stat -- library/exports .github spec/schemas kit/package.json
```

**One-way** if any of these is true. Each is listed, with the reason, in
[`CONTRIBUTING.md`](../../../CONTRIBUTING.md#merge-danger):

- the lock asks any device or component for a **major** bump;
- a component is renamed or removed, or a bay's `accepts` or `default` loses a
  ref;
- a file under `library/exports` is renamed or removed, or a port name or
  interface type in one changes;
- the manifest format, a schema key or a lint code is removed, renamed or
  changes meaning;
- the change publishes: a kit release, a tag;
- it touches `.github/workflows`, the merge script, or a repository setting.

Otherwise it is **two-way**: a revert restores the previous state and nobody
outside the repository has to do anything.

**Blast radius** is who notices if it is wrong, in a word or two and then a
sentence: `one device`, `every device seating <part>`, `DCIM data already
imported`, `kit consumers`, `CI only`.

A one-way door is held for the maintainer. Say so plainly in the section, and
say what you checked that makes you confident.

## Before you post

- Every heading in the template is present, in its order.
- No vendor material, no person named as a decider, no untracked path.
- The body says nothing you did not check.
