# Format stability: what can change, and what says so

Portrayal has four version numbers, and each answers a different question. This
page says what each one covers, what raises it, and what the project promises
about it while the package is at 0.x.

| Number | Where it appears | What it versions |
|---|---|---|
| `format` | every device manifest, component contract, listing and lab (`format: 1`) | the **file format** a manifest is written in |
| schema `v1` | the schema `$id`s and titles in `spec/schemas/` (device, component and listing; a lab has no schema yet) | the same thing, named: schema v1 *is* format 1 |
| package | `version` in `pyproject.toml` (0.1.0) | the **tools**: the linter, the compiler, the indexers and the exporter |
| `contract` | `devices.json` (`contract: 2` at 0.1.0) | the **published build** a consumer reads from `library/dist/`; `CHANGELOG.md` records each one |

The schemas are published at `https://portrayal.dev/schemas/v1/`, one file
per schema (`device.schema.json`, `component.schema.json`,
`listing.schema.json`), and that URL is each schema's `$id`, so an editor or a
validator that follows the `$id` finds the schema it names. A new format number
is published beside the old one under its own label (`/schemas/v2/`); a
published label is never reused for a different format.

Each device and component also carries its own semantic version and lock, which
records what changed in *that hardware's drawing*. That is a separate system,
and [DESIGN §9](../spec/DESIGN.md) covers it: art is a patch, an addition is a
minor, and geometry or ids are a major.

## What is a breaking change

**To the format** (which raises `format`, and the schema label with it):
- a key is removed or renamed;
- a key's meaning changes, for example a unit, a frame or what a value refers to;
- validation starts rejecting a file that used to be valid.

Adding an **optional** key does not raise `format`. A file written without it
stays valid, and a reader that ignores it is unaffected.

**To the published build** (which raises `contract`): the same rule applied to
the files under `library/dist/`. A field a consumer reads is removed or renamed,
or its meaning changes. A new field does not raise it.

The two move independently. A format change can leave the build's shape alone,
and a change to the build can happen without any change to the files authors
write.

## What else a consumer holds

Three more things reach a consumer outside this repository, and none of them
has a number of its own.

**A component major.** A manifest pins a component by name and major
(`name@2`), so removing a major breaks a manifest that pins it. While the
package is at 0.x, a superseded major may be removed, and every removal is
listed in `CHANGELOG.md` with the ref that replaces it. From 1.0, a retired
major is deprecated for at least one release before it is removed. DESIGN §9
has the reasoning.

**A lint code.** A device manifest waives a rule by its code (`lint.waive`),
so lint codes are never renumbered or reused. A rule that is deleted keeps its
code, listed as retired, and a new rule always takes a new code. A test pins
every code ever issued, so a code that moves or is handed to another rule
fails the suite.

**The DCIM exports** under `library/exports/` (NetBox and Nautobot device and
module types, and the fibre maps) are generated from the manifests and are not
covered by the `contract` number, which versions `library/dist/` only. They
follow the DCIM's own schema, and what can break is what an already-imported
record is called: a model name, a port name, a bay position. Before 1.0 such a
change is allowed, and it is announced in `CHANGELOG.md`, marked **BREAKING for
DCIM data already imported**, with what it renames. From 1.0 it is treated as
a `contract` change is.

## What is promised before 1.0

The package is at 0.x, and at 0.x the promise is deliberately small:

- **The tools read the current format only.** When `format` goes up, files are
  migrated in the same change. Older files are not read side by side.
- **Every breaking change is announced.** A `format` or `contract` change, a
  DCIM export change that re-files imported data, and a removed component major
  are each listed in `CHANGELOG.md`, with what to change in a file or a
  consumer to move across.
- **The version says so.** A change that raises `format` or `contract` also
  raises the package's minor version, so 0.1 to 0.2 is where to look.

## What 1.0 will promise

From 1.0, a change that raises `format` or `contract` is a major version of
the package. The **previous** format stays readable, and the previous
`contract` stays documented, for one release after the change, so a consumer
has a release in which to move.
