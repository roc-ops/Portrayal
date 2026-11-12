# Retiring a component major: the window, and what checks it

Status: proposed. The rule for a retired major was decided 2026-10-10 (#448):
while the package is at 0.x a superseded major may be removed, and from 1.0 it is
deprecated before it is removed. The marker and the L89 distinction are built.
The support window is **not** decided; this note lays out what is left and
proposes a way to close it.

This note changes nothing. It adds no schema key, no lint rule and no library
file. The items that would be one-way, if built, are listed in "What moves when
it is built".

## What is already in place

| Part of the rule | Where it lives |
| --- | --- |
| A retired major says where it went: `superseded-by: <ns/name@major>` on its contract, the key the schema already has. No second `deprecated:` key. | `spec/schemas/component.schema.json`, `spec/DESIGN.md` section 9 |
| The ref is a different major that exists, and a kit's successor is a kit. | L101 |
| A retired major that still ships is not "dead": L89 accepts it when its marker names a different major that exists, and still fails a superseded major that nothing seats, nothing names and that says nothing. | L89, `docs/lint-rules.md` |
| At 0.x a superseded major may be removed, and every removal is listed in `CHANGELOG.md` with the ref that replaces it. | `spec/DESIGN.md` section 9, `docs/format-stability.md`, `library/components/README.md`, `CHANGELOG.md` |
| The build publishes the marker: `components.json` carries `superseded-by` on every major, and the DCIM module export leaves a retired major out, because its model is its successor's. | `spec/tools/portrayal/components_index.py`, `spec/tools/portrayal/dcim_export.py` |
| A removed major that a saved rack names can be redirected by `supersedes:` on its replacement. | `docs/format-stability.md`, L184 |

## What is measured today

- 92 of the 2,691 component contracts carry `superseded-by:`: 8 Cisco, 3 common,
  1 Edgecore, 2 generic, 73 Juniper and 5 UfiSpace.
- Of those 92, one retired major names a successor that is itself retired:
  `juniper/mic-3d-4xge-xfp@2` names `@3`, whose own marker names `@4`; and
  `common/qsfp-transceiver@1` names `generic/qsfp-lc@1`, which is retired in
  favour of `@2`. L101 asks that the successor exists and is not the part itself,
  and nothing asks that it is live. No marker names a ref that is absent.
- Nothing outside this repository can pin a major yet, so no retirement has
  broken an outside manifest, and none can before the repository is public.

## What is not decided

The five items below are needed before 1.0 is cut. Each is a question, with the
choices it has, and the open questions at the end repeat them.

**1. How long the window is.** DESIGN section 9 says "at least one release". That
is a floor and not a number, and no tool reads it. A window can be counted in
releases of the package (the version is in `pyproject.toml`; `CHANGELOG.md` has
one section per release) or in days from the release that first carried the
marker. Counting releases is what the text says today.

**2. Where the window is recorded, so that a deletion can be checked against it.**

- *Text only.* The number is written in `docs/format-stability.md`, and a reviewer
  checks a removal against `CHANGELOG.md`. No key, no rule, nothing one-way. It
  cannot tell when a major was first marked, except by reading history.
- *A key on the retired contract that names the release that deprecated it*
  (a new `deprecated-in:`-style key). A check can then fail a removal that is
  earlier than the window. It adds a schema key, which is one-way, and each of the
  92 contracts above needs a value that history may not give exactly.
- *No key; the check reads the merge base.* Preflight already compares a diff with
  `origin/main`. A removal of a contract that the base marks `superseded-by:` could
  be counted against the release headings in `CHANGELOG.md`. It adds no key, and
  it moves the check from the tree to the diff, which is how the soft `prose`
  check already works.

**3. What a retirement with no successor is.** The marker's value is the
replacing ref, so a part that is withdrawn with no replacement cannot say so. At
0.x that is a removal listed in `CHANGELOG.md`. From 1.0 the deprecation has no
key to carry it.

**4. Whether a chain is allowed.** A consumer told to pin `@3` that finds `@3`
retired is told twice. The two chains above exist today. The choices are to allow
it, to require the marker to name the live major, or to have the build publish the
end of the chain.

**5. What the build publishes for a deprecated major.** `components.json` has
`superseded-by` and the module export skips the part. A consumer reading the index
cannot tell a major in its window from one that is already due for removal,
because no window is recorded.

## Proposal

Close what text can close now and build nothing one-way:

1. State the window as a number of package releases in `docs/format-stability.md`
   and `spec/DESIGN.md` section 9, so the promise a consumer reads has a figure.
2. Check a removal against it in review, from `CHANGELOG.md`, as at 0.x.
3. Leave the key, the check on removal and the chain rule until a first retirement
   is made after the repository is public. Those are the items that cannot be
   taken back.

## What moves when it is built

| Item | Effect | Door |
| --- | --- | --- |
| A number in the text only | none on the lock, the exports or any consumer's file | two-way |
| A `deprecated-in:`-style key | a schema key every consumer's validator must learn; `components.json` may gain a field; the 92 contracts need a value; a device lock records the digest of each contract the device seats, so a device that still seats a retired major moves | one-way |
| A check on removal in preflight | no library file changes; a new advisory or failing line | two-way |
| A rule that a successor is live | a new lint code, never an old one reused; the two chains above would need a marker edit, which moves no export | one-way for the code |

## Open questions

Each is a place where the text above proposes and does not decide. Whoever
decides records it as an `OWNER DECISION:` comment on #448.

1. How many releases is the window?
2. Is the window recorded in text only, in a key on the contract, or by the check
   reading the merge base?
3. What does a retirement with no successor say?
4. Is a chain of retired majors allowed?
5. Does the build say, for a deprecated major, where it is in its window?
